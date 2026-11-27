import unittest
from collections import Counter
from pathlib import Path

from tools.audio_catalog import build_catalog


ROOT = Path(__file__).resolve().parents[1]


class AudioCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = build_catalog(ROOT)

    def test_catalog_contains_exactly_the_grade_four_audio_set(self):
        self.assertEqual(len(self.items), 426)
        self.assertEqual(
            Counter(item["kind"] for item in self.items),
            {
                "word": 132,
                "training": 133,
                "acceptance": 133,
                "story": 28,
            },
        )
        self.assertEqual(len({item["id"] for item in self.items}), 426)

    def test_repeated_get_ready_points_to_both_units(self):
        item = next(
            item
            for item in self.items
            if item["kind"] == "word" and item["text"] == "get ready"
        )
        self.assertEqual(
            item["sources"],
            ["v2.1-unit5", "v2.1-unit7"],
        )

    def test_ids_are_stable_safe_mp3_names(self):
        for item in self.items:
            self.assertRegex(item["id"], r"^[a-z]+-[0-9a-f]{16}$")
            self.assertTrue(item["filename"].endswith(".mp3"))
            self.assertNotIn("/", item["filename"])
            self.assertNotIn("\\", item["filename"])
            self.assertTrue(item["text"].strip())


if __name__ == "__main__":
    unittest.main()
