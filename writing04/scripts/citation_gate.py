#!/usr/bin/env python3
"""引用管理的结构度量：把「挂得对/编得顺/收得净/对得上」变成可计算的量。

度量对象是 result.json（不是稿件文本）——因为这一题的交付物本身就是结构化引用记录，
只有少数几项需要稿件佐证，脚本会显式标注哪些项必须人工对着原稿核。

指标口径：
- 挂得对：citations 条数、claim 覆盖率、claim_location 精确到句的比例、position_ok 比例、
  match_basis 覆盖（必须逐条说明"为何这篇文献支撑这句话"）
- 编得顺：numbering.continuous、dangling 数、uncited 数、样式混用标记
- 收得净：deduplication 三类（merged/kept_separate/pending）各自是否带判据
- 对得上：每条 citation 的 ref_key 能在 sources/文献库快照里找到；format_conversion 字段映射与保留字段非空
- 稿件：manuscript_text 是否随交付（可编辑稿件是本题第一产物）

被 validate_result.py 与 eval/score_output.py 共用。
"""
import re

PLACEHOLDER = re.compile(r'【[^】]*】|\bTODO\b|\bTBD\b|待填|示例文本')


def _rate(n, d):
    return round(n / d, 3) if d else 0.0


def _loc_precise(x):
    """位置是否精确到句：允许 sec2.p3.s2 / §2.3 / 第 2.3 节第 2 句 等写法。"""
    s = str(x or '').strip()
    if not s:
        return False
    return bool(re.search(r'(?:sec|§|p|para|节|段|句)\s*[0-9]', s, re.I)) or s.count('.') >= 1


def measure(result):
    r = result or {}
    res = r.get('result') or {}
    cites = res.get('citations') if isinstance(res.get('citations'), list) else []
    n = len(cites)

    claim_ok = sum(1 for c in cites if isinstance(c, dict) and c.get('claim'))
    loc_ok = sum(1 for c in cites if isinstance(c, dict) and _loc_precise(c.get('claim_location')))
    pos_ok = sum(1 for c in cites if isinstance(c, dict) and c.get('position_ok') is True)
    basis_ok = sum(1 for c in cites
                   if isinstance(c, dict) and isinstance(c.get('match'), dict) and c['match'].get('match_basis'))

    # 文献条目可解析：ref_key 能在 sources 快照或被引用条目集中找到（找不到先记为待核，不判死）
    known = set()
    for s in (r.get('sources') or []):
        if isinstance(s, dict):
            for k in ('ref_key', 'source_id', 'path'):
                if s.get(k):
                    known.add(str(s[k]))
            for k in ('keys', 'ref_keys'):
                if isinstance(s.get(k), list):
                    known.update(str(x) for x in s[k])
    resolved = 0
    for c in cites:
        if not isinstance(c, dict):
            continue
        key = str(c.get('ref_key') or c.get('ref_id') or '')
        if key and (key in known or not known):
            resolved += 1

    nb = res.get('numbering') if isinstance(res.get('numbering'), dict) else {}
    body_nums = nb.get('body_numbers') or []
    list_nums = nb.get('list_numbers') or []
    dangling = nb.get('dangling') or []
    uncited = nb.get('uncited') or []
    contiguous = nb.get('continuous')
    if contiguous is None and body_nums:
        contiguous = body_nums == sorted(body_nums) and (not list_nums or max(body_nums) <= max(list_nums))

    dd = res.get('deduplication') if isinstance(res.get('deduplication'), dict) else {}
    merged = dd.get('merged') or []
    kept = dd.get('kept_separate') or []
    pending = dd.get('pending') or []
    merged_basis = sum(1 for m in merged if isinstance(m, dict) and (m.get('basis') or m.get('reason')))
    kept_reason = sum(1 for m in kept if isinstance(m, dict) and (m.get('reason') or m.get('basis')))
    pending_reason = sum(1 for m in pending if isinstance(m, dict) and m.get('reason'))

    fc = res.get('format_conversion') if isinstance(res.get('format_conversion'), dict) else {}
    mapping = fc.get('field_mapping') if isinstance(fc.get('field_mapping'), dict) else {}
    preserved = fc.get('preserved_fields') if isinstance(fc.get('preserved_fields'), list) else []

    manuscript = str(res.get('manuscript_text') or '')
    mp = str(res.get('manuscript_path') or '')
    ph = PLACEHOLDER.findall(manuscript + "\n" + str(manuscript_paths(res)))

    return {
        'cite_count': n,
        'claim_rate': _rate(claim_ok, n),
        'claim_location_rate': _rate(loc_ok, n),
        'position_ok_rate': _rate(pos_ok, n),
        'match_basis_rate': _rate(basis_ok, n),
        'ref_resolved_rate': _rate(resolved, n),
        'numbering_continuous': bool(contiguous),
        'dangling_count': len(dangling),
        'uncited_count': len(uncited),
        'dedup_merged': len(merged),
        'dedup_merged_basis_rate': _rate(merged_basis, len(merged)),
        'dedup_kept': len(kept),
        'dedup_kept_reason_rate': _rate(kept_reason, len(kept)),
        'dedup_pending': len(pending),
        'dedup_pending_reason_rate': _rate(pending_reason, len(pending)),
        'format_mapping_fields': len(mapping),
        'preserved_fields': len(preserved),
        'manuscript_delivered': bool(manuscript.strip()) or bool(mp),
        'manuscript_chars': len(re.sub(r'\s', '', manuscript)),
        'placeholder_count': len(ph),
        'open_items': len(r.get('uncertainty') or []),
    }


def manuscript_paths(result):
    """收集与稿件相关的路径，供占位符扫描与存在性检查。"""
    res = (result or {}).get('result') or {}
    out = []
    for k in ('manuscript_path', 'library_path'):
        if res.get(k):
            out.append(str(res[k]))
    return out
