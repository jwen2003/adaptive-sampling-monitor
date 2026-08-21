import unittest

from scan_decision_thresholds import candidate_is_accepted, sweep_thresholds


def make_result(name, concentration, margin, *, defined=True):
    return {
        "name": name,
        "concentration": concentration,
        "circular_margin": margin,
        "circular_defined": defined,
    }


class ThresholdScanTests(unittest.TestCase):
    def test_undefined_mean_is_always_rejected(self):
        result = make_result("undefined", 1.0, 30.0, defined=False)
        self.assertFalse(candidate_is_accepted(result, 120, 0.0, 0.0))

    def test_both_gates_must_pass(self):
        result = make_result("candidate", 0.95, 12.0)
        self.assertTrue(candidate_is_accepted(result, 120, 0.9, 0.1))
        self.assertFalse(candidate_is_accepted(result, 120, 0.96, 0.1))
        self.assertFalse(candidate_is_accepted(result, 120, 0.9, 0.11))

    def test_equal_to_threshold_is_accepted(self):
        result = make_result("boundary", 0.9, 6.0)
        self.assertTrue(candidate_is_accepted(result, 120, 0.9, 0.05))

    def test_stricter_gate_cannot_accept_more_scenarios(self):
        results = [
            make_result("strong", 0.99, 24.0),
            make_result("weak", 0.8, 3.0),
            make_result("undefined", 1.0, 30.0, defined=False),
        ]
        sweep = sweep_thresholds(
            results,
            120,
            concentration_thresholds=(0.8, 0.9),
            margin_thresholds=(0.01, 0.05),
        )
        counts = {
            (gate.min_concentration, gate.min_normalized_margin): len(gate.accepted)
            for gate in sweep
        }
        self.assertGreaterEqual(counts[(0.8, 0.01)], counts[(0.9, 0.01)])
        self.assertGreaterEqual(counts[(0.8, 0.01)], counts[(0.8, 0.05)])


if __name__ == "__main__":
    unittest.main()
