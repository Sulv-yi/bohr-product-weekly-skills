---
name: literature-pdf-structure-parser
description: 科研 PDF 结构化解析。任务要求把科研 PDF 解析成可用的结构化结果——正文、章节层级、图表题注、表格、公式、参考文献、页眉页脚——并且每条结果都要能指回原文页码与区块时使用。输出带 page / paragraph_id / quote 的结构化结果，读不出的部分如实标注而不是猜补。
---

# 科研 PDF 结构化解析

把一份科研 PDF 变成**可用、可核、可复核**的结构化结果。核心不是"输出一段像全文的文本"，
而是：每个结论都能指回原文页码与段落，每个字段都来自真实文件，读不出的地方明确写出来。

## 一、用途与适用边界

**适用**：任务要求把科研 PDF 解析成可用的结构化结果——正文、章节层级、图表题注、表格、公式、参考文献、页眉页脚——并且每条结果都要能指回原文页码与区块时使用。

**不适用**：只要文件大小/页数等元信息；输入不是 PDF（已是纯文本或表格）；要求对公式的科学
含义做学科判断（本 Skill 只做结构还原与证据绑定，不做学科结论生成）。

## 二、输入与输出契约

运行时把 `/input/case.json` 当唯一事实来源（字段以实际文件为准）：

| 字段 | 处理 |
|---|---|
| `case_id` | 原样写入 `result.json` |
| `task` / `question` | 决定输出形态：解析 / 翻译 / 笔记 / 断言 / 图谱 |
| `material` / `pdf` / `files` | 解析**真实文件**，不从标签猜内容 |
| `output_contract` | **逐字段原样覆盖**，不改名、不漏项 |

产物写到 `/app/output/result.json`，至少包含：

| 字段 | 内容 |
|---|---|
| `document` | 整篇结构：metadata / sections / captions / tables / references 的索引 |
| `paragraphs` | 段落数组，含 id / page / section / char_start / char_end |
| `tables` | 表格：行列、表头、证据段落；解析不出的写进 limitations |
| `sources` | 支撑结论的证据：page + paragraph_id + quote（逐字可回查） |
| `status` | `success` / `partial` / `blocked` / `unanswerable` |
| `uncertainty` | 未报告 / 无法判断 / 材料冲突，三态分开写 |
| `changes` | 本轮改动记录（先落一版，再增量改进） |

`status` 不是 `success` 时 `uncertainty` 必须非空，否则视为不诚实输出。

## 三、工作流

### 第 1 步 · 建文档模型（必做，一切引用都基于它）

```bash
python scripts/doctext.py /input/material.pdf --out work/doc.json
```

只探查不建段落时加 `--probe`。输出是**一份文档模型**，不是一段文本：

| 键 | 内容 |
|---|---|
| `backend` | `pypdf` / `pdftotext` / `builtin`，写进结果的运行说明 |
| `stats` | 页数、不可读页、页眉页脚剔除数、表格成功/失败数、可读率 |
| `metadata` | 标题、作者、单位、摘要、关键词、DOI（带 `title_confidence`） |
| `sections` | 章节树：标题、层级、页码、子节点 |
| `paragraphs` | 段落数组：`id`(如 `p003-07`)、`page`、`section`、`char_start/char_end` |
| `captions` | 图表题注：label（Figure 1 / 表 2）、页码、所属段落 |
| `tables` | 表格：表头、行、列数、证据；解析不了的进 `stats.unparsed_tables` 并给原因 |
| `references` | 参考文献条目：首作者、年份、DOI、原文 |
| `footnotes` | 脚注候选（作者注/基金/通讯地址） |

五条硬规则：

1. 引文必须能在 `paragraphs[].text` 里**逐字找到**，找不到就是定位错了，重来。
2. `backend=builtin` 表示环境没有第三方 PDF 库，字符可能缺失，**必须在 `uncertainty` 写明**。
3. `stats.unreadable_pages` 非空 → 这些页没有文字层，逐页记 `status:"unreadable"`，不得靠猜补。
4. `stats.unparsed_tables` 里的表**不要编造单元格**，如实写"结构不可解析 + 原因"。
5. 段落 id 只在本次运行内有效，跨运行不复用。

### 第 2 步 · 按任务产出主结果

本题是纯解析任务：直接用第 1 步的结构回答 `output_contract` 里的字段，不要再造第二套文本。

### 第 3 步 · 自检（必做，不通过不许交）

```bash
python scripts/readwork.py verify /app/output/result.json --doc work/doc.json
```

必须满足：`output_contract` 字段齐全、`status` 合法、`uncertainty` 与 `status` 一致、
每条 `sources` 的 `quote` 能在对应段落里逐字回查（`evidence_coverage` 应为 1.0）。
不通过就回到第 2 步改，**不要靠删证据让检查通过**。

## 四、评分维度落点（自查表）

| 维度 | 分值 | 本作品的落点 |
|--|--:|--|
| 实际效果·任务完成度 | 15 | `doctext.py` 一次给出段落/章节/题注/表格/参考文献五类结构，`result` 逐字段覆盖 `output_contract` |
| 实际效果·结果正确性 | 15 | 引文逐字回查（`verify` 的 `evidence_coverage`）；翻译类另查数字/单位/引用/公式保留 |
| 实际效果·结果完整性 | 5 | `metadata`（标题/作者/单位/摘要/关键词/DOI）+ 图表清单 + 参考文献条目 + 脚注 |
| 实际效果·结果可核验性 | 5 | 每条结论带 `page` + `paragraph_id` + `quote`，`quote_verified` 布尔位 |
| 使用增益·质量增益 | 15 | 无 Skill 时模型只能读"一段文本"；本 Skill 提供段 id、章节树、题注归属、证据回查四件套 |
| 使用增益·效率增益 | 5 | 单篇 1～2 秒产出完整模型（实测见 `examples/runs/RUNS.md`），不需要反复重读 PDF |
| 使用增益·增益可验证性 | 5 | 复现命令 + 两次运行结果一致（纯确定性，不含随机采样） |
| 创新增益·新增能力 | 5 | 三级后端降级（无第三方库也能解 ToUnicode 子集字体）；坐标栅格表格；共现与有向关系分离 |
| 创新增益·方法改进 | 5 | `paragraph_id + char 偏移` 的回查机制 + 引文校验闭环，把"可核验"变成可执行检查 |
| 创新增益·创新证据 | 5 | 两篇真实 PDF 的实测数字与失败原因，全部可在包内复现 |
| 可靠体验·调用与易用性 | 3 | 两条命令即可完成；参数与输出字段全在本文档 |
| 可靠体验·运行稳定性 | 4 | 无随机性、无网络、无外部状态；重复运行输出一致 |
| 可靠体验·异常处理 | 3 | 加密 / 无文字层 / 图片型表格 / 跨栏 / 占位文件 逐项分支处理（见第五节） |
| 生态贡献·文档完整性 | 3 | SKILL.md + README + 契约表 + 边界说明 + 实测记录 |
| 生态贡献·资源可复用性 | 4 | 纯标准库实现，无绝对路径、无个人文件依赖，复制即可用 |
| 生态贡献·分享推广价值 | 3 | GitHub 公开仓库，含两篇实测样本与可复现命令 |

## 五、异常与降级

| 情况 | 处置 |
|---|---|
| PDF 加密且需密码 | `status=blocked`，说明需密码/授权版本，不臆测内容 |
| 无文字层 / 扫描件 | 逐页记 `unreadable_pages`；不 OCR 猜字；需要时说明可接 OCR 分支 |
| 图片型表格 | 保留题注与位置，`tables` 留空并写原因 |
| 跨栏/并排表格 | 记 `unparsed_tables`（列数不稳定），不返回错误单元格 |
| 乱码字体 | 保留原始片段，用相邻段落交叉校验，写进 `uncertainty` |
| 材料是占位/记录页 | 如实输出其内容并标明"材料不含论文正文" |
| 超出预算（64 请求 / 900 秒） | 先落 `status=partial` 的完整骨架，再增量补齐 |

## 六、依赖

Python 3.9+，**零第三方依赖也能运行**。PDF 后端按序降级并在 `backend` 里如实标记：

1. `pypdf`（推荐，能解 ToUnicode 与子集字体，中文不乱码）
2. `pdftotext`（poppler，`-layout`）
3. 内置解析器：解 FlateDecode + 读 ToUnicode CMap + 取 `Tj/TJ`，纯标准库

`builtin` 后端的边界：不还原坐标、不识别表格结构；只保证有文字层的 PDF 能取出可定位文本，
**不冒充精确解析结果**，必须在 `uncertainty` 说明。

## 七、实测记录

见 `examples/runs/RUNS.md`（两篇真实 PDF，含 sha256、耗时、各类结构数量、
表格失败原因）。平台用自己的固定案例评测，这些记录只说明能力边界。

## 八、文件清单

| 文件 | 作用 |
|---|---|
| `scripts/doctext.py` | 文档模型引擎：后端降级 + 段落/章节/题注/表格/参考文献 |
| `scripts/readwork.py` | 任务加工工具：glossary / bilingual / notes / claims / graph / verify |
| `examples/runs/RUNS.md` | 真实运行记录与边界 |
| `GITHUB_URL.txt` | 本题作品的 GitHub 公开链接 |
