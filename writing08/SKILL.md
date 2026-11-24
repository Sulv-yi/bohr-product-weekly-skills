---
name: intro-related-work-writer
description: 依据科研材料起草或改写论文引言与相关工作，保证事实、数字、引用可逐条回溯原文，研究空白由已引文献推出，贡献与实际方法图表对齐。当需要"写引言""整理相关工作""补引用""核对贡献""按期刊格式改写"且要求保留来源与修改记录时使用；材料不足、引用查不到原文、目标格式未知时明确标注，不编造事实、元数据或结论。
---

# 引言与相关工作写作

把科研材料变成**能进论文、且每一句都能核对**的引言与相关工作。不是"近年来受到广泛关注"式的空转铺垫，也不是逐篇摘要拼接。

## 何时使用 / 不使用

**使用**：任务涉及起草或改写引言、研究背景、相关工作、研究空白、贡献陈述；补引用或核对引用；按目标期刊/会议格式改写。

**不使用**：只要求润色语言而无科研材料；要求生成材料外的事实或虚构引用；纯翻译（除非同时要求写作结构）。

## 输入

运行时读 `/input/case.json`，字段以实际文件为准：

| 字段 | 含义 | 处理 |
|---|---|---|
| `case_id` | 案例标识 | 原样写入 result.json |
| `task` / `instruction` | 写作任务 | 决定产出体裁、受众、篇幅 |
| `material` / `paper` / `files` | 科研材料路径 | 读真实文件，不从标签猜内容 |
| `audience` / `venue` / `style` | 受众与格式约束 | 用于格式与语气 |
| `output_contract` | 必须输出字段 | 逐字段原样覆盖 |

同时读 `/input/task.md`（若存在）。工作目录 `/app/work`，最终产物到 `/app/output`。

## 四条硬标准

1. **立得住**：背景指向真实研究脉络与具体未解问题，不写空泛重要性。
2. **分得清**：相关工作按问题/方法/路线**分组比较**，同一维度上对比取舍，不按时间罗列。
3. **说得实**：研究空白由已引文献的共同限制/未覆盖场景/冲突结论推出；断言有证据，或明确标为作者判断。
4. **对得上**：贡献条目与本文实际方法、图表、实验一一对应；引用元数据真实、格式统一、论断与引用一一对应。

## 工作流

### 第 1 步 · 建事实底稿（grounding）

从材料抽取：研究问题、方法路线、关键结果、局限、图表编号、参考文献清单（作者/年份/题名/来源）。每条事实记 `{claim, source:{file,page,section}, quote}`。用 `scripts/citation_check.py` 先建引用索引。

### 第 2 步 · 分组与比较

按 `references/related-work-grouping.md` 建立比较维度（问题设定 / 方法路线 / 数据与评价），把文献分组，每组写"共同做法 → 各自取舍 → 遗留问题"。禁止只写"X 做了…Y 做了…"。

### 第 3 步 · 推导研究空白与贡献

按 `references/background-and-gap.md`：空白 = 已引工作的共同限制 ∪ 未覆盖场景 ∪ 冲突结论；再写本文如何对应。按 `references/contribution-alignment.md`：每条贡献附正文证据（方法节/图表/实验），无证据则降级或标为作者判断。

### 第 4 步 · 起草与引用绑定

每段论断后紧跟引用键（如 `[3]` 或 `(Author, 2020)`）。写作与核对分离：先出稿，再逐条回查来源，禁止边写边凭记忆填引用。

### 第 5 步 · 核对

```bash
python <skill_dir>/scripts/citation_check.py /app/output/result.json --sources /app/work/sources.json --case /input/case.json
python <skill_dir>/scripts/validate_result.py /app/output/result.json --case /input/case.json
```

检查：引用键都有来源；来源元数据（作者/年份/来源）齐全；quote 可在原文找到；`output_contract` 字段齐全；无材料外事实。失败则回第 1/4 步修正。

### 第 6 步 · 输出

`/app/output/result.json` 至少含：

| 字段 | 内容 |
|---|---|
| `case_id` | 原样 |
| `status` | `success` / `partial` / `blocked` / `unanswerable` |
| `result` | 依 `output_contract` 的全部字段（含可编辑稿件） |
| `sources` | 事实/引用映射：`id`, `claim`, `file`, `page`, `section`, `quote` |
| `uncertainty` | 材料不足/引用缺失/冲突/需人工确认项 |
| `changes` | 修改差异与改动记录 |

若任务要求可编辑稿件，另存 `.md`/`.docx` 到 `/app/output/`，并记录版本差异。

## 异常处理

| 情况 | 处置 |
|---|---|
| 材料不足 | 写可写部分，缺口列 `uncertainty`，标 `partial`，不补造 |
| 引用查不到原文 | 保留论断但标"引用待核"，不伪造元数据 |
| 目标格式未知 | 用通用学术格式并在 uncertainty 说明，询问用户 |
| 空白缺依据 | 不硬写"研究空白"，说明已引工作未显示明确缺口 |
| 语言切换 | 按 task 指定语言；术语保留原文对照 |

## 依赖

Python 3.9+，仅标准库。材料若为 PDF，用 PyMuPDF/pdfplumber 提取文本层（见 `references/source-handling.md`）；无文字层走 OCR 并标注置信度。

## 资源

- `scripts/citation_check.py` — 引用键覆盖与来源元数据核验
- `scripts/validate_result.py` — 输出契约与证据一致性校验
- `references/background-and-gap.md` — 背景与研究空白推导模板
- `references/related-work-grouping.md` — 相关工作分组比较框架
- `references/contribution-alignment.md` — 贡献与图表证据对照
- `references/citation-verification.md` — 引用核验清单
- `references/source-handling.md` — 材料读取与边界处理
- `references/evidence-and-uncertainty.md` — 证据格式与不确定性标注
- `examples/minimal-example.md` — 最小调用示例（示意，非官方案例）

## 最小示例

见 `examples/minimal-example.md`。示意输出已明确标注为示例，不代表正式案例结果。
