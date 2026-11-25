---
name: methods-experiment-section-writer
description: 依据配置文件、实验日志、数据说明等事实底稿，交付"六类要素齐全、数值可回溯、可按之复做"的方法与实验章节成稿本体与可核验附件（来源映射表、自检表）。先生成结构化成稿骨架，再抽要素表、填正文、对齐参数表，显式追问材料缺口。用于方法与实验章节写作、补写、改写与可复现性核验；不为顺畅补数值，不臆造未报告的设置。
---

# 方法与实验章节写作（成稿优先 + 结构门槛 + 数值可追溯）

核心命题：**交付的是章节成稿本身**。题面四问——写得全（步骤/设置/参数/数据/对照/复现六类齐全）、写得准（取值/版本/划分与配置日志代码一致，不补数值）、做得着（按章节可复做，版本环境种子命令给全）、说得住（缺口显式标注，限制落到具体失效场景）。只交校验脚本或只有主干几句=0 分；六要素并成两三段，也拿不到"完整性/可核验性"的分。

## 适用 / 不适用

适用：从配置/日志/代码说明撰写 Methods、Experimental Setup、参数表、数据集划分、对照实验、复现清单、Limitation。
不适用：无事实底稿的虚构方法；只要"讲个大概"的科普；结果/讨论章节。

## 篇幅与要素预算（动笔前先按这个量写，不要写完再补）

方法章节是要被他人照着复现的，一页纸的"方法与实验"不可能合格。按下列预算一次写足，
否则会被门槛打回，白白消耗请求预算。

| 要素 | 中文下限 | 必须含 |
|---|---|---|
| 实验步骤 | 450 字 | 从输入到产出编号的完整流水，每步写清输入/操作/输出；循环与终止条件单列 |
| 实验设置 | 250 字 | 硬件、软件与版本、环境依赖；不得只写"使用某框架" |
| 参数配置 | 300 字 + 表 ≥8 行 | 名称/取值/单位/作用对象/来源五列齐全；正文逐项解释为什么取这个值 |
| 数据集 | 250 字 | 来源、规模、划分方式、预处理、标注口径；划分必须写清随机种子或分层依据 |
| 对照与基线 | 250 字 | 基线对象/版本/是否同预算/指标/统计方式/重复次数六项齐全 |
| 复现与限制 | 250 字 | 代码版本/环境/种子/命令/数据获取/划分六项齐全；限制写到触发条件或阈值 |
| 全文 | 1800 字 | 六要素合计，不含参数表与引用 |

## 成稿门槛（定稿前逐条对照，达不到不要标 success）

| 项 | 门槛 | 谁检查 |
|---|---|---|
| 正文篇幅 | ≥1800 字（英文按词计 0.6 折算） | `validate_result.py` |
| 六要素 | 步骤/设置/参数/数据/对照/复现限制**各自成段**，顺序不颠倒 | `validate_result.py` |
| 参数表 | ≥8 行，含名称/取值/单位/作用对象/来源，带来源行 ≥80% | `validate_result.py` |
| 正文-表对齐 | 表中取值 ≥80% 在正文出现（不许两张皮） | `selfcheck.md` |
| 对照 | 基线对象/版本/是否同预算/指标/统计方式/重复次数，六项命中 ≥5 | `validate_result.py` |
| 复现 | 代码版本/环境/种子/命令/数据获取/划分，六项命中 ≥5 | `validate_result.py` |
| 限制 | 写到触发条件或阈值（如"体素 <0.01 m 时显存 >40 GB"），不用套话 | `validate_result.py` |
| 缺口 | 材料没有的，进 `questions_for_author` / `uncertainty`，不补造 | 人工 + `selfcheck.md` |

门槛未过的处置：**回第 3/4 步补齐**，不要改 status 绕过；确实补不出的留 `partial` 并写明缺什么。

## 执行顺序（按此推进，禁止跳到校验）

### 第 0 步 · 读真实输入
读 `/input/case.json` 与 `task.md`，确认写作范围、受众、文体、格式与 `output_contract`。**先读实际材料文件**（配置/日志/代码说明/数据说明），不从领域标签推断内容——题面明确"不依据错误标签补造数据"。工作目录 `/app/work`，产物到 `/app/output`。

### 第 1 步 · 先落骨架（保证六要素齐全）
```bash
python <skill_dir>/scripts/draft_skeleton.py --case /input/case.json --out /app/work/draft_skeleton.json
```
生成含 steps/setup/parameters/dataset/baselines/reproducibility/limitations 各槽位与来源槽的 JSON 骨架。**不要跳过**：即使后续中断也留完整半成品。

### 第 2 步 · 抽取要素表
按 `references/element-extraction.md` 把材料抽成结构化表，每类要素一条并附来源：
- 步骤：`输入/操作/输出/判断条件`，有序，不把多步压成一句
- 参数：`名称/取值/单位/作用对象/来源`（config/日志/代码/作者确认）
- 数据集：名称、版本、规模、预处理、划分比例与随机方式、子集用途
- 对照：基线对象与版本、是否同预算、评价指标、统计方式、重复次数
- 环境：硬件、软件版本、随机种子、命令、数据获取方式

### 第 3 步 · 填骨架 = 成稿
写成 `/app/output/section.md`，小节顺序：方法步骤 → 实验设置 → 参数（表格）→ 数据集与划分 → 对照实验 → 可复现性与限制。每个数值/版本/条件必须能在要素表找到来源。
```bash
python <skill_dir>/scripts/align_params.py /app/work/elements.json /app/work/params.json
```
抓无来源数值与串位（判 `fabricated_value`）。**写作与核对分离**：先成稿，再逐条对齐，禁止边写边补数值。

### 第 4 步 · 复现清单 + 缺口追问
```bash
python <skill_dir>/scripts/check_reproducibility.py /app/output/result.json
```
六项（代码版本/环境/种子/命令/数据获取/划分）缺失项写入 `reproducibility_gaps` 与 `uncertainty`；材料不足、配置冲突、参数无来源、版本不明 → `questions_for_author` 显式追问，**blocking 项存在时 status 不能是 success**。限制条件落到具体失效场景。

### 第 5 步 · 落可核验附件
```bash
python <skill_dir>/scripts/build_outputs.py --draft /app/output/section.md \
    --result /app/output/result.json --outdir /app/output
```
产出 `source-map.csv`（要素 → 文件/位置/原句 → 落在哪一节）、`selfcheck.md`（结构指标 + 未清项）、`preview.pdf`（环境有 pandoc/xelatex 时）。有 PDF 即为可目视核验证据；没有则如实写明不可用。

### 第 6 步 · 校验（成稿之后，不是代替成稿）
```bash
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/section.md
```
报错逐条修；`--text` 传入成稿才能把 section.md 的结构算进去。

### 第 7 步 · 输出 result.json
按 `output_contract` 逐字段原样覆盖，至少含：

```json
{
  "case_id": "...",
  "status": "success | partial | unable | refused",
  "result": {
    "section": "可编辑章节正文（或指向 /app/output/section.md）",
    "elements": {"steps": [], "setup": {}, "parameters": [], "dataset": {}, "baselines": [], "reproducibility": {}},
    "reproducibility": {"code_version": "", "env": "", "seed": "", "command": "", "data": "", "split": ""},
    "questions_for_author": [{"question": "", "blocking": false}],
    "limitations": [{"scenario": "", "reason": "", "scope": ""}]
  },
  "sources": [{"id": "", "claim": "", "file": "config.yaml", "section": "train", "quote": "原句"}],
  "uncertainty": [{"type": "not_reported", "note": ""}],
  "changes": [{"from": "", "to": "", "reason": ""}]
}
```

`sources` 的定位方式：正文用编号时给 `cite_key`（如 `"3"`）；用文件名引用时 `file` 与正文写法一致（如正文写 `（config.yaml）`）；用图表或特定值定位时给 `locator`（如 `"Table 1"`、`"8f5c2a1"`）。无来源的设置标 partial + uncertainty，不硬标 success。

## 异常处理

| 情况 | 处置 |
|---|---|
| 材料缺失 / 参数无来源 | `questions_for_author` + `uncertainty`，状态 `partial`，不补数值 |
| 配置冲突 | 列出冲突项与各自来源交作者裁定，不自行选一个 |
| 数据集版本不明 | 标追问项，不臆造版本或规模 |
| 权限不足 / 材料不可读 | 状态 `unable`，说明原因与接管位置 |
| 日志只给曲线截图 | 只报能从图读出的量级并标 `not_reported`，不换算成精确值 |
| 时间/请求预算将耗尽 | 先存 `section.md` 与 partial 版 `result.json`，再增量补；不交空壳 |

## 依赖与资源

Python 3.9+，全部标准库；路径相对本目录，不依赖个人文件。`preview.pdf` 需要环境有 pandoc 或 xelatex，缺失则跳过并如实记录。

- `scripts/draft_skeleton.py` — 六要素成稿骨架（先跑，保证不空壳）
- `scripts/extract_params.py` — 从配置/日志文本抽取参数骨架
- `scripts/align_params.py` — 正文数值与参数表对齐，抓无来源/串位
- `scripts/check_reproducibility.py` — 复现六要素完整性检查
- `scripts/quality_gate.py` — 六要素/参数表/对照/复现的结构度量，被下面两个脚本共用
- `scripts/build_outputs.py` — 生成 `source-map.csv` / `selfcheck.md` / `preview.pdf`
- `scripts/validate_result.py` — 契约 + 结构门槛（不达标即报错）
- `references/` — 要素抽取、参数对齐、复现清单、缺口追问、核对清单、方案边界
- `examples/` — `minimal-example.md`、`selftest-*`（示例案例与输出）、`baseline-*`（对照侧示例）

`eval/` 是给评审与复现用的：评分表、指标脚本、A/B 协议、验收表。**运行一个案例时不需要读 `eval/`**。

## 限制

不提交预制答案，不为顺畅补数值，不臆造材料外事实。脚本捕获可机械判定的硬伤（无来源数值、正文与参数表不一致、复现要素缺失、限制是套话、空壳成稿）；数值本身对不对、限制条件是否真实，需人工对着材料复核，并在 `uncertainty` 如实说明。
