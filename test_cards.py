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

# С 12 сентября 2026 все три формата ранжируются одной линейкой: resh_1k + save_1k.
# A1..A6 — свои уникальные темы. T1..T3 — общая тема ('Shared Topic'): _repeated_topics
#          её находит, но Teardown по ней больше НЕ отбирается (решение Миши).
# X1..X3 — тема-заглушка ('Темы в подписи нет') у трёх авторов: заглушки не считаются
#          «повторяющейся темой» даже справочно.
# a2b — второй ролик автора a2 ниже его нормы: с 12 сентября он в пуле, потому что у
#          автора в окне есть ролик выше нормы.
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
# второй ролик автора a2: 800 просмотров при норме 1000 (ниже нормы), но очень высокие доли
con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play,dur,cap)
    VALUES (?,?,?,?,?,?,?,?)""", (sid, 'A2CODE002', 2, 'a2', RECENT_TS, 800, 60.0, 'cap a2 second'))
con.execute("""INSERT INTO scores (snapshot_id,code,eligible,author_median_play,resh_1k,save_1k,weights)
    VALUES (?,?,1,1000,120,120,'ig')""", (sid, 'A2CODE002'))
con.execute("INSERT INTO topics (code,topic,source) VALUES (?,?,'manual')", ('A2CODE002', 'Topic A2 bis'))
# одинокий автор z1 без единого ролика выше нормы: в пул не попадает
con.execute("INSERT INTO accounts (pk,username,status) VALUES (99,'z1','active')")
con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play,dur,cap)
    VALUES (?,?,?,?,?,?,?,?)""", (sid, 'Z1CODE001', 99, 'z1', RECENT_TS, 1200, 60.0, 'cap z1'))
con.execute("""INSERT INTO scores (snapshot_id,code,eligible,author_median_play,resh_1k,save_1k,weights)
    VALUES (?,?,1,1000,500,500,'ig')""", (sid, 'Z1CODE001'))
con.execute("INSERT INTO topics (code,topic,source) VALUES (?,?,'manual')", ('Z1CODE001', 'Topic Z1'))
con.commit()

picked, pool_n, rep_n = cards.select(con, today=TODAY)

eq('карточек предложено', len(picked), 9)
eq('форматов ровно три', len({c['fmt'] for c in picked}), 3)
eq('по три на формат', sorted(sum(c['fmt'] == f for c in picked) for f in cards.FORMATS), [3, 3, 3])
eq('у автора можно взять больше одного ролика', 'a2' in [c['author'] for c in picked] and
   sum(c['author'] == 'a2' for c in picked) >= 2, True)
eq('ролик ниже нормы автора-победителя попал в карточки',
   'A2CODE002' in {c['code'] for c in picked}, True)
eq('первая карточка — максимум пересылок + сохранений', picked[0]['code'], 'A2CODE002')
eq('в карточках нет автора без ролика выше нормы', 'z1' in {c['author'] for c in picked}, False)
eq('угол машиной не написан', {c['angle'] for c in picked}, {''})
eq('хук машиной не написан', {c['hook'] for c in picked}, {''})
eq('три колонки съёмки у каждой',
   all(set(c['shot']) == {'in frame', 'on screen', 'in the banner'} for c in picked), True)
eq('каркас описания у каждой', all(c['caption'].get('sharpen for the query') for c in picked), True)

pool = cards._pool(con, TODAY)
eq('все в окне свежести', max(r['age'] for r in pool) <= cards.FRESH_DAYS, True)
eq('у каждого автора в пуле есть ролик выше нормы',
   all(any(x['above_norm'] for x in pool if x['username'] == r['username']) for r in pool), True)
eq('ранг = пересылки + сохранения', all(abs(r[cards.RANK] - ((r['resh_1k'] or 0) + (r['save_1k'] or 0))) < 1e-9
                                        for r in pool), True)
eq('длина в границах',
   all(cards.DUR_MIN <= r['dur'] <= cards.DUR_MAX for r in pool), True)
eq('развлекательных тем нет', any(set(r['topics']) & cards.OFF_TOPICS for r in pool), False)

# закрытая тема опускает ролик вниз, но не выбрасывает: жёсткое исключение
# опустошало пул за два месяца
t = picked[0]['topics'][0]
eq('закрытая тема — своя, не общая (по конструкции фикстуры)', t, 'Topic A2 bis')
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

# Повторяющиеся темы считаются справочно; Teardown по ним больше не отбирается
rep = cards._repeated_topics(pool)
eq('повторяющаяся тема найдена (справочно)', rep, {'Shared Topic'})
td = [c for c in picked if c['fmt'] == 'M2 Teardown']
eq('Teardown ранжируется по долям, а не по повторяемости темы',
   any(not (set(c['topics']) & rep) for c in td), True)
eq('заглушки не считаются повторяющейся темой', bool(rep & cards.NOT_TOPICS), False)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
