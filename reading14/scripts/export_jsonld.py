#!/usr/bin/env python3
"""把 Nanopublication 结构转成标准 JSON-LD（nanopub 三分区：assertion/provenance/publication_info），
并做导出可解析性校验。支持 --check-only 仅校验不产出。

JSON-LD 结构参考 nanopublication 的三段式：
  @graph 含 assertion、provenance、pubinfo 三个命名图，head 声明三者的 triples。

用法:
    python3 export_jsonld.py <result.json> --out nanopubs.jsonld [--vocab assets/relation_vocab.json]
    python3 export_jsonld.py <result.json> --check-only
"""
import argparse
import json
import sys

NP_URI = "http://purl.org/nanopub/"

ASSERT_FIELDS = ['subject', 'relation', 'object', 'claim_text']
SRC_FIELDS = ['paper', 'authors', 'year', 'identifier']


def build_np_uri(nid):
    return NP_URI + str(nid).strip() + '#'


def convert(result):
    nps = (result.get('result') or {}).get('nanopublications') or []
    graphs = []
    heads = []
    for np_ in nps:
        nid = str(np_.get('id', ''))
        base = build_np_uri(nid)
        a = np_.get('assertion') or {}
        p = np_.get('provenance') or {}
        src = p.get('source') or {}
        evs = p.get('evidence') or []

        assertion = {
            '@id': base + 'assertion',
            'subject': a.get('subject', ''),
            'relation': a.get('relation', ''),
            'object': a.get('object', ''),
            'claim_text': a.get('claim_text', ''),
            'conditions': a.get('conditions', ''),
            'confidence': a.get('confidence', ''),
            'confidence_basis': a.get('confidence_basis', ''),
        }
        provenance = {
            '@id': base + 'provenance',
            'source': {
                'paper': src.get('paper', ''),
                'authors': src.get('authors', []),
                'year': src.get('year', ''),
                'version': src.get('version', ''),
                'identifier': src.get('identifier', ''),
            },
            'evidence': [
                {'text': e.get('text', ''), 'location': e.get('location', ''), 'type': e.get('type', '')}
                for e in evs if isinstance(e, dict)
            ],
        }
        pubinfo = {
            '@id': base + 'pubinfo',
            'created_by': (np_.get('publication_info') or {}).get('created_by', ''),
            'case_id': result.get('case_id', ''),
        }
        graphs.extend([assertion, provenance, pubinfo])
        heads.append({
            '@id': base + 'head',
            'assertion': assertion['@id'],
            'provenance': provenance['@id'],
            'pubinfo': pubinfo['@id'],
        })
    return {
        '@context': {
            'subject': {'@id': 'http://purl.org/nanopub/terms/subject'},
            'relation': {'@id': 'http://purl.org/nanopub/terms/relation'},
            'object': {'@id': 'http://purl.org/nanopub/terms/object'},
            'evidence': {'@id': 'http://purl.org/nanopub/terms/evidence', '@container': '@list'},
            'source': {'@id': 'http://purl.org/nanopub/terms/source'},
            'provenance': {'@id': 'http://purl.org/nanopub/terms/provenance'},
            'assertion': {'@id': 'http://purl.org/nanopub/terms/assertion'},
            'pubinfo': {'@id': 'http://purl.org/nanopub/terms/pubinfo'},
        },
        '@graph': heads + graphs,
        'case_id': result.get('case_id', ''),
        'nanopub_count': len(nps),
    }


def check(doc):
    errors, warnings = [], []
    if not isinstance(doc, dict):
        return {'status': 'failed', 'errors': ['导出不是对象']}
    for f in ('@context', '@graph', 'case_id'):
        if f not in doc:
            errors.append(f'导出缺 {f}')
    graph = doc.get('@graph') or []
    heads = [g for g in graph if isinstance(g, dict) and 'assertion' in g and '@id' in g]
    asserts = [g for g in graph if isinstance(g, dict) and 'relation' in g and 'claim_text' in g]
    provs = [g for g in graph if isinstance(g, dict) and 'source' in g and 'evidence' in g]
    pubinfos = [g for g in graph if isinstance(g, dict) and 'created_by' in g]
    if not heads:
        errors.append('无 head 节点（三图引用不完整）')
    if not asserts:
        errors.append('无 assertion 节点')
    if not provs:
        errors.append('无 provenance 节点')
    if not pubinfos:
        warnings.append('无 pubinfo 节点')
    for h in heads:
        for ref in ('assertion', 'provenance', 'pubinfo'):
            if not h.get(ref):
                errors.append(f'head {h.get("@id")} 缺 {ref} 引用')
    for a in asserts:
        for f in ASSERT_FIELDS:
            if not str(a.get(f, '')).strip():
                errors.append(f'assertion {a.get("@id")} 缺 {f}')
    for p in provs:
        for f in SRC_FIELDS:
            if not p.get('source', {}).get(f):
                errors.append(f'provenance {p.get("@id")} source 缺 {f}')
        if not p.get('evidence'):
            errors.append(f'provenance {p.get("@id")} 无 evidence')
    try:
        json.dumps(doc, ensure_ascii=False)
    except Exception as e:
        errors.append(f'不可序列化: {e}')
    return {
        'status': 'passed' if not errors else 'failed',
        'errors': errors, 'warnings': warnings,
        'counts': {'heads': len(heads), 'assertions': len(asserts),
                   'provenances': len(provs), 'pubinfos': len(pubinfos)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    ap.add_argument('--out')
    ap.add_argument('--check-only', action='store_true')
    args = ap.parse_args()
    result = json.load(open(args.result, encoding='utf-8'))
    doc = convert(result)
    rep = check(doc)
    if args.out and not args.check_only:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        rep['out'] = args.out
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
