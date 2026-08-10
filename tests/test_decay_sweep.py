import unittest

from temvera.decay import run_decay_sweep


class DecaySweepTest(unittest.TestCase):
    def test_cartesian_sweep_is_deterministic_and_complete(self) -> None:
        arguments = {
            "ages_days": (0, 30, 180),
            "half_lives_days": (30.0, 90.0),
            "thresholds": (0.25, 0.5),
        }
        rows = run_decay_sweep(**arguments)
        self.assertEqual(rows, run_decay_sweep(**arguments))
        self.assertEqual(len(rows), 3 * 2 * 2 * 2 * 2)
        self.assertEqual({row.method for row in rows}, {"rank_only", "state_level"})
        self.assertEqual(
            {row.scenario for row in rows}, {"changed_fact", "stable_old_fact"}
        )

    def test_sweep_preserves_decay_tradeoff(self) -> None:
        rows = run_decay_sweep(
            ages_days=(180,),
            half_lives_days=(30.0,),
            thresholds=(0.25,),
        )
        stable_state = next(
            row
            for row in rows
            if row.method == "state_level" and row.scenario == "stable_old_fact"
        )
        changed_rank = next(
            row
            for row in rows
            if row.method == "rank_only" and row.scenario == "changed_fact"
        )
        self.assertTrue(stable_state.abstained)
        self.assertTrue(changed_rank.relevant_selected)


if __name__ == "__main__":
    unittest.main()
