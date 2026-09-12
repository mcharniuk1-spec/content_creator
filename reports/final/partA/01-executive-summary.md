# 1. Executive Summary

M2Radar's content engine is a research-to-production pipeline for M2 Lab's English-language
Instagram account: a weekly, paid HikerAPI collection feeds a normalized SQLite corpus of reels
and creators, which a free local pipeline (faster-whisper transcription, ffmpeg scene/frame
extraction, LLM semantic analysis) turns into statistics, numeric insights, ranked hypotheses,
original shooting cards, and — once a card is shot — a deterministic Remotion render. Nothing in
the engine posts, spends money without an estimate, or claims a result it has not measured; every
processing stage records an explicit state rather than an implicit "done."

**Corpus, as of the 2026-09-11 migration.** 1,357 accounts (130 active), 3 snapshots
(2026-09-01/07/10), 5,147 reel readings over **N_ingested = 3,211** unique codes. Of those,
**N_transcript = 275** carry a transcript row (7 empty — no speech detected), **N_transcript_usable
= 268** have a usable script, **N_frames = 297** have extracted frames, and **N_ready = 268** have
both — the only denominator for any claim that joins script to visuals. These four numbers are
not interchangeable: 3,211 ≠ 275 ≠ 297 ≠ 268, and every number below names which one it divides by.

## Headline findings

| # | Finding | Confidence |
|---|---|---|
| 1 | The analysed corpus is 268 of 3,211 codes (8.3%) and is the **top** of `score.py`'s own ranking, not a random sample — median `robust_z` inside it is +1.26 against 0.00 across all ingested reels. | RELIABLE |
| 2 | Duration does not predict performance: Spearman(duration, robust_z) = −0.069 (p<0.001) over all 3,211 reels; HIGH outliers run a median 46.8s against 47.8s for the rest. | RELIABLE |
| 3 | Hook length carries no measured signal (rho ≈ +0.06–0.08, p>0.2); the median hook is 6.7s / 21.5 words, not the 0–3s window house rules assume. | PROBABLE |
| 4 | Show-first hooks (demo/result first, n=42) outperform on reach: median robust_z 2.17 / view_lift 5.81 vs 1.21 / 1.80 for the rest. | PROBABLE |
| 5 | Setup-first hooks (identity/story/problem-call-out, n=39) underperform: median robust_z 0.67 vs 1.36 (p=0.002). | PROBABLE |
| 6 | Questions in the script depress saves: rho(questions, save_rate) = −0.229 (p<0.001), survives creator normalisation. | RELIABLE |
| 7 | A screen on camera is the single most reliable visual finding: `screen_share` vs `share_rate` rho +0.203, creator-normalised +0.129–0.285 across two related tests. | RELIABLE |
| 8 | Split screen — the niche's most common opening (73/266) — is also its weakest visual pattern: median robust_z 1.03 vs 1.43 (p=0.044). | PROBABLE |
| 9 | Comment-keyword gates (59% of the corpus) inflate comment rate 23×, save rate 2.8×, share rate 1.8× and move reach not at all (p=0.58–0.63) — a live contamination risk for M2's own reference selection. | RELIABLE |
| 10 | Naming specific tools/numbers (`lex_entities_distinct`, specificity) is the one lexical family that predicts reach and survives creator normalisation (+0.16–0.21). | PROBABLE |

Ten reviewed shooting cards exist as an editorial deliverable — see the card book; they are not
re-described here. Separately, main's operational `cards` table holds 23 real, reel-referenced
cards (20 distinct reels) built by the legacy pipeline across three weekly runs.

## Limitations

Every structural finding above rests on 8.3% of the ingested corpus, and that 8.3% is not a random
sample — it is whatever `deep.py` processed after `score.py` had already ranked it near the top of
its creator's history, so every "weak" comparison group is the least-strong end of a pre-selected
strong set, and absent contrasts are not evidence a feature is irrelevant. The legacy cut-count
metric (`ffmpeg select='gt(scene,0.35)'`) is a scene-score threshold, not a shot-boundary detector,
and must never be quoted as a real edit count. Saves are missing on 9–10% of rows by HikerAPI's own
behaviour, not by design. The `followers` table is empty, so no claim about creator growth or our
own publishing performance is possible. Two disagreeing corpus-tier vocabularies coexist by
design (`video_state.corpus_tier` vs `engine.corpus.tiers()`) and must never be mixed in one
report. As of the final build the `runs`/`jobs` state-tracing tables hold 7 runs and 265 jobs
(analysis 5, cards 2): the analysis ingest and the ten-card finalisation were traced end to end,
while the weekly collection run and the watchdog have not yet executed on the server under the new
schema — their traces will appear after the first scheduled run. Nothing in the
analysis licenses a causal claim; everything is associational, computed over a top-of-ranking
selection.

## Next steps

The immediate backlog is 1,312 of the 1,535 newest-snapshot codes (410 first seen there) with
neither transcript nor frames — reprocessing them requires a fresh HikerAPI call because their CDN
links have expired; `engine.watchdog` is built for this but has not yet run against the live
corpus. Phase 3 (production: binding supplied MP4 takes into an EDL and rendering) is verified
end-to-end on one example card but has no scheduled cron step — every render today is
operator-initiated. Outstanding before the next data-based decision: resolve the two corpus-tier
vocabularies for reporting, decide whether to hold `cta_type` constant in reference selection (the
comment-gate contamination in finding 9), and export Max's ~1,062 transcripts and ~19,808 frames
from his branch through a receipt format so they can be reconciled into this database.

![Corpus coverage funnel](reports/charts/corpus_coverage_funnel.png)

The funnel above traces the same 3,211 → 297 → 268 narrowing that grounds every finding in this
summary — read as a warning about denominators, not as a pipeline diagram.

> **Addendum (2026-09-12, after the report was compiled).** The scheduled semantic-analysis stage
> (`engine/analyze_pending.py`) found 8 archive transcripts without a ta-v1 analysis and they were
> analysed and ingested after the chapters of this report were written: ta-v1 files 266 → 274,
> codes with beats 264 → 270 (two of the eight are music-only, no beats). Two of the eight belong to
> reels in the corpus (`DRXZJeHiAES`, `Db5sXEAP6C4`); six are archive reels with no `reels` row and
> stay outside every denominator. Numbers quoted in the chapters reflect the state at compilation
> (266 analysed / 264 with beats); `reports/data/*` and `reports/charts/*` were regenerated after
> the addition and may differ from the chapter text by these few codes.
