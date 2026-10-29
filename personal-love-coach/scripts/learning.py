"""Additive dual-track notes and response coverage; independent of score arithmetic."""
from datetime import date
import hashlib
from pathlib import Path

import coach

BASE = {"id", "round_id", "case_id", "date", "kind"}
PAYLOADS = {
    "reflection": {"analysis"},
    "response_status": {"status", "reason"},
    "coach_review": {"understanding", "expression", "action", "scope", "hypothesis", "supporting_evidence", "counterevidence"},
}
GENERATED = {"sequence", "case_fingerprint", "first_answer_fingerprint"}


def validate_note(note):
    coach.require(isinstance(note, dict) and note.get("kind") in PAYLOADS, "Unknown learning note kind")
    required = BASE | PAYLOADS[note["kind"]]
    optional = {"assistance"} if note["kind"] == "reflection" else set()
    coach.require(required <= set(note) and set(note) <= required | GENERATED | optional, "Learning note fields differ from its kind; scores are not accepted")
    if "assistance" in note:
        coach.require(note["assistance"] in ("unassisted", "assisted", "unknown"), "Invalid reflection assistance")
    for key in ("id", "round_id", "case_id"):
        coach.identifier(note[key])
    date.fromisoformat(note["date"])
    if note["kind"] == "response_status":
        coach.require(note["status"] in ("skipped", "cannot_formulate"), "Unknown missing-response status")
    for key in PAYLOADS[note["kind"]] - {"supporting_evidence", "counterevidence"}:
        coach.require(isinstance(note[key], str) and note[key].strip(), "Empty note field: " + key)
    if note["kind"] == "coach_review":
        for key in ("supporting_evidence", "counterevidence"):
            coach.require(isinstance(note[key], list) and all(isinstance(x, str) and x.strip() for x in note[key]), "Review evidence must be a string list")
        coach.require(bool(note["supporting_evidence"]), "Coach review needs supporting evidence, not just a label")
    if "sequence" in note:
        coach.require(type(note["sequence"]) is int and note["sequence"] > 0, "Invalid note sequence")
    for key in GENERATED - {"sequence"}:
        if key in note:
            coach.require(isinstance(note[key], str) and len(note[key]) == 64 and
                          all(c in "0123456789abcdef" for c in note[key]), "Invalid note fingerprint")
    return note


def load_notes(root, round_id):
    coach.identifier(round_id)
    directory = coach.checked_path(root, "learning-notes", round_id)
    notes = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        coach.checked_path(root, "learning-notes", round_id, path.name)
        note = validate_note(coach.read_json(path))
        coach.require(note["round_id"] == round_id and path.stem == note["id"] and "sequence" in note,
                      "Learning note identity or sequence mismatch")
        notes.append(note)
    coach.require(len({n["sequence"] for n in notes}) == len(notes), "Duplicate learning note sequence")
    return sorted(notes, key=lambda n: n["sequence"])


def save_note(root, note):
    note = dict(note)
    if note.get("kind") == "reflection":
        note.setdefault("assistance", "unknown")
    validate_note(note)
    coach.require(not GENERATED & set(note), "Generated note metadata cannot be supplied by the caller")
    with coach.data_lock(root) as root:
        session = coach.load_sessions(root).get(note["round_id"])
        coach.require(session is not None and note["case_id"] in session["case_ids"], "Learning note needs a selected session case")
        coach.require(note["kind"] == "response_status" or session["mode"] != "exam" or session["state"] == "completed",
                      "Finish examination before adding analysis, teaching review or response notes")
        answers = {a["case_id"]: a for a in coach.load_answers(root, note["round_id"])}
        first = answers.get(note["case_id"])
        notes = load_notes(root, note["round_id"])
        target = coach.checked_path(root, "learning-notes", note["round_id"], note["id"] + ".json")
        if target.exists():
            old = coach.read_json(target)
            coach.require({k: v for k, v in old.items() if k not in GENERATED} == note, "Saved learning notes cannot be rewritten; append a new correction")
            return {"saved": str(target), "scored": False, "counts_for_promotion": False}
        if note["kind"] == "response_status":
            coach.require(first is None, "An answered case cannot be relabeled as missing")
            coach.require(session["state"] != "completed", "Completed sessions cannot acquire missing answers")
        else:
            coach.require(first is not None, "Save the natural first answer before reflection or review")
        if note["kind"] == "reflection" and note["assistance"] == "unassisted":
            reviewed = any(n["case_id"] == note["case_id"] and n["kind"] == "coach_review" for n in notes)
            graded = any(r["case_id"] == note["case_id"] and r["round_id"] == note["round_id"] for r in coach.load_history(root))
            coach.require(not reviewed and not graded, "Prior grading/review prevents claiming this reflection is unassisted; use assisted or unknown")
        earliest = first["date"] if first else session["updated_at"]
        coach.require(note["date"] >= earliest and (not notes or note["date"] >= notes[-1]["date"]), "Learning note date cannot move backwards")
        stored = {**note, "sequence": max((n["sequence"] for n in notes), default=0) + 1}
        if session.get("case_bindings"):
            stored["case_fingerprint"] = session["case_bindings"][note["case_id"]]["fingerprint"]
        if first:
            stored["first_answer_fingerprint"] = hashlib.sha256(first["answer"].encode("utf-8")).hexdigest()
        coach.atomic_json(target, stored)
    return {"saved": str(target), "scored": False, "counts_for_promotion": False}


def coverage_report(root, round_id=None):
    sessions = coach.load_sessions(root)
    if round_id is not None:
        coach.identifier(round_id)
        coach.require(round_id in sessions, "Session not found")
        sessions = {round_id: sessions[round_id]}
    history = coach.load_history(root)
    counts = dict(selected_count=0, answered_count=0, graded_count=0, unanswered_count=0,
                  answered_ungraded_count=0, answered_after_cannot_formulate=0, answered_after_skipped=0)
    missing = dict(pending=0, skipped=0, cannot_formulate=0)
    contexts = {}
    reflection_counts = dict(unassisted=0, assisted=0, unknown=0)
    for key, session in sessions.items():
        answers = {a["case_id"] for a in coach.load_answers(root, key)}
        grades = {r["case_id"] for r in history if r["round_id"] == key and r["attempt"] == 1}
        answered = answers | grades
        notes = load_notes(root, key)
        for note in notes:
            if note["kind"] == "reflection":
                reflection_counts[note.get("assistance", "unknown")] += 1
        for case_id in session["case_ids"]:
            counts["selected_count"] += 1
            statuses = [n for n in notes if n["case_id"] == case_id and n["kind"] == "response_status"]
            context = session.get("case_bindings", {}).get(case_id, {}).get("learning_context", {})
            group = (context.get("communication_function", "unknown"), context.get("signal_clarity", "unknown"))
            tally = contexts.setdefault(group, dict(selected_count=0, answered_count=0, graded_count=0))
            tally["selected_count"] += 1
            if case_id in answered:
                counts["answered_count"] += 1
                tally["answered_count"] += 1
                if any(n["status"] == "cannot_formulate" for n in statuses):
                    counts["answered_after_cannot_formulate"] += 1
                if any(n["status"] == "skipped" for n in statuses):
                    counts["answered_after_skipped"] += 1
                if case_id not in grades:
                    counts["answered_ungraded_count"] += 1
            else:
                counts["unanswered_count"] += 1
                missing[statuses[-1]["status"] if statuses else "pending"] += 1
            if case_id in grades:
                counts["graded_count"] += 1
                tally["graded_count"] += 1
    return {**counts, "missing_by_status": missing,
            "reflection_notes_by_assistance": reflection_counts,
            "answer_coverage": counts["answered_count"] / counts["selected_count"] if counts["selected_count"] else None,
            "by_context": [dict(communication_function=k[0], signal_clarity=k[1], **v) for k, v in sorted(contexts.items())],
            "note": "Counts concern selected case instances, not proof every question was shown; missing answers are never zero grades."}
