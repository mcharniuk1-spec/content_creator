"""Сбор в базу на заглушке: снимок, ролики, расход. Чистая база."""
import datetime, os, sys, types
import collect_snapshot
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.collect-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP); fail = []
def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<50} {g}   ожидалось {w}")
    if g != w: fail.append(n)
q = lambda s, *a: con.execute(s, a).fetchone()[0]

for pk, u in ((1, 'alpha'), (2, 'beta'), (3, 'gone')):
    con.execute("INSERT INTO accounts (pk,username,tag,status,follower_count) "
                "VALUES (?,?,'core','active',10000)", (pk, u))
con.execute("INSERT INTO accounts (pk,username,status) VALUES (9,'dropped_one','dropped')")
con.commit()

hiker = types.ModuleType('hiker'); hiker._units = 0
hiker._cache_dir = None
def clips(pk, pages=1):
    hiker._units += 1
    if pk == 3:
        return []                       # аккаунт не отдал ленту
    return [{'code': f'CODE{pk}_{i:02d}', 'taken_at': 1788000000 + i, 'play': 1000 * (i + 1),
             'like_count': 10, 'comment_count': 2, 'reshare_count': 3,
             'save_count': None if i else 7, 'video_duration': 55.0,
             'product_type': 'clips', 'caption': {'text': f'cap {pk} {i}'}} for i in range(12)]
hiker.clips = clips
hiker.row = lambda m, **e: dict(
    code=m['code'], ts=m['taken_at'], kind=m.get('product_type'), play=m.get('play_count') or m['play'],
    like=m['like_count'], comm=m['comment_count'], resh=m['reshare_count'],
    save=m['save_count'], dur=m['video_duration'], cap=m['caption']['text'], **e)
sys.modules['hiker'] = hiker

sid, n, miss = collect_snapshot.run(con, today=datetime.date(2026, 9, 4))
eq('снимок создан', q("SELECT COUNT(*) FROM snapshots WHERE taken='2026-09-04'"), 1)
eq('роликов записано', n, 24)
eq('выбывший аккаунт не собирался', q("SELECT COUNT(*) FROM reels WHERE pk_user=9"), 0)
eq('аккаунт без ленты отмечен', miss, ['gone'])
eq('единиц по числу активных', hiker._units, 3)
eq('расход записан', q("SELECT units FROM spend WHERE item='сбор роликов'"), 3)
eq('в снимке проставлено число роликов', q("SELECT reels_n FROM snapshots WHERE id=?", sid), 24)
# в заглушке save заполнен только у первого ролика каждого аккаунта — остальные NULL
eq('save=None сохранён как NULL, а не ноль',
   q("SELECT COUNT(*) FROM reels WHERE save IS NULL"), 22)
eq('подпись сохранена', q("SELECT cap FROM reels WHERE code='CODE1_00'"), 'cap 1 0')
eq('расход одной строкой на день', q("SELECT COUNT(*) FROM spend WHERE item='сбор роликов'"), 1)

# повторный сбор в тот же день не плодит ни снимков, ни расхода
before_units = q("SELECT SUM(units) FROM spend")
collect_snapshot.run(con, today=datetime.date(2026, 9, 4))
eq('повторный сбор не создал второй снимок', q("SELECT COUNT(*) FROM snapshots"), 1)
eq('ролики не задвоились', q("SELECT COUNT(*) FROM reels"), 24)
eq('расход посчитан разницей, а не абсолютом',
   q("SELECT SUM(units) FROM spend"), before_units + 3)
eq('кривые коды не попадают в базу',
   q("SELECT COUNT(*) FROM reels WHERE LENGTH(code) < 5"), 0)
eq('снимок помечен завершённым', q("SELECT done FROM snapshots WHERE taken='2026-09-04'"), 1)

# второй день — отдельный снимок, история копится
collect_snapshot.run(con, today=datetime.date(2026, 9, 8))
eq('второй день — новый снимок', q("SELECT COUNT(*) FROM snapshots"), 2)
eq('история копится', q("SELECT COUNT(*) FROM reels"), 48)
import baseline
base, snaps = baseline.by_author(con)
eq('в базе сравнения ролик один раз, а не дважды', len(base[1]), 12)
eq('база собрана по двум снимкам', snaps[1], 2)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
