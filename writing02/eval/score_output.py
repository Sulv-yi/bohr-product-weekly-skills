#!/usr/bin/env python3
"""把润色结果算成可复核的指标，产出 scorecard.json。

用法:
    python eval/score_output.py --result /app/output/result.json \\
        --case /input/case.json --out /app/output/scorecard.json

    # 只看阈值和指标定义，不计算
    python eval/score_output.py --show-rubric

设计要点：
- 所有数字都由原文与改文实际比对得出，脚本里没有任何"自评"输入口，
  因此拿到的分数可以被他人在同一份原文上复现。
- 阈值来自 eval/rubric.json；改阈值即改验收标准，不需要改代码。
- 只依赖标准库，可在评测容器内直接运行。
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

HARD_KINDS = {"number_unit", "number", "citation", "figure_table"}
HEDGE_KINDS = {"hedge", "hedge_zh"}
NEG_KINDS = {"negation", "negation_zh"}

DEFAULT_THRESHOLDS = {
    "invariant_conservation": 1.0,
    "hedge_conservation": 1.0,
    "term_uniqueness": 1.0,
    "segment_coverage": 1.0,
    "edit_note_coverage": 0.9,
    "max_sentence_change_rate": 0.6,
}


def load_module(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("m_" + os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def norm_key(kind, value):
    return kind + "|" + re.sub(r"\s+", "", str(value)).lower()


def kind_counts(lock_report, kinds):
    out = {}
    for c in lock_report["counts"]:
        if c["kind"] in kinds:
            out[norm_key(c["kind"], c["value"])] = c["count"]
    return out


def total_of(lock_report, kinds):
    return sum(c["count"] for c in lock_report["counts"] if c["kind"] in kinds)


def split_sentences(text):
    """按句子切分。中文标点后直接切（中文无空格），英文标点后要求跟空白，避免 e.g. 误切。"""
    parts = re.split(r"(?<=[。！？；])|(?<=[.!?;])\s+|\n+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def collect_paragraphs(result):
    """从 result 里取段落对，按 pid 排序。"""
    body = result.get("result") if isinstance(result.get("result"), dict) else result
    paras = body.get("paragraphs") or []
    rows = []
    for p in paras:
        if not isinstance(p, dict):
            continue
        rows.append({
            "pid": p.get("pid") or p.get("id") or f"P{len(rows) + 1:02d}",
            "original": p.get("original") or "",
            "polished": p.get("polished") or p.get("revised") or "",
        })
    return rows


def collect_source_paragraphs(case):
    text = ""
    if isinstance(case, dict):
        for k in ("text", "source", "content", "original"):
            if isinstance(case.get(k), str) and case[k].strip():
                text = case[k]
                break
        if not text and isinstance(case.get("input"), dict):
            for k in ("text", "source", "content"):
                if isinstance(case["input"].get(k), str):
                    text = case["input"][k]
                    break
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def compute(result, case, thresholds):
    lock = load_module("scripts/lock_invariants.py")
    if lock is None:
        return {"status": "failed", "errors": ["找不到 scripts/lock_invariants.py，无法计算守恒指标"]}

    rows = collect_paragraphs(result)
    src_paras = collect_source_paragraphs(case or {})
    errors, warnings = [], []

    if not rows:
        return {"status": "failed",
                "errors": ["result.paragraphs 为空：没有逐段润色结果，无法计算任何指标"]}

    # 1) 段落覆盖
    expected = max(len(src_paras), len(rows))
    segment_coverage = round(len(rows) / expected, 4) if expected else 0.0
    if src_paras and len(rows) < len(src_paras):
        errors.append(f"漏段：原文 {len(src_paras)} 段，只交了 {len(rows)} 段")

    hard_total = hard_ok = 0
    hedge_pairs = 0
    hedge_ok = 0
    neg_ok = 0
    changed_sentences = total_sentences = 0
    term_hits = {}

    for r in rows:
        lo = lock.lock_text(r["original"])
        lp = lock.lock_text(r["polished"])

        # 2) 硬守恒：数字/单位/引用/图表指向
        co, cp = kind_counts(lo, HARD_KINDS), kind_counts(lp, HARD_KINDS)
        for k, n in co.items():
            hard_total += n
            hard_ok += min(n, cp.get(k, 0))
        for k, n in cp.items():
            hard_total += n  # 新增的硬事实也算进分母：凭空加数据要扣
            hard_ok += min(n, co.get(k, 0))
        if hard_total:
            pass

        # 3) 限定词与否定：按段守恒（允许 ±1 的自然语序调整）
        ho, hp = total_of(lo, HEDGE_KINDS), total_of(lp, HEDGE_KINDS)
        hedge_pairs += 1
        if abs(ho - hp) <= 1:
            hedge_ok += 1
        no_, np_ = total_of(lo, NEG_KINDS), total_of(lp, NEG_KINDS)
        if abs(no_ - np_) <= 1:
            neg_ok += 1

        # 4) 逐句改动率
        so, sp = split_sentences(r["original"]), split_sentences(r["polished"])
        total_sentences += len(so)
        changed_sentences += sum(1 for i, s in enumerate(so)
                                 if i >= len(sp) or re.sub(r"\s+", "", s) != re.sub(r"\s+", "", sp[i]))

    invariant_conservation = round(hard_ok / hard_total, 4) if hard_total else 1.0
    if invariant_conservation < 1.0:
        errors.append(f"硬事实未守恒：{hard_total - hard_ok}/{hard_total} 项数字/单位/引用/图表指向在改文中对不上")
    hedge_conservation = round(hedge_ok / hedge_pairs, 4) if hedge_pairs else 1.0
    if hedge_conservation < thresholds["hedge_conservation"]:
        warnings.append(f"限定强度有 {hedge_pairs - hedge_ok} 段变化超过 ±1 个限定词")
    negation_conservation = round(neg_ok / hedge_pairs, 4) if hedge_pairs else 1.0
    sentence_change_rate = round(changed_sentences / total_sentences, 4) if total_sentences else 0.0
    if sentence_change_rate > thresholds["max_sentence_change_rate"]:
        warnings.append(f"改动率 {sentence_change_rate:.0%} 超过阈值，接近整段重写而非最小编辑")

    # 5) 术语唯一性
    body = result.get("result") if isinstance(result.get("result"), dict) else result
    decisions = body.get("term_decisions") or []
    text_all = "\n".join(r["polished"] for r in rows)
    term_total = term_ok = 0
    for d in decisions:
        if not isinstance(d, dict):
            continue
        term = str(d.get("term") or "").strip()
        target = str(d.get("target") or "").strip()
        if not term:
            continue
        term_total += 1
        term_hits[term] = term_hits.get(term, 0) + 1
        if target and target in text_all:
            term_ok += 1
        else:
            warnings.append(f"术语「{term}」的统一译法「{target}」未在改文中出现")
    term_uniqueness = round(term_ok / term_total, 4) if term_total else 0.0
    if not term_total:
        errors.append("没有术语决策记录（result.term_decisions 为空）：术语一致性无法核验")

    # 6) 修改说明覆盖率
    log = body.get("change_log") or []
    with_reason = [c for c in log if isinstance(c, dict)
                   and (c.get("reason") or c.get("why"))
                   and (c.get("original") is not None)
                   and (c.get("revised") is not None)]
    edit_note_coverage = round(min(1.0, len(with_reason) / changed_sentences), 4) if changed_sentences else 1.0
    if changed_sentences and edit_note_coverage < thresholds["edit_note_coverage"]:
        errors.append(f"逐句修改说明不全：{changed_sentences} 句有改动，只有 {len(with_reason)} 条带原文/改文/理由的记录")

    # 7) 人工确认项
    manual = (result.get("uncertainty") or []) + (body.get("questions_for_author") or [])

    metrics = {
        "segment_coverage": segment_coverage,
        "invariant_conservation": invariant_conservation,
        "hedge_conservation": hedge_conservation,
        "negation_conservation": negation_conservation,
        "term_uniqueness": term_uniqueness,
        "edit_note_coverage": edit_note_coverage,
        "sentence_change_rate": sentence_change_rate,
        "manual_review_items": len(manual),
        "paragraphs": len(rows),
        "changed_sentences": changed_sentences,
    }

    # 判据：只卡硬门槛，软指标进 warnings
    if metrics["segment_coverage"] < thresholds["segment_coverage"]:
        errors.append(f"段落覆盖不足：{metrics['segment_coverage']:.0%}")
    if metrics["term_uniqueness"] < thresholds["term_uniqueness"]:
        errors.append(f"术语一致性不足：{metrics['term_uniqueness']:.0%}")

    return {
        "status": "passed" if not errors else "failed",
        "case_id": (case or {}).get("case_id") or result.get("case_id"),
        "metrics": metrics,
        "thresholds": thresholds,
        "errors": errors,
        "warnings": warnings,
        "computed_by": "eval/score_output.py v1.0",
        "computed_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "note": "全部指标由原文与改文实际比对得出，可用同一份输入复现；不含自评输入。",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result")
    ap.add_argument("--case")
    ap.add_argument("--out")
    ap.add_argument("--rubric", default=os.path.join(HERE, "rubric.json"))
    ap.add_argument("--show-rubric", action="store_true")
    args = ap.parse_args()

    thresholds = dict(DEFAULT_THRESHOLDS)
    if os.path.isfile(args.rubric):
        try:
            rubric = json.load(open(args.rubric, encoding="utf-8"))
            thresholds.update(rubric.get("thresholds") or {})
        except Exception as e:
            print(json.dumps({"status": "failed", "errors": [f"rubric 读取失败: {e}"]},
                             ensure_ascii=False), file=sys.stderr)

    if args.show_rubric:
        print(json.dumps({"thresholds": thresholds}, ensure_ascii=False, indent=1))
        return 0

    if not args.result:
        ap.error("需要 --result")

    result = json.load(open(args.result, encoding="utf-8"))
    case = json.load(open(args.case, encoding="utf-8")) if args.case else {}
    rep = compute(result, case, thresholds)

    text = json.dumps(rep, ensure_ascii=False, indent=1)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(text + "\n")
        print(json.dumps({"status": rep["status"], "out": args.out,
                          "metrics": rep.get("metrics"),
                          "errors": rep.get("errors", [])}, ensure_ascii=False))
    else:
        print(text)
    return 0 if rep["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
