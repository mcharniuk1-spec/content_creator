"""Разметка тем: выборка, воспроизводимость, доля нераспознанных. На копии базы."""
import os, shutil, sys
import tag_topics
from db import connect, DB_PATH
TMP = DB_PATH.replace('.db', '.test.db'); shutil.copy(DB_PATH, TMP)
con = connect(TMP); fail = []
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

con.execute('DELETE FROM topics'); con.commit()
done, unknown, n_rest = tag_topics.tag(con, sample=50)
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
tag_topics.tag(con, sample=50)
second = {r[0] for r in con.execute("SELECT code FROM topics WHERE source='sample'")}
eq('выборка воспроизводима при том же зерне', first == second, True)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
