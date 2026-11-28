#!/usr/bin/env python3
"""对比 A（baseline）与 B（skill）两份 scorecard，给出增益判定。

用法:
    python eval/compare_ab.py A-scorecard.json B-scorecard.json [--json]

判定规则写在 eval/ab-protocol.md 第 4 节，本脚本只执行规则，不做加权。
"""
import argparse
import json
import sys

# 指标方向：+1 越大越好，-1 越小越好，0 区间指标
DIRECTION = {
    "segment_coverage": 1,
    "invariant_conservation": 1,
    "hedge_conservation": 1,
    "negation_conservation": 1,
    "term_uniqueness": 1,
    "edit_note_coverage": 1,
    "sentence_change_rate": 0,   # 区间指标，单独处理
    "manual_review_items": 0,    # 只展示，不判优劣（见下）
}

# 如实标注「需人工确认」不该被判成效率变差：这一项越少只能说明标注得越少，
# 不能说明结果越好。放 INFO 里只展示，不进质量/效率判定。
INFO = {"manual_review_items"}


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    m = d.get("metrics")
    if not isinstance(m, dict):
        raise SystemExit(f"{path} 里没有 metrics，先用 score_output.py 生成")
    # errors_before_accept：交付前必须消除的错误条数，直接取同一脚本给出的
    # errors 列表长度。它是可复现的真实效率证据——基线要修 3 轮才干净、
    # skill 一次通过，差别就落在这里，不靠人工估时。
    m = dict(m)
    m["errors_before_accept"] = len(d.get("errors") or [])
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("skill")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    a, b = load(args.baseline), load(args.skill)
    rows = []
    for k, direction in DIRECTION.items():
        if k not in a or k not in b:
            continue
        delta = round(b[k] - a[k], 4)
        if k in INFO:
            verdict = "info"
        elif direction == 0:
            # 改动率：<=0.6 视为最小编辑；区间下限 0.2 以下说明没真改
            verdict = "ok" if 0.2 <= b[k] <= 0.6 else ("under-edit" if b[k] < 0.2 else "over-edit")
        elif direction > 0:
            verdict = "better" if delta > 0 else ("same" if delta == 0 else "worse")
        else:
            verdict = "better" if delta < 0 else ("same" if delta == 0 else "worse")
        rows.append({"metric": k, "baseline": a[k], "skill": b[k],
                     "delta": delta, "verdict": verdict})

    # 效率单独一行：错误消除数（越小越好）
    rows.append({"metric": "errors_before_accept", "baseline": a["errors_before_accept"],
                 "skill": b["errors_before_accept"],
                 "delta": b["errors_before_accept"] - a["errors_before_accept"],
                 "verdict": "better" if b["errors_before_accept"] < a["errors_before_accept"]
                 else ("same" if b["errors_before_accept"] == a["errors_before_accept"] else "worse")})

    quality_ok = (
        next((r["delta"] for r in rows if r["metric"] == "invariant_conservation"), 0) >= 0
        and next((r["delta"] for r in rows if r["metric"] == "term_uniqueness"), 0) >= 0
        and sum(1 for r in rows if r["verdict"] == "better" and r["metric"] not in INFO) >= 2
        and b.get("sentence_change_rate", 0) <= 0.6
    )
    efficiency_ok = (
        b["errors_before_accept"] <= a["errors_before_accept"]
        and b["errors_before_accept"] == 0
        and b.get("edit_note_coverage", 0) >= 0.9
    )

    out = {
        "rows": rows,
        "quality_gain": "established" if quality_ok else "not-established",
        "efficiency_gain": "established" if efficiency_ok else "not-established",
        "worse_metrics": [r["metric"] for r in rows if r["verdict"] == "worse"],
        "info_metrics": sorted(INFO),
        "note": "只报差值。任一项变差都要写进 uncertainty，不做选择性报告；"
                "manual_review_items 属如实标注，不计优劣。",
    }

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"{'指标':<26}{'baseline':>10}{'skill':>10}{'Δ':>10}  判定")
        for r in rows:
            print(f"{r['metric']:<26}{r['baseline']:>10.4f}{r['skill']:>10.4f}{r['delta']:>+10.4f}  {r['verdict']}")
        print()
        print("质量增益:", out["quality_gain"])
        print("效率增益:", out["efficiency_gain"])
        if out["worse_metrics"]:
            print("变差的指标:", ", ".join(out["worse_metrics"]), "（须写入 uncertainty）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
