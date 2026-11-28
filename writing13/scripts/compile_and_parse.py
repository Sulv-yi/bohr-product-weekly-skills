#!/usr/bin/env python3
"""多轮编译 + 全量日志解析：定位每一条错误的文件/行号/根因，不止于第一条。

- 按指定引擎与轮次编译（默认 latexmk，或 pdflatex/xelatex/lualatex + 多轮）；
- 解析 .log 中所有 ! error 与关键 warning，分类到根因并给修复策略；
- 检查引用/交叉引用收敛（Rerun 提示、undefined 清零）；
- 无引擎时如实报 status=unavailable，只做日志解析（若给出 --log）。

用法:
    python3 compile_and_parse.py <工程根目录> --out compile_report.json \
        [--engine pdflatex] [--rounds 3] [--main main.tex] [--log existing.log] [--timeout 120]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# 日志错误块：从 "! ..." 起到下一个 "!"、"Here is how much" 或 LaTeX 信息
ERROR_START = re.compile(r'^!', re.M)
LINE_REF = re.compile(r'(?:^|\s)(?:l\.|lines?\s+)(\d+)', re.I)
FILE_REF = re.compile(r'([\w./\\-]+\.tex)')
UNDEREF = re.compile(r'Reference\s+[`\']([^\']+)\'[^\n]{0,60}undefined', re.I)
# pdfTeX/XeTeX 的写法是：Citation `key' on page 1 undefined on input line 8.
# 引号与 undefined 之间隔着 "on page N"，旧正则要求紧跟 undefined，会整条漏掉。
UNDEFCITE = re.compile(r'Citation\s+[`\']([^\']+)\'[^\n]{0,60}undefined', re.I)
RERUN = re.compile(r'Rerun to get (?:cross-references|the bibliography|marks|things) right', re.I)
REQ_MISSING = re.compile(r'LaTeX Warning:\s*No\s*\\(author|title|date|maketitle)\s+given', re.I)
UNDEFCTRL = re.compile(r'Undefined control sequence', re.I)
MISSINGFILE = re.compile(r'(?:File|Package|I can\'t find file|LaTeX Error: File)\s+[`\']?([^\'\"\s]+\.(?:sty|cls|bib|tex|png|pdf|eps))', re.I)
FLOAT_LARGE = re.compile(r'Float too large for page', re.I)
OVERFULL = re.compile(r'Overfull \\hbox', re.I)
EMERGENCY = re.compile(r'Emergency stop', re.I)


def classify(block):
    """返回 (category, root_cause, fix_hint, severity)。"""
    if UNDEREF.search(block):
        r = UNDEREF.search(block).group(1)
        return ('undefined_reference', '引用了未定义的 label: %s（或编译轮次不足）' % r,
                '补 \\label{%s} 或再编译一轮' % r, 'error')
    if UNDEFCITE.search(block):
        c = UNDEFCITE.search(block).group(1)
        return ('undefined_citation', '引用了未定义的文献条目: %s（或 bib 未处理）' % c,
                '补 bib 条目并运行 bibtex/biber', 'error')
    if UNDEFCTRL.search(block):
        m = re.search(r'\\([A-Za-z@]+)', block[block.find('!') + 1:])
        cmd = '\\' + m.group(1) if m else '某命令'
        return ('undefined_control_sequence', '使用了未定义的命令 %s（拼错或缺少提供它的宏包）' % cmd,
                '检查拼写；确认已 \\usepackage 提供该命令的宏包', 'error')
    if MISSINGFILE.search(block):
        f = MISSINGFILE.search(block).group(1)
        return ('missing_file', '缺少文件/宏包/类文件: %s' % f,
                '安装宏包或补全文件；检查文件名大小写与路径', 'error')
    if MISSINGFILE.search(block) or re.search(r'File .* not found', block, re.I):
        return ('missing_file', '引用了找不到的文件', '补全文件或修正路径', 'error')
    if re.search(r'Missing \$ inserted', block, re.I):
        return ('math_mode', '正文里出现数学符号但不在数学模式（漏 $ 或 \\(...\\)）',
                '用 $...$ 或 \\(...\\) 包裹数学内容', 'error')
    if re.search(r'Runaway argument', block, re.I):
        return ('runaway_argument', '命令参数未正确闭合（缺 } 或多写了 %）',
                '检查花括号配对与行尾注释', 'error')
    if re.search(r'There\'s no line here to end', block, re.I):
        return ('line_break', '在不该换行的地方用了 \\\\', '删除多余的 \\\\', 'error')
    if re.search(r'Undefined environment', block, re.I):
        m = re.search(r'Undefined environment\s+([^\.\s]+)', block, re.I)
        return ('undefined_env', '使用了未定义的环境 %s' % (m.group(1) if m else '?'),
                '确认环境名拼写与对应宏包', 'error')
    if re.search(r'Double subscript|Double superscript', block, re.I):
        return ('math_script', '数学上下标重复（如 x^2^3）', '用花括号明确指数范围 x^{2^3}', 'error')
    if re.search(r'!?\s*LaTeX Error:', block, re.I):
        m = re.search(r'LaTeX Error:\s*([^\.\n]+)', block, re.I)
        return ('latex_error', m.group(1).strip() if m else 'LaTeX 报错',
                '见日志上下文定位', 'error')
    if EMERGENCY.search(block):
        return ('emergency_stop', '编译紧急停止', '检查前一个错误的级联影响', 'error')
    return ('generic_error', block.strip().splitlines()[0][:160] if block.strip() else '未知错误',
            '见日志上下文', 'error')


def parse_log(log_text):
    """解析完整日志，返回所有错误块 + 警告 + 收敛信号。"""
    errs = []
    starts = [m.start() for m in ERROR_START.finditer(log_text)]
    # LaTeX 日志在切入文件时写 "(.../file.tex"；按 offset 追踪当前文件，
    # 供不含文件名的错误块（只有 l.<N>）回补。
    file_events = [(m.start(), m.group(1)) for m in
                   re.finditer(r'\(([^\s()]*[\w./-]+\.tex)', log_text)]
    def file_at(offset):
        cur = None
        for pos, fn in file_events:
            if pos <= offset:
                cur = fn
            else:
                break
        return cur
    for idx, st in enumerate(starts):
        en = starts[idx + 1] if idx + 1 < len(starts) else len(log_text)
        block = log_text[st:en]
        # 截断到下一个大段信息，避免块过长
        cut = re.search(r'Here is how much of TeX\'s memory|^\s*\[\d+', block[1:], re.M)
        if cut:
            block = block[:cut.start() + 1]
        lines = block.splitlines()
        msg = lines[0].lstrip('! ').strip()
        cat, cause, hint, sev = classify(block)
        # 行号：匹配 l.<N> / lines <N>，文件：块内首个 .tex
        lm = LINE_REF.search(block)
        line = int(lm.group(1)) if lm else None
        fm = FILE_REF.search(block)
        if not fm:
            fm = re.search(r'(\S+\.tex)', block)
        file = fm.group(1) if fm else file_at(st)
        errs.append({
            'index': len(errs), 'category': cat, 'severity': sev,
            'message': msg, 'root_cause': cause, 'fix_hint': hint,
            'file': file, 'line': line,
            'excerpt': '\n'.join(lines[:6])[:600],
        })

    undef_refs = sorted(set(UNDEREF.findall(log_text)))
    undef_cites = sorted(set(UNDEFCITE.findall(log_text)))
    rerun = sorted(set(m.group(0) for m in RERUN.finditer(log_text)))
    overfull = len(OVERFULL.findall(log_text))
    float_large = len(FLOAT_LARGE.findall(log_text))
    req_missing = sorted(set(m.group(1).lower() for m in REQ_MISSING.finditer(log_text)))

    warnings = []
    for c in undef_cites:
        warnings.append({'category': 'undefined_citation', 'message': 'Citation `%s` undefined' % c,
                         'fix_hint': '补 bib 条目并运行 bibtex/biber；确认 \\bibliography'})
    for r in undef_refs:
        warnings.append({'category': 'undefined_reference', 'message': 'Reference `%s` undefined' % r,
                         'fix_hint': '补 \\label 或修正引用；确认编译轮次足够'})
    for f in req_missing:
        warnings.append({'category': 'template_required_missing',
                         'message': '模板必填项缺失：\\%s 未提供' % f,
                         'fix_hint': '补 \\%s，否则版式不合模板要求' % f})
    for r in rerun:
        warnings.append({'category': 'rerun_needed', 'message': r,
                         'fix_hint': '再编译一轮直到该提示消失'})
    if overfull:
        warnings.append({'category': 'overfull_hbox', 'message': 'Overfull \\hbox 出现 %d 次' % overfull,
                         'fix_hint': '调整断行/列宽/字号，避免内容溢出页边'})
    if float_large:
        warnings.append({'category': 'float_too_large', 'message': 'Float too large 出现 %d 次' % float_large,
                         'fix_hint': '缩小表格图片或调整浮动体位置约束'})

    converged = not undef_refs and not undef_cites and not rerun and not errs and not req_missing
    return {
        'errors': errs, 'warnings': warnings,
        'undefined_refs': undef_refs, 'undefined_cites': undef_cites,
        'rerun_signals': rerun, 'overfull_count': overfull,
        'converged': converged,
    }


def build(root, engine, rounds, main, timeout, existing_log):
    result = {
        'root': root, 'engine': engine, 'main': main, 'requested_rounds': rounds,
        'engine_available': bool(shutil.which(engine)) if engine else False,
        'rounds_run': [], 'status': 'unknown',
    }
    log_text = None

    if existing_log:
        log_text = open(existing_log, encoding='utf-8', errors='replace').read()
        result['log_source'] = existing_log
        result['engine_available'] = result['engine_available'] or True
    elif engine and shutil.which(engine):
        work = os.path.join(root, '_build_w13')
        os.makedirs(work, exist_ok=True)
        # 支持 latexmk 或裸引擎；从 root 复制 .tex/.bib 到构建目录
        for fn in os.listdir(root):
            if fn.endswith(('.tex', '.bib', '.cls', '.sty', '.png', '.jpg', '.pdf')):
                src = os.path.join(root, fn)
                if os.path.isfile(src):
                    shutil.copy2(src, work)
        target = main or 'main.tex'
        if engine == 'latexmk':
            cmd = ['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error', target]
        elif engine == 'tectonic':
            cmd = ['tectonic', '-X', 'compile', target]
        else:
            cmd = [engine, '-interaction=nonstopmode', '-halt-on-error', target]
        for r in range(1, rounds + 1):
            rc = None
            try:
                proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=timeout)
                out = (proc.stdout or '') + '\n' + (proc.stderr or '')
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                out = 'TIMEOUT: 编译超过 %d 秒' % timeout
            log_path = os.path.join(work, '%s.round%d.log' % (target.replace('.tex', ''), r))
            with open(log_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(out)
            result['rounds_run'].append({'round': r, 'returncode': rc,
                                         'log': log_path})
            log_text = out
            # 判断收敛：无 rerun 信号且无错误
            parsed_so_far = parse_log(out)
            if parsed_so_far['converged']:
                break
        result['work_dir'] = work
        result['log_source'] = result['rounds_run'][-1]['log'] if result['rounds_run'] else None
    else:
        result['status'] = 'unavailable'
        result['log_source'] = None

    if log_text is not None:
        p = parse_log(log_text)
        result.update(p)
        if p['errors']:
            result['status'] = 'failed'
        elif not p['converged']:
            result['status'] = 'needs_more_rounds'
        else:
            result['status'] = 'success'
    else:
        result.update({
            'errors': [], 'warnings': [], 'undefined_refs': [], 'undefined_cites': [],
            'rerun_signals': [], 'converged': False,
            'note': '本机无 TeX 引擎且未提供 --log；无法判定编译结果，请用 --log 解析真实日志。',
        })
    result['summary'] = {
        'error_count': len(result['errors']),
        'warning_count': len(result['warnings']),
        'categories': sorted(set(e['category'] for e in result['errors'])),
        'converged': result['converged'],
    }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--out', required=True)
    ap.add_argument('--engine')
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--main')
    ap.add_argument('--log')
    ap.add_argument('--timeout', type=int, default=120)
    args = ap.parse_args()
    rep = build(os.path.abspath(args.root), args.engine, args.rounds, args.main, args.timeout, args.log)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps({'status': rep['status'], 'out': args.out,
                      'summary': rep['summary']}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
