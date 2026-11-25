#!/usr/bin/env python3
"""生成结果与讨论章节的可核验附件：figure-audit.csv / claim-map.csv / selfcheck.md / preview.pdf。

题面把「每个数值能否回溯到某张图、某张表或某份统计输出」列为可核验性评分点。
`figure-audit.csv` 就是那份回溯表：正文出现的每个数值，对应到哪张图表、哪个值。

用法:
  python scripts/build_outputs.py --result /app/output/result.json \
      [--text /app/output/chapter.md] --outdir /app/output
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from results_gate import measure, NUM_U, _norm  # noqa: E402


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def pool_of(figure_data):
    """把 figure_data 摊平成 {数值字符串: [来源标签]}。"""
    pool = {}
    for item in (figure_data or []):
        tag = item.get('fig_id') or item.get('label') or 'figure'
        for k, v in (item.get('values') or {}).items():
            pool.setdefault(str(v), []).append(f'{tag}:{k}')
        for grp in (item.get('series') or []):
            for i, v in enumerate(grp.get('y') or []):
                pool.setdefault(str(v), []).append(f"{tag}:{grp.get('name') or 'y'}[{i}]")
    return pool


def write_figure_audit(text, figure_data, path):
    pool = pool_of(figure_data)
    nums = sorted({re.sub(r'\s', '', m) for m in NUM_U.findall(text or '')})
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['value_in_text', 'found_in_figure_data', 'sources', 'count_in_text'])
        for n in nums:
            key = _norm(n)
            hits = [k for k in pool if _norm(k) == key]
            src = sorted({s for k in hits for s in pool[k]})
            w.writerow([n, 'yes' if hits else 'no', '; '.join(src) or '-',
                        (text or '').count(n)])


def write_claim_map(figure_data, path):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['fig_id', 'caption', 'n', 'error_bar', 'stat', 'values'])
        for item in (figure_data or []):
            vals = item.get('values') or {}
            flat = '; '.join(f'{k}={v}' for k, v in vals.items())
            for grp in (item.get('series') or []):
                flat += f"; {grp.get('name') or 'y'}={grp.get('y')}"
            w.writerow([item.get('fig_id') or '', item.get('caption') or '',
                        item.get('n') or '', item.get('error_bar') or '',
                        item.get('stat') or '', flat[:300]])


def render_preview(md, outdir):
    if not md or not os.path.isfile(md):
        return 'skipped: 无 chapter.md'
    if not shutil.which('pandoc'):
        return 'skipped: 环境无 pandoc'
    out = os.path.join(outdir, 'preview.pdf')
    try:
        r = subprocess.run(['pandoc', md, '-o', out, '--pdf-engine=xelatex',
                            '-V', 'CJKmainfont=Noto Sans CJK SC'],
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and os.path.isfile(out):
            return 'ok: preview.pdf'
        return 'failed: ' + (r.stderr or '').strip().split('\n')[0][:160]
    except Exception as e:  # noqa: BLE001
        return f'failed: {type(e).__name__}'


def write_selfcheck(m, result, preview, path, min_chars):
    payload = result.get('result') or {}
    lines = ['# 自检表（脚本生成，非自评分）', '',
             f"- case: `{result.get('case_id')}`  status: **{result.get('status')}**",
             f"- 篇幅: {m['total_chars']} 字（门槛 {min_chars}）；"
             f"结果段 {m['results_chars']}、讨论段 {m['discussion_chars']}、局限 {m['limitation_chars']}",
             f"- 图表数据行: {m['figure_rows']}",
             f"- 结果段数值与图表一致率: {m['fig_number_rate']:.0%}",
             f"- 显著性表述 {m['stats_claims']} 句，带统计量 {m['stats_support']:.0%}",
             f"- 结果段解释性句子: {m['leakage']}（上限 2）",
             f"- 趋势边界表述: {'有' if m['trend_boundary'] else '**无**'}",
             f"- 论断句挂引用/图表编号: {m['binding_rate']:.0%}",
             f"- 局限具体线索: {m['limitation_markers']} 条；套话 {m['limitation_vague'] or '无'}",
             f"- 占位符残留: {m['placeholder_count']}",
             f"- 预览: {preview}", '']
    if m['fig_numbers_untraced']:
        lines += ['## 未能回溯到图表的数值（必须核对或删除）', '']
        lines += [f"- `{n}`" for n in m['fig_numbers_untraced']]
        lines.append('')
    if m['stats_unsupported']:
        lines += ['## 有"显著"但无统计量的句子（补检验或降表述）', '']
        lines += [f"- {s}" for s in m['stats_unsupported']]
        lines.append('')
    if m['leakage_samples']:
        lines += ['## 结果段里的解释性句子（应移到讨论）', '']
        lines += [f"- {s}" for s in m['leakage_samples']]
        lines.append('')
    unc = result.get('uncertainty') or []
    if unc:
        lines += ['## uncertainty', '']
        for u in unc:
            lines.append(f"- [{u.get('type')}] {u.get('note')}" if isinstance(u, dict) else f"- {u}")
        lines.append('')
    missing_n = [f.get('fig_id') for f in (payload.get('figure_data') or []) if not f.get('n')]
    if missing_n:
        lines += ['## 缺样本量 n 的图表', ''] + [f"- {i}" for i in missing_n] + ['']
    lines += ['## 未清项处置', '',
              '门槛未过就回流程补图表数据、补统计量或降表述强度，不改 status 绕过。']
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser(description='生成图表审计表与自检表')
    ap.add_argument('--result', required=True)
    ap.add_argument('--text')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--min-chars', type=int, default=1200)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    result = load(args.result, {})
    text = ''
    if args.text and os.path.isfile(args.text):
        with open(args.text, encoding='utf-8') as f:
            text = f.read()
    payload = result.get('result') or {}
    if not text:
        text = payload.get('manuscript') or ''
    fd = payload.get('figure_data') or []

    m = measure(text, result, args.min_chars)
    audit = os.path.join(args.outdir, 'figure-audit.csv')
    write_figure_audit(text, fd, audit)
    cmap = os.path.join(args.outdir, 'claim-map.csv')
    write_claim_map(fd, cmap)
    preview = render_preview(args.text, args.outdir)
    chk = os.path.join(args.outdir, 'selfcheck.md')
    write_selfcheck(m, result, preview, chk, args.min_chars)

    print(json.dumps({'figure_audit': audit, 'claim_map': cmap, 'selfcheck': chk,
                      'preview': preview, 'chars': m['total_chars'],
                      'fig_number_rate': m['fig_number_rate'],
                      'stats_support': m['stats_support'],
                      'leakage': m['leakage'],
                      'untraced': m['fig_numbers_untraced'][:6]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
