import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spectator_mvp.analyze import aggregate


class TestAnalyzeLogs(unittest.TestCase):
    def test_aggregate_counts_verdicts_and_questions(self):
        test_dir = Path(__file__).resolve().parent / "_tmp_analyze"
        test_dir.mkdir(exist_ok=True)
        log_path = test_dir / "sample.jsonl"
        try:
            rows = [
                {"event": "question", "payload": {"agent": {"name": "Скептик"}, "question": "Почему?"}},
                {"event": "vote", "payload": {"agent": {"name": "Скептик"}, "status": "refute"}},
                {"event": "round_finished", "payload": {"verdict": {"status": "refute"}}},
                {"event": "match_finished", "payload": {"calls": 18, "estimated_cost_usd": 0.001, "final_claim": "X"}},
            ]
            with log_path.open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")

            summary = aggregate([log_path])
            self.assertEqual(summary["verdicts"]["refute"], 1)
            self.assertEqual(summary["questions"]["Скептик"], 1)
            self.assertEqual(summary["votes"]["Скептик"]["refute"], 1)
            self.assertEqual(summary["total_calls"], 18)
        finally:
            if test_dir.exists():
                import shutil

                shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
