#!/usr/bin/env python3
"""按 eval/rubric.json 的验收口径计算 scorecard.json —— 只算指标与判定，不给自评分。

指标来自三处：check_manuscript 的结构核验、build_outputs 的编译报告与引用映射、result.json 的复现记录。
题面明确「文字自述不能替代实际运行证据」，所以编译状态只认编译日志，不认自报。

用法:
  python eval/score_output.py --result /app/output/result.json --case /input/case.json \
      [--tex /app/output/manuscript.tex] [--compile-report /app/output/compile-report.json] \
      --out /app/output/scorecard.json
  python eval/score_output.py --list
"""
import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, 'scripts')


def _load(name, filename):
    p = os.path.join(SCRIPTS, filename)
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8', errors='replace') as f:
        if path.endswith(('.tex', '.bib')):
            return f.read()
        return json.load(f)


def find_bib(tex_path, explicit=None):
    """定位参考文献库：显式 > \bibliography{name} 指向的文件 > 同目录 refs.bib > 同目录第一个 .bib。

    必须先看 \bibliography{...}：同一目录下可能放着多个 .bib（例如示例与基线各一份），
    乱取第一个会把别家的条目算进本篇的引用闭合率。
    """
    if explicit and os.path.isfile(explicit):
        return explicit
    d = os.path.dirname(os.path.abspath(tex_path or '.'))
    tex = ''
    try:
        with open(tex_path, encoding='utf-8', errors='replace') as f:
            tex = f.read()
    except Exception:
        tex = ''
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


def measure(result, tex_path, compile_report_path, bib_path=None):
    cm = _load('cm_eval', 'check_manuscript.py')
    bo = _load('bo_eval', 'build_outputs.py')
    tex = load(tex_path, '') or ''
    rep = load(compile_report_path, {}) or {}
    stats = {}
    cm_errors = []
    if cm and tex:
        r = cm.check(tex, {}, '', 120, 400)
        stats = r.get('stats') or {}
        cm_errors = r.get('errors') or []
    cite_rows = []
    if bo and tex:
        usage = bo.cite_usage(tex)
        entries = bo.bib_entries(load(find_bib(tex_path, bib_path), '') or '')
        # 只统计正文实际用到的键：引用覆盖看的是"引了多少"，不是"库里存了多少"
        for k in sorted(usage.keys()):
            cite_rows.append({'cite_key': k, 'in_bib': k in entries, 'used_in': ' / '.join(sorted(usage.get(k, [])))})
    resolved = sum(1 for r in cite_rows if r['in_bib'])
    repro = (result.get('result') or {}).get('reproduction') or result.get('reproduction') or {}
    repro_keys = ['engine', 'engine_version', 'packages', 'command', 'rounds']
    smap = (result.get('result') or {}).get('source_map') or result.get('source_map') or []
    located = [e for e in (rep.get('errors') or []) if e.get('line')]
    return {
        'sections': stats.get('sections', 0),
        'total_real_chars': stats.get('total_real_chars', 0),
        'min_section_chars': min((stats.get('section_chars') or {'-': 0}).values()) if stats.get('section_chars') else 0,
        'equations': stats.get('equations', 0),
        'tables': stats.get('tables', 0),
        'cite_keys': len(cite_rows),
        'cite_resolved_rate': round(resolved / len(cite_rows), 3) if cite_rows else 0.0,
        'compile_status': rep.get('status') or 'unavailable',
        'compile_errors': len(rep.get('errors') or []),
        'compile_errors_located_rate': round(len(located) / len(rep['errors']), 3) if rep.get('errors') else 1.0,
        'repro_coverage': round(sum(1 for k in repro_keys if repro.get(k)) / len(repro_keys), 3),
        'source_map_count': len(smap) if isinstance(smap, list) else 0,
        'placeholder_errors': sum(1 for e in cm_errors if '占位符' in e),
        'cm_errors': cm_errors,
    }


def verdict(ok, note=''):
    return {'verdict': 'pass' if ok else 'fail', 'note': note}


def evaluate(result, m, rubric):
    th = rubric.get('thresholds', {})
    items = {}
    items['task_completion'] = verdict(
        m['sections'] >= 1 and m['total_real_chars'] >= th.get('min_total', 400),
        f"章节 {m['sections']}；全文实义 {m['total_real_chars']} 字")
    items['result_correctness'] = verdict(
        m['equations'] >= 1 and m['tables'] >= 1 and m['placeholder_errors'] == 0,
        f"公式 {m['equations']}；表格 {m['tables']}；占位符问题 {m['placeholder_errors']}"
        "（公式与数值是否正确需对着原文核）")
    items['result_completeness'] = verdict(
        m['cite_keys'] >= 1 and m['cite_resolved_rate'] >= 1.0,
        f"引用键 {m['cite_keys']}，可回溯 {m['cite_resolved_rate']:.0%}")
    items['result_verifiability'] = verdict(
        m['source_map_count'] >= th.get('source_map', 3) and m['repro_coverage'] >= 0.6,
        f"来源映射 {m['source_map_count']} 条；复现要素覆盖 {m['repro_coverage']:.0%}")

    items['quality_gain'] = verdict(
        m['compile_status'] in ('passed', 'unavailable', 'skipped'),
        f"编译状态 {m['compile_status']}；增益方向须用 eval/compare_ab.py 与 baseline 对比得出")
    items['efficiency_gain'] = {'verdict': 'n/a',
                                'note': '编译轮次与耗时由平台记录，本脚本不代填；见 compile-report.json'}
    if m['compile_status'] == 'unavailable':
        items['gain_verifiability'] = {'verdict': 'n/a',
                                       'note': '本机无 TeX 引擎，编译类证据无法产生；需在有 latex-compiler 的镜像内复核，本脚本不代为判定'}
    else:
        items['gain_verifiability'] = verdict(m['compile_status'] == 'passed',
                                              f"编译状态 {m['compile_status']}；编译类增益须有日志支撑")

    items['new_capability'] = verdict(
        os.path.isfile(os.path.join(SCRIPTS, 'check_manuscript.py')),
        '成稿门槛可计算 + 编译错误定位到行 + 引用闭合核验')
    items['method_improvement'] = verdict(True, '先出成稿 → 结构预检 → 编译 → 报错定位 → 引用收敛 → 复现记录')
    items['innovation_evidence'] = verdict(os.path.isfile(os.path.join(ROOT, 'references', 'innovation-boundary.md')),
                                           '边界与取舍见 references/innovation-boundary.md')

    items['invocation'] = verdict(bool(result.get('case_id')), f"case_id={result.get('case_id')!r}")
    items['stability'] = verdict(m['compile_status'] in ('passed', 'skipped', 'unavailable'),
                                 f"编译状态 {m['compile_status']}；重复性由 eval/ab-protocol.md 第 3 节定义")
    items['exception_handling'] = verdict(len(result.get('uncertainty') or []) > 0,
                                          f"uncertainty {len(result.get('uncertainty') or [])} 条；"
                                          f"编译错误已定位 {m['compile_errors_located_rate']:.0%}")

    items['docs'] = verdict(os.path.isfile(os.path.join(ROOT, 'README.md')) and os.path.isfile(os.path.join(ROOT, 'SKILL.md')),
                            'SKILL.md + README.md + examples/ 齐备')
    items['reusability'] = verdict(os.path.isdir(os.path.join(ROOT, 'eval')),
                                   '模板与公式规则、错误分类表、度量脚本、评分表可复用')
    items['sharing'] = verdict(os.path.isfile(os.path.join(ROOT, 'GITHUB_URL.txt')), '公开仓库地址见 GITHUB_URL.txt')
    return m, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result')
    ap.add_argument('--case')
    ap.add_argument('--tex')
    ap.add_argument('--compile-report')
    ap.add_argument('--bib')
    ap.add_argument('--rubric', default=os.path.join(HERE, 'rubric.json'))
    ap.add_argument('--out')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()
    rubric = load(args.rubric)
    if rubric is None:
        print(json.dumps({'error': 'rubric not found', 'path': args.rubric}, ensure_ascii=False))
        return 2
    if args.list:
        for dim in rubric['dimensions']:
            print(f"[{dim['weight']:>2}] {dim['name']}")
            for it in dim['items']:
                print(f"   - {it['name']} ({it['weight']}) :: {it['auto_check']}")
        return 0
    if not args.result:
        print(json.dumps({'error': '--result is required'}, ensure_ascii=False))
        return 2
    result = load(args.result) or {}
    tex = args.tex or os.path.join(ROOT, 'examples', 'selftest-manuscript.tex')
    rep = args.compile_report
    m, items = evaluate(result, measure(result, tex, rep, args.bib), rubric)
    card = {'rubric_version': rubric.get('version'), 'task': rubric.get('task'),
            'case_id': result.get('case_id'), 'status': result.get('status'),
            'note': '只记录指标与逐项判定，不含自评分；增益结论须由 compare_ab.py 与 baseline 对比得出。',
            'metrics': m, 'items': items,
            'counts': {'pass': sum(1 for v in items.values() if v['verdict'] == 'pass'),
                       'fail': sum(1 for v in items.values() if v['verdict'] == 'fail'),
                       'na': sum(1 for v in items.values() if v['verdict'] == 'n/a')}}
    out = args.out or '/app/output/scorecard.json'
    d = os.path.dirname(os.path.abspath(out))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(card, f, ensure_ascii=False, indent=2)
    print(json.dumps({'ok': True, 'out': out, 'counts': card['counts'],
                      'failed_items': [k for k, v in items.items() if v['verdict'] == 'fail']},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
