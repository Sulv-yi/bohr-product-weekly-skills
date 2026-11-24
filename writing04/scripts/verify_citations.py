#!/usr/bin/env python3
"""核验参考文献与引用管理结果的四性质（本 Skill 核心）。

四性质（对应题面四问）：
  挂得对 placed  : 每条引用指向“需要来源支撑的论断句”，位置精确到句，不在段尾/图表注附近凑数。
  编得顺 numbered: 正文编号与文末列表同步、连续、无悬空/未引用；交叉引用与样式一致。
  收得净 deduped : 重复条目有合并记录与判据；同名作者不同文献不误合并；歧义项保留人工确认。
  对得上 matched : 每条引用真实存在、元数据齐全（DOI 可核验）；正文论断主题与所引文献 title/abstract 对应，逐句可说清。

被检 result.json 约定：
{
 "case_id": ..., "status": ...,
 "result": {
   "manuscript_path": "...", "library_path": "...",  // 或内联
   "citations": [
     {"cite_id":"c1","claim":"正文论断句原文","claim_location":"sec2.p3.s2",
      "ref_key":"smith2020","position_ok":true,
      "match":{"topic_terms":["..."],"match_basis":"...","strength":"direct|indirect"}}
   ],
   "deduplication": {"merged":[{"a":"k1","b":"k2","basis":"DOI一致"}],
                     "kept_separate":[{"a":"k1","b":"k3","reason":"同名作者不同题名"}],
                     "pending":[...]},
   "numbering": {"body_numbers":[...],"list_numbers":[...],"continuous":true,
                 "dangling":[],"uncited":[]},
   "format_conversion": {"from":"BibTeX","to":"GB/T 7714-2015","field_mapping":{...},
                         "preserved_fields":["doi","volume","issue","pages"]}
 },
 "sources": [...], "uncertainty": [...], "changes": [...]
}

用法:
    python3 verify_citations.py <result.json> --library entries.json [--manuscript text.md]
        [--dedupe dedupe.json] [--numbering numbering.json] [--out verify.json] [--strict]
退出码：无 error 为 0，否则 1。
"""
import argparse
import json
import re
import sys

VALID_STATUS = {'success', 'partial', 'unable', 'refused'}
REQUIRED_META = ['title', 'authors', 'year', 'doi']
TOPIC_STOP = set('the a an of in on for and or with we our this that these those study paper pattern method result'.split())


def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[^\w\u4e00-\u9fa5]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def content_tokens(s):
    # 支持字符串或字符串数组（topic_terms 常为数组）
    if isinstance(s, (list, tuple)):
        text = ' '.join(str(x) for x in s)
    else:
        text = s or ''
    return {t for t in norm(text).split() if len(t) > 2 and t not in TOPIC_STOP}


def load_json(path):
    return json.load(open(path, encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--library', required=True)
    ap.add_argument('--manuscript', default='')
    ap.add_argument('--dedupe', default='')
    ap.add_argument('--numbering', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()

    result = load_json(args.result)
    lib = load_json(args.library)
    by_key = {e.get('key'): e for e in lib.get('entries', [])}
    dedupe = load_json(args.dedupe) if args.dedupe else None
    numbering = load_json(args.numbering) if args.numbering else None
    manuscript = open(args.manuscript, encoding='utf-8', errors='replace').read() if args.manuscript else ''

    errors, warnings = [], []
    checks = {"placed": "ok", "numbered": "ok", "deduped": "ok", "matched": "ok"}
    R = result.get('result') or {}
    citations = R.get('citations') or []

    if result.get('status') not in VALID_STATUS:
        errors.append("status 非法: %r" % result.get('status'))

    # ---- 挂得对 placed ----
    if not citations:
        errors.append("citations 为空"); checks['placed'] = 'failed'
    for i, c in enumerate(citations):
        tag = "cite[%s]" % (c.get('cite_id') or i)
        if not isinstance(c, dict):
            errors.append(tag + " 非对象"); continue
        claim = str(c.get('claim') or '').strip()
        loc = str(c.get('claim_location') or '').strip()
        if not claim:
            errors.append(tag + " 缺论断句 claim"); checks['placed'] = 'failed'
        if not loc:
            errors.append(tag + " 缺论断位置 claim_location（须精确到句）")
            checks['placed'] = 'failed'
        elif re.match(r'^\s*(图|表|Fig|Table|Figure|图表)\s*\d', loc, re.I):
            errors.append(tag + " 引用位置落在图表注附近而非论断句: " + loc)
            checks['placed'] = 'failed'
        if c.get('position_ok') is False:
            errors.append(tag + " 自报 position_ok=false（引用未挂到需支撑的论断）")
            checks['placed'] = 'failed'
        if manuscript and claim:
            if norm(claim) not in norm(manuscript):
                # 允许逐词覆盖 >= 0.85
                toks = [t for t in norm(claim).split() if len(t) > 2]
                hay = norm(manuscript)
                hit = sum(1 for t in toks if t in hay)
                if not toks or hit / len(toks) < 0.85:
                    errors.append(tag + " 论断句不在稿件原文中（疑似编造/改写）")
                    checks['placed'] = 'failed'

    # ---- 对得上 matched ----
    for i, c in enumerate(citations):
        tag = "cite[%s]" % (c.get('cite_id') or i)
        key = c.get('ref_key')
        entry = by_key.get(key)
        if not entry:
            errors.append(tag + " 引用了不存在的文献条目: %r" % key)
            checks['matched'] = 'failed'
            continue
        # 元数据核验
        missing = [f for f in REQUIRED_META if not str(entry.get(f) or '').strip()]
        if missing:
            sev = errors if ('doi' in missing and not entry.get('url')) else warnings
            sev.append(tag + " 文献 %s 元数据缺失: %s" % (key, missing))
            if sev is errors:
                checks['matched'] = 'failed'
        doi = str(entry.get('doi') or '').strip()
        if doi and not re.match(r'^10\.\d{4,9}/\S+$', doi):
            warnings.append(tag + " DOI 格式疑似非法: " + doi[:40])
        # 主题匹配：claim 关键词与文献 title/abstract 交集
        m = c.get('match') or {}
        strength = m.get('strength')
        if strength not in ('direct', 'indirect'):
            warnings.append(tag + " match.strength 未标明 direct/indirect")
        if strength == 'indirect' and not result.get('uncertainty'):
            warnings.append(tag + " 间接匹配但 uncertainty 为空")
        claim_terms = content_tokens(c.get('claim')) | content_tokens(m.get('topic_terms') or [])
        ref_terms = content_tokens(entry.get('title')) | content_tokens(entry.get('abstract'))
        overlap = claim_terms & ref_terms
        basis = str(m.get('match_basis') or '').strip()
        if not basis:
            warnings.append(tag + " 缺 match_basis（逐句说清为何匹配）")
        if claim_terms and ref_terms and not overlap and not basis:
            errors.append(tag + " 论断与文献主题无词面交集且无匹配依据（疑似错引）")
            checks['matched'] = 'failed'

    # ---- 编得顺 numbered ----
    # 内联数据是最终交付，必须自身通过检查；外部 --numbering 只是旁证，不豁免内联。
    nb = R.get('numbering') or {}
    def check_nums(src_nums, tagname):
        b = src_nums.get('body_numbers') or []
        l = src_nums.get('list_numbers') or []
        if src_nums.get('status') == 'failed' or src_nums.get('errors'):
            errors.append("编得顺[%s]: 编号检查失败: %s" % (tagname, (src_nums.get('errors') or [])[:2]))
            checks['numbered'] = 'failed'
        if b and sorted(b) != list(range(1, max(b) + 1)):
            errors.append("编得顺[%s]: 正文编号不连续: %s" % (tagname, b[:10]))
            checks['numbered'] = 'failed'
        if l and sorted(l) != list(range(1, len(l) + 1)):
            errors.append("编得顺[%s]: 文末列表编号不连续: %s" % (tagname, l[:10]))
            checks['numbered'] = 'failed'
        if l and b:
            dangling = sorted(set(b) - set(l))
            if dangling:
                errors.append("编得顺[%s]: 悬空引用: %s" % (tagname, dangling))
                checks['numbered'] = 'failed'
        return b, l

    in_body, in_list = check_nums(nb, '内联') if nb else ([], [])
    ex_body, ex_list = check_nums(numbering, '外部') if numbering else ([], [])
    if nb and numbering and (in_body != ex_body or in_list != ex_list):
        errors.append("编得顺: 内联 numbering 与外部编号检查结果不一致（内联 %s/%s vs 外部 %s/%s）"
                      % (in_body, in_list, ex_body, ex_list))
        checks['numbered'] = 'failed'
    if not in_body and not in_list and not numbering:
        warnings.append("未提供编号检查结果（numbering 内联或 --numbering 均应给其一）")

    # ---- 收得净 deduped ----
    # 内联去重结果必须自身通过检查，外部 --dedupe 不豁免内联。
    ded = R.get('deduplication') or {}
    def check_dedup(merges, dnm, tagname):
        dnm_pairs = {frozenset([str(x.get('a')), str(x.get('b'))]) for x in dnm}
        for m in merges:
            basis = m.get('basis') or m.get('evidence') or ''
            if not basis:
                errors.append("收得净[%s]: 合并缺判据: %s" % (tagname, str(m)[:60]))
                checks['deduped'] = 'failed'
            pair = frozenset([str(m.get('a')), str(m.get('b'))])
            if pair in dnm_pairs:
                errors.append("收得净[%s]: 把明确不得合并的条目做了合并: %s" % (tagname, sorted(pair)))
                checks['deduped'] = 'failed'

    in_merges = ded.get('merged') or []
    in_dnm = ded.get('kept_separate') or []
    in_unc = ded.get('pending') or []
    check_dedup(in_merges, in_dnm, '内联')
    uncertain = in_unc
    if dedupe:
        merges = dedupe.get('merge') or []
        dnm = dedupe.get('do_not_merge') or []
        uncertain = dedupe.get('uncertain') or []
        check_dedup(merges, dnm, '外部')
    if uncertain and not result.get('uncertainty'):
        warnings.append("有 %d 条去重歧义项但未写入 uncertainty" % len(uncertain))

    # 格式转换字段保留
    fc = R.get('format_conversion') or {}
    if fc:
        preserved = set(fc.get('preserved_fields') or [])
        for f in ('doi', 'volume', 'issue', 'pages'):
            if f not in preserved:
                warnings.append("格式转换未声明保留关键字段: " + f)

    status = 'partial' if (errors or warnings) else ('success' if not args.strict else 'success')
    out = {
        "status": status,
        "checks": checks,
        "counts": {"citations": len(citations), "entries": len(by_key),
                   "errors": len(errors), "warnings": len(warnings)},
        "errors": errors,
        "warnings": warnings,
        "failed_properties": [k for k, v in checks.items() if v != 'ok'],
    }
    if args.out:
        json.dump(out, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
