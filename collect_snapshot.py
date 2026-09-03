#!/usr/bin/env python3
"""Сбор роликов по набору → снимок в базе. SPEC §4.2.

    python3 collect_snapshot.py           смета: сколько аккаунтов, единиц и денег
    python3 collect_snapshot.py --yes     собрать

Одна страница на аккаунт — 12 роликов. Столько за неделю никто не публикует, запас
трёхкратный. Каждый сбор пишется отдельным снимком: снимки не перезаписывают друг друга,
из них и складывается история, по которой считается норма автора.

Ссылки на видео живут часы, поэтому сразу после сбора должен идти разбор — этот порядок
зашит в run.py, руками цепочку лучше не собирать.
"""
import datetime, os, pathlib, sys
from db import connect, safe_code

PAGES = 1
PRICE = 0.02


def balance():
    """Остаток оплаченных единиц. Ноль запросов не стоит, но знать его надо до старта."""
    sys.path.insert(0, str(pathlib.Path(__file__).parent / 'lib'))
    sys.path.append(str(pathlib.Path.home() / '.claude' / 'skills' / 'hikerapi' / 'scripts'))
    os.environ.setdefault('HIKER_CACHE', str(pathlib.Path(__file__).parent / 'cache'))
    try:
        import hiker
        return (hiker.balance() or {}).get('requests')
    except Exception:
        return None


def plan(con, check_balance=True):
    n = con.execute("SELECT COUNT(*) FROM accounts WHERE status='active'").fetchone()[0]
    units = n * PAGES
    print(f'аккаунтов в наборе {n}, по {PAGES} странице = {units} ед. = ${units * PRICE:.2f}')
    if check_balance:
        left = balance()
        if left is not None:
            print(f'на счету {left} ед. = ${left * PRICE:.2f}'
                  + ('' if left >= units else '  — НЕ ХВАТИТ на этот прогон'))
            if left < units:
                return n, units, False
    return n, units, True


def run(con, today=None):
    sys.path.insert(0, str(pathlib.Path(__file__).parent / 'lib'))
    sys.path.append(str(pathlib.Path.home() / '.claude' / 'skills' / 'hikerapi' / 'scripts'))
    os.environ.setdefault('HIKER_CACHE', str(pathlib.Path(__file__).parent / 'cache'))
    import hiker
    today = (today or datetime.date.today()).isoformat()
    # Кэш режется по дате снимка. Иначе ключом остаётся только адрес запроса,
    # и следующий сбор молча вернёт ленты прошлой недели: 100 из 109 аккаунтов
    # уже лежали в общем кэше, и снимок №2 оказался бы копией первого.
    hiker._cache_dir = pathlib.Path(__file__).parent / 'cache' / today
    hiker._cache_dir.mkdir(parents=True, exist_ok=True)
    accounts = con.execute("""SELECT pk, username, follower_count, tag FROM accounts
                              WHERE status='active' ORDER BY username""").fetchall()
    con.execute("""INSERT INTO snapshots (taken,accounts_n,reels_n,note) VALUES (?,?,0,'сбор')
                   ON CONFLICT(taken) DO UPDATE SET accounts_n=excluded.accounts_n""",
                (today, len(accounts)))
    sid = con.execute('SELECT id FROM snapshots WHERE taken=?', (today,)).fetchone()[0]

    u0 = hiker._units          # счётчик накопительный за процесс: пишем разницу, не абсолют
    total, miss, bad = 0, [], []
    try:
        for i, a in enumerate(accounts, 1):
            raw = hiker.clips(a['pk'], pages=PAGES)
            if not raw:
                miss.append(a['username']); continue
            for m in raw:
                r = hiker.row(m)
                if not safe_code(r.get('code')):      # кривой код дальше не идёт никуда
                    bad.append(r.get('code'))
                    continue
                con.execute("""INSERT OR REPLACE INTO reels
                    (snapshot_id,code,pk_user,username,ts,kind,play,likes,comm,resh,save,dur,cap,followers)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid, r['code'], a['pk'], a['username'], r['ts'], r['kind'], r['play'],
                     r['like'], r['comm'], r['resh'], r['save'], r['dur'], r['cap'],
                     a['follower_count']))
                total += 1
            if i % 25 == 0:
                con.commit()
                print(f'  {i}/{len(accounts)} аккаунтов, роликов {total}, '
                      f'единиц {hiker._units - u0}', flush=True)
        con.execute('UPDATE snapshots SET done=1 WHERE id=?', (sid,))
    finally:
        spent = hiker._units - u0
        n = con.execute('SELECT COUNT(*) FROM reels WHERE snapshot_id=?', (sid,)).fetchone()[0]
        con.execute('UPDATE snapshots SET reels_n=?, units=? WHERE id=?', (n, spent, sid))
        if spent:
            con.execute("""INSERT INTO spend (at,item,units,price,usd,note)
                VALUES (?,?,?,?,?,?)""",
                (today, 'сбор роликов', spent, PRICE, round(spent * PRICE, 2),
                 f'снимок {today}, аккаунтов {len(accounts)}'))
        con.commit()
    print(f'\nснимок {today}: аккаунтов {len(accounts)}, роликов {n}')
    print(f'потрачено {hiker._units - u0} ед. = ${(hiker._units - u0) * PRICE:.2f}')
    if bad:
        print(f'отброшено кодов неверного формата: {len(bad)}')
    if miss:
        print(f'не отдали ленту: {len(miss)} — {", ".join(miss[:8])}'
              + ('…' if len(miss) > 8 else ''))
    return sid, n, miss


if __name__ == '__main__':
    con = connect()
    plan(con)
    if '--yes' not in sys.argv:
        print('\nэто смета. Сбор: python3 collect_snapshot.py --yes')
        print('Но лучше не отдельно, а целиком: python3 run.py --yes — тогда разбор пойдёт '
              'сразу за сбором, пока ссылки живы')
    else:
        run(con)
