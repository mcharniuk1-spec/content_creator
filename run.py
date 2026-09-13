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

Итог по шагам (OK/SKIPPED/FAILED + причина) печатается в конце независимо от того, дошёл
ли прогон до тринадцатого шага или упал раньше — реализовано через try/finally, чтобы
аудит reports/audit/03 §5 ("нужно читать весь лог, чтобы понять, что сломалось") не
повторялся при каждом сбое.

Если engine.state (владелец schema/state) импортируется, прогон пишет через него одну
`runs`-строку на весь прогон (start_run/finish_run) и по одной `jobs`-строке на те шаги,
для которых в SPEC §3 нашёлся осмысленный canonical stage (2,3,4,5,7,8,10,11,12 —
подробности выбора в engine/HANDOFF_NOTES.md ## hiker-owner); шаги 1,6,9,13 работают про
целый снимок/набор, а не про одну сущность, и через jobs не пишутся. Отключается на трёх
уровнях: ImportError на импорте engine.state, Exception при входе в job() (несовпадение
сигнатуры/словаря стадий — тогда шаг просто выполняется без трекинга), и BaseException
внутри самого шага пробрасывается дальше как раньше — трекинг никогда не глотает реальную
ошибку шага.
"""
import contextlib, datetime, subprocess, sys, time
from db import connect

import cards, collect_snapshot, deep, delta, notion, notion_db, pages, roster, score, stats, tag_topics

try:
    from engine import state as engine_state
except ImportError:
    engine_state = None


STEP_TITLES = {
    1: 'сбор роликов по набору',
    2: 'оценка против нормы автора',
    3: 'разбор верхушки окна',
    4: 'разметка тем',
    5: 'подписчики набора',
    6: 'живость и выбраковка',
    7: 'решения прошлой недели из Notion',
    8: 'карточки',
    9: 'что сдвинулось с прошлого снимка',
    10: 'карточки в Notion',
    11: 'таблицы решений в Notion',
    12: 'полные базы в Notion',
    13: 'три страницы',
}


def line(n, title):
    print(f'\n{"─" * 70}\n{n}. {title}\n{"─" * 70}', flush=True)


class StepTracker:
    """Копится по ходу прогона; печатается в finally, даже если прогон упал
    посередине — тогда непройденные шаги помечаются NOT_REACHED, а не пропадают
    из виду совсем."""

    def __init__(self):
        self.rows = {}

    def mark(self, n, state, reason=''):
        self.rows[n] = (state, reason)

    def render(self):
        out = [f"\n{'═' * 70}", 'итоги по шагам', '═' * 70]
        for n in sorted(STEP_TITLES):
            state, reason = self.rows.get(n, ('NOT_REACHED', ''))
            tail = f' — {reason}' if reason else ''
            out.append(f'  {n:>2}. {state:<12} {STEP_TITLES[n]}{tail}')
        return '\n'.join(out)


def _start_run(con):
    if not engine_state:
        return None
    try:
        return engine_state.start_run(con, 'weekly')
    except Exception:
        return None


@contextlib.contextmanager
def _job(con, run_id, entity_id, stage):
    """Оборачивает шаг в engine.state.job(), если он есть и совпадает по интерфейсу.

    engine.state.job() — генератор-контекстменеджер: сам факт его вызова ничего не
    исполняет, вся проверка (stage/entity_kind из фиксированного словаря, запись в БД)
    происходит только при входе (__enter__). Поэтому naive try/except вокруг вызова
    job(...) ничего бы не поймал — обёрнут явный __enter__/__exit__, чтобы отличить
    «engine.state недоступен или сигнатура разошлась» (тихо деградируем, шаг всё равно
    выполняется) от «сам шаг упал» (не глотаем — даём engine.state дописать FAILED и
    пробрасываем исключение дальше, как было раньше)."""
    if not (engine_state and run_id):
        yield
        return
    try:
        cm = engine_state.job(con, run_id, 'corpus', entity_id, stage)
        handle = cm.__enter__()
    except Exception:
        yield
        return
    try:
        yield handle
    except BaseException:
        try:
            cm.__exit__(*sys.exc_info())
        except Exception:
            pass
        raise
    else:
        try:
            cm.__exit__(None, None, None)
        except Exception:
            pass


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
    tracker = StepTracker()
    run_id = _start_run(con)

    try:
        # Шаги 1, 6, 9, 13 не пишутся через engine.state.job(): его stage — фиксированный
        # словарь из SPEC §3 для состояния отдельного видео/сущности, и для них там нет
        # осмысленного соответствия (сбор целого снимка, живость набора, дельта, сборка
        # страниц — не про одну сущность). Остальные шаги используют ближайший по смыслу
        # канонический stage при entity_kind='corpus', entity_id='weekly:<шаг>' — см.
        # engine/HANDOFF_NOTES.md ## hiker-owner для точной расшифровки выбора.
        line(1, f'сбор роликов по {n_acc} аккаунтам')
        sid, n_reels, miss = collect_snapshot.run(con)
        tracker.mark(1, 'OK')

        line(2, 'оценка против нормы автора по накопленной истории')
        with _job(con, run_id, 'weekly:score', 'STATISTICAL_ANALYSIS'):
            _, taken, res = score.score_snapshot(con)
        print(f'снимок {taken}: оценено {len(res)}, прошло порог {sum(1 for r in res if r["eligible"])}')
        tracker.mark(2, 'OK')

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
                tracker.mark(3, 'FAILED', 'ссылки мертвы сразу после сбора')
            else:
                # разбор верхушки = расшифровка + кадры; ближе по смыслу к TRANSCRIPTION,
                # хотя deep.run() делает и то, и другое за один проход
                with _job(con, run_id, 'weekly:deepdive', 'TRANSCRIPTION'):
                    done, no_url, empty = deep.run(con, rows)
                print(f'разобрано {done} из {len(rows)}, без ссылки {len(no_url)}, пустых {len(empty)}')
                tracker.mark(3, 'OK')
        else:
            tracker.mark(3, 'SKIPPED', 'в окне подходящих нет')

        line(4, 'разметка тем: верхушка целиком, остальное выборкой')
        with _job(con, run_id, 'weekly:topics', 'CATEGORIZATION'):
            done, unknown, n_rest = tag_topics.tag(con)
        tot, unk = sum(done.values()), sum(unknown.values())
        print(f'размечено {tot}, нераспознанных {unk} ({100 * unk / max(tot, 1):.0f}%)')
        tracker.mark(4, 'OK')

        line(5, 'подписчики набора — для ответа «кто растёт»')
        try:
            with _job(con, run_id, 'weekly:followers', 'PROFILE_FETCHED'):
                roster.refresh_followers(con)
            tracker.mark(5, 'OK')
        except Exception as e:
            print(f'источник профилей недоступен: {e}')
            tracker.mark(5, 'FAILED', str(e)[:120])

        line(6, 'живость и выбраковка')
        roster.check(con, silent_accounts=set(miss))
        if miss:
            print(f'не отдали ленту и получили промах: {len(miss)}')
        tracker.mark(6, 'OK')

        line(7, 'решения прошлой недели из Notion')
        try:
            with _job(con, run_id, 'weekly:notion-pull', 'NOTION_SYNC'):
                notion.pull(con)
            tracker.mark(7, 'OK')
        except SystemExit as e:
            print(f'Notion недоступен, идём дальше: {e}')
            tracker.mark(7, 'FAILED', str(e)[:160])

        line(8, 'карточки: блоки агентом → шортлист 15 → карточки решения')
        # 8а. блок каждому новому ролику пула (RULES.md §13.2): агент читает подпись и
        # расшифровку; ролики с файлом пропускаются, так что в будни это минуты
        notes = []
        for what, mod, budget in (('блоки', 'engine.block_route', 3600),
                                  ('карточки решения', 'engine.shortlist_adapt', 2700)):
            if what == 'карточки решения':
                with _job(con, run_id, 'weekly:cards', 'CARD_GENERATION'):
                    picked, pool_n, rep_n = cards.select(con)
                    week = cards.save(con, picked)
                print(f'кандидатов {pool_n}, повторяющихся тем {rep_n}, записано карточек {len(picked)}')
                for c in picked:
                    print(f'  {c["n"]:>2}. s{c["stage"]} {c["block"]:<10} {c["author"]:<22} {c["age"]:>2} дн.  {c["why"][:56]}')
            try:
                r = subprocess.run([sys.executable, '-m', mod, 'run', '--yes'], timeout=budget,
                                   capture_output=True, text=True)
                print((r.stdout or '').strip()[-600:])
                if r.returncode != 0:
                    notes.append(f'{what}: код {r.returncode}')
                    print((r.stderr or '').strip()[-400:])
            except subprocess.TimeoutExpired:
                notes.append(f'{what}: таймаут {budget} с')
                print(f'{what}: не уложились в {budget} с, идём дальше')
        tracker.mark(8, 'OK' if picked and not notes else ('SKIPPED' if not picked else 'FAILED'),
                     '; '.join(notes) if notes else ('' if picked else 'кандидатов не набралось'))

        line(9, 'что сдвинулось с прошлого снимка')
        delta.report(con)
        tracker.mark(9, 'OK')

        line(10, 'карточки в Notion')
        try:
            with _job(con, run_id, 'weekly:notion-cards', 'NOTION_SYNC'):
                n = notion.push(con, week)
            print(f'выгружено: {n}')
            tracker.mark(10, 'OK')
        except SystemExit as e:
            print(f'выгрузка не прошла: {e}')
            tracker.mark(10, 'FAILED', str(e)[:160])

        line(11, 'таблицы, на которых стоят решения — в Notion')
        try:
            with _job(con, run_id, 'weekly:notion-stats', 'NOTION_SYNC'):
                stats.push(con)
            print('раздел с цифрами обновлён')
            tracker.mark(11, 'OK')
        except SystemExit as e:
            print(f'не прошло: {e}')
            tracker.mark(11, 'FAILED', str(e)[:160])

        line(12, 'полные базы в Notion: ролики и аккаунты')
        try:
            with _job(con, run_id, 'weekly:notion-fulldb', 'NOTION_SYNC'):
                notion_db.push_reels(con)
                notion_db.push_accounts(con)
            tracker.mark(12, 'OK')
        except SystemExit as e:
            print(f'не прошло: {e}')
            tracker.mark(12, 'FAILED', str(e)[:160])

        line(13, 'три страницы')
        for k, (fn, name) in pages.BUILD.items():
            (pages.OUT / name).write_text(fn(con), encoding='utf-8')
            print(f'  {name:<12} {(pages.OUT / name).stat().st_size / 1024:>7.0f} КБ')
        tracker.mark(13, 'OK')

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
    finally:
        print(tracker.render())
        if engine_state and run_id:
            try:
                status = 'FAILED' if any(s == 'FAILED' for s, _ in tracker.rows.values()) else 'DONE'
                summary = {n: {'title': STEP_TITLES[n], 'state': s, 'reason': r}
                          for n, (s, r) in tracker.rows.items()}
                engine_state.finish_run(con, run_id, status, summary)
            except Exception:
                pass   # трекинг — удобство, не должен маскировать реальный исход прогона


if __name__ == '__main__':
    main(run='--yes' in sys.argv)
