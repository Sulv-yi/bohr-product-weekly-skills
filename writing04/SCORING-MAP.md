# 评分点对照表（自查用）

把题面 100 分的每个评分点，对到本 Skill 里**能被检查的东西**上。
用途：提交前逐行确认"这条有没有实物证据"，不写自评分，也不替代平台评审。

图例：**运行产物** = 跑一个案例时生成；**包内资源** = 随 Skill 提交的文件。

## 实际效果 40

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 任务完成度 | 15 | 可编辑稿件 + 逐条引用记录 + 五类动作产出 | 运行产物 `manuscript.md`、`result.json#result` |
| 结果正确性 | 15 | 论断原文、位置到句、match_basis、编号连续、去重判据 | 运行产物 `citation-map.csv`、`result.json#result.deduplication` |
| 结果完整性 | 5 | 四性质指标齐备 | 运行产物 `selfcheck.md` 第 1 节 |
| 结果可核验性 | 5 | 每条引用可回到条目与稿件位置 | 运行产物 `citation-map.csv`、`selfcheck.md` 第 3 节 |

## 使用增益 25

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 质量增益 | 15 | 同一 rubric 下的 A/B 指标差 | 包内 `eval/rubric.json` + `eval/score_output.py`；运行产物 `scorecard.json` |
| 效率增益 | 5 | 引用映射表与自检表自动生成，缺口清单化 | 包内 `scripts/build_outputs.py`；运行产物 `selfcheck.md` 第 2 节 |
| 增益可验证性 | 5 | 对照协议（条件一致、3 次重复取中位、变差如实报告） | 包内 `eval/ab-protocol.md`、`eval/acceptance.md`、`eval/compare_ab.py` |

## 创新增益 15

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 新增能力 | 5 | 四性质可计算；位置必须到句；去重三分判断必须有判据 | 包内 `scripts/citation_gate.py`、`scripts/verify_citations.py` |
| 方法改进 | 5 | 生成与核验分离；解析/去重/编号/定位/核验分工固定 | `SKILL.md#工作流`、`references/format-and-verification.md` |
| 创新证据 | 5 | 与基础 Agent / 文献管理软件 / 模板校验的边界 | `references/innovation-boundary.md` |

## 可靠体验 10

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 调用与易用性 | 3 | 触发/不触发、一次跑通的步骤、最小示例 | `SKILL.md#何时使用`、`examples/minimal-example.md` |
| 运行稳定性 | 4 | 三种文献库格式、只读输入写独立输出、重复运行一致 | `scripts/parse_library.py`、`eval/ab-protocol.md` 第 3 节 |
| 异常处理 | 3 | 五类异常与处置（字段缺失/DOI 不可核/歧义/编号冲突/格式不支持） | `SKILL.md#异常处理`、`references/edge-cases.md` |

## 生态贡献 10

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 文档完整性 | 3 | 用途/依赖/支持格式/示例/边界/维护 | `README.md`、`SKILL.md` |
| 资源可复用性 | 4 | 格式映射 asset、去重判据、度量脚本、评分表 | `assets/`、`scripts/`、`eval/`、`examples/` |
| 分享推广价值 | 3 | 公开仓库、引用案例与去重失败分析 | `GITHUB_URL.txt`、`examples/` |

## 提交前 60 秒自查

```bash
python scripts/draft_skeleton.py --case /input/case.json --out /tmp/deliverables.md   # 骨架能跑
python scripts/validate_result.py <result.json> --case <case>                          # 四性质门槛
python scripts/build_outputs.py --result <result.json> --outdir /tmp                   # 附件能生成
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --out /tmp/card.json                             # 评分卡
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/card.json               # 对照脚本
```

五条命令全过，说明包内所有声称的能力都可执行；任何一条跑不通，就不要在文档里写它。
