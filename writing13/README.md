# 写作13｜LaTeX 写作与编译 — Skill 交付

对应挑战：`product-arena-07-865de7e4`（写作13｜LaTeX 写作与编译）。本题**无** GitHub 附加分项。

## 一句话

把 LaTeX 稿件真正做到编译得通、改得对、交得可用、复现得了——用结构预检 + 多轮编译全量报错定位 + 引用收敛 + 来源映射 + 可复现构建记录替代"看起来像 LaTeX 的片段"。

## 文件清单

```
SKILL.md                        主文件：用途/成稿门槛/工作流/输入输出/异常处理
README.md                       本说明
SCORING-MAP.md                  评分点 → 证据位置对照 + 60 秒自查命令
GITHUB_URL.txt                  公开作品链接
scripts/
  probe_project.py              引擎/模板/主文件/依赖探查（不臆造软件状态）
  build_manuscript.py           按案例生成结构完整可编译的 .tex 成稿骨架 + refs.bib + 章节计划
  check_manuscript.py           成稿实质门槛（结构/篇幅/占位符/公式表格/引用闭合）
  static_check.py               无引擎结构硬损伤检查（括号/环境/label/引用）
  compile_and_parse.py          多轮编译 + 全量报错定位与根因分类 + 引用收敛
  build_outputs.py              落附件：cite-map.csv / compile-report.json / selfcheck.md / preview.pdf
  verify_result.py              五性质 + 契约自检（success 强制过成稿门槛）
references/
  error-taxonomy.md             编译错误分类与修复策略
  reproducibility.md            可重复构建记录规范
  template-and-math.md          模板适配与公式表格引用要点
  innovation-boundary.md        与基础 Agent / 在线编辑器 / 模板向导的边界与取舍
eval/
  rubric.json                   五维 100 分落成 21 条带 auto_check 的验收条目
  score_output.py               按 rubric 算指标与判定（不给自评分）
  compare_ab.py                 A/B 指标差与增益判定
  ab-protocol.md                对照协议（同引擎同 rubric、3 次取中位、变差如实报）
  acceptance.md                 硬门槛 H1–H7 + 人工盲评表
examples/
  minimal-example.md            最小调用示例（示意，非真实结果）
  selftest-case.json            自测用例输入（虚构材料）
  selftest-manuscript.tex       写实成稿示例（4 节 / 754 实义字 / 1 公式 / 1 表 / 3 引用）
  selftest-refs.bib             与上面成稿配套的文献库
  selftest-result.json          自测 result.json（含 source_map 与 reproduction）
  baseline-manuscript.tex       A/B 对照的 baseline 输出（2 节 / 无公式表 / 空泛）
  baseline-result.json          baseline 的 result.json
  scorecard.json                Skill 侧评分卡（14 pass / 2 na / 0 fail）
  baseline-scorecard.json       baseline 侧评分卡（3 条 fail）
  ab-report.md                  A/B 对照结果（8 项变好、0 项变差）
```

## 设计动机（对应题面四问）

- **成稿齐** → `build_manuscript.py` 先建出章节齐全、可直接编译的 .tex，再逐节写实；`check_manuscript.py` 卡住空骨架、占位符、凑不够篇幅的稿子。
- **编译得通** → `compile_and_parse.py` 多轮编译到收敛，全量解析每条 `!` 错误到 file:line + 根因，不止于首错。
- **改得对** → `static_check.py` 预检 label/引用/cite/环境；`source_map` 逐条绑定事实来源与改动记录。
- **交得可用** → `verify_result.py` 强制交付通过实质门槛的可编辑 .tex，禁止 PDF/截图/片段/检查报告顶替；`build_outputs.py` 同时落 `cite-map.csv`、`compile-report.json`、`selfcheck.md`，让每句论断与每条错误都有落点。
- **复现得了** → `probe_project.py` 探测真实引擎/版本/依赖，`reproduction` 记录命令与轮次；探测不到写 unknown，不猜版本号。

## 运行

Python 3.9+ 标准库即可。编译能力取决于环境是否提供 TeX 引擎。详见 SKILL.md 与 examples/minimal-example.md。

## 怎么确认它真能做到（不是文字自述）

```bash
python eval/score_output.py --list                       # 看 21 条验收条目各自绑定的检查命令
bash -c "$(sed -n '/提交前 60 秒自查/,/五条命令全过/p' SCORING-MAP.md | sed -n '/```bash/,/```/p')"
```

当前自测结果：Skill 侧 14 pass / 2 n/a / 0 fail；baseline 侧 3 条 fail（任务完成度、结果正确性、结果可核验性）。
A/B 对照 8 项变好、0 项变差（见 `examples/ab-report.md`）。两个 n/a 是编译类条目：
本机无 TeX 引擎，编译证据只能在带 `latex-compiler` 的镜像里产生，脚本拒绝把这种情况判成 pass。

## 环境缺失时会发生什么

本机无 TeX 引擎时：`probe_project.py` 如实标记；`static_check.py` 照常跑；`compile_and_parse.py` 返回 `status=unavailable` 并支持 `--log` 解析已有日志；`result.status` 只能到 partial，不伪造编译成功。评测镜像提供 `latex-compiler`，按真实引擎执行。

## 资源限制合规

30 个文本文件（≤50），均 UTF-8，总量约 220KB，单文件远小于 500KB，无符号链接，无凭证残留，无预置答案。

