#!/usr/bin/env python3
"""把引用记录落成可复核的附件：citation-map.csv + selfcheck.md（+ 稿件预览）。

产物（默认 /app/output）：
  citation-map.csv  逐条 cite_id → 论断原文 → 位置 → 文献键 → 匹配依据 → 位置是否成立
  selfcheck.md      四性质（挂得对/编得顺/收得净/对得上）的度量、未清项、待确认
  preview.pdf       有 pandoc 时渲染稿件，供目视检查引用标记与编号

为什么单列：题面要求"每条引用能否回到来源、去重依据与格式映射能否被独立复核"。
把 result.json 里的 citations 摊成一行一条的 CSV，复核人不必解析 JSON 就能逐条打勾。

用法:
  python build_outputs.py --result /app/output/result.json --outdir /app/output \
      [--manuscript /app/output/manuscript.md]
退出码 0=已生成；2=输入缺失。
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from citation_gate import measure  # noqa: E402

COLS = ['cite_id', 'claim', 'claim_location', 'ref_key', 'match_basis', 'strength', 'position_ok']


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def rows_of(result):
    res = result.get('result') or {}
    cites = res.get('citations') if isinstance(res.get('citations'), list) else []
    rows = []
    for i, c in enumerate(cites):
        if not isinstance(c, dict):
            continue
        match = c.get('match') if isinstance(c.get('match'), dict) else {}
        rows.append({
            'cite_id': c.get('cite_id') or f'c{i + 1}',
            'claim': str(c.get('claim') or '').replace('\n', ' ')[:200],
            'claim_location': c.get('claim_location') or '',
            'ref_key': c.get('ref_key') or c.get('ref_id') or '',
            'match_basis': str(match.get('match_basis') or '').replace('\n', ' ')[:200],
            'strength': match.get('strength') or '',
            'position_ok': c.get('position_ok'),
        })
    return rows


def render(manuscript, outdir):
    pdf = os.path.join(outdir, 'preview.pdf')
    pandoc = shutil.which('pandoc')
    if pandoc and manuscript and os.path.isfile(manuscript):
        try:
            subprocess.run([pandoc, manuscript, '-o', pdf, '-V', 'CJKmainfont=Noto Sans CJK SC'],
                           check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.isfile(pdf) and os.path.getsize(pdf) > 0:
                return pdf
        except Exception:
            pass
    return None


def unresolved(m, result):
    res = result.get('result') or {}
    out = []
    if m['cite_count'] == 0:
        out.append('citations 为空：没有任何逐条引用记录')
    if m['claim_rate'] < 1.0:
        out.append(f'{m["cite_count"] - round(m["claim_rate"] * m["cite_count"])} 条引用缺论断原文')
    if m['claim_location_rate'] < 1.0:
        out.append(f'位置未精确到句的引用占 {(1 - m["claim_location_rate"]):.0%}')
    if m['match_basis_rate'] < 1.0:
        out.append(f'缺 match_basis 的引用占 {(1 - m["match_basis_rate"]):.0%}（须逐条说明为何该文献支撑这句话）')
    if m['position_ok_rate'] < 1.0:
        out.append(f'position_ok 为假的引用占 {(1 - m["position_ok_rate"]):.0%}')
    if not m['numbering_continuous']:
        out.append('编号不连续')
    if m['dangling_count']:
        out.append(f'悬空引用 {m["dangling_count"]} 处')
    if m['dedup_merged'] and m['dedup_merged_basis_rate'] < 1.0:
        out.append('合并条目有缺判据的')
    if m['dedup_pending'] and m['dedup_pending_reason_rate'] < 1.0:
        out.append('pending 条目有缺原因的')
    if m['format_mapping_fields'] == 0:
        out.append('format_conversion.field_mapping 为空')
    if not m['manuscript_delivered']:
        out.append('未交付可编辑稿件（manuscript_text / manuscript_path 均空）')
    if m['placeholder_count']:
        out.append(f'残留占位符 {m["placeholder_count"]} 处')
    if (m['dedup_merged'] + m['dedup_kept'] + m['dedup_pending']) == 0:
        out.append('去重三类的判断都为空：若文献库确无重复，需在 uncertainty 说明')
    return out


def write_selfcheck(m, result, rows, preview, outdir):
    errs = unresolved(m, result)
    lines = ['# 引用管理自检表（结构度量，非自评分）', '',
             '> 由 `scripts/build_outputs.py` 依据 result.json 计算，可用同一输入重跑。',
             '> 下列指标只说明"记录是否齐备、是否可逐条复核"，论断与文献是否真的对得上，仍需人对着原文读。', '',
             '## 1. 四性质指标', '', '| 性质 | 指标 | 值 | 门槛 | 判定 |', '|---|---|---|---|---|']

    def row(prop, name, val, gate, ok):
        lines.append(f'| {prop} | {name} | {val} | {gate} | {"通过" if ok else "未达"} |')

    row('挂得对', '引用条数', m['cite_count'], '≥1', m['cite_count'] >= 1)
    row('挂得对', '论断原文覆盖', f"{m['claim_rate']:.0%}", '100%', m['claim_rate'] >= 1.0)
    row('挂得对', '位置精确到句', f"{m['claim_location_rate']:.0%}", '100%', m['claim_location_rate'] >= 1.0)
    row('挂得对', '匹配依据齐备', f"{m['match_basis_rate']:.0%}", '100%', m['match_basis_rate'] >= 1.0)
    row('挂得对', '位置成立（自报）', f"{m['position_ok_rate']:.0%}", '100%', m['position_ok_rate'] >= 1.0)
    row('编得顺', '编号连续', '是' if m['numbering_continuous'] else '否', '是', m['numbering_continuous'])
    row('编得顺', '悬空引用', m['dangling_count'], '0', m['dangling_count'] == 0)
    row('编得顺', '未引用条目', m['uncited_count'], '如实列出', True)
    row('收得净', '合并/分开/待定', f"{m['dedup_merged']}/{m['dedup_kept']}/{m['dedup_pending']}", '如实判定', True)
    row('收得净', '合并带判据', f"{m['dedup_merged_basis_rate']:.0%}" if m['dedup_merged'] else '无合并', '100%',
        (not m['dedup_merged']) or m['dedup_merged_basis_rate'] >= 1.0)
    row('对得上', '文献键可回溯', f"{m['ref_resolved_rate']:.0%}", '100%', m['ref_resolved_rate'] >= 1.0)
    row('对得上', '字段映射条数', m['format_mapping_fields'], '≥1', m['format_mapping_fields'] >= 1)
    row('对得上', '关键字段保留', m['preserved_fields'], '≥1', m['preserved_fields'] >= 1)
    row('交付', '可编辑稿件', '有' if m['manuscript_delivered'] else '无', '有', m['manuscript_delivered'])

    lines += ['', '## 2. 未清项', '']
    lines += [f'- {e}' for e in errs] if errs else ['- 无']
    lines += ['', '## 3. 逐条引用定位', '',
              f'共 {len(rows)} 条，见 `citation-map.csv`（{"/".join(COLS)}）。',
              '复核方式：对着稿件找到 claim_location 那一句，读 match_basis 判断这篇文献是否真的支撑它。', '']
    lines += ['', '## 4. 预览', '']
    if preview:
        lines.append('- `preview.pdf` 已生成，可直接目视检查引用标记与编号。')
    else:
        lines.append('- 未生成 PDF 预览（环境无 pandoc 或未提供稿件路径）；需在 uncertainty 标 not_reported。')
    unc = result.get('uncertainty') or []
    lines += ['', '## 5. 已登记的边界与待确认', '']
    lines += [f"- [{u.get('type', '?') if isinstance(u, dict) else '?'}] "
              f"{u.get('note', '') if isinstance(u, dict) else u}" for u in unc] or ['- 无']
    path = os.path.join(outdir, 'selfcheck.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return path, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', default='/app/output/result.json')
    ap.add_argument('--outdir', default='/app/output')
    ap.add_argument('--manuscript')
    ap.add_argument('--no-preview', action='store_true')
    args = ap.parse_args()
    if not os.path.isfile(args.result):
        print(json.dumps({'error': 'result not found', 'path': args.result}, ensure_ascii=False))
        return 2
    result = load(args.result)
    os.makedirs(args.outdir, exist_ok=True)

    rows = rows_of(result)
    csv_path = os.path.join(args.outdir, 'citation-map.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    ms = args.manuscript or str((result.get('result') or {}).get('manuscript_path') or '')
    preview = None if args.no_preview else render(ms, args.outdir)
    m = measure(result)
    md_path, errs = write_selfcheck(m, result, rows, preview, args.outdir)
    print(json.dumps({'ok': not errs, 'citation_map': csv_path, 'selfcheck': md_path,
                      'preview': preview, 'unresolved': errs, 'metrics': m},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
