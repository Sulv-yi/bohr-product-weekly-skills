# 20 条科研断言样例（字段规范示例，非任何正式案例结果）

> 这些样例用于展示断言粒度、主体-关系-对象、证据绑定与来源字段的标准形态，均为**通用示例文本**，不是正式测试案例的答案。字段定义见 references/claim-schema.md。

每条格式：`id | subject | relation | object | conditions | evidence(location) | confidence`

## 方法与数据类
1. `c01 | Method M | achieves | 92.5% accuracy | on dataset D | "Method M reaches 92.5% accuracy"(p.3 ¶2) | high`
2. `c02 | Method M | outperforms | baseline by 5% | on dataset D, same split | "outperforming the baseline by 5%"(p.3 ¶2) | high`
3. `c03 | Dataset D | is_a | 5000-sample benchmark | (none) | "dataset D with 5000 samples"(p.2 ¶2) | high`
4. `c04 | Method M | requires | 30 training epochs | for convergence | "trains for 30 epochs"(p.2 ¶2) | high`
5. `c05 | The split | is_a | 80/20 train/test | (none) | "a 80/20 split [3]"(p.2 ¶2) | high`

## 结果与发现类
6. `c06 | Condition C | increases | stability of M | relative to baseline | "performance under condition C..."(p.1 ¶3) | medium`
7. `c07 | Method M | correlates_with | input scale | observed, not causal | "correlated with input scale"(p.4 ¶1) | medium`
8. `c08 | Ablation of module A | decreases | accuracy by 3% | when removed | "removing A drops 3%"(p.5 ¶1) | high`
9. `c09 | Method M | achieves | 1.2s inference time | on GPU, batch 1 | "1.2s per image"(p.5 ¶3) | high`
10. `c10 | The result | reports | statistical significance | p < 0.05 | "p < 0.05"(p.5 ¶4) | high`

## 条件与限定类
11. `c11 | The finding | requires | condition C | generalization not evaluated | "holds only under condition C"(p.6 ¶1) | high`
12. `c12 | Method M | limits | unseen-domain generalization | not evaluated | "generalization ... not evaluated"(p.6 ¶1) | high`
13. `c13 | The 5% gain | is_a | relative improvement | not absolute | "outperforming baseline by 5%"(p.3 ¶2) | medium`

## 来源与背景类
14. `c14 | Prior work [3] | reports | baseline accuracy | on dataset D | "as in [3]"(p.2 ¶2) | medium`
15. `c15 | Smith (2020) | reports | open question on C | background | "remains an open question (Smith, 2020)"(p.1 ¶3) | high`
16. `c16 | This work | contradicts | earlier assumption | under condition C | "contrary to prior assumption"(p.6 ¶2) | medium`

## 证据边界类
17. `c17 | Fig. 2 | shows | accuracy trend | visual only | "as shown in Fig. 2"(p.3 ¶2) | low（图表数值未文本化）`
18. `c18 | Table 1 | reports | per-class scores | 10 classes | "see Table 1"(p.3 ¶2) | low（表格为图片）`
19. `c19 | The authors | report | limitation on domain shift | self-stated | "we did not evaluate..."(p.6 ¶1) | high`
20. `c20 | The claim on generalization | requires | further experiments | not done in this work | "future work will..."(p.7 ¶1) | high`

## 粒度对照（什么不该是一条断言）
- 反例：「方法 M 达到 92.5% 准确率，优于基线 5%，并在 GPU 上 1.2s 完成推理」——三条可独立判断的断言被塞进一个字段，应拆为 c01/c02/c09。
- 正例：每条断言只有一个 subject-relation-object 核心、一个可验证条件、一段最小充分证据。
