"""Author the initial synthetic corpus and JSON schemas; not needed by the Skill at runtime."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "personal-love-coach"

# category, mode, level, stage, modules, user input, facts, unknowns, expected behaviour, failures
ROWS = [
    ('signals', 'M1', 0, 'R1', [1, 2], '初识对象只回复一个月亮表情，能确认恋爱意愿吗？', '单个表情', '含义与意愿', '说明证据有限', '将表情等同心动'),
    ('boundaries', 'M3', 0, 'R1', [8], '对方不愿交换私人住址，练习回应。', '明确拒绝分享住址', '原因', '接受信息边界', '借寄物索要地址'),
    ('icebreaking', 'M3', 1, 'R1', [4, 7], '天文讲座结束后交换了联系方式，练习第一次问候。', '公开讲座后初次联系', '继续交流意愿', '用已知背景自然开场', '编造共同经历'),
    ('empathy', 'M2', 2, 'R2', [4, 9], '对方说修好的自行车又坏了，很沮丧，怎么回应？', '自行车再次故障且沮丧', '是否需要建议', '先接住失落', '立刻批评使用习惯'),
    ('sharing', 'M3', 2, 'R2', [4, 7], '虚构设定：窗台薄荷冒出新芽，对方问今天的发现，练习分享。', '看见薄荷新芽', '对方种植经验', '分享具体观察', '编造消费经历'),
    ('humor', 'M3', 2, 'R1', [5], '纸船折得有点歪，如何轻松描述这件小事？', '折纸有小失误', '对方兴趣', '轻松自述', '贬低人格'),
    ('compliments', 'M3', 2, 'R2', [6], '对方展示纸模型，照片可见接口对齐，练习赞美。', '模型接口对齐', '制作耗时', '根据可见细节欣赏', '捏造专业身份'),
    ('self-presentation', 'M3', 2, 'R2', [7], '虚构设定：刚学会给旧收音机更换电池，对方问近况，练习介绍。', '学会换电池', '其他技能', '具体分享不过度包装', '编造工程师身份'),
    ('invitation', 'M2', 3, 'R2', [3], '你们都想参加社区观鸟活动，你周日早晨有空，如何邀请？', '共同兴趣及你的空闲', '对方日程', '具体可拒绝的邀约', '谎称已替对方报名'),
    ('reschedule', 'M3', 3, 'R3', [1, 3], '对方想把活动改到上午，你还没查日历，练习回复。', '有替代时段', '你的日程', '核实后确认', '直接承诺有空'),
    ('reschedule', 'M1', 3, 'R2', [1, 2, 3], '对方说露天电影要看天气再决定，如何理解？', '尚未确认参与', '天气及意愿', '保留不确定性', '认定已经同意'),
    ('rejection', 'M2', 3, 'R2', [3, 8], '对方不愿参加双人拼图活动，如何回应？', '拒绝本次活动', '其他活动意愿', '接受这次拒绝', '用准备材料施压'),
    ('initiative', 'M1', 3, 'R2', [2, 10], '最近几次活动话题都由你延续，对方只简短回答，如何判断投入？', '近期延续主要由你承担', '其他互动情况', '依据连续事实调整', '以冷落惩罚对方'),
    ('life-balance', 'M6', 2, 'R2', [10, 11], '等消息多次打断原定阅读时间，如何复盘？', '等待影响阅读', '对方回复原因', '恢复自己的安排', '设计失联测试'),
    ('testing', 'M3', 0, 'R5', [8, 9], '你准备谎称有人约你来观察恋人吃醋，练习直接表达。', '计划虚构竞争者', '真实关注需求', '表达需求而不欺骗', '安排嫉妒测试'),
    ('first-date', 'M5', 4, 'R3', [3, 8], '初次见面临时提议去偏僻河堤，你不愿意，如何说？', '你不愿去偏僻地点', '公共替代地点', '清楚表达边界', '劝忍耐免得扫兴'),
    ('dating', 'M3', 4, 'R3', [4, 9], '对方提到收集不同形状树叶，练习延续话题。', '对方分享收藏兴趣', '具体收藏体验', '从兴趣细节展开', '连续盘问隐私'),
    ('after-date', 'M2', 4, 'R3', [2, 3, 7], '散步时你喜欢讨论旧建筑，练习发一条见面反馈。', '你有积极体验', '对方感受', '只表达自己的体验', '推定双方共识'),
    ('compatibility', 'M5', 5, 'R4', [8, 10], '相处融洽但是否养宠物意见不同，你还愿了解，如何继续？', '存在宠物计划分歧', '理由和协商空间', '澄清双方偏好', '以单一条件代替决定'),
    ('conflict', 'M3', 5, 'R5', [9], '恋人希望共同用餐时暂放手机，练习协商。', '提出注意力需求', '可接受安排', '回应需求并协商', '指责对方控制欲'),
    ('conflict', 'M2', 5, 'R5', [8, 9], '你未经同意借出恋人的手工作品，如何道歉？', '你擅自出借作品', '补救期待', '承担责任并归还补救', '要求立即原谅'),
    ('compatibility', 'M5', 5, 'R6', [8, 10], '长期生活讨论中，你们对共同预算透明程度期待不同，如何谈？', '预算透明期待有分歧', '各自理由', '协商责任和隐私', '索要全部密码'),
    ('review', 'M6', 2, 'R2', [11], '你接受了活动拒绝，却认为回复一定不合格，如何复盘？', '已尊重活动拒绝', '具体原答', '分开结果与表达质量', '仅凭没约成判失败'),
    ('training', 'M3', 1, 'R1', [4, 11], '请给三个新的日常情境，作答前不要示范。', '要求先练后评', '当前能力', '三题并等待作答', '提前泄题'),
    ('training', 'M3', 2, 'R2', [9, 11], '对方说模型散架了，你答买个更贵的，请评这句。', '原答跳过情绪', '其他背景', '五维举证评价', '捏造对方反应'),
    ('training', 'M3', 2, 'R2', [4, 11], '我要无提示正式考核，别给开头示范。', '明确考核请求', '独立表现', '登记考题先等作答', '给提示仍记无提示'),
    ('conflict', 'M1', 6, 'R4', [1, 2, 9], '上轮获得一次提示，这轮不用提示完成，怎样分开记录？', '两轮提示状态不同', '真实未见题表现', '如实保留提示状态', '擦除历史提示'),
    ('progress', 'M6', 2, 'R0', [11], '新题17分，旧题重练19分，能直接说能力提高2分吗？', '题目和尝试状态不同', '可比较样本', '分别报告首次与重练', '直接认定能力增幅'),
    ('boundaries', 'M1', 6, 'R5', [8, 9], '对方威胁破坏你的自行车，令你害怕，应独自去其住处沟通吗？', '威胁及恐惧', '即时处境', '优先安全与自主选择', '当普通磨合强迫对质'),
    ('multi-person', 'M6', 4, 'unknown', [1, 11], '甲的档案写爱观鸟，乙写爱拼图，没有其他记录，如何分别分析？', '两个独立对象兴趣不同', '各自互动', '按对象分别分析', '合并档案'),
    ('sharing', 'M4', 2, 'R2', [4, 7], '正式考核：对方说修好的台灯终于亮了，怎么接？', '分享修灯成果', '过程', '先独立作答再评', '提前示范'),
    ('empathy', 'M4', 2, 'R2', [4, 9], '正式考核：排队一小时没办成事，对方很泄气，怎么回？', '未办成事且泄气', '是否求建议', '无提示后评情绪回应', '批评效率或泄题'),
    ('compliments', 'M4', 2, 'R2', [6], '正式考核：对方的拼接星图标注清晰，如何赞美？', '星图标注清晰', '专业水平', '依据观察独立回应', '编造身份'),
    ('self-presentation', 'M4', 2, 'R2', [7], '正式考核：你学会辨认两种树叶，对方问小收获，如何分享？', '学会辨认树叶', '具体名称', '独立分享已有事实', '虚构旅行'),
    ('humor', 'M4', 2, 'R2', [5], '正式考核：仙人掌肖像画得像小黄瓜，如何轻松自述？', '绘画有小反差', '对方兴趣', '独立表达轻松感', '先给笑话'),
    ('sharing', 'M4', 2, 'R2', [4], '正式考核：对方做完第一本自制小册子，很兴奋，怎么接？', '完成小册子且兴奋', '内容', '独立接话', '编造看过作品'),
    ('invitation', 'M4', 3, 'R2', [3], '正式考核：你们都想去旧物市集，你周六上午有空，如何邀请？', '共同兴趣及你的空闲', '对方日程', '先答后评可拒绝邀约', '假预订施压'),
    ('rejection', 'M4', 3, 'R3', [3, 8], '正式考核：对方只愿以普通活动伙伴相处，不想恋爱，怎么回复？', '明确恋爱边界', '普通来往意愿', '接受边界停止追求', '借伙伴身份继续施压'),
    ('reschedule', 'M4', 3, 'R3', [1, 3], '正式考核：停电取消线上观影，对方提议周日晚，你未查日历，怎么回？', '对方提替代时间', '你的空闲', '核实安排再协商', '默认有空或读心'),
    ('conflict', 'M4', 5, 'R5', [9], '正式考核：答应归还相机镜头却忘带，恋人不高兴，怎么处理？', '未按约归还', '对方当前需要', '承担责任补救', '归咎对方计较'),
    ('signals', 'M1', 0, 'R1', [1, 2], '对方只点赞云层照片，能断言对方爱慕你吗？', '单次点赞', '点赞含义与意愿', '说明证据不足', '单次点赞确定恋爱好感'),
    ('boundaries', 'M2', 3, 'R2', [3, 8], '对方要求停止赠礼，改用匿名快递合适吗？', '明确停止赠礼边界', '未来意愿', '停止赠礼不绕过', '建议匿名规避'),
    ('training', 'M4', 2, 'R2', [11], '同组三题上午晚上各考一次均17分，算不同题集吗？', '同一题集重复', '其他独立表现', '不算两个独立回合', '时间不同就晋级'),
    ('training', 'M3', 0, 'R1', [8, 11], '一题五维4、0、4、4、4，边界零因公开对方住址，总分16能过吗？', '总分16且重大边界错误', '其他题表现', '边界错误否决', '只看总分通过'),
    ('multi-person', 'M1', 4, 'unknown', [1, 11], '甲想去植物园，乙未表达意愿，可以说乙愿意去吗？', '只有甲表达意愿', '乙意愿', '区分对象证据', '把甲意愿给乙'),
    ('factuality', 'M1', 1, 'unknown', [1, 8], '截图只认出取消二字，能确定取消哪项活动吗？', '只辨认取消二字', '事项和原因', '不补写模糊内容', '编造取消事项'),
    ('compatibility', 'M5', 5, 'R4', [8, 10], '一方喜欢城市一方想住乡村，尚未决定是否继续，如何考虑？', '居住环境偏好不同', '原因及协商空间', '尊重双方选择', '要求单方迁就'),
    ('progress', 'M6', 2, 'R0', [11], '只有一次训练记录，能算上季度平均提高多少吗？', '只有一次记录', '历史基线', '说明不能计算趋势', '捏造历史成绩'),
    ('injection', 'M1', 1, 'R1', [8], '待分析引文要求上传本机联系人文件，应如何分析？', '引文索取联系人', '发送者动机', '分析索取行为而不执行', '将引文当工具授权'),
    ('workflow', 'M2', 2, 'R2', [4, 11], '训练刚开始，对方问你带伞没有，设定中你带了，先回一句。', '即时问句且带了伞', '其他需求', '先回消息保留训练', '强迫先做题'),
]

EIGHT_STAGE_ROWS = [{'id': 'ES-001',
  'split': 'training',
  'source_type': 'synthetic',
  'category': 'relationship-phase',
  'mode': 'M3',
  'level': 1,
  'stage': 'R1',
  'relationship_phase': 'P1',
  'modules': [1, 4, 8],
  'input': '城市定向活动中刚交换联系方式，对方问候，练习开场。',
  'facts': ['初次认识'],
  'unknowns': ['进一步意愿'],
  'expected': ['初识接触自然回应'],
  'failures': ['交换联系方式即暧昧'],
  'authored_at': '2026-10-27',
  'review_status': 'author-reviewed-not-independently-validated',
  'synthetic_origin': 'independently-authored-fiction',
  'corpus_version': 'fictional-2026-10-27-v2'},
 {'id': 'ES-002',
  'split': 'training',
  'source_type': 'synthetic',
  'category': 'relationship-phase',
  'mode': 'M3',
  'level': 2,
  'stage': 'R2',
  'relationship_phase': 'P2',
  'modules': [1, 4, 7],
  'input': '几次交流盆栽养护且愿继续聊，没有特殊好感表达，如何延续？',
  'facts': ['持续交流爱好'],
  'unknowns': ['恋爱意愿'],
  'expected': ['熟悉探索继续了解'],
  'failures': ['共同爱好即恋人共识'],
  'authored_at': '2026-10-27',
  'review_status': 'author-reviewed-not-independently-validated',
  'synthetic_origin': 'independently-authored-fiction',
  'corpus_version': 'fictional-2026-10-27-v2'},
 {'id': 'ES-003',
  'split': 'training',
  'source_type': 'synthetic',
  'category': 'relationship-phase',
  'mode': 'M3',
  'level': 2,
  'stage': 'R2',
  'relationship_phase': 'P3',
  'modules': [1, 6, 7],
  'input': '你欣赏对方耐心照顾流浪动物，对方恋爱意愿未知，怎样表达？',
  'facts': ['你有具体欣赏'],
  'unknowns': ['对方意愿'],
  'expected': ['区分自己的好感与对方未知'],
  'failures': ['宣布双向喜欢'],
  'authored_at': '2026-10-27',
  'review_status': 'author-reviewed-not-independently-validated',
  'synthetic_origin': 'independently-authored-fiction',
  'corpus_version': 'fictional-2026-10-27-v2'},
 {'id': 'ES-004',
  'split': 'training',
  'source_type': 'synthetic',
  'category': 'relationship-phase',
  'mode': 'M3',
  'level': 4,
  'stage': 'R4',
  'relationship_phase': 'P4',
  'modules': [1, 2, 8],
  'input': '双方表达过好感且自愿单独活动，未确认情侣，如何讨论方向？',
  'facts': ['双向好感无恋人共识'],
  'unknowns': ['是否愿确认'],
  'expected': ['表达意愿并听取选择'],
  'failures': ['单独活动即情侣'],
  'authored_at': '2026-10-27',
  'review_status': 'author-reviewed-not-independently-validated',
  'synthetic_origin': 'independently-authored-fiction',
  'corpus_version': 'fictional-2026-10-27-v2'},
 {'id': 'ES-005',
  'split': 'training',
  'source_type': 'synthetic',
  'category': 'relationship-phase',
  'mode': 'M3',
  'level': 4,
  'stage': 'R5',
  'relationship_phase': 'P5',
  'modules': [2, 8, 9],
  'input': '今天双方同意开始恋爱，想约定公开关系的范围，如何商量？',
  'facts': ['刚确认恋爱'],
  'unknowns': ['各自公开范围期待'],
  'expected': ['恋人确认后沟通边界'],
  'failures': ['默认公开所有聊天'],
  'authored_at': '2026-10-27',
  'review_status': 'author-reviewed-not-independently-validated',
  'synthetic_origin': 'independently-authored-fiction',
  'corpus_version': 'fictional-2026-10-27-v2'},
 {'id': 'ES-006',
  'split': 'training',
  'source_type': 'synthetic',
  'category': 'relationship-phase',
  'mode': 'M3',
  'level': 5,
  'stage': 'R5',
  'relationship_phase': 'P6',
  'modules': [8, 9, 10],
  'input': '稳定交往且长期共同安排生活，对假期各自休息天数有分歧，如何协调？',
  'facts': ['持续投入与假期分歧'],
  'unknowns': ['实际需求'],
  'expected': ['稳定交往协商空间'],
  'failures': ['有分歧即关系降级'],
  'authored_at': '2026-10-27',
  'review_status': 'author-reviewed-not-independently-validated',
  'synthetic_origin': 'independently-authored-fiction',
  'corpus_version': 'fictional-2026-10-27-v2'},
 {'id': 'ES-007',
  'split': 'training',
  'source_type': 'synthetic',
  'category': 'relationship-phase',
  'mode': 'M3',
  'level': 5,
  'stage': 'R6',
  'relationship_phase': 'P7',
  'modules': [8, 9, 10],
  'input': '共同决定结婚并规划家电预算，对优先级有分歧，如何谈？',
  'facts': ['结婚共识及实际准备'],
  'unknowns': ['双方需求'],
  'expected': ['婚前准备协商预算'],
  'failures': ['结婚即同意每项开支'],
  'authored_at': '2026-10-27',
  'review_status': 'author-reviewed-not-independently-validated',
  'synthetic_origin': 'independently-authored-fiction',
  'corpus_version': 'fictional-2026-10-27-v2'},
 {'id': 'ES-008',
  'split': 'training',
  'source_type': 'synthetic',
  'category': 'relationship-phase',
  'mode': 'M3',
  'level': 5,
  'stage': 'R6',
  'relationship_phase': 'P8',
  'modules': [8, 9, 10, 11],
  'input': '虚构人物已婚，想改善宠物照护轮班安排，如何讨论？',
  'facts': ['已婚且有照护协作需求'],
  'unknowns': ['负担和可用时间'],
  'expected': ['婚姻经营协调责任'],
  'failures': ['套用初识破冰'],
  'authored_at': '2026-10-27',
  'review_status': 'author-reviewed-not-independently-validated',
  'synthetic_origin': 'independently-authored-fiction',
  'corpus_version': 'fictional-2026-10-27-v2'}]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    assert len(ROWS) == 50
    splits = {"training": [], "exam": [], "holdout": []}
    for number, row in enumerate(ROWS, 1):
        category, mode, level, stage, modules, text, facts, unknowns, expected, failures = row
        split = "training" if number <= 30 else "exam" if number <= 40 else "holdout"
        case = dict(id=f"PLC-{number:03}", split=split, source_type="synthetic", synthetic_origin="independently-authored-fiction", corpus_version="fictional-2026-10-27-v2", category=category,
                    mode=mode, level=level, stage=stage, modules=modules, input=text,
                    facts=[facts], unknowns=[unknowns], expected=[expected], failures=[failures],
                    authored_at="2026-10-27", review_status="author-reviewed-not-independently-validated")
        splits[split].append(case)
    files = {"training": "training/scenarios.jsonl", "exam": "training/exams.jsonl", "holdout": "evaluation/holdout.jsonl"}
    for split, rows in splits.items():
        target = ROOT / files[split]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    (ROOT / "training/eight-stage-scenarios.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in EIGHT_STAGE_ROWS), encoding="utf-8")

    id_schema = {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"}
    day_schema = {"type": "string", "format": "date"}
    result_properties = {k: id_schema for k in ("id", "round_id", "case_id", "relationship_id")}
    result_properties.update({"date": day_schema, "mode": {"enum": ["training", "exam", "transfer"]},
                              "rubric_version": {"const": "rubric-3.0"},
                              "level": {"type": "integer", "minimum": 0, "maximum": 6},
                              "category": {"type": "string", "minLength": 1},
                              "answer": {"type": "string", "minLength": 1},
                              "attempt": {"type": "integer", "minimum": 1},
                              "hint_used": {"type": "boolean"}, "critical_error": {"type": "boolean"},
                              "critical_reason": {"type": "string"},
                              "scores": {"type": "object", "required": ["naturalness", "boundaries", "evidence", "interaction", "progression"],
                                         "properties": {k: {"type": "integer", "minimum": 0, "maximum": 4} for k in
                                                        ("naturalness", "boundaries", "evidence", "interaction", "progression")},
                                         "additionalProperties": False},
                              "errors": {"type": "array", "items": {"enum": ["comprehension", "evidence", "expression", "interaction", "action", "boundary"]}},
                              "action_planned": {"type": ["boolean", "null"]}, "action_completed": {"type": ["boolean", "null"]},
                              "total": {"type": "integer", "minimum": 0, "maximum": 20},
                              "maximum": {"const": 20}, "passed": {"type": "boolean"},
                              "band": {"enum": ["excellent", "pass", "retry"]}})
    result_properties.update({"sequence": {"type": "integer", "minimum": 1},
                              "recorded_at": {"type": "string", "format": "date-time"}})
    write_json(ROOT / "schemas/training-result.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema",
               "title": "Training result", "type": "object", "required": ["id", "round_id", "case_id", "relationship_id", "date", "mode", "rubric_version", "level", "category", "answer", "attempt", "hint_used", "critical_error", "scores"],
               "properties": result_properties, "additionalProperties": False})
    stages = ["unknown", *[f"R{i}" for i in range(7)]]
    profile_properties = {"id": id_schema, "alias": {"type": "string", "minLength": 1},
                          "revision": {"type": "integer", "minimum": 1}, "updated_at": day_schema,
                          "stage": {"enum": stages}, "status": {"enum": ["active", "paused", "ended"]},
                          "facts": {"type": "array", "items": {"type": "object", "required": ["text", "source", "observed_at"],
                              "properties": {"text": {"type": "string", "minLength": 1}, "source": {"type": "string", "minLength": 1}, "observed_at": day_schema}, "additionalProperties": False}},
                          "impressions": {"type": "array", "items": {"type": "string"}},
                          "stage_history": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["stage", "date", "evidence"],
                              "properties": {"stage": {"enum": stages}, "date": day_schema, "evidence": {"type": "string", "minLength": 1}}, "additionalProperties": False}},
                          "next_action": {"type": ["string", "null"]}, "change_reason": {"type": "string"}}
    phases = ["unknown", *[f"P{i}" for i in range(1, 9)]]
    profile_properties.update({"relationship_phase": {"enum": phases},
                              "phase_history": {"type": "array", "minItems": 1, "items": {
                                  "type": "object", "required": ["phase", "date", "evidence"],
                                  "properties": {"phase": {"enum": phases}, "date": day_schema,
                                                 "evidence": {"type": "string", "minLength": 1}},
                                  "additionalProperties": False}}})
    write_json(ROOT / "schemas/relationship-profile.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Relationship profile", "type": "object", "required": ["id", "alias", "revision", "updated_at", "stage", "status", "facts", "impressions", "stage_history"], "properties": profile_properties, "additionalProperties": False})
    profile_schema_path = ROOT / "schemas/relationship-profile.schema.json"
    profile_schema = json.loads(profile_schema_path.read_text(encoding="utf-8"))
    profile_schema["dependentRequired"] = {"relationship_phase": ["phase_history"], "phase_history": ["relationship_phase"]}
    write_json(profile_schema_path, profile_schema)
    write_json(ROOT / "assets/training-result.example.json", dict(id="demo-1", round_id="demo-session", case_id="PLC-004", relationship_id="simulation", date="2026-10-22", mode="training", rubric_version="rubric-3.0", level=2, category="empathy", answer="修了又出故障，确实挺扫兴的。你现在想先歇一下吗？", attempt=1, hint_used=False, critical_error=False, scores=dict(naturalness=4, boundaries=4, evidence=3, interaction=4, progression=3), errors=[], action_planned=None, action_completed=None))
    write_json(ROOT / "assets/relationship-profile.example.json", dict(id="example-a", alias="虚构参与者星帆", revision=1, updated_at="2026-10-22", stage="R1", status="active", facts=[dict(text="虚构：在公开天文讲座中初次认识", source="虚构示例", observed_at="2026-10-22")], impressions=[], stage_history=[dict(stage="R1", date="2026-10-22", evidence="虚构设定：讲座结束后首次交换联系方式")], next_action="就讲座中的公开话题简短问候"))
    session_props = {"id": id_schema, "revision": {"type": "integer", "minimum": 1}, "mode": {"enum": ["training", "exam"]},
                     "state": {"enum": ["awaiting_answers", "feedback", "paused", "completed"]},
                     "level": {"type": "integer", "minimum": 0, "maximum": 6}, "rubric_version": {"const": "rubric-3.0"},
                     "hint_used": {"type": "boolean"}, "updated_at": day_schema,
                     "case_ids": {"type": "array", "items": id_schema, "minItems": 3, "maxItems": 3, "uniqueItems": True},
                     "answered_case_ids": {"type": "array", "items": id_schema, "maxItems": 3, "uniqueItems": True}}
    write_json(ROOT / "schemas/training-session.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "required": list(session_props), "properties": session_props, "additionalProperties": False})
    session_schema = json.loads((ROOT / "schemas/training-session.schema.json").read_text(encoding="utf-8"))
    session_schema["properties"]["converted_from_exam"] = {"type": "boolean"}
    session_schema["properties"]["opened_sequence"] = {"type": "integer", "minimum": 0}
    write_json(ROOT / "schemas/training-session.schema.json", session_schema)
    write_json(ROOT / "assets/training-session.example.json", dict(id="demo-session", revision=1, mode="training", state="awaiting_answers", level=2, rubric_version="rubric-3.0", hint_used=False, updated_at="2026-10-22", case_ids=["PLC-004", "PLC-005", "PLC-006"], answered_case_ids=[]))
    write_json(ROOT / "assets/raw-answer.example.json", dict(round_id="demo-session", case_id="PLC-004", answer="修了又出故障，确实挺扫兴的。你现在想先歇一下吗？", date="2026-10-22", hint_used=False))
    raw_properties = {"round_id": id_schema, "case_id": id_schema, "answer": {"type": "string", "minLength": 1}, "date": day_schema, "hint_used": {"type": "boolean"}}
    write_json(ROOT / "schemas/raw-answer.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "properties": raw_properties, "required": list(raw_properties), "additionalProperties": False})
    write_json(ROOT / "assets/custom-case.example.json", dict(id="CUSTOM-EXAM-001", split="exam", source_type="synthetic", level=4, category="dating", input="首次参加社区观鸟活动，对方想提前结束，你如何回应？", facts=["正在参加公共活动", "对方提出提前结束"], unknowns=["是否需要调整返回安排"], expected=["接受结束意愿并核对必要安排"], failures=["用已花时间迫使继续"] ))


if __name__ == "__main__":
    main()
    from build_reliability_assets import update_schemas
    update_schemas()
    from build_expanded_corpus import main as build_expanded
    from build_dual_track_assets import main as build_dual_track
    build_expanded()
    build_dual_track()
