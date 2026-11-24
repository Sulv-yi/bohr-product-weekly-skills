# 最小调用示例（示意，非真实案例结果）

以下为演示接口用的**示例数据**，不是平台固定案例的答案。

## 输入（示意）

`material.json`（两篇段落索引）：
```json
{"paragraphs": [
  {"paragraph_id":"p2","source_id":"primary","text":"Method M trains for 30 epochs on dataset D."},
  {"paragraph_id":"p3","source_id":"primary","text":"Method M reaches 92.5% accuracy, outperforming the baseline by 5%."},
  {"paragraph_id":"p2","source_id":"secondary","text":"We apply method M on dataset D with 2000 samples, reaching 78% accuracy."}
]}
```

`corpus-manifest.json`（示意，root 只属第一篇）：
```json
{"root":{"doi":"10.1/first","title":"First Paper","authors":["Smith"]},
 "papers":[
  {"source_id":"primary","doi":"10.1/first","title":"First Paper","authors":["Smith"],"license":"CC-BY"},
  {"source_id":"secondary","doi":"10.2/second","title":"Second Paper","authors":["Li"],"license":"CC-BY"}]}
```

## 调用

```bash
python3 scripts/build_skeleton.py --manifest corpus-manifest.json --material material.json \
  --case case.json --out skeleton.json
python3 scripts/extract_entities.py --material material.json --out candidates.json
# Agent 判定后填 result.json（节点/边/对齐/冲突/≥3查询）
python3 scripts/query_graph.py result.json --out query_results.json
python3 scripts/verify_graph.py result.json --material material.json \
  --manifest corpus-manifest.json --vocab assets/relation_vocab.json --case case.json --out verify.json
python3 scripts/export_graph.py result.json --out-dir graph_export
python3 scripts/validate_result.py result.json --case case.json
```

## 示意输出要点

- `Method M` 在两篇都出现，但 primary 用 5000 样本得 92.5%、secondary 用 2000 样本得 78% → **保留两个独立节点**，写 conflict，不合并、不合数值。
- `M` 是 primary 段 p3 的缩写 → 与 primary 的 `Method M` 做 merge，identity_basis 记录同篇缩写关系。
- 查询"跨篇同形术语"应返回 `Method M` 的两个节点并标注 conflict，而非一条虚假 same_as 边。
