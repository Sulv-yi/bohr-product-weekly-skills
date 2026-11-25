---
name: full-paper-writer
description: 依据研究材料（实验记录、图表、统计输出）与给定文献写出结构完整的学术论文初稿：先建材料索引，再按八类章节写，交付可编辑稿件 + 材料索引 + 章节/引用/图表核验表。校验章节齐备度、引用闭合、图表题注与正文提及成对、正文数值可回溯到材料位置、声明字段齐备；缺项如实标 partial，不编造数值与文献。当任务要求"根据材料写论文初稿""补全论文章节""把实验结果写成可投稿稿子""核对正文与图表是否一致"时使用。
---

# 学术论文写作（材料索引先行 + 八类章节 + 数值回溯）

核心命题：**交付一份能直接进入修改环节的稿子**，而不是提纲、写作建议或素材堆叠。
题面四问——写得实（数值、单位、样本量、图注都来自材料）、引得对（每条引用真的支撑那句，
元数据可查）、全得起来（章节、图表、参考文献、声明字段齐备）、改得动（层级、编号、引用格式保留）。

## 何时使用 / 不使用

**使用**：从实验材料起稿；按期刊/学科模板补全章节；把结果写成可投稿初稿；核对正文与图表一致性。
**不使用**：只润色语言（写作02）；只写引言与相关工作（写作08）；只写方法与实验（写作09）；
只做 LaTeX 编译（写作13）。

## 篇幅与结构预算（动笔前先按这个量写）

| 章节 | 最低字数 | 必须含 |
|---|---|---|
| 摘要 | 150 | 问题 → 方法 → 主要结果（带数值）→ 边界 |
| 引言 | 250 | 脉络 → 未解问题 → 本文工作 → 贡献逐条（每条挂引用或图表） |
| 材料与方法 | 220 | 材料、设备与参数、样本量、统计方法 |
| 结果 | 200 | 只写观察，按图序或问题序，每个数值指明出处 |
| 讨论 | 250 | 与文献对照、机制推测标注、局限落到方法与样本 |
| 结论 | 80 | 只复述结果支持的结论 |
| 数据可得性 | 20 | 数据/代码位置与获取途径 |
| 参考文献 | 12 条 | 与正文编号一一对应 |

全文 **≥1800 字**（中文按字，西文按词 ×0.6，数字按个 ×0.6）。
材料索引 **≥8 条**，图表题注 **≥2 组**（题注与正文提及成对），声明字段 **≥2 类且含数据可得性**。

字数口径解释：把数字计入是有意的——方法与结果天然参数密集，只数汉字会把
「参数写得很实」的段落判成篇幅不足，反过来鼓励注水。

## 成稿门槛（定稿前逐条对照，达不到不要标 success）

| 项 | 门槛 | 谁检查 |
|---|---|---|
| 全文篇幅 | ≥1800 字 | `validate_result.py` |
| 章节齐备 | 八类中 ≥6 类达到该节字数 | `validate_result.py` |
| 参考文献 | ≥12 条，正文编号全部闭合 | `validate_result.py` |
| 图表配对 | 题注与正文提及成对 ≥2 组，无孤立题注 | `validate_result.py` |
| 材料索引 | ≥8 条，条条有 locator | `validate_result.py` |
| 论断绑定 | ≥50% 论断句挂引用编号 | `validate_result.py` |
| 数值回溯 | 正文数值能在材料/来源里找到同值（告警线 90%） | `selfcheck.md` |
| 声明字段 | ≥2 类，必须含数据可得性 | `validate_result.py` |
| 干净度 | 无 `【…】`/`{{…}}`/`TODO`/`待补` | `validate_result.py` |

门槛不过就回第 3 步补内容，不改 status 绕过。

## 执行顺序（按此推进，禁止跳到校验）

### 第 0 步 · 读真实输入
读 `/input/case.json` 与 `/input/task.md`。字段以实际文件为准：`case_id` / `task`|`instruction` /
`material`|`paper`|`files` / `venue`|`style` / `output_contract`。**先读材料本体**（PDF/文本/表格/图），
不从标题或标签猜内容。工作目录 `/app/work`，产物写 `/app/output`。

### 第 1 步 · 建材料索引（先于正文）
把材料里的每个可用事实落成 `{material_id, kind, locator, claim, cite_key, quote}`：
`locator` 要能被人直接打开（文件+行号/表号/图号），`quote` 取原始片段不转述。
规范见 `references/material-index.md`。**这一步做完再写正文**，否则必然出现无出处的数值。

### 第 2 步 · 落章节骨架（保证形态）
```bash
python <skill_dir>/scripts/draft_skeleton.py --case /input/case.json \
    --out /app/output/manuscript.md
```
八类章节 + 声明位 + 图表位一次生成，每节标出最低字数与必须回答的问题。
骨架里的占位符定稿前必须清空——空标题不得分（按字数判）。

### 第 3 步 · 逐节写实
- 摘要：先写结果数值，再补问题与方法，最后一句写边界。
- 引言：贡献逐条，每条挂引用或图表编号，无对应的删掉。
- 方法：参数进表、正文给范围与依据；样本量写实数，不写"若干"。
- 结果：只写观察；每个数值后标 `（图 n）` 或 `（表 n）`；解释留给讨论。
- 讨论：与文献对照写"一致/不一致 + 可能原因"；机制推测必须写"可能"；局限写到方法与样本层面。
- 结论：只复述结果支持的结论，不出现新论断。
- 声明：数据可得性写清位置与限制；利益冲突无则明写"无"。

### 第 4 步 · 对齐图表与引用
- 正文写「（图 1）」就必须有 `图 1　…` 题注，反之亦然；题注写清是什么、n、误差棒含义。
- 引用编号与文献表一一对应；表里有的正文没引，删条目或补引用。

### 第 5 步 · 落可核验附件
```bash
python <skill_dir>/scripts/build_outputs.py --result /app/output/result.json \
    --text /app/output/manuscript.md --outdir /app/output --min-chars 1800
```
产出 `section-map.csv`（各节字数与门槛）、`material-index.csv`（材料 → 正文位置 → 引用 → 定位结果）、
`cite-audit.csv`（正文编号 ↔ 文献条目 ↔ 是否闭合）、`selfcheck.md`、`preview.pdf`（有 pandoc 时）。

### 第 6 步 · 跑门槛
```bash
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/manuscript.md
```
报错逐条修。`--text` 必须传，否则稿件侧指标算不到。

### 第 7 步 · 写 result.json
| 字段 | 内容 |
|---|---|
| `case_id` | 原样 |
| `status` | `success`/`partial`/`blocked`/`unanswerable`；门槛不过只能 partial |
| `result.manuscript` | 稿件全文（与 manuscript.md 一致） |
| `result.material_index` | 材料索引条目数组 |
| `sources` | `{id, cite_key, file, section, quote}` |
| `uncertainty` | `{type, note}`，type ∈ `not_reported/undetermined/conflict/needs_human_confirmation` |
| `changes` | 与上一版差异（首版写初稿来源） |

`output_contract` 列出的字段必须逐个出现，缺失即判失败。

## 异常处理

| 情况 | 处置 |
|---|---|
| 缺图注 | 补题注（内容/n/误差棒含义）；补不出改用文字描述 |
| 正文与图表冲突 | 以原始数据为准改正文，记 `conflict` |
| 缺原始数据 | 只写汇总值，不写逐样本统计，标 `not_reported` |
| 文献只有题录/摘要 | 只支撑摘要级论断；方法或样本量结论不得引它 |
| 材料超长 | 先建索引再按节取用；未读部分写进 uncertainty，不假装读过 |
| 材料自相矛盾 | 列 `conflict`，正文取更保守的一组并注明 |
| 文件缺失/无权限 | 不猜内容，`status=blocked`，写清需要谁提供 |
| 预算将尽 | 先落已有章节 + 索引 + 文献表，标 `partial`，再增量补 |

完整矩阵见 `references/edge-cases.md`。

## 依赖与资源

Python 3.9+，脚本仅用标准库；PDF 用 PyMuPDF/pdfplumber 读取，无文字层走 OCR 并标注置信度；
`preview.pdf` 需要 pandoc，缺失则跳过并如实记录。

- `scripts/draft_skeleton.py` — 八类章节骨架（先跑，防空壳）
- `scripts/sections_gate.py` — 结构度量（章节/图表配对/引用闭合/数值回溯），被下面两个脚本共用
- `scripts/validate_result.py` — 契约 + 成稿门槛
- `scripts/build_outputs.py` — `section-map.csv` / `material-index.csv` / `cite-audit.csv` / `selfcheck.md` / `preview.pdf`
- `references/` — 章节规范、材料索引规范、来源处理、证据与不确定性、异常矩阵、方案边界
- `examples/` — 最小调用 + selftest（含 baseline 与 A/B 报告，均标注为演示）

`eval/` 是给评审与复现用的（rubric、指标脚本、对照协议、验收表）。
**运行一个案例时不需要读 `eval/`**，别让它占用请求预算。

## 最小示例

见 `examples/minimal-example.md`：从材料索引到章节、附件、门槛结论的完整形态。
示例标注为演示数据，不代表正式案例结果。
