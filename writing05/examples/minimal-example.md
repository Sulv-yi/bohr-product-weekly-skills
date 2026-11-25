# 最小调用示例

一次完整跑通的形态。下面所有内容都是**示意**，材料包为演示数据，不代表正式案例结果。

## 1. 输入

`/input/case.json`（节选）：

```json
{
  "case_id": "selftest-001",
  "task": "依据材料包写一段关于多孔支架孔隙率与渗透性取舍的讨论，每条实质性论断给出原文依据、定位与证据强度，并处理冲突证据。",
  "material": "examples/selftest-materials.md",
  "genre": "discussion",
  "language": "zh",
  "output_contract": ["draft", "claims", "evidence_table", "conflicts", "conflict_search_note"]
}
```

材料条目（节选）：

```
### M01
- 类型：系统综述（2019）
- 定位：§2.1，p.4
- 原文摘录：「多孔支架的孔隙率提高会同时降低强度与刚度，渗透性则随之上升，二者方向相反。」
- 设计与样本：系统综述，纳入 58 项研究
```

## 2. 切论断 + 定级

```bash
python scripts/claim_split.py --text /app/output/draft.md --json /app/output/units.json
# -> {"unit_count": 46, "with_cite": 46}

python scripts/claim_split.py --quote "系统综述，纳入 58 项研究" \
    --claim "多孔钛支架的孔隙率提高会同时降低强度与刚度，渗透性则随之上升，二者方向相反" --grade
# -> {"strength": "strong", "basis": ["设计线索 系统综述"], "hedge_ok": true}

python scripts/claim_split.py --quote "体外单次实验，n=6" --claim "该机制已被证实" --grade
# -> {"strength": "weak", "hedge_ok": false, "hedge_note": "含绝对化断言，但证据为 weak"}
```

第二条的 `hedge_ok=false` 就是本题「说得准」要拦的东西：弱证据配了肯定句。

## 3. result.json（节选）

```json
{
  "case_id": "selftest-001",
  "status": "success",
  "result": {
    "draft": "……（成稿全文，1425 字）",
    "claims": [
      {"claim_id": "c1",
       "claim": "多孔钛支架的孔隙率提高会同时降低强度与刚度，渗透性则随之上升，二者方向相反",
       "locator": "§1 第 1 段", "strength": "strong",
       "strength_basis": ["设计线索 系统综述", "纳入 58 项研究"], "flags": []},
      {"claim_id": "c8",
       "claim": "偏差可能来自支柱断裂与层间未熔合两类来源，前者多出现在支柱倾角小于 35° 时",
       "locator": "§1 第 1 段", "strength": "weak",
       "strength_basis": ["设计线索 体外单次实验", "样本量 6 < 10"], "flags": []}
    ],
    "evidence_table": [
      {"evidence_id": "e1", "claim_id": "c1", "source": "M01",
       "quote": "多孔支架的孔隙率提高会同时降低强度与刚度，渗透性则随之上升，二者方向相反。",
       "locator": "M01 §2.1", "basis": ["设计线索 系统综述"], "strength": "strong",
       "relation": "supports"}
    ],
    "conflicts": [
      {"claim_id": "c25", "sources": ["M10", "M11"],
       "note": "M10（体外，气体流量法）称渗透率随孔径单调上升；M11（在体，压汞法）称超过 600 μm 后不再提升。"}
    ],
    "conflict_search_note": "在材料包 12 篇中检索方向性结论，命中一对相反结果（M10/M11），原因线索见 M12……"
  },
  "sources": [
    {"id": "M01", "cite_key": "1", "file": "examples/selftest-materials.md",
     "section": "M01 §2.1",
     "quote": "多孔支架的孔隙率提高会同时降低强度与刚度，渗透性则随之上升，二者方向相反。"}
  ],
  "uncertainty": [
    {"type": "not_reported", "note": "材料未给出各研究的统计检验结果，显著性无法复核。"}
  ],
  "changes": [{"from": "初稿（13 条论断）", "to": "46 条论断 + 46 行证据 + 冲突处置", "reason": "按门槛补全"}]
}
```

## 4. 附件与自检

```bash
python scripts/build_outputs.py --result /app/output/result.json \
    --draft /app/output/draft.md --outdir /app/output
```

`claim-map.csv` 前两行：

```
claim_id,claim,locator,strength,strength_basis,hedge_ok,evidence_ids,evidence_count,draft_located
c1,多孔钛支架的孔隙率提高会同时降低强度与刚度…,§1 第 1 段,strong,设计线索 系统综述; 纳入 58 项研究,yes,e1,1,verbatim
```

`selfcheck.md` 会列出：字数、论断数、覆盖率、定位率、强度判定率、相称率、
证据行数、来源元数据齐备率、冲突处置、占位符、待人工确认项。

## 5. 门槛结论

```bash
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/draft.md
# passed  case=selftest-001  status=success
#   字数=1425 论断=46 覆盖=100% 定位=100% 强度=100% 相称=89% 来源=12 元数据=100%
```

`passed` 不是"自评通过"，是脚本按 `eval/acceptance.md` 的 H1–H10 算出来的；
任何一项不过都会逐条列出原因，且不允许通过改 `status` 绕过。
