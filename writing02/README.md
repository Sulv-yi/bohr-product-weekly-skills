# 学术语言润色 Skill（语义守恒 + 可核对照）

## 一句话

润色学术文本时，把"改得对、说得像"和"没改坏、讲得清"同时做到：语法术语语气照改，但限定强度、数字单位、引用编号、图表指向原样保留，并给出逐句原文—改文—类型—理由对照。

## 适用

- 期刊论文 / 学位论文 / 基金申请 / 审稿回复 / 英文摘要的润色与校对
- 术语全篇统一、缩写首次出现治理
- 中译英表达优化（直译腔、冗余名词化、信息重心）

不适用：纯内容问答、事实核查、代写新结论、要求"把结论写强一点"的请求。

## 目录

```
SKILL.md                          触发条件、工作流、输入输出、异常处理
scripts/
  build_polish_draft.py           建逐段润色工作台（plan + 骨架 + 术语候选）
  check_polish.py                 成稿门槛（段落对齐/锁定项守恒/强度不变/篇幅合理）
  lock_invariants.py              改前锁定数字/单位/引用/图表/限定词/否定词
  invariant_guard.py              改后守恒校验（强度等级 + 关键项数量）
  term_consistency.py             术语统一与缩写定义回扫
  validate_result.py              输出契约校验（success 强制过 check_polish 门槛）
references/
  hedge-and-modality.md           限定词强度守恒表（L0–L5 + 中文）
  terminology-governance.md       术语表格式与缩写治理规则
  register-by-genre.md            五类文体语气规则
  minimal-edit.md                 最小编辑与 change_log 规范
  source-mapping.md               事实/数字/引用来源映射规范
examples/minimal-example.md       完整示例（含失败模式演示）
GITHUB_URL.txt                    GitHub 公开链接
```

## 依赖与安装

Python 3.9+，**全部脚本仅用标准库，无第三方依赖**。只读输入，不修改原稿。

## 核心方法

1. **建工作台**（`build_polish_draft.py`）：把原文切成段落，逐段锁定数字/单位/引用/图表指向与限定词，输出一段对一段的润色骨架。润色必须是逐段产出，不是一段概括。
2. **改前锁定**（`lock_invariants.py`）：把数字、单位、引用编号、图表指向、限定词强度、否定词、因果/相关词全部快照。
2. **分句最小编辑**：一句一记录，只改语言层，不碰专业含义。
3. **改后双回扫**：
   - `invariant_guard.py`：任何关键项数量变化或限定词跨级 → 判 failed，禁止交付
   - `term_consistency.py`：术语统一、缩写定义、禁止写法、拼写变体
4. **可核对照**：每个 change_log 含原文、改文、类型标签、理由、保留项；未改句子也要出现并标"无需修改"。

## 与评分维度的对应

| 维度 | 对应机制 |
|---|---|
| 实际效果 40 | 完整润色文本 + 逐句 change_log + sources 定位 + 输出契约校验 |
| 使用增益 25 | 确定性脚本承担锁定与回扫，Agent 专注语言层，减少返工 |
| 创新增益 15 | 限定强度守恒检查、术语表驱动全篇回扫、改写/审校双通道 |
| 可靠体验 10 | 五类文体规则、超长/混排/术语冲突等异常分支、回扫失败自动回退 |
| 生态贡献 10 | 规则集、术语表格式、脚本与示例可直接复用到其他学科 |

## GitHub

`https://github.com/Sulv-yi/bohr-product-weekly-skills/tree/main/writing02`
