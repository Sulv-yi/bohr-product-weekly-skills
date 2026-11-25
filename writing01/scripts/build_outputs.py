#!/usr/bin/env python3
"""生成可核验附件：section-map.csv / material-index.csv / cite-audit.csv / selfcheck.md / preview.pdf。

题面把「每条事实性论断能否指回具体材料位置和具体文献条目」列为可核验性评分点。
这三张表就是那份可回查物：只把信息塞在 result.json 里，复核人要自己解析 JSON。

用法:
  python scripts/build_outputs.py --result /app/output/result.json \
      [--text /app/output/manuscript.md] --outdir /app/output
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sections_gate import measure, CITE  # noqa: E402


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def locate(sentence, text):
    if not text or not sentence:
        return ''
    if sentence.strip() in text:
        return 'verbatim'
    probe = sentence.strip()[:12]
    return 'fragment' if probe and probe in text else 'not-found'


def write_section_map(m, path):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['section', 'chars', 'min_required', 'ok'])
        for name, v in m['sections'].items():
            w.writerow([name, v['chars'], v['min'], 'yes' if v['ok'] else 'no'])


def write_index(index, text, sources, path):
    smap = {str(s.get('cite_key')): s for s in (sources or [])}
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['material_id', 'kind', 'locator', 'claim_in_manuscript', 'cite_key',
                    'evidence_quote', 'located_in_manuscript', 'ref_resolved'])
        for i, m in enumerate(index, 1):
            ck = str(m.get('cite_key') or '')
            claim = m.get('claim') or m.get('supports') or ''
            w.writerow([
                m.get('material_id') or f'm{i}',
                m.get('kind') or '',
                m.get('locator') or m.get('section') or '',
                claim,
                ck,
                (m.get('quote') or '').replace('\n', ' ')[:120],
                locate(claim, text),
                ('yes' if ck in smap else ('no-key' if not ck else 'missing')),
            ])


def write_cite_audit(text, sources, path):
    body = set()
    for grp in CITE.findall(text or ''):
        for part in grp.replace(' ', '').split(','):
            if part.isdigit():
                body.add(int(part))
    smap = {}
    for s in (sources or []):
        k = str(s.get('cite_key') or '').strip()
        if k.isdigit():
            smap[int(k)] = s
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cite_key', 'in_body', 'ref_entry', 'section', 'quote', 'resolved'])
        for k in sorted(set(body) | set(smap)):
            s = smap.get(k)
            w.writerow([k, 'yes' if k in body else 'no', 'yes' if s else 'no',
                        (s or {}).get('section') or '',
                        ((s or {}).get('quote') or '')[:100],
                        'yes' if (k in body and s) else 'no'])


def render_preview(md, outdir):
    if not md or not os.path.isfile(md):
        return 'skipped: 无 manuscript.md'
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
             f"- 稿件篇幅: {m['total_chars']} 字（门槛 {min_chars}）",
             f"- 章节齐备度: {m['section_coverage']:.0%}", '',
             '| 章节 | 字数 | 门槛 | 达标 |', '|---|---|---|---|']
    for name, v in m['sections'].items():
        lines.append(f"| {name} | {v['chars']} | {v['min']} | {'✓' if v['ok'] else '✗'} |")
    lines += ['',
              f"- 引用: 正文 {m['cite_keys']} 个编号 / 文献表 {m['ref_entries']} 条，"
              f"闭合率 {m['cite_resolved_rate']:.0%}",
              f"- 图/表: 题注与正文提及成对 {m['fig_pairs']} 图 + {m['tab_pairs']} 表；"
              f"孤立题注 图 {m['fig_orphan_caps'] or '无'} 表 {m['tab_orphan_caps'] or '无'}",
              f"- 材料索引: {m['material_index_count']} 条",
              f"- 论断句挂引用: {m['cited_sentences']}/{m['claim_sentences']}"
              f"（{m['binding_rate']:.0%}）",
              f"- 数值可回溯率: {m['num_trace_rate']:.0%}",
              f"- 声明字段: {m['declaration_fields']} 类 {m['declarations']}",
              f"- 占位符残留: {m['placeholder_count']}",
              f"- 预览: {preview}", '']
    if m['num_untraced']:
        lines += ['## 未能回溯的数值（必须核对或删除）', '']
        lines += [f"- `{n}`" for n in m['num_untraced']]
        lines.append('')
    unc = result.get('uncertainty') or []
    if unc:
        lines += ['## uncertainty', '']
        for u in unc:
            lines.append(f"- [{u.get('type')}] {u.get('note')}" if isinstance(u, dict) else f"- {u}")
        lines.append('')
    miss = [mm.get('material_id') for mm in (payload.get('material_index') or [])
            if not (mm.get('locator') or mm.get('section'))]
    if miss:
        lines += ['## 材料索引缺定位', ''] + [f"- {i}" for i in miss] + ['']
    lines += ['## 未清项处置', '',
              '门槛未过就回流程补内容（补章节、补引用、补题注、补声明），',
              '不通过改 status 绕过；补不出的写进 uncertainty 并标 partial。']
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser(description='生成 section/index/cite 三张核验表与自检表')
    ap.add_argument('--result', required=True)
    ap.add_argument('--text')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--min-chars', type=int, default=1800)
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
    sources = result.get('sources') or []
    index = payload.get('material_index') or []

    m = measure(text, result, args.min_chars)

    sec = os.path.join(args.outdir, 'section-map.csv')
    write_section_map(m, sec)
    idx = os.path.join(args.outdir, 'material-index.csv')
    write_index(index, text, sources, idx)
    cite = os.path.join(args.outdir, 'cite-audit.csv')
    write_cite_audit(text, sources, cite)
    preview = render_preview(args.text, args.outdir)
    chk = os.path.join(args.outdir, 'selfcheck.md')
    write_selfcheck(m, result, preview, chk, args.min_chars)

    print(json.dumps({'section_map': sec, 'material_index': idx, 'cite_audit': cite,
                      'selfcheck': chk, 'preview': preview,
                      'chars': m['total_chars'], 'sections': m['section_coverage'],
                      'cites': f"{m['cite_keys']}/{m['ref_entries']}",
                      'figtab': [m['fig_pairs'], m['tab_pairs']],
                      'index': m['material_index_count'],
                      'untraced': m['num_untraced'][:6]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
