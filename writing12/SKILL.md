---
name: bilingual-academic-translator
description: 把学术原文逐段译成目标语言并产出段级双语对照稿：先锁术语表再动笔，按 Pxx 段号一一对齐，数值/单位/量级/有效数字原样落地，引用与图表公式标记保留原位，否定范围与情态强度不改。校验术语漂移、数值取整、标记丢失、限定条件删除，逐条列到段号；材料不足如实标 partial，不补写原文没有的结论。
---

# 学术翻译与双语写作（术语稳 + 数字实 + 对得齐 + 边界清）

核心命题：**翻译的错不在"语句不顺"，在四个可核查的地方**——同一个术语前后换了三种译法、
数字被顺手取整、图表引用和公式在译文里消失、`may be associated with` 被译成"导致了"。
这四件事都能从文本结构上量出来，不必靠"译得好不好"的口头判断。

## 何时使用 / 不使用

**使用**：把英文摘要/正文/图注译成中文并要双语对照；核对已有译稿的术语与数字；统一全篇译法；
保留引用与图表编号的整篇翻译。**不使用**：写原创论文（写作01）；润色中文稿（写作02）；
只查语法（写作02）。

## 预算与结构（动笔前先按这个量落）

| 项 | 最低量 | 为什么要这个量 |
|---|---|---|
| 段级对齐 | 原文段数 100% | 漏一段就是漏译，且事后无法定位 |
| 术语表 | ≥12 条，覆盖出现 ≥2 次的领域名词 | 少于 12 条说明没做抽取，只是随手续译 |
| 译文篇幅 | ≥1.4 中文字/英词（硬门槛 1.2） | 英译中常在 1.5–1.8；低于 1.2 必是省译 |
| 数值台账 | 原文每个数值 1 行 | 数值不能只"看起来在"，要能逐条点开 |
| 标记 | 引用/图表/公式/脚注四类全保留 | 少一个引用就是归属错误 |

## 门槛（定稿前逐条对照，达不到不要标 success）

| 项 | 门槛 | 谁检查 |
|---|---|---|
| 段覆盖 | ≥95%，段序不得打乱 | `validate_result.py` |
| 标记保留 | 引用/图表/公式/脚注 ≥90% | `validate_result.py` |
| 术语落地 | 术语表锁定译法在对应段出现 ≥95% | `validate_result.py` |
| 术语漂移 | 禁用变体出现 0 次 | `validate_result.py` |
| 数值落地 | 原文数值同值出现 ≥95% | `validate_result.py` |
| 量级错配 | 0 条（3.5 million ≠ 3.5 万） | `validate_result.py` |
| 语义边界 | 否定/情态/限定条件改动 ≤1 条 | `validate_result.py` |
| 限制语保留 | 带 may/suggest/associated with 的句子保留等强度措辞 ≥80% | `validate_result.py` |
| 篇幅 | ≥1.2 字/英词，且译文 ≥200 字 | `validate_result.py` |
| 干净度 | 无 `[待译]`/`TODO`/`【…】` | `validate_result.py` |

## 执行顺序

### 第 0 步 · 读真实输入
读 `/input/case.json`、`/input/task.md` 与材料本体。**先确认语向、受众、文体、输出形态**
（纯译文 / 双语对照 / 带修订标记）。任务没写清语向时按 `target_lang` 字段，不要自己猜。

### 第 1 步 · 先建术语表（这一步不能省）
从原文抽领域名词：出现 ≥2 次的多词短语、全大写缩写、希腊字母/数字下标符号。
每条写成 `{en, zh, variants[], section}`，`variants` 填**必须避免的漂移写法**（含机器翻译常见错译）。
同一英文词在不同学科译法不同时（如 `scaffold` 在材料学是"支架"、在软件是"脚手架"），
按材料所属学科锁定，并在 `section` 注明适用范围。

### 第 2 步 · 落段级骨架
```bash
python <skill_dir>/scripts/draft_bilingual.py --case /input/case.json --out /app/work/bilingual.md
```
产出 `## P01 / EN: … / ZH: [待译]` 结构。**段号是对齐主键**，后续所有核查都按它定位；
不要为了"句子顺"合并两段——合并后覆盖率会掉，且读者无法逐段对照改稿。

### 第 3 步 · 逐段译（术语表先查再译）
- 术语表命中的词，直接用锁定译法；表里没有又属领域名词的，**先补表再译**。
- 数值：原样搬到译文，**不做四舍五入**（`62.4` 不写 `62`，`0.068` 不写 `0.07`）。
  中英量级差异按真实值换算并写出：`3.5 million` → `350 万`；`1.2 billion` → `12 亿`。
- 标记：`[12,13–15]`、`(Zhang et al., 2021)`、`Fig. 2a`、`Table 1`、`$E=\sigma/\varepsilon$`、
  脚注 `^1` 全部保留；图表编号可换外壳（`Fig. 2a` → `图 2a`），但编号本体不变。
- 边界：`did not differ` → 「未见差异」而不是「差异显著」；`may be associated with` →
  「可能与…有关」而不是「导致」；`in vitro / pilot / single-centre` 这类限定条件必须跟着走。

### 第 4 步 · 落台账与自查
```bash
python <skill_dir>/scripts/build_outputs.py --result /app/output/result.json \
    --text /app/work/bilingual.md --outdir /app/output
```
产出 `term-audit.csv`（术语→译法→段号→漂移）、`align-map.csv`（段号对照图）、
`number-audit.csv`（每个数值→是否落地）、`selfcheck.md`、`preview.pdf`（有 pandoc 时）。

### 第 5 步 · 跑门槛
```bash
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/work/bilingual.md
```
`[fail]` 逐条修：术语没落地就回到第 3 步按表改；数值没落地先看是不是被四舍五入了；
标记丢失通常是译文里把「图 2a」写成了「图 2」。

### 第 6 步 · 写 result.json
`case_id` / `status` / `result.bilingual`（双语全文）/ `result.terms` / `result.human_review` /
`sources` / `uncertainty` / `changes`。`output_contract` 字段逐个覆盖。
`changes` 每条写清段号 + 改动类别（术语/数值/标记/边界）+ 具体改了什么。

## 异常处理

| 情况 | 处置 |
|---|---|
| 原文缺页码/缺图 | 译文对应段标 `not_reported`，不补造图表编号 |
| 术语表冲突（同词两译） | 以材料所属学科的主译为锁定值，另一译法写入 `variants` 并在 `uncertainty` 记录 |
| 超长文本（>20 段或 >8000 词） | 按章节分块译，块间保留段号连续；先出前 10 段并标 `partial` |
| 公式/表格在原文里是图片 | 译文中保留图位与题注编号，公式不复刻，标 `needs_human` |
| 引用格式异常（裸数字、`ibid.`） | 保留原样并标 `needs_human`，不擅自补全作者年份 |
| 语向不支持（小语种/混排） | 只译已识别语言段，其余标 `skipped` 并说明 |
| 原文编码错误/乱码 | 该段标 `unreadable`，不猜内容；在 `uncertainty` 记录段号 |
| 数值与图表不符（原文自身矛盾） | 照原文译，另在 `uncertainty` 标 `source_inconsistent` + 两个值 |
| 预算将尽 | 先落术语表 + 前 N 段双语 + 台账，标 `partial` 并写清从哪段起未译 |

## 依赖与资源

Python 3.9+，脚本仅用标准库；`preview.pdf` 需 pandoc，缺失则跳过并如实记录。

- `scripts/bilingual_gate.py` — 四把尺（术语/数值/标记/边界），被下面三个脚本共用
- `scripts/draft_bilingual.py` — 段级骨架
- `scripts/validate_result.py` — 契约 + 门槛
- `scripts/build_outputs.py` — `term-audit.csv` / `align-map.csv` / `number-audit.csv` / `selfcheck.md` / `preview.pdf`
- `references/` — 术语一致性、数值与单位、对齐、边界与否定、语域风格、异常矩阵、方案边界
- `examples/term-table.json` — 可直接换领域复用的术语表示例（生物材料，13 条）
- `eval/` — 评分表、指标脚本、对照协议、验收表（运行案例时不必读）

## 最小示例

见 `examples/minimal-example.md`。
