---
name: results-discussion-writer
description: 依据数据表、图表与统计输出写出结果与讨论章节：结果段只写观察并把每个数值标到（图 n）/（表 n），讨论段承担文献对照、机制推测与局限。校验正文数值与图表数据逐值一致、显著性措辞必须带统计量、结果段不夹解释、局限写到可检验层面。当任务要求"写结果与讨论""把数据写成章节""核对正文数值与图是否一致""说明趋势与显著性"时使用；缺图缺统计量如实标 partial，不编造数值。
---

# 结果与讨论章节写作（数值可回溯 + 统计量对齐 + 两节分离）

核心命题：**结果段只写观察，讨论段才解释**。题面四问——读得准（图表数值、单位、误差棒、
统计量正确读入）、分得清（结果段与讨论段不互相顶替）、说得住（趋势与因果表述有数据支撑）、
核得了（每个数值能回到某张图或某张表）。

## 何时使用 / 不使用

**使用**：把实验数据/图表写成结果与讨论；核对正文数值与图是否一致；补统计量与显著性表述；
写局限性。**不使用**：写方法章节（写作09）；写整篇初稿（写作01）；只润色语言（写作02）。

## 篇幅与结构预算（动笔前先按这个量写）

| 节 | 最低字数 | 必须含 |
|---|---|---|
| 结果 | 250 | 按图序/问题序；每个数值后标（图 n）或（表 n）；显著性措辞后带 p 值或检验名 |
| 讨论 | 300 | 与文献对照写"一致/不一致 + 可能原因"；机制推测写"可能"；每段落到一条数据或文献 |
| 局限 | 100 | 至少 3 条可检验线索：n、重复次数、单一物种/中心、未做的对照、随访时长 |

全文 **≥1200 字**；`figure_data` **≥2 行**（否则数值无处可核）。
`figure_data` 每行写 `{fig_id, caption, n, error_bar, stat, values{}}`——
正文出现的每个数值都必须能在 `values` 里找到同值。

## 门槛（定稿前逐条对照，达不到不要标 success）

| 项 | 门槛 | 谁检查 |
|---|---|---|
| 结果段字数 | ≥250 | `validate_result.py` |
| 讨论段字数 | ≥300 | `validate_result.py` |
| 图表数据行 | ≥2 | `validate_result.py` |
| 数值一致率 | 结果段数值与图表数据同值 ≥90% | `validate_result.py` |
| 统计支撑 | 显著性措辞带 p/CI/检验名 ≥80% | `validate_result.py` |
| 结果段解释句 | ≤2 句 | `validate_result.py` |
| 趋势边界 | 有小幅差异时必须写"未达显著"这类边界 | `validate_result.py` |
| 论断绑定 | ≥60% 句子挂引用编号或图表编号 | `validate_result.py` |
| 局限具体性 | ≥3 条可检验线索，禁"样本较少"套话 | `validate_result.py` |
| 干净度 | 无 `【…】`/`TODO`/`待补` | `validate_result.py` |

## 执行顺序

### 第 0 步 · 读真实输入
读 `/input/case.json` 与 `/input/task.md`，再读材料本体（数据表、图注、统计输出）。

### 第 1 步 · 先建图表数据（figure_data）
把每张图/表的数值落成 `{fig_id, caption, n, error_bar, stat, values{}}`。
**先于正文**：正文数值必须从这里取，否则会被"数值一致率"判为凭空出现。

### 第 2 步 · 落骨架
```bash
python <skill_dir>/scripts/draft_skeleton.py --case /input/case.json --out /app/output/chapter.md
```

### 第 3 步 · 写结果段（只写观察）
- 每句一个观察，数值后标（图 n）/（表 n）。
- 显著性必须带统计量：`（p=0.012，t 检验）`；没有统计量就不要写"显著"。
- 小幅差异写边界：`方向一致但未达显著（p=0.068）`。
- **不写**因为/由于/机制——那是讨论段。

### 第 4 步 · 写讨论段（解释与对照）
- 一致：`与…报道接近`；不一致：`与…不一致，可能原因是…`。
- 机制写"可能"，并说明本文是否测了关键中介变量。
- 每段落到一条本研究数据或具体文献，避免空谈。

### 第 5 步 · 写局限（具体化）
写 n、重复次数、物种/中心、未做的对照、随访时长、测量方法误差。
禁用"样本较少""有待进一步研究"这类套话——脚本会把它们列出来。

### 第 6 步 · 落附件
```bash
python <skill_dir>/scripts/build_outputs.py --result /app/output/result.json \
    --text /app/output/chapter.md --outdir /app/output
```
产出 `figure-audit.csv`（正文每个数值 → 图表字段）、`claim-map.csv`（图表清单）、
`selfcheck.md`、`preview.pdf`（有 pandoc 时）。

### 第 7 步 · 跑门槛
```bash
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/chapter.md
```

### 第 8 步 · 写 result.json
`case_id` / `status` / `result.manuscript`（章节全文）/ `result.figure_data` /
`sources` / `uncertainty` / `changes`。`output_contract` 字段必须逐个覆盖。

## 异常处理

| 情况 | 处置 |
|---|---|
| 缺图注或图注无 n | 补题注与 n；补不出在 `uncertainty` 标 `not_reported`，误差棒含义写"未标注" |
| 有数值无统计量 | 补 p 值/CI/检验名；给不出就把"显著"改为"方向一致"并降级 |
| 单位不明 | 以材料原始单位为准；换算要在正文写明换算关系 |
| 图表读数不清 | 不猜数值；该点写"图上无法读数"并列进 `uncertainty` |
| 引用找不到全文 | 只作背景引用，不用于支撑数值比较 |
| 阴性结果 | 照写，并写清"未观察到"而非"无差异" |
| 预算将尽 | 先落结果段 + figure_data + 局限，标 `partial` |

## 依赖与资源

Python 3.9+，脚本仅用标准库；`preview.pdf` 需 pandoc，缺失则跳过并如实记录。

- `scripts/draft_skeleton.py` — 结果/讨论/局限骨架
- `scripts/results_gate.py` — 度量（数值回溯、统计对齐、泄漏、局限具体性），被下面两个脚本共用
- `scripts/validate_result.py` — 契约 + 门槛
- `scripts/build_outputs.py` — `figure-audit.csv` / `claim-map.csv` / `selfcheck.md` / `preview.pdf`
- `references/` — 图表读取、统计语言、两节分离、异常矩阵、方案边界
- `eval/` — 评分表、指标脚本、对照协议、验收表（运行案例时不必读）

## 最小示例

见 `examples/minimal-example.md`。
