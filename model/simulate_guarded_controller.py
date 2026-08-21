"""Simulate final system actions after circular confidence gating."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from compare_decision_algorithms import (
    circular_stats,
    classify_initial_mean,
    classify_periodic_mean,
    decision_margin,
)
from cpu_sampling_decision import DecisionKind, SampleEdge


DEFAULT_MIN_CONCENTRATION = 0.9
DEFAULT_MIN_NORMALIZED_MARGIN = 0.025


@dataclass(frozen=True)
class GuardDecision:
    accepted: bool
    final_edge: SampleEdge | None
    action: str
    reason: str
    circular_mean: float
    concentration: float
    normalized_margin: float


def _passes_gate(
    concentration: float,
    normalized_margin: float,
    min_concentration: float,
    min_normalized_margin: float,
) -> tuple[bool, str]:
    if concentration < min_concentration:
        return False, "low_concentration"
    if normalized_margin < min_normalized_margin:
        return False, "low_decision_margin"
    return True, "accepted"


def simulate_initial(
    samples: list[int],
    period: float,
    min_concentration: float,
    min_normalized_margin: float,
) -> GuardDecision:
    stats = circular_stats(samples, period)
    if stats.mean_phase_count != stats.mean_phase_count:
        return GuardDecision(
            False, None, "recalibrate", "undefined_circular_mean",
            stats.mean_phase_count, stats.concentration, float("nan")
        )
    margin = decision_margin(stats.mean_phase_count, "initial", period)
    normalized_margin = margin / period
    accepted, reason = _passes_gate(
        stats.concentration,
        normalized_margin,
        min_concentration,
        min_normalized_margin,
    )
    if not accepted:
        return GuardDecision(
            False, None, "recalibrate", reason,
            stats.mean_phase_count, stats.concentration, normalized_margin
        )

    candidate = classify_initial_mean(stats.mean_phase_count, period)
    if candidate == DecisionKind.SET_RISING.value:
        edge = SampleEdge.RISING
    elif candidate == DecisionKind.SET_FALLING.value:
        edge = SampleEdge.FALLING
    else:
        return GuardDecision(
            False, None, "recalibrate", "unresolved_initial_boundary",
            stats.mean_phase_count, stats.concentration, normalized_margin
        )
    return GuardDecision(
        True, edge, f"set_{edge.value}", "accepted",
        stats.mean_phase_count, stats.concentration, normalized_margin
    )


def simulate_periodic_batch(
    samples: list[int],
    period: float,
    current_edge: SampleEdge,
    min_concentration: float,
    min_normalized_margin: float,
) -> GuardDecision:
    stats = circular_stats(samples, period)
    if stats.mean_phase_count != stats.mean_phase_count:
        return GuardDecision(
            False, current_edge, f"keep_{current_edge.value}",
            "undefined_circular_mean", stats.mean_phase_count,
            stats.concentration, float("nan")
        )
    margin = decision_margin(
        stats.mean_phase_count, "periodic", period, current_edge
    )
    normalized_margin = margin / period
    accepted, reason = _passes_gate(
        stats.concentration,
        normalized_margin,
        min_concentration,
        min_normalized_margin,
    )
    if not accepted:
        return GuardDecision(
            False, current_edge, f"keep_{current_edge.value}", reason,
            stats.mean_phase_count, stats.concentration, normalized_margin
        )

    candidate = classify_periodic_mean(
        stats.mean_phase_count, period, current_edge.value
    )
    if candidate == DecisionKind.SET_RISING.value:
        final_edge = SampleEdge.RISING
    elif candidate == DecisionKind.SET_FALLING.value:
        final_edge = SampleEdge.FALLING
    else:
        final_edge = current_edge
    return GuardDecision(
        True, final_edge,
        f"set_{final_edge.value}" if final_edge != current_edge else f"keep_{current_edge.value}",
        "accepted", stats.mean_phase_count, stats.concentration, normalized_margin
    )


def simulate_scenario(
    scenario: dict[str, Any],
    period: float,
    min_concentration: float,
    min_normalized_margin: float,
) -> dict[str, Any]:
    stage = scenario["stage"]
    if stage == "initial":
        decision = simulate_initial(
            scenario["samples"], period,
            min_concentration, min_normalized_margin
        )
        return {"name": scenario["name"], "stage": stage, "decisions": [decision]}

    current_edge = SampleEdge(scenario["current_edge"])
    batches = scenario["batches"] if stage == "periodic_sequence" else [scenario["samples"]]
    decisions: list[GuardDecision] = []
    for batch in batches:
        decision = simulate_periodic_batch(
            batch, period, current_edge,
            min_concentration, min_normalized_margin
        )
        decisions.append(decision)
        assert decision.final_edge is not None
        current_edge = decision.final_edge
    return {"name": scenario["name"], "stage": stage, "decisions": decisions}


def render_markdown(
    simulations: list[dict[str, Any]],
    period: float,
    min_concentration: float,
    min_normalized_margin: float,
) -> str:
    lines = [
        "# 带置信门的 CPU 最终动作模拟",
        "",
        f"探索门限：集中度 ≥ `{min_concentration:g}`，圆周裕量/T ≥ `{min_normalized_margin:g}`；`T={period:g}`。",
        "",
        "首次校准拒绝后请求重测；运行期拒绝后保持当前采样沿。",
        "",
        "| 场景 | 门限结果 | 原因 | 最终动作序列 |",
        "|---|---|---|---|",
    ]
    for simulation in simulations:
        decisions: list[GuardDecision] = simulation["decisions"]
        gate_text = " -> ".join("接受" if item.accepted else "拒绝" for item in decisions)
        reasons = " -> ".join(item.reason for item in decisions)
        actions = " -> ".join(item.action for item in decisions)
        lines.append(
            f"| {simulation['name']} | {gate_text} | {reasons} | {actions} |"
        )

    lines.extend(
        [
            "",
            "## 解释限制",
            "",
            "`recalibrate` 只表示首次校准不能发布新的采样沿；重试次数、默认安全沿和最终故障升级策略尚未定义。门限仍是探索参数。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios", type=Path,
        default=Path(__file__).with_name("algorithm_scenarios.json")
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).with_name("guarded_controller_results.md")
    )
    parser.add_argument(
        "--min-concentration", type=float,
        default=DEFAULT_MIN_CONCENTRATION
    )
    parser.add_argument(
        "--min-normalized-margin", type=float,
        default=DEFAULT_MIN_NORMALIZED_MARGIN
    )
    args = parser.parse_args()

    data = json.loads(args.scenarios.read_text(encoding="utf-8"))
    period = float(data["period_count"])
    simulations = [
        simulate_scenario(
            scenario, period,
            args.min_concentration, args.min_normalized_margin
        )
        for scenario in data["scenarios"]
    ]
    report = render_markdown(
        simulations, period,
        args.min_concentration, args.min_normalized_margin
    )
    args.output.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
