#!/usr/bin/env python3
"""Что мы опубликовали и что из этого вышло. SPEC §4.6 и §4.8.

    python3 posts.py add 2026-09-08 "Токены, стоимость, лимиты" РАЗБОР --url ... --lead Миша
    python3 posts.py list
    python3 posts.py closed              темы, закрытые за последние 6 недель
    python3 posts.py metrics 3           ввести шесть чисел по ролику №3

Память о снятом — единственный механизм против самоповтора: связок между роликами мы
не делаем, поэтому тема, закрытая за последние шесть недель, из отбора исключается.
"""
import datetime, sys
from db import connect

MEMORY_WEEKS = 6
FIELDS = [('reach_followers', 'охват по подписчикам'),
          ('reach_nonfollowers', 'охват по неподписчикам'),
          ('retention', 'удержание, доля 0..1'),
          ('dropoff_sec', 'точка отвала, секунда'),
          ('saves', 'сохранения'),
          ('follows', 'подписки с ролика')]


def closed_topics(con, weeks=MEMORY_WEEKS, today=None):
    """Темы, закрытые нами за окно памяти. Их отбор карточек не предлагает."""
    today = today or datetime.date.today()
    edge = (today - datetime.timedelta(weeks=weeks)).isoformat()
    return {r[0] for r in con.execute(
        'SELECT DISTINCT topic FROM our_posts WHERE topic IS NOT NULL AND published_at >= ?',
        (edge,))}


def add(con, date, topic, fmt, url=None, lead=None, goal=None, ref=None, note=None):
    datetime.date.fromisoformat(date)                 # падаем сразу, а не через месяц
    cur = con.execute("""INSERT INTO our_posts
        (published_at,format,topic,url,lead,goal,ref_code,note) VALUES (?,?,?,?,?,?,?,?)""",
        (date, fmt, topic, url, lead, goal, ref, note))
    con.commit()
    return cur.lastrowid


def set_metrics(con, post_id, **vals):
    if not con.execute('SELECT 1 FROM our_posts WHERE id=?', (post_id,)).fetchone():
        raise SystemExit(f'ролика №{post_id} нет')
    cols = [k for k, _ in FIELDS if vals.get(k) is not None]
    con.execute("""INSERT INTO our_metrics (post_id,measured_at) VALUES (?,?)
                   ON CONFLICT(post_id) DO UPDATE SET measured_at=excluded.measured_at""",
                (post_id, datetime.date.today().isoformat()))
    if cols:
        con.execute(f"UPDATE our_metrics SET {','.join(c + '=?' for c in cols)} WHERE post_id=?",
                    [vals[c] for c in cols] + [post_id])
    con.commit()
    return cols


def _ask(post_id, con):
    """Шесть чисел руками. Пустая строка — пропустить поле."""
    row = con.execute('SELECT published_at, topic, format FROM our_posts WHERE id=?',
                      (post_id,)).fetchone()
    if not row:
        raise SystemExit(f'ролика №{post_id} нет')
    print(f'ролик №{post_id}: {row[0]} · {row[2]} · {row[1]}\nEnter — пропустить поле\n')
    out = {}
    for key, label in FIELDS:
        s = input(f'  {label}: ').strip().replace(',', '.')
        if s:
            out[key] = float(s) if '.' in s else int(s)
    return out


def _list(con):
    rows = con.execute("""SELECT p.id, p.published_at, p.format, p.topic, p.lead,
        m.reach_followers, m.reach_nonfollowers, m.retention, m.saves, m.follows
        FROM our_posts p LEFT JOIN our_metrics m ON m.post_id=p.id
        ORDER BY p.published_at DESC, p.id DESC""").fetchall()
    if not rows:
        print('опубликованного пока нет — аккаунт не запущен')
        return
    print(f'{"№":>3}  {"дата":<11} {"формат":<10} {"тема":<38} {"ведущий":<8} цифры')
    for r in rows:
        have = 'есть' if r[5] is not None else '—'
        print(f'{r[0]:>3}  {r[1]:<11} {(r[2] or ""):<10} {(r[3] or "")[:36]:<38} '
              f'{(r[4] or ""):<8} {have}')
    cl = closed_topics(con)
    print(f'\nзакрыто тем за {MEMORY_WEEKS} недель: {len(cl)}')
    for t in sorted(cl):
        print(f'  · {t}')


if __name__ == '__main__':
    a = sys.argv[1:]
    con = connect()
    if not a or a[0] == 'list':
        _list(con)
    elif a[0] == 'closed':
        cl = closed_topics(con)
        print('\n'.join(sorted(cl)) if cl else f'за {MEMORY_WEEKS} недель ничего не закрыто')
    elif a[0] == 'add':
        if len(a) < 4:
            raise SystemExit('нужно: add ДАТА ТЕМА ФОРМАТ [--url U] [--lead Л] [--goal Г] [--ref КОД]')
        kw = {k.lstrip('-'): v for k, v in zip(a[4::2], a[5::2])}
        pid = add(con, a[1], a[2], a[3], **kw)
        print(f'записан ролик №{pid}. Тема исключена из отбора на {MEMORY_WEEKS} недель')
    elif a[0] == 'metrics':
        pid = int(a[1])
        cols = set_metrics(con, pid, **_ask(pid, con))
        print(f'\nзаписано полей: {len(cols)} из {len(FIELDS)}')
    else:
        print(__doc__)
