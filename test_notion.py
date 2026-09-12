"""Связка с Notion на заглушке: что уходит туда и что приходит обратно.

Сеть не трогаем — проверяется логика: какие карточки выгружаются, что тело переписывается
только у нетронутых, как решения ложатся в базу и как они меняют следующий отбор.

База синтетическая (db.SCHEMA на временном файле), а не копия рабочей. Настоящая причина
провала на этом чекауте: `con.execute('SELECT code FROM cards LIMIT 1')` без `WHERE week=?`
и без ORDER BY — на живой базе таблица `cards` копит карточки многих недель (сейчас 23
строки из нескольких прогонов), и запрос без фильтра по неделе брал случайную карточку
ИЗ ДРУГОЙ недели, а не одну из девяти только что выгруженных. Дальше вся цепочка сверки
(match по Reference-url, обратная запись статуса) сверялась с чужой карточкой и
проваливалась — это баг теста (нет `WHERE week=?`), а не notion.py: сам notion.py и
его сопоставление по Reference-url не менялись и работают верно. Здесь одна неделя,
код каждой карточки известен заранее, и запросы явно её называют."""
import datetime, os, sys
import notion
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.notion-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP)
fail = []

def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<52} {str(g)[:24]}   ожидалось {str(w)[:20]}")
    if g != w: fail.append(n)

WEEK = '2026-09-10'
SHEET_REL = 'data/notion-test-sheet.jpg'
SHEET_ABS = os.path.join(os.path.dirname(os.path.abspath(__file__)), SHEET_REL)
with open(SHEET_ABS, 'wb') as f:
    f.write(b'\xff\xd8\xff\xe0fake-jpeg-for-test')

con.execute("INSERT INTO snapshots (taken,accounts_n,reels_n,done) VALUES (?,3,3,1)", (WEEK,))
sid = con.execute('SELECT id FROM snapshots WHERE taken=?', (WEEK,)).fetchone()[0]

CARD_ROWS = [
    ('CARDA0001', 'authora', 'M2 Radar', 1),
    ('CARDB0002', 'authorb', 'M2 Builds', 2),
    ('CARDC0003', 'authorc', 'M2 Teardown', 3),
]
for i, (code, user, fmt, pri) in enumerate(CARD_ROWS, 1):
    con.execute("INSERT INTO accounts (pk,username,status) VALUES (?,?,'active')", (i, user))
    con.execute("""INSERT INTO reels (snapshot_id,code,pk_user,username,ts,play,dur,cap)
        VALUES (?,?,?,?,?,?,?,?)""",
        (sid, code, i, user, int(datetime.datetime(2026, 9, 8).timestamp()), 5000, 45.0, 'caption'))
    con.execute("""INSERT INTO scores (snapshot_id,code,eligible,author_median_play,
        resh_1k,save_1k,weights) VALUES (?,?,1,1000,10.0,16.0,'ig')""", (sid, code))
    sheet = SHEET_REL if i == 1 else None       # только у первой — картинка для проверки тела
    con.execute("""INSERT INTO cards (week,code,fmt,pri,why,angle,hook,
        shot_frame,shot_screen,shot_banner,caption,status)
        VALUES (?,?,?,?,'signal','','','frame','screen','banner','cap','draft')""",
        (WEEK, code, fmt, pri))
    if sheet:
        con.execute("INSERT INTO deepdives (code,snapshot_id,sheet) VALUES (?,?,?)", (code, sid, sheet))
con.commit()

os.environ['NOTION_TOKEN'] = 'test'
os.environ['NOTION_CARDS_DB'] = 'testdb'
sent, patched, archived = [], [], []
PAGES = []

def fake_call(method, path, body=None, raw=None, headers=None, base=None):
    if path.startswith('/databases') and method == 'POST':
        return {'results': PAGES}
    if path == '/pages' and method == 'POST':
        sent.append(body); return {'id': 'new'}
    if path.startswith('/pages/') and method == 'PATCH':
        patched.append(body); return {}
    if path.startswith('/blocks/') and method == 'PATCH' and body and body.get('archived'):
        archived.append(path); return {}
    if path.startswith('/blocks/') and 'children' in path:
        return {'results': [{'id': 'b1'}]} if method == 'GET' else {}
    if path == '/file_uploads':
        return {'id': 'up1', 'upload_url': 'https://x'}
    if path.startswith('/comments'):
        return {'results': [{'rich_text': [{'plain_text': 'снять короче, 45 секунд'}]}]}
    return {}
notion.call = fake_call

n = notion.push(con, WEEK)
eq('выгружены все карточки недели', n,
   con.execute('SELECT COUNT(*) FROM cards WHERE week=?', (WEEK,)).fetchone()[0])
eq('новые созданы как страницы', len(sent), n)
eq('у каждой проставлен статус Proposed',
   all(p['properties']['Status']['select']['name'] == 'Proposed' for p in sent), True)
eq('в теле есть кадры и речь',
   any(b['type'] == 'image' for b in sent[0]['children']), True)

# карточка, которую человек уже тронул, не перезаписывается
first_code = con.execute('SELECT code FROM cards WHERE week=? ORDER BY pri LIMIT 1', (WEEK,)).fetchone()[0]
PAGES.append({'id': 'p1', 'properties': {
    'Reference': {'url': f'https://instagram.com/reel/{first_code}'},
    'Status': {'select': {'name': 'Taking'}}}})
archived.clear(); patched.clear()
notion.push(con, WEEK)
eq('тело принятой карточки не тронуто', len(archived), 0)
eq('но свойства обновлены', len(patched) > 0, True)

# решения возвращаются в базу
PAGES[0]['properties']['Status'] = {'select': {'name': 'Not taking'}}
PAGES[0]['properties']['Lead'] = {'select': {'name': 'Max'}}
changed, notes = notion.pull(con, WEEK)
eq('статус записан в базу',
   con.execute('SELECT status FROM cards WHERE week=? AND code=?', (WEEK, first_code)).fetchone()[0],
   'Not taking')
eq('ведущий записан',
   con.execute('SELECT lead FROM cards WHERE week=? AND code=?', (WEEK, first_code)).fetchone()[0], 'Max')
eq('комментарий человека попал в журнал', notes, 1)
eq('и он читается', con.execute(
    "SELECT COUNT(*) FROM tool_log WHERE detail LIKE '%45 секунд%'").fetchone()[0], 1)

# и отклонённое больше не предлагается
import cards
today = datetime.date(2026, 9, 12)
pool = {r['code'] for r in cards._pool(con, today)}
eq('отклонённая карточка ушла из отбора', first_code in pool, False)

# повторный pull не плодит записи в журнале
_, notes2 = notion.pull(con, WEEK)
eq('тот же комментарий второй раз не записывается', notes2, 0)

con.close(); os.remove(TMP); os.remove(SHEET_ABS)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
