# 7. Data Acquisition

## How Hiker works in git

`lib/hiker.py` (293 lines) is the single HTTP surface for HikerAPI in the repository; every call
shells out to `curl` rather than `httpx` because, per the module's own comment, Python's SSL is
broken on the collection machine. `roster.py`, `collect_snapshot.py` and ad-hoc CLI calls all go
through it. The automated weekly cron run pays for exactly two endpoints: `/sys/balance`
(informational) and `/gql/user/clips` (one page per account, 12 reels/page — the only endpoint
`collect_snapshot.run()` calls). Account discovery (`/v2/fbsearch/reels`, `/v2/user/suggested/
profiles`, via `roster.py topup`) is a separate, manually invoked, paid path outside `cron.sh`.

## Key externalized, never in git

`_key()` resolves `HIKER_KEY` in order: process environment, then a literal `HIKER_KEY=` line in
the repo's own gitignored `.env`, then (Mac-only) `~/Desktop/.mcp.json`. If none resolve, the
process hard-exits rather than proceeding silently. `git grep` across every `*.py` file confirms
no literal key is hardcoded anywhere — only references to the env var name and header name. Server
and local `.env` file permissions are `600` (owner-only), and every cron invocation now starts with
`python -m engine.hiker_config`, which prints `HIKER_KEY: CONFIGURED/NOT_CONFIGURED/FAILED` —
never the value, only presence and length — plus one reachability line per configured Notion
database.

## Provenance chain

Before this branch, a `reels` row carried no pointer back to the API response that produced it —
the only recovery path was `deep.py`'s linear scan over every `cache/**/*clips*.json` file by
content, sorted by file mtime, which remains how URL resolution works today (provenance is
additive, not a replacement). The chain now runs:

```
lib.hiker.call()        -> writes <cache_dir>/<endpoint>_<hash>.json (response body)
                         -> writes <...>.json.meta.json (sidecar: timestamp, endpoint, params, status, units, sha256)
collect_snapshot.run()  -> reads last_fetch_meta() right after each account's clips() call
                         -> INSERT INTO fetch_log(fetch_id, provider, endpoint, params_json,
                                fetched_at, http_status, units, price, cache_path, sha256, ...)
                         -> every upserted reels row gets reels.fetch_id = that fetch_log.fetch_id
```

To audit any `reels` row: `SELECT fetch_id FROM reels WHERE code=?`, then `SELECT * FROM fetch_log
WHERE fetch_id=?` returns the exact endpoint, params (key never included), HTTP status, units
billed, price, and — via `cache_path` — the response file and its sha256 for byte-level
verification. This is guarded, not a hard dependency: on a database where `engine/schema.py`'s
migration hasn't run, `collect_snapshot.py` checks for the table/column first and silently skips
the provenance write, so the pre-existing pipeline keeps working unchanged. `fetch_log` in this
database is created and currently **empty** — the hiker owner's provenance code exists and is
unit-tested (13 cases, `tests/test_hiker_client.py`) but no collection run has been executed against
this schema version yet, matching the `runs`/`jobs` gap noted in chapter 6.

## Cost model, including the $0.02 receipt

`PRICE = 0.02` (Start tariff) is a hardcoded literal duplicated in three files
(`lib/hiker.py`, `collect_snapshot.py`, `roster.py`) — a real, flagged gap with no single source of
truth. Real spend, however, is tracked from the response header rather than assumed: `x-hiker-info`
supplies the nominal cost per call, and the running counter only increments on billable outcomes
(200/400/403/404), explicitly excluding 5xx.

Actual spend recorded to date, verified against `reports/data/spend.json` and the live `spend`
table (10 rows):

| Date | Item | Units | USD |
|---|---|---:|---:|
| 2026-09-01 | разведка ниши, 30 запросов | 30 | 0.60 |
| 2026-09-01 | профили 254 авторов | 253 | 5.06 |
| 2026-09-01 | ролики 100 аккаунтов, 2 страницы | 196 | 3.92 |
| 2026-09-01 | соседи и ролики добранных | 54 | 1.08 |
| 2026-09-01 | проверки | 30 | 0.60 |
| 2026-09-03 | добор: поиск и соседи (2 runs) | 60 | 1.20 |
| 2026-09-07 | сбор роликов (снимок 2026-09-07, 106 аккаунтов) | 106 | 2.12 |
| 2026-09-09 | добор профилей по списку Миши | 30 | 0.60 |
| 2026-09-10 | сбор роликов (снимок 2026-09-10, 130 аккаунтов) | 130 | 2.60 |

**Total: 889 units = $17.78** at a flat $0.02/unit, all recorded through this same header-parsing
mechanism, not estimated.

## Cache and what the weekly run pays for

`_cache_dir` defaults to `./hiker-cache`, but `collect_snapshot.run()` explicitly repoints it to
`cache/<snapshot-date>/` — the code comment records why: without date-partitioning, a same-week
re-run silently replayed a prior week's feed for 100 of 109 accounts. The weekly cron run's only
paid step is `collect_snapshot.run()` (~1 unit/account/week, ~$2–3 at the current 130-account
roster); every other step in `run.py`'s 13 steps is free. `roster.py topup` (search + suggested
accounts) is a separate, manually invoked paid path, not part of the automated cadence.

## Loore (optional, disabled by default)

`loore` is registered as `OPTIONAL_PROVIDER`, kind `media`/`transcription`, configured via
`LOORE_KEY` + `LOORE_ENABLED=1`. It stays `DISABLED` even when a key is present unless that second
flag is explicitly set — a key alone can never silently switch on a paid path. No call site in
this repository invokes it today; it exists in the provider registry as a documented future
fallback for media or transcription, not as an active dependency.
