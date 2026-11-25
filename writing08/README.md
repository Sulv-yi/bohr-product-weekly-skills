# 引言与相关工作写作 Skill

面向「写作08｜引言与相关工作写作」赛题的参赛 Skill。依据科研材料起草/改写引言与相关工作，事实、数字、引用可逐条回溯，研究空白由已引文献推出，贡献与实际证据对齐。

## 目录

```
SKILL.md                          主文件：触发条件、工作流、输入输出、异常处理
README.md                         本说明
GITHUB_URL.txt                    作品公开链接（提交前填写真实地址）
scripts/
  draft_skeleton.py               成稿骨架生成（四要素齐全，先跑，防空壳）
  citation_check.py               引用键覆盖、元数据完整性、编号连续性
  validate_result.py              输出契约 + 成稿实质性校验（空壳/占位符拦截）
references/
  background-and-gap.md           背景与研究空白推导
  related-work-grouping.md        相关工作分组比较框架
  contribution-alignment.md       贡献与图表证据对照
  citation-verification.md        引用核验清单
  source-handling.md              材料读取与边界处理
  evidence-and-uncertainty.md     证据格式与不确定性标注
examples/
  minimal-example.md              最小调用示例（示意，非官方案例）
```

## 与评分维度对应

| 评分维度 | 本 Skill 的应对 |
|---|---|
| 实际效果 40 | 四段式完整产出 + 逐条来源映射 + 空白推导 + 贡献对照 |
| 使用增益 25 | 写作与核对分离、脚本自动化引用核验，减少逐条核对与改写轮次 |
| 创新增益 15 | 分组比较框架、空白推导表、贡献-证据对照、引用绑定清单 |
| 可靠体验 10 | 材料不足/引用缺失/格式未知/语言切换等分支，脚本自检 |
| 生态贡献 10 | 完整文档、可复用模板与脚本、最小示例 |

## 依赖

Python 3.9+，脚本仅用标准库。PDF 材料提取用 PyMuPDF / pdfplumber（已在 source-handling.md 说明）；无文字层走 OCR 并标注。

## 评测环境使用

1. Skill 安装到 `/skills/weekly-skill`，官方 DeepSeek Harness 在 3 个固定案例运行。
2. 输入 `/input/case.json` + `/input/task.md`；`<skill_dir>` 为 Skill 安装根，脚本在 `scripts/` 子目录。
3. 工作 `/app/work`，最终 `/app/output/result.json`（含 case_id 及 output_contract 全部字段）+ 可编辑稿件。
4. 预算：64 次模型请求、900 秒、每响应 16384 tokens。先落完整初版再增量改进。

## 提交前检查

```bash
python scripts/validate_result.py <result> --case <case>
python scripts/citation_check.py <result> --sources <sources> --case <case>
```

资源约束：≤50 个 UTF-8 文本文件，单个 ≤500KB、总量 ≤2MB，禁止符号链接。当前目录远低于上限。

## GitHub 附加分

写作08 题面未列 GitHub 加分项（与部分其他题不同），GITHUB_URL.txt 仅作预留，按题面要求可不填。
