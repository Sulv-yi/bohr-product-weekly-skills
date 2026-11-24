#!/usr/bin/env python3
"""复现六要素完整性检查。

用法:
    python3 check_reproducibility.py <result.json> [--out report.json]

检查 result.reproducibility 的六个键是否非空：
  code_version, environment, seed, command, data, split
缺失项写入 gaps，并按 blocking 规则给出状态。
"""
import argparse
import json
import sys

FIELDS = {
    "code_version": "代码版本（commit/tag/仓库）",
    "environment": "环境依赖（OS/语言/框架/关键库版本）",
    "seed": "随机种子",
    "command": "运行命令",
    "data": "数据获取方式",
    "split": "数据集划分方式",
}


def empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip() or v.strip().lower() in {"n/a", "na", "tbd", "?", "unknown", "未知", "待确认"}
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--out")
    args = ap.parse_args()
    try:
        d = json.load(open(args.result, encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    repro = (d.get("result") or {}).get("reproducibility") or {}
    gaps = []
    for k, label in FIELDS.items():
        v = repro.get(k)
        if empty(v):
            gaps.append({"field": k, "label": label, "blocking": k in ("code_version", "seed", "split")})
    rep = {
        "status": "passed" if not gaps else "partial",
        "fields_checked": len(FIELDS),
        "gap_count": len(gaps),
        "gaps": gaps,
        "note": "缺失项应写入 uncertainty 与 questions_for_author，状态保持 partial；不得臆造。",
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if not gaps else 1


if __name__ == "__main__":
    sys.exit(main())
