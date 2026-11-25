# 异常处理：七种情况的处置

原则：**能修就修，不能修就如实标 partial / blocked，不编内容。**

## 1. 材料只有 PDF

```bash
pdf-text-tool paper.pdf -o paper.md      # 平台提供
pdftotext -layout paper.pdf paper.md      # 本机备选
```

若都不可用，`mm_run.py` 会写出：

```json
{"case_id": "...", "status": "blocked", "reason": "no_readable_material",
 "next": "用 pdf-text-tool 抽出带页码的 Markdown 后重跑"}
```

**不要**从文件名、摘要标签推测内容。案例输入是事实依据。

## 2. 抽取后没有页码锚点

`<!-- page N -->` 缺失时，`blocks.json` 的 `page=0`，`scaffold_stats.pages_missing=true`。

- 图上编号变成 `P0-Sn`，定位精度下降但**仍可回溯到句子**。
- `result.json` 的 `status` 写 `partial`，说明里写"未保留页码锚点"。
- 补救：用 `pdf-text-tool` 重新抽取（它默认保留页码）。

## 3. 表格被切成句子

抽取文本里表格常变成：

```
This | PET_B 5.94 3.17 ⋅ 10−13 | 7.37 1.32 ⋅ 10−12 | |
```

`mm_scaffold.py` 标 `table=true`，`mm_run.py` 的兜底不会用它做标题
（否则节点名就是一堆竖线和数字）。表格仍可作为 evidence 块引用。

## 4. 材料自相矛盾

例：摘要写「相对密度 0.2–0.28」，正文写「PET_B 在 15 MPa/220 ℃ 为 0.35」。

处置：
- 两个数各建一个节点，**不要合并**；
- 关系标 `conflict`，`why` 写清"摘要区间未覆盖 15 MPa 支路"；
- `uncertainty` 里写"两个数字来自不同段落，需回原文确认条件"。

## 5. 材料没有显式研究问题

不建 `question` 分支，`uncertainty` 里登记：

```json
{"node": "n0", "why": "材料没有显式陈述研究问题的句子", 
 "needs": "按案例任务补一条可检验的问题（含指标、阈值与对照）"}
```

`mm_check.py` 的 C3 会因此放行该分支，但报告里留痕。**硬凑一个"研究问题"是造假。**

## 6. 节点爆炸（>60）

说明归并没做。顺序：

1. 合并同级：同一指标的多个数合成一个节点，细节进 note；
2. 砍装饰句；
3. 仍超 60，拆图：按一级分支拆成 2–3 张，各自一个 `case_id` 后缀。

不要靠缩小字号解决——那是把可读性问题藏起来。

## 7. 重复材料（多版本 / 补充材料）

- 以最新版本建图；
- 旧版本与新版本的差异写进 `uncertainty`（"Table S1 与正文 0.28 不符"）；
- 支撑信息拿不到时，明确写"无法核到原始表格"，不要用正文数字代替。

判定标准：**能不能回到某一句原文**。回不到，就不是证据。
