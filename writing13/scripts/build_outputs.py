#!/usr/bin/env python3
"""把 LaTeX 交付物落成可复核的附件：selfcheck.md + cite-map.csv + compile-report.json（+ PDF）。

产物（默认 /app/output）：
  selfcheck.md        成稿门槛（章节/公式/表格/引用闭合）、编译结果、未清项
  cite-map.csv        \\cite 键 → 是否在 .bib 中 → 被哪些章节引用 → 条目题名
  compile-report.json 编译轮次、引擎与版本、错误定位（file:line + 首行报错）
  preview.pdf         编译成功时的产物（没有引擎就如实标 unavailable）

为什么单列：题面要求"报错定位到文件行号与根因、交付可重复编译的稿件"。
把编译证据和引用闭合摊成文件，复核人不必重跑猜结论；编译不通就写不通，不假装通过。

用法:
  python build_outputs.py --tex /app/output/manuscript.tex --result /app/output/result.json \
      --outdir /app/output [--bib refs.bib] [--no-compile]
退出码 0=产物已生成；2=输入缺失。
"""
import argparse
import csv
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read() if path.endswith(('.tex', '.bib', '.txt', '.log')) else json.load(f)


def load_check_module():
    p = os.path.join(HERE, 'check_manuscript.py')
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location('cm13', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_bib(tex_path):
    """定位参考文献库：\\bibliography{name} 指向的文件 > 同目录 refs.bib > 同目录第一个 .bib。

    先看 \\bibliography{} 是因为同一目录常放着多份 .bib（示例与基线各一份），
    乱取第一个会把别家的条目算进本篇的引用闭合率。
    """
    d = os.path.dirname(os.path.abspath(tex_path or '.'))
    tex = load(tex_path, '') or ''
    for m in re.finditer(r'\\bibliography\s*\{([^}]*)\}', tex):
        for name in m.group(1).split(','):
            cand = os.path.join(d, name.strip() + '.bib')
            if os.path.isfile(cand):
                return cand
    p = os.path.join(d, 'refs.bib')
    if os.path.isfile(p):
        return p
    import glob
    cands = sorted(glob.glob(os.path.join(d, '*.bib')))
    return cands[0] if cands else None


def bib_entries(bib_text):
    """极简 BibTeX 解析：key → {title, author, year}（够用于引用闭合与映射表）。"""
    out = {}
    for m in re.finditer(r'@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}', bib_text or '', re.S):
        key, body = m.group(2), m.group(3)
        entry = {'type': m.group(1).lower()}
        for f in ('title', 'author', 'year', 'journal', 'booktitle', 'doi'):
            mm = re.search(f + r'\s*=\s*[{"](.+?)[}"]\s*,?\s*\n', body, re.I | re.S)
            if mm:
                entry[f] = re.sub(r'\s+', ' ', mm.group(1)).strip()
        out[key] = entry
    return out


def cite_usage(tex):
    """统计每个 \\cite 键出现在哪些 \\section 下。"""
    body = re.sub(r'(?<!\\)%.*', '', tex)
    secs = re.split(r'\\(?:sub)*section\*?\{([^{}]*)\}', body)
    usage = {}
    if len(secs) == 1:
        for m in re.finditer(r'\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])?\{([^{}]*)\}', body):
            for k in m.group(1).split(','):
                k = k.strip()
                if k:
                    usage.setdefault(k, set()).add('（无章节标题）')
        return usage
    # secs = [前言, 标题1, 正文1, 标题2, 正文2, ...]
    head = secs[0]
    for m in re.finditer(r'\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])?\{([^{}]*)\}', head):
        for k in m.group(1).split(','):
            if k.strip():
                usage.setdefault(k.strip(), set()).add('摘要/前言')
    for i in range(1, len(secs) - 1, 2):
        title, chunk = secs[i], secs[i + 1]
        for m in re.finditer(r'\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])?\{([^{}]*)\}', chunk):
            for k in m.group(1).split(','):
                if k.strip():
                    usage.setdefault(k.strip(), set()).add(title.strip())
    return usage


def engine_info():
    for eng in ('latexmk', 'xelatex', 'pdflatex'):
        p = shutil.which(eng)
        if p:
            try:
                v = subprocess.run([eng, '--version'], capture_output=True, text=True, timeout=20)
                first = (v.stdout or v.stderr or '').splitlines()[0] if (v.stdout or v.stderr) else ''
            except Exception:
                first = ''
            return eng, p, first
    return None, None, ''


def compile_tex(tex, outdir, max_rounds=2):
    """尽力编译；把「没引擎」「编译失败」都如实写进报告，不伪造成功。"""
    eng, path, ver = engine_info()
    rep = {'engine': eng, 'engine_path': path, 'engine_version': ver, 'rounds': 0,
           'status': 'unavailable' if not eng else 'not_run', 'errors': [], 'pdf': None}
    if not eng:
        return rep
    work = os.path.join(outdir, '_compile')
    os.makedirs(work, exist_ok=True)
    src = os.path.abspath(tex)
    cmd_rounds = [['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error', src]] if eng == 'latexmk' \
        else [[eng, '-interaction=nonstopmode', '-halt-on-error', src]]
    last_log = ''
    for i in range(max_rounds):
        try:
            r = subprocess.run(cmd_rounds[0], cwd=os.path.dirname(src), capture_output=True,
                               text=True, timeout=600)
            last_log = (r.stdout or '') + (r.stderr or '')
            rep['rounds'] = i + 1
            if r.returncode == 0:
                rep['status'] = 'passed'
                break
            rep['status'] = 'failed'
        except subprocess.TimeoutExpired:
            rep['status'] = 'timeout'
            break
        except Exception as e:
            rep['status'] = 'error'
            last_log = str(e)
            break
    # 错误定位：LaTeX 的 "! ..." + "l.<行号>"
    for m in re.finditer(r'^!\s*(.+)$', last_log, re.M)  :
        tail = last_log[m.end():m.end() + 400]
        lm = re.search(r'l\.(\d+)', tail)
        rep['errors'].append({'message': m.group(1).strip()[:200],
                              'line': int(lm.group(1)) if lm else None,
                              'file': os.path.basename(src)})
        if len(rep['errors']) >= 10:
            break
    pdf = os.path.splitext(src)[0] + '.pdf'
    if os.path.isfile(pdf) and os.path.getsize(pdf) > 0:
        dst = os.path.join(outdir, 'preview.pdf')
        try:
            shutil.copyfile(pdf, dst)
            rep['pdf'] = dst
        except Exception:
            rep['pdf'] = pdf
    return rep


def write_selfcheck(stats, cm_rep, cite_rows, comp, reps, tex_name, path):
    errs = list(cm_rep.get('errors') or [])
    bad_cites = [r for r in cite_rows if r['in_bib'] == 'no']
    if bad_cites:
        errs.append('引用键在 .bib 中不存在: ' + ', '.join(r['cite_key'] for r in bad_cites))
    if comp['status'] == 'failed':
        errs.append(f"编译失败（{len(comp.get('errors') or [])} 条已定位错误）")
    elif comp['status'] in ('unavailable', 'error', 'timeout'):
        errs.append(f"编译未完成：{comp['status']}（需在 uncertainty 标 not_reported）")

    lines = ['# LaTeX 成稿与编译自检表（非自评分）', '',
             '> 由 `scripts/build_outputs.py` 依据 .tex/.bib/编译日志计算，可用同一输入重跑。',
             '> 结构达标与编译通过不等于内容正确；公式含义与数值仍需人对着原文核。', '',
             f'- 稿件：`{tex_name}`', '',
             '## 1. 结构指标', '', '| 项 | 值 | 门槛 | 判定 |', '|---|---|---|---|']
    st = stats or {}

    def row(name, val, gate, ok):
        lines.append(f'| {name} | {val} | {gate} | {"通过" if ok else "未达"} |')

    row('章节数', st.get('sections', 0), '≥1', (st.get('sections') or 0) >= 1)
    row('全文实义字数', st.get('total_real_chars', 0), '≥400', (st.get('total_real_chars') or 0) >= 400)
    row('公式环境', st.get('equations', 0), '≥1 且有真实内容', (st.get('equations') or 0) >= 1)
    row('表格', st.get('tables', 0), '≥1 且数据行 ≥2', (st.get('tables') or 0) >= 1)
    row('引用键数', len(cite_rows), '≥1', len(cite_rows) >= 1)
    row('引用键可回溯', f"{sum(1 for r in cite_rows if r['in_bib'] == 'yes')}/{len(cite_rows)}", '全部',
        bool(cite_rows) and not bad_cites)
    row('编译', comp['status'], 'passed', comp['status'] == 'passed')
    row('编译轮次', comp.get('rounds', 0), '记录实际轮次', True)

    lines += ['', '## 2. 未清项', '']
    lines += [f'- {e}' for e in errs] if errs else ['- 无']
    if comp.get('errors'):
        lines += ['', '### 编译错误定位', '', '| 文件 | 行 | 报错首行 |', '|---|---|---|']
        for e in comp['errors']:
            lines.append(f"| {e.get('file')} | {e.get('line')} | {e.get('message')} |")
    lines += ['', '## 3. 引用映射', '',
              f'共 {len(cite_rows)} 个键，逐条见 `cite-map.csv`（cite_key / in_bib / used_in / title）。', '']
    lines += ['', '## 4. 复现记录', '',
              f"- 引擎：{comp.get('engine') or '未找到（latexmk/xelatex/pdflatex 均不可用）'}",
              f"- 版本：{comp.get('engine_version') or 'n/a'}",
              f"- 轮次：{comp.get('rounds', 0)}",
              f"- 命令：见 result.reproduction.command；本节不做推测"]
    lines += ['', '## 5. 已登记的边界与待确认', '']
    lines += [f"- [{u.get('type', '?') if isinstance(u, dict) else '?'}] {u.get('note', '') if isinstance(u, dict) else u}"
              for u in (reps or [])] or ['- 无']
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tex', required=True)
    ap.add_argument('--result', default='/app/output/result.json')
    ap.add_argument('--bib')
    ap.add_argument('--outdir', default='/app/output')
    ap.add_argument('--min-sec', type=int, default=250)
    ap.add_argument('--min-total', type=int, default=1400)
    ap.add_argument('--no-compile', action='store_true')
    args = ap.parse_args()
    if not os.path.isfile(args.tex):
        print(json.dumps({'error': 'tex not found', 'path': args.tex}, ensure_ascii=False))
        return 2
    tex = load(args.tex)
    result = load(args.result, {}) or {}
    bib_path = args.bib or find_bib(args.tex)
    bib_text = load(bib_path, '') if bib_path else ''
    os.makedirs(args.outdir, exist_ok=True)

    mod = load_check_module()
    case = {}
    cm_rep = mod.check(tex, case, bib_text, args.min_sec, args.min_total) if mod else \
        {'status': 'failed', 'errors': ['check_manuscript.py 不可用'], 'warnings': [], 'stats': {}}
    stats = cm_rep.get('stats') or {}

    usage = cite_usage(tex)
    entries = bib_entries(bib_text)
    rows = []
    for key in sorted(set(list(usage.keys()) + list(entries.keys()))):
        e = entries.get(key, {})
        rows.append({'cite_key': key,
                     'in_bib': 'yes' if key in entries else 'no',
                     'used_in': ' / '.join(sorted(usage.get(key, []))) or '未在正文引用',
                     'title': (e.get('title') or '')[:120],
                     'year': e.get('year') or ''})
    csv_path = os.path.join(args.outdir, 'cite-map.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['cite_key', 'in_bib', 'used_in', 'title', 'year'])
        w.writeheader()
        w.writerows(rows)

    comp = {'engine': None, 'status': 'skipped', 'errors': [], 'rounds': 0, 'pdf': None} \
        if args.no_compile else compile_tex(args.tex, args.outdir)
    rep_path = os.path.join(args.outdir, 'compile-report.json')
    with open(rep_path, 'w', encoding='utf-8') as f:
        json.dump(comp, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(args.outdir, 'selfcheck.md')
    errs = write_selfcheck(stats, cm_rep, rows, comp, result.get('uncertainty'), os.path.basename(args.tex), md_path)
    print(json.dumps({'ok': not errs, 'selfcheck': md_path, 'cite_map': csv_path,
                      'compile_report': rep_path, 'compile': comp.get('status'),
                      'pdf': comp.get('pdf'), 'stats': stats,
                      'unresolved': errs, 'check_warnings': cm_rep.get('warnings')},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
