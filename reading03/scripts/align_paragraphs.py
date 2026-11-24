#!/usr/bin/env python3
"""段落级对齐校验：漏段 / 重复 / 错位。

用法:
    python3 align_paragraphs.py <source_segments.json> <result.json> [--out report.json]

source_segments.json: [{"source_id":"p-001","source_text":"..."}, ...]
result.json: {"result":{"segments":[{"source_id":"p-001", ...}, ...]}}
"""
import argparse
import json
import sys


def load(path):
    return json.load(open(path, encoding="utf-8"))


def ids_from_source(src):
    if isinstance(src, dict):
        src = src.get("segments", src.get("source_segments", []))
    out = []
    for s in src:
        if isinstance(s, dict) and s.get("source_id"):
            out.append(str(s["source_id"]))
    return out


def ids_from_result(res):
    segs = (res.get("result") or {}).get("segments", [])
    out = []
    for s in segs:
        if isinstance(s, dict) and s.get("source_id"):
            out.append(str(s["source_id"]))
    return out


def check(src_ids, res_ids):
    src_set, res_set = set(src_ids), set(res_ids)
    missing = [x for x in src_ids if x not in res_set]
    extra = [x for x in res_ids if x not in src_set]
    dup = sorted({x for x in res_ids if res_ids.count(x) > 1})
    # 错位：按原文顺序过滤后的译文顺序是否与原文一致
    common_src = [x for x in src_ids if x in res_set]
    common_res = [x for x in res_ids if x in src_set]
    # 去重后比较顺序（首次出现）
    seen = set()
    common_res_uniq = []
    for x in common_res:
        if x not in seen:
            seen.add(x)
            common_res_uniq.append(x)
    out_of_order = common_src != common_res_uniq
    coverage = len(set(common_src)) / len(src_set) if src_set else 0.0
    problems = []
    if missing: problems.append("missing")
    if dup: problems.append("duplicate")
    if out_of_order: problems.append("out_of_order")
    if extra: problems.append("extra")
    return {
        "status": "passed" if not problems else "failed",
        "source_count": len(src_set),
        "result_count": len(res_ids),
        "coverage": round(coverage, 4),
        "missing": sorted(set(missing)),
        "extra": sorted(set(extra)),
        "duplicate": dup,
        "out_of_order": out_of_order,
        "problems": problems,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("result")
    ap.add_argument("--out")
    args = ap.parse_args()
    try:
        rep = check(ids_from_source(load(args.source)), ids_from_result(load(args.result)))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
