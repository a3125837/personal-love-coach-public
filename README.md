# 个人恋爱教练 · Personal Love Coach

面向中文恋爱、相亲与长期关系的 AI 教练 Skill。帮助你看清互动中的事实、自然表达好感、判断关系是否适合继续，并通过模拟练习改善沟通。

**当前版本：4.0.0** · [更新记录](personal-love-coach/CHANGELOG.md) · [Skill 入口](personal-love-coach/SKILL.md) · [工具指南](personal-love-coach/scripts/USAGE.md)

这是供 AI 助手加载的 Skill，包含指令、参考指南、虚构教学资源与本地记录工具。需要具备文件读取能力的 AI 环境；模型由使用环境提供。

## 从这里开始

| 入口 | 你可以这样说 | 教练会做什么 |
|---|---|---|
| A · 真实聊天 | “这句话怎么理解、怎么回？” | 区分事实、推测和未知，给一个最推荐回复与下一步 |
| B · 综合训练 | “开始三题训练，先等我回答。” | 提供虚构情境，作答后点评，按实际反馈继续互动 |
| C · 复盘成长 | “看看我最近的判断和表达有什么问题。” | 分别核对理解、措辞和行动，用支持证据与反例修正判断 |
| D · 系统学习与考核 | “练习话题延伸”或“开始正式考核” | 按需学习、练习，或进入无提示三题考核 |

四入口对应底层六种工作模式：聊天分析、回复指导、模拟训练、正式考核、约会与婚恋、复盘成长。真实聊天需求可以随时打断训练，之后恢复。

## 4.0.0 更新了什么

本版增加[互动创造引擎](personal-love-coach/references/interaction-engine.md)，让辅导从修改单句延伸到连续互动：

- **8 个模块、40 项能力**：按场景组合话题、表达、自我披露、情绪承接、幽默与互动技巧，并明确适用前提和常见误用。
- **100 个原创话题入口**：20 个破冰、30 个浅层共鸣、30 个深入了解、20 个浪漫表达；提供开场、分享与衔接思路，属于话题脚手架。
- **11 类分支案例**：覆盖初识、回复简短、日常分享、互相调侃、情绪低落、暧昧、邀约、约会、冷场、拒绝和重新联系。学习视图提供三种表达和四类反馈分支。
- **连续接续练习**：支持 3–5 轮模拟，根据积极回应、普通回应、纠正或停止信号调整，不只评价第一句话。
- **更自然的表达选择**：内部比较至少三种不同方向，真实聊天通常只展示一个推荐版本、1–3 个短气泡；认真、低落或拒绝场景可以全程认真回应。

上述资源独立于原评分题库，不计作新考题。教材只用于方法提炼，未随仓库分发原始教材；全部内置案例与示例独立虚构。

## 关系递进与互动边界

关系判断采用 P1–P8 八段式：初识、熟悉、好感、暧昧、恋人确认、稳定交往、婚前准备、婚姻经营。分别核对好感投入、当下亲近意愿和关系共识；阶段可以停留、回退或结束，不能仅凭一句话判定升级。

调情、昵称、玩笑和邀请以双方意愿及当下反馈为前提。冷读保持试探且允许纠正；推拉仅采用无伤害的反差与真实欣赏；自我披露和经历回调必须真实。明确拒绝优先于模糊积极信号，停止推进也是正确行动。

阶段和分数是辅导工具，不是人格诊断、喜欢概率或现实关系成功率。

## 安装与使用

### 安装到 Codex

```shell
git clone https://github.com/a3125837/personal-love-coach-public.git
```

将仓库中的 **`personal-love-coach/` 整个文件夹**复制到你的 Skills 目录：

| 系统 | 默认目标目录 |
|---|---|
| Windows | `%USERPROFILE%\.codex\skills\personal-love-coach\` |
| macOS / Linux | `~/.codex/skills/personal-love-coach/` |

使用自定义 `CODEX_HOME` 时，放到其 `skills/` 下。更新前备份自己对同名 Skill 的修改。新会话中输入：

```text
$personal-love-coach
开始三题综合训练，先让我回答，不要提前给参考答案。
```

也可以直接提出具体需求：

```text
帮我分析这段聊天，区分事实与猜测，给一个可执行的下一步。

帮我改这条回复，保留我的用词，只改最影响理解的一处。

我想练习自然表达好感。模拟对方普通回应、转话题或拒绝时的接续。

复盘我的训练，同时列出已答、未评分和未回答，不只看平均分。
```

其他支持本地 Skill 的环境可按其安装规则加载该文件夹；支持项目文件读取的环境可从 [SKILL.md](personal-love-coach/SKILL.md) 开始按需读取。纯对话辅导不要求运行脚本。

### 本地工具

需要结构检查、检索或经授权保存记录时，使用 **Python 3.10+**；工具仅依赖标准库。进入 `personal-love-coach/` 后运行：

```shell
python scripts/coach.py validate
python scripts/coach.py question DT-001 --task expression
python scripts/interaction.py capabilities C01
python scripts/interaction.py topics T001
python scripts/interaction.py branches B01
```

分支案例默认只展示题面；主动学习时可加 `--view study` 查看表达示例和反馈分支。检索不会自动创建成绩、会话或晋级资格。完整记录流程见[工具指南](personal-love-coach/scripts/USAGE.md)。

## 训练、评分与晋级

每轮三题，五维分别为自然表达、边界感、反馈判断、互动处理和关系推进，每维 0–4 分，总分 **20 分**。

- 单题至少 16 分且无重大边界错误为合格；合理维持、收尾或退出也能得高分。
- 正式晋级需要同等级两轮不同题集，三题全部独立通过，并核查未见题、无提示及完成状态；等级为 Lv0–Lv6。
- 首答、个人分析、教练点评和多轮接续分别记录。后续分析不覆盖首答，接续不增加考试题数。
- 未回答不记零分；已答、待评分、未答、跳过和暂时不会回应分别统计。

原评分题库共 **112 道独立虚构案例**：60 道训练、42 道考试、10 道保留评测，另有 16 条行为评测探针。新增 40 项能力、100 个话题和 11 类分支属于教学资源，不能混作正式考题。

## 数据与隐私

保存个人记录前需取得用户授权，并选择 **Skill 目录之外**的数据目录。真实聊天、个人成绩、对象档案和分析笔记保存在该目录，不提交到源码仓库。工具不会自动联系对象或上传个人记录。

公开仓库不包含私人分享对话、真实人物材料或原始教材。公开历史从干净快照建立，与原私有仓库历史独立。

## 动态交互图

[个人恋爱教练-交互图.html](docs/个人恋爱教练-交互图.html) 支持搜索、路径追踪、缩放、主题切换及导出，便于查看模式、资料与本地工具之间的关系。

下载 HTML 后用 Chrome 或 Edge 打开即可，样式与脚本内嵌；GitHub 文件页只显示源码。该图保留 **3.0.1 历史架构快照**，尚未更新到 4.0.0；当前流程以 Skill 入口为准。它不会自行调用 AI 或执行本地工具。

## 项目结构

```text
personal-love-coach/
  SKILL.md          模式入口与共同规则
  references/       关系阶段、互动引擎和参考指南
  workflows/        六种工作模式
  training/         训练协议、评分题库和互动教学资源
  scripts/          本地记录、检索与评测配置工具
  schemas/          数据结构定义
  assets/           独立虚构输入示例
  evaluation/       保留评测、行为探针和验证报告
docs/               设计说明与动态交互图
tests/              程序回归测试
development/        数据构建与发布工具
```

## 验证与限制

在仓库根目录运行：

```shell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -q
python personal-love-coach/scripts/coach.py validate
python personal-love-coach/scripts/build_eval.py
node development/verify_offline.cjs
```

Windows PowerShell 可先设置 `$env:PYTHONUTF8='1'`，统一测试子进程编码。

4.0.0 已通过 **106 项程序测试、结构校验和 10 条离线回放**，见[验证报告](personal-love-coach/evaluation/reports/verification-4.0.0.md)。离线回放使用手写样本，只检查适配器与断言流程；这些结果不代表真实模型建议质量或现实恋爱效果已获验证。模型语义效果、独立人工评分一致性及现实迁移仍待评估。

## 版本与许可

以[本公开仓库](https://github.com/a3125837/personal-love-coach-public)为最新开发和发布基准。历史报告描述相应版本当时的验证范围。

- [版本记录](personal-love-coach/CHANGELOG.md)
- [来源与采用方式](personal-love-coach/references/sources-and-rules.md)
- [第三方许可说明](personal-love-coach/THIRD_PARTY_NOTICES.txt)

项目尚未指定整体开源许可证；公开可见不等于已授予开源使用许可。第三方声明仅适用于对应内容。
