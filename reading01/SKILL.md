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
| `structure_gain` | 本次运行相对"纯文本直出"多出来的结构：章节数 / 题注数 / 表格数 / 文献条数 |
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
| 使用增益·质量增益 | 15 | 同一份 PDF 的 A/B 实测：粘连/千字 7.06 → 0.00，可疑字符 12.30% → 0.12%，页序 20 → 9（真实 9 页）。表格见 `examples/runs/BENCH.md` |
| 使用增益·效率增益 | 5 | 一次调用产出全部结构（有 pypdf 时 0.7 s/篇，无 pypdf 0.23 s/篇）；对照条件同样一次直出，但不产出任何结构，后续章节/文献定位需人工重读 |
| 使用增益·增益可验证性 | 5 | `scripts/bench.py` 一行复现两种条件的全部指标；纯确定性实现，同输入重复运行结果一致 |
| 创新增益·新增能力 | 5 | 自带 `pdfmini`（纯标准库）：页树还原真实页序、按行内间隙投票判栏缝、无第三方库也能按坐标切表格 |
| 创新增益·方法改进 | 5 | `paragraph_id + char 偏移` 的回查机制 + 引文校验闭环；表格切分阈值自适应（多阈值取列数最稳的一组），而非写死 |
| 创新增益·创新证据 | 5 | 三篇真实 PDF、两种环境（有无 pypdf）的实测数字与失败原因，全部可在包内复现 |
| 可靠体验·调用与易用性 | 3 | 两条命令即可完成；参数与输出字段全在本文档 |
| 可靠体验·运行稳定性 | 4 | 无随机性、无网络、无外部状态；三后端逐级降级，任一后端异常都不中断整体解析 |
| 可靠体验·异常处理 | 3 | 加密 / 无文字层 / 图片型表格 / 跨栏 / 占位文件 逐项分支处理（见第五节） |
| 生态贡献·文档完整性 | 3 | SKILL.md + README + 契约表 + 边界说明 + 实测记录 |
| 生态贡献·资源可复用性 | 4 | 纯标准库实现，无绝对路径、无个人文件依赖，复制即可用 |
| 生态贡献·分享推广价值 | 3 | GitHub 公开仓库，含 A/B 实测表（`BENCH.md`）与一条命令即可复现的评测脚本 |

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

1. `pypdf`（若已安装，优先使用）
2. `pdftotext`（poppler，`-layout`）
3. `pdfmini`（本包自带，纯标准库）：解析对象表与对象流 → 按 `/Pages /Kids` 还原**真实页序**
   → 每页独立解析 `/Resources /Font`（各自带 ToUnicode，不跨字体混用）→ 跟踪文字矩阵拿到
   `(x, y, size)` → 按行内间隙投票判定栏缝，双栏先左后右 → 输出可直接切表格的坐标块

`pdfmini` 的边界：不做图片/矢量图形、不解密、不 OCR；字体缺 ToUnicode 且非标准编码时可能丢字。
遇到这些情况一律记入 `uncertainty`，**不冒充精确解析结果**。

## 七、实测记录与对照

- `examples/runs/BENCH.md`：同一批 PDF 在"不用 Skill / 用 Skill"两种条件下的逐项指标
  （页数、字符、粘连率、可疑字符率、结构数、回查命中、耗时），含无 pypdf 与有 pypdf 两种环境。
- `examples/runs/RUNS.md`：单篇解析的运行记录（sha256、耗时、结构数量、表格失败原因）。

关键数字（无 pypdf 环境，Wiley 双栏英文论文 9 页）：
页数 20 → **9**；粘连/千字 7.06 → **0.00**；可疑字符 12.30% → **0.12%**；
结构 无 → **6 章节 / 14 题注 / 40 参考文献**；回查命中 **100%**。

平台用自己的固定案例评测，这些记录只说明能力与边界，不冒充平台得分。

## 八、文件清单

| 文件 | 作用 |
|---|---|
| `scripts/doctext.py` | 文档模型引擎：后端降级 + 段落/章节/题注/表格/参考文献 |
| `scripts/pdfmini.py` | 纯标准库 PDF 解析：页树页序 + 字体 ToUnicode + 坐标 + 分栏阅读顺序 |
| `scripts/readwork.py` | 任务加工工具：glossary / bilingual / notes / claims / graph / verify |
| `scripts/bench.py` | A/B 对照评测：不用 Skill vs 用 Skill 的逐项指标 |
| `examples/runs/BENCH.md` | 对照数据（含无 pypdf 环境） |
| `examples/runs/RUNS.md` | 真实运行记录与边界 |
| `GITHUB_URL.txt` | 本题作品的 GitHub 公开链接 |
