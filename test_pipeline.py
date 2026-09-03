"""Пустая база и оркестровка — то, что не проверялось ничем.

Раньше три шага из девяти роняли прогон на новой базе с невнятной ошибкой,
а порядок шагов не был закреплён вообще.
"""
import datetime, os, sys
import baseline, blocks, cards, deep, delta, pages, roster, score, tag_topics
from db import connect

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.pipe-test.db')
if os.path.exists(TMP): os.remove(TMP)
con = connect(TMP)
fail = []
def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<54} {str(g)[:28]}   ожидалось {str(w)[:20]}")
    if g != w: fail.append(n)

print('ПУСТАЯ БАЗА')
eq('оценка не падает', score.score_snapshot(con)[2], [])
eq('разметка тем не падает', tag_topics.tag(con)[2], 0)
eq('разбор не падает', deep.pick(con), ([], 0))
eq('карточки не падают', cards.select(con)[0], [])
eq('дельта не падает', delta.report(con), None)
eq('живость не падает', roster.check(con), None)
for name, fn in (('ниша', pages.niche), ('снимаем', pages.shoot), ('радар', pages.radar)):
    try:
        html = fn(con); ok = html.startswith('<title>')
    except Exception as e:
        ok = f'{type(e).__name__}: {e}'
    eq(f'страница «{name}» собирается', ok, True)

print('\nБЛОКИ РЕЧИ')
def three(dur):
    """Три реплики внутри ролика: начало, середина, конец."""
    return [{'s': 0.0, 'e': 1.0, 't': 'hook'},
            {'s': dur * 0.45, 'e': dur * 0.55, 't': 'body'},
            {'s': dur * 0.92, 'e': dur, 't': 'tail'}]
for dur in (60, 30, 12, 8, 5):
    h, b, t = blocks.split(three(dur), dur)
    eq(f'ролик {dur} с: у каждого блока по реплике', (len(h), len(b), len(t)), (1, 1, 1))
h, b, t = blocks.split(three(60), 0)
eq('длительность неизвестна: всё после хука уходит в тело', (len(h), len(b), len(t)), (1, 2, 0))

print('\nПОРЯДОК ПРОГОНА')
import inspect, run
src = inspect.getsource(run.main)
order = [src.index(x) for x in ("line(1", "line(3", "line(7", "line(9")]
eq('сбор идёт раньше разбора', order[0] < order[1], True)
eq('разбор раньше карточек', order[1] < order[2], True)
eq('карточки раньше страниц', order[2] < order[3], True)
eq('прогон останавливается при нехватке единиц', 'прогон остановлен' in src, True)

con.close(); os.remove(TMP)
print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
