# 带证据的文献知识图谱

赛题：`product-arena-10-760d1a0b`（北化分站赛 · 文献知识图谱构建）

## 是什么

一个可被 Agent 调用的 Skill：把科研 PDF 解析成带页码与段落 id 的结构化文档模型，
再按本题要求加工成翻译 / 笔记 / 断言 / 图谱，所有结论都能回到原文位置。

## 怎么用

```bash
python scripts/doctext.py /input/material.pdf --out work/doc.json

# 一批论文：跨篇成图 + 自检（推荐路径）
python scripts/graph_build.py build --docs work/*.doc.json \
    --out /app/output/graph.json --audit /app/output/graph-audit.json
python scripts/graph_build.py query --graph /app/output/graph.json --q "<查询词>"

# 单篇 + 领域词表命中时
python scripts/readwork.py graph work/doc.json --out work/graph.json
python scripts/readwork.py graphexport work/graph.json --out work/graph.cypher
python scripts/readwork.py verify /app/output/result.json --doc work/doc.json
```

## 目录

- `SKILL.md` — 完整说明（适用边界、契约、工作流、评分维度落点、异常处理）
- `scripts/doctext.py` — 文档模型引擎（纯标准库可跑）
- `scripts/readwork.py` — 单篇任务加工与自检工具（词表驱动，精度高但换学科会抽空）
- `scripts/graph_build.py` — 跨篇图谱构建与自检：通用线索抽实体、动词定方向、按标签归一合并、
  证据逐条回查；`build / audit / query` 三个子命令，纯标准库
- `references/` — 方法细则（阅读顺序、表格重建、结构识别）
- `examples/runs/RUNS.md` — 真实 PDF 上的实测记录

## 依赖

Python 3.9+；可选 `pypdf`（推荐）或 `pdftotext`，两者都没有时走内置解析器。

## 限制

双栏并排表格、扫描件文字层缺失、跨页续表需要人工确认；这些情况在结果里如实标注，
不编造数据。详见 `SKILL.md` 第五节。
