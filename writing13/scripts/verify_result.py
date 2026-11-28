#!/usr/bin/env python3
"""核验 result.json 是否覆盖四关注点（编译得通/改得对/交得可用/复现得了）+ 契约。

用法:
    python3 verify_result.py <result.json> [--case case.json] [--static static_check.json] [--compile compile_report.json]

检查：
  编译得通 -> compile_report.status 与 result.build.compile_status 一致、错误已定位 file/line/root_cause；
  改得对   -> 事实/来源映射 exists，改动逐条带 source/修改记录；
  交得可用 -> 交付物是可编辑 .tex（非 PDF/截图片段）、列出 changed_files；
  复现得了 -> reproduction 记录 engine/engine_version/packages/command/rounds 齐全；
  成稿门槛 -> status=success 时必须有通过 check_manuscript 的 .tex 成稿，且 source_map >=3 条；
  契约     -> case_id / status / output_contract 字段 / sources / uncertainty / changes。
"""
import argparse
import importlib.util
import json
import os
import sys

VALID_STATUS = {'success', 'partial', 'unable', 'refused'}


def _load_check_manuscript():
    """同目录载入成稿核验器，避免要求使用者安装成包。"""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'check_manuscript.py')
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location('check_manuscript_mod', path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def _resolve_tex(result, result_dir, tex_arg):
    """定位本次交付的 .tex 成稿。"""
    if tex_arg and os.path.isfile(tex_arg):
        return tex_arg
    arts = (result.get('result') or {}).get('artifacts') or []
    own = (result.get('result') or {}).get('manuscript') or {}
    cands = []
    if isinstance(own, dict) and own.get('path'):
        cands.append(own['path'])
    for a in arts:
        if isinstance(a, dict):
            p = a.get('path') or a.get('file')
            if p and str(p).lower().endswith('.tex'):
                cands.append(p)
    for c in cands:
        for base in (result_dir, os.path.join(result_dir or '.', 'output'), '.'):
            p = c if os.path.isabs(c) else os.path.join(base, c)
            if os.path.isfile(p):
                return p
    return None


def verify(result, case, static, compile_rep, tex_path=None, result_dir=None,
           min_sec=120, min_total=400):
    errors, warnings = [], []
    if not isinstance(result, dict):
        return {'status': 'failed', 'errors': ['result 不是对象']}
    cid = result.get('case_id')
    st = result.get('status')
    if not cid:
        errors.append('缺少 case_id')
    if st not in VALID_STATUS:
        errors.append(f'status 非法: {st}')
    if case:
        exp = case.get('case_id')
        if exp and str(cid) != str(exp):
            errors.append(f'case_id 不符: 期望 {exp}, 得到 {cid}')
        for f in (case.get('output_contract') or []):
            if f not in (result.get('result') or {}):
                errors.append(f'result 缺少契约字段: {f}')

    r = result.get('result') or {}
    for f in ('artifacts', 'source_map', 'build'):
        if f not in r:
            warnings.append(f'result 缺少建议字段: {f}')
    for f in ('sources', 'uncertainty', 'changes'):
        if f not in result:
            errors.append(f'缺少顶层字段: {f}')
    if st in ('partial', 'unable', 'refused') and not (result.get('uncertainty') or []):
        errors.append(f'status={st} 时必须给出 uncertainty')

    # 交得可用：必须列出可编辑 .tex 产物，不能只给 PDF/截图
    artifacts = r.get('artifacts') or []
    tex_arts = [a for a in artifacts
                if isinstance(a, dict) and str(a.get('path', a.get('file', ''))).lower().endswith('.tex')]
    if artifacts and not tex_arts:
        errors.append('交付物中没有可编辑 .tex 源码（不能用 PDF/截图/片段代替）')
    changed = r.get('changed_files') or r.get('changes') or []
    if st == 'success' and not changed:
        warnings.append('success 但未记录改动文件/差异（交得可用/可核验性弱）')

    # 改得对：事实/来源映射逐条可回溯
    # 来源定位接受三种等价写法：source / source_id，或 file + locator（按 file#locator 归一）
    smap = r.get('source_map') or []
    for i, item in enumerate(smap):
        if not isinstance(item, dict):
            continue
        if not str(item.get('claim', item.get('text', ''))).strip():
            warnings.append(f'source_map[{i}] 缺 claim/text')
        loc = item.get('source') or item.get('source_id')
        if not loc:
            f, l = item.get('file'), item.get('locator')
            if f and l:
                loc = f'{f}#{l}'
                item.setdefault('source', loc)
        if not loc:
            warnings.append(f'source_map[{i}] 缺来源定位（source 或 file+locator）')

    # 编译得通：编译状态与错误定位
    build = r.get('build') or {}
    cstatus = build.get('compile_status')
    if st == 'success' and cstatus and cstatus not in ('success', 'compiled'):
        warnings.append(f'status=success 但 compile_status={cstatus}')
    if compile_rep:
        rep_status = compile_rep.get('status')
        for e in (compile_rep.get('errors') or []):
            if e.get('line') is None or not e.get('root_cause'):
                warnings.append(f"编译错误 #{e.get('index')} 未定位行号或根因")
        if st == 'success' and rep_status in ('failed', 'unavailable'):
            errors.append(f'result 声明 success，但 compile_report.status={rep_status}')

    # 复现得了：环境记录齐全
    repro = r.get('reproduction') or build.get('reproduction') or {}
    need = ['engine', 'engine_version', 'command', 'rounds']
    miss = [k for k in need if not repro.get(k)]
    if miss and st == 'success':
        errors.append('reproduction 缺复现要素: ' + ', '.join(miss))
    for k in ('packages', 'fonts'):
        if k not in repro:
            warnings.append(f'reproduction 建议记录 {k}（宏包/字体版本）')

    if static:
        if static.get('status') == 'failed' and st == 'success':
            errors.append('静态检查未通过但声明 success')

    # 交得可用（硬门槛）：success 必须真的交付一份通过实质核验的 .tex 成稿
    manuscript = None
    if st == 'success':
        resolved = _resolve_tex(result, result_dir, tex_path)
        if not resolved:
            errors.append('status=success 但定位不到 .tex 成稿（不接受只交检查报告/片段/PDF）')
        else:
            mod = _load_check_manuscript()
            if mod is None:
                warnings.append('未能加载 check_manuscript.py，已跳过成稿实质核验')
            else:
                tex_text = open(resolved, encoding='utf-8', errors='replace').read()
                pool = tex_text
                bp = os.path.join(os.path.dirname(resolved), 'refs.bib')
                if os.path.isfile(bp):
                    pool += open(bp, encoding='utf-8', errors='replace').read()
                manuscript = mod.check(tex_text, case, pool, min_sec, min_total)
                if manuscript['status'] != 'passed':
                    for e in manuscript['errors'][:8]:
                        errors.append('成稿未过硬门槛: ' + e)
                    warnings.append('空骨架/占位稿会被评测判为 incomplete，应继续写实后重跑')
        smap_n = len([x for x in (r.get('source_map') or []) if isinstance(x, dict)])
        if smap_n < 3:
            errors.append(f'source_map 仅 {smap_n} 条，success 需 >=3 条可回溯的事实/来源映射')

    return {
        'status': 'passed' if not errors else 'failed',
        'errors': errors, 'warnings': warnings,
        'checks': {
            'compilable': 'ok' if not any('编译' in e for e in errors) else 'failed',
            'correct_edit': 'ok' if not any('来源' in e or 'source_map' in e for e in errors) else 'failed',
            'usable_source': 'ok' if not any('可编辑' in e or '成稿' in e or '.tex' in e for e in errors) else 'failed',
            'reproducible': 'ok' if not any('复现要素' in e for e in errors) else 'failed',
        },
        'manuscript': (manuscript or {}).get('stats'),
        'case_id': cid, 'status_value': st,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--case')
    ap.add_argument('--static')
    ap.add_argument('--compile')
    ap.add_argument('--tex', help='本次交付的 .tex 成稿路径（缺省从 result.artifacts 推断）')
    ap.add_argument('--min-section-chars', type=int, default=120)
    ap.add_argument('--min-total-chars', type=int, default=400)
    args = ap.parse_args()
    result = json.load(open(args.result, encoding='utf-8'))
    case = json.load(open(args.case, encoding='utf-8')) if args.case else None
    static = json.load(open(args.static, encoding='utf-8')) if args.static else None
    compile_rep = json.load(open(args.compile, encoding='utf-8')) if args.compile else None
    rep = verify(result, case, static, compile_rep,
                 tex_path=args.tex,
                 result_dir=os.path.dirname(os.path.abspath(args.result)),
                 min_sec=args.min_section_chars,
                 min_total=args.min_total_chars)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
