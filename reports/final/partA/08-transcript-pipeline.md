# 8. Transcript Pipeline

## Local faster-whisper as the default

Both the legacy path (`deep.py`) and the new engine path (`engine/local_pipeline.py`) run
`faster-whisper` model `small`, `device='cpu'`, `compute_type='int8'`, with `language='en'` forced
— the code comment explains that auto-detection is unreliable on the non-native English accents
that dominate this niche's creators — and `vad_filter=True` to gate out silent stretches before
transcription. No model download or credential is required; the provider registry confirms
`local-faster-whisper` as `DEFAULT`, `CONFIGURED` on this machine with no environment variable at
all. `asr_version` is versioned explicitly (`faster-whisper-small-int8-v1`), so bumping the
constant reopens every code for reprocessing without touching prior rows.

## The 273+8 legacy transcripts

The pre-migration corpus held **273** transcript rows produced by `deep.py` from real HikerAPI
collections. Migration step (e) additionally imported **8** transcripts from the August 2026
pre-database archive (`dataset/2026-08-niche-research/`, same `{lang, segments}` shape), bringing
the total to **281** transcript rows post-migration — verified identically in
`reports/migration-validation.json` and `data/migration_log.md`. Of the 273 `deep.py`-produced
rows, all 273 now carry `transcript_meta` provenance (`provider='local'`,
`model='faster-whisper/small'`, `asr_version='faster-whisper-small-int8-v1'`, `created_at` taken
from `deepdives.done_at` since both are written in the same pass); the 8 August rows are recorded
honestly as `provider='unknown'` rather than given a provenance that cannot be proven — the source
files record no model, provider or date.

## ASR damage patterns found by the analysts

Direct reading of the 266 usable ta-v1 transcript analyses surfaced concrete ASR mis-transcriptions
consistent with `faster-whisper small` on fast, jargon-heavy speech — for example "Claude"
rendered as "cloud" in several transcripts (`DVZGBgTk6zz`'s mechanism beat: *"click cloud code and
install it"*, referring to Claude Code). This class of error is exactly why
`engine.lexical`'s entity lexicon is hierarchy-aware and coverage-limited rather than treated as
ground truth, and why `lex_entities_distinct` — not a raw transcript string match — is the
quantity the analysis chapters correlate against performance. No systematic correction pass for
this error class exists yet; it is a named, observed limitation, not a solved one.

## The 2 music-only reels and `EMPTY_NO_SPEECH`

Seven transcript rows (out of 275, pre-August-archive) carry `words = 0` and `segments = []`:
Whisper with `vad_filter=True` found no usable speech. These are music-only or text-on-screen
reels, not processing failures, and `video_state.transcript_state = EMPTY_NO_SPEECH` records them
as such rather than as `FAILED`. Two of the eight-code August-archive set have no `reels` row at
all and so contribute nothing to any tier count; the seven empty-transcript codes from the main
corpus form their own `TRANSCRIPT_UNUSABLE` tier under `engine.corpus.tiers()` rather than being
silently folded into `FRAMES_ONLY` (chapter 10 explains why the two corpus-tier vocabularies
disagree on exactly this point). One of these seven, `DcxV37-CJOC`, is doubly damaged: its
transcript captured five words of a 62-second reel *and* its frame extraction failed after the
first file (chapter 9) — it is kept in every table rather than dropped, exactly per the standing
rule against inventing or deleting data.

## The new video-by-video contract and watchdog

`engine/local_pipeline.py`'s `process_video(con, code, media_url_or_path, run_id, *, asr_version,
frames_version)` is idempotent and retryable (3 tries per step): skip if already `DONE` for the
same version pair → download (curl, sha256 recorded) → transcribe → ffmpeg scene-cut detection and
keyframe extraction → alignment → delete the mp4 unless `--keep-video` (no call site passes it) →
`refresh_video_state`. Each step writes one `jobs` row in the contract (chapter 6 notes this table
is currently empty in the live database — the contract is unit-tested, not yet observed against a
real run).

`engine/watchdog.py` is the Phase 2 catch-up worker: it selects codes where `analysis_ready=0` and
a signed CDN URL is still resolvable from an already-cached `cache/**/*clips*.json` file — it never
calls Hiker again, because the signed URL's lifetime is hours, not days (chapter 7's provenance
chain is what makes "still resolvable" checkable at all). Guarantees verified by reading the
module directly: idempotent (`process_video`'s own version-aware skip), rate-limited
(`RATE_SLEEP_S` between codes), safe against duplicate workers (`data/watchdog.lock`, pid +
timestamp, stale after 3 hours), and version-aware (bumping `asr_version` or `frames_version`
reopens eligibility for every code). It has not yet run against the live backlog of 1,312
unprocessed newest-snapshot codes (chapter 10) — it is built and tested (22 cases in
`tests/test_local_pipeline.py`, one marked `slow` and skipped by default) but not yet executed as
a scheduled cron step; `cron.sh` calls it with a 3,600-second timeout and a `|| echo` guard so its
failure never blocks the older 13-step chain, but that guard has not yet been exercised in
production either.
