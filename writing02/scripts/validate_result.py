#!/usr/bin/env python3
"""校验输出契约：case_id / status / result / sources / uncertainty / changes。

用法: python validate_result.py <result.json> [--case case.json] [--out check.json]
纯标准库实现。
"""
import sys
import json
import os

REQUIRED_TOP = {'case_id', 'status', 'result', 'sources', 'uncertainty', 'changes'}
REQUIRED_RESULT = {'polished_text', 'change_log', 'term_decisions'}
VALID_STATUS = {'success', 'partial', 'unable_to_determine', 'refused'}
CHANGE_TYPES = {'grammar', 'agreement', 'article_prep', 'tense_voice', 'punctuation',
                'terminology', 'register', 'conciseness', 'chinese_english', 'split'}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'usage: validate_result.py <result.json> [--case case.json] [--out check.json]'}))
        return 2
    path = sys.argv[1]
    case_id = None
    out = None
    if '--case' in sys.argv:
        try:
            case_id = json.load(open(sys.argv[sys.argv.index('--case') + 1], encoding='utf-8')).get('case_id')
        except Exception:
            pass
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]

    try:
        d = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        print(json.dumps({'error': f'{type(e).__name__}: {e}'}))
        return 2

    problems = []
    missing = REQUIRED_TOP - set(d)
    if missing:
        problems.append({'field': 'top', 'issue': 'missing fields', 'detail': sorted(missing)})
    if d.get('status') not in VALID_STATUS:
        problems.append({'field': 'status', 'issue': 'invalid value', 'detail': str(d.get('status'))})
    if case_id and d.get('case_id') != case_id:
        problems.append({'field': 'case_id', 'issue': 'mismatch',
                         'expected': case_id, 'actual': d.get('case_id')})
    r = d.get('result') or {}
    if not isinstance(r, dict):
        problems.append({'field': 'result', 'issue': 'must be object'})
        r = {}
    missing_r = REQUIRED_RESULT - set(r)
    if missing_r:
        problems.append({'field': 'result', 'issue': 'missing fields', 'detail': sorted(missing_r)})
    if not isinstance(r.get('polished_text'), str) or not r['polished_text'].strip():
        problems.append({'field': 'result.polished_text', 'issue': 'must be non-empty text'})
    cl = r.get('change_log')
    if not isinstance(cl, list) or not cl:
        problems.append({'field': 'result.change_log', 'issue': 'must be non-empty list'})
    else:
        for i, c in enumerate(cl):
            if not isinstance(c, dict):
                problems.append({'field': f'change_log[{i}]', 'issue': 'must be object'})
                continue
            for k in ('original', 'revised', 'reason'):
                if not c.get(k):
                    problems.append({'field': f'change_log[{i}].{k}', 'issue': 'missing'})
            ct = c.get('change_type')
            if ct is None:
                problems.append({'field': f'change_log[{i}].change_type', 'issue': 'missing'})
            else:
                types = ct if isinstance(ct, list) else [ct]
                unknown = [t for t in types if t and t not in CHANGE_TYPES]
                if unknown:
                    problems.append({'field': f'change_log[{i}].change_type',
                                     'issue': 'unknown type', 'detail': unknown})
    if not isinstance(d.get('sources'), list):
        problems.append({'field': 'sources', 'issue': 'must be list'})
    else:
        for i, s in enumerate(d['sources']):
            if not isinstance(s, dict) or not s.get('claim') or not s.get('location'):
                problems.append({'field': f'sources[{i}]', 'issue': 'claim/location missing'})
    for k in ('uncertainty', 'changes'):
        if not isinstance(d.get(k), list):
            problems.append({'field': k, 'issue': 'must be list'})

    result = {'status': 'passed' if not problems else 'failed',
              'case_id': d.get('case_id'), 'problems': problems}
    print(json.dumps({'status': result['status'], 'problems': len(problems)}, ensure_ascii=False))
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
