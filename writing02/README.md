# 学术语言润色 Skill（语义守恒 + 逐句可核 + 增益可验）

## 一句话

润色学术文本时，把"改得对、说得像"和"没改坏、讲得清"同时做到：语法术语语气照改，但限定强度、数字单位、引用编号、图表指向原样保留，逐句给出原文—改文—类型—理由，并把"到底改好了多少"算成可复现的指标。

## 适用

- 期刊论文 / 学位论文 / 基金申请 / 审稿回复 / 英文摘要的润色与校对
- 术语全篇统一、缩写首次出现治理
- 中译英表达优化（直译腔、冗余名词化、信息重心）

不适用：纯内容问答、纯翻译、纯格式转换、事实核查、代写新结论。

## 目录

```
SKILL.md                          触发条件、交付物清单、工作流、指标口径
scripts/
  build_polish_draft.py           建逐段工作台（plan + 骨架 + 术语候选）
  check_polish.py                 结构门槛（段落对齐/锁定项守恒/强度不变）
  lock_invariants.py              锁定数字/单位/引用/图表/限定词/否定词
  invariant_guard.py              改后全文不变量比对
  term_consistency.py             术语统一与缩写定义回扫
  validate_result.py              契约总校验（success 强制要求 scorecard 已通过）
eval/
  rubric.json                     题面 100 分细则落成的可执行条目与阈值
  score_output.py                 实测指标 → scorecard.json（无自评输入口）
  compare_ab.py                   A/B 差值判定（质量增益/效率增益）
  ab-protocol.md                  对照协议：条件一致、3 次重复、盲评
  acceptance.md                   硬门槛 H1–H5 与盲评表
references/
  hedge-and-modality.md           限定词强度守恒表（L0–L5 + 中文）
  terminology-governance.md       术语表格式与缩写治理规则
  register-by-genre.md            五类文体语气规则
  minimal-edit.md                 最小编辑与 change_log 规范
  source-mapping.md               事实/数字/引用来源映射规范
  exception-matrix.md             异常处理矩阵（超长/编码/混排/冲突/文体不明）
  innovation-boundary.md          与基础 Agent、通用工具、翻译、人工的边界
examples/
  minimal-example.md              最小调用示例（示意，非正式案例结果）
  selftest-case.json              自测输入样例
  selftest-result.json            自测输出样例（标注示例）
  scorecard.json                  自测样例跑出的指标，可复现
GITHUB_URL.txt                    GitHub 公开链接
```

## 依赖与安装

Python 3.9+，**全部脚本仅用标准库，无第三方依赖**。只读输入，不修改原稿。

## 核心方法

1. **建工作台**（`build_polish_draft.py`）：把原文切成段落，逐段锁定数字/单位/引用/图表指向与限定词，输出一段对一段的润色骨架。
2. **术语先定**（`term_consistency.py`）：同一概念只允许一种译法；冲突不自行裁决，交作者确认。
3. **分句最小编辑**：只动该动的地方，能改分句就不重写整句。
4. **逐句四元组**：每处实际改动都有原文、改文、类型标签、理由。改动几句就几条记录。
5. **算指标**（`eval/score_output.py`）：从原文与改文实际比对得出守恒率、术语一致性、覆盖率、改动率，写入 `scorecard.json`。**手写或自评的数字不算证据。**
6. **声明对照条件**（`eval/ab-protocol.md`）：同一原文、同一术语表、同一 rubric、3 次重复取中位数、盲评随机顺序。

## 与评分维度的对应

每一项都指向可运行的文件或命令，不是文字承诺。

| 维度 | 对应机制 | 怎么验 |
|---|---|---|
| 实际效果 40 | 逐段 `paragraphs` + 逐句 `change_log` + `sources` 定位 | `check_polish.py`、`score_output.py` |
| 使用增益 25 | 同一 rubric 下的 A/B 对照，指标可算、差值可复现 | `eval/rubric.json`、`eval/compare_ab.py` |
| 创新增益 15 | 术语表驱动全篇回扫、限定强度守恒、改写/审校双通道 | `term_consistency.py`、`references/innovation-boundary.md` |
| 可靠体验 10 | 触发边界、五类文体规则、异常矩阵、重复运行不漂移 | `references/exception-matrix.md`、`eval/ab-protocol.md` |
| 生态贡献 10 | rubric、指标脚本、术语表格式、自测样例可直接复用 | `eval/`、`examples/`、`GITHUB_URL.txt` |

## 自测（可复现）

```bash
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --out examples/scorecard.json
python scripts/validate_result.py examples/selftest-result.json --case examples/selftest-case.json
```

期望：第一条输出 `status=passed`，五项守恒指标均为 1.0，`sentence_change_rate≈0.4`；
第二条输出 `{"status": "passed", "problems": 0}`。
把样例里的 `42%` 改成任意模糊表述，第一条会立刻判 failed——这就是它能抓"顺手改掉数据"的证据。

## GitHub

`https://github.com/Sulv-yi/bohr-product-weekly-skills/tree/main/writing02`
