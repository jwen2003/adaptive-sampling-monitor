import math
import unittest

from compare_decision_algorithms import (
    circular_stats,
    classify_initial_mean,
    decision_margin,
    evaluate_scenario,
)
from cpu_sampling_decision import SampleEdge


class CircularStatisticsTests(unittest.TestCase):
    def test_wraparound_cluster_stays_near_zero(self):
        stats = circular_stats([1, 2, 118, 119], 120)
        distance_to_zero = min(stats.mean_phase_count, 120 - stats.mean_phase_count)
        self.assertLess(distance_to_zero, 1)
        self.assertGreater(stats.concentration, 0.99)

    def test_opposite_clusters_have_low_concentration(self):
        stats = circular_stats([0, 60], 120)
        self.assertTrue(math.isnan(stats.mean_phase_count))
        self.assertLess(stats.concentration, 1e-12)

    def test_wraparound_changes_decision(self):
        result = evaluate_scenario(
            {
                "name": "wrap",
                "description": "test",
                "stage": "initial",
                "samples": [1, 2, 1, 118, 119, 1, 2, 118, 119, 1],
            },
            120,
        )
        self.assertTrue(result["different"])
        self.assertEqual(result["legacy_decision"], "set_rising")
        self.assertEqual(result["circular_decision"], "set_falling")

    def test_float_noise_does_not_reclassify_exact_quarter_boundary(self):
        self.assertEqual(
            classify_initial_mean(30.0 - 1e-12, 120),
            "unresolved_initial_boundary",
        )

    def test_stability_and_decision_margin_are_independent(self):
        stats = circular_stats([30, 30, 31, 30, 31, 30, 31, 30, 30, 31], 120)
        self.assertGreater(stats.concentration, 0.99)
        self.assertLess(decision_margin(stats.mean_phase_count, "initial", 120), 1)

    def test_wrap_is_not_an_initial_decision_boundary(self):
        self.assertAlmostEqual(decision_margin(0.2, "initial", 120), 29.8)
        self.assertAlmostEqual(decision_margin(119.8, "initial", 120), 29.8)

    def test_periodic_margin_depends_on_current_edge(self):
        self.assertAlmostEqual(
            decision_margin(49, "periodic", 120, SampleEdge.FALLING), 1
        )
        self.assertAlmostEqual(
            decision_margin(49, "periodic", 120, SampleEdge.RISING), 39
        )

    def test_wraparound_reports_separate_legacy_and_circular_margins(self):
        result = evaluate_scenario(
            {
                "name": "wrap",
                "description": "test",
                "stage": "initial",
                "samples": [1, 2, 1, 118, 119, 1, 2, 118, 119, 1],
            },
            120,
        )
        self.assertAlmostEqual(result["legacy_margin"], 18.2)
        self.assertAlmostEqual(result["circular_margin"], 29.8, delta=0.001)

    def test_periodic_keep_region_prevents_repeated_switching(self):
        result = evaluate_scenario(
            {
                "name": "sequence",
                "description": "test",
                "stage": "periodic_sequence",
                "current_edge": "falling",
                "batches": [
                    [49, 50, 49],
                    [51, 52, 51],
                    [49, 50, 49],
                    [51, 50, 51],
                ],
            },
            120,
        )
        self.assertEqual(result["legacy_switches"], 1)
        self.assertEqual(result["circular_switches"], 1)


if __name__ == "__main__":
    unittest.main()
