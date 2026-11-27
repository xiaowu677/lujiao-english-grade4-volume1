#!/usr/bin/env python3
"""Merge the corrected workbook with authored Grade 4 context and stories."""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "知识闪记-鲁教版4年级英语 上册单词表V5-修正版.xlsx"
CONTENT = ROOT / "data" / "content.json"
OUTPUT = ROOT / "data" / "grade4.json"

GROUP_BY_POS = {
    "n.": "noun",
    "v.": "verb",
    "adj.": "adjective",
    "adv.": "adverb",
    "pron.": "pronoun",
    "prep.": "preposition",
    "phr.": "phrase",
    "modal v.": "modal",
    "det.": "determiner",
}

ZH_CONTEXT_OVERRIDES = {
    "with": "和某人一起",
    "grandparent": "祖父或祖母",
    "all right": "一切还好",
    "take": "拿",
    "well": "好",
    "has": "有",
    "him": "他",
    "racing": "比赛",
}


def read_workbook_units():
    worksheet = openpyxl.load_workbook(WORKBOOK, data_only=True).worksheets[0]
    units = {}
    for row in worksheet.iter_rows(min_row=2, values_only=True):
        unit, en, ipa, _syllables, zh, pos, _hint, example, translation, _audio = row
        units.setdefault(unit, []).append(
            {
                "en": en,
                "zh": zh,
                "ipa": ipa,
                "pos": pos,
                "group": GROUP_BY_POS.get(pos, "other"),
                "trainingSentence": example,
                "trainingZh": translation,
            }
        )
    return units


def merge_unit(source, authored):
    workbook_words = source[authored["id"]]
    scenes = authored["scenes"]
    scene_by_word = {}
    for scene in scenes:
        for word in scene["wordEns"]:
            if word in scene_by_word:
                raise ValueError(f"{authored['id']}: {word} appears in two scenes")
            scene_by_word[word] = scene["id"]

    words = []
    for word in workbook_words:
        acceptance = authored["acceptance"].get(word["en"])
        if not acceptance:
            raise ValueError(f"{authored['id']}: missing acceptance for {word['en']}")
        if word["en"] not in scene_by_word:
            raise ValueError(f"{authored['id']}: {word['en']} has no scene")
        def placeholder(match):
            return "{{word}}"

        training = re.sub(
            rf"(?<![A-Za-z]){re.escape(word['en'])}(?![A-Za-z])",
            placeholder,
            word["trainingSentence"],
            count=1,
            flags=re.IGNORECASE,
        )
        words.append(
            {
                **word,
                "zhInContext": ZH_CONTEXT_OVERRIDES.get(
                    word["en"],
                    word["zh"].split("；", 1)[0],
                ),
                "sceneId": scene_by_word[word["en"]],
                "trainingSentence": training,
                "acceptanceSentence": acceptance[0],
                "acceptanceZh": acceptance[1],
            }
        )

    extra_words = set(authored["acceptance"]) - {word["en"] for word in workbook_words}
    if extra_words:
        raise ValueError(f"{authored['id']}: extra acceptance words {sorted(extra_words)}")

    return {
        "id": authored["id"],
        "title": authored["title"],
        "titleZh": authored["titleZh"],
        "words": words,
        "scenes": scenes,
    }


def main():
    content = json.loads(CONTENT.read_text(encoding="utf-8"))
    workbook_units = read_workbook_units()
    result = {
        "version": content["version"],
        "grade": content["grade"],
        "volume": content["volume"],
        "publisher": content["publisher"],
        "units": [
            merge_unit(workbook_units, unit)
            for unit in content["units"]
        ],
    }
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    counts = {unit["id"]: len(unit["words"]) for unit in result["units"]}
    print(json.dumps({"output": str(OUTPUT), "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
