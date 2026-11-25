#!/usr/bin/env python3
"""论断切分与强度初判：把成稿拆成可判定的论断单元，给每条一个可复核的强度建议。

设计原则
--------
1. **只做可判定的切分**：一句话只有在含可检验断言时才成为论断单元。纯过渡句、
   纯方法罗列、纯引用罗列不单独成单元，避免用凑数量骗覆盖率。
2. **强度建议是规则推导，不是判断**：由原文摘录里出现的研究设计词、样本量词、
   重复验证词推出 `strong/moderate/weak/insufficient` 四档，并给出触发依据
   （`basis`）。规则命中不了就返回 `insufficient` 而不是猜 `moderate`。
3. **不做结论**：本脚本只产出候选与建议，最终等级由使用者复核后写入
   `result.claims[].strength`；脚本无法确认时会显式写 `needs_review`。

用法
----
  python scripts/claim_split.py --text draft.md [--json out.json]
  python scripts/claim_split.py --text draft.md --quote "原文摘录" --grade
"""
import argparse
import json
import re
import sys

# 句子边界：中文句末 + 分隔符 + 换行；保留分隔符以便还原位置
SENT_END = '。！？；!?;\n'
SKIP_PREFIX = ('#', '|', '-', '*', '>', '```')

# 研究设计词 → 证据等级（从强到弱，先命中者为准）
DESIGN_RULES = [
    ('strong', ['系统综述', 'meta 分析', 'meta分析', '荟萃分析', '随机对照', 'randomized',
                '多中心', '指南', '共识声明', '伞状综述']),
    ('moderate', ['队列', 'cohort', '前瞻性', '多组', '对照实验', '消融实验', 'ablation',
                  '重复实验', '三次独立', '多个数据集', '跨数据集', '复现']),
    ('weak', ['单例', '个案', '体外', 'in vitro', '初步', '预印本', 'preprint', 'n=1',
              '小样本', '单次实验', '未重复', '会议摘要']),
]
# 样本量线索
SAMPLE_RE = re.compile(r'(n\s*=\s*\d+|\d+\s*(?:例|名|只|个样本|份样本|位))')
# 弱样本阈值：n < 10 视为弱证据线索
SMALL_N = 10

STRENGTH_ORDER = {'insufficient': 0, 'weak': 1, 'moderate': 2, 'strong': 3}

# 模糊限制语（hedge）：出现在论断里表示作者已降级表述
HEDGES = ['可能', '或许', '提示', '倾向于', '初步', '尚不能', '尚不', '有待', '待验证',
          '不能排除', '受限于', '仅在', '局限', '相关', '关联', '推测', '假设', '疑似',
          '在一定程度上', '部分', '有限', '未达显著', '趋势', '不排除',
          '未见', '未能', '未提供', '未被', '不足以', '暂不', '存疑', '尚未', '尚需']
# 断言性过强的词：证据不强时出现即为表述过强
ASSERTIVE = ['证明', '证实', '确定', '必然', '一定', '显著优于', '完全', '彻底', '唯一',
             '首次', '首次证明', '毫无疑问', '毫无疑问地']

# 论断性线索：含下列任一类词才视为可判定论断
CLAIM_CUES = ['是', '为', '表明', '显示', '说明', '导致', '使得', '提高', '降低', '增加',
              '减少', '优于', '低于', '高于', '存在', '具有', '影响', '取决', '相关',
              '支持', '抑制', '促进', '改善', '恶化', '可达', '约为']


def split_sentences(text):
    """按句末标点与换行切句，返回 [(start, sentence)]。"""
    out, buf, start = [], '', 0
    for i, ch in enumerate(text):
        buf += ch
        if ch in SENT_END:
            s = buf.strip()
            if s:
                out.append((start, s))
            buf, start = '', i + 1
    if buf.strip():
        out.append((start, buf.strip()))
    return out


def is_claim(sent):
    """判断一句话是否为可判定论断单元。

    三条独立通道，命中任一即成单元——单一词表会漏掉"小于""未见"这类谓词，
    导致覆盖率被低估，因此加入两条更稳的通道：
      · 挂了引用编号：作者已声明这句话有依据，默认是论断；
      · 含数字且有单位量级：数值型断言本身就是可检验的。
    """
    s = sent.lstrip()
    if not s or s.startswith(SKIP_PREFIX):
        return False
    if len(re.sub(r'\s', '', s)) < 10:
        return False
    # 纯引用/纯编号行不算
    if re.fullmatch(r'[\[\]\d,，\-–\s]+', s):
        return False
    if re.search(r'\[\d+\]', s):
        return True
    if re.search(r'\d', s) and re.search(r'[%μ°A-Za-z]|百分点|倍|量级|个百分点', s):
        return True
    return any(c in s for c in CLAIM_CUES)


def _hit(text, words):
    return [w for w in words if w.lower() in text.lower()]


def grade(quote, claim=''):
    """由原文摘录 + 论断本身推出证据等级建议。返回 (grade, basis 列表, 标记)。"""
    q = (quote or '') + ' ' + (claim or '')
    basis, level = [], 'insufficient'
    for lv, words in DESIGN_RULES:
        hit = _hit(q, words)
        if hit:
            level = lv
            basis.append(f"设计线索 {hit[0]}")
            break
    m = SAMPLE_RE.search(q)
    if m:
        digits = re.sub(r'\D', '', m.group(0))
        n = int(digits) if digits else 0
        basis.append(f"样本量线索 {m.group(0)}")
        if n and n < SMALL_N and STRENGTH_ORDER[level] > STRENGTH_ORDER['weak']:
            level = 'weak'
            basis.append(f"样本量 {n} < {SMALL_N}，降至 weak")
    if not basis:
        basis.append('未命中设计/样本线索，留给人工判定')
        return 'insufficient', basis, 'needs_review'
    return level, basis, ''


def hedge_profile(claim):
    """返回论断的 hedge 与过强断言命中。"""
    return _hit(claim, HEDGES), _hit(claim, ASSERTIVE)


def hedge_ok(strength, claim):
    """表述强度与证据强度是否相称。

    strong      → 允许强断言，不要求 hedge
    moderate    → 不应出现绝对化断言词汇
    weak        → 应有 hedge 或范围限定
    insufficient→ 必须有 hedge 或明确"未知/待证"
    """
    hedges, assertive = hedge_profile(claim)
    if strength == 'strong':
        return True, '强证据允许直接表述'
    if strength == 'moderate':
        return (not assertive), ('含绝对化断言，证据仅 moderate' if assertive else '表述与 moderate 相称')
    if strength in ('weak', 'insufficient'):
        if assertive:
            return False, '含绝对化断言，但证据为 ' + strength
        return (bool(hedges)), ('缺少限定语，弱证据不应直述' if not hedges else '已带限定语')
    return False, '未知等级 ' + str(strength)


def units(text):
    """切出论断单元列表。"""
    res = []
    for idx, (pos, sent) in enumerate(split_sentences(text)):
        if not is_claim(sent):
            continue
        res.append({'unit_id': f'u{len(res) + 1}', 'sentence': sent,
                    'char_start': pos, 'cite_marks': re.findall(r'\[(\d+)\]', sent)})
    return res


def main():
    ap = argparse.ArgumentParser(description='论断切分与证据强度初判')
    ap.add_argument('--text', help='成稿路径')
    ap.add_argument('--quote', help='原文摘录（配合 --grade 用）')
    ap.add_argument('--claim', default='', help='论断原句（配合 --grade 用）')
    ap.add_argument('--grade', action='store_true', help='只做强度判定')
    ap.add_argument('--json', help='结果写入文件')
    args = ap.parse_args()

    if args.grade:
        lv, basis, flag = grade(args.quote or '', args.claim)
        ok, why = hedge_ok(lv, args.claim)
        out = {'strength': lv, 'basis': basis, 'flag': flag,
               'hedge_ok': ok, 'hedge_note': why}
    else:
        if not args.text:
            print('需要 --text 或 --grade', file=sys.stderr)
            return 2
        with open(args.text, encoding='utf-8') as f:
            text = f.read()
        us = units(text)
        out = {'units': us, 'unit_count': len(us),
               'with_cite': sum(1 for u in us if u['cite_marks'])}
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            f.write(payload + '\n')
        print(f"written {args.json}: units={out.get('unit_count', '-')}")
    else:
        print(payload)
    return 0


if __name__ == '__main__':
    sys.exit(main())
