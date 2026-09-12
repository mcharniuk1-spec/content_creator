# M2Radar Content Engine — canonical architecture spec (v1, 2026-09-11)

Binding for every module under `engine/`. Written by the orchestrator after the audits in
`reports/audit/01…05`. Anything not covered here follows the audit recommendations
(`reports/audit/01-branch-comparison.md` §5).

## 0. Decisions

1. **Source of truth = main's SQLite `data/radar.db`** (`db.py`, 15 tables). Nothing in the
   existing tables is renamed or dropped. New tables are added by `engine/schema.py`
   through an idempotent, versioned migration (`schema_migrations` table).
2. **Max's `Latest` is adopted as contracts, not as a store.** Ported verbatim into this
   branch: `schemas/video-scene-segmentation.schema.json`, `studio/remotion/` (EDL contract +
   composition), `m2_orchestrator/process_budget.py` → `engine/process_budget.py`,
   `m2_studio/provider-catalog.json` → `config/provider-catalog.json`. The `m2_signal`
   ledger and the 41-stage DAG are *not* ported; `latest` branch remains the reference.
3. **Production default path:** Hiker → `reels` → local faster-whisper → local scene/frame
   extraction → alignment → analysis. Loore is `OPTIONAL_PROVIDER` only (`engine/providers.py`
   registry; no credentials needed for the default path).
4. **Corpus split (V4 §60):** `analysis-ready` = code with usable transcript (words>0, timed
   segments) AND frames (266 codes today); `frames-only` (22); `ingested-not-analyzed` =
   everything else (1 313 codes in snapshot 3 alone). Conclusions about scripts/visuals use
   only analysis-ready codes; stats use all reels with metrics. Denominators are always
   reported separately.
5. **Every processing step writes a `jobs` row** (state trace) — see §2.
6. **`run.py` and `cron.sh` keep working unchanged in shape.** New stages are added as
   separate CLIs (`python3 -m engine.<module>`) that `cron.sh` calls after the existing
   13 steps; a failure in a new stage never blocks the old chain.
7. Python target: 3.10 (Mac) and 3.12 (server). Stdlib + numpy/pandas/scipy/matplotlib
   (analysis only, not needed on the server for the cron). ffmpeg via `imageio_ffmpeg`.
8. No paid API calls from any new module by default. Anything that costs money must
   print the estimate and require `--yes`.

## 1. Identifiers

- `code` = Instagram shortcode, the video id everywhere (as in `reels`, `frames`, `transcripts`).
- creator = `accounts.pk` / `accounts.username` (reels carry `pk_user` + `username`).
- `run_id` = `YYYY-MM-DD_HHMM-<6 hex>`; `job_id` = uuid4 hex.
- Versions: `asr_version` (e.g. `faster-whisper-small-int8-v1`), `frames_version`
  (`fixed9-v1` for the legacy 9-frame sampling; `scene-v1` for the new detector),
  `analysis_version` (`ta-v1` transcript analysis, `fa-v1` frame analysis), `features_version`.

## 2. New tables (`engine/schema.py`)

All `TEXT` timestamps are ISO-8601 UTC. JSON columns hold canonical JSON (sorted keys).

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT);

-- 2.1 state tracing (spec §7)
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, kind TEXT NOT NULL, -- weekly | watchdog | analysis | cards | manual
  git_commit TEXT, host TEXT, config_json TEXT, summary_json TEXT, status TEXT NOT NULL DEFAULT 'RUNNING');
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY, run_id TEXT REFERENCES runs(run_id), parent_job_id TEXT,
  entity_kind TEXT NOT NULL,           -- video | creator | corpus | hypothesis | card
  entity_id TEXT NOT NULL,             -- code / pk / 'corpus' / hypothesis_id / card_id
  stage TEXT NOT NULL,                 -- see §3 state list
  state TEXT NOT NULL,                 -- PENDING | RUNNING | DONE | FAILED | RETRY_REQUIRED | SKIPPED
  previous_state TEXT, started_at TEXT, finished_at TEXT, duration_s REAL,
  agent TEXT, provider TEXT, model TEXT, prompt_version TEXT, knowledge_version TEXT,
  input_refs_json TEXT, output_refs_json TEXT, data_version TEXT, retries INTEGER NOT NULL DEFAULT 0,
  error TEXT, validation TEXT, cost_json TEXT);
CREATE INDEX IF NOT EXISTS jobs_entity ON jobs(entity_kind, entity_id, stage);

-- 2.2 per-video processing state (one row per code; the "processing contract", spec §17B)
CREATE TABLE IF NOT EXISTS video_state (
  code TEXT PRIMARY KEY,
  ingested_at TEXT, first_snapshot_id INTEGER, last_snapshot_id INTEGER,
  media_state TEXT NOT NULL DEFAULT 'UNKNOWN',      -- AVAILABLE | EXPIRED | MISSING | DOWNLOADED
  media_sha256 TEXT, media_path TEXT, media_bytes INTEGER,
  transcript_state TEXT NOT NULL DEFAULT 'MISSING', -- MISSING | PENDING | DONE | EMPTY_NO_SPEECH | FAILED
  frames_state TEXT NOT NULL DEFAULT 'MISSING',     -- MISSING | PENDING | DONE_FIXED9 | DONE_SCENE | FAILED | PARTIAL
  alignment_state TEXT NOT NULL DEFAULT 'MISSING',  -- MISSING | DONE | NOT_POSSIBLE
  transcript_analysis_state TEXT NOT NULL DEFAULT 'MISSING', -- MISSING | PENDING | DONE | FAILED
  frame_analysis_state TEXT NOT NULL DEFAULT 'MISSING',
  features_state TEXT NOT NULL DEFAULT 'MISSING',
  analysis_ready INTEGER NOT NULL DEFAULT 0,        -- 1 when transcript DONE + frames DONE_* + both analyses DONE
  corpus_tier TEXT NOT NULL DEFAULT 'INGESTED_NOT_ANALYZED', -- ANALYSIS_READY | FRAMES_ONLY | INGESTED_NOT_ANALYZED
  asr_version TEXT, frames_version TEXT, analysis_version TEXT, features_version TEXT,
  flags_json TEXT,                                  -- ["MISSING_MEDIA","BROKEN_FRAME_REFERENCE",...]
  updated_at TEXT NOT NULL);

-- 2.3 transcript provenance (extends transcripts, which stays as is)
CREATE TABLE IF NOT EXISTS transcript_meta (
  code TEXT PRIMARY KEY REFERENCES transcripts(code),
  provider TEXT NOT NULL DEFAULT 'local', model TEXT, asr_version TEXT, language TEXT, lang_probability REAL,
  media_sha256 TEXT, words INTEGER, tokens INTEGER, chars INTEGER, speech_seconds REAL, words_per_second REAL,
  segments_n INTEGER, processing_seconds REAL, created_at TEXT, version INTEGER NOT NULL DEFAULT 1, note TEXT);

-- 2.4 transcript beats (semantic chapters, spec §62). One row per beat, from LLM analysis (ta-v1)
CREATE TABLE IF NOT EXISTS beats (
  beat_id TEXT PRIMARY KEY, code TEXT NOT NULL, idx INTEGER NOT NULL,
  role TEXT NOT NULL,          -- hook | hook_extension | setup | context | audience | problem | pain | tension | explanation | mechanism | solution | proof | example | objection | transformation | payoff | cta | closing | rehook | other
  start_s REAL, end_s REAL, duration_s REAL, share_of_speech REAL,
  text TEXT NOT NULL, words INTEGER, sentences INTEGER,
  audience_function TEXT, emotion TEXT, intention TEXT, persuasion TEXT, key_phrases_json TEXT,
  segment_idx_json TEXT,       -- indices into transcripts.segments
  scene_ids_json TEXT, frame_idx_json TEXT, visual_state TEXT, -- filled by alignment: a_roll|b_roll|split|screen|text|unknown
  analysis_version TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS beats_code ON beats(code, idx);

-- 2.5 scenes & frame labels (spec §5.5, §64). Legacy corpus: scenes derived from the 9 fixed frames
--     + labels (fa-v1); new corpus: real scene intervals from the detector (scene-v1).
CREATE TABLE IF NOT EXISTS scenes (
  scene_id TEXT PRIMARY KEY, code TEXT NOT NULL, idx INTEGER NOT NULL,
  start_s REAL NOT NULL, end_s REAL, duration_s REAL, boundary_reason TEXT, -- detector | sampled | transcript | manual
  scene_type TEXT,             -- taxonomy §4
  transition_in TEXT,          -- hard_cut | jump_cut | zoom_cut | match_cut | swipe | fade | overlay_reveal | split_reveal | text_punch_in | ui_zoom | broll_replace | unknown
  frame_idx_json TEXT,         -- frames.idx list inside the scene
  keyframe_path TEXT, frames_version TEXT NOT NULL, detector_json TEXT);
CREATE INDEX IF NOT EXISTS scenes_code ON scenes(code, idx);
CREATE TABLE IF NOT EXISTS frame_labels (
  code TEXT NOT NULL, idx INTEGER NOT NULL, t_sec REAL,
  frame_type TEXT,             -- taxonomy §4
  roll TEXT,                   -- A | B | SPLIT | SCREEN | TEXT | OTHER
  speaker_present INTEGER, face_present INTEGER, ui_present INTEGER, text_overlay INTEGER,
  overlay_text TEXT, caption_placement TEXT, framing TEXT, -- close_up | medium | wide | screen | none
  dominant_action TEXT, visual_density TEXT, -- low | medium | high
  is_visual_hook INTEGER, is_cta_visual INTEGER, is_proof_visual INTEGER,
  labels_json TEXT, confidence TEXT, analysis_version TEXT NOT NULL, model TEXT,
  PRIMARY KEY (code, idx));

-- 2.6 consolidated per-video features (spec §17C) — key columns + full JSON
CREATE TABLE IF NOT EXISTS video_features (
  code TEXT PRIMARY KEY, features_version TEXT NOT NULL, computed_at TEXT NOT NULL,
  -- content semantics (canonical categories, §5)
  topic TEXT, subtopic TEXT, subject TEXT, audience TEXT, audience_stage TEXT, pain TEXT, desire TEXT,
  problem TEXT, solution_type TEXT, proof_type TEXT, hook_type TEXT, cta_type TEXT, narrative TEXT,
  positioning_type TEXT, funnel_role TEXT, tone TEXT, emotion_path TEXT,
  -- script construction
  hook_text TEXT, hook_s REAL, hook_words INTEGER, setup_s REAL, problem_s REAL, explanation_s REAL,
  solution_s REAL, proof_s REAL, payoff_s REAL, cta_s REAL, total_s REAL, total_words INTEGER, wps REAL,
  avg_sentence_len REAL, info_density REAL, specificity REAL, numbers_n INTEGER, questions_n INTEGER,
  -- visual construction
  first_frame_type TEXT, hook_visual TEXT, a_roll_share REAL, b_roll_share REAL, split_share REAL,
  screen_share REAL, text_overlay_density REAL, scenes_n INTEGER, avg_scene_s REAL, cuts INTEGER,
  cuts_per_min REAL, cut_metric_quality TEXT, -- 'ffmpeg_scene_0.35_count_only' | 'scene-v1' | 'unavailable'
  visual_sequence TEXT,        -- e.g. "HOOK_CLOSEUP>SPLIT_PROOF>A_ROLL"
  visual_to_script_sync TEXT,
  -- performance (from engine/stats.py)
  play INTEGER, likes INTEGER, comm INTEGER, resh INTEGER, save INTEGER,
  like_rate REAL, comment_rate REAL, share_rate REAL, save_rate REAL, hi_intent_rate REAL,
  creator_median_play REAL, view_lift REAL, share_rate_lift REAL, save_rate_lift REAL, robust_z REAL,
  percentile_in_creator REAL, outlier_status TEXT, -- HIGH | NORMAL | LOW | SMALL_SAMPLE
  creator_consistency REAL, creator_n INTEGER,
  raw_labels_json TEXT, features_json TEXT NOT NULL);

-- 2.7 creator statistics (spec §18, §70)
CREATE TABLE IF NOT EXISTS creator_stats (
  pk INTEGER NOT NULL, snapshot_id INTEGER NOT NULL, username TEXT, followers INTEGER, n_videos INTEGER,
  median_play REAL, mean_play REAL, mad_play REAL, iqr_play REAL, sd_play REAL, cv_play REAL,
  median_likes REAL, median_comm REAL, median_resh REAL, median_save REAL,
  median_like_rate REAL, median_comment_rate REAL, median_share_rate REAL, median_save_rate REAL,
  posts_per_week REAL, outlier_share REAL, high_performer_share REAL, consistency_score REAL,
  reliability TEXT,            -- CONSISTENT | HIGH_VARIANCE | SMALL_SAMPLE
  topic_dist_json TEXT, hook_dist_json TEXT, cta_dist_json TEXT, visual_dist_json TEXT, positioning_summary TEXT,
  computed_at TEXT NOT NULL, stats_version TEXT NOT NULL, PRIMARY KEY (pk, snapshot_id));

-- 2.8 insights → hypotheses → references (spec §21A–D)
CREATE TABLE IF NOT EXISTS insights (
  insight_id TEXT PRIMARY KEY, run_id TEXT, statement TEXT NOT NULL, claim TEXT, metric TEXT, n INTEGER,
  comparison TEXT, evidence_json TEXT, supporting_codes_json TEXT, supporting_creators_json TEXT,
  transcript_pattern TEXT, frame_pattern TEXT, interpretation TEXT, implication TEXT,
  confidence TEXT NOT NULL,    -- RELIABLE | PROBABLE | INSUFFICIENT
  limitations TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hypotheses (
  hypothesis_id TEXT PRIMARY KEY, run_id TEXT, title TEXT NOT NULL, statement TEXT NOT NULL,
  audience TEXT, positioning_fit TEXT, pain TEXT, desired_outcome TEXT, hook TEXT, thesis TEXT,
  mechanism TEXT, proof TEXT, cta TEXT, visual_structure TEXT, format TEXT, -- M2 Radar | M2 Builds | M2 Teardown
  supporting_insights_json TEXT, candidate_refs_json TEXT, strengths TEXT, risks TEXT, novelty TEXT,
  confidence TEXT, scores_json TEXT, total_score REAL, reviewer_comment TEXT,
  status TEXT NOT NULL DEFAULT 'PROPOSED', -- PROPOSED | SELECTED | REJECTED
  card_id TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hypothesis_refs (
  hypothesis_id TEXT NOT NULL, code TEXT NOT NULL, function TEXT NOT NULL, -- topic|hook|pain|explanation|proof|cta|a_roll|b_roll|split|screen_proof|rhythm|transition
  reason TEXT NOT NULL, useful_beat_ids_json TEXT, useful_scene_ids_json TEXT,
  performance_json TEXT,       -- play, creator_median, view_lift, share_rate, save_rate
  transformation TEXT,         -- what is borrowed vs changed
  PRIMARY KEY (hypothesis_id, code, function));

-- 2.9 cards v2 (spec §29–31, §45). Full card JSON lives in cards/<card_id>.json; DB mirrors it.
CREATE TABLE IF NOT EXISTS cards_v2 (
  card_id TEXT PRIMARY KEY, run_id TEXT, hypothesis_id TEXT, title TEXT NOT NULL, format TEXT NOT NULL,
  concept TEXT, audience TEXT, objective TEXT, positioning TEXT, pain TEXT, promise TEXT, rationale TEXT,
  process TEXT, friction TEXT, ai_boundary TEXT, next_action TEXT, -- the four mandatory filter fields
  hooks_json TEXT, script_version INTEGER NOT NULL DEFAULT 1, script_json TEXT, -- sections with words+seconds
  total_words INTEGER, total_s REAL, target_wps REAL, tone TEXT,
  refs_json TEXT, storyboard_version INTEGER NOT NULL DEFAULT 1, editing_json TEXT, assets_json TEXT,
  claims_json TEXT,            -- per claim: OBSERVED | PLANNED | TO_MEASURE | MISSING
  review_json TEXT, status TEXT NOT NULL DEFAULT 'DRAFT', -- DRAFT | REVIEWED | APPROVED | SHOT | PUBLISHED | DROPPED
  json_path TEXT, pdf_page INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS card_scenes (
  card_id TEXT NOT NULL, scene_id TEXT NOT NULL, idx INTEGER NOT NULL, start_s REAL NOT NULL, end_s REAL NOT NULL,
  script_text TEXT, script_role TEXT, frame_type TEXT, layout TEXT, -- a_roll | split_screen | demo | motion_graphic (Remotion layouts)
  visual TEXT, overlay_text TEXT, transition TEXT, source_inspiration_json TEXT, -- [{code, scene_id|beat_id, why}]
  asset_status TEXT NOT NULL DEFAULT 'missing', -- generated | ready | missing | template
  asset_path TEXT, editing_notes TEXT, PRIMARY KEY (card_id, idx));
CREATE TABLE IF NOT EXISTS script_versions (
  card_id TEXT NOT NULL, version INTEGER NOT NULL, kind TEXT NOT NULL, -- writer | reviewer
  script_json TEXT NOT NULL, findings TEXT, created_at TEXT NOT NULL, PRIMARY KEY (card_id, version));

-- 2.10 provider registry & external fetch provenance
CREATE TABLE IF NOT EXISTS providers (
  name TEXT PRIMARY KEY, kind TEXT NOT NULL, -- social_data | transcription | frames | image_gen | video_gen | render | storage
  role TEXT NOT NULL,          -- DEFAULT | OPTIONAL_PROVIDER | FALLBACK
  state TEXT NOT NULL,         -- CONFIGURED | NOT_CONFIGURED | FAILED | DISABLED
  env_var TEXT, checked_at TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS fetch_log (
  fetch_id TEXT PRIMARY KEY, provider TEXT NOT NULL, endpoint TEXT NOT NULL, params_json TEXT,
  fetched_at TEXT NOT NULL, http_status INTEGER, units REAL, price REAL, cache_path TEXT, sha256 TEXT,
  snapshot_id INTEGER, run_id TEXT, note TEXT);
```

Migration also **adds columns** (ALTER … ADD COLUMN, guarded) to existing tables:
`reels.fetch_id TEXT` (provenance back-pointer), `frames.sha256 TEXT`, `frames.exists_ok INTEGER`,
`deepdives.evidence_state TEXT`, `cards.status_v2 TEXT`. Nothing else in old tables changes.

## 3. Stage names (jobs.stage) — canonical state list

`DISCOVERED, PROFILE_FETCHED, VIDEO_METADATA_FETCHED, STATS_FETCHED, MEDIA_FETCHED,
TRANSCRIPTION, TRANSCRIPT_ANALYSIS, FRAME_EXTRACTION, FRAME_ANALYSIS, ALIGNMENT, GENERAL_ANALYSIS,
STATISTICAL_ANALYSIS, CATEGORIZATION, REFERENCE_SELECTION, CONCEPT_GENERATION, CARD_GENERATION,
SCRIPT_GENERATION, SCRIPT_REVIEW, FRAME_PLAN, FRAME_GENERATION, VIDEO_GENERATION_READY,
VIDEO_RENDER, QUALITY_REVIEW, NOTION_SYNC, COMPLETED`. `jobs.state` ∈ PENDING | RUNNING | DONE |
FAILED | RETRY_REQUIRED | SKIPPED. `engine/state.py` exposes `start_run(kind)`, `job(run_id,
entity_kind, entity_id, stage, **meta)` context manager that writes RUNNING→DONE/FAILED with
duration and error, and `refresh_video_state(con, code)` which recomputes `video_state` from the
underlying tables (idempotent).

## 4. Taxonomies (canonical, closed vocabularies; raw labels kept in `*_json`)

- **frame_type / scene_type**: `A_ROLL_TALKING_HEAD, A_ROLL_CLOSE_UP, A_ROLL_MEDIUM, A_ROLL_WIDE,
  B_ROLL_CONTEXT, B_ROLL_PRODUCT, B_ROLL_PROCESS, SCREEN_RECORDING, SCREENSHOT, UI_DEMO, SPLIT_SCREEN,
  TEXT_ONLY, DATA_VISUAL, MEME, PROOF_VISUAL, HOOK_VISUAL, CTA_VISUAL, TRANSITION, MOTION_GRAPHIC,
  OVERLAY, UNKNOWN`.
- **roll**: `A | B | SPLIT | SCREEN | TEXT | OTHER`.
- **hook_type**: `question, bold_claim, contrarian, curiosity_gap, number_stat, story_open,
  problem_call_out, demo_first, result_first, warning_fear, identity_call, list_promise, other`.
- **pain (canonical)**: `time_waste, chaos_no_process, dont_know_where_to_start, tool_overload,
  cost_money, fear_of_replacement, quality_trust, missing_skills, slow_response_to_leads,
  manual_repetition, scaling_without_hiring, keeping_up_with_ai, other`.
- **solution_type**: `workflow_recipe, tool_walkthrough, prompt_technique, agent_build, comparison,
  framework_mental_model, case_story, warning_dont, resource_handoff, other`.
- **proof_type**: `screen_demo, numbers, before_after, personal_story, client_story, authority_claim,
  third_party_data, none`.
- **cta_type**: `comment_keyword, follow, save_share, link_in_bio, dm, free_resource, next_video,
  question_to_audience, none`.
- **narrative**: `problem_solution, listicle, tutorial_steps, story_arc, contrast_before_after,
  myth_bust, announcement_news, rant_opinion, demo_walkthrough, other`.
- **topic**: reuse `topics.py` vocabulary (27 labels) as canonical topic; `subtopic` free text
  normalized later.
- **funnel_role**: `awareness | trust | conversion`. **positioning_type**: `educator | builder |
  news | seller | entertainer`.

## 5. Analysis JSON contracts (LLM outputs, one file per code)

`data/analysis/transcripts/<code>.json` (schema id `ta-v1`):
```json
{"code":"…","analysis_version":"ta-v1","model":"…","language":"en",
 "beats":[{"idx":0,"role":"hook","start_s":0.0,"end_s":3.2,"text":"…","segment_idx":[0,1],
           "audience_function":"…","emotion":"…","intention":"…","persuasion":"…","key_phrases":["…"]}],
 "semantics":{"topic":"<topics.py label>","subtopic":"…","subject":"…","thesis":"…","audience":"…",
   "audience_stage":"…","pain":"<canonical>","pain_raw":"…","desire":"…","problem":"…","fear":"…",
   "aspiration":"…","solution":"…","solution_type":"<canonical>","mechanism":"…","proof_type":"<canonical>",
   "proof":"…","examples":["…"],"objection":"…","payoff":"…","cta":"…","cta_type":"<canonical>",
   "hook_type":"<canonical>","hook_text":"…","narrative":"<canonical>","tone":"…","emotion_path":"…",
   "funnel_role":"…","positioning_type":"…","tools_mentioned":["…"],"models_mentioned":["…"],
   "numbers_used":["…"],"rhetorical_devices":["…"],"open_loops":1,"pattern_interrupts":0},
 "interpretation":{"message":"…","intent":"…","audience_tension":"…","offer":"…","mechanism":"…",
   "emotion":"…","proof":"…","structural_reason":"…","visual_reason":"…"},
 "quality":{"specificity":1-5,"novelty":1-5,"clarity":1-5,"info_density":1-5,"grounded":true},
 "confidence":"RELIABLE|PROBABLE|INSUFFICIENT","notes":"…"}
```
`data/analysis/frames/<code>.json` (schema id `fa-v1`): per frame idx → `frame_type, roll, speaker_present,
face_present, ui_present, text_overlay, overlay_text, caption_placement, framing, dominant_action,
visual_density, is_visual_hook, is_cta_visual, is_proof_visual, notes`; plus video-level:
`first_frame_type, hook_visual, visual_sequence (list of frame_type in order, deduplicated runs),
transitions_observed, a_roll_share_est, b_roll_share_est, split_share_est, screen_share_est,
text_overlay_density, caption_style, background, cta_visual, proof_visuals, sync_notes, limitations`.
For the legacy corpus the frames are 9 fixed samples: shares are *estimates from samples*, transitions
between samples are `unknown` unless the two frames obviously differ (then `hard_cut_or_more`). Never
claim a transition that was not observed.

`engine/ingest_analysis.py` loads these files into `beats`, `frame_labels`, `scenes` (legacy: one
scene per run of identical frame_type across consecutive samples), and updates `video_state`.

## 6. Local pipeline (`engine/local_pipeline.py`) — video-by-video contract

`process_video(con, code, media_url_or_path, run_id, *, asr_version, frames_version)`:
1. skip if `video_state.transcript_state=DONE and frames_state=DONE_SCENE` for the same versions;
2. download to `data/video/<code>.mp4` (curl, timeout), record sha256 + bytes; `MEDIA_FETCHED` job;
3. transcribe with faster-whisper (`small`, int8, CPU, `language='en'`, `vad_filter=True`,
   `word_timestamps=False`) → segments `[{s,e,t}]`; write `transcripts` + `transcript_meta`
   (words/chars/tokens≈words*1.3/speech_seconds=sum(e-s)/wps); `EMPTY_NO_SPEECH` when no segments;
4. frames (`scene-v1`): ffmpeg `select='gt(scene,0.30)',showinfo` → cut timestamps list;
   scenes = intervals between cuts (plus 0 and dur); keyframe at scene start+0.2s and, for scenes
   >6 s, one mid-frame; plus hook samples at 0.4/1.2/2.4/4.0 s (compat with fixed9); write
   `frames` (idx continues), `scenes` with `boundary_reason='detector'`, `detector_json`
   with threshold; contact sheet 3xN; `deepdives` row (cuts = len(cuts), cuts_ps, evidence_state='scene-v1');
5. alignment (`engine/align.py`): beat/segment ↔ scene overlap by time; writes `beats.scene_ids_json`
   when beats exist, else stores segment→scene map in `video_state.flags_json` for later;
6. delete mp4 unless `--keep-video`; `refresh_video_state`.
Idempotent, retryable (3), each step a `jobs` row, versioned by `asr_version`/`frames_version`.
`engine/watchdog.py --limit N [--yes]`: selects codes where `analysis_ready=0 AND media available
(URL present in newest cache/*clips*.json and link alive)` and runs `process_video` sequentially;
prints a summary; never pays (uses cached URLs only). If no live URL: marks `media_state=EXPIRED`.

## 7. Stats (`engine/stats.py`)

Per creator per snapshot (`creator_stats`): median/mean/MAD/IQR/SD/CV of play; medians of counts and
rates; posts_per_week from ts; outlier_share (robust z>2); high_performer_share (play≥2×median);
consistency_score = 1/(1+CV) clipped; reliability: SMALL_SAMPLE n<5, CONSISTENT (CV<1 & n≥8),
else HIGH_VARIANCE. Per video (into `video_features` perf columns): rates with denominator guard
(play≥100 else NULL), view_lift = play/creator_median − 1, share/save rate lift vs creator median rate,
robust_z = (ln(1+play) − median ln)/(1.4826·MAD ln) clipped ±5 (same convention as score.py),
percentile in creator, outlier_status. Temporal: per creator ordered by ts — delta vs previous reel,
ratio to rolling median (window 5), slope over last 10 (log play). Reuse `baseline.py` conventions
where identical; do not reimplement `score.py`.

## 8. Card JSON (`cards/<card_id>.json`, schema `card-v2`)

```json
{"schema":"m2radar.card.v2","card_id":"C-2026-09-11-01","hypothesis_id":"H-…","format":"M2 Builds",
 "title":"…","strategy":{"concept":"…","audience":"…","objective":"…","positioning":"…","pain":"…","promise":"…","rationale":"…",
   "filter":{"process":"…","friction":"…","ai_boundary":"…","next_action":"…"}},
 "references":[{"code":"…","username":"…","url":"https://www.instagram.com/reel/<code>/","function":"hook",
   "play":0,"creator_median_play":0,"view_lift":0.0,"share_rate":0.0,"save_rate":0.0,"reason":"…",
   "useful_transcript":{"beat_id":"…","quote":"…"},"useful_frame":{"scene_id":"…","what":"…"},"transformed_how":"…"}],
 "hooks":[{"text":"…","type":"bold_claim","is_question":false}],
 "script":{"version":2,"sections":[{"role":"hook","text":"…","words":0,"seconds":0.0}],"total_words":0,"total_s":0.0,"target_wps":2.4,"tone":"…","emotional_effect":"…"},
 "storyboard":[{"scene_id":"S01","idx":0,"start_s":0.0,"end_s":2.2,"script_text":"…","script_role":"hook","frame_type":"A_ROLL_CLOSE_UP",
   "layout":"a_roll","visual":"…","overlay_text":"…","transition":"hard_cut","source_inspiration":[{"code":"…","scene_id":"…","why":"…"}],
   "asset_status":"template","asset_path":"cards/frames/C-…-S01.png","editing":"…"}],
 "editing":{"cut_timing":"…","captions":"…","emphasis":"…","zooms":"…","motion":"…","assets_required":["…"]},
 "claims":[{"text":"…","state":"OBSERVED|PLANNED|TO_MEASURE|MISSING","source":"…"}],
 "traceability":{"insights":["I-…"],"hypothesis":"H-…","evidence_summary":"…","original_synthesis":"…","why_better_than_generic":"…"},
 "review":{"version":1,"findings":["…"],"revised":true},
 "remotion_edl_path":"cards/edl/C-….json","status":"REVIEWED"}
```
`engine/cards_v2.py` validates the JSON, writes `cards_v2`/`card_scenes`/`script_versions`, exports
a Remotion EDL (`m2.remotion-edl.v1`, PREVIS mode, placeholder layers) validated by
`studio/remotion/contract.mjs`.

## 9. Files & ownership (Wave 2)

| Owner | Files |
|---|---|
| schema/state (Opus) | `engine/__init__.py, engine/schema.py, engine/state.py, engine/migrate_legacy.py, engine/db_util.py, tests/test_engine_schema.py, docs/M2RADAR_DATABASE_RECONCILIATION.md` |
| hiker (Sonnet) | `engine/hiker_config.py, engine/providers.py, lib/hiker.py (provenance sidecar + PRICE), collect_snapshot.py (fetch_log), roster.py (PRICE import), cron.sh (ff-only, config check), stats.py (endpoint fix), run.py (state summary), tests/test_hiker_client.py, tests/test_providers.py, .env.example, docs/data-lifecycle.md` |
| local pipeline (Sonnet) | `engine/local_pipeline.py, engine/scenes.py, engine/align.py, engine/watchdog.py, engine/process_budget.py (port), tests/test_local_pipeline.py, tests/fixtures/*` |
| features/stats (Opus) | `engine/lexical.py, engine/stats.py, engine/features.py, engine/ingest_analysis.py, engine/corpus.py (corpus tiers + code lists), tests/test_stats.py, tests/test_lexical.py, docs/M2RADAR_ANALYSIS_METHOD.md (draft)` |
| ports (Haiku) | `schemas/…, studio/remotion/…, config/provider-catalog.json, docs/m2-field-dictionary.csv, reference/latest/README.md` |

Shared rule: nobody edits another owner's files; if you need a change there, write it in
`engine/HANDOFF_NOTES.md` under your section and the orchestrator applies it.
