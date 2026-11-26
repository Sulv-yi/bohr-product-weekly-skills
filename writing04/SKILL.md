---
name: reference-citation-manager
description: 参考文献与引用管理 Skill。从真实稿件与文献库出发，完成引用插入定位、编号同步更新、文献去重归并、格式转换与字段保留、来源核验与正文—文末一致性检查，并交付可继续编辑的稿件与可逐条回溯的引用记录。核心保证：挂得对、编得顺、收得净、对得上。适用于学术写作中需要保证引用真实、编号连续、去重可解释、论断与文献匹配的场景。
---

# 参考文献与引用管理 Skill

围绕真实、高频的引用管理任务，形成可运行、可核验、可改进的最小闭环。聚焦四个问题：**挂得对 / 编得顺 / 收得净 / 对得上**。用同一份稿件与同一个文献库做前后对照时可给出可核验的改进证据。

**核心原则：交付的是可核对的产物本体，不是脚本运行结果本身。** 先落交付清单骨架（保证六类产物齐全），再填真实内容，最后才跑核验；标 success 必须有可编辑稿件、逐条 citations 与可回溯 sources，缺一即为不完整。


## 覆盖预算（动笔前先按这个量做，不要抽查几条就收工）

引用管理的交付物是**整篇稿件的引用账**，不是抽样。只核 4 条引用等于没做本题。

| 项 | 下限 | 说明 |
|---|---|---|
| 引用条数 | ≥15 条，且**稿件内每一处引文都要有对应记录** | 稿件只有 8 处引文时做 8 条，并在 `uncertainty` 写明"稿件引文总数为 8" |
| 位置精度 | 100% 到句 | 写成 `sec2.p3.s2` / `§2.3 第 2 段第 2 句`，不接受"第 2 节" |
| 匹配依据 | 100% 逐条写 | 说明该文献的哪一部分支撑这句话（数据、方法、结论），不接受"相关" |
| 去重判断 | 三分齐全 | merged / kept_separate / pending 各自带判据；pending 要写为何不能自动合并 |
| 字段映射 | ≥5 项 | 作者/年份/题名/期刊/卷期页/DOI 至少五项，逐项写目标格式的落点 |
| 保留字段 | ≥1 项 | DOI、卷期页等易在转换中丢失的字段，必须显式保留 |

## 交付门槛（定稿前逐条对照，达不到不要标 success）

| 项 | 门槛 | 谁检查 |
|---|---|---|
| 稿件本体 | 必须交付可编辑稿件（`manuscript_text` 或 `manuscript_path`），不能只交记录 | `validate_result.py` |
| 引用覆盖 | ≥15 条引用记录，且覆盖稿件内全部引文 | `validate_result.py` |
| 论断原文 | 每条引用都有 `claim`，且是稿件里能找到的原句 | `validate_result.py` |
| 位置精确 | `claim_location` 到句（`sec2.p3.s2` 这类），不是"第 2 节" | `validate_result.py` |
| 匹配依据 | 每条 `match.match_basis` 说明"为何这篇文献支撑这句话" | `validate_result.py` |
| 编号 | `continuous=true` 且 `dangling` 为空；`uncited` 如实列出 | `validate_result.py` |
| 去重 | `merged/kept_separate/pending` 三分判断，各自带判据；歧义进 pending | `validate_result.py` 告警 + 人工 |
| 格式 | `field_mapping` ≥5 项，`preserved_fields` ≥1 项（DOI/卷期页等） | `validate_result.py` |
| 干净度 | 无 `【…】`/`TODO`/`待填` 残留 | `validate_result.py` |
| 文献键 | 每个 `ref_key` 能在 `sources` 快照里找到 | `validate_result.py` |

门槛未过的处置：**回第 4/5 步补齐**，不要改 status 绕过；确实补不出的留 `partial` 并在 `uncertainty` 写明缺什么。

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
6. **落可核验附件**：`scripts/build_outputs.py --result /app/output/result.json --outdir /app/output [--manuscript 稿件路径]`。产出 `citation-map.csv`（cite_id → 论断 → 位置 → 文献键 → 匹配依据）、`selfcheck.md`（四性质指标 + 未清项）、`preview.pdf`（环境有 pandoc 时）。这一步把"每条引用能否回到来源"变成可逐行打勾的表。
7. **契约 + 结构门槛**：`scripts/validate_result.py result.json --case case.json`。标 success 必须：稿件已交付、每条引用有 claim + 到句的位置 + match_basis、文献键可回溯、编号连续无悬空、字段映射非空、无占位符；否则降 partial 并写入 uncertainty，**不要靠改 status 绕过**。

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

## 评分维度落点（自查表）

| 维度 | 分值 | 本作品的落点 |
|--|--:|--|
| 实际效果·完成度 | 15 | `parse_library.py` 统一解析 BibTeX/RIS/JSON；`citation_gate.py` 把四类要求变成可计算量 |
| 实际效果·正确性 | 15 | `verify_citations.py` 核验「挂得对/编得顺/收得净/对得上」四性质 |
| 实际效果·完整性 | 5 | `check_numbering.py` 编号连续性与正文引用键覆盖；`build_outputs.py` 输出 citation-map.csv |
| 实际效果·可核验性 | 5 | 每条引用绑定正文位置与条目键，交付物可直接复核 |
| 使用增益·质量增益 | 15 | 去重不强制合并：`dedupe_entries.py` 只给判据与建议，保留人工决定 |
| 使用增益·效率增益 | 5 | 库解析、去重、编号检查一次跑完，不需要逐条目视 |
| 使用增益·可验证性 | 5 | 结构度量可复跑，指标口径写在脚本内 |
| 创新增益 | 15 | 把"引用管理"从手感变成四维度量，并给出可解释的合并判据 |
| 可靠体验 | 10 | `validate_result.py` 防空壳/占位/零引用却标 success；异常处理见下一节 |
| 生态贡献 | 10 | 支持三种文献库格式；脚本可独立复用 |

## 异常处理

- 文献库字段缺失：解析留空；`verify_citations` 报告缺字段，DOI 缺失但无 URL 判 error，其余告警。
- DOI 解析失败/无网络：只做本地格式校验，写 "未联网核验真实性" 到 uncertainty，不宣称已核验。
- 条目歧义/去重不确定：写 `deduplication.pending` + uncertainty，交人工确认，不自动合并。
- 编号冲突/稿件格式不支持：`check_numbering` 报告 R2-R6，明确失败项与人工接管点。
- 重复运行：脚本无副作用（只读输入、写独立输出），编号按稿件实际标记重算。
- 预算将尽：先存 `result.json` 的 partial 版与 `citation-map.csv`，再补；不交空壳。

## 资源

- `assets/format_mapping.json`：BibTeX/RIS → 标准字段映射 + GB/T 7714 类型标识 + 关键保留字段。
- `scripts/`：7 个标准库脚本（draft_skeleton / parse_library / dedupe_entries / check_numbering / verify_citations / citation_gate / build_outputs / validate_result）。
- `references/`：工作流、去重判据、编号规则、格式规范、边界案例、方案边界。
- `examples/`：`minimal-example.md`、`selftest-*`（示例案例/结果/稿件）、`baseline-*`（对照侧示例）。
- `eval/`：评分表、指标脚本、A/B 协议、验收表 —— 给评审与复现用，**运行一个案例时不需要读**。

`/app/output` 最终应有：`manuscript.md`、`result.json`、`citation-map.csv`、`selfcheck.md`（有 pandoc 时另有 `preview.pdf`）。

依赖：Python 3 标准库。无需第三方包。每个脚本用 `--help` 查看参数。
