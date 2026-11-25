#!/usr/bin/env python3
"""生成可核验附件：element-map.csv / alignment.csv / schedule.csv / risk.csv / selfcheck.md / preview.pdf。

为什么这几张表必须有：开题方案的"对得上""排得开""说得清"都是相对输入材料的判断，
评审要能按行核对——哪个目标挂在哪条路线、哪个月归哪个里程碑、哪条风险缺哪个字段。

用法：
  python build_outputs.py --result /app/output/result.json --text /app/output/proposal.md \
      --outdir /app/output [--min-chars 1400]
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proposal_gate import (element_map, gap_specific, falsifiable, alignment, schedule,
                           risks, binding_rate, placeholders, _nchars,
                           split_sections)  # noqa: E402


def write_csv(path, header, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def render_preview(md, outdir):
    import shutil as _sh
    if not _sh.which('pandoc'):
        return 'skipped: 环境无 pandoc'
    out = os.path.join(outdir, 'preview.pdf')
    try:
        r = subprocess.run(['pandoc', md, '-o', out, '--pdf-engine=xelatex',
                            '-V', 'CJKmainfont=SimSun'], capture_output=True, timeout=180)
        return 'ok: preview.pdf' if r.returncode == 0 else 'failed: pandoc 返回 %d' % r.returncode
    except Exception as e:  # noqa: BLE001
        return 'failed: %s' % e


def main():
    ap = argparse.ArgumentParser(description='生成要素表 / 对齐表 / 排期表 / 风险表 / 自查 / 预览')
    ap.add_argument('--result', required=True)
    ap.add_argument('--text')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--min-chars', type=int, default=1400)
    a = ap.parse_args()

    res = json.load(open(a.result, encoding='utf-8'))
    body = open(a.text, encoding='utf-8').read() if a.text else res['result']['manuscript']
    plan = res['result'].get('plan') or {}
    os.makedirs(a.outdir, exist_ok=True)

    emap = element_map(body)
    write_csv(os.path.join(a.outdir, 'element-map.csv'),
              ['element', 'present', 'chars', 'need'],
              [[k, 'yes' if v[0] else 'NO', v[1], v[2]] for k, v in emap.items()])

    align, align_bad = alignment(plan, body)
    rows = []
    for g in plan.get('goals') or []:
        rows.append([g.get('id'), g.get('question'), g.get('route'), g.get('metric'),
                     g.get('outcome'), g.get('deadline_month'),
                     'ok' if g.get('id', '') not in ' '.join(align_bad) else 'CHECK'])
    write_csv(os.path.join(a.outdir, 'alignment.csv'),
              ['goal', 'question', 'route', 'metric', 'outcome', 'deadline_month', 'status'], rows)

    sch = schedule(plan)
    rows = [[m.get('id'), m.get('name'), m.get('start'), m.get('end'), m.get('effort')]
            for m in (plan.get('milestones') or [])]
    write_csv(os.path.join(a.outdir, 'schedule.csv'),
              ['milestone', 'name', 'start_month', 'end_month', 'effort_pm'], rows)

    write_csv(os.path.join(a.outdir, 'risk.csv'),
              ['risk', 'type', 'trigger', 'impact', 'fallback', 'decision'],
              [[r.get('id'), r.get('type'), r.get('trigger'), r.get('impact'),
                r.get('fallback'), r.get('decision')] for r in (plan.get('risks') or [])])

    q_text = ''
    for _l, title, b in split_sections(body):
        if re.search(r'研究问题|问题定义|科学问题', title or '') and _nchars(b) > _nchars(q_text):
            q_text = b
    gap_ok, gap_note = gap_specific(body, q_text)
    fal_ok, fal_note = falsifiable(q_text)
    rk_ok, rk_n, rk_bad = risks(plan)
    bind, bh, bt = binding_rate(body)
    preview = render_preview(os.path.abspath(a.text), a.outdir) if a.text else 'skipped: 未提供 md'
    elems_ok = sum(1 for v in emap.values() if v[0])

    lines = ['# 自查（自动生成）', '',
             f"- 字数：{_nchars(body)}；要素：{elems_ok}/{len(emap)}",
             f"- 立得住：缺口{'具体' if gap_ok else '空泛'}（{gap_note}）；问题{'可证伪' if fal_ok else '不可证伪'}（{fal_note}）",
             f"- 对得上：目标-路线-指标-成果对齐 {align:.0%}" + (f"；待核 {align_bad}" if align_bad else ''),
             f"- 排得开：周期覆盖 {'是' if sch['coverage'] else '否'}；空月 {sch.get('gaps')}；"
             f"重叠 {sch['overlap']}；工作量/人力 {sch['effort_ratio']}",
             f"- 说得清：风险完备 {rk_ok:.0%}，覆盖 {rk_n}/4 类；论断挂引用 {bind:.0%}（{bh}/{bt}）",
             f"- 占位符：{len(placeholders(body))}",
             f"- 预览：{preview}", '']
    if align_bad:
        lines += ['## 对齐待核', ''] + [f"- {x}" for x in align_bad] + ['']
    if rk_bad:
        lines += ['## 风险缺项', ''] + [f"- {x}" for x in rk_bad] + ['']
    chk = os.path.join(a.outdir, 'selfcheck.md')
    open(chk, 'w', encoding='utf-8').write('\n'.join(lines))

    print(json.dumps({'element_map': os.path.join(a.outdir, 'element-map.csv'),
                      'alignment': os.path.join(a.outdir, 'alignment.csv'),
                      'schedule': os.path.join(a.outdir, 'schedule.csv'),
                      'risk': os.path.join(a.outdir, 'risk.csv'),
                      'selfcheck': chk, 'preview': preview,
                      'total_chars': _nchars(body), 'elements_ok': elems_ok,
                      'gap_specific': gap_ok, 'falsifiable': fal_ok,
                      'alignment_rate': align, 'schedule_coverage': sch['coverage'],
                      'schedule_overlap': sch['overlap'], 'effort_ratio': sch['effort_ratio'],
                      'risk_complete': rk_ok, 'risk_types': rk_n, 'binding_rate': bind},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
