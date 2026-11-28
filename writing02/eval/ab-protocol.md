# 增益对照协议（A/B，可复现）

用途：让「加载 Skill 是否真的更好」这件事**可以被第三方重跑**，而不是靠文字自述。
平台会自己做基础 Agent 与 Skill Agent 的对照；本文件给出的是同一套对照口径，
任何人在自己的稿件上都能照做。

## 1. 对照条件必须逐项一致

| 条件 | 要求 | 如何保证 |
|---|---|---|
| 输入原文 | 同一份、同一版本 | 记录原文的 sha256 前 12 位 |
| 术语表 | 同一份 | 记录术语表 sha256 |
| 风格规则 | 同一份 register 规则 | 同一 `references/register-by-genre.md` |
| 轮次预算 | 相同模型、相同请求上限 | 记录 model 与 max_requests |
| 评分口径 | 同一 `eval/rubric.json` | 阈值写死在文件里 |
| 评分人 | 同一人 / 同一 judge | 记录 judge 标识 |
| 顺序 | A/B 匿名，随机顺序 | 由 `eval/ab-protocol.md` 的抽签脚本决定 |

任何一项不同，差值就不能归因于 Skill。

## 2. 两个条件

- **A（baseline）**：不加载本 Skill。只给通用指令「请润色下面这段学术文本，保持原意」。
- **B（skill）**：加载本 Skill，按 `SKILL.md` 的工作流执行，产出 `result.json` + `scorecard.json`。

A 与 B 使用**同一份原文、同一术语表、同一轮次预算**。

## 3. 重复性与取数

- 每个条件重复 **3 次**（平台也是 3 次）。
- 指标取 3 次的**中位数**，同时报告极差（max−min）。
- 同一段落 3 次结果的改动句集合若差异超过 30%，说明结论漂移，先修 Skill 再比较。

## 4. 指标与判定

用 `eval/score_output.py` 对 A、B 各自算同一组指标：

| 指标 | 含义 | 方向 |
|---|---|---|
| `invariant_conservation` | 数字/单位/引用/图表指向守恒率 | 越高越好，1.0 为满 |
| `hedge_conservation` | 限定强度守恒段占比 | 越高越好 |
| `negation_conservation` | 否定范围守恒段占比 | 越高越好 |
| `term_uniqueness` | 术语统一译法落实率 | 越高越好 |
| `edit_note_coverage` | 有原文/改文/理由的改动占比 | 越高越好 |
| `sentence_change_rate` | 改动句比例 | 越接近 0.2~0.4 越好，>0.6 视为过度改写 |
| `manual_review_items` | 需人工确认条目数 | **只展示，不判优劣**：这一项少只说明标注得少，不能说明结果更好；把它当"越少越好"等于惩罚诚实标注 |
| `errors_before_accept` | 交付前必须消除的错误条数 | 越低越好；取自同一评分脚本的 `errors` 列表长度，可确定性复现 |

**增益判定**（只报差值，不报绝对分）：

```
Δmetric = median(B) − median(A)
```

- 质量增益成立：`Δ invariant_conservation ≥ 0` 且 `Δ term_uniqueness ≥ 0`
  且至少两项严格变好，且 `sentence_change_rate` 没有升到 0.6 以上。
- 效率增益成立：B 的 `errors_before_accept = 0` 且 `errors_before_accept(B) ≤ errors_before_accept(A)`，
  且 B 的改动句都有对应说明（`edit_note_coverage ≥ 0.9`）。
  效率用"要修几轮才干净"来衡量，不用"人工确认项几条"来衡量——后者随标注详细程度反向变化，不适合当效率代理。
- 若某项变差，如实写进 `result.uncertainty`，不挑选性报告。`manual_review_items` 属如实标注，
  不参与增益判定，但要在报告里列出两侧数值并说明差异来源。

## 5. 盲评（质量增益的主观部分）

指标覆盖不了「是否更像同行写的」。这一项用盲评：

1. 把 A、B 两版去标识化为「版本 1」「版本 2」，顺序随机。
2. 评分人只看到两份文本 + 同一份评分表（`eval/acceptance.md` 第 2 节）。
3. 每人独立打分，不给对方看结果。
4. 至少 2 人；报告均值与分歧项，分歧项要写清"为什么分歧"。

## 6. 复现命令

```bash
# A 条件
python eval/score_output.py --result /app/work/A-result.json --case /input/case.json --out /app/work/A-scorecard.json
# B 条件
python eval/score_output.py --result /app/output/result.json --case /input/case.json --out /app/output/scorecard.json
# 对比
python eval/compare_ab.py /app/work/A-scorecard.json /app/output/scorecard.json
```

`compare_ab.py` 输出 Δ 表与判定，判定规则就是上面第 4 节，不含任何人工加权。

## 7. 边界

- 本协议不产生「正式案例成绩」，只用于开发期自测与第三方复现。
- 示例集在 `examples/` 中，均标注为示例，不冒充平台固定案例。
- 若平台已提供对照结果，以平台结果为准；本协议用于解释差异来源。
