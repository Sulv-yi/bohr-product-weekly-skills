# A/B 对照协议

## 4. 判定规则（解析与结构化类）

两侧共用同一份 PDF，指标由 `eval/ab_parse.py` 里同一段代码计算：

| 指标 | 含义 | 方向 |
|---|---|---|
| `page_error` | `|输出页数 − 真实页数| / 真实页数` | 越低越好 |
| `dup_line_ratio` | 重复文本行占比（页序错乱时的典型症状） | 越低越好 |
| `suspicious_char_ratio` | 可疑字符占比（缺 ToUnicode 时的症状） | 越低越好 |
| `sections` / `captions` / `references` / `tables` | 结构化条目数 | 越高越好 |
| `located_paragraphs` | 带 `page` 与字符区间的段落数 | 越高越好 |

- 质量增益成立：每个案例没有变差项，且至少两项严格变好。
- 效率增益成立：`page_error` 不高于基线，且 `located_paragraphs > 0`（可回查）。
- 基线为 0 而技能侧有产出（`new_capability`）按**新增能力**计，不按「变好一点」计。

**关于解析后端**：本机装有 pypdf 7.1.1，`build()` 优先走 pypdf。`pdfmini.py` 是环境无
第三方库时的降级路径，其价值见「可靠性」一节（同一份 9 页论文，旧拼接路径输出 20 页、
可疑字符 2.80%，pdfmini 输出 9 页、可疑字符 0）。不要把两者混成一个对照。
