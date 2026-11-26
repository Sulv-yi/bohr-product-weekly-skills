---
name: intro-related-work-writer
description: 依据科研材料起草或改写论文引言与相关工作，交付"四部分齐全、彼此承接、逐条可回溯"的成稿本体与可核验附件（来源映射表、自检表），而不只是规则或校验清单。先生成成稿骨架，再填真实内容，最后逐段绑定 sources 并跑结构门槛；缺来源宁可标 partial，不编造事实、元数据或结论。当需要"写引言""整理相关工作""补引用""核对贡献""按期刊格式改写"时使用。
---

# 引言与相关工作写作（成稿优先 + 结构门槛 + 逐条可核）

核心命题：**交付的是能直接进论文的成稿**。题面四问——立得住（背景指向真实脉络与具体问题）、分得清（相关工作按问题/方法/路线分组比较）、说得实（空白由已引文献缺口推出）、对得上（贡献与本文方法图表实验一一对应、引用元数据真实）。规则写得再好，没交出成稿=0 分；只交一段概述，也拿不到"结果完整性/可核验性"的分。

## 何时使用 / 不使用

**使用**：起草或改写引言、研究背景、相关工作、研究空白、贡献陈述；补引用或核对引用；按目标期刊/会议格式改写。
**不使用**：只润色语言而无科研材料；要求生成材料外的事实或虚构引用；纯翻译。

## 篇幅与引用预算（动笔前先按这个量写，不要写完再补）

「可以直接进入论文」是本题的交付标准，600 字的稿子不叫可进论文。按下列预算一次写足，
否则会被门槛打回，白白消耗请求预算。

| 部分 | 中文下限 | 英文下限 | 必须含 |
|---|---|---|---|
| 研究背景 | 350 字 | 220 words | 领域脉络 → 具体未解问题 → 技术约束，三段递进，不得用"近年来受到广泛关注"打头 |
| 相关工作 | 550 字 | 350 words | ≥3 组；**每组 ≥150 字、≥2 篇带引用**；按问题设定/方法路线/数据与评价分组，禁止逐篇摘要 |
| 研究空白 | 150 字 | 100 words | 由已引工作的共同限制/未覆盖场景/冲突结论推出，并写明本文如何对应 |
| 贡献 | 150 字 | 100 words | ≥3 条，每条附正文证据定位 |
| 全文 | 1600 字 | 1000 words | 四部分合计，不含标题与引用表 |

引用预算：**正文引用 ≥12 条**，覆盖关键工作、代表性工作与近 3 年进展；
每条都要能回到 file/page/section/quote。材料里文献不足 12 条时，
把材料涉及的全部引用都用上并在 `uncertainty` 写明"材料文献不足"，不编造条目。

## 成稿门槛（定稿前逐条对照，达不到不要标 success）

| 项 | 门槛 | 谁检查 |
|---|---|---|
| 正文篇幅 | ≥1600 字（英文按词计 0.6 折算） | `validate_result.py` |
| 四要素 | 背景/相关工作/空白/贡献**各自成段**，顺序不颠倒 | `validate_result.py` |
| 相关工作量 | 背景 ≥350 字、相关工作 ≥550 字、空白 ≥150 字、贡献 ≥150 字 | `selfcheck.md` |
| 分组比较 | 相关工作 ≥3 组，每组写"共同做法 → 各自取舍 → 遗留问题" | `validate_result.py` |
| 空白推导 | 有"已引工作限制 → 空白 → 本文对应"三段链，缺环即补 | `selfcheck.md` |
| 贡献 | ≥3 条，每条带 `§/Fig./Table/实验结果` 定位 | `validate_result.py` |
| 来源 | ≥12 条，claim/file/quote + page 或 section 齐备 | `validate_result.py` |
| 论断绑定 | 背景/相关工作/空白中 ≥30% 论断句挂引用编号 | `selfcheck.md` |
| 干净度 | 无 `【…】`/`[证据槽]`/`TODO` 残留 | `validate_result.py` |

门槛未过的处置：**回第 4 步补齐内容**，不要改 status 绕过；确实补不出的，写入 `uncertainty` 并标 `partial`。

## 执行顺序（按此推进，禁止跳到校验）

### 第 0 步 · 读真实输入
读 `/input/case.json` 与 `/input/task.md`（若存在）。字段以实际文件为准：`case_id` / `task`|`instruction` / `material`|`paper`|`files` / `audience`|`venue`|`style` / `output_contract`。**先读材料本体**（PDF/文本），不从标签或题名猜内容。工作目录 `/app/work`，产物到 `/app/output`。

### 第 1 步 · 先落骨架（保证四要素齐全）
```bash
python <skill_dir>/scripts/draft_skeleton.py --case /input/case.json --out /app/output/draft.md
```
把背景/相关工作/空白/贡献四段的标题、写作要求、证据槽都生成好。**不要跳过**：即使后续中断，也留下一份结构完整的半成品，而不是空文件。

### 第 2 步 · 建事实底稿（grounding）
从材料抽取：研究问题、方法路线、关键结果、局限、图表编号、参考文献元数据（作者/年份/题名/来源）。每条记 `{claim, source:{file,page,section}, quote}`，`quote` 必须是材料里能搜到的原句片段。PDF 读取与能力边界见 `references/source-handling.md`；无文字层走 OCR 并标注置信度，**不伪造 quote**。

### 第 3 步 · 分组比较 → 推空白 → 对贡献
- 相关工作：按 `references/related-work-grouping.md` 建比较维度（问题设定/方法路线/数据与评价），≥3 组，每组写"共同做法→各自取舍→遗留问题"，禁止逐篇摘要拼接。
- 研究空白：按 `references/background-and-gap.md`，空白 = 已引工作的共同限制 ∪ 未覆盖场景 ∪ 冲突结论，再写本文如何对应。
- 贡献：按 `references/contribution-alignment.md`，≥3 条，每条附正文证据（方法节/图表/实验），无证据则降级或标为作者判断。

### 第 4 步 · 填满骨架 = 成稿
把第 1 步的骨架逐段替换为真实内容：每段论断句末挂引用编号（顺序编码制 `[n]`，或按 task 指定格式）。**写作与核对分离**：先出稿，再逐条回查原文。所有 `【…】` 占位与 `[证据槽]` 定稿前必须清空。

### 第 5 步 · 落可核验附件（题面要求"每条引用能否回到来源、分组依据与对照能否被独立复核"）
```bash
python <skill_dir>/scripts/build_outputs.py --draft /app/output/draft.md \
    --result /app/output/result.json --outdir /app/output
```
产出三件：`source-map.csv`（claim → file/page/section/quote → 正文位置）、`selfcheck.md`（结构指标 + 未清项）、`preview.pdf`（环境有 pandoc/xelatex 时）。有 PDF 时它本身就是"可目视核验"的证据；没有则如实写明不可用，不声称已渲染。

### 第 6 步 · 校验（成稿之后，不是代替成稿）
```bash
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/draft.md
```
报错逐条修；`--text` 传入成稿，才能把 draft 的结构算进去。仍不达标就留在 `partial` 并把原因写进 `uncertainty`。

### 第 7 步 · 输出 result.json
字段（依 `output_contract` 逐个原样覆盖，缺失字段即失败）：

| 字段 | 内容 |
|---|---|
| `case_id` | 原样 |
| `status` | `success`/`partial`/`blocked`/`unanswerable`（无来源标 partial，不硬标 success） |
| `result` | 依 `output_contract` 全部字段，含可编辑成稿本体（背景/相关工作/空白/贡献） |
| `sources` | `{id, cite_key, claim, file, page, section, quote}`；`cite_key` 填正文里的引用编号（如 `"3"`），无编号时用 `locator`（如 `"Table 1"`） |
| `uncertainty` | `{type, note}`：材料不足/引用缺失/冲突/需人工确认 |
| `changes` | 修改差异记录 |

## 评分维度落点（自查表）

| 维度 | 分值 | 本作品的落点 |
|--|--:|--|
| 实际效果·完成度 | 15 | `draft_skeleton.py` 按 `output_contract` 的每个字段生成可直接改写的成稿骨架 |
| 实际效果·正确性 | 15 | `citation_check.py` 核验引用键覆盖、元数据完整性、编号连续性、论断绑定 |
| 实际效果·完整性 | 5 | `quality_gate.py` 把题面「成稿标准」转成可计算指标 |
| 实际效果·可核验性 | 5 | `build_outputs.py` 产出成稿 + 来源映射 + 结构自检表三件可复核附件 |
| 使用增益·质量增益 | 15 | 先定篇幅与引用预算再写，避免写完再补引用 |
| 使用增益·效率增益 | 5 | 引用与结构检查脚本化，减少返工 |
| 使用增益·可验证性 | 5 | 自检表逐项列出指标与实际值 |
| 创新增益 | 15 | 把"引言与相关工作"的四要素转成结构指标，而不是只给写作建议 |
| 可靠体验 | 10 | `validate_result.py` 校验契约与四要素；异常处理见下一节 |
| 生态贡献 | 10 | 骨架与检查器可迁移到其他章节写作 |

## 异常处理

| 情况 | 处置 |
|---|---|
| 材料不足 | 写可写部分，缺口列 `uncertainty`，标 `partial`，不补造 |
| 引用查不到原文 | 保留论断但标"引用待核"，不伪造元数据，status 降 partial |
| 目标格式未知 | 用通用学术格式并在 uncertainty 说明 |
| 空白缺依据 | 不硬写"研究空白"，说明已引工作未显示明确缺口 |
| 语言切换 | 按 task 指定语言；术语保留原文对照 |
| 材料只有 PDF 且无文字层 | 走 OCR，标注识别置信度与页范围；关键数字无法确认时列 `uncertainty` |
| 时间/请求预算将耗尽 | 先存 `draft.md` 与 `result.json` 的 partial 版，再增量补；不交空壳 |

## 依赖与资源

Python 3.9+，脚本仅用标准库；PDF 用 PyMuPDF/pdfplumber 提取，无文字层走 OCR（见 `references/source-handling.md`）；`preview.pdf` 需要环境有 pandoc 或 xelatex，缺失则跳过并如实记录。

- `scripts/draft_skeleton.py` — 四要素成稿骨架（先跑，防空壳）
- `scripts/quality_gate.py` — 结构度量（篇幅/分组/贡献/绑定率/空白链），被下面两个脚本共用
- `scripts/build_outputs.py` — 生成 `source-map.csv` / `selfcheck.md` / `preview.pdf`
- `scripts/validate_result.py` — 契约 + 成稿结构门槛（不达标即报错）
- `scripts/citation_check.py` — 引用键覆盖、元数据完整性、编号连续性
- `references/` — 分组框架、空白推导、贡献对齐、引用核验、材料处理、证据与不确定性、方案边界
- `examples/` — `minimal-example.md`（最小调用）、`selftest-*`（示例案例与输出，含 baseline 对照，均标注为演示）

`eval/` 是给评审与复现用的：评分表、指标脚本、A/B 协议、验收表。**运行一个案例时不需要读 `eval/`**，别让它占用预算。

## 最小示例

见 `examples/minimal-example.md`：从材料到骨架、事实底稿、sources、result.json、自检表的完整形态。示例明确标注为示意，不代表正式案例结果。
