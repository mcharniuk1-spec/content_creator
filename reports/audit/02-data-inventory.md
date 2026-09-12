# 02 — Data inventory

Audit date: 2026-09-11. Repo `m2-research/radar`, branch `content-engine`.
Source of truth: `data/server-mirror/radar.db`.
Machine-readable twin of this file: `reports/audit/02-data-inventory.json`.

**The mirror is byte-identical to production.** `md5 data/server-mirror/radar.db` =
`5b652f05823ea57f686ec66f88eaaedd` = `ssh m2vps md5sum /opt/radar/data/radar.db`. Every number
below is computed from that file or from a read-only check on the server; nothing is estimated.

---

## 1. Headline numbers

| | |
|---|---|
| Snapshots | 3 (2026-09-01, 2026-09-07, 2026-09-10), all `done=1` |
| Accounts | 1 357 rows; 130 in the working set |
| Reel rows | 5 147 |
| **Unique reel codes** | **3 211** |
| Reels with transcript | 273 (8.5 %) |
| Reels with frames | 295 (9.2 %) |
| **Fully analysis-ready (transcript AND frames)** | **273** — of which 266 usable |
| Frame files | 2 653 rows, 2 645 files present on the server, 8 missing |
| Deep dives | 282 |
| Topic-tagged codes | 1 454 (45.3 %) |
| Scored codes | 3 205 (99.8 %), 2 961 eligible |
| Cards | 23 |
| Total HikerAPI spend | 889 units = **$17.78** |
| Posting date range | 2020-03-26 → 2026-09-10 (UTC) |

Two facts dominate everything else:

1. **The analysis corpus is 273 reels, not 3 211.** Frames and transcripts are produced together
   by `deep.py`, so the two sets nest almost perfectly: every transcript code has frames, and
   only 22 frame codes lack a transcript. There is no separate transcript-only backlog to
   recover — there is only unprocessed raw metadata.
2. **1 313 of the 1 535 reels in the newest snapshot have neither.** That is the Hiker-only
   unprocessed backlog, 411 of them being codes seen for the first time on 2026-09-10.

---

## 2. Creators (`accounts`, 1 357 rows)

### By tag × status

| tag | status | n |
|---|---|---|
| core | active | **130** |
| out | out | 234 |
| (null) | candidate | 920 |
| (null) | rejected | 73 |

**Schema drift, flagged.** `db.py` documents `tag` as core/neighbor/out and `status` as
active/dropped/candidate. In the live data no row uses `neighbor` or `dropped`, and two undocumented
values are in use: `status='out'` (234 rows, paired with `tag='out'`) and `status='rejected'`
(73 rows). Anyone reading the schema comment to build a query will get wrong results.

### Accounts with at least one reel

**132** accounts — 129 of the 130 `core`, plus 3 `out` accounts that were collected before being
excluded (`10xoperator`, `petergriffin.ai`, `thevibefounder`, 24 reels each). The one core account
with zero reels is `cindie.zhu`. Every reel row resolves to an account: 0 usernames and 0 `pk_user`
values in `reels` are absent from `accounts`.

### Followers, bios, category

Follower count is present for 439 accounts and NULL for 918 (the candidate pool was never profiled).

| | |
|---|---|
| min / median / max | 16 / 64 887 / 10 219 802 |
| p25 / p75 | 13 858 / 196 951 |
| sum | 99 854 693 |

| band | n |
|---|---|
| unknown | 918 |
| 100k–500k | 134 |
| 10k–50k | 116 |
| 50k–100k | 66 |
| 1k–10k | 60 |
| 500k–1M | 25 |
| <1k | 24 |
| ≥1M | 14 |

Biography present: **365**. Category present: **182** (top values: Entrepreneur 61,
Digital creator 50, Education 12). Verified: 256. Private: 1.
`last_checked` is NULL for 918 accounts; 17 accounts carry `misses=1`.

`why_out` is filled for 307 of the 307 excluded accounts, the largest buckets being
"исключён вручную при разметке в августе" (106), "вне ниши по биографии" (98),
"мало подписчиков" (58). Provenance (`via`) is recorded for 948 accounts, all as
`сосед: <username>`.

**The `followers` time series is empty (0 rows).** "Who is growing" cannot be answered from this
database at all — see §12.

---

## 3. Reels

5 147 rows, **3 211 unique codes**. One row per code per snapshot, as designed.

| snapshot | taken | rows in `reels` | `snapshots.reels_n` declares |
|---|---|---|---|
| 1 | 2026-09-01 | 2 352 | 2 363 |
| 2 | 2026-09-07 | 1 260 | 1 260 |
| 3 | 2026-09-10 | 1 535 | 1 535 |

**Discrepancy:** snapshot 1 declares 2 363 reels but only 2 352 rows exist — 11 reels were counted
at collection and lost during the JSON→SQLite migration. Snapshots 2 and 3 tally exactly.

Codes seen in 1 snapshot: 2 005. In 2: 476. In all 3: 730. The 1 936 duplicate rows
(5 147 − 3 211) are by design, one metric reading per snapshot.

### Stats completeness (at unique-code level)

| | codes |
|---|---|
| play not null | 3 211 (100 %) |
| play > 0 | 3 210 |
| play = 0 or null in every snapshot | **1** (`B-MYSMhHXy6`) |
| likes / comments / reshares present | 3 211 (100 %) |
| **saves observed at least once** | **2 985** |
| **saves never observed** | **226** |
| duration > 0 | 3 211 (100 %) |
| caption non-empty | 3 186 |
| caption empty | 25 |
| publication ts present | 3 211 (100 %) |

Row-level: 486 of 5 147 rows have `save IS NULL` (225 / 108 / 153 by snapshot). Saves are the only
metric HikerAPI drops intermittently — roughly 9–10 % of rows in every snapshot, consistently. Play,
likes, comments, reshares, duration and ts are never null anywhere.

### Date range of publication

2020-03-26 10:25 UTC → 2026-09-10 04:39 UTC. The distribution is heavily front-loaded on the
present: 2026-08 alone holds 1 471 codes, 2026-09 holds 681, 2026-07 holds 401. Everything before
2025-12 totals 89 codes — these are evergreen or pinned posts pulled in with the recent feed.

### Duplicates and identity conflicts

- Same code across snapshots: by design, 1 936 extra rows.
- **Codes with conflicting `username`/`pk_user`: 1.** `DcFm9i5s5q8` is `umangratani` / pk 37255320
  in snapshot 1 and `umangratani.ai` / pk 51763867882 in snapshots 2 and 3. Same `ts`, same `dur`,
  continuous play counts (7 288 → 7 542 → 7 680) — the author changed handle and the account pk
  changed with it. Any per-author aggregate that groups by `pk_user` will split this author in two.
- Codes with conflicting `dur`: 2 (`DcKqq3PSVFx` 128.5/128.6, `DcQ05_ISy6h` 52.2/52.3) — rounding,
  harmless.
- Conflicting `ts`: 0. Null `pk_user`: 0. Null `username`: 0.
- `kind`: 5 146 rows `clips`, 1 row `feed`.

### Reels with no score

6 codes: `B-MYSMhHXy6` (play 0) and five reels by `dak.bugreja` (`DbbhtbHJl5L`, `DZ80z3ExaG6`,
`DZyBUfsRV5I`, `DZqO6ofJkZ-`, `DZiZlaiRerZ`). They appear in all three snapshots with healthy play
counts and are never scored — that author is missing a usable baseline in every run.

---

## 4. Transcripts

**273 rows, 273 unique codes, 8.5 % of reel codes.** Zero orphans — every transcript code exists in
`reels`.

| | |
|---|---|
| language | `en` for all 273 (forced in `deep.py`, `language='en'`; **the field carries no information**) |
| words min / median / max | 0 / 181 / 1 034 |
| words p25 / p75 | 124 / 236 |
| total words | 52 308 |
| empty text | 7 |
| under 10 words | 8 |

### Segment validity

| | |
|---|---|
| segments field missing | 0 |
| segments invalid JSON | 0 |
| **segments `[]` (empty list)** | **7** |
| transcripts with usable timed segments | **266** |
| total segments | 5 266 |
| segments per transcript min / median / max | 1 / 17 / 88 |

Every one of the 5 266 segments carries both `s` (start) and `e` (end) in seconds plus `t` (text).
There are no partially timed transcripts: a transcript either has full timecodes or is empty.

Segment duration: median 2.5 s, p25 1.7 s, p75 3.8 s, max 39.6 s (one run-on segment).

### Words per second

Computable for all 266 non-empty transcripts (duration is known for every reel):
min 0.081, p25 3.01, **median 3.48**, p75 3.78, max 5.00 words/sec. A median of 3.5 wps is normal
fast-talking creator pace and is a good sanity signal — the transcripts are not truncated or
padded. The 0.081 outlier is `DcxV37-CJOC` (5 words over 61 s), the same reel whose frames failed.

### The 7 dead transcripts

`DXaHEx7jOq6`, `DcWCLtCpaKu`, `Dcn-o-RyE4e`, `Dc3eD4KsJ00`, `Dcr51spRYwf`, `DdB_YL1yxES`,
`DcvrU4_xFjU` — words 0, text empty, segments `[]`. Whisper with `vad_filter=True` found no speech.
These are music-only or text-on-screen reels; the row exists but carries nothing. They are counted
in the 273 and must be excluded from any language analysis. Usable transcripts: **266**.

---

## 5. Frames, contact sheets, deep dives

### Frames table

**2 653 rows, 295 unique codes.** 293 codes have 9 frames, 2 codes have 8 (clips too short for the
ninth timecode). No null paths, no null timecodes, no orphans.

### File existence on the server — all 2 653 checked

Method: one ssh call running `python3` against `/opt/radar/data/radar.db` and `os.path.exists` on
every `frames.path`.

| | |
|---|---|
| rows checked | 2 653 |
| **files present** | **2 645** |
| **files missing** | **8** |
| zero-byte files | 0 |
| total frame bytes | 132.9 MB |

All 8 missing files belong to one code, **`DcxV37-CJOC`**: the DB has 9 frame rows, the directory
holds 1 jpg. The ffmpeg extraction died after the first frame; the DB rows were written anyway,
because `deep.py` inserts the frame rows unconditionally after the extraction loop without checking
that the files landed. That reel is also the 5-word transcript and is card id 28 (struck out).

### Contact sheets

295 `<code>_sheet.jpg` files on the server; all 282 `deepdives.sheet` paths resolve. **13 sheets
have no `deepdives` row**: `Db0KA0GIBik`, `DbN7QQsIUrW`, `DbQuSn4oGF3`, `Dbgkyf9oZEc`, `DcNwGdoAJnC`,
`DcOHdUPOaDm`, `DcOo9WcRK4k`, `DcUJddXCIKx`, `DcVsw1kux2Z`, `DcWLTTOvf8M`, `DcWQCQdN28T`,
`Dcd2hBaJ3wL`, `Dcgdhd_vinC`. These 13 have frames and sheets on disk but no cuts, no mp4 size and
no suitability field. The reverse (deep dive without frames) is 0.

### Disk vs. DB

296 directories under `/opt/radar/data/frames`; 295 are reel codes, one is `web` (114 jpgs, not a
reel — leftover from a page build). `DbYh2P-MQnj` has 18 jpgs on disk against 9 in the DB — a
re-run at different timecodes left the old set behind.

**The local rsync copy in `data/frames/` is complete**: 591 entries, 295 sheets, 3 063 jpgs, which
reconciles exactly with the server (2 645 tracked + 9 stale + 114 in `web` + 295 sheets).

### Deep dives (282 rows)

By snapshot: 100 / 97 / 85.

| field | value |
|---|---|
| cuts min / median / max | 0 / 7 / 42 |
| cuts = 0 | 38 |
| cuts NULL | 0 |
| cuts_ps min / median / max | 0.0 / 0.12 / 1.31 |
| mp4_mb median | 6.1 MB (NULL for 90 rows migrated from the August pass) |
| suitable = NULL (never reviewed) | **278** |
| suitable = 0 | 4 |
| suitable = 1 | **0** |

`unfit_why` is filled on exactly those 4: two "сгенерированные сцены с реальными людьми — правило 2а",
two "персонажи Family Guy и клонированные голоса — правило 2а". **Nothing has ever been marked
suitable.** The `suitable` field is effectively unused — 98.6 % NULL — so it cannot be used as a
filter.

### Is `cuts` a real cut count? — read `deep.py:cuts()`

```
ffmpeg -i <mp4> -filter:v "select='gt(scene,0.35)',showinfo" -f null -
```
then `len(re.findall(r'pts_time:', stderr))`.

This is **ffmpeg's scene-score threshold, not shot-boundary detection**. It counts frames whose
inter-frame difference score exceeds a fixed 0.35. Consequences:

- Misses hard cuts between visually similar shots — the same speaker, same set, same framing, which
  is exactly the talking-head format that dominates this niche.
- Over-counts fast camera motion, flashes, whip pans, heavy zoom transitions and screen-recording
  scrolls.
- The threshold is fixed at 0.35 with no per-clip calibration.
- `cuts_ps = cuts / max(dur, 1)` — for clips under one second the denominator is clamped, so
  `cuts_ps` is understated there.
- 38 rows report `cuts = 0`. That is plausible for a single-take piece to camera, but it is
  indistinguishable from a detection that simply did not fire.

**Verdict: usable as a relative "busy vs. calm" signal within this dataset. Not usable as an
absolute edit count, and not comparable to any externally reported cut rate.**

---

## 6. The analysis-ready corpus

| set | n |
|---|---|
| codes with a transcript | 273 |
| codes with frames | 295 |
| **codes with BOTH** | **273** |
| codes with frames but no transcript | 22 |
| codes with a transcript but no frames | 0 |
| **analysis-ready and transcript actually usable** | **266** |

The full code list is in the JSON as `code_lists.analysis_ready` (273 entries),
`code_lists.transcript_codes` (273), `code_lists.frame_codes` (295),
`code_lists.frames_only_no_transcript` (22) and
`code_lists.analysis_ready_but_transcript_unusable` (7).

Frames and transcripts are produced in the same `deep.py` pass on the same downloaded mp4, which is
why the nesting is near-total. The 22 frames-only codes are reels where Whisper returned nothing
usable or the transcript step was skipped.

## 7. Newest Hiker-only unprocessed set

Snapshot 3 (id 3, 2026-09-10) holds 1 535 codes, 470 of them seen for the first time.

| | n |
|---|---|
| codes in snapshot 3 | 1 535 |
| **with neither transcript nor frames** | **1 313** |
| of those, first seen on 2026-09-10 | **411** |
| with frames and/or transcript | 222 |

Lists: `code_lists.newest_snapshot_unprocessed` (1 313) and
`code_lists.newest_snapshot_unprocessed_first_seen` (411).

These are metadata-only rows: play, likes, comments, reshares, duration, caption, ts — no media, no
speech, no frames. The mp4 links they came with have long expired (CDN signatures last hours), so
re-processing them requires paying HikerAPI again for fresh links.

---

## 8. Topics

| | |
|---|---|
| rows | 2 482 |
| unique codes tagged | **1 454** (45.3 % of 3 211) |
| untagged reel codes | 1 757 |
| vocabulary size | 27 topics |
| topics per code min / median / max | 1 / 1 / 9 |
| orphans | 0 |

| source | rows | codes |
|---|---|---|
| sample | 1 432 | 857 |
| manual | 1 050 | 597 |

Top of the vocabulary: "Темы в подписи нет" 318, "Программирование и код" 242, "AI-видео и
производство контента" 182, "Claude Code: скиллы, плагины, команды" 172, "Новости моделей и
лабораторий" 169, "Дизайн и сайты через AI" 145, "Обучение и навыки" 134, "Личное, мотивация, влог"
133, "Обзор инструмента" 118, "Лидогенерация, скрейпинг, CRM" 103. Full frequency table in the JSON.

Note that the single largest label, at 318 occurrences, is **"Темы в подписи нет"** — the tagger's
way of saying it found nothing. Combined with "Только призыв, без темы в подписи" (52), 370 of the
2 482 tag rows are negative results. The 80 captions in `data/server-mirror/unmatched.md`
(dated 2026-09-10) are the queue waiting for new dictionary entries.

## 9. Scores

| | |
|---|---|
| rows | 7 477 |
| unique codes | **3 205** (99.8 %) |
| eligible rows | 6 820 |
| **eligible unique codes** | **2 961** |
| rows with `author_median_play` | 7 477 (100 %) |
| z NULL | 0 |

| snapshot | rows | codes | eligible rows |
|---|---|---|---|
| 1 | 4 692 | 2 346 | 4 285 |
| 2 | 1 255 | 1 255 | 1 156 |
| 3 | 1 530 | 1 530 | 1 379 |

Weights: `ig` 5 131 rows, `max` 2 346 rows. The `max` weight set was only ever run against
snapshot 1 — snapshots 2 and 3 have `ig` scores only. Any comparison of Max's weighting across
snapshots is impossible from this data.

`baseline_n` (reels of that author available for comparison) ranges 5–43, median band 11–23; the
single largest bucket is `baseline_n = 23` with 2 830 rows. `baseline_snaps`: 5 075 rows built from
1 snapshot, 1 255 from 2, 1 147 from 3. `axes` (components that survived): 6 145 rows on 5 axes,
1 083 on 4, 127 on 3, 122 on 2.

## 10. Cards

**23 rows.** Ids run 1–14 and 24–32 — **ids 15–23 are absent**, nine rows deleted or rolled back.
20 distinct codes; three codes recur across weeks (`Dco1mOJzZ4L`, `DcvBtiNtbYO`, `DcwCCgivcIQ`).

| week | n | status |
|---|---|---|
| 2026-09-03 | 5 | all `Proposed` |
| 2026-09-07 | 9 | 5 `draft`, 4 `вычеркнута` |
| 2026-09-10 | 9 | 4 `draft`, 5 `вычеркнута` |

`status` uses three vocabularies at once: `Proposed` (English, 2026-09-03), `draft` and
`вычеркнута` — not the `draft / взята / вычеркнута` the schema documents. Nothing is ever marked
`взята`.

Field completeness: **angle and hook filled on 14 of 23** — exactly the 14 not struck out. Every
struck-out card has `why`, `caption` and `shot_frame` filled but angle and hook empty, which is the
correct shape: the agent computed the facts, then rejected the reel before writing an angle.
`lead` is filled only on the five 2026-09-03 cards. **`goal` is empty on all 23.**

All 23 card codes exist in `reels` and all 23 have frames. One card lacks a transcript: id 14,
`DceZCRZIatT` (struck out anyway).

| id | week | code | fmt | pri | status | angle | hook |
|---|---|---|---|---|---|---|---|
| 1 | 09-03 | DbVKVz0y8xo | M2 Builds | 1 | Proposed | ✓ | ✓ |
| 2 | 09-03 | DbO4zvJR1k8 | M2 Teardown | 1 | Proposed | ✓ | ✓ |
| 3 | 09-03 | Dbi-yxNgrhG | M2 Radar | 2 | Proposed | ✓ | ✓ |
| 4 | 09-03 | DcCfMoZRkgW | M2 Teardown | 2 | Proposed | ✓ | ✓ |
| 5 | 09-03 | Da73u-0ysYU | M2 Radar | 3 | Proposed | ✓ | ✓ |
| 6 | 09-07 | DcvBtiNtbYO | M2 Radar | 1 | draft | ✓ | ✓ |
| 7 | 09-07 | DcvX-lDAhk_ | M2 Radar | 2 | draft | ✓ | ✓ |
| 8 | 09-07 | DcoE5ZsK4I7 | M2 Radar | 3 | вычеркнута | — | — |
| 9 | 09-07 | Dco1mOJzZ4L | M2 Builds | 4 | draft | ✓ | ✓ |
| 10 | 09-07 | DczDlj4qQjI | M2 Builds | 5 | вычеркнута | — | — |
| 11 | 09-07 | DcU_BdKulGJ | M2 Builds | 6 | draft | ✓ | ✓ |
| 12 | 09-07 | DcwCCgivcIQ | M2 Teardown | 7 | draft | ✓ | ✓ |
| 13 | 09-07 | Dc326slsdAU | M2 Teardown | 8 | вычеркнута | — | — |
| 14 | 09-07 | DceZCRZIatT | M2 Teardown | 9 | вычеркнута | — | — |
| 24 | 09-10 | Dc_tsSeAjBy | M2 Radar | 1 | draft | ✓ | ✓ |
| 25 | 09-10 | DcvBtiNtbYO | M2 Radar | 2 | вычеркнута | — | — |
| 26 | 09-10 | DcmK70aO5VP | M2 Radar | 3 | draft | ✓ | ✓ |
| 27 | 09-10 | Dct6Op3n6Zd | M2 Builds | 4 | вычеркнута | — | — |
| 28 | 09-10 | DcxV37-CJOC | M2 Builds | 5 | вычеркнута | — | — |
| 29 | 09-10 | DdCvFdHsnj1 | M2 Builds | 6 | draft | ✓ | ✓ |
| 30 | 09-10 | Dco1mOJzZ4L | M2 Teardown | 7 | draft | ✓ | ✓ |
| 31 | 09-10 | DcwCCgivcIQ | M2 Teardown | 8 | вычеркнута | — | — |
| 32 | 09-10 | Dc_iv4YKCAh | M2 Teardown | 9 | вычеркнута | — | — |

**Local dataset DBs:** `dataset/radar.db` holds the first 5 cards, `dataset/radar-0907.db` holds
the first 14. Both are prefixes of the server set — no card exists only locally.

**`runs/2026-09-07/cards.html`** (2.81 MB, title "Что снимать · 7 сентября"): renders the 5 kept
cards of that week — `DcvBtiNtbYO`, `DcvX-lDAhk_`, `Dco1mOJzZ4L`, `DcU_BdKulGJ`, `DcwCCgivcIQ` —
each with one base64-inlined contact sheet, plus a section "Что агент вычеркнул". The 4 struck-out
codes appear only as prose, not as cards. Alongside it, `turns.html` (4.63 MB) covers 10 further
codes, and 15 loose jpgs — every one of the 15 already has frames in the DB, so nothing here is
unique data. `README.md` records the run: 106 accounts, 1 260 reels, 97 analysed, cost $2.12, and
that the Notion export failed because the three databases had been archived.

## 11. Spend and tool log

**889 units, $17.78** across 10 rows, at a flat $0.02/unit.

| item | units | usd |
|---|---|---|
| профили 254 авторов | 253 | 5.06 |
| сбор роликов (2 runs) | 236 | 4.72 |
| ролики 100 аккаунтов, 2 страницы | 196 | 3.92 |
| добор: поиск и соседи (2 runs) | 60 | 1.20 |
| соседи и ролики добранных | 54 | 1.08 |
| разведка ниши, 30 запросов | 30 | 0.60 |
| проверки | 30 | 0.60 |
| добор профилей по списку Миши | 30 | 0.60 |

By date: 2026-09-01 $11.26 · 09-03 $1.20 · 09-07 $2.12 · 09-09 $0.60 · 09-10 $2.60.

**`tool_log`: 37 rows** — bug 18 (all 18 fixed), gap 14 (10 fixed, 4 open), junk 4 (3 fixed),
manual 1 (open). Six open items are listed in the JSON under `tool_log.open_items`.

## 12. Empty tables

`our_posts` 0 · `our_metrics` 0 · `followers` 0.

The whole feedback half of the schema is unpopulated. Nothing we publish is recorded, none of the
six manual metrics per post exist, and there is no follower time series for any account. Every
"who is growing / did it work for us" question is unanswerable from this database — not because the
data is bad, but because it was never entered.

---

## 13. Damage report — explicit flags

| flag | count | unit | definition |
|---|---|---|---|
| **MISSING_STATS** | **1** | reel code | `play` NULL or 0 in every snapshot row — `B-MYSMhHXy6` |
| **MISSING_MEDIA** | **1** | reel code | deep dive ran but no usable frame files landed — `DcxV37-CJOC` |
| **MISSING_TRANSCRIPT** | **2 938** | reel code | unique reel code with no `transcripts` row (22 of these do have frames) |
| **MISSING_FRAMES** | **2 916** | reel code | unique reel code with no `frames` rows |
| **BROKEN_FRAME_REFERENCE** | **8** | frames row | `frames.path` points at a non-existent file, all in `DcxV37-CJOC` |
| **UNALIGNED_TRANSCRIPT** | **7** | transcript row | `segments` is `[]` — no timestamps, no text |
| **DUPLICATE_VIDEO** | **0** | reel code | same `pk_user`+`ts`+`dur` under two codes — none exist |
| **STALE_METRICS** | **1 676** | reel code | not refreshed in snapshot 3: 1 480 last seen in snapshot 1, 196 in snapshot 2 |
| **UNRESOLVED_CREATOR_ID** | **1** | reel code | `DcFm9i5s5q8` carries two pk/username pairs across snapshots |

Secondary counts attached to those flags:

- **Saves**: 226 codes never returned a save count; 486 of 5 147 rows have `save IS NULL`. Treat
  as missing, never as zero — any saves-per-1k rate built without missingness handling is wrong.
- **Repost suspects** (a softer read of DUPLICATE_VIDEO): 25 groups covering **56 codes** share an
  author and a byte-identical caption over 30 characters under different codes — e.g. three codes
  for `DYznKz1vvH8 / DYznIPLPuEw / DYznCg6P3o4`. These are the same creative re-uploaded, and they
  inflate that author's baseline.
- **Untracked frame files**: 9 stale jpgs in `DbYh2P-MQnj`, 114 jpgs in a non-reel `web` directory.
- **Unresolved candidates**: 918 accounts have neither `follower_count` nor `last_checked` — the
  candidate pool was never profiled.
- **mp4 originals**: `/opt/radar/data/video` is empty. This is by design (SPEC §4.4) but it means
  **no reel has retrievable source video** — frames and transcripts are the only record, and neither
  can be regenerated without paying for a new link.

---

## 14. What exists only where

| Data | Main data (server DB + `data/`) | Max's `origin/Latest` / `max/main` | August archive |
|---|---|---|---|
| Reel metrics (3 211 codes, 5 147 readings) | **only here** | — | superseded copy: `archive/2026-08/data/reels.json`, 2 352 codes, all present in the DB |
| Transcripts | **273 codes, timed segments** | — | `archive/2026-08` 91 codes (all absorbed); `dataset/2026-08-niche-research` **8 codes, none in the DB** |
| Frames | **295 codes, 2 653 files** | — | `dataset/2026-08-niche-research` **8 codes / 74 jpgs + 7 base64 sets, none in the DB** |
| Scene cuts | 282 deep dives | — | `archive/2026-08/data/scenecuts.json`, 100 codes, absorbed |
| Scores | 7 477 rows, `ig`+`max` weights | — | `scored_ig.json` / `scored_max.json`, absorbed |
| Topics | 1 454 codes, 27 labels | — | absorbed |
| Cards (real, reel-referenced) | **23** | — | — |
| Script cards (invented) | — | **10 × `examples/ten-card-20260907/*.json`, `"synthesis": true`** | — |
| Storyboard PNGs | — | **10 files** | — |
| Field dictionary / schemas | — | **`docs/m2-field-dictionary.csv` (65 defs), `schemas/*.json`, `m2_signal/schema.sql`** | — |
| Account profiles | 439 profiled of 1 357 | — | `profiles.json` 258 + `neighbor_profiles.json` 98 (candidate research) |
| Raw HikerAPI cache | `cache/` 315 entries | — | `dataset/2026-08-niche-research/cache` 76 files |
| Rendered run pages | `runs/2026-09-07` (cards/turns HTML), server `/opt/radar/runs/2026-09-07` | — | `archive/2026-08/*.html` |
| Audit derivatives | `audit-2026-09-08/` (top-reels.csv 150 rows/119 codes, topics.csv 27 rows, 81 KB report) | — | — |

### On Max's branches — scanned, nothing found

Every non-binary file in `origin/Latest` (228 files) was read and matched against the 3 211 server
reel codes. **Zero transcripts, zero frames, zero feature exports, zero reel-level records.**
`outputs/reports/` does not exist on either branch. `max/main` differs from `origin/Latest` by five
files only: `docs/m2-20260911-execution-architecture-report.{md,pdf}`,
`docs/m2-20260911-reconciled-analysis-and-cards.{md,pdf}` and `scripts/build_m2_reconciled_pdf.py`.

One apparent hit is a false positive: `tests/test_media_recovery.py` contains the literal string
`B-MYSMhHXy6`, which happens to also be a reel code in snapshot 1. It is a test fixture, not data.

What is there is contracts and schemas: `docs/m2-field-dictionary.csv` defines 65 columns
(scope / column / notion_type / meaning / null semantics / permissible inference) sourced from
"package.private.json reels.properties / frozen Signal release" — a file that is not in the repo.
The ten card JSONs are fully written 60-second scripts with shot lists, but every one carries
`"synthesis": true` and a `DESIGNED_NOT_MODEL_EXECUTED` fixture state: they are invented examples,
not derived from any reel in our corpus.

### Local DB copies — all strict subsets, verified

| file | size | snapshots | reels | transcripts | frames codes | deepdives | topics | cards | records only local |
|---|---|---|---|---|---|---|---|---|---|
| `dataset/radar.db` | 2.78 MB | 1 | 2 352 | 91 | 114 | 100 | 914 | 5 | **0** |
| `dataset/radar-0907.db` | 3.94 MB | 1, 2 | 2 741 | 188 | 210 | 197 | 1 187 | 14 | **0** |
| `data/server-mirror/archive/radar-0907.db` | 3.94 MB | 1, 2 | 2 741 | 188 | 210 | 197 | 1 187 | 14 | **0** |

For each: zero reel / transcript / frame / deep dive / topic / account / card records present
locally and absent on the server, **and zero value differences** on the 3 612 shared
(snapshot_id, code) reel rows. Nothing needs to be recovered from them; they are safe to treat as
historical snapshots of the server DB and can be deleted without loss.

### The one genuine gap: `dataset/2026-08-niche-research`

This is the very first niche pass, before the database existed, and it was **never migrated**.
It holds 8 transcripts (`{lang, segments}` shape, same `s/e/t` segments) and frame sets for 8 codes
— 74 jpgs plus 7 base64 bundles of 6 frames each — for:

`DRXZJeHiAES` · `DT0fJmxjVnI` · `DU9OIJUCBQz` · `DZw4aTtzJpg` · `Db5sXEAP6C4` · `Db9AEm5upfu` ·
`DbOUP9OPDAQ` · `DcdbJKmxZ5o`

None of these 8 codes has a transcript or frames in the server DB. Only 2 of them (`DRXZJeHiAES`,
`Db5sXEAP6C4`) even exist in the `reels` table, so the other 6 have media analysis but no metrics.
Alongside them: `reels_pool.json` 117 reels, `pool2.json` 94, `profiles.json` 22 accounts,
`cand_search.json` 158 handles — candidate research that predates the account roster.
The identically named `archive/2026-08/` directory is a *different, later* pass and is fully
absorbed (all 91 of its transcripts and all 2 352 of its reels are in the DB).

### Other side sources

- `data/server-mirror/archive/harvest.log` — 7 lines. The 2026-09-03 top-up aborted: HikerAPI
  returned 401 on five consecutive attempts over two hours, stopped manually to avoid a block.
  933 accounts remained unprofiled.
- `data/server-mirror/unmatched.md` — 80 captions with no topic, dated 2026-09-10. The archived
  copy is the older 2026-09-08 version with 29.
- `data/server-mirror/archive/snapshots/2026-09-01.json` (404 KB, keys `taken`/`accounts`/`rows`) —
  the pre-DB form of snapshot 1; byte-identical copy in `dataset/snapshots/`.
- Server `/opt/radar/data/runs/` — two run logs (`2026-09-07_0700.log` 18 KB,
  `2026-09-10_0700.log` 19 KB) and a `2026-09-10/` directory. Server `/opt/radar/runs/2026-09-07/`
  holds 7 rendered pages (niche.html, radar.html, shoot.html and run output).
- `audit-2026-09-08/` — Misha's audit of Max's work: `data/top-reels.csv` (150 rows, 119 distinct
  codes, all present in the server `reels`; 85 rows flagged `transcript_available`),
  `data/topics.csv` (27 rows), 20 Notion exports, 4 audit documents, an 81 KB report with its PDF
  toolchain. All of it is derived from `radar-0907.db` — no unique records.

---

## 15. What could not be determined

1. **Whether the 11 missing snapshot-1 reels were dropped or miscounted.** `snapshots.reels_n`
   says 2 363, the table holds 2 352. The pre-DB JSON (`snapshots/2026-09-01.json`) is the only
   possible arbiter and reconciling it row by row is outside this inventory's scope.
2. **Whether `cuts = 0` on 38 deep dives means a genuine single take or a failed detection.** The
   mp4s are deleted, so it cannot be re-derived. Only the contact sheets can settle it, by eye.
3. **True cut counts for any reel.** See §5 — the method is a scene-score threshold, and the source
   video no longer exists to re-measure with a better one.
4. **Whether the 22 frames-only codes failed transcription or were skipped.** `deep.py` prints the
   Whisper failure to stdout and writes nothing to the DB, so the distinction is not recorded
   anywhere in the data. The run logs on the server may hold it.
5. **Anything about our own publishing performance.** `our_posts`, `our_metrics` and `followers`
   are empty.
6. **Max's upstream data.** The field dictionary references `package.private.json` as its source;
   that file is in neither branch, so the columns it documents cannot be checked against values.

---

## Appendix — SQL and commands used

Integrity of the mirror:

```
md5 data/server-mirror/radar.db
ssh m2vps 'md5sum /opt/radar/data/radar.db'
```

Accounts:

```sql
SELECT COALESCE(tag,'(null)'), COALESCE(status,'(null)'), COUNT(*)
  FROM accounts GROUP BY 1,2;

SELECT COUNT(*) FROM accounts a
 WHERE EXISTS (SELECT 1 FROM reels r WHERE r.pk_user = a.pk);

SELECT CASE WHEN follower_count IS NULL THEN 'unknown'
            WHEN follower_count < 1000 THEN '<1k'
            WHEN follower_count < 10000 THEN '1k-10k'
            WHEN follower_count < 50000 THEN '10k-50k'
            WHEN follower_count < 100000 THEN '50k-100k'
            WHEN follower_count < 500000 THEN '100k-500k'
            WHEN follower_count < 1000000 THEN '500k-1M'
            ELSE '>=1M' END, COUNT(*)
  FROM accounts GROUP BY 1;

SELECT COUNT(*) FROM accounts WHERE biography IS NOT NULL AND TRIM(biography) <> '';
SELECT COUNT(*) FROM accounts WHERE category  IS NOT NULL AND TRIM(category)  <> '';
```

Reels:

```sql
SELECT COUNT(*), COUNT(DISTINCT code) FROM reels;
SELECT snapshot_id, COUNT(*), COUNT(DISTINCT code) FROM reels GROUP BY 1;
SELECT n, COUNT(*) FROM (SELECT code, COUNT(DISTINCT snapshot_id) n FROM reels GROUP BY code) GROUP BY 1;

-- code-level stat presence
SELECT COUNT(*) FROM (SELECT code FROM reels GROUP BY code
                       HAVING SUM(CASE WHEN play > 0 THEN 1 ELSE 0 END) = 0);
SELECT COUNT(*) FROM (SELECT code FROM reels GROUP BY code
                       HAVING SUM(CASE WHEN save IS NOT NULL THEN 1 ELSE 0 END) = 0);
SELECT COUNT(*) FROM (SELECT code FROM reels GROUP BY code
                       HAVING SUM(CASE WHEN cap IS NOT NULL AND TRIM(cap) <> '' THEN 1 ELSE 0 END) > 0);

SELECT snapshot_id, COUNT(*), SUM(play IS NULL), SUM(play = 0), SUM(save IS NULL),
       SUM(resh IS NULL), SUM(dur IS NULL OR dur <= 0),
       SUM(cap IS NULL OR TRIM(cap) = ''), SUM(ts IS NULL OR ts = 0)
  FROM reels GROUP BY 1;

SELECT MIN(ts), MAX(ts) FROM reels WHERE ts > 0;
SELECT strftime('%Y-%m', ts, 'unixepoch'), COUNT(DISTINCT code)
  FROM reels WHERE ts > 0 GROUP BY 1;

-- identity conflicts
SELECT code FROM reels GROUP BY code
 HAVING COUNT(DISTINCT username) > 1 OR COUNT(DISTINCT pk_user) > 1;

-- DUPLICATE_VIDEO
SELECT pk_user, ts, dur, COUNT(DISTINCT code)
  FROM reels WHERE ts > 0 GROUP BY 1,2,3 HAVING COUNT(DISTINCT code) > 1;

-- repost suspects
SELECT pk_user, COUNT(DISTINCT code), GROUP_CONCAT(DISTINCT code)
  FROM reels WHERE cap IS NOT NULL AND LENGTH(TRIM(cap)) > 30
 GROUP BY pk_user, cap HAVING COUNT(DISTINCT code) > 1;

-- STALE_METRICS
SELECT ms, COUNT(*) FROM (SELECT code, MAX(snapshot_id) AS ms FROM reels GROUP BY code)
 GROUP BY ms;
```

Transcripts (segment validity checked in Python: `json.loads` on each `segments`, then
`all('s' in x and 'e' in x for x in parsed)`):

```sql
SELECT COALESCE(lang,'(null)'), COUNT(*) FROM transcripts GROUP BY 1;
SELECT COUNT(*) FROM transcripts WHERE text IS NULL OR TRIM(text) = '';
SELECT COUNT(*) FROM transcripts WHERE COALESCE(words,0) < 10;
SELECT COUNT(*) FROM transcripts WHERE code NOT IN (SELECT code FROM reels);
SELECT code, words, segments FROM transcripts;   -- parsed in Python
```

Words per second joins `transcripts.words` to `MAX(reels.dur)` per code.

Frames and deep dives:

```sql
SELECT COUNT(*), COUNT(DISTINCT code) FROM frames;
SELECT n, COUNT(*) FROM (SELECT code, COUNT(*) n FROM frames GROUP BY code) GROUP BY 1;
SELECT DISTINCT code FROM frames WHERE code NOT IN (SELECT code FROM deepdives);
SELECT code FROM deepdives WHERE code NOT IN (SELECT DISTINCT code FROM frames);
SELECT CASE WHEN suitable IS NULL THEN 'NULL' WHEN suitable = 1 THEN '1' ELSE '0' END,
       COUNT(*) FROM deepdives GROUP BY 1;
SELECT COALESCE(unfit_why,'(null)'), COUNT(*) FROM deepdives GROUP BY 1;
```

File existence on the server — one ssh call, all 2 653 paths:

```
ssh m2vps 'cd /opt/radar && python3 - <<EOF
import sqlite3, os
con = sqlite3.connect("file:data/radar.db?mode=ro", uri=True)
rows = list(con.execute("SELECT code, idx, path FROM frames"))
miss = [r for r in rows if not r[2] or not os.path.exists(r[2])]
print(len(rows), len(rows) - len(miss), len(miss))
EOF'
```

Corpus sets (Python, over the same DB):

```python
t = {r[0] for r in con.execute("SELECT DISTINCT code FROM transcripts")}
f = {r[0] for r in con.execute("SELECT DISTINCT code FROM frames")}
ready = sorted(t & f)                                   # 273

maxsid   = con.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]   # 3
new      = {r[0] for r in con.execute("SELECT DISTINCT code FROM reels WHERE snapshot_id=?", (maxsid,))}
prev     = {r[0] for r in con.execute("SELECT DISTINCT code FROM reels WHERE snapshot_id<?", (maxsid,))}
unproc   = sorted(c for c in new if c not in t and c not in f)          # 1313
unproc_n = sorted(c for c in (new - prev) if c not in t and c not in f) # 411
```

Topics, scores, cards, spend, tool log:

```sql
SELECT COUNT(*), COUNT(DISTINCT code) FROM topics;
SELECT topic, COUNT(*) FROM topics GROUP BY 1 ORDER BY 2 DESC;
SELECT COALESCE(source,'(null)'), COUNT(*), COUNT(DISTINCT code) FROM topics GROUP BY 1;

SELECT snapshot_id, COUNT(*), COUNT(DISTINCT code), SUM(eligible = 1),
       SUM(author_median_play IS NOT NULL) FROM scores GROUP BY 1;
SELECT weights, COUNT(*) FROM scores GROUP BY 1;
SELECT COALESCE(baseline_n,-1), COUNT(*) FROM scores GROUP BY 1 ORDER BY 1;
SELECT COALESCE(axes,-1), COUNT(*) FROM scores GROUP BY 1 ORDER BY 1;

SELECT id, week, code, fmt, pri, status,
       (angle IS NOT NULL AND TRIM(angle) <> ''),
       (hook  IS NOT NULL AND TRIM(hook)  <> ''),
       (code IN (SELECT code FROM frames)),
       (code IN (SELECT code FROM transcripts))
  FROM cards ORDER BY id;

SELECT item, COUNT(*), SUM(units), ROUND(SUM(usd),4) FROM spend GROUP BY 1;
SELECT COALESCE(kind,'(null)'), COUNT(*), SUM(fixed = 1) FROM tool_log GROUP BY 1;
```

Local DB comparison — for each of the three local copies, every code set was differenced against
the server and all shared `(snapshot_id, code)` reel rows were compared field by field on
`play, likes, comm, resh, save`.

Max's branches:

```
git ls-tree -r --name-only origin/Latest
git show origin/Latest:<path>          # every non-binary file, regex-matched
                                       # against the 3 211 server reel codes
git diff --stat origin/Latest max/main
```
