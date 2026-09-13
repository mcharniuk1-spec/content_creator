"""Shortlist selection: blocks, three stages, what the machine leaves empty.

Synthetic database (db.SCHEMA on a temp file), never a copy of the working one: a pool
with a known layout per content block, so the outcome of cards.select() (who lands in
which stage and block) is predicted, not read off live data after the fact.

Scheme (Misha, 13 Sep 2026): 15 reels a week, three stages.
  stage 1  one per block, the block's best reel that beat its author's own norm
  stage 2  the rest by shares + saves, any block, at most 3 per block in the 15
  stage 3  Misha picks 5 of 15, at most 2 from one block (a rule for him, printed by show)
"""
import datetime, os, sys
import cards, posts, content_blocks as cb
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.cards-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP); fail = []

def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<58} {g}   expected {w}")
    if g != w: fail.append(n)

TODAY = datetime.date(2026, 9, 1)
RECENT_TS = int(datetime.datetime.combine(TODAY - datetime.timedelta(days=2), datetime.time()).timestamp())

con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,12,0,1)", (TODAY.isoformat(),))
sid = con.execute("SELECT id FROM snapshots WHERE taken=?", (TODAY.isoformat(),)).fetchone()[0]

# username, resh_1k, save_1k, topic tag, caption. play 3000 vs author norm 1000: above norm.
# News is over-supplied and strongest (six authors, ranks 150-200): without the cap it would
# take every stage-2 slot. Builds has four. Every other block has exactly one reel.
ROWS = [
    ('p1', 40, 20, 'AI в конкретном бизнес-процессе', 'cap p1'),
    ('m1', 35, 20, 'Токены, стоимость, лимиты', 'cap m1'),
    ('k1', 30, 20, 'Критика и скепсис про AI', 'cap k1'),
    ('c1', 25, 20, 'Обзор инструмента', 'cap c1'),
    ('l1', 20, 20, 'Обучение и навыки', 'cap l1'),
    ('s1', 15, 20, 'Готовый репозиторий с GitHub', 'cap s1'),
    ('b1', 50, 20, 'Сборка агентов и мультиагентные системы', 'cap b1'),
    ('b2', 45, 20, 'Сборка агентов и мультиагентные системы', 'cap b2'),
    ('b3', 42, 20, 'Сборка агентов и мультиагентные системы', 'cap b3'),
    ('b4', 41, 20, 'Сборка агентов и мультиагентные системы', 'cap b4'),
    ('n1', 180, 20, 'Новости моделей и лабораторий', 'cap n1'),
    ('n2', 170, 20, 'Новости моделей и лабораторий', 'cap n2'),
    ('n3', 160, 20, 'Новости моделей и лабораторий', 'cap n3'),
    ('n4', 150, 20, 'Новости моделей и лабораторий', 'cap n4'),
    ('n5', 140, 20, 'Новости моделей и лабораторий', 'cap n5'),
    ('n6', 130, 20, 'Новости моделей и лабораторий', 'cap n6'),
    ('u1', 80, 20, 'Темы в подписи нет', 'cap u1'),
]
for pk, (user, resh_1k, save_1k, topic, cap) in enumerate(ROWS, 1):
    code = f'{user.upper()}CODE001'
    con.execute("INSERT INTO accounts (pk,username,status) VALUES (?,?,'active')", (pk, user))
    con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play,dur,cap)
        VALUES (?,?,?,?,?,?,?,?)""", (sid, code, pk, user, RECENT_TS, 3000, 60.0, cap))
    con.execute("""INSERT INTO scores (snapshot_id,code,eligible,author_median_play,
        resh_1k,save_1k,weights) VALUES (?,?,1,1000,?,?,'ig')""", (sid, code, resh_1k, save_1k))
    con.execute("INSERT INTO topics (code,topic,source) VALUES (?,?,'manual')", (code, topic))
con.execute("INSERT INTO topics (code,topic,source) VALUES ('N1CODE001','Topic N1','manual')")
# n1's second reel: below the author's norm (800 vs 1000), the only Trust reel in the pool.
# In the pool since 12 Sep (author qualifies), but stage 1 needs a reel above its own norm.
con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play,dur,cap)
    VALUES (?,?,?,?,?,?,?,?)""", (sid, 'N1CODE002', 11, 'n1', RECENT_TS, 800, 60.0,
                                  'they trust the answer, never verify, it hallucinated the invoice'))
con.execute("""INSERT INTO scores (snapshot_id,code,eligible,author_median_play,resh_1k,save_1k,weights)
    VALUES (?,?,1,1000,20,10,'ig')""", (sid, 'N1CODE002'))
con.execute("INSERT INTO topics (code,topic,source) VALUES ('N1CODE002','Темы в подписи нет','manual')")
# lone author z1 with no reel above norm: never in the pool
con.execute("INSERT INTO accounts (pk,username,status) VALUES (99,'z1','active')")
con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play,dur,cap)
    VALUES (?,?,?,?,?,?,?,?)""", (sid, 'Z1CODE001', 99, 'z1', RECENT_TS, 1200, 60.0, 'cap z1'))
con.execute("""INSERT INTO scores (snapshot_id,code,eligible,author_median_play,resh_1k,save_1k,weights)
    VALUES (?,?,1,1000,500,500,'ig')""", (sid, 'Z1CODE001'))
con.execute("INSERT INTO topics (code,topic,source) VALUES ('Z1CODE001','Новости моделей и лабораторий','manual')")
con.commit()

# ---------------------------------------------------------------- routing
eq('tag routes to its block', cb.classify(['Токены, стоимость, лимиты'], '')[0], 'money')
eq('words route when no tag', cb.classify([], 'never verify, it hallucinated')[0], 'trust')
eq('tag outweighs a stray word', cb.classify(['Новости моделей и лабораторий'], 'cost')[0], 'news')
eq('nothing matched -> unassigned', cb.classify(['Темы в подписи нет'], 'cap u1')[0], cb.UNASSIGNED)
eq('tie goes to the under-served block', cb.classify(['Токены, стоимость, лимиты',
                                                      'Новости моделей и лабораторий'], '')[0], 'money')

import json, tempfile
tmpdir = tempfile.mkdtemp()
json.dump({'code': 'X', 'analysis_version': 'br-v1', 'model': 'm', 'block': 'trust', 'secondary': None,
           'reason_if_null': None, 'evidence': ['never verify'], 'about': 'A reel about checking answers.',
           'confidence': 'HIGH', 'disagrees_with_regex': True}, open(os.path.join(tmpdir, 'X.json'), 'w'))
rt = cb.route('X', ['Токены, стоимость, лимиты'], 'cost', agent_dir=tmpdir)
eq('agent file overrides regex', (rt['block'], rt['source'], rt['regex_block']), ('trust', 'agent', 'money'))
eq('agent about travels with the route', rt['about'], 'A reel about checking answers.')
eq('no agent file -> regex', cb.route('Y', ['Токены, стоимость, лимиты'], '', agent_dir=tmpdir)['source'], 'regex')
from engine import block_route as br
eq('br-v1 validator accepts the fixture', br.validate(json.load(open(os.path.join(tmpdir, 'X.json')))), [])
eq('br-v1 validator wants evidence', any('evidence' in e for e in br.validate(
   dict(json.load(open(os.path.join(tmpdir, 'X.json'))), evidence=[]))), True)

# ---------------------------------------------------------------- selection
picked, pool_n, rep_n = cards.select(con, today=TODAY)
by_code = {c['code']: c for c in picked}
blocks = [c['block'] for c in picked]
stage1 = [c for c in picked if c['stage'] == 1]
stage2 = [c for c in picked if c['stage'] == 2]

eq('pool size', pool_n, 18)
eq('shortlist never above 15', len(picked) <= cards.SHORTLIST, True)
eq('shortlist here: 14 (one slot unfillable under the cap)', len(picked), 14)
eq('stage 1: one per block that has a reel above norm', len(stage1), 8)
eq('stage 1 blocks are distinct', len({c['block'] for c in stage1}), 8)
eq('stage 1 skips Trust (its only reel is below norm)', 'trust' in {c['block'] for c in stage1}, False)
eq('stage 1 reels all beat their author norm', all(c['above_norm'] for c in stage1), True)
eq('stage 1 comes first, in block order', [c['block'] for c in stage1],
   [b for b in cb.ORDER if b != 'trust'])
eq('stage 1 takes the best of the block', by_code['B1CODE001']['stage'], 1)
eq('stage 2 fills 6 + the unused stage-1 slot', len(stage2), 6)
eq('stage 2 is ranked by shares + saves', [c['code'] for c in stage2][:2], ['N2CODE001', 'N3CODE001'])
eq('cap: at most 3 per block', max(blocks.count(b) for b in set(blocks)), 3)
eq('news capped at 3 despite six strong reels', blocks.count('news'), 3)
eq('n4 left out by the cap, not by strength', 'N4CODE001' in by_code, False)
eq('below-norm Trust reel reaches stage 2', by_code.get('N1CODE002', {}).get('stage'), 2)
eq('unassigned reel competes on strength', by_code.get('U1CODE001', {}).get('block'), cb.UNASSIGNED)
eq('block explains itself', 'best in block' in by_code['P1CODE001']['why'], True)
eq('below-norm card says so', "below the author's norm" in by_code['N1CODE002']['why'], True)
eq('format = block default', all(c['fmt'] == cb.default_format(c['block']) for c in picked), True)
eq('numbering is 1..n', [c['n'] for c in picked], list(range(1, len(picked) + 1)))
eq('no author without a reel above norm', 'z1' in {c['author'] for c in picked}, False)
eq('angle left empty for the human', {c['angle'] for c in picked}, {''})
eq('hook left empty for the human', {c['hook'] for c in picked}, {''})
eq('three shooting columns on every card',
   all(set(c['shot']) == {'in frame', 'on screen', 'in the banner'} for c in picked), True)

pool = cards._pool(con, TODAY)
eq('every pool reel has a block', all('block' in r for r in pool), True)
eq('all within freshness', max(r['age'] for r in pool) <= cards.FRESH_DAYS, True)
eq('rank = shares + saves', all(abs(r[cards.RANK] - ((r['resh_1k'] or 0) + (r['save_1k'] or 0))) < 1e-9
                                for r in pool), True)
eq('no off-genre topics', any(set(r['topics']) & cards.OFF_TOPICS for r in pool), False)

# a closed topic sinks a reel inside its block but does not remove it
posts.add(con, (TODAY - datetime.timedelta(days=5)).isoformat(), 'Topic N1', 'РАЗБОР')
picked2, _, _ = cards.select(con, TODAY)
s1_news = [c for c in picked2 if c['stage'] == 1 and c['block'] == 'news'][0]
eq('closed topic: block best moves to the next reel', s1_news['code'], 'N2CODE001')
codes2 = {c['code'] for c in picked2}
eq('closed-topic reel yields its cap slot to fresher news', ('N1CODE001' in codes2, 'N4CODE001' in codes2), (False, True))
eq('closed topic is a sink, not a ban: still in the pool',
   'N1CODE001' in {r['code'] for r in cards._pool(con, TODAY)}, True)

# a reference already used is never proposed again
posts.add(con, TODAY.isoformat(), 'other topic', 'РАЗБОР', ref='B1CODE001')
eq('used reference excluded', 'B1CODE001' in {r['code'] for r in cards._pool(con, TODAY)}, False)

# stage 3 rule is checked, not enforced: the human picks in Notion
eq('pick rule constants', (cards.PICK, cards.PICK_PER_BLOCK), (5, 2))
week = cards.save(con, picked)
con.execute("UPDATE cards SET status='Shot' WHERE week=? AND code IN ('N1CODE001','N2CODE001','N3CODE001')", (week,))
con.commit()
eq('over-picked block reported', cards.pick_violations(con, week), {'news': 3})

con.close(); os.remove(TMP)
print('\n' + ('TEST PASSED' if not fail else f'FAILED: {fail}'))
sys.exit(1 if fail else 0)
