# 4. Database Reconciliation

Three places have held M2Radar data: main's SQLite (`data/radar.db`, the canonical store), Max's
`Latest` branch (the `m2_signal` ledger and a 65-column Notion field dictionary), and the August
2026 pre-database archive (`dataset/2026-08-niche-research/`). `docs/M2RADAR_DATABASE_RECONCILIATION.md`
is the binding map between them; this section summarizes its entity mapping, column-validation
highlights and vocabulary-drift findings.

## Entity mapping summary

| Entity | main (canonical) | Latest equivalent | Disposition |
|---|---|---|---|
| Creator / account | `accounts` (roster tag, status, misses, why_out, via) | `account_analysis`, `accounts.csv` (no roster lifecycle at all) | MIGRATED; roster lifecycle unique to main |
| Video / reel | `reels` (code, snapshot_id, ts, cap, play/likes/comm/resh/save, dur) | `observations` + `reel_analysis` + `reel_metric_values` | MIGRATED; Latest drops raw caption to a hash only |
| Score | `scores` (z, weights `ig`/`max`, baseline_n, baseline_snaps, axes) | `reel_metric_values`, `Diagnostic z` | MIGRATED unchanged; `weights` and `baseline_snaps` have **no Latest equivalent** |
| Transcript | `transcripts` (text, JSON segments) | evidence artifacts + provenance fields | The one place Latest is materially richer — see below |
| Frames / scenes | `frames`, `deepdives` (cuts, suitable, unfit_why) | `evidence_attempts`, scene/frame schema | MIGRATED; Latest refuses to import main's 2,653 existing frames |
| Cards | `cards` (23 rows, week/fmt/pri/status) | 10 example JSONs, all `"synthesis": true` | MIGRATED unchanged; Latest's examples are invented, not derived from any reel |
| State (new layer) | none pre-existing | `m2_orchestrator/state.py`, 41-stage DAG | NEW DERIVED, trimmed to 25 stages (`runs`/`jobs`/`video_state`) |
| Our own publishing | `our_posts`, `our_metrics` (both empty) | none | MIGRATED; unanswerable from any source |

Full attribute-level tables (creator, reel, transcript, beats, frames/scenes, features, cards,
state) live in the reconciliation doc §1–§8; the rows above are its summary, not a replacement.

## Column validation highlights

The reconciliation doc's per-field validation rules (§9) surface the corpus's real edge cases
rather than assuming clean data:

- **`views`**: NULL or 0 in every snapshot row for exactly one code (`B-MYSMhHXy6`) → `MISSING_STATS`.
- **`saves`**: NULL on 486 of 5,147 rows (226 codes never returned a value) — "treat as missing,
  never as zero"; any saves-per-1k rate built without this guard is wrong.
- **Transcript text**: an empty string with `words = 0` is a *legitimate result*
  (`EMPTY_NO_SPEECH`, 7 codes), not a processing failure.
- **Words per second**: `words / speech_seconds`, where `speech_seconds = Σ(e − s)` over segments
  — explicitly **not** words divided by video duration, a distinction the reconciliation was
  built to enforce after finding the two conflated in earlier ad-hoc analysis.
- **Cut counts**: `deepdives.cuts` is a `ffmpeg select='gt(scene,0.35)'` threshold count on an mp4
  that no longer exists — never a verified cut count. 38 of 282 deep dives report `cuts = 0`,
  indistinguishable from a detector that simply never fired.
- **Posting date vs snapshot date**: `reels.ts` is post age; `snapshots.taken` is capture date.
  Latest's ledger conflates the two — main's `AGE_BANDS` in `score.py` exists precisely because
  this distinction matters.

## Vocabulary drift found

`accounts.tag`/`accounts.status` is documented in `db.py` as `core/neighbor/out` and
`active/dropped/candidate`. The live data uses a different vocabulary entirely:

| tag | status | rows | documented? |
|---|---|---:|---|
| `core` | `active` | 130 | yes |
| `out` | `out` | 234 | **no** |
| NULL | `candidate` | 920 | tag NULL undocumented |
| NULL | `rejected` | 73 | **no** |

`neighbor` and `dropped` are documented but never used; `out` and `rejected` are used but
undocumented, and `tag` is NULL on 993 of 1,357 rows. A query written from the schema comment
(`WHERE status = 'dropped'`) silently returns zero rows rather than erroring. This drift is
recorded, not fixed — changing either column moves rows underneath `check.py`, `roster.py` and
`judge_accounts.py`, which the schema/state owner flagged as a decision for the roster owner and
Misha, not one to take unilaterally.

A second drift, in `cards.status`: three vocabularies appear across the 23 real cards —
`Proposed` (English, the first week only), `draft`, and `вычеркнута` — never the documented
`draft / взята / вычеркнута`. Nothing has ever reached `взята`. A `cards.status_v2` column was
added by migration (guarded `ALTER TABLE`) to bridge toward `engine/cards_v2.py`'s status
vocabulary (`DRAFT/REVIEWED/APPROVED/SHOT/PUBLISHED/DROPPED`) without touching the Russian
vocabulary the legacy scripts depend on.

## What was deliberately not adopted

`m2_signal/schema.sql` as a store (24 MB/snapshot vs 5.2 MB for main's whole history, and it
discards main's frame evidence on import); content-addressed releases (forbids re-running a day
whose bytes changed); the 41-stage DAG (29 stages unimplemented); Latest's scoring model (no age
bands, focal row left in its own baseline, single-release only); `analysis_eligibility.py`'s
hardcoded `expected_rows=2352` default (fails closed on the current 3,211-code corpus); the
Apple-Vision OCR path (macOS only); and `requirements-m2-media.txt` wholesale (pins versions
newer than, and in one case a downgrade from, the working ASR stack already installed).
