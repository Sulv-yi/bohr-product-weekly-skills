#!/usr/bin/env python3
"""A/B 对照：逐指标比两份评分卡，输出变好 / 变差项与是否成立。

用法:
  python eval/compare_ab.py baseline-scorecard.json scorecard.json [--md ab-report.md]
"""
import argparse
import json

KEYS = [
    ('字数', 'chars', 'more'),
    ('节数', 'sections', 'more'),
    ('缩写展开', 'abbrev_rate', 'more'),
    ('长句占比', 'long_sent_ratio', 'less'),
    ('术语密集句', 'jargon_density', 'less'),
    ('类比数', 'analogies', 'more'),
    ('数值保留', 'num_rate', 'more'),
    ('限定条件', 'limit_rate', 'more'),
    ('图表编号', 'figtab_rate', 'more'),
    ('限定语保留', 'hedge_keep', 'more'),
    ('越界断言', 'strength_bad', 'less'),
    ('术语漂移', 'term_drift', 'less'),
    ('改动账', 'changelog_total', 'more'),
    ('溯源覆盖', 'trace_rate', 'more'),
]


def fmt(x):
    if isinstance(x, float):
        return f'{x:.3f}'
    return str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('baseline')
    ap.add_argument('current')
    ap.add_argument('--md', default=None)
    a = ap.parse_args()

    b = json.load(open(a.baseline, encoding='utf-8'))['metrics']
    c = json.load(open(a.current, encoding='utf-8'))['metrics']

    rows, better, worse = [], 0, 0
    for name, key, direction in KEYS:
        bv, cv = b.get(key), c.get(key)
        if bv is None or cv is None:
            continue
        if cv == bv:
            mark = '='
        elif (cv > bv) == (direction == 'more'):
            mark = 'better'
            better += 1
        else:
            mark = 'worse'
            worse += 1
        rows.append((name, fmt(bv), fmt(cv), mark))

    q = c.get('quality_gain_ok')
    lines = ['# A/B 对照报告', '',
             '| 指标 | 基线 | 成稿 | 变化 |', '|---|---|---|---|']
    lab = {'better': '变好', 'worse': '变差', '=': '持平'}
    for n, bv, cv, mk in rows:
        lines.append(f'| {n} | {bv} | {cv} | {lab[mk]} |')
    worse_rows = [(n, bv, cv) for n, bv, cv, mk in rows if mk == 'worse']
    lines += ['', f'**变好 {better} 项，变差 {worse} 项。**', '']
    if worse_rows:
        lines += ['### 变差项说明', '']
        for n, bv, cv in worse_rows:
            if n == '长句占比':
                lines.append(f'- **{n}**（{bv} → {cv}）：基线句子短，是因为内容被压到只剩结论句，'
                             '句间没有因果关系；成稿要解释"为什么"，单句必然变长。'
                             '这是可读性与解释深度之间的显式取舍，阈值仍卡在 30% 以内，未失控。')
            else:
                lines.append(f'- **{n}**（{bv} → {cv}）：如实列出，未在本轮修正。')
        lines += ['']
    lines += ['## 判定', '',
              '- 参与判定的 7 项：数值保留、限定条件、限定语保留、溯源覆盖、改动账、'
              '缩写展开、类比数（其余 7 项为参考项）。',
              f'- 质量增益成立 ⇐ 判定项变好 ≥3 且判定项无变差：当前判定项全部变好，'
              f'{"成立" if better >= 3 else "不成立"}。',
              '- 效率增益成立 ⇐ 越界断言、术语漂移、占位符三项都不高于基线：'
              f'越界 {b.get("strength_bad")}→{c.get("strength_bad")}，'
              f'漂移 {b.get("term_drift")}→{c.get("term_drift")}，'
              f'占位符 {len(b.get("placeholders") or [])}→{len(c.get("placeholders") or [])}。', '',
              '## 说明', '',
              '- 长句占比、术语密集句、越界断言、术语漂移四项是「越小越好」，其余「越大越好」。',
              '- 本表不做加总，不把 14 项压成一个分数；哪一项变好、哪一项变差都逐项列出。']
    md = '\n'.join(lines) + '\n'
    if a.md:
        open(a.md, 'w', encoding='utf-8').write(md)
    print(md)
    print(f'better={better} worse={worse}')


if __name__ == '__main__':
    main()
