#!/usr/bin/env python3
"""Карточки под съёмку: отбор кандидатов и фактура. SPEC §4.6, правила — RULES.md §2.

    python3 cards.py                    шортлист недели (15, три ступени) и запись в базу
    python3 cards.py --dry              показать, ничего не записывая
    python3 cards.py --dry --md FILE    то же плюс шортлист одним markdown-документом
    python3 cards.py angle 3 "текст"    вписать угол в карточку №3
    python3 cards.py hook 3 "текст"     то же для хука
    python3 cards.py show               что сейчас в карточках недели
    python3 cards.py drop 3             вычеркнуть карточку

Машина отбирает и собирает фактуру: референс, метрики, контактный лист, склейки, темы,
расшифровку, три колонки съёмки и каркас описания. Угол и хук предлагает агент, читая
кадры и расшифровку, — эти поля дописываются командами выше, а не правкой исходника.
"""
import datetime, json, math, pathlib, sys
from db import connect
from posts import closed_topics
import content_blocks as cb

D = pathlib.Path(__file__).parent / 'data'
FRESH_DAYS = 14         # 14 → 30 решением Миши 12 сентября 2026, обратно 14 сентября 2026:
                        # окно на 30 дней подняло пул с 119 до 596 кандидатов, и сервер
                        # не успевает его разбирать в отведённое прогону время
# Схема шортлиста, решение Миши 13 сентября 2026 (RULES.md §13): 15 роликов в три ступени.
SHORTLIST = 15          # столько присылаем на выбор
MAX_PER_BLOCK = 3       # потолок одного блока в пятнадцати (иначе новости заберут всё)
PICK = 5                # столько Миша выбирает из пятнадцати
PICK_PER_BLOCK = 2      # правило для его выбора: не больше двух из одного блока (проверяется, не навязывается)
MIN_MULT = 1.5          # автор попадает в пул, если хотя бы один его ролик в окне превысил норму
DUR_MIN, DUR_MAX = 20, 120   # за этими границами жанр другой, приём не переносится
ONE_PER_AUTHOR = False  # решение Миши 12 сентября 2026: у автора смотрим все ролики окна,
                        # не только один; в карточки может попасть и его ролик ниже нормы
RANK = 'hi_intent'      # пересылки + сохранения на тысячу — одна линейка для всех трёх форматов
# Два правила Миши от 13 сентября 2026 (вечер), RULES.md §13.7: без полной расшифровки и кадров
# ролик не существует для карточек — подписи недостаточно; и только английская речь.
MIN_COVERAGE = 0.9      # endpoint ratio threshold, not measured speech completeness
MIN_WORDS = 30          # editorial minimum; fewer words do not prove absence of speech
LANG = 'en'

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


def _pool(con, today, require_evidence=True):
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
    dropped = {'no_transcript': 0, 'no_frames': 0, 'not_english': 0}
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
        ev = evidence(con, r['code'])           # §13.7: полная расшифровка, кадры, английский
        if require_evidence:                     # deep.py acquires evidence without this filter
            if not ev['language_verified']:
                dropped['not_english'] += 1; continue
            if not ev['transcript']:
                dropped['no_transcript'] += 1; continue
            if not ev['frames']:
                dropped['no_frames'] += 1; continue
            if ev['lang'] != LANG:
                dropped['not_english'] += 1; continue
        mult = round(r['play'] / r['author_median_play'], 1) if r['author_median_play'] else None
        d = dict(r); d['topics'] = topics; d['mult'] = mult
        d['above_norm'] = bool(mult and mult >= MIN_MULT)
        d[RANK] = (r['resh_1k'] or 0) + (r['save_1k'] or 0)
        d['age'] = (today - datetime.date.fromtimestamp(r['ts'])).days
        # блок контента — ось отбора с 13 сентября 2026 (content_blocks.py)
        rt = cb.route(r['code'], topics, cb.reel_text(con, r['code'], r['cap']))
        if rt['source'] == 'agent' and rt.get('reason_if_null'):   # agent read it: off the niche or no text
            continue
        d['block'], d['block_evidence'], d['block_source'] = rt['block'], rt['evidence'], rt['source']
        d['about'], d['regex_block'], d['block_confidence'] = rt['about'], rt['regex_block'], rt['confidence']
        # доля тем ролика, уже закрытых нами: 1.0 — снимали ровно об этом, 0 — тема свежая
        d['closed_share'] = (len([t for t in topics if t in closed]) / len(topics)) if topics else 0
        d['evidence'] = ev
        out.append(d)
    _pool.dropped = dropped                    # печатается в CLI: сколько отсеяно и почему
    return out


def evidence(con, code):
    """Structural evidence gate, not acoustic or semantic acceptance.

    transcript_end_ratio is the last valid segment end / duration. It does not
    measure covered speech or prove English audio. `coverage` is a compatibility
    alias; legacy forced-English and ta-v1 language values remain unverified.
    """
    t = con.execute('SELECT lang, words, segments FROM transcripts WHERE code=?', (code,)).fetchone()
    words = (t['words'] if t else 0) or 0
    lang = (t['lang'] if t else None)
    dur = (con.execute('SELECT dur FROM reels WHERE code=? ORDER BY snapshot_id DESC LIMIT 1', (code,)).fetchone() or [0])[0] or 0
    end = 0.0
    timing_valid = False
    try:
        dur = float(dur)
        segs = json.loads(t['segments']) if t and t['segments'] else []
        if not math.isfinite(dur) or dur <= 0 or not isinstance(segs, list) or not segs:
            raise ValueError('missing valid duration/segments')
        previous_start = -1.0
        for segment in segs:
            if not isinstance(segment, dict):
                raise ValueError('segment must be an object')
            start_raw = segment.get('s', segment.get('start'))
            end_raw = segment.get('e', segment.get('end'))
            if isinstance(start_raw, bool) or isinstance(end_raw, bool):
                raise ValueError('boolean timestamp')
            start, stop = float(start_raw), float(end_raw)
            if not (math.isfinite(start) and math.isfinite(stop)
                    and 0 <= start < stop <= dur and start >= previous_start):
                raise ValueError('invalid or out-of-order timestamp')
            previous_start = start
            end = max(end, stop)
        timing_valid = True
    except (TypeError, ValueError, OverflowError):
        pass
    ratio = end / dur if timing_valid else 0.0
    # Old forced-en ASR and semantic text labels do not verify spoken language.
    # Only the acquisition language gate supplies positive provenance here.
    language_verified = False
    gate_decision = 'LANGUAGE_UNKNOWN'
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='language_gate'").fetchone():
        gate = con.execute('SELECT language,decision FROM language_gate WHERE code=?', (code,)).fetchone()
        if gate:
            lang, gate_decision = gate[0], gate[1]
            language_verified = gate_decision == 'ENGLISH_DETECTED' and lang == 'en'
    if not language_verified:
        lang = lang if gate_decision == 'EXCLUDED_NON_ENGLISH' else 'unknown'
    frames = con.execute('SELECT COUNT(*) FROM frames WHERE code=?', (code,)).fetchone()[0]
    return {'transcript': language_verified and timing_valid and ratio >= MIN_COVERAGE and words >= MIN_WORDS,
            'coverage': round(ratio, 2), 'transcript_end_ratio': ratio,
            'timing_valid': timing_valid, 'language_verified': language_verified, 'language_decision': gate_decision,
            'words': words, 'frames': frames, 'lang': lang}


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


def _strength(r):
    # сначала по свежести темы, потом по пересылкам + сохранениям: жёсткое исключение
    # закрытых тем опустошало пул за два месяца, поэтому они опускаются, а не выбрасываются
    return (r['closed_share'], -(r[RANK] or 0))


def select(con, today=None):
    """Шортлист недели в три ступени (решение Миши 13 сентября 2026, RULES.md §13).

    1. По одному на блок: лучший ролик блока среди тех, что превысили норму своего автора.
       Нет такого ролика — место не заполняется мусором, а уходит на ступень 2.
    2. Остаток до SHORTLIST по силе из любого блока, но не больше MAX_PER_BLOCK на блок.
       Если под потолком кандидатов не хватило, шортлист короче пятнадцати — это сигнал.
    3. Миша выбирает PICK из шортлиста, не больше PICK_PER_BLOCK из блока (pick_violations)."""
    today = today or datetime.date.today()
    pool = _pool(con, today)
    repeated = _repeated_topics(pool)
    picked, seen, per_block = [], set(), {}
    for bid in cb.ORDER:                                   # ступень 1
        cand = sorted((r for r in pool if r['block'] == bid and r['above_norm']), key=_strength)
        if not cand:
            continue
        r = cand[0]
        seen.add(r['code']); per_block[bid] = 1
        picked.append(_card(r, cb.default_format(bid), FORMATS[cb.default_format(bid)], len(picked) + 1,
                            stage=1, note=f'best in block {cb.label(bid)}'))
    rest = sorted((r for r in pool if r['code'] not in seen), key=_strength)   # ступень 2
    rank_no = 0
    for r in rest:
        if len(picked) >= SHORTLIST:
            break
        rank_no += 1
        if per_block.get(r['block'], 0) >= MAX_PER_BLOCK:
            continue
        per_block[r['block']] = per_block.get(r['block'], 0) + 1
        seen.add(r['code'])
        fmt = cb.default_format(r['block'])
        picked.append(_card(r, fmt, FORMATS[fmt], len(picked) + 1,
                            stage=2, note=f'#{rank_no} by strength this week'))
    return picked, len(pool), len(repeated)


def pick_violations(con, week=None):
    """Ступень 3, проверка: блоки, из которых взято больше PICK_PER_BLOCK карточек.
    Взятой считается карточка со статусом съёмки или публикации; решает человек в Notion."""
    week = week or con.execute('SELECT MAX(week) FROM cards').fetchone()[0]
    rows = con.execute("""SELECT block, COUNT(*) n FROM cards WHERE week=? AND
        status IN ('взята','Taking','Shot','Published') GROUP BY block""", (week,)).fetchall()
    return {r['block']: r['n'] for r in rows if r['n'] > PICK_PER_BLOCK}


def _card(r, fmt, cfg, i, stage=None, note=''):
    """Фактура карточки. angle и hook человек пишет сам — это не выборка."""
    facts = []
    if stage:
        facts.append(f"block {cb.label(r['block'])} · stage {stage}: {note}")
        ev = r.get('block_evidence') or {}
        if ev.get('tags') or ev.get('words'):
            src = 'agent' if r.get('block_source') == 'agent' else 'tags/regex'
            quoted = ev.get('tags', []) + [f'"{w}"' if src == 'agent' else w for w in ev.get('words', [])[:3]]
            facts.append(f'routed by {src}: ' + ', '.join(quoted)
                         + (f" ({r['block_confidence']})" if r.get('block_confidence') else ''))
        if r.get('about'):
            facts.append('about: ' + r['about'])
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
    # persona hint dropped 13 Sep 2026 (evening): blocks are the axis, personas are the example layer
    if r.get('closed_share'):
        facts.append('we already covered this topic in the last six weeks'
                     if r['closed_share'] == 1 else 'part of its topics we already covered')
    return dict(
        n=i, code=r['code'], fmt=fmt, ref=f"https://instagram.com/reel/{r['code']}",
        block=r.get('block') or cb.UNASSIGNED, stage=stage, above_norm=bool(r.get('above_norm')),
        about=r.get('about'), block_source=r.get('block_source'), stage_note=note,
        block_evidence=r.get('block_evidence'),
        author=r['username'], age=r['age'], topics=r['topics'],
        why=' · '.join(facts), signal=cfg['signal'], sheet=r['sheet'],
        words=r['words'], cap=(r['cap'] or '')[:400],
        shot={'in frame': cfg['frame'], 'on screen': cfg['screen'], 'in the banner': cfg['banner']},
        caption={'sharpen for the query': next((t for t in r['topics'] if t not in NOT_TOPICS), None)
                                          or r.get('about') or cb.label(r.get('block')),
                 'must contain': 'process, cost, what changed',
                 'first line': 'written as a search query'},
        angle='', hook='', goal='', lead='', pri=None)


def render_md(picked, pool_n, today=None):
    """The shortlist as one markdown document (engine.shortlist_adapt.render_md): selection facts
    plus, once adapted, what they shot / our version / how we shoot it."""
    from engine import shortlist_adapt
    return shortlist_adapt.render_md(picked, pool_n, today)


def save(con, picked, week=None):
    """Фактура — в базу сразу. Угол и хук дописываются потом, поверх этих же строк."""
    week = week or datetime.date.today().isoformat()
    for c in picked:
        con.execute("""INSERT INTO cards
            (week,code,fmt,pri,lead,why,angle,hook,shot_frame,shot_screen,shot_banner,
             caption,goal,status,block,stage)
            VALUES (?,?,?,?,NULL,?,'','',?,?,?,?,'','draft',?,?)
            ON CONFLICT(week,code) DO UPDATE SET
              fmt=excluded.fmt, pri=excluded.pri, why=excluded.why,
              shot_frame=excluded.shot_frame, shot_screen=excluded.shot_screen,
              shot_banner=excluded.shot_banner, caption=excluded.caption,
              block=excluded.block, stage=excluded.stage""",
            (week, c['code'], c['fmt'], c['n'], c['why'],
             c['shot']['in frame'], c['shot']['on screen'], c['shot']['in the banner'],
             ' · '.join(f'{k}: {v}' for k, v in c['caption'].items()),
             c.get('block'), c.get('stage')))
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
    rows = con.execute("""SELECT c.pri, c.fmt, c.code, c.angle, c.hook, c.status, c.block, c.stage,
               r.username
        FROM cards c LEFT JOIN reels r ON r.code=c.code
        WHERE c.week=? GROUP BY c.code ORDER BY c.pri""", (week,)).fetchall()
    print(f'карточки недели {week}: {len(rows)}  (выбрать {PICK}, не больше {PICK_PER_BLOCK} из блока)\n')
    for r in rows:
        mark = '✓' if r['angle'] else ' '
        print(f"  {mark} {r['pri']:>2}. s{r['stage'] or '-'} {cb.label(r['block']):<18} {r['fmt']:<12} "
              f"{(r['username'] or '—'):<22} {r['status']:<10} {'угол есть' if r['angle'] else 'угла нет'}")
    n = sum(1 for r in rows if not r['angle'])
    if n:
        print(f'\nбез угла: {n}. Вписать: python3 cards.py angle НОМЕР "текст"')
    over = pick_violations(con, week)
    if over:
        print('\nправило выбора нарушено, больше %d из блока: ' % PICK_PER_BLOCK
              + ', '.join(f'{cb.label(b)} {n}' for b, n in over.items()))


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
        dr = getattr(_pool, 'dropped', {})
        print(f'кандидатов в окне {FRESH_DAYS} дней: {pool_n}   '
              f'тем, повторившихся у нескольких авторов (справочно): {rep_n}')
        print(f"отсеяно по §13.7: без расшифровки {dr.get('no_transcript', 0)}, без кадров {dr.get('no_frames', 0)}, "
              f"не английский {dr.get('not_english', 0)}\n")
        print(f'шортлист {len(picked)} из {SHORTLIST}: ступень 1 — по одному на блок, '
              f'ступень 2 — по силе, потолок {MAX_PER_BLOCK} на блок; выбрать {PICK}\n')
        for c in picked:
            print(f"  {c['n']:>2}. s{c['stage']} {cb.label(c['block']):<18} {c['fmt']:<12} "
                  f"{c['author']:<22} {c['age']:>2} дн.  {c['why']}")
            print(f"      темы: {', '.join(c['topics']) or '—'}")
        if '--md' in sys.argv:
            out = pathlib.Path(sys.argv[sys.argv.index('--md') + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_md(picked, pool_n), encoding='utf-8')
            print(f'\nшортлист записан: {out}')
        if '--dry' not in sys.argv:
            w = save(con, picked)
            print(f'\nзаписано в базу на неделю {w}. Угол и хук: '
                  f'python3 cards.py angle НОМЕР "текст"')
