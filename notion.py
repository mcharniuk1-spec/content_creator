#!/usr/bin/env python3
"""Карточки в Notion и решения обратно. SPEC §4.7 и §4.8.

    python3 notion.py push          выгрузить карточки недели
    python3 notion.py pull          забрать статусы и комментарии
    python3 notion.py check         проверить доступ

Notion здесь — не витрина, а контур обратной связи. Выгружаем то, с чем работают люди;
забираем обратно решение и комментарий. Без этого пятый слой остаётся нулевым: отмечать
решение было негде, и радар предлагал одно и то же.

Токен и адреса лежат в .env рядом с проектом:
    NOTION_TOKEN=...        секрет интеграции
    NOTION_CARDS_DB=...     идентификатор базы Cards
    NOTION_PAGE=...         страница, куда кладём сводку недели
"""
import datetime, json, mimetypes, os, pathlib, subprocess, sys, tempfile

API = 'https://api.notion.com/v1'
VERSION = '2022-06-28'
ROOT = pathlib.Path(__file__).parent


def env(name, required=True):
    if os.environ.get(name):
        return os.environ[name]
    f = ROOT / '.env'
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    if required:
        sys.exit(f'{name} не найден: положи его в .env рядом с проектом')
    return None


def call(method, path, body=None, raw=None, headers=None, base=API):
    """Через curl, а не через питоновский http: на маке у Python нет корневых
    сертификатов, и весь остальной код проекта ходит наружу тем же способом."""
    url = path if path.startswith('http') else base + path
    cmd = ['curl', '-s', '--proto', '=https', '--max-time', '120', '-X', method,
           '-H', f'Authorization: Bearer {env("NOTION_TOKEN")}',
           '-H', f'Notion-Version: {VERSION}',
           '-w', '\n%{http_code}']
    for k, v in (headers or {}).items():
        cmd += ['-H', f'{k}: {v}']
    tmp = None
    if body is not None:
        cmd += ['-H', 'Content-Type: application/json', '--data-binary', '@-']
        payload = json.dumps(body).encode()
    elif raw is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(raw); tmp.close()
        cmd += ['--data-binary', '@' + tmp.name]
        payload = None
    else:
        payload = None
    cmd += ['--', url]
    p = subprocess.run(cmd, input=payload, capture_output=True)
    if tmp:
        os.unlink(tmp.name)
    out = p.stdout.decode('utf-8', 'replace')
    text, _, code = out.rpartition('\n')
    if not code.strip().startswith('2'):
        raise SystemExit(f'Notion ответил {code.strip() or "без кода"}: {text[:300]}')
    return json.loads(text or '{}')


# ---------------------------------------------------------------- картинки ----
def upload(path, name=None):
    """Контактный лист в Notion. Без него карточка — это текст про кадры, а не кадры."""
    p = pathlib.Path(path)
    if not p.exists():
        return None
    name = name or p.name
    up = call('POST', '/file_uploads', {'filename': name,
                                        'content_type': mimetypes.guess_type(name)[0] or 'image/jpeg'})
    boundary = '----radar' + datetime.datetime.now().strftime('%H%M%S%f')
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
            f'Content-Type: image/jpeg\r\n\r\n').encode() + p.read_bytes() + \
           f'\r\n--{boundary}--\r\n'.encode()
    call('POST', up['upload_url'], raw=body,
         headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    return up['id']


# ------------------------------------------------------------------ выгрузка ----
def blocks_for(con, card):
    """Тело карточки: кадры, речь по блокам, угол, съёмка."""
    import blocks
    out = []
    text = lambda t, tp='paragraph': {'object': 'block', 'type': tp,
                                      tp: {'rich_text': [{'type': 'text', 'text': {'content': t[:1900]}}]}}
    head = lambda t: text(t, 'heading_2')

    sheet = ROOT / (card['sheet'] or '')
    if card['sheet'] and sheet.exists():
        fid = upload(sheet, f"{card['code']}.jpg")
        if fid:
            out.append({'object': 'block', 'type': 'image',
                        'image': {'type': 'file_upload', 'file_upload': {'id': fid}}})
            tcs = [r[0] for r in con.execute(
                'SELECT t_sec FROM frames WHERE code=? ORDER BY idx', (card['code'],)) if r[0]]
            if tcs:
                out.append(text('Frames at ' + ', '.join(f'{t:g}s' for t in tcs)
                                + ' — four of them inside the hook.'))

    b = blocks.blocks(con, card['code'])
    if b:
        out.append(head('What they say'))
        for k, label in (('hook', 'Hook'), ('body', 'Body'), ('tail', 'Ending')):
            if b[k]:
                out.append(text(f'{label} · {b["words"][k]} words', 'heading_3'))
                out.append(text(b[k]))

    out.append(head('Our angle'))
    out.append(text(card['angle'] or 'Not written yet — the agent fills this in.'))
    if card['hook']:
        out.append(text(f'Draft hook: {card["hook"]}', 'quote'))

    out.append(head('How we shoot it'))
    for label, v in (('In frame', card['shot_frame']), ('On screen', card['shot_screen']),
                     ('In the banner', card['shot_banner'])):
        if v:
            out.append({'object': 'block', 'type': 'bulleted_list_item',
                        'bulleted_list_item': {'rich_text': [
                            {'type': 'text', 'text': {'content': label + ': '},
                             'annotations': {'bold': True}},
                            {'type': 'text', 'text': {'content': v[:1800]}}]}})
    if card['caption']:
        out.append(text('Caption frame', 'heading_3'))
        out.append(text(card['caption']))

    out.append(head('Decide here'))
    out.append(text('Set Status above and leave a comment on this page. '
                    'Both are read back by the radar on the next run.'))
    return out


def push(con, week=None):
    db = env('NOTION_CARDS_DB')
    week = week or con.execute('SELECT MAX(week) FROM cards').fetchone()[0]
    if not week:
        print('карточек ещё нет'); return 0
    rows = con.execute("""SELECT c.*, r.username, r.play, s.author_median_play, s.resh_1k,
               s.save_1k, r.ts, d.sheet
        FROM cards c
        JOIN reels r ON r.code=c.code
             AND r.snapshot_id=(SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
        JOIN scores s ON s.code=c.code AND s.snapshot_id=r.snapshot_id AND s.weights='ig'
        LEFT JOIN deepdives d ON d.code=c.code
        WHERE c.week=? ORDER BY c.pri""", (week,)).fetchall()
    found = call('POST', f'/databases/{db}/query',
                 {'filter': {'property': 'Week', 'date': {'equals': week}}})['results']
    existing = {p['properties']['Reference']['url']: p for p in found
                if p['properties'].get('Reference', {}).get('url')}
    done = 0
    for c in rows:
        ref = f"https://instagram.com/reel/{c['code']}"
        mult = round(c['play'] / (c['author_median_play'] or 1), 1)
        age = (datetime.date.fromisoformat(week) - datetime.date.fromtimestamp(c['ts'])).days
        props = {
            'Name': {'title': [{'text': {'content': (c['hook'] or c['why'] or c['code'])[:80]}}]},
            'Week': {'date': {'start': week}},
            'Format': {'select': {'name': c['fmt']}},
            'Priority': {'number': c['pri']},
            'Reference': {'url': ref},
            'Author': {'rich_text': [{'text': {'content': c['username'] or ''}}]},
            'Signal': {'rich_text': [{'text': {'content': (c['why'] or '')[:1900]}}]},
            'Vs author norm': {'number': mult},
            'Age at pickup': {'number': age},
        }
        if c['lead']:
            props['Lead'] = {'select': {'name': c['lead']}}
        if ref in existing:
            page = existing[ref]
            call('PATCH', f'/pages/{page["id"]}', {'properties': props})
            # тело переписываем только у нетронутых карточек: если человек уже принял
            # решение или правил текст, его работа важнее свежей выгрузки
            st = ((page['properties'].get('Status') or {}).get('select') or {}).get('name')
            if st in (None, 'Proposed'):
                for b in call('GET', f'/blocks/{page["id"]}/children?page_size=100').get('results', []):
                    call('PATCH', f'/blocks/{b["id"]}', {'archived': True})
                call('PATCH', f'/blocks/{page["id"]}/children',
                     {'children': blocks_for(con, c)[:95]})
        else:
            props['Status'] = {'select': {'name': 'Proposed'}}
            call('POST', '/pages', {'parent': {'database_id': db}, 'properties': props,
                                    'children': blocks_for(con, c)[:95]})
        done += 1
        print(f'  {c["pri"]:>2}. {c["fmt"]:<12} {c["username"]:<22} выгружена', flush=True)
    return done


# ------------------------------------------------------------------ обратно ----
def pull(con, week=None):
    """Статусы и комментарии обратно в базу. Это и есть замкнутая петля."""
    db = env('NOTION_CARDS_DB')
    week = week or con.execute('SELECT MAX(week) FROM cards').fetchone()[0]
    res = call('POST', f'/databases/{db}/query',
               {'filter': {'property': 'Week', 'date': {'equals': week}}})['results']
    changed, notes = 0, 0
    for p in res:
        pr = p['properties']
        ref = (pr.get('Reference') or {}).get('url') or ''
        code = ref.rstrip('/').split('/')[-1]
        st = ((pr.get('Status') or {}).get('select') or {}).get('name')
        lead = ((pr.get('Lead') or {}).get('select') or {}).get('name')
        if not code or not st:
            continue
        cur = con.execute('SELECT status, lead FROM cards WHERE week=? AND code=?',
                          (week, code)).fetchone()
        if cur and (cur['status'] != st or cur['lead'] != lead):
            con.execute('UPDATE cards SET status=?, lead=COALESCE(?,lead) WHERE week=? AND code=?',
                        (st, lead, week, code))
            changed += 1
        # комментарии людей — в журнал: следующий прогон их читает
        for cm in call('GET', f'/comments?block_id={p["id"]}').get('results', []):
            txt = ''.join(t.get('plain_text', '') for t in cm.get('rich_text', [])).strip()
            if not txt:
                continue
            if not con.execute('SELECT 1 FROM tool_log WHERE detail=?', (txt,)).fetchone():
                con.execute("""INSERT INTO tool_log (at,kind,what,detail,fixed)
                               VALUES (?,'junk',?,?,0)""",
                            (datetime.date.today().isoformat(),
                             f'комментарий к карточке {code}', txt))
                notes += 1
    con.commit()
    print(f'обновлено статусов: {changed}, новых комментариев: {notes}')
    if changed:
        for r in con.execute("SELECT pri, status FROM cards WHERE week=? ORDER BY pri", (week,)):
            print(f'  карточка {r["pri"]}: {r["status"]}')
    return changed, notes


if __name__ == '__main__':
    from db import connect
    a = sys.argv[1:] or ['check']
    con = connect()
    if a[0] == 'check':
        me = call('GET', '/users/me')
        print('доступ есть, интеграция:', me.get('name') or me.get('bot', {}).get('owner', {}))
        db = call('GET', f'/databases/{env("NOTION_CARDS_DB")}')
        print('база:', ''.join(t['plain_text'] for t in db['title']))
        print('свойства:', ', '.join(db['properties']))
    elif a[0] == 'push':
        n = push(con)
        print(f'\nвыгружено карточек: {n}')
    elif a[0] == 'pull':
        pull(con)
    else:
        print(__doc__)
