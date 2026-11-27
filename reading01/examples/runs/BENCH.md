# 对照记录：不用 Skill vs 用 Skill

同一台机器、同一进程、同一批真实 PDF，只改"是否加载本 Skill"。
数据由 `scripts/bench.py` 现算，可原样复现：

```bash
python scripts/bench.py --out bench.json caseA.pdf caseB.pdf
```

## 条件说明

| 条件 | 做法 |
|---|---|
| baseline | 逐页纯文本直出：有 `pypdf` 用 `page.extract_text()`；无第三方库用旧的流序拼接（`doctext._builtin_legacy`）。这是"把 PDF 读成一段文本"的典型路径，没有页码结构、没有章节/题注/文献、没有证据定位。 |
| skill | `scripts/doctext.py`：页树纠正页序 → 坐标分栏 → 段落/章节/题注/表格/参考文献 → `scripts/readwork.py verify` 逐字回查。 |

指标含义：`粘连/千字` = 每千字中"连续 28 个以上无空格字母"的片段数（词界丢失的代理指标）；
`可疑字符%` = 非 ASCII 且非中日韩字符的占比（乱码/符号污染的代理指标）；
`回查命中` = 随机抽 20 段，其首 40 字能否在文档模型中逐字命中。

## 场景一：环境**没有** pypdf（只有标准库）

Wiley 双栏英文论文（`paper.pdf`，743 KB，9 页）：

| 指标 | baseline（流序拼接） | skill（pdfmini） |
|---|---:|---:|
| 识别页数 | 20（页序错乱、页眉重复） | **9**（与真实页数一致） |
| 正文字符 | 42180 | 36342 |
| 粘连/千字 | 7.06 | **0.00** |
| 可疑字符% | 12.30 | **0.12** |
| 章节 / 题注 / 文献 | 无 | **6 / 14 / 40** |
| 回查命中 | 不可测（无段落 id） | **100%** |
| 耗时 | 39 ms | 234 ms |

中文报告（`case2-zh.pdf`，452 KB，13 页）：

| 指标 | baseline | skill |
|---|---:|---:|
| 识别页数 | 14 | **13** |
| 正文字符 | 160753（重复抽取 + 乱码叠加） | **12126** |
| 可疑字符% | 4.88 | **0.45** |
| 章节 | 无 | **4** |
| 回查命中 | 不可测 | **100%** |

字符数下降不是丢内容，而是去掉了重复页眉、重复页面与乱码片段：
baseline 把同页内容重复抽出多遍（20 页来自 9 页的重复），所以字符虚高。

## 场景二：环境**有** pypdf

| 文件 | 页数 base/skill | 可疑字符% base/skill | 结构（skill） | 回查 | 耗时 base/skill |
|---|---|---|---:|---:|---:|
| paper.pdf | 9 / 9 | 0.86 / **0.27** | 6 章节 / 19 题注 / 1 表格 / 39 文献 | 100% | 1161 / **682 ms** |
| case2-zh.pdf | 13 / 13 | 0.46 / 0.46 | 10 章节 | 100% | 192 / 586 ms |
| gokcen1985.pdf | 1 / 1 | 0.38 / 0.38 | —（单页无结构） | 100% | 25 / 78 ms |

即使 pypdf 在场，block 文本本身可用，Skill 的增益仍在**结构层**：
章节树、题注归属、表格行列、参考文献条目、每段的 `page + paragraph_id + quote`。
没有这些，"解析结果"只是一段无法回查的文本。

## 已知边界（不掩盖）

- 表格：`paper.pdf` 在无 pypdf 时解析出 0 张（4 张题注存在但记为不可解析，原因是该刊表格用
  公式排版、单元格无稳定列边界）；有 pypdf 时解析出 1 张。跨行合并单元格会表现为空串。
- 扫描件：无文字层不做 OCR，逐页记 `unreadable_pages`，不猜字。
- 加密 PDF：`status=blocked`，不臆测内容。
- 字体：子集字体且缺 ToUnicode 时可能丢字，记入 `uncertainty`，不补造。

## 复现命令

```bash
python scripts/bench.py --out bench.json paper.pdf case2-zh.pdf gokcen1985.pdf
python scripts/doctext.py paper.pdf --out work/doc.json
python scripts/readwork.py verify work/result.json --doc work/doc.json
```
