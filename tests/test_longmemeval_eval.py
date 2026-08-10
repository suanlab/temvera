import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from temvera.longmemeval_eval import gold_signal, load_instances, session_turns


class LongMemEvalScorerTest(unittest.TestCase):
    def test_gold_substring_and_token_recall(self) -> None:
        present, recall = gold_signal("25 minutes", "your best was 25 minutes flat")
        self.assertTrue(present)
        self.assertEqual(recall, 1.0)
        present, recall = gold_signal("blue bicycle", "she bought a bicycle")
        self.assertFalse(present)
        self.assertAlmostEqual(recall, 0.5)
        present, recall = gold_signal("kayak", "nothing relevant here")
        self.assertFalse(present)
        self.assertEqual(recall, 0.0)

    def _fixture(self, directory: Path) -> Path:
        rows = [
            {
                "question_id": f"q{index}",
                "question_type": "knowledge-update" if index % 2 else "temporal-reasoning",
                "question": "what?",
                "answer": "answer",
                "haystack_dates": ["2023/05/25 (Thu) 20:21"],
                "haystack_sessions": [
                    [{"role": "user", "content": f"hello {index}"}, {"role": "assistant", "content": ""}]
                ],
            }
            for index in range(6)
        ]
        path = directory / "lme.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        return path

    def test_load_is_deterministic_per_type(self) -> None:
        with TemporaryDirectory() as tmp:
            path = self._fixture(Path(tmp))
            first = load_instances(
                path, question_types=("knowledge-update",), limit=2
            )
            second = load_instances(
                path, question_types=("knowledge-update",), limit=2
            )
        self.assertEqual([r["question_id"] for r in first], [r["question_id"] for r in second])
        self.assertEqual(len(first), 2)
        self.assertTrue(all(r["question_type"] == "knowledge-update" for r in first))

    def test_session_turns_skip_empty_and_carry_dates(self) -> None:
        with TemporaryDirectory() as tmp:
            path = self._fixture(Path(tmp))
            instance = load_instances(path, question_types=("knowledge-update",), limit=1)[0]
        lines = session_turns(instance)
        self.assertEqual(len(lines), 1)  # empty assistant turn dropped
        self.assertIn("2023/05/25", lines[0])
        self.assertIn("user:", lines[0])


if __name__ == "__main__":
    unittest.main()
