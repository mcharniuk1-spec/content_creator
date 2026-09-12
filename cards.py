#!/usr/bin/env python3
"""Карточки под съёмку: отбор кандидатов и фактура. SPEC §4.6, правила — RULES.md §2.

    python3 cards.py                    предложить карточки и записать их в базу
    python3 cards.py --dry              показать, ничего не записывая
    python3 cards.py angle 3 "текст"    вписать угол в карточку №3
    python3 cards.py hook 3 "текст"     то же для хука
    python3 cards.py show               что сейчас в карточках недели
    python3 cards.py drop 3             вычеркнуть карточку

Машина отбирает и собирает фактуру: референс, метрики, контактный лист, склейки, темы,
расшифровку, три колонки съёмки и каркас описания. Угол и хук предлагает агент, читая
кадры и расшифровку, — эти поля дописываются командами выше, а не правкой исходника.
"""
import datetime, json, pathlib, sys
from db import connect
from posts import closed_topics

D = pathlib.Path(__file__).parent / 'data'
FRESH_DAYS = 30         # было 14; решение Миши 12 сентября 2026
PER_FORMAT = 3          # предлагаем с запасом, вычёркивает человек
MIN_MULT = 1.5          # автор попадает в пул, если хотя бы один его ролик в окне превысил норму
DUR_MIN, DUR_MAX = 20, 120   # за этими границами жанр другой, приём не переносится
ONE_PER_AUTHOR = False  # решение Миши 12 сентября 2026: у автора смотрим все ролики окна,
                        # не только один; в карточки может попасть и его ролик ниже нормы
RANK = 'hi_intent'      # пересылки + сохранения на тысячу — одна линейка для всех трёх форматов

# Чего не берём никогда. Основание — POSITIONING.md §5 и §8, список «M2 Lab is not»
# и «Do not publish». Делится на две причины, потому что и лечится по-разному.

# Первая: не наш жанр вообще.
OFF_TOPICS = {
    'Мемы', 'Развлечение и конспирология', 'Виральные видеоэффекты',
    'Личное, мотивация, влог', 'Карьера, резюме, найм', 'Стартапы и венчур',
    # «make money with AI» — прямо назван в списке, чем M2 Lab не является
    'AI-агентство как бизнес', 'Бесплатный доступ и обход платы',
}

# Вторая: техническая территория. Из отбора НЕ исключает — референс оттуда часто даёт
# лучший материал, если его повернуть. Пометка нужна агенту: у такого ролика тема автора
# заведомо не совпадает с нашей, и угол придётся строить, а не пересказывать.
DEV_TOPICS = {
    'Программирование и код', 'Готовый репозиторий с GitHub',
    'Сборка агентов и мультиагентные системы', 'Память и контекст агентов',
    'Claude Code: скиллы, плагины, команды', 'Токены, стоимость, лимиты',
    'Новости моделей и лабораторий', 'Дизайн и сайты через AI',
    'AI-видео и производство контента',
}
# Не темы, а заглушки для нераспознанного: для Teardown их повторяемость ничего не значит.
NOT_TOPICS = {'Темы в подписи нет', 'Только призыв, без темы в подписи'}

# Как формат отбирает и как в нём снимают. Основание — RULES.md §2 и SPEC §7.
# Ранжирование во всех трёх форматах одно: пересылки + сохранения на тысячу (RANK).
# Формат решает, о чём мы говорим, а не по какой метрике смотрим.
FORMATS = {
    'M2 Radar': dict(
        slots=2, rank=RANK, signal='share + save',
        looks='new model, tool, trend, viral demo',
        frame='one static shot, presenter fully in frame',
        screen='full-frame insert: before and after, one number',
        banner='a number in the banner, held for the whole reel'),
    'M2 Builds': dict(
        slots=2, rank=RANK, signal='share + save, then follow',
        looks='builds, tests, tool comparisons',
        frame='own desk and rig, shot in one take',
        screen='terminal or interface where the break is visible',
        banner='what we built and the step where it broke'),
    'M2 Teardown': dict(
        slots=1, rank=RANK, signal='share + save, then search',
        looks='a repeated business process: ours, an industry one, or a viewer-sent one',
        frame='the process in frame: phone, laptop, paper',
        screen='the steps listed one at a time',
        banner='the cost figure: what this runs you per week'),
}


def _pool(con, today):
    """Свежие, пригодные, не использованные ролики авторов, у которых в окне есть ролик
    выше своей нормы. Решение Миши 12 сентября 2026: смотрим все ролики такого автора,
    не только выстреливший — из пяти его роликов в карточку может пойти и неудачный."""
    edge = int(datetime.datetime.combine(today - datetime.timedelta(days=FRESH_DAYS),
                                         datetime.time()).timestamp())
    closed = closed_topics(con, today=today)   # закрытые темы не выбрасываем, а опускаем вниз
    used = {r[0] for r in con.execute(
        'SELECT ref_code FROM our_posts WHERE ref_code IS NOT NULL')}
    # решения из Notion: отклонённое не предлагаем заново, снятое и опубликованное тоже
    decided = {r[0] for r in con.execute(
        """SELECT code FROM cards WHERE status IN ('Not taking','Shot','Published','вычеркнута')""")}
    used |= decided
    rows = con.execute("""
        SELECT r.code, r.username, r.play, r.resh, r.save, r.comm, r.dur, r.ts, r.cap,
               s.z, s.resh_1k, s.save_1k, s.author_median_play, s.baseline_n,
               d.cuts_ps, d.sheet, d.suitable,
               (SELECT words FROM transcripts t WHERE t.code=r.code) words
        FROM reels r
        JOIN scores s USING (snapshot_id, code)
        JOIN accounts a ON a.pk = r.pk_user AND a.status = 'active'
        LEFT JOIN deepdives d ON d.code = r.code
        WHERE r.snapshot_id = (SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
          AND s.eligible = 1 AND s.weights = 'ig' AND r.ts >= ?
          AND (d.suitable IS NULL OR d.suitable = 1)""", (edge,)).fetchall()
    out = []
    qualifying = set()                        # авторы с хотя бы одним роликом выше нормы в окне
    for r in rows:
        if r['author_median_play'] and r['play'] / r['author_median_play'] >= MIN_MULT:
            qualifying.add(r['username'])
    for r in rows:
        if r['code'] in used:
            continue
        if r['username'] not in qualifying:       # ни один ролик автора не превысил его норму
            continue
        topics = [t[0] for t in con.execute('SELECT topic FROM topics WHERE code=?', (r['code'],))]
        if set(topics) & OFF_TOPICS:              # не наш жанр
            continue
        # Тема референса не дисквалифицирует: мы смотрим, что снимают другие, и
        # поворачиваем это под свой угол. Технический ролик может дать отличную карточку
        # для SME — решает не тема автора, а способность её повернуть, и это проверяет
        # человек по обязательному фильтру, а не regex по словарю тем.
        if not (DUR_MIN <= (r['dur'] or 0) <= DUR_MAX):
            continue
        mult = round(r['play'] / r['author_median_play'], 1) if r['author_median_play'] else None
        d = dict(r); d['topics'] = topics; d['mult'] = mult
        d['above_norm'] = bool(mult and mult >= MIN_MULT)
        d[RANK] = (r['resh_1k'] or 0) + (r['save_1k'] or 0)
        d['age'] = (today - datetime.date.fromtimestamp(r['ts'])).days
        # доля тем ролика, уже закрытых нами: 1.0 — снимали ровно об этом, 0 — тема свежая
        d['closed_share'] = (len([t for t in topics if t in closed]) / len(topics)) if topics else 0
        out.append(d)
    return out


def _repeated_topics(pool, min_authors=3):
    """Справочно: темы, повторившиеся у нескольких авторов. С 12 сентября 2026 Teardown
    по ним НЕ отбирается (решение Миши: слишком абстрактный признак, ранжируем по
    пересылкам + сохранениям, как и остальные форматы); счётчик печатается как сигнал спроса."""
    by = {}
    for r in pool:
        for t in r['topics']:
            if t not in NOT_TOPICS:
                by.setdefault(t, set()).add(r['username'])
    return {t for t, a in by.items() if len(a) >= min_authors}


def select(con, today=None):
    today = today or datetime.date.today()
    pool = _pool(con, today)
    repeated = _repeated_topics(pool)
    picked, seen, authors = [], set(), set()
    fallback = False
    for fmt, cfg in FORMATS.items():
        cand = [r for r in pool if r['code'] not in seen]
        # сначала по свежести темы, потом по сигналу формата: жёсткое исключение опустошало
        # пул за два месяца — при 30 закрытых темах из 27 оставалось меньше сорока роликов
        cand.sort(key=lambda r: (r['closed_share'], -(r[cfg['rank']] or 0)))
        taken = 0
        for r in cand:
            if taken >= PER_FORMAT:
                break
            if ONE_PER_AUTHOR and r['username'] in authors:
                continue
            seen.add(r['code']); authors.add(r['username']); taken += 1
            picked.append(_card(r, fmt, cfg, len(picked) + 1))
    if len(picked) < PER_FORMAT:               # пул опустел — это сигнал, а не тишина
        fallback = True
    return picked, len(pool), len(repeated)


def _card(r, fmt, cfg, i):
    """Фактура карточки. angle и hook человек пишет сам — это не выборка."""
    facts = []
    if r['mult']:
        facts.append(f"{r['mult']}× this author's own norm "
                     f"({r['play']:,} against {r['author_median_play']:,})".replace(',', ' '))
        if not r.get('above_norm'):
            facts.append("below the author's norm — taken because another reel of theirs "
                         "in the window beat it")
    if r.get(RANK):
        facts.append(f"{r[RANK]:.0f} shares + saves per thousand")
    if r['resh_1k']:
        facts.append(f"{r['resh_1k']:.0f} shares per thousand")
    if r['save_1k']:
        facts.append(f"{r['save_1k']:.0f} saves per thousand")
    if r['cuts_ps'] is not None:
        facts.append('shot in one take' if r['cuts_ps'] < 0.02 else
                     f"{r['cuts_ps']:.2f} cuts per second")
    facts.append(f"{r['dur']:.0f} seconds")
    if r.get('closed_share'):
        facts.append('we already covered this topic in the last six weeks'
                     if r['closed_share'] == 1 else 'part of its topics we already covered')
    return dict(
        n=i, code=r['code'], fmt=fmt, ref=f"https://instagram.com/reel/{r['code']}",
        author=r['username'], age=r['age'], topics=r['topics'],
        why=' · '.join(facts), signal=cfg['signal'], sheet=r['sheet'],
        words=r['words'], cap=(r['cap'] or '')[:400],
        shot={'in frame': cfg['frame'], 'on screen': cfg['screen'], 'in the banner': cfg['banner']},
        caption={'sharpen for the query': r['topics'][0] if r['topics'] else '—',
                 'must contain': 'process, cost, what changed',
                 'first line': 'written as a search query'},
        angle='', hook='', goal='', lead='', pri=None)


def save(con, picked, week=None):
    """Фактура — в базу сразу. Угол и хук дописываются потом, поверх этих же строк."""
    week = week or datetime.date.today().isoformat()
    for c in picked:
        con.execute("""INSERT INTO cards
            (week,code,fmt,pri,lead,why,angle,hook,shot_frame,shot_screen,shot_banner,
             caption,goal,status)
            VALUES (?,?,?,?,NULL,?,'','',?,?,?,?,'','draft')
            ON CONFLICT(week,code) DO UPDATE SET
              fmt=excluded.fmt, pri=excluded.pri, why=excluded.why,
              shot_frame=excluded.shot_frame, shot_screen=excluded.shot_screen,
              shot_banner=excluded.shot_banner, caption=excluded.caption""",
            (week, c['code'], c['fmt'], c['n'], c['why'],
             c['shot']['in frame'], c['shot']['on screen'], c['shot']['in the banner'],
             ' · '.join(f'{k}: {v}' for k, v in c['caption'].items())))
    con.commit()
    return week


def fill(con, field, n, text, week=None):
    """Вписать угол или хук в карточку по её номеру."""
    if field not in ('angle', 'hook', 'lead', 'goal'):
        raise SystemExit('поле: angle, hook, lead или goal')
    week = week or con.execute('SELECT MAX(week) FROM cards').fetchone()[0]
    r = con.execute('SELECT id FROM cards WHERE week=? AND pri=?', (week, int(n))).fetchone()
    if not r:
        raise SystemExit(f'карточки №{n} за {week} нет')
    con.execute(f'UPDATE cards SET {field}=? WHERE id=?', (text, r['id']))
    con.commit()
    return week


def show(con, week=None):
    week = week or con.execute('SELECT MAX(week) FROM cards').fetchone()[0]
    if not week:
        print('карточек ещё нет'); return
    rows = con.execute("""SELECT c.pri, c.fmt, c.code, c.angle, c.hook, c.status, r.username
        FROM cards c LEFT JOIN reels r ON r.code=c.code
        WHERE c.week=? GROUP BY c.code ORDER BY c.pri""", (week,)).fetchall()
    print(f'карточки недели {week}: {len(rows)}\n')
    for r in rows:
        mark = '✓' if r['angle'] else ' '
        print(f"  {mark} {r['pri']:>2}. {r['fmt']:<12} {(r['username'] or '—'):<22} "
              f"{r['status']:<10} {'угол есть' if r['angle'] else 'угла нет'}")
    n = sum(1 for r in rows if not r['angle'])
    if n:
        print(f'\nбез угла: {n}. Вписать: python3 cards.py angle НОМЕР "текст"')


if __name__ == '__main__':
    con = connect()
    a = sys.argv[1:]
    if a and a[0] in ('angle', 'hook', 'lead', 'goal'):
        w = fill(con, a[0], a[1], a[2])
        print(f'{a[0]} записан в карточку №{a[1]} недели {w}')
    elif a and a[0] == 'show':
        show(con)
    elif a and a[0] == 'drop':
        week = con.execute('SELECT MAX(week) FROM cards').fetchone()[0]
        con.execute("UPDATE cards SET status='вычеркнута' WHERE week=? AND pri=?",
                    (week, int(a[1])))
        con.commit()
        print(f'карточка №{a[1]} вычеркнута')
    else:
        picked, pool_n, rep_n = select(con)
        print(f'кандидатов в окне {FRESH_DAYS} дней: {pool_n}   '
              f'тем, повторившихся у нескольких авторов (справочно): {rep_n}\n')
        for c in picked:
            print(f"  {c['n']:>2}. {c['fmt']:<12} {c['author']:<22} {c['age']:>2} дн.  {c['why']}")
            print(f"      темы: {', '.join(c['topics']) or '—'}")
        if '--dry' not in sys.argv:
            w = save(con, picked)
            print(f'\nзаписано в базу на неделю {w}. Угол и хук: '
                  f'python3 cards.py angle НОМЕР "текст"')
