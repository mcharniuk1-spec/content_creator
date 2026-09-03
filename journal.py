#!/usr/bin/env python3
"""Журнал по самой туле. SPEC §4.8.

    python3 journal.py                     показать: открытое сверху
    python3 journal.py add bug "что" "детали"
    python3 journal.py fixed 5
    python3 journal.py month               сводка за последние 30 дней

Что записывать: что сломалось, что предложило мусор, что правил руками, чего не хватило.
Смысл не в аккуратности, а в накоплении: за два дня работы так всплыли два бага в формуле,
ошибка в скилле, неверная трактовка баланса и дыра в фильтре — ничего из этого
не искали специально.
"""
import datetime, sys
from db import connect

KINDS = {'bug': 'сломалось', 'junk': 'выдало мусор',
         'manual': 'правил руками', 'gap': 'чего-то не хватило'}


def add(con, kind, what, detail=None, at=None):
    if kind not in KINDS:
        raise SystemExit(f'вид записи: {", ".join(KINDS)}')
    cur = con.execute('INSERT INTO tool_log (at,kind,what,detail,fixed) VALUES (?,?,?,?,0)',
                      (at or datetime.date.today().isoformat(), kind, what, detail))
    con.commit()
    return cur.lastrowid


def close(con, log_id):
    if not con.execute('SELECT 1 FROM tool_log WHERE id=?', (log_id,)).fetchone():
        raise SystemExit(f'записи №{log_id} нет')
    con.execute('UPDATE tool_log SET fixed=1 WHERE id=?', (log_id,))
    con.commit()


def show(con, since=None):
    where, args = ('WHERE at >= ?', (since,)) if since else ('', ())
    rows = con.execute(f'SELECT * FROM tool_log {where} ORDER BY fixed, at DESC, id DESC',
                       args).fetchall()
    if not rows:
        print('журнал пуст'); return
    for state, title in ((0, 'ОТКРЫТО'), (1, 'ЗАКРЫТО')):
        part = [r for r in rows if r['fixed'] == state]
        if not part:
            continue
        print(f'\n{title}  ({len(part)})')
        for r in part:
            print(f"  №{r['id']:<3} {r['at']}  {KINDS.get(r['kind'], r['kind']):<18} {r['what']}")
            if r['detail']:
                d = r['detail'].replace('\n', ' ')
                print(f"        {d[:150]}{'…' if len(d) > 150 else ''}")
    by = con.execute(f'SELECT kind, COUNT(*) FROM tool_log {where} GROUP BY kind ORDER BY 2 DESC',
                     args).fetchall()
    print('\nпо видам: ' + ' · '.join(f'{KINDS.get(k, k)} {n}' for k, n in by))


if __name__ == '__main__':
    a = sys.argv[1:]
    con = connect()
    if not a:
        show(con)
    elif a[0] == 'add':
        if len(a) < 3:
            raise SystemExit('нужно: add ВИД "что" ["детали"]')
        n = add(con, a[1], a[2], a[3] if len(a) > 3 else None)
        print(f'записано №{n}')
    elif a[0] == 'fixed':
        close(con, int(a[1]))
        print(f'№{a[1]} закрыта')
    elif a[0] == 'month':
        since = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        print(f'за 30 дней, с {since}')
        show(con, since)
    else:
        print(__doc__)
