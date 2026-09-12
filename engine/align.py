#!/usr/bin/env python3
"""Segment <-> scene alignment. engine/SPEC.md §6 step 5, §2.4-2.5.

    python3 -m engine.align --code CODE

Builds a time-based overlap map between transcript segments (`transcripts.segments`)
and detected scenes (`scenes`). If `beats` exist for the code (written by the
transcript-analysis owner from an LLM pass), fills `beats.scene_ids_json` /
`frame_idx_json` / `visual_state`; otherwise the segment->scene map is stashed in
`video_state.flags_json['alignment']` for later use. Also computes the handful of
alignment features SPEC §6 asks for and returns them.

Works without `beats` (most of the corpus today) and without `frame_labels` (visual
majority just comes back None/'unknown' then) — every external table is probed with
`_table_exists` first so a fresh DB or one where another owner hasn't landed their
tables yet doesn't raise, it just returns a smaller feature set / NOT_POSSIBLE.
"""
import argparse
import collections
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import connect  # noqa: E402

try:
    from engine.local_pipeline import _ensure_tables
except ImportError:
    def _ensure_tables(con):
        pass

HOOK_WINDOW_S = 3.0
CTA_TAIL_SHARE = 0.15
BOUNDARY_TOLERANCE_S = 0.5


def _now_iso():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def _table_exists(con, name):
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _get_scenes(con, code):
    if not _table_exists(con, 'scenes'):
        return []
    rows = con.execute(
        'SELECT scene_id, idx, start_s, end_s FROM scenes WHERE code=? ORDER BY idx', (code,)).fetchall()
    return [dict(r) for r in rows]


def _get_segments(con, code):
    r = con.execute('SELECT segments FROM transcripts WHERE code=?', (code,)).fetchone()
    if not r or not r['segments']:
        return []
    try:
        segs = json.loads(r['segments'])
    except (TypeError, ValueError):
        return []
    return segs if isinstance(segs, list) else []


def _get_duration(con, code, scenes_rows):
    if scenes_rows:
        last = scenes_rows[-1]
        return last['end_s'] if last['end_s'] is not None else last['start_s']
    r = con.execute('SELECT dur FROM reels WHERE code=? ORDER BY snapshot_id DESC LIMIT 1', (code,)).fetchone()
    return (r['dur'] if r else None) or 0.0


def _get_beats(con, code):
    if not _table_exists(con, 'beats'):
        return []
    rows = con.execute(
        'SELECT beat_id, idx, start_s, end_s FROM beats WHERE code=? ORDER BY idx', (code,)).fetchall()
    return [dict(r) for r in rows]


def _frames_in_range(con, code, s, e):
    if not _table_exists(con, 'frames'):
        return []
    rows = con.execute('SELECT idx FROM frames WHERE code=? AND t_sec>=? AND t_sec<?', (code, s, e)).fetchall()
    return [r['idx'] for r in rows]


def _frame_labels_roll(con, code, frame_idx):
    if not frame_idx or not _table_exists(con, 'frame_labels'):
        return None
    qmarks = ','.join('?' * len(frame_idx))
    rows = con.execute(
        f'SELECT roll FROM frame_labels WHERE code=? AND idx IN ({qmarks})',
        [code, *frame_idx]).fetchall()
    rolls = [r['roll'] for r in rows if r['roll']]
    if not rolls:
        return None
    return collections.Counter(rolls).most_common(1)[0][0]


def _scene_for_time(t, scenes_rows):
    for sc in scenes_rows:
        end = sc['end_s'] if sc['end_s'] is not None else float('inf')
        if sc['start_s'] <= t < end:
            return sc
    return scenes_rows[-1] if scenes_rows else None


def _segment_scene_map(segments, scenes_rows):
    out = []
    for seg in segments:
        sc = _scene_for_time(seg.get('s', 0.0), scenes_rows)
        out.append({'s': seg.get('s'), 'e': seg.get('e'),
                    'scene_id': sc['scene_id'] if sc else None,
                    'scene_idx': sc['idx'] if sc else None})
    return out


def _read_flags(con, code):
    row = con.execute('SELECT flags_json FROM video_state WHERE code=?', (code,)).fetchone()
    if not row or not row['flags_json']:
        return {}, row is not None
    try:
        data = json.loads(row['flags_json'])
    except (TypeError, ValueError):
        data = {}
    return (data if isinstance(data, dict) else {}), True


def _write_flags(con, code, flags):
    payload = json.dumps(flags, ensure_ascii=False, sort_keys=True)
    exists = con.execute('SELECT 1 FROM video_state WHERE code=?', (code,)).fetchone()
    now = _now_iso()
    if exists:
        con.execute('UPDATE video_state SET flags_json=?, updated_at=? WHERE code=?', (payload, now, code))
    else:
        con.execute('INSERT INTO video_state (code, flags_json, updated_at) VALUES (?,?,?)',
                    (code, payload, now))


def _set_alignment_state(con, code, state, reason=None):
    flags, _ = _read_flags(con, code)
    if reason:
        flags['alignment_reason'] = reason
    _write_flags(con, code, flags)
    con.execute("""UPDATE video_state SET alignment_state=? WHERE code=?""", (state, code))
    if con.execute('SELECT changes()').fetchone()[0] == 0:
        con.execute('INSERT INTO video_state (code, alignment_state, updated_at) VALUES (?,?,?)',
                    (code, state, _now_iso()))
    con.commit()


def _merge_alignment_into_flags(con, code, payload):
    flags, _ = _read_flags(con, code)
    flags['alignment'] = payload
    _write_flags(con, code, flags)


def _compute_features(segments, scenes_rows, beats_rows, dur):
    features = {
        'semantic_boundary_cut_rate': None, 'visual_change_per_sentence': None,
        'scene_changes_per_beat': None, 'first_cut_s': None,
        'hook_cut_count': 0, 'cta_cut_count': 0,
    }
    cut_starts = [sc['start_s'] for sc in scenes_rows if sc['idx'] > 0]
    features['first_cut_s'] = cut_starts[0] if cut_starts else None
    features['hook_cut_count'] = sum(1 for c in cut_starts if c <= HOOK_WINDOW_S)
    tail_from = dur * (1 - CTA_TAIL_SHARE) if dur else None
    features['cta_cut_count'] = (
        sum(1 for c in cut_starts if tail_from is not None and c >= tail_from) if dur else 0)

    if segments and scenes_rows:
        seg_starts = [s.get('s', 0.0) for s in segments]
        near = sum(1 for c in cut_starts if any(abs(c - ss) <= BOUNDARY_TOLERANCE_S for ss in seg_starts))
        features['semantic_boundary_cut_rate'] = round(near / len(cut_starts), 3) if cut_starts else 0.0
    if segments:
        features['visual_change_per_sentence'] = round(len(scenes_rows) / len(segments), 3)
    if beats_rows:
        features['scene_changes_per_beat'] = round(len(scenes_rows) / len(beats_rows), 3)
    return features


def align(con, code):
    """Returns the alignment feature dict; also sets video_state.alignment_state to
    DONE or NOT_POSSIBLE (with a reason recorded in flags_json)."""
    _ensure_tables(con)
    scenes_rows = _get_scenes(con, code)
    if not scenes_rows:
        reason = 'no scenes for this code'
        _set_alignment_state(con, code, 'NOT_POSSIBLE', reason=reason)
        return {'alignment_state': 'NOT_POSSIBLE', 'reason': reason}

    segments = _get_segments(con, code)
    dur = _get_duration(con, code, scenes_rows)
    beats_rows = _get_beats(con, code)

    # per engine/HANDOFF_NOTES.md (schema-owner, §3 "For the local-pipeline owner"):
    # engine.state.compute_video_state only reports alignment_state=DONE when a code
    # has at least one `beats` row with a non-empty scene_ids_json. A bare
    # segment->scene map (no beats yet) is real, useful data for later, but it is not
    # itself a finished alignment — so it leaves alignment_state at MISSING, matching
    # what the authoritative recompute would say if it ran right after this.
    any_beat_aligned = False
    if beats_rows:
        for b in beats_rows:
            b_end = b['end_s'] if b['end_s'] is not None else dur
            overlapping = [sc for sc in scenes_rows
                           if sc['start_s'] < b_end and (sc['end_s'] if sc['end_s'] is not None else dur) > b['start_s']]
            scene_ids = [sc['scene_id'] for sc in overlapping]
            frame_idx = []
            for sc in overlapping:
                frame_idx.extend(_frames_in_range(con, code, sc['start_s'],
                                                   sc['end_s'] if sc['end_s'] is not None else dur))
            visual_state = _frame_labels_roll(con, code, frame_idx) or 'unknown'
            con.execute('UPDATE beats SET scene_ids_json=?, frame_idx_json=?, visual_state=? WHERE beat_id=?',
                        (json.dumps(scene_ids), json.dumps(frame_idx), visual_state, b['beat_id']))
            if scene_ids:
                any_beat_aligned = True
    elif segments:
        seg_scene_map = _segment_scene_map(segments, scenes_rows)
        _merge_alignment_into_flags(con, code, {'segment_scene_map': seg_scene_map})

    features = _compute_features(segments, scenes_rows, beats_rows, dur)
    state = 'DONE' if any_beat_aligned else 'MISSING'
    con.execute("""UPDATE video_state SET alignment_state=? WHERE code=?""", (state, code))
    if con.execute('SELECT changes()').fetchone()[0] == 0:
        con.execute('INSERT INTO video_state (code, alignment_state, updated_at) VALUES (?,?,?)',
                    (code, state, _now_iso()))
    con.commit()
    return features


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--code', required=True)
    args = ap.parse_args(argv)
    con = connect()
    feats = align(con, args.code)
    print(json.dumps(feats, indent=2, ensure_ascii=False, default=str))
    con.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
