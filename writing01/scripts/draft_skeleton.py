#!/usr/bin/env python3
"""生成整篇稿件的章节骨架，保证「章节不齐」不会成为失败原因。

不代替写作，只保证产出形态：八类章节 + 图表题注位 + 参考文献位 + 声明位，
每节标出该节最低字数与必须回答的问题。后续由 Agent 填入真实内容。

用法:
  python scripts/draft_skeleton.py --case case.json --out /app/output/manuscript.md [--lang zh]
"""
import argparse
import json
import os

SECTIONS = [
    ('摘要', 'abstract', 150, '研究问题 → 方法 → 主要结果（带数值）→ 结论边界；不写引用'),
    ('1 引言', 'introduction', 300, '领域脉络 → 具体未解问题 → 本文做了什么 → 贡献逐条（每条挂引用或图表）'),
    ('2 材料与方法', 'methods', 300, '材料来源、设备与参数、样本量、统计方法；参数写进表，正文不重复罗列'),
    ('3 结果', 'results', 250, '只写观察到的现象，按图序或问题序；每个数值指明来自图/表编号'),
    ('4 讨论', 'discussion', 250, '与文献对照（一致/不一致及原因）、机制推测须标注为推测、局限写到方法与样本层面'),
    ('5 结论', 'conclusion', 100, '只复述结果支持的结论，不越出证据范围'),
    ('数据可得性', 'data_availability', 20, '数据/代码在哪、如何获取；不可公开要写原因与申请途径'),
    ('参考文献', 'references', 1, '至少 12 条，正文编号与条目一一对应；缺元数据的标"待核"'),
]

EXTRA = [
    ('作者贡献', 'author_contribution', '按 CRediT 或期刊要求逐项写'),
    ('利益冲突', 'conflict_of_interest', '无则写"作者声明无利益冲突"'),
    ('基金', 'funding', '基金号与项目名；无则写"本研究未受资助"'),
]


def main():
    ap = argparse.ArgumentParser(description='生成整篇稿件骨架')
    ap.add_argument('--case', help='case.json（可选，用于取 case_id 与语言）')
    ap.add_argument('--out', required=True)
    ap.add_argument('--lang', default='zh')
    ap.add_argument('--with-declarations', action='store_true', default=True,
                    help='附作者贡献/利益冲突/基金三个声明位（默认附）')
    args = ap.parse_args()

    cid = 'case'
    if args.case and os.path.isfile(args.case):
        with open(args.case, encoding='utf-8') as f:
            cid = json.load(f).get('case_id') or cid

    out = [f'<!-- case_id: {cid}；本文件为骨架，占位符必须在定稿前清空 -->', '']
    for title, key, min_c, hint in SECTIONS:
        out.append(f'## {title}')
        out.append('')
        out.append(f'<!-- {key}：≥{min_c} 字。{hint} -->')
        if key == 'references':
            out.append('')
            out.append('[1] 作者. 题名. 刊名, 年, 卷(期): 页. DOI:')
            out.append('[2] …（至少 12 条，与正文编号一一对应）')
        elif key == 'data_availability':
            out.append('')
            out.append('【数据可得性：说明数据与代码位置】')
        else:
            out.append('')
            out.append(f'【{title}：待写】')
        out.append('')
    if args.with_declarations:
        for title, key, hint in EXTRA:
            out.append(f'## {title}')
            out.append('')
            out.append(f'<!-- {key}：{hint} -->')
            out.append('')
            out.append(f'【{title}：待写】')
            out.append('')
    out += ['## 图表位置（题注必须与正文提及成对）', '',
            '图 1 【题注：这张图画的是什么，样本量与误差棒含义】', '',
            '表 1 【题注：表中各列含义与单位】', '']

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print(json.dumps({'out': args.out, 'sections': len(SECTIONS),
                      'note': '骨架仅为形态保证，占位符未清空前不得标 success'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
