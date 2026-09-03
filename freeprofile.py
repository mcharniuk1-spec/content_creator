#!/usr/bin/env python3
"""Бесплатный публичный профиль Instagram. Без ключа, без единиц HikerAPI.
Проверено 01.09.2026: работает обычным curl с браузерным User-Agent."""
import json, subprocess, time, pathlib, hashlib
CACHE = pathlib.Path(__file__).parent/'cache-free'; CACHE.mkdir(exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"

def profile(username, pause=0.7, fresh=False):
    """fresh=True — мимо кэша: подписчики меняются, и замороженное число бесполезно."""
    fn = CACHE/f"{hashlib.md5(username.encode()).hexdigest()[:12]}.json"
    if fn.exists() and not fresh:
        return json.loads(fn.read_text())
    from urllib.parse import quote
    p = subprocess.run(["curl","-s","--max-time","25","--proto","=https",
        "-H","x-ig-app-id: 936619743392459", "-H",f"User-Agent: {UA}", "--",
        "https://www.instagram.com/api/v1/users/web_profile_info/?username="
        + quote(username, safe='')],
        capture_output=True, text=True)
    time.sleep(pause)
    try:
        u = json.loads(p.stdout)["data"]["user"]
    except Exception:
        return None
    out = dict(pk=u["id"], username=u["username"], full_name=u.get("full_name"),
               follower_count=u["edge_followed_by"]["count"],
               media_count=u["edge_owner_to_timeline_media"]["count"],
               biography=u.get("biography"), category=u.get("category_name"),
               is_private=u.get("is_private"), is_verified=u.get("is_verified"))
    fn.write_text(json.dumps(out, ensure_ascii=False))
    return out
