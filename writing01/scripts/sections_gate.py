#!/usr/bin/env python3
"""整篇稿件结构度量：章节齐备度 / 图表-题注对齐 / 引用闭合 / 材料索引覆盖 / 数值可回溯。

只度量不判分。口径写在文件头，供 validate_result.py、build_outputs.py、eval/ 共用：

- total_chars      中文按字、西文按词 ×0.6 折算
- section_coverage 题面要求的章节里，实际有实质内容（≥该节门槛字数）的比例
- fig_pairs        正文提到「图 n」且存在对应题注的组数（表同理），
                   只有正文提及而无题注、或只有题注而无正文提及，都不计入
- cite_resolved    正文引用编号 ⊆ 参考文献表编号区间的比例
- binding_rate     论断句中挂引用编号的占比
- num_trace_rate   正文数值能在材料索引/来源映射里找到同值的比例（可回溯率）
- decl_fields      数据可得性 / 作者贡献 / 利益冲突 / 基金 四类声明的命中数
"""
import re

from quality_gate import split_sections  # noqa: E402

NUM_TOKEN = re.compile(r'\d+(?:\.\d+)?')
LATIN_WORD = re.compile(r'[A-Za-z][A-Za-z\-]+')


def _nchars(text):
    """中文按字、西文按词 ×0.6、**数字按个 ×0.6**。

    为什么把数字算进去：方法与结果章节天然是参数密集的（单位、样本量、统计量），
    只数汉字会把"参数写得很实"的段落判成"篇幅不足"，反过来鼓励注水。
    """
    if not text:
        return 0
    cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
    latin = len(LATIN_WORD.findall(text))
    nums = len(NUM_TOKEN.findall(text))
    return int(cjk + (latin + nums) * 0.6)

PLACEHOLDER_PATTERNS = [r'【[^】\n]{0,60}】', r'\{\{[^{}\n]{0,40}\}\}',
                        r'\[证据槽[^\]]*\]', r'\bTODO\b', r'\bTBD\b', r'待补', r'待填']


def placeholders(text):
    hits = []
    for pat in PLACEHOLDER_PATTERNS:
        hits += re.findall(pat, text or '')
    return hits

CITE = re.compile(r'\[(\d+(?:\s*[,-]\s*\d+)*)\]')
FIG_REF = re.compile(r'(?:图|Fig\.?|Figure)\s*(\d+)')
TAB_REF = re.compile(r'(?:表|Table)\s*(\d+)')
FIG_CAP = re.compile(r'^\s*(?:图|Fig\.?|Figure)\s*(\d+)[\s:：.]', re.M)
TAB_CAP = re.compile(r'^\s*(?:表|Table)\s*(\d+)[\s:：.]', re.M)
NUM = re.compile(r'\d+(?:\.\d+)?\s*(?:%|％|μm|mm|nm|°C|℃|MPa|GPa|kPa|Hz|h|min|s|W|mg|g|kg|mL|L|倍|例|名|个)')

# 章节规范名 → (识别正则, 该节最低字数)
SECTION_SPEC = [
    ('abstract', r'摘要|abstract', 150),
    ('introduction', r'引言|前言|introduction', 250),
    ('methods', r'方法|材料与方法|method|materials and methods|experimental', 220),
    ('results', r'结果|results', 200),
    ('discussion', r'讨论|discussion', 250),
    ('conclusion', r'结论|结语|conclusion', 80),
    ('data_availability', r'数据可得性|数据可用性|data availability', 20),
    ('references', r'参考文献|references|bibliography', 1),
]
DECL_PATTERNS = {
    'data_availability': r'数据可得性|数据可用性|data availability',
    'author_contribution': r'作者贡献|author contribution',
    'conflict_of_interest': r'利益冲突|conflict of interest|competing interest',
    'funding': r'基金|资助|funding|grant',
}
CLAIM_CUES = ['是', '为', '表明', '显示', '说明', '导致', '使得', '提高', '降低', '增加',
              '减少', '优于', '低于', '高于', '存在', '具有', '影响', '取决', '相关', '可达']


def find_section(text, pattern):
    """返回该规范名对应的正文；命中多个取字数最多的那个（避免命中目录行）。"""
    best = ''
    for _lvl, title, body in split_sections(text):
        if re.search(pattern, title or '', re.I):
            if _nchars(body) > _nchars(best):
                best = body
    return best


def section_metrics(text):
    out, present = {}, 0
    for name, pat, min_c in SECTION_SPEC:
        body = find_section(text, pat)
        n = _nchars(body)
        ok = n >= min_c
        present += 1 if ok else 0
        out[name] = {'chars': n, 'min': min_c, 'ok': ok}
    return out, round(present / len(SECTION_SPEC), 3)


def fig_table(text):
    figs_body = {int(m) for m in FIG_REF.findall(text)}
    figs_cap = {int(m) for m in FIG_CAP.findall(text)}
    tabs_body = {int(m) for m in TAB_REF.findall(text)}
    tabs_cap = {int(m) for m in TAB_CAP.findall(text)}
    return {
        'fig_refs': sorted(figs_body), 'fig_caps': sorted(figs_cap),
        'fig_pairs': len(figs_body & figs_cap),
        'fig_orphan_caps': sorted(figs_cap - figs_body),
        'tab_refs': sorted(tabs_body), 'tab_caps': sorted(tabs_cap),
        'tab_pairs': len(tabs_body & tabs_cap),
        'tab_orphan_caps': sorted(tabs_cap - tabs_body),
    }


def cite_metrics(text, sources=None):
    keys = set()
    for grp in CITE.findall(text):
        for part in re.split(r'[,\-]', grp):
            part = part.strip()
            if part.isdigit():
                keys.add(int(part))
    refs = (sources or [])
    ref_nums = set()
    for s in refs:
        k = str(s.get('cite_key') or '').strip()
        if k.isdigit():
            ref_nums.add(int(k))
    resolved = (keys & ref_nums) if ref_nums else set()
    return {
        'cite_keys': len(keys),
        'cite_max': max(keys) if keys else 0,
        'ref_entries': len(ref_nums) or len(refs),
        'cite_resolved_rate': round(len(resolved) / len(keys), 3) if keys else 0.0,
        'cite_dangling': sorted(keys - ref_nums)[:10] if ref_nums else [],
    }


def claim_sentences(text):
    out = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith(('#', '|', '>')):
            continue
        for seg in re.split(r'(?<=[。！？!?])\s*', line):
            seg = seg.strip()
            if len(seg) >= 10 and any(c in seg for c in CLAIM_CUES):
                out.append(seg)
    return out


def binding_rate(text):
    sents = claim_sentences(text)
    if not sents:
        return 0.0, 0, 0
    cited = sum(1 for s in sents if CITE.search(s))
    return round(cited / len(sents), 3), cited, len(sents)


def num_trace_rate(text, quotes):
    """正文数值是否能在材料摘录里找到同值。找不到的列出来，供人工确认。"""
    nums = {re.sub(r'\s', '', m) for m in NUM.findall(text)}
    pool = ''.join(re.sub(r'\s', '', q or '') for q in quotes)
    if not nums:
        return 0.0, []
    miss = [n for n in nums if n not in pool]
    return round((len(nums) - len(miss)) / len(nums), 3), sorted(miss)[:12]


def declarations(text):
    hit = [k for k, pat in DECL_PATTERNS.items() if re.search(pat, text, re.I)]
    return len(hit), hit


def measure(text, result=None, min_chars=1800):
    result = result or {}
    text = text or ''
    payload = result.get('result') if isinstance(result.get('result'), dict) else {}
    sources = result.get('sources') or []
    index = payload.get('material_index') or []

    sec, cov = section_metrics(text)
    ft = fig_table(text)
    cm = cite_metrics(text, sources)
    br, cited, total = binding_rate(text)
    quotes = [s.get('quote') for s in sources] + [m.get('quote') for m in index if m.get('quote')]
    ntr, miss = num_trace_rate(text, quotes)
    dn, dlist = declarations(text)

    return {
        'total_chars': _nchars(text),
        'min_chars_ok': _nchars(text) >= min_chars,
        'sections': sec,
        'section_coverage': cov,
        'fig_pairs': ft['fig_pairs'], 'tab_pairs': ft['tab_pairs'],
        'fig_orphan_caps': ft['fig_orphan_caps'], 'tab_orphan_caps': ft['tab_orphan_caps'],
        'cite_keys': cm['cite_keys'], 'ref_entries': cm['ref_entries'],
        'cite_resolved_rate': cm['cite_resolved_rate'], 'cite_dangling': cm['cite_dangling'],
        'claim_sentences': total, 'cited_sentences': cited, 'binding_rate': br,
        'material_index_count': len(index),
        'num_trace_rate': ntr, 'num_untraced': miss,
        'declaration_fields': dn, 'declarations': dlist,
        'placeholder_count': len(placeholders(text)),
    }
