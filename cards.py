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
FRESH_DAYS = 14
PER_FORMAT = 3          # предлагаем с запасом, вычёркивает человек
MIN_MULT = 1.5          # ролик обязан заметно превышать норму своего автора
DUR_MIN, DUR_MAX = 20, 120   # за этими границами жанр другой, приём не переносится
ONE_PER_AUTHOR = True   # иначе один автор занимает половину недели

# Вне ниши: развлечение ради развлечения. RULES.md §1.1.
OFF_TOPICS = {'Мемы', 'Развлечение и конспирология', 'Виральные видеоэффекты',
              'Личное, мотивация, влог'}
# Не темы, а заглушки для нераспознанного: для Teardown их повторяемость ничего не значит.
NOT_TOPICS = {'Темы в подписи нет', 'Только призыв, без темы в подписи'}

# Как формат отбирает и как в нём снимают. Основание — RULES.md §2 и SPEC §7.
FORMATS = {
    'M2 Radar': dict(
        slots=2, rank='resh_1k', signal='пересылка',
        looks='новая модель, инструмент, тренд, вирусное демо',
        frame='один статичный план, ведущий в кадре целиком',
        screen='полноэкранная вставка: до и после одним числом',
        banner='постоянная плашка с числом, висит весь ролик'),
    'M2 Builds': dict(
        slots=2, rank='save_1k', signal='сохранение и подписка',
        looks='сборка, тест, сравнение инструментов',
        frame='свой стол и стенд, съёмка одним планом',
        screen='терминал или интерфейс, где видно поломку',
        banner='что собирали и на каком шаге сломалось'),
    'M2 Teardown': dict(
        slots=1, rank='save_1k', signal='сохранение и поиск',
        looks='тема, повторившаяся у нескольких авторов',
        frame='процесс в кадре: телефон, ноутбук, бумага',
        screen='шаги процесса списком, по одному',
        banner='цифра стоимости: сколько это стоит в неделю'),
}


def _pool(con, today):
    """Свежие, прошедшие порог, пригодные, не из закрытых тем, не использованные."""
    edge = int(datetime.datetime.combine(today - datetime.timedelta(days=FRESH_DAYS),
                                         datetime.time()).timestamp())
    closed = closed_topics(con, today=today)   # закрытые темы не выбрасываем, а опускаем вниз
    used = {r[0] for r in con.execute(
        'SELECT ref_code FROM our_posts WHERE ref_code IS NOT NULL')}
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
    for r in rows:
        if r['code'] in used:
            continue
        topics = [t[0] for t in con.execute('SELECT topic FROM topics WHERE code=?', (r['code'],))]
        if set(topics) & OFF_TOPICS:              # развлечение — соседняя ниша
            continue
        if not (DUR_MIN <= (r['dur'] or 0) <= DUR_MAX):
            continue
        mult = round(r['play'] / r['author_median_play'], 1) if r['author_median_play'] else None
        if not mult or mult < MIN_MULT:           # не превысил свою же норму — не референс
            continue
        d = dict(r); d['topics'] = topics; d['mult'] = mult
        d['age'] = (today - datetime.date.fromtimestamp(r['ts'])).days
        # доля тем ролика, уже закрытых нами: 1.0 — снимали ровно об этом, 0 — тема свежая
        d['closed_share'] = (len([t for t in topics if t in closed]) / len(topics)) if topics else 0
        out.append(d)
    return out


def _repeated_topics(pool, min_authors=3):
    """Для Teardown: темы, которые повторились у нескольких авторов, а не выстрелили раз."""
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
        if fmt == 'M2 Teardown':
            cand = [r for r in cand if set(r['topics']) & repeated]
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
        facts.append(f"{r['mult']}× нормы своего автора ({r['play']:,} против {r['author_median_play']:,})"
                     .replace(',', ' '))
    if r['resh_1k']:
        facts.append(f"{r['resh_1k']:.0f} пересылок на тысячу")
    if r['save_1k']:
        facts.append(f"{r['save_1k']:.0f} сохранений на тысячу")
    if r['cuts_ps'] is not None:
        facts.append('снят одним планом' if r['cuts_ps'] < 0.02 else
                     f"склеек {r['cuts_ps']:.2f} в секунду")
    facts.append(f"{r['dur']:.0f} секунд")
    if r.get('closed_share'):
        facts.append(f"тему мы уже закрывали за последние {6} недель"
                     if r['closed_share'] == 1 else 'часть тем уже закрывали')
    return dict(
        n=i, code=r['code'], fmt=fmt, ref=f"https://instagram.com/reel/{r['code']}",
        author=r['username'], age=r['age'], topics=r['topics'],
        why=' · '.join(facts), signal=cfg['signal'], sheet=r['sheet'],
        words=r['words'], cap=(r['cap'] or '')[:400],
        shot={'в кадре': cfg['frame'], 'на экране': cfg['screen'], 'в плашке': cfg['banner']},
        caption={'затачиваем под запрос': r['topics'][0] if r['topics'] else '—',
                 'обязаны быть слова': 'process, cost, what changed',
                 'первая строка': 'формулируется как поисковый запрос'},
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
             c['shot']['в кадре'], c['shot']['на экране'], c['shot']['в плашке'],
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
              f'повторяющихся тем для Teardown: {rep_n}\n')
        for c in picked:
            print(f"  {c['n']:>2}. {c['fmt']:<12} {c['author']:<22} {c['age']:>2} дн.  {c['why']}")
            print(f"      темы: {', '.join(c['topics']) or '—'}")
        if '--dry' not in sys.argv:
            w = save(con, picked)
            print(f'\nзаписано в базу на неделю {w}. Угол и хук: '
                  f'python3 cards.py angle НОМЕР "текст"')
