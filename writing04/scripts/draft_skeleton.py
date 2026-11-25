#!/usr/bin/env python3
"""生成“引用管理交付清单骨架”，把六类动作产物与可回溯条目全部列全，
防止只跑校验脚本、却没交出可核对的成稿/清单本体。

用法:
  python draft_skeleton.py --case case.json --out /app/output/deliverables.md
退出码 0=成功, 2=文件错误。
"""
import sys
import json
import os
import argparse

ITEMS = [
    ("manuscript", "可编辑稿件", "交付改后的稿件本体（.md/.docx），逐条列出引用位置变更"),
    ("citations", "引用定位与匹配", "每条：论断原文 claim + 精确位置 + ref_key + match_basis"),
    ("deduplication", "去重归并", "merged/kept_separate/pending，每条带可解释判据"),
    ("numbering", "编号一致性", "正文/文末编号连续、无悬空、无未引用、样式统一"),
    ("format_conversion", "格式转换", "来源格式→目标格式，字段映射与保留字段清单"),
    ("sources", "来源快照", "文献库/稿件来源路径与快照记录"),
]

NOTE = ("说明：本清单是交付骨架，需填入真实产物。所有 【…】 占位在定稿前必须替换为真实内容；"
        "status=success 时稿件本体、citations、sources 均不得为空。")


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
    lines = ["# 参考文献与引用管理 · 交付清单骨架", "", f"> {NOTE}", "",
             f"case_id: {case.get('case_id', '<from case.json>')}", ""]
    for i, (key, name, rule) in enumerate(ITEMS, 1):
        lines += [f"## {i}. {name}  [{key}]", f"- 要求：{rule}",
                  f"- 交付：【填入真实产物路径或内容；引用须逐条可回溯】", ""]
    lines += ["## 定稿前检查",
              "1. 六类产物齐全且无占位符 2. citations 每条有 claim 原文与 match_basis "
              "3. numbering 连续无悬空 4. deduplication 每条有判据 5. sources 可回溯。"]
    outdir = os.path.dirname(os.path.abspath(args.out))
    if outdir and not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({'ok': True, 'out': args.out, 'items': [x[0] for x in ITEMS]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
