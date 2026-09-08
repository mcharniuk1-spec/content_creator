#!/usr/bin/env python3
"""Разбор верхушки: кадры, контактный лист, склейки. SPEC §4.4. Локально, без единиц.

    python3 deep.py --plan          кого разберём и почему
    python3 deep.py                 разобрать
    python3 deep.py check           показать разборы без отметки о пригодности
    python3 deep.py unfit КОД "почему"   пометить ролик непригодным
    python3 deep.py fit КОД         пометить пригодным

Разбирается то же множество, из которого берутся карточки, — иначе у карточки не будет
ни контактного листа, ни расшифровки. Одного общего окна свежести для этого мало:
разбор шёл по общей оценке, а карточки по долям пересылок и сохранений, и пересечение
оказалось нулевым. Поэтому пул тот же, а порядок внутри него — по всем трём линейкам сразу.

Речь распознаётся здесь же, пока видео ещё не удалено: раньше расшифровка жила отдельным
скриптом, который читал уже стёртые файлы, и у новых роликов её не было бы никогда.
"""
import collections, datetime, glob, json, pathlib, re, subprocess, sys
from db import connect

D = pathlib.Path(__file__).parent / 'data'
V, F = D / 'video', D / 'frames'
N, WINDOW, CAP = 100, 14, 2      # роликов за прогон, окно свежести, кап на автора


def pick(con, n=N, window=WINDOW, cap=CAP, today=None):
    """Тот же пул, что у карточек, отсортированный по трём линейкам по очереди.

    Карточки отбираются по долям пересылок и сохранений, а не по общей оценке,
    поэтому разбор обязан покрывать верх всех трёх списков, а не одного.
    """
    import cards
    today = today or datetime.date.today()
    pool = [r for r in cards._pool(con, today) if (r.get('dur') or 0) > 0]
    done = {x[0] for x in con.execute('SELECT code FROM deepdives')}
    pool = [r for r in pool if r['code'] not in done]

    # Сначала — то, что станет карточками. Отбор карточек идёт по своим правилам
    # (свой ранг у каждого формата, один автор — одна карточка), и если разбор
    # отберёт что-то другое, у карточки не будет ни кадров, ни расшифровки. Это уже
    # случалось: пересечение было нулевым.
    out, taken, seen = [], set(), collections.Counter()
    try:
        picked, _, _ = cards.select(con, today)
        want = {c['code'] for c in picked}
    except Exception:
        want = set()
    for r in pool:
        if r['code'] in want:
            taken.add(r['code']); seen[r['username']] += 1
            out.append(dict(r))

    # Остальное добираем по трём линейкам с капом на автора, чтобы одна плодовитая
    # страница не заняла разбор целиком.
    for key in ('resh_1k', 'save_1k', 'z'):
        for r in sorted(pool, key=lambda x: -(x.get(key) or 0)):
            if len(out) >= n:
                break
            if r['code'] in taken or seen[r['username']] >= cap:
                continue
            taken.add(r['code']); seen[r['username']] += 1
            out.append(dict(r))
    return out, len(pool)


def _urls(codes, taken=None):
    """Ссылки на видео лежат в кэше HikerAPI от сбора — платить второй раз не за что.

    Файлы перебираются от старых к новым, чтобы свежая ссылка перекрывала старую:
    подписанные ссылки CDN живут часы, и старый файл с тем же кодом отдаст 403.
    Если известна дата снимка, смотрим только его папку.
    """
    root = pathlib.Path(__file__).parent / 'cache'
    pattern = f'{taken}/*clips*.json' if taken else '**/*clips*.json'
    files = sorted(glob.glob(str(root / pattern), recursive=True),
                   key=lambda f: pathlib.Path(f).stat().st_mtime)
    found = {}
    for f in files:
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for m in (d.get('items') or d.get('response', {}).get('items') or []):
            if m.get('code') in codes:
                vv = m.get('video_versions') or []
                if vv:
                    found[m['code']] = vv[0]['url']
    return found


def links_alive(url):
    """CDN подписывает ссылки на часы. Проверяем одну, прежде чем качать сотню."""
    p = subprocess.run(['curl', '-sI', '--max-time', '20', url], capture_output=True, text=True)
    return ' 200' in p.stdout.split('\n')[0]


def timecodes(dur):
    """Плотно в зоне хука, дальше равномерно."""
    return sorted({t for t in [0.4, 1.2, 2.4, 4.0] + [round(dur * k / 6, 1) for k in range(1, 6)]
                   if t < dur - 0.3})


def cuts(ff, mp4):
    p = subprocess.run([ff, '-i', str(mp4), '-filter:v', "select='gt(scene,0.35)',showinfo",
                        '-f', 'null', '-'], capture_output=True, text=True)
    return len(re.findall(r'pts_time:', p.stderr))


_whisper = None


def transcribe(mp4):
    """Локально, бесплатно, английский форсирован: автоопределение врёт на акцентах."""
    global _whisper
    try:
        if _whisper is None:
            from faster_whisper import WhisperModel
            _whisper = WhisperModel('small', device='cpu', compute_type='int8')
        segs, _ = _whisper.transcribe(str(mp4), language='en', vad_filter=True)
        return [{'s': round(s.start, 1), 'e': round(s.end, 1), 't': s.text.strip()} for s in segs]
    except Exception as e:
        print(f'    расшифровка не вышла: {e}', flush=True)
        return None


def run(con, rows, keep_video=False, speech=True):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    V.mkdir(exist_ok=True); F.mkdir(exist_ok=True)
    urls = _urls({r['code'] for r in rows})
    sid = con.execute('SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()[0]
    today = datetime.date.today().isoformat()
    done, no_url, empty = 0, [], []
    for i, r in enumerate(rows, 1):
        c = r['code']; mp4 = V / f'{c}.mp4'
        if not mp4.exists():
            u = urls.get(c)
            if not u:
                no_url.append(c); continue
            subprocess.run(['curl', '-sL', '--max-time', '150', '-o', str(mp4), u])
        if not mp4.exists() or mp4.stat().st_size < 10_000:
            empty.append(c); mp4.unlink(missing_ok=True); continue
        mb = round(mp4.stat().st_size / 1048576, 1)
        od = F / c; od.mkdir(exist_ok=True)
        tcs = timecodes(r['dur'])
        for j, t in enumerate(tcs):
            p = od / f'{j:02d}_{t:g}s.jpg'
            if not p.exists():
                subprocess.run([ff, '-y', '-loglevel', 'error', '-ss', str(t), '-i', str(mp4),
                                '-frames:v', '1', '-q:v', '3', '-vf', 'scale=540:-1', str(p)])
        sheet = F / f'{c}_sheet.jpg'
        if not sheet.exists():
            subprocess.run([ff, '-y', '-loglevel', 'error', '-pattern_type', 'glob',
                            '-i', str(od / '*.jpg'), '-filter_complex', 'tile=3x3',
                            '-q:v', '4', str(sheet)])
        n = cuts(ff, mp4)
        if speech and not con.execute('SELECT 1 FROM transcripts WHERE code=?', (c,)).fetchone():
            segs = transcribe(mp4)               # пока mp4 ещё на диске
            if segs is not None:
                text = ' '.join(s['t'] for s in segs).strip()
                con.execute("""INSERT OR REPLACE INTO transcripts
                    (code,lang,words,text,segments) VALUES (?,'en',?,?,?)""",
                    (c, len(text.split()), text, json.dumps(segs, ensure_ascii=False)))
        con.execute("""INSERT OR REPLACE INTO deepdives
            (code,snapshot_id,cuts,cuts_ps,mp4_mb,sheet,suitable,done_at)
            VALUES (?,?,?,?,?,?,NULL,?)""",
            (c, sid, n, round(n / max(r['dur'], 1), 2), mb,
             f'data/frames/{c}_sheet.jpg', today))
        for j, t in enumerate(tcs):
            con.execute('INSERT OR REPLACE INTO frames (code,idx,t_sec,path) VALUES (?,?,?,?)',
                        (c, j, t, f'data/frames/{c}/{j:02d}_{t:g}s.jpg'))
        if not keep_video:
            mp4.unlink(missing_ok=True)      # SPEC §4.4: видео не храним
        done += 1
        if done % 10 == 0:
            con.commit(); print(f'  {done}/{len(rows)} · без ссылки {len(no_url)}', flush=True)
    con.commit()
    return done, no_url, empty


def mark(con, code, ok, why=None):
    """Пригодность видна только в кадрах: по цифрам и по биографии её не определить."""
    if not con.execute('SELECT 1 FROM deepdives WHERE code=?', (code,)).fetchone():
        raise SystemExit(f'разбора {code} нет')
    con.execute('UPDATE deepdives SET suitable=?, unfit_why=? WHERE code=?',
                (1 if ok else 0, None if ok else (why or 'не подходит'), code))
    con.commit()


def unchecked(con):
    return con.execute("""SELECT d.code, r.username, r.play, d.sheet
        FROM deepdives d LEFT JOIN reels r ON r.code=d.code
        WHERE d.suitable IS NULL GROUP BY d.code ORDER BY r.play DESC""").fetchall()


if __name__ == '__main__':
    con = connect()
    a = sys.argv[1:]
    if a and a[0] == 'unfit':
        mark(con, a[1], False, a[2] if len(a) > 2 else None)
        print(f'{a[1]} помечен непригодным — из карточек и топ-40 он уйдёт')
        sys.exit()
    if a and a[0] == 'fit':
        mark(con, a[1], True)
        print(f'{a[1]} помечен пригодным')
        sys.exit()
    if a and a[0] == 'check':
        rows = unchecked(con)
        print(f'разборов без отметки: {len(rows)}\n')
        for r in rows[:40]:
            print(f"  {r['code']:<13} {(r['username'] or '—'):<22} {r['play'] or 0:>9,}"
                  .replace(',', ' ') + f"   {r['sheet'] or ''}")
        print('\nпосмотреть лист и решить: python3 deep.py unfit КОД "причина"')
        sys.exit()
    rows, pool = pick(con)
    print(f'в окне {WINDOW} дней подходящих {pool}, к разбору {len(rows)}, '
          f'авторов {len({r["username"] for r in rows})}')
    if not rows:
        print('всё в окне уже разобрано'); sys.exit()
    if '--plan' in sys.argv:
        for r in rows[:12]:
            print(f'  {r["username"]:<24} z={r["z"]:.2f}  {r["play"]:>9,}  {r["dur"]:.0f} с'
                  .replace(',', ' '))
        print(f'  … всего {len(rows)}. Денег не стоит: только время и диск')
        sys.exit()
    urls = _urls({r['code'] for r in rows})
    live = next((c for c in (r['code'] for r in rows) if c in urls), None)
    if live and not links_alive(urls[live]):
        n_acc = len({r['username'] for r in rows})
        print(f'\nссылки на видео протухли: CDN отдаёт 403. Кэш сбора устарел.\n'
              f'Разбор идёт сразу после сбора — либо ждём следующего снимка, либо\n'
              f'пересобираем ленты {n_acc} авторов: {n_acc} ед. = ${n_acc * 0.02:.2f}')
        sys.exit(1)
    done, no_url, empty = run(con, rows)
    print(f'\nразобрано {done} из {len(rows)}')
    if no_url: print(f'  без ссылки на видео в кэше: {len(no_url)}')
    if empty:  print(f'  пустой файл при скачивании: {len(empty)}')
    print(f'кадров в базе: {con.execute("SELECT COUNT(*) FROM frames").fetchone()[0]}, '
          f'разборов: {con.execute("SELECT COUNT(*) FROM deepdives").fetchone()[0]}, '
          f'расшифровок: {con.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]}')
