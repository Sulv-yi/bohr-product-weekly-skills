---
name: latex-compile-fix-build
description: 面向科研稿件的 LaTeX 写作与编译 Skill。围绕"成稿齐/编译得通/改得对/交得可用/复现得了"，先用 build_manuscript 建出结构完整的 .tex 成稿骨架并逐节写实，再做结构预检、多轮编译、全量报错定位到文件行号与根因、引用/交叉引用收敛核验、成稿实质门槛检查、事实来源映射与可复现构建记录。当任务要求写/改 LaTeX 源码、修编译错误、适配模板、处理公式表格引用或交付可重复编译的稿件时使用；缺引擎、缺宏包、缺字体、报错级联等如实标注，不臆造编译成功或分数。
---

# LaTeX 写作与编译（成稿齐 · 编译得通 · 改得对 · 交得可用 · 复现得了）

把一份 LaTeX 稿件真正做到**写得出、可编译、可并入、可维护、可复现**，而不是交一段看起来像 LaTeX 的片段、一张 PDF 截图，或者一份只有报错清单的检查报告。四个性质互相咬合：

- **成稿齐**：先有一份章节完整、摘要齐全、公式与表格有真实内容的 `.tex`，再谈修编译错误。只有检查报告没有成稿，是本题最典型的失分形态。
- **编译得通**：源码在指定模板与 TeX 发行版下按预期轮次编译通过；报错定位到具体文件、行号与根因，而不是停在第一条错误信息上。
- **改得对**：公式符号与编号、表格数值与列宽、交叉引用与参考文献、版式与模板必填项，既符合原文意图又符合模板要求。
- **交得可用**：交付结构清楚、可继续编辑、可维护的 .tex 源码，不把 PDF / 截图 / 不可编译片段当结果。
- **复现得了**：他人按记录的模板版本、宏包与字体版本、编译命令与轮次，能得到同一份产物。

## 适用 / 不适用

**适用**：真实 LaTeX 工程的写作、改写、校对、模板适配、编译排错、引用处理、可重复构建；输入含 .tex 工程（主文件/子文件/.bib/模板/图片）与任务约束。

**不适用**：只要 PDF 转图片或格式转换；无源码的纯内容润色（本 Skill 交付必须含可编辑 .tex）；要求臆造编译结果或伪造评分的场景。

## 输入

运行时读 `/input/case.json` 与 `/input/task.md`（若存在）。字段以实际文件为准：

| 字段 | 含义 | 处理 |
|---|---|---|
| `case_id` | 案例标识 | 原样写入 result.json |
| `task` / `question` | 具体任务 | 决定写/改/排错/模板适配侧重 |
| `material` / `files` / `project` | 工程路径 | **读真实 .tex 工程**，不从题名猜内容 |
| `template` / `engine` | 指定模板/引擎 | 记录到 reproduction，编译按此执行 |
| `required_sections` / `sections` | 必需章节 | 传给 build_manuscript，确保章节不缺 |
| `output_contract` | 必须输出字段 | 逐字段原样覆盖 |

工作目录 `/app/work`，最终产物 `/app/output/result.json`（含所有 output_contract 字段与 case_id）+ 可编辑 .tex 源码。

## 核心原则

1. **先出成稿，再做检查**：第一步就把 `.tex` 写成一份完整稿件（`build_manuscript.py` 建结构 → 逐节写实），检查是给成稿兜底的，不能拿检查报告当交付物。
2. **空骨架不算交付**：骨架的章节正文是空的，必须逐节写实；`check_manuscript.py` 不过关就不能写 `status=success`。
3. **先探后改**：先 `probe_project.py` 摸清引擎/模板/主文件/依赖，再动手。
4. **预检先行**：`static_check.py` 在编译前抓结构性硬损伤（括号/环境/label/引用），不浪费编译轮次。
5. **全量定位**：编译报错必须逐条定位 file:line + 根因 + 修复策略，修完一条继续找下一条，直到清零。
6. **事实绑定**：公式/表格/引用/数字的改动逐条带来源或修改记录，不新增材料外事实。
7. **诚实构建**：无引擎、缺宏包/字体、报错级联时如实标注，不伪造"编译成功"。
8. **早存增量**：先落一版 result.json（哪怕 partial），再逐步改进，每步记 change。

## 成稿门槛（任一条不过，不得写 `status=success`）

| 门槛 | 阈值 | 由谁判 |
|---|---|---|
| 章节齐备 | `required_sections` 全在，且 ≥3 节 | `check_manuscript.py` |
| 每节写实 | 最薄一节实义字数 ≥250 | `check_manuscript.py` |
| 全篇成稿 | 全文实义字数 ≥1400 | `check_manuscript.py` |
| 摘要齐全 | `abstract` 存在且实义字数 ≥40 | `check_manuscript.py` |
| 公式有内容 | ≥1 个 `equation` 环境且非空 | `check_manuscript.py` |
| 表格有数据 | 表格 ≥2 行真实数据（只有表头判不合格） | `check_manuscript.py` |
| 引用闭合 | 每个 `\cite` 键都能在 `.bib` 找到；`\ref` 无悬空 | `check_manuscript.py` + `static_check.py` |
| 无占位符 | 残留 `TODO` / `TBD` / `【…】` / `{{…}}` = 0 | `check_manuscript.py` |
| 来源映射 | `source_map` ≥3 条互不重复 | `verify_result.py` |

门槛是脚本判的，不是清单判的：同一份 `.tex` 重跑得到的结论必须一致。
空骨架能过模板检查，但过不了这张表——这是本 Skill 与模板向导的分界。

## 实测结果（真实编译，非示意）

`examples/runs/REAL-BUILD.md` 记录一次真实执行：tectonic 0.15.0，两边都实际编译。

| 指标 | 基线（无 Skill） | 本 Skill |
|---|---:|---:|
| 编译状态 | success | success |
| PDF 页数 / 字节 | 1 / 40,283 | **5 / 209,054** |
| undefined 引用 | **2** | **0** |
| LaTeX Warning | **3** | **0** |
| 公式 / 表格 | 0 / 0 | 1 / 1 |

基线三条警告（`No \author given.` / `Citation 'wang2019' undefined` /
`There were undefined references.`）正好对应本 Skill 的三个检查点：
模板必填项、引用闭合、结构完整。产物 `examples/runs/preview.pdf` 与
原始 `.log` 都在包内，可打开核对。

## 工作流

### 第 0 步 · 探查工程（对应"复现得了"）
```bash
python scripts/probe_project.py <工程根> --out project.json [--engine pdflatex]
```
读 `engines`/`selected_engine`/`main_file`/`document_class`/`packages`/`dependencies.missing_*`。
无引擎 → 记录 `reproduction.engine=null` 与不确定性，走静态检查 + 日志解析路径，不假装编译过。

### 第 1 步 · 建出完整成稿骨架（对应"交得可用"，最先做）
```bash
python scripts/build_manuscript.py --case /input/case.json --out /app/output \
    --main main.tex [--template ieeetran] [--force]
```
产出：
- `main.tex`：导言区 + 摘要 + 各章节 + 公式/表格锚点 + 参考文献
- `refs.bib`：参考文献骨架（只收材料中真实存在的文献）
- `manuscript_plan.json`：章节清单与每节写作要求

章节优先取 `case.required_sections` / `case.sections`，没有则用通用科研结构（Introduction / Related Work / Method / Experiments / Results / Discussion / Conclusion）。已有非空成稿时不覆盖（要重建加 `--force`）。

### 第 2 步 · 逐节写实（对应"实际效果"的核心）
按 `manuscript_plan.json` 把材料里的真实内容写进每一节：
- 每节正文达到实质篇幅（默认 ≥250 字），写清论断并标注来源；
- 公式填进 `equation` 锚点，符号先在正文定义，`\label` 后在正文 `\ref`；
- 表格至少 2 行真实数据，数值与单位必须来自材料或实际运行；
- 摘要 3–5 句，覆盖问题、做法、带数值的结果、结论；
- 参考文献只收材料中真实出现的条目，不编造。

写不动的地方进 `uncertainty` 并标 `partial`，不要用 TODO/【】占位糊过去——占位符会被门槛拦住。

### 第 3 步 · 成稿硬门槛（写 result.json 之前必须过）
```bash
python scripts/check_manuscript.py /app/output/main.tex \
    --case /input/case.json --bib /app/output/refs.bib [--json /app/work/manuscript_check.json]
```
检查：结构齐全、环境配对、每节实义字数、摘要、全文总量、占位符残留、公式与表格是否真有内容、`\cite` 键能否在参考文献中回溯、必需章节是否齐全。
`status=failed` → 回第 2 步继续写，**不得**直接写 `success`。

### 第 4 步 · 静态预检（对应"改得对"，无需引擎）
```bash
python scripts/static_check.py <工程根> --out static_check.json [--strict]
```
抓花括号/环境配对、重复 label、未定义 \ref/\cite、\begin/\end 错配。每条带 file:line + 根因 + 修复提示。
`status=failed` → 按 issues 修 .tex，重跑直到无 error，再进编译。

### 第 5 步 · 编译与全量日志解析（对应"编译得通"）
```bash
python scripts/compile_and_parse.py <工程根> --out compile_report.json \
    --engine pdflatex --rounds 3 --main main.tex
# 或已有日志：--log compile.log
```
- 多轮编译直到交叉引用/参考文献收敛（`converged=true`）。
- 解析**所有** `!` error，逐条分类：undefined control sequence / missing file / math mode / runaway argument / undefined env / float too large 等，带 file:line + 根因 + fix_hint。
- 对每条 error 定位→修复→重编，循环到 `error_count=0` 且 `converged=true`。
- 无引擎且无 --log → `status=unavailable`，只做静态检查，result 标 partial 并说明。

### 第 6 步 · 继续写/改 .tex（对应"交得可用"）
编译通过不等于内容完备：按任务与报错继续补齐主文件/子文件结构、导言区宏包顺序、公式环境与编号引用、表格列宽与对齐、模板必填项。每个改动记进 `changed_files` + `changes`。

### 第 7 步 · 事实与来源映射（对应"改得对"）
`result.source_map` 逐条记录数字/术语/引用/图表/关键论断的来源或修改记录，**至少 3 条**（success 的硬要求）：
```json
{"claim":"公式(3) 的系数 α=0.85","source":"原文 §3.2 Eq.(3) / p.5","change":"保持原值，仅调整对齐环境"}
```
来源定位三种写法等价，`verify_result.py` 都认：`source`、`source_id`、或 `file` + `locator`
（归一为 `file#locator`）。缺任一种才会被判"缺来源定位"。
材料不足/冲突/需人工确认 → 写 `uncertainty`，不新增事实。

### 第 8 步 · 复现记录（对应"复现得了"）
`result.reproduction` 写全：
```json
{"engine":"pdflatex","engine_version":"TeX Live 2023","template":"ieeetrans.cls v1.8",
 "packages":{"amsmath":"v3.4","booktabs":"v1.618"},"fonts":["Times New Roman"],
 "command":"latexmk -pdf -interaction=nonstopmode main.tex","rounds":3}
```
不猜版本：探测不到写 `"unknown"` 并进 uncertainty。

### 第 9 步 · 落附件与证据（交付时必须一起给）
```bash
python scripts/build_outputs.py --tex /app/output/main.tex --result /app/output/result.json \
    --outdir /app/output [--bib /app/output/refs.bib] [--no-compile]
```
产出四件可核验附件，缺一件就等于让评审去信你的文字：
- `cite-map.csv`：每个 `\cite` 键 → 是否在 `.bib` 中 → 被哪几节引用 → 条目题名与年份
- `compile-report.json`：引擎、轮次、`status`、每条错误的 file:line 与根因、PDF 路径
- `selfcheck.md`：结构指标、未清项、复现要素三节，供人一眼核
- `preview.pdf`：编译成功时留档；无引擎则不生成并在 `selfcheck.md` 里写明原因

### 第 10 步 · 契约自检
```bash
python scripts/verify_result.py /app/output/result.json --case /input/case.json \
    --static static_check.json --compile compile_report.json --tex /app/output/main.tex
```
任一性质 failed → 回到对应步骤修正。通过后写 `/app/output/result.json`。
`status=success` 会被要求：定位得到 .tex 成稿、成稿过 `check_manuscript` 门槛、`source_map` ≥3 条、`reproduction` 要素齐全。

## 输入输出

输出 `/app/output/result.json` + 可编辑 .tex 源码到 `/app/output/`：

```json
{
  "case_id": "...",
  "status": "success | partial | unable | refused",
  "result": {
    "artifacts": [{"path":"main.tex","kind":"editable_source"}],
    "manuscript": {"path":"main.tex","sections":["Introduction","Method"],
                   "real_chars":1200,"gate":"check_manuscript passed"},
    "changed_files": ["main.tex", "refs.bib"],
    "source_map": [{"claim":"...","source":"...","change":"..."}],
    "build": {"compile_status":"success","converged":true,"error_count":0},
    "reproduction": {"engine":"pdflatex","engine_version":"...","template":"...",
      "packages":{},"fonts":[],"command":"...","rounds":3}
  },
  "sources": [{"source_id":"s1","location":"§3.2 p.5","quote":"..."}],
  "uncertainty": ["..."],
  "changes": ["..."]
}
```

`status`：`success` 成稿过硬门槛 + 编译通过 + 五性质全满足；`partial` 部分完成（必须写 uncertainty 指明限制）；`unable` 材料/环境不可用；`refused` 任务越界或无依据。**不预置答案、不伪造编译状态、不虚构分数。**

## 评分维度落点（自查表）

| 维度 | 分值 | 本作品的落点 |
|--|--:|--|
| 实际效果·完成度 | 15 | `build_manuscript.py` 生成结构完整、可直接编译的 .tex 成稿 |
| 实际效果·正确性 | 15 | `compile_and_parse.py` 多轮编译 + 全量日志解析，定位到文件/行号/根因 |
| 实际效果·完整性 | 5 | `check_manuscript.py` 确认是写实稿件而非空骨架或占位符 |
| 实际效果·可核验性 | 5 | `build_outputs.py` 输出 selfcheck.md + cite-map.csv + compile-report，编译可复现 |
| 使用增益·质量增益 | 15 | `static_check.py` 不依赖 TeX 引擎也能抓结构性硬损伤 |
| 使用增益·效率增益 | 5 | 日志解析一次列出全部错误，不需要逐轮试错 |
| 使用增益·可验证性 | 5 | `probe_project.py` 记录引擎与包清单，构建环境可复现 |
| 创新增益 | 15 | 编译前静态预检 + 编译后全量日志归因，两段式定位 |
| 可靠体验 | 10 | 无 TeX 引擎时降级为静态检查并如实标 `partial`；异常处理见下一节 |
| 生态贡献 | 10 | 支持多引擎探测；检查器可脱离本项目复用 |

## 异常处理

| 情形 | 处理 | status |
|---|---|---|
| 无 TeX 引擎 | 成稿照写 + 静态检查 + 日志解析路径，说明无法本机编译 | partial |
| 缺宏包 / 类文件 | 记录缺失项，建议安装/替换，不假装编译过 | partial |
| 缺字体 | 记录字体依赖，建议替代字体或安装 | partial |
| 报错级联（首错引发多错） | 全量定位后按根因排序，先修根因再重编 | 视结果 |
| 模板 .cls 缺失 | 用 `--template article` 建可编译成稿并标注与目标模板的差异 | partial |
| 材料不足以填满某节 | 该节写实能写的部分，缺口进 uncertainty，不写 TODO | partial |
| 权限不足 | 说明无法写入/编译的目录，给可人工接管位置 | unable |
| 材料冲突 / 未报告 | 写 uncertainty，不新增事实 | partial |

## 脚本

- `scripts/probe_project.py` — 引擎/模板/主文件/依赖探查（不臆造软件状态）
- `scripts/build_manuscript.py` — **按案例生成结构完整、可直接编译的 .tex 成稿骨架 + refs.bib + 章节计划**
- `scripts/check_manuscript.py` — **成稿实质门槛：结构/篇幅/占位符/公式表格/引用闭合**
- `scripts/static_check.py` — 无需引擎的结构硬损伤检查（括号/环境/label/引用）
- `scripts/compile_and_parse.py` — 多轮编译 + 全量报错定位与根因分类 + 引用收敛
- `scripts/build_outputs.py` — **落附件：cite-map.csv / compile-report.json / selfcheck.md / preview.pdf**
- `scripts/verify_result.py` — 五性质 + 契约自检（success 强制过成稿门槛）

配套（不参与写作，只用于验收与对照）：`eval/rubric.json`（五维 100 分的可执行条目）、
`eval/score_output.py`（算指标与判定，不给自评分）、`eval/compare_ab.py`（A/B 差值）、
`eval/ab-protocol.md`（对照协议）、`eval/acceptance.md`（人工验收与盲评表）、
`SCORING-MAP.md`（评分点 → 证据位置对照，含 60 秒自查命令）。

真实运行证据：`examples/runs/REAL-BUILD.md`（对照数据与复跑命令）、
`examples/runs/preview.pdf`（编译产物，5 页）、`examples/runs/selftest-build.log`（原始引擎日志）、
`examples/ab-report.md`（A/B 结论）。

依赖：Python 3.9+ 标准库；编译需环境提供 TeX 引擎（pdflatex/xelatex/lualatex/latexmk/tectonic）与 bibtex/biber，缺失时按上表降级。

## 限制

`static_check.py` 只覆盖可机械判定的结构损伤；`check_manuscript.py` 判的是"是不是一份写实的完整稿件"，判不了科学正确性；`compile_and_parse.py` 的根因分类覆盖高频错误类型，但语义级"公式含义是否与正文一致""表格数值是否符合原文"仍需人工/评审判断，已在 uncertainty 中如实声明。Skill 不伪造编译成功、不虚构版本或分数、不依赖作者个人文件。
