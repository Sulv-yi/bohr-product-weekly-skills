# 增益对照协议（A/B，可复现）

用途：让「加载 Skill 是否真的更好」可以被第三方重跑，而不是靠文字自述。
平台会自己做基础 Agent 与 Skill Agent 的对照；本文件给出**同一套口径**，
任何人换一篇论文都能照做。

## 1. 对照条件必须逐项一致

| 条件 | 要求 | 如何保证 |
|---|---|---|
| 输入材料 | 同一份、同一版本 | 记录材料 sha256 前 12 位 |
| 任务指令 | 同一句 | 用同一 `task.md`，只改"是否加载 Skill" |
| 轮次预算 | 相同模型、相同请求上限 | 记录 model 与 max_requests（题面为 64/900s） |
| 评分口径 | 同一 `eval/rubric.json` | 阈值写死在文件里，不随人调 |
| 评分人 | 同一人 / 同一 judge | 记录 judge 标识 |
| 顺序 | A/B 匿名、随机 | 由第三方抽签决定呈现顺序 |

任何一项不同，差值就不能归因于 Skill。

## 2. 两个条件

- **A（baseline）**：不加载本 Skill，指令为「根据材料写方法章节与实验设置」。
- **B（skill）**：加载本 Skill，按 `SKILL.md` 执行，产出 `section.md` + `result.json` + `source-map.csv` + `selfcheck.md`。

两侧使用同一材料、同一轮次预算、同一模型。

## 3. 重复性与取数

- 每个条件重复 **3 次**（与平台一致）。
- 指标取 3 次的**中位数**，同时报告极差（max−min）。
- 若 3 次的相关工作分组数或四要素结构不一致，说明输出不稳定，先修 Skill 再比较。

## 4. 指标与判定

用 `eval/score_output.py` 分别对 A、B 算同一组指标：

| 指标 | 含义 | 方向 |
|---|---|---|
| `element_coverage` | 六类要素是否各自成段 | 越高越好，1.0 为满 |
| `param_rows` | 参数表行数 | ≥5 |
| `param_source_rate` | 参数表带来源列的行占比 | 越高越好，1.0 为满 |
| `param_body_alignment` | 表中取值在正文出现的比例 | 越高越好 |
| `baseline_coverage` | 对照六项命中率 | 越高越好，≥0.67 |
| `repro_coverage` | 复现六项命中率 | 越高越好，≥0.67 |
| `limitation_specific` | 限制是否落到具体失效场景 | 是更好 |
| `placeholder_count` | 残留占位符 | 越低越好，0 为满 |
| `open_gaps` | 缺口与待确认条数 | 越低越好，但不得为 0 而隐藏真实缺口 |

**增益判定**（只报差值，不报绝对分）：

```
Δmetric = median(B) − median(A)
```

- 质量增益成立：`Δelement_coverage ≥ 0` 且 `Δparam_source_rate ≥ 0`
  且至少两项严格变好，且 `Δplaceholder_count ≤ 0`（不许靠删内容换指标）。
- 效率增益成立：`Δopen_gaps ≤ 0` 且 B 的 `param_source_rate == 1.0`。
- 任一项变差，如实写进 `result.uncertainty`，不挑选性报告。
  已知会变差的一项：`manual_review_items` 常在 Skill 侧升高，因为 Skill 更愿意把材料缺口登记出来。
  这是诚实性代价，不视为效率增益的反证；效率增益以平台记录的耗时与轮次为准。

## 5. 盲评（结构指标覆盖不到的部分）

1. 把 A、B 两版去标识化为「版本 1」「版本 2」，顺序随机。
2. 评分人只看两份文本 + `eval/acceptance.md` 第 2 节的评分表。
3. 至少 2 人独立打分，不给对方看结果。
4. 报告均值与分歧项；分歧项必须写清"为什么分歧"（引用具体句子）。

## 6. 复现命令

```bash
# A 条件
python eval/score_output.py --result /app/work/A-result.json --case /input/case.json --draft /app/work/A-section.md --out /app/work/A-scorecard.json
# B 条件
python eval/score_output.py --result /app/output/result.json --case /input/case.json --draft /app/output/section.md --out /app/output/scorecard.json
# 对比
python eval/compare_ab.py /app/work/A-scorecard.json /app/output/scorecard.json --md /app/output/ab-report.md
```

`compare_ab.py` 的判定规则就是第 4 节，不含人工加权。

## 7. 边界

- 本协议不产生「正式案例成绩」，只用于开发期自测与第三方复现。
- `examples/` 中的案例与输出均标注为示例（材料为演示用虚构内容），不冒充平台固定案例。
- 若平台已给出对照结果，以平台结果为准；本协议用于解释差异来源。
