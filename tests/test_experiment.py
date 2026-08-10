import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from temvera.experiment import (
    checksums,
    run_lifecycle_experiment,
    seal_run,
    verify_run,
    verify_run_set,
)


CONFIG = {
    "benchmark": "temvera-lifecycle-smoke",
    "dataset": {"entities": 2, "revisions": 3, "seed": 17},
}


class ExperimentTest(unittest.TestCase):
    def test_run_contains_required_reproducibility_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            run_dir = run_lifecycle_experiment(CONFIG, Path(directory))
            required = {
                "README.md",
                "checksums.json",
                "config.json",
                "environment.json",
                "error-analysis.json",
                "metrics.json",
                "predictions.jsonl",
                "stdout.log",
            }
            self.assertEqual({path.name for path in run_dir.iterdir()}, required)
            recorded = json.loads((run_dir / "checksums.json").read_text())
            self.assertEqual(recorded, checksums(run_dir))
            metrics = json.loads((run_dir / "metrics.json").read_text())
            self.assertEqual(metrics["oracle"]["exact_state_accuracy"], 1.0)
            errors = json.loads((run_dir / "error-analysis.json").read_text())
            self.assertEqual(errors["oracle"], [])
            self.assertTrue(errors["append_only"])

    def test_same_config_and_source_cannot_overwrite_run(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run_lifecycle_experiment(CONFIG, root)
            with self.assertRaises(FileExistsError):
                run_lifecycle_experiment(CONFIG, root)

    def test_seal_and_verify_generic_run_detects_tampering(self) -> None:
        with TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            run_dir.mkdir()
            result = run_dir / "results.json"
            result.write_text('{"score": 1}\n', encoding="utf-8")
            source = Path(directory) / "source"
            source.mkdir()
            (source / "method.py").write_text("VALUE = 1\n", encoding="utf-8")

            seal_run(
                run_dir,
                config={"seed": 7},
                command="temvera example",
                source_root=source,
            )

            self.assertTrue(verify_run(run_dir))
            with self.assertRaises(FileExistsError):
                seal_run(run_dir, config={"seed": 7}, command="temvera example")
            result.write_text('{"score": 0}\n', encoding="utf-8")
            self.assertFalse(verify_run(run_dir))

    def test_unsealed_or_empty_run_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            run_dir = Path(directory)
            self.assertFalse(verify_run(run_dir))
            with self.assertRaises(ValueError):
                seal_run(run_dir, config={}, command="temvera example")

    def test_verify_run_set_rejects_tamper_duplicates_and_traversal(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "accepted"
            run.mkdir()
            (run / "results.json").write_text("{}\n", encoding="utf-8")
            source = root / "source"
            source.mkdir()
            (source / "x.py").write_text("x = 1\n", encoding="utf-8")
            seal_run(run, config={}, command="example", source_root=source)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"accepted_runs": ["accepted"]}), encoding="utf-8"
            )
            self.assertTrue(verify_run_set(root, manifest))
            manifest.write_text(
                json.dumps({"accepted_runs": ["accepted", "accepted"]}),
                encoding="utf-8",
            )
            self.assertFalse(verify_run_set(root, manifest))
            manifest.write_text(
                json.dumps({"accepted_runs": ["../accepted"]}), encoding="utf-8"
            )
            self.assertFalse(verify_run_set(root, manifest))


if __name__ == "__main__":
    unittest.main()
