# 模板适配与公式表格引用要点

## 模板适配（改得对）

- 主文件与子文件：`\input`/`\include` 路径相对工程根，避免绝对路径。
- 导言区：先 `documentclass[选项]{模板}`，再按依赖顺序加载宏包；同一宏包只加载一次。
- 必填项：模板常要求 `\title/\author/\date`、`\begin{abstract}`、关键词、基金/分类等，逐项补齐。
- 迁入稿件：保留原文结构与论证顺序，不套通用模板重排章节。

## 数学公式

- 行内 `$...$`，行间 `equation`/`align`/`gather`/`multline`；多行对齐用 `align` + `&` 定位。
- 编号与引用：`\label{eq:x}` + `\eqref{eq:x}`；避免双重上下标；变量斜体、单位与函数名正体（`\mathrm`/`\text`）。
- 定理/证明用 `amsthm` 的 `theorem`/`proof` 环境，编号与正文叙述一致。
- 符号含义与正文保持一致；改动只调排版，不改数学含义。

## 表格与浮动体

- 三线表用 `booktabs` 的 `\toprule/\midrule/\bottomrule`，避免竖线。
- 列宽用 `p{...}` 或 `tabularx`，避免整表 `\scalebox` 掩盖溢出。
- 跨页长表用 `longtable`；宽表可 `resizebox` 但需说明缩放比例，不得裁切数据。
- 图表标题 `\caption` + `\label`，正文 `\ref` 对应；位置约束 `[htbp]`，不强制 `[H]` 除非必要。

## 引用与参考文献

- `\cite{key}` 的 key 必须在 `.bib` 中存在；`\bibliographystyle` + `\bibliography` 配套。
- biblatex 用 `\addbibresource` + `\printbibliography`，引擎走 biber。
- 多遍编译：pdflatex→bibtex→pdflatex×2，或 latexmk 自动收敛。
- `static_check.py` 可在无引擎时提前抓出不存在 cite key 与未定义 label。
