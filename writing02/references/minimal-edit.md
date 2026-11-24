# 最小编辑与逐句对照规范

## 最小编辑原则

1. **句子级为单位**：一次只处理一句，改完立即记录，不累积到整段再改。
2. **能改词不改句**：能用冠词、介词、时态、单复数解决的，不重构句子。
3. **能改局部不改整体**：长句切分只在确有语法错误或理解障碍时进行。
4. **不替换专业术语**：术语按 term_map 统一，不做同义替换。
5. **不"顺手"改进内容**：即使发现表达可以更精确，若涉及主张变化则列入 uncertainty，不擅改。

## change_log 记录格式

每一处修改一条记录，四要素缺一不可：

```json
{
  "original": "The results suggest that the method may works better.",
  "revised": "The results suggest that the method may work better.",
  "change_type": "grammar",
  "reason": "主谓一致：情态动词 may 后接动词原形",
  "preserved": ["suggest（L1 限定强度）", "may（L1）", "better（比较级）"]
}
```

`change_type` 取值（多选时用数组）：
- `grammar` 语法/句法
- `agreement` 主谓一致、单复数
- `article_prep` 冠词与介词
- `tense_voice` 时态语态
- `punctuation` 标点
- `terminology` 术语统一
- `register` 语域/语气
- `conciseness` 冗余精简
- `chinese_english` 中译英表达
- `split` 长句切分

`reason` 必须指出具体问题，不能写"使表达更流畅"这类空泛理由。

**未修改的句子也要出现在对照中**，标 `"change_type": []`、`"reason": "无需修改"`——这样第三方能确认全文都被处理过，而非只挑了几句。

## 禁止的做法

- 只交付润色后全文，不给对照
- 把多句合并成一条笼统的"已优化表达"
- reason 用"提升可读性""更加学术"等无法核实的说法
- 在 revised 中悄悄改数字、单位、引用编号或限定词
- 用"整段重写"掩盖单句的语义漂移
