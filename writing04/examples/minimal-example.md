# 最小调用示例（示意，非真实案例结果）

以下为演示接口的**示例数据**，不是平台固定案例答案。

## 输入（示意）

`refs.bib`：
```bibtex
@article{smith2020,
  author={Smith, J. and Lee, A.}, title={Widget Performance under Condition C},
  year={2020}, journal={J. Test}, volume={5}, number={2}, pages={10-20},
  doi={10.1000/jt.2020.5.2}}
@misc{smith2020pre,
  author={Smith, J. and Lee, A.}, title={Widget Performance under Condition C (preprint)},
  year={2019}, url={https://arxiv.org/abs/1901.00001}}
@inproceedings{li2019,
  author={Li, W.}, title={A Different Widget Study}, year={2019},
  booktitle={Proc. Conf}, pages={1-8}, doi={10.1000/conf.2019.1}}
```

`manuscript.md`：
```
# Introduction
Widget performance under condition C was previously studied [1].
We adopt method M and report accuracy [2].

# References
[1] Smith et al. Widget Performance under Condition C. J. Test, 2020.
[2] Li. A Different Widget Study. Proc. Conf, 2019.
```

## 调用

```bash
python3 scripts/parse_library.py refs.bib --out entries.json
python3 scripts/dedupe_entries.py entries.json --out dedupe.json
python3 scripts/check_numbering.py manuscript.md --out numbering.json --style numeric
python3 scripts/verify_citations.py result.json --library entries.json \
  --manuscript manuscript.md --dedupe dedupe.json --numbering numbering.json --out verify.json
python3 scripts/validate_result.py result.json --case case.json
```

## 示意输出要点

- `smith2020` 与 `smith2020pre`：题名相似（仅差 "(preprint)"）+ 作者一致 + 年份接近 → dedupe 建议 merge，basis="预印本与正式版，作者与题名高度一致"。
- `li2019` 题名不同 → 与 smith 判 do_not_merge（即使同领域）。
- 稿件编号 [1][2] 连续、列表两条均被引用 → numbering status=ok。
- 论断句 "Widget performance under condition C was previously studied" 挂 [1]，claim_location=sec1.p1.s1，match_basis 说明 smith2020 研究 condition C 下的 widget performance → 挂得对、对得上。
