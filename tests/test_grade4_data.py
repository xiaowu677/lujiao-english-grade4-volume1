import json
import re
import unittest
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "grade4.json"
WORKBOOK_PATH = ROOT / "data" / "知识闪记-鲁教版4年级英语 上册单词表V5-修正版.xlsx"

EXPECTED_COUNTS = {
    "unit1": 14,
    "unit2": 15,
    "unit3": 21,
    "unit4": 19,
    "unit5": 15,
    "unit6": 25,
    "unit7": 24,
}


def load_site_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def load_workbook_rows():
    workbook = openpyxl.load_workbook(WORKBOOK_PATH, data_only=True)
    worksheet = workbook.worksheets[0]
    return {
        str(unit): list(words)
        for unit, words in _group_rows(worksheet).items()
    }


def _group_rows(worksheet):
    grouped = {}
    for row in worksheet.iter_rows(min_row=2, values_only=True):
        unit, en, ipa, _syllables, zh, pos, _hint, example, translation, _audio = row
        grouped.setdefault(unit, []).append(
            {
                "en": en,
                "zh": zh,
                "ipa": ipa,
                "pos": pos,
                "trainingSentence": example,
                "trainingZh": translation,
            }
        )
    return grouped


def fill_template(template, word):
    filled = template.replace("{{word}}", word)
    if template.startswith("{{word}}"):
        filled = filled[:1].upper() + filled[1:]
    return filled


class Grade4DataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_site_data()
        cls.workbook = load_workbook_rows()

    def test_units_and_words_match_the_corrected_workbook_in_order(self):
        self.assertEqual(
            [unit["id"] for unit in self.data["units"]],
            list(EXPECTED_COUNTS),
        )

        for unit in self.data["units"]:
            expected = self.workbook[unit["id"]]
            self.assertEqual(len(unit["words"]), EXPECTED_COUNTS[unit["id"]])
            self.assertEqual(
                [word["en"] for word in unit["words"]],
                [word["en"] for word in expected],
                unit["id"],
            )

            for actual, source in zip(unit["words"], expected):
                for field in ("en", "zh", "ipa", "pos", "trainingZh"):
                    self.assertEqual(actual[field], source[field], f"{unit['id']} {actual['en']} {field}")
                self.assertEqual(
                    fill_template(actual["trainingSentence"], actual["en"]),
                    source["trainingSentence"],
                    f"{unit['id']} {actual['en']} trainingSentence",
                )

    def test_every_word_has_a_group_and_complete_context(self):
        for unit in self.data["units"]:
            for word in unit["words"]:
                for field in (
                    "group",
                    "zhInContext",
                    "sceneId",
                    "acceptanceSentence",
                    "acceptanceZh",
                ):
                    self.assertTrue(word[field], f"{unit['id']} {word['en']} missing {field}")

                self.assertNotIn(
                    "；",
                    word["zhInContext"],
                    f"{unit['id']} {word['en']} has multiple senses in acceptance",
                )

                self.assertEqual(
                    len(re.findall(r"\{\{word\}\}", word["trainingSentence"])),
                    1,
                    f"{unit['id']} {word['en']} training sentence",
                )
                self.assertEqual(
                    len(re.findall(r"\{\{word\}\}", word["acceptanceSentence"])),
                    1,
                    f"{unit['id']} {word['en']} acceptance sentence",
                )
                self.assertEqual(
                    len(re.findall(r"\{\{word\}\}", word["acceptanceZh"])),
                    1,
                    f"{unit['id']} {word['en']} Chinese acceptance sentence",
                )
                self.assertNotEqual(
                    word["trainingSentence"],
                    word["acceptanceSentence"],
                    f"{unit['id']} {word['en']} reuses its training sentence",
                )

    def test_four_stories_cover_each_unit_exactly_once(self):
        for unit in self.data["units"]:
            self.assertEqual(len(unit["scenes"]), 4, unit["id"])
            expected_words = [word["en"] for word in unit["words"]]
            scene_words = [
                word
                for scene in unit["scenes"]
                for word in scene["wordEns"]
            ]
            self.assertEqual(len(scene_words), len(set(scene_words)), unit["id"])
            self.assertEqual(set(scene_words), set(expected_words), unit["id"])

            for scene in unit["scenes"]:
                self.assertTrue(scene["title"].strip(), unit["id"])
                self.assertTrue(scene["subtitle"].strip(), unit["id"])
                self.assertTrue(scene["story"].strip(), unit["id"])
                self.assertTrue(scene["storyZh"].strip(), unit["id"])
                normalized_story = scene["story"].lower()
                for word in scene["wordEns"]:
                    self.assertIn(word.lower(), normalized_story, f"{unit['id']} {word}")

            for word in unit["words"]:
                scene = next(
                    scene
                    for scene in unit["scenes"]
                    if word["en"] in scene["wordEns"]
                )
                self.assertEqual(word["sceneId"], scene["id"], f"{unit['id']} {word['en']}")


if __name__ == "__main__":
    unittest.main()
