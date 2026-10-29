"""Local, offline storage and arithmetic for Personal Love Coach (Python 3.10+)."""
from __future__ import annotations

import argparse
import hashlib
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import statistics
import sys
sys.modules.setdefault("coach", sys.modules[__name__])

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ("naturalness", "boundaries", "evidence", "interaction", "progression")
RUBRIC = "rubric-3.0"
RELATIONSHIP_PHASES = ("unknown", *(f"P{i}" for i in range(1, 9)))
COMMUNICATION_FUNCTIONS = ("share", "vent", "play", "praise", "question", "invite", "request", "unknown")
SIGNAL_CLARITY = ("explicit", "ambiguous", "mixed", "unknown")
IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier(value):
    require(isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None,
            "ID must use 1-64 ASCII letters/digits/hyphens/underscores")
    require(value.upper() not in RESERVED, "Reserved Windows filename")
    return value


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path):
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def load_catalog(root=None, splits=None):
    splits = tuple(splits) if splits is not None else ("training", "exam", "holdout")
    require(set(splits) <= {"training", "exam", "holdout"}, "Unknown catalog split")
    groups = {"training": ["training/scenarios.jsonl", "training/eight-stage-scenarios.jsonl", "training/expanded-scenarios.jsonl", "training/dual-track-scenarios.jsonl"],
              "exam": ["training/exams.jsonl", "training/expanded-exams.jsonl"], "holdout": ["evaluation/holdout.jsonl"]}
    paths = [ROOT / path for split in splits for path in groups[split] if (ROOT / path).exists()]
    cases = {case["id"]: case for path in paths for case in read_jsonl(path)}
    if root is not None:
        directory = checked_path(root, "cases")
        if directory.exists():
            custom_paths = list(directory.glob("*.json"))  # Legacy flat layout stays readable.
            for split in splits:
                split_dir = checked_path(root, "cases", split)
                custom_paths.extend(split_dir.glob("*.json"))
            for path in sorted(custom_paths):
                checked_path(root, *path.relative_to(Path(root).absolute()).parts)
                case = read_json(path)
                validate_case(case)
                require(path.stem == case["id"], "Case identity conflicts with filename")
                if case["split"] in splits:
                    require(case["id"] not in cases, "Case identity conflicts with catalog")
                    cases[case["id"]] = case
    return cases


def validate_case(case):
    require(isinstance(case, dict), "Case must be an object")
    identifier(case.get("id"))
    require(case.get("split") in ("training", "exam"), "Custom cases must be training or exam")
    require(case.get("source_type") == "synthetic", "Register independently fictional synthetic cases only")
    require(type(case.get("level")) is int and 0 <= case["level"] <= 6, "Invalid case level")
    require(isinstance(case.get("category"), str) and case["category"].strip(), "Missing case category")
    require(isinstance(case.get("input"), str) and case["input"].strip(), "Custom case must preserve the actual prompt")
    for field in ("facts", "unknowns", "expected", "failures"):
        require(isinstance(case.get(field), list) and all(isinstance(x, str) and x.strip() for x in case[field]),
                "Case needs a string list: " + field)
    require(case["facts"] and case["expected"] and case["failures"], "Incomplete custom case rubric")
    if "relationship_phase" in case:
        require(case["relationship_phase"] in RELATIONSHIP_PHASES, "Invalid custom relationship phase")
    if "synthetic_origin" in case:
        require(case["synthetic_origin"] == "independently-authored-fiction", "Custom content must be independently fictional")
    if "learning_context" in case:
        validate_learning_context(case["learning_context"])
    return case


def register_case(root, case):
    validate_case(case)
    with data_lock(root) as root:
        catalog = load_catalog(root)
        require(case["id"] not in catalog, "Case IDs are immutable; select a new ID")
        fingerprint = re.sub(r"\s+", "", case["input"])
        require(not any(re.sub(r"\s+", "", old["input"]) == fingerprint for old in catalog.values()),
                "Reusing an existing prompt under a new ID is not an unseen case")
        target = checked_path(root, "cases", case["split"], case["id"] + ".json")
        require(not target.exists(), "Case filename already exists")
        atomic_json(target, case)
    return {"saved": str(target), "case_id": case["id"]}


def validate_learning_context(context):
    require(isinstance(context, dict) and set(context) == {"communication_function", "signal_clarity"} and
            context["communication_function"] in COMMUNICATION_FUNCTIONS and context["signal_clarity"] in SIGNAL_CLARITY,
            "Invalid learning context")


def case_fingerprint(case):
    fields = ("id", "split", "level", "category", "mode", "input", "facts", "unknowns", "expected", "failures",
              "stage", "relationship_phase", "corpus_version", "learning_context")
    content = {key: case[key] for key in fields if key in case}
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode("utf-8")).hexdigest()


def bind_case(case):
    return {**{key: case[key] for key in ("id", "input", "level", "category", "split")},
            "relationship_phase": case.get("relationship_phase", "unknown"),
            "corpus_version": case.get("corpus_version", "custom-" + case_fingerprint(case)),
            "fingerprint": case_fingerprint(case),
            **({"learning_context": case["learning_context"]} if "learning_context" in case else {})}


def current_cases_required(session, catalog):
    require("case_bindings" in session, "Legacy session has no verified prompt snapshot; retain it for review and open a new session")
    for key in session["case_ids"]:
        require(key in catalog and session["case_bindings"][key]["fingerprint"] == case_fingerprint(catalog[key]),
                "Case content changed; use the saved snapshot for review and open a new session for new answers")


def session_catalog(root, session):
    split = "exam" if session["mode"] == "exam" or session.get("converted_from_exam") else "training"
    return load_catalog(root, splits=(split,))


def load_sessions(root):
    directory = checked_path(root, "sessions")
    sessions = {}
    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            checked_path(root, "sessions", path.name)
            session = read_json(path)
            catalog = {} if "case_bindings" in session else session_catalog(root, session)
            validate_session(session, catalog, allow_missing=True)
            require(path.stem == session["id"], "Session filename and ID differ")
            sessions[session["id"]] = session
    return sessions


def validate_answer(answer):
    require(isinstance(answer, dict), "Raw answer must be an object")
    identifier(answer.get("round_id"))
    identifier(answer.get("case_id"))
    require(isinstance(answer.get("answer"), str) and answer["answer"].strip(), "Missing original answer text")
    date.fromisoformat(answer["date"])
    require(type(answer.get("hint_used")) is bool, "Raw-answer hint flag must be boolean")
    return answer


def load_answers(root, round_id):
    identifier(round_id)
    directory = checked_path(root, "answers", round_id)
    answers = []
    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            checked_path(root, "answers", round_id, path.name)
            item = validate_answer(read_json(path))
            require(item["round_id"] == round_id and path.stem == item["case_id"], "Raw-answer identity conflicts with filename")
            correction_path = checked_path(root, "hint-corrections", round_id, item["case_id"] + ".json")
            if correction_path.exists():
                correction = read_json(correction_path)
                validate_hint_correction(correction)
                require(correction["round_id"] == round_id and correction["case_id"] == item["case_id"], "Hint correction identity mismatch")
                item = {**item, "hint_used": True, "hint_correction_id": f'{round_id}/{item["case_id"]}'}
            answers.append(item)
    return answers


def write_answer_unlocked(root, answer, session):
    validate_answer(answer)
    require(session["state"] == "awaiting_answers", "Resume an awaiting-answer session before answering")
    require(answer["case_id"] in session["case_ids"], "Raw answer does not belong to session")
    require(not session["hint_used"] or answer["hint_used"], "Cannot erase session hints in a raw answer")
    require(session["mode"] != "exam" or not answer["hint_used"],
            "A hinted exam answer requires converting the session to training first")
    target = checked_path(root, "answers", answer["round_id"], answer["case_id"] + ".json")
    if target.exists():
        old = validate_answer(read_json(target))
        require(old["answer"] == answer["answer"], "Saved first answer is immutable; score later attempts separately")
        require(old["date"] == answer["date"] and old["hint_used"] == answer["hint_used"],
                "Saved answer metadata differs; use correct-hint for a factual hint correction")
    else:
        atomic_json(target, answer)
    return target


def save_answer(root, answer):
    validate_answer(answer)
    with data_lock(root) as root:
        session = load_sessions(root).get(answer["round_id"])
        require(session is not None, "Open a session before saving its raw answers")
        current_cases_required(session, session_catalog(root, session))
        target = write_answer_unlocked(root, answer, session)
    return {"saved": str(target), "scored": False}


def validate_hint_correction(value):
    require(isinstance(value, dict) and set(value) == {"round_id", "case_id", "date", "reason", "hint_used"}, "Invalid hint correction fields")
    identifier(value["round_id"])
    identifier(value["case_id"])
    date.fromisoformat(value["date"])
    require(value["hint_used"] is True and isinstance(value["reason"], str) and value["reason"].strip(),
            "Hint corrections need a reason and may only mark a previously omitted hint")


def correct_hint(root, correction):
    validate_hint_correction(correction)
    with data_lock(root) as root:
        raw_path = checked_path(root, "answers", correction["round_id"], correction["case_id"] + ".json")
        require(raw_path.exists(), "Save the first answer before correcting its hint metadata")
        raw = validate_answer(read_json(raw_path))
        require(raw["round_id"] == correction["round_id"] and raw["case_id"] == correction["case_id"], "Raw-answer identity mismatch")
        require(not raw["hint_used"], "The original answer already records a hint")
        require(correction["date"] >= raw["date"], "Correction cannot predate the answer")
        target = checked_path(root, "hint-corrections", correction["round_id"], correction["case_id"] + ".json")
        preserve_archive(target, correction)
    return {"saved": str(target), "original_preserved": True, "effective_hint_used": True}


def present_question(case, task="expression", include_phase=False):
    """Whitelist learner-visible data; internal labels and rubrics never leave here."""
    goals = {
        "expression": "请给出你会实际说的一条回复或行动。",
        "judgment": "请区分事实、可能解释与未知，再选一个下一步。",
        "information": "还需要确认什么才能决定下一步？优先提出一个关键问题。",
        "adaptation": "先给出此刻的回应；后续再根据新反馈调整。",
    }
    require(task in goals, "Unknown teaching task")
    require(not include_phase or task == "expression", "Only expression tasks may disclose the phase")
    require(case.get("split") == "training", "Question helper accepts training cases only")
    output = {"id": case["id"], "input": case["input"], "task": task, "instruction": goals[task]}
    if include_phase:
        phase = case.get("relationship_phase", "unknown")
        require(phase in RELATIONSHIP_PHASES, "Invalid relationship phase")
        output["relationship_phase"] = phase
    return output


def show_session(root, round_id):
    import learning
    identifier(round_id)
    sessions = load_sessions(root)
    require(round_id in sessions, "Session not found")
    session = sessions[round_id]
    catalog = session_catalog(root, session)
    bindings = session.get("case_bindings")
    changed = [key for key in session["case_ids"] if bindings and
               (key not in catalog or bindings[key]["fingerprint"] != case_fingerprint(catalog[key]))]
    questions = []
    for key in session["case_ids"]:
        source = bindings[key] if bindings else catalog.get(key)
        if source is None:
            questions.append({"id": key, "unavailable": True})
            continue
        setting = session.get("question_settings", {}).get(key, {"task": "expression", "include_phase": False})
        visible = present_question({**source, "split": "training"}, setting["task"], setting["include_phase"])
        questions.append({**visible, "level": source["level"], "category": source["category"]})
    answers = load_answers(root, round_id)
    results = [r for r in load_history(root) if r["round_id"] == round_id]
    answered = {a["case_id"] for a in answers} | {r["case_id"] for r in results if r["attempt"] == 1}
    # Snapshots contain internal phase labels. Keep learner-facing restoration separate from stored internals.
    visible_session = {key: value for key, value in session.items() if key != "case_bindings"}
    return {"session": visible_session, "questions": questions, "answers": answers, "results": results,
            "binding_status": "bound" if bindings else "legacy-unverified", "changed_case_ids": changed,
            "practice_turns": load_turns(root, round_id),
            "learning_notes": learning.load_notes(root, round_id),
            "remaining_case_ids": [case_id for case_id in session["case_ids"] if case_id not in answered],
            "unscored_case_ids": [case_id for case_id in answered if not any(r["case_id"] == case_id for r in results)]}


def load_turns(root, round_id):
    identifier(round_id)
    directory = checked_path(root, "practice-turns", round_id)
    turns = []
    for path in sorted(directory.glob("*/*.json")) if directory.exists() else []:
        checked_path(root, *path.relative_to(Path(root).absolute()).parts)
        item = read_json(path)
        validate_turn(item)
        require(item["round_id"] == round_id and item["case_id"] == path.parent.name and
                path.stem == f'{item["turn"]:04}', "Practice turn filename/identity mismatch")
        turns.append(item)
    for key in {t["case_id"] for t in turns}:
        selected = [t for t in turns if t["case_id"] == key]
        require([t["turn"] for t in selected] == list(range(1, len(selected) + 1)), "Practice turn sequence is incomplete")
        require(all(t["role"] == ("assistant" if i % 2 == 0 else "user") for i, t in enumerate(selected)), "Practice roles must alternate")
    return turns


def validate_turn(value):
    require(isinstance(value, dict) and set(value) == {"round_id", "case_id", "turn", "role", "text", "date", "simulation"}, "Invalid practice turn fields")
    identifier(value["round_id"])
    identifier(value["case_id"])
    date.fromisoformat(value["date"])
    require(type(value["turn"]) is int and 1 <= value["turn"] <= 9999, "Invalid practice turn number")
    require(value["role"] in ("assistant", "user") and isinstance(value["text"], str) and value["text"].strip(), "Practice turn needs role and text")
    require(value["simulation"] is True, "Practice turns must be explicitly marked as simulation")


def save_turn(root, turn):
    validate_turn(turn)
    with data_lock(root) as root:
        session = load_sessions(root).get(turn["round_id"])
        require(session and session["mode"] == "training", "Practice turns require a training session; exam follow-ups are blocked")
        require(turn["case_id"] in session["case_ids"], "Practice case does not belong to the session")
        answers = {a["case_id"]: a for a in load_answers(root, turn["round_id"])}
        require(turn["case_id"] in answers, "Save the first answer before practicing follow-ups")
        require(turn["date"] >= answers[turn["case_id"]]["date"], "Practice cannot predate the first answer")
        target = checked_path(root, "practice-turns", turn["round_id"], turn["case_id"], f'{turn["turn"]:04}.json')
        if target.exists():
            require(read_json(target) == turn, "Saved practice turns cannot be rewritten")
        else:
            previous = [t for t in load_turns(root, turn["round_id"]) if t["case_id"] == turn["case_id"]]
            require(turn["turn"] == len(previous) + 1, "Practice turns must be saved in order")
            require(turn["role"] == ("assistant" if len(previous) % 2 == 0 else "user"), "Practice roles must alternate")
            require(not previous or turn["date"] >= previous[-1]["date"], "Practice dates cannot move backwards")
            atomic_json(target, turn)
    return {"saved": str(target), "scored": False, "counts_for_promotion": False}


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def validate_result(record):
    require(isinstance(record, dict), "Result must be an object")
    for key in ("id", "round_id", "case_id", "relationship_id"):
        identifier(record.get(key))
    date.fromisoformat(record["date"])
    require(record.get("mode") in ("training", "exam", "transfer"), "Invalid result mode")
    require(record.get("rubric_version") == RUBRIC, "Unsupported rubric version")
    require(type(record.get("level")) is int and 0 <= record["level"] <= 6, "Level must be 0-6")
    require(type(record.get("attempt")) is int and record["attempt"] >= 1, "Attempt must be positive integer")
    require(isinstance(record.get("category"), str) and record["category"].strip(), "Missing category")
    require(isinstance(record.get("answer"), str) and record["answer"].strip(), "Missing actual answer")
    require(type(record.get("hint_used")) is bool, "hint_used must be boolean")
    require(type(record.get("critical_error")) is bool, "critical_error must be boolean")
    if record["critical_error"]:
        require(isinstance(record.get("critical_reason"), str) and record["critical_reason"].strip(),
                "Critical error needs textual evidence")
    scores = record.get("scores")
    require(isinstance(scores, dict) and set(scores) == set(DIMENSIONS), "Exactly five named dimensions required")
    require(all(type(value) is int and 0 <= value <= 4 for value in scores.values()),
            "Each dimension must be an integer from 0 to 4")
    errors = record.get("errors", [])
    require(isinstance(errors, list) and all(error in
            ("comprehension", "evidence", "expression", "interaction", "action", "boundary") for error in errors),
            "Unknown error category")
    for key in ("action_planned", "action_completed"):
        require(record.get(key) is None or type(record[key]) is bool, key + " must be bool or null")
    require(not record.get("action_completed") or record.get("action_planned") is True,
            "Completed action requires planned action")
    if "case_fingerprint" in record:
        require(isinstance(record["case_fingerprint"], str) and re.fullmatch(r"[0-9a-f]{64}", record["case_fingerprint"]), "Invalid case fingerprint")
    for key in ("corpus_version", "record_origin", "teaching_task"):
        require(key not in record or isinstance(record[key], str) and record[key].strip(), "Invalid record metadata: " + key)
    if "communication_function" in record:
        require(record["communication_function"] in COMMUNICATION_FUNCTIONS, "Invalid communication function")
    if "signal_clarity" in record:
        require(record["signal_clarity"] in SIGNAL_CLARITY, "Invalid signal clarity")
    if "total" in record:
        require(record["total"] == sum(scores.values()), "Stored total conflicts with five scores")
    if "sequence" in record:
        require(type(record["sequence"]) is int and record["sequence"] > 0, "Invalid history sequence")
    return record


def evaluate_result(record):
    validate_result(record)
    total = sum(record["scores"].values())
    passed = total >= 16 and not record["critical_error"]
    return {"total": total, "maximum": 20, "passed": passed,
            "band": "excellent" if passed and total >= 18 else "pass" if passed else "retry"}


def exam_status(records, level, sessions=None, catalog=None):
    require(type(level) is int and 0 <= level <= 6, "Invalid target level")
    for record in records:
        validate_result(record)
    require(len({r["id"] for r in records}) == len(records), "Duplicate result ID")
    records = [r for _, r in sorted(enumerate(records), key=lambda item: item[1].get("sequence", item[0] + 1))]
    sessions = sessions or {}
    catalog = catalog or load_catalog(splits=("exam",))
    rounds = {}
    for record in records:
        if record["mode"] == "exam":
            rounds.setdefault(record["round_id"], []).append(record)
    eligible = []
    rejected = {}
    for round_id, answers in rounds.items():
        session = sessions.get(round_id)
        if not session or session["mode"] != "exam" or session["hint_used"] or session.get("converted_from_exam"):
            rejected[round_id] = "Missing independent exam session or session used hints/was converted"
            continue
        if any(r.get("record_origin") == "legacy-import" for r in answers):
            rejected[round_id] = "Imported history is not independent examination evidence"
            continue
        if "case_bindings" not in session:
            rejected[round_id] = "Legacy examination has no verified content binding; coach review required"
            continue
        if any(r.get("case_fingerprint") != session["case_bindings"].get(r["case_id"], {}).get("fingerprint") or
               r.get("corpus_version") != session["case_bindings"].get(r["case_id"], {}).get("corpus_version") or
               r.get("record_origin") != "session" for r in answers):
            rejected[round_id] = "Exam results are not bound to this session's content version"
            continue
        if "case_bindings" in session and any(
                key not in catalog or session["case_bindings"][key]["fingerprint"] != case_fingerprint(catalog[key])
                for key in session["case_ids"]):
            rejected[round_id] = "Exam content changed since this session opened"
            continue
        if session["state"] != "completed" or session["level"] != level or set(session["answered_case_ids"]) != set(session["case_ids"]):
            rejected[round_id] = "Exam session is incomplete or has a different level"
            continue
        if len(answers) != 3 or len({r["case_id"] for r in answers}) != 3:
            rejected[round_id] = "Requires exactly three distinct first answers"
            continue
        if {r["case_id"] for r in answers} != set(session["case_ids"]) or any(
                r["case_id"] not in catalog or catalog[r["case_id"]]["split"] != "exam" or
                catalog[r["case_id"]]["level"] != level or catalog[r["case_id"]]["category"] != r["category"] for r in answers):
            rejected[round_id] = "Answers do not match the authoritative exam catalog/session"
            continue
        if any(r["level"] != level or r["hint_used"] or r["attempt"] != 1 or
               not evaluate_result(r)["passed"] for r in answers):
            continue
        if any(other["id"] != round_id and set(other["case_ids"]) & set(session["case_ids"]) and
               other.get("opened_sequence", float("inf")) < session.get("opened_sequence", 0)
               for other in sessions.values()):
            rejected[round_id] = "A selected case was exposed in an earlier session"
            continue
        # A first answer is independent only if that case was not previously practiced.
        if any(any(old["id"] != r["id"] and old["case_id"] == r["case_id"] and
                   records.index(old) < records.index(r)
                   for old in records) for r in answers):
            continue
        eligible.append((round_id, {r["case_id"] for r in answers}))
    pair = next(([a[0], b[0]] for i, a in enumerate(eligible) for b in eligible[i + 1:]
                 if a[1].isdisjoint(b[1])), None)
    return {"level": level, "eligible_rounds": [r[0] for r in eligible],
            "promotion_eligible": pair is not None and level < 6,
            "supporting_rounds": pair or [], "next_level": level + 1 if pair and level < 6 else level,
            "rejected_rounds": rejected,
            "needs_coach_review": "Verify unseen-case integrity and semantic scoring before promotion"}


def progress_report(records, sessions=None):
    ids = set()
    for record in records:
        validate_result(record)
        require(record["id"] not in ids, "Duplicate result ID")
        ids.add(record["id"])
    groups = {}
    sessions = sessions or {}
    records = [r for _, r in sorted(enumerate(records), key=lambda item: item[1].get("sequence", item[0] + 1))]
    seen = set()
    unseen_ids = set()
    effective = []
    for record in records:
        session = sessions.get(record["round_id"], {})
        item = {**record, "mode": session.get("mode", record["mode"]),
                "hint_used": record["hint_used"] or session.get("hint_used", False)}
        if record["case_id"] not in seen and record["attempt"] == 1 and not item["hint_used"]:
            unseen_ids.add(record["id"])
        seen.add(record["case_id"])
        effective.append(item)
    # Rewrites remain in history, but trend calculations use initial attempts only.
    for record in effective:
        if record["attempt"] == 1:
            key = (record["rubric_version"], record["level"], record["category"], record["mode"],
                   record.get("corpus_version", "unknown"), record.get("record_origin", "legacy-unverified"),
                   record.get("teaching_task", "unknown"), record.get("communication_function", "unknown"),
                   record.get("signal_clarity", "unknown"))
            groups.setdefault(key, []).append(record)
    summaries = []
    for key, rows in sorted(groups.items()):
        rows = sorted(rows, key=lambda r: (r["date"], r["id"]))
        independent = [r for r in rows if not r["hint_used"]]
        unseen = [r for r in rows if r["id"] in unseen_ids]
        totals = [evaluate_result(r)["total"] for r in rows]
        planned = [r for r in rows if r.get("action_planned") is True]
        known = [r for r in planned if r.get("action_completed") is not None]
        summaries.append({"rubric_version": key[0], "level": key[1], "category": key[2], "mode": key[3],
                          "corpus_version": key[4], "record_origin": key[5], "teaching_task": key[6],
                          "communication_function": key[7], "signal_clarity": key[8],
                          "verified_training": key[5] == "session" and key[4] != "unknown",
                          "count": len(rows), "mean_total": statistics.mean(totals),
                          "population_stddev": statistics.pstdev(totals),
                          "dimension_means": {d: statistics.mean(r["scores"][d] for r in rows) for d in DIMENSIONS},
                          "independent_answer_rate": len(independent) / len(rows),
                          "independent_pass_rate": sum(evaluate_result(r)["passed"] for r in independent) /
                          len(independent) if independent else None,
                          "unseen_independent_count": len(unseen), "repeat_case_count": sum(r["id"] not in unseen_ids and not r["hint_used"] for r in rows),
                          "unseen_independent_pass_rate": sum(evaluate_result(r)["passed"] for r in unseen) / len(unseen) if unseen else None,
                          "unassisted_mean_total": statistics.mean(evaluate_result(r)["total"] for r in independent) if independent else None,
                          "action_completion_rate": sum(r["action_completed"] for r in known) / len(known) if known else None,
                          "actions_with_unknown_outcome": len(planned) - len(known),
                          "series": [{"date": r["date"], "id": r["id"], "total": evaluate_result(r)["total"]} for r in rows]})
    return {"records": len(records), "comparable_groups": summaries,
            "note": "No causal or real-world effectiveness claim; assisted answers are not independent"}


def checked_path(root, *parts):
    root = Path(root).absolute()
    # Reject links/junctions in the full chain, including ancestors of a data root.
    for candidate in [root, *root.parents]:
        require(not candidate.is_symlink() and not (candidate.exists() and
                getattr(candidate.stat(), "st_file_attributes", 0) & 0x400), "Linked data paths are not supported")
    resolved_root = root.resolve()
    require(not resolved_root.is_relative_to(ROOT) and not ROOT.is_relative_to(resolved_root),
            "Data root must be outside and must not contain the installed Skill")
    current = root
    for part in parts:
        current = current / part
        require(not current.is_symlink() and not (current.exists() and
                getattr(current.stat(), "st_file_attributes", 0) & 0x400), "Linked data paths are not supported")
    require(current.resolve().is_relative_to(resolved_root), "Path escapes data root")
    return current


@contextmanager
def data_lock(root):
    root = checked_path(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = checked_path(root, ".write.lock")
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise ValueError("Another writer is active or a stale .write.lock needs review") from error
    try:
        handle.write(str(os.getpid()))
        handle.close()
        yield root
    finally:
        lock.unlink(missing_ok=True)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json_text(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def preserve_archive(path, old):
    if path.exists():
        require(read_json(path) == old, "Archive conflicts with the current revision; manual review required")
    else:
        atomic_json(path, old)


def import_result(root, record, reason):
    require(isinstance(reason, str) and reason.strip(), "Historical import needs a reason")
    return append_result(root, record, import_reason=reason)


def append_result(root, record, import_reason=None):
    validate_result(record)
    with data_lock(root) as root:
        directory = checked_path(root, "training-history")
        target = checked_path(root, "training-history", identifier(record["id"]) + ".json")
        require(not target.exists(), "Result ID already exists; history cannot be overwritten")
        existing = load_history(root)
        sessions = load_sessions(root)
        session = sessions.get(record["round_id"])
        catalog = session_catalog(root, session) if session else load_catalog(root, splits=("training",))
        # Transfer records may refer to an unregistered real-world action, but never to a reserved holdout ID.
        require(record["case_id"] not in read_json(ROOT / "evaluation/catalog-index.json")["holdout_ids"],
                "Reserved evaluation IDs cannot become user records")
        case = catalog.get(record["case_id"])
        if case and import_reason is None:
            require(case["level"] == record["level"] and case["category"] == record["category"],
                    "Result level/category conflicts with the registered case")
            require(case["split"] != "holdout", "Holdout cases cannot become user training records")
        if import_reason is not None:
            require(session is None, "Import historical results under a separate round ID")
            record = {**record, "record_origin": "legacy-import", "import_reason": import_reason,
                      "corpus_version": "unknown"}
            record.pop("case_fingerprint", None)
        elif record["mode"] in ("training", "exam"):
            require(session is not None and case is not None, "Training/exam results require a registered case and existing session")
        else:
            record = {**record, "record_origin": "transfer"}
        if record["mode"] == "exam" and import_reason is None:
            require(session is not None, "Exam answers require an existing session with this round_id")
            require(case and case["split"] == "exam", "Only registered exam cases count as examination")
            require(not record["hint_used"], "A hinted exam grade requires converting the session to training first")
        if session:
            current_cases_required(session, catalog)
            require(session["state"] in ("awaiting_answers", "feedback"), "Resume the session before recording; completed sessions are immutable")
            require(record["case_id"] in session["case_ids"] and record["level"] == session["level"],
                    "Answer does not belong to this session")
            require(record["mode"] == session["mode"], "Result mode conflicts with the authoritative session")
            require(not session["hint_used"] or record["hint_used"], "Session hint history cannot be cleared in a result")
            if record["attempt"] == 1:
                saved = {a["case_id"]: a for a in load_answers(root, session["id"])}.get(record["case_id"])
                if saved:
                    require(saved["answer"] == record["answer"], "Grade must quote the saved first answer exactly")
                    require(not saved["hint_used"] or record["hint_used"], "A grade cannot erase a saved raw-answer hint")
                else:
                    write_answer_unlocked(root, {key: record[key] for key in ("round_id", "case_id", "answer", "date", "hint_used")}, session)
            binding = session["case_bindings"][record["case_id"]]
            record = {**record, "corpus_version": binding["corpus_version"], "case_fingerprint": binding["fingerprint"],
                      "record_origin": "session", "teaching_task": session["question_settings"][record["case_id"]]["task"]}
            context = binding.get("learning_context", {"communication_function": "unknown", "signal_clarity": "unknown"})
            record.update(context)
        require(not any(r["round_id"] == record["round_id"] and r["case_id"] == record["case_id"] and
                        r["attempt"] == record["attempt"] for r in existing), "Duplicate answer attempt")
        if record["attempt"] > 1:
            require(any(r["case_id"] == record["case_id"] and r["round_id"] == record["round_id"] and
                        r["attempt"] == record["attempt"] - 1 for r in existing), "Previous attempt is missing")
        directory.mkdir(parents=True, exist_ok=True)
        sequence = max((r.get("sequence", i + 1) for i, r in enumerate(existing)), default=0) + 1
        atomic_json(target, {**record, **evaluate_result(record), "sequence": sequence,
                             "recorded_at": datetime.now(timezone.utc).isoformat()})
    return {"saved": str(target), **evaluate_result(record)}


def load_history(root):
    directory = checked_path(root, "training-history")
    if not directory.exists():
        return []
    records = []
    for path in sorted(directory.glob("*.json")):
        checked_path(root, "training-history", path.name)
        record = read_json(path)
        validate_result(record)
        if record["attempt"] == 1:
            raw = {a["case_id"]: a for a in load_answers(root, record["round_id"])}.get(record["case_id"])
            if raw:
                require(raw["answer"] == record["answer"] and (not raw["hint_used"] or record["hint_used"] or raw.get("hint_correction_id")),
                        "Saved grade conflicts with first-answer text or hints; review this record before assessment")
                if raw.get("hint_correction_id"):
                    record = {**record, "hint_used": True, "hint_correction_id": raw["hint_correction_id"]}
        records.append(record)
    return sorted(records, key=lambda r: (r.get("sequence", 0), r["date"], r["id"]))


def validate_profile(record):
    require(isinstance(record, dict), "Profile must be an object")
    identifier(record.get("id"))
    require(type(record.get("revision")) is int and record["revision"] >= 1, "Invalid revision")
    require(record.get("stage") in ("unknown", *(f"R{i}" for i in range(7))), "Invalid relationship stage")
    require(record.get("status") in ("active", "paused", "ended"), "Invalid relationship status")
    date.fromisoformat(record["updated_at"])
    require(isinstance(record.get("alias"), str) and record["alias"].strip(), "Missing alias")
    for key in ("facts", "impressions", "stage_history"):
        require(isinstance(record.get(key), list), "Missing list: " + key)
    for fact in record["facts"]:
        require(isinstance(fact, dict) and all(isinstance(fact.get(k), str) and fact[k].strip()
                for k in ("text", "source", "observed_at")), "Each fact needs text, source and date")
        date.fromisoformat(fact["observed_at"])
    for event in record["stage_history"]:
        require(isinstance(event, dict) and event.get("stage") in ("unknown", *(f"R{i}" for i in range(7)))
                and isinstance(event.get("evidence"), str) and event["evidence"].strip(),
                "Stage history needs stage and evidence")
        date.fromisoformat(event["date"])
    require(bool(record["stage_history"]) and record["stage_history"][-1]["stage"] == record["stage"],
            "Current stage must agree with latest evidence event")
    if "relationship_phase" in record or "phase_history" in record:
        require(record.get("relationship_phase") in RELATIONSHIP_PHASES, "Invalid eight-stage relationship phase")
        history = record.get("phase_history")
        require(isinstance(history, list) and bool(history), "Eight-stage phase needs dated evidence history")
        previous_date = None
        for event in history:
            require(isinstance(event, dict) and event.get("phase") in RELATIONSHIP_PHASES and
                    isinstance(event.get("evidence"), str) and event["evidence"].strip(),
                    "Each phase event needs a valid phase and evidence")
            event_date = date.fromisoformat(event["date"])
            require(event_date <= date.fromisoformat(record["updated_at"]) and
                    (previous_date is None or event_date >= previous_date), "Phase history dates must be ordered and not future-dated")
            previous_date = event_date
        require(history[-1]["phase"] == record["relationship_phase"], "Relationship phase disagrees with latest evidence")
    return record


def save_profile(root, record):
    validate_profile(record)
    with data_lock(root) as root:
        target = checked_path(root, "profiles", identifier(record["id"]) + ".json")
        old = read_json(target) if target.exists() else None
        require(record["revision"] == (old["revision"] + 1 if old else 1), "Revision conflict")
        if old:
            require(record["updated_at"] >= old["updated_at"], "Profile update cannot move date backwards")
            require(record["stage_history"][:len(old["stage_history"])] == old["stage_history"],
                    "Preserve stage history; append a correction event instead")
            if "relationship_phase" in old:
                require("relationship_phase" in record and
                        record.get("phase_history", [])[:len(old["phase_history"])] == old["phase_history"],
                        "Preserve eight-stage phase history; append a correction event instead")
            require(isinstance(record.get("change_reason"), str) and record["change_reason"].strip(),
                    "Profile updates need a change_reason")
            archive = checked_path(root, "archive", f'{record["id"]}-r{old["revision"]}.json')
            require(record["id"] == old["id"], "Profile identity cannot change by filename case")
            preserve_archive(archive, old)
        atomic_json(target, record)
    return {"saved": str(target), "revision": record["revision"]}


def validate_session(record, catalog=None, allow_missing=False):
    require(isinstance(record, dict), "Session must be an object")
    identifier(record.get("id"))
    require(type(record.get("revision")) is int and record["revision"] >= 1, "Invalid session revision")
    require(record.get("mode") in ("training", "exam"), "Invalid session mode")
    require(record.get("state") in ("awaiting_answers", "feedback", "paused", "completed"), "Invalid session state")
    require(type(record.get("level")) is int and 0 <= record["level"] <= 6, "Invalid session level")
    require(record.get("rubric_version") == RUBRIC, "Invalid session rubric")
    require(type(record.get("hint_used")) is bool, "Session hint_used must be boolean")
    date.fromisoformat(record["updated_at"])
    cases = record.get("case_ids")
    require(isinstance(cases, list) and len(cases) == 3 and len(set(cases)) == 3, "Session requires three distinct cases")
    for case_id in cases:
        identifier(case_id)
    answered = record.get("answered_case_ids")
    require(isinstance(answered, list) and len(set(answered)) == len(answered) and set(answered) <= set(cases),
            "Answered cases must be a unique subset of selected cases")
    if record["state"] in ("feedback", "completed"):
        require(len(answered) == 3, "Finish all three answers before round feedback/completion")
    if record["mode"] == "exam":
        require(not record["hint_used"], "A hinted exam must be converted to training")
    converted = record.get("converted_from_exam", False)
    require(type(converted) is bool, "converted_from_exam must be boolean")
    require(not converted or record["mode"] == "training", "Converted sessions must be training")
    bindings = record.get("case_bindings")
    if bindings is not None:
        require(isinstance(bindings, dict) and set(bindings) == set(cases), "Snapshots must match the selected cases")
        for key, binding in bindings.items():
            require(isinstance(binding, dict) and binding.get("id") == key and
                    isinstance(binding.get("input"), str) and binding["input"].strip(), "Invalid question snapshot")
            require(isinstance(binding.get("fingerprint"), str) and re.fullmatch(r"[0-9a-f]{64}", binding["fingerprint"]), "Invalid snapshot fingerprint")
            require(isinstance(binding.get("corpus_version"), str) and binding["corpus_version"].strip(), "Snapshot needs content version")
            require(binding.get("relationship_phase") in RELATIONSHIP_PHASES and
                    isinstance(binding.get("category"), str) and binding["category"].strip(), "Invalid snapshot metadata")
            if "learning_context" in binding:
                validate_learning_context(binding["learning_context"])
    settings = record.get("question_settings")
    if settings is not None:
        require(isinstance(settings, dict) and set(settings) == set(cases), "Teaching settings must match selected cases")
        for setting in settings.values():
            require(isinstance(setting, dict) and set(setting) == {"task", "include_phase"} and
                    setting["task"] in ("expression", "judgment", "information", "adaptation") and
                    type(setting["include_phase"]) is bool, "Invalid teaching settings")
            require(not setting["include_phase"] or setting["task"] == "expression", "Judgment tasks cannot disclose the phase")
            require(record["mode"] != "exam" or not setting["include_phase"], "Exams cannot disclose the phase")
    require((bindings is None) == (settings is None), "Snapshots and teaching settings must be supplied together")
    catalog = catalog if catalog is not None else load_catalog(splits=("training", "exam"))
    for case_id in cases:
        case = bindings.get(case_id) if bindings is not None else catalog.get(case_id)
        # Legacy sessions with removed cases remain readable, with no verified write path.
        if case is None and bindings is None:
            require(allow_missing, "Unknown case; register its prompt and rubric before opening a session")
            continue
        require(case["level"] == record["level"], "Session level conflicts with the registered case")
        require(case["split"] == ("exam" if converted else record["mode"]), "Case split conflicts with session mode")
    return record


def save_session(root, record):
    with data_lock(root) as root:
        target = checked_path(root, "sessions", identifier(record["id"]) + ".json")
        old = read_json(target) if target.exists() else None
        catalog = session_catalog(root, record)
        record = dict(record)
        if old:
            for key in ("case_bindings", "question_settings"):
                if key in old:
                    require(key not in record or record[key] == old[key], "Question snapshots/settings are immutable; open a new session")
                    record[key] = old[key]
                else:
                    require(key not in record, "Cannot silently attach current content to a legacy session")
        else:
            require(all(key in catalog for key in record.get("case_ids", [])), "Unknown case; register it before opening a session")
            expected = {key: bind_case(catalog[key]) for key in record.get("case_ids", [])}
            require("case_bindings" not in record or record["case_bindings"] == expected, "New snapshots must match registered content")
            record["case_bindings"] = expected
            record.setdefault("question_settings", {key: {"task": "expression", "include_phase": False} for key in record.get("case_ids", [])})
        validate_session(record, catalog, allow_missing=old is not None)
        require(record["revision"] == (old["revision"] + 1 if old else 1), "Session revision conflict")
        if record.get("converted_from_exam"):
            require(old and (old["mode"] == "exam" or old.get("converted_from_exam")),
                    "Exam conversion requires an existing exam session")
        if old:
            require(record["id"] == old["id"], "Session identity cannot change by filename case")
            require(record["updated_at"] >= old["updated_at"], "Session date cannot move backwards")
            require(record["case_ids"] == old["case_ids"] and record["level"] == old["level"],
                    "Use a new session ID for different cases or level")
            require(old["state"] != "completed", "Completed sessions cannot be changed")
            require(set(old["answered_case_ids"]) <= set(record["answered_case_ids"]), "Cannot erase answered-case history")
            require(not old["hint_used"] or record["hint_used"], "Cannot erase hint history")
            require(old["mode"] != "training" or record["mode"] == "training", "Training cannot turn into an independent exam")
            require(old["mode"] != "exam" or record["mode"] == "exam" or record.get("converted_from_exam"),
                    "Record exam-to-training conversion explicitly")
            archive = checked_path(root, "archive", f'session-{record["id"]}-r{old["revision"]}.json')
            preserve_archive(archive, old)
        history = load_history(root)
        graded_cases = {r["case_id"] for r in history if r["round_id"] == record["id"] and r["attempt"] == 1}
        recorded_cases = graded_cases | {a["case_id"] for a in load_answers(root, record["id"])}
        require(set(record["answered_case_ids"]) <= recorded_cases, "Answered-case claims need actual saved first answers")
        if record["state"] == "completed":
            require(set(record["case_ids"]) <= graded_cases, "Completion needs saved grades for all three first answers")
        opened = old.get("opened_sequence", 0) if old else max(
            (s.get("opened_sequence", 0) for s in load_sessions(root).values()), default=0) + 1
        atomic_json(target, {**record, "opened_sequence": opened})
    return {"saved": str(target), "revision": record["revision"], "state": record["state"]}


def validate_package():
    case_files = {"training": [ROOT / "training/scenarios.jsonl", ROOT / "training/eight-stage-scenarios.jsonl"],
                  "exam": [ROOT / "training/exams.jsonl"], "holdout": [ROOT / "evaluation/holdout.jsonl"]}
    for split, name in (("training", "expanded-scenarios.jsonl"), ("training", "dual-track-scenarios.jsonl"), ("exam", "expanded-exams.jsonl")):
        if (ROOT / "training" / name).exists():
            case_files[split].append(ROOT / "training" / name)
    ids, fingerprints, counts, modules = set(), set(), {}, set()
    for split, paths in case_files.items():
        cases = [case for path in paths for case in read_jsonl(path)]
        counts[split] = len(cases)
        for case in cases:
            identifier(case["id"])
            require(case["id"] not in ids, "Duplicate case ID across splits")
            ids.add(case["id"])
            require(case["source_type"] == "synthetic" and case["split"] == split, "Wrong provenance or split")
            require(case["mode"] in ("M1", "M2", "M3", "M4", "M5", "M6"), "Invalid mode")
            require(type(case["level"]) is int and 0 <= case["level"] <= 6, "Invalid case level")
            require(case["stage"] in ("unknown", *(f"R{i}" for i in range(7))), "Invalid stage")
            if "relationship_phase" in case:
                require(case["relationship_phase"] in RELATIONSHIP_PHASES, "Invalid case relationship phase")
            if "learning_context" in case:
                validate_learning_context(case["learning_context"])
            require(case["facts"] and case["expected"] and case["failures"] and case["modules"], "Incomplete case")
            require(all(type(m) is int and 1 <= m <= 11 for m in case["modules"]), "Invalid module")
            fingerprint = re.sub(r"\s+", "", case["input"])
            require(fingerprint not in fingerprints, "Repeated input across splits")
            fingerprints.add(fingerprint)
            modules.update(case["modules"])
    require(sum(counts.values()) >= 50, "At least 50 initial cases required")
    require(modules == set(range(1, 12)), "Missing capability coverage")
    catalog = load_catalog(splits=("training", "exam"))
    level_counts = {str(level): {split: sum(c["level"] == level and c["split"] == split for c in catalog.values())
                                for split in ("training", "exam")} for level in range(7)}
    require(all(v["training"] >= 3 and v["exam"] >= 6 for v in level_counts.values()), "Insufficient level coverage for three-question training/two-round exams")
    require(set(read_json(ROOT / "evaluation/catalog-index.json")["holdout_ids"]) ==
            {c["id"] for c in read_jsonl(ROOT / "evaluation/holdout.jsonl")}, "Evaluation ID index is stale")
    for path in ROOT.rglob("*.md"):
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in link or link.startswith("#"):
                continue
            destination = (path.parent / link.split("#")[0]).resolve()
            require(destination.is_relative_to(ROOT) and destination.exists(), f"Broken local link: {path.name}: {link}")
    entry = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    require(entry.startswith("---\n") and "name: personal-love-coach" in entry, "Missing frontmatter")
    return {"valid": True, "case_counts": counts, "level_counts": level_counts, "modules": sorted(modules),
            "note": "Structural checks do not prove coaching quality or semantic isolation"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    question = sub.add_parser("question", help="Render a training prompt without its internal rubric")
    question.add_argument("case_id")
    question.add_argument("--task", choices=("expression", "judgment", "information", "adaptation"), default="expression")
    question.add_argument("--include-phase", action="store_true")
    question.add_argument("--data-root")
    score = sub.add_parser("score")
    score.add_argument("record")
    for name in ("record", "profile", "session", "case", "answer", "correct-hint", "turn", "import-result", "learning-note"):
        cmd = sub.add_parser(name)
        cmd.add_argument("input")
        cmd.add_argument("--data-root", required=True)
        if name == "import-result":
            cmd.add_argument("--reason", required=True)
    for name in ("progress", "exam-status", "coverage"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--data-root", required=True)
        if name == "exam-status":
            cmd.add_argument("--level", type=int, required=True)
        if name == "coverage":
            cmd.add_argument("--session-id")
    review = sub.add_parser("review-dates")
    review.add_argument("--from-date", required=True)
    show = sub.add_parser("show-session")
    show.add_argument("session_id")
    show.add_argument("--data-root", required=True)
    args = parser.parse_args(argv)
    if args.command == "validate":
        result = validate_package()
    elif args.command == "question":
        catalog = load_catalog(args.data_root, splits=("training",))
        require(args.case_id in catalog, "Unknown case")
        result = present_question(catalog[args.case_id], args.task, args.include_phase)
    elif args.command == "score":
        result = evaluate_result(read_json(args.record))
    elif args.command == "record":
        result = append_result(args.data_root, read_json(args.input))
    elif args.command == "profile":
        result = save_profile(args.data_root, read_json(args.input))
    elif args.command == "session":
        result = save_session(args.data_root, read_json(args.input))
    elif args.command == "case":
        result = register_case(args.data_root, read_json(args.input))
    elif args.command == "answer":
        result = save_answer(args.data_root, read_json(args.input))
    elif args.command == "correct-hint":
        result = correct_hint(args.data_root, read_json(args.input))
    elif args.command == "turn":
        result = save_turn(args.data_root, read_json(args.input))
    elif args.command == "import-result":
        result = import_result(args.data_root, read_json(args.input), args.reason)
    elif args.command == "learning-note":
        import learning
        result = learning.save_note(args.data_root, read_json(args.input))
    elif args.command == "show-session":
        result = show_session(args.data_root, args.session_id)
    elif args.command == "progress":
        import learning
        result = progress_report(load_history(args.data_root), load_sessions(args.data_root))
        result["coverage"] = learning.coverage_report(args.data_root)
    elif args.command == "coverage":
        import learning
        result = learning.coverage_report(args.data_root, args.session_id)
    elif args.command == "exam-status":
        result = exam_status(load_history(args.data_root), args.level, load_sessions(args.data_root), load_catalog(args.data_root, splits=("exam",)))
    else:
        start = date.fromisoformat(args.from_date)
        result = {"review_dates": [(start + timedelta(days=n)).isoformat() for n in (3, 7, 14)],
                  "reminder_created": False}
    print(json_text(result), end="")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
