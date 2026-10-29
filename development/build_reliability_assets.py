"""Extend schemas additively; reproducible without rewriting the original fictional corpus."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "personal-love-coach"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_schemas():
    string = {"type": "string", "minLength": 1}
    identity = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"}
    day = {"type": "string", "format": "date"}
    fingerprint = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    task = {"enum": ["expression", "judgment", "information", "adaptation"]}
    settings = {"type": "object", "required": ["task", "include_phase"],
                "properties": {"task": task, "include_phase": {"type": "boolean"}}, "additionalProperties": False,
                "if": {"properties": {"include_phase": {"const": True}}},
                "then": {"properties": {"task": {"const": "expression"}}}}
    binding_props = dict(id=identity, input=string, level={"type": "integer", "minimum": 0, "maximum": 6},
                         category=string, split={"enum": ["training", "exam"]},
                         relationship_phase={"enum": ["unknown", *[f"P{i}" for i in range(1, 9)]]},
                         corpus_version=string, fingerprint=fingerprint)
    binding = {"type": "object", "properties": binding_props, "required": list(binding_props), "additionalProperties": False}
    schema_path = ROOT / "schemas/training-session.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["properties"].update(case_bindings={"type": "object", "additionalProperties": binding},
                                question_settings={"type": "object", "additionalProperties": settings})
    # Input may specify teaching settings alone; save_session creates the matching snapshots.
    schema["dependentRequired"] = {"case_bindings": ["question_settings"]}
    write(schema_path, schema)
    path = ROOT / "schemas/training-result.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["properties"].update(corpus_version=string, case_fingerprint=fingerprint, teaching_task=task,
                                record_origin={"enum": ["session", "transfer", "legacy-import"]},
                                import_reason=string, hint_correction_id=string)
    write(path, schema)
    path = ROOT / "schemas/raw-answer.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["properties"]["hint_correction_id"] = string
    write(path, schema)
    for name, props in {
        "hint-correction": dict(round_id=identity, case_id=identity, date=day, reason=string, hint_used={"const": True}),
        "practice-turn": dict(round_id=identity, case_id=identity, turn={"type": "integer", "minimum": 1, "maximum": 9999},
                              role={"enum": ["assistant", "user"]}, text=string, date=day, simulation={"const": True}),
    }.items():
        write(ROOT / f"schemas/{name}.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "type": "object", "required": list(props), "properties": props, "additionalProperties": False})
    write(ROOT / "assets/hint-correction.example.json", dict(round_id="demo-session", case_id="PLC-004",
          date="2026-10-28", reason="虚构示例：首答前已用提示，原标记有误", hint_used=True))
    write(ROOT / "assets/practice-turn.example.json", dict(round_id="demo-session", case_id="PLC-004", turn=1,
          role="assistant", text="虚构接续：今天想先歇会。", date="2026-10-28", simulation=True))
    cases = [json.loads(line) for line in (ROOT / "evaluation/holdout.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    write(ROOT / "evaluation/catalog-index.json", {"holdout_ids": [case["id"] for case in cases]})
    from build_dual_track_assets import update_schemas as update_learning_schemas
    update_learning_schemas()


if __name__ == "__main__":
    update_schemas()
