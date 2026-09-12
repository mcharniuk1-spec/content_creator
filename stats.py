#!/usr/bin/env python3
"""Таблицы, на которых стоят решения радара. Уходят на главную страницу в Notion.

    python3 stats.py            показать в терминале
    python3 stats.py --push     обновить раздел в Notion

Смысл раздела — чтобы решение можно было проверить, а не принять на веру: видно, какие
ролики и какие авторы вышли наверх по каждому критерию, и по какому из них отбиралась
каждая карточка.
"""
import datetime, statistics, sys
from db import connect

WINDOW = 14
TOP = 10
MARKER = 'Numbers behind the picks'

# Что означает каждый показатель — словами, а не формулой.
GLOSSARY = [
    ('Score', 'How far a reel sits above its own author\'s usual result — not above the niche. '
              'Built from views, engagement, shares, saves and comments, each measured against '
              'that author\'s median inside the same age band. Capped at 5.'),
    ('Vs own norm', 'Views divided by the author\'s median views. 3× means three times their '
                    'usual. This is the plainest version of the same idea as Score.'),
    ('Shares / 1k', 'Shares per thousand views. The strongest single signal we have: in the top '
                    'hundred it separates a winner 3.6× more reliably than anything else.'),
    ('Saves / 1k', 'Saves per thousand views. Second strongest, 2.8×. People save wording, '
                   'checklists and stacks — things they intend to come back to.'),
    ('Hit rate', 'Share of an author\'s reels in the window that beat their own median. '
                 'High rate with few reels means consistency, not luck.'),
    ('Axes', 'How many of the five components survived. A component with no spread inside that '
             'author is dropped rather than counted as zero, and the weights are renormalised.'),
]

FORMAT_SIGNAL = [
    ('M2 Radar', 'Shares / 1k', 'the topic has to survive another week'),
    ('M2 Builds', 'Saves / 1k', 'we must be able to build it, and something must break'),
    ('M2 Teardown', 'Saves / 1k', 'a topic repeated across several authors, plus a reason to forward'),
]


def window_rows(con, today=None):
    today = today or datetime.date.today()
    edge = int(datetime.datetime.combine(today - datetime.timedelta(days=WINDOW),
                                         datetime.time()).timestamp())
    return [dict(r) for r in con.execute("""
        SELECT r.code, r.username, r.play, r.resh, r.save, r.dur, r.ts,
               s.z, s.resh_1k, s.save_1k, s.author_median_play, s.axes
        FROM reels r JOIN scores s USING(snapshot_id,code)
        JOIN accounts a ON a.pk=r.pk_user AND a.status='active'
        LEFT JOIN deepdives d ON d.code=r.code
        WHERE r.snapshot_id=(SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
          AND s.weights='ig' AND s.eligible=1 AND r.ts>=?
          AND (d.suitable IS NULL OR d.suitable=1)""", (edge,))]


def reel_tables(rows):
    mult = lambda r: r['play'] / (r['author_median_play'] or 1)
    num = lambda n: f'{int(n):,}'.replace(',', ' ')
    def table(title, key, fmt, note, last=('Vs own norm', lambda r: f'{mult(r):.1f}×')):
        got = [r for r in rows if key(r) is not None]
        got.sort(key=lambda r: -key(r))
        return (title, note,
                ['Reel', 'Author', 'Value', 'Views', last[0]],
                [[r['code'], r['username'], fmt(key(r)), num(r['play']), last[1](r)]
                 for r in got[:TOP]])
    return [
        table('Top reels by score', lambda r: r['z'], lambda v: f'{v:.2f}',
              'The list the radar itself ranks by. A capped 5.00 means the reel maxed out '
              'several components at once.'),
        table('Top reels by shares per thousand', lambda r: r['resh_1k'], lambda v: f'{v:.0f}',
              'M2 Radar cards are picked from this list.'),
        table('Top reels by saves per thousand', lambda r: r['save_1k'], lambda v: f'{v:.0f}',
              'M2 Builds and M2 Teardown cards are picked from this list.'),
        table('Top reels by multiple of their own norm', mult, lambda v: f'{v:.1f}×',
              'Biggest outliers relative to their own author. Useful as a sanity check on Score.',
              last=('Shares / 1k', lambda r: f"{r['resh_1k']:.0f}" if r['resh_1k'] is not None else '—')),
    ]


def author_tables(rows, min_reels=3):
    by = {}
    for r in rows:
        by.setdefault(r['username'], []).append(r)
    strong = [(u, v) for u, v in by.items() if len(v) >= min_reels]
    med = lambda v, k: statistics.median([x[k] for x in v if x[k] is not None] or [0])
    hit = lambda v: sum(1 for x in v if x['play'] > (x['author_median_play'] or 1)) / len(v) * 100
    num = lambda n: f'{int(n):,}'.replace(',', ' ')

    def table(title, fn, fmt, note, last=('Median views', lambda v: num(med(v, 'play')))):
        got = sorted(strong, key=lambda kv: -fn(kv[1]))
        return (title, note,
                ['Author', 'Value', 'Reels in window', last[0]],
                [[u, fmt(fn(v)), str(len(v)), last[1](v)] for u, v in got[:TOP]])
    return [
        table('Top accounts by median shares per thousand',
              lambda v: med(v, 'resh_1k'), lambda x: f'{x:.0f}',
              'Who reliably gets forwarded, not who got lucky once.'),
        table('Top accounts by median saves per thousand',
              lambda v: med(v, 'save_1k'), lambda x: f'{x:.0f}',
              'Who produces things people keep.'),
        table('Top accounts by hit rate', hit, lambda x: f'{x:.0f}%',
              'Share of their reels beating their own median. Consistency rather than one spike.'),
        table('Top accounts by median views', lambda v: med(v, 'play'), lambda x: num(x),
              'Plain reach. Kept last on purpose: it says the least about whether a reel worked.',
              last=('Hit rate', lambda v: f'{hit(v):.0f}%')),
    ]


def render_text(con, today=None):
    rows = window_rows(con, today)
    out = [f'окно {WINDOW} дней: {len(rows)} роликов, {len({r["username"] for r in rows})} авторов\n']
    for title, note, head, body in reel_tables(rows) + author_tables(rows):
        out.append(f'\n{title}')
        for r in body[:5]:
            out.append('  ' + '  '.join(f'{c:<22}' if i < 2 else f'{c:>10}'
                                        for i, c in enumerate(r)))
    return '\n'.join(out)


# ------------------------------------------------------------------- Notion ----
def push(con, today=None):
    import notion
    page = notion.env('NOTION_PAGE')
    rows = window_rows(con, today)
    snaps = con.execute('SELECT COUNT(*) FROM snapshots WHERE done=1').fetchone()[0]
    taken = con.execute('SELECT taken FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()[0]

    def txt(t, tp='paragraph', **kw):
        d = {'rich_text': [{'type': 'text', 'text': {'content': t[:1900]}}]}
        d.update(kw)
        return {'object': 'block', 'type': tp, tp: d}

    def table(head, body):
        cell = lambda s: [{'type': 'text', 'text': {'content': str(s)[:200]}}]
        rows_ = [{'object': 'block', 'type': 'table_row',
                  'table_row': {'cells': [cell(h) for h in head]}}]
        rows_ += [{'object': 'block', 'type': 'table_row',
                   'table_row': {'cells': [cell(c) for c in r]}} for r in body]
        return {'object': 'block', 'type': 'table',
                'table': {'table_width': len(head), 'has_column_header': True,
                          'has_row_header': False, 'children': rows_}}

    blocks = [
        txt(MARKER, 'heading_1'),
        txt(f'Snapshot {taken}. Window {WINDOW} days: {len(rows)} reels across '
            f'{len({r["username"] for r in rows})} accounts, after dropping reels marked unusable. '
            f'Rebuilt on every run.'),
        txt('What each number means', 'heading_2'),
    ]
    for name, desc in GLOSSARY:
        blocks.append({'object': 'block', 'type': 'bulleted_list_item',
                       'bulleted_list_item': {'rich_text': [
                           {'type': 'text', 'text': {'content': name + ' — '},
                            'annotations': {'bold': True}},
                           {'type': 'text', 'text': {'content': desc}}]}})
    blocks.append(txt('Which list each format is picked from', 'heading_2'))
    blocks.append(table(['Format', 'Ranked by', 'Also has to pass'],
                        [[a, b, c] for a, b, c in FORMAT_SIGNAL]))

    blocks.append(txt('Reels', 'heading_2'))
    for title, note, head, body in reel_tables(rows):
        blocks += [txt(title, 'heading_3'), txt(note), table(head, body)]

    blocks.append(txt('Accounts', 'heading_2'))
    blocks.append(txt('Only accounts with three or more reels in the window — below that a '
                      'median means nothing.'))
    for title, note, head, body in author_tables(rows):
        blocks += [txt(title, 'heading_3'), txt(note), table(head, body)]

    blocks.append(txt('What moved since last run', 'heading_2'))
    if snaps < 2:
        blocks.append(txt('Nothing to compare yet — this is the first completed snapshot. '
                          'Growth, new topics and who broke through appear from the second run on.',
                          'callout', icon={'emoji': '⏳'}))
    else:
        import delta
        two = delta.snapshots(con)
        td = delta.topics_delta(con, two[0]['id'], two[1]['id'])
        up, gone = delta.authors_delta(con, two[0]['id'], two[1]['id'])
        fd = delta.followers_delta(con)
        blocks.append(txt(f'{two[1]["taken"]} → {two[0]["taken"]}'))
        blocks.append(table(['Topic', 'Was', 'Now', 'Change'],
                            [[t['topic'], t['was'], t['now'], f"{t['d']:+d}"]
                             for t in td[:TOP] if t['d']]))
        if up:
            blocks.append(txt('Broke through for the first time: ' + ', '.join(up[:12])))
        if fd:
            blocks.append(table(['Account', 'Followers before', 'Now', 'Change'],
                                [[r['username'], r['c0'], r['c1'], f"{r['pct']:+.1f}%"]
                                 for r in fd[:TOP]]))

    # раздел пересобирается целиком: всё от маркера и ниже заменяется
    old = notion.call('GET', f'/blocks/{page}/children?page_size=100').get('results', [])
    hit = False
    for b in old:
        if not hit:
            rt = b.get(b['type'], {}).get('rich_text') or []
            if any(MARKER in t.get('plain_text', '') for t in rt):
                hit = True
        if hit:
            # Баг из аудита (reports/audit/03 §3, 09-07: "Notion ответил 400: Updating
            # a page via the blocks endpoint unsupported. Call patch /v1/pages/:page_id
            # instead"). Причина: если среди дочерних блоков страницы затесался вложенный
            # child_page/child_database (например, кто-то руками создал подстраницу под
            # разделом со статистикой), его id — это id страницы/базы, и Notion прямо
            # запрещает архивировать его через /blocks/{id} — нужен /pages/{id} или
            # /databases/{id} соответственно. Обычные блоки (paragraph, table, heading…)
            # по-прежнему архивируются через /blocks/.
            if b['type'] == 'child_page':
                notion.call('PATCH', f'/pages/{b["id"]}', {'archived': True})
            elif b['type'] == 'child_database':
                notion.call('PATCH', f'/databases/{b["id"]}', {'archived': True})
            else:
                notion.call('PATCH', f'/blocks/{b["id"]}', {'archived': True})
    for i in range(0, len(blocks), 90):
        notion.call('PATCH', f'/blocks/{page}/children', {'children': blocks[i:i + 90]})
    return len(blocks)


if __name__ == '__main__':
    con = connect()
    if '--push' in sys.argv:
        n = push(con)
        print(f'раздел «{MARKER}» обновлён, блоков: {n}')
    else:
        print(render_text(con))
