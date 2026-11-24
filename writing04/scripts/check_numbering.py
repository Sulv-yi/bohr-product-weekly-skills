#!/usr/bin/env python3
"""编号同步与一致性检查（编得顺）。

输入：
  --manuscript  稿件文本（含正文引用标记，如 [1]、[2,3]、① 、(Smith,2020) 等；顺序编码制）
  --result      可选 result.json（若已含 renumber 后的结果）
  --style       样式：numeric([n]) / superscript(上标n) / author-year(著者-出版年)
检查项：
  R1 正文引用标记能否解析出编号集合
  R2 编号是否连续（从 1 起、无缺号、无重复段）
  R3 每个正文编号是否在文末列表存在（无悬空引用）
  R4 文末列表每个条目是否被正文引用（无未引用条目）
  R5 文末列表编号是否连续且与正文编号集合一致
  R6 样式一致性（同一稿件混用多种标记样式 -> warning/error）

稿件中的文末列表用标记识别：以 "参考文献"/"References"/"REFERENCES"/"Bibliography" 行为界，
其后的 "[n] ..." 行为条目；若稿件无该标记，则 --bib-count 指定文末条目数做 R3/R4 的弱检查。

用法:
    python3 check_numbering.py manuscript.md --out numbering.json [--style numeric]
    python3 check_numbering.py manuscript.md --bib-count 8 --out numbering.json
"""
import argparse
import json
import re


def split_body_refs(text):
    """返回 (正文文本, 文末列表文本)。"""
    lines = text.splitlines()
    idx = None
    # 兼容 Markdown 标题 "# References"、纯文本行、带冒号
    pat = re.compile(r'^\s*#{0,6}\s*(参考文献|参考资料|References|REFERENCES|Bibliography|BIBLIOGRAPHY)\s*[:：]?\s*$', re.I)
    for i, line in enumerate(lines):
        if pat.match(line):
            idx = i
            break
    if idx is None:
        return text, ''
    return '\n'.join(lines[:idx]), '\n'.join(lines[idx + 1:])


CITE_NUM = re.compile(r'\[(\d+(?:\s*[,\-–]\s*\d+)*)\]')
AUTHOR_YEAR = re.compile(r'\(([^)]*\b(?:19|20)\d{2}[a-z]?[^)]*)\)')
SUP_SNIPPET = re.compile(r'(?:<sup>|\\textsuperscript\{|\^)(\d+)(?:</sup>|})?')


def parse_nums(body, style):
    nums = set()
    raw = []
    if style in ('numeric', 'auto'):
        for m in CITE_NUM.finditer(body):
            part = m.group(1)
            for seg in re.split(r'[,，]', part):
                seg = seg.strip()
                if re.match(r'^\d+\s*[-–]\s*\d+$', seg):
                    a, b = re.split(r'[-–]', seg)
                    a, b = int(a), int(b)
                    if b >= a and b - a <= 20:
                        nums.update(range(a, b + 1))
                elif seg.isdigit():
                    nums.add(int(seg))
            raw.append(m.group(0))
    if style == 'superscript':
        for m in SUP_SNIPPET.finditer(body):
            nums.add(int(m.group(1))); raw.append(m.group(0))
    if style in ('author-year', 'auto'):
        for m in AUTHOR_YEAR.finditer(body):
            raw.append(m.group(0))
    return sorted(nums), raw


def ref_list_nums(reftext):
    """从文末列表行首 [n] 抽编号。"""
    nums = []
    for line in reftext.splitlines():
        m = re.match(r'^\s*\[(\d+)\]\s*\S', line)
        if m:
            nums.append(int(m.group(1)))
    return nums


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manuscript')
    ap.add_argument('--out', required=True)
    ap.add_argument('--style', default='auto', choices=['auto', 'numeric', 'superscript', 'author-year'])
    ap.add_argument('--bib-count', type=int, default=None)
    args = ap.parse_args()

    text = open(args.manuscript, encoding='utf-8', errors='replace').read()
    body, reftext = split_body_refs(text)
    nums, raw = parse_nums(body, args.style)
    list_nums = ref_list_nums(reftext)

    errors, warnings = [], []
    # R2 正文编号连续性
    if nums:
        expected = set(range(1, max(nums) + 1))
        missing = sorted(expected - set(nums))
        if missing:
            errors.append("R2 正文编号缺号: %s（编号不连续）" % missing[:10])
    else:
        warnings.append("R2 未从正文解析出任何引用编号（检查标记样式是否与 --style 匹配）")

    # R5 文末列表编号
    if list_nums:
        if sorted(list_nums) != list(range(1, len(list_nums) + 1)):
            errors.append("R5 文末列表编号不连续或重复: %s" % list_nums)
    elif args.bib_count:
        list_nums = list(range(1, args.bib_count + 1))

    # R3 悬空引用：正文有、列表无
    if list_nums and nums:
        dangling = sorted(set(nums) - set(list_nums))
        if dangling:
            errors.append("R3 悬空引用（正文引用但列表无条目）: %s" % dangling)
        # R4 未引用条目：列表有、正文无
        uncited = sorted(set(list_nums) - set(nums))
        if uncited:
            warnings.append("R4 文末条目未被正文引用: %s" % uncited)

    # R6 样式一致性
    styles_seen = set()
    if CITE_NUM.search(body):
        styles_seen.add('numeric')
    if SUP_SNIPPET.search(body):
        styles_seen.add('superscript')
    if AUTHOR_YEAR.search(body):
        styles_seen.add('author-year')
    if len(styles_seen) > 1:
        errors.append("R6 同一稿件混用多种引用样式: %s" % sorted(styles_seen))

    payload = {
        "status": "ok" if not errors else "failed",
        "style_detected": sorted(styles_seen) or [args.style],
        "body_numbers": nums,
        "list_numbers": list_nums,
        "raw_markers": raw[:50],
        "checks": {
            "R2_body_continuous": not any(e.startswith('R2') for e in errors),
            "R3_no_dangling": not any(e.startswith('R3') for e in errors),
            "R4_all_list_cited": not any(e.startswith('R4') for e in warnings),
            "R5_list_continuous": not any(e.startswith('R5') for e in errors),
            "R6_style_consistent": not any(e.startswith('R6') for e in errors),
        },
        "errors": errors,
        "warnings": warnings,
    }
    json.dump(payload, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(json.dumps({"out": args.out, "status": payload['status'],
                      "body_nums": len(nums), "list_nums": len(list_nums),
                      "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False))
    import sys
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
