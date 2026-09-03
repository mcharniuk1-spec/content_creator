"""База сравнения автора: все его ролики за всю историю снимков, каждый по одному разу.

Зачем: медиана, посчитанная по одной выгрузке, стоит на 24 роликах и шатается.
Через месяц у автора накопится 8–10 выгрузок, часть роликов уйдёт со страницы, часть
добавится — база сравнения растёт, норма становится устойчивее. SPEC §4.3.

Ролик, попавший в несколько снимков, берётся из последнего: просмотры только растут,
поэтому последний замер и есть самый полный.
"""
import collections

LATEST = """
SELECT code, pk_user, username, ts, play, likes, comm, resh, save, dur, snapshot_id
FROM (SELECT r.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY snapshot_id DESC) rn
      FROM reels r)
WHERE rn = 1
"""


def latest_rows(con):
    """Все известные ролики, каждый в самом свежем замере."""
    return [dict(r) for r in con.execute(LATEST)]


def by_author(con):
    """{pk_user: [ролики]} — база сравнения. Плюс в скольких снимках автор встречался:
    это и есть глубина истории, на которую опирается его норма."""
    out = collections.defaultdict(list)
    for r in latest_rows(con):
        out[r['pk_user']].append(r)
    snaps = {pk: n for pk, n in con.execute(
        'SELECT pk_user, COUNT(DISTINCT snapshot_id) FROM reels GROUP BY pk_user')}
    return out, snaps


def snapshot_rows(con, snapshot_id):
    """Ролики одного снимка — то, что оцениваем."""
    return [dict(r) for r in con.execute(
        """SELECT code, pk_user, username, ts, play, likes, comm, resh, save, dur, snapshot_id
           FROM reels WHERE snapshot_id = ?""", (snapshot_id,))]


def last_snapshot(con):
    return con.execute('SELECT id, taken FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()


if __name__ == '__main__':
    from db import connect
    con = connect()
    base, snaps = by_author(con)
    sizes = sorted(len(v) for v in base.values())
    sid, taken = last_snapshot(con)
    n = len(snapshot_rows(con, sid))
    print(f'снимков в базе: {con.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]}'
          f'  последний {taken}, роликов {n}')
    print(f'авторов с базой сравнения: {len(base)}')
    print(f'роликов в базе на автора: минимум {sizes[0]}, медиана {sizes[len(sizes)//2]}, '
          f'максимум {sizes[-1]}')
    print(f'авторов с базой меньше 5 роликов: {sum(1 for s in sizes if s < 5)}')
