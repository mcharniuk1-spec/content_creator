#!/usr/bin/env python3
"""Проверка здоровья базы. Не сверка с прошлым, а инварианты, которые обязаны держаться.

    python3 check.py

Раньше здесь сверялись числа с августовскими JSON. Это перестало работать в тот момент,
когда база зажила своей жизнью: набор растёт, темы дописываются, оценки пересчитываются.
Теперь проверяется не «ровно столько же», а «не может быть иначе».
"""
import os, sys
from db import connect, DB_PATH, safe_code

con = connect()
one = lambda s, *a: con.execute(s, a).fetchone()[0]
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
ok = bad = 0


def check(name, got, want, note=''):
    global ok, bad
    good = got == want
    ok += good; bad += not good
    print(f"  {'✓' if good else '✗'} {name:<46} {str(got):>8}   ожидалось {str(want):<8} {note}")


print('\nСВЯЗНОСТЬ')
check('оценок без ролика', one("""SELECT COUNT(*) FROM scores s
    LEFT JOIN reels r USING(snapshot_id,code) WHERE r.code IS NULL"""), 0)
check('роликов от аккаунта вне базы', one("""SELECT COUNT(DISTINCT r.pk_user) FROM reels r
    LEFT JOIN accounts a ON a.pk=r.pk_user WHERE a.pk IS NULL"""), 0)
check('карточек без ролика', one("""SELECT COUNT(*) FROM cards c
    LEFT JOIN reels r ON r.code=c.code WHERE r.code IS NULL"""), 0)
check('метрик без публикации', one("""SELECT COUNT(*) FROM our_metrics m
    LEFT JOIN our_posts p ON p.id=m.post_id WHERE p.id IS NULL"""), 0)
check('кадров без файла на диске', sum(
    1 for (p,) in con.execute('SELECT path FROM frames') if not os.path.exists(f'{D}/../{p}')), 0)
check('листов без файла', sum(
    1 for (p,) in con.execute('SELECT sheet FROM deepdives WHERE sheet IS NOT NULL')
    if not os.path.exists(f'{D}/../{p}')), 0)

print('\nПРАВИЛА НАБОРА')
check('у всех в наборе проставлена тема',
      one("SELECT COUNT(*) FROM accounts WHERE status='active' AND tag IS NULL"), 0)
check('у каждого отсеянного записана причина',
      one("SELECT COUNT(*) FROM accounts WHERE status IN ('out','rejected') AND why_out IS NULL"), 0)
check('у выбывших проставлена дата',
      one("SELECT COUNT(*) FROM accounts WHERE status='dropped' AND dropped_at IS NULL"), 0)
check('непригодные не попадают в отбор', one("""SELECT COUNT(*) FROM cards c
    JOIN deepdives d ON d.code=c.code WHERE d.suitable=0 AND c.status<>'вычеркнута'"""), 0)

print('\nДАННЫЕ')
check('коды роликов проходят формат',
      sum(1 for (c,) in con.execute('SELECT DISTINCT code FROM reels') if not safe_code(c)), 0)
check('у каждой темы указан источник', one("SELECT COUNT(*) FROM topics WHERE source IS NULL"), 0)
check('у каждой оценки указаны веса', one('SELECT COUNT(*) FROM scores WHERE weights IS NULL'), 0)
check('расход сходится с ценой единицы',
      round(one('SELECT SUM(usd) FROM spend') or 0, 2),
      round(one('SELECT SUM(units*price) FROM spend') or 0, 2),
      f"{one('SELECT SUM(units) FROM spend') or 0} единиц")
check('незавершённых снимков нет',
      one('SELECT COUNT(*) FROM snapshots WHERE done=0'), 0,
      'частичный сбор не должен считаться снимком')
check('sqlite integrity_check', one('PRAGMA integrity_check'), 'ok')

print('\nЧТО В БАЗЕ')
for name, q in (('аккаунтов в наборе', "SELECT COUNT(*) FROM accounts WHERE status='active'"),
                ('кандидатов', "SELECT COUNT(*) FROM accounts WHERE status='candidate'"),
                ('снимков', 'SELECT COUNT(*) FROM snapshots WHERE done=1'),
                ('роликов', 'SELECT COUNT(*) FROM reels'),
                ('оценок', 'SELECT COUNT(*) FROM scores'),
                ('размечено тем', 'SELECT COUNT(DISTINCT code) FROM topics'),
                ('разборов', 'SELECT COUNT(*) FROM deepdives'),
                ('из них непригодных', 'SELECT COUNT(*) FROM deepdives WHERE suitable=0'),
                ('расшифровок', "SELECT COUNT(*) FROM transcripts WHERE text<>''"),
                ('карточек', 'SELECT COUNT(*) FROM cards'),
                ('наших публикаций', 'SELECT COUNT(*) FROM our_posts'),
                ('записей в журнале', 'SELECT COUNT(*) FROM tool_log')):
    print(f'  {name:<24} {one(q):>6}')

print(f"\n{'ВСЁ СОШЛОСЬ' if not bad else f'РАСХОЖДЕНИЙ: {bad}'}  ({ok} проверок)   "
      f'{os.path.getsize(DB_PATH) / 1048576:.1f} МБ\n')
sys.exit(1 if bad else 0)
