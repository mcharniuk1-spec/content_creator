#!/usr/bin/env python3
"""Разметка кандидатов по теме. Читается биография, решение — человеческое.

    python3 tag_candidates.py            показать предложение
    python3 tag_candidates.py --apply    записать в базу

Критерий один — тема аккаунта, не число подписчиков (RULES.md §1):
берём внедрение AI в рабочий процесс — агенты, воркфлоу, операции, инструменты для работы,
экономика внедрения. С 8 сентября сюда же входят обучающие и информативные аккаунты,
если они учат применению в работе: как писать промпт, как собрать процесс, что сколько стоит.
Не берём объяснение устройства моделей, ежедневные новостные ленты, «заработок на AI»,
трейдинг и финансы, личный бренд и карьеру, креатив и дизайн без бизнес-угла,
юмор и пародии, неанглоязычные аккаунты.
"""
import sys
from db import connect

# Прочитано по биографиям. Каждое решение — с основанием.
CORE = {
    'harpercarrollai':  'обучение нетехнических с нуля — с 8 сентября в скоупе',
    'soojintech':       'снимает страх перед AI у новичков — наша аудитория 0–6',
    'sanji.chien':      'туториалы и разборы под рабочую задачу',
    'myrasayed_':       'продуктовый опыт, объясняет применение в работе',
    'chriswinfield':    'промпты под рабочую задачу — «хватит получать мусор от AI»',
    'chase.h.ai':      'Claude Code и разбор инструментов под работу',
    'askdatadawn':     'AI workflows для аналитиков — рабочий процесс, а не обзор',
    'protips.ai':      'автоматизация рутины, «automate the grind»',
    'chris.raroque':   'собирает приложения соло и документирует сборку',
    'josesiles.data':  'data-инженер в Nestlé — внедрение внутри компании',
    'itsthatlady.dev': 'инструменты и сборка, семь лет разработки, ex-GitHub',
    'nathanhodgson.ai': 'инструменты под продуктивность, работал с Google, Meta, OpenAI, Anthropic',
    'damini.knows':    'AI, инструменты, системы — с уклоном в бизнес',
    'thetechniko':     'тестирует инструменты до того, как на них потратятся',
}

# Пограничные: тема рядом, но не наша. Держим в отказе с причиной, чтобы не пересматривать по кругу.
NEAR = {
    'aasifcodes':      'обучение data и AI',
    'drcintas':        'профессор, образовательный контент',
    'yleintech':       'AI и тех вообще',
    'hasantoxr':       'AI-образование',
    'aidisruptor':     'ежедневные AI-новости',
    'alex.snippet':    'программирование вообще',
    'growthforbreakfast': 'разборы брендов без AI',
    'robonuggets':     '«learn & earn» — соседняя ниша заработка',
}


def report(con):
    rows = con.execute("""SELECT username, follower_count, biography, is_private FROM accounts
        WHERE status='candidate' AND follower_count IS NOT NULL""").fetchall()
    passed = [r for r in rows if not r['is_private'] and 5000 <= r['follower_count'] <= 1_000_000]
    core = [r for r in passed if r['username'] in CORE]
    print(f'кандидатов с профилем {len(rows)}, прошли пороги {len(passed)}\n')
    print(f'В НАБОР — {len(core)}:\n')
    for r in sorted(core, key=lambda x: -x['follower_count']):
        print(f"  {r['username']:<20} {r['follower_count']:>7,}".replace(',', ' ')
              + f"   {CORE[r['username']]}")
    print(f'\nРЯДОМ, НО НЕ БЕРЁМ — {len(NEAR)}:\n')
    for u, why in NEAR.items():
        print(f'  {u:<20} {why}')
    print(f'\nОСТАЛЬНЫЕ {len(passed) - len(core) - len(NEAR)} — вне ниши: трейдинг и финансы, '
          f'личный бренд и карьера,\nкреатив и дизайн, «заработок на AI», юмор, неанглоязычные.')
    return passed, core


def apply(con, passed, core):
    for r in passed:
        u = r['username']
        if u in CORE:
            con.execute("UPDATE accounts SET tag='core' WHERE username=?", (u,))
        else:
            con.execute("UPDATE accounts SET tag='out', status='out', why_out=? WHERE username=?",
                        (NEAR.get(u, 'вне ниши по биографии'), u))
    con.execute("""UPDATE accounts SET status='rejected',
        why_out = CASE WHEN is_private=1 THEN 'приватный'
                       WHEN follower_count < 5000 THEN 'мало подписчиков'
                       ELSE 'много подписчиков' END
        WHERE status='candidate' AND follower_count IS NOT NULL
          AND (is_private=1 OR follower_count < 5000 OR follower_count > 1000000)""")
    con.commit()
    print(f'\nразмечено. tag=core проставлен {len(core)} аккаунтам — в набор они попадут '
          f'командой ниже, после твоего слова:')
    print("  UPDATE accounts SET status='active' WHERE tag='core' AND status='candidate'")


if __name__ == '__main__':
    con = connect()
    passed, core = report(con)
    if '--apply' in sys.argv:
        apply(con, passed, core)
