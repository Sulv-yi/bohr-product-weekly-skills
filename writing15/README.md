# 使用说明（README）

## 一、这是什么

一个可被 Agent 调用的**开题报告与研究计划书**写作 Skill。给它课题指南、前期数据与约束
（周期、人力、考核要求），它产出：

1. 七要素齐全的稿件（可直接交给导师改）；
2. `plan.json` 结构表（目标/路线/里程碑/风险/预算）；
3. 四张核验台账（要素字数、四元组对齐、排期、风险）；
4. 自查报告与结果 JSON（含不确定项）。

它不做"更漂亮的文字"，它做的是**能被逐行核对的方案**。

## 二、安装与依赖

- Python 3.9+，脚本仅用标准库，无第三方依赖；
- `preview.pdf` 需要 pandoc + xelatex（缺失则跳过并如实记录）；
- 把本目录整体放进 Agent 的 skill 目录即可，入口 `SKILL.md`。

## 三、一次完整调用

```bash
# 1) 七要素骨架 + plan 模板
python scripts/draft_outline.py --case /input/case.json \
    --out /app/work/proposal.md --plan-out /app/work/plan.json

# 2) 逐节写稿，同时填 plan.json（先改表再改正文）

# 3) 台账与自查
python scripts/build_outputs.py --result /app/output/result.json \
    --text /app/work/proposal.md --outdir /app/output

# 4) 门槛（不通过按 [fail] 逐条修）
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/work/proposal.md
```

第 4 步通过的标准输出：

```
passed  case=selftest-001  status=success
  字数=1896 要素=7/7 缺口=具体 可证伪=是 对齐=100% 周期覆盖=是 重叠=0 工作量比=1.0 风险完备=100%/4类 引用绑定=89%
```

## 四、输入与输出

**输入**（`/input/case.json`）

| 字段 | 说明 |
|---|---|
| `case_id` | 案例标识，回填到 `result.json` |
| `task` | 任务说明：体裁、受众、格式 |
| `discipline` | 学科（术语与指标口径依此判断） |
| `cycle_months` / `capacity_pm` | 周期与可用人力，缺则按 edge-cases 处置 |
| `materials` | 课题指南、前期数据等材料路径 |
| `output_contract` | 必须覆盖的输出字段 |

**输出**（`/app/output/`）

| 文件 | 内容 |
|---|---|
| `proposal.md` | 七要素全文（主产物） |
| `element-map.csv` | 七要素 → 是否齐备 → 字数 / 门槛 |
| `alignment.csv` | 目标 → 问题 → 路线 → 指标 → 成果 → 时点 |
| `schedule.csv` | 里程碑 → 起止月 → 人月 |
| `risk.csv` | 风险 → 类型 → 触发信号 → 影响 → 备选 → 决策时点 |
| `selfcheck.md` | 全指标自查 + 待核清单 |
| `result.json` | `case_id` / `status` / `result.manuscript` / `result.plan` / `sources` / `uncertainty` / `changes` |
| `preview.pdf` | 有 pandoc 时的可读版 |

## 五、关键方法

| 方法 | 一句话 | 详见 |
|---|---|---|
| 缺口三段式 | 已知 → 未知 → 待验证，缺口句必须与问题共享主题词 | `references/falsifiable-question.md` |
| 可证伪四要件 | 指标 + 阈值 + 对照 + 时间点 | 同上 |
| 四元组映射 | 目标必须挂路线、指标、成果，正文要呼应指标 | `references/alignment.md` |
| 排期三约束 | 覆盖全周期、不重叠、工作量 ≤ 人力 | `references/schedule-feasibility.md` |
| 风险四要素 | 触发信号 + 影响范围 + 备选方案 + 决策时点 | `references/risk-matrix.md` |

## 六、适用与限制

**适用**：硕博开题、内部立项、课题申报的研究方案部分；把研究想法收敛成可执行方案。

**限制**：不判断科学价值；不替作者定阈值；不编造前期数据；不裁决学科规范冲突；
极短周期（≤6 个月）时人月门槛偏机械，应缩范围；人文艺术类题目"指标+阈值"的强制
需放宽并在 `uncertainty` 说明。

## 七、自查与维护

- 自查：`python eval/score_output.py --result … --case … --text … --baseline examples/baseline-scorecard.json --out scorecard.json`（16 项判定）；
- A/B：`python eval/compare_ab.py examples/baseline-scorecard.json examples/scorecard.json --md examples/ab-report.md`；
- 维护：阈值只在 `eval/rubric.json` 里改，不在下游脚本放宽；新增学科时改
  `proposal_gate.ELEMENTS` 的节名正则与 `RISK_TYPES` 的关键词。

## 八、本目录结构

```
SKILL.md                    入口（何时用 / 预算 / 门槛 / 执行顺序 / 异常）
scripts/                    proposal_gate.py · draft_outline.py · validate_result.py · build_outputs.py
references/                 七要素 · 可证伪问题 · 对齐 · 排期 · 风险 · 异常 · 方案边界（7 篇）
examples/                   selftest 全链 · baseline 对照 · minimal-example.md
eval/                       rubric.json · score_output.py · compare_ab.py · ab-protocol.md · acceptance.md
SCORING-MAP.md              评分维度 → 材料位置
```
