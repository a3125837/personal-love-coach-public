"""Independent synthetic regressions for the self-audit findings and compatibility."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1] / "personal-love-coach"
sys.path.insert(0, str(SKILL / "scripts"))
import coach


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "data"
        self.session = coach.read_json(SKILL / "assets/training-session.example.json")
        coach.save_session(self.root, self.session)
        self.answer = dict(round_id=self.session["id"], case_id="PLC-004", answer="又出故障确实扫兴。",
                           date="2026-10-28", hint_used=False)

    def tearDown(self):
        self.temp.cleanup()

    def grade(self):
        return dict(id="grade-one", **self.answer, relationship_id="simulation", mode="training",
                    rubric_version=coach.RUBRIC, level=2, category="empathy", attempt=1,
                    critical_error=False, scores={d: 4 for d in coach.DIMENSIONS})

    def test_duplicate_answer_rejects_changed_metadata(self):
        coach.save_answer(self.root, self.answer)
        with self.assertRaises(ValueError):
            coach.save_answer(self.root, {**self.answer, "hint_used": True})
        self.assertFalse(coach.load_answers(self.root, self.session["id"])[0]["hint_used"])

    def test_hint_correction_preserves_raw_and_grade_but_changes_effective_statistics(self):
        coach.append_result(self.root, self.grade())
        raw = self.root / "answers/demo-session/PLC-004.json"
        grade = self.root / "training-history/grade-one.json"
        before = (raw.read_bytes(), grade.read_bytes())
        correction = dict(round_id="demo-session", case_id="PLC-004", date="2026-10-28",
                          reason="补正：首答前已得到提示", hint_used=True)
        coach.correct_hint(self.root, correction)
        coach.correct_hint(self.root, correction)
        self.assertEqual(before, (raw.read_bytes(), grade.read_bytes()))
        self.assertTrue(coach.load_answers(self.root, "demo-session")[0]["hint_used"])
        report = coach.progress_report(coach.load_history(self.root), coach.load_sessions(self.root))
        self.assertEqual(report["comparable_groups"][0]["independent_answer_rate"], 0)
        with self.assertRaises(ValueError):
            coach.correct_hint(self.root, {**correction, "hint_used": False})

    def test_changed_or_deleted_catalog_restores_snapshot_and_blocks_new_grades(self):
        coach.save_answer(self.root, self.answer)
        catalog = coach.load_catalog()
        old_input = catalog["PLC-004"]["input"]
        catalog["PLC-004"] = {**catalog["PLC-004"], "input": "这是同题号的新题干"}
        with patch.object(coach, "load_catalog", return_value=catalog):
            restored = coach.show_session(self.root, "demo-session")
            self.assertEqual(restored["questions"][0]["input"], old_input)
            self.assertIn("PLC-004", restored["changed_case_ids"])
            with self.assertRaises(ValueError):
                coach.append_result(self.root, self.grade())
        del catalog["PLC-004"]
        with patch.object(coach, "load_catalog", return_value=catalog):
            self.assertEqual(coach.show_session(self.root, "demo-session")["questions"][0]["input"], old_input)

    def test_restore_remembers_judgment_task_without_phase(self):
        s = {**self.session, "id": "judgment-round", "question_settings": {
            key: {"task": "judgment", "include_phase": False} for key in self.session["case_ids"]}}
        coach.save_session(self.root, s)
        restored = coach.show_session(self.root, s["id"])
        for question in restored["questions"]:
            self.assertEqual(question["task"], "judgment")
            self.assertNotIn("relationship_phase", question)
        self.assertNotIn("case_bindings", restored["session"])
        with self.assertRaises(ValueError):
            coach.save_session(self.root, {**s, "revision": 2, "question_settings": {
                key: {"task": "expression", "include_phase": False} for key in s["case_ids"]}})

    def test_new_training_needs_session_and_registered_case(self):
        with self.assertRaises(ValueError):
            coach.append_result(self.root, {**self.grade(), "round_id": "unopened"})
        with self.assertRaises(ValueError):
            coach.append_result(self.root, {**self.grade(), "case_id": "unregistered"})

    def test_legacy_import_remains_visible_but_not_verified_training(self):
        record = {**self.grade(), "round_id": "old-round", "case_id": "old-case"}
        coach.import_result(self.root, record, "独立虚构的历史导入测试")
        rows = coach.load_history(self.root)
        self.assertEqual(rows[0]["record_origin"], "legacy-import")
        group = coach.progress_report(rows)["comparable_groups"][0]
        self.assertEqual(group["corpus_version"], "unknown")
        self.assertFalse(group["verified_training"])

    def test_legacy_session_read_does_not_invent_snapshot(self):
        path = self.root / "sessions/demo-session.json"
        legacy = coach.read_json(path)
        legacy.pop("case_bindings", None)
        legacy.pop("question_settings", None)
        path.write_text(coach.json_text(legacy), encoding="utf-8")
        restored = coach.show_session(self.root, "demo-session")
        self.assertEqual(restored["binding_status"], "legacy-unverified")
        self.assertNotIn("case_bindings", coach.read_json(path))
        with self.assertRaises(ValueError):
            coach.save_answer(self.root, self.answer)

    def test_progress_separates_content_versions(self):
        a = {**self.grade(), "corpus_version": "fiction-a", "case_fingerprint": "a" * 64}
        b = {**a, "id": "grade-two", "round_id": "other", "corpus_version": "fiction-b", "case_fingerprint": "b" * 64}
        self.assertEqual(len(coach.progress_report([a, b])["comparable_groups"]), 2)

    def test_training_catalog_does_not_read_builtin_exams_or_holdout(self):
        reader = coach.read_jsonl
        seen = []
        def tracked(path):
            seen.append(Path(path).name)
            return reader(path)
        with patch.object(coach, "read_jsonl", side_effect=tracked):
            cases = coach.load_catalog(splits=("training",))
        self.assertTrue(cases)
        self.assertNotIn("exams.jsonl", seen)
        self.assertNotIn("holdout.jsonl", seen)
        self.assertTrue(all(c["split"] == "training" for c in cases.values()))

    def test_review_metadata_does_not_invalidate_content(self):
        case = coach.load_catalog()["PLC-004"]
        changed = {**case, "review_status": "reviewed-again", "authored_at": "2026-10-29"}
        self.assertEqual(coach.case_fingerprint(case), coach.case_fingerprint(changed))
        self.assertNotEqual(coach.case_fingerprint(case), coach.case_fingerprint({**case, "expected": ["另一评价条件"]}))

    def test_new_custom_cases_are_partitioned_by_split(self):
        base = dict(source_type="synthetic", level=1, category="sharing", unknowns=[], expected=["自然表达"], failures=["虚构身份"])
        for split in ("training", "exam"):
            coach.register_case(self.root, dict(base, id="CUSTOM-" + split, split=split,
                input="独立虚构的分区测试场景：" + split, facts=["各自不同的题干"]))
        self.assertTrue((self.root / "cases/exam/CUSTOM-exam.json").exists())
        original = coach.read_json
        seen = []
        def tracked(path):
            seen.append(str(path).replace("\\", "/"))
            return original(path)
        with patch.object(coach, "read_json", side_effect=tracked):
            catalog = coach.load_catalog(self.root, splits=("training",))
        self.assertIn("CUSTOM-training", catalog)
        self.assertFalse(any("cases/exam/" in path for path in seen))

    def test_exam_turns_are_blocked(self):
        catalog = coach.load_catalog(splits=("exam",))
        keys = [key for key, c in catalog.items() if c["level"] == 2][:3]
        s = {**self.session, "id": "exam-only", "mode": "exam", "case_ids": keys}
        coach.save_session(self.root, s)
        coach.save_answer(self.root, {**self.answer, "round_id": s["id"], "case_id": keys[0]})
        with self.assertRaises(ValueError):
            coach.save_turn(self.root, dict(round_id=s["id"], case_id=keys[0], turn=1, role="assistant",
                text="模拟接续", date="2026-10-28", simulation=True))

    def test_old_unbound_results_read_without_migration(self):
        directory = self.root / "training-history"
        directory.mkdir()
        legacy = {**self.grade(), "round_id": "legacy-round"}
        path = directory / "grade-one.json"
        path.write_text(coach.json_text(legacy), encoding="utf-8")
        before = path.read_bytes()
        rows = coach.load_history(self.root)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(coach.progress_report(rows)["comparable_groups"][0]["corpus_version"], "unknown")

    def test_corrected_exam_cannot_qualify_for_promotion(self):
        catalog = coach.load_catalog(splits=("exam",))
        keys = [key for key, c in catalog.items() if c["level"] == 2][:3]
        s = {**self.session, "id": "exam-corrected", "mode": "exam", "case_ids": keys}
        coach.save_session(self.root, s)
        for i, key in enumerate(keys):
            c = catalog[key]
            coach.append_result(self.root, {**self.grade(), "id": f"exam-grade-{i}", "round_id": s["id"],
                "case_id": key, "category": c["category"], "mode": "exam"})
        coach.save_session(self.root, {**s, "revision": 2, "state": "completed", "answered_case_ids": keys})
        coach.correct_hint(self.root, dict(round_id=s["id"], case_id=keys[0], date="2026-10-28", reason="补正已遗漏的考前提示", hint_used=True))
        status = coach.exam_status(coach.load_history(self.root), 2, coach.load_sessions(self.root))
        self.assertNotIn(s["id"], status["eligible_rounds"])

    def test_full_two_round_path_exists_at_every_level(self):
        catalog = coach.load_catalog(splits=("training", "exam"))
        for level in range(7):
            with self.subTest(level=level):
                self.assertGreaterEqual(sum(c["level"] == level and c["split"] == "training" for c in catalog.values()), 3)
                keys = [key for key, c in catalog.items() if c["level"] == level and c["split"] == "exam"]
                self.assertEqual(len(keys), 6)
                root = Path(self.temp.name) / f"level-{level}"
                for index in range(2):
                    selected = keys[index * 3:index * 3 + 3]
                    s = {**self.session, "id": f"exam-{index}", "level": level, "mode": "exam", "case_ids": selected}
                    coach.save_session(root, s)
                    for key in selected:
                        c = catalog[key]
                        coach.append_result(root, {**self.grade(), "id": f"grade-{key}", "round_id": s["id"],
                            "case_id": key, "category": c["category"], "level": level, "mode": "exam"})
                    coach.save_session(root, {**s, "revision": 2, "state": "completed", "answered_case_ids": selected})
                status = coach.exam_status(coach.load_history(root), level, coach.load_sessions(root))
                self.assertEqual(len(status["eligible_rounds"]), 2)
                self.assertEqual(status["promotion_eligible"], level < 6)

    def test_expanded_corpus_matches_its_fictional_builder(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("expanded_builder", SKILL.parent / "development/build_expanded_corpus.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        for filename, rows in zip(("expanded-scenarios.jsonl", "expanded-exams.jsonl"), builder.build()):
            self.assertEqual(rows, coach.read_jsonl(SKILL / "training" / filename))
            self.assertTrue(all(c["synthetic_origin"] == "independently-authored-fiction" for c in rows))

    def test_cli_hint_and_followup_workflow_and_all_saved_schemas(self):
        import subprocess
        import jsonschema
        def run(command, *args):
            completed = subprocess.run([sys.executable, str(SKILL / "scripts/coach.py"), command,
                *map(str, args), "--data-root", str(self.root)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)
        def input_file(name, value):
            path = Path(self.temp.name) / (name + ".json")
            path.write_text(coach.json_text(value), encoding="utf-8")
            return path
        run("answer", input_file("answer", self.answer))
        run("record", input_file("grade", self.grade()))
        correction = dict(round_id="demo-session", case_id="PLC-004", date="2026-10-28", reason="虚构补正", hint_used=True)
        run("correct-hint", input_file("hint", correction))
        turn = dict(round_id="demo-session", case_id="PLC-004", turn=1, role="assistant", text="虚构反馈", date="2026-10-28", simulation=True)
        run("turn", input_file("turn", turn))
        output = run("show-session", "demo-session")
        self.assertEqual(len(output["practice_turns"]), 1)
        self.assertTrue(output["results"][0]["hint_used"])
        values = {"training-session": coach.load_sessions(self.root)["demo-session"],
                  "training-result": output["results"][0], "raw-answer": output["answers"][0],
                  "hint-correction": correction, "practice-turn": turn}
        for name, value in values.items():
            jsonschema.validate(value, coach.read_json(SKILL / f"schemas/{name}.schema.json"), format_checker=jsonschema.FormatChecker())

    def test_training_storage_path_never_reads_builtin_exam_text(self):
        seen = []
        original = coach.read_jsonl
        def tracked(path):
            seen.append(Path(path).name)
            return original(path)
        with patch.object(coach, "read_jsonl", side_effect=tracked):
            coach.save_answer(self.root, self.answer)
            coach.append_result(self.root, self.grade())
            coach.show_session(self.root, "demo-session")
        self.assertNotIn("exams.jsonl", seen)
        self.assertNotIn("expanded-exams.jsonl", seen)
        self.assertNotIn("holdout.jsonl", seen)

    def test_interrupted_hint_correction_can_retry_without_changing_originals(self):
        coach.append_result(self.root, self.grade())
        correction = dict(round_id="demo-session", case_id="PLC-004", date="2026-10-28", reason="虚构补正重试", hint_used=True)
        original = coach.atomic_json
        def interrupted(path, value):
            if "hint-corrections" in path.parts:
                raise OSError("simulated interrupted write")
            return original(path, value)
        with patch.object(coach, "atomic_json", side_effect=interrupted), self.assertRaises(OSError):
            coach.correct_hint(self.root, correction)
        self.assertFalse(coach.load_answers(self.root, "demo-session")[0]["hint_used"])
        coach.correct_hint(self.root, correction)
        self.assertTrue(coach.load_answers(self.root, "demo-session")[0]["hint_used"])

    def test_mismatched_result_version_and_legacy_exam_never_promote(self):
        catalog = coach.load_catalog(splits=("exam",))
        keys = [key for key, c in catalog.items() if c["level"] == 2][:3]
        s = {**self.session, "id": "bound-exam", "mode": "exam", "case_ids": keys}
        coach.save_session(self.root, s)
        for key in keys:
            coach.append_result(self.root, {**self.grade(), "id": "exam-" + key, "round_id": s["id"],
                "case_id": key, "category": catalog[key]["category"], "mode": "exam"})
        coach.save_session(self.root, {**s, "revision": 2, "state": "completed", "answered_case_ids": keys})
        rows = coach.load_history(self.root)
        rows[0]["corpus_version"] = "another-version"
        sessions = coach.load_sessions(self.root)
        self.assertNotIn(s["id"], coach.exam_status(rows, 2, sessions)["eligible_rounds"])
        sessions[s["id"]].pop("case_bindings")
        self.assertNotIn(s["id"], coach.exam_status(rows, 2, sessions)["eligible_rounds"])

    def test_practice_turns_survive_restore_without_modifying_first_answer(self):
        coach.save_answer(self.root, self.answer)
        turn = dict(round_id="demo-session", case_id="PLC-004", turn=1, role="assistant",
                    text="虚构接续：我今天想先歇会。", date="2026-10-28", simulation=True)
        coach.save_turn(self.root, turn)
        coach.save_turn(self.root, turn)
        coach.save_turn(self.root, {**turn, "turn": 2, "role": "user", "text": "好，你先休息。"})
        with self.assertRaises(ValueError):
            coach.save_turn(self.root, {**turn, "turn": 4})
        restored = coach.show_session(self.root, "demo-session")
        self.assertEqual(len(restored["practice_turns"]), 2)
        self.assertEqual(restored["answers"][0]["answer"], self.answer["answer"])
        self.assertEqual(restored["results"], [])


if __name__ == "__main__":
    unittest.main()
