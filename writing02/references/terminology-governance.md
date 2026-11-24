# 术语治理与全篇一致性

## 术语表格式

输入术语表为 JSON，支持两种形式：

```json
{
  "term_map": {
    "machine learning": "machine learning",
    "机器学习": "machine learning",
    "ML": "machine learning",
    "deep neural network": "deep neural network",
    "DNN": "deep neural network"
  },
  "abbreviations": {
    "DNN": "deep neural network",
    "SOTA": "state of the art"
  },
  "forbidden": ["state-of-the-art 方法（宣传化）", "明显优于（无数据支持）"]
}
```

- `term_map`：任意原写法 → 唯一标准写法。键区分大小写但回扫时大小写不敏感。
- `abbreviations`：缩写 → 全称，用于检查首次出现是否定义。
- `forbidden`：禁止使用的写法，命中即报冲突。

## 治理规则

1. **标准写法唯一**：同一概念全篇只用 term_map 的值。原文出现键中任一写法，改为值。
2. **缩写首次出现定义**：正文中缩写首次出现处必须同时给出全称，形如 `deep neural network (DNN)`。已有定义处不再重复。
3. **不在表内不擅改**：术语表未覆盖的候选同义词只列入 `needs_confirmation`，保留原写法，不自行选边。
4. **跨章节回扫**：术语统一是全文操作，不能只改当前段落。改完必须跑 `term_consistency.py` 扫全文。
5. **术语表内部冲突**：若两个原写法映射到不同标准写法，或 forbidden 与 term_map 冲突，不擅自选边，列入 uncertainty，按 case 原文保留。
6. **大小写与连字符**：作为术语的一部分，按 term_map 值逐字统一；表外术语的大小写差异不视为错误。
7. **中英对齐**：中译英场景，中文术语按 term_map 映射到英文标准写法；无映射的列入 needs_confirmation，并给出建议译法但不强制采用。

## 输出中的记录

每一项术语决策写入 `result.term_decisions`：

```json
{"from": "机器学习", "to": "machine learning", "basis": "term_map"}
{"from": "AI模型", "to": "", "basis": "needs_confirmation", "suggestion": "AI model"}
```

`basis` 只能是 `term_map` 或 `needs_confirmation`。
