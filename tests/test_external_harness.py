import unittest

from temvera.external_harness import (
    LatestValueSystem,
    OracleMemorySystem,
    evaluate_external,
)
from temvera.generator import generate_histories, generate_lifecycle_suite


class ExternalHarnessTest(unittest.TestCase):
    def _mixed_events(self):
        return generate_histories(
            seed=7,
            entities=4,
            revisions=3,
            reconfirm_probability=0.5,
            expire_probability=0.3,
            purge_probability=0.3,
        )

    def test_oracle_reference_system_is_exact(self) -> None:
        events = self._mixed_events()
        result = evaluate_external(OracleMemorySystem(events), events)
        self.assertGreater(result.cases, 0)
        self.assertEqual(result.exact_state_accuracy, 1.0)
        self.assertEqual(result.evidence_recall, 1.0)
        self.assertEqual(result.stale_use_rate, 0.0)

    def test_harness_discriminates_time_blind_system(self) -> None:
        events = self._mixed_events()
        oracle = evaluate_external(OracleMemorySystem(events), events)
        latest = evaluate_external(LatestValueSystem(events), events)
        self.assertLess(latest.exact_state_accuracy, oracle.exact_state_accuracy)
        self.assertGreater(latest.stale_use_rate, oracle.stale_use_rate)

    def test_reference_system_abstains_after_purge(self) -> None:
        events = generate_lifecycle_suite(seed=11)
        result = evaluate_external(OracleMemorySystem(events), events)
        self.assertGreater(result.abstention_cases, 0)
        self.assertEqual(result.abstention_accuracy, 1.0)

    def test_replay_helps_a_time_blind_system_answer_as_of(self) -> None:
        events = self._mixed_events()
        # A transaction-time-blind system reads the whole store without replay,
        # so it returns globally-latest (often stale) values on historical
        # as-of queries. Per-query replay restricts it to what was known then,
        # improving exactness and cutting stale use. The harness must expose
        # this difference rather than let the no-replay path look artificially
        # correct.
        replay = evaluate_external(LatestValueSystem(events), events)
        no_replay = evaluate_external(
            LatestValueSystem(events), events, per_query_replay=False
        )
        self.assertGreater(
            replay.exact_state_accuracy, no_replay.exact_state_accuracy
        )
        self.assertGreaterEqual(
            no_replay.stale_use_rate, replay.stale_use_rate
        )


if __name__ == "__main__":
    unittest.main()
