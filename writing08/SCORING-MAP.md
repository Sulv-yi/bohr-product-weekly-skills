# 评分点对照表（自查用）

把题面 100 分的每个评分点，对到本 Skill 里**能被检查的东西**上。
用途：提交前逐行确认"这条有没有实物证据"，不写自评分，也不替代平台评审。

图例：**运行产物** = 跑一个案例时生成；**包内资源** = 随 Skill 提交的文件。

## 实际效果 40

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 任务完成度 | 15 | 四要素成稿正文 | 运行产物 `draft.md`；`result.json#result` |
| 结果正确性 | 15 | 来源五元组（claim/file/page/section/quote）、空白天花板 | 运行产物 `source-map.csv`、`result.json#sources`、`#uncertainty` |
| 结果完整性 | 5 | 分组数、各节字数、覆盖要素 | 运行产物 `selfcheck.md` 第 1 节 |
| 结果可核验性 | 5 | 逐条来源定位 + 推导链可见 | 运行产物 `source-map.csv`、`selfcheck.md` 第 3 节 |

## 使用增益 25

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 质量增益 | 15 | 同一 rubric 下的 A/B 指标差 | 包内 `eval/rubric.json` + `eval/score_output.py`；运行产物 `scorecard.json` |
| 效率增益 | 5 | 来源映射与自检表自动生成，人工核对条目清单化 | 包内 `scripts/build_outputs.py`；运行产物 `selfcheck.md` 第 2 节 |
| 增益可验证性 | 5 | 对照协议（条件一致、3 次重复取中位、变差如实报告） | 包内 `eval/ab-protocol.md`、`eval/acceptance.md`、`eval/compare_ab.py` |

## 创新增益 15

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 新增能力 | 5 | 结构门槛可计算、贡献必须带证据、空白链可判定 | 包内 `scripts/quality_gate.py`、`scripts/validate_result.py` |
| 方法改进 | 5 | 骨架先落 → 分组比较 → 空白推导 → 贡献对齐 → 结构复核；写作与核对分离 | `SKILL.md#执行顺序`、`references/` |
| 创新证据 | 5 | 与基础 Agent / 文献管理工具 / 通用写作助手的边界与取舍 | `references/innovation-boundary.md` |

## 可靠体验 10

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 调用与易用性 | 3 | 触发/不触发条件、一次跑通的步骤、最小示例 | `SKILL.md#何时使用`、`examples/minimal-example.md` |
| 运行稳定性 | 4 | 不同学科/篇幅/引用格式下的同一流程；重复性取数方式 | `SKILL.md` 流程、`eval/ab-protocol.md` 第 3 节 |
| 异常处理 | 3 | 7 类异常与处置（材料不足/引用查不到/格式未知/空白缺依据/语言/无文字层/预算耗尽） | `SKILL.md#异常处理`、`references/source-handling.md` |

## 生态贡献 10

| 评分点 | 分 | 证据 | 位置 |
|---|---|---|---|
| 文档完整性 | 3 | 用途/依赖/配置/示例/适用学科与语言/引用格式/限制/维护 | `README.md`、`SKILL.md` |
| 资源可复用性 | 4 | 度量脚本、分组与贡献模板、评分表、示例题集可被他人直接用于自己的论文 | `scripts/`、`references/`、`eval/`、`examples/` |
| 分享推广价值 | 3 | 公开仓库、可分享的写作案例与失败分析 | `GITHUB_URL.txt`、`examples/`、`references/innovation-boundary.md` |

## 提交前 60 秒自查

```bash
python scripts/draft_skeleton.py --case /input/case.json --out /tmp/d.md      # 骨架能跑
python scripts/validate_result.py <result.json> --case <case> --text <draft>  # 门槛判定
python scripts/build_outputs.py --draft <draft> --result <result> --outdir /tmp  # 附件能生成
python eval/score_output.py --result examples/selftest-result.json \
    --case examples/selftest-case.json --draft examples/selftest-draft.md --out /tmp/card.json
python eval/compare_ab.py examples/baseline-scorecard.json /tmp/card.json     # 对照脚本可用
```

五条命令全过，说明包内所有声称的能力都可执行；任何一条跑不通，就不要在文档里写它。
