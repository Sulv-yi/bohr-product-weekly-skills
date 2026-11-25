#!/usr/bin/env python3
"""把章节成稿与来源映射落成可复核的三件附加产物，并给出结构自检表。

产物（默认 /app/output）：
  source-map.csv   逐条 参数/步骤/条件 → file/page/section/quote → 出现在哪一节
  selfcheck.md     六要素覆盖、参数表可核性、对照与复现要件、未清项
  preview.pdf      环境有 pandoc 或 xelatex 时渲染成稿，供目视检查

为什么要有：题面要求"数值与步骤能否追溯到具体材料、缺口与人工确认项能否被复核"。
只写在 result.json 里，复核人要自己解析 JSON；落成 CSV 与自检表后，
一条命令就能对着 config.yaml / train.log 核。

用法:
  python build_outputs.py --draft /app/output/section.md --result /app/output/result.json \
      --outdir /app/output
退出码 0=已生成；2=输入缺失。
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
from quality_gate import measure, find_elements  # noqa: E402

ELEM_ZH = {'steps': '方法步骤', 'setup': '实验设置', 'parameters': '参数',
           'dataset': '数据集与划分', 'baselines': '对照实验', 'reproducibility': '可复现性与限制'}


def load_result(path):
    if not path or not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def locate(draft, sources):
    """定位来源：编号 [n] → locator（文件名的短标识）→ quote 首 12 字。"""
    elems = find_elements(draft)
    spans = [(ELEM_ZH.get(k, k), body) for k, (_t, body) in elems.items()]
    flat = re.sub(r'\s+', '', draft)
    rows = []
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            continue
        quote = (s.get('quote') or '').strip()
        key = str(s.get('cite_key') or '').strip()
        where = ''
        if key and re.search(r'\[' + re.escape(key) + r'(?:\s*[,\-–]\s*\d+)*\]', draft):
            hits = [n for n, b in spans if re.search(r'\[' + re.escape(key) + r'(?:\s*[,\-–]\s*\d+)*\]', b)]
            where = ' / '.join(dict.fromkeys(hits)) or '正文（未落在六要素小节）'
        loc = str(s.get('locator') or '').strip()
        if not where and loc and loc in draft:
            hits = [n for n, b in spans if loc in b]
            where = (' / '.join(dict.fromkeys(hits)) or '正文') + f'（按 locator {loc}）'
        if not where:
            base = os.path.basename(str(s.get('file') or ''))
            stem = re.sub(r'\.[A-Za-z0-9]+$', '', base)
            if stem and len(stem) >= 3 and stem in draft:
                hits = [n for n, b in spans if stem in b]
                where = (' / '.join(dict.fromkeys(hits)) or '正文') + f'（按文件名 {base}）'
        if not where and quote:
            probe = re.sub(r'\s+', '', quote)[:12]
            if probe and probe in flat:
                hits = [n for n, b in spans if probe in re.sub(r'\s+', '', b)]
                where = (' / '.join(dict.fromkeys(hits)) or '正文') + '（按引文命中）'
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
    pdf = os.path.join(outdir, 'preview.pdf')
    pandoc = shutil.which('pandoc')
    if pandoc:
        try:
            subprocess.run([pandoc, draft, '-o', pdf, '-V', 'CJKmainfont=Noto Sans CJK SC', '--pdf-engine=xelatex'],
                           check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.isfile(pdf) and os.path.getsize(pdf) > 0:
                return pdf
        except Exception:
            pass
    return None


def write_selfcheck(m, result, rows, preview, outdir, min_chars):
    errs = []
    if m['total_chars'] < min_chars:
        errs.append(f'正文 {m["total_chars"]} 字，低于门槛 {min_chars}')
    if m['missing_elements']:
        errs.append('六要素缺件: ' + ', '.join(m['missing_elements']))
    if m['param_rows'] < 5:
        errs.append(f'参数表仅 {m["param_rows"]} 行，需 ≥5 行')
    elif m['param_source_rate'] < 0.8:
        errs.append(f'参数表带来源的行 {m["param_source_rate"]:.0%}，需 ≥80%')
    if m['baseline_coverage'] < 0.66:
        errs.append(f'对照六项命中 {m["baseline_coverage"]:.0%}，需 ≥67%（基线/版本/同预算/指标/统计/重复）')
    if m['repro_coverage'] < 0.66:
        errs.append(f'复现六项命中 {m["repro_coverage"]:.0%}，需 ≥67%（版本/环境/种子/命令/数据/划分）')
    if not m['limitation_specific']:
        errs.append('限制条件未落到具体失效场景')
    if m['placeholder_count']:
        errs.append(f'残留占位符 {m["placeholder_count"]} 处')
    unlocated = [r['source_id'] for r in rows if r['used_in'].startswith('未在正文')]
    if unlocated:
        errs.append('以下来源未在正文定位: ' + ', '.join(unlocated))

    lines = ['# 章节自检表（结构度量，非自评分）', '',
             '> 由 `scripts/build_outputs.py` 依据成稿与 result.json 计算，可用同一输入重跑。',
             '> 通过本表只说明结构达标；数值是否与 config/log 一致，必须逐条对着材料核。', '',
             '## 1. 结构指标', '', '| 指标 | 值 | 门槛 | 判定 |', '|---|---|---|---|']

    def row(name, val, gate, ok):
        lines.append(f'| {name} | {val} | {gate} | {"通过" if ok else "未达"} |')

    row('正文总字数', m['total_chars'], f'≥{min_chars}', m['total_chars'] >= min_chars)
    row('六要素覆盖', f"{m['element_coverage']:.0%}", '100%', m['element_coverage'] >= 1.0)
    for k, v in m['section_chars'].items():
        row(f'　{ELEM_ZH.get(k, k)} 字数', v, '见 README 门槛表', bool(m['section_min_ok'].get(k)))
    row('参数表行数', m['param_rows'], '≥5', m['param_rows'] >= 5)
    row('参数带来源比例', f"{m['param_source_rate']:.0%}", '≥80%', m['param_source_rate'] >= 0.8)
    row('正文-参数表对齐率', f"{m['param_body_alignment']:.0%}", '≥80%', m['param_body_alignment'] >= 0.8)
    row('对照可比性六项', f"{m['baseline_coverage']:.0%}" + f"（{len(m['baseline_checks'])}/6）", '≥67%', m['baseline_coverage'] >= 0.66)
    row('复现清单六项', f"{m['repro_coverage']:.0%}" + f"（{len(m['repro_checks'])}/6）", '≥67%', m['repro_coverage'] >= 0.66)
    row('限制落到失效场景', '是' if m['limitation_specific'] else '否', '是', bool(m['limitation_specific']))
    row('缺口/待确认条数', m['open_gaps'], '如实即可', True)

    lines += ['', '## 2. 未清项（提交前逐条处理）', '']
    lines += [f'- {e}' for e in errs] if errs else ['- 无']
    lines += ['', '## 3. 来源定位', '',
              f'共 {len(rows)} 条来源，逐条定位见 `source-map.csv`。', '']
    if unlocated:
        lines.append(f'{len(unlocated)} 条未在正文找到落点：{", ".join(unlocated)}。处置：补引用、删条目、或写入 uncertainty 说明保留理由。')
    lines += ['', '## 4. 预览', '']
    if preview:
        lines.append('- `preview.pdf` 已生成，可直接目视检查表格与编号。')
    else:
        lines.append('- 环境内未找到 pandoc/xelatex，未生成 PDF 预览；成稿为 `section.md`，可直接编辑。')
        lines.append('- 该情况需写入 `uncertainty`（type=not_reported），不要声称已渲染。')
    q = (result.get('result') or {}).get('questions_for_author') or []
    unc = result.get('uncertainty') or []
    lines += ['', '## 5. 待作者确认（来自 result.json）', '']
    body = []
    for item in list(q) + list(unc):
        if isinstance(item, dict):
            body.append(f"- [{item.get('type', 'question')}] {item.get('note') or item.get('question') or ''}")
        else:
            body.append(f'- {item}')
    lines += body or ['- 无（若材料确有缺口，此处为空本身就是一个问题）']
    path = os.path.join(outdir, 'selfcheck.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return path, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--draft', default='/app/output/section.md')
    ap.add_argument('--result', default='/app/output/result.json')
    ap.add_argument('--outdir', default='/app/output')
    ap.add_argument('--min-chars', type=int, default=1800)
    ap.add_argument('--no-preview', action='store_true')
    args = ap.parse_args()
    if not os.path.isfile(args.draft):
        print(json.dumps({'error': 'draft not found', 'path': args.draft}, ensure_ascii=False))
        return 2
    draft = open(args.draft, encoding='utf-8').read()
    result = load_result(args.result)
    sources = result.get('sources') or []
    os.makedirs(args.outdir, exist_ok=True)

    rows = locate(draft, sources)
    csv_path = os.path.join(args.outdir, 'source-map.csv')
    write_csv(rows, csv_path)
    preview = None if args.no_preview else render_preview(args.draft, args.outdir)
    m = measure(draft, result.get('uncertainty') or [],
                (result.get('result') or {}).get('questions_for_author') or [],
                min_chars=args.min_chars)
    md_path, errs = write_selfcheck(m, result, rows, preview, args.outdir, args.min_chars)
    print(json.dumps({'ok': not errs, 'source_map': csv_path, 'selfcheck': md_path,
                      'preview': preview, 'unresolved': errs, 'metrics': m},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
