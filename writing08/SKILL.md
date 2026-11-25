---
name: intro-related-work-writer
description: 依据科研材料起草或改写论文引言与相关工作，交付“四部分齐全、彼此承接、可逐条回溯”的成稿本体，而不只是规则或校验清单。先生成成稿骨架，再填真实内容，最后逐段绑定 sources；缺来源宁可标 partial，不编造事实、元数据或结论。当需要“写引言”“整理相关工作”“补引用”“核对贡献”“按期刊格式改写”时使用。
---

# 引言与相关工作写作（成稿优先 + 逐条可核）

核心命题：**交付的是成稿本身**。评分四问——立得住（背景指向真实脉络与具体问题）、分得清（相关工作按问题/方法/路线分组比较）、说得实（空白由已引文献缺口推出）、对得上（贡献与本文方法图表实验一一对应、引用元数据真实）。规则再好，没交出成稿=0 分。

## 何时使用 / 不使用

**使用**：起草或改写引言、研究背景、相关工作、研究空白、贡献陈述；补引用或核对引用；按目标期刊/会议格式改写。
**不使用**：只润色语言而无科研材料；要求生成材料外的事实或虚构引用；纯翻译。

## 执行顺序（必须按此推进，禁止跳到校验）

### 第 0 步 · 读真实输入
读 `/input/case.json` 与 `/input/task.md`（若存在）。字段以实际文件为准：`case_id` / `task`|`instruction` / `material`|`paper`|`files` / `audience`|`venue`|`style` / `output_contract`。**先读材料本体**（PDF/文本），不从标签或题名猜内容。工作目录 `/app/work`，产物到 `/app/output`。

### 第 1 步 · 先落骨架（保证四要素齐全）
```bash
python <skill_dir>/scripts/draft_skeleton.py --case /input/case.json --out /app/output/draft.md
```
这一步把背景/相关工作/空白/贡献四段的标题、写作要求、证据槽全部生成好。**不要跳过**：它保证即使后续中断，也留下一份结构完整的半成品，而不是空文件。

### 第 2 步 · 建事实底稿（grounding）
从材料抽取：研究问题、方法路线、关键结果、局限、图表编号、参考文献元数据（作者/年份/题名/来源）。每条记 `{claim, source:{file,page,section}, quote}`。PDF 读取与能力边界见 `references/source-handling.md`；无文字层走 OCR 并标注置信度，不伪造。

### 第 3 步 · 分组比较 → 推空白 → 对贡献
- 相关工作：按 `references/related-work-grouping.md` 建比较维度（问题设定/方法路线/数据与评价），每组写“共同做法→各自取舍→遗留问题”，禁止逐篇摘要拼接。
- 研究空白：按 `references/background-and-gap.md`，空白 = 已引工作的共同限制 ∪ 未覆盖场景 ∪ 冲突结论，再写本文如何对应。
- 贡献：按 `references/contribution-alignment.md`，每条贡献附正文证据（方法节/图表/实验），无证据则降级或标为作者判断。

### 第 4 步 · 填满骨架 = 成稿
把第 1 步的骨架逐段替换为真实内容：每段论断句末挂 `[证据槽]` 指向 sources 里的 id。**写作与核对分离**：先出稿，再逐条回查原文，禁止边写边凭记忆填引用。所有 `【…】` 占位与 `[证据槽]` 定稿前必须清空。

### 第 5 步 · 校验（成稿之后，不是代替成稿）
```bash
python <skill_dir>/scripts/citation_check.py /app/output/result.json --case /input/case.json
python <skill_dir>/scripts/validate_result.py /app/output/result.json --case /input/case.json
```
校验新增“成稿实质性”检查：标 success 必须有 ≥200 字正文、无占位符、sources 非空。校验失败回第 3/4 步修正，**不要靠把 status 改成 partial 绕过**。

### 第 6 步 · 输出 result.json
字段（依 `output_contract` 逐个原样覆盖，缺失字段即失败）：

| 字段 | 内容 |
|---|---|
| `case_id` | 原样 |
| `status` | `success`/`partial`/`blocked`/`unanswerable`（无来源标 partial，不硬标 success） |
| `result` | 依 `output_contract` 全部字段，含可编辑成稿本体（背景/相关工作/空白/贡献） |
| `sources` | `{id, claim, file, page, section, quote}` 逐条可回溯 |
| `uncertainty` | `{type, note}`：材料不足/引用缺失/冲突/需人工确认 |
| `changes` | 修改差异记录 |

若要求可编辑稿件，另存 `.md`/`.docx` 到 `/app/output/`，并保留 `draft.md` 作为过程证据。

## 异常处理

| 情况 | 处置 |
|---|---|
| 材料不足 | 写可写部分，缺口列 `uncertainty`，标 `partial`，不补造 |
| 引用查不到原文 | 保留论断但标“引用待核”，不伪造元数据，status 降 partial |
| 目标格式未知 | 用通用学术格式并在 uncertainty 说明 |
| 空白缺依据 | 不硬写“研究空白”，说明已引工作未显示明确缺口 |
| 语言切换 | 按 task 指定语言；术语保留原文对照 |

## 依赖与资源

Python 3.9+，仅标准库。PDF 用 PyMuPDF/pdfplumber 提取，无文字层走 OCR（见 `references/source-handling.md`）。
- `scripts/draft_skeleton.py` — 生成四要素成稿骨架（先跑，保证不空壳）
- `scripts/citation_check.py` — 引用键覆盖与元数据核验
- `scripts/validate_result.py` — 契约 + 成稿实质性校验
- `references/background-and-gap.md` / `related-work-grouping.md` / `contribution-alignment.md` / `citation-verification.md` / `source-handling.md` / `evidence-and-uncertainty.md`
- `examples/minimal-example.md`（标注示例，非官方案例） — 完整链路示范

## 最小示例

见 `examples/minimal-example.md`：从材料到成稿骨架、事实底稿、sources、result.json 的完整形态。示例明确标注为示意，不代表正式案例结果。
