# 评分点对照表（自查用）

把题面 100 分的每个评分点，对到本 Skill 里**能被检查的东西**上。
用途：提交前逐行确认"这条有没有实物证据"，不写自评分，也不替代平台评审。

图例：**运行产物** = 跑一个案例时生成；**包内资源** = 随 Skill 提交的文件。

## 实际效果 40

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 任务完成度 | 15 | 六节成稿正文 | 运行产物 `section.md`；`result.json#result.section` |
| 结果正确性 | 15 | 参数表逐行来源 + 正文与表对齐 | 运行产物 `source-map.csv`；`selfcheck.md` 第 1 节 |
| 结果完整性 | 5 | 六要素覆盖、对照六项、复现六项 | 运行产物 `selfcheck.md` 第 1 节 |
| 结果可核验性 | 5 | 要素→文件/位置/原句；限制落到失效场景 | 运行产物 `source-map.csv`、`selfcheck.md` 第 3/5 节 |

## 使用增益 25

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 质量增益 | 15 | 同一 rubric 下的 A/B 指标差 | 包内 `eval/rubric.json` + `eval/score_output.py`；运行产物 `scorecard.json` |
| 效率增益 | 5 | 参数表与来源映射自动生成、缺口清单化 | 包内 `scripts/build_outputs.py`；运行产物 `selfcheck.md` 第 2 节 |
| 增益可验证性 | 5 | 对照协议（条件一致、3 次重复取中位、变差如实报告） | 包内 `eval/ab-protocol.md`、`eval/acceptance.md`、`eval/compare_ab.py` |

## 创新增益 15

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 新增能力 | 5 | 六要素/参数来源/正文-表对齐/对照与复现要件可计算 | 包内 `scripts/quality_gate.py`、`scripts/validate_result.py` |
| 方法改进 | 5 | 抽要素 → 写作 → 数值对齐 → 缺口追问 → 结构复核；写作与核对分离 | `SKILL.md#执行顺序`、`references/` |
| 创新证据 | 5 | 与基础 Agent / 实验记录工具 / 模板生成器的边界与取舍 | `references/innovation-boundary.md` |

## 可靠体验 10

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 调用与易用性 | 3 | 适用/不适用、一次跑通的步骤、最小示例 | `SKILL.md#适用`、`examples/minimal-example.md` |
| 运行稳定性 | 4 | 不同材料形态下的同一流程；重复性取数方式 | `SKILL.md` 流程、`eval/ab-protocol.md` 第 3 节 |
| 异常处理 | 3 | 6 类异常与处置（材料缺失/配置冲突/版本不明/权限/只有图/预算耗尽） | `SKILL.md#异常处理`、`references/gap-questioning.md` |

## 生态贡献 10

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 文档完整性 | 3 | 用途/依赖/配置/示例/适用边界/需人工确认项/维护 | `README.md`、`SKILL.md` |
| 资源可复用性 | 4 | 要素清单模板、参数表模板、追问清单、度量脚本、评分表 | `references/`、`scripts/`、`eval/`、`examples/` |
| 分享推广价值 | 3 | 公开仓库、章节样例、失败模式 | `GITHUB_URL.txt`、`examples/` |

## 提交前 60 秒自查

```bash
python scripts/draft_skeleton.py --case /input/case.json --out /tmp/s.json        # 骨架能跑
python scripts/validate_result.py <result.json> --case <case> --text <section>    # 门槛判定
python scripts/build_outputs.py --draft <section> --result <result> --outdir /tmp # 附件能生成
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --draft examples/selftest-draft.md --out /tmp/card.json
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/card.json          # 对照脚本可用
```

五条命令全过，说明包内所有声称的能力都可执行；任何一条跑不通，就不要在文档里写它。
