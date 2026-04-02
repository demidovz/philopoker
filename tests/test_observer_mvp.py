import os
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spectator_mvp.config import AppConfig
from spectator_mvp.game import SocraticMatch
from spectator_mvp.llm import _fallback_payload_for_task


class TestObserverMvp(unittest.TestCase):
    def test_vote_fallback_fills_empty_fields(self):
        payload = {
            "candidate_refined_claim": "Более точная версия тезиса.",
            "candidate_new_claim": "Новая продуктивная идея.",
        }
        repaired = _fallback_payload_for_task(
            "vote",
            payload,
            {"status": "spawn_new_claim", "rationale": "", "contradiction_found": False},
        )
        self.assertTrue(repaired["rationale"])
        self.assertEqual(repaired["new_claim"], "Новая продуктивная идея.")

    def test_mock_match_runs_and_keeps_usage(self):
        test_dir = Path(__file__).resolve().parent / "_tmp_logs"
        test_dir.mkdir(exist_ok=True)
        log_path = test_dir / "match.jsonl"
        if log_path.exists():
            log_path.unlink()
        try:
            config = AppConfig(
                thesis="Свобода воли существует.",
                rounds=1,
                mode="mock",
                model="gpt-5-nano",
                pause_mode="off",
                temperature=0.6,
                api_key=None,
                log_path=log_path,
            )
            match = SocraticMatch(config)
            match.run()
            self.assertGreater(match.backend.usage.calls, 0)
            self.assertTrue(match.state.current_claim)
            self.assertNotIn("Протагор считает", match.state.current_claim)
            self.assertTrue(log_path.exists())
            with log_path.open("r", encoding="utf-8") as handle:
                rows = [line for line in handle if line.strip()]
            self.assertGreater(len(rows), 3)
        finally:
            if test_dir.exists():
                shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
