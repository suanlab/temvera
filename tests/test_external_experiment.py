import unittest

from temvera.external_harness import OracleMemorySystem
from temvera.external_experiment import projected_ingests, score_on_events
from temvera.generator import generate_histories
from temvera.nl_workload import naturalize_events


class ExternalExperimentTest(unittest.TestCase):
    def _events(self):
        return naturalize_events(
            generate_histories(
                seed=7,
                entities=3,
                revisions=2,
                reconfirm_probability=0.5,
                expire_probability=0.3,
                purge_probability=0.3,
            )
        )

    def test_oracle_is_exact_under_both_replay_modes(self) -> None:
        events = self._events()
        for mode in ("transaction_checkpoint", "single_pass"):
            result = score_on_events(
                OracleMemorySystem(events), events, replay=mode
            )
            self.assertEqual(result["exact_state_accuracy"], 1.0, mode)
            self.assertEqual(result["evidence_recall"], 1.0, mode)
            self.assertEqual(result["stale_use_rate"], 0.0, mode)

    def test_checkpoint_replay_ingests_each_turn_once(self) -> None:
        # Forward checkpoints must not re-ingest: a counting system sees exactly
        # one ingest per event.
        events = self._events()

        class Counter(OracleMemorySystem):
            ingests = 0

            def ingest(self, turn):
                type(self).ingests += 1
                super().ingest(turn)

        Counter.ingests = 0
        score_on_events(Counter(events), events, replay="transaction_checkpoint")
        self.assertEqual(Counter.ingests, len(events))

    def test_projected_ingests_matches_event_counts(self) -> None:
        config = {
            "seeds": [7, 13, 17],
            "scales": [{"entities": 3, "revisions": 2}],
            "profiles": [{"name": "revision_only"}],
        }
        projection = projected_ingests(config)
        self.assertEqual(projection["cells"], 3)
        self.assertGreater(projection["ingest_calls"], 0)
        self.assertGreater(projection["search_calls"], 0)


if __name__ == "__main__":
    unittest.main()
