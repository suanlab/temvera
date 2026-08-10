from datetime import datetime, timedelta, timezone
import unittest

from temvera.evaluation import (
    AppendOnlyBaseline,
    BM25Baseline,
    FullContextBaseline,
    QueryCase,
    RecentContextBaseline,
    cases_from_oracle,
    error_analysis,
    evaluate,
)
from temvera.generator import generate_histories
from temvera.model import MemoryEvent, Operation
from temvera.oracle import LifecycleOracle


T0 = datetime(2025, 1, 1, tzinfo=timezone.utc)


class EvaluationTest(unittest.TestCase):
    def test_metrics_expose_stale_append_only_result(self) -> None:
        events = (
            MemoryEvent("e1", Operation.INGEST, "old", T0, "s", "a", "old", T0),
            MemoryEvent(
                "e2",
                Operation.INGEST,
                "new",
                T0 + timedelta(days=2),
                "s",
                "a",
                "new",
                T0 + timedelta(days=1),
            ),
            MemoryEvent(
                "e3",
                Operation.SUPERSEDE,
                "new",
                T0 + timedelta(days=2),
                valid_from=T0 + timedelta(days=1),
                target_id="old",
            ),
        )
        case = QueryCase(
            "q1",
            "s",
            "a",
            T0 + timedelta(days=3),
            T0 + timedelta(days=3),
            frozenset({"new"}),
            frozenset({"old"}),
        )
        oracle_result = evaluate(LifecycleOracle(events), (case,))
        append_result = evaluate(AppendOnlyBaseline(events), (case,))
        self.assertEqual(oracle_result.exact_state_accuracy, 1.0)
        self.assertEqual(oracle_result.stale_use_rate, 0.0)
        self.assertLess(append_result.exact_state_accuracy, 1.0)
        self.assertGreater(append_result.stale_use_rate, 0.0)
        errors = error_analysis(AppendOnlyBaseline(events), (case,))
        self.assertEqual(errors[0].missed_ids, ())
        self.assertEqual(errors[0].stale_ids, ("old",))
        self.assertEqual(errors[0].unexpected_ids, ("old",))

    def test_generated_cases_make_oracle_self_consistent(self) -> None:
        events = generate_histories(seed=99, entities=3, revisions=4)
        cases = cases_from_oracle(events)
        result = evaluate(LifecycleOracle(events), cases)
        self.assertGreaterEqual(len(cases), 12)
        self.assertEqual(result.exact_state_accuracy, 1.0)
        self.assertEqual(result.evidence_recall, 1.0)

    def test_cases_include_purged_and_expired_empty_truth(self) -> None:
        events = (
            MemoryEvent("e1", Operation.INGEST, "purged", T0, "s", "a", "x", T0),
            MemoryEvent(
                "e2", Operation.PURGE, "purged", T0 + timedelta(days=2)
            ),
            MemoryEvent(
                "e3", Operation.INGEST, "expired", T0, "s", "b", "y", T0
            ),
            MemoryEvent(
                "e4",
                Operation.EXPIRE,
                "expired",
                T0 + timedelta(days=2),
                valid_to=T0 + timedelta(days=1),
            ),
        )
        cases = cases_from_oracle(events)
        purged_final = [
            case
            for case in cases
            if case.subject == "s"
            and case.attribute == "a"
            and case.transaction_at == T0 + timedelta(days=2)
        ]
        expired_boundary = [
            case
            for case in cases
            if case.attribute == "b" and case.valid_at == T0 + timedelta(days=1)
        ]
        self.assertTrue(purged_final)
        self.assertTrue(all(not case.expected_ids for case in purged_final))
        self.assertTrue(all(case.category == "purge" for case in purged_final))
        self.assertTrue(expired_boundary)
        self.assertTrue(all(not case.expected_ids for case in expired_boundary))
        self.assertTrue(
            all(case.category == "expiry_boundary" for case in expired_boundary)
        )

    def test_context_and_bm25_baselines_have_fixed_semantics(self) -> None:
        events = (
            MemoryEvent("e1", Operation.INGEST, "old", T0, "s", "a", "old", T0),
            MemoryEvent(
                "e2",
                Operation.INGEST,
                "other",
                T0 + timedelta(hours=1),
                "unrelated",
                "field",
                "noise",
                T0,
            ),
            MemoryEvent(
                "e3",
                Operation.INGEST,
                "new",
                T0 + timedelta(days=2),
                "s",
                "a",
                "new",
                T0 + timedelta(days=1),
            ),
        )
        arguments = {
            "subject": "s",
            "attribute": "a",
            "valid_at": T0 + timedelta(days=3),
            "transaction_at": T0 + timedelta(days=3),
        }
        self.assertEqual(
            {item.belief_id for item in FullContextBaseline(events).query(**arguments)},
            {"old", "new"},
        )
        self.assertEqual(
            [item.belief_id for item in RecentContextBaseline(events).query(**arguments)],
            ["new"],
        )
        self.assertEqual(
            [item.belief_id for item in BM25Baseline(events).query(**arguments)],
            ["new"],
        )

    def test_bm25_rejects_invalid_budget(self) -> None:
        with self.assertRaises(ValueError):
            BM25Baseline((), limit=0)


if __name__ == "__main__":
    unittest.main()
