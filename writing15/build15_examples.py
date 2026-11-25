#!/usr/bin/env python3
"""装配写作15的示例产物：case / result / baseline-result。

为什么用脚本装配：manuscript 字段必须是真实稿件的全文，手抄会与 md 不同步。
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(ROOT, 'examples')


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def dump(obj, p):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')


case = {
    'case_id': 'selftest-001',
    'task': ('依据课题指南与前期数据撰写开题报告：七要素齐全，研究问题可证伪，'
             '目标-路线-指标-成果一一对应，阶段计划落在给定周期与人力内，'
             '风险写触发信号与备选方案，论断挂引用。'),
    'discipline': '生物材料 / 骨组织工程',
    'cycle_months': 24,
    'capacity_pm': 36,
    'materials': 'examples/selftest-materials.md',
    'output_contract': ['manuscript', 'plan', 'sources', 'uncertainty', 'changes'],
}
dump(case, os.path.join(EX, 'selftest-case.json'))

plan = {
    'cycle_months': 24,
    'capacity_pm': 36,
    'capacity_note': '博士生 1 名 ×24 月 + 技术员 0.5 人 ×24 月',
    'goals': [
        {'id': 'G1', 'question': 'Q1', 'route': 'R2', 'metric': '孔隙率 ≥70%',
         'outcome': 'O1', 'deadline_month': 9},
        {'id': 'G2', 'question': 'Q1', 'route': 'R3', 'metric': 'd33 ≥5 pC/N',
         'outcome': 'O2', 'deadline_month': 12},
        {'id': 'G3', 'question': 'Q2', 'route': 'R3', 'metric': 'ALP 活性 ≥30%',
         'outcome': 'O3', 'deadline_month': 18},
    ],
    'routes': [
        {'id': 'R1', 'step': '熔融沉积成型制备三组支架', 'input': 'PLA 粒料 + BaTiO3 粉体',
         'output': 'Φ10×5 mm 圆柱试样 24 件/组'},
        {'id': 'R2', 'step': '微型 CT 测孔隙率 + 单轴压缩测模量', 'input': 'R1 试样',
         'output': '每组均值与标准差'},
        {'id': 'R3', 'step': '准静态 d33 + MC3T3-E1 细胞 ALP 活性', 'input': 'R2 合格试样',
         'output': '剂量-响应数据表'},
        {'id': 'R4', 'step': '兔股骨髁缺损模型体内验证', 'input': 'R3 有明确响应时启动',
         'output': '8/12 周成骨率'},
    ],
    'milestones': [
        {'id': 'M1', 'name': '工艺定型与试样制备', 'start': 1, 'end': 6, 'effort': 9},
        {'id': 'M2', 'name': '结构力学表征与 d33 测量', 'start': 7, 'end': 12, 'effort': 9},
        {'id': 'M3', 'name': '体外细胞实验与剂量-响应分析', 'start': 13, 'end': 18, 'effort': 9},
        {'id': 'M4', 'name': '体内验证与数据整合', 'start': 19, 'end': 24, 'effort': 9},
    ],
    'risks': [
        {'id': 'K1', 'type': '数据获取', 'trigger': '第 8 月合格试样数 < 计划 60%',
         'impact': 'R2/R3 统计', 'fallback': '启用第二台打印机并外协加工', 'decision': '第 8 月末'},
        {'id': 'K2', 'type': '方法可行性', 'trigger': '同批 d33 变异系数 > 15%',
         'impact': 'G2 曲线可信度', 'fallback': '改动态法并增加平行样', 'decision': '第 10 月'},
        {'id': 'K3', 'type': '进度', 'trigger': '第 16 月未取得动物伦理批件',
         'impact': 'R4 与 M4 后半段', 'fallback': 'R4 降级为体外机制实验', 'decision': '第 16 月末'},
        {'id': 'K4', 'type': '伦理合规', 'trigger': '细胞检定报告缺失或支原体不合格',
         'impact': 'R3 全部数据', 'fallback': '更换已检定批次并重做对照', 'decision': 'R3 启动前'},
        {'id': 'K5', 'type': '数据获取', 'trigger': '两批粉体中位径相差 > 20%',
         'impact': '组间可比性', 'fallback': '统一批次并做批间校正', 'decision': '每批入库时'},
    ],
    'budget': [
        {'item': 'BaTiO3 粉体与 PLA 粒料', 'amount_wan': 8},
        {'item': '打印与测试机时', 'amount_wan': 14},
        {'item': '细胞与动物实验', 'amount_wan': 20},
        {'item': '人员与差旅', 'amount_wan': 18},
    ],
    'budget_total_wan': 60,
}

sources = [
    {'id': 'S1', 'locator': '[1] 骨移植流行病学综述', 'use': '年手术量 200 万例'},
    {'id': 'S2', 'locator': '[2] 自体骨移植并发症', 'use': '供区并发症 8%–12%'},
    {'id': 'S3', 'locator': '[4] PLA 支架力学综述', 'use': '模量 3–8 MPa、孔隙率 70%–85%'},
    {'id': 'S4', 'locator': '[6] BaTiO3 压电性能', 'use': 'd33 约 190 pC/N'},
    {'id': 'S5', 'locator': '[7][8] 既有工作', 'use': '缺口依据：两项指标未同时量化'},
    {'id': 'S6', 'locator': '[9] 前期工艺参数', 'use': 'R1 打印温度与分散方案'},
    {'id': 'S7', 'locator': '[10] ISO 13314', 'use': '压缩测试标准与加载速率'},
    {'id': 'S8', 'locator': '[11] 机构伦理与生物安全规定', 'use': 'R3 细胞实验合规依据'},
]

uncertainty = [
    {'item': 'in-vivo 步骤', 'status': 'undetermined',
     'note': 'R4 是否启动取决于 R3 是否出现明确剂量-响应，计划中已写决策条件'},
    {'item': '人力口径', 'status': 'needs_human',
     'note': 'capacity_pm=36 按「博士生 24 月 + 技术员 0.5×24 月」折算，若实际配置不同需重算'},
    {'item': '经费', 'status': 'not_reported',
     'note': '材料未给经费上限，预算按 60 万元估算，仅作相容性校验，不作申报依据'},
]

changes = [
    {'kind': '要素', 'detail': '七要素按「背景-问题-目标-路线-计划-风险-成果」顺序落节，节名与检查表一致'},
    {'kind': '问题', 'detail': 'Q1/Q2 均改写为含指标、阈值、对照与时间点的可证伪表述'},
    {'kind': '对齐', 'detail': 'G1→R2/O1、G2→R3/O2、G3→R3/O3 三组一一映射写入 plan'},
    {'kind': '计划', 'detail': '四个里程碑首尾相接覆盖 1–24 月，工作量 36 人月 = 可用人力'},
    {'kind': '风险', 'detail': '五条风险各带触发信号、影响范围、备选方案与决策时点，覆盖四类'},
]

result = {
    'case_id': 'selftest-001',
    'status': 'success',
    'result': {
        'manuscript': read(os.path.join(EX, 'selftest-proposal.md')),
        'plan': plan,
        'output_contract': {k: True for k in case['output_contract']},
    },
    'sources': sources,
    'uncertainty': uncertainty,
    'changes': changes,
}
dump(result, os.path.join(EX, 'selftest-result.json'))

baseline = json.loads(json.dumps(result))
baseline['result']['manuscript'] = read(os.path.join(EX, 'baseline-proposal.md'))
baseline['result']['plan'] = {
    'cycle_months': 24,
    'capacity_pm': 36,
    'goals': [
        {'id': 'G1', 'question': '探究压电支架对成骨的影响', 'route': 'R1',
         'metric': '观察成骨效果', 'outcome': ''},
        {'id': 'G2', 'question': '探究填料的影响', 'route': 'R9',
         'metric': '评价性能', 'outcome': ''},
    ],
    'routes': [
        {'id': 'R1', 'step': '制备支架并做细胞实验', 'input': '原料', 'output': '结果'},
    ],
    'milestones': [
        {'id': 'M1', 'name': '前期准备', 'start': 1, 'end': 8, 'effort': 20},
        {'id': 'M2', 'name': '实验开展', 'start': 8, 'end': 20, 'effort': 22},
    ],
    'risks': [
        {'id': 'K1', 'type': '风险', 'trigger': '', 'impact': '', 'fallback': '', 'decision': ''},
        {'id': 'K2', 'type': '风险', 'trigger': '', 'impact': '', 'fallback': '', 'decision': ''},
    ],
}
baseline['uncertainty'] = []
baseline['changes'] = []
dump(baseline, os.path.join(EX, 'baseline-result.json'))

print('wrote selftest-case.json / selftest-result.json / baseline-result.json')
