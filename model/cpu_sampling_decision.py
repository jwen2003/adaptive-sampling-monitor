"""V.35 CPU-side sampling-edge decision reference model.

This model intentionally reproduces the reconstructed legacy algorithm:

* initial calibration: arithmetic mean of 10 valid phase measurements;
* periodic calibration: one result per sampling instant, one decision for each
  non-overlapping batch of 3 valid measurements;
* all comparisons are performed exactly in counter units, without floating
  point rounding;
* the two gaps and exact thresholds in the periodic table keep the current
  edge;
* exact thresholds in the initial table remain unresolved, because there is no
  existing edge whose value can safely be retained.

It is a software/reference artifact.  It is not part of the CPLD RTL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Iterable, Optional


class SampleEdge(str, Enum):
    RISING = "rising"
    FALLING = "falling"


class DecisionKind(str, Enum):
    SET_RISING = "set_rising"
    SET_FALLING = "set_falling"
    KEEP = "keep"
    INSUFFICIENT_SAMPLES = "insufficient_samples"
    UNRESOLVED_INITIAL_BOUNDARY = "unresolved_initial_boundary"


@dataclass(frozen=True)
class Decision:
    kind: DecisionKind
    edge: Optional[SampleEdge]
    sample_count: int
    mean_phase_count: Optional[Fraction]


def _validate_period(period_count: Fraction | int) -> Fraction:
    period = Fraction(period_count)
    if period <= 0:
        raise ValueError("period_count must be positive")
    return period


def _mean(samples: Iterable[int]) -> tuple[list[int], Fraction]:
    values = list(samples)
    if not values:
        raise ValueError("at least one phase sample is required")
    if any((not isinstance(value, int)) or value < 0 for value in values):
        raise ValueError("phase samples must be non-negative integers")
    return values, Fraction(sum(values), len(values))


def decide_initial(samples: Iterable[int], period_count: Fraction | int) -> Decision:
    """Apply the reconstructed 10-sample power-up/frequency-change table."""
    values, mean = _mean(samples)
    if len(values) != 10:
        return Decision(DecisionKind.INSUFFICIENT_SAMPLES, None, len(values), mean)

    period = _validate_period(period_count)
    if 0 < mean < period / 4 or 3 * period / 4 < mean < period:
        return Decision(DecisionKind.SET_FALLING, SampleEdge.FALLING, 10, mean)
    if period / 4 < mean < 3 * period / 4:
        return Decision(DecisionKind.SET_RISING, SampleEdge.RISING, 10, mean)

    return Decision(
        DecisionKind.UNRESOLVED_INITIAL_BOUNDARY, None, 10, mean
    )


def decide_periodic(
    samples: Iterable[int],
    period_count: Fraction | int,
    current_edge: SampleEdge,
) -> Decision:
    """Apply the reconstructed periodic table to one 3-sample batch."""
    values, mean = _mean(samples)
    if len(values) != 3:
        return Decision(
            DecisionKind.INSUFFICIENT_SAMPLES, current_edge, len(values), mean
        )

    period = _validate_period(period_count)
    if 0 < mean < period / 12 or 11 * period / 12 < mean < period:
        return Decision(DecisionKind.SET_FALLING, SampleEdge.FALLING, 3, mean)
    if 5 * period / 12 < mean < 7 * period / 12:
        return Decision(DecisionKind.SET_RISING, SampleEdge.RISING, 3, mean)

    # Includes the two explicit retain regions, the two undocumented gaps,
    # exact thresholds, zero, and values outside one nominal period.
    return Decision(DecisionKind.KEEP, current_edge, 3, mean)


@dataclass
class LegacyCpuController:
    """Minimal stateful scheduler for valid CPLD results.

    Wall-clock timing remains outside this class: the caller supplies one valid
    periodic result at each 1 s sampling instant.  Invalid/missing measurements
    are not added to a batch.
    """

    period_count: Fraction | int
    current_edge: Optional[SampleEdge] = None
    calibrated: bool = False
    _samples: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.period_count = _validate_period(self.period_count)

    @property
    def samples_pending(self) -> int:
        return len(self._samples)

    def frequency_changed(self, new_period_count: Fraction | int) -> None:
        self.period_count = _validate_period(new_period_count)
        self.current_edge = None
        self.calibrated = False
        self._samples.clear()

    def add_measurement(self, phase_count: int, *, valid: bool = True) -> Decision:
        if not valid:
            return Decision(
                DecisionKind.INSUFFICIENT_SAMPLES,
                self.current_edge,
                len(self._samples),
                None,
            )

        if (not isinstance(phase_count, int)) or phase_count < 0:
            raise ValueError("phase_count must be a non-negative integer")
        self._samples.append(phase_count)

        target = 3 if self.calibrated else 10
        if len(self._samples) < target:
            return Decision(
                DecisionKind.INSUFFICIENT_SAMPLES,
                self.current_edge,
                len(self._samples),
                Fraction(sum(self._samples), len(self._samples)),
            )

        batch = self._samples[:target]
        del self._samples[:target]

        if not self.calibrated:
            decision = decide_initial(batch, self.period_count)
            if decision.edge is not None:
                self.current_edge = decision.edge
                self.calibrated = True
            return decision

        assert self.current_edge is not None
        decision = decide_periodic(batch, self.period_count, self.current_edge)
        self.current_edge = decision.edge
        return decision
