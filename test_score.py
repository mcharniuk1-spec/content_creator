"""Формула: то, что аудит нашёл незакрытым ни одной проверкой.

Проверяется на собранных вручную наборах, а не на живой базе: нужно видеть,
что делает каждый предохранитель по отдельности.
"""
import sys, time
import score

fail = []
def eq(n, g, w):
    print(f"  {'✓' if g == w else '✗'} {n:<54} {g}   ожидалось {w}")
    if g != w: fail.append(n)

NOW = time.time()
def reel(code, play, resh=None, save=None, like=10, comm=2, days=1, pk=1):
    return dict(code=code, pk_user=pk, play=play, like=like, comm=comm,
                resh=resh if resh is not None else play // 100,
                save=save, dur=55.0, ts=NOW - days * 86400)

# ── порог разброса: на логарифмической оси абсолютный, на шкале долей относительный ──
import math
xs = [math.log1p(p) for p in (4000, 7000, 10000, 15000, 25000)]     # обычный разброс автора
eq('живой автор: просмотры не выбрасываются',
   score.robust_z(xs[2], xs, log_scale=True) is not None, True)
flat = [math.log1p(p) for p in (9800, 9900, 10000, 10100, 10200)]   # ровный как стол
eq('автор без разброса: компонента выбрасывается',
   score.robust_z(flat[2], flat, log_scale=True), None)
eq('на шкале долей порог свой',
   score.robust_z(20.0, [20.0, 20.1, 19.9, 20.05, 20.02], log_scale=False), None)
eq('совсем без разброса выбрасывается всегда',
   score.robust_z(5.0, [5.0] * 6, log_scale=True), None)

# ── потолок оценки ──
z = score.robust_z(1000.0, [10.0, 14.0, 20.0, 26.0, 33.0], log_scale=False)
eq('одна компонента не может решить всё', z, score.Z_CLIP)

# ── ролик не входит в собственную норму ──
base = [reel(f'BASE{i:02d}', p) for i, p in enumerate((600, 800, 1000, 1200, 1500, 2000))]
hit = reel('HITCODE01', 100000)
res = score.score([hit], score.W_IG, base={1: base + [hit]}, now=NOW)
eq('оценка посчиталась', len(res), 1)
eq('медиана автора не поднялась из-за самого ролика', res[0]['author_median_play'], 1100)

# ── возрастные полки ──
old = [reel(f'OLD{i:02d}', p, days=200) for i, p in enumerate((30000, 40000, 50000, 60000, 80000, 100000))]
fresh = [reel(f'NEW{i:02d}', p, days=1) for i, p in enumerate((600, 800, 1000, 1200, 1500, 2000))]
r = score.score([fresh[0]], score.W_IG, base={1: old + fresh}, now=NOW)
eq('свежий ролик сравнивается со свежими, а не с годовалыми',
   r[0]['author_median_play'], 1200)
eq('и это отмечено в оценке', r[0]['banded'], True)

# ── пропуск не превращается в ноль ──
rows = [reel(f'MIX{i:02d}', 1000 + i * 500, save=None if i % 2 else 30) for i in range(8)]
res = score.score(rows, score.W_IG, base={1: rows}, now=NOW)
eq('ролик без сохранений всё равно оценивается', len(res), 8)
eq('у него компонента сохранений пропущена, а не нулевая',
   all('save' in r['omitted'] for r in res if r['save'] is None), True)
eq('веса пересчитаны на уцелевшие оси',
   all(r['axes'] == len(r['components']) for r in res), True)

# ── минимальная база ──
eq('автор с четырьмя роликами не оценивается',
   len(score.score([reel('SHORT01', 900)], score.W_IG,
                   base={1: [reel(f'S{i}0000', 600 + i * 400) for i in range(4)]}, now=NOW)), 0)

# ── порог попадания в подборку ──
base9 = [reel(f'B{i:02d}000', 6000 + i * 1500) for i in range(9)]
weak = reel('WEAKCODE1', 500)
res = score.score([weak], score.W_IG, base={1: base9 + [weak]}, now=NOW)
eq('ролик ниже 30% нормы автора в подборку не идёт',
   res[0]['eligible'] if res else None, False)

# ── одинаковые ролики: молчание вместо ошибки ──
same = [reel(f'SAME{i:02d}0', 1000) for i in range(6)]
eq('у автора без разброса оценок нет, и это не падение',
   score.score(same, score.W_IG, base={1: same}, now=NOW), [])

print('\n' + ('ТЕСТ ПРОЙДЕН' if not fail else f'ПРОВАЛЕНО: {fail}'))
sys.exit(1 if fail else 0)
