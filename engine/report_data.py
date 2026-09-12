#!/usr/bin/env python3
"""Report-ready data bundles for the M2Radar report writers (engine/SPEC.md §2.6-2.8, §7;
V4 execution-prompt §42-43).

Read-only against `data/radar.db`: every function here runs SELECT statements only. It
never INSERTs, UPDATEs or DELETEs a row, and it never opens a `runs`/`jobs` trace --
Wave-2 owners (schema/hiker/pipeline/features) are still writing to the same file
concurrently and this module has nothing to add to that trace. `engine/ingest_insights.py`
is the one Wave-3 module that writes.

Every artefact below is built by a small, separately callable function so
`engine/charts.py` can reuse the same rows instead of re-deriving them (single source of
truth for "what is a video row", "what is the strong/weak split", "what is a script
part").

Two vocabularies both call something a "corpus tier" and they do not agree on purpose
(`engine/HANDOFF_NOTES.md`, features-owner §1): `video_state.corpus_tier` is a
*processing* state (what still needs doing), `engine.corpus.tiers()` is an *evidence*
tier (what a report may divide by). `corpus_tiers.json` carries both, explicitly labelled,
rather than picking a winner.

    python3 -m engine.report_data --out reports/data
    python3 -m engine.report_data --out reports/data --db data/radar.db
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
import hashlib
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine import corpus, stats  # noqa: E402
from engine import state as engine_state  # noqa: E402

# ---------------------------------------------------------------------------
# small shared helpers
# ---------------------------------------------------------------------------

ROLES = ('hook', 'setup', 'problem', 'explanation', 'solution', 'proof', 'payoff', 'cta')

CATEGORY_FIELDS = (
    ('topic', None), ('subtopic', 20), ('pain', None), ('solution_type', None),
    ('proof_type', None), ('hook_type', None), ('cta_type', None), ('narrative', None),
    ('funnel_role', None), ('positioning_type', None), ('first_frame_type', None),
    ('visual_sequence', 15),
)
TOOLS_TOP_N = 30

VIDEO_KEY_COLUMNS = (
    'topic', 'subtopic', 'subject', 'audience', 'audience_stage', 'pain', 'desire', 'problem',
    'solution_type', 'proof_type', 'hook_type', 'cta_type', 'narrative', 'positioning_type',
    'funnel_role', 'tone', 'emotion_path',
    'hook_text', 'hook_s', 'hook_words', 'setup_s', 'problem_s', 'explanation_s', 'solution_s',
    'proof_s', 'payoff_s', 'cta_s', 'total_s', 'total_words', 'wps', 'avg_sentence_len',
    'info_density', 'specificity', 'numbers_n', 'questions_n',
    'first_frame_type', 'hook_visual', 'a_roll_share', 'b_roll_share', 'split_share',
    'screen_share', 'text_overlay_density', 'scenes_n', 'avg_scene_s', 'cuts', 'cuts_per_min',
    'cut_metric_quality', 'visual_sequence', 'visual_to_script_sync',
    'play', 'likes', 'comm', 'resh', 'save', 'like_rate', 'comment_rate', 'share_rate',
    'save_rate', 'hi_intent_rate', 'creator_median_play', 'view_lift', 'share_rate_lift',
    'save_rate_lift', 'robust_z', 'percentile_in_creator', 'outlier_status',
    'creator_consistency', 'creator_n',
)

VIDEO_CSV_FIELDS = (
    ('code', 'username', 'pk_user', 'url', 'evidence_tier', 'processing_tier', 'dur')
    + VIDEO_KEY_COLUMNS
)

CREATOR_CSV_FIELDS = (
    'pk', 'username', 'snapshot_id', 'followers', 'n_videos', 'median_play', 'mean_play',
    'mad_play', 'iqr_play', 'sd_play', 'cv_play', 'median_likes', 'median_comm', 'median_resh',
    'median_save', 'median_like_rate', 'median_comment_rate', 'median_share_rate',
    'median_save_rate', 'posts_per_week', 'outlier_share', 'high_performer_share',
    'consistency_score', 'reliability', 'computed_at', 'stats_version',
    'top1_code', 'top1_robust_z', 'top1_view_lift', 'top1_play',
    'top2_code', 'top2_robust_z', 'top2_view_lift', 'top2_play',
    'top3_code', 'top3_robust_z', 'top3_view_lift', 'top3_play',
)


def now_iso():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def _median(vals):
    vals = [v for v in vals if v is not None]
    return round(statistics.median(vals), 6) if vals else None


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(statistics.mean(vals), 6) if vals else None


def _distribution(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return {'n': 0}
    qs = statistics.quantiles(vals, n=4) if len(vals) >= 4 else None
    return {
        'n': len(vals), 'min': vals[0], 'max': vals[-1],
        'median': _median(vals), 'mean': _mean(vals),
        'p25': round(qs[0], 6) if qs else None, 'p75': round(qs[2], 6) if qs else None,
    }


def db_md5(path, chunk=1 << 20):
    h = hashlib.md5()
    try:
        with open(path, 'rb') as fh:
            for block in iter(lambda: fh.read(chunk), b''):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def quartile_cutoffs(rows, min_each=None):
    """(q1, q3) of `robust_z` across `rows`, or None if too few to split honestly."""
    floor = min_each or stats.SMALL_CELL_N
    z = sorted(r['robust_z'] for r in rows if r.get('robust_z') is not None)
    if len(z) < floor * 4:
        return None
    qs = statistics.quantiles(z, n=4)
    return round(qs[0], 6), round(qs[2], 6)


def split_strong_weak(rows, cutoffs=None):
    """Top vs bottom quartile of `robust_z`, matching `engine.stats.associations`'s
    'strong_vs_weak' convention. Returns (strong, weak, (q1, q3)) or (None, None, None)."""
    cutoffs = cutoffs or quartile_cutoffs(rows)
    if cutoffs is None:
        return None, None, None
    q1, q3 = cutoffs
    strong = [r for r in rows if r.get('robust_z') is not None and r['robust_z'] >= q3]
    weak = [r for r in rows if r.get('robust_z') is not None and r['robust_z'] <= q1]
    return strong, weak, cutoffs


def confidence_label(n, n_creators):
    """Size-only confidence for a frequency/median table -- no significance test is run
    here, so this is deliberately *not* the same three labels `engine/stats.py`'s
    `associations()` uses (that RELIABLE also requires p<0.01 and a creator-normalised
    check). Reuses the same n/creator thresholds so a '5' or a '30' means the same thing
    everywhere in this codebase."""
    if n < stats.SMALL_CELL_N or n_creators < stats.SMALL_CELL_CREATORS:
        return 'INSUFFICIENT'
    if n >= stats.RELIABLE_N and n_creators >= stats.RELIABLE_CREATORS:
        return 'SUFFICIENT_SAMPLE'
    return 'PROBABLE'


CONFIDENCE_RULE_NOTE = (
    'Size-only (n videos, n creators), reusing engine.stats.SMALL_CELL_N/_CREATORS and '
    'RELIABLE_N/_CREATORS as thresholds. INSUFFICIENT: n<%d or creators<%d (suppressed_reason '
    'given, row kept). SUFFICIENT_SAMPLE: n>=%d and creators>=%d. PROBABLE: in between. This is '
    'NOT the same as associations.json confidence, which also requires p<0.01 and a '
    'creator-normalised check -- a median table with no significance test cannot claim that.'
    % (stats.SMALL_CELL_N, stats.SMALL_CELL_CREATORS, stats.RELIABLE_N, stats.RELIABLE_CREATORS)
)


# ---------------------------------------------------------------------------
# video rows (shared by videos.csv, analysis_ready.csv, charts.py, everything else)
# ---------------------------------------------------------------------------

def code_creator_map(con):
    """code -> (pk_user, username) at each code's newest reading."""
    out = {}
    for r in con.execute(corpus.LATEST_SQL):
        out[r['code']] = (r['pk_user'], r['username'])
    return out


def code_dur_map(con):
    return {r['code']: r['dur'] for r in con.execute(corpus.LATEST_SQL)}


def build_video_rows(con):
    """One dict per code in `video_features`: key columns + username/pk_user/url/dur +
    both corpus-tier vocabularies + the parsed `features_json` under `_fj` (private, not
    written to CSV/JSON verbatim -- callers pull specific blocks out of it)."""
    tier_of = corpus.tier_of(con)
    proc_tier = dict(con.execute('SELECT code, corpus_tier FROM video_state'))
    creator = code_creator_map(con)
    dur = code_dur_map(con)

    out = []
    for r in con.execute('SELECT * FROM video_features'):
        d = dict(r)
        code = d['code']
        try:
            fj = json.loads(d.get('features_json') or '{}')
        except (TypeError, ValueError):
            fj = {}
        pk_user, username = creator.get(code, (None, None))
        row = {
            'code': code,
            'username': username or d.get('username'),
            'pk_user': pk_user,
            'url': 'https://www.instagram.com/reel/%s/' % code,
            'evidence_tier': tier_of.get(code),
            'processing_tier': proc_tier.get(code),
            'dur': dur.get(code),
            '_fj': fj,
        }
        for col in VIDEO_KEY_COLUMNS:
            row[col] = d.get(col)
        out.append(row)
    return out


def script_block(row):
    return (row.get('_fj') or {}).get('script') or {}


def visual_block(row):
    return (row.get('_fj') or {}).get('visual') or {}


def semantics_extra(row):
    return (row.get('_fj') or {}).get('semantics_extra') or {}


# ---------------------------------------------------------------------------
# 1. corpus_tiers.json
# ---------------------------------------------------------------------------

def build_corpus_tiers(con):
    t = corpus.tiers(con)
    proc = collections.defaultdict(list)
    for code, tier in con.execute('SELECT code, corpus_tier FROM video_state'):
        proc[tier].append(code)
    proc_total = sum(len(v) for v in proc.values())
    return {
        'generated_at': now_iso(),
        'n_ingested': t['counts']['n_ingested'],
        'vocabularies': {
            'video_state.corpus_tier': {
                'meaning': 'processing state -- what still needs doing (engine/SPEC.md §2.2)',
                'definition': (
                    'FRAMES_ONLY = frames extracted AND transcript_state != DONE. Wider than the '
                    'literal spec reading on purpose: it also covers the 7 codes whose transcript '
                    'row is empty (Whisper heard no speech) -- see engine/HANDOFF_NOTES.md, '
                    'schema-owner §1, decision 1.'
                ),
                'n_total_with_a_state_row': proc_total,
                'tiers': {
                    tier: {'n': len(proc.get(tier, [])), 'codes': sorted(proc.get(tier, []))}
                    for tier in engine_state.CORPUS_TIERS
                },
            },
            'engine.corpus.tiers': {
                'meaning': 'evidence tier -- the denominator a report may divide by (engine/corpus.py)',
                'definition': (
                    'FRAMES_ONLY here = frames AND no transcripts row at all (narrower). The 7 '
                    'empty-transcript codes get their own TRANSCRIPT_UNUSABLE tier instead of '
                    'being folded into FRAMES_ONLY -- see docs/M2RADAR_ANALYSIS_METHOD.md §1.1.'
                ),
                'counts': t['counts'],
                'denominators': t['denominators'],
                'tier_of_code_totals': t['tier_of_code_totals'],
                'tiers': {
                    'ANALYSIS_READY': t['analysis_ready'],
                    'FRAMES_ONLY': t['frames_only'],
                    'TRANSCRIPT_UNUSABLE': t['transcript_unusable'],
                    'INGESTED_NOT_ANALYZED': t['ingested_not_analyzed'],
                },
                'transcript_no_frames': t['transcript_no_frames'],
                'orphans_not_in_reels': t['orphans_not_in_reels'],
                'newest_snapshot_id': t['snapshot_id'],
                'newest_snapshot_unprocessed': t['newest_snapshot_unprocessed'],
            },
        },
        'note': (
            'The two vocabularies disagree by design (engine/HANDOFF_NOTES.md, features-owner §1) '
            'and are not interchangeable -- every downstream report must name which one a number '
            'was divided by.'
        ),
    }


# ---------------------------------------------------------------------------
# 2. creators.csv
# ---------------------------------------------------------------------------

def build_creator_rows(con, video_rows):
    row = con.execute('SELECT MAX(snapshot_id) FROM creator_stats').fetchone()
    snap = row[0] if row else None
    creators = ([dict(r) for r in con.execute(
        'SELECT * FROM creator_stats WHERE snapshot_id=?', (snap,))] if snap is not None else [])

    by_pk = collections.defaultdict(list)
    for v in video_rows:
        if v.get('pk_user') is not None and v.get('robust_z') is not None:
            by_pk[v['pk_user']].append(v)

    out = []
    for c in creators:
        vids = sorted(by_pk.get(c['pk'], []), key=lambda v: -v['robust_z'])
        rec = dict(c)
        for i in range(3):
            pfx = 'top%d_' % (i + 1)
            if i < len(vids):
                t = vids[i]
                rec[pfx + 'code'] = t['code']
                rec[pfx + 'robust_z'] = t.get('robust_z')
                rec[pfx + 'view_lift'] = t.get('view_lift')
                rec[pfx + 'play'] = t.get('play')
            else:
                rec[pfx + 'code'] = rec[pfx + 'robust_z'] = rec[pfx + 'view_lift'] = rec[pfx + 'play'] = None
        out.append(rec)
    out.sort(key=lambda r: -(r['median_play'] or 0))
    return out, snap


# ---------------------------------------------------------------------------
# 3/4. videos.csv / analysis_ready.csv
# ---------------------------------------------------------------------------

def analysis_ready_rows(video_rows, ready_codes):
    ready_codes = set(ready_codes)
    return [r for r in video_rows if r['code'] in ready_codes]


# ---------------------------------------------------------------------------
# 5. category_freq_perf.json
# ---------------------------------------------------------------------------

def category_value_stats(rows, get_values, top_n=None):
    """`get_values(row)` returns a list of category values a row belongs to (usually one,
    several for a multi-valued field like tools_mentioned)."""
    groups = collections.defaultdict(list)
    for r in rows:
        for val in get_values(r) or []:
            if val:
                groups[val].append(r)
    out = []
    for val, grp in groups.items():
        n = len(grp)
        n_creators = len({g['pk_user'] for g in grp if g.get('pk_user') is not None})
        rec = {
            'value': val, 'n': n, 'n_creators': n_creators,
            'median_view_lift': _median([g.get('view_lift') for g in grp]),
            'median_share_rate': _median([g.get('share_rate') for g in grp]),
            'median_save_rate': _median([g.get('save_rate') for g in grp]),
            'median_robust_z': _median([g.get('robust_z') for g in grp]),
        }
        conf = confidence_label(n, n_creators)
        rec['confidence'] = conf
        if conf == 'INSUFFICIENT':
            rec['suppressed_reason'] = ('n=%d (<%d) or creators=%d (<%d)'
                                        % (n, stats.SMALL_CELL_N, n_creators, stats.SMALL_CELL_CREATORS))
        out.append(rec)
    out.sort(key=lambda d: -d['n'])
    return out[:top_n] if top_n else out


def build_category_freq_perf(video_rows):
    fields = {}
    for field, top_n in CATEGORY_FIELDS:
        fields[field] = category_value_stats(
            video_rows, lambda r, f=field: [r.get(f)], top_n=top_n)
    fields['tools_mentioned'] = category_value_stats(
        video_rows, lambda r: semantics_extra(r).get('tools_mentioned') or [], top_n=TOOLS_TOP_N)
    return {
        'generated_at': now_iso(),
        'n_videos_considered': len(video_rows),
        'confidence_rule': CONFIDENCE_RULE_NOTE,
        'fields': fields,
    }


# ---------------------------------------------------------------------------
# 6. script_parts.json
# ---------------------------------------------------------------------------

def script_stats_for(rows):
    out = {}
    for role in ROLES:
        secs, words, shares = [], [], []
        for r in rows:
            sb = script_block(r)
            if sb.get('%s_s' % role) is not None:
                secs.append(sb['%s_s' % role])
            if sb.get('%s_words' % role) is not None:
                words.append(sb['%s_words' % role])
            if sb.get('%s_share' % role) is not None:
                shares.append(sb['%s_share' % role])
        out[role] = {
            'n': len(secs),
            'median_seconds': _median(secs), 'mean_seconds': _mean(secs),
            'median_words': _median(words), 'mean_words': _mean(words),
            'median_share': _median(shares), 'mean_share': _mean(shares),
        }
    return out


def build_script_parts(video_rows):
    with_script = [r for r in video_rows if script_block(r).get('part_source') == 'beats']
    n = len(with_script)
    strong, weak, cutoffs = split_strong_weak(with_script)
    strong_weak = {'available': False,
                   'reason': 'fewer than %d rows with a script block and robust_z on each side'
                             % (4 * stats.SMALL_CELL_N)}
    if cutoffs is not None:
        strong_weak = {
            'available': True, 'q1_robust_z': cutoffs[0], 'q3_robust_z': cutoffs[1],
            'n_strong': len(strong), 'n_weak': len(weak),
            'strong': script_stats_for(strong), 'weak': script_stats_for(weak),
        }

    by_narrative = {}
    groups = collections.defaultdict(list)
    for r in with_script:
        if r.get('narrative'):
            groups[r['narrative']].append(r)
    for val, grp in groups.items():
        rec = {'n': len(grp), **script_stats_for(grp)}
        if len(grp) < stats.SMALL_CELL_N:
            rec['confidence'] = 'INSUFFICIENT'
            rec['suppressed_reason'] = 'n=%d (<%d)' % (len(grp), stats.SMALL_CELL_N)
        by_narrative[val] = rec

    topic_counts = collections.Counter(r['topic'] for r in with_script if r.get('topic'))
    by_topic = {}
    for t, cnt in topic_counts.most_common(8):
        grp = [r for r in with_script if r.get('topic') == t]
        by_topic[t] = {'n': len(grp), **script_stats_for(grp)}

    return {
        'generated_at': now_iso(), 'n': n,
        'denominator_note': (
            "codes whose script block was built from beats (features_json.script.part_source=="
            "'beats', i.e. a ta-v1 semantic parse exists) -- NOT the timing-only fallback, and "
            "NOT the full ANALYSIS_READY tier if a code has frames but no beats yet"
        ),
        'roles': list(ROLES),
        'overall': script_stats_for(with_script),
        'strong_vs_weak': strong_weak,
        'by_narrative': by_narrative,
        'by_topic_top8': by_topic,
    }


# ---------------------------------------------------------------------------
# 7. visual_patterns.json
# ---------------------------------------------------------------------------

def build_visual_patterns(video_rows):
    with_seq = [r for r in video_rows if r.get('visual_sequence')]
    seq_groups = collections.defaultdict(list)
    for r in with_seq:
        seq_groups[r['visual_sequence']].append(r)
    sequences = []
    for seq, grp in seq_groups.items():
        sequences.append({
            'sequence': seq, 'n': len(grp),
            'n_creators': len({g['pk_user'] for g in grp if g.get('pk_user') is not None}),
            'creators': sorted({g['username'] for g in grp if g.get('username')}),
            'codes': sorted(g['code'] for g in grp),
            'median_view_lift': _median([g.get('view_lift') for g in grp]),
            'median_robust_z': _median([g.get('robust_z') for g in grp]),
        })
    sequences.sort(key=lambda d: -d['n'])
    top_sequences = sequences[:10]

    transitions = collections.Counter()
    for r in video_rows:
        for k, v in (visual_block(r).get('transitions') or {}).items():
            transitions[k] += v

    with_shares = [r for r in video_rows if r.get('a_roll_share') is not None]
    strong, weak, cutoffs = split_strong_weak(with_shares)
    share_strong_weak = {'available': False,
                         'reason': 'fewer than %d rows with a roll share and robust_z on each side'
                                   % (4 * stats.SMALL_CELL_N)}
    if cutoffs is not None:
        cols = {}
        for col in ('a_roll_share', 'b_roll_share', 'split_share', 'screen_share'):
            cols[col] = {
                'median_strong': _median([r.get(col) for r in strong]),
                'median_weak': _median([r.get(col) for r in weak]),
                'n_strong': sum(1 for r in strong if r.get(col) is not None),
                'n_weak': sum(1 for r in weak if r.get(col) is not None),
            }
        share_strong_weak = {'available': True, 'q1_robust_z': cutoffs[0], 'q3_robust_z': cutoffs[1],
                             'n_strong': len(strong), 'n_weak': len(weak), 'shares': cols}

    cpm_by_quality = collections.defaultdict(list)
    for r in video_rows:
        if r.get('cuts_per_min') is not None:
            cpm_by_quality[r.get('cut_metric_quality') or 'unavailable'].append(r['cuts_per_min'])
    cuts_dist = {q: _distribution(vals) for q, vals in cpm_by_quality.items()}

    return {
        'generated_at': now_iso(),
        'n_with_visual_sequence': len(with_seq),
        'sequences_top10': top_sequences,
        'n_distinct_sequences': len(sequences),
        'transitions_observed': dict(transitions),
        'transitions_caveat': (
            "Only transitions fa-v1 actually observed between two labelled samples are counted; "
            "everything else is 'unknown' by SPEC §5 rule (never claim a cut that was not seen)."
        ),
        'roll_share_strong_vs_weak': share_strong_weak,
        'cuts_per_min_by_metric_quality': cuts_dist,
        'cuts_per_min_caveat': (
            "cut_metric_quality='ffmpeg_scene_0.35_count_only' is a scene-score threshold count, "
            "not shot-boundary detection -- relative 'busy vs calm' signal inside this dataset "
            "only, never comparable across datasets or to an external cut rate "
            "(docs/M2RADAR_ANALYSIS_METHOD.md §7.1)."
        ),
    }


# ---------------------------------------------------------------------------
# 8. alignment.json
# ---------------------------------------------------------------------------

def build_alignment(con):
    total_beats = con.execute('SELECT COUNT(*) FROM beats').fetchone()[0]
    with_scene_ids = con.execute(
        "SELECT COUNT(*) FROM beats WHERE scene_ids_json IS NOT NULL "
        "AND scene_ids_json NOT IN ('', '[]', 'null')").fetchone()[0]
    aligned_codes = con.execute(
        "SELECT COUNT(*) FROM video_state WHERE alignment_state='DONE'").fetchone()[0]
    total_codes = con.execute('SELECT COUNT(*) FROM video_state').fetchone()[0]

    base = {
        'generated_at': now_iso(),
        'n_beats_total': total_beats,
        'n_beats_with_scene_ids': with_scene_ids,
        'n_codes_alignment_done': aligned_codes,
        'n_codes_total': total_codes,
    }
    if with_scene_ids == 0:
        base['available'] = False
        base['reason'] = (
            'No beats row carries a non-empty scene_ids_json yet (alignment_state is '
            'MISSING/NOT_POSSIBLE for the whole corpus as of this run -- engine/HANDOFF_NOTES.md, '
            'pipeline-owner §3). semantic_boundary_cut_rate and related figures cannot be computed '
            'until engine/align.py writes beats.scene_ids_json for at least one code.'
        )
        return base

    # Path exercised once alignment data exists: for every beat that carries scene_ids_json,
    # check whether the beat boundary coincides with a scene start (i.e. the beat's first
    # linked scene begins at/after the beat's own start_s within a 0.3s tolerance) -- a rough,
    # explicitly-defined proxy for "does the edit cut where the script turns a corner".
    TOL = 0.3
    total_checked, aligned_boundaries = 0, 0
    per_code = collections.defaultdict(lambda: [0, 0])
    scene_starts_by_code = collections.defaultdict(list)
    for r in con.execute('SELECT code, start_s FROM scenes'):
        scene_starts_by_code[r['code']].append(r['start_s'])

    for r in con.execute(
            "SELECT code, start_s, scene_ids_json FROM beats WHERE scene_ids_json IS NOT NULL "
            "AND scene_ids_json NOT IN ('', '[]', 'null')"):
        try:
            scene_ids = json.loads(r['scene_ids_json'])
        except (TypeError, ValueError):
            scene_ids = []
        if not scene_ids or r['start_s'] is None:
            continue
        total_checked += 1
        starts = scene_starts_by_code.get(r['code'], [])
        hit = any(abs((s or 0) - r['start_s']) <= TOL for s in starts)
        aligned_boundaries += int(hit)
        per_code[r['code']][0] += int(hit)
        per_code[r['code']][1] += 1

    base['available'] = True
    base['method'] = (
        'A beat boundary counts as cut-aligned when a scene in the same code starts within '
        '%.1fs of the beat start_s. Descriptive only -- not a causal or editorial-quality claim.'
        % TOL)
    base['n_beat_boundaries_checked'] = total_checked
    base['semantic_boundary_cut_rate'] = (
        round(aligned_boundaries / total_checked, 4) if total_checked else None)
    base['by_code'] = {c: {'aligned': v[0], 'checked': v[1]} for c, v in per_code.items()}
    return base


# ---------------------------------------------------------------------------
# 9. associations.json / temporal.json
# ---------------------------------------------------------------------------

def build_associations(con):
    assoc = stats.associations(con)
    assoc = dict(assoc)
    assoc['generated_at'] = now_iso()
    assoc['source'] = 'engine.stats.associations(con) -- copied verbatim, not recomputed'
    return assoc


def build_temporal(con):
    temp = stats.temporal(con, write=False)
    slopes = [v['log_play_slope_last10'] for v in temp.values() if v.get('log_play_slope_last10') is not None]
    return {
        'generated_at': now_iso(),
        'n': len(temp),
        'denominator': 'N_ingested -- every code with a reels row and a publish ts',
        'with_rolling_median': sum(1 for v in temp.values() if v.get('ratio_to_rolling_median') is not None),
        'with_slope': len(slopes),
        'median_log_play_slope_last10': _median(slopes),
        'slope_definition': 'OLS slope of ln(1+play) on post index, last 10 posts (engine.stats._slope)',
        'rows': temp,
    }


# ---------------------------------------------------------------------------
# 10. existing_cards.json
# ---------------------------------------------------------------------------

def build_existing_cards(con):
    cards = [dict(r) for r in con.execute('SELECT * FROM cards ORDER BY id')]
    codes = [c['code'] for c in cards if c.get('code')]
    latest = {}
    if codes:
        for r in con.execute(corpus.LATEST_SQL):
            if r['code'] in codes:
                latest[r['code']] = dict(r)
    scores_by_code = collections.defaultdict(list)
    if codes:
        qmarks = ','.join('?' * len(codes))
        for r in con.execute('SELECT * FROM scores WHERE code IN (%s)' % qmarks, codes):
            scores_by_code[r['code']].append(dict(r))
    transcript_codes = {r[0] for r in con.execute('SELECT code FROM transcripts')}
    frame_codes = {r[0] for r in con.execute('SELECT code FROM frames')}

    out = []
    for c in cards:
        code = c.get('code')
        rec = dict(c)
        rec['reel'] = latest.get(code)
        rec['scores'] = scores_by_code.get(code, [])
        rec['has_transcript'] = code in transcript_codes
        rec['has_frames'] = code in frame_codes
        rec['has_reel_row'] = code in latest
        out.append(rec)
    return {
        'generated_at': now_iso(), 'n': len(out), 'source_table': 'cards (legacy, pre schema v2)',
        'cards': out,
    }


# ---------------------------------------------------------------------------
# 11. runs_jobs.json / flags.json / spend.json
# ---------------------------------------------------------------------------

def build_runs_jobs(con):
    runs = [dict(r) for r in con.execute('SELECT * FROM runs ORDER BY started_at')]
    counts = collections.Counter()
    for r in con.execute('SELECT stage, state, COUNT(*) AS n FROM jobs GROUP BY stage, state'):
        counts[(r['stage'], r['state'])] = r['n']
    return {
        'generated_at': now_iso(),
        'n_runs': len(runs), 'n_jobs': sum(counts.values()),
        'runs': runs,
        'job_counts_by_stage_state': [
            {'stage': k[0], 'state': k[1], 'n': v} for k, v in sorted(counts.items())
        ],
    }


def build_flags(con):
    counter = collections.Counter()
    n_total, n_flagged = 0, 0
    for (raw,) in con.execute('SELECT flags_json FROM video_state'):
        n_total += 1
        try:
            flags = json.loads(raw) if raw else []
        except (TypeError, ValueError):
            flags = []
        if flags:
            n_flagged += 1
        for f in flags:
            counter[f] += 1
    return {
        'generated_at': now_iso(), 'n_codes': n_total, 'n_codes_with_any_flag': n_flagged,
        'flag_vocabulary': engine_state.FLAGS, 'counts': dict(counter),
    }


def build_spend(con):
    rows = [dict(r) for r in con.execute('SELECT * FROM spend ORDER BY at')]
    total_usd = sum(r.get('usd') or 0 for r in rows)
    by_item = collections.Counter()
    for r in rows:
        by_item[r.get('item') or 'unlabelled'] += (r.get('usd') or 0)
    return {
        'generated_at': now_iso(), 'n_entries': len(rows), 'total_usd': round(total_usd, 4),
        'by_item_usd': {k: round(v, 4) for k, v in by_item.items()}, 'entries': rows,
    }


# ---------------------------------------------------------------------------
# manifest + I/O
# ---------------------------------------------------------------------------

def row_counts_all(con):
    names = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    out = {}
    for n in names:
        try:
            out[n] = con.execute('SELECT COUNT(*) FROM "%s"' % n).fetchone()[0]
        except Exception:
            out[n] = None
    return out


def _write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, sort_keys=True, indent=1, default=str)


def _write_csv(path, rows, fields):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields), extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def generate(con, out_dir):
    """Build and write every bundle. Returns the manifest dict (also written as
    manifest.json). Read-only against `con` -- see module docstring."""
    os.makedirs(out_dir, exist_ok=True)
    written = []

    def emit_json(name, obj):
        _write_json(os.path.join(out_dir, name), obj)
        written.append(name)

    def emit_csv(name, rows, fields):
        _write_csv(os.path.join(out_dir, name), rows, fields)
        written.append(name)

    t = corpus.tiers(con)
    video_rows = build_video_rows(con)

    emit_json('corpus_tiers.json', build_corpus_tiers(con))

    creator_rows, snap = build_creator_rows(con, video_rows)
    emit_csv('creators.csv', creator_rows, CREATOR_CSV_FIELDS)
    emit_csv('videos.csv', video_rows, VIDEO_CSV_FIELDS)
    emit_csv('analysis_ready.csv', analysis_ready_rows(video_rows, t['analysis_ready']), VIDEO_CSV_FIELDS)

    emit_json('category_freq_perf.json', build_category_freq_perf(video_rows))
    emit_json('script_parts.json', build_script_parts(video_rows))
    emit_json('visual_patterns.json', build_visual_patterns(video_rows))
    emit_json('alignment.json', build_alignment(con))
    emit_json('associations.json', build_associations(con))
    emit_json('temporal.json', build_temporal(con))
    emit_json('existing_cards.json', build_existing_cards(con))
    emit_json('runs_jobs.json', build_runs_jobs(con))
    emit_json('flags.json', build_flags(con))
    emit_json('spend.json', build_spend(con))

    db_file = con.execute('PRAGMA database_list').fetchone()[2]
    manifest = {
        'generated_at': now_iso(),
        'db_path': os.path.relpath(db_file, REPO) if db_file else None,
        'db_md5': db_md5(db_file) if db_file else None,
        'row_counts': row_counts_all(con),
        'n_video_rows': len(video_rows),
        'n_creator_rows': len(creator_rows),
        'creator_stats_snapshot_id': snap,
        'files': sorted(written),
    }
    _write_json(os.path.join(out_dir, 'manifest.json'), manifest)
    manifest['files'] = sorted(written + ['manifest.json'])
    return manifest


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', default=os.path.join(REPO, 'reports', 'data'))
    ap.add_argument('--db', default=corpus.DB_PATH)
    args = ap.parse_args(argv)

    con = corpus.connect(args.db)
    try:
        manifest = generate(con, args.out)
    finally:
        con.close()
    print('report_data: wrote %d files to %s (db_md5=%s)'
          % (len(manifest['files']), args.out, db_md5(args.db)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
