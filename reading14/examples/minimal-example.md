# 最小调用示例（示意，非真实案例结果）

> 本页为接口与流程示意，不代表任何正式测试案例的答案或评分。

## 输入（假设 /input/case.json）

```json
{
  "case_id": "demo-np-001",
  "task": "把给定论文段落拆成原子断言，绑定证据并导出 JSON-LD。",
  "material": "/input/paper.txt",
  "output_contract": ["nanopublications"]
}
```

## 调用链

```bash
# 0. PDF 输入时先探查
python scripts/probe_pdf.py /input/paper.pdf > /app/work/probe.json

# 1. 预切候选断言
python scripts/split_claims.py /input/paper.txt --out /app/work/candidates.json

# 2. 逐条核定断言 + 绑定证据 + 补溯源 → /app/output/result.json

# 3. 四性质核验
python scripts/verify_nanopub.py /app/output/result.json \
    --material /input/paper.txt --vocab assets/relation_vocab.json \
    --case /input/case.json --out /app/work/verify.json --strict

# 4. JSON-LD 导出 + 校验
python scripts/export_jsonld.py /app/output/result.json --out /app/output/nanopubs.jsonld

# 5. 契约自检
python scripts/validate_result.py /app/output/result.json --case /input/case.json
```

## 示意输出（节选，字段为示例值）

```json
{
  "case_id": "demo-np-001",
  "status": "success",
  "result": {
    "nanopublications": [
      {
        "id": "np-001",
        "assertion": {"subject":"Method M","relation":"achieves","object":"92.5% accuracy",
          "claim_text":"Method M reaches 92.5% accuracy","conditions":"on dataset D",
          "confidence":"high","confidence_basis":"原文逐字数值，直接证据"},
        "provenance": {
          "evidence": [{"text":"Method M reaches 92.5% accuracy","location":"p.3 ¶2","type":"direct"}],
          "source": {"paper":"A Study of M","authors":["Smith, J."],"year":"2020",
            "version":"v1","identifier":"DOI:10.1000/example","data_source":"dataset D"}
        },
        "publication_info": {"created_by":"Bohr-Scholar-Agent","created_at":"2026-11-24"}
      }
    ]
  },
  "sources": [{"source_id":"s1","location":"p.3 ¶2","quote":"Method M reaches 92.5% accuracy"}],
  "uncertainty": [],
  "changes": ["split compound sentence into np-001/np-002"]
}
```

## 破坏性对照（应报错）

- 证据 `text` 改成原文没有的句子 → aligned failed。
- relation 写 `boosts`（不在词表且无别名）→ machine failed。
- `source` 删掉 `authors`/`year`/`identifier` → traceable failed。
- 两条 nanopub 用同一 `id` → machine failed。
- 把"达到92.5%，优于基线5%"塞进一条 claim_text → granular warn。
