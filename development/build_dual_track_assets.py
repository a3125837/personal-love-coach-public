"""Independent fictional practice and additive schemas for dual-track learning."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "personal-love-coach"
ROWS = [
    (2, "shared-joy", "share", "explicit", "对方说第一次调出想要的水彩颜色，兴奋地发来色卡。先给自然回复，再分析这条消息的交流作用。", "对方在分享成果与兴奋", "是否还想讲制作过程", "可以共同高兴或好奇，不必重复情绪标签或立刻建议", "把喜悦变成技术测验"),
    (2, "positive-feedback", "praise", "explicit", "你们一起整理旧书后，对方说和你搭档挺轻松。你也有同感，先说第一反应，再说明依据。", "对方肯定相处体验且你也有同感", "是否包含恋爱意图", "接受欣赏，真实回馈感受，不把一次好评当承诺", "解释自己为什么平时不轻松而忽略当下反馈"),
    (2, "ambiguous-play", "play", "ambiguous", "在熟悉的桌游伙伴群中，对方笑着说你像规则百科全书，没有更多语气信息。先给自然回应，再区分可能的玩笑和不确定性。", "对方用了规则百科全书的比喻", "是欣赏还是嫌解释太多", "允许轻松回应或简短确认，不诊断对方心意", "从比喻确定恋爱好感或直接认定讽刺"),
    (5, "action-care", "request", "explicit", "恋人说搬书箱有点累，问你能否帮十分钟。你正在完成必须按时提交的任务，半小时后才有空。你怎么回应并复盘自己的决定？", "对方有具体请求且你现在有时间约束", "延后是否仍需要帮助", "说清可用时间并确认需要，允许拒绝或其他安排", "为证明关心承诺无法做到的立刻到场"),
    (5, "immediate-repair", "vent", "explicit", "对方说照料的盆栽枯了，你先列出养护步骤；对方说现在只是难过，不想听步骤。你下一句怎么调整？", "对方明确希望先谈感受", "是否愿意继续倾诉", "就地停止说教并接住具体失落，不只承诺以后注意", "继续给养护方案或要求对方接受好意"),
    (5, "decision-expression", "request", "mixed", "恋人希望睡前留一小段时间聊聊，你正在收尾一项工作。你分析后决定十分钟后合上电脑，但草稿只写今天先算了。怎样检查并表达最终决定？", "分析中的决定与草稿不同", "双方能接受的开始时间与时长", "说清最终自愿选择，也可重新决定，但不能替用户虚构承诺", "只夸分析正确而忽略实际回复不一致"),
]


def build_cases():
    return [dict(id=f"DT-{i:03}", split="training", source_type="synthetic", synthetic_origin="independently-authored-fiction",
        corpus_version="fictional-2026-10-28-dual", authored_at="2026-10-28", review_status="author-reviewed-not-independently-validated",
        mode="M3", level=level, category=category, stage="unknown", relationship_phase="unknown", modules=[1, 4, 8, 9, 11],
        learning_context=dict(communication_function=function, signal_clarity=clarity), input=prompt,
        facts=[fact], unknowns=[unknown], expected=[expected], failures=[failure])
        for i, (level, category, function, clarity, prompt, fact, unknown, expected, failure) in enumerate(ROWS, 1)]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_schemas():
    text = {"type": "string", "minLength": 1}
    identity = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"}
    function = {"enum": ["share", "vent", "play", "praise", "question", "invite", "request", "unknown"]}
    clarity = {"enum": ["explicit", "ambiguous", "mixed", "unknown"]}
    context = {"type": "object", "required": ["communication_function", "signal_clarity"],
        "properties": {"communication_function": function, "signal_clarity": clarity}, "additionalProperties": False}
    for filename in ("training-result", "training-session"):
        path = ROOT / f"schemas/{filename}.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        if filename == "training-result":
            schema["properties"].update(communication_function=function, signal_clarity=clarity)
        else:
            schema["properties"]["case_bindings"]["additionalProperties"]["properties"]["learning_context"] = context
        write(path, schema)
    common = dict(id=identity, round_id=identity, case_id=identity, date={"type": "string", "format": "date"},
        sequence={"type": "integer", "minimum": 1}, case_fingerprint={"type": "string", "pattern": "^[0-9a-f]{64}$"},
        first_answer_fingerprint={"type": "string", "pattern": "^[0-9a-f]{64}$"})
    payloads = {
        "reflection": dict(analysis=text),
        "response_status": dict(status={"enum": ["skipped", "cannot_formulate"]}, reason=text),
        "coach_review": dict(understanding=text, expression=text, action=text, scope=text, hypothesis=text,
            supporting_evidence={"type": "array", "items": text, "minItems": 1}, counterevidence={"type": "array", "items": text}),
    }
    variants = [{"type": "object", "properties": {**common, "kind": {"const": kind}, **payload},
        "required": ["id", "round_id", "case_id", "date", "kind", *payload], "additionalProperties": False}
        for kind, payload in payloads.items()]
    variants[0]["properties"]["assistance"] = {"enum": ["unassisted", "assisted", "unknown"]}
    write(ROOT / "schemas/learning-note.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema", "oneOf": variants})
    write(ROOT / "assets/learning-note.example.json", dict(id="reflect-one", round_id="demo-session", case_id="PLC-004",
        date="2026-10-28", kind="reflection", assistance="unassisted", analysis="虚构示例：先回应反复故障带来的失落，是否需要建议仍未知。"))
    write(ROOT / "assets/response-status.example.json", dict(id="status-one", round_id="demo-session", case_id="PLC-005",
        date="2026-10-28", kind="response_status", status="cannot_formulate", reason="虚构示例：暂时不知道怎样自然分享。"))


def main():
    rows = build_cases()
    (ROOT / "training/dual-track-scenarios.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    update_schemas()


if __name__ == "__main__":
    main()
