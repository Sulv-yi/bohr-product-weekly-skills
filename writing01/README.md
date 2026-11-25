# full-paper-writer

依据研究材料与给定文献写出**结构完整、可进入修改环节**的学术论文初稿。
先建材料索引，再按八类章节写，交付可编辑稿件 + 材料索引 + 三张核验表。

题面四问对应四件事：写得实（数值来自材料）、引得对（引用闭合且有依据）、
全得起来（章节/图表/文献/声明齐备）、改得动（层级与编号保留）。

## 目录

```
SKILL.md                        主文件：预算/门槛/七步流程/异常处理
README.md                       本说明
SCORING-MAP.md                  100 分逐项对到证据位置 + 60 秒自查命令
GITHUB_URL.txt                  公开作品链接
scripts/
  draft_skeleton.py             八类章节骨架（形态保证，防空壳）
  sections_gate.py              结构度量（章节/图表配对/引用闭合/数值回溯），口径写在文件头
  validate_result.py            契约 + 成稿门槛
  build_outputs.py              section-map.csv / material-index.csv / cite-audit.csv / selfcheck.md / preview.pdf
references/
  section-spec.md               八类章节最低要求与常见失败
  material-index.md             材料索引五字段、数值可回溯率口径
  source-handling.md            PDF/OCR/无文字层的处理边界
  evidence-and-uncertainty.md   证据强度与不确定性表达
  edge-cases.md                 八类异常与处置
  innovation-boundary.md        对基础 Agent / 模板向导 / 文献工具 / 查重工具的边界
eval/
  rubric.json                   16 条验收口径（对应题面五维）
  score_output.py               算指标与 pass/fail/n-a，不给自评分
  compare_ab.py                 两份评分卡的 Δ 表与增益判定
  ab-protocol.md                对照协议（含不可判定项规则）
  acceptance.md                 H1–H9 硬门槛 + 四问盲评表
examples/
  selftest-materials.md         自测材料包（演示数据）
  selftest-case.json            自测案例
  selftest-manuscript.md        自测稿件（8 节 / 12 引用 / 2 组图表 / 10 条索引）
  selftest-result.json          自测输出
  baseline-manuscript.md / baseline-result.json   对照稿（同题目，不带方法）
  scorecard.json / baseline-scorecard.json        两份评分卡
  ab-report.md                  A/B 对照结果
  minimal-example.md            最小调用示例
```

## 运行

Python 3.9+，脚本仅用标准库。`preview.pdf` 需 pandoc，缺失则跳过并如实记录。

```bash
python scripts/draft_skeleton.py --case /input/case.json --out /app/output/manuscript.md
python scripts/build_outputs.py --result /app/output/result.json \
    --text /app/output/manuscript.md --outdir /app/output
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/manuscript.md
```

## 设计取舍

- **材料索引先于正文**：先有「数值 → 材料位置」表，再写稿，避免正文出现无出处数值。
- **字数口径把数字算进去**：方法与结果参数密集，只数汉字会逼出注水段落。
- **图表双向配对**：正文提及与题注取交集，孤立题注单独报出，一侧存在不得分。
- **不可判定判 n/a**：无 pandoc 的预览项、无 baseline 的增益项都判 `n/a`，不判 pass。
- **不做稻草人对照**：baseline 是同题目下认真写的短稿，差距来自方法而非故意写错。

## 资源限制合规

26 个文本文件（≤50），均 UTF-8，总量 < 2MB，单文件 < 500KB，无符号链接，
无凭证残留，无预制答案；`examples/` 全部标注为演示数据。

## 维护

门槛变更需同步三处：`references/section-spec.md`、`scripts/sections_gate.py#SECTION_SPEC`、
`eval/rubric.json#thresholds`；改完重跑 `eval/compare_ab.py` 并更新 `examples/ab-report.md`。
