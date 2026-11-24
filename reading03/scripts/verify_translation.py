#!/usr/bin/env python3
"""译文硬信息守恒回扫：数字/单位、引用、图表公式编号、否定限定、术语一致。

用法:
    python3 verify_translation.py <source_segments.json> <result.json> \
        [--glossary glossary.json] [--out verify.json]

逐段比对原文与译文中的"可机械判定的硬信息"，任一不守恒即记 failure。
语义级误译与指代无法机械判定，输出 semantic_review_required=true 提示人工复核。
"""
import argparse
import json
import re
import sys

# 数字 + 可选单位 + 比较符
NUM = re.compile(
    r"(?<![\w])\d+(?:\.\d+)?(?:\s*[–\-~]\s*\d+(?:\.\d+)?)?\s*"
    r"(?:nm|um|μm|mm|cm|m|kg|g|mg|s|ms|min|h|%|°C|K|V|A|mol|M|mM|μM|"
    r"nm/\w+|p\s*[<>=]\s*0?\.\d+|times|fold)?", re.I)
# 引用编号 [12] 或 (Smith, 2020)
CITE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]|\(([A-Z][A-Za-z]+(?:\s+et\s+al\.?)?),\s*(\d{4})\)")
# 图表公式编号（英文）
REFNUM = re.compile(r"\b(Fig(?:ure)?\.?|Table|Eq(?:uation)?\.?|Scheme|Section)\s*(\d+)", re.I)
# 图表公式编号（中文：图 2 / 表 3 / 式(4) / 第 5 节）
REFNUM_ZH = re.compile(r"(图|表|式|公式|第?\s*节)\s*\(?(\d+)\)?")
ZH_MAP = {"图": "fig", "表": "table", "式": "eq", "公式": "eq", "节": "section", "第 节": "section"}
# 否定词
NEG = re.compile(r"\b(no|not|never|without|neither|nor|fail(?:ed|s|ure)?|lack(?:s|ed|ing)?)\b", re.I)
# 限定/强度词
HEDGE = re.compile(r"\b(only|merely|however|although|whereas|despite|tend(?:s|ed)?|may|might|suggest(?:s|ed)?)\b", re.I)
# 中文对应否定词（粗略，用于判断译文是否含否定）
NEG_ZH = re.compile(r"(未|不|无|没有|非|否|缺乏|未能|并未|并非)")


def load(p):
    return json.load(open(p, encoding="utf-8"))


def segs_of_source(src):
    if isinstance(src, dict):
        src = src.get("segments", src.get("source_segments", []))
    d = {}
    for s in src:
        if isinstance(s, dict) and s.get("source_id"):
            d[str(s["source_id"])] = s.get("source_text", "") or ""
    return d


def segs_of_result(res):
    d = {}
    for s in (res.get("result") or {}).get("segments", []):
        if isinstance(s, dict) and s.get("source_id"):
            d[str(s["source_id"])] = (s.get("translation", "") or "", s)
    return d


def norm_nums(text):
    """归一化数字：去掉单位空格差异，保留数值与比较符。"""
    out = []
    for m in NUM.finditer(text or ""):
        s = re.sub(r"\s+", "", m.group(0)).lower()
        out.append(s)
    return out


def norm_cites(text):
    out = []
    for m in CITE.finditer(text or ""):
        if m.group(1):
            out.extend("[" + x.strip() + "]" for x in m.group(1).split(","))
        else:
            out.append("(" + m.group(2) + "," + m.group(3) + ")")
    return out


def norm_refnums(text):
    out = []
    for m in REFNUM.finditer(text or ""):
        out.append(m.group(1).lower().rstrip(".") + str(m.group(2)))
    for m in REFNUM_ZH.finditer(text or ""):
        key = m.group(1).replace(" ", "")
        prefix = ZH_MAP.get(key, ZH_MAP.get(key + " ", "section"))
        out.append(prefix + str(m.group(2)))
    return out


def check_term_consistency(segs, glossary):
    """术语表锁定译名是否全篇统一：出现疑似误译别的译名即报漂移。"""
    failures = []
    if not glossary:
        return failures
    terms = glossary.get("terms", []) if isinstance(glossary, dict) else glossary
    for entry in terms:
        if not isinstance(entry, dict):
            continue
        src_term = entry.get("term", "")
        locked = entry.get("translation", "")
        if not src_term or not locked:
            continue
        note = entry.get("note", "") or ""
        # 从 note 里解析 "别名: A|B" 作为禁止出现的误译
        banned = []
        m = re.search(r"误译[:：]\s*([^;；,，]+)", note)
        if m:
            banned = [x.strip() for x in re.split(r"[|/、]", m.group(1)) if x.strip()]
        for sid, (trans, _s) in segs.items():
            if locked not in trans and banned:
                hit = [b for b in banned if b in trans]
                if hit:
                    failures.append({
                        "kind": "term_drift", "source_id": sid,
                        "term": src_term, "expected": locked,
                        "found": hit, "reason": "术语出现锁定译名之外的误译",
                    })
    return failures


def verify(src_segs, res_segs, glossary):
    failures = []
    semantic_required = False
    for sid, src_text in src_segs.items():
        if sid not in res_segs:
            continue  # 对齐脚本负责漏段
        trans, _meta = res_segs[sid]
        # 数字/单位守恒（原文数值必须在译文出现）
        s_nums, t_nums = norm_nums(src_text), norm_nums(trans)
        for n in s_nums:
            core = re.sub(r"[a-z]", "", n)
            if not core:
                continue
            if not any(core in t or t in n for t in t_nums):
                failures.append({"kind": "number_unit", "source_id": sid,
                                 "value": n, "reason": "原文数值/单位未在译文保留"})
        # 引用编号
        s_c, t_c = norm_cites(src_text), norm_cites(trans)
        for c in s_c:
            if c not in t_c:
                failures.append({"kind": "citation", "source_id": sid,
                                 "value": c, "reason": "引用编号丢失或串位"})
        # 图表公式编号
        s_r, t_r = norm_refnums(src_text), norm_refnums(trans)
        for r in s_r:
            if r not in t_r:
                failures.append({"kind": "refnum", "source_id": sid,
                                 "value": r, "reason": "图表/公式/章节编号未对应"})
        # 否定守恒：原文有否定词，译文须有中文否定标记
        if NEG.search(src_text) and not NEG_ZH.search(trans):
            failures.append({"kind": "negation", "source_id": sid,
                             "value": NEG.search(src_text).group(0),
                             "reason": "原文否定词在译文中缺失，可能反转结论"})
        # 限定词：原文有强度词，译文须含对应中文限定（粗略提示，人工复核）
        if HEDGE.search(src_text):
            semantic_required = True
    failures.extend(check_term_consistency(res_segs, glossary))
    return {
        "status": "passed" if not failures else "failed",
        "segments_checked": len(set(src_segs) & set(res_segs)),
        "failure_count": len(failures),
        "failures": failures,
        "semantic_review_required": semantic_required,
        "note": "机械回扫仅覆盖硬信息；指代、语气、语义级误译需人工复核并写入 uncertainty。",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("result")
    ap.add_argument("--glossary")
    ap.add_argument("--out")
    args = ap.parse_args()
    try:
        src = segs_of_source(load(args.source))
        res = load(args.result)
        res_segs = segs_of_result(res)
        gl = load(args.glossary) if args.glossary else None
        rep = verify(src, res_segs, gl)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
