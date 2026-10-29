"""Regression tests from independent forward testing of the complete workflow."""
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


def session(key="exam-a", cases=None, **updates):
    record = dict(id=key, revision=1, mode="exam", state="awaiting_answers", level=2,
                  rubric_version=coach.RUBRIC, hint_used=False, updated_at="2026-10-22",
                  case_ids=cases or ["PLC-031", "PLC-032", "PLC-033"], answered_case_ids=[])
    record.update(updates)
    return record


def result(case_id="PLC-031", round_id="exam-a", **updates):
    cases = [*coach.read_jsonl(SKILL / "training/scenarios.jsonl"), *coach.read_jsonl(SKILL / "training/exams.jsonl")]
    case = next(c for c in cases if c["id"] == case_id)
    record = dict(id=f"answer-{round_id}-{case_id}", round_id=round_id, case_id=case_id,
                  relationship_id="simulation", date="2026-10-22", mode="exam", rubric_version=coach.RUBRIC,
                  level=case["level"], category=case["category"], answer="这是虚构的独立测试回答。",
                  attempt=1, hint_used=False, critical_error=False, scores={d: 4 for d in coach.DIMENSIONS})
    record.update(updates)
    return record


class WorkflowIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "data"

    def tearDown(self):
        self.temp.cleanup()

    def test_exam_record_requires_existing_session(self):
        with self.assertRaises(ValueError):
            coach.append_result(self.root, result())

    def test_training_case_cannot_be_saved_as_exam(self):
        with self.assertRaises(ValueError):
            coach.append_result(self.root, result("PLC-004"))

    def test_catalog_level_is_authoritative_for_session(self):
        with self.assertRaises(ValueError):
            coach.save_session(self.root, session(level=5))

    def test_hinted_exam_state_cannot_be_overridden_by_result_flags(self):
        original = session()
        coach.save_session(self.root, original)
        coach.save_session(self.root, {**original, "revision": 2, "mode": "training",
                                      "converted_from_exam": True, "hint_used": True})
        with self.assertRaises(ValueError):
            coach.append_result(self.root, result())

    def test_completed_round_requires_actual_answers(self):
        original = session()
        coach.save_session(self.root, original)
        with self.assertRaises(ValueError):
            coach.save_session(self.root, {**original, "revision": 2, "state": "completed",
                                          "answered_case_ids": original["case_ids"]})

    def test_known_case_category_cannot_drift(self):
        with self.assertRaises(ValueError):
            coach.append_result(self.root, result("PLC-004", mode="training", category="invented"))

    def test_profile_retry_after_archiving_interruption(self):
        original = coach.read_json(SKILL / "assets/relationship-profile.example.json")
        coach.save_profile(self.root, original)
        updated = {**original, "revision": 2, "change_reason": "测试新增安排", "next_action": "下一次自然问候"}
        writer = coach.atomic_json
        def interrupted(path, value):
            if path.parent.name == "profiles":
                raise OSError("fault injected after archive")
            return writer(path, value)
        with patch.object(coach, "atomic_json", interrupted):
            with self.assertRaises(OSError):
                coach.save_profile(self.root, updated)
        # A retry must recognise an identical archive, preserve it, and commit the new profile.
        coach.save_profile(self.root, updated)
        self.assertEqual(coach.read_json(self.root / "profiles/example-a.json")["revision"], 2)
        self.assertEqual(coach.read_json(self.root / "archive/example-a-r1.json"), original)

    def test_session_retry_after_archiving_interruption(self):
        original = session()
        coach.save_session(self.root, original)
        updated = {**original, "revision": 2, "state": "paused"}
        writer = coach.atomic_json
        def interrupted(path, value):
            if path.parent.name == "sessions":
                raise OSError("fault injected after archive")
            return writer(path, value)
        with patch.object(coach, "atomic_json", interrupted):
            with self.assertRaises(OSError):
                coach.save_session(self.root, updated)
        coach.save_session(self.root, updated)
        self.assertEqual(coach.read_json(self.root / "sessions/exam-a.json")["state"], "paused")

    def test_cli_two_real_rounds_support_promotion(self):
        for key, start in (("round-one", 31), ("round-two", 34)):
            cases = [f"PLC-{n:03}" for n in range(start, start + 3)]
            original = session(key, cases)
            coach.save_session(self.root, original)
            for case_id in cases:
                coach.append_result(self.root, result(case_id, key))
            coach.save_session(self.root, {**original, "revision": 2, "state": "completed", "answered_case_ids": cases})
        import subprocess
        run = subprocess.run([sys.executable, str(SKILL / "scripts/coach.py"), "exam-status", "--level", "2",
                              "--data-root", str(self.root)], capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(run.stdout)["promotion_eligible"])

    def test_exam_raw_answer_survives_restart_before_scoring(self):
        import subprocess
        original = session()
        coach.save_session(self.root, original)
        payload = {"round_id": original["id"], "case_id": "PLC-031", "answer": "虚构测试答复：台灯重新亮起来了，真不错。",
                   "date": "2026-10-22", "hint_used": False}
        source = Path(self.temp.name) / "raw-answer.json"
        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        run = subprocess.run([sys.executable, str(SKILL / "scripts/coach.py"), "answer", str(source), "--data-root", str(self.root)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        resumed = subprocess.run([sys.executable, str(SKILL / "scripts/coach.py"), "show-session", original["id"], "--data-root", str(self.root)],
                                 capture_output=True, text=True)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        restored = json.loads(resumed.stdout)
        self.assertEqual(restored["answers"][0]["answer"], payload["answer"])
        self.assertEqual(restored["results"], [])
        self.assertEqual(restored["remaining_case_ids"], ["PLC-032", "PLC-033"])

    def test_grade_cannot_rewrite_a_saved_first_answer(self):
        coach.save_session(self.root, session())
        directory = self.root / "answers/exam-a"
        directory.mkdir(parents=True)
        payload = {"round_id": "exam-a", "case_id": "PLC-031", "answer": "首次原答", "date": "2026-10-22", "hint_used": False}
        (directory / "PLC-031.json").write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            coach.append_result(self.root, result(answer="修改后伪装首次回答"))

    def test_custom_cases_register_prompt_and_level_before_use(self):
        identifiers = []
        for index in range(3):
            case = dict(id=f"CUSTOM-{index}", split="exam", source_type="synthetic", level=4, category="dating",
                        input=f"原创虚构线下场景{index}：如何回应这一次共同活动的提议？", facts=["双方已同意见面"],
                        unknowns=["对方活动偏好"], expected=["结合真实安排回应"], failures=["编造已经买票"])
            coach.register_case(self.root, case)
            identifiers.append(case["id"])
        coach.save_session(self.root, session("custom-round", identifiers, level=4))
        restored = coach.load_sessions(self.root)["custom-round"]
        self.assertEqual(restored["case_ids"], identifiers)
        with self.assertRaises(ValueError):
            coach.register_case(self.root, {**case, "id": "NEW-ID"})

    def test_unregistered_session_cannot_invent_difficulty(self):
        with self.assertRaises(ValueError):
            coach.save_session(self.root, session(cases=["UNKNOWN-1", "UNKNOWN-2", "UNKNOWN-3"]))

    def test_repeated_case_is_not_unseen_transfer(self):
        first = result("PLC-004", round_id="practice-a", mode="training")
        repeated = {**first, "id": "repeated", "round_id": "practice-b"}
        report = coach.progress_report([first, repeated])
        group = report["comparable_groups"][0]
        self.assertEqual(group["independent_answer_rate"], 1)
        self.assertEqual(group["unseen_independent_count"], 1)
        self.assertEqual(group["repeat_case_count"], 1)

    def test_hints_later_in_session_invalidate_existing_exam_records(self):
        original = session()
        coach.save_session(self.root, original)
        coach.append_result(self.root, result())
        coach.save_session(self.root, {**original, "revision": 2, "mode": "training", "converted_from_exam": True,
                                      "hint_used": True, "answered_case_ids": ["PLC-031"]})
        report = coach.progress_report(coach.load_history(self.root), coach.load_sessions(self.root))
        group = report["comparable_groups"][0]
        self.assertEqual(group["mode"], "training")
        self.assertEqual(group["independent_answer_rate"], 0)
        self.assertFalse(coach.exam_status(coach.load_history(self.root), 2, coach.load_sessions(self.root))["promotion_eligible"])

    def test_exam_raw_hint_requires_conversion_before_saving(self):
        coach.save_session(self.root, session())
        with self.assertRaises(ValueError):
            coach.save_answer(self.root, dict(round_id="exam-a", case_id="PLC-031", answer="提示后的回答",
                                             date="2026-10-22", hint_used=True))

    def test_grade_cannot_erase_a_raw_answer_hint(self):
        coach.save_session(self.root, session())
        directory = self.root / "answers/exam-a"
        directory.mkdir(parents=True)
        payload = dict(round_id="exam-a", case_id="PLC-031", answer="提示后的回答", date="2026-10-22", hint_used=True)
        (directory / "PLC-031.json").write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            coach.append_result(self.root, result(answer=payload["answer"], hint_used=False))

    def test_resumed_exam_includes_question_prompts_but_not_answer_rubrics(self):
        coach.save_session(self.root, session())
        resumed = coach.show_session(self.root, "exam-a")
        self.assertEqual(len(resumed.get("questions", [])), 3)
        for question in resumed.get("questions", []):
            self.assertTrue(question["input"])
            self.assertNotIn("expected", question)
            self.assertNotIn("failures", question)


if __name__ == "__main__":
    unittest.main()
