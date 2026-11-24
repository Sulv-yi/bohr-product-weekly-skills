#!/usr/bin/env python3
"""从带坐标的文本块构建论文自己的章节骨架（不套用通用摘要模板）。

输入 extract_blocks.py 产出的 blocks.json（每块含 id/page/bbox/text），或等价的
{"blocks":[...]}。按标题编号 / 常见章节词 / 版式特征识别标题，输出：
  - outline: [{section_id, title, level, order, start_block, page}]
  - block_section: {block_id: section_id}
  - full_text: 供锚点回链核验

用法:
    python3 build_outline.py <blocks.json> --out outline.json
    python3 build_outline.py <blocks.json> --out outline.json --custom-headings "S1:引言| S2:方法"
"""
import argparse
import json
import re
import sys

# 编号标题: "1 Introduction" / "2.1 Methods" / "3  Results" / "IV. DISCUSSION"
NUM_HEAD = re.compile(r'^\s*(\d{1,2}(?:\.\d{1,2}){0,2}|[IVX]{1,4})[\.\)、\s]\s*(.{2,80})$')
# 无编号的常见章节词（中英）
WORD_HEAD = re.compile(
    r'^\s*(摘\s*要|abstract|前\s*言|引\s*言|introduction|background|background and|'
    r'related work|目\s*的|objective|研究问题|research question|数\s*据|data|'
    r'方\s*法|methods?|methodology|materials? and methods?|实验|experiments?|'
    r'results?|结\s*果|分\s*析|analysis|讨\s*论|discussion|结\s*论|conclusions?|'
    r'总\s*结|limitations?|局\s*限|references?|参考文献|附\s*录|appendix)\s*[:：.]?\s*$',
    re.I,
)
# 若一行以冒号结尾且很短，也可能是小节标题
SHORT_COLON = re.compile(r'^\s*(.{2,40})[:：]\s*$')


def _norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def _looks_like_heading(text):
    t = _norm(text)
    if not t or len(t) > 100:
        return None
    if WORD_HEAD.match(t):
        return _clean_word_head(t)
    m = NUM_HEAD.match(t)
    if m:
        title = _norm(m.group(2))
        if title and not title.endswith(('.', '。', ',', '，')):
            return title
    if SHORT_COLON.match(t) and len(t) <= 42:
        return t.rstrip(':：')
    # 全大写英文短行
    letters = [c for c in t if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(t) <= 60:
        return t
    return None


def _clean_word_head(t):
    return _norm(t.rstrip(':.：'))


def build(blocks, custom=None):
    outline = []
    block_section = {}
    cur = None
    custom_map = {}
    if custom:
        for part in custom.split('|'):
            if ':' in part:
                sid, title = part.split(':', 1)
                custom_map[_norm(title).lower()] = sid.strip()

    for b in blocks:
        bid = str(b.get('id', ''))
        text = b.get('text', '')
        head = _looks_like_heading(text)
        sid = custom_map.get(_norm(head).lower()) if head else None
        if head and sid is None:
            cur = {
                'section_id': 'S%d' % (len(outline) + 1),
                'title': head,
                'level': 1,
                'order': len(outline) + 1,
                'start_block': bid,
                'page': b.get('page'),
            }
            # 依据编号推断层级
            m = NUM_HEAD.match(_norm(text))
            if m and '.' in m.group(1):
                cur['level'] = m.group(1).count('.') + 1
            outline.append(cur)
        elif custom_map.get(_norm(text).lower()):
            sid2 = custom_map[_norm(text).lower()]
            cur = {
                'section_id': sid2,
                'title': _norm(text),
                'level': 1,
                'order': len(outline) + 1,
                'start_block': bid,
                'page': b.get('page'),
            }
            outline.append(cur)
        if cur:
            block_section[bid] = cur['section_id']
        else:
            block_section[bid] = 'PREAMBLE'

    if not outline:
        outline.append({
            'section_id': 'S1', 'title': '(未识别章节)', 'level': 1,
            'order': 1, 'start_block': blocks[0].get('id', '') if blocks else '',
            'page': blocks[0].get('page') if blocks else None,
        })
        for b in blocks:
            block_section[str(b.get('id', ''))] = 'S1'

    full_text = '\n'.join(_norm(b.get('text', '')) for b in blocks)
    return {
        'outline': outline,
        'block_section': block_section,
        'full_text': full_text,
        'block_count': len(blocks),
        'section_count': len(outline),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('blocks')
    ap.add_argument('--out', required=True)
    ap.add_argument('--custom-headings', default=None)
    args = ap.parse_args()
    data = json.load(open(args.blocks, encoding='utf-8'))
    blocks = data.get('blocks', data if isinstance(data, list) else [])
    rep = build(blocks, args.custom_headings)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        'status': 'ok', 'out': args.out,
        'section_count': rep['section_count'], 'block_count': rep['block_count'],
        'sections': [s['title'] for s in rep['outline']],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.exit(main())
