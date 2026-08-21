import unittest

from simulate_dynamic_tracking import simulate_track


class DynamicTrackingTests(unittest.TestCase):
    def simulate(self, centers, current="falling"):
        return simulate_track(
            {
                "name": "track",
                "description": "test",
                "current_edge": current,
                "batch_centers": centers,
            },
            120,
            3,
            0.9,
            0.025,
        )

    def test_slow_crossing_adds_delay(self):
        result = self.simulate([44, 47, 49, 51, 52, 54, 56])
        self.assertEqual(result.legacy_first_switch, 3)
        self.assertEqual(result.guarded_first_switch, 5)
        self.assertEqual(result.guarded_delay_batches, 2)
        self.assertEqual(result.guarded_delay_seconds, 6)

    def test_fast_jump_has_no_extra_delay(self):
        result = self.simulate([40, 60, 60, 60])
        self.assertEqual(result.legacy_first_switch, 1)
        self.assertEqual(result.guarded_first_switch, 1)
        self.assertEqual(result.guarded_delay_seconds, 0)

    def test_transient_crossing_is_ignored_by_guard(self):
        result = self.simulate([45, 48, 49, 51, 49, 47, 45])
        self.assertEqual(result.legacy_first_switch, 3)
        self.assertIsNone(result.guarded_first_switch)

    def test_slow_cross_to_falling_is_delayed(self):
        result = self.simulate([16, 13, 11, 9, 8, 6, 4], current="rising")
        self.assertEqual(result.legacy_first_switch, 3)
        self.assertEqual(result.guarded_first_switch, 5)


if __name__ == "__main__":
    unittest.main()
