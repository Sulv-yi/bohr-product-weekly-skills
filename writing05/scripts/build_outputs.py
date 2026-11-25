#!/usr/bin/env python3
"""生成可核验附件：claim-map.csv / evidence-table.md / selfcheck.md / preview.pdf。

为什么单独一步：题面把「论断编号、原文摘录、定位信息与强度理由能否被独立复核」
列为结果可核验性的评分点。这些附件就是那份可复核物，不能靠正文自述代替。

用法:
  python scripts/build_outputs.py --result /app/output/result.json \
      [--draft /app/output/draft.md] --outdir /app/output
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
from evidence_gate import measure  # noqa: E402
from claim_split import hedge_ok  # noqa: E402


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def locate(sentence, draft):
    """论断原句是否能在成稿里定位（整句优先，退化为前 12 字的片段）。"""
    if not draft or not sentence:
        return ''
    if sentence.strip() and sentence.strip() in draft:
        return 'verbatim'
    probe = sentence.strip()[:12]
    if probe and probe in draft:
        return 'fragment'
    return 'not-found'


def write_claim_map(claims, table, draft, path):
    by_claim = {}
    for r in table:
        by_claim.setdefault(r.get('claim_id'), []).append(r)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['claim_id', 'claim', 'locator', 'strength', 'strength_basis',
                    'hedge_ok', 'evidence_ids', 'evidence_count', 'draft_located'])
        for c in claims:
            cid = c.get('claim_id') or ''
            ev = by_claim.get(cid, [])
            ok, _ = hedge_ok(c.get('strength'), c.get('claim') or '')
            w.writerow([
                cid,
                (c.get('claim') or '').replace('\n', ' '),
                c.get('locator') or c.get('section') or c.get('page') or '',
                c.get('strength') or '',
                '; '.join(c.get('strength_basis') or []),
                'yes' if ok else 'no',
                '|'.join(str(e.get('evidence_id') or '') for e in ev),
                len(ev),
                locate(c.get('claim') or '', draft),
            ])


def write_evidence_table(table, path):
    lines = ['# 证据表', '',
             '每条论断对应到具体来源、原文摘录与定位。等级由研究设计与样本线索推出，',
             '`basis` 列写明触发依据；命中不了线索的写 `insufficient`，不猜中间档。', '',
             '| 证据编号 | 论断编号 | 来源 | 原文摘录 | 定位 | 设计与样本依据 | 证据等级 | 与论断的关系 |',
             '|---|---|---|---|---|---|---|---|']
    for r in table:
        lines.append('| {} | {} | {} | {} | {} | {} | {} | {} |'.format(
            r.get('evidence_id') or '', r.get('claim_id') or '',
            (r.get('source') or r.get('ref') or ''),
            (r.get('quote') or '').replace('|', '\\|').replace('\n', ' ')[:120],
            r.get('locator') or '',
            '; '.join(r.get('basis') or []) or '',
            r.get('strength') or '',
            r.get('relation') or 'supports'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def render_preview(md_path, outdir):
    """有 pandoc/xelatex 才渲染；没有就如实返回原因，不假装渲染成功。"""
    if not md_path or not os.path.isfile(md_path):
        return 'skipped: 无 draft.md'
    if not shutil.which('pandoc'):
        return 'skipped: 环境无 pandoc'
    out = os.path.join(outdir, 'preview.pdf')
    try:
        r = subprocess.run(['pandoc', md_path, '-o', out, '--pdf-engine=xelatex',
                            '-V', 'CJKmainfont=Noto Sans CJK SC'],
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and os.path.isfile(out):
            return 'ok: preview.pdf'
        return 'failed: ' + (r.stderr or '').strip().split('\n')[0][:160]
    except Exception as e:  # noqa: BLE001
        return f'failed: {type(e).__name__}'


def write_selfcheck(m, result, claims, table, preview, path, min_chars):
    payload = result.get('result') or {}
    lines = ['# 自检表（脚本生成，非自评分）', '',
             f"- case: `{result.get('case_id')}`  status: **{result.get('status')}**",
             f"- 成稿篇幅: {m['total_chars']} 字（门槛 {min_chars}）",
             f"- 论断清单: {m['claims_count']} 条；成稿论断单元: {m['draft_units']}；"
             f"覆盖 {m['claim_coverage']:.0%}",
             f"- 精确定位率: {m['locator_rate']:.0%}；强度判定率: {m['strength_rate']:.0%}；"
             f"表述相称率: {m['hedge_alignment']:.0%}",
             f"- 证据表: {m['evidence_rows']} 行，覆盖论断 {m['evidence_claim_coverage']:.0%}",
             f"- 来源: {m['source_count']} 条，元数据齐备率 {m['source_metadata_rate']:.0%}",
             f"- 冲突证据处置: {'已列出/已说明' if m['conflict_handled'] else '**未处理**'}",
             f"- 占位符残留: {m['placeholder_count']}",
             f"- 预览: {preview}", '']

    pend = [c.get('claim_id') for c in claims if c.get('flags')]
    if pend:
        lines += ['## 待人工确认', ''] + [f"- {i}" for i in pend] + ['']
    miss = [c.get('claim_id') for c in claims
            if c.get('claim_id') not in {r.get('claim_id') for r in table}]
    if miss:
        lines += ['## 无证据行的论断（必须补或删）', ''] + [f"- {i}" for i in miss] + ['']
    conf = payload.get('conflicts') or []
    if conf:
        lines += ['## 冲突证据', '']
        for c in conf:
            lines.append(f"- {c.get('claim_id', '-')}: {c.get('note') or c}")
        lines.append('')
    elif payload.get('conflict_search_note'):
        lines += ['## 冲突证据', '', payload['conflict_search_note'], '']
    unc = result.get('uncertainty') or []
    if unc:
        lines += ['## uncertainty', '']
        for u in unc:
            if isinstance(u, dict):
                lines.append(f"- [{u.get('type')}] {u.get('note')}")
            else:
                lines.append(f"- {u}")
        lines.append('')
    lines += ['## 未清项处置', '',
              '门槛未过就回流程第 4 步补内容（补证据、补定位、降表述强度），',
              '不通过改 status 绕过；确实补不出的写入 uncertainty 并标 partial。']
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser(description='生成 claim-map / evidence-table / selfcheck / preview')
    ap.add_argument('--result', required=True)
    ap.add_argument('--draft')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--min-chars', type=int, default=1400)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    result = load(args.result, {})
    draft = ''
    if args.draft and os.path.isfile(args.draft):
        with open(args.draft, encoding='utf-8') as f:
            draft = f.read()
    payload = result.get('result') or {}
    claims = payload.get('claims') or []
    table = payload.get('evidence_table') or []

    m = measure(draft or (payload.get('draft') or ''), result, args.min_chars)

    cmap = os.path.join(args.outdir, 'claim-map.csv')
    write_claim_map(claims, table, draft, cmap)
    etab = os.path.join(args.outdir, 'evidence-table.md')
    write_evidence_table(table, etab)
    preview = render_preview(args.draft, args.outdir)
    chk = os.path.join(args.outdir, 'selfcheck.md')
    write_selfcheck(m, result, claims, table, preview, chk, args.min_chars)

    print(json.dumps({'claim_map': cmap, 'evidence_table': etab, 'selfcheck': chk,
                      'preview': preview,
                      'claims': len(claims), 'evidence_rows': len(table),
                      'chars': m['total_chars'], 'placeholder': m['placeholder_count']},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
