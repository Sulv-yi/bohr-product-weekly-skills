#!/usr/bin/env python3
"""结果与讨论章节的度量：图表读数一致性 / 显著性表述与统计量对齐 / 描述与解释分离 / 局限具体性。

只度量不判分。口径写在文件头，供 validate_result.py、build_outputs.py、eval/ 共用：

- fig_number_rate    正文结果段里的数值，能在 `result.figure_data` 里找到同值的比例。
                     这是「读得准」的直接抓手：数值凭空出现就是 0。
- stats_support      出现显著性措辞（显著/差异显著/p<）的句子里，给出统计量（p 值、CI、
                     检验名、自由度）的比例。没有统计量的"显著"是表述过强。
- leakage            结果段里出现解释性措辞（因为/由于/说明机制/可能源于）的句数。
                     结果段只写观察，解释属讨论段，两节不互相顶替。
- trend_boundary     是否写了"趋势一致但未达显著"这类有边界的表述（布尔）。
- binding            论断句中挂引用编号或图表编号的比例。
- limitation_specific 局限是否写到可检验的层面（样本量/重复次数/单一物种/未做对照等），
                     而不是"样本较少"这类套话。
"""
import re

HEADING = re.compile(r'^\s{0,3}(#{1,6})\s*(.+?)\s*$', re.M)
LATIN_WORD = re.compile(r'[A-Za-z][A-Za-z\-]+')
PLACEHOLDER_PATTERNS = [r'【[^】\n]{0,60}】', r'\{\{[^{}\n]{0,40}\}\}',
                        r'\[证据槽[^\]]*\]', r'\bTODO\b', r'\bTBD\b', r'待补', r'待填']


def _nchars(text):
    """中文按字、西文按词 ×0.6、数字按个 ×0.6。

    数字计入是因为结果段天然参数密集（n=、p 值、单位），只数汉字会把"读数写得很实"
    的段落判成篇幅不足，反过来鼓励注水。
    """
    if not text:
        return 0
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    latin = len(LATIN_WORD.findall(text))
    nums = len(NUM_PLAIN.findall(text))
    return int(cjk + (latin + nums) * 0.6)


def placeholders(text):
    hits = []
    for pat in PLACEHOLDER_PATTERNS:
        hits += re.findall(pat, text or '')
    return hits


def split_sections(text):
    """按 Markdown 标题切段，返回 [(level, title, body)]，body 含其下级小节。

    body 一直延伸到「下一个同级或更高级标题」为止，而不是下一个标题——否则
    `## 结果` 的正文只剩到 `### 3.1` 之间的几十个字，篇幅会被误判。
    """
    text = text or ''
    ms = list(HEADING.finditer(text))
    if not ms:
        return [(0, '', text)]
    out = []
    for i, m in enumerate(ms):
        lvl = len(m.group(1))
        end = len(text)
        for nxt in ms[i + 1:]:
            if len(nxt.group(1)) <= lvl:
                end = nxt.start()
                break
        out.append((lvl, m.group(2), text[m.end():end]))
    return out

NUM_U = re.compile(r'\d+(?:\.\d+)?\s*(?:%|％|μm|mm|nm|°C|℃|MPa|GPa|kPa|Pa|Hz|h|min|s|W|mg|g|kg|mL|L|倍|例|名|个|次)')
NUM_PLAIN = re.compile(r'\d+(?:\.\d+)?')
CITE_OR_FIG = re.compile(r'\[\d+\]|（图\s*\d+）|\(图\s*\d+\)|（表\s*\d+）|\(表\s*\d+\)|图\s*\d+|表\s*\d+')

STAT_WORDS = ['显著', '差异显著', '显著高于', '显著低于', '极显著', 'p<', 'p 值', 'P<']
STAT_EVID = ['p<', 'p <', 'p=', 'p =', 'P<', 'CI', '置信区间', 't 检验', '方差分析', 'ANOVA',
             'Mann-Whitney', 'Kruskal', '自由度', 'F(', 'χ2', '卡方']
EXPLAIN_CUES = ['因为', '由于', '说明机制', '可能源于', '归因于', '这表明机制', '原因是',
                '之所以', '其机制', '可解释为']
TREND_BOUNDARY = ['未达显著', '未达到显著', '趋势一致', '仅在', '方向上一致', '未达统计学显著',
                  '不显著']
LIMIT_SPECIFIC = [
    r'n\s*=\s*\d+', r'\d+\s*(?:例|名|只|个试样|批次)', r'单批次', r'未重复', r'单一物种',
    r'单一{0,2}(?:层厚|合金|体系|中心)', r'未做(?:对照|重复|疲劳)', r'仅覆盖', r'体温|室温',
    r'样本量', r'随访', r'未纳入', r'限于', r'未验证',
]
LIMIT_VAGUE = ['样本较少', '样本量较少', '样本有限', '条件有限', '有待进一步研究', '需要更多研究']


def find_section(text, pattern):
    best = ''
    for _lvl, title, body in split_sections(text):
        if re.search(pattern, title or '', re.I):
            if _nchars(body) > _nchars(best):
                best = body
    return best


def sentences(text):
    out = []
    for line in (text or '').split('\n'):
        line = line.strip()
        if not line or line.startswith(('#', '|', '>')):
            continue
        for seg in re.split(r'(?<=[。！？!?])\s*', line):
            seg = seg.strip()
            if len(seg) >= 8:
                out.append(seg)
    return out


def _norm(x):
    """把数值规范成可比较的字符串：2.10 -> 2.1，61% -> 61，-2.1% -> -2.1。"""
    m = re.search(r'-?\d+(?:\.\d+)?', str(x).replace('−', '-'))
    if not m:
        return ''
    try:
        return f'{float(m.group(0)):g}'
    except ValueError:
        return ''


def fig_number_rate(results_text, figure_data):
    """结果段数值 → 图表数据池 的可回溯率。

    比较用数值规范形（2.10 与 2.1 视为同值，61% 与 61 视为同值）：
    单位不进比较，因为同一数据在图上与正文里的单位写法可以不同。
    """
    pool = set()
    for item in (figure_data or []):
        for v in (item.get('values') or {}).values():
            pool.add(_norm(v))
        for grp in (item.get('series') or []):
            for v in (grp.get('y') or []):
                pool.add(_norm(v))
    nums = {_norm(m) for m in NUM_U.findall(results_text or '')}
    nums.discard('')
    if not nums:
        return 0.0, []
    # 正文常把方向写进文字（"下降 2.1%"），图表存的是 -2.1：符号不进比较，按绝对值也算命中
    pool_abs = {k.lstrip('-') for k in pool}
    miss = sorted(n for n in nums if n not in pool and n.lstrip('-') not in pool_abs)
    return round((len(nums) - len(miss)) / len(nums), 3), miss[:10]


def stats_alignment(text):
    sents = [s for s in sentences(text) if any(w in s for w in STAT_WORDS)]
    if not sents:
        return 1.0, 0, []
    ok = [s for s in sents if any(w in s for w in STAT_EVID)]
    bad = [s for s in sents if s not in ok]
    return round(len(ok) / len(sents), 3), len(sents), bad[:5]


def measure(text, result=None, min_chars=1200):
    result = result or {}
    payload = result.get('result') if isinstance(result.get('result'), dict) else {}
    text = text or ''
    res = find_section(text, r'结果|results')
    dis = find_section(text, r'讨论|discussion')
    lim = find_section(text, r'局限|不足|limitation')
    fig_rate, fig_miss = fig_number_rate(res or text, payload.get('figure_data'))
    st_rate, st_n, st_bad = stats_alignment((res or '') + '\n' + (dis or ''))

    all_sents = sentences(text)
    cited = [s for s in all_sents if CITE_OR_FIG.search(s)]
    leak = [s for s in (res or '').split('。') if any(c in s for c in EXPLAIN_CUES)]

    limit_text = lim or dis
    spec = [p for p in LIMIT_SPECIFIC if re.search(p, limit_text or '')]
    vague = [w for w in LIMIT_VAGUE if w in (limit_text or '')]

    return {
        'total_chars': _nchars(text),
        'min_chars_ok': _nchars(text) >= min_chars,
        'results_chars': _nchars(res),
        'discussion_chars': _nchars(dis),
        'limitation_chars': _nchars(lim),
        'fig_number_rate': fig_rate,
        'fig_numbers_untraced': fig_miss,
        'figure_rows': len(payload.get('figure_data') or []),
        'stats_claims': st_n,
        'stats_support': st_rate,
        'stats_unsupported': st_bad,
        'leakage': len(leak),
        'leakage_samples': [s.strip()[:40] for s in leak[:3]],
        'trend_boundary': any(w in text for w in TREND_BOUNDARY),
        'binding_rate': round(len(cited) / len(all_sents), 3) if all_sents else 0.0,
        'sentences': len(all_sents),
        'limitation_markers': len(spec),
        'limitation_vague': vague,
        'placeholder_count': len(placeholders(text)),
    }
