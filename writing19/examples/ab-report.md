# 对照实验记录：兜底草稿 vs 按 SKILL 改写

- 日期：2026-11-25
- 材料：Merillas 等 2026，*Mater. Today Sustain.* 34:101352（12 页 / 759 句 / 57,785 字）
- 环境：Windows / Python 3.13 / 仅标准库
- 两次运行的工具、块编号、校验门槛完全相同，**差异只来自语义环节**

## 1. 运行命令

```bash
# A1 · 兜底草稿（脚本自动建图，无人工语义）
python3 scripts/mm_run.py --material paper.md --work work --out out_draft --case-id m26

# A2 · 按 SKILL 改写（人读 blocks.md 后重写 nodes.json，脚本只做校验与导出）
python3 scripts/mm_check.py  --blocks work/blocks.json \
    --nodes examples/handcrafted-nodes.json --out work/check_hand
python3 scripts/mm_export.py --nodes examples/handcrafted-nodes.json \
    --blocks work/blocks.json --out out_hand/mindmap
```

## 2. 指标

| 指标 | A1 兜底 | A2 改写 | 说明 |
|---|---|---|---|
| 节点数（不含根） | 32 | 20 | A1 把过渡句也做成了节点 |
| 关系数 | 20 | 6 | A1 的多数是"同分支相邻句"的自动连线 |
| 关系类型数 | 4 | 5 | A2 多出 `conflict`（对照臂与结论的张力） |
| 证据覆盖 | 100% | 100% | 两者每节点都挂原文块 |
| 以连接词开头的节点 | **11** | **0** | `Despite` / `This` / `as` / `It must be` 开头 |
| 碎片节点（<10 字） | 6 | 3 | A2 只剩"研究问题（1 条）"这类分类节点 |
| 标题长度 CV | 0.44 | 0.23 | 同级粒度更齐 |
| 自查通过项 | 10/10 | 10/10 | 结构约束对两者都生效 |

A1 的 11 个读不通的节点（原文照录）：

```
Despite these advancements
This way optimized microcellular s…
despite containing several non-mis…
which is subsequently confirmed in…
This indicates that we are working…
this peak is absent in the second …
as previously said
as it will be discussed in the fol…
it is important to highlight that …
This temperature must be reached s…
It must be considered that
```

这些节点的共同点：**它们是句子的状语或衔接部分，不是判断**。
读者点开一个"as previously said"的节点，得不到任何信息。

## 3. 校验器在人工产物上抓到的真实错误

A2 第一次提交时，C7（数字可核）报出：

```
n10 标题里的 0.2 在所挂原文里找不到
```

节点写的是「薄膜相对密度最低达 0.20」，挂 `P10-S48`，而该块原文是：

> The greatest density reduction in the recycled materials was achieved for PET_C
> foamed at 220 °C, achieving relative densities of **0.18** at 15 MPa saturation
> pressure and **0.17** for the ones saturated at 30 MPa.

0.20 来自另一块（`P10-S49`：其它材料最低约 0.2），被记忆合并到了 PET_C 上。
改法是拆开：PET_C 写 0.17（30 MPa），note 里补 0.18（15 MPa）。

**这是这个 Skill 最直接的证据**：错误不是"看起来不对"被发现的，
是"数字对不上原文"被脚本拦下的。人眼读图不会去逐个核对小数点。

## 4. 另外两个被结构性拦下的问题

| 问题 | 拦截项 | 处置 |
|---|---|---|
| 表格行被当标题（`This \| PET_B 5.94 3.17 ⋅ 10−13 \| 7.37…`） | scaffold `table=true` | 表格只作证据，不做节点名 |
| 标题在 34 字处截断，`7.37` 只剩 `7`，C7 误报 | C7 截断容忍 | 允许"截断后的数字是原文数字的前缀" |

## 5. 这个对照不能说明什么

- 不能说明"加载 Skill 比不加载提升多少"。A1 与 A2 都用了同一套脚本，
  真正的 A0（同一模型、无 Skill、单次提问）没有独立运行。
- 不能说明语义环节的提升可由脚本自动获得。A2 的 20 个节点是人读后写的，
  脚本只提供块编号和检查，不给措辞。
- 样本只有一篇论文。换材料（中文综述、实验方案、项目计划）时，
  A1 的碎片率和 A2 的改写成本都会变，没有测。
