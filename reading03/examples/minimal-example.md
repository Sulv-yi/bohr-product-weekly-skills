# 最小调用示例（示意，非官方案例结果）

以下为**示意输出**，仅展示接口和流程，不代表题面固定案例的真实译文。

## 输入 case.json
```json
{"case_id":"demo-001","output_contract":["segments","glossary"],
 "material":"两句英文科研文本"}
```

## 原文（demo 文本）
- p-001: "The proposed method may reduce latency by 30 nm scale devices [3], but no significant improvement was observed in Fig. 2."
- p-002: "However, these results suggest that SEI formation is critical."

## 步骤
```bash
# 1. 术语抽取
python3 scripts/build_glossary.py source.txt --out glossary.json
#    确认术语译名后锁定：SEI -> "SEI 膜"（note 写 "误译:固体电解质|SEI层"）

# 2. 逐段翻译，产出 result.json（含 source_id/location/rationale）

# 3. 对齐 + 守恒 + 契约校验
python3 scripts/align_paragraphs.py source_segments.json result.json
python3 scripts/verify_translation.py source_segments.json result.json --glossary glossary.json
python3 scripts/validate_result.py result.json --case case.json
```

## 示意输出 result.json（片段）
```json
{
  "case_id": "demo-001",
  "status": "success",
  "result": {
    "segments": [
      {"source_id":"p-001",
       "source_text":"The proposed method may reduce latency by 30 nm scale devices [3], but no significant improvement was observed in Fig. 2.",
       "translation":"所提出的方法可将 30 nm 尺度器件的延迟降低 [3]，但在图 2 中未观察到显著改善。",
       "location":"p.1 ¶1",
       "rationale":"may 译为'可'保留限定强度；no 译为'未'保留否定；[3]/Fig.2 原样保留；30 nm 保留单位。",
       "untranslated":[]},
      {"source_id":"p-002",
       "source_text":"However, these results suggest that SEI formation is critical.",
       "translation":"然而，这些结果表明 SEI 膜的形成至关重要。",
       "location":"p.1 ¶2",
       "rationale":"However 译'然而'保留让步；SEI 按术语表锁定译名'SEI 膜'。",
       "untranslated":[]}
    ],
    "glossary": [{"term":"SEI","translation":"SEI 膜","scope":"全文","note":"误译:固体电解质|SEI层"}]
  },
  "sources": [{"source_id":"p-001","location":"p.1 ¶1","quote":"no significant improvement"}],
  "uncertainty": [],
  "changes": ["将 attention 译名统一为'注意力'"]
}
```

## 校验预期
- 对齐：2/2 段覆盖，无漏/重/错位 → passed
- 守恒：`30 nm`、`[3]`、`Fig. 2`、否定 `no→未` 全部保留 → passed
- 术语：SEI 全篇用'SEI 膜' → passed
