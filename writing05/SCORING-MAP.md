# 评分点 → 证据位置对照表

题面五维 100 分。下表说明「这一分靠什么拿、在哪能查到」，最后附 60 秒自查命令。
本表不含自评分——自评不被采信，能复算的指标才作数。

## 实际效果（40）

| 评分点 | 分 | 对应产物 | 复核方式 |
|---|---|---|---|
| 任务完成度 | 15 | `draft.md`（成稿）+ `result.claims[]` + `result.evidence_table[]` 三段齐备 | `validate_result.py` 的 `task_completion` 判定；字数 ≥1400、论断 ≥12 |
| 结果正确性 | 15 | `claim-map.csv`（每条论断的定位与强度）+ `sources[]` + `uncertainty[]` | 元数据齐备率 ≥90%、占位符 0、相称率 ≥80% |
| 结果完整性 | 5 | `result.conflicts[]` / `conflict_search_note` | 二者之一非空，否则判未处理冲突 |
| 结果可核验性 | 5 | `claim-map.csv` + `evidence-table.md` | 定位率 ≥90%、证据行覆盖率 ≥90%（编号—摘录—定位—理由四件齐） |

要点：**只交成稿拿不到这 40 分的完整性/可核验部分**。附件不是附赠，是评分点本体。

## 使用增益（25）

| 评分点 | 分 | 对应证据 | 说明 |
|---|---|---|---|
| 质量增益 | 15 | `examples/ab-report.md` | 同材料同字数下，定位率/强度判定率/相称率/证据覆盖 7 项变好、0 项变差 |
| 效率增益 | 5 | `eval/ab-protocol.md` 第 4 节 + `open_items` | 待人工确认项不增加、绑定率不下降；返工前置到脚本判定 |
| 增益可验证性 | 5 | `eval/rubric.json` + `eval/score_output.py` + `eval/compare_ab.py` | 第三方可用同一 rubric 重跑；无 baseline 时判 `n/a` 不判 pass |

## 创新增益（15）

| 评分点 | 分 | 对应证据 | 说明 |
|---|---|---|---|
| 新增能力 | 5 | `scripts/claim_split.py` | 论断切分 + 强度规则判定 + 语气相称校验，三件基础 Agent 不稳定具备 |
| 方法改进 | 5 | `assets/strength-table.json` + `claim_split.grade/hedge_ok` | 定级从「靠语感」变成「设计线索→样本线索→复现线索」的规则推导 |
| 创新证据 | 5 | `references/innovation-boundary.md` | 对基础 Agent / 写作助手 / 引文工具三方边界写清，含做不到的 5 条 |

## 可靠体验（10）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 调用与易用性 | 3 | `SKILL.md` 七步流程 + `examples/minimal-example.md` |
| 运行稳定性 | 4 | 脚本仅标准库；同一输入重复运行结果一致；缺字段不崩 |
| 异常处理 | 3 | `references/edge-cases.md` 六类 + `SKILL.md` 异常表 |

## 生态贡献（10）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 文档完整性 | 3 | `README.md` + `references/evidence-strength.md` |
| 资源可复用性 | 4 | `references/claim-units.md` + `scripts/claim_split.py` + `assets/strength-table.json`（可按学科替换） |
| 分享推广价值 | 3 | `GITHUB_URL.txt` + `references/edge-cases.md` |

## 60 秒自查（五条命令）

```bash
cd <skill_dir>

# 1 门槛：契约 + 证据九条
python scripts/validate_result.py examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-draft.md

# 2 切分：论断单元数与挂引用比例
python scripts/claim_split.py --text examples/selftest-draft.md

# 3 附件：claim-map / evidence-table / selfcheck 可生成
python scripts/build_outputs.py --result examples/selftest-result.json \
    --draft examples/selftest-draft.md --outdir /tmp/o05

# 4 评分卡：16 项 pass / 0 fail
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --draft examples/selftest-draft.md \
    --baseline examples/baseline-scorecard.json --out /tmp/o05/card.json

# 5 对照：质量/效率增益是否成立、有无变差项
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/o05/card.json
```

## 当前实测数值（可复算）

| 指标 | 值 | 门槛 |
|---|---|---|
| 成稿字数 | 1425 | ≥1400 |
| 论断条数 / 成稿论断单元 | 46 / 46（覆盖 100%） | ≥12 / ≥80% |
| 精确定位率 | 100% | ≥90% |
| 强度判定率 | 100% | 100% |
| 表述相称率 | 89% | ≥80% |
| 证据行 / 覆盖 | 46 / 100% | ≥90% |
| 来源条数 / 元数据齐备 | 12 / 100% | ≥12 / ≥90% |
| 冲突处置 | 已列 1 对相反结论 + 检索范围说明 | 非空 |
| 占位符 | 0 | 0 |
