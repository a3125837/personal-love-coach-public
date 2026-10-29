"""Learner prompt isolation and task constraints, independent of advice wording."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "personal-love-coach/scripts"))
import coach
import build_eval


class QuestionPresentationTests(unittest.TestCase):
    def setUp(self):
        self.case = copy.deepcopy(coach.load_catalog()["ES-002"])

    def test_internal_data_cannot_leak_by_adding_fields(self):
        self.case.update(expected=["SECRET-RUBRIC"], facts=["SECRET-FACT"],
                         future_internal_analysis="SECRET-FUTURE", relationship_phase="P2")
        for task in ("expression", "judgment", "information", "adaptation"):
            prompt = coach.present_question(self.case, task)
            self.assertEqual(set(prompt), {"id", "input", "task", "instruction"})
            self.assertEqual(prompt["input"], self.case["input"])
            self.assertNotIn("SECRET", json.dumps(prompt))
        self.assertEqual(self.case["expected"], ["SECRET-RUBRIC"])

    def test_phase_disclosure_is_explicit_and_expression_only(self):
        self.assertEqual(coach.present_question(self.case, include_phase=True)["relationship_phase"], "P2")
        for task in ("judgment", "information", "adaptation"):
            with self.assertRaises(ValueError):
                coach.present_question(self.case, task, True)

    def test_training_helper_rejects_exam_and_holdout(self):
        for split in ("exam", "holdout"):
            with self.assertRaises(ValueError):
                coach.present_question({**self.case, "split": split})

    def test_invalid_task_fails_closed(self):
        with self.assertRaises(ValueError):
            coach.present_question(self.case, "show-rubric")

    def test_cli_has_safe_default_and_rejects_disclosure(self):
        command = [sys.executable, str(coach.ROOT / "scripts/coach.py"), "question", "ES-002"]
        run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn("relationship_phase", json.loads(run.stdout))
        denied = subprocess.run(command + ["--task", "judgment", "--include-phase"], capture_output=True)
        self.assertNotEqual(denied.returncode, 0)

    def test_behavior_suite_requires_real_provider_and_separates_judge_rubric(self):
        with self.assertRaises(ValueError):
            build_eval.build(suite="behavior")
        config = build_eval.build("candidate-model", "judge-model", suite="behavior")
        self.assertEqual(len(config["tests"]), 16)
        for test in config["tests"]:
            self.assertNotIn("expected", test["vars"])
            self.assertEqual(test["assert"][-1]["type"], "llm-rubric")


if __name__ == "__main__":
    unittest.main()
