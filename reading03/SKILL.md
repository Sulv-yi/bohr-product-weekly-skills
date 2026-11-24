---
name: literature-translation-verifiable
description: 可靠性优先的科研文献翻译 Skill。把英文论文段落译为中文双语对照，强制术语表锁定、段落级一一对齐、数字/单位/公式/引用/否定限定守恒，并为每段译文保留原文定位与译法依据。用于科研阅读中的文献翻译、双语对照、术语一致性核验任务。
---

# 文献翻译（可核验双语对照）

## 用途

把真实科研文献（题面固定案例的 PDF 或文本）翻译成**可核验的段落级双语对照** result，而不是大意或改写。核心目标不是"译得漂亮"，而是四个可检查的性质：

- **术语稳**：同一术语在标题、摘要、正文、图注、结论里始终用同一译名，术语表被真正执行。
- **段落全**：跨页、跨栏、跨章节不漏段、不重复、不错位，段号与原文一一对应。
- **关系准**：指代、否定与限定、因果让步、数字单位、公式与文献编号与原文一致。
- **可核验**：每段译文能指回原文段落/句子并说明译法依据；译不准的显式标注，不含混处理。

## 适用 / 不适用

适用：英文科研论文（含摘要/正文/图注/表头/公式/参考文献标记）→ 中文双语对照；术语一致性要求高；长文跨页分段翻译；需要逐段核验与回改。

不适用：非科研体裁的创意翻译；无原文定位需求的摘要式改写；要求译文润色优先于事实保真的场景（本 Skill 宁可标注"存疑"也不臆造）。

## 工作流

### 第 0 步：识别边界与材料
读取 `/input/case.json` 与 `task.md`，确认翻译任务范围（全文 / 指定段落区间）、语言方向、术语表口径、输出契约字段。**先读实际文件**，不从标签或题名推断内容。材料缺失 / 无文字层 / 语言混杂要在输出的 `uncertainty` 中说明。

### 第 1 步：输入探查
若输入是 PDF：用 `scripts/probe_pdf.py` 探查文字层、页数、语言；无文字层时标注为 `partial` 并说明需 OCR，不臆造原文。
若输入是文本 / JSON：直接进入分段。

### 第 2 步：抽取术语并建表
用 `scripts/build_glossary.py <原文文本> --out glossary.json` 抽取候选术语（缩写、连写复合词、高频实词），生成术语表骨架。为每条术语确定**唯一译名**，写入 `glossary.json`（字段：`term` / `translation` / `scope` / `note`）。术语表一旦确定即锁定，全篇按此回填。

### 第 3 步：段落切分与对齐
按语义边界切分（标题/摘要/章节/段落/图注/表头各自成段），为每段分配稳定 `source_id`（如 `p-003`）。长文跨页时保留段号连续，携带前一段末尾作为上下文。输出 `segments.json`：每段含 `source_id` / `source_text` / `location`（页码、段落序号）。

### 第 4 步：逐段翻译 + 依据
按术语表逐段翻译，每段产出：
- `source_id`（与原文一一对应）
- `source_text`（原文）
- `translation`（译文）
- `location`（页码 / 段落 / 句序）
- `rationale`（译法依据：术语对照、指代消解、否定/限定的处理）
- `untranslated`（该段存疑片段列表，可为 []）

### 第 5 步：守恒核验（本 Skill 的核心）
运行 `scripts/verify_translation.py <原文segments.json> <译文result.json> --glossary glossary.json --out verify.json`，自动回扫：
- **数字 / 单位**：原文出现的数值与单位是否在译文保留（如 `30 nm`、`p < 0.05`）。
- **引用标记**：`[12]`、`(Smith, 2020)` 等编号是否保留且未串位。
- **图表公式编号**：`Fig. 2`、`Table 3`、`Eq. (4)` 是否对应。
- **否定与限定**：`no / not / without / however / only` 等是否在译文有对应表达，防止"否定丢失"造成结论反转。
- **术语一致**：术语表锁定的译名是否在全篇统一使用，出现未锁定译法即报漂移。

任一项失败 → 回到第 4 步修正对应段，直到核验通过或明确标注 `uncertainty`。

### 第 6 步：契约自检
运行 `scripts/validate_result.py <result.json> --case <case.json>`，确认 `case_id`、状态、段落覆盖、证据定位、状态与不确定性字段齐全；再用 `scripts/align_paragraphs.py` 检查段号无漏、无重、无错位。通过后写入 `/app/output/result.json`。

## 输入输出

输入：`/input/case.json`（含 `case_id` / `output_contract` / 材料路径）+ 题面 `task.md`。
输出：`/app/output/result.json`，至少包含：

```json
{
  "case_id": "...",
  "status": "success | partial | unable | refused",
  "result": {
    "segments": [{"source_id":"p-001","source_text":"...","translation":"...","location":"p.1 ¶2","rationale":"...","untranslated":[]}],
    "glossary": [{"term":"...","translation":"...","scope":"..."}]
  },
  "sources": [{"source_id":"p-001","location":"p.1 ¶2","quote":"..."}],
  "uncertainty": ["..."],
  "changes": ["..."]
}
```

## 异常处理

- **PDF 无文字层 / 扫描件**：状态 `partial`，`uncertainty` 写明需 OCR，不编造原文。
- **原文残缺 / 语言混杂**：能译的部分正常译，残缺段标 `untranslated` 并说明。
- **公式 / 表格为图片**：保留编号标记，正文说明"图片内容未识别"，不臆造数据。
- **术语表冲突**：按 `scope` 就近优先，冲突写入 `uncertainty`。
- **无法完成**：状态 `unable` / `refused` 并给原因与可人工接管位置。

## 脚本

- `scripts/probe_pdf.py` — PDF 文字层 / 页数 / 语言探查（复用版，缺依赖时多级降级）
- `scripts/build_glossary.py` — 候选术语抽取与术语表骨架
- `scripts/align_paragraphs.py` — 段落级对齐：漏段 / 重复 / 错位检查
- `scripts/verify_translation.py` — 数字单位 / 引用 / 图表公式编号 / 否定限定 / 术语守恒回扫
- `scripts/validate_result.py` — 输出契约与状态自检

依赖：Python 3.9+，标准库即可运行；PDF 解析可选 PyMuPDF（`pip install pymupdf`），缺失时按 `probe_pdf.py` 的降级链处理。

## 限制

不依赖作者个人文件；不提交预制答案；不对无法定位的内容编造译文。核验脚本捕获的是"可机械判定的硬损伤"（数字、编号、否定、术语漂移），语义级误译仍需人工复核，这一点在 `uncertainty` 中如实说明。
