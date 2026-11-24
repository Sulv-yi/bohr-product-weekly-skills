# 最小调用示例（示意，非官方案例）

> 以下内容为**示例**，仅说明输入输出形态，不代表任何正式案例的真实结果或评分。

## 场景

某案例要求：依据给定论文材料，写一段相关工作并给出来源。

## 输入（/input/case.json，示例）

```json
{
  "case_id": "demo-w08-001",
  "task": "写一段相关工作，按方法路线分组，附引用",
  "material": "/input/material/paper_a.pdf",
  "output_contract": ["related_work", "gap", "contributions"]
}
```

## Agent 执行

```bash
python <skill_dir>/scripts/citation_check.py /app/output/result.json \
  --sources /app/work/sources.json --case /input/case.json
python <skill_dir>/scripts/validate_result.py /app/output/result.json --case /input/case.json
```

## 输出（/app/output/result.json，示例）

```json
{
  "case_id": "demo-w08-001",
  "status": "success",
  "result": {
    "related_work": "示例：按是否依赖人工标注，现有方法分为两类……（示例文本，非正式结果）[1][2]",
    "gap": "示例：上述两类方法均假设……（示例文本）[2]",
    "contributions": "示例：本文提出……（示例文本，见第3节）"
  },
  "sources": [
    {
      "id": "1", "claim": "该类方法依赖人工标注",
      "file": "paper_a.pdf", "page": 3, "section": "2 Related Work",
      "quote": "Existing approaches rely on manual annotation ..."
    }
  ],
  "uncertainty": [],
  "changes": ["按方法路线分组并绑定引用；逐条核对 quote"]
}
```

要点：`result` 覆盖全部 `output_contract` 字段；每条论断有 `sources`；quote 逐字来自原文；无依据处写入 uncertainty。
