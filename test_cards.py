"""Отбор карточек: фильтры, слоты, что машина не заполняет. На копии базы."""
import datetime, os, shutil, sys
import cards, posts
from db import connect, DB_PATH
TMP = DB_PATH.replace('.db', '.test.db'); shutil.copy(DB_PATH, TMP)
con = connect(TMP); fail = []
def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<52} {g}   ожидалось {w}")
    if g != w: fail.append(n)

TODAY = datetime.date(2026, 9, 1)
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
posts.add(con, (TODAY - datetime.timedelta(days=5)).isoformat(), t, 'РАЗБОР')
pool2 = cards._pool(con, TODAY)
closed_only = [r for r in pool2 if set(r['topics']) <= {t}]
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
td = [c for c in picked if c['fmt'] == 'M2 Teardown']
eq('Teardown только по повторяющимся темам',
   all(set(c['topics']) & rep for c in td), True)
eq('заглушки не считаются темой для Teardown', bool(rep & cards.NOT_TOPICS), False)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
