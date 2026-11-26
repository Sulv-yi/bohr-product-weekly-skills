# 实测记录（自有样本，非平台正式案例）

下面是本作品在**两篇真实 PDF 上实际跑出的结果**，用于说明能力边界。
平台会用自己的 3 个固定案例评测；这里的结果只代表本机实测，不作为官方得分依据。

复现命令：

```bash
python scripts/doctext.py "<your.pdf>" --out work/doc.json
python scripts/readwork.py claims work/doc.json --out work/claims.json --max 60
```

## case-2col-wiley

- 文件：`paper.pdf`（sha256 前 16 位 `8e61d273a2b04e9c`）
- 后端：`pypdf`，耗时 1935 ms
- 页数 9，段落 146，章节 6，题注 19，参考文献 39 条
- 表格：解析 0 个，未解析 6 个（原因写进 `stats.unparsed_tables`，不编造单元格）
- 页眉页脚剔除 0 行；不可读页 无；可读率 1.0
- 识别标题：One-component photoinitiator based on benzophenone and sesamol（置信度 medium）
- DOI：10.1002/pat.4337
- 章节：1 | INTRODUCTION / 2 | EXPERIMENTAL / 3 | RESULTS AND DISCUSSI / 4 | CONCLUSIONS / ACKNOWLEDGEMENTS / REFERENCES
- 本任务加工产物：`{"claim_count": 21, "claims_sample": [{"claim_id": "c001", "text": "All the results suggest that BPBDO is a 1-component photoinitiator that is an efficient photoinitiator for free radical polymerization.", "page": 1}, {"claim_id": "c002", "text": "Photopolymerization has received increased attention over the last few decades due to its several benefits, such as having high efficiency and low energ`

## case-zh-report

- 文件：`case2-zh.pdf`（sha256 前 16 位 `1ec8d773dbd4fbbc`）
- 后端：`pypdf`，耗时 1560 ms
- 页数 13，段落 97，章节 10，题注 0，参考文献 0 条
- 表格：解析 0 个，未解析 0 个（原因写进 `stats.unparsed_tables`，不编造单元格）
- 页眉页脚剔除 0 行；不可读页 无；可读率 1.0
- 识别标题：交线有解机械制图相贯线 3D 交互与三视图实验平台微信小程序应用开发赛 参赛作品介绍文档参赛作品类别:教育辅助、工具类。（置信度 low）
- 章节：一、团队介绍 / 二、小程序介绍 / 2.10 五项核心特色序号特色 说明 可验证指标 / 2.13 功能总览能力 实现程度教材题库 / 2.14 功能模块与使用场景模块 功能 对应课程 / 三、开发文档 / 4.1 所用 AI 工具名称与版本 / 3 平面立体扩展支持四棱锥、棱柱、圆台与挖空穿孔
- 本任务加工产物：`{"claim_count": 0, "claims_sample": []}`

## 已知边界（如实记录，未在本机样本上解决）

1. **双栏论文里「跨栏并排」的表格**：表格与正文处在同一视觉行，按坐标栅格切分会被正文打断，此时如实记 `unparsed_tables` 并给出原因，不返回错误的单元格。
2. **扫描件/无文字层**：不做 OCR 猜测，逐页记 `unreadable_pages`；需要文字时由上层决定是否接 OCR。
3. **占位型 PDF**（记录页写着原文文件缺失）：如实输出所述内容并标注「材料本身不含论文正文」，不虚构论文内容。
4. **参考文献切条目**：编号缺失时会退化为按作者字母起首切分，条目数与原文可能有偏差，已在 `reference_unparsed` 计数。
