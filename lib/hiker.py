#!/usr/bin/env python3
"""Кэширующий клиент HikerAPI.

Ключ читается из ~/Desktop/.mcp.json — в код не класть.
Все запросы через curl: urllib на этой машине падает на SSL.
Каждый ответ пишется на диск; повторный вызов с теми же параметрами стоит ноль.
Реальная цена берётся из заголовка ответа x-hiker-info.

  python3 hiker.py balance
  python3 hiker.py profile ampleevandrey
  python3 hiker.py about 3598258148              # дата создания, страна, прежние имена
  python3 hiker.py medias 3598258148 --pages 3   # лента с reshare/save (рилсы + статика)
  python3 hiker.py clips 3598258148 --pages 2    # только рилсы
  python3 hiker.py highlights 3598258148         # с force=on: 1 единица вместо 2
  python3 hiker.py reels "йога для начинающих"   # разведка ниши
  python3 hiker.py suggested 3598258148          # 80 соседей за 1 запрос
  python3 hiker.py get /v1/media/by/code code=DcEKGyyojT8

Флаги: --no-cache, --cache DIR (по умолчанию ./hiker-cache), --pages N.
"""
import datetime, json, os, pathlib, os, sys, time, hashlib, pathlib, subprocess, urllib.parse

BASE = "https://api.hikerapi.com"

# Единственный источник тарифа: раньше 0.02 было прописано буквально в трёх файлах
# (lib/hiker.py, collect_snapshot.py, roster.py) — при смене тарифа три места надо было
# редактировать руками, и ничто не подсказывало, что цифра устарела. Теперь PRICE
# выводится из этой датированной квитанции; collect_snapshot.py и roster.py делают
# `from lib.hiker import PRICE` вместо своего литерала.
PRICE_RECEIPT = {
    "price_usd": 0.02,
    "tariff": "Start",
    "source": "hiker-doc.readthedocs.io/guides/rate-limits",
    "checked": "2026-08-31",
}
PRICE = PRICE_RECEIPT["price_usd"]

RATE_SLEEP = 1 / 15     # 15 запросов в секунду на платных планах
KEYFILE = pathlib.Path.home() / "Desktop" / ".mcp.json"

_cache_dir = pathlib.Path(os.environ.get("HIKER_CACHE", "hiker-cache"))
_units = 0              # единицы запроса, списанные за этот процесс
_last = 0.0
_last_meta = None       # provenance последнего call(): см. last_fetch_meta()


def _key():
    """Ключ из окружения или из .env рядом с проектом; на маке — из настроек MCP.

    Три источника, потому что инструмент живёт в двух местах: на сервере ключ
    приходит из .env, на рабочей машине — из того же файла, что и у остальных
    инструментов, чтобы не держать его в двух копиях.
    """
    if os.environ.get("HIKER_KEY"):
        return os.environ["HIKER_KEY"]
    env = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("HIKER_KEY="):
                return line.split("=", 1)[1].strip()
    try:
        return json.loads(KEYFILE.read_text())["mcpServers"]["hikerapi"]["env"]["HIKERAPI_KEY"]
    except Exception as e:
        sys.exit(f"ключ не найден: ни в HIKER_KEY, ни в .env, ни в {KEYFILE}: {e}")


def _curl_transport(url, key, timeout=45):
    """Транспорт по умолчанию: curl (urllib на этой машине падает на SSL, см. модуль).
    Возвращает сырой stdout — заголовки + пустая строка + тело, как отдаёт curl -D -.
    Инжектируется через call(transport=...), чтобы тесты не трогали subprocess."""
    p = subprocess.run(
        ["curl", "-s", "-D", "-", "--max-time", str(timeout),
         "-H", f"x-access-key: {key}",
         "-H", "accept: application/json", url],
        capture_output=True, text=True)
    return p.stdout


def _meta_path(fn):
    return fn.with_name(fn.name + ".meta.json")


def last_fetch_meta():
    """Provenance последнего call(): свежего запроса или попадания в кэш.
    None до первого вызова call() в этом процессе."""
    return _last_meta


def call(path, use_cache=True, tries=3, transport=None, **params):
    """Один вызов. Возвращает разобранный JSON или None."""
    global _units, _last, _last_meta
    transport = transport or _curl_transport
    params = {k: v for k, v in params.items() if v is not None}
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}{path}" + (f"?{qs}" if qs else "")

    _cache_dir.mkdir(parents=True, exist_ok=True)
    slug = path.strip("/").replace("/", "_")
    fn = _cache_dir / f"{slug}_{hashlib.md5(url.encode()).hexdigest()[:12]}.json"
    if use_cache and fn.exists():
        mp = _meta_path(fn)
        if mp.exists():
            try:
                _last_meta = json.loads(mp.read_text())
            except Exception:
                _last_meta = {"endpoint": path, "cache_path": str(fn), "note": "meta unreadable"}
        else:
            # кэш старее этой функциональности: провенанса нет, но повторный вызов
            # всё равно не должен падать
            _last_meta = {"endpoint": path, "cache_path": str(fn), "note": "no sidecar (pre-provenance cache)"}
        return json.loads(fn.read_text())

    last = None
    for attempt in range(tries):
        gap = time.time() - _last
        if gap < RATE_SLEEP:
            time.sleep(RATE_SLEEP - gap)
        raw = transport(url, _key())
        _last = time.time()
        head, _, body = raw.partition("\r\n\r\n")
        if not body:
            head, _, body = raw.partition("\n\n")

        # x-hiker-info даёт НОМИНАЛЬНУЮ цену эндпоинта, а не факт списания:
        # заголовок приходит и на 50x, которые не билятся. Считаем только реально
        # оплаченные исходы — 200, 400, 403, 404.
        nominal = 0
        for line in head.splitlines():
            if line.lower().startswith("x-hiker-info:"):
                try:
                    nominal = int(json.loads(line.split(":", 1)[1].strip()).get("reqs", 0))
                except Exception:
                    pass

        code = 0
        if head.startswith("HTTP/"):
            try:
                code = int(head.split()[1])
            except Exception:
                pass

        if code == 429:                       # лимит в секунду, не билится
            time.sleep(2)
            continue
        if code == 402:
            sys.exit("[hiker] 402: кончились деньги на счёте")

        try:
            d = json.loads(body)
        except Exception:
            last = (body or "")[:200]
            time.sleep(2 * (attempt + 1))
            continue

        if isinstance(d, dict) and d.get("exc_type"):
            last = d
            if code in (400, 403, 404):
                _units += nominal          # провайдер сделал работу — платим
            # 50x не билятся, но повторять больше двух раз бессмысленно:
            # если провайдер лёг, он лежит надолго.
            if d["exc_type"] in ("InstagramServerError", "InternalError") and attempt >= 1:
                break
            if d["exc_type"] in ("EndpointDeprecated", "ValidationError", "UserNotFound"):
                break                         # повтор не поможет, а 400/404 ещё и билятся
            time.sleep(3 * (attempt + 1))
            continue

        _units += nominal
        fn.write_text(json.dumps(d, ensure_ascii=False))
        # Провенанс рядом с ответом: раньше кэш был просто файлом с телом ответа,
        # и по нему нельзя было узнать, когда он получен и по какой цене — только
        # реверсить md5 в имени файла. Ключ сюда никогда не попадает — только
        # эндпоинт, параметры (без секретов) и метаданные ответа.
        _last_meta = {
            "fetched_at": datetime.datetime.now(datetime.timezone.utc)
                .isoformat(timespec="seconds").replace("+00:00", "Z"),
            "endpoint": path,
            "params": {k: v for k, v in params.items()
                       if "key" not in k.lower() and "token" not in k.lower()},
            "http_status": code or 200,
            "units": nominal,
            "cache_path": str(fn),
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        }
        try:
            _meta_path(fn).write_text(json.dumps(_last_meta, ensure_ascii=False))
        except OSError:
            pass  # провенанс — удобство, не должен ронять сбор из-за диска
        return d
    print(f"[hiker] не вышло {path}: {last}", file=sys.stderr)
    return None


def balance():
    return call("/sys/balance", use_cache=False)


def profile(username):
    d = call("/v1/user/by/username", username=username)
    return (d or {}).get("user") or d


def about(user_id):
    """Дата создания аккаунта, страна регистрации, прежние имена."""
    return call("/gql/user/about", id=user_id)


def medias(user_id, pages=2):
    """Вся лента с play/reshare/save — рилсы и статика вместе. Лучший выбор по умолчанию."""
    out, cur = [], None
    for _ in range(pages):
        d = call("/gql/user/medias", user_id=user_id, flat="true",
                 profile_grid_items_cursor=cur)
        if not d:
            break
        items = d.get("items") or []
        out += items
        cur = d.get("profile_grid_items_cursor") or d.get("end_cursor")
        if not cur or not items:
            break
    return out


def clips(user_id, pages=2, sort_by_views=None):
    """Только рилсы, 12 за запрос."""
    out, mx = [], None
    for _ in range(pages):
        d = call("/gql/user/clips", user_id=user_id, flat="true",
                 max_id=mx, sort_by_views=sort_by_views)
        if not d:
            break
        out += d.get("items") or []
        mx = d.get("max_id")
        if not d.get("more_available") or not mx:
            break
    return out


def highlights(user_id):
    """force=on снимает проверку приватности: 1 единица вместо 2."""
    return call("/v1/user/highlights", user_id=user_id, force="on")


def reels_search(query, max_id=None):
    """Разведка ниши. Искать рилсы, не аккаунты."""
    d = call("/v2/fbsearch/reels", query=query, reels_max_id=max_id)
    if not d:
        return [], None
    out = []
    for mod in d.get("reels_serp_modules", []):
        for c in mod.get("clips", []):
            m = c.get("media") or {}
            u = m.get("user") or {}
            out.append(row(m, user=u.get("username"), followers=u.get("follower_count")))
    return out, d.get("reels_max_id")


def suggested(user_id, expand=False):
    """80 соседних аккаунтов за 1 запрос. Наследует язык сида. Подписчиков не отдаёт."""
    d = call("/v2/user/suggested/profiles", user_id=user_id,
             expand_suggestion="true" if expand else None)
    return (d or {}).get("users") or (d or {}).get("items") or d


def row(m, **extra):
    """Плоская строка. save намеренно может быть None — не ноль."""
    cap = ((m.get("caption") or {}).get("text") or "").replace("\n", " ")
    r = dict(
        code=m.get("code"),
        ts=m.get("taken_at") or m.get("1ltaken_at"),
        kind=m.get("product_type") or ("clips" if m.get("video_duration") else "static"),
        play=m.get("play_count") or 0,          # view_count всегда пуст
        like=m.get("like_count") or 0,
        comm=m.get("comment_count") or 0,
        resh=m.get("reshare_count") or 0,
        save=m.get("save_count"),               # None = «н/д»
        dur=round(m.get("video_duration") or m.get("1fvideo_duration") or 0, 1),
        cap=cap[:200],
    )
    r.update(extra)
    return r


def per_1k(r, field):
    v = r.get(field)
    return None if v is None or not r.get("play") else round(v * 1000 / r["play"], 1)


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _summary(rows):
    reels = [r for r in rows if r["play"]]
    return (f"{len(rows)} постов ({len(reels)} с просмотрами) · "
            f"медиана просмотров {median([r['play'] for r in reels])} · "
            f"пересылок/1k {median([per_1k(r,'resh') for r in reels])} · "
            f"сохранений/1k {median([per_1k(r,'save') for r in reels])}")


def _main():
    global _cache_dir
    argv = sys.argv[1:]
    if "--cache" in argv:
        _cache_dir = pathlib.Path(argv[argv.index("--cache") + 1])
    pages = int(argv[argv.index("--pages") + 1]) if "--pages" in argv else 2
    uc = "--no-cache" not in argv
    args = [a for i, a in enumerate(argv)
            if not a.startswith("--") and (i == 0 or not argv[i - 1] in ("--cache", "--pages"))]
    if not args:
        sys.exit(__doc__)
    cmd, rest = args[0], args[1:]

    if cmd == "balance":
        b = balance() or {}
        print(json.dumps(b, ensure_ascii=False))
        print(f"≈ {b.get('requests')} единиц ≈ ${b.get('amount')} · "
              f"лимит {b.get('rate')} зпр/сек · цена единицы ${PRICE}", file=sys.stderr)
    elif cmd == "get":
        kw = dict(p.split("=", 1) for p in rest[1:])
        print(json.dumps(call(rest[0], use_cache=uc, **kw), ensure_ascii=False, indent=1))
    elif cmd == "profile":
        u = profile(rest[0]) or {}
        print(json.dumps({k: u.get(k) for k in
              ("pk", "username", "full_name", "follower_count", "following_count",
               "media_count", "biography", "category", "is_verified", "is_private")},
              ensure_ascii=False, indent=1))
    elif cmd == "about":
        print(json.dumps(about(rest[0]), ensure_ascii=False, indent=1))
    elif cmd in ("medias", "clips"):
        raw = (medias if cmd == "medias" else clips)(rest[0], pages=pages)
        rows = [row(m) for m in raw]
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        print(_summary(rows), file=sys.stderr)
    elif cmd == "highlights":
        print(json.dumps(highlights(rest[0]), ensure_ascii=False, indent=1))
    elif cmd == "reels":
        rows, _ = reels_search(" ".join(rest))
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        if rows:
            print(_summary(rows), file=sys.stderr)
    elif cmd == "suggested":
        print(json.dumps(suggested(rest[0]), ensure_ascii=False, indent=1))
    else:
        sys.exit(__doc__)

    print(f"[hiker] списано единиц: {_units} ≈ ${_units * PRICE:.2f}", file=sys.stderr)


if __name__ == "__main__":
    _main()
