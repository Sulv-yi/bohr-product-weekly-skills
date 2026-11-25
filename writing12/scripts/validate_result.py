#!/usr/bin/env python3
"""契约层 + 门槛层：结果 JSON 结构不对直接拒，度量不达标不判 success。

用法：
  python validate_result.py /app/output/result.json --case /input/case.json --text /app/output/bilingual.md
  python validate_result.py ... --json     # 只输出度量，不打印人话

退出码：0 通过；1 结构错；2 门槛未达。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bilingual_gate import (parse_pairs, term_check, number_check, marker_check,
                            align_check, boundary_check, placeholders_of,
                            _nchars)  # noqa: E402

REQUIRED_RESULT = ['bilingual', 'terms']
REQUIRED_TOP = ['case_id', 'status', 'result', 'sources', 'uncertainty', 'changes']

GATE_PAIR = 0.95
GATE_MARKER = 0.9
GATE_TERM = 0.95
GATE_NUMBER = 0.95
GATE_HEDGE = 0.8
GATE_RATIO = 1.2      # 英译中「字/词」比的下限：实际常用 1.5–1.8，1.2 以下就是漏译
MIN_TARGET_CHARS = 200
MAX_BOUNDARY = 1


def measure(result, case=None, text=None):
    r = result.get('result') or {}
    body = text if text else (r.get('bilingual') or '')
    pairs = parse_pairs(body)
    terms = r.get('terms') or []
    expect = None
    if case:
        expect = case.get('segments') or (case.get('input') or {}).get('segments')

    cov, ordered, miss = align_check(pairs, expect)
    t_cov, leak, conflict = term_check(pairs, terms)
    overall_marker, marker_rows = marker_check(pairs)
    viol, hedge = boundary_check(pairs)

    n_hit = n_all = 0
    mag_all, sig_all = [], 0
    # 逐段数值落地，最后按"原文数值个数"加权，避免长短段等权
    tot_n = hit_n = 0
    for pid, (en, zh) in pairs.items():
        if not en or not zh:
            continue
        _rate, _mag, _sig, rows = number_check(en, zh)
        tot_n += len(rows)
        hit_n += sum(1 for _r in rows if _r[3])
        mag_all += [(pid,) + tuple(m) for m in _mag]
        sig_all += _sig
    num_rate = round(hit_n / float(tot_n), 3) if tot_n else 1.0

    zh_chars = _nchars(' '.join(z for _e, z in pairs.values()))
    en_words = len(re.findall(r'[A-Za-z][A-Za-z\-]+', ' '.join(e for e, _z in pairs.values())))
    return {
        'segments': len(pairs),
        'pair_coverage': cov,
        'order_preserved': ordered,
        'missing_segments': miss,
        'marker_keep': overall_marker,
        'marker_rows': marker_rows,
        'term_coverage': t_cov,
        'term_variant_leak': len(leak),
        'term_leak_rows': leak,
        'term_conflict': len(conflict),
        'number_transfer_rate': num_rate,
        'numbers_total': tot_n,
        'magnitude_errors': len(mag_all),
        'sigfig_loss': sig_all,
        'boundary_violation': len(viol),
        'boundary_rows': viol,
        'hedge_alignment': hedge,
        'target_chars': zh_chars,
        'source_words': en_words,
        'length_ratio': round(zh_chars / float(en_words), 2) if en_words else 0.0,
        'placeholder_count': len(placeholders_of(body)),
    }


def gate(m):
    fails = []
    if m['pair_coverage'] < GATE_PAIR:
        fails.append(f"对得齐：段覆盖 {m['pair_coverage']:.0%} < {GATE_PAIR:.0%}，缺 {m['missing_segments']}")
    if not m['order_preserved']:
        fails.append('对得齐：段序被打乱')
    if m['marker_keep'] < GATE_MARKER:
        fails.append(f"对得齐：标记保留 {m['marker_keep']:.0%} < {GATE_MARKER:.0%}")
    if m['term_coverage'] < GATE_TERM:
        fails.append(f"术语稳：锁定译法落地 {m['term_coverage']:.0%} < {GATE_TERM:.0%}")
    if m['term_conflict']:
        fails.append(f"术语稳：术语表自相矛盾 {m['term_conflict']} 条")
    if m['number_transfer_rate'] < GATE_NUMBER:
        fails.append(f"数字实：数值落地 {m['number_transfer_rate']:.0%} < {GATE_NUMBER:.0%}")
    if m['magnitude_errors']:
        fails.append(f"数字实：量级错配 {m['magnitude_errors']} 条")
    if m['boundary_violation'] > MAX_BOUNDARY:
        fails.append(f"边界清：语义边界改动 {m['boundary_violation']} 条 > {MAX_BOUNDARY}")
    if m['hedge_alignment'] < GATE_HEDGE:
        fails.append(f"边界清：模糊限制语保留 {m['hedge_alignment']:.0%} < {GATE_HEDGE:.0%}")
    if m['target_chars'] < MIN_TARGET_CHARS:
        fails.append(f"篇幅：译文 {m['target_chars']} 字 < {MIN_TARGET_CHARS}")
    elif m['length_ratio'] < GATE_RATIO:
        fails.append(f"篇幅：译文/原文 {m['length_ratio']} 字每词 < {GATE_RATIO}（疑似漏译或过度省译）")
    if m['placeholder_count']:
        fails.append(f"干净度：占位符 {m['placeholder_count']} 处")
    return fails


def main():
    global MIN_TARGET_CHARS
    ap = argparse.ArgumentParser(description='双语稿门槛校验')
    ap.add_argument('result')
    ap.add_argument('--case')
    ap.add_argument('--text')
    ap.add_argument('--min-chars', type=int, default=MIN_TARGET_CHARS)
    ap.add_argument('--out')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    res = json.load(open(a.result, encoding='utf-8'))
    case = json.load(open(a.case, encoding='utf-8')) if a.case else None
    text = open(a.text, encoding='utf-8').read() if a.text else None

    missing = [k for k in REQUIRED_TOP if k not in res]
    missing += [k for k in REQUIRED_RESULT if k not in (res.get('result') or {})]
    if missing:
        print('结构错误：缺字段 ' + ', '.join(missing))
        return 1

    m = measure(res, case, text)
    if a.min_chars != MIN_TARGET_CHARS:
        MIN_TARGET_CHARS = a.min_chars
    fails = gate(m)

    if a.out:
        json.dump(m, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if a.json:
        print(json.dumps(m, ensure_ascii=False, indent=1))
        return 0 if not fails else 2

    print(('passed ' if not fails else 'failed ') + f"case={res.get('case_id')} status={res.get('status')}")
    print(f"  段={m['segments']} 覆盖={m['pair_coverage']:.0%} 标记={m['marker_keep']:.0%} "
          f"术语落地={m['term_coverage']:.0%} 漂移={m['term_variant_leak']} "
          f"数值={m['number_transfer_rate']:.0%} 量级错={m['magnitude_errors']} "
          f"边界改动={m['boundary_violation']} 限制语={m['hedge_alignment']:.0%} "
          f"译文字数={m['target_chars']}")
    for f in fails:
        print('  [fail] ' + f)
    return 0 if not fails else 2


if __name__ == '__main__':
    sys.exit(main())
