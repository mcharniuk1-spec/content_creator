# 03 — Server runtime & HikerAPI integration audit

Scope: `/opt/radar` on `m2vps` (root@vmi3550498), git branch `main` == local `content-engine`
at commit `92e71e7a0543bacce2adafd65941eaa008632d62` ("The profile name leads with the
search term"). Read-only. No file on the server or in the repo was modified; nothing from
`.env` beyond variable names was read or printed.

---

## 1. Server checkout vs. git

- Server: `git status` → `On branch main / Your branch is up to date with 'origin/main'`,
  `git diff --stat` empty. Only untracked path: `.venv/` (the venv itself, correctly
  gitignored). `git rev-parse HEAD` = `92e71e7a0543bacce2adafd65941eaa008632d62`.
- Local (`content-engine`, which is even with `main` — `git log -1 --format=%H main` and
  `content-engine` both resolve to the same commit): same SHA, `git diff --stat main
  content-engine` empty. Local `git status` shows 10 untracked `runs/2026-09-07/*.jpg`
  files (leftover contact-sheet crops from a manual session — not on the server, not a
  discrepancy in the deployed code).
- Conclusion: **server code == git main, exactly.** The runtime gap is entirely in
  what's *not* in git — data, caches, the venv — not in code drift.

### What exists on the server but not in git (sizes, from `du -sh`)

| Path | Size | What it is | In `.gitignore`? |
|---|---|---|---|
| `.venv/` | 509 MB | Python 3.12 venv (faster-whisper, ctranslate2, av, numpy, httpx, imageio-ffmpeg, onnxruntime) | not tracked, not listed (implicit — never committed) |
| `data/` | 303 MB | `radar.db` (5.0 MB, sqlite), `data/frames/` (269 MB, 297 reel folders, 2653 frame files), `data/video/` (empty — videos are deleted after frame extraction), `data/runs/*.log` + weekly `niche.html`/`shoot.html`/`radar.html` copies, `data/archive/` (old audits, snapshots) | `data/` ✓ |
| `cache/` | 112 MB | Raw HikerAPI JSON responses, date-partitioned (`cache/2026-09-04/`, `.../09-07/`, `.../09-08/`, `.../09-10/`), 237 files total incl. `sys_balance_*.json` | `cache/` ✓ |
| `hiker-cache/` | 128 KB | Same client, default (non-dated) cache dir — 31 files, used by ad-hoc `lib/hiker.py` CLI calls outside `collect_snapshot.py`'s dated cache | `hiker-cache/` ✓ |
| `dataset/`, `design/`, `docs/`, `audit-2026-09-08/`, `*.html` build artifacts | ~32 MB combined | working docs / prior audit exports / built pages | mostly `*.html` ✓ (with explicit exceptions for `runs/**/*.html` and `audit.html`) |
| `__pycache__/` | 284 KB | bytecode | ✓ |

Server disk: 193 GB total, 5.9 GB used, 187 GB free — no pressure. RAM: 11 GiB total,
548 MiB used at rest, no swap. 6 CPUs. Matches the stated spec; there is headroom for
faster-whisper `small` on CPU (int8) and ffmpeg frame extraction, which is what the cron
run actually uses.

`sqlite3` row counts on the live DB: `accounts` 1357, `snapshots` 3, `reels` 5147,
`deepdives` 282, `frames` 2653, `transcripts` 273, `cards` 23, `spend` 10. Only 3
snapshots exist total — the project is ~2 weeks old, which matters for the prune.py risk
below (nothing is old enough to be pruned yet).

**Secrets check** — `git grep -nE "hiker_|HIKER|Bearer|x-access-key"` across `*.py`
returns only *references to env vars and header names* (`os.environ["HIKER_KEY"]`,
`f"x-access-key: {_key()}"`, `f"Authorization: Bearer {env('NOTION_TOKEN')}"` in
`notion.py:42`) — **no literal key or token is hardcoded anywhere in the repo.**
`.env.example` (root) lists only variable names with empty values. Confirmed server
`.env` variable names via `sed -E 's/=.*/=<redacted>/' .env`: `HIKER_KEY`,
`NOTION_CARDS_DB`, `NOTION_PAGE`, `NOTION_TOKEN`, `NOTION_REELS_DB`, `NOTION_ACCOUNTS_DB`
— matches `.env.example` exactly. `.env` permissions on both server and locally are
`-rw-------` (600, owner-only).

---

## 2. How HikerAPI is actually called today

**HTTP client** — `lib/hiker.py` (`/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/lib/hiker.py`),
12.5 KB, one file, no framework. Every call shells out to `curl` (`lib/hiker.py:71-75`)
rather than using `httpx` (installed in the venv but unused by this module) — the
docstring at line 5 explains why: *"Все запросы через curl: urllib на этой машине
падает на SSL."* This is the one and only HTTP surface for HikerAPI in the whole repo;
`roster.py`, `collect_snapshot.py` and the ad-hoc CLI all import `hiker` and go through
`hiker.call()`.

**Key resolution** — `lib/hiker.py:33-50`, function `_key()`. Three fallbacks, in order:
1. `os.environ["HIKER_KEY"]` (this is what's used on the server, from `.env` loaded by
   `notion.py`-style `env()` pattern — actually collect_snapshot.py/roster.py rely on the
   shell environment already carrying `HIKER_KEY`, set via `.env` + whatever loads it into
   the process env before Python starts — worth flagging, see gap list);
2. `HIKER_KEY=` line inside `<repo>/.env` if the env var isn't set;
3. `~/Desktop/.mcp.json` → `mcpServers.hikerapi.env.HIKERAPI_KEY` (the Mac-only fallback,
   for parity with the `hikerapi` Claude Code skill on the work laptop).
If none resolve, `sys.exit(f"ключ не найден: ...")` — hard stop, no silent failure.

**Endpoints actually used** (grep of `lib/hiker.py` + call sites):
| Endpoint | Called from | Purpose |
|---|---|---|
| `/sys/balance` | `hiker.balance()` ← `collect_snapshot.balance()` | units left, before every collection run |
| `/v1/user/by/username` | `hiker.profile()` | not used in the weekly pipeline (candidate profiles go through the *free* `freeprofile.py` web endpoint instead) |
| `/gql/user/about` | `hiker.about()` | account creation date/country — not wired into any script's `__main__`, library-only |
| `/gql/user/medias` | `hiker.medias()` | full feed (reels+static) — not used by the weekly collector (which uses `clips` only), available via CLI |
| `/gql/user/clips` | `hiker.clips()` ← `collect_snapshot.run()` | **the only endpoint the paid weekly run hits.** 1 page per account (`PAGES=1`, `collect_snapshot.py:17`), 12 reels/page |
| `/v1/user/highlights` | `hiker.highlights()` | library-only, unused in pipeline |
| `/v2/fbsearch/reels` | `hiker.reels_search()` / `roster._search()` | account discovery ("topup") — paid, but topup isn't in the weekly `run.py` chain, only in manual `roster.py topup --yes` |
| `/v2/user/suggested/profiles` | `hiker.suggested()` / `roster._suggested()` | "similar accounts" discovery — same, topup-only |

So of everything `lib/hiker.py` exposes, the **automated weekly cron run only pays for
two things**: `/sys/balance` (free-ish, informational) and `/gql/user/clips` (the
per-account collection, 1 unit/account/week). `roster.py topup` (search + suggested
accounts) is a separate, manually-invoked, paid path not in `cron.sh`.

**Cost accounting** — `PRICE = 0.02` (Start tariff) is a **hardcoded literal, duplicated
in three files**: `lib/hiker.py:24`, `collect_snapshot.py:18`, `roster.py:23`. There is no
single source of truth and no receipt tying that number to a specific date or HikerAPI
plan page — if the tariff changes, three files need editing and nothing would flag a
stale price. Real spend is tracked in the `spend` table (`db.py:198-206`: `at, item,
units, price, usd, note`) written by `collect_snapshot.run()` (`collect_snapshot.py:93-97`)
and `roster.topup()` (`roster.py:165-167`). Units actually charged are read back from the
**response header**, not assumed from the endpoint: `lib/hiker.py:81-90` parses
`x-hiker-info` for the nominal cost, and `lib/hiker.py:112-125` only adds to the running
`_units` counter on billable outcomes (200/400/403/404), explicitly *not* on 5xx ("50x не
билятся"). This is a real, if informal, budget-safety mechanism — see comparison with
Max's design in §6.

**Caching** — `_cache_dir` (`lib/hiker.py:28`) defaults to `./hiker-cache`, overridable via
`HIKER_CACHE` env var. `collect_snapshot.run()` explicitly repoints it to
`cache/<snapshot-date>/` (`collect_snapshot.py:56-57`) — the code comment at
`collect_snapshot.py:53-55` documents why: without date-partitioning, a same-week re-run
would silently replay last week's feed and 100/109 accounts would return stale data (this
already happened once, per the comment). Cache key = `md5(full URL incl. querystring)`,
first 12 hex chars, filename `<endpoint-slug>_<hash>.json` (`lib/hiker.py:60-62`). **Cache
content is the raw response body only** — `fn.write_text(json.dumps(d, ensure_ascii=False))`
(`lib/hiker.py:126`) — no wrapper with timestamp, request params, or endpoint version. The
filename hash is the only provenance; there is no metadata sidecar. **This is a real gap**:
you cannot look at a cached file and know when it was fetched or under what price/tariff,
only what URL produced it (indirectly, via reversing the hash — not actually recoverable).

**Rate limiting / retries** — `RATE_SLEEP = 1/15` (15 req/s cap, `lib/hiker.py:25`), enforced
by a wall-clock check before each request (`lib/hiker.py:68-70`). Retries: up to 3 attempts
(`tries=3` default), with `429` → sleep 2s and retry without counting against budget
(`lib/hiker.py:99-101`); `402` → hard `sys.exit` ("кончились деньги на счёте");
`InstagramServerError`/`InternalError` → give up after 2 attempts; `EndpointDeprecated` /
`ValidationError` / `UserNotFound` → give up immediately (no point retrying, and 400/404
still bill). Malformed JSON body → retry with backoff `2*(attempt+1)`.

**Normalization** — `hiker.row()` (`lib/hiker.py:203-219`) flattens a raw media object into
`{code, ts, kind, play, like, comm, resh, save, dur, cap}`. Notably `save` is left as
`None` rather than coerced to 0 when HikerAPI doesn't report it ("save намеренно может
быть None — не ноль") — a deliberate, documented distinction between "zero saves" and
"unknown," which the scoring code (`score.py`, not read line-by-line in this audit but
referenced by `stats.py`/`notion_db.py`) is expected to respect. `collect_snapshot.run()`
(`collect_snapshot.py:72-83`) takes each row, checks `safe_code()` (defined in `db.py`,
rejects malformed reel codes before they ever reach the `reels` table), and does
`INSERT OR REPLACE INTO reels`. **There is no separate "raw payload" table or file
referenced from a normalized row** — the only place the raw JSON survives is the
undated-provenance `cache/` directory tree; the `reels` row itself carries no pointer back
to which cache file / which API response it came from. If you needed to re-derive or audit
a specific `reels` row against the exact bytes HikerAPI returned, you'd have to guess which
`cache/<date>/*clips*.json` file to open (this is exactly what `deep.py:_urls()` does,
line 73-88, scanning every `clips*.json` under `cache/` sorted by file mtime — it works,
but it's a linear scan over undifferentiated files, not a lookup).

**No hardcoded secrets** — confirmed above (§1).

---

## 3. The cron run, end to end

**Schedule**: `0 7 * * 1,4 /opt/radar/cron.sh` (Mon/Thu 07:00, server TZ — confirm against
Europe/Vienna if it matters for freshness windows; not verified in this audit).

**`cron.sh`** (`/opt/radar/cron.sh`, same file in git):
1. Sets `PATH`/`HOME=/root`/`LANG`/`LC_ALL=C.UTF-8` explicitly — comment says without this
   neither `claude` nor `git` resolve, and Cyrillic output turns to garbage under cron's
   near-empty environment.
2. `cd /opt/radar`, logs to `data/runs/$(date +%Y-%m-%d_%H%M).log` (untracked, matches §1).
3. **`git pull -q --rebase`** before running — "код мог обновиться на рабочей машине." If
   it fails, the comment says to continue on current code (`|| echo "git pull не прошёл,
   идём на текущем коде"`) — but the run itself is **not gated** on that failure; a broken
   rebase just gets logged and the cron proceeds on whatever `main` state it's in. Flagged
   as a risk in §7c.
4. `timeout 7200 .venv/bin/python run.py --yes` — the 13-step pipeline (below).
5. If `run.py` exit code is 0: `claude -p "$(cat prompts/angles.md)" --allowed-tools
   "Bash,Read,Edit" ` (60-minute timeout) writes angles/hooks onto the week's cards, then
   `notion.py push`, then rebuilds `niche.html`/`shoot.html`/`radar.html` via `pages.py` and
   copies them into `data/runs/<date>/`.
6. Log rotation: keeps the last 20 `*.log` files.

**`run.py`'s 13 steps** (`run.py:11-23`, executed in `main()`):
1. Collect reels by roster (paid — `collect_snapshot.run`)
2. Score against each author's own norm (free)
3. Deep-dive the top of the window: frames + speech (free, but must happen right after
   collection while CDN links are alive)
4. Topic tagging (free)
5. Refresh follower counts (free)
6. Liveness check / roster pruning (free)
7. Pull last week's decisions from Notion (free)
8. Build cards (free)
9. Delta vs. last snapshot (free)
10. Push cards to Notion (free)
11. Push the "numbers behind the picks" stats block to Notion (free)
12. Push full `reels`/`accounts` databases to Notion (free)
13. Rebuild the three static pages (free)

Steps 7, 10, 11, 12 are individually wrapped in `try/except SystemExit` in `run.py`
(lines 92-96, 108-113, 115-120, 122-127) — **a Notion failure at any of these steps is
caught and logged, never aborts the run.** This is why the pipeline reliably reaches step
13 even with Notion fully broken (confirmed in the logs below).

### Run 2026-09-10 07:00–08:08 (65 min) — quotes from `data/runs/2026-09-10_0700.log`

- Balance/cost: *"аккаунтов в наборе 130, по 1 странице = 130 ед. = $2.60"* /
  *"на счету 204 ед. = $4.08"*.
- Step 1: *"снимок 2026-09-10: аккаунтов 130, роликов 1535"* / *"потрачено 130 ед. =
  $2.60"* — exactly 1 unit/account, matches `PAGES=1`.
- Step 2: *"снимок 2026-09-10: оценено 1530, прошло порог 1379"*.
- Step 3 (deep-dive): ffmpeg spat repeated `[h264 @ ...] Invalid NAL unit size` /
  `missing picture in access unit` / `Decoding error: Invalid data found when processing
  input` for at least 4 distinct source files, but the step still finished cleanly:
  *"разобрано 85 из 85, без ссылки 0, пустых 0"* — corrupt/partial downloads got frames
  extracted from the decodable portion rather than failing the reel outright (ffmpeg
  degrades gracefully on partial mp4s here; no reel was recorded as failed).
- Step 4: *"размечено 619, нераспознанных 158 (26%)"*.
- Step 5 (followers): *"источник молчит пять раз подряд — остановились на 0"* /
  *"обновлено профилей: 0 из 130"* — the free public-profile source (`freeprofile.py`,
  same anonymous endpoint used for candidate profiles) was rate-limited/blocked for the
  entire run; follower growth tracking got **zero** updates this run.
- Step 6: *"живых 112 / не набрали 3 ролика за 30 дней 17 (первый промах) / пропущено 1"* —
  130 active accounts, 120 short of the 250 target.
- Step 7 (Notion pull): **failed** — *"Notion недоступен, идём дальше: Notion ответил
  404: {"object":"error","status":404,"code":"object_not_found","message":"Could not find
  database with ID: d5b6ab42-6b8a-4240-9f01-f9e3b34be9e6. Make sure the relevant pages and
  databases are shared with your integration \"M2 Lab Radar\"."`* — this is the Cards DB.
- Step 8: *"кандидатов 138, повторяющихся тем 12, записано карточек 9"* — 9 cards built
  covering M2 Radar/Builds/Teardown formats, e.g. *"9. M2 Teardown kayvon.ai 3 дн. 42.4×
  this author's own norm (1 123 071 against 26 518)"*.
- Step 10 (cards → Notion): **failed**, same 404 on the Cards DB id.
- Step 11 (stats block): *"раздел с цифрами обновлён"* — this one **succeeded**; it writes
  to `NOTION_PAGE` (a page, not a database), which apparently is still shared/valid.
- Step 12 (full reels/accounts DBs): **failed** — 404 on a *different* database id
  (`679fa6d6-f7a4-4ab0-bb48-dd6797a1c31a`, the Reels DB).
- Run total: *"прогон занял 65 мин, потрачено сегодня $2.60"*.
- Post-run `claude -p prompts/angles.md` **did run successfully** (its full prose output —
  card-by-card angle/hook writeups for cards #1, #3, #6, #7, with #2/#4/#5/#8/#9 explicitly
  struck — is appended to the log after "── прогон завершился с кодом 0 ──"), followed by
  another failed `notion.py push` (*"выгрузка углов в Notion не прошла"*, same 404).

### Run 2026-09-07 07:00–08:18 (73 min) — quotes from `data/runs/2026-09-07_0700.log`

This run is the "last one before the Notion databases were trashed" reference point:
- Step 1: *"снимок 2026-09-07: аккаунтов 106, роликов 1260"*, *"потрачено 106 ед. = $2.12"*.
- Step 3: only an HF Hub auth warning (*"You are sending unauthenticated requests to the HF
  Hub..."* — informational, not an error; faster-whisper's tokenizer download check), then
  *"разобрано 97 из 97, без ссылки 0, пустых 0"* — clean.
- Step 4: *"размечено 550, нераспознанных 126 (23%)"*.
- Step 5: same follower-source blackout, *"обновлено профилей: 0 из 106"*.
- Step 6: *"живых 91 / не набрали 3 ролика 15"*.
- Step 7 (Notion pull): **succeeded** — *"обновлено статусов: 5, новых комментариев: 0"*,
  listing `карточка 1: Proposed` etc. **This is the last run where the Cards DB was still
  reachable.**
- Step 8: 9 cards built.
- Step 10 (cards → Notion): **succeeded** — *"1. M2 Radar leadgenman выгружена"* ... 9/9
  *"выгружено: 9"*.
- Step 11 (stats table update inside the page body): **failed** with a *different* error
  than the 09-10 run — *"Notion ответил 400: ... Updating a page via the blocks endpoint
  unsupported. Call patch /v1/pages/:page_id instead"* — a **code bug** in `stats.push()`
  (calling the wrong endpoint), not a permissions/trash issue. Worth fixing independent of
  the trashed-database problem.
- Step 12 (full DBs): **failed**, same 404 pattern already on 09-07 for the Reels DB id
  (`679fa6d6-...`) — so the Reels DB was already unreachable on the 7th, one step ahead of
  Cards (which broke by the 10th).
- Post-run `claude -p` produced full angle/hook writeups for 5 of the week's cards.
- Final `notion.py push` for the angles: **failed**, 404 on the Cards DB — meaning between
  the *body* of the 09-07 run (where the initial `notion.py push` in step 10 worked) and the
  *post-agent* push minutes later, the Cards DB became unreachable too. This is consistent
  with the memory note that all three Notion databases were moved to trash around Sep 7 and
  the timing lines up almost exactly with this run.

**Net conclusion for §3**: the pipeline itself is robust to Notion being fully broken —
every Notion call site is wrapped and logged, never crashes the run — but as of both
captured runs, **all Notion writes/reads except the `NOTION_PAGE` stats block are failing
with 404 (Cards DB, Reels DB)**, and one additional real bug exists in `stats.py`'s
page-body update call (400, wrong endpoint) that predates and is independent of the
trashed-database issue.

Deep-dives, transcripts and reel collection are unaffected by any of this — they are 100%
local/HikerAPI and don't depend on Notion at all.

---

## 4. Local transcription (`deep.py`) and `prune.py`

Full file read: `/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/deep.py` (327 lines incl. docstring)
and `prune.py` (48 lines).

- **Model**: faster-whisper `small`, `device='cpu'`, `compute_type='int8'`
  (`deep.py:118`), loaded once per process (`_whisper` module-level singleton,
  `deep.py:109-111`) and reused across reels in the same run. English is **forced**
  (`language='en'`, `deep.py:119`) — the docstring at line 113 explains: auto-detect is
  unreliable on non-native English accents, which is the norm for this niche's creators.
  `vad_filter=True` — voice-activity gating before transcription, to skip silent stretches.
- **Media download**: the mp4 URL comes from `_urls()` (`deep.py:66-88`), which — crucially
  — does **not** call HikerAPI again. It scans the already-cached `clips*.json` responses
  under `cache/` (optionally scoped to one snapshot's dated subfolder), oldest file first
  so a newer cached response for the same reel code overwrites the URL from an older one
  (comment at `deep.py:69-71`: signed CDN URLs live only hours, so an old file's URL would
  already 403). It then does `curl -sL --max-time 150 -o <mp4> <url>` (`deep.py:140`).
  **CDN link lifetime is "a few hours"** — this is why `run.py` and `cron.sh` never
  separate collection from deep-dive into different invocations, and why `deep.py`'s
  standalone `__main__` path (`deep.py:226-233`) checks link liveness with a `curl -sI`
  HEAD request before attempting a full batch download, refusing to proceed ("ссылки на
  видео протухли: CDN отдаёт 403") if the check fails — and quotes the exact cost to
  re-collect (`${n_acc * 0.02:.2f}`) rather than silently re-spending. **This link-lifetime
  fragility is a structural constraint on any future refactor** — collection and deep-dive
  cannot be decoupled into independently-schedulable/retryable stages without either (a)
  keeping the download step tightly coupled to collection, or (b) downloading media
  immediately into permanent storage at collection time (which the current design
  deliberately avoids to save disk/bandwidth, see below).
- **Frame sampling policy**: `timecodes(dur)` (`deep.py:97-100`) — **not evenly spaced**.
  Four fixed early timestamps (`0.4, 1.2, 2.4, 4.0`s) to densely cover the hook, then five
  more evenly spaced across the rest of the duration (`dur*k/6` for k=1..5), deduplicated
  and dropped if within 0.3s of the end. For a 60s reel this yields exactly 9 frames
  (asserted in `test_deep.py:56`); shorter reels yield fewer.
- **Cut detection**: ffmpeg's built-in scene-change filter, threshold 0.35 —
  `[ff, '-i', mp4, '-filter:v', "select='gt(scene,0.35)',showinfo", '-f', 'null', '-']`
  (`deep.py:104-105`), counted via regex over stderr's `pts_time:` occurrences
  (`deep.py:106`). Normalized to cuts/second (`cuts_ps`) for cross-duration comparison,
  stored in `deepdives.cuts` / `deepdives.cuts_ps`.
- **Contact sheet**: 3×3 tile of the extracted frames via ffmpeg's `tile=3x3` filter
  (`deep.py:151-155`), written to `data/frames/<code>_sheet.jpg`, referenced by
  `deepdives.sheet` and later uploaded straight into the Notion card body (`notion.py`
  `upload()`/`blocks_for()`, §5) — the sheet is the human-facing artifact, not the raw
  frames.
- **What's stored where**: `deepdives` (one row per reel: cuts, cuts/s, mp4 size, sheet
  path, `suitable` yes/no/null, `unfit_why`, `done_at`) · `frames` (one row per
  frame: `code, idx, t_sec, path`) · `transcripts` (one row per reel: `lang, words, text,
  full JSON segments with per-segment start/end/text`) — **segments do carry timestamps**
  (`{'s':..., 'e':..., 't':...}`, `deep.py:120`), stored as a JSON blob in
  `transcripts.segments`, so sub-reel-level "what was said when" is preserved, not just a
  flat transcript string.
- **Video itself is never persisted** — `mp4.unlink(missing_ok=True)` runs at the end of
  every reel's processing unless `keep_video=True` is explicitly passed (`deep.py:172-173`,
  never passed from any call site in the codebase) — "SPEC §4.4: видео не храним." Frames
  and the contact sheet are the only visual artifacts kept.
- **Idempotency**: `pick()` filters out any code already in `deepdives`
  (`deep.py:35-36`); `run()` skips re-downloading if the mp4 already exists on disk
  (`deep.py:136`), skips re-extracting a frame if its file already exists
  (`deep.py:147-148`), skips re-transcribing if a `transcripts` row already exists for that
  code (`deep.py:157`). All DB writes use `INSERT OR REPLACE`.
- **Failure handling**: empty/undersized downloads (`< 10_000` bytes) are unlinked and
  counted as `empty`, not retried (`deep.py:141-142`); reels with no resolvable URL in
  cache are counted as `no_url`, not retried; a transcription exception is caught per-reel
  and logged (*"расшифровка не вышла: {e}"*) without aborting the batch (`deep.py:121-123`)
  — confirmed in practice by the 2026-09-10 log, where multiple `h264`/`NAL unit`
  decode errors from corrupted downloads did not stop the run (see §3). There is **no
  retry** of a failed download or a failed transcription within the same run — a failure
  is permanent for that run and would only be revisited if the reel resurfaces in a later
  `pick()` window (bounded by `WINDOW=14` days) and hasn't yet acquired a `deepdives` row —
  but it already has one (written even on partial success, just possibly with
  `suitable=NULL`), so **a reel whose download/transcription failed is not automatically
  retried on the next run** — it needs a human `deep.py fit`/`unfit` decision or a bug fix,
  there's no automatic "retry N times across runs" path.

### `prune.py` — the frame-deletion risk

- Deletes **only frame JPGs and the contact sheet** — `shutil.rmtree(D/'frames'/code)`
  and unlinking `sheet` (`prune.py:39-43`) — for `deepdives` rows where `done_at < now -
  8 weeks` **and** the code never became a card (`code NOT IN (SELECT code FROM cards)`,
  `prune.py:19-20`). It does **not** delete the `deepdives` row, the `frames` DB rows'
  metadata, or the `transcripts` row/text/segments — those stay forever ("строки разбора,
  склейки и расшифровки остались — они весят копейки и нужны истории", printed by the
  script itself). It is also **not wired into `cron.sh` or `run.py`** — it's a manual,
  `--yes`-gated command that nobody has apparently run yet (the DB has 3 snapshots total,
  none older than ~2 weeks, so nothing is eligible for pruning today).
- **Actual risk, correctly scoped**: this only deletes *pixels*, and only for reels that
  were deep-dived but never selected as a card. The structured signal (scores, topics,
  transcript text+segments, cut counts) is retained indefinitely. The real loss is: if a
  future analysis wants to re-look at *what was on screen* for an un-selected reel older
  than 8 weeks, it can't — the frames and contact sheet are gone, and (per §2/§3) the raw
  HikerAPI response that could regenerate them is itself sitting in an undated, unmanaged
  `cache/` directory with no expiry policy of its own and no guaranteed retention either.
  So the real exposure isn't "prune.py is reckless" (it's conservative — it protects
  cards) — it's that **there is no tier between "keep frames forever" and "delete
  frames+lose ability to ever regenerate them,"** because the raw payload (`cache/`) that
  would let you regenerate frames from a still-valid transcript timestamp is itself
  unmanaged and the source video is *never* retained by design (§4 above). Once a signed
  CDN URL expires (hours) and the cache file that held it ages out or is manually cleared,
  a pruned reel's frames are permanently unrecoverable.

---

## 5. Notion (`notion.py`, `notion_db.py`, `test_notion.py`)

**What's pushed where** (env var names only, no values read):
- `notion.push()` (`notion.py:140-192`) — writes/updates one Notion page per selected card
  into the database at `NOTION_CARDS_DB`. Card body includes the contact sheet image
  (uploaded via `/file_uploads`, `notion.py:70-84`), transcript broken into hook/body/tail
  blocks (via `blocks.py`, not read in this audit), the written angle/hook, shot
  instructions, and a caption frame. **Only untouched cards get their body rewritten** —
  if a human has moved `Status` away from `Proposed`/null, the body is left alone
  (`notion.py:178-185`) so manual edits survive a re-push.
- `notion.pull()` (`notion.py:196-233`) — reads `Status`/`Lead` back from `NOTION_CARDS_DB`
  into the local `cards` table, and copies any page comments into `tool_log` (dedup'd by
  exact comment text, `notion.py:222`) so the next run's card selection can exclude
  already-rejected reels (`cards._pool()`, referenced but not the audit's target file).
- `stats.push()` (referenced via `run.py` step 11, file not fully read but header confirms
  it writes a "Numbers behind the picks" block, marker `MARKER = 'Numbers behind the picks'`
  at `stats.py:11`) — targets `NOTION_PAGE` (a page, not a database).
- `notion_db.push_reels()` / `push_accounts()` (`notion_db.py:79-108`, `155-206`) — mirror
  the **entire** 14-day reel window and the **entire** active account roster into
  `NOTION_REELS_DB` / `NOTION_ACCOUNTS_DB` respectively, with every derived metric
  (score, shares/1k, saves/1k, topics, hook/body/tail word counts, comment-bait/DM-promise/
  money-claim flags, etc.) — this is explicitly the "show your work" layer per the file's
  own docstring ("любое решение можно было разобрать, а не принять на веру").
- Env vars referenced (names only, confirmed present in `.env`/`.env.example`):
  `NOTION_TOKEN`, `NOTION_CARDS_DB`, `NOTION_PAGE`, `NOTION_REELS_DB`, `NOTION_ACCOUNTS_DB`.

**Current failure state** — confirmed from the two logs in §3, not from any live Notion
API call (none was made in this audit): as of 2026-09-07 the Reels DB (`679fa6d6-...`) was
already unreachable (404, "Could not find database... share it with your integration"),
and by 2026-09-10 the Cards DB (`d5b6ab42-...`) had joined it. This matches the memory note
that the three databases referenced by `.env` were moved to trash on Sep 7 and Max moved to
his own database — the 404 message text itself ("Make sure the relevant pages and databases
are shared with your integration") is the generic Notion error for "the integration lost
access," consistent with a trashed/unshared page rather than a code bug for those two.
The **`NOTION_PAGE` stats block still works** (09-10 log: "раздел с цифрами обновлён") —
it's a page, and pages don't get trashed the same way a linked database does, or it wasn't
part of what got moved.

**One independent, real bug**: `stats.py`'s Notion write (the page-body update, used for
whatever isn't the top-level page property write) hit `400 validation_error: "Updating a
page via the blocks endpoint unsupported. Call patch /v1/pages/:page_id instead"` on
09-07 — this is a wrong-endpoint bug in the code, not a permissions/trash issue, and it
happened on a run where the Cards DB push otherwise succeeded. Worth a standalone fix
regardless of the Notion database relocation.

**`test_notion.py`** (`/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/test_notion.py`, read in
full) — a genuine offline test: it monkeypatches `notion.call` with a `fake_call()` closure
that inspects the HTTP method+path and returns canned responses (no network). It verifies:
all of a week's cards get pushed as new pages with `Status: Proposed`; a card body
containing a contact-sheet image block; that a human-touched card (`Status: Taking`) has
its body left alone (not archived/rewritten) while its properties still update; that a
pulled `Status`/`Lead` change is written back to the local `cards` table; that a page
comment lands in `tool_log` exactly once (not duplicated on a second `pull()`); and that a
rejected card disappears from the future candidate pool. **This is the only file in the
whole Hiker/Notion stack that has real mocked-transport test coverage** — `lib/hiker.py`'s
actual `call()` (the curl subprocess, header parsing, retry/backoff logic) has **no test
at all**; `test_collect.py` mocks the entire `hiker` module at the `sys.modules` level
(replacing `hiker.clips`/`hiker.row` outright, `test_collect.py:20-34`), so it verifies
`collect_snapshot.py`'s DB-writing logic but never exercises a single line of
`lib/hiker.py` itself.

---

## 6. Max's `Latest` branch — Hiker design comparison

Read directly from `origin/Latest` via `git show` (not merged, not deployed): `hiker_server.py`,
`m2_signal/hiker_adapter.py`, `docs/hiker-server-activation.md`, `config/hiker-*.template.json`,
`integrations/radar/server_entry.py`, `integrations/radar/README.md`.

**Does it call Hiker at all?** No — not automatically, and by explicit design. The
activation doc's own first line: *"This is an operator procedure for a separately approved
future server run. No step here was executed against HikerAPI during this integration."*
And its last line: *"Server activation is controlled by Michael; shipping code does not
activate it."* `integrations/radar/README.md` reinforces: *"Default behavior remains
replay only... No Git pull, install, schedule change, semantic model, Notion write or
publishing action is hidden in the timer."* Concretely: `hiker_server.py --config
plan.json` with no `--execute` flag only prints a plan (`config_sha256`, account count,
budget) and never reads a key or calls the network (`hiker_server.py:19-25`,
`live_schema_state: LIVE_SCHEMA_UNVERIFIED` in the printed plan). Even `--execute` refuses
to run without `--private-dir` and `--approval` (`hiker_server.py:28`), and the approval
object itself must carry a matching `config_sha256`, an explicit `approved=true`,
timezone-aware non-expired `expires_at`, and (for anything beyond a literal one-request
pilot) a separately reviewed and hash-bound "live schema receipt" proving what the actual
API response shape looks like before any wider collection is permitted
(`m2_signal/hiker_adapter.py:66-98`, `_verify_live_schema_receipt`).

**Gating mechanism, concretely**:
- `validate_collection_config()` (`m2_signal/hiker_adapter.py:29-50`) requires an *exact*
  field set (no more, no less) including a `price_receipt_sha256` — a hash of a dated,
  verified tariff document — so unlike the current repo's three-copies-of-`0.02` problem,
  the price used for budgeting is cryptographically pinned to a specific receipt, not a
  literal assumed in code.
- `LiveTransport` (`m2_signal/hiker_adapter.py:114-131`) is a single-purpose, no-redirect,
  no-retry HTTP call with credential injected only from env (`HIKER_KEY`/`HIKERAPI_KEY`,
  same var names as the current repo) and a hard 25 MB response cap; any transport
  exception is normalized to a generic `HIKER_TRANSPORT_OUTCOME_UNKNOWN` — deliberately
  never echoing raw error text that might contain the key.
- Every dispatch is preceded by writing an immutable `dispatch/<key>.json` reservation
  *before* the network call (`m2_signal/hiker_adapter.py:collect()`, dispatch-then-call
  pattern), and the raw page + a checkpoint are written immediately after — so a crash
  mid-run leaves a reconcilable trail (`UNCERTAIN_PREVIOUS_DISPATCH_REQUIRES_RECONCILIATION`)
  instead of silently re-billing on restart. This is a materially stronger
  idempotency/crash-safety guarantee than the current repo's cache-file-by-URL-hash
  approach, which has no concept of "a request was dispatched but the outcome is unknown."
  A budget ceiling (`maximum_cost_usd` / `request_cost_ceiling_usd`) is checked *before*
  each new dispatch, not just tallied after the fact.
- Response validation is strict and typed (`_validate_page`, `_native_row`,
  `m2_signal/hiker_adapter.py:161-198`): malformed items are quarantined with a reason
  code rather than silently dropped or crashing the batch, and pagination consistency
  (`more_available` implying a real cursor and nonempty items) is asserted, not assumed.
- Path safety (`integrations/radar/server_entry.py:safe_path`/`validate_paths`) rejects
  symlinks, hardlinks, and inputs/outputs escaping declared private/source roots — a class
  of server-hardening the current repo doesn't attempt (the current repo's file paths are
  all simple `pathlib.Path(__file__).parent / ...` with no traversal checks, which is fine
  for a single trusted operator but not designed against any adversarial input).

**Reusable pieces, concretely**, if/when this repo's architecture gets refactored:
1. **`price_receipt_sha256`-style provenance for the cost model** — replaces the current
   three-copies-of-`PRICE=0.02` with a single dated, hashed receipt; directly fixes the gap
   noted in §2.
2. **Dispatch-before-call + checkpoint-after-call idempotency** — directly fixes the "raw
   payload has no provenance / can't tell what was fetched when" gap in §2 and gives a real
   answer to "was this billed or not" after a crash, which the current `_units` in-memory
   counter cannot answer once a process dies mid-run.
3. **The approval/expiry/scope model** — overkill for a one-operator hobby-scale pipeline
   today, but the *shape* (a config hash bound to an explicit, expiring, scoped approval
   object) is exactly what a "CONFIGURED / NOT_CONFIGURED / FAILED" config validator
   (per the gap list below) should borrow from, just simplified to fit this project's
   actual risk level (one trusted operator, not a partner-hosted server).
4. **Quarantine-with-reason instead of silent drop** for malformed API rows — the current
   repo's `safe_code()` check in `db.py` silently discards bad codes (`bad.append(r.get
   ('code'))`, just a count in the printed summary); a `reason` string per quarantined item
   (as Max's `_native_row` returns) would make debugging a future schema change far easier.
5. **`safe_path`-style traversal/symlink checks** are probably not worth porting wholesale
   (this server has one operator and one deploy target), but the *specific* check "run
   output must live under a declared private root, inputs must live under declared source
   roots" is a cheap, useful discipline even for a single-operator box, and would have
   caught, e.g., the untracked `runs/2026-09-07/*.jpg` files sitting outside any declared
   data directory (§1).

**What Max's design deliberately does *not* do**, and shouldn't be ported: it has no
concept of the *weekly cron cadence*, the topic-tagging/scoring/card-selection/Notion
feedback loop, or the deep-dive/transcription pipeline at all — it is purely a
collection-and-replay skeleton for a *different*, more heavily gated future activation
model (`m2_signal`/`m2_orchestrator`, a separate codebase from this repo's `run.py`
pipeline). Porting its *patterns* (receipts, dispatch-then-call, quarantine) is reasonable;
porting its *code* wholesale is not — it solves a partner-hosted-server trust problem this
project doesn't currently have.

---

## Gap list — what the committed architecture must contain for the server to run Hiker from git alone

1. **A config/secret validator with explicit states** (`CONFIGURED` / `NOT_CONFIGURED` /
   `FAILED`) run once at the top of `run.py`/`cron.sh`, checking: `HIKER_KEY` present and
   non-empty, `NOTION_TOKEN`/`NOTION_CARDS_DB`/`NOTION_PAGE`/`NOTION_REELS_DB`/
   `NOTION_ACCOUNTS_DB` present, and (new) a **live reachability probe** for each Notion
   database ID before the run trusts it — this alone would have turned nine minutes of
   silent 404s per run into one clear "Notion Cards DB: FAILED — not shared with
   integration" line at the top of the log, instead of discovering it by reading three
   separate stack traces buried in a 180-line log.
2. **Raw payload provenance.** Every cached HikerAPI response should carry (as a sidecar
   or wrapper, not just an opaque hash-named file) at minimum: fetch timestamp, full
   request path+params, HTTP status, and the nominal unit cost from `x-hiker-info`. Today
   none of that survives outside the log line printed at fetch time.
3. **A single source of truth for the tariff** (`PRICE`), ideally receipt-hashed per
   Max's `price_receipt_sha256` pattern, replacing the three hardcoded `0.02` literals in
   `lib/hiker.py`, `collect_snapshot.py`, `roster.py`.
4. **A normalization module with a documented raw→row mapping**, so a `reels` row can be
   traced back to the exact cache file / API response it came from (currently only
   possible by re-scanning `cache/**/*clips*.json` by content, as `deep.py:_urls()` does).
5. **State transitions for the weekly run** need to be visible at a glance: today you have
   to read the whole log to learn "Notion pull worked, cards push worked, stats push failed
   with a 400, full-DB push failed with a 404" — a structured summary block at the end of
   `run.py` (per-step state: OK/SKIPPED/FAILED + reason) would turn this audit's §3 into a
   two-line health check.
6. **Tests/mocks for `lib/hiker.py` itself.** `test_collect.py` mocks around it entirely;
   there is no test exercising the curl subprocess call, header parsing, retry/backoff, or
   429/402/5xx handling in `lib/hiker.py:call()`. A `subprocess.run`-mocking test suite
   (or refactor `hiker.py` to accept an injectable transport, à la Max's `LiveTransport`
   pattern) would catch a regression in exactly the code that currently has zero coverage
   and handles real money.
7. **`.env.example` is already complete and accurate** (matches the server's actual
   variable names 1:1) — no gap there, just worth confirming it stays that way as new env
   vars get added.
8. **Docs**: nothing in the repo currently documents the CDN-link-lifetime constraint,
   the collection→deep-dive coupling it forces, or the prune.py retention model as a single
   coherent statement — it's scattered across code comments in `deep.py`, `prune.py` and
   `collect_snapshot.py`. A short `docs/data-lifecycle.md` collecting "what's kept, for how
   long, and why collection+deepdive can't be split" would prevent a future refactor from
   accidentally decoupling steps that must stay coupled.

## Risks

- **`prune.py` and frame loss** — correctly scoped today (only non-card frames, only after
  8 weeks, transcripts/DB rows untouched — see §4), but structurally there is no way to
  regenerate a pruned reel's frames later, because raw video is never kept and the raw
  HikerAPI cache has no retention guarantee of its own. Not urgent (nothing is 8 weeks old
  yet) but will start mattering within the next ~6 weeks of continuous operation.
- **CDN link lifetime (hours)** — hard-couples collection and deep-dive into one
  invocation; any future refactor that tries to make these independently retryable steps
  needs to solve this first (either by downloading immediately at collection time, which
  costs disk, or by keeping the coupling and just making the combined step atomic/resumable).
- **Notion trash / broken links** — confirmed via logs, not live-checked in this audit
  (per the "do not call the Notion API" boundary on this task). Two of three databases are
  currently 404ing; only the `NOTION_PAGE` stats block still writes successfully. This is
  presumably already known to Misha per the memory note about Max's Sep 7 move, but the
  logs give exact error text and exact dates for whoever fixes the sharing.
- **`git pull --rebase` inside `cron.sh`, unguarded** — a rebase conflict or failure is
  caught and logged but does **not** stop the run; the cron proceeds on whatever code state
  results, silently. A conflicted rebase could leave the working tree in a half-merged state
  that `run.py` then executes against. Recommend at minimum `git pull --ff-only` (fails
  loudly and cleanly instead of attempting a merge) or an explicit abort+alert on conflict.
- **`claude -p` dependency inside the cron chain** — the angle-writing step is a full
  agent invocation with a 60-minute timeout and `Bash,Read,Edit` tool access, running
  unattended at 07:00 twice a week. It's gated on `run.py --yes` exiting 0, and its own
  failure is caught (`|| echo "агент не отработал..."`), so it degrades gracefully — but
  it is the single most complex, least deterministic step in the entire chain, running
  with file-editing tool access on a production server with no human present.

## Recommended minimal changes to keep the cron working during the refactor

1. Fix the `stats.py` 400 (wrong Notion endpoint) — small, independent, unrelated to the
   trashed databases, and currently silently eating one of the four Notion write paths
   every run.
2. Either re-share the Cards/Reels/Accounts databases with the "M2 Lab Radar" integration,
   or point `.env`'s three DB-id vars at Max's replacement databases (per memory) — this
   is a config change, not a code change, and restores 3 of 4 Notion write paths.
3. Add a single top-of-run Notion reachability check (a cheap `GET /v1/databases/<id>`
   per configured ID) that prints `Notion Cards DB: OK|FAILED` etc. *before* the expensive
   paid collection step runs — so a broken Notion link is visible in the first 5 seconds of
   the log instead of discovered by reading to the bottom.
4. Change `git pull -q --rebase` to `git pull -q --ff-only` in `cron.sh` — same "don't block
   the run" behavior on failure, but removes the possibility of an unattended rebase leaving
   a half-merged tree.
5. Deduplicate `PRICE = 0.02` into one importable constant (even without Max's full
   receipt-hash mechanism, a single `from lib.hiker import PRICE` everywhere removes the
   three-copies drift risk immediately, cheaply, without waiting for a bigger refactor).

None of the above require touching the HikerAPI call surface, the deep-dive pipeline, or
the cron schedule itself — they're safe to land independently and in any order.
