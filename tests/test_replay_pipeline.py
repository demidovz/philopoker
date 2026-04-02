import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spectator_mvp.config import AppConfig
from spectator_mvp.game import SocraticMatch
from spectator_mvp.replay import load_events


class TestReplayPipeline(unittest.TestCase):
    def test_run_match_produces_replayable_log(self):
        test_dir = Path(__file__).resolve().parent / "_tmp_replay"
        test_dir.mkdir(exist_ok=True)
        log_path = test_dir / "match.jsonl"
        try:
            config = AppConfig(
                thesis="Истина всегда зависит от точки зрения.",
                rounds=1,
                mode="mock",
                model="gpt-5-nano",
                pause_mode="off",
                temperature=0.6,
                api_key=None,
                log_path=log_path,
            )
            match = SocraticMatch(config, live_ui=False)
            match.run()
            events = load_events(log_path)
            kinds = [event["event"] for event in events]
            self.assertIn("backend_healthcheck", kinds)
            self.assertIn("seating", kinds)
            self.assertIn("arbiter_message", kinds)
            self.assertIn("round_event", kinds)
            self.assertIn("round_finished", kinds)
            round_finished = next(event for event in events if event["event"] == "round_finished")
            self.assertTrue(round_finished["payload"]["verdict"]["winner"])
            self.assertIn("contradiction_found", round_finished["payload"]["verdict"])
            self.assertIn("points", round_finished["payload"]["verdict"])
            match_finished = next(event for event in events if event["event"] == "match_finished")
            self.assertTrue(match_finished["payload"]["champion"])
            self.assertIn("initial_claim", match_finished["payload"])
            self.assertIn("child_summary", match_finished["payload"])
            self.assertIn("change_summary", match_finished["payload"])
        finally:
            if test_dir.exists():
                import shutil

                shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
