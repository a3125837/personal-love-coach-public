"""Check provenance and generation consistency without keeping private-source fingerprints."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "personal-love-coach"


class FictionalCorpusTests(unittest.TestCase):
    def test_corpus_and_generator_use_same_newly_authored_text(self):
        spec = importlib.util.spec_from_file_location("fictional_assets", ROOT / "development/build_assets.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        cases = []
        for name in ("training/scenarios.jsonl", "training/exams.jsonl", "evaluation/holdout.jsonl",
                     "training/eight-stage-scenarios.jsonl"):
            cases.extend(json.loads(line) for line in (SKILL / name).read_text(encoding="utf-8").splitlines())
        self.assertEqual(len(cases), 58)
        self.assertEqual(len({case["input"] for case in cases}), 58)
        for case in cases:
            self.assertEqual(case["source_type"], "synthetic")
            self.assertEqual(case["synthetic_origin"], "independently-authored-fiction")
            self.assertEqual(case["corpus_version"], "fictional-2026-10-27-v2")
        for row, case in zip(builder.ROWS, cases[:50]):
            self.assertEqual(list(row[5:]), [case["input"], case["facts"][0], case["unknowns"][0],
                                           case["expected"][0], case["failures"][0]])
        self.assertEqual(builder.EIGHT_STAGE_ROWS, cases[50:])

    def test_skill_does_not_embed_private_share_access_links(self):
        # This disallows a class of access links, without retaining a user's actual URL or text.
        for path in SKILL.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json", ".jsonl", ".yaml", ".html", ".txt"}:
                with self.subTest(path=path.relative_to(SKILL).as_posix()):
                    self.assertNotIn("chatgpt.com/share/", path.read_text(encoding="utf-8"))
                    self.assertNotIn("chatgpt.com/s/t_", path.read_text(encoding="utf-8"))

    def test_replay_ids_match_current_holdout_bank(self):
        bank = [json.loads(line) for line in (SKILL / "evaluation/holdout.jsonl").read_text(encoding="utf-8").splitlines()]
        fixtures = [json.loads(line) for line in (SKILL / "evaluation/offline-fixtures.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([case["id"] for case in bank], [fixture["id"] for fixture in fixtures])
        self.assertTrue(all(item["source_type"] == "hand-authored-offline-fixture" for item in fixtures))


if __name__ == "__main__":
    unittest.main()
