#!/usr/bin/env python3
"""Разбиение расшифровки на хук, тело и концовку. По таймкодам, не по смыслу.

    python3 blocks.py           статистика по разобранным
    python3 blocks.py КОД       показать один ролик по блокам

Границы взяты из того, как ролики устроены, а не из головы:
хук — первые 5 секунд, потому что кадры мы и режем плотно именно там (0.4 / 1.2 / 2.4 / 4.0);
концовка — последние 15% длительности, но не меньше шести секунд: там живёт финальная строка
и призыв. Всё между ними — тело.
"""
import json, statistics, sys
from db import connect

HOOK_SEC = 5.0
TAIL_SHARE = 0.15
TAIL_MIN = 6.0


def split(segments, dur):
    """Сегменты → три списка. Сегмент относится к блоку по своему началу.

    Граница концовки не может заехать в хук: у роликов короче одиннадцати секунд
    иначе не бывает тела вообще, а при неизвестной длительности вся речь после
    пятой секунды уезжала в концовку.
    """
    dur = dur or 0
    if dur:
        # на коротком ролике пять секунд хука и шесть концовки не помещаются рядом,
        # поэтому обе границы сжимаются по длине: тело обязано существовать
        hook_end = min(HOOK_SEC, dur * 0.3)
        tail_len = max(min(TAIL_MIN, dur * 0.3), dur * TAIL_SHARE)
        tail_from = max(hook_end, dur - tail_len)
    else:
        hook_end, tail_from = HOOK_SEC, 10 ** 9      # длительность неизвестна
    hook, body, tail = [], [], []
    for s in segments:
        (hook if s['s'] < hook_end else tail if s['s'] >= tail_from else body).append(s)
    return hook, body, tail


def text(segs):
    return ' '.join(s['t'].strip() for s in segs).strip()


def blocks(con, code):
    r = con.execute("""SELECT t.segments, r.dur FROM transcripts t
        JOIN reels r ON r.code = t.code WHERE t.code = ? LIMIT 1""", (code,)).fetchone()
    if not r or not r['segments']:
        return None
    h, b, t = split(json.loads(r['segments']), r['dur'])
    return {'hook': text(h), 'body': text(b), 'tail': text(t),
            'dur': r['dur'], 'words': {'hook': len(text(h).split()),
                                       'body': len(text(b).split()),
                                       'tail': len(text(t).split())}}


if __name__ == '__main__':
    con = connect()
    if len(sys.argv) > 1:
        b = blocks(con, sys.argv[1])
        if not b:
            sys.exit('нет расшифровки')
        for k, ru in (('hook', 'ХУК'), ('body', 'ТЕЛО'), ('tail', 'КОНЦОВКА')):
            print(f'\n{ru}  ({b["words"][k]} слов)\n  {b[k] or "—"}')
        sys.exit()
    rows = [blocks(con, r[0]) for r in con.execute(
        "SELECT code FROM transcripts WHERE text<>''")]
    rows = [b for b in rows if b]
    print(f'роликов с расшифровкой: {len(rows)}\n')
    for k, ru in (('hook', 'хук'), ('body', 'тело'), ('tail', 'концовка')):
        w = [b['words'][k] for b in rows]
        print(f'  {ru:<9} слов: медиана {statistics.median(w):>5.0f}   '
              f'пусто у {sum(1 for x in w if not x):>3} роликов')
    print(f'\n  длина ролика: медиана {statistics.median([b["dur"] for b in rows]):.0f} с')
