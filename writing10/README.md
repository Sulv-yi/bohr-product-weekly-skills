# results-discussion-writer

依据数据表、图表与统计输出写出结果与讨论章节。三个可判定的抓手：
**正文数值逐值回溯到图表**、**显著性措辞必须有统计量**、**结果段不许夹解释**。

## 目录

```
SKILL.md                     主文件：预算/门槛/八步流程/异常处理
README.md                    本说明
SCORING-MAP.md               100 分逐项对到证据位置 + 自查命令
GITHUB_URL.txt               公开作品链接
scripts/
  draft_skeleton.py          结果/讨论/局限骨架
  results_gate.py            度量口径（文件头写明每个指标的算法）
  validate_result.py         契约 + 门槛
  build_outputs.py           figure-audit.csv / claim-map.csv / selfcheck.md / preview.pdf
references/
  figure-reading.md          从数据表与图注可靠取数
  stats-language.md          显著性措辞与统计量对齐
  split-results-discussion.md 两节分工与泄漏检查
  edge-cases.md              七类异常与处置
  innovation-boundary.md     与基础 Agent / 写作助手的边界
eval/
  rubric.json                16 条验收口径
  score_output.py            算指标与判定，不给自评分
  compare_ab.py              Δ 表与增益判定
  ab-protocol.md             对照协议
  acceptance.md              H1–H9 + 四问盲评表
examples/
  selftest-materials.md      自测材料（演示数据）
  selftest-case.json         自测案例
  selftest-chapter.md        自测章节（1219 字 / 图表 3 行 / 局限 6 条）
  selftest-result.json       自测输出（含 figure_data）
  baseline-chapter.md / baseline-result.json  对照稿
  scorecard.json / baseline-scorecard.json    评分卡
  ab-report.md               A/B 结果
  minimal-example.md         最小示例
```

## 运行

```bash
python scripts/draft_skeleton.py --case /input/case.json --out /app/output/chapter.md
python scripts/build_outputs.py --result /app/output/result.json \
    --text /app/output/chapter.md --outdir /app/output
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/chapter.md
```

## 设计取舍

- **先建 figure_data 再写正文**：正文数值只能来自图表数据，杜绝"顺手写个约数"。
- **单位不进比较、符号按绝对值**：正文常把方向写进文字（"下降 2.1%"），图表存 -2.1 = 同值。
- **显著性必须带统计量**：没有 p 值/CI/检验名的"显著"判为表述过强。
- **结果段解释句上限 2 句**：两节互相顶替是本题最常见的失分点。
- **局限用可检验线索判定**："样本较少"不计分，`n=8`、`未做对照`、`单中心` 才计分。

## 资源限制合规

24 个文本文件（≤50），均 UTF-8，总量 < 2MB，单文件 < 500KB，无符号链接，无凭证残留，无预制答案。
