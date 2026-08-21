"""Compare the reconstructed legacy mean with circular phase statistics."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cpu_sampling_decision import (
    DecisionKind,
    SampleEdge,
    decide_initial,
    decide_periodic,
)


@dataclass(frozen=True)
class CircularStats:
    mean_phase_count: float
    concentration: float


def circular_distance(a: float, b: float, period: float) -> float:
    direct = abs(a - b) % period
    return min(direct, period - direct)


def decision_margin(
    mean: float,
    stage: str,
    period: float,
    current_edge: SampleEdge | None = None,
) -> float:
    """Return distance to the nearest phase where the output edge changes."""
    if math.isnan(mean):
        return float("nan")
    if stage == "initial":
        boundaries = (period / 4, 3 * period / 4)
    elif stage == "periodic":
        if current_edge is None:
            raise ValueError("current_edge is required for periodic margin")
        if current_edge == SampleEdge.FALLING:
            boundaries = (5 * period / 12, 7 * period / 12)
        else:
            boundaries = (period / 12, 11 * period / 12)
    else:
        raise ValueError(f"unsupported margin stage: {stage}")
    return min(circular_distance(mean, boundary, period) for boundary in boundaries)


def circular_stats(samples: list[int], period_count: float) -> CircularStats:
    if not samples:
        raise ValueError("at least one phase sample is required")
    if period_count <= 0:
        raise ValueError("period_count must be positive")

    angles = [2.0 * math.pi * sample / period_count for sample in samples]
    mean_cos = sum(math.cos(angle) for angle in angles) / len(angles)
    mean_sin = sum(math.sin(angle) for angle in angles) / len(angles)
    concentration = math.hypot(mean_cos, mean_sin)

    if concentration < 1e-12:
        return CircularStats(float("nan"), concentration)

    angle = math.atan2(mean_sin, mean_cos)
    if angle < 0:
        angle += 2.0 * math.pi
    return CircularStats(angle * period_count / (2.0 * math.pi), concentration)


def classify_initial_mean(mean: float, period: float) -> str:
    if math.isnan(mean):
        return "undefined_circular_mean"
    epsilon = period * 1e-9
    if any(
        math.isclose(mean, boundary, rel_tol=0.0, abs_tol=epsilon)
        for boundary in (0.0, period / 4, 3 * period / 4, period)
    ):
        return DecisionKind.UNRESOLVED_INITIAL_BOUNDARY.value
    if 0 < mean < period / 4 or 3 * period / 4 < mean < period:
        return DecisionKind.SET_FALLING.value
    if period / 4 < mean < 3 * period / 4:
        return DecisionKind.SET_RISING.value
    return DecisionKind.UNRESOLVED_INITIAL_BOUNDARY.value


def classify_periodic_mean(mean: float, period: float, current_edge: str) -> str:
    if math.isnan(mean):
        return f"keep_{current_edge}"
    epsilon = period * 1e-9
    if any(
        math.isclose(mean, boundary, rel_tol=0.0, abs_tol=epsilon)
        for boundary in (
            0.0,
            period / 12,
            4 * period / 12,
            5 * period / 12,
            7 * period / 12,
            8 * period / 12,
            11 * period / 12,
            period,
        )
    ):
        return f"keep_{current_edge}"
    if 0 < mean < period / 12 or 11 * period / 12 < mean < period:
        return DecisionKind.SET_FALLING.value
    if 5 * period / 12 < mean < 7 * period / 12:
        return DecisionKind.SET_RISING.value
    return f"keep_{current_edge}"


def evaluate_scenario(scenario: dict[str, Any], period: int) -> dict[str, Any]:
    stage = scenario["stage"]
    if stage == "periodic_sequence":
        return evaluate_periodic_sequence(scenario, period)

    samples = scenario["samples"]
    circular = circular_stats(samples, period)
    legacy_mean = float(sum(samples) / len(samples))

    if stage == "initial":
        legacy = decide_initial(samples, period)
        legacy_decision = legacy.kind.value
        circular_decision = classify_initial_mean(circular.mean_phase_count, period)
    elif stage == "periodic":
        current_edge = SampleEdge(scenario["current_edge"])
        legacy = decide_periodic(samples, period, current_edge)
        legacy_decision = (
            f"keep_{current_edge.value}"
            if legacy.kind == DecisionKind.KEEP
            else legacy.kind.value
        )
        circular_decision = classify_periodic_mean(
            circular.mean_phase_count, period, current_edge.value
        )
    else:
        raise ValueError(f"unsupported stage: {stage}")

    return {
        "name": scenario["name"],
        "description": scenario["description"],
        "legacy_mean": legacy_mean,
        "circular_mean": circular.mean_phase_count,
        "circular_defined": not math.isnan(circular.mean_phase_count),
        "concentration": circular.concentration,
        "legacy_margin": decision_margin(
            legacy_mean,
            stage,
            period,
            SampleEdge(scenario["current_edge"]) if stage == "periodic" else None,
        ),
        "circular_margin": decision_margin(
            circular.mean_phase_count,
            stage,
            period,
            SampleEdge(scenario["current_edge"]) if stage == "periodic" else None,
        ),
        "legacy_decision": legacy_decision,
        "circular_decision": circular_decision,
        "different": legacy_decision != circular_decision,
    }


def evaluate_periodic_sequence(
    scenario: dict[str, Any], period: int
) -> dict[str, Any]:
    legacy_edge = SampleEdge(scenario["current_edge"])
    circular_edge = legacy_edge
    legacy_steps: list[str] = []
    circular_steps: list[str] = []
    concentrations: list[float] = []
    legacy_margins: list[float] = []
    circular_margins: list[float] = []
    legacy_switches = 0
    circular_switches = 0
    all_circular_means_defined = True

    for batch in scenario["batches"]:
        legacy_edge_before_decision = legacy_edge
        legacy_batch_mean = float(sum(batch) / len(batch))
        legacy = decide_periodic(batch, period, legacy_edge)
        next_legacy_edge = legacy.edge
        assert next_legacy_edge is not None
        if next_legacy_edge != legacy_edge:
            legacy_switches += 1
        legacy_edge = next_legacy_edge
        legacy_steps.append(legacy_edge.value)
        legacy_margins.append(
            decision_margin(
                legacy_batch_mean,
                "periodic",
                period,
                legacy_edge_before_decision,
            )
        )

        circular = circular_stats(batch, period)
        all_circular_means_defined &= not math.isnan(circular.mean_phase_count)
        circular_edge_before_decision = circular_edge
        circular_action = classify_periodic_mean(
            circular.mean_phase_count, period, circular_edge.value
        )
        if circular_action == DecisionKind.SET_RISING.value:
            next_circular_edge = SampleEdge.RISING
        elif circular_action == DecisionKind.SET_FALLING.value:
            next_circular_edge = SampleEdge.FALLING
        else:
            next_circular_edge = circular_edge
        if next_circular_edge != circular_edge:
            circular_switches += 1
        circular_edge = next_circular_edge
        circular_steps.append(circular_edge.value)
        concentrations.append(circular.concentration)
        circular_margins.append(
            decision_margin(
                circular.mean_phase_count,
                "periodic",
                period,
                circular_edge_before_decision,
            )
        )

    return {
        "name": scenario["name"],
        "description": scenario["description"],
        "legacy_mean": float("nan"),
        "circular_mean": float("nan"),
        "circular_defined": all_circular_means_defined,
        "concentration": min(concentrations),
        "legacy_margin": min(legacy_margins),
        "circular_margin": min(circular_margins),
        "legacy_decision": " -> ".join(legacy_steps),
        "circular_decision": " -> ".join(circular_steps),
        "different": legacy_steps != circular_steps,
        "legacy_switches": legacy_switches,
        "circular_switches": circular_switches,
    }


def render_markdown(results: list[dict[str, Any]], period: int) -> str:
    lines = [
        "# CPU 判决算法场景对照结果",
        "",
        f"接收时钟周期：`T={period}` 个相位计数单位。圆周集中度越接近 1，样本在圆周上越集中。",
        "",
        "| 场景 | 普通平均 | 圆周平均 | 集中度 | 普通裕量 | 圆周裕量 | 普通裕量/T | 圆周裕量/T | 原算法 | 圆周候选 | 是否不同 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for result in results:
        legacy_mean = result["legacy_mean"]
        circular_mean = result["circular_mean"]
        legacy_text = "sequence" if math.isnan(legacy_mean) else f"{legacy_mean:.2f}"
        circular_text = "undefined" if math.isnan(circular_mean) else f"{circular_mean:.2f}"
        legacy_margin = result["legacy_margin"]
        circular_margin = result["circular_margin"]
        legacy_margin_text = (
            "undefined" if math.isnan(legacy_margin) else f"{legacy_margin:.2f}"
        )
        circular_margin_text = (
            "undefined" if math.isnan(circular_margin) else f"{circular_margin:.2f}"
        )
        legacy_normalized_text = (
            "undefined"
            if math.isnan(legacy_margin)
            else f"{legacy_margin / period:.3f}"
        )
        circular_normalized_text = (
            "undefined"
            if math.isnan(circular_margin)
            else f"{circular_margin / period:.3f}"
        )
        lines.append(
            "| {name} | {legacy} | {circular} | {concentration:.3f} | "
            "{legacy_margin} | {circular_margin} | {legacy_normalized} | "
            "{circular_normalized} | "
            "{legacy_decision} | {circular_decision} | {different} |".format(
                name=result["name"],
                legacy=legacy_text,
                circular=circular_text,
                concentration=result["concentration"],
                legacy_margin=legacy_margin_text,
                circular_margin=circular_margin_text,
                legacy_normalized=legacy_normalized_text,
                circular_normalized=circular_normalized_text,
                legacy_decision=result["legacy_decision"],
                circular_decision=result["circular_decision"],
                different="是" if result["different"] else "否",
            )
        )

    lines.extend(["", "## 场景说明", ""])
    for result in results:
        lines.append(f"- `{result['name']}`：{result['description']}")
        if "legacy_switches" in result:
            lines.append(
                f"  - 实际切换次数：原算法 {result['legacy_switches']} 次，"
                f"圆周候选 {result['circular_switches']} 次。"
            )
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "普通裕量由普通平均计算，圆周裕量由圆周平均计算；裕量只表示对应均值到有效决策边界的距离，不能证明该均值可信。",
            "本报告只比较统计量及由同一阈值表产生的裁定。圆周算法目前是候选对照，",
            "不是已确认替代方案；集中度阈值、异常值定义和失败恢复仍未规定。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path(__file__).with_name("algorithm_scenarios.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("algorithm_comparison_results.md"),
    )
    args = parser.parse_args()

    data = json.loads(args.scenarios.read_text(encoding="utf-8"))
    period = int(data["period_count"])
    results = [evaluate_scenario(item, period) for item in data["scenarios"]]
    report = render_markdown(results, period)
    args.output.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
