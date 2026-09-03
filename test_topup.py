"""Добор на заглушках вместо API: ищем опечатки заранее, а не за деньги.

Две стадии проверяются раздельно, как они и работают: `topup` — платная, только поиск
и соседи, пишет кандидатов сразу; `profiles` — бесплатная, добирает профили и отсеивает
по порогам. Разделены потому, что бесплатный источник профилей рейт-лимитится, и обрыв
на нём не должен стоить повторного поиска.

База берётся пустая: тест проверяет поведение, а не содержимое рабочей.
"""
import os, sys, types
import roster
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.topup-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP)
fail = []
def eq(name, got, want):
    print(f"  {'✓' if got == want else '✗'} {name:<50} {got}   ожидалось {want}")
    if got != want: fail.append(name)
n = lambda s: con.execute(s).fetchone()[0]

# минимальный набор: один живой аккаунт, чтобы было от кого брать соседей
con.execute("INSERT INTO accounts (pk,username,tag,status) VALUES (1,'seed','core','active')")
con.execute("INSERT INTO snapshots (taken) VALUES ('2026-09-01')")
sid = n("SELECT id FROM snapshots")
con.execute("INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play) VALUES (?,'C1',1,'seed',1,100)", (sid,))
con.execute("INSERT INTO scores (snapshot_id,code,z,eligible) VALUES (?,'C1',1.0,1)", (sid,))
con.commit()

CAND = {9000001: ('good_one', 40_000, False), 9000002: ('good_two', 12_000, False),
        9000003: ('too_small', 900, False),   9000004: ('too_big', 3_000_000, False),
        9000005: ('locked', 50_000, True),    9000006: ('from_neighbor', 80_000, False)}

hiker = types.ModuleType('hiker'); hiker._units = 0
def call(path, use_cache=True, **kw):
    assert use_cache is False, 'добор обязан ходить мимо кэша'
    hiker._units += 1
    if 'fbsearch' in path:
        users = [{'pk': pk, 'username': u} for pk, (u, _, _) in list(CAND.items())[:5]]
        users.append({'pk': 1, 'username': 'seed'})          # уже в базе — отсеется
        return {'reels_serp_modules': [{'clips': [{'media': {'user': u}} for u in users]}]}
    return {'users': [{'pk': 9000006, 'username': 'from_neighbor'}]}
hiker.call = call
sys.modules['hiker'] = hiker

fp = types.ModuleType('freeprofile')
by_name = {u: (pk, f, p) for pk, (u, f, p) in CAND.items()}
fp.profile = lambda u, **k: (None if u not in by_name else
    {'pk': by_name[u][0], 'username': u, 'full_name': u, 'follower_count': by_name[u][1],
     'media_count': 10, 'biography': f'bio {u}', 'category': None,
     'is_verified': False, 'is_private': by_name[u][2]})
sys.modules['freeprofile'] = fp

roster.topup(con, run=True)
eq('платная стадия записала всех найденных', n('SELECT COUNT(*) FROM accounts') - 1, 6)
eq('известный аккаунт не задвоился', n('SELECT COUNT(*) FROM accounts WHERE pk=1'), 1)
eq('источник кандидата сохранён', n('SELECT COUNT(*) FROM accounts WHERE via IS NOT NULL'), 6)
eq('расход записан строкой', n("SELECT COUNT(*) FROM spend WHERE item='добор: поиск и соседи'"), 1)
eq('единицы совпали с потраченными',
   n("SELECT units FROM spend WHERE item='добор: поиск и соседи'"), hiker._units)
eq('до профилей порогов ещё нет', n("SELECT COUNT(*) FROM accounts WHERE status='rejected'"), 0)

roster.profiles(con)
eq('прошли пороги', n("SELECT COUNT(*) FROM accounts WHERE status='candidate'"), 3)
eq('отсеяны, но не удалены', n("SELECT COUNT(*) FROM accounts WHERE status='rejected'"), 3)
eq('у отсеянных записана причина',
   n("SELECT COUNT(*) FROM accounts WHERE status='rejected' AND why_out IS NOT NULL"), 3)
eq('мелкий отсеян', n("SELECT why_out FROM accounts WHERE username='too_small'"), 'мало подписчиков')
eq('крупный отсеян', n("SELECT why_out FROM accounts WHERE username='too_big'"), 'много подписчиков')
eq('приватный отсеян', n("SELECT why_out FROM accounts WHERE username='locked'"), 'приватный')
eq('сосед прошёл', n("SELECT COUNT(*) FROM accounts WHERE username='from_neighbor' AND status='candidate'"), 1)
eq('tag машиной не проставлен', n("SELECT COUNT(*) FROM accounts WHERE status='candidate' AND tag IS NOT NULL"), 0)
eq('файл на разметку собран', open('data/candidates.md', encoding='utf-8').read().count('- [ ]'), 3)

# источник замолчал: пять пустых подряд — остановка, кандидаты остаются ждать
con.execute("UPDATE accounts SET follower_count=NULL, status='candidate' WHERE pk>1")
con.commit()
fp.profile = lambda u, **k: None
roster.profiles(con)
eq('после отказа источника кандидаты не потеряны',
   n("SELECT COUNT(*) FROM accounts WHERE status='candidate' AND follower_count IS NULL"), 6)

con.close(); os.remove(TMP); os.remove('data/candidates.md')
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
