---
name: academic-language-polishing
description: 润色学术文本但严格保持原意与证据——先建逐段对齐的润色工作台，再校对语法用词、统一全篇术语、贴合目标文体语域，同时守住限定强度、数字单位、引用编号与图表指向，最后用成稿门槛逐段复核并输出原文-改文-修改类型-理由的可核对照。当用户要求润色、校对、改写、学术英文优化、中译英表达调整、术语统一或按期刊/学位/基金文体改写时使用。不用于纯内容问答、事实核查或代写新结论。
---

# 学术语言润色（语义守恒 + 逐段成稿 + 可核对照）

## 用途与触发

**该用**：用户给出已有稿件/段落/摘要，要求润色、校对、改写、术语统一、语气贴合、中译英表达优化、按特定期刊或文体调整。

**不该用**：纯内容问答、要求补做实验或新增结论、要求"把结论写强一点"这类改变主张的请求——此时先说明边界，不擅改。

## 五个硬目标

| 目标 | 含义 | 失败表现 |
|---|---|---|
| 段段有着落 | 润色结果与原文**逐段一一对齐**（pid + original + polished），不是一段总结 | 只交"改写要点"或检查报告 |
| 改得对 | 语法、句法、搭配、标点、用词错误被真正修掉 | 换种说法掩盖错误 |
| 说得像 | 符合目标文体语域，术语全篇统一 | 口语化、宣传化、术语漂移 |
| 没改坏 | 限定强度、数据单位、引用编号、图表指向、因果/相关关系原样保持 | may→is、约30%→30%、[3]→[4] |
| 讲得清 | 每处修改有原文、改文、类型标签与理由 | 只给改后全文，无法判断该不该改 |

## 工作流

### 1. 建立约束清单（先做，不可跳过）

从输入中提取并锁定：
- `case_id` / 输入标识；目标文体（期刊论文 / 学位论文 / 基金申请 / 审稿回复 / 英文摘要）；受众与目标语言
- 术语表路径（若有）；必须有 `term_map`（原写法→统一写法）；无术语表时从稿件抽取候选并标 `needs_confirmation`
- 不可变项清单：**所有数字、单位、符号、引用编号（[n]/(year)/上标）、图表指向（Fig./Table/图/表）、否定词、条件句、限定词**

### 2. 建逐段润色工作台（决定交付形态的关键一步）

```
python <skill_dir>/scripts/build_polish_draft.py --case /input/case.json --out /app/work
# 材料在单独文件里时：--text /input/material.md
```

产出三件东西：
- `polish_plan.json`：每段原文 + 该段锁定的数字/单位/引用/图表指向/限定词数量/否定词数量 + 段号
- `polished_skeleton.md`：逐段骨架，每段一个「原文 / 润色」槽位，锁定项直接印在段落旁边
- `term_seed.md`：术语候选，供建术语表

这一步的意义：把"润色"变成**一段对一段的产出**，而不是写一段概括。写的时候锁定项就在眼前，不会丢数字、不会把否定句改成肯定句。

### 3. 快照锁定（改前，双保险）

```
python <skill_dir>/scripts/lock_invariants.py <原文文件> --out /app/work/lock.json
```

把不可变项连同出现位置写入 lock 文件；骨架已给段落级锁定项，lock 文件做全文级复核。

### 4. 逐段编辑

- 按 `polished_skeleton.md` 逐段填写，**不得合并、不得跳段、不得只改一部分**
- 只改语言层：语法、搭配、冠词介词、时态语态、标点、长句切分、直译腔、冗余名词化
- **禁止**改变：限定词强度、因果与相关的措辞、否定范围、量词、数字单位、引用编号、图表指向
- 术语按 `term_map` 统一；不在表内的术语不擅自替换，列入 `needs_confirmation`
- 每段产出：`pid` / `original` / `polished`；每处改动再进 `change_log`（`original` / `revised` / `change_type` / `reason`）

### 5. 改后回扫（必做）

```
python <skill_dir>/scripts/invariant_guard.py /app/work/lock.json /app/output/result.json --out /app/work/guard.json
python <skill_dir>/scripts/term_consistency.py /app/work/lock.json /app/output/result.json --term-map <术语表.json>
```

逐项核对锁定项在改文中是否原样保留；任何数字、单位、引用、图表、限定词数量下降或强度变化 → 判 `failed`，回到第 4 步修正，不得直接交付。

### 6. 成稿门槛（写 status=success 之前必须过）

```
python <skill_dir>/scripts/check_polish.py /app/output/result.json --plan /app/work/polish_plan.json
```

判六件事：段落对齐（pid 唯一、polished 非空）、不漏段、每段锁定项多重集与原文一致（不丢不增不挪段）、否定词数量一致、限定词数量偏差 ≤1、篇幅比在 0.4~3.0（0.7~1.6 之外提示）、无占位符，且 `polished_text` 与各段拼接一致。

`status=failed` → 回第 4 步继续改，**不得**跳过。

### 7. 组装输出

最终 `result.json` 必须包含题面要求的全部字段：

```json
{
  "case_id": "...",
  "status": "success | partial | unable_to_determine | refused",
  "result": {
    "polished_text": "润色后完整文本，由各段 polished 顺序拼接生成（不要另写一版）",
    "paragraphs": [
      {"pid": "P01", "original": "原文该段逐字", "polished": "润色后该段"}
    ],
    "change_log": [
      {"original":"...", "revised":"...", "change_type":"grammar|terminology|register|conciseness|punctuation",
       "reason":"...", "preserved":["..."]}
    ],
    "term_decisions": [{"from":"...", "to":"...", "basis":"term_map|needs_confirmation"}]
  },
  "sources": [
    {"claim":"...", "location":"原文第N段/第N句", "type":"fact|number|citation|term"}
  ],
  "uncertainty": ["材料不足/术语冲突/需人工确认的条目"],
  "changes": ["本次处理概览"]
}
```

最后跑契约自检：

```
python <skill_dir>/scripts/validate_result.py /app/output/result.json --case /input/case.json --out /app/work/validate.json
```

`status=success` 会被强制要求：`paragraphs` 逐段齐全且过 `check_polish` 门槛。

`status` 判定：全部段落完成且两轮回扫与门槛均通过 = `success`；部分段落完成 = `partial` 并写清缺口；材料冲突无法判断 = `unable_to_determine`；请求越界（要求加强结论/编造事实）= `refused` 并说明原因。

## 异常处理

| 情况 | 处置 |
|---|---|
| 超长输入 | `build_polish_draft.py` 按空行分段；仍过长时按 `--max-paragraphs` 分批，批间沿用同一术语表与锁定项 |
| 输入没有段落结构 | 脚本按句群聚合切段（每 3 句一段），保证仍能逐段对齐；在 uncertainty 说明切分方式 |
| 编码混乱 | 先记录原始字节与疑点，按最可能编码解码并在 uncertainty 标注；不静默替换 |
| 公式/引用混杂 | 公式与引用编号整体作为不可变 token 锁定，不做任何字符级改写 |
| 中英日混排 | 分语种处理，保持各语种内部术语一致；混排边界标 needs_confirmation |
| 术语表内部冲突 | 不擅自选边，同时列入 uncertainty 与 needs_confirmation，按 case 原始写法保留 |
| 目标文体不明 | 默认按"期刊论文"处理并在 uncertainty 说明，不猜测具体期刊风格 |
| 同一段重复润色 | 以 lock 文件为基准重新回扫，避免二次编辑造成语义漂移 |

## 依赖

纯 Python 3.9+ 标准库，无第三方依赖。所有脚本只读输入、不修改原稿。

## 资源

- `scripts/build_polish_draft.py` — **建逐段润色工作台（plan + 骨架 + 术语候选）**
- `scripts/check_polish.py` — **成稿门槛：段落对齐、锁定项守恒、强度不变、篇幅合理**
- `scripts/lock_invariants.py` — 改前锁定数字/单位/引用/图表/限定词
- `scripts/invariant_guard.py` — 改后守恒校验（限定强度、引用编号、图表指向）
- `scripts/term_consistency.py` — 术语一致性回扫与缩写首次出现检查
- `scripts/validate_result.py` — 输出契约与证据一致性校验（success 强制过成稿门槛）
- `references/hedge-and-modality.md` — 限定词强度守恒表
- `references/terminology-governance.md` — 术语表与缩写治理规则
- `references/register-by-genre.md` — 不同文体语气规则
- `references/minimal-edit.md` — 最小编辑与逐句对照规范
- `references/source-mapping.md` — 事实/数字/引用来源映射规范
- `examples/minimal-example.md` — 完整输入输出示例（示例，非正式案例结果）
