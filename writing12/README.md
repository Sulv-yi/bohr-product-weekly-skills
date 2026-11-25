# 使用说明（README）

## 一、这是什么

一个可被 Agent 调用的**学术翻译与双语写作** Skill。给它一份学术材料与任务说明，
它产出：

1. 段级双语对照稿（`P01 EN / ZH` 结构，可直接逐段改稿）；
2. 术语表（锁定译法 + 禁用变体）；
3. 三张核验台账（术语审计、对齐图、数值台账）；
4. 自查报告与结果 JSON（含不确定项与人工确认项）。

它不做"更长的译文"，它做的是**能复核的译文**。

## 二、安装与依赖

- Python 3.9+，脚本仅用标准库，无第三方依赖；
- `preview.pdf` 需要 pandoc + xelatex（缺失则跳过并在自查里如实记录）；
- 把本目录整体放到 Agent 的 skill 目录即可，入口为 `SKILL.md`。

## 三、一次完整调用

```bash
# 1) 落段级骨架（读 case.json 里的 materials）
python scripts/draft_bilingual.py --case /input/case.json --out /app/work/bilingual.md

# 2) 按术语表逐段译，填 ZH 位（人工或 Agent 执行，此步是本 Skill 的主体工作）

# 3) 落台账与自查
python scripts/build_outputs.py --result /app/output/result.json \
    --text /app/work/bilingual.md --outdir /app/output

# 4) 跑门槛（不通过就按 [fail] 逐条改）
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/work/bilingual.md
```

第 4 步通过的标准输出形如：

```
passed  case=selftest-001  status=success
  段=10 覆盖=100% 标记=100% 术语落地=100% 漂移=0 数值=100% 量级错=0 边界改动=0 限制语=100% 译文字数=360
```

## 四、输入与输出

**输入**（`/input/case.json`）

| 字段 | 说明 |
|---|---|
| `case_id` | 案例标识，回填到 `result.json` |
| `task` | 任务说明：语向、受众、文体、输出形态 |
| `source_lang` / `target_lang` | 语向 |
| `segments` | 期望的段号列表（可选；不填则按材料实际段数） |
| `materials` | 原文材料路径 |
| `output_contract` | 必须覆盖的输出字段 |

**输出**（`/app/output/`）

| 文件 | 内容 |
|---|---|
| `bilingual.md` | 段级双语对照稿（主产物） |
| `term-audit.csv` | 术语 → 锁定译法 → 出现段 → 漂移 |
| `align-map.csv` | 段号 → 原文首 40 字 → 译文首 40 字 → 状态 |
| `number-audit.csv` | 每个数值 → 值 → 单位 → `landed`/`MISSING`/`MAGNITUDE_ERROR` |
| `selfcheck.md` | 全指标自查 + 漂移/边界/漏译清单 |
| `result.json` | `case_id` / `status` / `result.bilingual` / `result.terms` / `sources` / `uncertainty` / `changes` |
| `preview.pdf` | 有 pandoc 时的可读版 |

## 五、关键方法

| 方法 | 一句话 | 详见 |
|---|---|---|
| 先建表后动笔 | 术语表是对齐与核查的共同底座 | `references/term-consistency.md` |
| 段号主键 | 所有核查落到 `Pxx`，漏段立刻可见 | `references/alignment.md` |
| 数值按值比对 | 不做字面比对，防"万/百万"混淆 | `references/number-and-units.md` |
| 标记归一化 | `Fig. 2a` 与「图 2a」等价，`图 2` 不等价 | `references/alignment.md` §4 |
| 边界只平移不升级 | `may` → 「可能」，不 → 「导致」 | `references/boundary-and-negation.md` |

## 六、适用与限制

**适用**：期刊摘要/正文/图注的中英互译；已有译稿的术语与数值核对；整篇双语对照交付。

**限制**：不判断文笔；不统一原文矛盾；不补缺失引用；术语表的学科裁决由人负责；
1–2 段的极短材料上建表成本高于收益；非学术文体（诗歌、广告、口语）不适用。

## 七、自查与维护

- 自查：`python eval/score_output.py --result … --case … --text … --baseline examples/baseline-scorecard.json --out scorecard.json`
  ，16 项判定逐条给出 pass/fail；
- A/B：`python eval/compare_ab.py examples/baseline-scorecard.json examples/scorecard.json --md examples/ab-report.md`；
- 维护：新增术语并回 `examples/term-table.json`；阈值只允许在 `eval/rubric.json` 里改，
  不允许在下游脚本里放宽。

## 八、本目录结构

```
SKILL.md                    入口（何时用 / 预算 / 门槛 / 执行顺序 / 异常）
scripts/                    bilingual_gate.py · draft_bilingual.py · validate_result.py · build_outputs.py
references/                 术语 · 数值 · 对齐 · 边界 · 语域 · 异常 · 方案边界（7 篇）
examples/                   term-table.json · selftest 全链 · baseline 对照 · minimal-example.md
eval/                       rubric.json · score_output.py · compare_ab.py · ab-protocol.md · acceptance.md
SCORING-MAP.md              评分维度 → 材料位置
```
