# 阅读10｜文献总结与结构化笔记 — Skill 交付

对应挑战：`product-arena-06-6d8cf72b`（阅读10｜文献总结与结构化笔记）。

## 一句话

把真实论文变成对得上自身章节、要素齐全、每条结论可回原文、可检索可复用的结构化笔记，而不是通用模板摘要。

## 文件清单

```
SKILL.md                          主文件：用途/工作流/输入输出/异常处理
README.md                         本说明
GITHUB_URL.txt                    公开作品链接
scripts/
  probe_pdf.py                    PDF 探查（多级降级，复用）
  build_outline.py                还原论文真实章节骨架（对得上）
  build_card_skeleton.py          生成稳定 ID 的卡片骨架
  verify_notes.py                 四性质 + 数字/引用/锚点硬损伤核验（核心）
  validate_result.py              输出契约与状态自检
references/
  note-schema.md                  字段字典与锚点格式
  reading-workflow.md             阅读与笔记工作流细则
  edge-cases.md                   异常与边界处理
examples/
  minimal-example.md              最小调用示例（示意，非真实结果）
```

## 设计动机（对应题面四问）

- **对得上** → `build_outline.py` 从论文真实标题建骨架，`section_notes` 必须按其 order 排列；`--strict-align` 查覆盖。
- **留得住** → `paper_card` 五要素齐全，findings 每条带 conditions，另列 premises。
- **找得回** → `sources` 逐字 quote + 精确 location，`verify_notes.py` 规范化回原文匹配。
- **用得上** → `knowledge_points` 唯一 id/term、别名单值化、带定义与锚点，可检索可比较。

可机械判定的部分（顺序/字段/锚点/数字引用/去重）由脚本核验；语义准确性需人工复核，已在 SKILL.md 与输出 uncertainty 中如实声明。

## 运行

Python 3.9+，标准库即可；PDF 解析可选 PyMuPDF/pdfplumber/pdftotext（缺失走 `probe_pdf.py` 降级链）。详见 SKILL.md 的"脚本"与 examples/minimal-example.md。

## 资源限制合规

11 个文本文件（≤50），均 UTF-8，总量远小于 2MB，单文件远小于 500KB，无符号链接，无凭证残留，无预置答案。
