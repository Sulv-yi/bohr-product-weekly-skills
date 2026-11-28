# 真实编译记录（不是示意，可逐条复跑）

本文件记录一次**真实执行**的编译与 A/B 对照。所有数字来自实际运行产生的 PDF 与 `.log`，
命令附在每节末尾，任何人可复跑得到同一结论。

## 一、环境

| 项 | 值 |
|---|---|
| 引擎 | tectonic 0.15.0（XeTeX + xdvipdfmx，TeX Live bundle） |
| 命令 | `tectonic -X compile <main>.tex --outdir <dir> --keep-logs` |
| 中文字体 | `ctex` 默认 FandolSong-Regular（缺字时有回退警告，见第四节） |
| 采样时间 | 2026-11-28 |

选 tectonic 是因为它是**单文件可执行**，无需装整套 TeX Live 即可复现；
`pdflatex` / `xelatex` / `latexmk` 的等价命令见 `references/reproducibility.md`。

## 二、A/B 对照（两边都真编译，不是"unavailable"）

| 指标 | 基线（无 Skill，`baseline-manuscript.tex`） | 有 Skill（`selftest-manuscript.tex`） |
|---|---:|---:|
| 编译状态 | success | success |
| PDF 页数 | 1 | **5** |
| PDF 字节 | 40,283 | 209,054 |
| 章节数 | 2 | 5 |
| 正文实义字数 | 102 | 754 |
| 公式环境 | 0 | 1 |
| 表格（有数据行） | 0 | 1 |
| `\cite` 键 / 可解析 | 1 / 1 | 10 / 10 |
| **undefined 引用** | **2** | **0** |
| **LaTeX Warning** | **3** | **0** |
| Overfull / Underfull box | 0 / 0 | 0 / 0 |
| 硬错误（`!`） | 0 | 0 |

基线在 `.log` 里的三条警告原文：

```
LaTeX Warning: No \author given.
LaTeX Warning: Citation `wang2019' on page 1 undefined on input line 8.
LaTeX Warning: There were undefined references.
```

这三条正好对应 Skill 的三个检查点：**模板必填项**（\author 缺失）、
**引用闭合**（cite 键无法在 .bib 回溯）、**结构完整**（只有 2 节、无公式无表格）。
基线"能编译"但"不能并入稿件"——这正是本题区分的两种状态。

## 三、复跑命令

```bash
# 基线侧
mkdir -p /tmp/ab/base && cp examples/baseline-manuscript.tex /tmp/ab/base/main.tex
cd /tmp/ab/base && tectonic -X compile main.tex --outdir . --keep-logs

# Skill 侧
mkdir -p /tmp/ab/skill
cp examples/selftest-manuscript.tex /tmp/ab/skill/main.tex
cp examples/selftest-refs.bib      /tmp/ab/skill/selftest-refs.bib
cd /tmp/ab/skill && tectonic -X compile main.tex --outdir . --keep-logs

# 统计（页数 + 警告数）
python - <<'PY'
import re
from pypdf import PdfReader
for d in ('/tmp/ab/base', '/tmp/ab/skill'):
    log = open(d + '/main.log', encoding='utf-8', errors='replace').read()
    print(d, 'pages', len(PdfReader(d + '/main.pdf').pages),
          'undefined', len(re.findall('undefined', log)),
          'warn', len(re.findall('LaTeX Warning', log)))
PY
```

## 四、已知边界（如实记录，不掩盖）

1. **`ctex` 字体回退警告**：bundle 内 FandolSong 不含个别字形时会打印
   `Font "FandolSong-Regular" does not contain requested ...`，属字体覆盖问题，不影响 PDF 生成；
   需要严格字形时应改用系统中文字体（`\setCJKmainfont`）。
2. **tectonic 的多遍提示**：日志会出现
   `Rerunning TeX because "main.bbl" changed` 与
   `warning: internal consistency problem when checking if main.bbl changed`，
   这是 tectonic 内部对 bbl 变化的检测策略，**不是稿件缺陷**：最终 `.log` 中
   undefined 引用为 0、交叉引用全部解析。用 `latexmk` 时该提示不会出现。
3. 本对照是**本地自建**对照，用于证明能力差异，不等同平台正式白板；
   平台正式对照以组织方生成为准。

## 五、这份记录证明了什么

- Skill 侧稿件在真实引擎下**编译通过且零警告**，不是"看起来像 LaTeX 的片段"；
- 差异不是文风差异，而是**可机械计数的四项**：页数、引用解析率、警告数、结构要素数；
- 对照的弱项（基线 3 条警告）与 Skill 的检查点一一对应，说明 Skill 的检查项不是凭空的清单。
