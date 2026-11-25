# 最小调用示例（示意输出，非正式案例结果）

## 输入

`case.json`（最小版）：

```json
{
  "case_id": "demo-001",
  "task": "撰写一份 12 个月的硕士开题报告",
  "discipline": "生物材料",
  "cycle_months": 12,
  "capacity_pm": 14,
  "materials": "demo-materials.md",
  "output_contract": ["manuscript", "plan"]
}
```

`demo-materials.md` 要点：前期数据显示纯 PLA 支架孔隙率 78%、模量 35 MPa；
组内讨论指出"压电输出与成骨响应未在同一样品上同时测过"。

## 调用

```bash
python scripts/draft_outline.py --case case.json \
    --out work/proposal.md --plan-out work/plan.json
# → 七要素骨架 + plan 模板（cycle=12, capacity=14）

# 逐节写，同时填 plan.json；写完落台账：
python scripts/build_outputs.py --result out/result.json --text work/proposal.md --outdir out
python scripts/validate_result.py out/result.json --case case.json --text work/proposal.md
```

## 示意输出（`work/proposal.md` 片段）

```markdown
## 研究问题与可证伪假设

Q1：在纯 PLA 支架中引入 7.0 wt% BaTiO3 后，压缩模量能否提升 ≥50% 且孔隙率保持 ≥70%？
判断标准为每组 n = 12、以纯 PLA 为对照、第 9 月完成测试；任一阈值越界即判该假设不成立。

## 阶段计划

M1（第 1–4 月）：工艺定型与试样制备，工作量 5 人月，交付试样与工艺卡。
M2（第 5–8 月）：结构力学与压电测量，工作量 5 人月，交付数据集。
M3（第 9–12 月）：数据分析与论文撰写，工作量 4 人月，交付论文初稿。
```

## 示意输出（`selfcheck.md`）

```
- 字数：1520；要素：7/7
- 立得住：缺口具体（缺口线索 3 个，主题词重叠 6 个）；问题可证伪（可证伪）
- 对得上：目标-路线-指标-成果对齐 100%
- 排得开：周期覆盖 是；空月 []；重叠 0；工作量/人力 1.0
- 说得清：风险完备 100%，覆盖 4/4 类；论断挂引用 67%（6/9）
- 占位符：0
```

注意三处与本 Skill 直接相关：问题带了阈值（≥50%、≥70%）与对照（纯 PLA、n = 12）；
三个里程碑首尾相接覆盖 1–12 月且合计 14 人月 = 可用人力；风险四类齐全。
这正是"能交给导师改"与"还得重写"的分界。

> 以上 `case_id`、数据与结论均为示意，正式案例由平台运行时提供，本作品不预置答案。
