# 实测记录（自有样本，非平台正式案例）

下面是本作品在**两篇真实 PDF 上实际跑出的结果**，用于说明能力边界。
平台会用自己的 3 个固定案例评测；这里的结果只代表本机实测，不作为官方得分依据。

复现命令：

```bash
python scripts/doctext.py "<your.pdf>" --out work/doc.json
python scripts/readwork.py graph work/doc.json --out work/graph.json
```

## case-2col-wiley

- 文件：`paper.pdf`（sha256 前 16 位 `8e61d273a2b04e9c`）
- 后端：`pypdf`，耗时 1608 ms
- 页数 9，段落 146，章节 6，题注 19，参考文献 39 条
- 表格：解析 0 个，未解析 6 个（原因写进 `stats.unparsed_tables`，不编造单元格）
- 页眉页脚剔除 0 行；不可读页 无；可读率 1.0
- 识别标题：One-component photoinitiator based on benzophenone and sesamol（置信度 medium）
- DOI：10.1002/pat.4337
- 章节：1 | INTRODUCTION / 2 | EXPERIMENTAL / 3 | RESULTS AND DISCUSSI / 4 | CONCLUSIONS / ACKNOWLEDGEMENTS / REFERENCES
- 本任务加工产物：`{"node_count": 30, "edge_count": 74, "edges_sample": [{"source": "material:benzophenone", "relation": "co_occurs_with", "target": "material:sesamol", "strength": "weak"}, {"source": "material:benzophenone", "relation": "co_occurs_with", "target": "material:sesamol", "strength": "weak"}, {"source": "method:mass spectrometry", "relation": "co_occurs_with", "target": "material:benzophenone", "strengt`

## case-zh-report

- 文件：`case2-zh.pdf`（sha256 前 16 位 `1ec8d773dbd4fbbc`）
- 后端：`pypdf`，耗时 1504 ms
- 页数 13，段落 97，章节 10，题注 0，参考文献 0 条
- 表格：解析 0 个，未解析 0 个（原因写进 `stats.unparsed_tables`，不编造单元格）
- 页眉页脚剔除 0 行；不可读页 无；可读率 1.0
- 识别标题：交线有解机械制图相贯线 3D 交互与三视图实验平台微信小程序应用开发赛 参赛作品介绍文档参赛作品类别:教育辅助、工具类。（置信度 low）
- 章节：一、团队介绍 / 二、小程序介绍 / 2.10 五项核心特色序号特色 说明 可验证指标 / 2.13 功能总览能力 实现程度教材题库 / 2.14 功能模块与使用场景模块 功能 对应课程 / 三、开发文档 / 4.1 所用 AI 工具名称与版本 / 3 平面立体扩展支持四棱锥、棱柱、圆台与挖空穿孔
- 本任务加工产物：`{"node_count": 0, "edge_count": 0, "edges_sample": []}`

## 已知边界（如实记录，未在本机样本上解决）

1. **双栏论文里「跨栏并排」的表格**：表格与正文处在同一视觉行，按坐标栅格切分会被正文打断，此时如实记 `unparsed_tables` 并给出原因，不返回错误的单元格。
2. **扫描件/无文字层**：不做 OCR 猜测，逐页记 `unreadable_pages`；需要文字时由上层决定是否接 OCR。
3. **占位型 PDF**（记录页写着原文文件缺失）：如实输出所述内容并标注「材料本身不含论文正文」，不虚构论文内容。
4. **参考文献切条目**：编号缺失时会退化为按作者字母起首切分，条目数与原文可能有偏差，已在 `reference_unparsed` 计数。

## 跨篇图谱构建（graph_build.py，2026-11-28 实测）

输入：`local-tests/paper.pdf`（英文 9 页，光聚合）+ `local-tests/case2-zh.pdf`（中文 13 页）。

```bash
python scripts/doctext.py paper.pdf --out d1.json
python scripts/doctext.py case2-zh.pdf --out d2.json
python scripts/graph_build.py build --docs d1.json d2.json \
    --out graph.json --audit audit.json
```

结果：节点 61、边 86、测量 43、仅提及 53；`audit.ok = true`，
节点证据回查率 1.0、边证据回查率 1.0、弱边比 0.651、关系分布
`{co_occurs_with: 56, uses: 20, increases: 4, decreases: 3, compares_with: 2, composed_of: 1}`。

样例见 `graph-sample.json`（截断到 12 节点 / 16 边）与 `graph-audit-sample.json`。
中文篇只抽出 27 个实体（英文篇 87 个）：中文缺大小写与化学式线索，靠指标词与括号内英文命中；
这是已知边界，换中文材料时应在 `uncertainty` 写明。
