# 方法与实验章节写作 Skill

面向「写作09｜方法与实验章节写作」赛题的参赛 Skill。把散落的实验材料整理成**可复现、可追溯**的方法与实验章节：
六类要素各自成段、参数表带来源、正文与表不两张皮、对照与复现要件可数、缺口显式追问。

## 设计主线

题面四个关注点 → 本 Skill 的可执行机制：

| 题面关注 | 本 Skill 机制 | 对应脚本/文档 |
|---|---|---|
| 写得全 | 六类要素各自成段 + 结构门槛（缺件即报错） | `quality_gate.py` / `element-extraction.md` |
| 写得准 | 参数表带来源列 + 正文与表取值对齐率 | `align_params.py` / `parameter-alignment.md` |
| 做得着 | 对照六项 + 复现六项逐项判定 | `check_reproducibility.py` / `reproducibility.md` |
| 说得住 | 限制须写到触发条件或阈值；缺口进 `questions_for_author` | `validate_result.py` / `gap-questioning.md` |

## 目录

```
SKILL.md                        触发条件、成稿门槛、7 步流程、异常处理
SCORING-MAP.md                  评分点 → 证据 对照表（自查用，不含自评分）
README.md                       本说明
GITHUB_URL.txt                  作品公开链接
scripts/
  draft_skeleton.py             六要素成稿骨架（先跑，防空壳）
  extract_params.py             从配置/日志抽取参数骨架
  align_params.py               正文数值 vs 参数表，抓无来源/串位
  check_reproducibility.py      复现六要素完整性
  quality_gate.py               六要素/参数表/对照/复现的结构度量
  build_outputs.py              生成 source-map.csv、selfcheck.md、preview.pdf
  validate_result.py            契约 + 结构门槛（不达标报错）
references/
  element-extraction.md         六类要素抽取（带来源）
  parameter-alignment.md        正文数值与参数表对齐、三类错误
  reproducibility.md            复现六要素、对照可比性、限制写法
  gap-questioning.md            缺口追问清单与状态规则
  verification-checklist.md     交付前逐条自查
  innovation-boundary.md        与已有方案的边界（基础 Agent、实验记录工具、模板生成器）
eval/
  rubric.json                   题面五维落地为可执行条目（含 auto_check 命令）
  score_output.py               按 rubric 算指标与逐项判定（不自评）
  compare_ab.py                 A/B 差值表与增益判定（规则写死）
  ab-protocol.md                对照协议：条件一致、3 次重复取中位、变差如实报告
  acceptance.md                 验收硬门槛 H1–H7 + 盲评表
examples/
  minimal-example.md            最小调用示例
  selftest-case.json            示例案例（演示用虚构材料，非平台固定案例）
  selftest-draft.md / -result.json   Skill 侧示例输出
  baseline-draft.md / -result.json   对照侧示例输出（模拟不加载 Skill）
  scorecard.json / baseline-scorecard.json / ab-report.md  评分卡与差值表
```

## 依赖与适用边界

- Python 3.9+，全部脚本仅用标准库；路径相对本目录，不依赖作者本地文件。
- `preview.pdf` 需要环境有 `pandoc`（推荐 `--pdf-engine=xelatex`）或 `xelatex`；缺失时不生成，并在 `selfcheck.md` 中如实写明。
- 适用：从 config/log/代码说明/数据说明撰写 Methods、Experimental Setup、参数表、数据划分、对照实验、复现清单、Limitation。
- 不适用：无事实底稿的虚构方法；只要"讲个大概"的科普；结果/讨论章节。
- 领域适配：六要素的名称与粒度需按领域替换（临床需加伦理与入排标准，工程需加设备与安全条件），替换点在 `references/element-extraction.md` 顶部。

## 在评测环境里怎么用

1. Skill 安装到 `/skills/weekly-skill`，官方 DeepSeek Harness 在 3 个固定案例运行。
2. 输入 `/input/case.json` + `/input/task.md`；`<skill_dir>` 为 Skill 安装根，脚本在 `scripts/`。
3. 工作 `/app/work`；最终 `/app/output/` 应有：`result.json`（含 case_id 与 output_contract 全部字段）、`section.md`、`source-map.csv`、`selfcheck.md`（有 pandoc 时另有 `preview.pdf`）。
4. 预算：64 次模型请求、900 秒、每响应 16384 tokens。先落完整初版再增量改进；`eval/` 在运行期不必读取。

## 维护

- 版本：1.2（2026-11）。变更：新增结构门槛与 `quality_gate.py`、`build_outputs.py`、`eval/` 对照层；`validate_result.py` 由"成稿实质性"升级为六要素结构门槛。
- 改评分口径只改两处：`eval/rubric.json` 的 `thresholds` 与 `scripts/quality_gate.py` / `validate_result.py` 里的常量；改完跑一遍 `SCORING-MAP.md` 末尾的五条命令。
- 已知限制：脚本只判"来源标注齐不齐、正文与表对不对得上"，数值本身对错需人工核对；`param_rows` 可被拆行注水，复查时看取值是否重复。

## 提交前检查

```bash
python scripts/validate_result.py examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-draft.md
python scripts/build_outputs.py --draft examples/selftest-draft.md \
    --result examples/selftest-result.json --outdir /tmp/out
```

资源约束：≤50 个 UTF-8 文本文件，单个 ≤500KB、总量 ≤2MB，禁止符号链接。
