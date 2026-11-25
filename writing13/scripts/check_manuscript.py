#!/usr/bin/env python3
"""成稿实质性核验：确认 .tex 是一份写实、完整、可交付的稿件，而不是空骨架或占位符。

用法:
    python3 check_manuscript.py main.tex [--case case.json] [--bib refs.bib]
    python3 check_manuscript.py main.tex --min-section-chars 120 --min-total-chars 600

检查：
  结构   -> documentclass / begin-end document / 环境配对 / 必需章节齐全
  实质   -> 每节正文去注释去命令后的实义字数达标；摘要非空；全文总字数达标
  占位   -> 无 TODO / TBD / FIXME / placeholder / 待补充 / 【】 等占位痕迹；
            且 build_manuscript 的「本节正文待写」提示已被全部替换
  要素   -> 至少一个含真实内容的 equation、一个含 >=2 数据行的 table
  引用   -> \\cite 的 key 能在 refs.bib 或 thebibliography 中找到

退出码 0 = 通过（可写 status=success）；1 = 未通过（应写 partial 并说明缺什么）。
"""
import argparse
import json
import os
import re
import sys

PLACEHOLDER_TOKENS = [
    "TODO", "TBD", "FIXME", "XXX", "placeholder", "Placeholder",
    "待补充", "待填写", "待完善", "待写", "【", "】", "{{", "}}",
]

CJK = r'\u4e00-\u9fff\u3400-\u4dbf'


def strip_comments(tex):
    """去掉未转义的 % 行注释。"""
    out = []
    for line in tex.splitlines():
        buf = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '\\' and i + 1 < len(line):
                buf.append(line[i:i + 2])
                i += 2
                continue
            if ch == '%':
                break
            buf.append(ch)
            i += 1
        out.append(''.join(buf))
    return '\n'.join(out)


def clean_prose(chunk):
    """把 LaTeX 片段清成纯文本，用于数实义字。"""
    s = chunk
    # 去掉非正文参数的命令（引用/标签/输入/文献）
    s = re.sub(r'\\(?:cite[a-zA-Z]*|ref|eqref|label|input|include|bibliography|bibliographystyle|'
               r'usepackage|documentclass|includegraphics|url|href)\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})*', ' ', s)
    s = re.sub(r'\\(?:begin|end)\{[^{}]*\}', ' ', s)
    s = re.sub(r'\\[a-zA-Z]+\*?', ' ', s)
    s = s.replace('{', ' ').replace('}', ' ').replace('$', ' ').replace('&', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def count_real(s):
    """CJK 字符数 + 英文单词数。"""
    cjk = len(re.findall(r'[%s]' % CJK, s))
    words = len(re.findall(r'[A-Za-z][A-Za-z0-9\-]{1,}', s))
    return cjk + words


def split_sections(tex):
    """返回 [(title, body), ...]，body 为该节到下一节/参考文献之前的内容。"""
    stripped = strip_comments(tex)
    marks = list(re.finditer(r'\\section\*?\{([^{}]*)\}', stripped))
    out = []
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(stripped)
        tail = stripped[start:end]
        cut = re.search(r'\\(?:bibliography|begin\{thebibliography\}|end\{document\})', tail)
        if cut:
            tail = tail[:cut.start()]
        out.append((m.group(1).strip(), tail))
    return out


def check(tex, case, bib_text, min_sec, min_total):
    errors, warnings = [], []
    raw = tex

    # ---- 结构 ----
    if not re.search(r'\\documentclass', raw):
        errors.append('缺少 \\documentclass')
    if not re.search(r'\\begin\{document\}', raw):
        errors.append('缺少 \\begin{document}')
    if not re.search(r'\\end\{document\}', raw):
        errors.append('缺少 \\end{document}')

    body = strip_comments(raw)
    begins = re.findall(r'\\begin\{([^{}]*)\}', body)
    ends = re.findall(r'\\end\{([^{}]*)\}', body)
    from collections import Counter
    cb, ce = Counter(begins), Counter(ends)
    for env in set(list(cb) + list(ce)):
        if cb[env] != ce[env]:
            errors.append(f'环境未配对: {env} begin={cb[env]} end={ce[env]}')

    # ---- 骨架是否填实 ----
    if '本节正文待写' in raw:
        errors.append('仍是 build_manuscript 生成的空骨架：需逐节写实后删除该提示')

    # ---- 占位符 ----
    for tok in PLACEHOLDER_TOKENS:
        if tok in body:
            errors.append(f'正文残留占位符: {tok}')

    # ---- 章节实质 ----
    secs = split_sections(raw)
    if not secs:
        errors.append('没有任何 \\section，成稿未成形')

    required = []
    if isinstance(case, dict):
        for key in ('required_sections', 'sections', 'manuscript_sections', 'outline'):
            v = case.get(key)
            if isinstance(v, list) and v:
                for it in v:
                    if isinstance(it, str):
                        required.append(it.strip())
                    elif isinstance(it, dict):
                        t = it.get('title') or it.get('name') or it.get('section')
                        if t:
                            required.append(str(t).strip())
                break
    got_titles = [t.lower() for t, _ in secs]
    for req in required:
        if req and not any(req.lower() in g or g in req.lower() for g in got_titles):
            errors.append(f'缺少必需章节: {req}')

    thin = []
    for title, chunk in secs:
        n = count_real(clean_prose(chunk))
        if n < min_sec:
            thin.append(f'{title}({n}字)')
    if thin:
        errors.append(f'以下章节实质篇幅不足 {min_sec} 字: ' + '; '.join(thin))

    abstract = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', raw, re.S)
    if not abstract:
        warnings.append('没有 abstract 环境')
    elif count_real(clean_prose(abstract.group(1))) < 40:
        errors.append('摘要实质篇幅不足 40 字')

    total = count_real(clean_prose(body))
    if total < min_total:
        errors.append(f'全文实义字数 {total} < {min_total}，不成稿')

    # ---- 数学与表格要素 ----
    eqs = re.findall(r'\\begin\{(equation\*?|align\*?)\}(.*?)\\end\{\1\}', body, re.S)
    filled_eq = [e for _, e in eqs if count_real(clean_prose(e)) > 0 or re.search(r'[=+\-\\]', e)]
    if not filled_eq:
        errors.append('没有含真实内容的 equation/align 公式')

    tables = re.findall(r'\\begin\{(tabular\*?|table)\}(.*?)\\end\{\1\}', body, re.S)
    ok_table = False
    best_table_rows = 0
    for _, t in tables:
        rows = []
        for line in t.splitlines():
            # 去掉表格横线命令后再判断该行是否有 & 分隔的数据
            line = re.sub(r'\\(?:toprule|midrule|bottomrule|hline|cline\{[^{}]*\})', '', line)
            if '&' in line:
                rows.append(line)
        # 第一条含 & 的行按表头处理，其余才算数据行
        data = [r for r in rows[1:] if count_real(clean_prose(r)) > 0]
        best_table_rows = max(best_table_rows, len(data))
        if len(data) >= 2:
            ok_table = True
            break
    if tables and not ok_table:
        errors.append(f'表格只有表头骨架，没有真实数据行（当前最多 {best_table_rows} 行，需 >=2 行）')
    if not tables:
        warnings.append('没有表格（本题结果通常需要表格支撑）')

    # ---- 引用闭合 ----
    cites = re.findall(r'\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])?\{([^{}]*)\}', body)
    keys = []
    for c in cites:
        keys.extend([k.strip() for k in c.split(',') if k.strip()])
    if keys:
        pool = bib_text or ''
        for k in set(keys):
            if k not in pool:
                errors.append(f'引用键无法回溯: \\cite{{{k}}} 在参考文献中不存在')
    else:
        warnings.append('正文没有任何 \\cite（本题通常需要引用文献）')

    return {
        'status': 'passed' if not errors else 'failed',
        'errors': errors,
        'warnings': warnings,
        'stats': {
            'sections': len(secs),
            'total_real_chars': total,
            'section_chars': {t: count_real(clean_prose(c)) for t, c in secs},
            'cite_keys': sorted(set(keys)),
            'equations': len(eqs),
            'tables': len(tables),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tex')
    ap.add_argument('--case')
    ap.add_argument('--bib')
    ap.add_argument('--min-section-chars', type=int, default=120)
    ap.add_argument('--min-total-chars', type=int, default=400)
    ap.add_argument('--json')
    args = ap.parse_args()

    if not os.path.isfile(args.tex):
        print(json.dumps({'status': 'failed', 'errors': [f'找不到稿件: {args.tex}']}, ensure_ascii=False))
        return 1
    tex = open(args.tex, encoding='utf-8', errors='replace').read()
    case = json.load(open(args.case, encoding='utf-8')) if args.case and os.path.isfile(args.case) else None

    bib_text = ''
    for cand in [args.bib, os.path.join(os.path.dirname(os.path.abspath(args.tex)), 'refs.bib')]:
        if cand and os.path.isfile(cand):
            bib_text += open(cand, encoding='utf-8', errors='replace').read()
    if not bib_text:
        # 也接受正文内 thebibliography
        bib_text = tex

    rep = check(tex, case, bib_text, args.min_section_chars, args.min_total_chars)
    out = json.dumps(rep, ensure_ascii=False, indent=2)
    print(out)
    if args.json:
        open(args.json, 'w', encoding='utf-8').write(out)
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
