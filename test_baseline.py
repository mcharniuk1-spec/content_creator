"""Проверка, что база сравнения действительно копит историю.

Снимок пока один, поэтому второй имитируем на копии базы: часть роликов та же
(с подросшими просмотрами), часть — новые. Проверяем три вещи:
повторный ролик не удваивается · берётся свежий замер · база автора растёт.
"""
import os, shutil, sqlite3, sys
import baseline
from db import connect, DB_PATH

TMP = DB_PATH.replace('.db', '.test.db')
shutil.copy(DB_PATH, TMP)
con = connect(TMP)
fail = []

def eq(name, got, want):
    print(f"  {'✓' if got == want else '✗'} {name:<48} {got}   ожидалось {want}")
    if got != want: fail.append(name)

sid1 = con.execute('SELECT id FROM snapshots').fetchone()[0]
pk = con.execute('SELECT pk_user FROM reels GROUP BY pk_user HAVING COUNT(*)=24 LIMIT 1').fetchone()[0]
was = len(baseline.by_author(con)[0][pk])

con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,note) VALUES ('2026-09-04',100,0,'тест')")
sid2 = con.execute("SELECT id FROM snapshots WHERE taken='2026-09-04'").fetchone()[0]
# 20 прежних роликов автора с подросшими просмотрами + 3 новых
old = con.execute('SELECT * FROM reels WHERE pk_user=? AND snapshot_id=? LIMIT 20', (pk, sid1)).fetchall()
cols = [d[0] for d in con.execute('SELECT * FROM reels LIMIT 1').description]
for r in old:
    d = dict(r); d['snapshot_id'] = sid2; d['play'] = int(d['play'] * 1.5)
    con.execute(f"INSERT INTO reels ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [d[c] for c in cols])
for i in range(3):
    d = dict(old[0]); d['snapshot_id'] = sid2; d['code'] = f'TESTNEW{i}'; d['play'] = 10_000 + i
    con.execute(f"INSERT INTO reels ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [d[c] for c in cols])
con.commit()

base, snaps = baseline.by_author(con)
now = base[pk]
eq('роликов автора в базе сравнения', len(now), was + 3)
eq('повторный ролик учтён один раз', len({r['code'] for r in now}), len(now))
grown = con.execute('SELECT play FROM reels WHERE snapshot_id=? AND code=?', (sid1, old[0]['code'])).fetchone()[0]
eq('взят свежий замер, а не первый',
   [r['play'] for r in now if r['code'] == old[0]['code']][0], int(grown * 1.5))
eq('снимков в базе автора', snaps[pk], 2)
eq('оцениваем только новый снимок', len(baseline.snapshot_rows(con, sid2)), 23)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
