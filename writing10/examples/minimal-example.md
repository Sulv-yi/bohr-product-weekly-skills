# 最小调用示例

示意内容，数据与文献条目为演示数据，不代表正式案例结果。

## 1. 输入

```json
{
  "case_id": "selftest-001",
  "task": "依据数据表、图表与统计输出写出结果与讨论章节……",
  "output_contract": ["manuscript", "figure_data"]
}
```

## 2. 先建 figure_data

```json
{"fig_id": "图 1", "caption": "三组肿瘤体积（cm³）与组间检验", "n": "每组 8 只",
 "error_bar": "标准差", "stat": "t 检验",
 "values": {"对照_均值": 2.41, "低剂量_均值": 1.86, "高剂量_均值": 0.94,
            "高剂量_p": 0.012, "低剂量_p": 0.068, "高剂量_降幅_pct": 61}}
```

正文写 `2.41 cm³`、`0.94 cm³`、`61%`、`p=0.012`，都能在上述 `values` 找到同值。
写了 `3.0 cm³` 而 values 里没有 → `figure-audit.csv` 会标 `no`。

## 3. 骨架与写作要点

```bash
python scripts/draft_skeleton.py --case /input/case.json --out /app/output/chapter.md
```

- 结果段：`给药 21 天后，对照组体积为 2.41 cm³…（图 1）[1]`；显著性 `（p=0.012，t 检验）`。
- 边界：`低剂量组下降 23%，方向一致但未达显著（p=0.068）`。
- 讨论段：`与…不一致，可能原因是给药频次更高与观察期更长`。
- 局限：`每组 8 只、单中心、单批次`、`未做生存分析`、`未设阳性对照`。

## 4. 附件

```bash
python scripts/build_outputs.py --result /app/output/result.json \
    --text /app/output/chapter.md --outdir /app/output
```

`figure-audit.csv` 前两行：

```
value_in_text,found_in_figure_data,sources,count_in_text
2.41,no,-,1        <- 若 values 里没有 2.41，就是 no
```

## 5. 门槛结论

```bash
python scripts/validate_result.py /app/output/result.json \
    --case /input/case.json --text /app/output/chapter.md
# passed  case=selftest-001  status=success
#   字数=1219 结果=317 讨论=896 图表一致=100% 统计支撑=100% 泄漏=0 绑定=100% 局限线索=6
```
