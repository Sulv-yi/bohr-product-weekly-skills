---
name: literature-pdf-struct-parser
description: 把科研 PDF（论文、预印本、技术报告）解析成结构化、可逐条回溯原文的结果。当任务要求读取论文 PDF 并做问答、翻译、信息提取、章节拆解、表格还原、阅读顺序修正或知识结构化，且要求关键结论带页码/段落/图表定位时使用。适用于双栏多栏论文、跨页表格、公式符号、扫描版 PDF、加密或无文字层等真实版式；输出包含结果、证据定位、不确定性与运行状态，绝不靠猜补齐。
---

# 科研 PDF 结构化解析

把一份科研 PDF 变成**可用、可核、可编辑**的结构化结果。不是"输出一段看起来像全文的文本"，而是每个结论都能指回原文页码与区块，读不出的部分如实标注。

## 何时使用 / 不使用

**使用**：输入含 PDF 路径，且要求提取正文、章节、表格、公式、图表题注、参考文献，或基于 PDF 回答/翻译/提取/核验/结构化，并需要证据定位。

**不使用**：只要 PDF 元数据或文件大小；只要对已有文本做润色（无 PDF 输入）；要求理解公式的科学含义并做学术判断（本 Skill 只做结构识别与保真，不做学科结论生成）。

## 输入

运行时从 `/input/case.json` 读取案例，字段以实际文件为准：

| 字段 | 含义 | 处理 |
|---|---|---|
| `case_id` | 案例标识 | 原样写入 result.json |
| `task` / `question` | 本案例的具体任务 | 决定输出形态（问答/翻译/提取/结构化） |
| `material` / `pdf` / `files` | 材料路径 | 解析真实文件，不从标签猜内容 |
| `output_contract` | 必须输出的字段清单 | **逐字段原样覆盖**，不得遗漏或改名 |

同时读 `/input/task.md`（若存在）获取版式约束与评分范围。工作目录 `/app/work`，最终产物到 `/app/output`。

## 核心原则

1. **读真实文件**：先打开 PDF 本体，不依据错误的领域标签补造数据。
2. **先探后解**：先跑 `scripts/probe_pdf.py` 摸清页数、文字层、加密、栏数、图像型页面，再决定解析路径。
3. **逐块带坐标**：用 `scripts/extract_blocks.py` 导出带 `page/bbox/text` 的文本块，后续每一步都基于块 ID 引用。
4. **证据绑定**：每条结论携带 `{page, block_id, bbox, quote}`，quote 必须能在原文块中找到。
5. **诚实标注**：未报告=材料没有；无法判断=有材料但读不出或冲突；两者分开写，绝不写成事实。
6. **早存增量**：先落一版完整 result.json，再逐步改进；每步记录 change。

## 工作流

### 第 1 步 · 探查（probe）

```bash
python <skill_dir>/scripts/probe_pdf.py "<pdf路径>" > /app/work/probe.json
```

读 `encrypted`、`has_text_layer`、`pages`、`page_stats`、`column_hint`、`image_only_pages`。分支：

- 加密且无密码 → `status=blocked`，说明需用户提供密码，不臆测内容。
- 无文字层 / 图像型页占比高 → 走 OCR 分支（见 `references/ocr-and-edge-cases.md`）。
- 有文字层 → 走正常提取分支。

### 第 2 步 · 带坐标提取（extract）

```bash
python <skill_dir>/scripts/extract_blocks.py "<pdf路径>" --out /app/work/blocks.json
```

产出块数组，每块含 `id`(如 `p003-b012`)、`page`、`bbox`、`text`、`column`。排序按"栏优先、再按 y"，处理跨栏与跨页续接。

### 第 3 步 · 版式与结构还原

按 `references/reading-order.md` 判定阅读顺序、剔除页眉页脚、合并跨页续段；按 `references/table-reconstruction.md` 还原表格；按 `references/structure-and-formula.md` 识别标题层级、图表题注、公式与上下标、参考文献。

### 第 4 步 · 回答 / 提取 / 翻译 / 结构化

严格按 `task` 要求产出主结果。每条结论后紧跟证据块 ID 与原文引用。翻译保留术语一致性与原编号；提取保留字段原值、单位与符号；问答先给答案再给依据。

### 第 5 步 · 校验（validate）

```bash
python <skill_dir>/scripts/validate_result.py /app/output/result.json --blocks /app/work/blocks.json --case /input/case.json
```

必须通过：所有 `output_contract` 字段齐全、每条证据的 quote 能在对应块中找到、status/uncertainty/changes 合法。失败则回到第 3/4 步修正。

### 第 6 步 · 输出

`/app/output/result.json` 至少包含：

| 字段 | 内容 |
|---|---|
| `case_id` | 原样 |
| `status` | `success` / `partial` / `blocked` / `unanswerable` |
| `result` | 依 `output_contract` 的全部字段 |
| `sources` | 证据数组：`page`, `block_id`, `bbox`, `quote` |
| `uncertainty` | 未报告/无法判断/冲突项及原因 |
| `changes` | 本轮改动记录 |

若任务要求可编辑产物（表格/大纲/结构 JSON），另存到 `/app/output/`，并尽量提供 PDF/PNG 渲染预览供检查。

## 异常处理

| 情况 | 处置 |
|---|---|
| 加密 PDF | 报 `blocked`，说明需密码或授权版本，不猜测 |
| 无文字层/扫描件 | 走 OCR 分支，标注识别置信度与可能错字 |
| 图片型表格 | 输出结构骨架 + `uncertainty` 标注无法取值，不编数值 |
| 乱码字体/符号丢失 | 用同页相邻块交叉校验，保留原始乱码片段 |
| 页码错乱 | 以 PDF 物理页序为准，另记印刷页码映射 |
| 超出页数/预算 | 优先保证核心章节与证据完整，其余标 `partial` |

## 依赖

Python 3.9+，**零依赖也可运行**。PDF 解析按以下顺序自动降级，并在 probe 结果里写明实际使用的后端：
1. PyMuPDF（`fitz`，推荐，能力最完整）
2. pdfplumber
3. pypdf
4. 系统 `pdftotext`
5. `scripts/pdf_fallback.py` —— 纯标准库兜底，无需任何第三方包，直接解析 PDF 内容流并支持字面串 `(...)` 与十六进制串 `<...>`（中文子集字体常见形式）

安装可选：`pip install pymupdf`；OCR：`pip install ocrmypdf` + 系统 tesseract-ocr。

兜底后端的能力边界（必须如实写进 result 的 `uncertainty`）：不解析字体 CID/ToUnicode 映射，子集嵌入字体的中文可能显示为原始码；不还原版面坐标、不识别表格与图片。它只保证有文字层的 PDF 至少能提取出可定位的文本行，**不冒充精确解析结果**。优先使用高级后端。

## 资源

- `scripts/probe_pdf.py` — 探查 PDF 版式与文字层
- `scripts/extract_blocks.py` — 带坐标的块提取与阅读顺序
- `scripts/pdf_fallback.py` — 纯标准库兜底解析（无第三方依赖时的最后防线）
- `scripts/validate_result.py` — 输出契约与证据一致性校验
- `references/reading-order.md` — 多栏/跨页/页眉页脚规则
- `references/table-reconstruction.md` — 合并单元格/多层表头/跨页续表
- `references/structure-and-formula.md` — 标题层级/题注/公式符号/参考文献
- `references/evidence-and-uncertainty.md` — 证据格式与不确定性标注
- `references/ocr-and-edge-cases.md` — 扫描件与异常输入
- `examples/minimal-example.md` — 最小调用示例（示意，非官方案例）

## 最小示例

见 `examples/minimal-example.md`。示意输出已明确标注为示例，不代表正式案例结果。
