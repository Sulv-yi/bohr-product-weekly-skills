#!/usr/bin/env python3
"""落双语骨架：把原文按 Pxx 切好，`ZH` 位留待译标记。

为什么先落骨架再译：段号是后续所有核查（术语、数值、标记、边界）的主键。
先有骨架，漏段会立刻暴露成 `[待译]`；对着整篇原文自由发挥则很难事后发现少译一段。

用法：
  python draft_bilingual.py --case /input/case.json --out /app/work/bilingual.md
  python draft_bilingual.py --materials /input/source.md --out ... --prefix P
"""
import argparse
import json
import os
import re
import sys


def split_source(text):
    """按 `## Pxx` 或 `## 1.` 之类的编号切段；没有编号就按空行切。"""
    ms = list(re.finditer(r'^\s{0,3}(?:#{2,4}\s*)?\[?(P?\d{1,3})\]?\s*$', text or '', re.M))
    if ms:
        out = []
        for i, m in enumerate(ms):
            end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
            body = text[m.end():end].strip()
            body = re.sub(r'^\s*(?:EN|原文|Source)\s*[:：]\s*', '', body, flags=re.M)
            pid = m.group(1)
            if not pid.startswith('P'):
                pid = 'P%02d' % int(pid)
            out.append((pid, body.strip()))
        return out
    paras = [p.strip() for p in re.split(r'\n\s*\n', text or '') if p.strip()]
    return [('P%02d' % (i + 1), p) for i, p in enumerate(paras)]


def main():
    ap = argparse.ArgumentParser(description='生成双语对照骨架')
    ap.add_argument('--case')
    ap.add_argument('--materials')
    ap.add_argument('--out', required=True)
    ap.add_argument('--target', default='ZH')
    a = ap.parse_args()

    src = a.materials
    if not src and a.case:
        case = json.load(open(a.case, encoding='utf-8'))
        src = case.get('materials') or (case.get('input') or {}).get('materials')
        base = os.path.dirname(os.path.abspath(a.case))
        if src and not os.path.isabs(src):
            cand = os.path.join(base, src)
            src = cand if os.path.exists(cand) else src
    if not src or not os.path.exists(src):
        print('找不到原文材料，请用 --materials 指定路径', file=sys.stderr)
        return 2

    segs = split_source(open(src, encoding='utf-8').read())
    lines = ['# 双语对照稿（骨架）', '',
             '> 每个 `Pxx` 为一个对齐单元；`ZH` 位填译文，译完再跑 validate_result.py。', '']
    for pid, body in segs:
        lines += ['## %s' % pid, '', 'EN: ' + ' '.join(body.split()), '',
                  '%s: [待译]' % a.target, '']
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or '.', exist_ok=True)
    open(a.out, 'w', encoding='utf-8').write('\n'.join(lines))
    print(json.dumps({'out': a.out, 'segments': len(segs),
                      'ids': [p for p, _b in segs]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
