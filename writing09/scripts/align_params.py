#!/usr/bin/env python3
"""正文数值与参数表对齐：抓无来源数值 / 数值串位 / 覆盖不全。

用法:
    python3 align_params.py <section.txt> <params.json> [--out report.json]

params.json: {"parameters":[{"name","value","unit","source","confirmed"}]}
section.txt: 方法与实验章节正文（纯文本）
"""
import argparse
import json
import re
import sys

# 数值串（含科学计数、百分号、小数、范围）
# 排除标识符中的数字（CIFAR-10、ResNet-18、GPT-3、a1b2c3d）：前面是 字母+连字符 的跳过
NUM = re.compile(r"(?<![\w.@])(?<![A-Za-z]-)-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\s*[%]?(?![\w-])")


def canon(x):
    """数值归一化：去空格，科学计数转浮点字符串。"""
    x = x.strip().rstrip("%").replace(" ", "")
    try:
        return "num:" + format(float(x), ".10g")
    except ValueError:
        return "raw:" + x.lower()


def load_params(p):
    d = json.load(open(p, encoding="utf-8"))
    return d.get("parameters", []) if isinstance(d, dict) else d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("section")
    ap.add_argument("params")
    ap.add_argument("--out")
    args = ap.parse_args()
    try:
        text = open(args.section, encoding="utf-8").read()
        params = load_params(args.params)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    # 参数表中的合法数值集合（只要来源非空）
    allowed = set()
    confirmed_names = set()
    for p in params:
        if not isinstance(p, dict):
            continue
        src = p.get("source", "")
        val = str(p.get("value", ""))
        if src and val:
            allowed.add(canon(val))
        if p.get("confirmed") and p.get("name"):
            confirmed_names.add(str(p["name"]).lower())
    body_nums = [canon(m.group(0)) for m in NUM.finditer(text)]
    # 无来源数值：正文数值不在允许集合
    fabricated = sorted({n for n in body_nums if n.startswith("num:") and n not in allowed})
    # 覆盖：确认的关键参数名是否在正文出现（支持中英别名）
    ALIAS = {
        "lr": ["lr", "学习率", "learning rate"], "learning_rate": ["learning rate", "学习率"],
        "batch_size": ["batch size", "batch_size", "批大小", "批量"],
        "epochs": ["epoch", "轮", "迭代轮"], "epoch": ["epoch", "轮"],
        "seed": ["seed", "种子", "随机种子"], "weight_decay": ["weight decay", "权重衰减", "衰减"],
        "momentum": ["momentum", "动量"], "dropout": ["dropout", "丢弃"],
    }
    low = text.lower()
    uncovered = []
    for k in confirmed_names:
        aliases = ALIAS.get(k, [k.replace("_", " ")])
        if not any(a in low for a in aliases):
            uncovered.append(k)
    uncovered.sort()
    problems = []
    if fabricated: problems.append("fabricated_value")
    if uncovered: problems.append("uncovered_parameter")
    rep = {
        "status": "passed" if not problems else "failed",
        "body_number_count": len(body_nums),
        "allowed_values": len(allowed),
        "fabricated_values": fabricated,
        "uncovered_parameters": uncovered,
        "problems": problems,
        "note": "fabricated_value 表示正文数值在参数表中无来源或未对齐；需补来源或修正数值。",
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
