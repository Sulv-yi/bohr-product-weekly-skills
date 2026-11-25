# evidence-driven-writing

文献证据驱动写作 Skill：把一段需要文献支撑的写作任务落成 **论断清单 — 证据表 — 成稿** 三段交付，
每条论断带原文摘录、页/节/段定位与四档证据强度，并校验正文语气与该强度相称。

题面四问对应四件事：找得到（定位到段落）、对得上（摘录真的支撑这句）、
说得准（强度与语气相称）、复得现（编号/摘录/定位/理由四件齐）。

## 目录

```
SKILL.md                          主文件：用途/预算/门槛/七步流程/异常处理
README.md                         本说明
SCORING-MAP.md                    100 分逐项对到证据位置 + 60 秒自查命令
GITHUB_URL.txt                    公开作品链接
scripts/
  claim_split.py                  论断切分 + 强度规则判定 + 语气相称校验
  evidence_gate.py                结构与证据度量（口径写在文件头，供其余脚本共用）
  validate_result.py              契约 + 证据门槛
  build_outputs.py                claim-map.csv / evidence-table.md / selfcheck.md / preview.pdf
assets/
  strength-table.json             四档强度与关系类型的机读口径（可按学科替换）
references/
  claim-units.md                  论断单元切分口径
  evidence-strength.md            四档定级顺序、常见误判
  uncertainty-language.md         限定语与冲突处置
  edge-cases.md                   六类异常与处置
  innovation-boundary.md          对基础 Agent / 写作助手 / 引文工具的边界
eval/
  rubric.json                     21 条验收口径（对应题面五维）
  score_output.py                 算指标与 pass/fail/n-a，不给自评分
  compare_ab.py                   两份评分卡的 Δ 表与增益判定
  ab-protocol.md                  对照协议（含不可判定项规则）
  acceptance.md                   H1–H10 硬门槛 + 五性质盲评表
examples/
  minimal-example.md              最小调用示例
  selftest-materials.md           自测材料包（演示数据，非真实文献）
  selftest-case.json              自测案例
  selftest-draft.md               自测成稿（1425 字，46 条论断）
  selftest-result.json            自测输出（三段齐备 + 冲突处置）
  baseline-draft.md / baseline-result.json   对照稿（同材料，不带方法）
  scorecard.json / baseline-scorecard.json   两份评分卡
  ab-report.md                    A/B 对照结果
```

## 运行

Python 3.9+，脚本仅用标准库。`preview.pdf` 需要 pandoc，缺失时跳过并在 `selfcheck.md` 如实记录。

```bash
# 1) 切论断
python scripts/claim_split.py --text /app/output/draft.md --json /app/output/units.json
# 2) 定级（可反复调用）
python scripts/claim_split.py --quote "<原文摘录>" --claim "<论断原句>" --grade
# 3) 落附件
python scripts/build_outputs.py --result /app/output/result.json \
    --draft /app/output/draft.md --outdir /app/output
# 4) 跑门槛
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/draft.md
```

## 设计取舍

- **门槛前置到 SKILL.md 的预算表**：Agent 动笔前就按 1400 字 / ≥12 条论断写，
  而不是写完被门槛打回、白白消耗请求预算。
- **强度判定是规则不是判断**：设计线索 → 样本线索 → 复现线索，命中不了写 `insufficient`，
  不允许默认 `moderate`；改判可以，但要在 `strength_basis` 留理由。
- **不可判定判 `n/a`，不判 pass**：无 pandoc 时预览项、无 baseline 时增益项都判 `n/a`。
- **不做稻草人对照**：baseline 是同材料下认真写的短稿，差距来自方法而非故意写错。

## 资源限制合规

26 个文本文件（≤50），均 UTF-8，总量 < 2MB，单文件 < 500KB，无符号链接，
无凭证残留，无预制答案。`examples/` 全部标注为演示数据。

## 维护

口径变更需同步三处：`assets/strength-table.json`、`references/evidence-strength.md`、
`eval/rubric.json#thresholds`；改完重跑 `eval/compare_ab.py` 并更新 `examples/ab-report.md`。
