# 最小调用示例（示意，非官方案例）

> 以下内容为**示例**，仅说明输入输出形态，不代表任何正式案例的真实结果或评分。

## 场景

某案例要求：读取一份双栏论文 PDF，回答"本文提出的方法叫什么、用在哪个数据集上"，并给出证据位置。

## 输入（/input/case.json，示例）

```json
{
  "case_id": "demo-001",
  "task": "回答：本文方法名称与所用数据集，并给出原文依据",
  "material": "/input/material/demo.pdf",
  "output_contract": ["answer", "method_name", "dataset"]
}
```

## Agent 执行

```bash
python <skill_dir>/scripts/probe_pdf.py /input/material/demo.pdf > /app/work/probe.json
python <skill_dir>/scripts/extract_blocks.py /input/material/demo.pdf --out /app/work/blocks.json
# Agent 阅读 blocks.json，按 SKILL.md 工作流定位答案与证据
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
  --blocks /app/work/blocks.json --case /input/case.json
```

## 输出（/app/output/result.json，示例）

```json
{
  "case_id": "demo-001",
  "status": "success",
  "result": {
    "answer": "示例：方法名为 X-Net，在 DemoSet 数据集上评估。（示例文本，非正式结果）",
    "method_name": "X-Net",
    "dataset": "DemoSet"
  },
  "sources": [
    {
      "page": 2,
      "block_id": "p002-b007",
      "bbox": [72.0, 210.5, 300.2, 228.9],
      "quote": "We propose X-Net and evaluate it on DemoSet."
    }
  ],
  "uncertainty": [],
  "changes": ["首次提取双栏顺序并定位方法描述块"]
}
```

要点：`result` 覆盖全部 `output_contract` 字段；每条结论有 `sources`；quote 逐字来自原文块；无不确定项时 `uncertainty` 为空数组。
