---
name: reference-citation-manager
description: 参考文献与引用管理 Skill。从真实稿件与文献库出发，完成引用插入定位、编号同步更新、文献去重归并、格式转换与字段保留、来源核验与正文—文末一致性检查，并交付可继续编辑的稿件与可逐条回溯的引用记录。核心保证：挂得对、编得顺、收得净、对得上。适用于学术写作中需要保证引用真实、编号连续、去重可解释、论断与文献匹配的场景。
---

# 参考文献与引用管理 Skill

围绕真实、高频的引用管理任务，形成可运行、可核验、可改进的最小闭环。聚焦四个问题：**挂得对 / 编得顺 / 收得净 / 对得上**。用同一份稿件与同一个文献库做前后对照时可给出可核验的改进证据。

**核心原则：交付的是可核对的产物本体，不是脚本运行结果本身。** 先落交付清单骨架（保证六类产物齐全），再填真实内容，最后才跑核验；标 success 必须有可编辑稿件、逐条 citations 与可回溯 sources，缺一即为不完整。

## 何时使用 / 不适用

- **适用**：给定稿件 + 文献库（BibTeX/RIS/JSON）+ 目标格式规范，需要做引用定位、编号重排、去重、格式转换、来源核验与一致性检查。
- **不适用**：无文献库或稿件时（应返回 `unable` 并说明缺口）；需要联网核验 DOI 但环境无网络时，只做本地格式校验并把"未联网核验"写入 uncertainty，不宣称已核验真实性。

## 输入

平台固定案例提供：`/input/case.json`（`case_id`、`task`、`output_contract`）、稿件文本、文献库文件、目标格式规范。可能给出事实底稿/受众/文体约束。

## 输出

`/app/output/result.json`：

```jsonc
{
  "case_id": "...", "status": "success | partial | unable | refused",
  "result": {
    "manuscript_path": "...", "library_path": "...",
    "citations": [{
      "cite_id": "c1", "claim": "需来源支撑的论断句原文",
      "claim_location": "sec2.p3.s2", "ref_key": "smith2020", "position_ok": true,
      "match": {"topic_terms": ["..."], "match_basis": "逐句说明为何该文献支撑此论断",
                "strength": "direct | indirect"}
    }],
    "deduplication": {
      "merged": [{"a": "k1", "b": "k2", "basis": "DOI 一致/预印本与正式版"}],
      "kept_separate": [{"a": "k1", "b": "k3", "reason": "同名作者不同文献"}],
      "pending": [{"pair": [...], "reason": "字段不足需人工确认"}]
    },
    "numbering": {"body_numbers": [1,2,3], "list_numbers": [1,2,3],
                  "continuous": true, "dangling": [], "uncited": []},
    "format_conversion": {"from": "BibTeX", "to": "GB/T 7714-2015",
                          "field_mapping": {...},
                          "preserved_fields": ["doi","volume","issue","pages"]}
  },
  "sources": [{"source_id":"s1","path":"refs.bib","note":"文献库快照"}],
  "uncertainty": [...], "changes": ["..."]
}
```

可编辑稿件放 `/app/output/`，并保留原始稿件/文献库快照与逐条改动记录。

## 工作流（严格顺序）

0. **先落交付清单骨架（防空壳）**：`scripts/draft_skeleton.py --case /input/case.json --out /app/output/deliverables.md`。生成六类产物的标题、要求与占位槽；即使后续中断也留完整半成品。定稿前清空所有 【…】 占位。
1. **解析文献库**：`scripts/parse_library.py <refs.bib|refs.ris|refs.json>... --out entries.json`。支持三种格式，字段缺失留空不臆造，`_source_file` 标来源。
2. **去重归并建议**：`scripts/dedupe_entries.py entries.json --out dedupe.json`。产出 `merge` / `uncertain` / `do_not_merge` 三类建议，每条带可解释判据。人工确认后写入 `result.deduplication`。
3. **编号与一致性检查**：`scripts/check_numbering.py manuscript.md --out numbering.json [--style numeric|superscript|author-year|auto] [--bib-count N]`。检查连续性、悬空引用、未引用条目、样式混用。把结果写入 `result.numbering`。
4. **引用定位与匹配**：逐句识别需支撑的论断，选正确引用位置，绑定文献条目并写 match_basis。`verify_citations.py` 会检查 claim 是否在稿件原文、位置是否落在图表注附近、主题是否匹配。
5. **核验（核心）**：`scripts/verify_citations.py result.json --library entries.json --manuscript manuscript.md [--dedupe dedupe.json] [--numbering numbering.json] --out verify.json [--strict]`。四性质有 error 必须修复；warning 要么修复要么写入 uncertainty。
6. **契约 + 实质性校验**：`scripts/validate_result.py result.json --case case.json`。标 success 必须：citations 非空且每条有 claim+ref_key、sources 非空、无占位符、编号连续无悬空；否则降 partial 并写入 uncertainty，**不要靠改 status 绕过**。

## 四个关注点如何被脚本保证

| 关注点 | 脚本保证 |
|---|---|
| 挂得对 | `verify_citations.py` 要求每条引用有 claim 原文 + 精确到句的 claim_location；位置落在图表注/段尾凑数、claim 不在稿件原文、自报 position_ok=false 均判错 |
| 编得顺 | `check_numbering.py` / verify 检查正文编号连续、无悬空引用、文末条目全被引用、样式不混用 |
| 收得净 | `dedupe_entries.py` 给可解释判据（DOI/题名/作者/年份），同名作者不同题名明确判 do_not_merge；合并缺判据、把 do_not_merge 对强行合并均判错 |
| 对得上 | 引用条目必须存在、元数据齐全（DOI 格式校验）；论断关键词与文献 title/abstract 须有交集或给出 match_basis，否则判错引 |

## 六类动作覆盖

1. 引用插入与定位（挂得对）
2. 编号更新与交叉引用（编得顺）
3. 文献去重与条目归并（收得净）
4. 格式转换与字段补齐（`assets/format_mapping.json`，保留 DOI/卷期页等）
5. 来源核验与一致性检查（对得上）
6. 正文—文末双向同步（check_numbering 的悬空/未引用双向检查）

## 异常处理

- 文献库字段缺失：解析留空；`verify_citations` 报告缺字段，DOI 缺失但无 URL 判 error，其余告警。
- DOI 解析失败/无网络：只做本地格式校验，写 "未联网核验真实性" 到 uncertainty，不宣称已核验。
- 条目歧义/去重不确定：写 `deduplication.pending` + uncertainty，交人工确认，不自动合并。
- 编号冲突/稿件格式不支持：`check_numbering` 报告 R2-R6，明确失败项与人工接管点。
- 重复运行：脚本无副作用（只读输入、写独立输出），编号按稿件实际标记重算。

## 资源

- `assets/format_mapping.json`：BibTeX/RIS → 标准字段映射 + GB/T 7714 类型标识 + 关键保留字段。
- `scripts/`：6 个标准库脚本（draft_skeleton / parse_library / dedupe_entries / check_numbering / verify_citations / validate_result）。
- `references/`：工作流、去重判据、编号规则、格式规范、边界案例。
- `examples/minimal-example.md`：完整最小调用示例（示意输出已标注）。

依赖：Python 3 标准库。无需第三方包。每个脚本用 `--help` 查看参数。
