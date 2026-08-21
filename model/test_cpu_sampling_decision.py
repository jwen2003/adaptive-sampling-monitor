import unittest
from fractions import Fraction

from cpu_sampling_decision import (
    DecisionKind,
    LegacyCpuController,
    SampleEdge,
    decide_initial,
    decide_periodic,
)


class InitialDecisionTests(unittest.TestCase):
    def test_requires_exactly_ten_samples(self):
        result = decide_initial([25] * 9, 120)
        self.assertEqual(result.kind, DecisionKind.INSUFFICIENT_SAMPLES)

    def test_initial_regions(self):
        self.assertEqual(decide_initial([10] * 10, 120).edge, SampleEdge.FALLING)
        self.assertEqual(decide_initial([60] * 10, 120).edge, SampleEdge.RISING)
        self.assertEqual(decide_initial([110] * 10, 120).edge, SampleEdge.FALLING)

    def test_initial_exact_threshold_is_explicitly_unresolved(self):
        result = decide_initial([30] * 10, 120)
        self.assertEqual(result.kind, DecisionKind.UNRESOLVED_INITIAL_BOUNDARY)
        self.assertIsNone(result.edge)

    def test_exact_fractional_mean_without_float_rounding(self):
        result = decide_initial([29] * 9 + [30], 120)
        self.assertEqual(result.mean_phase_count, Fraction(291, 10))
        self.assertEqual(result.edge, SampleEdge.FALLING)


class PeriodicDecisionTests(unittest.TestCase):
    def test_periodic_switch_regions(self):
        self.assertEqual(
            decide_periodic([5] * 3, 120, SampleEdge.RISING).edge,
            SampleEdge.FALLING,
        )
        self.assertEqual(
            decide_periodic([60] * 3, 120, SampleEdge.FALLING).edge,
            SampleEdge.RISING,
        )
        self.assertEqual(
            decide_periodic([115] * 3, 120, SampleEdge.RISING).edge,
            SampleEdge.FALLING,
        )

    def test_explicit_retain_regions(self):
        for mean in (20, 100):
            result = decide_periodic([mean] * 3, 120, SampleEdge.RISING)
            self.assertEqual(result.kind, DecisionKind.KEEP)
            self.assertEqual(result.edge, SampleEdge.RISING)

    def test_undocumented_gaps_and_equalities_keep(self):
        for mean in (10, 40, 45, 50, 70, 75, 80, 110):
            result = decide_periodic([mean] * 3, 120, SampleEdge.FALLING)
            self.assertEqual(result.kind, DecisionKind.KEEP)
            self.assertEqual(result.edge, SampleEdge.FALLING)


class ControllerTests(unittest.TestCase):
    def test_ten_then_non_overlapping_groups_of_three(self):
        controller = LegacyCpuController(120)
        for _ in range(9):
            result = controller.add_measurement(60)
            self.assertEqual(result.kind, DecisionKind.INSUFFICIENT_SAMPLES)
        self.assertEqual(controller.add_measurement(60).edge, SampleEdge.RISING)

        self.assertEqual(controller.add_measurement(5).kind, DecisionKind.INSUFFICIENT_SAMPLES)
        self.assertEqual(controller.add_measurement(5).kind, DecisionKind.INSUFFICIENT_SAMPLES)
        self.assertEqual(controller.add_measurement(5).edge, SampleEdge.FALLING)
        self.assertEqual(controller.samples_pending, 0)

        self.assertEqual(controller.add_measurement(60).kind, DecisionKind.INSUFFICIENT_SAMPLES)
        self.assertEqual(controller.add_measurement(60).kind, DecisionKind.INSUFFICIENT_SAMPLES)
        self.assertEqual(controller.current_edge, SampleEdge.FALLING)

    def test_invalid_result_does_not_enter_batch(self):
        controller = LegacyCpuController(120)
        controller.add_measurement(60, valid=False)
        self.assertEqual(controller.samples_pending, 0)

    def test_frequency_change_discards_history_and_restarts_initial(self):
        controller = LegacyCpuController(120)
        for _ in range(10):
            controller.add_measurement(60)
        controller.add_measurement(5)
        controller.frequency_changed(240)
        self.assertFalse(controller.calibrated)
        self.assertIsNone(controller.current_edge)
        self.assertEqual(controller.samples_pending, 0)

    def test_wraparound_exposes_legacy_arithmetic_mean_problem(self):
        # Samples cluster near 0/T physically, but their arithmetic mean lands
        # near the middle and therefore selects the rising edge.
        result = decide_initial([1, 2, 1, 118, 119, 1, 2, 118, 119, 1], 120)
        self.assertEqual(result.mean_phase_count, Fraction(482, 10))
        self.assertEqual(result.edge, SampleEdge.RISING)


if __name__ == "__main__":
    unittest.main()
