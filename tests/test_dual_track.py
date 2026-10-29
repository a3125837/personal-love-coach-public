"""Synthetic end-to-end invariants for first reactions, reflection and missingness."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1] / "personal-love-coach"
sys.path.insert(0, str(SKILL / "scripts"))
import coach
import learning


class DualTrackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "data"
        self.session = coach.read_json(SKILL / "assets/training-session.example.json")
        coach.save_session(self.root, self.session)
        self.raw = dict(round_id="demo-session", case_id="PLC-004", date="2026-10-28", answer="又出故障，确实扫兴。", hint_used=False)

    def tearDown(self):
        self.temp.cleanup()

    def note(self, **updates):
        note = dict(id="note-one", round_id="demo-session", case_id="PLC-004", date="2026-10-28",
                    kind="reflection", analysis="我先回应失落，再看对方是否想解决问题。")
        note.update(updates)
        return {key: value for key, value in note.items() if value is not None}

    def test_reflection_needs_first_answer(self):
        with self.assertRaises(ValueError):
            learning.save_note(self.root, self.note())

    def test_reflection_survives_restart_without_changing_first_answer(self):
        coach.save_answer(self.root, self.raw)
        path = self.root / "answers/demo-session/PLC-004.json"
        before = path.read_bytes()
        learning.save_note(self.root, self.note())
        learning.save_note(self.root, self.note())
        self.assertEqual(path.read_bytes(), before)
        restored = coach.show_session(self.root, "demo-session")
        self.assertEqual(restored["learning_notes"][0]["analysis"], self.note()["analysis"])
        self.assertEqual(restored["results"], [])
        with self.assertRaises(ValueError):
            learning.save_note(self.root, self.note(analysis="另一段分析"))

    def test_status_does_not_create_zero_grade(self):
        learning.save_note(self.root, self.note(kind="response_status", analysis=None, status="cannot_formulate", reason="暂时不知道怎么表达"))
        report = learning.coverage_report(self.root)
        self.assertEqual(report["selected_count"], 3)
        self.assertEqual(report["answered_count"], 0)
        self.assertEqual(report["missing_by_status"]["cannot_formulate"], 1)
        self.assertEqual(report["graded_count"], 0)
        self.assertEqual(coach.load_history(self.root), [])

    def test_later_answer_preserves_prior_difficulty_without_double_counting(self):
        learning.save_note(self.root, self.note(kind="response_status", analysis=None, status="cannot_formulate", reason="暂时不会回应"))
        coach.save_answer(self.root, self.raw)
        report = learning.coverage_report(self.root)
        self.assertEqual(report["answered_count"], 1)
        self.assertEqual(report["answered_after_cannot_formulate"], 1)
        self.assertEqual(report["unanswered_count"], 2)
        with self.assertRaises(ValueError):
            learning.save_note(self.root, self.note(id="cannot-again", kind="response_status", analysis=None, status="skipped", reason="已回答不能改成跳过"))

    def test_pending_exam_blocks_teaching_notes(self):
        case_ids = ["PLC-031", "PLC-032", "PLC-033"]
        coach.save_session(self.root, {**self.session, "id": "exam-one", "mode": "exam", "case_ids": case_ids})
        coach.save_answer(self.root, {**self.raw, "round_id": "exam-one", "case_id": case_ids[0]})
        with self.assertRaises(ValueError):
            learning.save_note(self.root, self.note(round_id="exam-one", case_id=case_ids[0]))

    def test_note_cannot_inject_scores_or_claimed_promotion(self):
        coach.save_answer(self.root, self.raw)
        with self.assertRaises(ValueError):
            learning.save_note(self.root, self.note(total=20))

    def test_coach_review_keeps_three_checkpoints_and_counterevidence(self):
        coach.save_answer(self.root, self.raw)
        review = self.note(kind="coach_review", analysis=None, understanding="识别了失落", expression="实际表达了理解", action="允许停留",
            scope="仅此情境", hypothesis="复杂情绪仍待验证", supporting_evidence=["本题原答"], counterevidence=["尚无跨情境记录"])
        learning.save_note(self.root, review)
        notes = learning.load_notes(self.root, "demo-session")
        self.assertEqual(notes[0]["action"], "允许停留")
        self.assertEqual(notes[0]["scope"], "仅此情境")

    def test_status_and_note_identity_and_date_are_checked(self):
        for update in (dict(case_id="not-selected"), dict(date="2020-01-01"), dict(id="../escape")):
            with self.subTest(update=update), self.assertRaises(ValueError):
                learning.save_note(self.root, self.note(kind="response_status", analysis=None, status="skipped", reason="测试", **update))

    def test_coverage_of_empty_data_is_honest(self):
        other = Path(self.temp.name) / "empty"
        report = learning.coverage_report(other)
        self.assertEqual(report["selected_count"], 0)
        self.assertIsNone(report["answer_coverage"])

    def test_reflection_assistance_cannot_be_erased_after_review(self):
        coach.save_answer(self.root, self.raw)
        review = self.note(id="review", kind="coach_review", analysis=None, understanding="接住失落", expression="简短回应", action="不催促",
            scope="仅这一题", hypothesis="跨场景待验证", supporting_evidence=["本题原答"], counterevidence=[])
        learning.save_note(self.root, review)
        with self.assertRaises(ValueError):
            learning.save_note(self.root, self.note(assistance="unassisted"))
        learning.save_note(self.root, self.note(assistance="assisted"))
        self.assertEqual(learning.coverage_report(self.root)["reflection_notes_by_assistance"]["assisted"], 1)

    def test_exam_can_record_missing_status_without_creating_a_grade(self):
        ids = ["PLC-031", "PLC-032", "PLC-033"]
        coach.save_session(self.root, {**self.session, "id": "missing-exam", "mode": "exam", "case_ids": ids})
        learning.save_note(self.root, self.note(round_id="missing-exam", case_id=ids[0], kind="response_status", analysis=None,
            status="skipped", reason="暂时跳过"))
        report = learning.coverage_report(self.root, "missing-exam")
        self.assertEqual(report["missing_by_status"]["skipped"], 1)
        self.assertEqual(report["answered_count"], 0)
        self.assertEqual(coach.load_history(self.root), [])

    def test_context_is_bound_and_cannot_be_faked_in_grade(self):
        ids = ["DT-001", "DT-002", "DT-003"]
        session = {**self.session, "id": "context", "case_ids": ids}
        coach.save_session(self.root, session)
        case = coach.load_catalog()[ids[0]]
        record = dict(id="context-grade", round_id="context", case_id=ids[0], relationship_id="simulation", date="2026-10-28",
            mode="training", rubric_version=coach.RUBRIC, level=2, category=case["category"], attempt=1, hint_used=False,
            critical_error=False, scores={d:4 for d in coach.DIMENSIONS}, answer="太棒了，调出来一定很开心。",
            communication_function="vent", signal_clarity="ambiguous")
        coach.append_result(self.root, record)
        saved = coach.load_history(self.root)[0]
        self.assertEqual(saved["communication_function"], "share")
        self.assertEqual(saved["signal_clarity"], "explicit")
        other = {**saved, "id":"other", "signal_clarity":"ambiguous"}
        self.assertEqual(len(coach.progress_report([saved, other])["comparable_groups"]), 2)
        self.assertNotIn("learning_context", coach.show_session(self.root, "context")["questions"][0])

    def test_new_notes_validate_schema_and_cli_recovers_them(self):
        import subprocess
        import jsonschema
        coach.save_answer(self.root, self.raw)
        path = Path(self.temp.name) / "reflection.json"
        path.write_text(coach.json_text(self.note(assistance="unassisted")), encoding="utf-8")
        command = [sys.executable, str(SKILL / "scripts/coach.py")]
        completed = subprocess.run(command + ["learning-note", str(path), "--data-root", str(self.root)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        completed = subprocess.run(command + ["coverage", "--data-root", str(self.root)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["answered_ungraded_count"], 1)
        schema = coach.read_json(SKILL / "schemas/learning-note.schema.json")
        for item in learning.load_notes(self.root, "demo-session"):
            jsonschema.validate(item, schema, format_checker=jsonschema.FormatChecker())

    def test_corpus_matches_independent_builder_and_schemas(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("dual_assets", SKILL.parent / "development/build_dual_track_assets.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        self.assertEqual(builder.build_cases(), coach.read_jsonl(SKILL / "training/dual-track-scenarios.jsonl"))
        for case in builder.build_cases():
            coach.validate_learning_context(case["learning_context"])
            self.assertEqual(case["synthetic_origin"], "independently-authored-fiction")


if __name__ == "__main__":
    unittest.main()
