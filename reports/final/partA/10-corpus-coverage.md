# 10. Corpus Coverage

## The tier table and its denominators

`engine.corpus.tiers()` (generated 2026-09-11T22:26Z, db md5 `6834ecb414400838fb17258919a2b442`) is
the evidence-tier vocabulary a report may divide by — distinct by design from
`video_state.corpus_tier`, the processing-state vocabulary (chapter 4 §4.4 of the architecture
doc explains why the two disagree and must never be mixed in one number):

| Tier (`engine.corpus.tiers()`) | Codes | Meaning |
|---|---:|---|
| `ANALYSIS_READY` | 268 | usable transcript (words>0, timed segments) **and** frames |
| `FRAMES_ONLY` | 22 | frames extracted, no `transcripts` row at all |
| `TRANSCRIPT_UNUSABLE` | 7 | a transcript row exists but is empty — no speech detected |
| `INGESTED_NOT_ANALYZED` | 2,914 | Hiker metadata only |
| **Total unique codes** | **3,211** | |

The second vocabulary, `video_state.corpus_tier`, reports `ANALYSIS_READY 268 / FRAMES_ONLY 29 /
INGESTED_NOT_ANALYZED 2,914` — it folds the 7 empty transcripts into `FRAMES_ONLY` rather than
giving them their own tier. Both are correct for what they measure; neither substitutes for the
other.

Denominators, named explicitly per number as the method requires:

| Denominator | n | The only questions it may answer |
|---|---:|---|
| `N_ingested` | 3,211 | Metric-only statements: performance, creator norms, temporal trends |
| `N_transcript` | 275 | "How many transcript rows exist" — nothing else (7 of them empty) |
| `N_transcript_usable` | 268 | Every statement about language, script or wording |
| `N_frames` | 297 | Every statement about what is on screen |
| `N_ready` | 268 | Every statement joining script **and** visuals |

266/3,211 ≈ 8.3% is the honest coverage figure for any structural claim about the niche; it is not
a random 8.3% (chapter 8/9 and the analysis chapters explain the selection bias this implies).

![Corpus coverage funnel](reports/charts/corpus_coverage_funnel.png)

The funnel traces the same narrowing — 3,211 ingested down to 268 fully analysed — as a single
picture; read it alongside the denominator table above, never in place of it.

## The newest-snapshot backlog, queued for the watchdog

Snapshot 3 (2026-09-10, id 3) holds 1,535 codes. **1,312** have neither transcript nor frames,
**410** of those seen for the first time in that snapshot (the pre-migration audit figure was
1,313/411; the one-code shift is the August-archive resolution). Their signed CDN media links have
expired, so reprocessing any of them costs a fresh HikerAPI call, not a free pass. `engine.watchdog`
selects and processes exactly this set from already-cached URLs without paying Hiker again, but as
chapter 8 records, it has not yet run against this backlog.

## Missingness flags (`reports/data/flags.json`)

| Flag | Codes | Definition |
|---|---:|---|
| `MISSING_TRANSCRIPT` | 2,936 | No `transcripts` row |
| `MISSING_FRAMES` | 2,914 | No `frames` rows |
| `STALE_METRICS` | 1,676 | Not present in the newest completed snapshot |
| `DUPLICATE_VIDEO` | 56 | Same author, byte-identical caption over 30 chars, different code (25 groups) |
| `UNALIGNED_TRANSCRIPT` | 7 | `transcripts.segments` empty or unparseable |
| `MISSING_STATS` | 1 | `play` NULL or 0 in every snapshot row (`B-MYSMhHXy6`) |
| `MISSING_MEDIA` | 1 | Deep dive ran but no usable frame files landed (`DcxV37-CJOC`) |
| `BROKEN_FRAME_REFERENCE` | 1 (8 rows) | `frames.path` points at a non-existent file |
| `UNRESOLVED_CREATOR_ID` | 1 | More than one `(pk_user, username)` pair across snapshots (`DcFm9i5s5q8`) |

**3,006 of 3,211 codes (94%) carry at least one flag** — mostly `MISSING_TRANSCRIPT` /
`MISSING_FRAMES`, i.e. simply unprocessed, not damaged. Real damage is concentrated in a handful of
codes named above by their exact code, not by count alone.

## Data-loss audit, per stage

| Stage | Expected | Observed | Missing | Failed | Duplicates | Orphans | Fix applied | Unresolved |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Ingestion (Hiker → `reels`) | 2,363 reels declared, snapshot 1 | 2,352 rows | 11 | 0 | 1,936 rows (by design, one reading/snapshot) | 0 from unknown account | none | 11 reels lost in JSON→SQLite migration, snapshot 1 only |
| Transcription | 3,211 candidate codes | 275 rows (281 post-migration) | 2,936 | 7 empty (`EMPTY_NO_SPEECH`) | 0 | 6 (`transcripts_without_reel`) | August archive import, +8 | 6 orphan codes, no paid re-lookup done |
| Frame extraction | 297 codes sampled | 2,653 rows / 2,645 files (2,727/2,719 post-migration) | 2,914 codes with none | 8 rows, 1 code (`DcxV37-CJOC`) | 9 stale jpgs (`DbYh2P-MQnj`) + 114 non-reel files (`web/`) | 6 (`frame_codes_without_reel`) | August archive import, +74 | 8 broken references, source video gone, unrecoverable |
| Scoring | 3,211 codes | 3,205 scored (99.8%), 2,961 eligible | 6 (no usable baseline) | 0 | n/a | 0 (`scores_without_reel`) | none | 6 codes (1 zero-play, 5 by one author) |
| Topic tagging | 3,211 codes | 1,454 tagged (45.3%) | 1,757 untagged | 0 | n/a | 0 (`topics_without_reel`) | ongoing manual/sample tagging | 1,757 backlog + 80 captions in `unmatched.md` |
| Cards (legacy) | n/a, candidate-driven | 23 rows, 20 distinct codes | ids 15–23 absent (9 rows) | 0 | 3 codes recur across weeks (by design) | 0 (`cards_without_reel`) | none | 9 deleted/rolled-back ids, not investigated further |
| Identity resolution | 3,211 codes, 1 creator each | 3,210 clean | n/a | n/a | n/a | n/a | none | 1 code (`DcFm9i5s5q8`), two `(pk_user, username)` pairs |
| August archive import | 8 legacy codes | 8 transcripts + 74 frames imported | n/a | n/a | 0 base64 fallbacks needed | 6 (`orphans_not_in_reels`) | full import, this migration | 6 codes with no `reels` row, excluded from every denominator |

`foreign_key_violations: []` and `integrity_check: ok` database-wide (`reports/migration-validation.json`)
— the loss above sits at the data-completeness layer (unprocessed backlog, one truncated download,
one pre-schema archive), not at referential integrity. No fix in this audit silently discarded a
record; every unresolved item is named by exact code and kept in whichever table already held it.
