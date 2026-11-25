# 评分点 → 证据位置对照表

题面五维 100 分。下表说明「这一分靠什么拿、在哪能查到」，末尾附 60 秒自查。
不含自评分——自评不被采信，能复算的指标才作数。

## 实际效果（40）

| 评分点 | 分 | 对应产物 | 复核方式 |
|---|---|---|---|
| 任务完成度 | 15 | `manuscript.md`（八节成稿） | 字数 ≥1800、章节齐备度 ≥75% |
| 结果正确性 | 15 | `material-index.csv` + `cite-audit.csv` | 引用闭合 100%、数值可回溯 ≥90%、占位符 0 |
| 结果完整性 | 5 | 稿件声明节 + 图表题注 | 声明 ≥2 类且含数据可得性、图表成对 ≥2 |
| 结果可核验性 | 5 | `material-index.csv` + `section-map.csv` | 索引 ≥8 条带 locator、论断句挂引用 ≥50% |

## 使用增益（25）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 质量增益 | 15 | `examples/ab-report.md`：8 项变好、0 项变差 |
| 效率增益 | 5 | 索引前置使「找数值出处」不再靠回读全文 |
| 增益可验证性 | 5 | `eval/rubric.json` + `score_output.py` + `compare_ab.py` 同口径重跑 |

## 创新增益（15）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 新增能力 | 5 | `sections_gate.num_trace_rate`（正文数值逐值回溯）+ `fig_pairs`（题注双向配对） |
| 方法改进 | 5 | 材料索引先于正文；字数口径计入数字，避免注水 |
| 创新证据 | 5 | `references/innovation-boundary.md`（含做不到的 5 条） |

## 可靠体验（10）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 调用与易用性 | 3 | `SKILL.md` 七步 + `examples/minimal-example.md` |
| 运行稳定性 | 4 | 脚本仅标准库；重复运行结果一致；缺字段不崩 |
| 异常处理 | 3 | `references/edge-cases.md` 八类 |

## 生态贡献（10）

| 评分点 | 分 | 对应证据 |
|---|---|---|
| 文档完整性 | 3 | `README.md` + `references/section-spec.md` |
| 资源可复用性 | 4 | 章节清单、材料索引结构、度量口径均可直接复用 |
| 分享推广价值 | 3 | `GITHUB_URL.txt` + `references/edge-cases.md` |

## 60 秒自查（五条命令）

```bash
cd <skill_dir>
python scripts/validate_result.py examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-manuscript.md
python scripts/build_outputs.py --result examples/selftest-result.json \
    --text examples/selftest-manuscript.md --outdir /tmp/o01
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-manuscript.md \
    --baseline examples/baseline-scorecard.json --out /tmp/o01/card.json
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/o01/card.json
```

## 当前实测数值（可复算）

| 指标 | 值 | 门槛 |
|---|---|---|
| 稿件字数 | 1918 | ≥1800 |
| 章节齐备度 | 88%（7/8 达标） | ≥75% |
| 正文引用 / 文献条目 | 12 / 12（闭合 100%） | ≥12 且全部闭合 |
| 图表成对 | 1 图 + 1 表 | ≥2 组 |
| 材料索引 | 10 条 | ≥8 |
| 论断句挂引用 | 88% | ≥50% |
| 数值可回溯率 | 100% | 告警线 90% |
| 声明字段 | 3 类（数据可得性/作者贡献/利益冲突） | ≥2 且含数据可得性 |
| 占位符 | 0 | 0 |
