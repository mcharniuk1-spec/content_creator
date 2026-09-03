#!/usr/bin/env python3
"""Признаки, которые выводятся из подписи и речи — то, чего нет в метриках.

    python3 analyze.py            сводка по окну
    python3 analyze.py КОД        разбор одного ролика

Метрики говорят, что зашло. Эти признаки — как оно сделано: чем открывают, сколько
говорят, зовут ли в комментарии, есть ли число в первой строке. По ним видно приём,
а не результат, и именно они переносятся в наши ролики.
"""
import json, re, statistics, sys
from db import connect

# Каждый признак — отдельный вопрос к материалу, а не украшение таблицы.
CAPTION = [
    ('comment_bait', r'\bcomment\b.{0,30}\b(and|to get|for)\b|\bcomment\s+["“]?\w+',
     'зовёт написать слово в комментарии'),
    ('bio_link', r'link in bio|bio link|link below', 'отправляет по ссылке в профиле'),
    ('dm_promise', r'\bdm\b|send (it|you)|i.ll send', 'обещает прислать в личные'),
    ('money_claim', r'\$\s?\d|\b\d+k\b.{0,12}(month|mo|year)|revenue|\bmrr\b|income',
     'обещание дохода'),
    ('question', r'\?', 'вопрос в подписи'),
    ('number', r'\d', 'есть число'),
    ('list_form', r'^\s*\d[\.\)]|\b(step|number)\s+(one|two|1|2)\b', 'подан списком'),
]
HOOK = [
    ('hook_question', r'\?', 'открывает вопросом'),
    ('hook_number', r'\d', 'число в первых словах'),
    ('hook_you', r'\byou\b|\byour\b', 'обращается на «ты» сразу'),
    ('hook_claim', r'\b(nobody|everyone|most people|stop|never|don.t)\b', 'открывает утверждением-противопоставлением'),
]


def caption_flags(cap):
    cap = cap or ''
    return {name: bool(re.search(rx, cap, re.I)) for name, rx, _ in CAPTION}


def speech_facts(con, code, dur=None):
    """Что видно в речи: объём, темп, устройство хука."""
    r = con.execute("SELECT text, segments FROM transcripts WHERE code=? AND text<>''",
                    (code,)).fetchone()
    if not r:
        return {}
    words = r['text'].split()
    segs = json.loads(r['segments'])
    head = ' '.join(words[:20])
    out = {'words': len(words), 'lines': len(segs),
           'wpm': round(len(words) / (dur / 60), 0) if dur else None}
    out.update({name: bool(re.search(rx, head, re.I)) for name, rx, _ in HOOK})
    import blocks
    b = blocks.blocks(con, code)
    if b:
        out.update({'hook_words': b['words']['hook'], 'body_words': b['words']['body'],
                    'tail_words': b['words']['tail']})
    return out


def facts(con, row):
    """Полный набор признаков по ролику: из подписи, из речи, из кадров."""
    out = dict(caption_flags(row['cap']))
    out.update(speech_facts(con, row['code'], row['dur']))
    out['topics'] = [t[0] for t in con.execute('SELECT topic FROM topics WHERE code=?', (row['code'],))]
    out['one_take'] = (row['cuts_ps'] is not None and row['cuts_ps'] < 0.02)
    out['analysed'] = row['cuts_ps'] is not None
    return out


def summary(con, rows):
    """Доля роликов с каждым признаком — чтобы видеть приём, а не единичный случай."""
    n = len(rows)
    got = [facts(con, r) for r in rows]
    out = []
    for name, _, human in CAPTION + HOOK:
        have = sum(1 for f in got if f.get(name))
        base = sum(1 for f in got if name in f)
        if base:
            out.append((human, have, base, 100 * have / base))
    return out


if __name__ == '__main__':
    con = connect()
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        code = sys.argv[1]
        r = con.execute("""SELECT r.*, d.cuts_ps FROM reels r LEFT JOIN deepdives d ON d.code=r.code
                           WHERE r.code=? LIMIT 1""", (code,)).fetchone()
        if not r:
            sys.exit('нет такого ролика')
        f = facts(con, r)
        print(f'{code} · {r["username"]}\n')
        for k, v in f.items():
            print(f'  {k:<14} {v}')
        sys.exit()
    import datetime
    edge = int(datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=14),
                                         datetime.time()).timestamp())
    rows = con.execute("""SELECT r.*, d.cuts_ps FROM reels r
        JOIN scores s USING(snapshot_id,code) LEFT JOIN deepdives d ON d.code=r.code
        WHERE r.snapshot_id=(SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
          AND s.weights='ig' AND s.eligible=1 AND r.ts>=?""", (edge,)).fetchall()
    print(f'роликов в окне: {len(rows)}\n')
    for human, have, base, pct in summary(con, rows):
        print(f'  {human:<44} {have:>4} из {base:<4} {pct:>5.0f}%')
