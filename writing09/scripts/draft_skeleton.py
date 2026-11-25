#!/usr/bin/env python3
"""生成“可直接改写的方法与实验章节成稿骨架”，把六类要素 + 复现 + 追问
全部落成一个带占位槽和来源槽的结构化 JSON 骨架，保证写得全。

为什么需要：0 分常见原因是只交了校验脚本或只写了主干几句，
没有交出“步骤/设置/参数/数据/对照/复现/限制”齐全的成稿本体。
本脚本不代替写作，而是强制产出形态完整：每个要素有槽、每个数值有来源槽，
后续由 agent 填真实内容后即为可核验成稿。

用法:
  python draft_skeleton.py --case case.json --out /app/output/draft_skeleton.json
退出码 0=成功, 2=文件错误。
"""
import sys
import json
import os
import argparse

ELEMENTS = [
    ("steps", "方法步骤", ["input", "operation", "output", "condition"], "每步输入/操作/输出/判断条件；不把多步压成一句"),
    ("setup", "实验设置", ["hardware", "software", "seed", "repeats"], "训练/验证/测试分开；硬件/版本/种子/重复次数"),
    ("parameters", "参数表", ["name", "value", "unit", "scope", "source"], "名称/取值/单位/作用对象/来源(配置/日志/代码/作者确认)"),
    ("dataset", "数据集与划分", ["name", "version", "size", "preprocess", "split", "usage"], "名称/版本/规模/预处理/划分比例与随机方式/子集用途"),
    ("baselines", "对照实验", ["baseline", "version", "same_budget", "metric", "stats"], "基线对象与版本/是否同预算/指标/统计方式"),
    ("reproducibility", "复现清单", ["code_version", "env", "seed", "command", "data", "split"], "代码版本/环境/种子/命令/数据获取/划分方式"),
    ("limitations", "限制条件", ["scenario", "reason", "scope"], "落到具体失效场景，不用套话"),
]


def build(case):
    out = {
        "case_id": case.get("case_id", "<from case.json>"),
        "status": "partial",
        "_note": "成稿骨架：把所有 【...】 占位替换为来自材料的真实内容；每个数值必须能在 sources 找到对应条目；定稿后删除本字段并把 status 改为 success/partial。",
        "result": {
            "section": "【方法与实验章节正文：按 方法步骤→实验设置→参数→数据集→对照→复现→限制 的顺序成稿；每个数值/版本/条件后标注来源编号】",
            "elements": {},
            "reproducibility": {},
            "questions_for_author": [],
            "limitations": [],
        },
        "sources": [],
        "uncertainty": [{"type": "needs_human_confirmation", "note": "骨架阶段：待填入真实内容与来源后更新"}],
        "changes": ["由 draft_skeleton.py 生成骨架，待填充真实内容"],
    }
    for key, name, fields, rule in ELEMENTS:
        out["result"]["elements"][key] = {
            "_name": name,
            "_rule": rule,
            "_slots": {f: f"【{name}·{f}：待填，值须来自材料】" for f in fields},
        }
    for f in ("code_version", "env", "seed", "command", "data", "split"):
        out["result"]["reproducibility"][f] = f"【{f}：待填或标 not_reported】"
    out["result"]["limitations"] = [{"scenario": "【具体失效场景】", "reason": "【原因】", "scope": "【适用范围】"}]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    if not os.path.isfile(args.case):
        print(json.dumps({'error': 'case file not found', 'path': args.case}, ensure_ascii=False))
        return 2
    with open(args.case, encoding='utf-8') as f:
        case = json.load(f)
    obj = build(case)
    outdir = os.path.dirname(os.path.abspath(args.out))
    if outdir and not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(json.dumps({'ok': True, 'out': args.out, 'elements': [e[0] for e in ELEMENTS]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
