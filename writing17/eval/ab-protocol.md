# A/B 对照协议

## 目的

证明加载本 Skill 相对不加载，在同一份材料、同一个任务上的增益可被第三方按同一脚本复算。

## 输入

- 材料：`examples/selftest-materials.md`（技术报告摘要，含 5 节）
- 案例：`examples/selftest-case.json`
- 基线稿：`examples/baseline-popular.md`（直译压缩：不展开缩写、丢限定、无溯源、无改动账）
- 成稿：`examples/selftest-popular.md`

## 判定规则（写死）

- 质量增益成立 ⇐ 14 项指标中变好 ≥3 且变差 =0。
- 效率增益成立 ⇐ 越界断言、术语漂移、占位符三项都不高于基线（三项都是"要人回头改"的返工量）。

## 复算命令

```bash
python eval/score_output.py --result examples/baseline-result.json --case examples/selftest-case.json \
    --text examples/baseline-popular.md --out examples/baseline-scorecard.json
python eval/score_output.py --result examples/selftest-result.json --case examples/selftest-case.json \
    --text examples/selftest-popular.md --baseline examples/baseline-scorecard.json --out examples/scorecard.json
python eval/compare_ab.py examples/baseline-scorecard.json examples/scorecard.json --md examples/ab-report.md
```

## 不做的事

- 不换材料做对照（差异会来自材料本身）
- 不选择性报告（变差项必须出现在 ab-report.md）
- 不用自评分代替判定（只输出 pass/fail 与指标值）
