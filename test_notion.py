"""Связка с Notion на заглушке: что уходит туда и что приходит обратно.

Сеть не трогаем — проверяется логика: какие карточки выгружаются, что тело переписывается
только у нетронутых, как решения ложатся в базу и как они меняют следующий отбор.
"""
import datetime, os, shutil, sys
import cards, notion
from db import connect, DB_PATH

TMP = DB_PATH.replace('.db', '.notion-test.db')
shutil.copy(DB_PATH, TMP)
con = connect(TMP)
fail = []
def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<52} {str(g)[:24]}   ожидалось {str(w)[:20]}")
    if g != w: fail.append(n)

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

week = con.execute('SELECT MAX(week) FROM cards').fetchone()[0]
n = notion.push(con, week)
eq('выгружены все карточки недели', n,
   con.execute('SELECT COUNT(*) FROM cards WHERE week=?', (week,)).fetchone()[0])
eq('новые созданы как страницы', len(sent), n)
eq('у каждой проставлен статус Proposed',
   all(p['properties']['Status']['select']['name'] == 'Proposed' for p in sent), True)
eq('в теле есть кадры и речь',
   any(b['type'] == 'image' for b in sent[0]['children']), True)

# карточка, которую человек уже тронул, не перезаписывается
PAGES.append({'id': 'p1', 'properties': {
    'Reference': {'url': f"https://instagram.com/reel/{con.execute('SELECT code FROM cards LIMIT 1').fetchone()[0]}"},
    'Status': {'select': {'name': 'Taking'}}}})
archived.clear(); patched.clear()
notion.push(con, week)
eq('тело принятой карточки не тронуто', len(archived), 0)
eq('но свойства обновлены', len(patched) > 0, True)

# решения возвращаются в базу
code = con.execute('SELECT code FROM cards LIMIT 1').fetchone()[0]
PAGES[0]['properties']['Status'] = {'select': {'name': 'Not taking'}}
PAGES[0]['properties']['Lead'] = {'select': {'name': 'Max'}}
changed, notes = notion.pull(con, week)
eq('статус записан в базу',
   con.execute('SELECT status FROM cards WHERE code=?', (code,)).fetchone()[0], 'Not taking')
eq('ведущий записан', con.execute('SELECT lead FROM cards WHERE code=?', (code,)).fetchone()[0], 'Max')
eq('комментарий человека попал в журнал', notes, 1)
eq('и он читается', con.execute(
    "SELECT COUNT(*) FROM tool_log WHERE detail LIKE '%45 секунд%'").fetchone()[0], 1)

# и отклонённое больше не предлагается
today = datetime.date(2026, 9, 3)
pool = {r['code'] for r in cards._pool(con, today)}
eq('отклонённая карточка ушла из отбора', code in pool, False)

# повторный pull не плодит записи в журнале
_, notes2 = notion.pull(con, week)
eq('тот же комментарий второй раз не записывается', notes2, 0)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
