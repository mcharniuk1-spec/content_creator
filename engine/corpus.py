#!/usr/bin/env python3
"""Corpus tiers, code lists and denominators (SPEC §0.4, §9).

The single honest answer to "how many videos do we have?" is: it depends on which
question you are asking. Four different denominators live in this database and they
are never equal:

    N_ingested   3 211  reel codes with Hiker metadata (play/likes/... only)
    N_transcript   273  codes with a transcripts row
    N_frames       295  codes with frames rows
    N_ready        266  codes with a *usable* transcript (words>0 AND timed
                        segments) AND frames — the only corpus that may be used
                        for conclusions about scripts or visuals

Every report that quotes a number must also quote which of these it divided by.
This module is the one place that computes them, so the numbers cannot drift.

    python3 -m engine.corpus            print the tier table
    python3 -m engine.corpus --json     dump the full code lists as JSON

This module also carries `ensure_tables()`: `engine/schema.py` (another owner)
is the real migration; until it lands, the features/stats modules create the
tables they write to from the SPEC §2 DDL verbatim.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO, 'data', 'radar.db')

# Tier names mirror video_state.corpus_tier (SPEC §2.2) plus one extra bucket the
# audit found and the spec's three-way split has no room for: 7 codes that have a
# transcripts row and frames, but the transcript is empty (Whisper heard no speech).
# They are not analysis-ready and they are not "frames only" either.
ANALYSIS_READY = 'ANALYSIS_READY'
FRAMES_ONLY = 'FRAMES_ONLY'
TRANSCRIPT_UNUSABLE = 'TRANSCRIPT_UNUSABLE'
INGESTED_NOT_ANALYZED = 'INGESTED_NOT_ANALYZED'

LATEST_SQL = """
SELECT code, pk_user, username, ts, play, likes, comm, resh, save, dur, followers, snapshot_id
FROM (SELECT r.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY snapshot_id DESC) rn
      FROM reels r)
WHERE rn = 1
"""

# ---------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------

# Verbatim from engine/SPEC.md §2.4–2.7 — only the tables this owner writes to.
# Kept as a literal copy so a diff against the spec is a plain text diff.
DDL = """
CREATE TABLE IF NOT EXISTS beats (
  beat_id TEXT PRIMARY KEY, code TEXT NOT NULL, idx INTEGER NOT NULL,
  role TEXT NOT NULL,
  start_s REAL, end_s REAL, duration_s REAL, share_of_speech REAL,
  text TEXT NOT NULL, words INTEGER, sentences INTEGER,
  audience_function TEXT, emotion TEXT, intention TEXT, persuasion TEXT, key_phrases_json TEXT,
  segment_idx_json TEXT,
  scene_ids_json TEXT, frame_idx_json TEXT, visual_state TEXT,
  analysis_version TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS beats_code ON beats(code, idx);

CREATE TABLE IF NOT EXISTS scenes (
  scene_id TEXT PRIMARY KEY, code TEXT NOT NULL, idx INTEGER NOT NULL,
  start_s REAL NOT NULL, end_s REAL, duration_s REAL, boundary_reason TEXT,
  scene_type TEXT,
  transition_in TEXT,
  frame_idx_json TEXT,
  keyframe_path TEXT, frames_version TEXT NOT NULL, detector_json TEXT);
CREATE INDEX IF NOT EXISTS scenes_code ON scenes(code, idx);

CREATE TABLE IF NOT EXISTS frame_labels (
  code TEXT NOT NULL, idx INTEGER NOT NULL, t_sec REAL,
  frame_type TEXT,
  roll TEXT,
  speaker_present INTEGER, face_present INTEGER, ui_present INTEGER, text_overlay INTEGER,
  overlay_text TEXT, caption_placement TEXT, framing TEXT,
  dominant_action TEXT, visual_density TEXT,
  is_visual_hook INTEGER, is_cta_visual INTEGER, is_proof_visual INTEGER,
  labels_json TEXT, confidence TEXT, analysis_version TEXT NOT NULL, model TEXT,
  PRIMARY KEY (code, idx));

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
  cuts_per_min REAL, cut_metric_quality TEXT,
  visual_sequence TEXT,
  visual_to_script_sync TEXT,
  play INTEGER, likes INTEGER, comm INTEGER, resh INTEGER, save INTEGER,
  like_rate REAL, comment_rate REAL, share_rate REAL, save_rate REAL, hi_intent_rate REAL,
  creator_median_play REAL, view_lift REAL, share_rate_lift REAL, save_rate_lift REAL, robust_z REAL,
  percentile_in_creator REAL, outlier_status TEXT,
  creator_consistency REAL, creator_n INTEGER,
  raw_labels_json TEXT, features_json TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS creator_stats (
  pk INTEGER NOT NULL, snapshot_id INTEGER NOT NULL, username TEXT, followers INTEGER, n_videos INTEGER,
  median_play REAL, mean_play REAL, mad_play REAL, iqr_play REAL, sd_play REAL, cv_play REAL,
  median_likes REAL, median_comm REAL, median_resh REAL, median_save REAL,
  median_like_rate REAL, median_comment_rate REAL, median_share_rate REAL, median_save_rate REAL,
  posts_per_week REAL, outlier_share REAL, high_performer_share REAL, consistency_score REAL,
  reliability TEXT,
  topic_dist_json TEXT, hook_dist_json TEXT, cta_dist_json TEXT, visual_dist_json TEXT, positioning_summary TEXT,
  computed_at TEXT NOT NULL, stats_version TEXT NOT NULL, PRIMARY KEY (pk, snapshot_id));
"""


def ensure_tables(con):
    """Make sure the tables this owner writes to exist.

    `engine/schema.py` owns the real versioned migration; when it is importable we
    call it and do nothing else. The DDL fallback exists only so features/stats can
    run before that module lands, and it is `CREATE TABLE IF NOT EXISTS` — it never
    touches a table schema.py already created.
    """
    try:
        from engine import schema  # type: ignore
    except ImportError:
        schema = None
    if schema is not None and hasattr(schema, 'migrate'):
        schema.migrate(con)
        return 'schema.migrate'
    con.executescript(DDL)
    con.commit()
    return 'ddl-fallback'


def connect(path=DB_PATH):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


FEATURES_VERSION = 'fv-1'


def merge_features(con, code, key, payload, columns=None, features_version=None):
    """Read-modify-write one `video_features` row.

    Three different producers write into the same row — `engine/lexical.py` (the
    `lexical` key), `engine/stats.py` (`perf`, `temporal` + the perf columns) and
    `engine/features.py` (everything else). None of them may clobber the others, so
    every write reads the existing `features_json`, updates exactly one key and puts
    the rest back. `columns` writes named key columns in the same transaction; a
    column not listed is left alone rather than set to NULL.

    `features_json` and `features_version` are NOT NULL in the schema, so the first
    write for a code has to INSERT.
    """
    import datetime
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    row = con.execute('SELECT features_json, features_version FROM video_features WHERE code=?',
                      (code,)).fetchone()
    if row is None:
        data, version = {}, features_version or FEATURES_VERSION
    else:
        try:
            data = json.loads(row[0] or '{}')
        except (TypeError, ValueError):
            data = {}
        version = features_version or row[1] or FEATURES_VERSION
    if key is not None:
        data[key] = payload
    blob = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    if row is None:
        con.execute('INSERT INTO video_features (code, features_version, computed_at, features_json)'
                    ' VALUES (?,?,?,?)', (code, version, now, blob))
    else:
        con.execute('UPDATE video_features SET features_json=?, computed_at=?, features_version=?'
                    ' WHERE code=?', (blob, now, version, code))
    if columns:
        cols = [k for k in columns if k != 'code']
        if cols:
            con.execute('UPDATE video_features SET %s WHERE code=?'
                        % ', '.join(f'{k}=?' for k in cols),
                        [columns[k] for k in cols] + [code])
    return True


# ---------------------------------------------------------------------------
# tiers
# ---------------------------------------------------------------------------

def _usable_transcript_codes(con):
    """words>0 AND at least one segment that carries a start time.

    The audit found 7 rows with words=0 / text='' / segments='[]' — Whisper with
    vad_filter found no speech. They are rows, not transcripts.
    """
    usable, unusable = set(), set()
    for r in con.execute('SELECT code, words, segments FROM transcripts'):
        try:
            segs = json.loads(r['segments'] or '[]')
        except (TypeError, ValueError):
            segs = []
        timed = [s for s in segs if isinstance(s, dict) and s.get('s') is not None]
        (usable if (r['words'] or 0) > 0 and timed else unusable).add(r['code'])
    return usable, unusable


def tiers(con):
    """Corpus tiers, code lists and the denominators table.

    Returns a JSON-serializable dict. Tiers are mutually exclusive and cover every
    ingested code exactly once; the `denominators` list is what reports must quote.
    """
    all_codes = set(r[0] for r in con.execute('SELECT DISTINCT code FROM reels'))
    transcript_codes = set(r[0] for r in con.execute('SELECT DISTINCT code FROM transcripts'))
    frame_codes = set(r[0] for r in con.execute('SELECT DISTINCT code FROM frames'))
    usable, unusable = _usable_transcript_codes(con)

    # A transcript or a frame set for a code that has no `reels` row carries no metrics,
    # so it can never enter a performance denominator. The audit found none; the August
    # archive backfill has since produced some. They are reported as orphans rather than
    # folded into a tier, because a tier that does not sum to N_ingested is worse than a
    # visible discrepancy — that is exactly how a 3 217 creeps into a report of 3 211.
    orphans = sorted((transcript_codes | frame_codes) - all_codes)
    transcript_codes &= all_codes
    frame_codes &= all_codes
    usable &= all_codes
    unusable &= all_codes

    analysis_ready = sorted(usable & frame_codes)
    frames_only = sorted(frame_codes - transcript_codes)
    transcript_unusable = sorted(unusable & frame_codes)
    # transcript rows without frames: 0 today, but never assume it
    transcript_no_frames = sorted(transcript_codes - frame_codes)
    analysed = set(analysis_ready) | set(frames_only) | set(transcript_unusable) | set(transcript_no_frames)
    ingested_not_analyzed = sorted(all_codes - analysed)

    row = con.execute('SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()
    newest_id = row[0] if row else None
    newest_codes, unprocessed, unprocessed_first_seen = set(), [], []
    if newest_id is not None:
        newest_codes = set(r[0] for r in con.execute(
            'SELECT code FROM reels WHERE snapshot_id=?', (newest_id,)))
        first_seen = {c: s for c, s in con.execute(
            'SELECT code, MIN(snapshot_id) FROM reels GROUP BY code')}
        unprocessed = sorted(newest_codes - transcript_codes - frame_codes)
        unprocessed_first_seen = sorted(c for c in unprocessed if first_seen.get(c) == newest_id)

    counts = {
        'n_ingested': len(all_codes),
        'n_transcript_rows': len(transcript_codes),
        'n_transcript_usable': len(usable),
        'n_frames': len(frame_codes),
        'n_ready': len(analysis_ready),
        'n_frames_only': len(frames_only),
        'n_transcript_unusable': len(transcript_unusable),
        'n_transcript_no_frames': len(transcript_no_frames),
        'n_ingested_not_analyzed': len(ingested_not_analyzed),
        'n_orphans_not_in_reels': len(orphans),
        'n_newest_snapshot': len(newest_codes),
        'n_newest_unprocessed': len(unprocessed),
        'n_newest_unprocessed_first_seen': len(unprocessed_first_seen),
    }

    denominators = [
        ('N_ingested', counts['n_ingested'],
         'reel codes with Hiker metadata — the only denominator for metric-only stats'),
        ('N_transcript', counts['n_transcript_rows'],
         'codes with a transcripts row (7 of them are empty)'),
        ('N_transcript_usable', counts['n_transcript_usable'],
         'words>0 and timed segments — denominator for every language statement'),
        ('N_frames', counts['n_frames'],
         'codes with frames rows (9 fixed samples each, legacy fixed9-v1)'),
        ('N_ready', counts['n_ready'],
         'usable transcript AND frames — denominator for script+visual conclusions'),
    ]

    return {
        'snapshot_id': newest_id,
        'orphans_not_in_reels': orphans,
        'counts': counts,
        'denominators': denominators,
        'tier_of_code_totals': {
            ANALYSIS_READY: len(analysis_ready),
            FRAMES_ONLY: len(frames_only),
            TRANSCRIPT_UNUSABLE: len(transcript_unusable),
            INGESTED_NOT_ANALYZED: len(ingested_not_analyzed),
        },
        'analysis_ready': analysis_ready,
        'frames_only': frames_only,
        'transcript_unusable': transcript_unusable,
        'transcript_no_frames': transcript_no_frames,
        'ingested_not_analyzed': ingested_not_analyzed,
        'newest_snapshot_unprocessed': unprocessed,
        'newest_snapshot_unprocessed_first_seen': unprocessed_first_seen,
        'transcript_codes': sorted(transcript_codes),
        'frame_codes': sorted(frame_codes),
    }


def tier_of(con):
    """{code: tier} for every ingested code."""
    t = tiers(con)
    out = {}
    for tier, key in ((ANALYSIS_READY, 'analysis_ready'), (FRAMES_ONLY, 'frames_only'),
                      (TRANSCRIPT_UNUSABLE, 'transcript_unusable'),
                      (INGESTED_NOT_ANALYZED, 'ingested_not_analyzed')):
        for c in t[key]:
            out[c] = tier
    for c in t['transcript_no_frames']:
        out.setdefault(c, TRANSCRIPT_UNUSABLE)
    return out


def latest_metrics(con):
    """One row per code, taken from the newest snapshot that code appears in.

    Views only ever grow, so the newest reading is the most complete one. This is
    `baseline.py`'s convention, extended with `followers`; it is the input to every
    performance calculation in `engine/stats.py`.

    Returns a pandas DataFrame (pandas is an analysis-only dependency; the server
    cron never imports this module).
    """
    import pandas as pd
    rows = [dict(r) for r in con.execute(LATEST_SQL)]
    df = pd.DataFrame(rows, columns=['code', 'pk_user', 'username', 'ts', 'play', 'likes',
                                     'comm', 'resh', 'save', 'dur', 'followers', 'snapshot_id'])
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def format_table(t):
    c = t['counts']
    lines = []
    lines.append('CORPUS TIERS  (mutually exclusive, cover every ingested code)')
    lines.append('')
    lines.append(f"  {'tier':<26} {'codes':>7}   {'share of ingested':>17}")
    lines.append('  ' + '-' * 56)
    total = c['n_ingested'] or 1
    for tier in (ANALYSIS_READY, FRAMES_ONLY, TRANSCRIPT_UNUSABLE, INGESTED_NOT_ANALYZED):
        n = t['tier_of_code_totals'][tier]
        lines.append(f'  {tier:<26} {n:>7}   {100.0 * n / total:>16.1f}%')
    lines.append('  ' + '-' * 56)
    total_tiers = sum(t['tier_of_code_totals'].values())
    lines.append(f"  {'TOTAL':<26} {total_tiers:>7}"
                 + ('' if total_tiers == c['n_ingested'] else '   <-- does not match N_ingested'))
    if c.get('n_orphans_not_in_reels'):
        lines.append(f"  (+ {c['n_orphans_not_in_reels']} orphan code(s) with analysis but no "
                     f"reels row, excluded from every tier: "
                     f"{', '.join(t['orphans_not_in_reels'][:6])})")
    lines.append('')
    lines.append('DENOMINATORS  (N_ingested != N_transcript != N_frames != N_ready)')
    lines.append('')
    lines.append(f"  {'name':<22} {'n':>7}   what it counts")
    lines.append('  ' + '-' * 96)
    for name, n, what in t['denominators']:
        lines.append(f'  {name:<22} {n:>7}   {what}')
    lines.append('')
    lines.append('NEWEST SNAPSHOT')
    lines.append('')
    lines.append(f"  snapshot_id                     {t['snapshot_id']}")
    lines.append(f"  codes in it                     {c['n_newest_snapshot']:>7}")
    lines.append(f"  unprocessed (no transcript, no frames)  {c['n_newest_unprocessed']:>7}")
    lines.append(f"  of those, first seen in it      {c['n_newest_unprocessed_first_seen']:>7}")
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    db = DB_PATH
    if '--db' in argv:
        db = argv[argv.index('--db') + 1]
    con = connect(db)
    t = tiers(con)
    if '--json' in argv:
        print(json.dumps(t, ensure_ascii=False, sort_keys=True, indent=1))
    else:
        print(format_table(t))
    con.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
