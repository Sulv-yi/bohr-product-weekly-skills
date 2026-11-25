#!/usr/bin/env python3
"""开题方案的四把尺：立得住 / 对得上 / 排得开 / 说得清。

只度量不判分。口径写在下面，validate_result.py、build_outputs.py、eval/ 共用同一套：

- elements_coverage  七要素（背景/问题/目标/技术路线/阶段计划/风险/预期成果）各自有实质内容的比例，
                     每节还有最低字数，几句话糊过去不算。
- gap_specific       背景段是否写出「已知→未知→待验证」的缺口，而不只是综述。
                     缺口句要带线索词（尚未/未见/缺乏/不清楚/gap），且与问题段共享主题词。
- falsifiable        研究问题是否可证伪：含指标 + 阈值（数字/比较符）+ 对照或时间点。
                     「探究 X 的影响」不可证伪；「孔隙率 ≥70% 且与对照差 ≥5 个百分点」可证伪。
- alignment_rate     目标、路线、指标、成果的一一对应率：每个目标都要挂到一条路线步骤、
                     一个可考核指标、一项预期成果，缺一环不算对齐。
- schedule_coverage  里程碑是否覆盖 1..T 全周期（有空月就是排不开）。
- schedule_overlap   里程碑月份区间重叠数（重叠意味着任务量被重复计入）。
- effort_ratio       里程碑工作量合计 / 可用人力（人月）。>1 就是排不下。
- risk_complete      每条风险是否写全「触发信号 + 影响 + 备选方案 + 决策时点」的比例。
- risk_types         覆盖的风险类型数（数据/方法/进度/伦理合规 四类）。
- binding_rate       论断句挂引用编号的比例。
"""
import re

HEADING = re.compile(r'^\s{0,3}(#{1,6})\s*(.+?)\s*$', re.M)
CJK = re.compile(r'[\u4e00-\u9fff]')
NUM = re.compile(r'\d+(?:\.\d+)?')
PLACEHOLDER_PATTERNS = [r'【[^】\n]{0,60}】', r'\{\{[^{}\n]{0,40}\}\}',
                        r'\[待补[^\]]*\]', r'\bTODO\b', r'\bTBD\b', r'待补', r'待填']

# 七要素：识别正则 + 最低字数（按 _nchars 折算）
ELEMENTS = [
    ('background', r'研究背景|背景|background|立项依据', 350),
    ('question', r'研究问题|问题定义|科学问题|question|aim(?:s)?\b', 150),
    ('objectives', r'研究目标|目标|objectives?\b', 150),
    ('approach', r'技术路线|研究方案|方法|approach|methodology|work ?package', 300),
    ('schedule', r'阶段计划|进度|时间安排|里程碑|schedule|timeline|milestones?', 150),
    ('risks', r'风险|risk', 150),
    ('outcomes', r'预期成果|预期结果|考核|outcomes?|deliverables?', 120),
]

GAP_CUES = ['尚未', '未见', '缺乏', '不清楚', '尚无', '仍不', '空白', 'gap', 'unknown',
            'has not been', 'remains unclear', '未解决', '少有研究', '缺少']
FALSIFY_METRIC = ['%', '％', 'MPa', 'μm', 'nm', 'mg', 'mL', 'h', 'min', 'd', '倍', '例', '个',
                  'p<', 'p <', 'AUC', 'RMSE', '准确率', '灵敏度', '特异度', '回收率', '浓度']
FALSIFY_CMP = ['≥', '≤', '>', '<', '不低', '不高于', '至少', '至多', '以内', '之间', '达到',
               '高于', '低于', '提升', '下降', '差异']
FALSIFY_CTRL = ['对照', 'control', '基线', 'baseline', '随机', '盲法', '重复', 'n =', 'n=']
RISK_TYPES = {'数据获取': ['数据', '样本', '获取', '入组', 'data'],
              '方法可行性': ['方法', '技术', '工艺', '合成', '成型', '可行性', 'method'],
              '进度': ['进度', '延期', '周期', '时间', 'schedule'],
              '伦理合规': ['伦理', '合规', '审批', '知情', 'IRB', '动物伦理', 'ethic']}


def split_sections(text):
    """按 Markdown 标题切段，body 延伸到下一个同级或更高级标题。"""
    text = text or ''
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


def _nchars(text):
    if not text:
        return 0
    cjk = len(CJK.findall(text))
    latin = len(re.findall(r'[A-Za-z][A-Za-z\-]+', text))
    nums = len(NUM.findall(text))
    return int(cjk + (latin + nums) * 0.6)


def placeholders(text):
    hits = []
    for pat in PLACEHOLDER_PATTERNS:
        hits += re.findall(pat, text or '')
    return hits


def element_map(text):
    """七要素 → (是否有实质内容, 字数)。同名多节取字数最多的那节。"""
    secs = split_sections(text)
    got = {}
    for key, pat, need in ELEMENTS:
        best = ''
        for _lvl, title, body in secs:
            if re.search(pat, title or '', re.I):
                if _nchars(body) > _nchars(best):
                    best = body
        got[key] = (_nchars(best) >= need, _nchars(best), need)
    return got


def _bigrams(text):
    """中文 2-gram 集合：定长切片会把同一概念切成不同块，导致重叠被低估。"""
    out = set()
    for run in re.findall(r'[\u4e00-\u9fff]{2,}', text or ''):
        for i in range(len(run) - 1):
            out.add(run[i:i + 2])
    return out


def gap_specific(text, question_text):
    """缺口是否具体：背景里有缺口句，且缺口句与问题段共享主题词。"""
    bg = ''
    for _lvl, title, body in split_sections(text):
        if re.search(ELEMENTS[0][1], title or '', re.I) and _nchars(body) > _nchars(bg):
            bg = body
    hits = [c for c in GAP_CUES if c.lower() in (bg or '').lower()]
    if not hits:
        return False, '背景段无缺口线索词（尚未/未见/缺乏…）'
    q_words = _bigrams(question_text)
    bg_words = _bigrams(bg)
    share = q_words & bg_words
    if len(share) < 2:
        return False, '缺口句与问题段主题词重叠不足（<2 个）'
    return True, '缺口线索 %d 个，主题词重叠 %d 个' % (len(hits), len(share))


def falsifiable(question_text):
    """问题是否可证伪：指标 + 阈值 + 对照/时间点。"""
    t = question_text or ''
    has_metric = any(u in t for u in FALSIFY_METRIC) or bool(NUM.search(t))
    has_cmp = any(c in t for c in FALSIFY_CMP)
    has_ctrl = any(c in t for c in FALSIFY_CTRL)
    ok = bool(has_metric and has_cmp and has_ctrl)
    miss = [n for n, v in (('指标', has_metric), ('阈值', has_cmp), ('对照/时间点', has_ctrl)) if not v]
    return ok, ('可证伪' if ok else '缺 ' + '、'.join(miss))


def alignment(plan, body):
    """目标-路线-指标-成果的 1-1-1 对齐率。"""
    goals = plan.get('goals') or []
    routes = {r.get('id') for r in (plan.get('routes') or [])}
    if not goals:
        return 0.0, ['未提供 goals']
    ok = 0
    bad = []
    for g in goals:
        gid = g.get('id') or '?'
        miss = []
        if not g.get('route') or g.get('route') not in routes:
            miss.append('路线')
        metric = g.get('metric') or ''
        if not metric or not (any(u in metric for u in FALSIFY_METRIC) or NUM.search(metric)):
            miss.append('指标')
        if not g.get('outcome'):
            miss.append('成果')
        if metric and body and metric.split('≥')[0].strip()[:4] not in body:
            # 指标在正文里找不到同款表述，说明正文与结构表各写各的
            miss.append('正文未呼应指标')
        if miss:
            bad.append('%s 缺 %s' % (gid, '、'.join(miss)))
        else:
            ok += 1
    return round(ok / float(len(goals)), 3), bad


def schedule(plan):
    """周期覆盖 / 重叠 / 工作量比。"""
    ms = plan.get('milestones') or []
    cycle = plan.get('cycle_months') or 0
    cap = plan.get('capacity_pm') or 0
    if not ms:
        return dict(coverage=False, overlap=0, effort_ratio=None, gaps=[], bad=[])
    marks = []
    bad = []
    total_effort = 0.0
    for m in ms:
        try:
            s = int(m.get('start')); e = int(m.get('end'))
        except (TypeError, ValueError):
            bad.append('%s 月份不完整' % (m.get('id') or '?'))
            continue
        marks.append((s, e))
        total_effort += float(m.get('effort') or 0)
    covered = set()
    for s, e in marks:
        covered |= set(range(s, e + 1))
    gaps = [i for i in range(1, int(cycle) + 1) if i not in covered] if cycle else []
    overlap = 0
    for i in range(len(marks)):
        for j in range(i + 1, len(marks)):
            a, b = marks[i], marks[j]
            if max(a[0], b[0]) <= min(a[1], b[1]):
                overlap += 1
    ratio = round(total_effort / cap, 2) if cap else None
    return dict(coverage=(not gaps), overlap=overlap, effort_ratio=ratio,
                gaps=gaps, bad=bad, total_effort=total_effort, cycle=cycle, capacity=cap)


def risks(plan):
    """风险完备率 + 类型覆盖。"""
    rs = plan.get('risks') or []
    if not rs:
        return 0.0, 0, ['未提供 risks']
    ok = 0
    bad = []
    types = set()
    for r in rs:
        rid = r.get('id') or '?'
        miss = [f for f in ('trigger', 'fallback', 'decision') if not r.get(f)]
        txt = ' '.join(str(r.get(f) or '') for f in ('type', 'trigger', 'fallback', 'desc'))
        for tname, kws in RISK_TYPES.items():
            if any(k.lower() in txt.lower() for k in kws):
                types.add(tname)
        if miss:
            bad.append('%s 缺 %s' % (rid, '、'.join(miss)))
        else:
            ok += 1
    return round(ok / float(len(rs)), 3), len(types), bad


CITE = re.compile(r'\[\d+(?:[,\-–]\d+)*\]')
CLAIM_CUES = ['表明', '显示', '说明', '证实', '提示', '报道', '发现', '已知', '研究显示',
              'shows', 'suggests', 'reported']


CITE_SECTIONS = r'背景|立项依据|引言|相关工作|研究问题|科学问题|研究目标|技术路线'
NUMERIC_CLAIM_SECTIONS = r'背景|立项依据|引言|相关工作'


def binding_rate(text):
    """论断句挂引用编号的比例。

    两类句算论断：
    1) 带"表明/显示/报道/已知/未见"这类转述线索的句子（无论在哪个节）；
    2) 位于背景/引言/相关工作里的**带数值**的句子——那里的数字来自文献，必须挂引用。

    目标、路线、计划里的数值（n = 24、100 nm、1 mm/min）是本项目自定口径，
    拿文献引用去要求它们属于误判，所以不做数值论断统计。
    """
    claims = total = 0
    for _lvl, title, body in split_sections(text or ''):
        if not re.search(CITE_SECTIONS, title or ''):
            continue
        numeric_claim = bool(re.search(NUMERIC_CLAIM_SECTIONS, title or ''))
        for line in (body or '').split('\n'):
            line = line.strip()
            if not line or line.startswith(('#', '|', '>')):
                continue
            for seg in re.split(r'(?<=[。！？!?])\s*', line):
                seg = seg.strip()
                if len(seg) < 12:
                    continue
                is_claim = any(c in seg for c in CLAIM_CUES) or (numeric_claim and NUM.search(seg))
                if not is_claim:
                    continue
                total += 1
                if CITE.search(seg):
                    claims += 1
    return round(claims / float(total), 3) if total else 0.0, claims, total
