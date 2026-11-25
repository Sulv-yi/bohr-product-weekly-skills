#!/usr/bin/env python3
"""成稿质量门槛：把题面的「成稿标准」变成可计算的结构指标。

为什么单列一个模块：0 分→60 分的分水岭是“有没有交出成稿”；60 分往上要拿分，
要交的是“能直接进论文的成稿”——四部分齐全、段落够厚、相关工作真按组比较、
空白有推导链、贡献条条带证据。这些都可以从文本结构上量出来，不必靠自评。

只做结构度量，不判断内容对错；判断留给作者与 eval/ 下的对照协议。
用法（被 validate_result.py 与 eval/score_output.py 共用）：
  from quality_gate import measure
  m = measure(draft_text, sources, uncertainty)
退出码约定：本模块无 CLI。
"""
import re

CJK = re.compile(r'[\u4e00-\u9fff]')
PLACEHOLDER = re.compile(r'【[^】]*】|\[证据槽\]|\[evidence slot\]|\bTODO\b|\bTBD\b')
CITE = re.compile(r'\[\d+(?:[,-]\d+)*\]|\[@[^\]\s]+\]|\([A-Z][A-Za-z\-]+(?:\s+et\s+al\.)?,?\s*(?:19|20)\d{2}\)')
HEADING = re.compile(r'^\s{0,3}(#{1,6})\s*(.+?)\s*$', re.M)

PART_PATTERNS = {
    'background': (r'研究背景|引言背景|背景与动机|background|motivation', r'背景|background|motivation'),
    'related_work': (r'相关工作|相关研究|文献综述|related work|related research|literature review', r'相关工作|相关研究|related'),
    'gap': (r'研究空白|研究缺口|未解决问题|gap|research gap|open problem', r'空白|缺口|gap'),
    'contributions': (r'贡献|本文工作|contributions?', r'贡献|contribution'),
}

GAP_MARKERS = ['共同', '然而', '但', '尚未', '未覆盖', '未涉及', '冲突', '矛盾', '局限', '限制',
               'however', 'yet', 'remains', 'not addressed', 'conflict', 'limitation']
ALIGN_MARKERS = ['本文', '本研究', 'we ', 'this paper', 'this work', 'our ']
EVID_MARKERS = ['§', 'Fig', 'Table', '图 ', '表 ', '式(', 'Section', '章节', '实验结果', 'data']


def _nchars(text):
    """中文字符数 + 英文词数*0.6，用于跨语言统一篇幅口径。"""
    if not text:
        return 0
    cjk = len(CJK.findall(text))
    latin = len(re.findall(r'[A-Za-z][A-Za-z\-]+', text))
    return int(cjk + latin * 0.6)


def split_sections(text):
    """按 Markdown 标题切段，返回 [(level, title, body)]，body 含其下级小节。

    关键：body 一直延伸到「下一个同级或更高级标题」为止，而不是下一个标题。
    否则 `## 相关工作` 的正文只剩到 `### 2.1` 之间的几十个字，分组与篇幅会被误判。
    """
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


NUM_PREFIX = re.compile(r'^\s*(?:第?[0-9一二三四五六七八九十]+[\.、\)）]?|[（(][0-9]+[)）])\s*')


def _title_match(title, pat):
    """标题匹配优先级：去掉编号后「以该要素开头」> 标题中含该要素。

    只看 contains 会误命中文章总标题（如「…：引言与相关工作」），
    而总标题那一节的 body 是全文，会把分组数与篇幅都算错。
    """
    clean = NUM_PREFIX.sub('', title).strip()
    if re.match(pat, clean, re.I):
        return 2
    if re.search(pat, clean, re.I):
        return 1
    return 0


def find_parts(text):
    """把四要素映射到具体段落：标题匹配（开头优先）→ 段首关键词兜底。"""
    sections = split_sections(text)
    found = {}
    for key, (title_pat, body_pat) in PART_PATTERNS.items():
        best = None
        for lvl, title, body in sections:
            score = _title_match(title, title_pat)
            if not score:
                continue
            # 同分取更短的 body（更specific），再取更深的层级
            cand = (score, -lvl, -len(body))
            if best is None or cand > best[0]:
                best = (cand, title, body)
        if best:
            found[key] = (best[1], best[2])
    if len(found) < 4:
        # 退化路径：全文按空行切块，用段首关键词兜底匹配
        blocks = [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]
        for key, (title_pat, body_pat) in PART_PATTERNS.items():
            if key in found:
                continue
            for b in blocks:
                if re.search(body_pat, b[:120], re.I):
                    found[key] = ('', b)
                    break
    return found


def count_groups(related_body):
    """相关工作分组数：三级标题、或「组1/Group A/（1）」等显式分组标记。"""
    if not related_body:
        return 0
    subs = [t for lvl, t, _ in split_sections(related_body) if lvl >= 3]
    if len(subs) >= 2:
        return len(subs)
    marks = re.findall(r'^\s*(?:#{3,6}\s*)?(?:组\s*\d|Group\s+[A-Z0-9]|第[一二三四五六]组|\([1-9]\)|（[1-9]）|[1-9][\.、]\s*[^\n]{2,40})',
                       related_body, re.M)
    uniq = {re.sub(r'\s+', '', m)[:12] for m in marks}
    if len(uniq) >= 2:
        return len(uniq)
    # 兜底：按“路线/方法族”命名段落计数
    paras = [p for p in re.split(r'\n\s*\n', related_body) if _nchars(p) >= 40]
    return len(paras)


def count_contributions(contrib_body):
    """贡献条数：列表项或编号项。"""
    if not contrib_body:
        return 0
    items = re.findall(r'^\s*(?:[-*+]\s+|\(?[1-9][\)\.、]\s*|[（(][1-9][)）]\s*)(\S.{5,})$',
                       contrib_body, re.M)
    return len(items)


def contrib_with_evidence(contrib_body):
    """贡献条目中带证据定位（图/表/节/实验）的条数。"""
    if not contrib_body:
        return 0
    items = re.findall(r'^\s*(?:[-*+]\s+|\(?[1-9][\)\.、]\s*|[（(][1-9][)）]\s*)(\S.{5,})$',
                       contrib_body, re.M)
    n = 0
    for it in items:
        if any(m in it for m in EVID_MARKERS):
            n += 1
    return n


def claim_sentences(text):
    """切论断句：中文按句末标点，英文按 . ! ? 后跟空格；行边界也算断开。

    行边界必须断开：Markdown 里标题与段落各占一行，若不切，标题会粘进下一句，
    句子变长且不带引用标记，把绑定率压低到失真。
    """
    parts = re.split(r'(?<=[。！？；!?;])\s*|\n+', text)
    return [p.strip() for p in parts if _nchars(p) >= 12]


def binding_rate(text):
    """论断-引用绑定率：带引用标记的论断句占比。

    只应对「需要有出处的论断」计数：背景、相关工作、空白三节。
    贡献陈述与本文结论本就不引他人文献，计入会把比率稀释成无意义的小数。
    """
    sents = claim_sentences(text)
    if not sents:
        return 0.0
    hit = sum(1 for s in sents if CITE.search(s))
    return round(hit / len(sents), 3)


def gap_chain(background, gap):
    """空白推导链：是否由已引工作限制推出（限制词）并落到本文（对齐词）。"""
    blob = f"{background or ''}\n{gap or ''}"
    has_limit = any(m in blob for m in GAP_MARKERS)
    has_align = any(m in blob.lower() for m in [x.lower() for x in ALIGN_MARKERS])
    return bool(has_limit and has_align)


def source_metadata(sources):
    """来源元数据完整率：file/quote/claim 三项齐备且带定位（page 或 section）。"""
    if not sources:
        return 0.0
    ok = 0
    for s in sources:
        if not isinstance(s, dict):
            continue
        if s.get('claim') and s.get('quote') and s.get('file') and (s.get('page') or s.get('section')):
            ok += 1
    return round(ok / len(sources), 3)


def measure(draft_text, sources=None, uncertainty=None, min_chars=1600):
    """返回结构指标字典；键名与 eval/rubric.json 的 metrics 一一对应。"""
    sources = sources or []
    uncertainty = uncertainty or []
    parts = find_parts(draft_text)
    lens = {k: _nchars(v[1]) for k, v in parts.items()}
    rel = parts.get('related_work', ('', ''))[1]
    con = parts.get('contributions', ('', ''))[1]
    cited_scope = "\n".join(parts.get(k, ('', ''))[1] for k in ('background', 'related_work', 'gap'))
    n_con = count_contributions(con)
    with_ev = contrib_with_evidence(con)
    total = _nchars(draft_text)
    ph = PLACEHOLDER.findall(draft_text)
    return {
        'total_chars': total,
        'min_chars_ok': total >= min_chars,
        'four_part_coverage': round(len(parts) / 4, 3),
        'missing_parts': [k for k in PART_PATTERNS if k not in parts],
        'section_chars': lens,
        'section_min_ok': {
            'background': lens.get('background', 0) >= 350,
            'related_work': lens.get('related_work', 0) >= 550,
            'gap': lens.get('gap', 0) >= 150,
            'contributions': lens.get('contributions', 0) >= 150,
        },
        'related_groups': count_groups(rel),
        'contributions': n_con,
        'contributions_with_evidence': with_ev,
        'contribution_evidence_rate': round(with_ev / n_con, 3) if n_con else 0.0,
        'claim_binding_rate': binding_rate(cited_scope),
        'gap_chain_present': gap_chain(parts.get('background', ('', ''))[1], parts.get('gap', ('', ''))[1]),
        'source_count': len(sources),
        'source_metadata_rate': source_metadata(sources),
        'placeholder_count': len(ph),
        'manual_review_items': len(uncertainty),
    }
