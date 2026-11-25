# 验收清单

第三方拿到这个包后，按顺序勾选即可判断"能不能用"。每项都指明要看的文件或命令。

## A. 能不能跑起来（10 分钟）

- [ ] `python3 scripts/mm_scaffold.py --in <任意 md> --out work --title "T"` 生成三件套
- [ ] `work/blocks.json` 里每个块有 `id/page/text/chars/noise/heading/hints`
- [ ] `python3 scripts/mm_run.py --material <md> --work work2 --out out --case-id demo` 跑通
- [ ] `out/` 下有 `mindmap.mm/.opml/.md/.svg` 与 `result.json`
- [ ] 用 XMind 或 FreeMind 打开 `mindmap.mm`，节点层数与 `mindmap.md` 一致
- [ ] 浏览器打开 `mindmap.svg`，一级分支分栏、节点右下角有 `P页-S句`
- [ ] 只依赖 Python 3.8+，未安装任何第三方包

## B. 检查是否真的在检查（关键）

- [ ] 删掉某个节点的 `evidence` 后跑 `mm_check.py`，C6 报 FAIL
- [ ] 把某节点标题的数字改成原文没有的数，C7 报 FAIL
- [ ] 把两个节点挂到不存在的父节点，C2 报 FAIL
- [ ] 把深度加到 5 层，C8 报 FAIL
- [ ] 把关系减到 2 条，C9 报 FAIL
- [ ] 把某节点 `level` 改成 `inference` 但不登记 uncertainty，C10 报 FAIL
- [ ] 以上任一 FAIL 时，`mm_check.py` 退出码为 1

## C. 证据是否可回溯

- [ ] 从 `mindmap.md` 任取 3 个节点，按 `P页-S句` 在 `blocks.json` 找到原文
- [ ] 这 3 个节点标题里的数字，与原文数字一致（含小数位）
- [ ] `result.json` 的 `uncertainty` 里每条都有 `why` 与 `needs`
- [ ] 材料缺页码时，`pages_missing=true`，`result.json` 的 `status=partial`

## D. 两个版本的可比性

- [ ] `examples/handcrafted-nodes.json` 用同一份 blocks 跑 `mm_check.py` 得 10/10
- [ ] `examples/ab-report.md` 的指标可用 `eval/score_output.py` 复算
- [ ] 复算结果与表里的「节点数/关系数/证据覆盖/结构分」一致

## E. 边界（不通过也算合格，但必须如实说明）

- [ ] 只给 PDF：返回 `status=blocked`，不编造内容
- [ ] 材料 300 字以内：`SKILL.md` 已写"不适用，直接给摘要"
- [ ] 表格很多：`table=true` 的块不做节点名
- [ ] 材料自相矛盾：两条都进图，关系标 `conflict`，并进 uncertainty

## F. 明确不承诺的

- 语义正确的标题（脚本只保证结构与可核对，措辞靠 Agent 或人）
- 影像/光谱图的内容还原（只做文本材料）
- 超过 60 个节点时的排版美观（应拆图）
