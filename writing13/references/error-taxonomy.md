# 编译错误分类与修复策略

## 高频错误 → 根因 → 修复

| 日志信号 | 类别 | 根因 | 修复 |
|---|---|---|---|
| `Undefined control sequence` | undefined_control_sequence | 命令拼错 / 缺提供它的宏包 | 核对拼写；补 `\usepackage` |
| `! LaTeX Error: File x.sty not found` | missing_file | 缺宏包 / 文件名大小写错 | 安装宏包；核对文件名与路径 |
| `Missing $ inserted` | math_mode | 数学符号不在数学模式 | 用 `$...$` / `\(...\)` / 数学环境 |
| `Runaway argument` | runaway_argument | 参数缺 `}` 或多写 `%` | 查花括号配对与行尾注释 |
| `There's no line here to end` | line_break | 不该换行处用 `\\` | 删多余 `\\` |
| `Undefined environment` | undefined_env | 环境名拼错 / 缺宏包 | 核对环境名与宏包 |
| `Double subscript/superscript` | math_script | `x^2^3` 歧义 | 用花括号 `x^{2^3}` |
| `Reference ... undefined` | undefined_reference | 缺 `\label` 或轮次不足 | 补 label；多编一轮 |
| `Citation ... undefined` | undefined_citation | 缺 bib 条目 / 未跑 bibtex | 补条目；跑 bibtex/biber |
| `Rerun to get ... right` | rerun_needed | 交叉引用/目录未收敛 | 再编一轮直到消失 |
| `Overfull \hbox` | overfull_hbox | 内容溢出版心 | 调断行/列宽/字号 |
| `Float too large` | float_too_large | 浮动体超页 | 缩放/拆表/调整放置约束 |
| `Emergency stop` | emergency_stop | 前序错误级联 | 修根因后重编 |

## 定位要点

- 日志里 `!` 开始的是硬错误；紧随其后的 `l.<N>` 或 `./file.tex: <N>` 是行号。
- 一个根因常引发多条后续错误（级联）：先修最早的根因，再重编，不要逐条打补丁。
- `undefined ref/cite` 不是源码错误，而是编译轮次或 bib 流程问题，单独处理。

## 全量解析原则

`compile_and_parse.py` 收集**所有** `!` 错误块，按上表分类，逐条给 `file`/`line`/`root_cause`/`fix_hint`。
评审看的是"是否定位到具体文件行号与根因"，不是"第一条错误改没改"。
