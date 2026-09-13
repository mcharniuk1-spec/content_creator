#!/usr/bin/env python3
"""Content blocks: the selection axis of the weekly shortlist (Misha, 13 Sep 2026).

Nine blocks answer "what does M2 Lab talk about" for AI-for-non-technical-founders.
A found reel is routed to ONE block. First choice: the agent's reading of caption and
transcript (`data/analysis/blocks/<code>.json`, engine/block_route.py, contract br-v1).
Fallback: its topic tags (`topics` table, dictionary in topics.py) plus a regex pass over
caption and transcript. The card says which of the two routed it. Personas (Rick, Emma,
Anna) are no longer the axis: they stay as "on whose example" inside a block.
A tenth block, "Answers to comments", is an internal source of topics, not a shelf the
radar fills; it is added later when the comment stream exists.

    python3 content_blocks.py            block of every reel in the 30-day pool, counts
    python3 content_blocks.py --stats    counts only

Routing is a hint with evidence (which tag, which words); the human picking 5 of 15
sees the block and can disagree. Nothing here is a judgement of quality.
"""
import datetime, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).parent
TA_DIR = ROOT / 'data' / 'analysis' / 'transcripts'
AGENT_DIR = ROOT / 'data' / 'analysis' / 'blocks'     # br-v1 files from engine/block_route.py

# Order = tie-break priority: the under-served blocks first (corpus has few of them,
# Reddit asks for them most), the over-supplied ones last (news, builds, skills).
# fmt = default shooting format (cards.FORMATS) for a card born in this block.
BLOCKS = {
    'process':  dict(name='Process', ru='Процесс',
                     tags={'AI в конкретном бизнес-процессе', 'Лидогенерация, скрейпинг, CRM',
                           'Голосовые агенты и телефония', 'Продуктивность и офисные инструменты'},
                     rx=r"lead|invoice|quote|estimate|voicemail|missed call|inbox|follow.?up|onboard|"
                        r"customer|client|support ticket|scheduling|bookkeep|crm\b|receptionist|"
                        r"your (business|process|workflow)|small business|automate|hours? (a|per) week",
                     fmt='M2 Teardown'),
    'money':    dict(name='Money', ru='Деньги',
                     tags={'Токены, стоимость, лимиты'},
                     rx=r"\$\d|per month|/mo\b|a month|subscription|pricing|cost|cheaper|expensive|"
                        r"pay(ing)? for|roi\b|worth it|overpay|budget|save \d+%",
                     fmt='M2 Radar'),
    'trust':    dict(name='Trust', ru='Доверие',
                     tags=set(),
                     rx=r"hallucinat|made up|wrong answer|trust|verify|double.?check|fact.?check|"
                        r"privacy|your data|leak|confidential|security|policy|permission|"
                        r"human in the loop|review before|approve",
                     fmt='M2 Teardown'),
    'mistakes': dict(name='Mistakes', ru='Ошибки',
                     tags={'Критика и скепсис про AI'},
                     rx=r"mistake|stop (doing|using)|don.t (do|use|buy)|wrong way|failed|"
                        r"waste[ds]? |overrated|hype|slop|regret|lesson|what went wrong|turned off",
                     fmt='M2 Teardown'),
    'pick':     dict(name='What to pick', ru='Что выбрать',
                     tags={'Обзор инструмента'},
                     rx=r"\bvs\.?\b|versus|compar|best (tool|app|ai)|top \d|which (one|tool|ai)|"
                        r"alternative|instead of|better than|ranked|tier list|tested \d+",
                     fmt='M2 Radar'),
    'learn':    dict(name='Learn', ru='Обучение',
                     tags={'Обучение и навыки', 'Как думать и работать с AI', 'Память и контекст агентов'},
                     rx=r"beginner|explain|how (it|ai) works|what is|learn|course|tutorial|"
                        r"step.by.step|in a weekend|weekend|basics|101\b|guide|prompt",
                     fmt='M2 Builds'),
    'skills':   dict(name='Skills and repos', ru='Скиллы и репозитории',
                     tags={'Claude Code: скиллы, плагины, команды', 'Готовый репозиторий с GitHub'},
                     rx=r"\bmcp\b|skill|plugin|github|repo\b|open.?source|template|starter|"
                        r"extension|integration|connector",
                     fmt='M2 Builds'),
    'builds':   dict(name='Builds', ru='Билды',
                     tags={'Сборка агентов и мультиагентные системы', 'Дизайн и сайты через AI',
                           'AI-видео и производство контента', 'Программирование и код'},
                     rx=r"\bbuilt\b|i built|build(ing)? (a|an|my|this)|from scratch|prototype|"
                        r"shipped|launched my|in \d+ (minutes|hours)|no.?code|vibe.?cod",
                     fmt='M2 Builds'),
    'news':     dict(name='News', ru='Новости',
                     tags={'Новости моделей и лабораторий'},
                     rx=r"just (dropped|launched|released|announced)|new (model|version|update)|"
                        r"gpt.?\d|claude \d|gemini \d|openai|anthropic|breaking|this week in",
                     fmt='M2 Radar'),
}
ORDER = list(BLOCKS)
TAG_W, RX_W = 2, 1            # a curated tag says more than one matching word
UNASSIGNED = 'unassigned'      # nothing matched: still in the pool, competes on strength only

_RX = {bid: re.compile(b['rx'], re.I) for bid, b in BLOCKS.items()}


def reel_text(con, code, cap=''):
    """Caption plus transcript text when we have it (ta-v1 beats, else raw segments)."""
    parts = [cap or '']
    ta = TA_DIR / f'{code}.json'
    if ta.exists():
        try:
            parts += [b.get('text', '') for b in json.loads(ta.read_text(encoding='utf-8')).get('beats', [])]
        except ValueError:
            pass
    else:
        row = con.execute('SELECT segments FROM transcripts WHERE code=?', (code,)).fetchone() if con else None
        if row and row[0]:
            try:
                segs = json.loads(row[0])
                parts += [s.get('text', '') for s in segs if isinstance(s, dict)]
            except ValueError:
                pass
    return ' '.join(parts)


def classify(topics, text=''):
    """-> (block_id, evidence) — the block with the highest score; ties go to the block
    earlier in ORDER (under-served first). evidence = {'tags': [...], 'words': [...]}"""
    topics = set(topics or [])
    text = text or ''
    best, best_score, best_ev = UNASSIGNED, 0, {'tags': [], 'words': []}
    for bid in ORDER:
        b = BLOCKS[bid]
        tags = sorted(topics & b['tags'])
        words = sorted({m.group(0).lower() for m in _RX[bid].finditer(text)})
        score = TAG_W * len(tags) + RX_W * min(len(words), 4)
        if score > best_score:
            best, best_score, best_ev = bid, score, {'tags': tags, 'words': words[:4]}
    return best, best_ev


_agent_cache = {}


def agent_route(code, agent_dir=AGENT_DIR):
    """br-v1 file for a reel (engine/block_route.py) or None. Cached per process."""
    key = (str(agent_dir), code)
    if key not in _agent_cache:
        p = pathlib.Path(agent_dir) / f'{code}.json'
        d = None
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding='utf-8'))
            except ValueError:
                d = None
        _agent_cache[key] = d if isinstance(d, dict) and d.get('analysis_version') == 'br-v1' else None
    return _agent_cache[key]


def route(code, topics, text='', agent_dir=AGENT_DIR):
    """Block of a reel with its provenance: the agent's br-v1 file when it exists, else
    tags + regex. -> dict(block, evidence, source, about, regex_block, confidence)."""
    regex_block, ev = classify(topics, text)
    d = agent_route(code, agent_dir)
    if d is None:
        return {'block': regex_block, 'evidence': ev, 'source': 'regex', 'about': None,
                'regex_block': regex_block, 'confidence': None}
    block = d.get('block') if d.get('block') in BLOCKS else UNASSIGNED
    return {'block': block, 'evidence': {'tags': [], 'words': list(d.get('evidence') or [])[:3]},
            'source': 'agent', 'about': d.get('about'), 'regex_block': regex_block,
            'confidence': d.get('confidence'),
            # agent said null: off the niche or no text to judge; cards._pool drops such reels
            'reason_if_null': (d.get('reason_if_null') or 'no block') if block == UNASSIGNED else None}


def label(bid):
    return BLOCKS[bid]['name'] if bid in BLOCKS else 'Unassigned'


def default_format(bid):
    return BLOCKS[bid]['fmt'] if bid in BLOCKS else 'M2 Radar'


def distribution(pool):
    """{block_id: count} over a cards._pool() result (each item has 'block')."""
    out = {bid: 0 for bid in ORDER + [UNASSIGNED]}
    for r in pool:
        out[r.get('block') or UNASSIGNED] += 1
    return out


if __name__ == '__main__':
    from db import connect
    import cards
    con = connect()
    pool = cards._pool(con, datetime.date.today())
    dist = distribution(pool)
    print(f'reels in the {cards.FRESH_DAYS}-day pool: {len(pool)}\n')
    for bid, n in dist.items():
        print(f'  {n:>4}  {label(bid)}')
    if '--stats' not in sys.argv:
        print()
        for r in sorted(pool, key=lambda r: (r['block'] or 'zz', -(r[cards.RANK] or 0))):
            ev = r.get('block_evidence') or {}
            print(f"  {label(r['block']):<20} {r.get('block_source', '?'):<5} {r['username']:<22} {r['code']}  "
                  f"{r[cards.RANK]:>5.0f}  {', '.join(ev.get('tags', []))[:40]} | {', '.join(ev.get('words', []))[:60]}")
