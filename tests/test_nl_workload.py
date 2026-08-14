import unittest

from temvera.evaluation import cases_from_oracle, evaluate
from temvera.generator import generate_histories, generate_lifecycle_suite
from temvera.nl_workload import build_nl_cases, naturalize_events, render_turns
from temvera.oracle import LifecycleOracle


class NLWorkloadTest(unittest.TestCase):
    def test_render_is_deterministic_and_one_turn_per_event(self) -> None:
        events = generate_histories(
            seed=7,
            entities=3,
            revisions=3,
            reconfirm_probability=0.5,
            expire_probability=0.3,
            purge_probability=0.3,
        )
        first = render_turns(events)
        second = render_turns(events)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(events))
        self.assertEqual(
            [turn.event_id for turn in first], [event.event_id for event in events]
        )

    def test_cases_resolve_values_and_mark_deletion_as_empty(self) -> None:
        events = generate_lifecycle_suite(seed=11)
        cases = build_nl_cases(events)
        self.assertTrue(cases)
        valid_cases = [case for case in cases if case.category == "valid_time"]
        self.assertTrue(valid_cases)
        self.assertTrue(all(case.expected_values for case in valid_cases))
        purge_cases = [case for case in cases if case.category == "purge"]
        self.assertTrue(purge_cases)
        self.assertTrue(all(not case.expected_values for case in purge_cases))

    def test_query_text_names_subject_attribute_and_times(self) -> None:
        events = generate_histories(seed=3, entities=2, revisions=2)
        case = build_nl_cases(events)[0]
        self.assertIn(case.subject, case.query_text)
        self.assertIn(case.attribute, case.query_text)
        self.assertIn(case.valid_at.date().isoformat(), case.query_text)
        self.assertIn(case.transaction_at.date().isoformat(), case.query_text)

    def test_naturalize_is_injective_and_preserves_oracle_exactness(self) -> None:
        events = generate_histories(
            seed=17, entities=3, revisions=2, expire_probability=0.3, purge_probability=0.3
        )
        natural = naturalize_events(events)
        # Same number of events and belief ids, distinct tokens stay distinct.
        self.assertEqual(len(natural), len(events))
        orig_subjects = {e.subject for e in events if e.subject}
        nat_subjects = {e.subject for e in natural if e.subject}
        self.assertEqual(len(orig_subjects), len(nat_subjects))
        self.assertNotEqual(orig_subjects, nat_subjects)
        # Relabeling is a bijection, so the oracle stays exact on the new tokens.
        cases = cases_from_oracle(natural)
        result = evaluate(LifecycleOracle(natural), cases)
        self.assertEqual(result.exact_state_accuracy, 1.0)
        self.assertEqual(result.evidence_recall, 1.0)

    def test_stale_values_never_overlap_expected(self) -> None:
        events = generate_histories(
            seed=21, entities=4, revisions=4, expire_probability=0.5
        )
        for case in build_nl_cases(events):
            self.assertFalse(case.expected_values & case.stale_values)




class MultiAttributeTest(unittest.TestCase):
    def test_default_is_unchanged_so_sealed_runs_stay_valid(self) -> None:
        from temvera.generator import generate_histories as gen

        self.assertEqual(
            gen(seed=17, entities=3, revisions=2),
            gen(seed=17, entities=3, revisions=2, attributes=1),
        )

    def test_each_attribute_draws_from_its_own_value_class(self) -> None:
        from temvera.generator import generate_histories as gen
        from temvera.model import Operation

        events = naturalize_events(
            gen(seed=17, entities=3, revisions=2, attributes=4)
        )
        by_attribute: dict[str, set[str]] = {}
        for event in events:
            if event.operation is Operation.INGEST:
                by_attribute.setdefault(event.attribute, set()).add(event.value)
        self.assertGreaterEqual(len(by_attribute), 4)
        # No value may be shared between two attributes, or retrieval could not
        # separate them and the workload would stay degenerate.
        seen: set[str] = set()
        for values in by_attribute.values():
            self.assertFalse(seen & values)
            seen |= values

    def test_oracle_stays_exact_on_multi_attribute_histories(self) -> None:
        from temvera.generator import generate_histories as gen

        events = naturalize_events(
            gen(seed=23, entities=3, revisions=3, attributes=3,
                expire_probability=0.3, purge_probability=0.3)
        )
        cases = cases_from_oracle(events)
        result = evaluate(LifecycleOracle(events), cases)
        self.assertEqual(result.exact_state_accuracy, 1.0)
        self.assertEqual(result.evidence_recall, 1.0)


if __name__ == "__main__":
    unittest.main()
