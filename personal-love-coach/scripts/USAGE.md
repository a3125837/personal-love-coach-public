# 本地离线工具

V4只读知识检索：`python scripts/interaction.py capabilities C01`、`topics T001`、`branches B01`。默认案例仅给题面；用户主动学习时加`--view study`查看三种表达与四分支。这些资源不自动创建会话、成绩、真实记忆或晋级资格；实际生成和选择由教练完成。详见[互动创造引擎](../references/interaction-engine.md)。

3.1.0档案可选增加`relationship_phase`（unknown或P1–P8）和`phase_history`（非空事件列表，每项含phase、date、evidence），两者一起提供。日期有序且不晚于updated_at，最新事件须匹配当前阶段；修订保留全部旧历史并追加。旧`stage`/`stage_history`仍必需且保留原义。旧档案可直接读取，脚本不会从旧字段推断八段式，也不会自动判断真实关系。

Python 3.10+，仅标准库。以下路径相对于已安装的 Skill；请先切到该目录或使用脚本绝对路径。无需 API 密钥。

```powershell
python scripts/coach.py validate
python scripts/coach.py question ES-002 --task judgment
python scripts/coach.py question ES-002 --task expression --include-phase
python scripts/coach.py score assets/training-result.example.json
python scripts/coach.py review-dates --from-date 2026-10-22
```

`question`按训练分区读取，默认不展示阶段，不输出内部评分资料。`--task`可选expression、judgment、information、adaptation，只有expression允许`--include-phase`；独立注册的训练题可用`--data-root`读取。它不自动改写题干，教练仍须确认原题干没有泄露待考答案。此命令不保存作答，也不改变会话。接续用`turn`另存，详见[接续协议](../references/flirting-and-calibration.md)。新自定义题按cases/training与cases/exam分区；旧版cases根目录的平铺文件仍兼容读取，因此旧布局尚不具备严格的按目录隔离，不自动搬动用户文件。

保存前确认用户授权及独立目录。以下为示意路径，替换为实际选择的目录：

```powershell
python scripts/coach.py session 'C:/chosen/session.json' --data-root 'C:/chosen/personal-love-coach-data'
python scripts/coach.py answer 'C:/chosen/raw-answer.json' --data-root 'C:/chosen/personal-love-coach-data'
python scripts/coach.py record 'C:/chosen/result.json' --data-root 'C:/chosen/personal-love-coach-data'
python scripts/coach.py profile 'C:/chosen/profile.json' --data-root 'C:/chosen/personal-love-coach-data'
python scripts/coach.py show-session demo-session --data-root 'C:/chosen/personal-love-coach-data'
python scripts/coach.py case 'C:/chosen/custom-case.json' --data-root 'C:/chosen/personal-love-coach-data'
python scripts/coach.py progress --data-root 'C:/chosen/personal-love-coach-data'
python scripts/coach.py exam-status --level 2 --data-root 'C:/chosen/personal-love-coach-data'
```

示例文件在 [训练成绩示例](../assets/training-result.example.json) 和 [人物档案示例](../assets/relationship-profile.example.json)。它们完全虚构，不要作为用户真实记录导入。结构定义在 [成绩 Schema](../schemas/training-result.schema.json) 与 [对象 Schema](../schemas/relationship-profile.schema.json)。

`score` 只计算已由教练评审的五维分数，不读取文本来自动给分。`exam-status` 校验两个独立三题回合、目标等级、首次作答、无提示、无重题和及格条件；需要教练复核语义与未见题真实性。

考试成绩必须绑定已经存在且未完成的会话，`round_id`等于session的`id`；会话决定mode、等级和提示状态，题库决定题目等级与category。训练题、保留集、未登记题目或低等级题不能靠改成绩字段充当高级考试。`exam-status`还要求两轮会话均completed。旧版脱离会话的考试成绩可留作历史，但不作为晋级凭据。

`record` 每份记录单独原子保存、不覆盖，重复 ID 和重复题次报错。`profile` 新建 revision=1，更新必须递增revision、保留阶段历史并写 change_reason，旧版存 archive。与当前文件冲突时先确认事实，不覆盖。使用自定义代号，不用姓名、电话或联系方式作 ID。

`session` 保存三题进度；示例见 [训练会话](../assets/training-session.example.json)。新建 revision=1，更新递增；暂停后可恢复等待作答。不能删除已答题记录、清除提示历史或把训练转成独立考核；换题使用新会话ID。考核拿到提示后只能转为训练，不能保留考核资格。完成状态要求三题均已回答；实际答案与分数仍使用 `record` 保存。

已有考核转练习时设置 `mode: training`、`converted_from_exam: true` 并记录 `hint_used`；这允许本次继续讲解原考题，不把它当普通训练选题来源，也不得再将其用于独立考核。新建会话不能伪装成已转换考核。

推荐持久化顺序：创建会话 → 每题收原答即`answer` → 评分后`record` → 更新会话revision及已答ID → 三题均评分后completed。正式考核可以先保存三条原答、统一反馈时再写三条成绩，原答不会因未评分而丢失。

`answer`只保存首次原文，不要求分数；字段为`round_id`、`case_id`、`answer`、`date`、`hint_used`，例子见 [原答示例](../assets/raw-answer.example.json)。改进后的回答用`record`的attempt=2另存，不覆盖首次原文。`show-session`读取指定会话、原答、评分、剩余题目和待评分题目；paused恢复时在读回后用`session`递增revision改回awaiting_answers，再继续回答。

恢复输出的questions包含题干、等级与类别，不包含expected/failures等参考评价条件，避免把考核恢复变成提前给答案。

题库不足时，用`case`先登记三个新题，再开会话。例子见 [原创考题示例](../assets/custom-case.example.json)。需记录实际input、split、level、category、事实、未知、合格行为和失败条件；相同题干换ID会被拒绝。此校验不能自动识别语义相同的改写，教练仍须复核。数据中的cases不可覆盖已注册题；确需修订使用新ID并记录原因。

`progress` 把相同等级、类别、模式、评分版本、语料版本、记录来源和教学任务的首次作答分组；原始记录保留重练。旧资料版本为unknown并单列，verified_training=false，不能把该组的无提示比例当成已经核实的独立训练证据。独立合格率分母为无提示首次作答；行动完成率分母为已知结果的计划行动，另列未知数。未完成或无数据以 null 表示。

其中“独立”表示本次未提示，不代表从未练过。另列unseen_independent_count、unseen_independent_pass_rate与repeat_case_count，区分首次未提示和重复题；unassisted_mean_total只算无提示成绩。后续会话转练习/使用提示时，报告按最新会话状态保守重分类，旧成绩原文不会被修改。这些指标仍不能证明现实能力迁移。

写入期间有 `.write.lock`；并发写入失败时稍后重试。进程异常退出遗留锁时，先确认没有写进程再清理，不能盲目解锁。脚本拒绝符号链接、目录联接和 Skill 内数据目录。输出成功路径只说明本地保存成功，不等于跨设备同步或永久记忆。

档案或会话在归档成功后主文件提交中断，可直接重试同一修订；相同旧版归档会被复用，有内容冲突才要求人工复核。主文件使用唯一临时文件后原子替换，旧的临时文件不会阻断下一次写入。

## 3.3.0记录完整性与兼容

新训练成绩与考试成绩都需要已登记题目和会话。旧的无会话成绩可继续读取；需要主动导入时用`import-result FILE --reason '导入原因' --data-root DIR`，单独round_id，记录标记legacy-import、版本unknown，不作为独立晋级证据。现实行动可继续用mode=transfer，单列统计；不得改模式把模拟题冒充现实迁移。

新会话自动保存case_bindings（题干快照、内容摘要、版本及背景）与question_settings（逐题task/include_phase），更新会话时省略这两项会自动保留，不能偷换。可在初次session JSON中为每个题号指定`{"task":"judgment","include_phase":false}`；默认expression且不展示阶段。考试不允许展示阶段。question命令的临时参数不自动写入会话，恢复以开会话时保存的配置为准。

`show-session`优先恢复快照，输出binding_status与changed_case_ids；题库改变或题目删除后仍能复盘原题，但拒绝新作答或混评。不影响作答的审核日期、审核备注变化不会使题目失效。旧会话没有绑定时标为legacy-unverified，保留只读核查，不根据当前题库伪造旧版本；继续练习请开新ID的会话，不迁移旧答案为新首答，考试须另用未见题。

首答保存的原文、日期与提示状态相同才能幂等重试，字段不同会明确报错。若首答前实际用过提示但标记遗漏，填写[提示补正示例](../assets/hint-correction.example.json)，运行`correct-hint FILE --data-root DIR`。补正单向设为true，包含原因和日期；原答和成绩文件均不改写，读取时应用有效提示状态，成长统计与考试资格随之重算。首答之后才请求提示不属于首答事实补正，应记为后续练习；不能用补正接口抹掉提示。

多轮训练按[接续示例](../assets/practice-turn.example.json)运行`turn FILE --data-root DIR`。先有已保存首答，再从turn=1的assistant模拟反馈开始，user回答为turn=2，按角色交替、日期不倒退保存，simulation必须为true；相同记录可重试，不同内容不能覆盖。`show-session`恢复practice_turns。接续不创建成绩、题次或晋级资格。考试会话不允许写接续，需要先明确转为training；已完成的考试保持不可变，要练习另开训练会话并独立登记虚构练习题。

## 3.4.0双轨笔记与覆盖统计

```powershell
python scripts/coach.py learning-note 'C:/chosen/learning-note.json' --data-root 'C:/chosen/personal-love-coach-data'
python scripts/coach.py coverage --session-id demo-session --data-root 'C:/chosen/personal-love-coach-data'
```

`learning-note`需要id、round_id、case_id、date、kind。三种kind分别为reflection（用户自己的analysis，可选assistance=unassisted/assisted/unknown，缺省unknown）、response_status（status=skipped/cannot_formulate及reason）、coach_review（understanding、expression、action、scope、hypothesis、supporting_evidence数组、counterevidence数组）。见[分析示例](../assets/learning-note.example.json)、[暂时不会回应示例](../assets/response-status.example.json)与[Schema](../schemas/learning-note.schema.json)。不要把教练分析写成用户原始分析，也不把分析中想到的选项当实际承诺。

分析与点评须先保存首答；考试未completed时禁止写入这两种教学笔记，但可以标记缺失状态。先前已有评分或点评时，不能再声称新分析unassisted。首答提示与分析辅助状态分别记录，不追溯修改首答。response_status不能把已答改成未答；后来答出会保留曾经困难的事件。相同id和内容可幂等重试，不同内容须新增id；日期不倒退，工具自动绑定原答摘要及选题摘要。旧会话缺摘要时不补造来源。

`show-session`增加learning_notes；`progress`增加coverage。coverage中的selected_count指会话已选题次，不声称每题都已展示。answered_count可包括旧版保留的首次成绩，graded_count只计已评分首答；另列已答未评分、未答及pending/skipped/cannot_formulate。回答覆盖率只描述样本覆盖，不是能力或掌握率；reflection_notes_by_assistance是分析笔记条数，不是独立题次。未回答不创建0分记录，也不算完成三题或通过考核。

新题可登记learning_context（communication_function与signal_clarity）；新会话绑定该信息，评分时从绑定题目取值，不接受成绩自行改标签。progress再按这两个条件分组，coverage按条件计数。旧题和旧成绩缺少标签时保留unknown，不按题目位置或用户印象补齐。新笔记位于授权目录的learning-notes，不上传到源码仓库，不改变既有评分与晋级条件。
