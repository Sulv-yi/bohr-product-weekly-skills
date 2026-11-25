# 评分点对照表（自查用）

把题面 100 分的每个评分点，对到本 Skill 里**能被检查的东西**上。
用途：提交前逐行确认"这条有没有实物证据"，不写自评分，也不替代平台评审。

图例：**运行产物** = 跑一个案例时生成；**包内资源** = 随 Skill 提交的文件。

## 实际效果 40

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 任务完成度 | 15 | 可编辑 `.tex` 成稿（章节齐全、摘要、公式表格有真实内容）+ 编译记录 | 运行产物 `main.tex`、`selfcheck.md`；`result.json#result.manuscript` |
| 结果正确性 | 15 | 每条 `!` 错误定位到 file:line + 根因；引用键闭合；表格数据行齐 | 运行产物 `compile-report.json`、`cite-map.csv`、`selfcheck.md` 第 2 节 |
| 结果完整性 | 5 | 章节数、每节实义字数、公式数、表格数、引用闭合率 | 运行产物 `selfcheck.md` 第 1 节；`scorecard.json#metrics` |
| 结果可核验性 | 5 | 事实来源映射 ≥3 条 + 复现六要素 | 运行产物 `cite-map.csv`、`result.json#result.source_map`、`#reproduction` |

## 使用增益 25

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 质量增益 | 15 | 同一 rubric 下的 A/B 指标差（8 项变好、0 项变差） | 包内 `eval/rubric.json` + `eval/score_output.py`；`examples/ab-report.md` |
| 效率增益 | 5 | 结构预检先拦、编译一次跑完、错误按 file:line 归并；`cite-map.csv` 替代人肉对账 | 包内 `scripts/build_outputs.py`；运行产物 `cite-map.csv` |
| 增益可验证性 | 5 | 对照协议（同引擎同 rubric、3 次取中位、变差如实报、无引擎时判 n/a 不判 pass） | 包内 `eval/ab-protocol.md`、`eval/acceptance.md`、`eval/compare_ab.py` |

## 创新增益 15

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 新增能力 | 5 | 成稿实质门槛可计算（实义字数/公式内容/表格数据行/引用闭合/占位符）；编译错误定位到行；引用映射可逐条核 | 包内 `scripts/check_manuscript.py`、`scripts/build_outputs.py` |
| 方法改进 | 5 | 先出成稿 → 结构预检 → 编译 → 报错定位 → 引用收敛 → 复现记录；生成与核验分离 | `SKILL.md#核心原则`、`SKILL.md#工作流`、`references/error-taxonomy.md` |
| 创新证据 | 5 | 与基础 Agent / 在线编辑器 / 模板向导的边界与取舍；明确不声称的部分 | `references/innovation-boundary.md` |

## 可靠体验 10

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 调用与易用性 | 3 | 适用/不适用条件、0–9 步一次跑通、最小示例 | `SKILL.md#适用--不适用`、`examples/minimal-example.md` |
| 运行稳定性 | 4 | 不同工程/模板/引擎同一流程；脚本只读输入写独立输出；重复性取数口径 | `SKILL.md#工作流`、`scripts/probe_project.py`、`eval/ab-protocol.md` 第 3 节 |
| 异常处理 | 3 | 8 类异常与处置（无引擎/缺宏包/缺字体/报错级联/模板缺失/材料不足/权限/冲突），一律写入 uncertainty | `SKILL.md#异常处理`、`references/error-taxonomy.md` |

## 生态贡献 10

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 文档完整性 | 3 | 用途/依赖/工作流/输入输出/异常/限制/示例 | `README.md`、`SKILL.md`、`examples/minimal-example.md` |
| 资源可复用性 | 4 | 成稿门槛脚本、错误分类表、模板与公式规则、评分表与对照脚本可被他人直接用于自己的工程 | `scripts/`、`references/`、`eval/`、`examples/` |
| 分享推广价值 | 3 | 公开作品链接、可分享的编译排错案例与失败模式 | `GITHUB_URL.txt`、`references/error-taxonomy.md`、`references/innovation-boundary.md` |

## 提交前 60 秒自查

```bash
# 1) 骨架能跑（会拦住空骨架：39 字 + 表格无数据行 → 判 failed，符合预期）
python scripts/build_manuscript.py --case examples/selftest-case.json --out /tmp/x13 --main main.tex
python scripts/check_manuscript.py /tmp/x13/main.tex --case examples/selftest-case.json --bib /tmp/x13/refs.bib

# 2) 成稿门槛 + 结构指标
python scripts/check_manuscript.py examples/selftest-manuscript.tex --bib examples/selftest-refs.bib

# 3) 附件能生成（cite-map.csv / selfcheck.md / compile-report.json）
python scripts/build_outputs.py --tex examples/selftest-manuscript.tex --outdir /tmp/o13

# 4) 评分脚本可用
python eval/score_output.py --result examples/selftest-result.json \
    --tex examples/selftest-manuscript.tex --out /tmp/card13.json

# 5) 对照脚本可用
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/card13.json
```

五条命令全过，说明包内所有声称的能力都可执行；任何一条跑不通，就不要在文档里写它。

已知边界（写在这里，避免自查时误判）：

- 本机无 TeX 引擎，`compile-report.json#status` 为 `unavailable`，
  `score_output.py` 把 `gain_verifiability` 判 `n/a` 而不是 `pass`。
  评测镜像提供 `latex-compiler`，编译类指标需在镜像内复核后再看。
- `check_manuscript.py` 判的是"是不是写实的完整稿件"，判不了科学正确性；
  公式含义与表格数值是否符合原文，仍需人工/评审判断。
