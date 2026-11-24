#!/usr/bin/env python3
"""生成结构化笔记卡片骨架（论文卡片 + 章节笔记 + 知识点 的空白模板）。

不预填答案，只根据 outline 生成稳定 ID 与章节槽位，供 Agent 逐条填写并保证
section_id / source_id / knowledge id 命名规范一致。

用法:
    python3 build_card_skeleton.py --outline outline.json --case case.json --out skeleton.json
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outline', required=True)
    ap.add_argument('--case')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    outline = json.load(open(args.outline, encoding='utf-8'))
    case = json.load(open(args.case, encoding='utf-8')) if args.case else {}
    cid = case.get('case_id', '')
    skeleton = {
        'case_id': cid,
        'status': 'partial',
        'result': {
            'paper_card': {
                'title': '', 'venue_year': '',
                'research_question': [], 'data': [], 'method': [],
                'findings': [], 'limitations': [], 'premises': [],
            },
            'section_notes': [
                {'section_id': s['section_id'], 'order': s.get('order', i + 1),
                 'title': s.get('title', ''), 'summary': '', 'source_ids': []}
                for i, s in enumerate(outline.get('outline', []))
            ],
            'knowledge_points': [],
        },
        'sources': [],
        'uncertainty': [],
        'changes': ['skeleton generated from outline'],
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(skeleton, f, ensure_ascii=False, indent=2)
    print(json.dumps({'status': 'ok', 'out': args.out,
                      'sections': len(skeleton['result']['section_notes'])},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.exit(main())
