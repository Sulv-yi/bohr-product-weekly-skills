# 阅读14｜Nanopublication — Skill 交付

对应挑战：`product-arena-09-0e8befd4`（阅读14｜Nanopublication）。本题有 GitHub 公开链接 **5 分**附加分。

## 一句话

把论文段落拆成原子断言，为每条绑定最小充分证据与原文位置，补全溯源链，导出可被下游直接解析的 JSON-LD——拆得细、对得上、追得回、读得懂。

## 文件清单

```
SKILL.md                         主文件：用途/工作流/输入输出/异常处理
README.md                        本说明
GITHUB_URL.txt                   公开作品链接
scripts/
  split_claims.py                段落预切候选断言骨架（拆得细）
  verify_nanopub.py              四性质 + 证据/关系/溯源硬损伤核验（核心）
  export_jsonld.py               JSON-LD 三图导出与可解析性校验（读得懂）
  validate_result.py             输出契约与状态自检
  probe_pdf.py                   PDF 探查（多级降级，复用）
assets/
  relation_vocab.json            关系受控词表（canonical + 别名 + 方向 + 质量标记）
references/
  claim-schema.md                字段字典与粒度判据
  evidence-and-quality.md        证据绑定与质量检查
  edge-cases.md                  异常与边界处理
examples/
  claim-samples-20.md            20 条断言字段样例（非真实案例答案）
  minimal-example.md             最小调用示例（示意，非真实结果）
```

## 设计动机（对应题面四问）

- **拆得细** → `split_claims.py` 预切候选 + 复合句提示；每条 nanopub 单 subject/relation/object。
- **对得上** → 证据片段逐字回原文规范化匹配，标 direct/indirect，位置精确到段/图表/字段。
- **追得回** → provenance.source 逐项记录论文/作者/年/版本/标识符，缺失写 unknown。
- **读得懂** → `export_jsonld.py` 产出标准 JSON-LD 三图（assertion/provenance/pubinfo）并校验可解析。

关系走 `assets/relation_vocab.json` 受控词表，避免同义表述各自为政、相关≠因果。

## 运行

Python 3.9+ 标准库；PDF 可选 PyMuPDF/pdfplumber/pdftotext。详见 SKILL.md 与 examples/minimal-example.md。

## 资源限制合规

14 个文本文件（≤50），均 UTF-8，总量远小于 2MB，单文件远小于 500KB，无符号链接，无凭证残留，无预制答案。20 条断言样例标注为字段示例而非正式案例答案。
