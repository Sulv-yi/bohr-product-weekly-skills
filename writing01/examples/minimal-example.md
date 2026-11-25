# 最小调用示例

下面所有内容都是**示意**，材料包与文献条目为演示数据，不代表正式案例结果。

## 1. 输入

```json
{
  "case_id": "selftest-001",
  "task": "依据研究材料与文献写出一份结构完整、可进入修改环节的学术论文初稿，事实性内容可回溯到材料位置与文献条目。",
  "material": "examples/selftest-materials.md",
  "genre": "research_article",
  "language": "zh",
  "output_contract": ["manuscript", "material_index"]
}
```

## 2. 先建索引（节选）

```json
{"material_id": "m1", "kind": "测量数据", "locator": "raw/compression.csv 第 1–20 行",
 "claim": "孔隙率由 55% 升至 80% 时，压缩强度由 148 MPa 降至 56 MPa",
 "cite_key": "1",
 "quote": "孔隙率由 55% 升至 80% 时，压缩强度由 148 MPa 降至 56 MPa，降幅 62%。"}
```

索引先行有硬理由：正文里的每个数值都必须能在某条索引的 `quote` 里找到同值，
否则会被 `num_trace_rate` 列为「未能回溯」。先写正文再补索引，这一步必然失败。

## 3. 骨架 → 逐节写实

```bash
python scripts/draft_skeleton.py --case /input/case.json --out /app/output/manuscript.md
```

骨架给八类章节 + 声明位 + 图表位，每节标最低字数。占位符 `【…】` 定稿前必须清空——
空标题按字数判，不得分。

## 4. 三张核验表

```bash
python scripts/build_outputs.py --result /app/output/result.json \
    --text /app/output/manuscript.md --outdir /app/output --min-chars 1800
```

- `section-map.csv`：`section, chars, min_required, ok` —— 每节字数与是否达标；
- `material-index.csv`：`material_id, kind, locator, claim_in_manuscript, cite_key,
  evidence_quote, located_in_manuscript, ref_resolved` —— 材料到正文的对照；
- `cite-audit.csv`：`cite_key, in_body, ref_entry, section, quote, resolved` —— 引用闭合审计。

## 5. 门槛结论

```bash
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/manuscript.md
# passed  case=selftest-001  status=success
#   字数=1918 章节=88% 引用=12/12 图表对=1+1 索引=10 绑定=88% 数值可回溯=100%
```

`passed` 是脚本按 `eval/acceptance.md` 的 H1–H9 算出来的，不是自评；
任一项不过都会逐条列出，且不允许通过改 `status` 绕过。
