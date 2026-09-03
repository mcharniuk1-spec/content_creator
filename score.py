#!/usr/bin/env python3
"""Оценка ролика против медианы его собственного автора.

Формула Макса (m2_engine): robust-z по ln(1+x), MAD вместо стандартного отклонения,
группировка по автору, минимальная база 5 роликов, пропущенный компонент не заполняется
нулём, а выкидывается с пересчётом весов.

Наши отличия: добавлены сохранения (ниша save-driven); «ранняя скорость» выключена,
пока не накопятся недельные снимки; база сравнения автора собирается по всей истории
снимков, а не по текущей выгрузке (SPEC §4.3, `baseline.py`).

Запуск:
    python3 score.py           оценить последний снимок, записать в базу
    python3 score.py --json    старый путь: посчитать из reels.json в scored_*.json
"""
import json, math, statistics, pathlib, collections, sys, time

D = pathlib.Path(__file__).parent/'data'
EPS = 1e-9
MIN_BASELINE = 5
Z_CLIP = 5.0        # потолок и пол для одной компоненты: без него почти нулевой MAD взрывает оценку
MAD_FLOOR = 0.05    # для долей: разброс меньше 5% от медианы — судить не о чем
LOG_MAD_FLOOR = 0.10  # для просмотров шкала логарифмическая, и 5% от медианы там означали бы
                      # разброс почти вдвое. Компонента просмотров из-за этого выбрасывалась
                      # у 41% роликов, и верхушка ранжировалась по двум разным шкалам сразу.
PLAY_FLOOR = 0.30   # ролик, недобравший 30% медианы своего автора, в подборку не идёт
AGE_BANDS = (7, 30, 90)   # свежий ролик ещё набирает просмотры, и сравнивать его с годовалыми
                          # нечестно: на замере медиана к норме автора шла 0.70× у роликов
                          # до трёх дней и 1.54× у роликов старше трёх месяцев

# Два набора весов — сравниваем осознанно.
W_MAX = {'views':0.30, 'eng':0.20, 'resh':0.20, 'save':0.20, 'comm':0.10}   # как у Макса, save на месте velocity
W_IG  = {'views':0.15, 'eng':0.15, 'resh':0.30, 'save':0.30, 'comm':0.10}   # по опубликованным механикам Instagram

def age_band(ts, now=None):
    """Полка возраста: ролики сравниваются внутри своей, а не со всей лентой автора."""
    if not ts:
        return len(AGE_BANDS)
    days = ((now or time.time()) - ts) / 86400
    for i, edge in enumerate(AGE_BANDS):
        if days <= edge:
            return i
    return len(AGE_BANDS)


def per_1k(v, play):
    return None if v is None or not play else v * 1000.0 / play

def components(r):
    """Сырые значения компонент. None = «н/д», не ноль."""
    p = r['play']
    return {
        'views': math.log1p(p),
        'eng':   per_1k((r['like'] or 0) + (r['comm'] or 0), p),
        'resh':  per_1k(r['resh'], p),
        'save':  per_1k(r['save'], p),
        'comm':  per_1k(r['comm'], p),
    }

def robust_z(x, xs, log_scale=False):
    """log_scale — величина уже в логарифмах, порог разброса там абсолютный."""
    med = statistics.median(xs)
    mad = statistics.median([abs(v - med) for v in xs])
    floor = LOG_MAD_FLOOR if log_scale else MAD_FLOOR * abs(med)
    if mad < EPS or mad < floor:
        return None                      # разброса нет — компонента ничего не различает
    z = 0.6745 * (x - med) / mad
    return max(-Z_CLIP, min(Z_CLIP, z))  # обрезаем, чтобы один компонент не решал всё

def score(rows, weights, base=None, now=None):
    """rows — что оцениваем, base — {pk_user: [ролики]} для сравнения.

    Без base каждый автор сравнивается сам с собой внутри rows (старое поведение).
    С base распределение берётся из накопленной истории, а оцениваются только rows.
    """
    now = now or time.time()
    by = collections.defaultdict(list)
    for r in rows: by[r['pk_user']].append(r)
    out = []
    for pk, rs in by.items():
        bs_all = base.get(pk, []) if base is not None else rs
        if len(bs_all) < MIN_BASELINE: continue
        comps = [components(r) for r in rs]
        for r, c in zip(rs, comps):
            # сам ролик из своей же нормы исключается: иначе выброс частично прячет сам себя
            bs = [b for b in bs_all if b.get('code') != r.get('code')]
            # и сравнивается он со своей возрастной полкой, если в ней хватает роликов
            band = age_band(r.get('ts'), now)
            same = [b for b in bs if age_band(b.get('ts'), now) == band]
            banded = len(same) >= MIN_BASELINE
            if banded:
                bs = same
            if len(bs) < MIN_BASELINE - 1: continue
            base_comps = [components(b) for b in bs]
            zs, used = {}, {}
            for name in weights:
                xs = [cc[name] for cc in base_comps if cc[name] is not None]
                if c[name] is None or len(xs) < MIN_BASELINE: continue
                z = robust_z(c[name], xs, log_scale=(name == 'views'))
                if z is None: continue
                zs[name] = z; used[name] = weights[name]
            if not used: continue
            tot = sum(used.values())
            r2 = dict(r)
            r2['z'] = round(sum(zs[n]*used[n] for n in used)/tot, 4)
            r2['components'] = {n: round(zs[n], 2) for n in zs}
            r2['omitted'] = [n for n in weights if n not in zs]
            r2['axes'] = len(zs)          # на скольких осях посчитана оценка
            amp = int(statistics.median([x['play'] for x in bs]))
            r2['author_median_play'] = amp
            r2['baseline_n'] = len(bs)
            r2['banded'] = banded          # считалось ли по возрастной полке
            r2['eligible'] = r['play'] >= max(1000, PLAY_FLOOR * amp)
            for n in ('resh','save','comm'):
                r2[n+'_1k'] = per_1k(r[n], r['play'])
            out.append(r2)
    out.sort(key=lambda r: -r['z'])
    return out

def score_snapshot(con, weights=W_IG, tag='ig'):
    """Оценить последний снимок против накопленной базы и записать в scores."""
    import baseline
    snap = baseline.last_snapshot(con)
    if not snap:
        print('снимков нет — сначала сбор'); return None, None, []
    sid, taken = snap
    base, snaps = baseline.by_author(con)
    rows = [r for r in baseline.snapshot_rows(con, sid) if r.get('play')]
    for r in rows: r['like'] = r.pop('likes')          # имя колонки в базе — likes
    for v in base.values():
        for b in v:
            if 'likes' in b: b['like'] = b.pop('likes')
    res = score(rows, weights, base)
    con.execute('DELETE FROM scores WHERE snapshot_id=? AND weights=?', (sid, tag))
    con.executemany("""INSERT INTO scores
        (snapshot_id,code,z,eligible,author_median_play,c_views,c_eng,c_resh,c_save,c_comm,
         resh_1k,save_1k,comm_1k,baseline_n,baseline_snaps,weights,axes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(sid, r['code'], r['z'], int(r['eligible']), r['author_median_play'],
          r['components'].get('views'), r['components'].get('eng'), r['components'].get('resh'),
          r['components'].get('save'), r['components'].get('comm'),
          r['resh_1k'], r['save_1k'], r['comm_1k'], r['baseline_n'],
          snaps.get(r['pk_user']), tag, r['axes']) for r in res])
    con.commit()
    return sid, taken, res


if __name__ == "__main__" and '--json' not in sys.argv:
    from db import connect
    con = connect()
    sid, taken, res = score_snapshot(con)
    zs = sorted(r['z'] for r in res)
    print(f'снимок {taken}: оценено {len(res)}, прошло порог '
          f'{sum(1 for r in res if r["eligible"])}')
    print(f'z: медиана {zs[len(zs)//2]:.3f}, максимум {zs[-1]:.2f}, минимум {zs[0]:.2f}')
    bn = sorted(r['baseline_n'] for r in res)
    print(f'база сравнения на ролик: медиана {bn[len(bn)//2]} роликов автора')
    print('\nтоп-5:')
    for r in res[:5]:
        print(f"  {r['username']:<22} {r['play']:>9,}  z={r['z']:.2f}  "
              f"медиана автора {r['author_median_play']:,}  база {r['baseline_n']}")
    sys.exit()

if __name__ == "__main__":
    rows = [r for r in json.load(open(D/'reels.json')) if r.get('play')]
    print(f"роликов с просмотрами: {len(rows)} из {len(json.load(open(D/'reels.json')))}")
    sv = sum(1 for r in rows if r['save'] is not None)
    print(f"сохранения есть у {sv} ({100*sv//len(rows)}%), пересылки у {sum(1 for r in rows if r['resh'])}")
    for name, W in (('IG', W_IG), ('MAX', W_MAX)):
        s = score(rows, W)
        json.dump(s, open(D/f'scored_{name.lower()}.json','w'), ensure_ascii=False)
        print(f"{name}: оценено {len(s)}, топ-z {s[0]['z']}, медиана z {statistics.median([r['z'] for r in s]):.3f}")
    a = {r['code'] for r in json.load(open(D/'scored_ig.json'))[:40]}
    b = {r['code'] for r in json.load(open(D/'scored_max.json'))[:40]}
    print(f"\nпересечение топ-40 между двумя наборами весов: {len(a&b)} из 40")
