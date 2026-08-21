import unittest

from cpu_sampling_decision import SampleEdge
from simulate_guarded_controller import simulate_initial, simulate_periodic_batch, simulate_scenario


class GuardedControllerTests(unittest.TestCase):
    def test_stable_wraparound_is_accepted_and_sets_falling(self):
        decision = simulate_initial(
            [1, 2, 1, 118, 119, 1, 2, 118, 119, 1],
            120, 0.9, 0.025
        )
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.final_edge, SampleEdge.FALLING)

    def test_outlier_case_is_rejected_for_low_concentration(self):
        decision = simulate_initial(
            [27, 27, 28, 27, 28, 27, 27, 28, 27, 90],
            120, 0.9, 0.025
        )
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.action, "recalibrate")
        self.assertEqual(decision.reason, "low_concentration")

    def test_periodic_rejection_keeps_current_edge(self):
        decision = simulate_periodic_batch(
            [51, 52, 51], 120, SampleEdge.FALLING, 0.9, 0.025
        )
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.final_edge, SampleEdge.FALLING)
        self.assertEqual(decision.reason, "low_decision_margin")

    def test_explicit_keep_can_pass_gate_without_switching(self):
        decision = simulate_periodic_batch(
            [20, 21, 19], 120, SampleEdge.FALLING, 0.9, 0.025
        )
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.final_edge, SampleEdge.FALLING)
        self.assertEqual(decision.action, "keep_falling")

    def test_threshold_sequence_has_no_guarded_switch(self):
        result = simulate_scenario(
            {
                "name": "sequence",
                "stage": "periodic_sequence",
                "current_edge": "falling",
                "batches": [
                    [49, 50, 49], [51, 52, 51], [49, 50, 49],
                    [51, 50, 51], [49, 49, 50]
                ],
            },
            120, 0.9, 0.025
        )
        self.assertTrue(all(not item.accepted for item in result["decisions"]))
        self.assertTrue(
            all(item.final_edge == SampleEdge.FALLING for item in result["decisions"])
        )


if __name__ == "__main__":
    unittest.main()
