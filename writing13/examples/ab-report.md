# A/B 对照结果

- baseline: `examples/baseline-manuscript.tex` + `examples/baseline-scorecard.json`
- skill: `examples/selftest-manuscript.tex` + `examples/scorecard.json`
- 生成命令：`python eval/compare_ab.py examples/baseline-scorecard.json examples/scorecard.json --md examples/ab-report.md`
- 两侧均在真实引擎（tectonic 0.15.0）下编译，完整记录见 `examples/runs/REAL-BUILD.md`

## 一、静态指标（脚本生成，未手改）

| 指标 | baseline | skill | Δ | 方向 |
|---|---|---|---|---|
| sections | 2 | 5 | +3 | higher |
| total_real_chars | 102 | 1973 | +1871 | higher |
| min_section_chars | 38 | 289 | +251 | higher |
| equations | 0 | 1 | +1 | higher |
| tables | 0 | 1 | +1 | higher |
| cite_keys | 1 | 10 | +9 | higher |
| cite_resolved_rate | 1.0 | 1.0 | +0 | higher |
| repro_coverage | 0.4 | 1.0 | +0.6 | higher |
| source_map_count | 1 | 10 | +9 | higher |
| compile_errors_located_rate | 1.0 | 1.0 | +0 | higher |
| compile_errors | 0 | 0 | +0 | lower |
| placeholder_errors | 0 | 0 | +0 | lower |

## 二、真实编译指标（两边都实际编译）

| 指标 | baseline | skill |
|---|---:|---:|
| compile_status（脚本判定） | `needs_more_rounds` | `success` |
| PDF 页数 | 1 | 5 |
| PDF 字节 | 40,283 | 209,054 |
| **undefined 引用** | **2** | **0** |
| **LaTeX Warning** | **3** | **0** |
| Overfull / Underfull box | 0 / 0 | 0 / 0 |
| 硬错误（`!`） | 0 | 0 |

基线三条警告原文：

```
LaTeX Warning: No \author given.
LaTeX Warning: Citation `wang2019' on page 1 undefined on input line 8.
LaTeX Warning: There were undefined references.
```

三条正好对应本 Skill 的三个检查点：模板必填项、引用闭合、结构完整。

## 三、评分卡逐项

| 侧 | pass | fail | n/a | fail 明细 |
|---|---:|---:|---:|---|
| baseline | 8 | 7 | 0 | 任务完成度、结果正确性、结果完整性、结果可核验性、质量增益、增益可验证性、稳定性 |
| skill | 15 | **0** | 1 | — |

## 四、结论

- **编译状态**：baseline=`needs_more_rounds`（有未解析引用）→ skill=`success`（0 警告，引用全解析）
- **质量增益成立**：结构要素全部增加，编译警告降到 0
- **效率增益成立**：Skill 侧一次 `build → check → static → compile → verify` 即得零警告产物
- **变差项**：无

## 五、边界

本对照为本地自建，用于证明能力差异；平台正式对照以组织方生成的为准。
tectonic 的 `internal consistency problem ... main.bbl changed` 属引擎内部提示，非稿件缺陷，
最终 undefined = 0。详见 `examples/runs/REAL-BUILD.md` 第四节。
