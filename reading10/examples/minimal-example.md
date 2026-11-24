# 最小调用示例（示意，非真实案例结果）

> 本页所有内容均为接口示意，不代表任何正式测试案例的答案或评分。

## 输入（假设 /input/case.json）

```json
{
  "case_id": "demo-001",
  "task": "按论文章节做结构化笔记，输出论文卡片、章节笔记与可检索知识点，关键结论回到原文。",
  "material": "/input/paper.pdf",
  "output_contract": ["paper_card", "section_notes", "knowledge_points"]
}
```

## 调用链

```bash
# 1. 探查
python scripts/probe_pdf.py /input/paper.pdf > /app/work/probe.json

# 2. 带块提取（PDF 有文字层时；复用 reading01 的 extract_blocks.py 或等价工具）
python scripts/extract_blocks.py /input/paper.pdf --out /app/work/blocks.json

# 3. 还原章节骨架
python scripts/build_outline.py /app/work/blocks.json --out /app/work/outline.json

# 4. 生成卡片骨架
python scripts/build_card_skeleton.py --outline /app/work/outline.json \
    --case /input/case.json --out /app/work/skeleton.json

# 5. 逐节填笔记 + 登记 sources + 填卡片 + 拆知识点 → /app/output/result.json

# 6. 双重自检
python scripts/validate_result.py /app/output/result.json --case /input/case.json
python scripts/verify_notes.py /app/output/result.json --outline /app/work/outline.json \
    --material /app/work/blocks.json --case /input/case.json --strict-align --out /app/work/verify.json
```

## 示意输出（节选，字段为示例值）

```json
{
  "case_id": "demo-001",
  "status": "success",
  "result": {
    "paper_card": {
      "title": "（示例）A Study of X",
      "research_question": [{"text": "X 在条件 C 下是否优于基线？", "source_ids": ["s1"]}],
      "data": [{"text": "示例数据集 D，规模 N（示意）", "source_ids": ["s2"]}],
      "method": [{"text": "示例方法 M（示意）", "source_ids": ["s2"]}],
      "findings": [{"text": "示例：提升 5%（示意）", "conditions": "仅在条件 C、样本 D 上成立（示意）", "source_ids": ["s3"]}],
      "limitations": [{"text": "示例：未覆盖场景 E（示意）", "source_ids": ["s4"]}],
      "premises": [{"text": "结论依赖条件 C（示意）", "source_ids": ["s3"]}]
    },
    "section_notes": [
      {"section_id": "S2", "order": 1, "title": "Introduction", "summary": "（示例摘要）", "source_ids": ["s1"]}
    ],
    "knowledge_points": [
      {"id": "k1", "term": "X", "aliases": ["概念 X（示意）"], "definition": "（示例定义）", "source_ids": ["s1"]}
    ]
  },
  "sources": [
    {"source_id": "s1", "location": "p.1 ¶2", "quote": "原文逐字片段（示意）"}
  ],
  "uncertainty": [],
  "changes": ["skeleton generated from outline"]
}
```

## 破坏性对照（verify 应报错）

把某条 note 的 `section_id` 改成 skeleton 外的 `S9` → `alignment` failed；
把某 source 的 `quote` 改成原文没有的句子 → `traceable` failed；
删掉 findings 的 `conditions` → retention 告警；
把两条知识点 term 改成同一个 → `reusable` failed。
