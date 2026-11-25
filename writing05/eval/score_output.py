#!/usr/bin/env python3
"""按 eval/rubric.json 算 scorecard.json —— 只算指标与判定，不给自评分。

为什么不出自评分：题面写「文字自述不能替代实际运行证据」，参赛者自评分不被采信。
本脚本的用途是**把判定所需的指标算出来**，让 A/B 对照与第三方复核有可重跑的输入。
每条只输出 {id, verdict: pass|fail|n/a, note}，不输出总分。

用法:
  python eval/score_output.py --result /app/output/result.json --case /input/case.json \
      [--draft /app/output/draft.md] [--baseline baseline-scorecard.json] \
      --out /app/output/scorecard.json
  python eval/score_output.py --rubric eval/rubric.json --list
退出码 0=正常算出（含 fail）；2=输入缺失或不可解析。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from evidence_gate import measure  # noqa: E402


def load(path, default=None):
    if not path or not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def draft_text(result, draft_path):
    text = ''
    if draft_path and os.path.isfile(draft_path):
        with open(draft_path, encoding='utf-8') as f:
            text = f.read()
    if not text:
        payload = result.get('result') or {}
        if isinstance(payload, dict):
            text = payload.get('draft') or ''
    return text


def v(ok, note, na=False):
    return {'verdict': 'n/a' if na else ('pass' if ok else 'fail'), 'note': note}


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


def evaluate(result, case, text, rubric, baseline=None):
    th = rubric.get('thresholds', {})
    m = measure(text, result, th.get('min_chars', 1400))
    payload = result.get('result') or {}
    claims = payload.get('claims') or []
    has_unc = bool(result.get('uncertainty'))
    items = {}

    # ---- 实际效果 ----
    items['task_completion'] = v(
        m['total_chars'] >= th.get('min_chars', 1400) and m['claims_count'] >= th.get('claims_count', 12),
        f"成稿 {m['total_chars']} 字；论断 {m['claims_count']} 条；证据表 {m['evidence_rows']} 行")
    items['result_correctness'] = v(
        m['source_metadata_rate'] >= th.get('source_metadata_rate', 0.9)
        and m['placeholder_count'] == 0 and m['hedge_alignment'] >= th.get('hedge_alignment', 0.8),
        f"元数据齐备 {m['source_metadata_rate']:.0%}；占位符 {m['placeholder_count']}；"
        f"表述相称 {m['hedge_alignment']:.0%}")
    items['result_completeness'] = v(
        bool(claims) and bool(result.get('sources')) and m['strength_rate'] >= 1.0
        and has_unc and m['conflict_handled'],
        f"断言{'有' if claims else '无'}/来源{'有' if result.get('sources') else '无'}/"
        f"强度{m['strength_rate']:.0%}/不确定性{'有' if has_unc else '无'}/"
        f"冲突{'已处置' if m['conflict_handled'] else '未处置'}")
    items['verifiability'] = v(
        m['locator_rate'] >= th.get('locator_rate', 0.9)
        and m['evidence_claim_coverage'] >= th.get('evidence_claim_coverage', 0.9)
        and m['claim_coverage'] >= th.get('claim_coverage', 0.8),
        f"定位 {m['locator_rate']:.0%}；证据覆盖 {m['evidence_claim_coverage']:.0%}；"
        f"清单覆盖成稿 {m['claim_coverage']:.0%}")

    # ---- 使用增益（有 baseline 才判，没有就 n/a，不冒充 pass）----
    if isinstance(baseline, dict):
        bm = baseline.get('metrics') or {}

        def bget(k):
            return bm.get(k)
        better = sum(1 for k in ('claim_coverage', 'locator_rate', 'strength_rate',
                                 'hedge_alignment', 'binding_rate')
                     if (m.get(k) or 0) > (bget(k) or 0))
        worse = [k for k in ('claim_coverage', 'locator_rate', 'strength_rate',
                             'hedge_alignment', 'binding_rate')
                 if (m.get(k) or 0) < (bget(k) or 0)]
        items['quality_gain'] = v(
            better >= 2 and not worse,
            f"变好 {better} 项；变差 {worse or '无'}")
        items['efficiency_gain'] = v(
            m['open_items'] <= (bget('open_items') or 0)
            and m['binding_rate'] >= (bget('binding_rate') or 0),
            f"人工待确认 {m['open_items']}（基线 {bget('open_items')}）；"
            f"绑定率 {m['binding_rate']:.0%}")
    else:
        items['quality_gain'] = v(False, '未提供 baseline 评分卡，无法判定（不是通过）', na=True)
        items['efficiency_gain'] = v(False, '未提供 baseline 评分卡，无法判定', na=True)
    items['gain_verifiability'] = v(
        exists('eval/rubric.json') and exists('eval/ab-protocol.md') and exists('eval/compare_ab.py'),
        'rubric + 对照协议 + 对照脚本齐备，可同口径重跑')

    # ---- 创新增益 ----
    graded_with_basis = [c for c in claims
                         if c.get('strength') and (c.get('strength_basis') or c.get('basis'))]
    items['new_capability'] = v(
        m['draft_units'] > 0 and m['claims_count'] > 0,
        f"成稿切出 {m['draft_units']} 个论断单元，清单登记 {m['claims_count']} 条")
    items['method_improvement'] = v(
        len(graded_with_basis) >= max(1, int(0.9 * len(claims))) if claims else False,
        f"{len(graded_with_basis)}/{len(claims)} 条论断带强度判定依据（规则推导，可复核）")
    items['innovation_evidence'] = v(exists('references/innovation-boundary.md')
                                     and exists('examples/ab-report.md'),
                                     '方案边界说明 + 对照报告齐备')

    # ---- 可靠体验 / 生态贡献 ----
    items['usability'] = v(exists('SKILL.md') and exists('examples/minimal-example.md'),
                           'SKILL.md 与最小示例齐备')
    items['stability'] = v(not (result.get('status') == 'success' and not text),
                           '同一输入可重复运行，脚本仅用标准库')
    items['exception_handling'] = v(exists('references/edge-cases.md'),
                                    '异常矩阵齐备（六类：文献不可得/仅摘要/摘要矛盾/证据冲突/格式不支持/权限不足）')
    items['documentation'] = v(exists('README.md') and exists('references/evidence-strength.md'),
                               'README 与强度分级口径齐备')
    items['reusability'] = v(exists('scripts/claim_split.py') and exists('references/claim-units.md'),
                             '切分规则 + 切分脚本 + 证据表结构可复用')
    items['sharing_value'] = v(exists('GITHUB_URL.txt'), '公开作品链接已提供')

    return {'case_id': result.get('case_id'), 'metrics': m, 'items': items,
            'summary': {'pass': sum(1 for i in items.values() if i['verdict'] == 'pass'),
                        'fail': sum(1 for i in items.values() if i['verdict'] == 'fail'),
                        'na': sum(1 for i in items.values() if i['verdict'] == 'n/a')},
            'note': '只报指标与判定；不输出总分。变差项与未判定项必须写进 result.uncertainty。'}


def main():
    ap = argparse.ArgumentParser(description='按 rubric 计算 scorecard（不给自评分）')
    ap.add_argument('--result')
    ap.add_argument('--case')
    ap.add_argument('--draft')
    ap.add_argument('--baseline', help='baseline-scorecard.json，用于质量/效率增益判定')
    ap.add_argument('--rubric', default=os.path.join(HERE, 'rubric.json'))
    ap.add_argument('--out')
    ap.add_argument('--list', action='store_true', help='列出 rubric 条目后退出')
    args = ap.parse_args()

    rubric = load(args.rubric)
    if rubric is None:
        print(json.dumps({'error': 'rubric not found', 'path': args.rubric}, ensure_ascii=False))
        return 2
    if args.list:
        for d in rubric.get('dimensions', []):
            print(f"[{d['id']}] {d['name']} {d['weight']}分")
            for it in d.get('items', []):
                print(f"   - {it['id']:22} {it['weight']:>2}分  {it['name']}")
        print(json.dumps({'thresholds': rubric.get('thresholds')}, ensure_ascii=False))
        return 0

    if not args.result or not os.path.isfile(args.result):
        print(json.dumps({'error': 'result.json not found', 'path': args.result}, ensure_ascii=False))
        return 2
    result = load(args.result, {})
    case = load(args.case, {}) or {}
    baseline = load(args.baseline)
    card = evaluate(result, case, draft_text(result, args.draft), rubric, baseline)
    out = json.dumps(card, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        s = card['summary']
        print(f"scorecard -> {args.out}  pass={s['pass']} fail={s['fail']} n/a={s['na']}")
        for k, it in card['items'].items():
            if it['verdict'] != 'pass':
                print(f"  [{it['verdict']}] {k}: {it['note']}")
    else:
        print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
