#!/usr/bin/env python3
"""Полные базы в Notion: каждый ролик окна и каждый аккаунт набора.

    python3 notion_db.py reels        выгрузить ролики окна
    python3 notion_db.py accounts     выгрузить аккаунты
    python3 notion_db.py both

Здесь лежит всё собранное и всё выведенное — метрики, оценка и её составляющие, длина,
склейки, объём речи по блокам, темп, признаки подписи и хука, темы. Сводные таблицы на
главной странице показывают верхушку; эти базы — то, из чего верхушка получена, чтобы
любое решение можно было разобрать, а не принять на веру.
"""
import datetime, statistics, sys
import analyze, notion
from db import connect

WINDOW = 14
CHUNK = 90


def tag(t):
    """Notion не пускает запятые в теги мультивыбора."""
    return t.replace(',', ' —')[:95]


def window_reels(con, today=None):
    today = today or datetime.date.today()
    edge = int(datetime.datetime.combine(today - datetime.timedelta(days=WINDOW),
                                         datetime.time()).timestamp())
    rows = con.execute("""
        SELECT r.*, s.z, s.resh_1k, s.save_1k, s.comm_1k, s.author_median_play, s.axes,
               s.baseline_n, d.cuts_ps, d.suitable,
               (SELECT 1 FROM cards c WHERE c.code=r.code) picked
        FROM reels r JOIN scores s USING(snapshot_id,code)
        JOIN accounts a ON a.pk=r.pk_user AND a.status='active'
        LEFT JOIN deepdives d ON d.code=r.code
        WHERE r.snapshot_id=(SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
          AND s.weights='ig' AND s.eligible=1 AND r.ts>=?
        ORDER BY s.z DESC""", (edge,)).fetchall()
    return [dict(r) for r in rows], today


def reel_props(con, r, today):
    f = analyze.facts(con, r)
    yes = lambda v: {'checkbox': bool(v)}
    num = lambda v: {'number': round(v, 2) if isinstance(v, float) else v} if v is not None else {'number': None}
    p = {
        'Reel': {'title': [{'text': {'content': r['code']}}]},
        'Author': {'rich_text': [{'text': {'content': r['username'] or ''}}]},
        'URL': {'url': f"https://instagram.com/reel/{r['code']}"},
        'Posted': {'date': {'start': datetime.date.fromtimestamp(r['ts']).isoformat()}},
        'Age days': num((today - datetime.date.fromtimestamp(r['ts'])).days),
        'Views': num(r['play']), 'Likes': num(r['likes']), 'Comments': num(r['comm']),
        'Shares': num(r['resh']), 'Saves': num(r['save']),
        'Shares 1k': num(r['resh_1k']), 'Saves 1k': num(r['save_1k']), 'Comments 1k': num(r['comm_1k']),
        'Score': num(r['z']),
        'Vs own norm': num(round(r['play'] / (r['author_median_play'] or 1), 1)),
        'Axes': num(r['axes']), 'Baseline': num(r['baseline_n']),
        'Duration s': num(r['dur']), 'Cuts per s': num(r['cuts_ps']),
        'One take': yes(f.get('one_take')),
        'Transcript words': num(f.get('words')),
        'Hook words': num(f.get('hook_words')), 'Body words': num(f.get('body_words')),
        'Ending words': num(f.get('tail_words')), 'Words per min': num(f.get('wpm')),
        'Topics': {'multi_select': [{'name': tag(t)} for t in f.get('topics', [])[:8]]},
        'Comment bait': yes(f.get('comment_bait')), 'DM promise': yes(f.get('dm_promise')),
        'Money claim': yes(f.get('money_claim')), 'Caption question': yes(f.get('question')),
        'Caption number': yes(f.get('number')),
        'Hook question': yes(f.get('hook_question')), 'Hook number': yes(f.get('hook_number')),
        'Hook you': yes(f.get('hook_you')), 'Hook claim': yes(f.get('hook_claim')),
        'Analysed': yes(f.get('analysed')),
        'Usable': {'select': {'name': 'not checked' if r['suitable'] is None
                              else ('yes' if r['suitable'] else 'no')}},
        'Picked as card': yes(r['picked']),
        'Caption': {'rich_text': [{'text': {'content': (r['cap'] or '')[:1900]}}]},
    }
    return p


def push_reels(con, today=None, limit=None):
    db = notion.env('NOTION_REELS_DB')
    rows, today = window_reels(con, today)
    if limit:
        rows = rows[:int(limit)]
    have = {}
    cur = None
    while True:
        body = {'page_size': 100}
        if cur:
            body['start_cursor'] = cur
        res = notion.call('POST', f'/databases/{db}/query', body)
        for p in res['results']:
            t = p['properties']['Reel']['title']
            if t:
                have[t[0]['plain_text']] = p['id']
        cur = res.get('next_cursor')
        if not cur:
            break
    added = updated = 0
    for i, r in enumerate(rows, 1):
        props = reel_props(con, r, today)
        if r['code'] in have:
            notion.call('PATCH', f'/pages/{have[r["code"]]}', {'properties': props}); updated += 1
        else:
            notion.call('POST', '/pages', {'parent': {'database_id': db}, 'properties': props}); added += 1
        if i % 50 == 0:
            print(f'  {i}/{len(rows)}', flush=True)
    print(f'ролики: добавлено {added}, обновлено {updated}, всего {len(rows)}')
    return added + updated


def account_stats(con, today=None):
    rows, today = window_reels(con, today)
    by = {}
    for r in rows:
        by.setdefault(r['username'], []).append(r)
    med = lambda v, k: statistics.median([x[k] for x in v if x[k] is not None] or [0])
    out = {}
    for u, v in by.items():
        an = [x for x in v if x['cuts_ps'] is not None]
        facts = [analyze.facts(con, x) for x in v]
        topics = {}
        for f in facts:
            for t in f.get('topics', []):
                topics[t] = topics.get(t, 0) + 1
        best = max(v, key=lambda x: x['z'])
        out[u] = dict(
            n=len(v), views=med(v, 'play'), resh=med(v, 'resh_1k'), save=med(v, 'save_1k'),
            hit=sum(1 for x in v if x['play'] > (x['author_median_play'] or 1)) / len(v) * 100,
            dur=med(v, 'dur'), cuts=med(an, 'cuts_ps') if an else None,
            one_take=(sum(1 for x in an if x['cuts_ps'] < 0.02) / len(an) * 100) if an else None,
            bait=sum(1 for f in facts if f.get('comment_bait')) / len(facts) * 100,
            topics=[t for t, _ in sorted(topics.items(), key=lambda kv: -kv[1])[:6]],
            best=best['code'], best_z=best['z'])
    return out


def signature(s):
    """Что этот аккаунт делает постоянно — читается прямо из его же цифр."""
    bits = []
    if s['one_take'] is not None:
        bits.append(f"{s['one_take']:.0f}% of analysed reels shot in one take"
                    if s['one_take'] >= 50 else f"cuts most reels ({s['cuts']:.2f}/s median)")
    bits.append(f"median {s['dur']:.0f}s")
    if s['bait'] >= 40:
        bits.append(f"asks for a comment in {s['bait']:.0f}% of reels")
    if s['resh'] and s['save'] and s['save'] > s['resh'] * 1.5:
        bits.append('gets saved more than forwarded — reference material')
    elif s['resh'] and s['save'] and s['resh'] > s['save']:
        bits.append('gets forwarded more than saved — argument material')
    if s['hit'] >= 70:
        bits.append(f"consistent: {s['hit']:.0f}% of reels beat their own median")
    return ' · '.join(bits)


def push_accounts(con, today=None):
    db = notion.env('NOTION_ACCOUNTS_DB')
    st = account_stats(con, today)
    accounts = con.execute("""SELECT pk, username, follower_count, media_count, category,
        biography, tag, status FROM accounts WHERE status='active' ORDER BY username""").fetchall()
    have = {}
    cur = None
    while True:
        body = {'page_size': 100}
        if cur:
            body['start_cursor'] = cur
        res = notion.call('POST', f'/databases/{db}/query', body)
        for p in res['results']:
            t = p['properties']['Account']['title']
            if t:
                have[t[0]['plain_text']] = p['id']
        cur = res.get('next_cursor')
        if not cur:
            break
    n = 0
    num = lambda v: {'number': round(v, 2) if isinstance(v, float) else v} if v is not None else {'number': None}
    for a in accounts:
        s = st.get(a['username'])
        props = {
            'Account': {'title': [{'text': {'content': a['username']}}]},
            'Followers': num(a['follower_count']), 'Posts total': num(a['media_count']),
            'Category': {'rich_text': [{'text': {'content': a['category'] or ''}}]},
            'Bio': {'rich_text': [{'text': {'content': ' '.join((a['biography'] or '').split())[:1900]}}]},
            'In our set': {'checkbox': True},
            'Status': {'rich_text': [{'text': {'content': a['status']}}]},
        }
        if s:
            props.update({
                'Reels in window': num(s['n']), 'Median views': num(s['views']),
                'Median shares 1k': num(s['resh']), 'Median saves 1k': num(s['save']),
                'Hit rate': num(s['hit']), 'Median duration': num(s['dur']),
                'Median cuts per s': num(s['cuts']), 'One take share': num(s['one_take']),
                'Comment bait share': num(s['bait']),
                'Topics': {'multi_select': [{'name': tag(t)} for t in s['topics']]},
                'Best reel': {'url': f"https://instagram.com/reel/{s['best']}"},
                'Best reel score': num(s['best_z']),
                'Signature moves': {'rich_text': [{'text': {'content': signature(s)[:1900]}}]},
            })
        if a['username'] in have:
            notion.call('PATCH', f'/pages/{have[a["username"]]}', {'properties': props})
        else:
            notion.call('POST', '/pages', {'parent': {'database_id': db}, 'properties': props})
        n += 1
        if n % 25 == 0:
            print(f'  {n}/{len(accounts)}', flush=True)
    print(f'аккаунты: выгружено {n}')
    return n


if __name__ == '__main__':
    con = connect()
    a = sys.argv[1:] or ['both']
    if a[0] in ('reels', 'both'):
        push_reels(con, limit=(a[1] if len(a) > 1 and a[1].isdigit() else None))
    if a[0] in ('accounts', 'both'):
        push_accounts(con)
