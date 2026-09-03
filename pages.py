#!/usr/bin/env python3
"""Три страницы недели вместо прежних пяти отчётов. SPEC §4.7.

    python3 pages.py            собрать все три
    python3 pages.py niche      только «что в нише»

1. niche.html  — что в нише: темы, сигналы, что сдвинулось. Листаешь.
2. shoot.html  — что снимаем: карточки. Работаешь.
3. radar.html  — набор, формула, топ-40. Проверяешь, на чём стоят цифры.

Все три самодостаточны: контактные листы вшиты в файл, наружу страница не ходит.
"""
import base64, datetime, html, pathlib, statistics, sys
import cards
from db import connect, safe_code

D = pathlib.Path(__file__).parent / 'data'
OUT = pathlib.Path(__file__).parent
WINDOW = 14
esc = html.escape
num = lambda n: f'{int(n):,}'.replace(',', ' ') if n is not None else '—'
med = lambda xs: statistics.median(xs) if xs else None

CSS = """
:root{--ground:#F6F7F9;--surface:#fff;--sunk:#ECEEF2;--ink:#14161C;--ink2:#3B4050;
--muted:#6A7085;--rule:#DDE0E8;--rule2:#E8EAF0;--acc:#2E3D70;--acc2:#E4E8F4;--ok:#256250}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--ground:#0F1116;--surface:#171A21;
--sunk:#1E2129;--ink:#E8EAF0;--ink2:#C0C5D2;--muted:#8B92A6;--rule:#2A2E38;--rule2:#22252D;
--acc:#8E9EDA;--acc2:#1A1F31;--ok:#6BB59B}}
*{box-sizing:border-box}body{margin:0;background:var(--ground);color:var(--ink);
font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.w{max-width:1060px;margin:0 auto;padding:0 24px 80px}
header{padding:48px 0 26px;border-bottom:1px solid var(--rule)}
.kick{font:500 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.14em;
text-transform:uppercase;color:var(--acc);display:flex;gap:12px;flex-wrap:wrap}
h1{font-size:clamp(30px,5vw,46px);line-height:1.05;letter-spacing:-.03em;margin:16px 0 0}
.sub{color:var(--ink2);max-width:640px;margin:14px 0 0}
section{margin-top:44px;padding-top:34px;border-top:1px solid var(--rule2)}
h2{font-size:clamp(20px,2.6vw,26px);line-height:1.15;letter-spacing:-.02em;margin:0 0 14px}
h3{font-size:17px;margin:24px 0 8px}p{margin:0 0 12px;max-width:660px}
.scroll{overflow-x:auto;border:1px solid var(--rule);border-radius:4px;background:var(--surface);margin:0 0 16px}
table{border-collapse:collapse;width:100%;font-size:14.5px;min-width:520px}
th{font:500 10px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
text-align:left;padding:11px 13px 8px;border-bottom:1px solid var(--rule);white-space:nowrap}
td{padding:9px 13px;border-bottom:1px solid var(--rule2);color:var(--ink2);vertical-align:top}
tbody tr:last-child td{border-bottom:0}td:first-child{color:var(--ink)}
td.n,th.n{text-align:right;font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums;
color:var(--ink);white-space:nowrap}
.box{background:var(--surface);border:1px solid var(--rule);border-left:3px solid var(--acc);
border-radius:4px;padding:16px 18px;margin:0 0 16px;max-width:680px}
.box b{display:block;font:500 10px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);margin-bottom:7px}.box p:last-child{margin-bottom:0}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:5px;margin:0 0 22px;overflow:hidden}
.chead{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;padding:15px 18px;
border-bottom:1px solid var(--rule2);background:var(--sunk)}
.cn{font:600 12px/1 ui-monospace,monospace;color:var(--acc)}
.fmt{font:500 11px/1 ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.cbody{padding:16px 18px}.cbody img{width:100%;border-radius:4px;display:block;margin:0 0 14px}
.f{display:grid;grid-template-columns:130px 1fr;gap:5px 14px;font-size:14.5px;margin:0 0 12px}
.f dt{font:500 10px/1.5 ui-monospace,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.f dd{margin:0;color:var(--ink2)}
.empty{color:var(--muted);font-style:italic}
.tc{font:400 12px/1.5 ui-monospace,monospace;color:var(--muted);margin:-8px 0 14px}
.tr{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 14px}
.tr>div{background:var(--sunk);border-radius:4px;padding:12px 14px}
.tr h4{font:500 10px/1 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
color:var(--acc);margin:0 0 8px}
.tr p{font-size:13.5px;line-height:1.5;margin:0;color:var(--ink2)}
.f dd b{font-weight:600;color:var(--ink)}
@media(max-width:760px){.tr{grid-template-columns:1fr}}
a{color:var(--acc)}footer{margin-top:48px;padding-top:20px;border-top:1px solid var(--rule);
font-size:13px;color:var(--muted)}
@media(max-width:640px){.f{grid-template-columns:1fr;gap:1px}.f dt{margin-top:8px}}
"""


def page(title, kick, h1, sub, body):
    return (f'<title>{esc(title)}</title><style>{CSS}</style><div class=w><header>'
            f'<div class=kick>{"".join(f"<span>{esc(k)}</span>" for k in kick)}</div>'
            f'<h1>{esc(h1)}</h1><p class=sub>{esc(sub)}</p></header>{body}'
            f'<footer>Собрано из data/radar.db · {datetime.date.today().isoformat()} · '
            f'страницу делает pages.py, цифры — score.py и cards.py</footer></div>')


def table(headers, rows, numeric=()):
    th = ''.join(f'<th{" class=n" if i in numeric else ""}>{esc(h)}</th>'
                 for i, h in enumerate(headers))
    tr = ''.join('<tr>' + ''.join(
        f'<td{" class=n" if i in numeric else ""}>{c}</td>' for i, c in enumerate(r)) + '</tr>'
        for r in rows)
    return f'<div class=scroll><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def _window(con, today):
    edge = int(datetime.datetime.combine(today - datetime.timedelta(days=WINDOW),
                                         datetime.time()).timestamp())
    return [dict(r) for r in con.execute("""
        SELECT r.code,r.username,r.play,r.resh,r.save,r.dur,r.ts,
               s.z,s.resh_1k,s.save_1k,s.author_median_play
        FROM reels r JOIN scores s USING(snapshot_id,code)
        JOIN accounts a ON a.pk=r.pk_user AND a.status='active'
        WHERE r.snapshot_id=(SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
          AND s.eligible=1 AND s.weights='ig' AND r.ts>=?""", (edge,))]


def _shift_block(con, snaps):
    """Что изменилось между снимками. До второго снимка так и говорим."""
    if snaps < 2:
        return ('<div class="box"><b>Что сдвинулось</b><p>Сравнивать пока не с чем: '
                'снимок один. Дельта появится со второго завершённого сбора.</p></div>')
    import delta
    two = delta.snapshots(con)
    cur, prev = two[0]['id'], two[1]['id']
    td = delta.topics_delta(con, cur, prev)
    new = [t for t in td if t['new'] and t['now'] >= 3]
    up = [t for t in td if t['d'] > 0 and not t['new']][:4]
    down = sorted([t for t in td if t['d'] < 0], key=lambda x: x['d'])[:4]
    hits_new, hits_gone = delta.authors_delta(con, cur, prev)
    fd = delta.followers_delta(con)[:5]
    row = lambda t: f"{esc(t['topic'])} {t['was']}→{t['now']}"
    parts = [f"<div class=\"box\"><b>Что сдвинулось · {two[1]['taken']} → {two[0]['taken']}</b>"]
    if new:
        parts.append('<p><strong>Темы, которых не было:</strong> '
                     + ' · '.join(f"{esc(t['topic'])} ({t['now']})" for t in new) + '</p>')
    if up:
        parts.append('<p><strong>Прибавили:</strong> ' + ' · '.join(row(t) for t in up) + '</p>')
    if down:
        parts.append('<p><strong>Убавили:</strong> ' + ' · '.join(row(t) for t in down) + '</p>')
    if hits_new:
        parts.append('<p><strong>Залетели впервые:</strong> '
                     + ', '.join(esc(u) for u in hits_new[:10]) + '</p>')
    if fd:
        parts.append('<p><strong>Растут:</strong> ' + ' · '.join(
            f"{esc(r['username'])} {r['pct']:+.1f}%" for r in fd) + '</p>')
    return ''.join(parts) + '</div>'


# ------------------------------------------------------------------ ниша ----
def niche(con, today=None):
    today = today or datetime.date.today()
    rows = _window(con, today)
    codes = {r['code']: r for r in rows}
    topics = {}
    for code, t in con.execute('SELECT code,topic FROM topics'):
        if code in codes:
            topics.setdefault(t, []).append(codes[code])
    snaps = con.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0]

    tr = []
    for t, rs in sorted(topics.items(), key=lambda kv: -(med([x['resh_1k'] or 0 for x in kv[1]]) or 0)):
        if len(rs) < 5 or t in cards.NOT_TOPICS:
            continue
        # пропуск — это «нет данных», а не ноль: сохранения отдаются не у всех роликов,
        # и нули занижали медиану темы и портили порядок
        resh = med([x['resh_1k'] for x in rs if x['resh_1k'] is not None])
        save = med([x['save_1k'] for x in rs if x['save_1k'] is not None])
        tr.append((esc(t), num(len(rs)), num(len({x['username'] for x in rs})),
                   f'{resh:.0f}' if resh is not None else '—',
                   f'{save:.0f}' if save is not None else '—',
                   f"{med([x['play'] / (x['author_median_play'] or 1) for x in rs]):.1f}×"))
    top = sorted(rows, key=lambda r: -(r['resh_1k'] if r['resh_1k'] is not None else -1))[:12]
    tt = [(f'<a href="https://instagram.com/reel/{esc(r["code"])}" '
           f'rel="noopener noreferrer">{esc(r["username"])}</a>',
           num(r['play']), f"{r['play'] / (r['author_median_play'] or 1):.1f}×",
           f"{r['resh_1k']:.0f}" if r['resh_1k'] is not None else '—',
           f"{r['save_1k']:.0f}" if r['save_1k'] is not None else '—', f"{r['dur']:.0f} с")
          for r in top]

    shift = _shift_block(con, snaps)
    body = (f'<section><h2>Темы окна</h2>'
            f'<p>Роликов в окне {len(rows)}, авторов {len({r["username"] for r in rows})}. '
            f'Темы меньше пяти роликов не показаны — на них ничего не видно.</p>'
            + table(['Тема', 'Роликов', 'Авторов', 'Пересылок/1k', 'Сохранений/1k', 'К норме автора'],
                    tr, numeric={1, 2, 3, 4, 5})
            + f'</section><section><h2>Что пересылали</h2>{shift}'
            + table(['Автор', 'Просмотров', 'К норме', 'Пересылок/1k', 'Сохранений/1k', 'Длина'],
                    tt, numeric={1, 2, 3, 4, 5}) + '</section>')
    return page('Что в нише', [f'окно {WINDOW} дней', f'снимков {snaps}',
                               today.isoformat()], 'Что в нише',
                'Темы, сигналы и верхушка окна. Листаешь, чтобы понять, о чём сейчас снимают.', body)


# --------------------------------------------------------------- снимаем ----
def shoot(con, today=None):
    """Карточки недели: фактура из базы, угол и хук — предложенные, не пустые."""
    today = today or datetime.date.today()
    import blocks
    week = con.execute('SELECT MAX(week) FROM cards').fetchone()[0]
    # снимок фиксируется явно: без этого пять карточек дают десять строк на двух снимках,
    # и цифра на карточке берётся из произвольной недели
    rows = con.execute("""SELECT c.*, r.username, r.play, r.dur, r.ts, r.cap,
            s.z, s.resh_1k, s.save_1k, s.author_median_play, d.cuts_ps, d.sheet
        FROM cards c
        JOIN reels r ON r.code = c.code
             AND r.snapshot_id = (SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
        JOIN scores s ON s.code = c.code AND s.snapshot_id = r.snapshot_id
             AND s.weights = 'ig'
        LEFT JOIN deepdives d ON d.code = c.code
        WHERE c.week = ? AND c.status <> 'вычеркнута'
        ORDER BY c.pri, c.fmt""", (week,)).fetchall()
    out = []
    for i, c in enumerate(rows, 1):
        age = (today - datetime.date.fromtimestamp(c['ts'])).days
        mult = c['play'] / (c['author_median_play'] or 1)
        sheet = ''
        p = OUT / (c['sheet'] or '')
        frames = (OUT / 'data' / 'frames').resolve()
        inside = c['sheet'] and p.exists() and str(p.resolve()).startswith(str(frames))
        if inside:
            sheet = ('<img alt="девять кадров ролика" src="data:image/jpeg;base64,'
                     + base64.b64encode(p.read_bytes()).decode() + '">')
        tcs = [r[0] for r in con.execute(
            'SELECT t_sec FROM frames WHERE code=? ORDER BY idx', (c['code'],))]
        tc = ('<p class=tc>кадры на ' + ', '.join(f'{t:g} с' for t in tcs if t is not None)
              + ' — четыре в зоне хука, пять дальше</p>') if tcs else ''
        b = blocks.blocks(con, c['code'])
        tr = ''
        if b:
            tr = '<div class=tr>' + ''.join(
                f'<div><h4>{ru} · {b["words"][k]} слов</h4><p>{esc(b[k]) or "—"}</p></div>'
                for k, ru in (('hook', 'Хук'), ('body', 'Тело'), ('tail', 'Концовка'))) + '</div>'
        f = lambda k, v: f'<dt>{esc(k)}</dt><dd>{v}</dd>'
        metrics = (f'{num(c["play"])} просмотров · {mult:.1f}× нормы автора · '
                   f'{c["resh_1k"] or 0:.0f} пересылок и {c["save_1k"] or 0:.0f} сохранений '
                   f'на тысячу · {c["dur"]:.0f} с · '
                   + ('снят одним планом' if (c['cuts_ps'] or 0) < 0.02
                      else f'склеек {c["cuts_ps"]:.2f} в секунду'))
        out.append(
            f'<div class=card><div class=chead><span class=cn>Карточка {i:02d}</span>'
            f'<span class=fmt>{esc(c["fmt"])}</span><span class=fmt>приоритет {c["pri"]}</span>'
            f'<span class=fmt>ведёт {esc(c["lead"] or "—")}</span></div>'
            f'<div class=cbody>{sheet}{tc}'
            f'<dl class=f>'
            + f('референс', f'<a href="https://instagram.com/reel/{esc(c["code"])}" '
                            f'rel="noopener noreferrer">{esc(c["username"])}</a> · {age} дн. назад')
            + f('цифры', esc(metrics))
            + f('почему сработало', esc(c['why']))
            + '</dl>' + tr
            + '<dl class=f>'
            + f('наш угол', f'<b>{esc(c["angle"])}</b>')
            + f('черновик хука', f'<b>{esc(c["hook"])}</b>')
            + f('что в кадре', esc(c['shot_frame']))
            + f('что на экране', esc(c['shot_screen']))
            + f('что в плашке', esc(c['shot_banner']))
            + f('каркас описания', esc(c['caption']))
            + f('к чему ведём', '<span class=empty>не решено — открытый вопрос спецификации</span>')
            + '</dl></div></div>')
    stale = ''
    if week and (today - datetime.date.fromisoformat(week)).days > 7:
        stale = ('<div class="box"><b>Карточки старше недели</b><p>Последний отбор — '
                 f'{esc(week)}, сегодня {today.isoformat()}. Это прошлый набор: '
                 'запусти прогон, иначе страница показывает не ту неделю.</p></div>')
    body = (f'<section><h2>Карточки недели</h2>{stale}'
            '<div class="box"><b>Что здесь предложено, а что измерено</b>'
            '<p>Цифры, кадры и расшифровка по блокам — измерены. Угол, хук и три колонки съёмки — '
            '<strong>предложение агента</strong>: берёте как есть или правите. Пустым остаётся '
            'только «к чему ведём» — накопитель не выбран.</p></div>'
            + ''.join(out) + '</section>')
    return page('Что снимаем', [f'неделя {week}', f'карточек {len(rows)}',
                                today.isoformat()], 'Что снимаем',
                'Референс, его разбор по кадрам и по блокам речи, и наш угол под съёмку.', body)


# ----------------------------------------------------------------- радар ----
def radar(con, today=None):
    today = today or datetime.date.today()
    import score
    st = dict(con.execute('SELECT status, COUNT(*) FROM accounts GROUP BY status').fetchall())
    snap = con.execute('SELECT taken, reels_n FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()
    if not snap:
        return page('Радар', ['снимков нет'], 'Радар',
                    'Снимков ещё нет — запусти прогон.',
                    '<section><p>База пуста. Первый сбор: <code>python3 run.py</code></p></section>')
    top = con.execute("""SELECT r.username,r.code,r.play,r.resh,r.save,r.dur,
        s.z,s.resh_1k,s.save_1k,s.author_median_play,s.baseline_n,d.cuts_ps
        FROM reels r JOIN scores s USING(snapshot_id,code)
        JOIN accounts a ON a.pk=r.pk_user AND a.status='active'
        LEFT JOIN deepdives d ON d.code=r.code
        WHERE s.eligible=1 AND s.weights='ig' AND (d.suitable IS NULL OR d.suitable=1)
          AND r.snapshot_id=(SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
        ORDER BY s.z DESC, r.play DESC LIMIT 40""").fetchall()
    tt = [(f'{i}', f'<a href="https://instagram.com/reel/{esc(r["code"])}" '
           f'rel="noopener noreferrer">{esc(r["username"])}</a>',
           num(r['play']), f'{r["z"]:.2f}',
           f'{r["play"]/(r["author_median_play"] or 1):.1f}×',
           f'{r["resh_1k"]:.0f}' if r['resh_1k'] is not None else '—',
           f'{r["save_1k"]:.0f}' if r['save_1k'] is not None else '—',
           f'{r["dur"]:.0f} с', f'{r["cuts_ps"]:.2f}' if r['cuts_ps'] is not None else '—',
           num(r['baseline_n'])) for i, r in enumerate(top, 1)]
    spend = con.execute('SELECT SUM(units), SUM(usd) FROM spend').fetchone()
    spend = (spend[0] or 0, spend[1] or 0.0)
    w = ' · '.join(f'{k} {v}' for k, v in score.W_IG.items())
    body = (f'<section><h2>Набор</h2>'
            + table(['Состояние', 'Аккаунтов'],
                    [('в наборе', num(st.get('active', 0))),
                     ('кандидаты, ждут разметки', num(st.get('candidate', 0))),
                     ('выбыли', num(st.get('dropped', 0))),
                     ('исключены вручную', num(st.get('out', 0)))], numeric={1})
            + f'<p>Последний снимок {snap["taken"]}, роликов {num(snap["reels_n"])}. '
            f'Потрачено {num(spend[0])} единиц, ${spend[1]:.2f}.</p></section>'
            f'<section><h2>Формула</h2>'
            f'<div class="box"><b>Веса</b><p>{esc(w)}</p></div>'
            f'<div class="box"><b>Предохранители</b><p>Компонента с разбросом меньше '
            f'{score.MAD_FLOOR:.0%} от медианы выбрасывается, оценка ограничена по модулю '
            f'{score.Z_CLIP:.0f}. В подборку не идёт ролик ниже {score.PLAY_FLOOR:.0%} медианы '
            f'своего автора или ниже тысячи просмотров.</p></div>'
            f'<p>Медиана автора считается по накопленной истории снимков. Столбец «база» — '
            f'сколько роликов автора стояло за оценкой.</p></section>'
            f'<section><h2>Топ-40</h2>'
            + table(['#', 'Автор', 'Просмотров', 'z', 'К норме', 'Пересылок/1k',
                     'Сохранений/1k', 'Длина', 'Склеек/с', 'База'],
                    tt, numeric={0, 2, 3, 4, 5, 6, 7, 8, 9}) + '</section>')
    return page('Радар', [snap['taken'], f'аккаунтов {st.get("active", 0)}',
                          f'${spend[1]:.2f}'], 'Радар',
                'Набор, формула и топ-40 целиком. Сюда заходишь, чтобы проверить, на чём стоят цифры.',
                body)


BUILD = {'niche': (niche, 'niche.html'), 'shoot': (shoot, 'shoot.html'),
         'radar': (radar, 'radar.html')}

if __name__ == '__main__':
    which = [a for a in sys.argv[1:] if a in BUILD] or list(BUILD)
    con = connect()
    for k in which:
        fn, name = BUILD[k]
        (OUT / name).write_text(fn(con), encoding='utf-8')
        print(f'  {name:<12} {(OUT / name).stat().st_size / 1024:>7.0f} КБ')
