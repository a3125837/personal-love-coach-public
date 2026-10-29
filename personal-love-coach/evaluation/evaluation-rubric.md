# 质量回归与运行方式

## 数据与隔离

3.1.1的58条题干、事实、未知和评判要求均独立重写为虚构场景：训练38、考核10、保留10。8条阶段题不充当独立保留评测。语料版本`fictional-2026-10-27-v2`，与旧版本题号相同也不能当作相同题干；旧版前向检查不验证新语料。作者已逐条审阅场景、事实、未知、合格行为与失败条件，状态为 `author-reviewed-not-independently-validated`。没有真实聊天数据。保留集不是教学材料，只有评测时加载。当前Lv2有两组三题独立考题，其余等级不足时按流程原创补齐并登记。

## 评测层次

1. `python scripts/coach.py validate`：ID、分集、能力覆盖、引用及结构。
2. `python -m unittest discover -s tests -v`：算分、否决、晋级、历史、隔离、版本与路径测试（tests在开发项目中，不在分发包中）。
3. Promptfoo离线回放：加载已写明是人工编写的输出样本，验证provider、prompt装配和JSON断言。**这不是实际模型行为测试**。
4. 真实模型回归：通过 `scripts/build_eval.py` 指定目标provider与judge，保留集测试事实忠实、边界、校准、表达、行动与路由。它会把Skill与相应参考文件装成文本输入，不具备完整代理工具调用环境，另须在目标代理环境验证读取/持久化行为。
5. 独立人工盲评与真实迁移：后续采集。未运行就明确待验证，不能用作者示范回放冒充。

## 离线配置

```powershell
python scripts/build_eval.py
npx promptfoo eval -c evaluation/promptfooconfig.yaml --no-cache -o evaluation/reports/offline.json
```

默认provider是本地 `replay-provider.cjs`，只返回 `offline-fixtures.jsonl` 的明确人工输出，不调用网络。Promptfoo需要单独安装；版本记录写在实际报告中，不在Skill中捆绑node_modules。

## 真实模型配置

先由使用者选择目标和评审模型，在环境中配置所需密钥。不要把真实私聊作为样本发给服务。模型评测会产生费用；本次开发未配置密钥或自动调用付费模型。

```powershell
python scripts/build_eval.py --provider YOUR_PROVIDER_ID --judge YOUR_JUDGE_ID --output evaluation/live.yaml
npx promptfoo eval -c evaluation/live.yaml --no-cache -o evaluation/reports/live.json
```

配置中的 `llm-rubric` 断言包含每案的合格/失败条件，评审者在评分时才看到；被测模型提示不包含预期答案、失败条件或考题答案。每案输出用JSON信封承载mode、facts、unknowns、action、reply、user_response，便于结构验证；用户日常交互无需输出JSON。

## 门禁与差异复核

事实编造、拒绝后继续施压、绕过边界、训练泄题及对象混淆属于关键失败，保留集全部通过才可宣称这批行为测试通过。自然度评分需独立人工复核，不能只凭关键词或模型自评。

比较新旧版本时固定输入、目标模型/参数、judge、运行日期、prompt哈希和rubric版本；同时检查新未见案例。关键退化不发布稳定质量结论。分歧保留双方理由，不简单平均。发布报告区分结构通过、语义通过、人工复核和现实效果。
