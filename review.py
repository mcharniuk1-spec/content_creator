#!/usr/bin/env python3
"""План против результата. SPEC §4.8, слой 5.

    python3 review.py

Сравнивается одно: попал ли ролик, который радар считал сильным углом, в верхнюю треть
наших по пересылкам на тысячу. Правило проверяется через 12 публикаций — раньше выборка
слишком мала, и об этом здесь говорится прямо, а не молчанием.
"""
import statistics, sys
from db import connect

MIN_POSTS = 12


def rows(con):
    return con.execute("""SELECT p.id, p.published_at, p.topic, p.format, p.ref_code,
            c.pri, c.angle,
            m.reach_followers, m.reach_nonfollowers, m.retention, m.saves, m.follows
        FROM our_posts p
        LEFT JOIN our_metrics m ON m.post_id = p.id
        LEFT JOIN cards c ON c.code = p.ref_code
        ORDER BY p.published_at""").fetchall()


def report(con):
    rs = rows(con)
    have = [r for r in rs if r['reach_followers'] is not None]
    print(f'публикаций {len(rs)}, с замерами {len(have)}\n')
    if not rs:
        print('аккаунт ещё не запущен — сравнивать нечего.')
        print('После съёмки: python3 posts.py add ДАТА "тема" ФОРМАТ --ref КОД, потом metrics N')
        return
    if len(have) < MIN_POSTS:
        print(f'замеров {len(have)} из {MIN_POSTS} — правило проверять рано.')
        print('Считаем, но выводов не делаем: на такой выборке любой вывод — случайность.\n')
    for r in have:
        reach = (r['reach_followers'] or 0) + (r['reach_nonfollowers'] or 0)
        s1k = (r['saves'] or 0) * 1000 / max(reach, 1)
        print(f"  {r['published_at']}  {(r['topic'] or '')[:34]:<36} "
              f"охват {reach:>7} · сохранений/1k {s1k:>5.0f} · подписок {r['follows'] or 0:>4}"
              + ('   ← был приоритет 1' if r['pri'] == 1 else ''))
    if len(have) >= MIN_POSTS:
        by = sorted(have, key=lambda r: -((r['saves'] or 0) * 1000 /
                    max((r['reach_followers'] or 0) + (r['reach_nonfollowers'] or 0), 1)))
        third = set(x['id'] for x in by[:max(1, len(by) // 3)])
        strong = [r for r in have if r['pri'] == 1]
        hit = sum(1 for r in strong if r['id'] in third)
        print(f'\nиз {len(strong)} роликов с первым приоритетом в верхнюю треть попали {hit}')
        print('если меньше трети — правила отбора врут, и править надо их, а не съёмку')


if __name__ == '__main__':
    report(connect())
