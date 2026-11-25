#!/usr/bin/env python3
"""生成结果与讨论章节骨架（形态保证，防空壳）。"""
import argparse
import json
import os

SECTIONS = [
    ('3 结果', 'results', 250,
     '只写观察：按图序或问题序；每个数值后标（图 n）/（表 n）；显著性措辞必须带 p 值或检验名；'
     '不做解释（因为/由于/机制属讨论段）'),
    ('4 讨论', 'discussion', 300,
     '与文献对照要写"一致/不一致 + 可能原因"；机制推测必须写"可能"；'
     '每段落到一条本研究数据或具体文献'),
    ('4.1 局限', 'limitation', 100,
     '写到可检验层面：样本量、重复次数、单一物种/中心、未做的对照、随访时长；'
     '禁用"样本较少""有待进一步研究"这类套话'),
]


def main():
    ap = argparse.ArgumentParser(description='生成结果与讨论章节骨架')
    ap.add_argument('--case')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    cid = 'case'
    if args.case and os.path.isfile(args.case):
        with open(args.case, encoding='utf-8') as f:
            cid = json.load(f).get('case_id') or cid

    out = [f'<!-- case_id: {cid}；骨架占位符必须在定稿前清空 -->', '',
           '<!-- figure_data 必须先填：正文每个数值都要能在里面找到同值 -->', '']
    for title, key, min_c, hint in SECTIONS:
        out += [f'## {title}', '', f'<!-- {key}：≥{min_c} 字。{hint} -->', '',
                f'【{title}：待写】', '']
    out += ['<!-- 图表数据写进 result.json 的 figure_data，不要留在正文里：',
            '     {fig_id, caption, n, error_bar, stat, values{}} -->', '']

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print(json.dumps({'out': args.out, 'sections': len(SECTIONS),
                      'note': '骨架仅为形态保证；占位符未清空前不得标 success'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
