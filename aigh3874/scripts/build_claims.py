#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_claims.py — 生成 evidence/claims.csv。

引文是手工从 materials/paper.md 复制的，脚本只做一件事：
校验每条引文确实逐字出现在原文里（防止抄写错误进入评估材料）。

用法: python3 scripts/build_claims.py
"""
import csv
import sys

PAPER = "materials/paper.md"
OUT = "evidence/claims.csv"
CORPUS_OUT = "evidence/corpus.csv"

# claim_id, subject, metric, value, page, quote, claim
CLAIMS = [
    ("C01", "PET_B", "cell_size", "2", "1",
     "PET_B shows cell sizes close to 2 μm",
     "PET_B 的泡孔尺寸可做到约 2 μm"),
    ("C02", "PET_B", "relative_density", "0.2,0.28", "1",
     "relative densities of 0.2 to 0.28",
     "PET_B 相对密度 0.2–0.28，摘要把它当作结果区间"),
    ("C03", "PET_C", "cell_size", "5,18", "1",
     "cell sizes from 5 to 18 μm",
     "PET_C 泡孔尺寸 5–18 μm"),
    ("C04", "PET_V", "relative_density", "0.16,0.18", "6",
     "in PET_V, the minimum relative density is obtained at Tf = 200 °C, "
     "irrespective of the saturation pressure, reaching values of 0.16 and 0.18 "
     "at 15 MPa and 30 MPa",
     "原生料 PET_V 的最低相对密度 0.16（15 MPa）/ 0.18（30 MPa），发泡温度 200 ℃"),
    ("C05", "PET_B", "relative_density", "0.35,0.20", "7",
     "in PET_B sample the minimum in relative density is obtained at different "
     "foaming temperatures depending on the saturation pressure: at 220 °C for "
     "psat = 15 MPa, with a value of 0.35; and at 200 °C for psat = 30 MPa, "
     "reaching a value of 0.20",
     "PET_B 的最低相对密度随压力分岔：0.35（15 MPa, 220 ℃）/ 0.20（30 MPa, 200 ℃）"),
    ("C06", "PET_V", "mfi", "highest", "4",
     "It is observed that the PET_V has the highest MFI value",
     "三种料里 PET_V 的 MFI 最高"),
    ("C07", "PET_B", "none", "11.52", "4",
     "11.52 ±1.04",
     "PET_B 的 MFI 为 11.52 g/10 min（表 1）"),
    ("C08", "3D-printed", "density_reduction", "40", "10",
     "a reduction of more than 40% in relative density in the 3D printed "
     "materials has been achieved",
     "3D 打印件的相对密度降幅超过 40%"),
    ("C09", "3D-printed", "density_reduction", "40", "10",
     "weight reductions of up to 40% and cell sizes around 2 μm",
     "讨论与结论段把同一降幅写成 weight reductions up to 40%"),
    ("C10", "3D-printed", "relative_density", "1.26", "10",
     "This 3D printed cap presents a density of 1.26 kg/m3",
     "3D 打印帽的固体密度记为 1.26 kg/m3"),
    ("C11", "3D-printed", "none", "", "1",
     "we demonstrate for the first time that rPET 3D-printed components can be "
     "foamed while preserving their overall geometry",
     "rPET 3D 打印件保形发泡属首次报道"),
    ("C12", "PET_B", "none", "0.80", "2",
     "Using a typical bottle-grade PET (0.80 dl/g) would result in significantly "
     "higher melt strength, which could bias the interpretation",
     "作者自述：若对照臂改用瓶级 0.80 dl/g 原生料，会引入解释偏倚"),
    ("C13", "PET_C", "relative_density", "0.20,0.17", "7",
     "minimum relative density is found at Tf = 220 °C, regardless of the "
     "saturation pressure, with values of 0.20 at 15 MPa, and 0.17 at 30 MPa",
     "PET_C 的最低相对密度 0.20（15 MPa）/ 0.17（30 MPa）"),
    ("C14", "PET_B", "none", "0.70,0.80", "2",
     "intrinsic viscosity of 0.70-0.80 dl/g",
     "PET_B 特性黏度 0.70–0.80 dl/g，高于对照 PET_V 的 0.63 dl/g"),
]


# 证据句底账：正文里能承载该指标的句子，标明料名、数值与页码
# 这不是为了凑数，而是给 C 项检查一个可逐行审计的对照集
CORPUS = [
    ("1", "PET_B", "relative_density", "0.2,0.28",
     "relative densities of 0.2 to 0.28"),
    ("7", "PET_B", "relative_density", "0.35,0.20",
     "with a value of 0.35; and at 200 °C for psat = 30 MPa, reaching a value of 0.20"),
    ("6", "PET_V", "relative_density", "0.16,0.18",
     "reaching values of 0.16 and 0.18 at 15 MPa and 30 MPa"),
    ("7", "PET_C", "relative_density", "0.20,0.17",
     "with values of 0.20 at 15 MPa, and 0.17 at 30 MPa"),
    ("10", "PET_C", "relative_density", "0.18,0.17",
     "achieving relative densities of 0.18 at 15 MPa saturation pressure and 0.17 "
     "for the ones saturated at 30 MPa"),
    ("1", "PET_C", "cell_size", "5,18",
     "cell sizes from 5 to 18 μm"),
    ("9", "PET_C", "cell_size", "3,6,20",
     "PET_C has two clear primary cell sizes in 3 and 6 μm, but it has some even "
     "bigger cells (some up to 20 μm)"),
    ("9", "PET_B", "cell_size", "2",
     "remains almost constant around 2 μm"),
    ("1", "PET_B", "cell_size", "2",
     "PET_B shows cell sizes close to 2 μm"),
    ("4", "PET_V", "mfi", "46.70", "46.70 ±0.68"),
    ("4", "PET_B", "mfi", "11.52", "11.52 ±1.04"),
    ("4", "PET_C", "mfi", "26.26", "26.26 ± 2.60"),
    ("10", "3D-printed", "relative_density", "1.26",
     "This 3D printed cap presents a density of 1.26 kg/m3"),
    ("10", "3D-printed", "density_reduction", "40",
     "a reduction of more than 40% in relative density in the 3D printed materials "
     "has been achieved"),
    ("10", "3D-printed", "density_reduction", "40",
     "weight reductions of up to 40%"),
]


def main():
    paper = open(PAPER, encoding="utf-8").read()
    bad = []
    for cid, _s, _m, _v, _p, quote, _c in CLAIMS:
        if quote not in paper:
            bad.append(cid)
    for i, (_p, subj, metric, _v, quote) in enumerate(CORPUS, 1):
        if quote not in paper:
            bad.append("corpus#%d(%s/%s)" % (i, subj, metric))
    if bad:
        print("引文未逐字命中：", ", ".join(bad))
        return 1

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["claim_id", "subject", "metric", "value", "page", "quote", "claim"])
        for row in CLAIMS:
            w.writerow(list(row))

    with open(CORPUS_OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["page", "subject", "metric", "value", "quote"])
        for row in CORPUS:
            w.writerow(list(row))

    print("wrote %s: %d claims" % (OUT, len(CLAIMS)))
    print("wrote %s: %d corpus rows, 引文全部逐字命中" % (CORPUS_OUT, len(CORPUS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
