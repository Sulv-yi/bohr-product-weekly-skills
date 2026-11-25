# 参考文献与引用管理 Skill

从真实稿件与文献库出发，完成引用定位、编号同步、文献去重、格式转换与来源核验，交付可继续编辑的稿件与可逐条回溯的引用记录。四关注点：挂得对 / 编得顺 / 收得净 / 对得上。

## 目录

- `SKILL.md`：主说明（用途、输入输出、工作流、四性质保证、异常处理）。
- `scripts/`
  - `draft_skeleton.py`：先生成六类交付清单骨架（防空壳，先跑）。
  - `parse_library.py`：解析 BibTeX/RIS/JSON 文献库为统一条目。
  - `dedupe_entries.py`：去重归并建议（可解释判据 D1-D5）。
  - `check_numbering.py`：编号连续性/悬空/未引用/样式一致性检查。
  - `verify_citations.py`：**核心核验**（四性质 + 元数据 + 主题匹配）。
  - `validate_result.py`：结构契约 + 成稿实质性校验（空壳/占位符/零引用拦截）。
- `assets/format_mapping.json`：BibTeX/RIS → 标准字段映射 + GB/T 7714 类型标识。
- `references/`：结果 schema、去重判据、编号规则、格式核验、边界案例。
- `examples/minimal-example.md`：完整最小调用示例（示意）。

## 依赖

Python 3 标准库，无需第三方包。

## 使用顺序

draft_skeleton（先落骨架）→ parse_library → dedupe_entries → check_numbering → 逐句填 citations → verify_citations → validate_result。

## 关键规则

- 引用挂在需支撑的论断句，位置精确到句，不在图表注/段尾凑数。
- 编号连续、无悬空引用、文末条目全被引用、样式不混用。
- 合并必须有判据；同名作者不同题名不得合并；歧义交人工确认。
- 格式转换保留 DOI/卷期页等关键字段。
- DOI 无网络时只做格式校验，不宣称已联网核验真实性。

## GitHub

`https://github.com/Sulv-yi/bohr-product-weekly-skills/tree/main/writing04`
