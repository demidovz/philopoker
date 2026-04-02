import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spectator_mvp.theses import thesis_by_id, thesis_choices_text


class TestThesisCatalog(unittest.TestCase):
    def test_thesis_lookup_by_id(self):
        self.assertEqual(thesis_by_id("free_will"), "Свобода воли существует.")
        self.assertIsNone(thesis_by_id("missing"))

    def test_choices_text_contains_ids_and_text(self):
        text = thesis_choices_text()
        self.assertIn("free_will", text)
        self.assertIn("simulation", text)
        self.assertIn("Свобода воли существует.", text)


if __name__ == "__main__":
    unittest.main()
