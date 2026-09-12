"""Versioned, idempotent migration for the engine tables (SPEC §2).

Nothing in main's 15 legacy tables is renamed or dropped. This module only

  * creates the new tables and indices, exactly as named in SPEC §2;
  * adds a short list of guarded columns to existing tables;
  * records every applied version in `schema_migrations`.

Re-running is a no-op. CLI:

    python3 -m engine.schema [--db PATH]            apply, then report
    python3 -m engine.schema [--db PATH] --check    report only, exit 1 if pending
"""
import argparse
import sys

from engine.db_util import columns, connect, now, row_counts, table_exists

# --------------------------------------------------------------------------- #
# v1 — the new tables, verbatim from SPEC §2
# --------------------------------------------------------------------------- #

V1_SQL = """
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

-- 2.5 scenes & frame labels (spec §5.5, §64)
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
  topic TEXT, subtopic TEXT, subject TEXT, audience TEXT, audience_stage TEXT, pain TEXT, desire TEXT,
  problem TEXT, solution_type TEXT, proof_type TEXT, hook_type TEXT, cta_type TEXT, narrative TEXT,
  positioning_type TEXT, funnel_role TEXT, tone TEXT, emotion_path TEXT,
  hook_text TEXT, hook_s REAL, hook_words INTEGER, setup_s REAL, problem_s REAL, explanation_s REAL,
  solution_s REAL, proof_s REAL, payoff_s REAL, cta_s REAL, total_s REAL, total_words INTEGER, wps REAL,
  avg_sentence_len REAL, info_density REAL, specificity REAL, numbers_n INTEGER, questions_n INTEGER,
  first_frame_type TEXT, hook_visual TEXT, a_roll_share REAL, b_roll_share REAL, split_share REAL,
  screen_share REAL, text_overlay_density REAL, scenes_n INTEGER, avg_scene_s REAL, cuts INTEGER,
  cuts_per_min REAL, cut_metric_quality TEXT, -- 'ffmpeg_scene_0.35_count_only' | 'scene-v1' | 'unavailable'
  visual_sequence TEXT,        -- e.g. "HOOK_CLOSEUP>SPLIT_PROOF>A_ROLL"
  visual_to_script_sync TEXT,
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
"""

# --------------------------------------------------------------------------- #
# v2 — guarded columns on the legacy tables (SPEC §2, closing paragraph)
# --------------------------------------------------------------------------- #

ADDED_COLUMNS = [
    ('reels', 'fetch_id', 'TEXT'),            # provenance back-pointer into fetch_log
    ('frames', 'sha256', 'TEXT'),             # content hash of the jpg on disk
    ('frames', 'exists_ok', 'INTEGER'),       # 1 file present, 0 broken reference
    ('deepdives', 'evidence_state', 'TEXT'),  # fixed9-v1 | scene-v1
    ('cards', 'status_v2', 'TEXT'),           # bridge to cards_v2.status
]


def _add_columns(con):
    """ALTER TABLE … ADD COLUMN, skipped when the column is already there."""
    for table, col, typ in ADDED_COLUMNS:
        if not table_exists(con, table):
            continue                          # legacy table absent: nothing to widen
        if col not in columns(con, table):
            con.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {typ}')


# (version, note, sql string | callable(con))
MIGRATIONS = [
    (1, 'engine tables: runs/jobs/video_state/transcript_meta/beats/scenes/frame_labels/'
        'video_features/creator_stats/insights/hypotheses/hypothesis_refs/cards_v2/'
        'card_scenes/script_versions/providers/fetch_log (SPEC §2)', V1_SQL),
    (2, 'guarded columns: reels.fetch_id, frames.sha256, frames.exists_ok, '
        'deepdives.evidence_state, cards.status_v2', _add_columns),
]

ENGINE_TABLES = [
    'schema_migrations', 'runs', 'jobs', 'video_state', 'transcript_meta', 'beats', 'scenes',
    'frame_labels', 'video_features', 'creator_stats', 'insights', 'hypotheses',
    'hypothesis_refs', 'cards_v2', 'card_scenes', 'script_versions', 'providers', 'fetch_log',
]
LEGACY_TABLES = [
    'accounts', 'snapshots', 'reels', 'scores', 'topics', 'deepdives', 'frames', 'transcripts',
    'our_posts', 'our_metrics', 'followers', 'cards', 'tool_log', 'spend',
]


def _ensure_ledger(con):
    con.execute('CREATE TABLE IF NOT EXISTS schema_migrations '
                '(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT)')


def applied_versions(con):
    """Versions already recorded, ascending. Empty list on a fresh database."""
    _ensure_ledger(con)
    return [r[0] for r in con.execute('SELECT version FROM schema_migrations ORDER BY version')]


def pending_versions(con):
    done = set(applied_versions(con))
    return [v for v, _, _ in MIGRATIONS if v not in done]


def migrate(con, verbose=False):
    """Apply every migration not yet recorded. Idempotent; returns the versions applied."""
    _ensure_ledger(con)
    done = set(applied_versions(con))
    applied = []
    for version, note, step in MIGRATIONS:
        if version in done:
            continue
        if callable(step):
            step(con)
        else:
            con.executescript(step)
        con.execute('INSERT OR REPLACE INTO schema_migrations (version, applied_at, note) '
                    'VALUES (?,?,?)', (version, now(), note))
        con.commit()
        applied.append(version)
        if verbose:
            print(f'  applied migration {version}: {note.splitlines()[0]}')
    con.execute('PRAGMA foreign_keys = ON')
    return applied


def report(con):
    """Human-readable status: applied versions + row counts for every table."""
    _ensure_ledger(con)
    rows = list(con.execute('SELECT version, applied_at, note FROM schema_migrations ORDER BY version'))
    lines = ['applied migrations:']
    if rows:
        for v, at, note in rows:
            lines.append(f'  v{v:<3} {at}  {(note or "").splitlines()[0][:78]}')
    else:
        lines.append('  (none)')
    pend = pending_versions(con)
    lines.append(f'pending migrations: {pend if pend else "none"}')

    counts = row_counts(con)
    lines.append('')
    lines.append(f'{"legacy tables":<24}{"rows":>10}')
    for t in LEGACY_TABLES:
        lines.append(f'  {t:<22}{counts.get(t, "-"):>10}')
    lines.append('')
    lines.append(f'{"engine tables":<24}{"rows":>10}')
    for t in ENGINE_TABLES:
        lines.append(f'  {t:<22}{counts.get(t, "MISSING"):>10}')
    extra = sorted(set(counts) - set(LEGACY_TABLES) - set(ENGINE_TABLES))
    if extra:
        lines.append('')
        lines.append('other tables: ' + ', '.join(extra))
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Apply/report the engine schema migration.')
    ap.add_argument('--db', default=None, help='path to radar.db (default: data/radar.db)')
    ap.add_argument('--check', action='store_true',
                    help='report only; do not apply. Exit 1 when migrations are pending.')
    args = ap.parse_args(argv)

    con = connect(args.db)
    try:
        if args.check:
            pend = pending_versions(con)
            print(report(con))
            if pend:
                print(f'\nPENDING: {pend} — run `python3 -m engine.schema` to apply')
                return 1
            print('\nschema up to date')
            return 0
        applied = migrate(con, verbose=True)
        print(f'applied now: {applied if applied else "nothing (already up to date)"}\n')
        print(report(con))
        return 0
    finally:
        con.close()


if __name__ == '__main__':
    sys.exit(main())
