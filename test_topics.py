"""Разметка тем: выборка, воспроизводимость, доля нераспознанных.

База синтетическая (db.SCHEMA на временном файле), а не копия рабочей. Причина:
`tag_topics.tag()` размечает верхушку (то, что уже разобрано — deepdives) через
JOIN к roликам ИМЕННО последнего снимка — если код разобран, но его подпись живёт
только в более старом снимке (обычный итог роста базы), верхушка размечается не
целиком. Это настоящее ограничение tag_topics.py (не в периметре ответственности
этого файла — см. check.py, раздел «известные ограничения», и docs/TESTING.md),
а не то, что должен ловить модульный тест на выдуманных данных. Здесь у каждого
разбора подпись обязана лежать в актуальном снимке — так проверяется сама функция
tag(), а не состояние прод-базы на сегодняшний день.
"""
import os, sys
import tag_topics
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.topics-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP)
fail = []

def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<52} {g}   ожидалось {w}")
    if g != w: fail.append(n)

eq('«comment X and I will send» — не тема, а призыв',
   tag_topics.match('Comment "AGENTS" and I\'ll send'), ['Только призыв, без темы в подписи'])
eq('подпись про токены попадает в свою тему',
   'Токены, стоимость, лимиты' in tag_topics.match('this burns tokens and costs you money'), True)
eq('пустая подпись не даёт тем', tag_topics.match(''), [])
eq('ролик может попасть в несколько тем',
   len(tag_topics.match('claude code plugin for lead scraping and crm')) > 1, True)

# ---- снимок и ролики: верхушка (deepdives) целиком видна в этом же снимке -------
import datetime
TODAY = datetime.date(2026, 9, 1)
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,1,0,1)", (TODAY.isoformat(),))
sid = con.execute("SELECT id FROM snapshots WHERE taken=?", (TODAY.isoformat(),)).fetchone()[0]
NOW = int(datetime.datetime.combine(TODAY - datetime.timedelta(days=2), datetime.time()).timestamp())

TOP_CAPS = {
    'TOP001AAAA': 'this burns tokens and costs you money',      # узнаваемая тема
    'TOP002AAAA': 'claude code plugin for lead scraping crm',   # несколько тем
    'TOP003AAAA': 'ничего распознаваемого тут нет вообще',      # уйдёт в «без темы»
}
for code, cap in TOP_CAPS.items():
    con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,cap)
        VALUES (?,?,1,'author',?,?)""", (sid, code, NOW, cap))
    con.execute("INSERT INTO deepdives (code,snapshot_id) VALUES (?,?)", (code, sid))

# окно выборки (rest): роликов достаточно, чтобы выборка размером 50 была ограничена
for i in range(60):
    con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,cap)
        VALUES (?,?,1,'author',?,?)""",
        (sid, f'REST{i:03d}AAA', NOW, f'случайный текст {i}'))
con.commit()

done, unknown, n_rest = tag_topics.tag(con, today=TODAY, sample=50)
eq('верхушка размечена целиком', done['manual'],
   con.execute('SELECT COUNT(*) FROM deepdives').fetchone()[0])
eq('выборка ограничена размером', done['sample'], 50)
eq('нераспознанные помечены явно',
   con.execute("SELECT COUNT(DISTINCT code) FROM topics WHERE topic='Темы в подписи нет'").fetchone()[0],
   unknown['manual'] + unknown['sample'])
eq('источник разметки различается',
   {r[0] for r in con.execute('SELECT DISTINCT source FROM topics')}, {'manual', 'sample'})

first = {r[0] for r in con.execute("SELECT code FROM topics WHERE source='sample'")}
con.execute('DELETE FROM topics'); con.commit()
tag_topics.tag(con, today=TODAY, sample=50)
second = {r[0] for r in con.execute("SELECT code FROM topics WHERE source='sample'")}
eq('выборка воспроизводима при том же зерне', first == second, True)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
