"""Отбор на разбор: окно свежести, кап на автора, повторно не качаем.

База синтетическая (db.SCHEMA на временном файле), а не копия рабочей. Причина
конкретного прежнего провала: "все прошли порог отбора" читало
`SELECT eligible FROM scores WHERE code=?` без snapshot_id/weights — на живой базе
с несколькими снимками один и тот же код встречается в scores не одной строкой, и
запрос мог вернуть строку из другого снимка. Здесь у каждого кода ровно одна строка
в scores, и запрос всё равно сделан однозначным (см. ниже) — так проверяется отбор
deep.pick(), а не то, какая случайная строка попадётся.
"""
import datetime, os, sys, collections
import cards, deep
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.deep-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP); fail = []

def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<52} {g}   ожидалось {w}")
    if g != w: fail.append(n)

TODAY = datetime.date(2026, 9, 1)
RECENT_TS = int(datetime.datetime.combine(TODAY - datetime.timedelta(days=2), datetime.time()).timestamp())
OLD_TS = int(datetime.datetime.combine(TODAY - datetime.timedelta(days=60), datetime.time()).timestamp())

con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,20,0,1)", (TODAY.isoformat(),))
sid = con.execute("SELECT id FROM snapshots WHERE taken=?", (TODAY.isoformat(),)).fetchone()[0]

pk_seq = iter(range(1, 1000))


def add_reel(user, code, resh_1k, save_1k, ts=RECENT_TS, topic=None):
    pk = next(pk_seq)
    if not con.execute('SELECT 1 FROM accounts WHERE username=?', (user,)).fetchone():
        con.execute("INSERT INTO accounts (pk,username,status) VALUES (?,?,'active')", (pk, user))
    else:
        pk = con.execute('SELECT pk FROM accounts WHERE username=?', (user,)).fetchone()[0]
    con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play,dur,cap)
        VALUES (?,?,?,?,?,?,?,?)""", (sid, code, pk, user, ts, 3000, 60.0, f'cap {code}'))
    con.execute("""INSERT INTO scores (snapshot_id,code,eligible,author_median_play,
        resh_1k,save_1k,weights) VALUES (?,?,1,1000,?,?,'ig')""", (sid, code, resh_1k, save_1k))
    con.execute("INSERT INTO topics (code,topic,source) VALUES (?,?,'manual')",
                (code, topic or f'Topic {code}'))


# та же фикстура, что делает cards.select() предсказуемым (9 карточек, 3 формата)
MAIN = [
    ('a1', 100, 10), ('a2', 95, 9), ('a3', 90, 8),
    ('a4', 50, 100), ('a5', 45, 95), ('a6', 40, 90),
]
for user, resh_1k, save_1k in MAIN:
    add_reel(user, f'{user.upper()}CODE01', resh_1k, save_1k)
for i, user in enumerate(('t1', 't2', 't3'), 1):
    add_reel(user, f'{user.upper()}CODE01', 10 - i, 50 - i * 5, topic='Shared Topic')

# автор с запасом: три ролика сверх формируемых карточек — деп кап (deep.CAP=2)
# должен ограничить его до двух в добавочной части очереди
for i in range(3):
    add_reel('capauthor', f'CAPCODE{i:02d}', 1, 1)

# ролик за пределами окна свежести — должен остаться в reels, но не попасть в пул
add_reel('oldauthor', 'OLDCODE001', 1, 1, ts=OLD_TS)
con.commit()

rows, pool = deep.pick(con, today=TODAY)
edge = int(datetime.datetime.combine(TODAY - datetime.timedelta(days=deep.WINDOW),
                                     datetime.time()).timestamp())

eq('берём не больше сотни', len(rows) <= 100, True)
pool_codes = {r['code'] for r in cards._pool(con, TODAY)}
eq('всё к разбору — из пула карточек', {r['code'] for r in rows} <= pool_codes, True)
eq('все внутри окна свежести', min(r['ts'] for r in rows) >= edge, True)
eq('старше окна не берём',
   con.execute('SELECT COUNT(*) FROM reels WHERE ts < ?', (edge,)).fetchone()[0] > 0, True)
eq('старый ролик не попал в разбор', 'OLDCODE001' in {r['code'] for r in rows}, False)

picked, _, _ = cards.select(con, today=TODAY)
extra = [r for r in rows if r['code'] not in {c['code'] for c in picked}]
cnt_extra = collections.Counter(r['username'] for r in extra)
eq('на автора не больше двух в доборе', max(cnt_extra.values()) if cnt_extra else 0, deep.CAP)
eq('кап действительно сработал (capauthor обрезан)', cnt_extra.get('capauthor'), deep.CAP)
eq('порядок покрывает все три линейки формата',
   len({round(r['resh_1k'] or 0) for r in rows[:20]}) > 1, True)
eq('все прошли порог отбора',
   all(con.execute("""SELECT eligible FROM scores
       WHERE code=? AND snapshot_id=? AND weights='ig'""", (r['code'], sid)).fetchone()[0]
       for r in rows), True)

# уже разобранное второй раз не берём
dd = {r[0] for r in con.execute('SELECT code FROM deepdives')}
eq('разобранное в отбор не попало', len({r['code'] for r in rows} & dd), 0)
first = rows[0]['code']
con.execute("INSERT OR REPLACE INTO deepdives (code,snapshot_id,done_at) VALUES (?,?,'x')", (first, sid))
con.commit()
rows2, _ = deep.pick(con, today=TODAY)
eq('после разбора ролик уходит из очереди', first in {r['code'] for r in rows2}, False)
eq('очередь не опустела', len(rows2) > 0, True)

# то же окно, что у карточек — иначе листов у карточек не будет
eq('окно разбора совпадает с окном карточек', deep.WINDOW, cards.FRESH_DAYS)
picked, _, _ = cards.select(con, TODAY)
# у карточки должен быть материал: либо она в очереди разбора, либо разобрана раньше
# и кадры с расшифровкой уже лежат в базе. Повторно качать её незачем.
queued = {r['code'] for r in rows}
done = {x[0] for x in con.execute('SELECT code FROM deepdives')}
eq('у каждой карточки есть кадры или очередь на разбор',
   len([c for c in picked if c['code'] not in queued and c['code'] not in done]), 0)

eq('таймкоды: девять кадров на минутном ролике', len(deep.timecodes(60)), 9)
eq('короткий ролик даёт меньше кадров', len(deep.timecodes(3)) < 9, True)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
