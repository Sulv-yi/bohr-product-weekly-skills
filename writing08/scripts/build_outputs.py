#!/usr/bin/env python3
"""把成稿与来源映射落成「可被别人复核」的三件附加产物，并给出结构自检表。

产物（都在 --outdir，默认 /app/output）：
  source-map.csv   逐条 claim → file/page/section/quote → 出现在哪一段
  selfcheck.md     结构指标 + 门槛判定 + 未清项（给作者与复核人看，不是自评分）
  preview.pdf      若环境有 pandoc 或 xelatex，把 draft.md 渲染成可目视的预览

为什么要单独落这三件：题面要求「每条引用能否回到来源、分组依据与贡献对照能否被独立复核」。
只把信息塞在 result.json 里，复核人要自己解析 JSON；落成 CSV 与自检表后，
一条命令就能对着原文核，且不改动成稿本体。

用法:
  python build_outputs.py --draft /app/output/draft.md --result /app/output/result.json \
      --outdir /app/output
退出码 0=产物已生成；2=输入缺失。
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quality_gate import measure, find_parts, split_sections  # noqa: E402

PART_ZH = {'background': '研究背景', 'related_work': '相关工作',
           'gap': '研究空白', 'contributions': '贡献表述'}


def load_result(path):
    if not path or not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def locate_quotes(draft, sources):
    """把每条 source 定位到正文：先按引用编号 [n] 找，再按 quote 首 12 字找。

    顺序不能反：sources 的 quote 是**来源原文**里的话，正文引用的是编号，
    quote 通常不出现在正文中；只按 quote 匹配会把所有来源都判成「未定位」。
    """
    parts = find_parts(draft)
    spans = [(key, body) for key, (_t, body) in parts.items()]
    flat = re.sub(r'\s+', '', draft)
    rows = []
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            continue
        quote = (s.get('quote') or '').strip()
        key = str(s.get('cite_key') or '').strip()
        cands = [k for k in (key, re.sub(r'\D', '', str(s.get('id') or '')), str(i + 1)) if k]
        where = ''
        for c in cands:
            pat = r'\[' + re.escape(c) + r'(?:\s*[,\-–]\s*\d+)*\]'
            if re.search(pat, draft):
                hits = [PART_ZH.get(name, name) for name, body in spans if re.search(pat, body)]
                where = ' / '.join(dict.fromkeys(hits)) or '正文（未落在四要素小节）'
                break
        loc = str(s.get('locator') or '').strip()
        if not where and loc and loc in draft:
            for name, body in spans:
                if loc in body:
                    where = PART_ZH.get(name, name) + f'（按 locator {loc}）'
                    break
            if not where:
                where = f'正文（locator {loc}）'
        if not where and quote:
            probe = re.sub(r'\s+', '', quote)[:12]
            if probe and probe in flat:
                for name, body in spans:
                    if probe in re.sub(r'\s+', '', body):
                        where = PART_ZH.get(name, name) + '（按引文命中）'
                        break
        rows.append({
            'source_id': s.get('id') or f'S{i + 1}',
            'claim': (s.get('claim') or '').replace('\n', ' ')[:160],
            'file': s.get('file') or '',
            'page': s.get('page') or '',
            'section': s.get('section') or '',
            'quote': quote.replace('\n', ' ')[:160],
            'used_in': where or '未在正文定位（需核对）',
        })
    return rows


def write_csv(rows, path):
    cols = ['source_id', 'claim', 'file', 'page', 'section', 'quote', 'used_in']
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def render_preview(draft, outdir):
    """尽力渲染预览：pandoc 优先，其次 xelatex（仅对 .tex），都没有就如实说明。"""
    pdf = os.path.join(outdir, 'preview.pdf')
    pandoc = shutil.which('pandoc')
    if pandoc:
        for engine_extra in (['--pdf-engine=xelatex'], []):
            try:
                subprocess.run([pandoc, draft, '-o', pdf, '-V', 'CJKmainfont=Noto Sans CJK SC']
                               + engine_extra, check=True, timeout=180,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.isfile(pdf) and os.path.getsize(pdf) > 0:
                    return pdf, 'pandoc'
            except Exception:
                continue
    return None, 'unavailable'


def write_selfcheck(m, result, rows, preview, outdir, min_chars):
    errs = []
    if not m['min_chars_ok']:
        errs.append(f'篇幅不足：中文 {m["cjk_chars"]} 字 / 英文 {m["en_words"]} 词'
                    f'（门槛：中文 1600 字或英文 1000 词）')
    if m['missing_parts']:
        errs.append('四要素缺件: ' + ', '.join(m['missing_parts']))
    if m['related_groups'] < 3:
        errs.append(f'相关工作仅 {m["related_groups"]} 组，需 ≥3 组')
    if m['contributions'] < 3:
        errs.append(f'贡献仅 {m["contributions"]} 条，需 ≥3 条')
    if m['source_count'] < 4:
        errs.append(f'sources 仅 {m["source_count"]} 条，需 ≥4 条')
    if m['placeholder_count']:
        errs.append(f'残留占位符 {m["placeholder_count"]} 处')
    unlocated = [r['source_id'] for r in rows if r['used_in'].startswith('未在正文')]
    if unlocated:
        errs.append('以下来源未在正文定位: ' + ', '.join(unlocated))

    lines = ['# 成稿自检表（结构度量，非自评分）', '',
             '> 本表由 `scripts/build_outputs.py` 依据成稿与 result.json 计算，可被任何人用同一输入重跑。',
             '> 通过本表只说明结构达标，不代表内容正确；内容正确性需作者与复核人对着来源逐条核。', '',
             '## 1. 结构指标', '',
             '| 指标 | 值 | 门槛 | 判定 |', '|---|---|---|---|']
    def row(name, val, gate, ok):
        lines.append(f'| {name} | {val} | {gate} | {"通过" if ok else "未达"} |')

    row('正文篇幅（中文计字 / 英文计词）', f'中 {m["cjk_chars"]} 字 / 英 {m["en_words"]} 词',
        '中文≥1600 字 或 英文≥1000 词', m['min_chars_ok'])
    row('四要素覆盖', f"{m['four_part_coverage']:.0%}", '100%', m['four_part_coverage'] >= 1.0)
    for k, v in m['section_chars'].items():
        row(f'　{PART_ZH.get(k, k)} 字数', v, '背景≥240 / 相关工作≥300 / 空白≥120 / 贡献≥120',
            bool(m['section_min_ok'].get(k)))
    row('相关工作分组数', m['related_groups'], '≥3', m['related_groups'] >= 3)
    row('贡献条数', m['contributions'], '≥3', m['contributions'] >= 3)
    row('贡献带证据定位比例', f"{m['contribution_evidence_rate']:.0%}", '100%', m['contribution_evidence_rate'] >= 1.0)
    row('论断-引用绑定率', f"{m['claim_binding_rate']:.0%}", '≥30%', m['claim_binding_rate'] >= 0.3)
    row('空白推导链', '有' if m['gap_chain_present'] else '缺', '有', bool(m['gap_chain_present']))
    row('来源条数', m['source_count'], '≥4', m['source_count'] >= 4)
    row('来源元数据完整率', f"{m['source_metadata_rate']:.0%}", '≥80%', m['source_metadata_rate'] >= 0.8)
    row('需人工确认项', m['manual_review_items'], '如实即可，0 需有依据', True)

    lines += ['', '## 2. 未清项（提交前应逐条处理）', '']
    lines += [f'- {e}' for e in errs] if errs else ['- 无']
    lines += ['', '## 3. 来源定位', '',
              f'共 {len(rows)} 条来源，逐条定位见 `source-map.csv`（source_id / claim / file / page / section / quote / used_in）。', '']
    if unlocated:
        lines.append(f'其中 {len(unlocated)} 条未在正文找到对应引用位置：{", ".join(unlocated)}。')
        lines.append('处置：在正文补上引用，或删掉该条来源，或写入 `uncertainty` 说明为何保留。')
    lines += ['', '## 4. 预览', '']
    if preview:
        lines.append(f'- `preview.pdf` 已由 pandoc 生成，可直接目视检查排版与引用呈现。')
    else:
        lines.append('- 环境内未找到 pandoc/xelatex，未生成 PDF 预览；成稿本体为 `draft.md`，可直接编辑。')
        lines.append('- 该情况需写入 `uncertainty`（type=not_reported），不要声称已渲染。')
    unc = result.get('uncertainty') or []
    lines += ['', '## 5. 已登记的缺口与待确认项（来自 result.json）', '']
    if unc:
        for u in unc:
            if isinstance(u, dict):
                lines.append(f"- [{u.get('type', '?')}] {u.get('note', '')}")
            else:
                lines.append(f'- {u}')
    else:
        lines.append('- 无（若材料确有缺口，此处为空本身就是一个问题）')
    path = os.path.join(outdir, 'selfcheck.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return path, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--draft', default='/app/output/draft.md')
    ap.add_argument('--result', default='/app/output/result.json')
    ap.add_argument('--outdir', default='/app/output')
    ap.add_argument('--min-chars', type=int, default=0,
                    help='0=按语言自适应（中文 1600 字 / 英文 1000 词）')
    ap.add_argument('--no-preview', action='store_true')
    args = ap.parse_args()
    if not os.path.isfile(args.draft):
        print(json.dumps({'error': 'draft not found', 'path': args.draft}, ensure_ascii=False))
        return 2
    with open(args.draft, encoding='utf-8') as f:
        draft = f.read()
    result = load_result(args.result)
    sources = result.get('sources') or []
    os.makedirs(args.outdir, exist_ok=True)

    rows = locate_quotes(draft, sources)
    csv_path = os.path.join(args.outdir, 'source-map.csv')
    write_csv(rows, csv_path)

    preview, engine = (None, 'unavailable') if args.no_preview else render_preview(args.draft, args.outdir)
    m = measure(draft, sources, result.get('uncertainty') or [], min_chars=args.min_chars or None)
    md_path, errs = write_selfcheck(m, result, rows, preview, args.outdir, args.min_chars)

    print(json.dumps({'ok': not errs, 'source_map': csv_path, 'selfcheck': md_path,
                      'preview': preview, 'preview_engine': engine,
                      'unresolved': errs, 'metrics': m}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
