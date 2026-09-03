#!/usr/bin/env python3
"""Что изменилось между снимками. SPEC §4.7, слой 1.

    python3 delta.py            последний снимок против предыдущего

Радар без дельты — это срез, а не радар. Считается три вещи: темы (стало больше или
меньше роликов и авторов, что появилось впервые), авторы (кто залетел, кого не было),
подписчики (кто растёт). До второго снимка честно говорит, что сравнивать не с чем.
"""
import sys
from db import connect


def snapshots(con, n=2):
    return con.execute('SELECT id, taken FROM snapshots WHERE done=1 '
                       'ORDER BY taken DESC LIMIT ?', (n,)).fetchall()


def topics_delta(con, cur, prev):
    def load(sid):
        return {t: (n, a) for t, n, a in con.execute("""
            SELECT t.topic, COUNT(*), COUNT(DISTINCT r.username)
            FROM topics t JOIN reels r USING(code)
            WHERE r.snapshot_id=? GROUP BY t.topic""", (sid,))}
    a, b = load(cur), load(prev)
    out = []
    for t in set(a) | set(b):
        n0, a0 = b.get(t, (0, 0))
        n1, a1 = a.get(t, (0, 0))
        out.append({'topic': t, 'was': n0, 'now': n1, 'd': n1 - n0,
                    'authors_was': a0, 'authors_now': a1, 'new': t not in b})
    return sorted(out, key=lambda x: -x['d'])


def authors_delta(con, cur, prev, min_mult=1.5):
    def hits(sid):
        return {u for (u,) in con.execute("""
            SELECT DISTINCT r.username FROM reels r JOIN scores s USING(snapshot_id,code)
            WHERE r.snapshot_id=? AND s.weights='ig' AND s.eligible=1
              AND s.author_median_play>0 AND r.play*1.0/s.author_median_play >= ?""",
            (sid, min_mult))}
    a, b = hits(cur), hits(prev)
    return sorted(a - b), sorted(b - a)


def followers_delta(con):
    rows = con.execute("""
        SELECT a.username, MIN(f.at) f0, MAX(f.at) f1,
               (SELECT follower_count FROM followers x WHERE x.pk=f.pk ORDER BY at LIMIT 1) c0,
               (SELECT follower_count FROM followers x WHERE x.pk=f.pk ORDER BY at DESC LIMIT 1) c1
        FROM followers f JOIN accounts a ON a.pk=f.pk
        GROUP BY f.pk HAVING COUNT(*) > 1""").fetchall()
    out = [dict(r, d=(r['c1'] or 0) - (r['c0'] or 0),
                pct=((r['c1'] or 0) - (r['c0'] or 0)) / max(r['c0'] or 1, 1) * 100) for r in rows]
    return sorted(out, key=lambda x: -x['pct'])


def report(con):
    snaps = snapshots(con)
    if len(snaps) < 2:
        print(f'снимков {len(snaps)} — сравнивать не с чем.')
        print('Дельта появится со второго завершённого сбора, не раньше.')
        return None
    cur, prev = snaps[0], snaps[1]
    print(f'{prev["taken"]} → {cur["taken"]}\n')
    td = topics_delta(con, cur['id'], prev['id'])
    new = [t for t in td if t['new'] and t['now'] >= 3]
    print('ТЕМЫ, КОТОРЫХ НЕ БЫЛО')
    print('  ' + ('\n  '.join(f"{t['topic']} — {t['now']} роликов у {t['authors_now']} авторов"
                              for t in new) if new else '—'))
    print('\nПРИБАВИЛИ')
    for t in [x for x in td if x['d'] > 0 and not x['new']][:6]:
        print(f"  {t['topic']:<44} {t['was']:>4} → {t['now']:<4} ({t['d']:+d})")
    print('\nУБАВИЛИ')
    for t in sorted([x for x in td if x['d'] < 0], key=lambda x: x['d'])[:6]:
        print(f"  {t['topic']:<44} {t['was']:>4} → {t['now']:<4} ({t['d']:+d})")
    up, down = authors_delta(con, cur['id'], prev['id'])
    print(f'\nЗАЛЕТЕЛИ ВПЕРВЫЕ ({len(up)})\n  ' + (', '.join(up[:12]) or '—'))
    print(f'ПЕРЕСТАЛИ ({len(down)})\n  ' + (', '.join(down[:12]) or '—'))
    fd = followers_delta(con)
    print('\nРОСТ ПОДПИСЧИКОВ')
    if not fd:
        print('  ряда ещё нет — python3 roster.py followers, и так каждую неделю')
    for r in fd[:8]:
        print(f"  {r['username']:<24} {r['c0']:>8,} → {r['c1']:<8,} {r['pct']:+.1f}%"
              .replace(',', ' '))
    return {'topics': td, 'new': new, 'up': up, 'down': down, 'followers': fd}


if __name__ == '__main__':
    report(connect())
