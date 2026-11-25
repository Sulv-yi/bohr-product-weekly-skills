#!/usr/bin/env python3
"""落七要素骨架：按固定节名把大纲铺好，每节留最小字数提示。

为什么先落骨架：七要素是硬门槛（缺一节就掉分），而"边写边想结构"最容易漏掉
风险与预期成果两节。骨架把节名固化成可与检查表对齐的形式，漏节会立刻暴露。

用法：
  python draft_outline.py --out /app/work/proposal.md [--case /input/case.json] \
      [--cycle 24] [--capacity 36]
"""
import argparse
import json
import os
import sys

SECTIONS = [
    ('研究背景与立项依据', 350,
     '已知结论（挂引用）→ 未知（缺口句）→ 待验证（本课题）'),
    ('研究问题与可证伪假设', 150,
     'Q1/Q2 各写：指标 + 阈值 + 对照/时间点'),
    ('研究目标', 150,
     'G1–G3 各写：可考核指标 + 交付时点'),
    ('技术路线', 300,
     'R1–Rn 各写：输入 → 处理 → 输出；标串行依赖与关键路径'),
    ('阶段计划', 150,
     'M1–Mn 各写：起止月 + 工作量（人月）；合计 ≤ 可用人力'),
    ('风险与备选方案', 150,
     '每条写：触发信号 + 影响范围 + 备选方案 + 决策时点'),
    ('预期成果与考核方式', 120,
     'O1–On 各写：交付形式 + 考核方式'),
]

PLAN_STUB = {
    'cycle_months': 0,
    'capacity_pm': 0,
    'goals': [{'id': 'G1', 'question': 'Q1', 'route': 'R1', 'metric': '', 'outcome': 'O1',
               'deadline_month': 0}],
    'routes': [{'id': 'R1', 'step': '', 'input': '', 'output': ''}],
    'milestones': [{'id': 'M1', 'name': '', 'start': 1, 'end': 0, 'effort': 0}],
    'risks': [{'id': 'K1', 'type': '', 'trigger': '', 'impact': '', 'fallback': '',
               'decision': ''}],
}


def main():
    ap = argparse.ArgumentParser(description='生成开题报告七要素骨架')
    ap.add_argument('--out', required=True)
    ap.add_argument('--case')
    ap.add_argument('--cycle', type=int, default=0)
    ap.add_argument('--capacity', type=float, default=0)
    ap.add_argument('--plan-out', help='同时落一份 plan.json 空模板')
    a = ap.parse_args()

    cycle, cap = a.cycle, a.capacity
    if a.case and os.path.isfile(a.case):
        case = json.load(open(a.case, encoding='utf-8'))
        cycle = cycle or int(case.get('cycle_months') or 0)
        cap = cap or float(case.get('capacity_pm') or 0)

    lines = ['# 开题报告', '',
             f'> 周期 {cycle or "TBD"} 个月；可用人力 {cap or "TBD"} 人月。'
             '每节最低字数见括号，写完跑 validate_result.py。', '']
    for name, need, hint in SECTIONS:
        lines += ['## %s（≥%d 字）' % (name, need), '', '<!-- %s -->' % hint, '',
                  '（本节内容）', '']
    lines += ['## 数据与材料可得性', '', '（数据归档方式与共享限制）', '']

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or '.', exist_ok=True)
    open(a.out, 'w', encoding='utf-8').write('\n'.join(lines))

    if a.plan_out:
        stub = json.loads(json.dumps(PLAN_STUB))
        stub['cycle_months'] = cycle
        stub['capacity_pm'] = cap
        os.makedirs(os.path.dirname(os.path.abspath(a.plan_out)) or '.', exist_ok=True)
        json.dump(stub, open(a.plan_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        open(a.plan_out, 'a', encoding='utf-8').write('\n')

    print(json.dumps({'out': a.out, 'sections': [s[0] for s in SECTIONS],
                      'cycle_months': cycle, 'capacity_pm': cap,
                      'plan_out': a.plan_out}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
