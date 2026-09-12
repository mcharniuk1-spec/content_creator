# M2Radar — database reconciliation

**Version 1, 2026-09-11.** Owner: schema/state (`engine/schema.py`, `engine/state.py`,
`engine/migrate_legacy.py`, `engine/db_util.py`).

This document is the map between the three places M2Radar data has lived — main's SQLite
database, Max's `Latest` branch (the `m2_signal` ledger and the Notion field dictionary), and
the August 2026 pre-database archive — and the one canonical store the engine now uses.

Sources: `engine/SPEC.md` (binding), `reports/audit/01-branch-comparison.md` §4,
`reports/audit/02-data-inventory.md` §13–§14, `db.py`, `docs/m2-field-dictionary.csv`,
and the migration actually executed against `data/radar.db` on 2026-09-11
(`data/migration_log.md`, `reports/migration-validation.json`).

---

## 0. The rule

**Canonical store = main's SQLite `data/radar.db`.** Nothing in the 15 legacy tables was
renamed, retyped or dropped. `engine/schema.py` adds 17 new tables and five guarded columns
through a versioned, idempotent migration recorded in `schema_migrations`. Max's `Latest` is
adopted as *contracts and vocabulary*, never as a store — its `m2_signal` ledger costs 24 MB
per snapshot against 5.2 MB for main's entire history, and it discards main's frame evidence
on import (`legacy.py`, audit 01 §6.6.1).

### Disposition vocabulary

Every row below carries exactly one disposition.

| Disposition | Meaning |
|---|---|
| **MIGRATED** | The value already lived in main's schema and was carried over unchanged. |
| **RENAMED** | Same value, different column name in the canonical store. |
| **TRANSFORMED** | Value recomputed or reshaped on the way in (parsed, aggregated, re-typed). |
| **NEW DERIVED** | Did not exist in any source; computed by the engine from what does exist. |
| **PRESERVED RAW** | Kept verbatim in a `*_json` / free-text column so a later, better parser can revisit it. |
| **DEPRECATED** | Exists in a source, deliberately not carried into the canonical store. |
| **NOT ADOPTED** | Exists only in `Latest`; the concept was considered and rejected for now. |

---

## 1. Creator / account

Main is canonical here without qualification: `Latest` has no roster lifecycle at all.

| Attribute | main | Latest (`m2_signal` / field dictionary) | Canonical | Disposition | Note |
|---|---|---|---|---|---|
| creator id | `accounts.pk` | `account_analysis.account` / `Name` | `accounts.pk` | MIGRATED | Integer Instagram pk. Also `reels.pk_user`. |
| handle | `accounts.username` | `accounts.csv` username | `accounts.username` | MIGRATED | `UNIQUE`. |
| display name | `accounts.full_name` | — | `accounts.full_name` | MIGRATED | |
| followers (current) | `accounts.follower_count` | `Followers at export` | `accounts.follower_count` | MIGRATED | NULL for 918 of 1 357 — the candidate pool was never profiled. |
| followers (time series) | `followers(pk, at, follower_count)` | — (`profile_horizon_state: CURRENT_DB_NOT_HISTORICAL_SNAPSHOT`) | `followers` | MIGRATED | **0 rows.** "Who is growing" is unanswerable from this database. |
| followers at post time | `reels.followers` | — | `reels.followers` | MIGRATED | Per snapshot; the only historical follower signal that exists. |
| following / media count | `accounts.following_count`, `media_count` | `accounts.csv` | same | MIGRATED | |
| bio, category | `accounts.biography`, `accounts.category` | imported by Latest | same | MIGRATED | Bio on 365, category on 182. |
| verified / private | `accounts.is_verified`, `is_private` | — | same | MIGRATED | |
| roster tag | `accounts.tag` | **none** | `accounts.tag` | MIGRATED | Vocabulary drift — see §11. |
| roster status | `accounts.status` | **none** | `accounts.status` | MIGRATED | Vocabulary drift — see §11. |
| liveness misses | `accounts.misses`, `checked_snapshot`, `last_checked` | **none** | same | MIGRATED | 2 misses = dropped. |
| exclusion reason | `accounts.why_out` | **none** | `accounts.why_out` | MIGRATED | Filled on all 307 excluded accounts. |
| provenance | `accounts.via` | **none** | `accounts.via` | MIGRATED | 948 rows, all `сосед: <username>`. |
| dropped date | `accounts.dropped_at` | **none** | same | MIGRATED | |
| per-creator rollup | **none** | `account_analysis` (129 rows), `Median views`, `Baseline n`, `Hit fraction`, `Wilson lower/upper`, `Hit state` | `creator_stats` (SPEC §2.7) | NEW DERIVED | New table: median/mean/MAD/IQR/SD/CV of play, rate medians, `posts_per_week`, `outlier_share`, `consistency_score`, `reliability`. Keyed `(pk, snapshot_id)` so history is kept — Latest's is single-release. |
| account cluster | — | `account_cluster_id` | — | NOT ADOPTED | No clustering step exists yet. |

---

## 2. Video / reel

| Attribute | main | Latest | Canonical | Disposition | Note |
|---|---|---|---|---|---|
| video id | `reels.code` | `observations.reel_id` / `Name` | `reels.code` | MIGRATED | Instagram shortcode; the join key everywhere (`frames`, `transcripts`, `topics`, `deepdives`, `video_state`, `beats`, `scenes`). Validated by `db.safe_code`. |
| snapshot | `reels.snapshot_id` → `snapshots.taken` | `releases` + `Release` / `Snapshot` | unchanged | MIGRATED | Main keys on date, Latest on content hash. Not adopted — see §10. |
| creator | `reels.pk_user`, `reels.username` | `observations.account` | unchanged | MIGRATED | Both kept; one code disagrees across snapshots (§8, `UNRESOLVED_CREATOR_ID`). |
| published at | `reels.ts` (unix) | `Published UTC` | `reels.ts` | MIGRATED | Latest's snapshot dates are *capture* dates, not post ages (audit 01 §6.6.8). |
| media type | `reels.kind` | — (dropped by Latest) | `reels.kind` | MIGRATED | |
| caption | `reels.cap` | `caption_sha256` only | `reels.cap` | MIGRATED | Latest stores only the hash. Main keeps the text — needed for the duplicate-caption check. |
| views | `reels.play` | `observations.views` / `Views` | `reels.play` | MIGRATED | |
| likes / comments / shares / saves | `reels.likes`, `comm`, `resh`, `save` | `Likes`, `Comments`, `Reshares`, `Saves` | unchanged | MIGRATED | `save` NULL on 486 of 5 147 rows — missing, never zero. |
| duration | `reels.dur` | `media_duration_seconds` / `Seconds` | `reels.dur` | MIGRATED | |
| rates per 1k | `scores.resh_1k`, `save_1k`, `comm_1k` | `Likes/Comments/Reshares/Saves per 1k views` | `video_features.like_rate` … `save_rate` | TRANSFORMED | Recomputed with a denominator guard (`play ≥ 100`, else NULL) per SPEC §7. `scores` keeps its own values untouched. |
| score | `scores.z`, `c_*`, `eligible`, `author_median_play`, `baseline_n`, `baseline_snaps`, `axes`, `weights` | `reel_metric_values`, `Diagnostic z`, `Components`, `Baseline n`, `View index` | `scores` unchanged | MIGRATED | **`weights` and `baseline_snaps` have no Latest equivalent** — main's `ig` vs `max` comparison and its cross-snapshot baseline cannot be expressed there. Do not port `scores` into Signal. |
| topic labels | `topics(code, topic, source)` | `topic_codes`, `topic_state` | `topics` unchanged; canonical topic also lands in `video_features.topic` | MIGRATED | `topics.source` (`manual` vs `sample`) is **lost in Latest** and kept here. |
| fetch provenance | **none** | `sources`, `release_observations` (row-level back-pointer) | `reels.fetch_id` → `fetch_log` | NEW DERIVED | Column added by migration v2; `fetch_log` is created and empty until the hiker owner fills it. |
| quarantine flag | — | `Quarantine`, `quarantined` | `video_state.flags_json` | TRANSFORMED | Expressed as explicit flags (§8) rather than one boolean. |

---

## 3. Transcript

This is the one place where `Latest`'s model is materially richer than main's, and it is the
model adopted. Main's `transcripts` table records no provenance whatsoever: no model id, no
media hash, no language probability.

| Attribute | main | Latest | Canonical | Disposition | Note |
|---|---|---|---|---|---|
| transcript id | `transcripts.code` | `transcript_evidence_id` | `transcripts.code` | MIGRATED | One transcript per video. |
| full text | `transcripts.text` | evidence artifact | `transcripts.text` | MIGRATED | |
| timed segments | `transcripts.segments` (JSON `[{s,e,t}]`) | evidence artifact | `transcripts.segments` | PRESERVED RAW | Left exactly as `deep.py` wrote it; `beats.segment_idx_json` indexes into it. |
| language | `transcripts.lang` | `asr_language` | `transcript_meta.language` | RENAMED | Always `en` — `deep.py` forces it. |
| language probability | **none** | `asr_language_probability` | `transcript_meta.lang_probability` | NEW DERIVED | NULL for the whole legacy corpus; `deep.py` never captured it. Honest NULL, not a guess. |
| provider | **none** | implicit | `transcript_meta.provider` | NEW DERIVED | `local` for 273 rows, `unknown` for the 8 August rows. |
| model | **none** | model-hash manifest | `transcript_meta.model` | NEW DERIVED | `faster-whisper/small`; `note` records `device=cpu, compute_type=int8, language=en, vad_filter=True`. |
| ASR version | **none** | — | `transcript_meta.asr_version` | NEW DERIVED | `faster-whisper-small-int8-v1` (SPEC §1). NULL where unprovable. |
| source media hash | **none** | `media_observed_sha256`, `media_corpus_expected_sha256` | `transcript_meta.media_sha256` | NEW DERIVED | NULL everywhere: the mp4s were deleted by design (SPEC §4.4) and cannot be rehashed. |
| word count | `transcripts.words` | `transcript_word_count_lexical`, `Legacy ASR reported words` | `transcript_meta.words` | TRANSFORMED | Recomputed from the segment text. It agreed with `transcripts.words` on all 273 rows. |
| token count | **none** | — | `transcript_meta.tokens` | NEW DERIVED | `round(words × 1.3)` (SPEC §6.3). An estimate, labelled as one. |
| character count | **none** | — | `transcript_meta.chars` | NEW DERIVED | `len(text)`. |
| speech seconds | **none** | — | `transcript_meta.speech_seconds` | NEW DERIVED | `Σ(e − s)` over segments. Speech time, **not** video duration. |
| words per second | **none** | `transcript_words_per_second`, `transcript_aligned_words_per_second` | `transcript_meta.words_per_second` | NEW DERIVED | `words / speech_seconds`. NULL when there is no speech. |
| segment count | **none** | — | `transcript_meta.segments_n` | NEW DERIVED | |
| created at | **none** (implicit) | evidence timestamp | `transcript_meta.created_at` | TRANSFORMED | Taken from `deepdives.done_at`: `deep.py` writes the transcript and the deep dive in the same pass. |
| rate comparability | — | `transcript_rate_comparability` | `video_state.transcript_state` + flags | TRANSFORMED | Expressed as `DONE / EMPTY_NO_SPEECH / FAILED / MISSING` plus `UNALIGNED_TRANSCRIPT`. |
| artifact verified | — | `transcript_artifact_verified`, `transcript_source_identity_state` | — | NOT ADOPTED | Requires the media hash chain, which no longer exists for the legacy corpus. |

---

## 4. Segments and beats (semantic chapters)

| Attribute | main | Latest | Canonical | Disposition | Note |
|---|---|---|---|---|---|
| raw segment | `transcripts.segments[i]` = `{s, e, t}` | evidence artifact | unchanged | PRESERVED RAW | The ASR output. Never edited. |
| beat id | **none** | — | `beats.beat_id` | NEW DERIVED | |
| beat ↔ segments | **none** | — | `beats.segment_idx_json` | NEW DERIVED | Indices into `transcripts.segments`, so a beat can always be traced to the exact words. |
| semantic role | **none** | `structural_label_state` (state only, no labels) | `beats.role` | NEW DERIVED | Closed vocabulary, SPEC §2.4: `hook, hook_extension, setup, context, audience, problem, pain, tension, explanation, mechanism, solution, proof, example, objection, transformation, payoff, cta, closing, rehook, other`. |
| timing, share of speech | **none** | — | `beats.start_s`, `end_s`, `duration_s`, `share_of_speech` | NEW DERIVED | |
| words / sentences | **none** | — | `beats.words`, `beats.sentences` | NEW DERIVED | |
| audience function, emotion, intention, persuasion | **none** | — | `beats.audience_function`, `emotion`, `intention`, `persuasion` | NEW DERIVED | From `ta-v1` LLM analysis. |
| key phrases | **none** | — | `beats.key_phrases_json` | PRESERVED RAW | |
| beat ↔ scene | **none** | — | `beats.scene_ids_json`, `frame_idx_json`, `visual_state` | NEW DERIVED | Filled by alignment. **Empty today** — 681 beats over 116 codes, none aligned yet. |
| analysis version | **none** | `formula_version` | `beats.analysis_version` | NEW DERIVED | `ta-v1`. |
| full LLM output | **none** | — | `data/analysis/transcripts/<code>.json` | PRESERVED RAW | The whole `ta-v1` document, file per code (SPEC §5). |

---

## 5. Frames and scenes

`Latest` is richer per frame (SHA-256, decoded index, PTS) but **refuses to import main's
existing frames** — `legacy.py` reports `frames coverage 0%` for a corpus that already holds
2 653 files. Main's rows stay canonical; Latest's *mechanics* are the upgrade path.

| Attribute | main | Latest | Canonical | Disposition | Note |
|---|---|---|---|---|---|
| frame id | `frames(code, idx)` | `evidence_attempts(modality='frames')` | unchanged | MIGRATED | |
| timestamp | `frames.t_sec` | decoded index + PTS | `frames.t_sec` | MIGRATED | Legacy sampling: 0.4 / 1.2 / 2.4 / 4.0 s plus `dur·k/6` (`deep.py:timecodes`). |
| file path | `frames.path` | artifact store | `frames.path` | MIGRATED | Repo-relative. 8 rows point at files that do not exist (§8). |
| file hash | **none** | frame SHA-256 | `frames.sha256` | NEW DERIVED | Added by migration v2, computed from disk. 2 645 of 2 653 legacy rows hashed. |
| file present | **none** | `frames_artifact_verified` | `frames.exists_ok` | NEW DERIVED | 1 / 0. Drives `BROKEN_FRAME_REFERENCE` and `frames_state = PARTIAL`. |
| frames requested vs kept | **none** | `frame_requested_count`, `frame_budget_max`, `frame_sampling_truncated` | — | NOT ADOPTED | No budgeting layer yet; `engine/process_budget.py` is the port that would carry it. |
| contact sheet | `deepdives.sheet` | — | unchanged | MIGRATED | All 282 sheets present on disk. |
| cut count | `deepdives.cuts`, `cuts_ps` | `cut_count`, `cut_candidate_count`, `cut_observation_state` | unchanged; surfaced as `video_features.cuts`, `cuts_per_min` | MIGRATED | **This is a scene-score threshold count, not a verified cut count** — see §9. |
| evidence state | **none** | `cut_summary_state`, `frames_source_identity_state` | `deepdives.evidence_state` | NEW DERIVED | Set to `fixed9-v1` on all 282 rows: the frames are fixed samples, not detected scenes. |
| human fitness verdict | `deepdives.suitable`, `unfit_why` | **none** | unchanged | MIGRATED | Operationally central — `cards.py` filters on it. Latest has no field for it. |
| scene interval | **none** | `video-scene-segmentation.schema.json` | `scenes(scene_id, code, idx, start_s, end_s, duration_s)` | NEW DERIVED | New table. 169 rows today, all `boundary_reason='sampled'`, `frames_version='fixed9-v1'` — derived from the fixed samples, not from a detector. |
| scene type / transition | **none** | `scene_review_state`, `reviewed_scene_state` (states only) | `scenes.scene_type`, `scenes.transition_in` | NEW DERIVED | Closed taxonomies, SPEC §4. |
| detector evidence | **none** | — | `scenes.detector_json`, `scenes.frames_version` | PRESERVED RAW | `scene-v1` is reserved for the real detector; nothing carries it yet. |
| per-frame labels | **none** | — | `frame_labels` (`frame_type`, `roll`, `speaker_present`, `face_present`, `ui_present`, `text_overlay`, `overlay_text`, `caption_placement`, `framing`, `dominant_action`, `visual_density`, `is_visual_hook`, `is_cta_visual`, `is_proof_visual`) | NEW DERIVED | From `fa-v1`. 486 rows over 54 codes today. |
| raw label payload | **none** | — | `frame_labels.labels_json`, `data/analysis/frames/<code>.json` | PRESERVED RAW | |

---

## 6. Analytical features

| Attribute | main | Latest | Canonical | Disposition | Note |
|---|---|---|---|---|---|
| feature row | scattered across `scores`, `topics`, `deepdives` | `corpus_features.py`, `reel_analysis.payload` | `video_features` (one row per code) | NEW DERIVED | 73 columns plus `features_json`, SPEC §2.6. |
| content semantics | `topics.topic` only | `topic_codes` | `video_features.topic, subtopic, subject, audience, audience_stage, pain, desire, problem, solution_type, proof_type, hook_type, cta_type, narrative, positioning_type, funnel_role, tone, emotion_path` | NEW DERIVED | Closed vocabularies, SPEC §4. Free-text originals in `raw_labels_json`. |
| script construction | **none** | `structural_features.py` | `video_features.hook_text, hook_s, hook_words, setup_s … cta_s, total_s, total_words, wps, avg_sentence_len, info_density, specificity, numbers_n, questions_n` | NEW DERIVED | |
| visual construction | `deepdives.cuts`, `cuts_ps` | `cut_count` | `video_features.first_frame_type, hook_visual, a_roll_share … text_overlay_density, scenes_n, avg_scene_s, cuts, cuts_per_min, visual_sequence, visual_to_script_sync` | NEW DERIVED | Shares over the legacy corpus are **estimates from 9 samples**, marked by `cut_metric_quality`. |
| cut metric honesty | **none** | `cut_observation_state` | `video_features.cut_metric_quality` | NEW DERIVED | `ffmpeg_scene_0.35_count_only` \| `scene-v1` \| `unavailable`. Never present a sampled estimate as a measurement. |
| performance | `scores.*` | `reel_metric_values` | `video_features.play … creator_n` | TRANSFORMED | Rates, `view_lift`, `share_rate_lift`, `save_rate_lift`, `robust_z`, `percentile_in_creator`, `outlier_status`, `creator_consistency`. Same `robust_z` convention as `score.py`. |
| raw payload | — | `payload` blob | `video_features.features_json` | PRESERVED RAW | `NOT NULL` — the full computed record always survives. |
| eligibility gates | — | `comparability_gate`, `metric_eligibility_gate`, `model_gate`, `missingness_reasons`, `acquisition_state` | `video_state` states + flags | TRANSFORMED | One explicit state machine instead of five booleans. |
| `expected_rows=2352` default | — | `analysis_eligibility.py:70` | — | DEPRECATED | Hardcoded to the 2026-09-01 snapshot; fails closed on today's corpus. Do not port. |

---

## 7. Cards

| Attribute | main | Latest | Canonical | Disposition | Note |
|---|---|---|---|---|---|
| legacy card | `cards(id, week, code, fmt, pri, lead, why, angle, hook, shot_frame, shot_screen, shot_banner, caption, goal, status)` | `docs/m2-field-dictionary.csv` card scope (11 cols) + `examples/ten-card-*/M2-*.json` | `cards` unchanged | MIGRATED | 23 real, reel-referenced cards. Untouched by the migration. |
| status bridge | `cards.status` (`draft` / `взята` / `вычеркнута`) | `Status` | `cards.status_v2` | NEW DERIVED | Column added by migration v2, empty until `engine/cards_v2.py` fills it. The Russian vocabulary in `cards.status` is left as is — `check.py` and `cards.py` depend on it. |
| card v2 | **none** | the 10 example JSONs | `cards_v2`, `card_scenes`, `script_versions` + `cards/<card_id>.json` | NEW DERIVED | SPEC §2.9 / §8. |
| Latest's example cards | — | `examples/ten-card-20260907/*.json` | — | NOT ADOPTED | Every one carries `"synthesis": true` and `DESIGNED_NOT_MODEL_EXECUTED`: invented scripts, not derived from any reel in this corpus (audit 02 §14). They are process evidence, not data. |
| our own publishing | `our_posts`, `our_metrics` | **none** | unchanged | MIGRATED | Both empty. Nothing is known about our own performance. |

---

## 8. State (new layer)

Nothing in main corresponded to this; `Latest`'s `m2_orchestrator/state.py` is the model
adopted, trimmed from 41 stages to the 25 in SPEC §3.

| Attribute | main | Latest | Canonical | Disposition |
|---|---|---|---|---|
| run | `runs/` log files | `releases`, `events` in `state.sqlite` | `runs(run_id, started_at, finished_at, kind, git_commit, host, config_json, summary_json, status)` | NEW DERIVED |
| job | **none** | orchestrator job records | `jobs` — 23 columns incl. `parent_job_id`, `previous_state`, `duration_s`, `agent`, `provider`, `model`, `prompt_version`, `knowledge_version`, `input_refs_json`, `output_refs_json`, `retries`, `error`, `validation`, `cost_json` | NEW DERIVED |
| per-video state | **none** | `evidence_attempts` + a dozen `*_state` fields | `video_state` (22 columns) | NEW DERIVED |
| corpus tier | implicit | `comparability_gate` | `video_state.corpus_tier` | NEW DERIVED |
| damage flags | audit prose | `missingness_reasons` | `video_state.flags_json` | NEW DERIVED |
| human observations | `tool_log` | `events` (machine) | `tool_log` unchanged | MIGRATED |
| spend history | `spend` | `reserved_cost_upper_bound_usd`, `actual_provider_charge_usd` | `spend` unchanged; forward reservation → `fetch_log.units`, `price` | MIGRATED |
| provider registry | **none** | `m2_studio/providers.py`, `provider-catalog.json` | `providers` | NEW DERIVED |

### Flag definitions as implemented

`video_state.flags_json` is a sorted JSON array, **one entry per code**. Audit §13 counts
some of these per *row*; both numbers are reported.

| Flag | Rule in `engine/state.py` | Codes | Audit §13 |
|---|---|---:|---|
| `MISSING_STATS` | `play` NULL or 0 in every snapshot row, or no `reels` row | 1 | 1 code |
| `MISSING_MEDIA` | a `deepdives` row exists and either no `frames` rows or ≥ half the files are gone | 1 | 1 code |
| `MISSING_TRANSCRIPT` | no `transcripts` row | 2 936 | 2 938 codes (before the August import) |
| `MISSING_FRAMES` | no `frames` rows | 2 914 | 2 916 codes (before the August import) |
| `BROKEN_FRAME_REFERENCE` | any `frames.exists_ok = 0` | 1 | 8 **rows**, all in `DcxV37-CJOC` |
| `UNALIGNED_TRANSCRIPT` | `transcripts` row whose `segments` is empty or unparseable | 7 | 7 rows |
| `DUPLICATE_VIDEO` | same `pk_user` and byte-identical caption over 30 chars under another code | 56 | 0 by the strict `pk+ts+dur` rule; 56 by the caption rule |
| `STALE_METRICS` | not present in the newest completed snapshot | 1 676 | 1 676 |
| `UNRESOLVED_CREATOR_ID` | more than one `(pk_user, username)` pair across snapshots | 1 | 1 (`DcFm9i5s5q8`) |

---

## 9. Column validation for the key analytical fields

Per SPEC §67. "Current" = collected by today's pipeline. "Legacy" = present only for codes
collected before the engine existed.

| Field | Source of truth | Nullable | Validation rule | Current / legacy |
|---|---|---|---|---|
| views | `reels.play` | yes | Integer ≥ 0. NULL or 0 in every snapshot row → `MISSING_STATS`. Never coerce NULL to 0. | both |
| likes | `reels.likes` | yes | Integer ≥ 0. | both |
| comments | `reels.comm` | yes | Integer ≥ 0. | both |
| shares | `reels.resh` | yes | Integer ≥ 0. Hiker does not always return it. | both |
| saves | `reels.save` | **yes, and materially** | Integer ≥ 0. NULL on 486 of 5 147 rows / 226 codes. **Treat as missing, never as zero**; a saves-per-1k built without missingness handling is wrong. | both |
| engagement rates | `video_features.like_rate`, `comment_rate`, `share_rate`, `save_rate` | yes | Computed only when `play ≥ 100`, else NULL (SPEC §7). Denominator is `play` in the same snapshot row. | current |
| duration | `reels.dur` | yes | Seconds, REAL > 0. Rows with `dur ≤ 0` are excluded from deep dive selection (`deep.py:pick`). | both |
| followers (creator, now) | `accounts.follower_count` | yes | Integer ≥ 0. NULL for 918 unprofiled candidates. Not a historical value. | both |
| followers (at post time) | `reels.followers` | yes | Integer ≥ 0, per snapshot. Use this, not `accounts`, for any per-post normalisation. | both |
| posting date | `reels.ts` | yes | Unix seconds. **Post age**, distinct from `snapshots.taken` (capture date). Latest conflates the two. | both |
| transcript text | `transcripts.text` | no (may be `''`) | Empty string + `words = 0` is a legitimate result (`EMPTY_NO_SPEECH`, 7 codes), not a failure. | both |
| transcript timing | `transcripts.segments` | yes | JSON array of `{s, e, t}` with `e ≥ s`. Empty array → `UNALIGNED_TRANSCRIPT`. `words > 0` with empty segments → `transcript_state = FAILED`. | both |
| transcript word count | `transcript_meta.words` | yes | Recomputed from segment text; must equal `transcripts.words` (it does, on all 273 legacy rows). | current |
| words per second | `transcript_meta.words_per_second` | yes | `words / speech_seconds`, where speech_seconds = `Σ(e − s)`. NULL when there is no speech. **Not** words / video duration. | current |
| ASR provenance | `transcript_meta.provider`, `model`, `asr_version` | yes | `local` + `faster-whisper/small` + `faster-whisper-small-int8-v1` only where a `deepdives` row proves `deep.py` produced it. Otherwise `unknown` / NULL. | current for 273, unknown for 8 |
| frames | `frames(code, idx, t_sec, path)` | `t_sec` yes | `path` must resolve to a file; `exists_ok` records the answer, `sha256` the content. 2 719 of 2 727 present. | both |
| frame timing | `frames.t_sec` | yes | Seconds from video start. NULL only for frames imported from base64 with no timing information. | both |
| scene ids | `scenes.scene_id` (+ `beats.scene_ids_json`) | `scene_ids_json` yes | `frames_version` must say how the scene was obtained: `sampled` (from the 9 fixed frames) or `detector` (`scene-v1`). Never present a sampled interval as a detected scene. | legacy sampled only today |
| hook | `video_features.hook_type`, `hook_text`, `hook_s`, `hook_words` | yes | `hook_type` from the closed list in SPEC §4; `hook_text` must be a verbatim span of `transcripts.text`. | current |
| topic | `topics.topic` → `video_features.topic` | yes | One of `topics.py`'s 27 labels. `topics.source` must be `manual` or `sample` — never NULL (`check.py` enforces it). | both |
| pain | `video_features.pain` (+ `raw_labels_json.pain_raw`) | yes | Closed list of 13 values, SPEC §4. Free text preserved separately. | current |
| solution | `video_features.solution_type` | yes | Closed list of 10 values. | current |
| CTA | `video_features.cta_type` | yes | Closed list of 9 values including `none`. `none` is a finding, not a gap. | current |
| word counts | `transcript_meta.words`, `beats.words`, `video_features.total_words` | yes | Must reconcile: `Σ beats.words ≤ transcript_meta.words` (beats may skip filler). | current |
| cut counts | `deepdives.cuts`, `cuts_ps` → `video_features.cuts`, `cuts_per_min` | yes | **Threshold count, not a verified cut count**: `ffmpeg select='gt(scene,0.35)'` on an mp4 that no longer exists. `cut_metric_quality` must say `ffmpeg_scene_0.35_count_only`. 38 deep dives report `cuts = 0`, and whether that is a single take or a failed detection cannot be re-derived. | legacy |
| scene counts | `video_features.scenes_n`, `avg_scene_s` | yes | Only meaningful with `frames_version='scene-v1'`. For the legacy corpus the value is derived from 9 samples and must be labelled an estimate. | legacy estimate today |

---

## 10. What was deliberately not adopted from `Latest`

| Item | Why |
|---|---|
| `m2_signal/schema.sql` as the store | 24 MB per snapshot vs 5.2 MB for main's entire history; and `legacy.py` discards main's 2 653 frames and 282 deep dives on import. |
| Content-addressed releases (`corpus_sha256`, `config_sha256`, `implementation_sha256`) | Good hygiene, but it forbids re-running a day whose bytes changed, and main's snapshots are append-only already. Revisit when a second consumer needs reproducibility guarantees. |
| The 41-stage DAG | 29 stages have no implementation. Trimmed to the 25 in SPEC §3. |
| Latest's scoring | No age bands, focal row left in its own baseline, single-release only. Main's `score.py` / `baseline.py` are stronger. |
| `analysis_eligibility.load_feature_rows(expected_rows=2352)` | Hardcoded to the 2026-09-01 snapshot; fails closed on the current corpus. |
| `media_ocr.py` / `m2_vision_ocr.swift` | Apple Vision, macOS only — dead on the server. |
| `requirements-m2-media.txt` | Pins newer versions than the working ASR stack here, including a Pillow downgrade. Installing it wholesale would disturb a pipeline that ships. |

Adopted as contracts: `schemas/video-scene-segmentation.schema.json`, `studio/remotion/`,
`m2_orchestrator/process_budget.py`, `m2_studio/provider-catalog.json`,
`docs/m2-field-dictionary.csv` (65 documented Notion columns, including null semantics and
permissible inference — main had no data dictionary at all).

---

## 11. Vocabulary drift in `accounts.tag` / `accounts.status`

Found by the data inventory (audit 02 §2) and **not fixed by this migration** — changing
either column would move rows underneath `check.py`, `roster.py` and `judge_accounts.py`,
which is not a schema decision to take alone.

`db.py` documents:

* `accounts.tag` — `core / neighbor / out`
* `accounts.status` — `active / dropped / candidate`

The live data uses:

| tag | status | rows | documented? |
|---|---|---:|---|
| `core` | `active` | 130 | yes |
| `out` | `out` | 234 | **`status='out'` is undocumented** |
| NULL | `candidate` | 920 | tag NULL is undocumented |
| NULL | `rejected` | 73 | **`status='rejected'` is undocumented** |

So: `neighbor` and `dropped` are documented but unused; `out` and `rejected` are used but
undocumented; and `tag` is NULL for 993 of 1 357 rows. Anyone writing
`WHERE status = 'dropped'` from the schema comment gets zero rows and no error. `check.py`
already half-acknowledges this — it tests `status IN ('out','rejected')` for `why_out`, a
vocabulary the schema comment does not contain.

Recommended (needs the roster owner and Misha): document `out` and `rejected`, drop
`neighbor` and `dropped` from the comment or start using them, and decide whether `tag`
should be `NOT NULL DEFAULT 'candidate'`. Until then, treat the schema comment in `db.py` as
stale and this table as the real vocabulary.

---

## 12. Migration results — executed 2026-09-11 against `data/radar.db`

Command: `python3 -m engine.migrate_legacy --db data/radar.db`.
Full record: `data/migration_log.md`, `reports/migration-validation.json`.

### Row counts, before → after

| Table | Before | After | Δ |
|---|---:|---:|---:|
| `transcripts` | 273 | 281 | +8 |
| `transcript_meta` | 0 | 281 | +281 |
| `frames` | 2 653 | 2 727 | +74 |
| `video_state` | 135 | 3 211 | +3 076 |
| `providers` | 0 | 9 | +9 |
| `schema_migrations` | 0 | 2 | +2 |

Untouched: `accounts` 1 357, `snapshots` 3, `reels` 5 147, `scores` 7 477, `topics` 2 482,
`deepdives` 282, `cards` 23, `tool_log` 37, `spend` 10, `our_posts` 0, `our_metrics` 0,
`followers` 0.

**On the 135 pre-existing `video_state` rows.** Other Wave-2 owners are writing to the same
`data/radar.db` while this migration runs; they had already imported `engine.schema` and
called `refresh_video_state` on part of the corpus. The same applies to `beats` (681 rows,
116 codes), `scenes` (169, 53 codes), `frame_labels` (486, 54 codes), `video_features`
(3 211) and `creator_stats` (132): those tables are created by this migration but populated
by their owners, not by it. Re-run
`python3 -m engine.migrate_legacy --db data/radar.db` once every owner has finished to get a
consistent final set of numbers.

### Identity counts after migration

| What | n |
|---|---:|
| accounts | 1 357 (130 active) |
| creators with at least one reel | 132 |
| unique video codes | 3 211 |
| video readings (code × snapshot) | 5 147 |
| transcripts | 281 |
| transcripts usable (`words > 0`, timed segments) | 274 |
| transcript_meta rows | 281 |
| frame rows / frame codes | 2 727 / 303 |
| deep dives | 282 |
| cards | 23 |
| video_state rows | 3 211 |

### Step results

| Step | Result |
|---|---|
| a — schema | migrations 1 and 2 applied; 18 tables (17 new + the `schema_migrations` ledger) and 5 guarded columns |
| b — `transcript_meta` | 273 rows written with local faster-whisper provenance; word count matched `transcripts.words` on all 273 |
| c — frames on disk | 2 653 rows checked: **2 645 present** (sha256 computed), **8 broken**, all in `DcxV37-CJOC` |
| d — `deepdives.evidence_state` | `fixed9-v1` on all 282 rows |
| e — August 2026 archive | **8 transcripts and 74 frames over 8 codes imported**, none previously in the database; 0 base64 fallbacks needed; **6 codes UNRESOLVED** |
| f — `video_state` | 3 211 rows, one per distinct code in `reels` |
| g — `providers` | 9 rows; state from env-var presence only, no value read or stored |
| h — validation | `integrity_check` = `ok`, **0 foreign-key violations**, 0 orphaned scores / cards / metrics / topics, 0 PK duplicates |

### Corpus tiers

| Tier | Codes |
|---|---:|
| `ANALYSIS_READY` | 268 |
| `FRAMES_ONLY` | 29 |
| `INGESTED_NOT_ANALYZED` | 2 914 |

Two divergences from SPEC §0.4's illustrative counts, both deliberate:

* **268, not 266.** The two August codes that do have a `reels` row —
  `DRXZJeHiAES` and `Db5sXEAP6C4` — now have both a transcript and frames.
* **29, not 22.** SPEC's 22 counts codes with frames and *no transcripts row*. Seven more
  have frames plus a transcript row with `words = 0` (`EMPTY_NO_SPEECH`): visuals, no usable
  script, which is what "frames-only" means. Calling them `INGESTED_NOT_ANALYZED` would hide
  29 frame sets from the visual corpus. Flagged for the orchestrator in
  `engine/HANDOFF_NOTES.md`.

### The August 2026 archive — the one genuine gap, now closed

`dataset/2026-08-niche-research/` holds the first niche pass, made before the database
existed and never migrated. Manifests are in `dataset/`; the jpgs they name live in
`data/server-mirror/archive/2026-08-niche-research/frames/`.

* 8 transcripts (`{lang, segments}`, the same `{s,e,t}` shape) → `transcripts` +
  `transcript_meta` with `provider = 'unknown'` and
  `note = 'aug-2026-archive, provider unverified'`. The files record no model, no provider
  and no date, so none is claimed.
* 74 jpgs → `data/frames/<code>/legacy_NN.jpg`, rows in `frames` with `sha256` and
  `exists_ok = 1`. `video_state.frames_version` resolves to `aug2026` from the path.
* **`t_sec` was recovered.** The source filenames (`<code>_0004.jpg`) encode *deciseconds*,
  not frame numbers: `0004 / 0012 / 0024` are `deep.py`'s 0.4 / 1.2 / 2.4 s hook samples, and
  the remaining seven sit at `dur·k/8`. Verified against the durations in the archive's own
  `reels_pool.json` — e.g. `DU9OIJUCBQz`, pool duration 126.47 s, frames at 15.8 / 31.6 /
  47.4 / 63.2 / 79.1 / 94.9 / 110.7 s = `126.47·k/8`.
* `frames_b64.json` (7 codes × 6 frames) was **not** used: every frame it holds also exists
  as a jpg. It remains the fallback path in the importer.

**6 of the 8 codes have no `reels` row** and are logged as UNRESOLVED in
`data/migration_log.md`: `DT0fJmxjVnI`, `DU9OIJUCBQz`, `DZw4aTtzJpg`, `Db9AEm5upfu`,
`DbOUP9OPDAQ`, `DcdbJKmxZ5o`. Their transcripts and frames are kept. **No `reels` row was
invented for them** — they have no metrics, no author and no `video_state` row, and they are
excluded from every denominator until a paid HikerAPI lookup resolves them. This is the only
reason `transcripts_without_reel` and `frame_codes_without_reel` report 6 rather than 0.

### Damage carried forward, unchanged

`check.py` reports the same single discrepancy as before the migration — 14 of 15 checks
pass. The failing one is `кадров без файла на диске = 8`, all in `DcxV37-CJOC`: a 0.3 MB
download of a 61-second reel left one frame of nine on disk. That is real damage in the
corpus, not a migration artefact, and it is now visible in the data rather than only in an
audit: `frames.exists_ok = 0` on those 8 rows, `frames_state = PARTIAL`, `media_state =
MISSING`, flags `BROKEN_FRAME_REFERENCE` and `MISSING_MEDIA`.

### Re-runnability

Verified: the migration was run twice against a byte-copy of the production database and the
second run produced **identical** `video_state`, `transcript_meta`, `frames`, `transcripts`,
`deepdives.evidence_state` and `providers` rows. Every write is `INSERT OR REPLACE` or
`UPDATE` on a deterministic key, the August import only touches codes that are absent, and
step (b) never overwrites a transcript whose provenance another step has already recorded.
Only `updated_at`, `providers.checked_at` and the generated files' timestamps move.

---

## 13. Open items

1. `fetch_log` and `reels.fetch_id` are created and empty — the hiker owner fills them.
2. `beats.scene_ids_json` is empty on all 681 beats: alignment has not run.
3. No scene carries `frames_version = 'scene-v1'`; until the detector writes it, every code
   stays `frames_state = DONE_FIXED9` and every visual share stays an estimate.
4. `transcript_meta.media_sha256` and `lang_probability` are NULL for the whole corpus and
   cannot be backfilled — the mp4s are gone. New videos must capture both at transcription
   time.
5. `followers`, `our_posts`, `our_metrics` are empty. Creator growth and our own performance
   are outside what this database can answer.
6. `accounts.tag` / `status` vocabulary drift (§11) is documented, not fixed.
7. `video_features` currently carries a row for all 3 211 codes, including the 2 914 with
   neither transcript nor frames, so `video_state.features_state` reads `DONE` corpus-wide.
   That is true of the table and misleading as a state; raised with the features owner in
   `engine/HANDOFF_NOTES.md` §4.
