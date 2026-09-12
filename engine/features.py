#!/usr/bin/env python3
"""Consolidate everything known about one video into `video_features` (SPEC §2.6, V4 §17C).

Four inputs, one row:

    semantics   ta-v1 JSON `semantics` block, canonicalised to the SPEC §4 vocabularies
    script      `beats` durations folded into the eight part-length columns
    visual      `frame_labels` + `scenes` + the legacy `deepdives` cut count
    perf        written earlier by `engine/stats.py`

Everything that does not fit a key column lands in `features_json`, and the raw model
labels are kept verbatim in `raw_labels_json` — a column is a normalised claim, the JSON
is the evidence behind it.

Two things this module refuses to do:

* **Invent a part length.** If a video has no beats, the eight `*_s` columns stay NULL
  and the timing hook/body/tail fallback from `engine/lexical.py` remains the only
  part-length statement, clearly marked `boundary='timing'`. A 5-second hook by the
  clock is not a hook by meaning and the two are never mixed in the same column.
* **Call the legacy cut count a cut count.** `deepdives.cuts` is
  `ffmpeg select='gt(scene,0.35)'` frame hits — it misses cuts between two similar
  talking-head shots and fires on whip pans. `cut_metric_quality` carries that
  qualifier into every downstream table so no report can quote the number without it.

    python3 -m engine.features                  build every code that has any input
    python3 -m engine.features --code DBKJLzavogz
    python3 -m engine.features --refresh        recompute stats first, then rebuild
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine import corpus, ingest_analysis as ia, stats  # noqa: E402

FEATURES_VERSION = corpus.FEATURES_VERSION
TA_DIR = ia.TA_DIR

LEGACY_CUT_QUALITY = 'ffmpeg_scene_0.35_count_only'
SCENE_CUT_QUALITY = 'scene-v1'
NO_CUT_METRIC = 'unavailable'

# beat role -> the part-length column it contributes to (SPEC §2.6, V4 §11)
ROLE_BUCKETS = {
    'hook_s': ('hook', 'hook_extension'),
    'setup_s': ('setup', 'audience'),
    'problem_s': ('problem', 'pain', 'tension'),
    'explanation_s': ('explanation', 'mechanism', 'context'),
    'solution_s': ('solution',),
    'proof_s': ('proof', 'example'),
    'payoff_s': ('payoff', 'transformation'),
    'cta_s': ('cta', 'closing'),
}
# roles deliberately outside the eight columns: they are structural moves, not parts
UNBUCKETED_ROLES = ('objection', 'rehook', 'other')

ROLL_SHARE_COLUMNS = {'A': 'a_roll_share', 'B': 'b_roll_share', 'SPLIT': 'split_share',
                      'SCREEN': 'screen_share'}

KEY_COLUMNS = (
    'topic', 'subtopic', 'subject', 'audience', 'audience_stage', 'pain', 'desire', 'problem',
    'solution_type', 'proof_type', 'hook_type', 'cta_type', 'narrative', 'positioning_type',
    'funnel_role', 'tone', 'emotion_path',
    'hook_text', 'hook_s', 'hook_words', 'setup_s', 'problem_s', 'explanation_s', 'solution_s',
    'proof_s', 'payoff_s', 'cta_s', 'total_s', 'total_words', 'wps', 'avg_sentence_len',
    'info_density', 'specificity', 'numbers_n', 'questions_n',
    'first_frame_type', 'hook_visual', 'a_roll_share', 'b_roll_share', 'split_share',
    'screen_share', 'text_overlay_density', 'scenes_n', 'avg_scene_s', 'cuts', 'cuts_per_min',
    'cut_metric_quality', 'visual_sequence', 'visual_to_script_sync',
)


def _now():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def _round(x, n=4):
    return None if x is None else round(float(x), n)


# ---------------------------------------------------------------------------
# semantics
# ---------------------------------------------------------------------------

def _load_ta(code, ta_dir=None):
    path = os.path.join(ta_dir or TA_DIR, '%s.json' % code)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


class _NullWarn:
    """`ingest_analysis.canon` warns into a file; rebuilding features must not re-warn
    about labels the ingest already recorded."""

    def add(self, *a, **k):
        pass


def semantics_block(doc, code, legacy_topics=None):
    """ta-v1 `semantics` -> canonical column values + the raw labels kept beside them."""
    sem = (doc or {}).get('semantics') or {}
    warn = _NullWarn()
    out, raw = {}, dict(sem)
    for field, (vocab, fallback) in ia.SEMANTIC_VOCAB.items():
        out[field] = ia.canon(sem.get(field), vocab, fallback, code, field, warn)
    for field in ('subtopic', 'subject', 'audience', 'audience_stage', 'desire', 'problem',
                  'tone', 'emotion_path', 'hook_text'):
        v = sem.get(field)
        out[field] = v if isinstance(v, str) and v.strip() else None
    # topic keeps the topics.py vocabulary; the legacy tagger is the fallback and is
    # only used when it produced exactly one label (see engine/stats.feature_frame).
    topic = sem.get('topic')
    if not topic and legacy_topics is not None:
        topic = legacy_topics[0] if len(legacy_topics) == 1 else None
    out['topic'] = topic
    out['_extra'] = {k: sem.get(k) for k in
                     ('thesis', 'pain_raw', 'fear', 'aspiration', 'solution', 'mechanism',
                      'proof', 'examples', 'objection', 'payoff', 'cta', 'tools_mentioned',
                      'models_mentioned', 'numbers_used', 'rhetorical_devices', 'open_loops',
                      'pattern_interrupts') if k in sem}
    out['_interpretation'] = (doc or {}).get('interpretation')
    out['_quality'] = (doc or {}).get('quality')
    out['_confidence'] = (doc or {}).get('confidence')
    return out, raw


# ---------------------------------------------------------------------------
# script construction
# ---------------------------------------------------------------------------

def script_block(con, code, lexical=None):
    """Beat durations folded into the eight part-length columns.

    `total_s` is the sum of beat durations — the *spoken* length, which is shorter than
    the video for any reel with a silent opening or an outro card. `dur` (the video's
    own length) stays in `reels`; the two must never be swapped, so both are reported.
    """
    rows = [dict(r) for r in con.execute(
        'SELECT idx, role, start_s, end_s, duration_s, share_of_speech, text, words'
        ' FROM beats WHERE code=? ORDER BY idx', (code,))]
    if not rows:
        out = {'beats_n': 0, 'part_source': 'none'}
        if lexical and (lexical.get('blocks') or {}).get('available'):
            b = lexical['blocks']
            out.update({'part_source': 'timing_fallback',
                        'timing_hook_s': b.get('hook_span_s'), 'timing_hook_words': b.get('hook_words'),
                        'timing_body_s': b.get('body_span_s'), 'timing_body_words': b.get('body_words'),
                        'timing_tail_s': b.get('tail_span_s'), 'timing_tail_words': b.get('tail_words')})
        return out

    by_role = collections.defaultdict(lambda: {'s': 0.0, 'w': 0, 'n': 0})
    for r in rows:
        d = r['duration_s'] or 0.0
        by_role[r['role']]['s'] += d
        by_role[r['role']]['w'] += r['words'] or 0
        by_role[r['role']]['n'] += 1

    total_s = sum(v['s'] for v in by_role.values())
    total_words = sum(v['w'] for v in by_role.values())
    out = {'beats_n': len(rows), 'part_source': 'beats',
           'total_s': _round(total_s, 3), 'total_words': total_words,
           'wps': _round(total_words / total_s, 4) if total_s else None,
           'roles_present': sorted(by_role),
           'role_seconds': {k: _round(v['s'], 3) for k, v in sorted(by_role.items())},
           'role_words': {k: v['w'] for k, v in sorted(by_role.items())},
           'role_shares': {k: _round(v['s'] / total_s, 4) for k, v in sorted(by_role.items())} if total_s else {}}
    for col, roles in ROLE_BUCKETS.items():
        s = sum(by_role[r]['s'] for r in roles if r in by_role)
        out[col] = _round(s, 3) if any(r in by_role for r in roles) else None
        out[col.replace('_s', '_words')] = sum(by_role[r]['w'] for r in roles if r in by_role) or None
        out[col.replace('_s', '_share')] = _round(s / total_s, 4) if total_s and s else None
    out['unbucketed_s'] = _round(sum(by_role[r]['s'] for r in UNBUCKETED_ROLES if r in by_role), 3)
    hooks = [r for r in rows if r['role'] in ('hook', 'hook_extension')]
    out['hook_text'] = ' '.join((h['text'] or '').strip() for h in hooks).strip() or None
    out['first_beat_role'] = rows[0]['role']
    out['last_beat_role'] = rows[-1]['role']
    out['time_to_first_proof_s'] = next(
        (r['start_s'] for r in rows if r['role'] in ('proof', 'example')), None)
    out['time_to_solution_s'] = next(
        (r['start_s'] for r in rows if r['role'] == 'solution'), None)
    return out


# ---------------------------------------------------------------------------
# visual construction
# ---------------------------------------------------------------------------

def visual_block(con, code, fa_doc=None, dur=None):
    """frame_labels + scenes + the legacy deepdives cut count."""
    labels = [dict(r) for r in con.execute(
        'SELECT idx, t_sec, frame_type, roll, text_overlay, ui_present, face_present,'
        ' is_visual_hook, is_cta_visual, is_proof_visual, visual_density'
        ' FROM frame_labels WHERE code=? ORDER BY idx', (code,))]
    scenes = [dict(r) for r in con.execute(
        'SELECT idx, start_s, end_s, duration_s, scene_type, transition_in, boundary_reason'
        ' FROM scenes WHERE code=? ORDER BY idx', (code,))]
    dd = con.execute('SELECT cuts, cuts_ps FROM deepdives WHERE code=?', (code,)).fetchone()

    out = {'frames_labelled': len(labels), 'scenes_n': len(scenes) or None}
    if labels:
        n = len(labels)
        out['share_basis'] = 'labelled samples (%d fixed frames)' % n
        rolls = collections.Counter(l['roll'] for l in labels if l['roll'])
        for roll, col in ROLL_SHARE_COLUMNS.items():
            out[col] = _round(rolls.get(roll, 0) / n)
        out['text_roll_share'] = _round(rolls.get('TEXT', 0) / n)
        overlays = [l['text_overlay'] for l in labels if l['text_overlay'] is not None]
        out['text_overlay_density'] = _round(sum(overlays) / len(overlays)) if overlays else None
        out['ui_share'] = _round(sum(1 for l in labels if l['ui_present']) / n)
        out['face_share'] = _round(sum(1 for l in labels if l['face_present']) / n)
        out['frame_type_counts'] = dict(collections.Counter(
            l['frame_type'] for l in labels if l['frame_type']))
        out['first_frame_type'] = labels[0]['frame_type']
        hook_frames = [l for l in labels if l['is_visual_hook']]
        out['hook_visual'] = hook_frames[0]['frame_type'] if hook_frames else labels[0]['frame_type']
        out['has_cta_visual'] = int(any(l['is_cta_visual'] for l in labels))
        out['has_proof_visual'] = int(any(l['is_proof_visual'] for l in labels))
        dens = collections.Counter(l['visual_density'] for l in labels if l['visual_density'])
        out['visual_density_mode'] = dens.most_common(1)[0][0] if dens else None
        # deduplicated runs, exactly the SPEC §5 definition of visual_sequence
        seq = []
        for l in labels:
            if l['frame_type'] and (not seq or seq[-1] != l['frame_type']):
                seq.append(l['frame_type'])
        out['visual_sequence'] = '>'.join(seq) or None
        out['visual_sequence_len'] = len(seq)

    if scenes:
        durs = [s['duration_s'] for s in scenes if s['duration_s'] is not None]
        out['avg_scene_s'] = _round(statistics.mean(durs), 3) if durs else None
        out['median_scene_s'] = _round(statistics.median(durs), 3) if durs else None
        out['scene_boundary_reason'] = scenes[0].get('boundary_reason')
        trans = collections.Counter(s['transition_in'] for s in scenes[1:] if s['transition_in'])
        out['transitions'] = dict(trans)
        out['transitions_observed_n'] = sum(v for k, v in trans.items() if k != 'unknown')
        if not out.get('visual_sequence'):
            seq = []
            for s in scenes:
                if s['scene_type'] and (not seq or seq[-1] != s['scene_type']):
                    seq.append(s['scene_type'])
            out['visual_sequence'] = '>'.join(seq) or None

    detector = any(s.get('boundary_reason') == 'detector' for s in scenes)
    if detector:
        out['cuts'] = max(len(scenes) - 1, 0)
        out['cuts_per_min'] = _round(out['cuts'] * 60.0 / dur, 3) if dur else None
        out['cut_metric_quality'] = SCENE_CUT_QUALITY
    elif dd and dd['cuts'] is not None:
        out['cuts'] = dd['cuts']
        out['cuts_per_min'] = _round(dd['cuts'] * 60.0 / dur, 3) if dur else None
        out['cut_metric_quality'] = LEGACY_CUT_QUALITY
        out['cut_metric_caveat'] = (
            "ffmpeg select='gt(scene,0.35)' frame count. Misses cuts between similar "
            "talking-head shots, fires on whip pans and screen scrolls. Relative signal "
            "inside this dataset only; never comparable to an external cut rate.")
    else:
        out['cuts'] = None
        out['cuts_per_min'] = None
        out['cut_metric_quality'] = NO_CUT_METRIC

    if fa_doc:
        out['first_frame_type'] = fa_doc.get('first_frame_type') or out.get('first_frame_type')
        # fa-v1 writes `hook_visual` as free prose. The column is grouped on, so it holds
        # the derived frame_type; the model's description keeps its own key.
        out['hook_visual_note'] = fa_doc.get('hook_visual')
        out['visual_to_script_sync'] = fa_doc.get('sync_notes')
        out['fa_limitations'] = fa_doc.get('limitations')
        out['caption_style'] = fa_doc.get('caption_style')
        out['background'] = fa_doc.get('background')
        # the model's own share estimates are kept beside ours, never instead of them
        out['shares_estimated_by_model'] = {
            k: fa_doc.get(k) for k in ('a_roll_share_est', 'b_roll_share_est',
                                       'split_share_est', 'screen_share_est')
            if fa_doc.get(k) is not None}
        if fa_doc.get('text_overlay_density') is not None and out.get('text_overlay_density') is None:
            out['text_overlay_density'] = fa_doc.get('text_overlay_density')
    return out


def _load_fa(code):
    path = os.path.join(ia.FA_DIR, '%s.json' % code)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def build(con, code, write=True, legacy_topics=None, dur=None, perf=None, lexical=None):
    """Consolidate one code. Returns (columns, features_json_blocks)."""
    corpus.ensure_tables(con)
    row = con.execute('SELECT features_json, raw_labels_json FROM video_features WHERE code=?',
                      (code,)).fetchone()
    existing = {}
    if row:
        try:
            existing = json.loads(row[0] or '{}')
        except (TypeError, ValueError):
            existing = {}
    if lexical is None:
        lexical = existing.get('lexical') or {}
    if perf is None:
        perf = existing.get('perf') or {}
    if dur is None:
        r = con.execute('SELECT dur FROM reels WHERE code=? ORDER BY snapshot_id DESC LIMIT 1',
                        (code,)).fetchone()
        dur = r[0] if r else None
    if legacy_topics is None:
        legacy_topics = [t for (t,) in con.execute('SELECT topic FROM topics WHERE code=?', (code,))]

    ta = _load_ta(code)
    fa = _load_fa(code)
    sem, raw_sem = semantics_block(ta, code, legacy_topics)
    script = script_block(con, code, lexical)
    visual = visual_block(con, code, fa, dur)

    cols = {}
    for field in ('topic', 'subtopic', 'subject', 'audience', 'audience_stage', 'pain', 'desire',
                  'problem', 'solution_type', 'proof_type', 'hook_type', 'cta_type', 'narrative',
                  'positioning_type', 'funnel_role', 'tone', 'emotion_path'):
        cols[field] = sem.get(field)

    cols['hook_text'] = sem.get('hook_text') or script.get('hook_text')
    for col in ROLE_BUCKETS:
        cols[col] = script.get(col)
    cols['hook_words'] = script.get('hook_words')
    cols['total_s'] = script.get('total_s')
    cols['total_words'] = script.get('total_words') or (lexical.get('words') or None)
    cols['wps'] = script.get('wps') or lexical.get('wps')
    cols['avg_sentence_len'] = lexical.get('avg_sentence_len')
    cols['info_density'] = lexical.get('info_density')
    cols['specificity'] = lexical.get('specificity')
    cols['numbers_n'] = lexical.get('numbers_n')
    cols['questions_n'] = lexical.get('questions_n')

    for col in ('first_frame_type', 'hook_visual', 'a_roll_share', 'b_roll_share', 'split_share',
                'screen_share', 'text_overlay_density', 'scenes_n', 'avg_scene_s', 'cuts',
                'cuts_per_min', 'cut_metric_quality', 'visual_sequence', 'visual_to_script_sync'):
        cols[col] = visual.get(col)

    for col in stats.PERF_COLUMNS:
        if col in perf:
            cols[col] = perf[col]

    blocks = {'semantics': {k: v for k, v in sem.items() if not k.startswith('_')},
              'semantics_extra': sem.get('_extra'),
              'interpretation': sem.get('_interpretation'),
              'quality': sem.get('_quality'),
              'analysis_confidence': sem.get('_confidence'),
              'script': script, 'visual': visual,
              'inputs': {'ta_v1': bool(ta), 'fa_v1': bool(fa), 'beats': script.get('beats_n', 0),
                         'frame_labels': visual.get('frames_labelled', 0),
                         'lexical': bool(lexical), 'perf': bool(perf), 'dur': dur},
              'built_at': _now(), 'features_version': FEATURES_VERSION}

    if write:
        # One write. `cols` is written in full, Nones included: every value in it was
        # recomputed from the current inputs, so leaving a stale label behind would be
        # worse than clearing it. Keys owned by other modules ('lexical', 'perf',
        # 'temporal') are carried over untouched.
        data = dict(existing)
        data.update(blocks)
        corpus.merge_features(con, code, None, None, columns=cols,
                              features_version=FEATURES_VERSION)
        con.execute('UPDATE video_features SET features_json=?, raw_labels_json=? WHERE code=?',
                    (json.dumps(data, ensure_ascii=False, sort_keys=True, default=str),
                     json.dumps(raw_sem, ensure_ascii=False, sort_keys=True, default=str)
                     if raw_sem else None, code))
    return cols, blocks


def build_all(con, code=None, verbose=True):
    """Build for every code that has any input: beats, frame labels, a lexical block or perf."""
    corpus.ensure_tables(con)
    if code:
        codes = [code]
    else:
        codes = set()
        for q in ('SELECT DISTINCT code FROM beats', 'SELECT DISTINCT code FROM frame_labels',
                  'SELECT DISTINCT code FROM scenes'):
            codes |= {r[0] for r in con.execute(q)}
        for r in con.execute("SELECT code, features_json FROM video_features"):
            try:
                fj = json.loads(r[1] or '{}')
            except (TypeError, ValueError):
                continue
            if fj.get('lexical'):
                codes.add(r[0])
        codes = sorted(codes)

    topics = collections.defaultdict(list)
    for c, t in con.execute('SELECT code, topic FROM topics'):
        topics[c].append(t)
    durs = {r['code']: r['dur'] for r in con.execute(corpus.LATEST_SQL)}

    n = 0
    for c in codes:
        build(con, c, write=True, legacy_topics=topics.get(c, []), dur=durs.get(c))
        n += 1
        if verbose and n % 100 == 0:
            print('  ... %d/%d' % (n, len(codes)))
    con.commit()
    if verbose:
        filled = con.execute('SELECT COUNT(*) FROM video_features WHERE hook_type IS NOT NULL').fetchone()[0]
        vis = con.execute('SELECT COUNT(*) FROM video_features WHERE first_frame_type IS NOT NULL').fetchone()[0]
        scr = con.execute('SELECT COUNT(*) FROM video_features WHERE hook_s IS NOT NULL').fetchone()[0]
        print('features: built %d codes | semantics %d | script parts %d | visual %d'
              % (n, filled, scr, vis))
    return n


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    db = argv[argv.index('--db') + 1] if '--db' in argv else corpus.DB_PATH
    code = argv[argv.index('--code') + 1] if '--code' in argv else None
    con = corpus.connect(db)
    if '--refresh' in argv:
        from engine import stats
        print('refreshing stats first ...')
        stats.creator_stats(con)
        stats.video_perf(con)
        stats.temporal(con)
    build_all(con, code)
    if code:
        row = con.execute('SELECT * FROM video_features WHERE code=?', (code,)).fetchone()
        if row:
            print(json.dumps({k: row[k] for k in row.keys() if k != 'features_json'
                              and row[k] is not None}, ensure_ascii=False, indent=1, default=str))
    con.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
