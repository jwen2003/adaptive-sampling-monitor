"""Compare legacy and confidence-gated decisions over dynamic phase tracks."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cpu_sampling_decision import SampleEdge, decide_periodic
from simulate_guarded_controller import (
    DEFAULT_MIN_CONCENTRATION,
    DEFAULT_MIN_NORMALIZED_MARGIN,
    simulate_periodic_batch,
)


@dataclass(frozen=True)
class TrackingResult:
    name: str
    description: str
    centers: tuple[int, ...]
    legacy_edges: tuple[SampleEdge, ...]
    guarded_edges: tuple[SampleEdge, ...]
    legacy_first_switch: int | None
    guarded_first_switch: int | None
    guarded_delay_batches: int | None
    guarded_delay_seconds: int | None


def make_batch(center: int) -> list[int]:
    if center <= 0:
        return [center, center, center + 1]
    return [center - 1, center, center + 1]


def _first_switch(edges: list[SampleEdge], initial_edge: SampleEdge) -> int | None:
    return next(
        (index for index, edge in enumerate(edges) if edge != initial_edge),
        None,
    )


def simulate_track(
    scenario: dict[str, Any],
    period: float,
    batch_interval_seconds: int,
    min_concentration: float,
    min_normalized_margin: float,
) -> TrackingResult:
    initial_edge = SampleEdge(scenario["current_edge"])
    legacy_edge = initial_edge
    guarded_edge = initial_edge
    legacy_edges: list[SampleEdge] = []
    guarded_edges: list[SampleEdge] = []

    for center in scenario["batch_centers"]:
        batch = make_batch(center)
        legacy = decide_periodic(batch, period, legacy_edge)
        assert legacy.edge is not None
        legacy_edge = legacy.edge
        legacy_edges.append(legacy_edge)

        guarded = simulate_periodic_batch(
            batch,
            period,
            guarded_edge,
            min_concentration,
            min_normalized_margin,
        )
        assert guarded.final_edge is not None
        guarded_edge = guarded.final_edge
        guarded_edges.append(guarded_edge)

    legacy_first = _first_switch(legacy_edges, initial_edge)
    guarded_first = _first_switch(guarded_edges, initial_edge)
    if legacy_first is not None and guarded_first is not None:
        delay_batches = guarded_first - legacy_first
        delay_seconds = delay_batches * batch_interval_seconds
    else:
        delay_batches = None
        delay_seconds = None

    return TrackingResult(
        scenario["name"],
        scenario["description"],
        tuple(scenario["batch_centers"]),
        tuple(legacy_edges),
        tuple(guarded_edges),
        legacy_first,
        guarded_first,
        delay_batches,
        delay_seconds,
    )


def _edge_sequence(edges: tuple[SampleEdge, ...]) -> str:
    return " -> ".join(edge.value for edge in edges)


def _switch_text(index: int | None) -> str:
    return "未切换" if index is None else f"第 {index + 1} 批"


def render_markdown(
    results: list[TrackingResult],
    period: float,
    batch_interval_seconds: int,
    min_concentration: float,
    min_normalized_margin: float,
) -> str:
    lines = [
        "# CPU 动态相位跟踪结果",
        "",
        f"`T={period:g}`，每批约 `{batch_interval_seconds}` 秒；探索门限为集中度 ≥ `{min_concentration:g}`、圆周裕量/T ≥ `{min_normalized_margin:g}`。",
        "",
        "| 场景 | 相位中心序列 | 原算法首次切换 | 带门限首次切换 | 延迟 |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        if result.guarded_delay_batches is not None:
            delay = (
                f"{result.guarded_delay_batches} 批 / "
                f"约 {result.guarded_delay_seconds} 秒"
            )
        elif result.legacy_first_switch is not None:
            delay = "带门限版本未切换"
        else:
            delay = "两者均未切换"
        centers = ", ".join(map(str, result.centers))
        lines.append(
            f"| {result.name} | `{centers}` | {_switch_text(result.legacy_first_switch)} | "
            f"{_switch_text(result.guarded_first_switch)} | {delay} |"
        )

    lines.extend(["", "## 逐批采样沿", ""])
    for result in results:
        lines.extend(
            [
                f"### {result.name}",
                "",
                result.description,
                "",
                f"- 原算法：`{_edge_sequence(result.legacy_edges)}`",
                f"- 带门限：`{_edge_sequence(result.guarded_edges)}`",
                "",
            ]
        )

    lines.extend(
        [
            "## 解释限制",
            "",
            "轨迹使用每批三个相邻整数样本构造，未加入真实抖动概率、测量丢失或频率变化。切换延迟按当前“每秒一个结果、三个结果一批”的重建换算。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios", type=Path,
        default=Path(__file__).with_name("dynamic_phase_scenarios.json")
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).with_name("dynamic_tracking_results.md")
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
    interval = int(data["batch_interval_seconds"])
    results = [
        simulate_track(
            scenario,
            period,
            interval,
            args.min_concentration,
            args.min_normalized_margin,
        )
        for scenario in data["scenarios"]
    ]
    report = render_markdown(
        results,
        period,
        interval,
        args.min_concentration,
        args.min_normalized_margin,
    )
    args.output.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
