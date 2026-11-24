#!/usr/bin/env python3
"""探查 LaTeX 工程与可用 TeX 发行版/引擎，产出可复现构建所需的环境清单骨架。

不臆造软件状态：检查不到引擎/宏包就如实写 null / missing，交给上层标注不确定。
输出 project.json：engines / selected_engine / packages / files / template / fonts / warnings。

用法:
    python3 probe_project.py <工程根目录> --out project.json [--engine pdflatex]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

ENGINES = ['latexmk', 'pdflatex', 'xelatex', 'lualatex', 'tectonic', 'bibtex', 'biber']

PKG_USE = re.compile(r'\\usepackage(?:\[[^\]]*\])?\s*\{([^}]+)\}')
DOC_CLASS = re.compile(r'\\documentclass(?:\[[^\]]*\])?\s*\{([^}]+)\}')
INPUT_RE = re.compile(r'\\(?:input|include)\s*\{([^}]+)\}')
GFX_RE = re.compile(r'\\includegraphics(?:\[[^\]]*\])?\s*\{([^}]+)\}')
BIB_RE = re.compile(r'\\bibliography\s*\{([^}]+)\}')


def which(exe):
    return shutil.which(exe)


def version(exe):
    try:
        p = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=10)
        out = (p.stdout or p.stderr).splitlines()
        return ' '.join(out[:2]).strip()[:300] if out else ''
    except Exception:
        return ''


def scan_tex(root):
    tex_files, all_files = [], []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.git', 'build', '_build', '__pycache__')]
        for fn in files:
            rel = os.path.relpath(os.path.join(base, fn), root).replace('\\', '/')
            all_files.append(rel)
            if fn.endswith('.tex'):
                tex_files.append(rel)
    return sorted(all_files), sorted(tex_files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--out', required=True)
    ap.add_argument('--engine')
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    engines = {}
    for e in ENGINES:
        path = which(e)
        engines[e] = {'path': path, 'version': version(e) if path else None}

    all_files, tex_files = scan_tex(root)

    # 找主文件：含 \documentclass 的 .tex
    main_file, doc_class, packages = None, None, []
    for rel in tex_files:
        txt = open(os.path.join(root, rel), encoding='utf-8', errors='replace').read()
        m = DOC_CLASS.search(txt)
        if m and not main_file:
            main_file = rel
            doc_class = m.group(1)
            packages = [p.strip() for grp in PKG_USE.findall(txt) for p in grp.split(',') if p.strip()]

    # 结构依赖
    inputs, graphics, bibs = set(), set(), set()
    for rel in tex_files:
        txt = open(os.path.join(root, rel), encoding='utf-8', errors='replace').read()
        for x in INPUT_RE.findall(txt):
            inputs.add(x if x.endswith('.tex') else x + '.tex')
        for x in GFX_RE.findall(txt):
            graphics.add(x)
        for grp in BIB_RE.findall(txt):
            for b in grp.split(','):
                bibs.add(b.strip() if b.strip().endswith('.bib') else b.strip() + '.bib')

    def present(name):
        return any(f.replace('\\', '/').endswith(name.replace('\\', '/')) for f in all_files)

    missing_inputs = sorted(x for x in inputs if not present(x))
    missing_gfx = sorted(x for x in graphics if not present(x))
    missing_bibs = sorted(x for x in bibs if not present(x))

    selected = args.engine or ('latexmk' if which('latexmk') else
                               'xelatex' if which('xelatex') else
                               'pdflatex' if which('pdflatex') else
                               'tectonic' if which('tectonic') else None)

    warnings = []
    if not selected:
        warnings.append('未检测到任何 TeX 引擎，编译步骤无法在本机执行；仅能做静态检查')
    if missing_inputs:
        warnings.append('缺失 input 文件: ' + ', '.join(missing_inputs))
    if missing_bibs:
        warnings.append('缺失 bib 文件: ' + ', '.join(missing_bibs))

    out = {
        'root': root,
        'engines': engines,
        'selected_engine': selected,
        'main_file': main_file,
        'document_class': doc_class,
        'is_template': bool(doc_class and doc_class not in ('article', 'report', 'book', 'beamer', 'letter')),
        'packages': sorted(set(packages)),
        'files': {'all': all_files, 'tex': tex_files},
        'dependencies': {
            'inputs': sorted(inputs), 'graphics': sorted(graphics), 'bib': sorted(bibs),
            'missing_inputs': missing_inputs, 'missing_graphics': missing_gfx, 'missing_bib': missing_bibs,
        },
        'fonts': [],  # 由上层按 \setmainfont 等填写，不猜测
        'warnings': warnings,
        'status': 'ok' if not missing_inputs and not missing_bibs else 'incomplete',
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        'status': out['status'], 'out': args.out,
        'selected_engine': selected, 'main_file': main_file,
        'document_class': doc_class, 'tex_files': len(tex_files),
        'warnings': warnings,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
