# 验收表：什么算交付完成

硬门槛（H）不过 → 不许标 `success`；软性项（S）不过 → 可交付但要在 `uncertainty` 说明。
所有项都能用命令复算，不看自述。

## 硬门槛

| 编号 | 门槛 | 判据 | 复核命令 |
|---|---|---|---|
| H1 | 稿件实体 | `manuscript.md` 存在，≥1800 字（西文词×0.6、数字×0.6） | `validate_result.py --text` |
| H2 | 章节齐备 | 八类中 ≥6 类达到该节字数门槛 | 同上（`section_coverage`） |
| H3 | 参考文献 | ≥12 条，正文编号 100% 闭合，无悬空 | 同上（`cite_resolved_rate`） |
| H4 | 图表配对 | 题注与正文提及成对 ≥2 组，无孤立题注 | 同上（`fig_pairs`/`tab_pairs`） |
| H5 | 材料索引 | ≥8 条，条条有 locator | 同上（`material_index_count`） |
| H6 | 论断绑定 | ≥50% 论断句挂引用编号 | 同上（`binding_rate`） |
| H7 | 声明字段 | ≥2 类且含数据可得性 | 同上（`declaration_fields`） |
| H8 | 数值可回溯 | 正文数值能在材料/来源 `quote` 找到同值 ≥90% | `selfcheck.md` |
| H9 | 干净度 | 无 `【…】`/`{{…}}`/`TODO`/`待补` | 同上（`placeholder_count`） |

## 软性项

| 编号 | 项 | 期望 |
|---|---|---|
| S1 | 摘要含结果数值 | 摘要出现结果段的数值与边界句 |
| S2 | 讨论含不一致文献 | 至少一处"与…不一致 + 可能原因" |
| S3 | 局限具体 | 写到方法/样本/测量层面，非"样本较少"套话 |
| S4 | 预览 | 有 pandoc 时产出 `preview.pdf`，无则判 n/a |
| S5 | 对照报告 | `examples/ab-report.md` 存在且列出变差项（无也写"无"） |

## 四问盲评表（给评审用，不看作者自述）

| 性质 | 只看这一份文件就能判断 | 文件 |
|---|---|---|
| 写得实 | 正文数值是否都有材料出处 | `material-index.csv` |
| 引得对 | 正文编号与文献条目是否一一对应 | `cite-audit.csv` |
| 全得起来 | 章节/图表/声明是否齐备 | `section-map.csv` + 稿件 |
| 改得动 | 层级、题注编号、引用格式是否保留 | `manuscript.md` |

## 复核顺序（60 秒）

```bash
python scripts/validate_result.py examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-manuscript.md
python scripts/build_outputs.py --result examples/selftest-result.json \
    --text examples/selftest-manuscript.md --outdir /tmp/o01
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-manuscript.md \
    --baseline examples/baseline-scorecard.json --out /tmp/o01/card.json
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/o01/card.json
```
