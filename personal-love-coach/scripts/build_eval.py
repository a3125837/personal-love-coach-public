"""Build Promptfoo offline replay or live-model configs without exposing expected answers in prompts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from coach import read_jsonl

ROUTES = {
    "M1": ["workflows/chat-analysis.md", "references/relationship-stages.md"],
    "M2": ["workflows/reply-coaching.md", "references/conversation-playbook.md", "references/invitation-playbook.md", "references/relationship-stages.md", "references/flirting-and-calibration.md", "references/personal-style.md"],
    "M3": ["workflows/simulation-training.md", "training/training-protocol.md", "training/dual-track-training.md", "training/scoring-rubric.md", "training/calibration-guide.md", "references/relationship-stages.md", "references/flirting-and-calibration.md"],
    "M4": ["workflows/examination.md", "training/training-protocol.md", "training/scoring-rubric.md", "training/calibration-guide.md", "references/relationship-stages.md"],
    "M5": ["workflows/dating-advice.md", "references/relationship-stages.md", "references/compatibility-and-conflict.md"],
    "M6": ["workflows/review-and-growth.md", "training/dual-track-training.md", "governance/data-and-maintenance.md"],
}


def build(provider=None, judge=None, suite="holdout"):
    if bool(provider) != bool(judge):
        raise ValueError("Live evaluation requires both --provider and --judge")
    if suite not in ("holdout", "behavior"):
        raise ValueError("Unknown evaluation suite")
    if suite == "behavior" and not provider:
        raise ValueError("Behavior probes require a real candidate and judge; no authored replay is provided")
    common = ["SKILL.md", "references/core-principles.md", "references/decision-engine.md"]
    tests = []
    case_path = "evaluation/behavioral-regression.jsonl" if suite == "behavior" else "evaluation/holdout.jsonl"
    for case in read_jsonl(ROOT / case_path):
        paths = list(dict.fromkeys(common + ROUTES[case["mode"]]))
        instructions = "\n\n".join((ROOT / path).read_text(encoding="utf-8") for path in paths)
        # Instructions only; cases, expected responses and failure rubrics stay outside the candidate prompt.
        assertion = {"type": "javascript", "value": "(() => { try { const r=JSON.parse(output); return typeof r === 'object' && r !== null && r.mode === context.vars.expected_mode && Array.isArray(r.facts) && Array.isArray(r.unknowns) && typeof r.action === 'string' && Array.isArray(r.reply) && r.reply.length <= 3 && typeof r.user_response === 'string'; } catch { return false; } })()"}
        assertions = [assertion]
        if provider:
            assertions.append({"type": "llm-rubric", "value": "根据输入而不是凭输出自述评审。必须满足：" + "；".join(case["expected"]) + "。任何以下行为为失败：" + "；".join(case["failures"]) + "。不虚构事实，不确定心理不确定表达。给出通过/失败的依据。"})
        tests.append({"description": case["id"], "vars": {"case_id": case["id"], "input": case["input"],
                     "instructions": instructions, "expected_mode": case["mode"]}, "assert": assertions})
    config = {"description": "Personal Love Coach live semantic evaluation" if provider else "OFFLINE AUTHORED REPLAY — plumbing only, no model behaviour claim",
              "prompts": ["{{instructions}}\n\n当前用户输入：{{input}}\n\n这是评测输出格式要求：返回JSON对象，字段mode（M1到M6）、facts数组、unknowns数组、action字符串、reply数组（最多3条）、user_response字符串。实际给用户的完整回复放在user_response。遵守教练流程；训练未作答前不能给标准答案。不要把评测格式误认为用户要保存数据。"],
              "providers": [provider or "file://replay-provider.cjs"], "tests": tests}
    if judge:
        config["defaultTest"] = {"options": {"provider": judge}}
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider")
    parser.add_argument("--judge")
    parser.add_argument("--suite", choices=("holdout", "behavior"), default="holdout")
    parser.add_argument("--output")
    args = parser.parse_args()
    config = build(args.provider, args.judge, args.suite)
    default_name = "promptfoo-behavior.yaml" if args.suite == "behavior" else "promptfoo-live.yaml" if args.provider else "promptfooconfig.yaml"
    output = Path(args.output or ROOT / "evaluation" / default_name).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # JSON is valid YAML and keeps this builder standard-library-only.
    data = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    if not args.provider:
        config["providers"] = ["file://" + (ROOT / "evaluation/replay-provider.cjs").as_posix()]
        # Use a path relative to the output config for portability.
        import os
        config["providers"] = ["file://" + os.path.relpath(ROOT / "evaluation/replay-provider.cjs", output.parent).replace("\\", "/")]
        data = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    output.write_text(data, encoding="utf-8")
    print(json.dumps({"saved": str(output), "cases": len(config["tests"]), "live": bool(args.provider),
                      "sha256": hashlib.sha256(data.encode()).hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
