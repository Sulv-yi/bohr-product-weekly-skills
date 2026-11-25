# 参考文献与引用管理 Skill

从真实稿件与文献库出发，完成引用定位、编号同步、文献去重、格式转换与来源核验，
交付可继续编辑的稿件与可逐条回溯的引用记录。四关注点：挂得对 / 编得顺 / 收得净 / 对得上。

## 目录

```
SKILL.md                        主说明（交付门槛、输入输出、7 步工作流、四性质保证、异常处理）
SCORING-MAP.md                  评分点 → 证据 对照表（自查用，不含自评分）
README.md                       本说明
GITHUB_URL.txt                  作品公开链接
scripts/
  draft_skeleton.py             先生成六类交付清单骨架（防空壳，先跑）
  parse_library.py              解析 BibTeX/RIS/JSON 文献库为统一条目
  dedupe_entries.py             去重归并建议（可解释判据 D1-D5）
  check_numbering.py            编号连续性/悬空/未引用/样式一致性检查
  verify_citations.py           核心核验（四性质 + 元数据 + 主题匹配）
  citation_gate.py              四性质结构度量（被下面两个脚本共用）
  build_outputs.py              生成 citation-map.csv、selfcheck.md、preview.pdf
  validate_result.py            契约 + 四性质结构门槛（不达标报错）
assets/
  format_mapping.json           BibTeX/RIS → 标准字段映射 + GB/T 7714 类型标识 + 保留字段
references/
  result-schema.md              结果结构定义
  dedup-rules.md                去重判据 D1-D5
  numbering-citations.md        编号与引用一致性规则
  format-and-verification.md    格式转换与核验口径
  edge-cases.md                 边界案例与处置
  innovation-boundary.md        与已有方案的边界（基础 Agent、文献管理软件、模板校验）
eval/
  rubric.json                   题面五维落地为可执行条目（含 auto_check 命令）
  score_output.py               按 rubric 算指标与逐项判定（不自评）
  compare_ab.py                 A/B 差值表与增益判定（规则写死）
  ab-protocol.md                对照协议：条件一致、3 次重复取中位、变差如实报告
  acceptance.md                 验收硬门槛 H1–H8 + 盲评表
examples/
  minimal-example.md            最小调用示例
  selftest-case.json            示例案例（演示用虚构稿件与文献库，非平台固定案例）
  selftest-result.json / -manuscript.md   Skill 侧示例输出与稿件
  baseline-result.json          对照侧示例输出（模拟不加载 Skill）
  scorecard.json / baseline-scorecard.json / ab-report.md  评分卡与差值表
```

## 依赖

Python 3.9+ 标准库，无需第三方包。`preview.pdf` 需要环境有 `pandoc`，缺失则不生成并在 `selfcheck.md` 中如实写明。

## 使用顺序

draft_skeleton（先落骨架）→ parse_library → dedupe_entries → check_numbering →
逐句填 citations → verify_citations → **build_outputs（落映射表与自检表）** → validate_result。

`/app/output` 最终应有：`manuscript.md`、`result.json`、`citation-map.csv`、`selfcheck.md`（有 pandoc 时另有 `preview.pdf`）。

## 关键规则

- 引用挂在需支撑的论断句，位置精确到句，不在图表注/段尾凑数。
- 每条引用必须有 `match_basis`：说明这篇文献的哪一点支撑这句话。
- 编号连续、无悬空引用、文末条目全被引用、样式不混用。
- 合并必须有判据；同名作者不同题名不得合并；歧义交人工确认（进 `pending`）。
- 格式转换保留 DOI/卷期页等关键字段，并给出字段映射。
- DOI 无网络时只做格式校验，不宣称已联网核验真实性。

## 在评测环境里怎么用

1. Skill 安装到 `/skills/weekly-skill`，官方 DeepSeek Harness 在 3 个固定案例运行。
2. 输入 `/input/case.json` + `task.md`；`<skill_dir>` 为 Skill 安装根，脚本在 `scripts/`。
3. 工作 `/app/work`；最终产物到 `/app/output`。
4. 预算：64 次模型请求、900 秒、每响应 16384 tokens。先落完整初版再增量改进；`eval/` 在运行期不必读取。

## 维护

- 版本：1.2（2026-11）。变更：新增 `citation_gate.py` 与四性质结构门槛、`build_outputs.py`、`eval/` 对照层、`SCORING-MAP.md`。
- 改口径只改两处：`eval/rubric.json` 的 `thresholds` 与 `scripts/citation_gate.py` / `validate_result.py` 的常量；改完跑 `SCORING-MAP.md` 末尾五条命令。
- 已知限制：`match_basis` 由作者撰写，脚本只保证其存在与形式可核，是否真支撑需人读原文；离线时 DOI 只做格式校验。

## 提交前检查

```bash
python scripts/validate_result.py examples/selftest-result.json --case examples/selftest-case.json
python scripts/build_outputs.py --result examples/selftest-result.json --outdir /tmp/out \
    --manuscript examples/selftest-manuscript.md
```

资源约束：≤50 个 UTF-8 文本文件，单个 ≤500KB、总量 ≤2MB，禁止符号链接。

## GitHub

`https://github.com/Sulv-yi/bohr-product-weekly-skills/tree/main/writing04`
