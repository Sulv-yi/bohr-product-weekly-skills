# 实体对齐与冲突（对得齐）

## 可合并（merge，需 identity_basis）

- 同一篇内：缩写 ↔ 全称（"Method M" / "M"），大小写变体，单复数。
- 作者明示："we refer to X as Y hereafter"。
- 同一 DOI / 同一版本的同篇多格式文件（primary-material.json 与其 Markdown）——这是同篇，不算跨篇。

## 不得合并（写入 conflicts）

- **跨篇同形通用术语**：两篇都出现 "CNN"、"accuracy"、"dataset D"，但物理样品/模型实例/数据集/条件不同。
- **同名但样本/条件不同**：一篇在数据集 D 上 92.5%，另一篇在数据集 D 上 78%，不合成一个结论节点。
- **根元数据复用**：把第一篇的 DOI/作者套到第二篇。

## 判定原则

"相同通用方法/材料术语 ≠ 相同对象实例"。默认策略：**跨篇倾向保留独立节点**，除非有显式身份依据（同一 DOI、作者明示同一实体、可回查的共同标识符）。
宁可多保留节点 + 记录冲突，也不要错误合并造成虚假跨篇结论。

## 记录格式

```json
{"from": "n005", "to": "n001", "action": "merge",
 "identity_basis": "primary 段 p3: 'Method M (hereafter M)'，同 source_id=primary"}
{"nodes": ["n002", "n006"], "reason": "同名 dataset D，primary 样本 5000、secondary 样本 2000，条件不同，不合并"}
```
