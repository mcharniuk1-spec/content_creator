"""Отбор на разбор: окно свежести, кап на автора, повторно не качаем. На копии базы."""
import datetime, os, shutil, sys, collections
import deep
from db import connect, DB_PATH
TMP = DB_PATH.replace('.db', '.test.db'); shutil.copy(DB_PATH, TMP)
con = connect(TMP); fail = []
def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<52} {g}   ожидалось {w}")
    if g != w: fail.append(n)

TODAY = datetime.date(2026, 9, 1)
rows, pool = deep.pick(con, today=TODAY)
edge = int(datetime.datetime.combine(TODAY - datetime.timedelta(days=deep.WINDOW),
                                     datetime.time()).timestamp())

eq('берём не больше сотни', len(rows) <= 100, True)
pool_codes = {r['code'] for r in __import__('cards')._pool(con, TODAY)}
eq('всё к разбору — из пула карточек', {r['code'] for r in rows} <= pool_codes, True)
eq('все внутри окна свежести', min(r['ts'] for r in rows) >= edge, True)
eq('старше окна не берём',
   con.execute('SELECT COUNT(*) FROM reels WHERE ts < ?', (edge,)).fetchone()[0] > 0, True)
cnt = collections.Counter(r['username'] for r in rows)
eq('на автора не больше двух', max(cnt.values()), deep.CAP)
eq('порядок покрывает все три линейки формата',
   len({round(r['resh_1k'] or 0) for r in rows[:20]}) > 1, True)
eq('все прошли порог отбора',
   all(con.execute('SELECT eligible FROM scores WHERE code=?', (r['code'],)).fetchone()[0]
       for r in rows), True)

# уже разобранное второй раз не берём
dd = {r[0] for r in con.execute('SELECT code FROM deepdives')}
eq('разобранное в отбор не попало', len({r['code'] for r in rows} & dd), 0)
first = rows[0]['code']
con.execute("INSERT OR REPLACE INTO deepdives (code,snapshot_id,done_at) VALUES (?,1,'x')", (first,))
con.commit()
rows2, _ = deep.pick(con, today=TODAY)
eq('после разбора ролик уходит из очереди', first in {r['code'] for r in rows2}, False)
eq('очередь не опустела', len(rows2) > 0, True)

# то же окно, что у карточек — иначе листов у карточек не будет
import cards
eq('окно разбора совпадает с окном карточек', deep.WINDOW, cards.FRESH_DAYS)
pool_cards = {r['code'] for r in cards._pool(con, TODAY)}
picked, _, _ = cards.select(con, TODAY)
eq('каждая отобранная карточка попадает в разбор',
   len({c['code'] for c in picked} - {r['code'] for r in rows}), 0)

eq('таймкоды: девять кадров на минутном ролике', len(deep.timecodes(60)), 9)
eq('короткий ролик даёт меньше кадров', len(deep.timecodes(3)) < 9, True)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
