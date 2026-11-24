---
name: literature-structured-notes
description: 面向真实科研论文的「文献总结与结构化笔记」Skill。按论文自身章节生成章节摘要，用统一字段做论文卡片，拆出可检索知识点，并为每条关键笔记保留可回原文的锚点（页码/段落/图表/字段）。当任务要求读论文做总结、章节笔记、论文卡片、知识点提取、来源回链或可检索/可复用笔记时使用；对未报告、无法判断、材料冲突明确说明，绝不套通用摘要模板或编造出处。
---

# 文献总结与结构化笔记（对得上 · 留得住 · 找得回 · 用得上）

把一篇真实论文变成**可继续用**的结构化笔记，而不是一段压缩后的通读摘要。产出四个互相咬合的部分：论文卡片、章节笔记、知识点索引、证据锚点。核心不是"写得多"，而是四个可机械核验的性质：

- **对得上**：笔记骨架与论文自身的章节和论证顺序一致，不套通用摘要模板。
- **留得住**：研究问题、数据、方法条件、主要发现、局限都记录，尤其记下让结论成立的前提条件。
- **找得回**：每条关键笔记能指回原文的具体章节/段落/页码/图表，而不是笼统出处。
- **用得上**：笔记可检索、可比较、可继续加工，能被下一次阅读或写作直接使用。

## 适用 / 不适用

**适用**：真实论文（PDF / 文本 / 结构化材料）→ 章节总结、论文卡片、知识点清单、证据链接、可检索笔记；要求关键结论回到原文定位；同一领域多篇论文需要并排比较。

**不适用**：只要一段随意读后感；无回链要求的通俗科普改写；把结论当事实、不需要标注前提与不确定性的场景（本 Skill 宁可标注"未报告/无法判断"也不臆造）。

## 输入

运行时读 `/input/case.json` 与 `/input/task.md`（若存在）。字段以实际文件为准：

| 字段 | 含义 | 处理 |
|---|---|---|
| `case_id` | 案例标识 | 原样写入 result.json |
| `task` / `question` | 本案例的具体任务 | 决定笔记侧重点（章节总结 / 卡片 / 知识点 / 问答） |
| `material` / `pdf` / `files` | 材料路径 | **读真实文件**，不从题名或领域标签猜内容 |
| `output_contract` | 必须输出的字段清单 | 逐字段原样覆盖，不得遗漏或改名 |

工作目录 `/app/work`，最终产物 `/app/output/result.json`（含所有 output_contract 字段与 case_id）。

## 四个核心性质与工作流

### 第 0 步 · 识别边界
读 case.json 与 task.md，确认：材料类型、任务范围、笔记侧重、输出契约字段。**先读实际文件**。材料缺失、无文字层、语言混杂都要写进 `uncertainty`。

### 第 1 步 · 探查材料
若输入 PDF：先跑 `scripts/probe_pdf.py` 看页数、文字层、加密、栏数、图像型页面。无文字层 → 标 `partial` 并说明需 OCR，不编造原文。若文本/JSON → 直接进第 2 步。

### 第 2 步 · 还原论文自己的骨架（对得上）
```bash
python scripts/build_outline.py <blocks.json> --out outline.json
```
从带坐标文本块识别论文真实章节（编号标题 / 常见章节词 / 版式特征），产出 `outline`（`section_id`/`title`/`level`/`order`）与 `full_text`。**笔记章节顺序必须来自这里**，不自己发明"背景-方法-结果-讨论"通用模板；若论文没有独立"讨论"节，就不要硬造一节。

```bash
python scripts/build_card_skeleton.py --outline outline.json --case /input/case.json --out skeleton.json
```
生成稳定 ID 的空白卡片骨架，之后逐条填。

### 第 3 步 · 逐章做笔记 + 绑定锚点（找得回）
按 `outline` 顺序，每节产出一条 `section_notes`：自己写的 `summary` + 该节证据的 `source_ids`。同时把证据登记到顶层 `sources`：

```json
{"source_id":"s1","location":"p.3 ¶2 / Fig.2","quote":"原文逐字片段（必须能在材料中匹配到）"}
```
锚点粒度要与可核验性匹配：能定位到段就不写"见全文"，能定位到图注就不写"见结果节"。`quote` 用原文逐字片段（规范化后需能在材料里找到），这是"找得回"的机械保证。

### 第 4 步 · 填论文卡片（留得住）
`result.paper_card` 用统一字段，保证多篇论文可并排比较：

| 字段 | 内容 |
|---|---|
| `research_question` | 研究问题 / 目标 |
| `data` | 数据 / 样本 / 来源 |
| `method` | 方法 / 实验条件 |
| `findings` | 主要发现，**每条带 `conditions`（成立前提/适用范围）** |
| `limitations` | 局限 |
| `premises` | 让结论成立的关键前提条件（单列） |

每个字段值是条目数组，条目含 `text` 与 `source_ids`。没报告的写"未报告"并进 `uncertainty`，**不写成事实**。

### 第 5 步 · 拆知识点（用得上）
`result.knowledge_points`：把重要概念、变量、方法、结论拆成可检索条目：
```json
{"id":"k1","term":"术语原名","aliases":["缩写","同义表述"],"definition":"定义","source_ids":["s2"]}
```
`id`/`term` 必须唯一，别名不能撞到别的条目的 term（脚本会查）。术语、缩写、同义表都要处理，避免条目重复或自相矛盾。

### 第 6 步 · 双重自检
```bash
python scripts/validate_result.py /app/output/result.json --case /input/case.json
python scripts/verify_notes.py /app/output/result.json --outline outline.json \
    --material <原文文本或blocks.json> --case /input/case.json --strict-align --out verify.json
```
- `validate_result.py` 查结构与契约是否齐全。
- `verify_notes.py` 查四个性质 + 硬损伤（数字/引用守恒、锚点可解析）。任一项 failed → 回到对应步骤修正。
  - alignment failed → 回第 2/3 步对齐章节顺序
  - retention failed → 回第 4 步补要素/前提
  - traceable failed → 回第 3 步修 quote/source_id
  - reusable failed → 回第 5 步去重
  - 数值/引用告警 → 核对是否臆造或串位

## 输入输出

输出 `/app/output/result.json`：

```json
{
  "case_id": "...",
  "status": "success | partial | unable | refused",
  "result": {
    "paper_card": {
      "title": "", "venue_year": "",
      "research_question": [{"text":"...","source_ids":["s1"]}],
      "data": [], "method": [],
      "findings": [{"text":"...","conditions":"...","source_ids":["s2"]}],
      "limitations": [], "premises": []
    },
    "section_notes": [
      {"section_id":"S2","order":1,"title":"Introduction","summary":"...","source_ids":["s1"]}
    ],
    "knowledge_points": [
      {"id":"k1","term":"...","aliases":[],"definition":"...","source_ids":["s2"]}
    ]
  },
  "sources": [{"source_id":"s1","location":"p.3 ¶2","quote":"..."}],
  "uncertainty": ["未报告...", "无法判断...", "材料冲突..."],
  "changes": ["..."]
}
```

`status` 语义：`success` 全部笔记完成且可回链；`partial` 部分完成（必须写 uncertainty 指明限制）；`unable` 材料不可用；`refused` 任务越界或无依据。**正式测试案例、白板、评分由平台提供，不预置答案、不伪造分数。**

## 异常处理

- **扫描件 / 无文字层**：`partial` + 说明需 OCR，不编造原文。
- **加密 / 权限受限**：`unable` + 说明需密码或授权。
- **双栏错序**：用 `build_outline.py` 的 `order` 与 `block_section` 校正阅读顺序，错序写进 changes。
- **图表公式缺失 / 图片型**：保留图表编号标记，正文写"图片内容未识别"，不臆造数据。
- **超长文**：分节处理，节序连续，避免上下文截断漏节；`--strict-align` 查覆盖。
- **非中文论文**：按原文语言记录术语，中文译名作为 alias，不强译。
- **材料冲突 / 未报告 / 无法判断**：三者分开写进 `uncertainty`，绝不写成事实。

## 脚本

- `scripts/probe_pdf.py` — PDF 文字层/页数/语言/加密探查（多级降级）
- `scripts/build_outline.py` — 还原论文真实章节骨架（对得上）
- `scripts/build_card_skeleton.py` — 生成稳定 ID 的卡片骨架
- `scripts/verify_notes.py` — 四性质 + 数字/引用/锚点硬损伤核验（核心）
- `scripts/validate_result.py` — 输出契约与状态自检

依赖：Python 3.9+，标准库即可运行；PDF 解析可选 PyMuPDF/pdfplumber/pdftotext（缺失走 `probe_pdf.py` 降级链）。

## 限制

`verify_notes.py` 捕获的是"可机械判定的硬损伤"（章节顺序、字段缺失、锚点不可解析、数字/引用串位、知识点重复），语义级的总结是否准确、前提是否真正关键仍需人工复核，这一点在 `uncertainty` 中如实声明。Skill 只做结构保真与可核验笔记，不做学科结论原创判断。不依赖作者个人文件，不提交预制答案。
