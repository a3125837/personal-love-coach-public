import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1] / "personal-love-coach"
sys.path.insert(0, str(SKILL / "scripts"))
import coach


def profile(phase="P4"):
    record = coach.read_json(SKILL / "assets/relationship-profile.example.json")
    record.update(relationship_phase=phase,
                  phase_history=[dict(phase=phase, date="2026-10-27", evidence="虚构档案事件：双方表示希望继续单独相处，未约定恋人身份")],
                  updated_at="2026-10-27")
    return record


class EightStageProfileTests(unittest.TestCase):
    def test_old_profile_remains_unchanged_without_inferred_phase(self):
        old = coach.read_json(SKILL / "assets/relationship-profile.example.json")
        with tempfile.TemporaryDirectory() as root:
            coach.save_profile(root, old)
            saved = coach.read_json(Path(root) / "profiles" / (old["id"] + ".json"))
            self.assertEqual(saved, old)
            self.assertNotIn("relationship_phase", saved)

    def test_all_eight_phases_and_unknown_match_schema(self):
        import jsonschema
        schema = coach.read_json(SKILL / "schemas/relationship-profile.schema.json")
        for phase in ("unknown", *[f"P{i}" for i in range(1, 9)]):
            with self.subTest(phase=phase):
                item = profile(phase)
                coach.validate_profile(item)
                self.assertEqual(list(jsonschema.Draft202012Validator(schema).iter_errors(item)), [])

    def test_invalid_phase_missing_evidence_and_history_disagreement_rejected(self):
        for update in (dict(relationship_phase="P9"), dict(phase_history=[]),
                       dict(phase_history=[dict(phase="P3", date="2026-10-27", evidence="不匹配")]),
                       dict(phase_history=[dict(phase="P4", date="2026-10-27", evidence="")])):
            with self.subTest(update=update), self.assertRaises(ValueError):
                coach.validate_profile({**profile(), **update})

    def test_phase_history_cannot_be_erased_on_revision(self):
        old = profile()
        with tempfile.TemporaryDirectory() as root:
            coach.save_profile(root, old)
            revised = {**old, "revision": 2, "change_reason": "测试", "phase_history": [], "relationship_phase": "unknown"}
            with self.assertRaises(ValueError):
                coach.save_profile(root, revised)
            omitted = copy.deepcopy(old)
            omitted.update(revision=2, change_reason="遗漏阶段数据")
            del omitted["relationship_phase"]
            del omitted["phase_history"]
            with self.assertRaises(ValueError):
                coach.save_profile(root, omitted)

    def test_phase_transition_needs_new_dated_evidence_and_keeps_old_history(self):
        old = profile()
        with tempfile.TemporaryDirectory() as root:
            coach.save_profile(root, old)
            revised = copy.deepcopy(old)
            revised.update(revision=2, relationship_phase="P5", change_reason="虚构：双方确认恋人")
            revised["phase_history"].append(dict(phase="P5", date="2026-10-27", evidence="虚构档案事件：双方同意以恋人身份交往"))
            coach.save_profile(root, revised)
            saved = coach.read_json(Path(root) / "profiles" / (old["id"] + ".json"))
            self.assertEqual(saved["relationship_phase"], "P5")
            self.assertEqual(saved["stage"], old["stage"])
            self.assertEqual(len(saved["phase_history"]), 2)


if __name__ == "__main__":
    unittest.main()
