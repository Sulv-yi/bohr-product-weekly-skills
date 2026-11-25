---
name: evidence-driven-writing
description: 文献证据驱动写作：把一段需要文献支撑的写作任务落成「论断清单—证据表—成稿」三段交付，每条论断带原文摘录、页/节/段定位与四档证据强度，并校验正文语气与该强度相称。先切分论断单元，再逐条定级配证据，最后写成稿并跑证据门槛；缺来源宁可标 partial，不编造引用、不把弱证据写成共识。当任务要求"依据文献写/改一段学术文字""给每句找到依据""标注证据强度""处理冲突证据"时使用。
---

# 文献证据驱动写作（三段交付 + 强度定级 + 逐条可回查）

核心命题：**交付的不是一段好文字，而是一份能被别人逐条查证的证据链**。
题面四问——找得到（每条论断落到具体文献的具体段落）、对得上（原文真的支持这句，
不是支撑了一句相近但更弱/更强的话）、说得准（证据强度与正文语气相称，相关性不写成因果）、
复得现（编号/摘录/定位/理由四件齐，他人可独立回查）——四问答不全，文笔再好也拿不到分。

## 何时使用 / 不使用

**使用**：依据给定文献写引言/讨论/综述段；给已有稿件补依据；标注证据强度；
处理冲突证据；把"有引用"升级成"有定位"。
**不使用**：只需润色语言（用写作02）；需要生成材料外的新知识；纯格式转换。

## 三段交付（缺任一段即不合格）

| 段 | 产物 | 要求 |
|---|---|---|
| 论断清单 | `result.claims[]` + `claim-map.csv` | 覆盖全文论断单元，每条有 `claim_id`、原句、定位、强度、强度依据 |
| 证据表 | `result.evidence_table[]` + `evidence-table.md` | 每条论断 ≥1 行，行内有来源、原文摘录、定位、设计与样本依据、等级、与论断的关系 |
| 成稿 | `draft.md` | 可直接进入修改流程，论断句挂引用编号 `[n]`，与证据表编号体系分开 |

**只交成稿 = 只做了三分之一**。附件不是附赠材料，是本题"结果可核验性"的直接得分点。

## 篇幅与证据预算（动笔前先按这个量写，不要写完再补）

| 项 | 下限 | 说明 |
|---|---|---|
| 成稿正文 | 1400 字（西文按词 ×0.6） | 少于这个量，论断单元撑不到 12 个 |
| 论断条数 | ≥12 | 材料文献不足时把全部用上并在 `uncertainty` 写明，不编条目 |
| 证据行 | ≥论断条数 × 0.9 | 一条论断可对多行（多篇文献），`context` 行不顶替 support |
| 来源条数 | ≥12 | 每条含 file + page/section + quote |
| 单篇来源支撑 | ≤3 条论断 | 超过要检查是否过度引用 |
| 强度判定 | 100% | 允许 `insufficient`，不允许空着或 `needs_review` 残留 |

## 交付门槛（定稿前逐条对照，达不到不要标 success）

| 项 | 门槛 | 谁检查 |
|---|---|---|
| 正文篇幅 | ≥1400 字 | `validate_result.py` |
| 论断覆盖 | 清单覆盖成稿论断单元 ≥80% | `validate_result.py` |
| 精确定位 | ≥90% 论断带页/节/段定位 | `validate_result.py` |
| 强度判定 | 100% 落在 `strong/moderate/weak/insufficient` | `validate_result.py` |
| 表述相称 | ≥80% 论断的语气与强度相符 | `validate_result.py` |
| 来源 | ≥12 条，元数据齐备率 ≥90% | `validate_result.py` |
| 证据闭合 | ≥90% 论断有证据行，`claim_id` 全部存在 | `validate_result.py` |
| 冲突 | `conflicts[]` 非空或 `conflict_search_note` 已写 | `validate_result.py` |
| 干净度 | 无 `【…】`/`{{…}}`/`TODO`/`待补` | `validate_result.py` |

门槛不过的处置：**回第 3 步补证据或降表述强度**，不改 status 绕过；
确实补不出的写进 `uncertainty` 并标 `partial`。

## 执行顺序（按此推进，禁止跳到校验）

### 第 0 步 · 读真实输入
读 `/input/case.json` 与 `/input/task.md`。字段以实际文件为准：`case_id` /
`task`|`instruction` / `material`|`paper`|`files` / `audience`|`style` / `output_contract`。
**先读材料本体**（PDF/文本），不从标题或标签猜内容。工作目录 `/app/work`，产物写 `/app/output`。

### 第 1 步 · 切论断单元
```bash
python <skill_dir>/scripts/claim_split.py --text /app/output/draft.md --json /app/output/units.json
```
先把"哪句是要被判定的论断"定下来。切分口径见 `references/claim-units.md`：
含可检验断言的句子才成单元；标题、题注、参数罗列、导航句不算。
**先有单元才能算覆盖率**——这是本题"每条论断"要求的操作前提。

### 第 2 步 · 抽证据并定级
对每个单元找来源：原文摘录（可在材料里搜到的原句）、定位（页/节/段）、
设计与样本线索。用规则先判一档：
```bash
python <skill_dir>/scripts/claim_split.py --quote "<原文摘录>" --claim "<论断原句>" --grade
```
返回 `strength` + `basis` + `hedge_ok`。**建议不等于定论**：可改判，但改判理由要写进
`strength_basis`。命中不了线索一律 `insufficient`，不允许默认 `moderate`。
口径见 `references/evidence-strength.md`，机读版在 `assets/strength-table.json`。

### 第 3 步 · 写正文，让语气配得上强度
- `strong`：可直接陈述；`moderate`：限定条件、不用绝对化词；
  `weak`：必须带限定语；`insufficient`：写未知或移出正文。
- 相关性不写成因果，单篇小样本不写成领域共识，未达显著写成"趋势一致但未达显著"。
- 论断句末挂引用编号，编号对参考文献表，与 `claim_id` 是两套体系。
写法细则见 `references/uncertainty-language.md`。

### 第 4 步 · 落三段产物
`draft.md`（成稿）、`result.json` 里的 `claims[]` 与 `evidence_table[]`。
段与段必须对得上：`claims[].claim` 是成稿原句（不缩写），
`evidence_table[].claim_id` 指向已存在的 `claim_id`。

### 第 5 步 · 生成可核验附件
```bash
python <skill_dir>/scripts/build_outputs.py --result /app/output/result.json \
    --draft /app/output/draft.md --outdir /app/output --min-chars 1400
```
产出 `claim-map.csv`（论断→定位→强度→证据→是否在成稿定位到）、
`evidence-table.md`（含原文摘录与等级依据）、`selfcheck.md`（指标 + 未清项）、
`preview.pdf`（有 pandoc 时；没有则如实写明不可用）。

### 第 6 步 · 跑门槛
```bash
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/draft.md
```
报错逐条修。**`--text` 必须传**，否则成稿侧指标算不到。

### 第 7 步 · 写 result.json
| 字段 | 内容 |
|---|---|
| `case_id` | 原样 |
| `status` | `success`/`partial`/`blocked`/`unanswerable`；门槛不过只能 partial |
| `result.draft` | 成稿全文（与 draft.md 一致） |
| `result.claims` | `{claim_id, claim, locator, strength, strength_basis, flags[]}` |
| `result.evidence_table` | `{evidence_id, claim_id, source, quote, locator, basis[], strength, relation}` |
| `result.conflicts` | `[{claim_id, sources, note}]`，无冲突则空数组 |
| `result.conflict_search_note` | 检索范围与未见冲突的说明 |
| `sources` | `{id, cite_key, file, page/section, quote}` |
| `uncertainty` | `{type, note}`，type ∈ `not_reported/undetermined/conflict/needs_human_confirmation` |
| `changes` | 与上一版的差异（首版写初稿来源） |

`output_contract` 里列出的字段必须逐个原样出现，缺失即判失败。

## 异常处理

| 情况 | 处置 |
|---|---|
| 文献不可得（只有题录） | 该条判 `insufficient`，论断降级或移入待核清单，标 `partial` |
| 仅有摘要 | 只支撑摘要级断言；方法/样本量相关论断不得用该条 |
| 原文与摘要矛盾 | 以全文为准，写 `conflicts[]`，正文写明不一致 |
| 证据相互冲突 | 列冲突 → 正文写不一致与可能原因 → 强度降级 |
| 扫描件/无文字层 | 走 OCR，标注页范围与置信度；公式符号列"未能确认" |
| 文件缺失/无权限 | 不猜内容，`status=blocked`，写清缺什么 |
| 预算将尽 | 先落 partial 版三段产物，再增量补；不交空壳 |

完整矩阵见 `references/edge-cases.md`。

## 依赖与资源

Python 3.9+，脚本仅用标准库；`preview.pdf` 需要 pandoc（无则跳过并如实记录）。

- `scripts/claim_split.py` — 论断切分 + 证据强度规则判定 + 语气相称校验
- `scripts/evidence_gate.py` — 结构与证据度量（被下面两个脚本共用，口径写在文件头）
- `scripts/validate_result.py` — 契约 + 证据门槛
- `scripts/build_outputs.py` — `claim-map.csv` / `evidence-table.md` / `selfcheck.md` / `preview.pdf`
- `assets/strength-table.json` — 四档强度与关系类型（可按学科替换）
- `references/` — 切分口径、强度定级、不确定性与冲突、异常矩阵、方案边界
- `examples/` — 最小调用 + selftest（含 baseline 与 A/B 报告，均标注为演示）

`eval/` 是给评审与复现用的（rubric、指标脚本、对照协议、验收表）。
**运行一个案例时不需要读 `eval/`**，别让它占用请求预算。

## 最小示例

见 `examples/minimal-example.md`：从材料到论断清单、证据表、`result.json`、附件的完整形态。
示例明确标注为示意，不代表正式案例结果。
