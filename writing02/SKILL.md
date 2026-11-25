---
name: academic-language-polishing
description: 润色学术文本但严格保持原意与证据——先建逐段对齐的润色工作台，再逐句校对语法用词、统一全篇术语、贴合目标文体语域，同时守住限定强度、数字单位、引用编号与图表指向，最后用成稿门槛与指标脚本自查，产出「原文-改文-类型-理由」逐句对照和可复核的 scorecard。当用户要求润色、校对、改写、学术英文优化、中译英表达调整、术语统一或按期刊/学位/基金文体改写时使用。不用于纯内容问答、事实核查或代写新结论。
---

# 学术语言润色（语义守恒 + 逐句可核 + 增益可验）

## 用途与触发

**该用**：用户给出已有稿件/段落/摘要，要求润色、校对、改写、术语统一、语气贴合、中译英表达优化、按特定期刊或文体调整。

**不该用**：纯内容问答、纯翻译请求、纯格式转换、要求补做实验或新增结论、要求"把结论写强一点"——此时先说明边界，不擅改（详见 `references/exception-matrix.md`）。

## 交付物清单（运行时必须产出，缺一即不合格）

| 文件 | 内容 | 由谁产生 |
|---|---|---|
| `/app/output/result.json` | `case_id` + 全部 `output_contract` 字段 + `result.paragraphs`（逐段 pid/original/polished）+ `result.change_log`（逐句四元组）+ `result.term_decisions` + `sources` + `uncertainty` + `changes` | Agent 写 |
| `/app/output/scorecard.json` | 守恒率、术语一致性、覆盖率、改动率等**实测指标** | `eval/score_output.py` 生成，**不许手写** |
| `/app/output/ab_plan.json` | 对照条件声明：同一原文/术语表/rubric、3 次重复、盲评安排 | Agent 按 `eval/ab-protocol.md` 写 |

`scorecard.json` 必须由脚本从原文与改文实际比对得出。手写或自评的数字一律视为无效证据。

## 五个硬目标

| 目标 | 含义 | 失败表现 |
|---|---|---|
| 段段有着落 | 润色结果与原文**逐段一一对齐**（pid + original + polished） | 只交"改写要点"或检查报告 |
| 改得对 | 语法、句法、搭配、标点、用词错误被真正修掉 | 换种说法掩盖错误 |
| 说得像 | 符合目标文体语域，术语全篇统一 | 口语化、宣传化、术语漂移 |
| 没改坏 | 限定强度、数据单位、引用编号、图表指向、因果/相关关系原样保持 | may→is、约30%→30%、[3]→[4] |
| 讲得清 | **每一处实际改动**都有原文、改文、类型标签与理由 | 只给改后全文，或只给一条示例修改 |

第五条是本题最容易丢分的地方：题面要的是**逐句**修改说明，不是"逐段润色 + 一条示例"。
凡是句子发生了改动，就必须有对应的一条 `change_log` 记录。

## 工作流（严格顺序）

### 1. 建立约束清单（不可跳过）

从 `/input/case.json` 与 `/input/task.md` 提取：
- `case_id`、`output_contract` 的每个字段名（**逐个字段都要在 result.json 里有对应**）
- 目标文体（期刊论文 / 学位论文 / 基金申请 / 审稿回复 / 英文摘要）、受众、目标语言
- 术语表路径；无表时从稿件抽取候选并标 `needs_confirmation`

```bash
python scripts/build_polish_draft.py --case /input/case.json --out /app/work
```

产出 `polish_plan.json`（逐段锁定项）、`polished_skeleton.md`（一段对一段的骨架）、`term_seed.md`。

### 2. 术语先定，再改文

按 `references/terminology-governance.md` 建 `term_map`：原写法 → 唯一统一写法。
同一概念只允许一种译法；缩写首次出现给全称。冲突**不自行裁决**，记入 `questions_for_author`。

```bash
python scripts/term_consistency.py --map /app/work/term_map.tsv --text /app/work/polished_draft.md
```

### 3. 逐段润色，最小编辑

按 `references/minimal-edit.md`：只动该动的地方，能改分句就不重写整句，能改词就不改结构。
按 `references/register-by-genre.md` 调整语域。逐段写入 `result.paragraphs`。

### 4. 逐句写修改说明（四元组）

每处改动一条：

```json
{"original": "原文该句", "revised": "改后该句",
 "change_type": "grammar|terminology|register|semantics_guard|...",
 "reason": "为什么必须改；不改会错在哪"}
```

`change_type` 取值见 `scripts/validate_result.py` 的 `CHANGE_TYPES`。
**改动了几何句，就要有几条记录**，覆盖率低于 0.9 会被 `score_output.py` 判不通过。

### 5. 自查（两道，都要过）

```bash
# 结构门槛：段落对齐、锁定项守恒、强度不变
python scripts/check_polish.py /app/output/result.json --plan /app/work/polish_plan.json
# 指标证据：算出 scorecard.json
python eval/score_output.py --result /app/output/result.json \
    --case /input/case.json --out /app/output/scorecard.json
# 契约总校验（success 时强制要求 scorecard 已通过）
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --out /app/output/check.json
```

三道全过才算完成。任何一道报错，回到对应步骤修，不跳过。

### 6. 声明对照条件

按 `eval/ab-protocol.md` 写 `ab_plan.json`：同一份原文、同一术语表、同一 `eval/rubric.json`、
3 次重复取中位数、盲评顺序随机。只声明你实际做到的，没做的写 `not_done` 并说明原因。

## 指标口径（可被他人复现）

`eval/score_output.py` 计算的指标与阈值在 `eval/rubric.json`：

| 指标 | 阈值 | 说明 |
|---|---|---|
| `segment_coverage` | 1.0 | 原文每段都有润色段 |
| `invariant_conservation` | 1.0 | 数字/单位/引用/图表指向既没丢也没新增 |
| `hedge_conservation` | 1.0 | 每段限定词数量变化 ≤1 |
| `term_uniqueness` | 1.0 | 术语统一译法在改文中真的出现 |
| `edit_note_coverage` | ≥0.9 | 有改动就有四元组记录 |
| `sentence_change_rate` | ≤0.6 | 超过视为整段重写而非最小编辑 |

阈值改在 `rubric.json` 里，不改代码——这样别人可以用同一份脚本、不同标准复核。

## 与已有方案的边界

见 `references/innovation-boundary.md`。要点：本 Skill 不竞争"文笔"，
竞争的是**可核验性**——润色后仍能证明哪些没变、为什么改、改得对不对。

## 资源

```
SKILL.md                          本文件
scripts/
  build_polish_draft.py           建逐段工作台（plan + 骨架 + 术语候选）
  check_polish.py                 结构门槛（段落对齐/锁定项守恒/强度不变）
  lock_invariants.py              锁定数字/单位/引用/图表/限定词/否定词
  term_consistency.py             术语一致性与候选抽取
  invariant_guard.py              改动前后不变量全文比对
  validate_result.py              契约总校验（success 强制要求 scorecard）
eval/
  rubric.json                     100 分细则落成的可执行条目与阈值
  score_output.py                 实测指标 → scorecard.json
  compare_ab.py                   A/B 差值判定
  ab-protocol.md                  对照协议（条件一致、3 次重复、盲评）
  acceptance.md                   硬门槛与盲评表
references/
  minimal-edit.md                 最小编辑原则与分句级策略
  terminology-governance.md       术语表建设与冲突处置
  register-by-genre.md            各文体语域规则
  hedge-and-modality.md           限定强度与情态守恒
  source-mapping.md               来源映射写法
  exception-matrix.md             异常处理矩阵
  innovation-boundary.md          与基础 Agent/通用工具/翻译/人工的边界
examples/
  minimal-example.md              最小调用示例（示意，非正式案例结果）
GITHUB_URL.txt                    公开仓库地址
```

## 边界与诚实要求

- 不把示例集成绩写成正式案例成绩。
- 材料不足、术语冲突、文体不明，如实写入 `uncertainty`，`status` 标 `partial`。
- `manual_review_items` 允许非零；为凑 0 而隐藏缺口比留空更糟。
- 运行预算有限（64 次请求 / 900 秒）：先存 partial 产物，再逐步改进，不一次做完所有事。
