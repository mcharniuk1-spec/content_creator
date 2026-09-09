# Верификация: analytics-audit.md

| Claim | Location | Verdict | Evidence |
|---|---|---|---|
| 2 352 рилса, 100 аккаунтов | §1 table, row 1 | CONFIRMED | `data/max-pipeline.md:42` "2,352 Reels, 100 accounts" |
| `"hikerapi_calls": 0` | §1, `max-pipeline.md:62` | CONFIRMED | line 62 verbatim |
| 1 062/2 352 (45,2%): 954/108/108/24/1 158 | §1 ASR row, `max-latest-pipeline.md:53` | CONFIRMED | line 53 verbatim; sum 954+108+108+24+1158=2352 |
| `"The other 1,044 transcripts have lexical inventory..."` | §1, `:53` | CONFIRMED | verbatim at line 53 |
| 18 read, 262 samples, 64 observations | §1, §2 | CONFIRMED | `max-latest-pipeline.md:45`, `notion-raw/01:34` verbatim |
| R7 pilot: `SUSPICIOUS_TIMINGS`/`analysis_ready:false`/`approved:false` | §1, `:55` | CONFIRMED | verbatim at line 55 |
| 1 194 frame sets, 19 808 images | §1, `notion-raw/01:33` | CONFIRMED | verbatim at line 33 |
| 9 625 cut candidates | §1 (no citation given) | CONFIRMED (uncited) | actually at `notion-raw/04:45`, not `01:33` — number is correct, just not sourced to the line shown |
| 64 frames, 17 collages, 3 reels | §1, `:41` | CONFIRMED | verbatim `frames_covered:64`, `collages_inspected:17` at line 41 |
| `source_media_included:false` / `raw_transcripts_included:false` | §1, `:41,:57` | CONFIRMED | both verbatim at cited lines |
| `"kind":"ILLUSTRATED_CONTACT_SHEET"` + `"Composition guide only; not an owner take..."` | §1, cited `:43` | **WRONG citation** | `"kind"` phrase is at line 43, but the full "Composition guide only; not an owner take, product output, or production asset binding." string is verbatim only at **line 30** (13 lines off) |
| `"editorial_review_state":"ACCEPTED_WITH_LIMITATIONS_OWNER_SHOOT_PENDING"` + `AWAITING_OWNER_ASSET` | §1, cited `:30` | **WRONG citation** (partial) | `AWAITING_OWNER_ASSET` is at line 30 (OK); the `editorial_review_state` value is at **line 61**, not 30 (31 lines off). Value itself confirmed real — verified directly in `data/max-latest/M2-I01.json` |
| Design pack deleted (~90 files, PRODUCTION.md) | §1, §3.9, `:18` | CONFIRMED | verbatim at line 18 |
| 3.784% → 45.2% coverage shift | §1 closing para | CONFIRMED | `max-pipeline.md:73` "3.784%"; `max-latest-pipeline.md:53` "45.2%" |
| Old release: `NOT_ATTEMPTED`/`MISSING_SOURCE_MEDIA`, legacy transcripts, 64 synthetic Remotion frames | §1 comparison para | CONFIRMED | `max-pipeline.md:67,74,69` verbatim |
| 65 fields, 0 hook/problem/solution/tool/CTA columns | §3.2 | CONFIRMED | `m2-field-dictionary.csv` = 65 data rows + header; grep of column-name field for hook/problem/solution/tool/cta → 0 hits |
| `Text fit candidate` / `Lexical text words` fields | §3.1, cited `:31,:34` | CONFIRMED, imprecise | fields exist, but at lines 31 and **33** (not 34) — 2-line drift, within tolerance |
| `DESIGNED_NOT_MODEL_EXECUTED` in all 10 cards | §3.8, §8 | CONFIRMED | present exactly once in each of the 10 `data/max-latest/M2-*.json` files |
| start_ms/end_ms on 7 scenes = 60 000ms | §3.4 | CONFIRMED | `M2-I01.json` shots: 0-7000...50000-60000, sums to 60s |
| "template 7×8.5s" | §3.4 | Loose but acceptable | actual scene lengths are 7/9/9/8/8/9/10s (avg 8.57s); called a "template," not exact — not a factual error |

## Section 2 — quoted conclusions, verbatim check

| Quote | Cited at | Verdict |
|---|---|---|
| "The strongest direction for this slate is to show a small, recognisable failure..." | `notion-raw/01:23` | CONFIRMED verbatim |
| "That is an editorial conclusion from the selected material, not a claim..." | `01:24` | CONFIRMED verbatim |
| "concrete work problems can be made legible with an input, a visible gap, and a next decision" | `notion-raw/04:25` | CONFIRMED verbatim |
| "We have not isolated which feature caused a Reel's views." | `04:25` | CONFIRMED verbatim |
| "A high ratio helps identify a post worth inspecting. It cannot establish..." | `01:38` | CONFIRMED verbatim |
| "1,062 non-empty machine transcripts — 45.2% of Reels" | `01:32` | CONFIRMED verbatim |
| "18 selected Reels from 15 accounts: full-text and sampled-visual review..." | `01:34` | CONFIRMED verbatim |
| "The ten demonstrations are authored fictional examples..." | `01:47` | CONFIRMED verbatim |
| "It is a secondary, untrusted reference for editorial structure..." | `03:41` | CONFIRMED verbatim |
| "Read the entire selected transcript and inspect timestamped visual evidence..." | `03:31` | CONFIRMED verbatim |
| "It proves deterministic data handling... does not prove representative market coverage..." | `notion-raw/90:37` | CONFIRMED verbatim, **but context note**: this page (90) is a 2026-08-25 "Signal-to-Studio Bootstrap" review of an unrelated YouTube/12-seed pilot, not the Sept Instagram reels pipeline being audited. Quote is real; using it to characterize the same pipeline is a stretch the audit doesn't flag. |
| "BLOCKED for ... transcript coverage, full-video analysis, and frame-by-frame reference coverage" | `notion-raw/91:69` | CONFIRMED verbatim, **same caveat**: page 91 is the 2026-08-26 "North Hux" cross-platform account-discovery dashboard (YouTube/TikTok/IG scouting), a separate tool from the M2 reels pipeline. The audit's line "его собственный дашборд помечает ровно те три вещи, которые нужны для карточек" implies it's the same system's dashboard; it is an adjacent one. |

## Section 4 — transcript schema example (DbVq4mwz38L)

All confirmed against `radar-0907.db` (sqlite3, read-only) and its `segments` JSON:
- `reels`: author=heystevetan, play=439974, dur=53.5 — CONFIRMED
- `scores` (weights='ig'): z=5.0, author_median_play=15832, resh_1k=27.856→27.86, save_1k=53.955→53.96, comm_1k=26.595→26.59, baseline_n=5 — CONFIRMED, exact
- `transcripts`: lang=en, words=213 — CONFIRMED
- Hook/problem/solution/CTA text and timings — CONFIRMED verbatim, boundaries match segment `s`/`e` exactly (hook 0.0–3.2, problem 9.9–19.8, solution 19.8–32.2, CTA 47.8–53.5)
- `deepdives`: cuts=7, cuts_ps=0.13 — CONFIRMED
- **WRONG (minor)**: `asr_note` says ASR rendered "cloud code" at "45.6-47.8 s"; the segment table shows the text "You drop into cloud code" only spans 45.6–46.6s. 46.6–47.8s is a separate segment ("to walk you through the hard part") that does not contain "cloud code". Should read 45.6–46.6s.

## Section 5 — frame schema example (DbVq4mwz38L)

All 9 frames confirmed on disk (`data/frames/DbVq4mwz38L/`) and in `frames` table at exact timestamps: 0.4, 1.2, 2.4, 4.0, 8.9, 17.8, 26.8, 35.7, 44.6s. Spot-checked on-screen text against actual images (0.4s, 4.0s, 8.9s, 17.8s, 35.7s, 44.6s) — every quoted string ("This 17 YEAR OLD", "It is called OpenReply", "types"/"iamrishabhm_ Repo" etc., "$39"/"Bill amount"/"101K", "Tech stack"/"Next.js 16 and React 19", "and THE REPO"/"Set it up with your AI assistant"/"If you use Claude Code, Cursor, or a similar tool") is CONFIRMED verbatim on the actual frame. "Last frame at 44.6s, CTA starts at 47.8s" — CONFIRMED (frame table max t=44.6; transcript segment CTA starts 47.8).

## Brand-file citations (§4 rules, §6–§8)

All spot-checked against `~/Desktop/m2lab-brand/brand/06-formats.md` and `04-voice.md`: pillars/questions (`06-formats.md:9-11`), timing bands (`:17-23`), four-question gate (`:30-37`), three readers (`:43-47`), comment-bait ban (`:60`), sound-off/no-handle check (`:92-94`), "Is the proof ours?" (`:94`), failure-in-body principle (`04-voice.md:26-32`), CTA-as-own-action (`:44-50`), 6-8 words on cover (`:68`), verdict format (`:83-89`), WAS/NOW/SAVED (`:91-98`) — all CONFIRMED verbatim, exact lines.

## Verdict: PASS WITH FIXES

1. Fix citation for storyboard quote in §1 table: split into `:30` (full "Composition guide only..." string) and `:43` (the `"kind"` label + paraphrase).
2. Fix citation for `editorial_review_state` value in §1 table: `:61`, not `:30` (or cite the card JSON directly, which also works).
3. Correct the ASR note in §4's schema example: "cloud code" ASR text is 45.6–46.6s, not 45.6–47.8s.
4. Optional: tighten §3.1's field-dictionary line pointers to `:31` and `:33` (currently `:31`/`:34`).
5. Optional: add a one-line caveat that `notion-raw/90` and `91` describe adjacent/earlier Max projects (Aug 25 YouTube bootstrap; Aug 26 North Hux cross-platform dashboard), not the September Instagram reels pipeline itself — the quotes are accurate but not from the same system being audited.

No fabricated numbers, no invented quotes, and both real-data schema examples (transcript and frames) check out cleanly against the live database and files.
