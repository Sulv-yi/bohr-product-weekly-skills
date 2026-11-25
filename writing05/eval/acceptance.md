# 验收表：什么算交付完成

硬门槛（H）不过 → 不许标 `success`。软性项（S）不过 → 可以交付但必须在
`uncertainty` 说明。所有项都能用下面的命令复算，不看自述。

## 硬门槛

| 编号 | 门槛 | 判据 | 复核命令 |
|---|---|---|---|
| H1 | 成稿实体 | `draft.md` 存在，正文 ≥1400 字（西文按词 ×0.6） | `validate_result.py --text draft.md` |
| H2 | 三段齐备 | 成稿 + `result.claims[]` + `result.evidence_table[]` 同时存在且非空 | 同上 |
| H3 | 论断覆盖 | 论断清单覆盖成稿论断单元 ≥80% | 同上（`claim_coverage`） |
| H4 | 精确定位 | ≥90% 的论断带页/节/段定位 | 同上（`locator_rate`） |
| H5 | 强度判定 | 100% 判定的论断落在四档内，无 `needs_review` 残留 | 同上（`strength_rate`） |
| H6 | 表述相称 | ≥80% 的论断表述强度与证据强度相称 | 同上（`hedge_alignment`） |
| H7 | 来源可回溯 | ≥12 条来源，file+(page\|section)+quote 齐备率 ≥90% | 同上（`source_metadata_rate`） |
| H8 | 冲突处置 | `conflicts[]` 非空，或 `conflict_search_note` 说明检索范围 | 同上 |
| H9 | 干净度 | 无 `【…】` / `{{…}}` / `TODO` / `待补` 残留 | 同上（`placeholder_count`） |
| H10 | 证据表闭合 | ≥90% 论断有对应证据行，且证据行的 `claim_id` 都存在 | 同上 |

## 软性项

| 编号 | 项 | 期望 | 说明 |
|---|---|---|---|
| S1 | 成稿引用绑定 | 论断单元挂引用编号 ≥60% | 未挂的在自检表说明（如本文自有数据） |
| S2 | 来源集中度 | 单篇来源支撑 ≤3 条论断 | 超过要检查是否过度引用 |
| S3 | 待确认项 | `uncertainty` 非空 | 至少写一处材料缺口 |
| S4 | 预览 | 有 pandoc 时产出 `preview.pdf` | 无环境判 n/a，不声称已渲染 |
| S5 | 对照报告 | `examples/ab-report.md` 存在且列出变差项 | 变差项为空也要写"无" |

## 五性质盲评表（给评审用，不看作者自述）

| 性质 | 只看这一份文件就能判断 | 文件 |
|---|---|---|
| 找得到 | 每条论断是否落到具体文献的具体段落 | `claim-map.csv` |
| 对得上 | 摘录是否真的支撑论断、著录是否准确 | `evidence-table.md` |
| 说得准 | 证据强度与正文语气是否相称 | `claim-map.csv` 的 `hedge_ok` 列 + 正文 |
| 复得现 | 论断编号/摘录/定位/强度理由是否四件齐 | `claim-map.csv` + `evidence-table.md` |
| 不越界 | 材料外事实是否被引入 | `result.uncertainty` + 正文 |

## 复核顺序（60 秒）

```bash
python scripts/validate_result.py examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-draft.md
python scripts/claim_split.py --text examples/selftest-draft.md
python scripts/build_outputs.py --result examples/selftest-result.json \
    --draft examples/selftest-draft.md --outdir /tmp/o05
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --draft examples/selftest-draft.md \
    --baseline examples/baseline-scorecard.json --out /tmp/o05/card.json
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/o05/card.json
```
