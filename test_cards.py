"""Отбор карточек: фильтры, слоты, что машина не заполняет.

База синтетическая (db.SCHEMA на временном файле), а не копия рабочей — с известным
заранее пулом из 12 роликов (9 обычных + 3 с общей темой для Teardown), так что
исход cards.select() (кто попадёт в какой формат) предсказан, а не подсмотрен
после факта на живых данных.
"""
import datetime, os, sys
import cards, posts
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.cards-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP); fail = []

def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<52} {g}   ожидалось {w}")
    if g != w: fail.append(n)

TODAY = datetime.date(2026, 9, 1)
RECENT_TS = int(datetime.datetime.combine(TODAY - datetime.timedelta(days=2), datetime.time()).timestamp())

con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,12,0,1)", (TODAY.isoformat(),))
sid = con.execute("SELECT id FROM snapshots WHERE taken=?", (TODAY.isoformat(),)).fetchone()[0]

# A1..A6 — свои уникальные темы, ранжируются по resh_1k (Radar) и save_1k (Builds).
# T1..T3 — общая тема ('Shared Topic'), ранжируются по save_1k, но идут в Teardown
#          только через отбор _repeated_topics (>=3 авторов на тему).
# X1..X3 — тема-заглушка ('Темы в подписи нет') у трёх авторов: проверяет, что
#          заглушки не считаются "повторяющейся темой" для Teardown, хотя формально
#          у них тоже 3 автора на одну "тему".
ROWS = [
    # username,  resh_1k, save_1k, topic
    ('a1', 100, 10, 'Topic A1'),
    ('a2',  95,  9, 'Topic A2'),
    ('a3',  90,  8, 'Topic A3'),
    ('a4',  50, 100, 'Topic A4'),
    ('a5',  45,  95, 'Topic A5'),
    ('a6',  40,  90, 'Topic A6'),
    ('t1',  10,  50, 'Shared Topic'),
    ('t2',   9,  45, 'Shared Topic'),
    ('t3',   8,  40, 'Shared Topic'),
    ('x1',   1,   1, 'Темы в подписи нет'),
    ('x2',   1,   1, 'Темы в подписи нет'),
    ('x3',   1,   1, 'Темы в подписи нет'),
]
for pk, (user, resh_1k, save_1k, topic) in enumerate(ROWS, 1):
    code = f'{user.upper()}CODE001'
    con.execute("INSERT INTO accounts (pk,username,status) VALUES (?,?,'active')", (pk, user))
    con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play,dur,cap)
        VALUES (?,?,?,?,?,?,?,?)""", (sid, code, pk, user, RECENT_TS, 3000, 60.0, f'cap {user}'))
    con.execute("""INSERT INTO scores (snapshot_id,code,eligible,author_median_play,
        resh_1k,save_1k,weights) VALUES (?,?,1,1000,?,?,'ig')""", (sid, code, resh_1k, save_1k))
    con.execute("INSERT INTO topics (code,topic,source) VALUES (?,?,'manual')", (code, topic))
con.commit()

picked, pool_n, rep_n = cards.select(con, today=TODAY)

eq('карточек предложено', len(picked), 9)
eq('форматов ровно три', len({c['fmt'] for c in picked}), 3)
eq('по три на формат', sorted(sum(c['fmt'] == f for c in picked) for f in cards.FORMATS), [3, 3, 3])
eq('один автор — одна карточка', len({c['author'] for c in picked}), len(picked))
eq('угол машиной не написан', {c['angle'] for c in picked}, {''})
eq('хук машиной не написан', {c['hook'] for c in picked}, {''})
eq('три колонки съёмки у каждой',
   all(set(c['shot']) == {'in frame', 'on screen', 'in the banner'} for c in picked), True)
eq('каркас описания у каждой', all(c['caption'].get('sharpen for the query') for c in picked), True)

pool = cards._pool(con, TODAY)
eq('все в окне свежести', max(r['age'] for r in pool) <= cards.FRESH_DAYS, True)
eq('все превышают норму автора', min(r['mult'] for r in pool) >= cards.MIN_MULT, True)
eq('длина в границах',
   all(cards.DUR_MIN <= r['dur'] <= cards.DUR_MAX for r in pool), True)
eq('развлекательных тем нет', any(set(r['topics']) & cards.OFF_TOPICS for r in pool), False)

# закрытая тема опускает ролик вниз, но не выбрасывает: жёсткое исключение
# опустошало пул за два месяца
t = picked[0]['topics'][0]
eq('закрытая тема — своя, не общая (по конструкции фикстуры)', t, 'Topic A1')
posts.add(con, (TODAY - datetime.timedelta(days=5)).isoformat(), t, 'РАЗБОР')
pool2 = cards._pool(con, TODAY)
# подмножество, а не совпадение: пустой список тем — тоже formально "подмножество {t}",
# но ролик без тем не является "роликом на закрытую тему" — это отфильтровано явно
closed_only = [r for r in pool2 if r['topics'] and set(r['topics']) <= {t}]
eq('ролики на закрытую тему остались в пуле', len(closed_only) > 0, True)
eq('и помечены как уже закрытые',
   all(r['closed_share'] == 1 for r in closed_only), True)
picked2, _, _ = cards.select(con, TODAY)
eq('но в карточки идут после свежих',
   all(c['n'] > 3 or not set(c['topics']) <= {t} for c in picked2), True)

# использованный референс не предлагается второй раз
posts.add(con, TODAY.isoformat(), 'иная тема', 'РАЗБОР', ref=picked[1]['code'])
eq('использованный референс исключён',
   picked[1]['code'] in {r['code'] for r in cards._pool(con, TODAY)}, False)

# Teardown берёт только темы, повторившиеся у нескольких авторов
rep = cards._repeated_topics(pool)
eq('повторяющаяся тема найдена', rep, {'Shared Topic'})
td = [c for c in picked if c['fmt'] == 'M2 Teardown']
eq('Teardown только по повторяющимся темам',
   all(set(c['topics']) & rep for c in td), True)
eq('заглушки не считаются темой для Teardown', bool(rep & cards.NOT_TOPICS), False)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
