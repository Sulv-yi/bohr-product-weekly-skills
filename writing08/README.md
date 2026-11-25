# 引言与相关工作写作 Skill

面向「写作08｜引言与相关工作写作」赛题的参赛 Skill。依据科研材料起草/改写引言与相关工作：
四要素成稿、相关工作按维度分组比较、研究空白由已引文献推出、贡献逐条带证据，
并把"每条引用能否回到来源"落成可复核的 CSV 与自检表。

## 目录

```
SKILL.md                          主文件：触发条件、成稿门槛、7 步流程、异常处理
SCORING-MAP.md                    评分点 → 证据 对照表（自查用，不含自评分）
README.md                         本说明
GITHUB_URL.txt                    作品公开链接
scripts/
  draft_skeleton.py               成稿骨架生成（四要素齐全，先跑，防空壳）
  quality_gate.py                 结构度量：篇幅/分组/贡献/绑定率/空白推导链
  build_outputs.py                生成 source-map.csv、selfcheck.md、preview.pdf
  validate_result.py              契约 + 成稿结构门槛（不达标报错）
  citation_check.py               引用键覆盖、元数据完整性、编号连续性
references/
  background-and-gap.md           背景与研究空白推导
  related-work-grouping.md        相关工作分组比较框架
  contribution-alignment.md       贡献与图表证据对照
  citation-verification.md        引用核验清单
  source-handling.md              材料读取与边界处理
  evidence-and-uncertainty.md     证据格式与不确定性标注
  innovation-boundary.md          与已有方案的边界（与基础 Agent、文献工具、写作助手）
eval/
  rubric.json                     题面五维落地为可执行条目（含 auto_check 命令）
  score_output.py                 按 rubric 算指标与逐项判定，输出 scorecard.json（不自评）
  compare_ab.py                   A/B 差值表与增益判定（规则写死，不含人工加权）
  ab-protocol.md                  对照协议：条件一致、3 次重复取中位、变差如实报告
  acceptance.md                   验收硬门槛 H1–H6 + 盲评表
examples/
  minimal-example.md              最小调用示例
  selftest-case.json              示例案例（演示用虚构材料，非平台固定案例）
  selftest-draft.md / -result.json  Skill 侧示例输出
  baseline-draft.md / -result.json  对照侧示例输出（模拟不加载 Skill）
  scorecard.json / baseline-scorecard.json / ab-report.md  上述两者的评分卡与差值表
```

## 评分维度对应

| 评分维度 | 本 Skill 的应对 |
|---|---|
| 实际效果 40 | 四要素成稿 + 结构门槛（篇幅/分组/贡献/绑定率）+ 逐条来源映射 |
| 使用增益 25 | 骨架一次到位、来源映射与自检表自动生成；`eval/` 提供可重跑的对照口径 |
| 创新增益 15 | 结构可计算、贡献必须带证据、空白推导链可判定；方案边界写清 |
| 可靠体验 10 | 7 类异常处置；预算将尽时先存 partial；脚本只依赖标准库 |
| 生态贡献 10 | 完整文档、可复用的度量脚本与模板、示例题集与 A/B 记录 |

## 依赖与适用边界

- Python 3.9+，全部脚本仅用标准库；PDF 提取用 PyMuPDF / pdfplumber（见 `references/source-handling.md`），无文字层走 OCR。
- `preview.pdf` 需要环境有 `pandoc`（推荐 `--pdf-engine=xelatex`）或 `xelatex`；缺失时不生成，并在 `selfcheck.md` 中如实写明。
- 适用：中英文论文的引言/相关工作章节；顺序编码制或作者-年份制引用（格式由 `task.md` 指定）。
- 不适用：无科研材料时的纯文学创作；要求生成材料外事实或虚构引用；纯翻译。
- 学科适配：分组维度与空白类型需按领域替换，替换点在 `references/related-work-grouping.md` 顶部说明。

## 在评测环境里怎么用

1. Skill 安装到 `/skills/weekly-skill`，官方 DeepSeek Harness 在 3 个固定案例运行。
2. 输入 `/input/case.json` + `/input/task.md`；`<skill_dir>` 为 Skill 安装根，脚本在 `scripts/`。
3. 工作 `/app/work`；最终 `/app/output/` 应有：`result.json`（含 case_id 与 output_contract 全部字段）、`draft.md`、`source-map.csv`、`selfcheck.md`（有 pandoc 时另有 `preview.pdf`）。
4. 预算：64 次模型请求、900 秒、每响应 16384 tokens。先落完整初版再增量改进；`eval/` 在运行期不必读取。

## 维护

- 版本：1.2（2026-11）。变更：新增结构门槛与 `quality_gate.py`、`build_outputs.py`、`eval/` 对照层；`validate_result.py` 由"成稿实质性"检查升级为结构门槛。
- 改评分口径只改两处：`eval/rubric.json` 的 `thresholds` 与 `scripts/quality_gate.py` / `validate_result.py` 里的常量；两处须一致，改完跑一遍 `SCORING-MAP.md` 末尾的五条命令。
- 已知限制：结构指标只说明"形态是否合规"，不能替代对内容正确性的判断；`claim_binding_rate` 不区分"该引而未引"。

## 提交前检查

```bash
python scripts/validate_result.py examples/selftest-result.json \
    --case examples/selftest-case.json --text examples/selftest-draft.md
python scripts/build_outputs.py --draft examples/selftest-draft.md \
    --result examples/selftest-result.json --outdir /tmp/out
```

资源约束：≤50 个 UTF-8 文本文件，单个 ≤500KB、总量 ≤2MB，禁止符号链接。当前包内文本文件 30 个、约 185KB。
