#!/usr/bin/env python3
"""Чистка: кадры и расшифровки старше срока. SPEC §4.4 — видео не храним, но кадры копятся.

    python3 prune.py            что удалилось бы
    python3 prune.py --yes      удалить

При ста разборах дважды в неделю это около гигабайта в месяц. Кадры нужны, пока ролик
может попасть в карточку, то есть недолго: окно свежести — две недели, память тем — шесть.
"""
import datetime, os, pathlib, shutil, sys
from db import connect

KEEP_WEEKS = 8
D = pathlib.Path(__file__).parent / 'data'


def stale(con, weeks=KEEP_WEEKS):
    edge = (datetime.date.today() - datetime.timedelta(weeks=weeks)).isoformat()
    return con.execute("""SELECT code, sheet FROM deepdives
        WHERE done_at < ? AND code NOT IN (SELECT code FROM cards)""", (edge,)).fetchall()


if __name__ == '__main__':
    con = connect()
    rows = stale(con)
    size = 0
    for r in rows:
        d = D / 'frames' / r['code']
        if d.exists():
            size += sum(f.stat().st_size for f in d.glob('*.jpg'))
        s = D.parent / (r['sheet'] or '')
        if r['sheet'] and s.exists():
            size += s.stat().st_size
    print(f'разборов старше {KEEP_WEEKS} недель и не в карточках: {len(rows)}, '
          f'кадров на {size / 1048576:.0f} МБ')
    if '--yes' not in sys.argv:
        print('это план. Удалить: python3 prune.py --yes')
        sys.exit()
    for r in rows:
        shutil.rmtree(D / 'frames' / r['code'], ignore_errors=True)
        s = D.parent / (r['sheet'] or '')
        if r['sheet'] and s.exists():
            s.unlink()
        con.execute('DELETE FROM frames WHERE code=?', (r['code'],))
        con.execute('UPDATE deepdives SET sheet=NULL WHERE code=?', (r['code'],))
    con.commit()
    print(f'удалено кадров по {len(rows)} роликам, освобождено {size / 1048576:.0f} МБ.')
    print('строки разбора, склейки и расшифровки остались — они весят копейки и нужны истории')
