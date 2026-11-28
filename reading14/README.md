# 断言拆解与证据绑定的 Nanopublication

赛题：`product-arena-09-0e8befd4`（北化分站赛 · Nanopublication）

## 是什么

一个可被 Agent 调用的 Skill：把科研 PDF 解析成带页码与段落 id 的结构化文档模型，
再按本题要求加工成翻译 / 笔记 / 断言 / 图谱，所有结论都能回到原文位置。

## 怎么用

```bash
python scripts/doctext.py /input/material.pdf --out work/doc.json
python scripts/readwork.py claims work/doc.json --out work/claims.json --max 60
python scripts/readwork.py nanopub work/claims.json --doc work/doc.json --out work/nanopub.json
python scripts/readwork.py verify /app/output/result.json --doc work/doc.json
```

## 目录

- `SKILL.md` — 完整说明（适用边界、契约、工作流、评分维度落点、异常处理）
- `scripts/doctext.py` — 文档模型引擎（纯标准库可跑）
- `scripts/readwork.py` — 任务加工与自检工具
- `references/` — 方法细则（阅读顺序、表格重建、结构识别）
- `examples/runs/RUNS.md` — 真实 PDF 上的实测记录

## 依赖

Python 3.9+；可选 `pypdf`（推荐）或 `pdftotext`，两者都没有时走内置解析器。

## 限制

双栏并排表格、扫描件文字层缺失、跨页续表需要人工确认；这些情况在结果里如实标注，
不编造数据。详见 `SKILL.md` 第五节。
