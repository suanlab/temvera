import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from temvera.dataset import freeze_dataset, verify_dataset


class DatasetTest(unittest.TestCase):
    def test_freeze_is_verifiable_and_refuses_overwrite(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "frozen"
            manifest = freeze_dataset(output, entities=2, revisions=2)
            self.assertTrue(verify_dataset(output))
            self.assertEqual(manifest["license"], "Apache-2.0")
            self.assertIn("permitted", str(manifest["redistribution"]))
            self.assertEqual(set(manifest["splits"]), {"train", "development", "test"})
            with self.assertRaises(FileExistsError):
                freeze_dataset(output, entities=2, revisions=2)

            split_ids = {}
            for split in manifest["splits"]:
                rows = [
                    json.loads(line)
                    for line in (output / f"{split}.jsonl").read_text().splitlines()
                ]
                split_ids[split] = {row["belief_id"] for row in rows}
            self.assertFalse(split_ids["train"] & split_ids["development"])
            self.assertFalse(split_ids["train"] & split_ids["test"])

    def test_freeze_is_byte_reproducible(self) -> None:
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            freeze_dataset(first, entities=2, revisions=2)
            freeze_dataset(second, entities=2, revisions=2)
            self.assertEqual(
                {path.name: path.read_bytes() for path in first.iterdir()},
                {path.name: path.read_bytes() for path in second.iterdir()},
            )

    def test_repository_fixture_matches_current_generator(self) -> None:
        repository_fixture = Path(__file__).parents[1] / "data" / "fixtures" / "lifecycle-v0"
        with TemporaryDirectory() as directory:
            regenerated = Path(directory) / "lifecycle-v0"
            freeze_dataset(regenerated, entities=8, revisions=4)
            self.assertEqual(
                {path.name: path.read_bytes() for path in repository_fixture.iterdir()},
                {path.name: path.read_bytes() for path in regenerated.iterdir()},
            )

    def test_tampering_fails_verification(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "frozen"
            freeze_dataset(output, entities=1, revisions=1)
            with (output / "test.jsonl").open("a", encoding="utf-8") as stream:
                stream.write("{}\n")
            self.assertFalse(verify_dataset(output))

    def test_identifier_leakage_fails_verification(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "frozen"
            freeze_dataset(output, entities=1, revisions=1)
            train = [
                json.loads(line)
                for line in (output / "train.jsonl").read_text().splitlines()
            ]
            test_path = output / "test.jsonl"
            test = [json.loads(line) for line in test_path.read_text().splitlines()]
            test[0]["belief_id"] = train[0]["belief_id"]
            test_path.write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in test) + "\n"
            )
            manifest = json.loads((output / "manifest.json").read_text())
            manifest["splits"]["test"]["sha256"] = hashlib.sha256(
                test_path.read_bytes()
            ).hexdigest()
            (output / "manifest.json").write_text(json.dumps(manifest))
            self.assertFalse(verify_dataset(output))


if __name__ == "__main__":
    unittest.main()
