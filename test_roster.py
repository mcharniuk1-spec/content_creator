"""Проверка выбраковки: два промаха подряд — выбыл, один — ждёт. И что повторный
запуск на том же снимке ничего не меняет. Второй снимок имитируем на копии базы.
"""
import datetime, os, shutil, sys, time
import roster
from db import connect, DB_PATH

TMP = DB_PATH.replace('.db', '.test.db')
shutil.copy(DB_PATH, TMP)
con = connect(TMP)
fail = []

def eq(name, got, want):
    print(f"  {'✓' if got == want else '✗'} {name:<52} {got}   ожидалось {want}")
    if got != want: fail.append(name)

n = lambda s: con.execute(s).fetchone()[0]

# первая проверка уже прошла на рабочей базе — переигрываем её здесь с нуля
con.execute('UPDATE accounts SET misses=0, checked_snapshot=NULL, status=?, dropped_at=NULL '
            "WHERE status IN ('active','dropped')", ('active',))
con.commit()
было = n("SELECT COUNT(*) FROM accounts WHERE status='active'")
roster.check(con)
first_miss = n("SELECT COUNT(*) FROM accounts WHERE misses=1")
eq('после первой проверки: промахи есть', first_miss > 0, True)
eq('после первой проверки: выбывших', n("SELECT COUNT(*) FROM accounts WHERE status='dropped'"), 0)

# повторный запуск на том же снимке
roster.check(con)
eq('повтор на том же снимке не добавил промахов',
   n("SELECT COUNT(*) FROM accounts WHERE misses=1"), first_miss)

# второй снимок: копируем ролики как есть, значит те же 15 снова не наберут свежих
sid1 = n('SELECT id FROM snapshots ORDER BY taken LIMIT 1')
# второй снимок через две недели: промах засчитывается не чаще раза в 12 дней,
# иначе два сбора одной недели выбивают аккаунт за три дня
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done,note) VALUES ('2026-09-15',100,0,1,'тест')")
sid2 = n("SELECT id FROM snapshots WHERE taken='2026-09-15'")
cols = [d[0] for d in con.execute('SELECT * FROM reels LIMIT 1').description]
put = ','.join(cols)
for r in con.execute('SELECT * FROM reels WHERE snapshot_id=?', (sid1,)).fetchall():
    d = dict(r); d['snapshot_id'] = sid2
    con.execute(f"INSERT INTO reels ({put}) VALUES ({','.join('?' * len(cols))})",
                [d[c] for c in cols])
con.commit()
roster.check(con)
eq('после второй проверки: выбыли все, кто промахнулся дважды',
   n("SELECT COUNT(*) FROM accounts WHERE status='dropped'"), first_miss)
eq('у выбывших проставлена дата',
   n("SELECT COUNT(*) FROM accounts WHERE status='dropped' AND dropped_at IS NULL"), 0)
eq('выбывшие не удалены из базы', n("SELECT COUNT(*) FROM accounts WHERE status='dropped'") > 0, True)
eq('активных осталось', n("SELECT COUNT(*) FROM accounts WHERE status='active'"), было - first_miss)

# аккаунт, которого нет в снимке, не штрафуется
pk = n("SELECT pk FROM accounts WHERE status='active' AND misses=0 LIMIT 1")
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done,note) VALUES ('2026-09-30',100,0,1,'тест')")
sid3 = n("SELECT id FROM snapshots WHERE taken='2026-09-30'")
for r in con.execute('SELECT * FROM reels WHERE snapshot_id=? AND pk_user<>?', (sid1, pk)).fetchall():
    d = dict(r); d['snapshot_id'] = sid3
    con.execute(f"INSERT INTO reels ({put}) VALUES ({','.join('?' * len(cols))})",
                [d[c] for c in cols])
con.commit()
before = n(f"SELECT misses FROM accounts WHERE pk={pk}")
roster.check(con)
eq('аккаунт вне снимка не получил промах', n(f"SELECT misses FROM accounts WHERE pk={pk}"), before)

# а тот, кто в сборе молчал, промах получает
pk2 = n("SELECT pk FROM accounts WHERE status='active' AND misses=0 LIMIT 1")
u2 = con.execute(f"SELECT username FROM accounts WHERE pk={pk2}").fetchone()[0]
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done,note) VALUES ('2026-10-20',100,0,1,'тест')")
sid4 = n("SELECT id FROM snapshots WHERE taken='2026-10-20'")
for row in con.execute('SELECT * FROM reels WHERE snapshot_id=? AND pk_user<>?', (sid1, pk2)).fetchall():
    d = dict(row); d['snapshot_id'] = sid4
    con.execute(f"INSERT INTO reels ({put}) VALUES ({','.join('?' * len(cols))})", [d[c] for c in cols])
con.commit()
b2 = n(f"SELECT misses FROM accounts WHERE pk={pk2}")
roster.check(con, silent_accounts={u2})
eq('молчавший на сборе аккаунт промах получил', n(f"SELECT misses FROM accounts WHERE pk={pk2}"), b2 + 1)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
