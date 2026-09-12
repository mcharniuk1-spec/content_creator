"""Проверка выбраковки: два промаха подряд — выбыл, один — ждёт. И что повторный
запуск на том же снимке ничего не меняет.

База синтетическая (db.SCHEMA на временном файле), а не копия рабочей: на живой базе
второй снимок строился сдвигом дат поверх реальных таймкодов роликов, и то, сколько
аккаунтов "промахнётся дважды", зависело от того, как реальная активность 130 аккаунтов
легла на новое окно в 30 дней — не от логики roster.check(), а от текущего состояния
продакшен-данных. Здесь пять аккаунтов с таймкодами, которые сам тест и придумал,
поэтому исход предсказан заранее, а не подогнан под то, что вышло на этот раз.
"""
import datetime, os, sys, time
import roster
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.roster-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP)
fail = []

def eq(name, got, want):
    print(f"  {'✓' if got == want else '✗'} {name:<52} {got}   ожидалось {want}")
    if got != want: fail.append(name)

n = lambda s: con.execute(s).fetchone()[0]
ts = lambda d: int(time.mktime(d.timetuple()))

# ---- набор: пятеро с известным заранее поведением -------------------------------
# alive1     — всегда набирает свежие ролики, никогда не мажет
# miss_a/b   — ни разу не набирают ролики: первый снимок — первый промах, второй — выбывает
# skip_acc   — сбор её вообще не покрывает (нет строк в reels): пропуск, не промах
# silent_acc — как alive1, но на последнем снимке "молчит" (silent_accounts)
ACCOUNTS = ['alive1', 'miss_a', 'miss_b', 'skip_acc', 'silent_acc']
for pk, u in enumerate(ACCOUNTS, 1):
    con.execute("INSERT INTO accounts (pk,username,status) VALUES (?,?,'active')", (pk, u))
con.commit()
PK = {u: i for i, u in enumerate(ACCOUNTS, 1)}


def add_reels(sid, taken_date, alive_usernames):
    """Три свежих ролика (внутри окна ALIVE_DAYS) для каждого из alive_usernames."""
    recent = ts(taken_date - datetime.timedelta(days=5))
    for u in alive_usernames:
        for i in range(3):
            con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play)
                VALUES (?,?,?,?,?,?)""", (sid, f'{u[:6]}{sid}{i}A', PK[u], u, recent, 1000))
    con.commit()


def add_stale_reel(sid, taken_date, stale_usernames):
    """Один старый ролик (за пределами окна ALIVE_DAYS) — сбор его видел, значит
    это промах, а не пропуск: разница между 'молчал' и 'не набрал' именно в этом."""
    old = ts(taken_date - datetime.timedelta(days=roster.ALIVE_DAYS + 10))
    for u in stale_usernames:
        con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play)
            VALUES (?,?,?,?,?,?)""", (sid, f'{u[:6]}{sid}OLD', PK[u], u, old, 500))
    con.commit()


было = n("SELECT COUNT(*) FROM accounts WHERE status='active'")

# ---- снимок 1: только alive1 и silent_acc набирают свежие ролики ---------------
d1 = datetime.date(2026, 1, 1)
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,5,0,1)", (d1.isoformat(),))
sid1 = n(f"SELECT id FROM snapshots WHERE taken='{d1.isoformat()}'")
add_reels(sid1, d1, ['alive1', 'silent_acc'])
add_stale_reel(sid1, d1, ['miss_a', 'miss_b'])   # видны сбору, но неактивны — промах
# skip_acc — ни одной строки в этом снимке вовсе — пропуск, не промах

roster.check(con)
first_miss = n("SELECT COUNT(*) FROM accounts WHERE misses=1")
eq('после первой проверки: промахи есть', first_miss > 0, True)
eq('после первой проверки: ровно два промаха (miss_a, miss_b)', first_miss, 2)
eq('после первой проверки: выбывших', n("SELECT COUNT(*) FROM accounts WHERE status='dropped'"), 0)
eq('skip_acc не промахнулась — сбор её не покрыл', n("SELECT misses FROM accounts WHERE pk=?" .replace('?', str(PK['skip_acc']))), 0)

# повторный запуск на том же снимке — ничего не меняет
roster.check(con)
eq('повтор на том же снимке не добавил промахов',
   n("SELECT COUNT(*) FROM accounts WHERE misses=1"), first_miss)

# ---- снимок 2, через 12 дней (MISS_GAP_DAYS): miss_a/b мажут второй раз --------
d2 = d1 + datetime.timedelta(days=roster.MISS_GAP_DAYS)
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,5,0,1)", (d2.isoformat(),))
sid2 = n(f"SELECT id FROM snapshots WHERE taken='{d2.isoformat()}'")
add_reels(sid2, d2, ['alive1', 'silent_acc'])
add_stale_reel(sid2, d2, ['miss_a', 'miss_b'])   # снова видны, снова неактивны

roster.check(con)
eq('после второй проверки: выбыли все, кто промахнулся дважды',
   n("SELECT COUNT(*) FROM accounts WHERE status='dropped'"), first_miss)
eq('у выбывших проставлена дата',
   n("SELECT COUNT(*) FROM accounts WHERE status='dropped' AND dropped_at IS NULL"), 0)
eq('выбывшие не удалены из базы', n("SELECT COUNT(*) FROM accounts WHERE status='dropped'") > 0, True)
eq('активных осталось', n("SELECT COUNT(*) FROM accounts WHERE status='active'"), было - first_miss)

# ---- снимок 3: аккаунт вне снимка не получает промах ----------------------------
d3 = d2 + datetime.timedelta(days=roster.MISS_GAP_DAYS)
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,5,0,1)", (d3.isoformat(),))
sid3 = n(f"SELECT id FROM snapshots WHERE taken='{d3.isoformat()}'")
add_reels(sid3, d3, ['silent_acc'])          # alive1 в этом снимке отсутствует вовсе
before = n(f"SELECT misses FROM accounts WHERE pk={PK['alive1']}")
roster.check(con)
eq('аккаунт вне снимка не получил промах', n(f"SELECT misses FROM accounts WHERE pk={PK['alive1']}"), before)

# ---- снимок 4: аккаунт, который на сборе "молчал", промах получает -------------
d4 = d3 + datetime.timedelta(days=roster.MISS_GAP_DAYS)
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,5,0,1)", (d4.isoformat(),))
sid4 = n(f"SELECT id FROM snapshots WHERE taken='{d4.isoformat()}'")
add_reels(sid4, d4, ['alive1'])              # silent_acc в этом снимке тоже без строк,
                                               # но передана явно как "молчавшая"
b2 = n(f"SELECT misses FROM accounts WHERE pk={PK['silent_acc']}")
roster.check(con, silent_accounts={'silent_acc'})
eq('молчавший на сборе аккаунт промах получил', n(f"SELECT misses FROM accounts WHERE pk={PK['silent_acc']}"), b2 + 1)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
