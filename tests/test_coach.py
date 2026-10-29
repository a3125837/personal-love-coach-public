import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "personal-love-coach"
sys.path.insert(0, str(SKILL / "scripts"))
import coach
import build_eval


def answer(number=1, **updates):
    result = dict(id=f"answer-{number}", round_id="round-1", case_id=f"case-{number}",
                  relationship_id="simulation", date="2026-10-22", mode="training", rubric_version=coach.RUBRIC,
                  level=2, category="sharing", answer="虚构测试答复：看见薄荷新芽，我感到很惊喜。", attempt=1,
                  hint_used=False, critical_error=False, scores=dict(zip(coach.DIMENSIONS, (4, 4, 4, 3, 3))),
                  errors=[], action_planned=None, action_completed=None)
    result.update(updates)
    return result


class ScoreTests(unittest.TestCase):
    def test_twenty_point_scale(self):
        result = answer(scores={d: 4 for d in coach.DIMENSIONS})
        self.assertEqual(coach.evaluate_result(result), dict(total=20, maximum=20, passed=True, band="excellent"))

    def test_critical_error_veto_at_sixteen(self):
        result = answer(scores=dict(zip(coach.DIMENSIONS, (4, 0, 4, 4, 4))), critical_error=True,
                        critical_reason="在明确拒绝后仍要求见面")
        self.assertEqual(coach.evaluate_result(result)["total"], 16)
        self.assertFalse(coach.evaluate_result(result)["passed"])

    def test_threshold(self):
        self.assertFalse(coach.evaluate_result(answer(scores={d: 3 for d in coach.DIMENSIONS}))["passed"])
        self.assertTrue(coach.evaluate_result(answer(scores=dict(zip(coach.DIMENSIONS, (4, 3, 3, 3, 3)))))["passed"])

    def test_invalid_values_fail(self):
        for value in (-1, 5, 20, True, 3.0, "4", float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                result = answer()
                result["scores"]["evidence"] = value
                coach.evaluate_result(result)

    def test_missing_dimension_and_empty_answer(self):
        result = answer()
        del result["scores"]["evidence"]
        with self.assertRaises(ValueError):
            coach.evaluate_result(result)
        with self.assertRaises(ValueError):
            coach.evaluate_result(answer(answer="  "))

    def test_critical_requires_reason(self):
        with self.assertRaises(ValueError):
            coach.evaluate_result(answer(critical_error=True))


class ExamTests(unittest.TestCase):
    def six_answers(self):
        catalog = coach.load_catalog()
        return [answer(i, round_id=f"round-{1 if i <= 3 else 2}", mode="exam", case_id=f"PLC-{30+i:03}",
                       category=catalog[f"PLC-{30+i:03}"]["category"],
                       case_fingerprint=coach.case_fingerprint(catalog[f"PLC-{30+i:03}"]),
                       corpus_version=catalog[f"PLC-{30+i:03}"]["corpus_version"], record_origin="session") for i in range(1, 7)]

    def status(self, records, level):
        sessions = {}
        for index, key in enumerate(("round-1", "round-2"), 1):
            cases = [f"PLC-{n:03}" for n in range(31 if index == 1 else 34, 34 if index == 1 else 37)]
            sessions[key] = dict(id=key, mode="exam", state="completed", level=2, hint_used=False,
                                 case_ids=cases, answered_case_ids=cases, opened_sequence=index,
                                 case_bindings={case_id: coach.bind_case(coach.load_catalog()[case_id]) for case_id in cases})
        return coach.exam_status(records, level, sessions)

    def test_two_distinct_rounds_promote(self):
        self.assertTrue(self.status(self.six_answers(), 2)["promotion_eligible"])

    def test_one_round_does_not_promote(self):
        self.assertFalse(self.status(self.six_answers()[:3], 2)["promotion_eligible"])

    def test_hint_or_failed_answer_blocks(self):
        for update in (dict(hint_used=True), dict(scores={d: 1 for d in coach.DIMENSIONS}), dict(attempt=2)):
            rows = self.six_answers()
            rows[0].update(update)
            self.assertFalse(self.status(rows, 2)["promotion_eligible"])

    def test_repeated_case_blocks(self):
        rows = self.six_answers()
        rows[3]["case_id"] = rows[0]["case_id"]
        self.assertFalse(self.status(rows, 2)["promotion_eligible"])

    def test_prior_training_blocks_even_same_date(self):
        rows = self.six_answers()
        previous = answer(99, mode="training", case_id=rows[0]["case_id"], round_id="old")
        self.assertFalse(self.status([previous] + rows, 2)["promotion_eligible"])

    def test_wrong_level_or_incomplete_round_blocks(self):
        rows = self.six_answers()
        rows[0]["level"] = 1
        self.assertFalse(self.status(rows, 2)["promotion_eligible"])
        self.assertFalse(self.status(self.six_answers()[:-1], 2)["promotion_eligible"])

    def test_max_level_does_not_promote(self):
        rows = self.six_answers()
        for row in rows:
            row["level"] = 6
        self.assertFalse(self.status(rows, 6)["promotion_eligible"])


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "data"

    def tearDown(self):
        self.temp.cleanup()

    def test_append_preserves_first_answer_and_rejects_duplicate(self):
        first = answer(mode="training")
        coach.import_result(self.root, first, "虚构历史导入")
        with self.assertRaises(ValueError):
            coach.import_result(self.root, first, "虚构历史导入")
        second = answer(2, mode="training", case_id=first["case_id"], attempt=2, answer="修改后的回答")
        coach.import_result(self.root, second, "虚构历史导入")
        history = coach.load_history(self.root)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["answer"], first["answer"])
        self.assertEqual(coach.progress_report(history)["comparable_groups"][0]["count"], 1)

    def test_duplicate_attempt_and_missing_prior_rejected(self):
        coach.import_result(self.root, answer(), "虚构历史导入")
        with self.assertRaises(ValueError):
            coach.import_result(self.root, answer(2, case_id="case-1"), "虚构历史导入")
        with self.assertRaises(ValueError):
            coach.import_result(self.root, answer(3, attempt=3), "虚构历史导入")

    def test_sequence_preserves_same_day_record_order(self):
        coach.import_result(self.root, answer(9, mode="training", case_id="case-1", round_id="practice"), "虚构历史导入")
        for i in range(1, 7):
            coach.import_result(self.root, answer(i, round_id=f"round-{1 if i <= 3 else 2}"), "虚构历史导入")
        rows = coach.load_history(self.root)
        self.assertEqual(rows[0]["id"], "answer-9")
        self.assertEqual([r["sequence"] for r in rows], list(range(1, 8)))
        self.assertFalse(coach.exam_status(rows, 2)["promotion_eligible"])

    def test_path_traversal_reserved_names_and_skill_root_rejected(self):
        for name in ("../escape", "..", "a/b", "a\\b", "CON", "nul", "C:drive"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                coach.identifier(name)
        with self.assertRaises(ValueError):
            coach.checked_path(SKILL, "data")

    def test_linked_storage_rejected_when_supported(self):
        self.root.mkdir()
        target = Path(self.temp.name) / "target"
        target.mkdir()
        try:
            (self.root / "profiles").symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("OS has not granted symlink creation")
        with self.assertRaises(ValueError):
            coach.checked_path(self.root, "profiles", "a.json")

    def test_lock_blocks_second_writer(self):
        with coach.data_lock(self.root):
            with self.assertRaises(ValueError):
                coach.append_result(self.root, answer())
        self.assertFalse((self.root / ".write.lock").exists())

    def test_separate_people_and_revision_archives(self):
        profile = coach.read_json(SKILL / "assets/relationship-profile.example.json")
        coach.save_profile(self.root, profile)
        other = copy.deepcopy(profile)
        other.update(id="example-b", alias="虚构B")
        coach.save_profile(self.root, other)
        revised = copy.deepcopy(profile)
        revised.update(revision=2, stage="R2", change_reason="新增交流事实")
        revised["stage_history"].append(dict(stage="R2", date="2026-10-22", evidence="双方多轮交流"))
        coach.save_profile(self.root, revised)
        self.assertEqual(coach.read_json(self.root / "profiles/example-b.json")["stage"], "R1")
        self.assertEqual(coach.read_json(self.root / "archive/example-a-r1.json")["stage"], "R1")
        with self.assertRaises(ValueError):
            coach.save_profile(self.root, revised)

    def test_session_pause_resume_and_preserve_answered_state(self):
        session = coach.read_json(SKILL / "assets/training-session.example.json")
        coach.save_session(self.root, session)
        coach.append_result(self.root, answer(case_id="PLC-004", category="empathy", round_id=session["id"]))
        session.update(revision=2, state="paused", answered_case_ids=["PLC-004"])
        coach.save_session(self.root, session)
        session.update(revision=3, state="awaiting_answers")
        coach.save_session(self.root, session)
        invalid = {**session, "revision": 4, "answered_case_ids": []}
        with self.assertRaises(ValueError):
            coach.save_session(self.root, invalid)
        self.assertEqual(coach.read_json(self.root / "sessions/demo-session.json")["answered_case_ids"], ["PLC-004"])

    def test_session_split_leak_and_early_completion_blocked(self):
        session = coach.read_json(SKILL / "assets/training-session.example.json")
        for updates in (dict(case_ids=["PLC-041", "PLC-005", "PLC-006"]),
                        dict(case_ids=["PLC-031", "PLC-005", "PLC-006"]), dict(state="completed")):
            with self.assertRaises(ValueError):
                coach.validate_session({**session, **updates})

    def test_hinted_exam_cannot_keep_exam_qualification(self):
        session = coach.read_json(SKILL / "assets/training-session.example.json")
        session.update(mode="exam", hint_used=True, case_ids=["PLC-031", "PLC-032", "PLC-033"])
        with self.assertRaises(ValueError):
            coach.validate_session(session)

    def test_exam_can_be_converted_to_practice_without_restoring_exam(self):
        session = coach.read_json(SKILL / "assets/training-session.example.json")
        session.update(mode="exam", case_ids=["PLC-031", "PLC-032", "PLC-033"])
        coach.save_session(self.root, session)
        session.update(revision=2, mode="training", converted_from_exam=True, hint_used=True)
        coach.save_session(self.root, session)
        self.assertEqual(coach.read_json(self.root / "sessions/demo-session.json")["mode"], "training")
        session.update(revision=3, mode="exam", converted_from_exam=False, hint_used=False)
        with self.assertRaises(ValueError):
            coach.save_session(self.root, session)


class ProgressTests(unittest.TestCase):
    def test_empty_is_not_fake_progress(self):
        self.assertEqual(coach.progress_report([])["comparable_groups"], [])

    def test_difficulties_modes_and_categories_separated(self):
        rows = [answer(1, level=1), answer(2, level=4), answer(3, level=1, category="humor"),
                answer(4, level=1, mode="exam")]
        self.assertEqual(len(coach.progress_report(rows)["comparable_groups"]), 4)

    def test_independent_and_action_denominators(self):
        rows = [answer(1, action_planned=True, action_completed=True),
                answer(2, hint_used=True, action_planned=True, action_completed=False),
                answer(3, action_planned=True, action_completed=None)]
        group = coach.progress_report(rows)["comparable_groups"][0]
        self.assertEqual(group["independent_answer_rate"], 2 / 3)
        self.assertEqual(group["independent_pass_rate"], 1)
        self.assertEqual(group["action_completion_rate"], 0.5)
        self.assertEqual(group["actions_with_unknown_outcome"], 1)

    def test_unknown_versions_and_corrupt_totals_rejected(self):
        for result in (answer(rubric_version="rubric-2"), answer(total=100)):
            with self.assertRaises(ValueError):
                coach.progress_report([result])


class PackagingAndEvalTests(unittest.TestCase):
    def test_fifty_cases_and_module_coverage(self):
        self.assertEqual(coach.validate_package()["case_counts"], dict(training=60, exam=42, holdout=10))

    def test_schema_examples_and_saved_result(self):
        import jsonschema
        for stem in ("training-result", "relationship-profile", "training-session", "raw-answer"):
            schema = coach.read_json(SKILL / f"schemas/{stem}.schema.json")
            jsonschema.Draft202012Validator.check_schema(schema)
            value = coach.read_json(SKILL / f"assets/{stem}.example.json")
            jsonschema.validate(value, schema, format_checker=jsonschema.FormatChecker())
        with tempfile.TemporaryDirectory() as directory:
            s = coach.read_json(SKILL / "assets/training-session.example.json")
            coach.save_session(directory, s)
            coach.append_result(directory, answer(case_id="PLC-004", category="empathy", round_id=s["id"]))
            saved = coach.load_history(directory)[0]
            jsonschema.validate(saved, coach.read_json(SKILL / "schemas/training-result.schema.json"),
                                format_checker=jsonschema.FormatChecker())
        with tempfile.TemporaryDirectory() as directory:
            coach.save_session(directory, coach.read_json(SKILL / "assets/training-session.example.json"))
            saved_session = coach.load_sessions(directory)["demo-session"]
            jsonschema.validate(saved_session, coach.read_json(SKILL / "schemas/training-session.schema.json"),
                                format_checker=jsonschema.FormatChecker())

    def test_expected_answers_not_in_candidate_prompt(self):
        config = build_eval.build("openai:test-target", "openai:test-judge")
        self.assertEqual(len(config["tests"]), 10)
        for test in config["tests"]:
            self.assertNotIn("expected", test["vars"])
            self.assertNotIn("failures", test["vars"])
            self.assertEqual(len(test["assert"]), 2)
            self.assertNotIn("expected_mode", config["prompts"][0])

    def test_live_requires_explicit_target_and_judge(self):
        with self.assertRaises(ValueError):
            build_eval.build("openai:target")

    def test_cli_review_dates_does_not_create_reminder(self):
        run = subprocess.run([sys.executable, str(SKILL / "scripts/coach.py"), "review-dates", "--from-date", "2026-10-22"],
                             capture_output=True, text=True, check=True)
        output = json.loads(run.stdout)
        self.assertEqual(output["review_dates"], ["2026-10-25", "2026-10-29", "2026-11-05"])
        self.assertFalse(output["reminder_created"])


if __name__ == "__main__":
    unittest.main()
