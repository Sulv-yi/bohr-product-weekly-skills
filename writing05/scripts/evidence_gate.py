#!/usr/bin/env python3
"""证据驱动写作的结构与证据度量（被 validate_result.py / build_outputs.py / eval 共用）。

只度量，不判分。所有指标都能由第三方用同一份 result.json + draft 复算。
口径写在此处，避免上游各自解释：

- total_chars       中文按字计，西文按词 × 0.6 折算（与题目"英文按词计"的常用折法一致）
- claim_coverage    result.claims 覆盖了成稿中多少比例的论断单元（上限 1.0）
- locator_rate      有 page/section/paragraph 任一精确定位的论断占比
- strength_rate     有明确四档强度且未被标 needs_review 的论断占比
- hedge_alignment   表述强度与证据强度相称的论断占"已判定强度"论断的比例
- binding_rate      成稿论断单元中挂引用编号的占比
- source_metadata   来源里 file + (page|section) + quote 三项齐备的占比
- conflict_handled  是否对冲突证据给出显式处置（列出冲突，或声明已检索未发现）
"""
import re

from claim_split import units as claim_units  # noqa: E402

CJK = re.compile(r'[\u4e00-\u9fff]')
WORD = re.compile(r'[A-Za-z][A-Za-z\-\']*')

STRENGTHS = ('strong', 'moderate', 'weak', 'insufficient')
PLACEHOLDER_PATTERNS = [r'\{\{[^{}\n]{0,40}\}\}', r'【[^】\n]{0,40}】', r'\[证据槽[^\]]*\]',
                        r'\bTODO\b', r'\bTBD\b', r'待填', r'待补']
OPEN_FLAGS = ('needs_review', 'pending')

# 与 claim_split.hedge_ok 保持一致
from claim_split import hedge_ok as _hedge_ok  # noqa: E402


def _nchars(text):
    """中文按字、西文按词 ×0.6 折算的有效篇幅。"""
    cjk = len(CJK.findall(text))
    words = len(WORD.findall(text))
    return int(cjk + words * 0.6)


def split_sections(text):
    """按 Markdown 标题切片，返回 {标题: 正文}；正文延伸到下一个同级或更高级标题。"""
    lines = text.split('\n')
    heads = []
    for i, ln in enumerate(lines):
        m = re.match(r'^(#{1,6})\s+(.*)$', ln.strip())
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    body_of = {}
    for k, (i, level, title) in enumerate(heads):
        end = len(lines)
        for j, lv2, _ in heads[k + 1:]:
            if lv2 <= level:
                end = j
                break
        body_of[title] = '\n'.join(lines[i + 1:end])
    if not heads:
        body_of['(全文)'] = text
    return body_of


def placeholders(text):
    hits = []
    for pat in PLACEHOLDER_PATTERNS:
        hits += re.findall(pat, text or '')
    return hits


def _has_locator(c):
    if c.get('locator'):
        return True
    for k in ('page', 'section', 'paragraph', 'para'):
        if c.get(k) not in (None, '', 0):
            return True
    return False


def source_metadata(sources):
    """来源元数据齐备率：file + (page|section) + quote。"""
    if not sources:
        return 0.0
    ok = 0
    for s in sources:
        has_file = bool(s.get('file') or s.get('path'))
        has_loc = any(s.get(k) not in (None, '', 0) for k in ('page', 'section', 'locator'))
        has_quote = bool(s.get('quote'))
        if has_file and has_loc and has_quote:
            ok += 1
    return ok / len(sources)


def measure(draft_text, result=None, min_chars=1400):
    result = result or {}
    payload = result.get('result') if isinstance(result.get('result'), dict) else {}
    claims = payload.get('claims') or []
    table = payload.get('evidence_table') or []
    sources = result.get('sources') or []
    text = draft_text or ''

    us = claim_units(text)
    n_units = len(us)
    cited = sum(1 for u in us if u['cite_marks'])

    # 论断清单指标
    n_claims = len(claims)
    ids = [c.get('claim_id') for c in claims if c.get('claim_id')]
    loc = sum(1 for c in claims if _has_locator(c) or c.get('source_quote') or c.get('quote'))
    graded = [c for c in claims
              if c.get('strength') in STRENGTHS and not (set(c.get('flags') or []) & set(OPEN_FLAGS))]
    ok_hedge = 0
    for c in graded:
        ok, _ = _hedge_ok(c['strength'], c.get('claim') or '')
        if ok:
            ok_hedge += 1

    # 证据表覆盖
    t_claims = {r.get('claim_id') for r in table if r.get('claim_id')}
    t_cover = (len(t_claims & set(ids)) / len(ids)) if ids else 0.0

    conflicts = payload.get('conflicts')
    conflict_handled = bool(conflicts) or bool(payload.get('conflict_search_note'))

    secs = split_sections(text)
    sec_chars = {k: _nchars(v) for k, v in secs.items()}

    return {
        'total_chars': _nchars(text),
        'min_chars_ok': _nchars(text) >= min_chars,
        'section_chars': sec_chars,
        'section_min': min(sec_chars.values()) if sec_chars else 0,
        'draft_units': n_units,
        'draft_cited_units': cited,
        'binding_rate': round(cited / n_units, 3) if n_units else 0.0,
        'claims_count': n_claims,
        'claim_coverage': round(min(n_claims / n_units, 1.0), 3) if n_units else 0.0,
        'locator_rate': round(loc / n_claims, 3) if n_claims else 0.0,
        'strength_rate': round(len(graded) / n_claims, 3) if n_claims else 0.0,
        'hedge_alignment': round(ok_hedge / len(graded), 3) if graded else 0.0,
        'evidence_rows': len(table),
        'evidence_claim_coverage': round(t_cover, 3),
        'conflict_handled': conflict_handled,
        'source_count': len(sources),
        'source_metadata_rate': round(source_metadata(sources), 3),
        'placeholder_count': len(placeholders(text)),
        'open_items': sum(1 for c in claims if set(c.get('flags') or []) & set(OPEN_FLAGS)),
    }
