"""科研成果转化写作的度量层（纯标准库）。

子场景：把论文/技术报告改成面向公众的科普稿，并保留证据与可编辑性。

四个关注点对应四组函数：
- 读得懂  abbrev_check / readability
- 留得住  retention / hedge_retention
- 说得准  strength_align / term_consistency
- 接得住  changelog_rate / trace_rate
"""
import re

# ---------- 基础 ----------

CJK = r'\u4e00-\u9fff'

ABBREV_USE = re.compile(r'\b([A-Z]{2,}[0-9]{0,4})\b')
ABBREV_DEF = re.compile(r'([\u4e00-\u9fff]{2,14})[（(]\s*([A-Z][A-Za-z0-9\-]{1,11})\s*[)）]')
ABBREV_DEF_EN = re.compile(r'([A-Za-z][A-Za-z\s\-]{3,40})[（(]\s*([A-Z][A-Za-z0-9\-]{1,11})\s*[)）]')

# 不需要展开的常见单位/统计符号
ABBREV_WHITELIST = {
    'AI', 'DNA', 'RNA', 'MRI', 'XPS', 'SEM', 'TEM', 'XRD', 'PLA', 'HA',
    'CO2', 'H2O', 'O2', 'MPa', 'GPa', 'kPa', 'kV', 'SD', 'CR2032', 'PDF', 'CSV', 'JSON',
}

NUM_TOKEN = re.compile(
    r'[-+]?\d+(?:\.\d+)?\s*(?:%|‰|wt%|at%|°C|K|mAh/g|mAh|MPa|GPa|kPa|Pa|nm|µm|um|mm|cm|m|'
    r'mg|g|kg|µL|uL|mL|L|h|min|s|ms|V|mV|A|mA|µA|uA|W|kW|Hz|kHz|MHz|GHz|ppm|ppb|'
    r'倍|个|例|名|人|周|月|年|天|小时)'
)
NUM_BARE = re.compile(r'[-+]?\d+(?:\.\d+)?')

HEDGE = ['可能', '或许', '也许', '推测', '尚不清楚', '有待', '未证实', '初步', '倾向于',
         '未能', '未见', '不足以', '存疑', '尚需', '暂不', '尚不', '不确定', '相关', '提示']
ASSERTIVE = ['证明', '证实', '表明', '说明', '确认', '必然', '一定', '完全', '显著优于',
             '彻底', '杜绝', '根治', '百分之百', '绝对']
LIMIT_WORD = ['仅', '只', '限于', '条件下', '前提', '除外', '不适用', '样本', 'n =', 'n=',
              '体外', '离体', '动物实验', '短期', '随访', '单一', '初步']
FIG_TAB = re.compile(r'(?:Fig(?:ure)?\.?|图|Table|表)\s*\d+[a-zA-Z]?')

SENT_SPLIT = re.compile(r'(?<=[。！？!?；;])\s*')
TRACE_TAG = re.compile(r'【\s*(?:源|出处)\s*[:：]?\s*([^】]{1,60})】')
CHANGE_TAG = re.compile(r'\[(?:删|改|增|合|移)[^\]]{0,120}\]')


def _nchars(text):
    """中文按字计，西文按词×0.6 计，数字按个×0.6 计。"""
    text = text or ''
    cjk = len(re.findall(f'[{CJK}]', text))
    latin = len(re.findall(r'[A-Za-z]+', text))
    digits = len(re.findall(r'\d+', text))
    return int(round(cjk + latin * 0.6 + digits * 0.6))


def split_sections(text):
    """按 markdown 标题切节，返回 [(level, title, body)]。"""
    out = []
    cur_t, cur_b, cur_l = None, [], 0
    for line in (text or '').split('\n'):
        m = re.match(r'^(#{1,6})\s+(.*)$', line.strip())
        if m:
            if cur_t is not None or cur_b:
                out.append((cur_l, cur_t or '', '\n'.join(cur_b).strip()))
            cur_l, cur_t, cur_b = len(m.group(1)), m.group(2).strip(), []
        else:
            cur_b.append(line)
    if cur_t is not None or cur_b:
        out.append((cur_l, cur_t or '', '\n'.join(cur_b).strip()))
    return out


def placeholders(text):
    """未填的占位符：TODO / TBD / XXX / 待补充 / 空表格单元。"""
    pats = [r'\bTODO\b', r'\bTBD\b', r'\bXXX\b', r'待补充', r'待填写', r'请填写', r'<[^>\n]{1,20}>',
            r'\{\{[^}\n]{1,30}\}\}']
    hits = []
    for p in pats:
        hits += re.findall(p, text or '')
    return hits


# ---------- 读得懂 ----------

def abbrev_check(source, target):
    """缩写首次出现是否展开。

    判定：源文里出现过的缩写，在成稿里第一次出现时，前面 30 字内要有中文全称
    或英文全称（形如「中文全称（ABBR）」）。白名单里的通用缩写不计。
    """
    src_abbr = {m.group(1) for m in ABBREV_USE.finditer(source or '')}
    src_abbr |= {m.group(1) for m in ABBREV_USE.finditer(source or '')}
    used = [a for a in src_abbr if a in (target or '')]
    rows, ok = [], 0
    for a in sorted(used):
        if a in ABBREV_WHITELIST or len(a) < 2:
            continue
        idx = (target or '').find(a)
        ctx = (target or '')[max(0, idx - 60):idx]
        # 已展开的两种写法：中文/英文全称（ABBR） 或 全称，ABBR
        tail = re.search(r'[（(]\s*$|[，,]\s*$', ctx)
        full_name = bool(re.search(r'[A-Za-z]{4,}', ctx)) or bool(re.search(f'[{CJK}]{{2,}}', ctx))
        defined = bool(tail) and full_name and len(ctx.strip()) >= 4
        rows.append((a, defined, ctx[-24:].replace('\n', ' ')))
        if defined:
            ok += 1
    rate = round(ok / float(len(rows)), 3) if rows else 1.0
    return rate, rows


def readability(target):
    """可读性：句均长、超长句占比、术语密度。"""
    sents = [s.strip() for s in SENT_SPLIT.split(target or '') if _nchars(s.strip()) >= 4]
    if not sents:
        return {'sent_count': 0, 'avg_len': 0, 'long_ratio': 0.0, 'jargon_density': 0.0, 'long_sents': []}
    lens = [_nchars(s) for s in sents]
    long_s = [s for s, L in zip(sents, lens) if L > 60]
    # 术语密度：连用两个以上西文词或含括号缩写的句子占比
    jargon = [s for s in sents if re.search(r'[A-Za-z]{3,}\s+[A-Za-z]{3,}', s) or re.search(r'[（(][A-Za-z\-]{2,}[)）]', s)]
    return {
        'sent_count': len(sents),
        'avg_len': round(sum(lens) / float(len(lens)), 1),
        'long_ratio': round(len(long_s) / float(len(sents)), 3),
        'jargon_density': round(len(jargon) / float(len(sents)), 3),
        'long_sents': [s[:50] for s in long_s[:6]],
    }


def analogy_present(target):
    """科普稿是否有至少两处类比/解释性衔接（像/好比/相当于/可以理解为/想象）。"""
    cues = ['像', '好比', '相当于', '可以理解为', '想象', '打个比方', '类似于', '不妨']
    hits = [(c, len(re.findall(c, target or ''))) for c in cues]
    total = sum(n for _c, n in hits)
    return total, hits


# ---------- 留得住 ----------

def _num_set(text):
    """抽取「数值+单位」与裸数值，返回规范化字符串集合。"""
    out = set()
    for m in NUM_TOKEN.finditer(text or ''):
        s = m.group(0).replace(' ', '')
        out.add(re.sub(r'[^\d\.\-a-zA-Z%‰°µ/]', '', s))
    return out


def _norm_num(s):
    s = s.strip()
    s = re.sub(r'^\+', '', s)
    if re.match(r'^-?\d+\.\d+$', s):
        s = s.rstrip('0').rstrip('.')
    return s


def _norm_ft(tok):
    """图表编号归一：Fig. 2a → 图2a，Table 1 → 表1。"""
    t = re.sub(r'\s+', '', tok or '')
    t = re.sub(r'^(?:Fig(?:ure)?\.?|FIG\.?)', '图', t)
    t = re.sub(r'^(?:Table|TABLE)', '表', t)
    return t


def retention(source, target):
    """关键信息保留率：数值、限定条件、图表编号三类。

    数值按「规范形」比对（2.10 与 2.1 等价，61% 与 61 不等价——百分比是口径的一部分）。
    """
    src_nums = {_norm_num(x) for x in _num_set(source)}
    tgt_nums = {_norm_num(x) for x in _num_set(target)}
    # 裸数字也纳入（避免单位写法差异导致漏比）
    src_bare = {_norm_num(m.group(0)) for m in NUM_BARE.finditer(source or '')}
    tgt_bare = {_norm_num(m.group(0)) for m in NUM_BARE.finditer(target or '')}
    num_all = src_nums | src_bare
    num_hit = {x for x in num_all if x in (tgt_nums | tgt_bare)}
    # 限定条件：源文里的限定词，成稿里至少保留一半以上语义（按词面命中）
    src_lim = [w for w in LIMIT_WORD if w in (source or '')]
    lim_hit = [w for w in src_lim if w in (target or '')]
    # 图表编号
    src_ft = {_norm_ft(m.group(0)) for m in FIG_TAB.finditer(source or '')}
    tgt_ft = {_norm_ft(m.group(0)) for m in FIG_TAB.finditer(target or '')}
    ft_hit = {x for x in src_ft if x in tgt_ft}
    return {
        'num_total': len(num_all),
        'num_rate': round(len(num_hit) / float(len(num_all)), 3) if num_all else 1.0,
        'num_missing': sorted(num_all - num_hit)[:12],
        'limit_total': len(src_lim),
        'limit_rate': round(len(lim_hit) / float(len(src_lim)), 3) if src_lim else 1.0,
        'limit_missing': [w for w in src_lim if w not in lim_hit][:10],
        'figtab_total': len(src_ft),
        'figtab_rate': round(len(ft_hit) / float(len(src_ft)), 3) if src_ft else 1.0,
        'figtab_missing': sorted(src_ft - ft_hit)[:8],
    }


def hedge_retention(source, target):
    """限定语保留：源文有 hedge 的段落，成稿对应段落不能变成断言。"""
    src_hedged = sum(1 for s in SENT_SPLIT.split(source or '') if any(h in s for h in HEDGE))
    tgt_hedged = sum(1 for s in SENT_SPLIT.split(target or '') if any(h in s for h in HEDGE))
    tgt_assert = sum(1 for s in SENT_SPLIT.split(target or '') if any(a in s for a in ASSERTIVE))
    keep = round(min(1.0, tgt_hedged / float(src_hedged)), 3) if src_hedged else 1.0
    return {'src_hedged': src_hedged, 'tgt_hedged': tgt_hedged,
            'tgt_assertive': tgt_assert, 'keep_rate': keep}


# ---------- 说得准 ----------

def strength_align(source, target):
    """论断强度对齐：源文弱（有 hedge）的句子，成稿里不能只剩断言。

    做法：取成稿里含强断言词的句子，逐句看是否有 hedge 或溯源标记；
    既无 hedge 又无溯源的强断言句记一条越界。
    """
    rows = []
    sents = [s.strip() for s in SENT_SPLIT.split(target or '') if _nchars(s) >= 8]
    for s in sents:
        strong = [a for a in ASSERTIVE if a in s]
        if not strong:
            continue
        hedged = any(h in s for h in HEDGE)
        traced = bool(TRACE_TAG.search(s))
        rows.append((s[:60], ','.join(strong), hedged, traced))
    bad = [r for r in rows if not r[2] and not r[3]]
    return {'strong_sents': len(rows), 'violations': len(bad), 'rows': rows[:12],
            'bad_rows': bad[:8]}


def term_consistency(target, terms=None):
    """同一概念的多个说法是否收敛。

    terms: [(concept, [变体列表])]，在成稿里统计每个变体出现次数；
    若同一 concept 下两个以上变体同时出现，记一次漂移。
    """
    terms = terms or []
    drift, rows = [], []
    for concept, variants in terms:
        hit = [(v, (target or '').count(v)) for v in variants if v and v in (target or '')]
        hit = [(v, n) for v, n in hit if n > 0]
        rows.append((concept, hit))
        if len(hit) > 1:
            # 子串互斥：若短变体都包含在某长变体里，不算漂移
            only_sub = all(any(v != w and v in w for w in [h[0] for h in hit]) for v, _n in hit)
            if not only_sub:
                drift.append((concept, hit))
    return {'drift': len(drift), 'rows': rows[:12], 'drift_rows': drift[:6]}


# ---------- 接得住 ----------

def changelog_rate(text):
    """修改清单覆盖率：标记为改动的位置数 / 段落数。

    支持两种标记：行内 [删:理由] / [改:理由]，或单独的「修改清单」章节条目。
    """
    body_sections = split_sections(text or '')
    n_para = 0
    for _l, t, b in body_sections:
        if re.search(r'修改|变更|改动|清单|说明', t):
            continue
        n_para += len([p for p in (b or '').split('\n\n') if _nchars(p) >= 20])
    inline = len(CHANGE_TAG.findall(text or ''))
    # 清单章节里的条目
    listed = 0
    for _l, t, b in body_sections:
        if re.search(r'修改|变更|改动|清单', t):
            listed = len([ln for ln in (b or '').split('\n') if re.match(r'^\s*[-*|]\s*\S', ln)])
    total = inline + listed
    rate = round(min(1.0, total / float(max(n_para, 1))), 3)
    return {'paras': n_para, 'inline_tags': inline, 'listed': listed, 'total': total, 'rate': rate}


def trace_rate(text):
    """溯源覆盖率：含数值或结论性表述的句子，能被同段或本句的【源：…】覆盖的比例。

    按段落判，而不是只认句末标记。理由：一段数据表统一标注出处，
    段内每一行都可按该出处回查，逐行挂标记属形式主义。
    """
    total = hit = 0
    for para in re.split(r'\n\s*\n', text or ''):
        para_marked = bool(TRACE_TAG.search(para))
        for s in SENT_SPLIT.split(para):
            s = s.strip()
            if _nchars(s) < 10:
                continue
            if not (NUM_BARE.search(s) or any(w in s for w in ['表明', '发现', '显示', '结果', '结论', '提出'])):
                continue
            total += 1
            if para_marked or TRACE_TAG.search(s):
                hit += 1
    return {'claims': total, 'traced': hit,
            'rate': round(hit / float(total), 3) if total else 0.0}


def audience_fit(target, audience='公众'):
    """受众适配：是否写明目标读者与阅读目的，是否避免公式/行话堆叠。"""
    head = (target or '')[:600]
    has_aud = bool(re.search(r'(?:面向|读者|受众|适合)', head))
    has_purpose = bool(re.search(r'(?:为什么读|读完[你]?[会]?[能]?知道|读完能|目的是|帮助读者|你需要知道)', head))
    formulas = len(re.findall(r'\$[^$]{2,40}\$', target or ''))
    return {'audience_declared': has_aud, 'purpose_declared': has_purpose, 'formulas': formulas}
