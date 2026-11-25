#!/usr/bin/env python3
"""学术翻译与双语写作的四把尺：术语稳 / 数字实 / 对得齐 / 边界清。

只度量不判分。口径写在下面，validate_result.py、build_outputs.py、eval/ 共用同一套：

- pair_coverage      源段 [Pxx] 有对应译段的比例。缺段就是漏译，不做"意译合并"的辩解。
- order_preserved    译段编号序列与源段同序的比例（合并/调序会被抓到）。
- marker_keep        公式 `$…$`、引用 `[12]`/`(Smith, 2020)`、图表 `Fig. 2a`/`Table 1`、
                     脚注 `^1` 四类标记在译段中保留的比例（按标记本体比对，不看位置）。
- term_coverage      术语表里的 en 在某段原文出现时，该段译文含锁定译法的比例。
- term_variant_leak  锁定译法之外、与锁定译法共享 ≥60% 字形的短语出现次数（术语漂移）。
- number_transfer_rate  原文数值在译文中以同值落地的比例。万/亿 ↔ thousand/million/billion
                     按真实量级换算；四舍五入、丢小数按未落地计。
- magnitude_errors   量级错配条数（3.5 million 落成 3.5 万、0.037 落成 3.7% 之类）。
- sigfig_loss        原文有效数字位数被削掉的条数（0.037 → 0.04）。
- boundary_violation 语义边界被改动的条数：否定范围、情态强度（may/suggest → 一定/导致）、
                     限定条件（in vitro → 未保留"体外"）。
- hedge_alignment    带模糊限制语（may/could/suggest/associated with/approximately）的源句，
                     译文保留等强度限制语的比例。
"""
import re

CJK = re.compile(r'[\u4e00-\u9fff]')

# ---------- 双语块解析 ----------

SEG_HEAD = re.compile(r'^\s{0,3}#{2,4}\s*\[?(P\d{1,3})\]?', re.M)
EN_LINE = re.compile(r'^\s*(?:EN|原文|Source)\s*[:：]\s*(.+)$', re.M)
ZH_LINE = re.compile(r'^\s*(?:ZH|译文|Target)\s*[:：]\s*(.+)$', re.M)


def parse_pairs(text):
    """把 `## P01 / EN: … / ZH: …` 形式的双语稿切成 {pid: (en, zh)}。

    也接受一行一段的 `[P01] EN: …` 写法。缺 EN 或缺 ZH 的段照收，值为空串，
    这样 pair_coverage 才能如实反映漏译，而不是把漏译段直接丢掉。
    """
    text = text or ''
    heads = list(SEG_HEAD.finditer(text))
    pairs = {}
    for i, m in enumerate(heads):
        pid = m.group(1)
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end]
        en = EN_LINE.search(body)
        zh = ZH_LINE.search(body)
        pairs[pid] = (en.group(1).strip() if en else '',
                      zh.group(1).strip() if zh else '')
    return pairs


# ---------- 术语 ----------

def _norm_term(s):
    return re.sub(r'[^\w\u4e00-\u9fff]+', ' ', (s or '').lower()).strip()


def term_check(pairs, terms):
    """terms: [{'en':…, 'zh':…, 'variants':[…], 'sections':[…]}]（variants 可省）。

    返回 (coverage, leak_hits, conflict_terms)：
    - coverage     有 en 出现的段里，译文含 zh 的比例
    - leak_hits    [(pid, term_en, found_variant)] 疑似漂移，供人工确认
    - conflict_terms  术语表内部自相矛盾（同一 en 对应多个 zh）的 en 列表
    """
    seen = {}
    conflict = set()
    for t in terms or []:
        en = _norm_term(t.get('en'))
        zh = (t.get('zh') or '').strip()
        if not en or not zh:
            continue
        if en in seen and seen[en] != zh:
            conflict.add(t.get('en'))
        seen[en] = zh

    hit = miss = 0
    leak = []
    for pid, (en, zh) in pairs.items():
        if not en:
            continue
        low = ' ' + _norm_term(en) + ' '
        for t in terms or []:
            key = _norm_term(t.get('en'))
            lock = (t.get('zh') or '').strip()
            if not key or not lock or key not in low:
                continue
            if not zh:
                miss += 1
                continue
            if lock in zh:
                hit += 1
            else:
                miss += 1
                leak.append((pid, t.get('en'), lock + '→缺失'))
            for v in t.get('variants') or []:
                v = (v or '').strip()
                # 变体是锁定译法的子串（鼠成骨细胞 ⊂ 小鼠成骨细胞）不算漂移，
                # 否则模板化的正确用法会被判错，术语检查就失去意义。
                if v and v != lock and v not in lock and lock not in v and v in zh:
                    leak.append((pid, t.get('en'), v))
    cov = round(hit / (hit + miss), 3) if (hit + miss) else 1.0
    return cov, leak, sorted(conflict)


def variant_scan(text, lock_zh, min_len=2):
    """找与锁定译法共享 ≥60% 字形、但不等于它的中文片段（术语漂移的味道）。

    只用于提示人工复核：同义改写不一定错，但同一篇里换三种说法一定是漂移。
    """
    if not lock_zh or len(lock_zh) < min_len:
        return []
    chars = set(lock_zh)
    out = []
    for m in re.finditer(r'[\u4e00-\u9fff]{%d,8}' % min_len, text or ''):
        w = m.group(0)
        if w == lock_zh or lock_zh in w:
            continue
        for i in range(max(0, len(w) - len(lock_zh)) + 1):
            seg = w[i:i + len(lock_zh)]
            if len(seg) < len(lock_zh):
                continue
            if seg == lock_zh:
                continue
            share = len(set(seg) & chars) / float(len(chars))
            if share >= 0.6:
                out.append(seg)
                break
    return sorted(set(out))


# ---------- 数字 ----------

NUM = re.compile(r'(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(\s*(?:%|wt%|vol%|°C|℃|K|mm|cm|m|μm|nm|'
                 r'kPa|MPa|GPa|Pa|Hz|kHz|MHz|h|min|s|mg|g|kg|mL|L|μL|nmol|mmol|mol|fold|倍|'
                 r'thousand|million|billion|万|亿))?')
CN_MAG = {'万': 1e4, '亿': 1e8, 'thousand': 1e3, 'million': 1e6, 'billion': 1e9}


def numbers(text):
    """抓数值 + 量级词，返回 [(raw, value, unit_or_mag, sigfig)]。"""
    out = []
    for m in NUM.finditer(text or ''):
        raw = m.group(1).replace(',', '')
        unit = (m.group(2) or '').strip()
        try:
            v = float(raw)
        except ValueError:
            continue
        if unit in CN_MAG:
            out.append((m.group(0).strip(), v * CN_MAG[unit], unit, _sigfig(raw)))
        else:
            out.append((m.group(0).strip(), v, unit, _sigfig(raw)))
    return out


def _sigfig(raw):
    s = raw.lstrip('0').replace('.', '')
    s = s.lstrip('0')
    return len(s) if s else 1


def number_check(src, tgt):
    """数值落地检查。返回 (transfer_rate, magnitude_errors, sigfig_loss, rows)。

    命中规则：值相等（容差 0.5%），或量级换算后相等（3.5 million ↔ 350 万）。
    只看值，不看单位写法：单位错配由 magnitude_errors 抓（3.5 million → 3.5 万）。
    """
    sns = numbers(src)
    tns = numbers(tgt)
    if not sns:
        return 1.0, [], 0, []
    tvals = [(v, sf) for _r, v, _u, sf in tns]
    hit = 0
    mag_err, sig_loss, rows = [], 0, []
    for raw, v, unit, sf in sns:
        cand = [tv for tv, _ in tvals]
        same = [x for x in cand if v and abs(x - v) / abs(v) <= 0.005]
        rows.append((raw, v, unit, bool(same)))
        if same:
            hit += 1
            if min((t2 for t2, s2 in tvals if abs(t2 - v) / max(abs(v), 1e-9) <= 0.005),
                   default=None) is not None:
                near = [s2 for t2, s2 in tvals if abs(t2 - v) / abs(v) <= 0.005]
                if near and min(near) < sf:
                    sig_loss += 1
        else:
            # 量级错配：出现了同数字不同量级（3.5 million 落成 3.5 万 → 出现 3.5）
            base = v / CN_MAG.get(unit, 1) if unit in CN_MAG else v
            if any(abs(x - base) / max(abs(base), 1e-9) <= 0.005 for x in cand):
                mag_err.append((raw, base))
    rate = round(hit / float(len(sns)), 3)
    return rate, mag_err, sig_loss, rows


# ---------- 标记 ----------

MARKERS = [
    ('cite_bracket', re.compile(r'\[[\d,\s\-–]{1,20}\]')),
    ('cite_author', re.compile(r'[\(（][A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?[,，]\s*\d{4}[a-z]?[\)）]')),
    ('fig', re.compile(r'(?:Fig(?:ure)?\.?|图)\s*(\d+)\s*([a-zA-Z])?')),
    ('table', re.compile(r'(?:Table|表)\s*(\d+)')),
    ('formula', re.compile(r'\$[^$]{1,80}\$')),
    ('footnote', re.compile(r'\^(\d+)')),
]


def _marker_keys(name, m):
    """把标记归一成跨语言可比的键：`Fig. 2a` 与「图 2a」都得 fig:2a。

    为什么必须归一：中英对照里图表编号本来就换了"外壳"（Fig.→图），
    直接比字面会把正确保留的图表引用全判成丢失。
    """
    if name == 'cite_bracket':
        nums = []
        for part in re.split(r',', m.group(0).strip('[]')):
            part = part.strip()
            rng = re.match(r'(\d+)\s*[-–]\s*(\d+)', part)
            if rng:
                a, b = int(rng.group(1)), int(rng.group(2))
                nums += list(range(a, b + 1))
            elif part.isdigit():
                nums.append(int(part))
        return ['cite:%d' % n for n in sorted(set(nums))]
    if name == 'cite_author':
        raw = m.group(0).strip('()（）').lower().replace(' ', '').replace('，', ',')
        return ['auth:' + raw]
    if name == 'fig':
        return ['fig:%s%s' % (m.group(1), (m.group(2) or '').lower())]
    if name == 'table':
        return ['tbl:' + m.group(1)]
    if name == 'formula':
        return ['fx:' + re.sub(r'\s+', '', m.group(0))]
    if name == 'footnote':
        return ['fn:' + m.group(1)]
    return []


def marker_check(pairs):
    """标记保留率：源段里出现过的标记键，译段里还在不在（按类统计再取总均值）。"""
    per = {}
    for pid, (en, zh) in pairs.items():
        zh_keys = set()
        for name, rx in MARKERS:
            for m in rx.finditer(zh or ''):
                zh_keys |= set(_marker_keys(name, m))
        for name, rx in MARKERS:
            for m in rx.finditer(en or ''):
                for key in _marker_keys(name, m):
                    per.setdefault(name, [0, 0])
                    per[name][1] += 1
                    if key in zh_keys:
                        per[name][0] += 1
    rows = {k: (round(v[0] / float(v[1]), 3), v[0], v[1]) for k, v in per.items()}
    total_hit = sum(v[0] for v in per.values())
    total_all = sum(v[1] for v in per.values())
    overall = round(total_hit / float(total_all), 3) if total_all else 1.0
    return overall, rows


# ---------- 对齐 ----------

def align_check(pairs, expect_ids=None):
    ids = list(pairs.keys())
    if expect_ids:
        miss = [p for p in expect_ids if p not in pairs or not pairs[p][1]]
        cov = round((len(expect_ids) - len(miss)) / float(len(expect_ids)), 3)
    else:
        miss = [p for p, (e, z) in pairs.items() if e and not z]
        with_en = [p for p, (e, _z) in pairs.items() if e] or ids
        cov = round((len(with_en) - len(miss)) / float(len(with_en)), 3) if with_en else 1.0
    order = [int(p[1:]) for p in ids if re.fullmatch(r'P\d+', p)]
    ordered = order == sorted(order)
    return cov, ordered, miss


# ---------- 语义边界 ----------

NEG_EN = re.compile(r'\b(?:not|no|none|neither|nor|never|cannot|can not|did not|was not|were not|'
                    r'without|fail(?:ed)? to)\b', re.I)
NEG_ZH = ['未', '不', '无', '没有', '并非', '不能', '未能', '未见', '缺乏', '排除']
HEDGE_EN = re.compile(r'\b(?:may|might|could|suggest(?:s|ed|ing)?|appear(?:s|ed)?|seem(?:s|ed)?|'
                      r'likely|possibly|probably|approximately|about|around|tend(?:s|ed)? to|'
                      r'associated with|correlat(?:e|ed|es) with|we cannot exclude|'
                      r'it is unclear)\b', re.I)
HEDGE_ZH = ['可能', '或许', '也许', '提示', '似乎', '看来', '大约', '左右', '倾向于',
            '相关', '伴随', '尚不清楚', '无法排除', '有待']
STRENGTH_UP = [('associated with', '导致'), ('correlated with', '引起'), ('may', '一定'),
               ('suggest', '证明'), ('could', '必然'), ('possibly', '确定')]
SCOPE_EN = re.compile(r'\b(in vitro|in vivo|ex vivo|animal model|murine|rat|mouse|pilot|'
                      r'preliminary|single[- ]cent(?:er|re))\b', re.I)
SCOPE_ZH = {'in vitro': ['体外'], 'in vivo': ['体内'], 'ex vivo': ['离体', '体外'],
            'animal model': ['动物模型'], 'murine': ['小鼠'], 'rat': ['大鼠'],
            'mouse': ['小鼠'], 'pilot': ['预实验', '初步'], 'preliminary': ['初步'],
            'single-center': ['单中心'], 'single centre': ['单中心']}


def boundary_check(pairs):
    """否定范围、情态强度、限定条件三类改动的条数。"""
    viol = []
    hedge_hit = hedge_all = 0
    for pid, (en, zh) in pairs.items():
        if not en or not zh:
            continue
        # 1) 否定翻转：原文有否定，译文一个否定词都没有
        if NEG_EN.search(en) and not any(w in zh for w in NEG_ZH):
            viol.append((pid, 'negation_dropped', NEG_EN.search(en).group(0)))
        # 2) 情态强度升级：原文 may/suggest/associated with 被译成断言
        for src_w, tgt_w in STRENGTH_UP:
            if re.search(r'\b%s\b' % re.escape(src_w), en, re.I) and tgt_w in zh:
                viol.append((pid, 'strength_up', f'{src_w}→{tgt_w}'))
        # 3) 情态保留
        if HEDGE_EN.search(en):
            hedge_all += 1
            if any(w in zh for w in HEDGE_ZH):
                hedge_hit += 1
        # 4) 限定条件丢失
        for m in SCOPE_EN.finditer(en):
            key = m.group(0).lower()
            words = SCOPE_ZH.get(key, [])
            if words and not any(w in zh for w in words):
                viol.append((pid, 'scope_dropped', key))
    hedge = round(hedge_hit / float(hedge_all), 3) if hedge_all else 1.0
    return viol, hedge


# ---------- 篇幅 ----------

PLACEHOLDER_PATTERNS = [r'【[^】\n]{0,60}】', r'\{\{[^{}\n]{0,40}\}\}',
                        r'\[待译[^\]]*\]', r'\bTODO\b', r'\bTBD\b', r'待译', r'待补']


def placeholders_of(text):
    hits = []
    for pat in PLACEHOLDER_PATTERNS:
        hits += re.findall(pat, text or '')
    return hits


def _nchars(text):
    """中文按字、西文按词 ×0.6、数字按个 ×0.6（译文字数天然少于英文原文）。"""
    if not text:
        return 0
    cjk = len(CJK.findall(text))
    latin = len(re.findall(r'[A-Za-z][A-Za-z\-]+', text))
    nums = len(re.findall(r'\d+(?:\.\d+)?', text))
    return int(cjk + (latin + nums) * 0.6)
