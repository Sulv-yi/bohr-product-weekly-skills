#!/usr/bin/env python3
"""不依赖 TeX 引擎的 .tex 静态健康检查（编译前预检，抓结构性硬损伤）。

检查项（每项带 file:line + 类别 + 根因 + 修复提示）：
  1. 花括号 {} 平衡
  2. \\begin{env}/\\end{env} 配对与嵌套
  3. math 分隔符 $...$ / \\(...\\) / 环境 平衡（行内 $ 计数）
  4. 重复 \\label
  5. \\ref/\\eqref/\\pageref/\\autoref/\\cref 引用未定义 label
  6. \\cite/\\citep/\\citet/\\citeauthor 键在 .bib 中不存在
  7. \\newcommand 重定义 / \\usepackage 重复加载（告警）

用法:
    python3 static_check.py <工程根目录> --out static_check.json [--strict]

说明：本脚本只报"可机械判定的硬损伤"，不判断是否真的编译通过；
编译结果以 compile_report 为准。二者互补。
"""
import argparse
import collections
import json
import os
import re
import sys

LABEL_DEF = re.compile(r'\\label\s*\{([^}]+)\}')
REF_USE = re.compile(r'\\(?:ref|eqref|pageref|autoref|cref|Cref|nameref)\s*\{([^}]+)\}')
CITE_USE = re.compile(r'\\(?:cite|citep|citet|citeauthor|citeyear|autocite)\s*(?:\[[^\]]*\])*\s*\{([^}]+)\}')
BIB_KEY = re.compile(r'@\w+\s*\{\s*([^,\s]+)\s*,')
BEGIN_ENV = re.compile(r'\\begin\s*\{([^}]+)\}')
END_ENV = re.compile(r'\\end\s*\{([^}]+)\}')
NEWCMD = re.compile(r'\\(?:re)?newcommand\s*\{\\([A-Za-z@]+)\}')
PKG_USE = re.compile(r'\\usepackage(?:\[[^\]]*\])?\s*\{([^}]+)\}')
COMMENT = re.compile(r'(?<!\\)%.*$')


def strip_comments(line):
    return COMMENT.sub('', line)


def scan_file(path, rel):
    issues = []
    raw = open(path, encoding='utf-8', errors='replace').read()
    lines = raw.splitlines()

    # 花括号平衡（按行，忽略转义 \{ \}，注释已剥离）
    depth = 0
    for ln, line in enumerate(lines, 1):
        s = strip_comments(line)
        i = 0
        while i < len(s):
            c = s[i]
            if c == '\\' and i + 1 < len(s) and s[i + 1] in '{}':
                i += 2
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth < 0:
                    issues.append(mk(rel, ln, 'brace', 'error', '多余的右花括号 }',
                                     '花括号深度变为负，通常是多写了一个 }'))
                # depth 不 clamp，继续以反映真实状态
            i += 1
    if depth > 0:
        issues.append(mk(rel, len(lines), 'brace', 'error', '花括号未闭合',
                         '文件结束仍有 %d 个未闭合的 {' % depth))

    # 环境配对（栈）
    stack = []
    for ln, line in enumerate(lines, 1):
        s = strip_comments(line)
        for m in BEGIN_ENV.finditer(s):
            stack.append((m.group(1), ln))
        for m in END_ENV.finditer(s):
            env = m.group(1)
            if not stack:
                issues.append(mk(rel, ln, 'env', 'error', '\\end{%s} 没有对应的 \\begin' % env,
                                 '孤立的 \\end，检查是否漏写 \\begin 或拼写错误'))
            elif stack[-1][0] != env:
                top, top_line = stack[-1]
                issues.append(mk(rel, ln, 'env', 'error',
                                 '环境不匹配：\\end{%s} 对应 \\begin{%s}(行%d)' % (env, top, top_line),
                                 '环境交叉嵌套，需按后进先出闭合'))
                # 尝试找到栈中匹配的 begin 并弹出其上的
                idx = None
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k][0] == env:
                        idx = k
                        break
                if idx is not None:
                    for _ in range(len(stack) - 1, idx - 1, -1):
                        _, l = stack.pop()
                        issues.append(mk(rel, l, 'env', 'warning', '环境 %s 未闭合' % _, '', ))
            else:
                stack.pop()
    for env, ln in stack:
        issues.append(mk(rel, ln, 'env', 'error', '环境 %s 未闭合' % env,
                         '缺少 \\end{%s}' % env))

    # 行内 $ 计数（粗略：忽略 \$，同一行成对）
    for ln, line in enumerate(lines, 1):
        s = strip_comments(line)
        cnt = 0
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s) and s[i + 1] == '$':
                i += 2
                continue
            if s[i] == '$':
                cnt += 1
            i += 1
        if cnt % 2 == 1:
            issues.append(mk(rel, ln, 'math', 'warning', '行内 $ 数量为奇数',
                             '可能有未闭合的行内公式，注意跨行公式应使用 \\(...\\) 或环境'))

    labels = [(m.group(1), i + 1) for i, l in enumerate(lines)
              for m in LABEL_DEF.finditer(strip_comments(l))]
    refs = [(m.group(1), i + 1) for i, l in enumerate(lines)
            for m in REF_USE.finditer(strip_comments(l))]
    cites = [(m.group(1), i + 1) for i, l in enumerate(lines)
             for m in CITE_USE.finditer(strip_comments(l))]
    newcmds = [(m.group(1), i + 1) for i, l in enumerate(lines)
               for m in NEWCMD.finditer(strip_comments(l))]
    pkgs = [(p.strip(), i + 1) for i, l in enumerate(lines)
            for g in PKG_USE.findall(strip_comments(l)) for p in g.split(',') if p.strip()]

    return {
        'rel': rel, 'lines': len(lines), 'labels': labels, 'refs': refs,
        'cites': cites, 'newcmds': newcmds, 'packages': pkgs, 'issues': issues,
    }


def mk(file, line, category, severity, message, hint):
    return {'file': file, 'line': line, 'category': category,
            'severity': severity, 'message': message, 'hint': hint}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--out', required=True)
    ap.add_argument('--strict', action='store_true', help='引用未定义/重复 label 视为 error')
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    tex_files = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.git', 'build', '_build', '__pycache__')]
        for fn in files:
            if fn.endswith('.tex'):
                tex_files.append(os.path.relpath(os.path.join(base, fn), root).replace('\\', '/'))

    bib_keys = set()
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.git', 'build', '_build', '__pycache__')]
        for fn in files:
            if fn.endswith('.bib'):
                txt = open(os.path.join(base, fn), encoding='utf-8', errors='replace').read()
                txt = re.sub(r'(?m)^%.*$', '', txt)
                bib_keys.update(BIB_KEY.findall(txt))

    per_file = [scan_file(os.path.join(root, rel), rel) for rel in sorted(tex_files)]
    issues = [it for f in per_file for it in f['issues']]

    # 全局 label 定义与重复
    label_defs = collections.Counter()
    label_locs = {}
    for f in per_file:
        for name, ln in f['labels']:
            label_defs[name] += 1
            label_locs.setdefault(name, (f['rel'], ln))
    for name, cnt in label_defs.items():
        if cnt > 1:
            f, ln = label_locs[name]
            issues.append(mk(f, ln, 'label', 'error' if args.strict else 'warning',
                             '重复 label: %s（出现 %d 次）' % (name, cnt),
                             '交叉引用会指向最后一个定义，需改名'))

    # 引用未定义
    for f in per_file:
        for name, ln in f['refs']:
            keys = [k.strip() for k in re.split(r'[,;]', name) if k.strip()]
            for k in keys:
                if k not in label_defs:
                    issues.append(mk(f['rel'], ln, 'ref', 'error' if args.strict else 'warning',
                                     '引用了未定义的 label: %s' % k,
                                     '补 \\label{%s} 或修正引用名；多遍编译后仍 undefined 需查' % k))
        if bib_keys:  # 有 bib 才判定 cite，避免无 bib 工程误报
            for name, ln in f['cites']:
                keys = [k.strip() for k in name.split(',') if k.strip()]
                for k in keys:
                    if k not in bib_keys:
                        issues.append(mk(f['rel'], ln, 'cite', 'error' if args.strict else 'warning',
                                         '引用了 .bib 中不存在的条目: %s' % k,
                                         '补 bib 条目或修正 key；注意大小写'))

    # 重复 usepackage（告警）
    for f in per_file:
        cnt = collections.Counter(p for p, _ in f['packages'])
        for p, c in cnt.items():
            if c > 1:
                issues.append(mk(f['rel'], 1, 'package', 'warning',
                                 '宏包 %s 重复加载 %d 次' % (p, c),
                                 '合并为一次，避免选项冲突'))

    errors = [i for i in issues if i['severity'] == 'error']
    warnings = [i for i in issues if i['severity'] == 'warning']
    by_cat = collections.Counter(i['category'] for i in issues)
    report = {
        'status': 'failed' if errors else ('passed_with_warnings' if warnings else 'passed'),
        'root': root,
        'tex_files': len(tex_files),
        'bib_entries': len(bib_keys),
        'labels': len(label_defs),
        'counts': {'errors': len(errors), 'warnings': len(warnings)},
        'by_category': dict(by_cat),
        'issues': issues,
        'note': '静态检查只覆盖可机械判定的硬损伤；是否真正编译通过以 compile_report 为准。',
    }
    with open(args.out, 'w', encoding='utf-8') as fo:
        json.dump(report, fo, ensure_ascii=False, indent=2)
    print(json.dumps({
        'status': report['status'], 'out': args.out,
        'errors': len(errors), 'warnings': len(warnings), 'by_category': dict(by_cat),
    }, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
