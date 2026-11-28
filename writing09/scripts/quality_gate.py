#!/usr/bin/env python3
"""方法与实验章节的结构度量：把题面「写得全/写得准/做得着/说得住」变成可计算的量。

度量口径：
- 六要素覆盖（步骤/设置/参数/数据/对照/复现与限制）——按小节标题判定，各节还要求最小篇幅；
- 参数表可核性——表格行数、带来源列的行占比、表中取值在正文出现的比例（正文与表不能两张皮）；
- 对照可比性——基线对象/版本/同预算/指标/统计方式/重复次数 六项命中数；
- 复现清单——代码版本/环境/种子/命令/数据获取/划分 六项命中数；
- 限制是否落到具体失效场景（出现"当…时"或阈值不等式，而不是"存在一定局限性"）；
- 缺口是否登记（uncertainty / questions_for_author 条数）。

只度量文本结构，不判断数值对错——数值对错必须对着配置文件逐条核。
被 validate_result.py 与 eval/score_output.py 共用。
"""
import re

CJK = re.compile(r'[\u4e00-\u9fff]')
PLACEHOLDER = re.compile(r'【[^】]*】|\[待填\]|\bTODO\b|\bTBD\b|\bXXX\b')

ELEMENTS = {
    'steps': (r'方法步骤|方法|流程|步骤|method|procedure|pipeline', r'步骤|流程|method'),
    'setup': (r'实验设置|训练设置|运行环境|实验环境|setup|experimental setup|environment', r'设置|环境|setup'),
    'parameters': (r'参数|超参|hyperparam|parameters?', r'参数|parameter'),
    'dataset': (r'数据集|数据与划分|数据|data(set)?|corpus', r'数据集|数据|dataset|data'),
    'baselines': (r'对照|基线|baseline|comparison', r'对照|基线|baseline'),
    'reproducibility': (r'可复现|复现|限制条件|局限|reproduc|limitation', r'复现|限制|reproduc|limitation'),
}
NUM = re.compile(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?\s*(?:%|W|mm/s|μm|um|nm|ms|s|GB|MB|K|°C|eV|MPa|Hz|epochs?|steps?)?')


def _counts(text):
    if not text:
        return 0, 0
    return len(CJK.findall(text)), len(re.findall(r'[A-Za-z][A-Za-z\-]+', text))


def _nchars(text):
    cjk, latin = _counts(text)
    return int(cjk + latin * 0.6)


# 篇幅门槛分语言两套。原实现只有中文口径一套数字，
# 英文按「词×0.6」折算后同一门槛等于要求 2.6 倍词数，英文案例会被误判为不达标。
GATE_ZH = {'total': 1800, 'steps': 450, 'setup': 250, 'parameters': 300,
           'dataset': 250, 'baselines': 250, 'reproducibility': 250}
GATE_EN = {'total': 1100, 'steps': 290, 'setup': 160, 'parameters': 190,
           'dataset': 160, 'baselines': 160, 'reproducibility': 160}


def _lang_of(text):
    cjk, latin = _counts(text)
    return 'en' if latin > cjk * 2 and latin >= 60 else 'zh'


HEADING = re.compile(r'^\s{0,3}(#{1,6})\s*(.+?)\s*$', re.M)
NUM_PREFIX = re.compile(r'^\s*(?:第?[0-9一二三四五六七八九十]+[\.、\)）]?|[（(][0-9]+[)）])\s*')


def split_sections(text):
    """按 Markdown 标题切段；body 延伸到下一个同级或更高级标题。"""
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


def find_elements(text):
    """六要素 → (title, body)。标题开头命中优先；只在总标题里出现的不算。"""
    sections = split_sections(text)
    found = {}
    for key, (pat, _) in ELEMENTS.items():
        best = None
        for lvl, title, body in sections:
            clean = NUM_PREFIX.sub('', title).strip()
            if re.match(pat, clean, re.I):
                score = 2
            elif re.search(pat, clean, re.I):
                score = 1
            else:
                continue
            cand = (score, -lvl, -len(body))
            if best is None or cand > best[0]:
                best = (cand, title, body)
        if best:
            found[key] = (best[1], best[2])
    if len(found) < 6:
        blocks = [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]
        for key, (pat, body_pat) in ELEMENTS.items():
            if key in found:
                continue
            for b in blocks:
                if re.search(body_pat, b[:120], re.I):
                    found[key] = ('', b)
                    break
    return found


def parse_param_table(body):
    """解析 Markdown 表格：返回 [(row_cells)], 以及是否有「来源」列及其列序。"""
    if not body:
        return [], None
    lines = [l.strip() for l in body.splitlines() if l.strip().startswith('|')]
    if len(lines) < 2:
        return [], None
    rows = []
    header = None
    for l in lines:
        cells = [c.strip() for c in l.strip('|').split('|')]
        if set(''.join(cells)) <= set('-: '):
            continue
        if header is None:
            header = cells
            continue
        rows.append(cells)
    src_idx = None
    if header:
        for i, c in enumerate(header):
            if re.search(r'来源|依据|出处|source|origin', c, re.I):
                src_idx = i
                break
    return rows, src_idx


def param_metrics(elem_body):
    rows, src_idx = parse_param_table(elem_body)
    n = len(rows)
    labeled = 0
    values = []
    for r in rows:
        if src_idx is not None and src_idx < len(r) and r[src_idx].strip() not in ('', '-', '—', '?'):
            labeled += 1
        # 取值通常在第 2 列
        if len(r) > 1:
            values.append(r[1])
    return {
        'param_rows': n,
        'param_source_rate': round(labeled / n, 3) if n else 0.0,
        'param_values': values,
    }


def align_rate(body_text, values):
    """正文与参数表对齐率：表中取值在正文出现的比例。"""
    if not values:
        return 0.0
    flat = re.sub(r'\s+', '', body_text)
    hit = 0
    for v in values:
        vv = re.sub(r'\s+', '', v)
        if vv and vv in flat:
            hit += 1
    return round(hit / len(values), 3)


BASELINE_MARKS = {
    'baseline_identity': r'基线|对照|baseline|相比|对比对象',
    'baseline_version': r'版本|version|checkpoint|权重|commit',
    'same_budget': r'同预算|同等预算|相同预算|同等条件|相同设置|same budget|equal budget',
    'metric': r'指标|评价标准|metric|准确率|F1|IoU|PSNR|BLEU|RMSE|MAE',
    'statistics': r'统计|均值|标准差|置信区间|显著性|std|mean|p\s*[<=]',
    'repeats': r'重复|次数|种子|trials?|runs?\s*[×x]|次独立',
}

REPRO_MARKS = {
    'code_version': r'代码版本|commit|git|仓库|release|版本号',
    'env': r'环境|依赖|requirements|镜像|CUDA|驱动|Python\s*3|版本',
    'seed': r'随机种子|seed',
    'command': r'命令|运行|python\s|bash|脚本入口|\.sh',
    'data_source': r'数据获取|下载|数据集地址|申请|公开数据|URL|DOI',
    'split': r'划分|split|训练/验证/测试|比例|交叉验证',
}

LIMIT_SPECIFIC = r'(?:当|若|在)[^。；\n]{0,40}(?:时|情况下|小于|大于|<|>|≤|≥)|(?:小于|大于|<|>|≤|≥)\s*\d'


def measure(elem_text, body_text=None, uncertainty=None, questions=None, min_chars=None):
    """elem_text: 成稿正文；body_text: 同一份（可为 None）。返回指标字典。"""
    text = elem_text or ''
    uncertainty = uncertainty or []
    questions = questions or []
    parts = find_elements(text)
    lens = {k: _nchars(v[1]) for k, v in parts.items()}
    pm = param_metrics(parts.get('parameters', ('', ''))[1])
    setup_body = "\n".join(parts.get(k, ('', ''))[1] for k in ('setup', 'baselines', 'reproducibility'))
    baseline_hits = [k for k, pat in BASELINE_MARKS.items() if re.search(pat, setup_body, re.I)]
    repro_hits = [k for k, pat in REPRO_MARKS.items() if re.search(pat, text, re.I)]
    limit_body = parts.get('reproducibility', ('', ''))[1]
    lang = _lang_of(text)
    gate = GATE_EN if lang == 'en' else GATE_ZH
    if min_chars:
        gate = dict(gate); gate['total'] = min_chars
    cjk_total, word_total = _counts(text)
    word_of = lambda k: len(re.findall(r'[A-Za-z][A-Za-z\-]+', parts.get(k, ('', ''))[1]))
    return {
        'lang': lang,
        'cjk_chars': cjk_total,
        'en_words': word_total,
        'total_chars': _nchars(text),
        'min_chars_ok': (word_total >= gate['total']) if lang == 'en' else (cjk_total >= gate['total']),
        'element_coverage': round(len(parts) / len(ELEMENTS), 3),
        'missing_elements': [k for k in ELEMENTS if k not in parts],
        'section_chars': lens,
        # 章节厚度只作为提示，不作为硬门槛：方法与实验章节的详略随领域差别很大，
        # 真正卡住"写没写全"的是六要素覆盖与参数表/对照/复现三项的结构完整性。
        'section_min_ok': {
            k: (word_of(k) >= gate[k] if lang == 'en' else lens.get(k, 0) >= gate[k])
            for k in ('steps', 'setup', 'parameters', 'dataset', 'baselines', 'reproducibility')
        },
        'param_rows': pm['param_rows'],
        'param_source_rate': pm['param_source_rate'],
        'param_body_alignment': align_rate(text, pm['param_values']),
        'baseline_checks': baseline_hits,
        'baseline_coverage': round(len(baseline_hits) / len(BASELINE_MARKS), 3),
        'repro_checks': repro_hits,
        'repro_coverage': round(len(repro_hits) / len(REPRO_MARKS), 3),
        'limitation_specific': bool(re.search(LIMIT_SPECIFIC, limit_body, re.I)),
        'placeholder_count': len(PLACEHOLDER.findall(text)),
        'open_gaps': len(uncertainty) + len(questions),
    }
