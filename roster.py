#!/usr/bin/env python3
"""Набор аккаунтов: проверка живости, выбраковка, добор новых. SPEC §4.1.

    python3 roster.py check          живость по последнему снимку — бесплатно
    python3 roster.py followers      обновить подписчиков набора — бесплатно
    python3 roster.py plan           смета добора: сколько единиц и сколько денег
    python3 roster.py topup --yes    прогон добора; без --yes печатает смету и выходит

Проверка живости не стоит ничего: всё нужное уже лежит в снимках. Платит только добор.
"""
import datetime, json, os, pathlib, sys, time

from db import connect

D = pathlib.Path(__file__).parent / 'data'
ALIVE_REELS = 3           # роликов за окно, чтобы считаться живым
ALIVE_DAYS = 30
MISS_LIMIT = 2            # проваленных проверок подряд до выбраковки
MISS_GAP_DAYS = 12        # между промахами: снимков два в неделю, и без этого зазора
                          # «две проверки подряд» превращались в три дня вместо месяца
MIN_FOLLOWERS, MAX_FOLLOWERS = 5_000, 1_000_000
TARGET = 250              # целевой размер набора, SPEC §4.1
PRICE = 0.02              # тариф Start; на Standard в двадцать раз меньше


# ---------------------------------------------------------------- живость ----
def check(con, apply=True, silent_accounts=()):
    """silent_accounts — те, кто на сборе не отдал ленту вовсе. Их молчание — это
    не «сбор не покрыл», а сигнал, и промах им ставится."""
    snap = con.execute('SELECT id, taken FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()
    if not snap:
        print('снимков нет'); return
    sid, taken = snap['id'], snap['taken']
    edge = int(time.mktime(datetime.date.fromisoformat(taken).timetuple())) - ALIVE_DAYS * 86400

    rows = con.execute("""
        SELECT a.pk, a.username, a.misses, a.checked_snapshot, a.last_checked,
               COUNT(r.code) total,
               SUM(CASE WHEN r.ts >= ? THEN 1 ELSE 0 END) recent
        FROM accounts a LEFT JOIN reels r ON r.pk_user = a.pk AND r.snapshot_id = ?
        WHERE a.status = 'active' GROUP BY a.pk""", (edge, sid)).fetchall()

    alive = dead = skipped = dropped = 0
    already = sum(1 for r in rows if r['checked_snapshot'] == sid)
    for r in rows:
        if r['checked_snapshot'] == sid:        # этот снимок уже считали
            continue
        if not r['total'] and r['username'] not in silent_accounts:
            skipped += 1                        # сбор его не покрыл — штрафовать не за что
            continue
        if (r['recent'] or 0) >= ALIVE_REELS:
            alive += 1
            if apply:
                con.execute("""UPDATE accounts SET misses=0, last_checked=?, checked_snapshot=?
                               WHERE pk=?""", (taken, sid, r['pk']))
        else:
            # второй промах засчитывается, только если с первого прошло больше недели:
            # иначе два сбора одной недели выбивают аккаунт за три дня
            gap_ok = (not r['last_checked'] or not r['misses'] or
                      (datetime.date.fromisoformat(taken)
                       - datetime.date.fromisoformat(r['last_checked'])).days >= MISS_GAP_DAYS)
            dead += 1
            m = (r['misses'] or 0) + (1 if gap_ok else 0)
            out = m >= MISS_LIMIT
            dropped += out
            if apply:
                con.execute("""UPDATE accounts SET misses=?, last_checked=?, checked_snapshot=?,
                               status=?, dropped_at=? WHERE pk=?""",
                            (m, taken, sid, 'dropped' if out else 'active',
                             taken if out else None, r['pk']))
    if apply:
        con.commit()
    n = con.execute("SELECT COUNT(*) FROM accounts WHERE status='active'").fetchone()[0]
    print(f'снимок {taken}')
    print(f'  живых                {alive}')
    print(f'  не набрали {ALIVE_REELS} ролика за {ALIVE_DAYS} дней   {dead}'
          + (f'   → выбыло {dropped}' if dropped else '   (первый промах, ждут второго)'))
    if skipped:
        print(f'  пропущено            {skipped}   нет в снимке, сбор не покрыл')
    if already:
        print(f'  уже проверены        {already}   на этом же снимке')
    print(f'\nв наборе активных: {n}, до цели {TARGET} не хватает {max(0, TARGET - n)}')
    return n


# ------------------------------------------------------------------ добор ----
def plan(con, verbose=True):
    from queries import ALL
    active = con.execute("SELECT COUNT(*) FROM accounts WHERE status='active'").fetchone()[0]
    need = max(0, TARGET - active)
    seeds = min(20, active)                     # сидов для «похожих аккаунтов»
    units = {'поиск по запросам': len(ALL),
             'похожие аккаунты от сидов': seeds,
             'ролики новых аккаунтов, 1 страница': need}
    tot = sum(units.values())
    if verbose:
        print(f'в наборе {active}, цель {TARGET}, добираем до {need}\n')
        for k, v in units.items():
            print(f'  {k:<40} {v:>4} ед.  ${v * PRICE:>6.2f}')
        print(f'  {"итого":<40} {tot:>4} ед.  ${tot * PRICE:>6.2f}')
        print('\nпрофили кандидатов берутся бесплатно через публичный веб-API — единиц не тратят')
    return tot, need, seeds


def _search(hiker, q, cached=False):
    """Поиск мимо кэша: в доборе нужны те, кто получает охват сейчас, а не в прошлый раз.
    cached=True — перечитать уже оплаченный ответ из кэша, не тратя единиц."""
    d = hiker.call('/v2/fbsearch/reels', use_cache=cached, query=q)
    out = []
    for mod in (d or {}).get('reels_serp_modules', []):
        for c in mod.get('clips', []):
            u = ((c.get('media') or {}).get('user')) or {}
            if u.get('pk'):
                out.append({'pk_user': u['pk'], 'user': u.get('username')})
    return out


def _suggested(hiker, pk, cached=False):
    d = hiker.call('/v2/user/suggested/profiles', use_cache=cached, user_id=pk)
    return (d or {}).get('users') or (d or {}).get('items') or []


def topup(con, run=False, cached=False):
    tot, need, seeds = plan(con)
    if not run:
        print(f'\nэто смета. Прогон: python3 roster.py topup --yes')
        return
    sys.path.insert(0, str(pathlib.Path(__file__).parent / 'lib'))
    sys.path.append(str(pathlib.Path.home() / '.claude' / 'skills' / 'hikerapi' / 'scripts'))
    os.environ.setdefault('HIKER_CACHE', str(pathlib.Path(__file__).parent / 'cache'))
    import hiker
    from queries import ALL, RU
    import freeprofile

    known = {int(r[0]) for r in con.execute('SELECT pk FROM accounts')}
    found = {}

    print('\nпоиск по запросам')
    for i, q in enumerate(ALL, 1):
        for r in _search(hiker, q, cached):
            pk = r.get('pk_user')
            if pk and int(pk) not in known:
                found.setdefault(int(pk), {'username': r.get('user'), 'via': f'поиск: {q}'})
        print(f'  {i:2}/{len(ALL)}  {q[:40]:42} новых всего {len(found)}', flush=True)

    print('\nпохожие аккаунты от сидов')
    seed_rows = con.execute("""SELECT a.pk, a.username FROM accounts a
        JOIN reels r ON r.pk_user=a.pk JOIN scores s ON s.code=r.code
        WHERE a.status='active' AND a.tag='core'
        GROUP BY a.pk ORDER BY AVG(s.z) DESC LIMIT ?""", (seeds,)).fetchall()
    for i, s in enumerate(seed_rows, 1):
        for u in _suggested(hiker, s['pk'], cached):
            pk = u.get('pk') or u.get('id')
            if pk and int(pk) not in known:
                found.setdefault(int(pk), {'username': u.get('username'),
                                           'via': f'сосед: {s["username"]}'})
        print(f'  {i:2}/{len(seed_rows)}  {s["username"][:28]:30} новых всего {len(found)}', flush=True)

    today = datetime.date.today().isoformat()
    for pk, v in found.items():
        con.execute("""INSERT OR IGNORE INTO accounts
            (pk,username,tag,status,added_at,via) VALUES (?,?,NULL,'candidate',?,?)""",
            (pk, v.get('username'), today, v.get('via')))
    if not cached:
        con.execute('INSERT INTO spend (at,item,units,price,usd,note) VALUES (?,?,?,?,?,?)',
                    (today, 'добор: поиск и соседи', hiker._units, PRICE,
                     round(hiker._units * PRICE, 2), f'найдено {len(found)}'))
    con.commit()
    print(f'\nновых кандидатов записано: {len(found)}')
    print(f'потрачено: {hiker._units} ед. = ${hiker._units * PRICE:.2f}'
          + ('  (из кэша, деньги не списаны)' if cached else ''))
    print('дальше профили — бесплатно: python3 roster.py profiles')


def refresh_followers(con, limit=None):
    """Подписчики активных аккаунтов. Бесплатно, но без этого число заморожено
    на дате первого запроса и вопрос «кто растёт» остаётся без ответа навсегда."""
    import freeprofile
    rows = con.execute("""SELECT pk, username, follower_count FROM accounts
        WHERE status='active' ORDER BY COALESCE(last_checked,'') LIMIT ?""",
        (int(limit or 10**6),)).fetchall()
    today = datetime.date.today().isoformat()
    got, grown, blocked = 0, 0, 0
    for a in rows:
        p = freeprofile.profile(a['username'], fresh=True)
        if not p:
            blocked += 1
            if blocked >= 5:
                print(f'  источник молчит пять раз подряд — остановились на {got}')
                break
            continue
        blocked = 0
        before = a['follower_count'] or 0
        after = p.get('follower_count') or 0
        con.execute("""INSERT INTO followers (pk,at,follower_count) VALUES (?,?,?)
                       ON CONFLICT(pk,at) DO UPDATE SET follower_count=excluded.follower_count""",
                    (a['pk'], today, after))
        con.execute('UPDATE accounts SET follower_count=?, last_checked=? WHERE pk=?',
                    (after, today, a['pk']))
        got += 1
        grown += after > before
    con.commit()
    print(f'обновлено профилей: {got} из {len(rows)}, выросли у {grown}')
    return got


def profiles(con, limit=None):
    """Профили кандидатов через публичный веб-API. Единиц не тратит.

    Источник анонимный и рейт-лимитится: на 401 останавливаемся и предлагаем вернуться
    позже — недобранные кандидаты остаются в базе и ждут следующего захода.
    """
    import freeprofile
    rows = con.execute("""SELECT pk, username FROM accounts
        WHERE status='candidate' AND follower_count IS NULL AND username IS NOT NULL
        ORDER BY pk""").fetchall()
    if limit:
        rows = rows[:int(limit)]
    print(f'кандидатов без профиля: {len(rows)}')
    got, rej, blocked = 0, {}, 0
    for i, a in enumerate(rows, 1):
        p = freeprofile.profile(a['username'])
        if not p:
            blocked += 1
            if blocked >= 5:
                print(f'  источник не отвечает пять раз подряд — останавливаемся на {i-1}')
                break
            continue
        blocked = 0
        if int(p['pk']) != int(a['pk']):
            # имя занято другим аккаунтом: обновлять по нему чужую строку нельзя,
            # а оставлять кандидата без профиля значит вешать добор на нём навсегда
            con.execute("""UPDATE accounts SET status='rejected', why_out='сменил имя',
                           follower_count=0 WHERE pk=?""", (a['pk'],))
            rej['сменил имя'] = rej.get('сменил имя', 0) + 1
            got += 1
            continue
        f = p.get('follower_count') or 0
        why = ('приватный' if p.get('is_private') else
               'мало подписчиков' if f < MIN_FOLLOWERS else
               'много подписчиков' if f > MAX_FOLLOWERS else None)
        con.execute("""UPDATE accounts SET full_name=?, follower_count=?, media_count=?,
            biography=?, category=?, is_verified=?, is_private=?, status=?, why_out=?
            WHERE pk=?""",
            (p.get('full_name'), f, p.get('media_count'), p.get('biography'),
             p.get('category'), int(bool(p.get('is_verified'))), int(bool(p.get('is_private'))),
             'rejected' if why else 'candidate', why, int(a['pk'])))
        got += 1
        if why:
            rej[why] = rej.get(why, 0) + 1
        if i % 50 == 0:
            con.commit(); print(f'  {i}/{len(rows)}', flush=True)
    con.commit()
    keep = con.execute("""SELECT username, follower_count, biography, via FROM accounts
        WHERE status='candidate' AND follower_count IS NOT NULL ORDER BY follower_count DESC""").fetchall()
    if keep:
        (D / 'candidates.md').write_text(
            f'# Кандидаты на добор, {datetime.date.today().isoformat()}\n\n'
            f'Отметь: **core** — берём, **out** — не берём. Тема, не число подписчиков.\n\n'
            + '\n'.join(f'- [ ] **{k["username"]}** · {k["follower_count"]:,} подписчиков · {k["via"] or ""}\n'
                        f'      {(k["biography"] or "").strip()[:180]}' for k in keep),
            encoding='utf-8')
    print(f'\nпрофилей получено: {got} из {len(rows)}')
    for k, v in rej.items():
        print(f'  отсеяно, {k}: {v}')
    print(f'прошли пороги и ждут разметки: {len(keep)}')
    if got < len(rows):
        print(f'осталось на следующий заход: {len(rows) - got} — источник анонимный '
              f'и рейт-лимитится, вернуться через час')
    if keep:
        print('список на разметку: data/candidates.md — тема решается руками, не формулой')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    con = connect()
    if cmd == 'check':
        check(con)
    elif cmd == 'plan':
        plan(con)
    elif cmd == 'topup':
        topup(con, run='--yes' in sys.argv, cached='--cached' in sys.argv)
    elif cmd == 'profiles':
        profiles(con, limit=sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == 'followers':
        refresh_followers(con, limit=sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(__doc__)
