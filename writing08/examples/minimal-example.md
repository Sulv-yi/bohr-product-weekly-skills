# 最小调用示例（示意，非官方案例）

> 以下内容为**示例**，仅说明输入输出形态，不代表任何正式案例的真实结果或评分。

## 场景

某案例要求：依据给定论文材料，写一段相关工作并给出来源。

## 输入（/input/case.json，示例）

```json
{
  "case_id": "demo-w08-001",
  "task": "写一段相关工作，按方法路线分组，附引用",
  "material": "/input/material/paper_a.pdf",
  "output_contract": ["related_work", "gap", "contributions"]
}
```

## Agent 执行

```bash
# 1) 先落四要素骨架（防只交大纲）
python <skill_dir>/scripts/draft_skeleton.py --case /input/case.json --out /app/output/draft.md
# 2) 填真实内容、逐段绑定 sources，写成 result.json
# 3) 落可核验附件：来源映射表 + 自检表（有 pandoc 时含 preview.pdf）
python <skill_dir>/scripts/build_outputs.py --draft /app/output/draft.md \
    --result /app/output/result.json --outdir /app/output
# 4) 结构门槛 + 引用核验
python <skill_dir>/scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/draft.md
python <skill_dir>/scripts/citation_check.py /app/output/result.json \
    --sources /app/work/sources.json --case /input/case.json
```

`/app/output` 最终应是：`draft.md`、`result.json`、`source-map.csv`、`selfcheck.md`（+ 有环境时 `preview.pdf`）。

## 输出（/app/output/result.json，示例）

```json
{
  "case_id": "demo-w08-001",
  "status": "success",
  "result": {
    "related_work": "示例：按是否依赖人工标注，现有方法分为两类……（示例文本，非正式结果）[1][2]",
    "gap": "示例：上述两类方法均假设……（示例文本）[2]",
    "contributions": "示例：本文提出……（示例文本，见第3节）"
  },
  "sources": [
    {
      "id": "1", "claim": "该类方法依赖人工标注",
      "file": "paper_a.pdf", "page": 3, "section": "2 Related Work",
      "quote": "Existing approaches rely on manual annotation ..."
    }
  ],
  "uncertainty": [],
  "changes": ["按方法路线分组并绑定引用；逐条核对 quote"]
}
```

要点：`result` 覆盖全部 `output_contract` 字段；每条论断有 `sources`；quote 逐字来自原文；无依据处写入 uncertainty。

---

## 附：来源映射演示（用公开文献元数据，标注为示例）

> 本段仅演示“论断 → sources 条目”的映射形态，文献元数据取自本地 PDF 文件名/首页，
> **quote 字段在实际案例中必须运行时从原文逐字提取**，此处不预填逐字引文、不冒充正式答案。

示例材料（本地文献，非官方案例）：Carmenini et al., *Green Chemistry*, 2025, 27, 12830–12843,
"One-pot depolymerization–repolymerization of PET waste into sustainable photocurable liquid copolyesters for high-performance additive manufacturing"（14 页，文本层可用）。

演示映射：

```json
{
  "id": "S1",
  "claim": "已有研究把消费后 PET 废料经一锅解聚-再聚合转为可光固化的共聚酯，用于增材制造",
  "author": "Carmenini, Rosario; Sanz de León, Alberto; Benelli, Tiziana; et al.",
  "year": 2025,
  "venue": "Green Chemistry, 27, 12830-12843",
  "file": "Carmenini et al. 2025 - One-pot depolymerization-repolymerization of PET waste.pdf",
  "page": 1,
  "section": "Abstract / Introduction",
  "quote": "<运行时用 PDF 工具从该页逐字提取，例如摘要首句；此处为示例不预填>"
}
```

要点：元数据（作者/年份/卷页/题名）真实且可核；`quote` 留待运行时提取而非编造；
正文论断 `PET 废料可转为光固化共聚酯 [S1]` 与该条目一一对应。换成组织方固定案例时，
流程完全相同——只换材料与 case_id，不复用本示例的任何文字。
