#!/usr/bin/env python3
"""生成“可直接改写的引言与相关工作成稿骨架”，把 output_contract 的每个字段
都落成一个带小标题、占位槽和证据槽的段落骨架，强制四要素齐全。

为什么需要：0 分常见原因是 agent 只写了几句空泛话或只交了校验脚本，
没有交出“四部分齐全、彼此承接、可逐条回溯”的成稿本体。
本脚本不代替写作，而是保证产出形态完整——后续由 agent 填入真实内容，
每段旁边预留 [证据槽] 指向 sources，从机制上杜绝“只有大纲/只有原则”。

用法:
  python draft_skeleton.py --case case.json --out /app/output/draft.md
  python draft_skeleton.py --case case.json --out /app/output/draft.md --lang zh
退出码 0=成功, 2=参数/文件错误。
"""
import sys
import json
import os
import argparse

# 题面四要素的规范顺序与写作要求（缺一即为不完整）
CANON = [
    ("background", "研究背景", "指向真实研究脉络与具体未解问题；避免“近年来受到广泛关注”式空转", "2-4 句"),
    ("related_work", "相关工作", "按问题/方法/技术路线分组比较；同维度对比取舍，不逐篇摘要", "每组 2-4 句"),
    ("gap", "研究空白", "由已引文献的共同限制/未覆盖场景/冲突结论推出；说明本文如何填补", "2-4 句"),
    ("contributions", "贡献表述", "与本文方法、图表、实验一一对应；不夸大适用范围", "逐条列点"),
]

ZH = {
    "title": "引言与相关工作 · 成稿骨架",
    "note": "说明：本文件是成稿骨架，需由作者/Agent 填入真实内容并逐段绑定 sources。占位符 【…】 与 [证据槽] 必须在定稿前全部替换或删除。",
    "evidence": "证据槽",
    "check": "定稿前检查：①四部分齐全且顺序正确 ②每个论断后挂 [证据槽] 指向 sources ③无材料外事实 ④不确定处写 uncertainty。",
}

# output_contract 里同一要素可能出现的字段名（不同案例写法不一致）。
# 判定时按别名归一到 CANON 的分类，输出时优先用契约里的原名，避免
# 「契约要 introduction，产出却写 background」被判成字段缺失。
ALIAS = {
    "background": ("introduction", "intro", "background", "motivation", "research_background"),
    "related_work": ("related_work", "relatedwork", "related", "literature_review", "prior_work"),
    "gap": ("gap", "research_gap", "knowledge_gap", "problem_statement", "open_problem"),
    "contributions": ("contributions", "contribution", "our_contributions", "key_contributions"),
}


def contract_keys(case):
    c = case.get('output_contract') if case else None
    if isinstance(c, list):
        return [str(x) for x in c]
    if isinstance(c, dict):
        return [str(x) for x in c.keys()]
    return []


def resolve_names(keys):
    """返回 {canon_key: 契约里的实际字段名或 canon_key}。"""
    named = {}
    low = {k.strip().lower(): k for k in keys}
    for canon, alts in ALIAS.items():
        for a in alts:
            if a in low:
                named[canon] = low[a]
                break
    return named

EN = {
    "title": "Introduction & Related Work - Draft Skeleton",
    "note": "Note: This is a draft skeleton. Replace every 【…】 placeholder and [evidence slot] with verified content bound to sources before finalizing.",
    "evidence": "evidence slot",
    "check": "Before finalizing: (1) all four parts present and ordered; (2) each claim carries an evidence slot into sources; (3) no out-of-material facts; (4) uncertainties listed.",
}


def contract_keys(case):
    c = case.get('output_contract') if case else None
    if isinstance(c, list):
        return [str(x) for x in c]
    if isinstance(c, dict):
        return [str(x) for x in c.keys()]
    return []


def build(case, lang='zh'):
    t = ZH if lang == 'zh' else EN
    keys = contract_keys(case)
    named = resolve_names(keys)
    lines = [f"# {t['title']}", "", f"> {t['note']}", ""]
    lines.append(f"case_id: {case.get('case_id', '<from case.json>')}")
    lines.append("")
    for idx, (key, zhname, rule, length) in enumerate(CANON, 1):
        field = named.get(key, key)
        matched = (not keys) or (field in keys)
        tag = "" if matched else "  （注意：output_contract 未列出此字段，仍需成稿或说明为何省略）"
        alias_note = "" if field == key else f"（契约字段名 {field}，result.result 必须用此名）"
        lines.append(f"## {idx}. {zhname}  [{key}]{tag}{alias_note}")
        lines.append(f"- 写作要求：{rule}；建议篇幅：{length}")
        lines.append(f"- 正文：【在此写入{zhname}段落；每条论断句末标注 [证据槽] 编号】")
        lines.append(f"- {t['evidence']}：指向 sources 中对应 id；无来源的论断须改写或移入 uncertainty")
        lines.append("")
    extra = [k for k in keys if k not in named.values()
             and k not in [c for c, *_ in CANON] and k not in ('references_used', 'references')]
    if extra:
        lines.append("## 契约里的其他字段（必须逐个覆盖，不可缺）")
        for k in extra:
            lines.append(f"- `{k}`：【按 output_contract 要求填写】")
        lines.append("")
    lines.append("## 来源与不确定性清单（与正文同步维护）")
    lines.append("- sources：逐条记录 claim / file / page / section / quote")
    lines.append("- uncertainty：材料不足、引用查不到、结论冲突、需作者确认项")
    lines.append("- changes：修改差异记录")
    lines.append("")
    lines.append(t['check'])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--lang', choices=['zh', 'en'], default='zh')
    args = ap.parse_args()
    if not os.path.isfile(args.case):
        print(json.dumps({'error': 'case file not found', 'path': args.case}, ensure_ascii=False))
        return 2
    with open(args.case, encoding='utf-8') as f:
        case = json.load(f)
    text = build(case, args.lang)
    outdir = os.path.dirname(os.path.abspath(args.out))
    if outdir and not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(text)
    print(json.dumps({'ok': True, 'out': args.out, 'chars': len(text),
                      'contract_fields': contract_keys(case)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
