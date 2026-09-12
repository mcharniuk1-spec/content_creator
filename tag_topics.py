#!/usr/bin/env python3
"""Разметка тем по выборке. SPEC §4.5.

    python3 tag_topics.py            разметить: верхушку целиком + случайную выборку
    python3 tag_topics.py --stats    что уже размечено

Размечаем не всё. Разобранная верхушка — полностью, она всё равно проходит через руки.
Карта «что снимают» — по случайной выборке 400 роликов окна: для статистики этого хватает,
а полная разметка нужна была бы только под поштучный поиск, которым мы не пользуемся.

Словарь тем выведен из чтения подписей (`topics.py`), а не придуман заранее. Доля
нераспознанных называется явно — это само по себе факт: у части роликов содержание
живёт только в видео.
"""
import datetime, pathlib, random, re, sys
from db import connect

D = pathlib.Path(__file__).parent / 'data'
from topics import TOPICS

WINDOW = 30   # = cards.FRESH_DAYS; 14 → 30 решением Миши 12 сентября 2026
SAMPLE = 400
SEED = 20260903        # выборка воспроизводима: та же неделя — та же выборка

RX = [(name, re.compile(rx, re.I)) for name, rx in TOPICS]


def match(cap):
    cap = cap or ''
    return [name for name, rx in RX if rx.search(cap)]


def tag(con, today=None, sample=SAMPLE):
    today = today or datetime.date.today()
    edge = int(datetime.datetime.combine(today - datetime.timedelta(days=WINDOW),
                                         datetime.time()).timestamp())
    row = con.execute('SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()
    if not row:
        return {'manual': 0, 'sample': 0}, {'manual': 0, 'sample': 0}, 0
    sid = row[0]

    top = [dict(r) for r in con.execute("""SELECT r.code, r.cap FROM reels r
        JOIN deepdives d ON d.code = r.code WHERE r.snapshot_id = ?""", (sid,))]
    rest = [dict(r) for r in con.execute("""SELECT r.code, r.cap FROM reels r
        LEFT JOIN deepdives d ON d.code = r.code
        WHERE r.snapshot_id = ? AND r.ts >= ? AND d.code IS NULL""", (sid, edge))]
    random.Random(SEED).shuffle(rest)
    rest = rest[:sample]

    done = {'manual': 0, 'sample': 0}
    unknown = {'manual': 0, 'sample': 0}
    for rows, source in ((top, 'manual'), (rest, 'sample')):
        for r in rows:
            names = match(r['cap'])
            if names:
                con.execute("DELETE FROM topics WHERE code=? AND topic='Темы в подписи нет'",
                            (r['code'],))
            else:
                names = ['Темы в подписи нет']
                unknown[source] += 1
            for n in names:
                con.execute('INSERT OR REPLACE INTO topics (code,topic,source) VALUES (?,?,?)',
                            (r['code'], n, source))
            done[source] += 1
    miss = con.execute("""SELECT r.code, r.username, r.cap FROM reels r
        JOIN topics t ON t.code=r.code AND t.topic='Темы в подписи нет'
        WHERE r.snapshot_id=? AND r.cap<>'' ORDER BY r.play DESC LIMIT 80""", (sid,)).fetchall()
    if miss:
        (D / 'unmatched.md').write_text(
            f'# Подписи, для которых нет темы — {today.isoformat()}\n\n'
            'Читаются глазами, из них дописывается словарь в `topics.py`. Пока тема не заведена,\n'
            'эти ролики для радара не существуют.\n\n'
            + '\n'.join(f"- **{m['username']}** `{m['code']}`\n      "
                         + ' '.join((m['cap'] or '').split())[:200] for m in miss),
            encoding='utf-8')
    con.commit()
    return done, unknown, len(rest)


def stats(con):
    n_codes = con.execute('SELECT COUNT(DISTINCT code) FROM topics').fetchone()[0]
    n_top = con.execute('SELECT COUNT(DISTINCT topic) FROM topics').fetchone()[0]
    print(f'размечено роликов {n_codes}, тем {n_top}\n')
    for t, n, a in con.execute("""SELECT t.topic, COUNT(*), COUNT(DISTINCT r.username)
        FROM topics t JOIN reels r USING(code) GROUP BY t.topic ORDER BY 2 DESC LIMIT 12"""):
        print(f'  {n:>4} роликов у {a:>3} авторов   {t}')


if __name__ == '__main__':
    con = connect()
    if '--stats' in sys.argv:
        stats(con); sys.exit()
    done, unknown, n_rest = tag(con)
    tot = done['manual'] + done['sample']
    unk = unknown['manual'] + unknown['sample']
    print(f'верхушка: размечено {done["manual"]}, без темы в подписи {unknown["manual"]}')
    print(f'выборка:  размечено {done["sample"]} из окна {WINDOW} дней, '
          f'без темы в подписи {unknown["sample"]}')
    print(f'\nвсего {tot}, нераспознанных {unk} ({100 * unk / max(tot, 1):.0f}%)')
    print('их подписи выложены в data/unmatched.md — из них дописывается словарь')
