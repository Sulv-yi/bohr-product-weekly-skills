"""产出可核验附件：术语审计、改动账、证据表、自查表、预览。

用法：
  python3 scripts/build_outputs.py --result result.json --text popular.md --outdir /app/output
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from popularize_gate import (  # noqa: E402
    abbrev_check, analogy_present, audience_fit, changelog_rate, hedge_retention,
    placeholders, readability, retention, split_sections, strength_align,
    term_consistency, trace_rate, _nchars,
)


def write_term_audit(path, res, text):
    """术语审计：每个概念在成稿里的实际说法与次数。"""
    rows = term_consistency(text, res.get('terms') or [])['rows']
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['concept', 'variant_used', 'count', 'verdict'])
        for concept, hit in rows:
            if not hit:
                w.writerow([concept, '', 0, '未出现'])
                continue
            for v, n in hit:
                w.writerow([concept, v, n, '锁定' if len(hit) == 1 else '多说法'])
    return len(rows)


def write_change_log(path, res):
    """改动账：逐条 op / where / why。"""
    changes = res.get('changes') or []
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['#', 'op', 'where', 'why'])
        for i, c in enumerate(changes, 1):
            if isinstance(c, dict):
                w.writerow([i, c.get('op', ''), c.get('where', ''), c.get('why', '')])
            else:
                w.writerow([i, '', '', str(c)])
    return len(changes)


def write_evidence(path, res, source, text):
    """证据表：数值 / 限定条件 / 图表三类保留情况。"""
    ret = retention(source, text)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['kind', 'total', 'kept_rate', 'missing'])
        w.writerow(['数值', ret['num_total'], ret['num_rate'], '; '.join(ret['num_missing'])])
        w.writerow(['限定条件', ret['limit_total'], ret['limit_rate'], '; '.join(ret['limit_missing'])])
        w.writerow(['图表编号', ret['figtab_total'], ret['figtab_rate'], '; '.join(ret['figtab_missing'])])
    return ret


def write_selfcheck(path, res, source, text):
    # 与 validate_result 同口径：缩写展开只查正文，清单里引用被删原文不算未展开
    body_only = '\n'.join(
        b for _l, t, b in split_sections(text)
        if not re.search(r'修改|变更|改动|清单', t or '')
    ) or text
    a_rate, a_rows = abbrev_check(source, body_only)
    rd = readability(text)
    ana, _ = analogy_present(text)
    hr = hedge_retention(source, text)
    sa = strength_align(source, text)
    tr = trace_rate(text)
    cl = changelog_rate(text)
    af = audience_fit(text, res.get('audience') or '')
    ret = retention(source, text)
    lines = [
        '# 自查表',
        '',
        f"- 字数：{_nchars(text)}",
        f"- 节数：{len(split_sections(text))}",
        f"- 受众声明：{'有' if af['audience_declared'] else '无'}；阅读目的：{'有' if af['purpose_declared'] else '无'}",
        f"- 缩写展开：{a_rate:.0%}；未展开：{', '.join(r[0] for r in a_rows if not r[1]) or '无'}",
        f"- 句均长 {rd['avg_len']}；超长句 {rd['long_ratio']:.0%}；术语密集句 {rd['jargon_density']:.0%}",
        f"- 类比 / 解释性衔接：{ana} 处",
        f"- 数值保留 {ret['num_rate']:.0%}（{ret['num_total']} 个）；限定条件 {ret['limit_rate']:.0%}；图表 {ret['figtab_rate']:.0%}",
        f"- 限定语保留 {hr['keep_rate']:.0%}（源 {hr['src_hedged']} 句 → 成稿 {hr['tgt_hedged']} 句）",
        f"- 越界断言：{sa['violations']} 句",
        f"- 溯源覆盖：{tr['rate']:.0%}（{tr['traced']}/{tr['claims']} 条论断）",
        f"- 改动账：{len(res.get('changes') or [])} 条；正文行内标记 {cl['inline_tags']} 处",
        f"- 占位符：{len(placeholders(text))} 处",
        '',
        '## 结论口径',
        '',
        '本表只报度量结果，不做质量判断。"越界断言 0" 指成稿中没有既无 hedge 又无溯源的强断言句，',
        '不等于每个结论都正确；数值保留率高也不等于取舍合理。判断仍需人读一遍。',
    ]
    open(path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def make_preview(md_path, out_pdf):
    """尝试用 pandoc 生成预览 PDF；不可用时降级为 md 副本。"""
    try:
        r = subprocess.run(
            ['pandoc', md_path, '-o', out_pdf, '--pdf-engine=xelatex',
             '-V', 'CJKmainfont=Microsoft YaHei'],
            capture_output=True, timeout=90,
        )
        if r.returncode == 0 and os.path.exists(out_pdf):
            return 'pandoc'
    except Exception:
        pass
    fallback = os.path.splitext(out_pdf)[0] + '.md'
    open(fallback, 'w', encoding='utf-8').write(open(md_path, encoding='utf-8').read())
    return 'md-fallback:' + os.path.basename(fallback)


def main():
    ap = argparse.ArgumentParser(description='科研成果转化写作产物构建')
    ap.add_argument('--result', required=True)
    ap.add_argument('--text', required=True)
    ap.add_argument('--outdir', required=True)
    a = ap.parse_args()

    res = json.load(open(a.result, encoding='utf-8'))
    text = open(a.text, encoding='utf-8').read()
    source = res.get('source_text') or ''
    if not source and res.get('source_path'):
        sp = res['source_path']
        if not os.path.exists(sp):
            sp = os.path.join(os.path.dirname(os.path.abspath(a.result)), sp)
        if os.path.exists(sp):
            source = open(sp, encoding='utf-8').read()

    os.makedirs(a.outdir, exist_ok=True)
    n_term = write_term_audit(os.path.join(a.outdir, 'term-audit.csv'), res, text)
    n_chg = write_change_log(os.path.join(a.outdir, 'change-log.csv'), res)
    ret = write_evidence(os.path.join(a.outdir, 'evidence-table.csv'), res, source, text)
    write_selfcheck(os.path.join(a.outdir, 'selfcheck.md'), res, source, text)
    how = make_preview(a.text, os.path.join(a.outdir, 'preview.pdf'))

    print(f"term-audit.csv  {n_term} 个概念")
    print(f"change-log.csv  {n_chg} 条改动")
    print(f"evidence-table.csv 数值 {ret['num_rate']:.0%} / 限定 {ret['limit_rate']:.0%} / 图表 {ret['figtab_rate']:.0%}")
    print("selfcheck.md    ok")
    print(f"preview         {how}")


if __name__ == '__main__':
    main()
