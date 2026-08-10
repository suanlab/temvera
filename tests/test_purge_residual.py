import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from temvera.generator import generate_histories
from temvera.nl_workload import naturalize_events
from temvera.purge_residual import purged_values, scan_temvera


class PurgeResidualTest(unittest.TestCase):
    def _events(self):
        return naturalize_events(
            generate_histories(
                seed=17, entities=3, revisions=2, purge_probability=1.0
            )
        )

    def test_purged_values_are_detected(self) -> None:
        values = purged_values(self._events())
        self.assertTrue(values)

    def test_projections_drop_purged_values_but_ledger_retains(self) -> None:
        events = self._events()
        transaction_at = max(event.recorded_at for event in events)
        with TemporaryDirectory() as tmp:
            report = scan_temvera(events, Path(tmp) / "store", transaction_at)
        stores = {s.store: s.occurrences for s in report.stores}
        # Documented limitation (D-005): the append-only JSONL keeps the payload.
        self.assertGreater(stores["raw_ledger_jsonl"], 0)
        # Every rebuilt projection must be free of the purged value.
        for name in (
            "markdown_projection",
            "lexical-index.json",
            "vector-index.json",
            "graph-index.json",
        ):
            self.assertEqual(stores[name], 0, name)

    def test_report_totals_sum_stores(self) -> None:
        events = self._events()
        transaction_at = max(event.recorded_at for event in events)
        with TemporaryDirectory() as tmp:
            report = scan_temvera(events, Path(tmp) / "store", transaction_at)
        self.assertEqual(report.total, sum(s.occurrences for s in report.stores))
        self.assertIn("temvera", report.as_dict()["system"])


if __name__ == "__main__":
    unittest.main()
