# 文献翻译 Skill（可核验双语对照）

面向 Bohrium 产品周赛「阅读03｜文献翻译」。把真实科研文献译成**段落级双语对照**，以术语一致、段落完整、关系保真、可核验为核心。

## 设计主线
题面四个关注点 → 本 Skill 的可执行能力：

| 题面关注 | 本 Skill 机制 | 对应脚本/文档 |
|---|---|---|
| 术语稳 | 术语表抽取→锁定→全篇回扫，误译即报 | `build_glossary.py` / `verify_translation.py` / `terminology-lock.md` |
| 段落全 | 稳定段号、跨页续号、漏重错位检查 | `align_paragraphs.py` / `paragraph-alignment.md` |
| 关系准 | 数字单位、引用、图表公式编号、否定限定守恒回扫 | `verify_translation.py` / `relation-fidelity.md` |
| 可核验 | 每段 location + rationale + 原文 quote；未译显式标注 | `validate_result.py` / `verification-checklist.md` / `untranslated-policy.md` |

## 目录
```
SKILL.md                     触发条件、7 步工作流、输入输出、异常处理
references/
  terminology-lock.md        术语抽取与锁定、漂移检测
  paragraph-alignment.md     分段、段号约定、跨页续译、对齐校验
  relation-fidelity.md       数字/引用/图表/否定/限定六类守恒
  verification-checklist.md  交付前逐条自查清单
  untranslated-policy.md     未译与不确定性标注规则
  probe-and-boundaries.md    输入探查、任务边界、材料异常
scripts/
  build_glossary.py          候选术语抽取
  align_paragraphs.py        漏段/重复/错位检查
  verify_translation.py      硬信息守恒回扫（核心）
  validate_result.py         输出契约自检
examples/minimal-example.md  最小输入/输出示例（示意）
```

## 依赖与运行
- Python 3.9+，核心脚本仅用标准库
- PDF 输入时可选 `pip install pymupdf`；缺失时按探查脚本的降级链处理
- 全部路径相对本目录，不依赖任何个人文件；未打包任何测试答案

## 校验方法
```bash
python3 scripts/build_glossary.py source.txt --out glossary.json
python3 scripts/align_paragraphs.py source_segments.json result.json
python3 scripts/verify_translation.py source_segments.json result.json --glossary glossary.json
python3 scripts/validate_result.py result.json --case case.json
```

## 能力边界（如实说明）
- 守恒脚本只捕获**可机械判定**的硬损伤（数字、编号、否定、术语漂移）
- 指代、语气、语义级误译无法机械判定 → 输出 `semantic_review_required`，需人工复核并写入 `uncertainty`
- 无文字层 / 图片公式 / 扫描件 → 状态 `partial` 并标明，不编造原文或数据

## 评分对应
- 实际效果 40：段落级可核验译文 + 硬信息守恒
- 使用增益 25：术语一致率 / 长文完整率 / 事实准确率可对照
- 创新增益 15：术语强制锁定回填、跨页续译上下文、守恒自检清单
- 可靠体验 10：多后端探查、异常降级、未译显式标注
- 生态贡献 10：规则文档 + 可复用脚本 + 术语表格式

GitHub 公开链接（5 分附加分）：见 `GITHUB_URL.txt`。
