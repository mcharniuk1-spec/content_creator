"""Журнал: запись, закрытие, окно месяца. На синтетической базе (db.SCHEMA), не на
копии рабочей: журнал считает счётчики от нуля, и живая база с её собственными
открытыми записями делает "было + 1" правдой по случайности, а не по конструкции."""
import datetime, os, sys
import journal
from db import connect
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.journal-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP); fail = []
def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<48} {g}   ожидалось {w}"); fail.append(n) if g != w else None
c = lambda s, *a: con.execute(s, a).fetchone()[0]

was_open = c('SELECT COUNT(*) FROM tool_log WHERE fixed=0')
i = journal.add(con, 'junk', 'предложило ролик не из ниши', 'аккаунт про трейдинг')
eq('запись добавлена', c('SELECT COUNT(*) FROM tool_log WHERE id=?', i), 1)
eq('новая запись открыта', c('SELECT fixed FROM tool_log WHERE id=?', i), 0)
eq('открытых стало больше на одну', c('SELECT COUNT(*) FROM tool_log WHERE fixed=0'), was_open + 1)
journal.close(con, i)
eq('запись закрывается', c('SELECT fixed FROM tool_log WHERE id=?', i), 1)

old = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
j = journal.add(con, 'bug', 'старая запись', at=old)
since = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
eq('старое в окно месяца не попадает', c('SELECT COUNT(*) FROM tool_log WHERE at>=? AND id=?', since, j), 0)
eq('свежее попадает', c('SELECT COUNT(*) FROM tool_log WHERE at>=? AND id=?', since, i), 1)
for bad in ('ошибка', 'BUG', ''):
    try:
        journal.add(con, bad, 'x'); ok = False
    except SystemExit:
        ok = True
    eq(f'вид «{bad or "пусто"}» не принимается', ok, True)
try:
    journal.close(con, 99999); ok = False
except SystemExit:
    ok = True
eq('закрыть несуществующую нельзя', ok, True)
con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
