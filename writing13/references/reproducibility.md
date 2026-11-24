# 可重复构建记录规范

## 必记字段（reproduction）

| 字段 | 内容 | 示例 |
|---|---|---|
| `engine` | 编译引擎 | pdflatex / xelatex / lualatex / latexmk / tectonic |
| `engine_version` | 发行版与版本 | TeX Live 2023 / MiKTeX 23.x / `pdflatex --version` 首行 |
| `template` | 模板类文件与版本 | ieeetrans.cls v1.8 / 自建 thesis.cls |
| `packages` | 宏包名→版本 | `{amsmath: "v3.4", booktabs: "v1.618"}` |
| `fonts` | 字体依赖 | ["Times New Roman", "Latin Modern"] |
| `command` | 完整编译命令 | `latexmk -pdf -interaction=nonstopmode main.tex` |
| `rounds` | 收敛所需轮次 | 3（含 bibtex 则单独记） |
| `bib_tool` | 参考文献工具 | bibtex / biber / none |

## 探测不到就写 unknown + uncertainty

不臆造软件状态。`probe_project.py` 通过 `shutil.which` 探测引擎，`--version` 取版本；
取不到就 `null`/`unknown`，并在 `result.uncertainty` 写明"本机未检测到引擎，版本需人工确认"。

## 收敛判定

1. `compile_and_parse.py` 多轮编译，每轮解析日志。
2. `converged = 无 error 且无 undefined_ref/cite 且无 Rerun 提示`。
3. 达标即停；未达标记 `status=needs_more_rounds`，增加轮次或修 bib 流程。

## 交付 bundle 建议

- 可编辑 .tex（主文件 + 子文件）+ .bib + 图片 + 模板 .cls/.sty（若允许）
- `BUILD.md`：一行编译命令 + 环境 + 轮次
- 不把 PDF 当源码交付；PDF 仅作可选预览，附 `result.json` 里说明由何命令生成
