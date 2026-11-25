# 最小调用示例（示例，非正式案例结果）

下面的输入输出仅用于说明接口与流程，**不是平台固定案例的答案**。

## 输入原文

```
The results suggest that the proposed method may works better than existing approaches in all cases. We obviously solved the problem of data scarcity by using 30 subjects (n = 30) in our experiments [3], and this clearly demonstrate that our model is superior to others shown in Fig. 2.
```

## 术语表（terms.json）

```json
{
  "term_map": {"proposed method": "proposed method", "our model": "proposed method"},
  "abbreviations": {},
  "forbidden": []
}
```

## 调用步骤

```bash
# 1. 改前锁定不可变项
python scripts/lock_invariants.py input.txt --out /app/work/lock.json

# 2. Agent 按 SKILL.md 工作流逐句润色，产出 draft.json

# 3. 守恒回扫
python scripts/invariant_guard.py /app/work/lock.json /app/work/draft.json --out /app/work/guard.json

# 4. 术语一致性回扫
python scripts/term_consistency.py input.txt /app/work/draft.json --term-map terms.json --out /app/work/terms.json

# 5. 输出契约校验
python scripts/validate_result.py /app/output/result.json --case /input/case.json
```

## 示意输出（result.json 节选）

```json
{
  "case_id": "demo-001",
  "status": "success",
  "result": {
    "polished_text": "The results suggest that the proposed method may work better than existing approaches in all cases. We addressed the problem of data scarcity by including 30 subjects (n = 30) in our experiments [3], and this suggests that the proposed method outperforms the approaches shown in Fig. 2.",
    "change_log": [
      {
        "original": "may works better",
        "revised": "may work better",
        "change_type": "agreement",
        "reason": "情态动词 may 后接动词原形",
        "preserved": ["may（L1 限定强度）", "better（比较级）"]
      },
      {
        "original": "obviously solved",
        "revised": "addressed",
        "change_type": "register",
        "reason": "期刊语域去除宣传化副词 obviously",
        "preserved": ["解决该问题这一主张"]
      },
      {
        "original": "clearly demonstrate that our model is superior to others shown in Fig. 2",
        "revised": "suggests that the proposed method outperforms the approaches shown in Fig. 2",
        "change_type": "register",
        "reason": "clearly demonstrate（L4）降为 suggest（L1）会改变强度——此处注意：原句 L4 与本示例实际冲突，按守恒规则应保留 demonstrate，仅把 our model 统一为 proposed method。保留此条用于演示失败模式。",
        "preserved": []
      }
    ],
    "term_decisions": [
      {"from": "our model", "to": "proposed method", "basis": "term_map"}
    ]
  },
  "sources": [
    {"claim": "30 subjects (n = 30)", "location": "第1段第2句", "type": "number"},
    {"claim": "引用 [3]", "location": "第1段第2句", "type": "citation"},
    {"claim": "Fig. 2", "location": "第1段第2句", "type": "figure_table"}
  ],
  "uncertainty": ["目标期刊未指定，按通用期刊语域处理"],
  "changes": ["处理 3 处语法/语域问题，统一 1 处术语，锁定 3 类不可变项"]
}
```

**注意**：上面第三条 change_log 是**故意演示的失败模式**——把 `clearly demonstrate`（L4）改成 `suggest`（L1）会造成限定强度漂移，实际运行中 `invariant_guard.py` 会判 failed 并阻止交付。正确做法见 `references/hedge-and-modality.md`：保持 L4，只做术语统一与搭配修正。

---

## 附：逐段润色链路最小示例（示意，非正式案例结果）

> 下面用两段自造文本演示接口与判定形态，**不是任何正式案例的内容，也不得作为预制答案**。

```bash
# 1) 建工作台：切段 + 逐段锁定
python scripts/build_polish_draft.py --case /input/case.json --out /app/work
# -> polish_plan.json / polished_skeleton.md / term_seed.md

# 2) 按骨架逐段填润色（Agent 的主要工作，不能跳过、不能合并段落）

# 3) 成稿门槛
python scripts/check_polish.py /app/output/result.json --plan /app/work/polish_plan.json
```

只给一段总结会被判失败：

```json
{"status": "failed",
 "errors": ["result.paragraphs 为空：润色成稿必须逐段对齐（pid/original/polished），只给一段总结或一份检查报告不算成稿"]}
```

润色时丢了数字也会被判失败：

```json
{"status": "failed",
 "errors": ["P02 丢失锁定项 number_unit=42%（原文 1 次，现 0 次）"]}
```

把"存在相关性"写成"存在相关性（R²=0.87）"这种凭空补数据同样会被拦住：

```json
{"status": "failed",
 "errors": ["P03 新增了原文没有的 number=0.87（现 1 次，原文 0 次）"]}
```

全部段落对齐且锁定项守恒时：

```json
{"status": "passed", "warnings": [], "stats": {"paragraphs": 3, "src_chars": 210, "out_chars": 214}}
```
