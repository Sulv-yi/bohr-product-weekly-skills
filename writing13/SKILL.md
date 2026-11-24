---
name: latex-compile-fix-build
description: 面向科研稿件的 LaTeX 写作与编译 Skill。围绕"编译得通/改得对/交得可用/复现得了"，对真实 .tex 工程做结构预检、多轮编译、全量报错定位到文件行号与根因、引用/交叉引用收敛核验、事实来源映射与可复现构建记录。当任务要求写/改 LaTeX 源码、修编译错误、适配模板、处理公式表格引用或交付可重复编译的稿件时使用；缺引擎、缺宏包、缺字体、报错级联等如实标注，不臆造编译成功或分数。
---

# LaTeX 写作与编译（编译得通 · 改得对 · 交得可用 · 复现得了）

把一份 LaTeX 稿件真正做到**可编译、可并入、可维护、可复现**，而不是交一段看起来像 LaTeX 的片段或一张 PDF 截图。聚焦一个高频真问题——**编译-修复-构建闭环**——四个性质互相咬合：

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
| `output_contract` | 必须输出字段 | 逐字段原样覆盖 |

工作目录 `/app/work`，最终产物 `/app/output/result.json`（含所有 output_contract 字段与 case_id）+ 可编辑 .tex 源码。

## 核心原则

1. **先探后改**：先 `probe_project.py` 摸清引擎/模板/主文件/依赖，再动手。
2. **预检先行**：`static_check.py` 在编译前抓结构性硬损伤（括号/环境/label/引用），不浪费编译轮次。
3. **全量定位**：编译报错必须逐条定位 file:line + 根因 + 修复策略，修完一条继续找下一条，直到清零。
4. **事实绑定**：公式/表格/引用/数字的改动逐条带来源或修改记录，不新增材料外事实。
5. **诚实构建**：无引擎、缺宏包/字体、报错级联时如实标注，不伪造"编译成功"。
6. **早存增量**：先落一版 result.json（哪怕 partial），再逐步改进，每步记 change。

## 工作流

### 第 0 步 · 探查工程（对应"复现得了"）
```bash
python scripts/probe_project.py <工程根> --out project.json [--engine pdflatex]
```
读 `engines`/`selected_engine`/`main_file`/`document_class`/`packages`/`dependencies.missing_*`。
无引擎 → 记录 `reproduction.engine=null` 与不确定性，走静态检查 + 日志解析路径，不假装编译过。

### 第 1 步 · 静态预检（对应"改得对"，无需引擎）
```bash
python scripts/static_check.py <工程根> --out static_check.json [--strict]
```
抓花括号/环境配对、重复 label、未定义 \\ref/\\cite、\\begin/\\end 错配。每条带 file:line + 根因 + 修复提示。
`status=failed` → 按 issues 修 .tex，重跑直到无 error，再进编译。

### 第 2 步 · 编译与全量日志解析（对应"编译得通"）
```bash
python scripts/compile_and_parse.py <工程根> --out compile_report.json \
    --engine pdflatex --rounds 3 --main main.tex
# 或已有日志：--log compile.log
```
- 多轮编译直到交叉引用/参考文献收敛（`converged=true`）。
- 解析**所有** `!` error，逐条分类：undefined control sequence / missing file / math mode / runaway argument / undefined env / float too large 等，带 file:line + 根因 + fix_hint。
- 对每条 error 定位→修复→重编，循环到 `error_count=0` 且 `converged=true`。
- 无引擎且无 --log → `status=unavailable`，只做静态检查，result 标 partial 并说明。

### 第 3 步 · 写/改 .tex（对应"交得可用"）
按任务与报错，产出可编辑 .tex：主文件/子文件结构清楚，导言区宏包加载顺序合理，公式用合适环境并正确编号引用，表格列宽/对齐合规，模板必填项齐全。每个改动记进 `changed_files` + `changes`。

### 第 4 步 · 事实与来源映射（对应"改得对"）
`result.source_map` 逐条记录数字/术语/引用/图表/关键论断的来源或修改记录：
```json
{"claim":"公式(3) 的系数 α=0.85","source":"原文 §3.2 Eq.(3) / p.5","change":"保持原值，仅调整对齐环境"}
```
材料不足/冲突/需人工确认 → 写 `uncertainty`，不新增事实。

### 第 5 步 · 复现记录（对应"复现得了"）
`result.reproduction` 写全：
```json
{"engine":"pdflatex","engine_version":"TeX Live 2023","template":"ieeetrans.cls v1.8",
 "packages":{"amsmath":"v3.4","booktabs":"v1.618"},"fonts":["Times New Roman"],
 "command":"latexmk -pdf -interaction=nonstopmode main.tex","rounds":3}
```
不猜版本：探测不到写 `"unknown"` 并进 uncertainty。

### 第 6 步 · 契约自检
```bash
python scripts/verify_result.py /app/output/result.json --case /input/case.json \
    --static static_check.json --compile compile_report.json
```
四性质任一 failed → 回到对应步骤修正。通过后写 `/app/output/result.json`。

## 输入输出

输出 `/app/output/result.json` + 可编辑 .tex 源码到 `/app/output/`：

```json
{
  "case_id": "...",
  "status": "success | partial | unable | refused",
  "result": {
    "artifacts": [{"path":"main.tex","kind":"editable_source"}],
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

`status`：`success` 编译通过+四性质全满足；`partial` 部分完成（必须写 uncertainty 指明限制）；`unable` 材料/环境不可用；`refused` 任务越界或无依据。**不预置答案、不伪造编译状态、不虚构分数。**

## 异常处理

| 情形 | 处理 | status |
|---|---|---|
| 无 TeX 引擎 | 静态检查 + 日志解析路径，说明无法本机编译 | partial |
| 缺宏包 / 类文件 | 记录缺失项，建议安装/替换，不假装编译过 | partial |
| 缺字体 | 记录字体依赖，建议替代字体或安装 | partial |
| 报错级联（首错引发多错） | 全量定位后按根因排序，先修根因再重编 | 视结果 |
| 模板 .cls 缺失 | 说明需模板文件，用通用类做静态检查并标注差异 | partial |
| 权限不足 | 说明无法写入/编译的目录，给可人工接管位置 | unable |
| 材料冲突 / 未报告 | 写 uncertainty，不新增事实 | partial |

## 脚本

- `scripts/probe_project.py` — 引擎/模板/主文件/依赖探查（不臆造软件状态）
- `scripts/static_check.py` — 无需引擎的结构硬损伤检查（括号/环境/label/引用）
- `scripts/compile_and_parse.py` — 多轮编译 + 全量报错定位与根因分类 + 引用收敛
- `scripts/verify_result.py` — 四性质 + 契约自检

依赖：Python 3.9+ 标准库；编译需环境提供 TeX 引擎（pdflatex/xelatex/lualatex/latexmk/tectonic）与 bibtex/biber，缺失时按上表降级。

## 限制

`static_check.py` 只覆盖可机械判定的结构损伤；`compile_and_parse.py` 的根因分类覆盖高频错误类型，但语义级"公式含义是否与正文一致""表格数值是否符合原文"仍需人工/评审判断，已在 uncertainty 中如实声明。Skill 不伪造编译成功、不虚构版本或分数、不依赖作者个人文件。
