---
name: methods-experiment-section-writer
description: 依据配置文件、实验日志、数据说明等事实底稿，交付“六类要素齐全、数值可回溯、可按之复做”的方法与实验章节成稿本体。先生成结构化成稿骨架，再填真实内容并对齐参数表，显式追问材料缺口。用于方法与实验章节写作、补写、改写与可复现性核验；不为顺畅补数值，不臆造未报告的设置。
---

# 方法与实验章节写作（成稿优先 + 可复现可追溯）

核心命题：**交付的是章节成稿本身**。评分四问——写得全（步骤/设置/参数/数据/对照/复现六类齐全）、写得准（取值/版本/划分与配置日志代码一致，不补数值）、做得着（按章节可复做，版本环境种子命令给全）、说得住（缺口显式标注，限制落到具体失效场景）。只交校验脚本或只有主干几句=0 分。

## 适用 / 不适用

适用：从配置/日志/代码说明撰写 Methods、Experimental Setup、参数表、数据集划分、对照实验、复现清单、Limitation。
不适用：无事实底稿的虚构方法；只要“讲个大概”的科普；结果/讨论章节。

## 执行顺序（必须按此推进，禁止跳到校验）

### 第 0 步 · 读真实输入
读 `/input/case.json` 与 `task.md`，确认写作范围、受众、文体、格式与 `output_contract`。**先读实际材料文件**（配置/日志/代码说明/数据说明），不从领域标签推断内容——题面明确“不依据错误标签补造数据”。工作目录 `/app/work`，产物到 `/app/output`。

### 第 1 步 · 先落骨架（保证六要素齐全）
```bash
python <skill_dir>/scripts/draft_skeleton.py --case /input/case.json --out /app/output/draft_skeleton.json
```
生成含 steps/setup/parameters/dataset/baselines/reproducibility/limitations 各槽位与来源槽的 JSON 骨架。**不要跳过**：即使后续中断也留完整半成品，而非空文件。

### 第 2 步 · 抽取要素底稿
按 `references/element-extraction.md` 把材料抽成结构化表，每类要素一条并附来源：
- 步骤：`输入/操作/输出/判断条件`，有序，不把多步压成一句
- 参数：`名称/取值/单位/作用对象/来源`（配置/日志/代码/作者确认）。可用 `scripts/extract_params.py` 抽骨架
- 数据集：名称、版本、规模、预处理、划分比例与随机方式、子集用途
- 对照：基线对象与版本、是否同预算、评价指标、统计方式、重复次数
- 环境：硬件、软件版本、随机种子、命令、数据获取方式

### 第 3 步 · 填骨架 = 成稿 + 数值对齐
把骨架槽位替换为真实内容，写成 `section` 正文（方法步骤→实验设置→参数→数据集→对照→复现→限制）。每个数值/版本/条件必须能在要素表找到来源。运行：
```bash
python <skill_dir>/scripts/align_params.py <稿件要素表> <参数表>
```
抓无来源数值与串位（判 `fabricated_value`）。**写作与核对分离**：先成稿，再逐条对齐，禁止边写边补数值。

### 第 4 步 · 复现清单 + 缺口追问
运行 `scripts/check_reproducibility.py <result.json>`，六要素（代码版本/环境依赖/随机种子/运行命令/数据获取/划分方式）缺失项写入 `reproducibility_gaps` 与 `uncertainty`，不臆造。材料不足、配置冲突、参数无来源、版本不明 → `questions_for_author` 显式追问，不自补。限制条件落到具体失效场景（如“输入分辨率 <256 时插值失真”），不用套话。

### 第 5 步 · 校验（成稿之后，不是代替成稿）
```bash
python <skill_dir>/scripts/validate_result.py <result.json> --case /input/case.json
```
新增“成稿实质性”：标 success 必须 section ≥200 字、无占位符、六要素齐全、sources 非空。失败回第 3/4 步修正，**不要靠改 status 绕过**。

### 第 6 步 · 输出 result.json
按 `output_contract` 逐字段原样覆盖，至少含：

```json
{
  "case_id": "...",
  "status": "success | partial | unable | refused",
  "result": {
    "section": "可编辑的方法与实验章节正文（成稿本体）",
    "elements": {"steps":[], "setup":{}, "parameters":[], "dataset":{}, "baselines":[], "reproducibility":{}},
    "reproducibility": {"code_version":"...","env":"...","seed":"...","command":"...","data":"...","split":"..."},
    "questions_for_author": [],
    "limitations": [{"scenario":"...","reason":"...","scope":"..."}]
  },
  "sources": [{"element":"lr","value":"1e-4","source":"config.yaml:12","quote":"..."}],
  "uncertainty": [],
  "changes": []
}
```
无来源的设置标 partial + uncertainty，不硬标 success。

## 异常处理

- **材料缺失 / 参数无来源**：`questions_for_author` + `uncertainty`，状态 `partial`，不补数值。
- **配置冲突**：列出冲突项与各自来源交作者裁定，不自行选一个。
- **数据集版本不明**：标追问项，不臆造版本或规模。
- **权限不足 / 材料不可读**：状态 `unable`，说明原因与接管位置。

## 依赖与资源

Python 3.9+，全部标准库；路径相对本目录，不依赖个人文件。
- `scripts/draft_skeleton.py` — 六要素成稿骨架（先跑，保证不空壳）
- `scripts/extract_params.py` — 从配置/日志文本抽取参数骨架
- `scripts/align_params.py` — 正文数值与参数表对齐，抓无来源/串位
- `scripts/check_reproducibility.py` — 复现六要素完整性检查
- `scripts/validate_result.py` — 契约 + 成稿实质性校验
- `references/element-extraction.md` / `parameter-alignment.md` / `reproducibility.md` / `gap-questioning.md` / `verification-checklist.md`
- `examples/minimal-example.md`（标注示例，非官方案例）

## 限制

不提交预制答案，不为顺畅补数值，不臆造材料外事实。脚本捕获可机械判定的硬伤（无来源数值、复现要素缺失、空壳成稿），语义恰当性与限制条件真实性需人工复核，在 `uncertainty` 如实说明。
