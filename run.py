#!/usr/bin/env python3
"""Недельный прогон целиком, в правильном порядке.

    python3 run.py              смета: что произойдёт и сколько это стоит
    python3 run.py --yes        прогон

Порядок зашит здесь намеренно. Собранный руками он один раз уже развалился: разбор пошёл
через двое суток после сбора, и все сто ссылок на видео отдали 403. Ссылки живут часы,
поэтому разбор идёт сразу за сбором, в том же прогоне.

    1. сбор роликов по набору        платно, единица на аккаунт
    2. оценка против нормы автора    бесплатно
    3. разбор верхушки: кадры и речь бесплатно, но сразу за сбором
    4. разметка тем по выборке       бесплатно
    5. подписчики набора             бесплатно
    6. живость и выбраковка          бесплатно
    7. карточки в базу               бесплатно
    8. решения из Notion             бесплатно, до отбора: отклонённое не предлагаем заново
    9. дельта к прошлому снимку      бесплатно
   10. карточки в Notion             бесплатно
   11. таблицы решений в Notion      бесплатно
   12. полные базы в Notion          бесплатно
   13. три страницы                  бесплатно

После прогона остаётся человеческое, и прогон о нём напоминает: отметить непригодные
ролики по кадрам и вписать углы. Страницы после этого пересобираются одной командой.
"""
import datetime, sys, time
from db import connect

import cards, collect_snapshot, deep, delta, notion, notion_db, pages, roster, score, stats, tag_topics


def line(n, title):
    print(f'\n{"─" * 70}\n{n}. {title}\n{"─" * 70}', flush=True)


def main(run=False):
    con = connect()
    n_acc, units, enough = collect_snapshot.plan(con)
    if run and not enough:
        print('\nпрогон остановлен: единиц на счету меньше, чем нужно на сбор.')
        print('Пополни баланс или уменьши набор — собирать половину набора смысла нет.')
        return
    if not run:
        print(f'\nдальше всё бесплатно: оценка, разбор верхушки, темы, выбраковка, страницы.')
        print(f'итого прогон стоит ${units * collect_snapshot.PRICE:.2f}')
        print('\nэто смета. Прогон: python3 run.py --yes')
        return

    t0 = time.time()
    line(1, f'сбор роликов по {n_acc} аккаунтам')
    sid, n_reels, miss = collect_snapshot.run(con)

    line(2, 'оценка против нормы автора по накопленной истории')
    _, taken, res = score.score_snapshot(con)
    print(f'снимок {taken}: оценено {len(res)}, прошло порог {sum(1 for r in res if r["eligible"])}')

    line(3, 'разбор верхушки окна — сразу за сбором, пока ссылки живы')
    rows, pool = deep.pick(con)
    print(f'в окне подходящих {pool}, к разбору {len(rows)}')
    if rows:
        urls = deep._urls({r['code'] for r in rows})
        live = next((c for c in (r['code'] for r in rows) if c in urls), None)
        if live and not deep.links_alive(urls[live]):
            print('ссылки уже мертвы — этого быть не должно сразу после сбора')
            con.execute("""INSERT INTO tool_log (at,kind,what,detail,fixed) VALUES
                (?,'bug','ссылки мертвы сразу после сбора',
                 'разбор в том же прогоне не смог скачать видео — проверить, откуда берутся ссылки',0)""",
                (datetime.date.today().isoformat(),))
            con.commit()
        else:
            done, no_url, empty = deep.run(con, rows)
            print(f'разобрано {done} из {len(rows)}, без ссылки {len(no_url)}, пустых {len(empty)}')

    line(4, 'разметка тем: верхушка целиком, остальное выборкой')
    done, unknown, n_rest = tag_topics.tag(con)
    tot, unk = sum(done.values()), sum(unknown.values())
    print(f'размечено {tot}, нераспознанных {unk} ({100 * unk / max(tot, 1):.0f}%)')

    line(5, 'подписчики набора — для ответа «кто растёт»')
    try:
        roster.refresh_followers(con)
    except Exception as e:
        print(f'источник профилей недоступен: {e}')

    line(6, 'живость и выбраковка')
    roster.check(con, silent_accounts=set(miss))
    if miss:
        print(f'не отдали ленту и получили промах: {len(miss)}')

    line(7, 'решения прошлой недели из Notion')
    try:
        notion.pull(con)
    except SystemExit as e:
        print(f'Notion недоступен, идём дальше: {e}')

    line(8, 'карточки')
    picked, pool_n, rep_n = cards.select(con)
    week = cards.save(con, picked)
    print(f'кандидатов {pool_n}, повторяющихся тем {rep_n}, записано карточек {len(picked)}')
    for c in picked:
        print(f'  {c["n"]:>2}. {c["fmt"]:<12} {c["author"]:<22} {c["age"]:>2} дн.  {c["why"][:56]}')

    line(9, 'что сдвинулось с прошлого снимка')
    delta.report(con)

    line(10, 'карточки в Notion')
    try:
        n = notion.push(con, week)
        print(f'выгружено: {n}')
    except SystemExit as e:
        print(f'выгрузка не прошла: {e}')

    line(11, 'таблицы, на которых стоят решения — в Notion')
    try:
        stats.push(con)
        print('раздел с цифрами обновлён')
    except SystemExit as e:
        print(f'не прошло: {e}')

    line(12, 'полные базы в Notion: ролики и аккаунты')
    try:
        notion_db.push_reels(con)
        notion_db.push_accounts(con)
    except SystemExit as e:
        print(f'не прошло: {e}')

    line(13, 'три страницы')
    for k, (fn, name) in pages.BUILD.items():
        (pages.OUT / name).write_text(fn(con), encoding='utf-8')
        print(f'  {name:<12} {(pages.OUT / name).stat().st_size / 1024:>7.0f} КБ')

    spent = con.execute("SELECT SUM(usd) FROM spend WHERE at=?",
                        (datetime.date.today().isoformat(),)).fetchone()[0] or 0
    print(f'\n{"═" * 70}\nпрогон занял {(time.time() - t0) / 60:.0f} мин, '
          f'потрачено сегодня ${spent:.2f}')
    unchecked = len(deep.unchecked(con))
    print(f'\nосталось человеческое:')
    print(f'  1. пригодность по кадрам — {unchecked} разборов без отметки: '
          f'python3 deep.py check')
    print(f'  2. углы и хуки — python3 cards.py angle НОМЕР "текст"')
    print(f'  3. пересобрать страницы после углов — python3 pages.py')


if __name__ == '__main__':
    main(run='--yes' in sys.argv)
