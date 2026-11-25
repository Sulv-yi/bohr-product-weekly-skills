#!/usr/bin/env python3
"""生成可核验附件：term-audit.csv / align-map.csv / number-audit.csv / selfcheck.md / preview.pdf。

为什么这几张表是必须的：术语、数值、标记、边界四类改动的"可核验性"没法靠一段自述证明，
评审需要按段号逐条对照原文与译文。三张 CSV 就是这个对照入口。

用法：
  python build_outputs.py --result /app/output/result.json --text /app/output/bilingual.md \
      --outdir /app/output [--min-chars 200]
"""
import argparse
import csv
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bilingual_gate import (parse_pairs, term_check, number_check, marker_check,
                            align_check, boundary_check, placeholders_of, _nchars)  # noqa: E402


def write_csv(path, header, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def render_preview(md, outdir):
    """有 pandoc 才渲染；没有就如实返回原因，不假装渲染成功。"""
    import shutil as _sh
    if not _sh.which('pandoc'):
        return 'skipped: 环境无 pandoc'
    out = os.path.join(outdir, 'preview.pdf')
    try:
        r = subprocess.run(['pandoc', md, '-o', out, '--pdf-engine=xelatex',
                            '-V', 'CJKmainfont=SimSun'], capture_output=True, timeout=180)
        return 'ok: preview.pdf' if r.returncode == 0 else 'failed: pandoc 返回 %d' % r.returncode
    except Exception as e:  # noqa: BLE001
        return 'failed: %s' % e


def main():
    ap = argparse.ArgumentParser(description='生成术语审计 / 对齐图 / 数值台账 / 自查 / 预览')
    ap.add_argument('--result', required=True)
    ap.add_argument('--text', help='双语稿 md；缺省取 result.result.bilingual')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--min-chars', type=int, default=200)
    a = ap.parse_args()

    res = json.load(open(a.result, encoding='utf-8'))
    body = open(a.text, encoding='utf-8').read() if a.text else res['result']['bilingual']
    terms = res['result'].get('terms') or []
    pairs = parse_pairs(body)
    os.makedirs(a.outdir, exist_ok=True)

    # 1) 术语审计：术语 → 锁定译法 → 出现段 → 漂移
    cov, leak, conflict = term_check(pairs, terms)
    rows = []
    for t in terms:
        en, zh = t.get('en'), t.get('zh')
        segs = [p for p, (e, _z) in pairs.items()
                if en and en.lower() in (e or '').lower()]
        bad = [f'{p}:{v}' for p, _e, v in leak if _e == en]
        rows.append([en, zh, ' / '.join(segs) or '-', len(segs), '; '.join(bad) or 'ok',
                     '; '.join(t.get('variants') or [])])
    write_csv(os.path.join(a.outdir, 'term-audit.csv'),
              ['en', 'zh_locked', 'segments', 'hits', 'drift', 'forbidden_variants'], rows)

    # 2) 对齐图：段号 → 原文首 40 字 → 译文首 40 字 → 标记比对
    rows = []
    for pid in sorted(pairs, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
        en, zh = pairs[pid]
        rows.append([pid, (en or '')[:40], (zh or '')[:40],
                     'ok' if (en and zh) else 'MISSING',
                     len((en or '').split()), _nchars(zh or '')])
    write_csv(os.path.join(a.outdir, 'align-map.csv'),
              ['seg', 'source_head', 'target_head', 'status', 'source_words', 'target_chars'], rows)

    # 3) 数值台账：原文数值 → 值 → 单位 → 是否落地
    rows = []
    for pid in sorted(pairs, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
        en, zh = pairs[pid]
        if not en or not zh:
            continue
        _rate, _mag, _sig, nrows = number_check(en, zh)
        for raw, val, unit, ok in nrows:
            rows.append([pid, raw, val, unit or '-', 'landed' if ok else 'MISSING'])
        for raw, base in _mag:
            rows.append([pid, raw, base, '-', 'MAGNITUDE_ERROR'])
    write_csv(os.path.join(a.outdir, 'number-audit.csv'),
              ['seg', 'raw', 'value', 'unit', 'status'], rows)

    # 4) 自查
    cov_a, ordered, miss = align_check(pairs)
    overall_marker, mrows = marker_check(pairs)
    viol, hedge = boundary_check(pairs)
    tot = hit = 0
    for pid, (en, zh) in pairs.items():
        if en and zh:
            _r, _m, _s, nrows = number_check(en, zh)
            tot += len(nrows)
            hit += sum(1 for r in nrows if r[3])
    num_rate = round(hit / float(tot), 3) if tot else 1.0
    preview = render_preview(os.path.abspath(a.text), a.outdir) if a.text else 'skipped: 未提供 md'

    lines = ['# 自查（自动生成）', '',
             f"- 段数：{len(pairs)}；覆盖：{cov_a:.0%}；段序：{'保持' if ordered else '被打乱'}",
             f"- 标记保留：{overall_marker:.0%}（" +
             '；'.join(f'{k} {v[0]}/{v[1]}' for k, v in mrows.items()) + '）',
             f"- 术语落地：{cov:.0%}；漂移：{len(leak)} 处；术语表矛盾：{len(conflict)} 条",
             f"- 数值落地：{num_rate:.0%}（{hit}/{tot}）",
             f"- 边界改动：{len(viol)} 条；模糊限制语保留：{hedge:.0%}",
             f"- 译文字数：{_nchars(' '.join(z for _e, z in pairs.values()))}；"
             f"占位符：{len(placeholders_of(body))}",
             f"- 预览：{preview}", '']
    if leak:
        lines += ['## 术语漂移', ''] + [f"- {p} · {en} · 出现 `{v}`" for p, en, v in leak] + ['']
    if viol:
        lines += ['## 边界改动', ''] + [f"- {p} · {k} · {d}" for p, k, d in viol] + ['']
    if miss:
        lines += ['## 漏译段', ''] + [f"- {p}" for p in miss] + ['']
    chk = os.path.join(a.outdir, 'selfcheck.md')
    open(chk, 'w', encoding='utf-8').write('\n'.join(lines))

    print(json.dumps({'term_audit': os.path.join(a.outdir, 'term-audit.csv'),
                      'align_map': os.path.join(a.outdir, 'align-map.csv'),
                      'number_audit': os.path.join(a.outdir, 'number-audit.csv'),
                      'selfcheck': chk, 'preview': preview,
                      'segments': len(pairs), 'pair_coverage': cov_a,
                      'marker_keep': overall_marker, 'term_coverage': cov,
                      'term_leak': len(leak), 'number_transfer_rate': num_rate,
                      'boundary_violation': len(viol), 'hedge_alignment': hedge},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
