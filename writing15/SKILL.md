---
name: research-proposal-writer
description: 依据课题指南、前期数据与文献写开题报告/研究计划书：七要素（背景-问题-目标-技术路线-阶段计划-风险-预期成果）逐节落位，研究问题必须含指标、阈值、对照与时间点，目标挂到路线步骤与考核指标，里程碑按月排布并核对人力上限，风险写触发信号与备选方案。校验缺口是否推导到位、目标-路线-指标-成果是否对齐、计划是否覆盖全周期、风险是否四要素齐全；材料缺失如实标 partial，不编造前期数据。
---

# 开题报告与研究计划书（立得住 + 对得上 + 排得开 + 说得清）

核心命题：开题报告被否，很少因为"写得不好看"，而是四件可核查的事没过：
**缺口不是从背景推出来的**、**目标与路线各写各的**、**24 个月排了 40 人月的活**、
**风险只有一句"及时调整"**。这四件事都能从结构上量出来。

## 何时使用 / 不使用

**使用**：博士/硕士开题报告、课题申报书的研究方案部分、内部立项计划书；
把一段研究想法收敛成可执行、可考核的方案。
**不使用**：写论文正文（写作01）；写方法与结果章节（写作09/10）；基金申请书的
国内外研究现状与经费论证（写作14）。

## 预算与结构（动笔前先按这个量写）

| 节 | 最低字数 | 必须含 |
|---|---|---|
| 研究背景与立项依据 | 350 | 已知（挂引用）→ 未知（缺口句）→ 待验证 |
| 研究问题与可证伪假设 | 150 | 指标 + 阈值 + 对照/时间点 |
| 研究目标 | 150 | 目标数 = 问题数 ×1–3，每个带指标与交付时点 |
| 技术路线 | 300 | 每步输入 → 处理 → 输出；标串行依赖与关键路径 |
| 阶段计划 | 150 | 起止月 + 工作量（人月），合计 ≤ 可用人力 |
| 风险与备选方案 | 150 | 触发信号 + 影响范围 + 备选方案 + 决策时点 |
| 预期成果与考核方式 | 120 | 交付形式 + 达标判据 |

全文 **≥1400 字**（`_nchars`：中文按字、西文按词×0.6、数字按个×0.6）。

## 门槛（定稿前逐条对照，达不到不要标 success）

| 项 | 门槛 | 谁检查 |
|---|---|---|
| 七要素齐备 | ≥6/7，缺项须写进 `uncertainty` | `validate_result.py` |
| 缺口具体 | 背景有缺口线索词，且与问题段主题词重叠 ≥2 | `validate_result.py` |
| 问题可证伪 | 指标 + 阈值 + 对照/时间点三类齐全 | `validate_result.py` |
| 目标对齐 | 四元组齐全率 ≥90%，指标要在正文呼应 | `validate_result.py` |
| 周期覆盖 | 里程碑覆盖 1..T，无空月 | `validate_result.py` |
| 里程碑不重叠 | 重叠 0 处 | `validate_result.py` |
| 人力相容 | 工作量合计 / 可用人力 ≤1.0 | `validate_result.py` |
| 风险完备 | 四要素齐全率 ≥90%，覆盖 4 类 | `validate_result.py` |
| 论断挂引用 | 背景/问题/目标/路线里 ≥60% | `validate_result.py` |
| 干净度 | 无 `【…】`/`TODO`/`待补` | `validate_result.py` |

## 执行顺序

### 第 0 步 · 读真实输入，先问三个数
读 `/input/case.json` + 材料（课题指南、前期数据、组内讨论）。开工前必须拿到：
**周期（月）**、**可用人力（人月）**、**考核指标要求**。缺哪项按 `references/edge-cases.md` 处置，
不要自己编一个"24 个月"就开写。

### 第 1 步 · 抽约束，列缺口
把材料里的已知结论、约束（周期/经费/伦理/设备）、前期数据的数字抄成一张表。
再从"已知"里推"未知"：写一句**缺口陈述**，它必须与第 2 步的问题共享主题词。

### 第 2 步 · 问题收敛成可证伪形式
1–3 个问题，每个都写成「指标 + 阈值 + 对照/时间点」。
不合格的写法："探究 X 的影响"。合格的写法见 `references/falsifiable-question.md`。

### 第 3 步 · 落骨架
```bash
python <skill_dir>/scripts/draft_outline.py --case /input/case.json \
    --out /app/work/proposal.md --plan-out /app/work/plan.json
```
七要素按检查表可识别的节名铺好，同时给一份 `plan.json` 空模板。

### 第 4 步 · 逐节写（六条硬规矩）
1. 背景每句带数字的都挂引用；缺口句单独成句并加粗，让评审一眼看到。
2. 问题段复制第 2 步的写法，句末写判断标准（越界即判不成立）。
3. 目标写成 `G1/G2/G3`，每条带指标与交付时点；数量与问题对应。
4. 路线写成 `R1..Rn`，每条三件事：输入、处理、输出；末尾一段写串行依赖与关键路径。
5. 计划写成 `M1..Mn`，每条四件事：起止月、名称、工作量、交付物；合计 ≤ 可用人力。
6. 风险 4–6 条，覆盖数据获取/方法可行性/进度/伦理合规四类，每条四要素齐全，
   决策时点必须早于该里程碑结束月。

### 第 5 步 · 落结构表（plan.json）
把 G/R/M/K 与阈值写进 `plan.goals / routes / milestones / risks`，
`cycle_months` 与 `capacity_pm` 从指南来。这张表是"对得上""排得开"的唯一依据，
正文与表必须同源——**先改表再改正文**，不要反过来。

### 第 6 步 · 落台账与自查
```bash
python <skill_dir>/scripts/build_outputs.py --result /app/output/result.json \
    --text /app/work/proposal.md --outdir /app/output
```
产出 `element-map.csv`（七要素字数）、`alignment.csv`（四元组）、
`schedule.csv`（月份/人月）、`risk.csv`（四要素）、`selfcheck.md`、`preview.pdf`（有 pandoc 时）。

### 第 7 步 · 跑门槛
```bash
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/work/proposal.md
```
`[fail]` 逐条修：要素缺就补节；缺口空泛就加重叠的主题词；
对齐不足就回 `plan.json` 补 route/metric/outcome；排不开就缩范围或调里程碑；
风险缺项就补触发信号与决策时点。

### 第 8 步 · 写 result.json
`case_id` / `status` / `result.manuscript`（全文）/ `result.plan`（结构表）/
`sources` / `uncertainty` / `changes`。`output_contract` 字段逐个覆盖；
`changes` 每条写清"改了哪一节、按什么依据改"。

## 异常处理

| 情况 | 处置 |
|---|---|
| 缺课题指南/周期/人力 | 先索要；要不到按最常见配置写并声明折算口径，标 `guideline_missing` |
| 周期过短 | 缩范围或把体内/长期步骤写成条件触发，标 `scope_adjusted` |
| 指标不可达 | 下调阈值并写依据，或改相对提升，标 `threshold_unreachable` |
| 经济/伦理未定 | 写成条件触发 + 风险条目，不写"已获批准" |
| 引用无法获取 | 只作背景引用，不用来支撑具体数值 |
| 学科规范冲突 | 选一个并注明标准号，另一写法进 `uncertainty` |
| 预算分项不符 | 调分项使合计 = 总额，或注明差额 |
| 预算将尽 | 先落七要素骨架 + 前四节 + plan，标 `partial` |

## 依赖与资源

Python 3.9+，脚本仅用标准库；`preview.pdf` 需 pandoc，缺失则跳过并如实记录。

- `scripts/proposal_gate.py` — 四把尺（缺口/可证伪/对齐/排期/风险），被下面三个脚本共用
- `scripts/draft_outline.py` — 七要素骨架 + `plan.json` 模板
- `scripts/validate_result.py` — 契约 + 门槛
- `scripts/build_outputs.py` — 四张台账 + 自查 + 预览
- `references/` — 七要素、可证伪问题、四元组对齐、排期可行性、风险矩阵、异常矩阵、方案边界
- `eval/` — 评分表、指标脚本、对照协议、验收表（运行案例时不必读）

## 最小示例

见 `examples/minimal-example.md`。
