#!/usr/bin/env python3
"""从配置/日志文本抽取参数骨架（名称/取值/来源行号）。

用法:
    python3 extract_params.py <material.txt> [--out params.json]

识别：
  1) key=value  (lr=1e-4, batch_size: 32)
  2) --flag value  (--epochs 100)
  3) 常见超参赋值 (learning rate 0.001, seed 42)
输出候选参数，需人工补单位/作用对象与确认来源。
"""
import argparse
import json
import re
import sys

KEYVAL = re.compile(
    r"\b([\w.]{2,30})\s*[=:]\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?|true|false|none|null|'[^']*'|\"[^\"]*\")",
    re.I)
FLAG = re.compile(r"(--[\w-]{2,30})\s+(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")
NAMED = re.compile(
    r"\b(learning rate|lr|batch size|batch_size|epochs?|seed|momentum|weight decay|"
    r"temperature|top-?k|dropout|hidden dim|max length)\b\s*(?:is|of|=|:)?\s*"
    r"(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", re.I)
KNOWN = {"lr", "learning_rate", "batch_size", "epochs", "epoch", "seed", "momentum",
         "weight_decay", "temperature", "top_k", "dropout", "hidden_dim", "max_length"}


def relevant(key):
    k = key.lower().lstrip("-")
    return k in KNOWN or any(x in k for x in ("lr", "rate", "seed", "epoch", "batch",
                                              "decay", "dropout", "dim", "length", "size"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", default="params.json")
    args = ap.parse_args()
    try:
        lines = open(args.source, encoding="utf-8").read().splitlines()
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    params, seen = [], set()
    for i, line in enumerate(lines, 1):
        # 按 key 去重（同一行同一参数只保留一次，优先 KEYVAL/FLAG 的精确取值）
        for m in list(FLAG.finditer(line)) + list(KEYVAL.finditer(line)) + list(NAMED.finditer(line)):
            key = m.group(1).lstrip("-")
            if not relevant(key):
                continue
            k = key.lower()
            if k in seen:
                continue
            seen.add(k)
            params.append({
                "name": key,
                "value": m.group(2),
                "unit": "",
                "scope": "",
                "source": f"{args.source}:{i}",
                "confirmed": False,
            })
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"parameters": params}, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "status": "candidates_extracted", "count": len(params), "out": args.out,
        "note": "请确认 unit/scope/source，确认后 confirmed=true 方可用于正文对齐",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
