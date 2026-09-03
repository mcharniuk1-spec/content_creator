"""Память о снятом и ввод своих цифр. Работает на копии базы."""
import datetime, os, shutil, sys
import posts
from db import connect, DB_PATH

TMP = DB_PATH.replace('.db', '.test.db')
shutil.copy(DB_PATH, TMP)
con = connect(TMP)
fail = []
def eq(name, got, want):
    print(f"  {'✓' if got == want else '✗'} {name:<50} {got}   ожидалось {want}")
    if got != want: fail.append(name)

today = datetime.date(2026, 10, 1)
d = lambda days: (today - datetime.timedelta(days=days)).isoformat()

p1 = posts.add(con, d(3), 'Токены, стоимость, лимиты', 'РАЗБОР', url='u1', lead='Миша')
p2 = posts.add(con, d(20), 'Готовый репозиторий с GitHub', 'ВИТРИНА', lead='Макс')
p3 = posts.add(con, d(41), 'AI в конкретном бизнес-процессе', 'РАЗБОР')
p4 = posts.add(con, d(60), 'Обучение и навыки', 'НОВОСТЬ')          # старше шести недель

cl = posts.closed_topics(con, today=today)
eq('тем в памяти', len(cl), 3)
eq('свежая тема закрыта', 'Токены, стоимость, лимиты' in cl, True)
eq('на 41-й день ещё закрыта', 'AI в конкретном бизнес-процессе' in cl, True)
eq('на 60-й день уже открыта', 'Обучение и навыки' in cl, False)
eq('окно ровно шесть недель', posts.MEMORY_WEEKS * 7, 42)

posts.set_metrics(con, p1, reach_followers=4200, reach_nonfollowers=18700,
                  retention=0.41, dropoff_sec=7.5, saves=310, follows=96)
m = con.execute('SELECT * FROM our_metrics WHERE post_id=?', (p1,)).fetchone()
eq('шесть чисел записаны', sum(m[k] is not None for k, _ in posts.FIELDS), 6)
eq('охват по неподписчикам', m['reach_nonfollowers'], 18700)

posts.set_metrics(con, p1, saves=350)                  # правка одного поля
m = con.execute('SELECT * FROM our_metrics WHERE post_id=?', (p1,)).fetchone()
eq('правка одного поля', m['saves'], 350)
eq('остальные не затёрлись', m['reach_followers'], 4200)
eq('строка метрик одна на ролик',
   con.execute('SELECT COUNT(*) FROM our_metrics WHERE post_id=?', (p1,)).fetchone()[0], 1)

try:
    posts.add(con, '08.09.2026', 'x', 'y'); ok = False
except ValueError:
    ok = True
eq('кривая дата не проходит', ok, True)
try:
    posts.set_metrics(con, 999, saves=1); ok = False
except SystemExit:
    ok = True
eq('метрики к несуществующему ролику не пишутся', ok, True)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
