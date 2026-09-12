"""Проверка, что база сравнения действительно копит историю.

База синтетическая (db.SCHEMA на временном файле), а не копия рабочей: тест раньше
требовал автора ровно с 24 роликами в первом снимке живой базы, и это переставало
быть правдой при первом же новом сборе. Здесь автор с 24 роликами — часть фикстуры,
а не факт о продакшене.

Второй снимок имитируем поверх него: часть роликов та же (с подросшими просмотрами),
часть — новые. Проверяем три вещи: повторный ролик не удваивается · берётся свежий
замер · база автора растёт.
"""
import os, sys
import baseline
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.baseline-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP)
fail = []

def eq(name, got, want):
    print(f"  {'✓' if got == want else '✗'} {name:<48} {got}   ожидалось {want}")
    if got != want: fail.append(name)

con.execute("INSERT INTO accounts (pk,username,status) VALUES (1,'author',  'active')")
con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,units,done) VALUES ('2026-08-01',1,24,24,1)")
sid1 = con.execute("SELECT id FROM snapshots WHERE taken='2026-08-01'").fetchone()[0]

cols = ['snapshot_id', 'code', 'pk_user', 'username', 'ts', 'kind', 'play', 'likes',
        'comm', 'resh', 'save', 'dur', 'cap', 'followers']
put = ','.join(cols)
ph = ','.join('?' * len(cols))
# ровно 24 ролика автора в первом снимке — фикстура, а не совпадение в живой базе
for i in range(24):
    con.execute(f'INSERT INTO reels ({put}) VALUES ({ph})',
                (sid1, f'OLD{i:02d}A', 1, 'author', 1_700_000_000 + i, 'reel',
                 1000 + i, 50, 5, 10, 8, 40.0, 'cap', 5000))
con.commit()

was = len(baseline.by_author(con)[0][1])
eq('роликов автора в первом снимке', was, 24)

con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,note) VALUES ('2026-09-04',1,0,'тест')")
sid2 = con.execute("SELECT id FROM snapshots WHERE taken='2026-09-04'").fetchone()[0]
# 20 прежних роликов автора с подросшими просмотрами + 3 новых
old = con.execute('SELECT * FROM reels WHERE pk_user=1 AND snapshot_id=? LIMIT 20', (sid1,)).fetchall()
for r in old:
    d = dict(r); d['snapshot_id'] = sid2; d['play'] = int(d['play'] * 1.5)
    con.execute(f"INSERT INTO reels ({put}) VALUES ({ph})", [d[c] for c in cols])
for i in range(3):
    d = dict(old[0]); d['snapshot_id'] = sid2; d['code'] = f'TESTNEW{i}'; d['play'] = 10_000 + i
    con.execute(f"INSERT INTO reels ({put}) VALUES ({ph})", [d[c] for c in cols])
con.commit()

base, snaps = baseline.by_author(con)
now = base[1]
eq('роликов автора в базе сравнения', len(now), was + 3)
eq('повторный ролик учтён один раз', len({r['code'] for r in now}), len(now))
grown = con.execute('SELECT play FROM reels WHERE snapshot_id=? AND code=?', (sid1, old[0]['code'])).fetchone()[0]
eq('взят свежий замер, а не первый',
   [r['play'] for r in now if r['code'] == old[0]['code']][0], int(grown * 1.5))
eq('снимков в базе автора', snaps[1], 2)
eq('оцениваем только новый снимок', len(baseline.snapshot_rows(con, sid2)), 23)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
