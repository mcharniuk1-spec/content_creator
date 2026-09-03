#!/usr/bin/env python3
"""Добор профилей кандидатов бесплатным источником, с ожиданием рейт-лимита.

    python3 harvest.py            работает до победы или до 14 часов
    python3 harvest.py --status   что уже собрано

Публичный веб-API Instagram отдаёт 401 после примерно 150 профилей подряд и открывается
обратно через какое-то время. Поэтому: проба одним запросом раз в 20 минут, и как только
источник отвечает — заход на 120 профилей. Денег не стоит нигде.
"""
import datetime, subprocess, sys, time
from db import connect
import roster

BATCH = 120          # за один заход, с запасом до наблюдавшегося потолка в ~150
PAUSE = 20 * 60      # между заходами и между пробами
MAX_HOURS = 14
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0 Safari/537.36')
PROBE = 'instagram'  # аккаунт для пробы, заведомо существующий


def now():
    return datetime.datetime.now().strftime('%H:%M')


def source_open():
    p = subprocess.run(
        ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '20',
         '-H', 'x-ig-app-id: 936619743392459', '-H', f'User-Agent: {UA}',
         f'https://www.instagram.com/api/v1/users/web_profile_info/?username={PROBE}'],
        capture_output=True, text=True)
    return p.stdout.strip() == '200', p.stdout.strip()


def counts(con):
    q = lambda s: con.execute(s).fetchone()[0]
    return (q("SELECT COUNT(*) FROM accounts WHERE status='candidate' AND follower_count IS NULL"),
            q("SELECT COUNT(*) FROM accounts WHERE status='candidate' AND follower_count IS NOT NULL"),
            q("SELECT COUNT(*) FROM accounts WHERE status='rejected'"),
            q("SELECT COUNT(*) FROM accounts WHERE status='active'"))


if __name__ == '__main__':
    con = connect()
    left, ready, rej, active = counts(con)
    if '--status' in sys.argv:
        print(f'без профиля {left} · с профилем {ready} · отсеяно {rej} · в наборе {active}')
        sys.exit()

    print(f'{now()}  старт. без профиля {left}, в наборе {active}, цель 250')
    started = time.time()
    probe_n = 0
    while True:
        if time.time() - started > MAX_HOURS * 3600:
            print(f'{now()}  прошло {MAX_HOURS} часов, останавливаюсь'); break
        left, ready, rej, active = counts(con)
        if not left:
            print(f'{now()}  кандидатов без профиля не осталось'); break

        probe_n += 1
        ok, code = source_open()
        if not ok:
            print(f'{now()}  проба {probe_n}: источник отвечает {code}, ждём 20 минут '
                  f'(осталось {left})', flush=True)
            time.sleep(PAUSE)
            continue

        print(f'{now()}  проба {probe_n}: источник открыт, заход на {BATCH}', flush=True)
        before = counts(con)
        roster.profiles(con, limit=BATCH)
        after = counts(con)
        got = before[0] - after[0]
        print(f'{now()}  за заход получено {got}, прошли пороги {after[1] - before[1]}, '
              f'отсеяно {after[2] - before[2]}, осталось {after[0]}', flush=True)
        if after[0] == 0:
            print(f'{now()}  всё'); break
        time.sleep(PAUSE)

    left, ready, rej, active = counts(con)
    print(f'\n{now()}  итог: без профиля {left} · прошли пороги и ждут разметки {ready} · '
          f'отсеяно {rej} · в наборе {active}')
