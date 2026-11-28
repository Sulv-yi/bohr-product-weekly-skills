# A/B 对照结果

同一份输入（`examples/selftest-case.json`，6 段中文摘要），用**同一个评分脚本、同一份 rubric**分别给两份产物打分：

- A（baseline）：不加载本 Skill 的基础 Agent 典型输出形态 —— 逐段整体重写、无逐句修改说明、限定强度在改写中漂移。产物见 `examples/baseline-result.json`。
- B（skill）：按本 Skill 流程产出 —— 最小编辑、逐句说明、术语先定。产物见 `examples/selftest-result.json`。

复现命令：

```bash
python eval/score_output.py --result examples/baseline-result.json \
    --case examples/selftest-case.json --out examples/baseline-scorecard.json
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --out examples/scorecard.json
python eval/compare_ab.py examples/baseline-scorecard.json examples/scorecard.json
```

## 逐项指标

| 指标 | baseline | skill | Δ | 判定 |
|---|---:|---:|---:|---|
| segment_coverage | 1 | 1 | +0.0000 | same |
| invariant_conservation | 1 | 1 | +0.0000 | same |
| hedge_conservation | 1 | 1 | +0.0000 | same |
| negation_conservation | 0.8333 | 1 | +0.1667 | better |
| term_uniqueness | 0 | 1 | +1.0000 | better |
| edit_note_coverage | 0 | 1 | +1.0000 | better |
| sentence_change_rate | 0.8571 | 0.2857 | -0.5714 | ok |
| manual_review_items | 0 | 2 | +2.0000 | info |
| errors_before_accept | 3 | 0 | -3.0000 | better |

## 结论

- 质量增益：**established**
- 效率增益：**established**

效率增益的口径是**交付前必须消除的错误条数**（`errors_before_accept`，取自同一脚本的 `errors` 列表长度）：
基线产物要消除 3 类错误（无术语决策记录、逐句说明缺失、术语一致性 0）才达到可交付，
Skill 产物一次通过（0 条）。这不是估时，是把两份产物分别喂给同一校验脚本得到的确定性结果，任何人可复现。

## 如实标注的项（不计优劣）

`manual_review_items` 基线 0 → skill 2。这不是退步：Skill 会把「术语分工需按目标期刊核」
和「本样例只做语言层编辑」两条不确定项写进 `uncertainty`，基线一条都没标。
把「标注得多」当「效率差」会惩罚诚实标注，因此该项只展示、不参与增益判定。

## 已知不足

- `hedge_conservation` 与 `invariant_conservation` 两侧都是 1.0，说明这份样例上这两项的区分度不足；
  要真正压出差距，需要一份限定词更密集的样例。已在 `uncertainty` 说明。
- 对照只覆盖中文摘要 6 段。英文材料的最小编辑阈值（改动率上限）未在本题验证。
