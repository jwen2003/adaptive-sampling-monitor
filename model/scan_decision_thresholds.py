"""Sweep candidate confidence gates over the deterministic V.35 scenarios."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from compare_decision_algorithms import evaluate_scenario


DEFAULT_CONCENTRATION_THRESHOLDS = (0.0, 0.5, 0.8, 0.9, 0.95, 0.99)
DEFAULT_MARGIN_THRESHOLDS = (0.0, 0.005, 0.01, 0.025, 0.05, 0.10)


@dataclass(frozen=True)
class GateResult:
    min_concentration: float
    min_normalized_margin: float
    accepted: tuple[str, ...]
    rejected: tuple[str, ...]


def candidate_is_accepted(
    result: dict[str, Any],
    period: float,
    min_concentration: float,
    min_normalized_margin: float,
) -> bool:
    """Return whether the circular candidate passes both confidence gates."""
    if not 0.0 <= min_concentration <= 1.0:
        raise ValueError("min_concentration must be between 0 and 1")
    if not 0.0 <= min_normalized_margin <= 0.5:
        raise ValueError("min_normalized_margin must be between 0 and 0.5")
    if not result["circular_defined"]:
        return False
    normalized_margin = result["circular_margin"] / period
    return (
        result["concentration"] >= min_concentration
        and normalized_margin >= min_normalized_margin
    )


def sweep_thresholds(
    results: list[dict[str, Any]],
    period: float,
    concentration_thresholds: tuple[float, ...] = DEFAULT_CONCENTRATION_THRESHOLDS,
    margin_thresholds: tuple[float, ...] = DEFAULT_MARGIN_THRESHOLDS,
) -> list[GateResult]:
    sweep: list[GateResult] = []
    for concentration in concentration_thresholds:
        for margin in margin_thresholds:
            accepted = tuple(
                result["name"]
                for result in results
                if candidate_is_accepted(result, period, concentration, margin)
            )
            rejected = tuple(
                result["name"] for result in results if result["name"] not in accepted
            )
            sweep.append(GateResult(concentration, margin, accepted, rejected))
    return sweep


def _find_gate(
    sweep: list[GateResult], concentration: float, margin: float
) -> GateResult:
    return next(
        gate
        for gate in sweep
        if gate.min_concentration == concentration
        and gate.min_normalized_margin == margin
    )


def render_markdown(
    results: list[dict[str, Any]],
    sweep: list[GateResult],
    period: float,
    concentration_thresholds: tuple[float, ...],
    margin_thresholds: tuple[float, ...],
) -> str:
    lines = [
        "# CPU 候选算法门限扫描结果",
        "",
        f"场景周期为 `T={period:g}` 个相位计数单位。接受条件为：圆周均值有效、集中度不低于门限、圆周裕量/T 不低于门限。",
        "",
        "表中数字为通过门限的场景数，场景总数为 " + str(len(results)) + "。",
        "",
        "| 最小集中度 \\ 最小圆周裕量/T | "
        + " | ".join(f"{margin:g}" for margin in margin_thresholds)
        + " |",
        "|---:|" + "---:|" * len(margin_thresholds),
    ]
    for concentration in concentration_thresholds:
        counts = [
            len(_find_gate(sweep, concentration, margin).accepted)
            for margin in margin_thresholds
        ]
        lines.append(
            f"| {concentration:g} | " + " | ".join(map(str, counts)) + " |"
        )

    profiles = (
        ("仅排除无定义均值", 0.0, 0.0),
        ("宽松观察", 0.8, 0.01),
        ("中等观察", 0.9, 0.025),
        ("严格观察", 0.99, 0.05),
    )
    lines.extend(["", "## 代表性门限组合", ""])
    for label, concentration, margin in profiles:
        gate = _find_gate(sweep, concentration, margin)
        lines.extend(
            [
                f"### {label}",
                "",
                f"门限：集中度 ≥ `{concentration:g}`，圆周裕量/T ≥ `{margin:g}`。",
                "",
                "接受：" + (", ".join(f"`{name}`" for name in gate.accepted) or "无"),
                "",
                "拒绝：" + (", ".join(f"`{name}`" for name in gate.rejected) or "无"),
                "",
            ]
        )

    lines.extend(
        [
            "## 解释限制",
            "",
            "这些门限名称只是方便比较，不代表产品推荐值。场景是定向构造样本，不是现场概率分布；扫描结果只能显示参数敏感性，不能据此估计误码率或误拒绝率。",
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
        default=Path(__file__).with_name("threshold_scan_results.md"),
    )
    args = parser.parse_args()

    data = json.loads(args.scenarios.read_text(encoding="utf-8"))
    period = float(data["period_count"])
    results = [evaluate_scenario(item, int(period)) for item in data["scenarios"]]
    sweep = sweep_thresholds(results, period)
    report = render_markdown(
        results,
        sweep,
        period,
        DEFAULT_CONCENTRATION_THRESHOLDS,
        DEFAULT_MARGIN_THRESHOLDS,
    )
    args.output.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
