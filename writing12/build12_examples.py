#!/usr/bin/env python3
"""装配写作12的示例产物：case / result / baseline-result。

为什么用脚本装配而不是手写 JSON：bilingual 字段必须是真实交付稿的全文，
手抄一份会与 md 不同步；这里直接读 md 落进 JSON，保证二者逐字一致。
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
    'task': ('把节选英文学术稿逐段译为中文，输出段级双语对照稿；锁定领域术语；'
             '数值、引用、图表与公式标记原样保留；不改否定范围与情态强度。'),
    'source_lang': 'en',
    'target_lang': 'zh',
    'segments': ['P%02d' % i for i in range(1, 11)],
    'materials': 'examples/selftest-materials.md',
    'output_contract': ['bilingual', 'terms', 'human_review', 'uncertainty', 'changes'],
}
dump(case, os.path.join(EX, 'selftest-case.json'))

terms = json.load(open(os.path.join(EX, 'term-table.json'), encoding='utf-8'))['terms']

sources = [
    {'id': 'S1', 'locator': 'examples/selftest-materials.md P01–P10',
     'kind': '原文', 'use': '所有译文段的唯一事实来源'},
    {'id': 'S2', 'locator': 'examples/term-table.json',
     'kind': '术语表', 'use': '13 条锁定译法与禁用漂移写法'},
]

uncertainty = [
    {'item': 'P05 d33', 'status': 'needs_human', 'note': '张量分量写法保留原符号，未中文化'},
    {'item': 'P08 pilot cohort', 'status': 'needs_human',
     'note': '译为「预实验队列」；若原意为探索性队列需按团队惯例替换'},
    {'item': 'P10 DOI', 'status': 'not_translated', 'note': 'DOI 为标识符，按原样保留'},
]

changes = [
    {'seg': 'P01', 'kind': '术语', 'detail': 'scaffolds → 支架（锁定），未用「脚手架」'},
    {'seg': 'P03', 'kind': '数值', 'detail': '62.4 / 78.3 / 71.6 / 0.012 原样，未取整'},
    {'seg': 'P05', 'kind': '标记', 'detail': '[12,13–15] 与 (Zhang et al., 2021) 原样保留'},
    {'seg': 'P06', 'kind': '公式', 'detail': '$E = \\sigma / \\varepsilon$ 原样，未改排版'},
    {'seg': 'P07', 'kind': '边界', 'detail': 'may be associated with → 可能与…有关（未升级为因果）'},
    {'seg': 'P08', 'kind': '边界', 'detail': 'in vitro / single-centre / pilot 三项限定条件全部保留'},
]

result = {
    'case_id': 'selftest-001',
    'status': 'success',
    'result': {
        'target_lang': 'zh',
        'bilingual': read(os.path.join(EX, 'selftest-bilingual.md')),
        'terms': terms,
        'human_review': ['P05 d33 写法', 'P08 pilot cohort 用词', 'P10 DOI 原样'],
        'output_contract': {k: True for k in case['output_contract']},
    },
    'sources': sources,
    'uncertainty': uncertainty,
    'changes': changes,
}
dump(result, os.path.join(EX, 'selftest-result.json'))

baseline = json.loads(json.dumps(result))
baseline['result']['bilingual'] = read(os.path.join(EX, 'baseline-bilingual.md'))
baseline['result']['human_review'] = []
baseline['changes'] = []
dump(baseline, os.path.join(EX, 'baseline-result.json'))

print('wrote selftest-case.json / selftest-result.json / baseline-result.json')
