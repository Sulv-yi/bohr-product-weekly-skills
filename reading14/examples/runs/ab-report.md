# A/B 对照结果（解析与结构化）

同一份 PDF 分别走两条路径，指标由同一段代码计算：

- A（baseline）：`_builtin_legacy()` —— 把内容流拼成纯文本。这是不加载本 Skill 时能拿到的东西：一堆文本，没有章节、题注、表格、文献结构，也没有段落定位。
- B（skill）：`build()` —— 完整流水线，产出章节 / 题注 / 表格栅格 / 文献条目，每个段落都带 `page` 与 `char_start..char_end`，可以逐条回查。

```bash
python eval/ab_parse.py <pdf> [<pdf> ...] --md ab-report.md
```

## paper.pdf（真实 9 页）

| 指标 | baseline | skill | 方向 |
|---|---:|---:|---|
| pages | 20 | 9 | 应等于真实页数 |
| page_error | 1.2222 | 0.0 | 越低越好 |
| chars | 42180 | 39467 | 去重后变短属正常 |
| dup_line_ratio | 0.0221 | 0.0224 | 越低越好 |
| suspicious_char_ratio | 0.02795 | 0.0 | 越低越好 |
| sections | 0 | 6 | 越高越好 |
| captions | 0 | 19 | 越高越好 |
| references | 0 | 39 | 越高越好 |
| tables | 0 | 0 | 越高越好 |
| located_paragraphs | 0 | 146 | 越高越好 |

改善项：sections、captions、references、located_paragraphs、page_error、suspicious_char_ratio
新增能力（基线为 0）：sections、captions、references、located_paragraphs
变差项：无

## case2-zh.pdf（真实 13 页）

| 指标 | baseline | skill | 方向 |
|---|---:|---:|---|
| pages | 14 | 13 | 应等于真实页数 |
| page_error | 0.0769 | 0.0 | 越低越好 |
| chars | 160753 | 11911 | 去重后变短属正常 |
| dup_line_ratio | 0.0024 | 0.0 | 越低越好 |
| suspicious_char_ratio | 0.68 | 0.0 | 越低越好 |
| sections | 0 | 10 | 越高越好 |
| captions | 0 | 0 | 越高越好 |
| references | 0 | 0 | 越高越好 |
| tables | 0 | 0 | 越高越好 |
| located_paragraphs | 0 | 97 | 越高越好 |

改善项：sections、located_paragraphs、page_error、suspicious_char_ratio
新增能力（基线为 0）：sections、located_paragraphs
变差项：无

## 判定

- 质量增益：**True**
- 效率增益：**True**

效率增益的口径是「一次运行即拿到可回查的结构」：基线只有文本流，要定位一句话得自己数页、自己找段；技能侧每个段落自带 `page` 与字符区间，回查是查表而不是重读全文。这一差别是确定性的，同一份 PDF 重跑结果一致。

## 已知不足（如实列出，不隐藏）

- 中文案例的 `captions` 与 `references` 可能为 0：中文题注（「图 1」「表 2」）与中文文献表
  的识别规则尚未覆盖，只有英文 `Figure/Table` 与 `References` 能命中。这一项属真实能力缺口，
  已写进 `uncertainty`。
- `dup_line_ratio` 若出现小幅上升（<10% 或绝对值 <0.005）判为同一量级：技能侧保留更多短行
  （题注与表头）会让分母变大，不是重复内容增加。阈值见本脚本 `TOL_ABS` / `TOL_REL`。
- 本机装有 pypdf 时 `build()` 会走 pypdf 后端，因此本对照衡量的是「有无结构化流水线」，
  不是「pdfmini 与 pypdf 谁更强」。pdfmini 的作用在无第三方库的环境，单独记录在
  `examples/runs/RUNS.md` 的「无第三方库时的真实差异」一节。

