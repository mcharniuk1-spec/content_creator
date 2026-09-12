#!/usr/bin/env python3
"""Load the LLM analysis JSON files into the database (SPEC §4, §5).

    data/analysis/transcripts/<code>.json   schema ta-v1  -> beats
    data/analysis/frames/<code>.json        schema fa-v1  -> frame_labels + scenes

Two rules govern everything here.

**Unknown labels are never thrown away and never silently accepted.** SPEC §4 fixes
closed vocabularies so that frequency analysis means something; a model that answers
`talking_head_closeup` instead of `A_ROLL_CLOSE_UP` would otherwise fragment the data
into synonyms. So the canonical column gets `other` / `UNKNOWN`, the raw string is kept
in `labels_json.raw`, and a line goes into `data/analysis/ingest_warnings.md` naming the
code, the field and the value. Nothing is lost and nothing is invented.

**Legacy scenes are sampled, not detected.** The old corpus has 9 fixed frames per
video (0.4/1.2/2.4/4.0 s then evenly spaced). A "scene" here is one run of consecutive
samples that carry the same `frame_type`, its start is the first sample's timecode, and
`boundary_reason='sampled'` says exactly that. A transition is written only if the
fa-v1 output observed one; otherwise `transition_in='unknown'`. SPEC §5 is explicit:
never claim a cut that was not seen.

    python3 -m engine.ingest_analysis --transcripts --frames
    python3 -m engine.ingest_analysis --frames --code DUGghN2E82c
"""
from __future__ import annotations

import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine import corpus  # noqa: E402

TA_DIR = os.path.join(REPO, 'data', 'analysis', 'transcripts')
FA_DIR = os.path.join(REPO, 'data', 'analysis', 'frames')
WARN_PATH = os.path.join(REPO, 'data', 'analysis', 'ingest_warnings.md')

TA_SCHEMA = 'ta-v1'
FA_SCHEMA = 'fa-v1'
LEGACY_FRAMES_VERSION = 'fixed9-v1'

# --- canonical vocabularies (SPEC §4) --------------------------------------

BEAT_ROLES = {'hook', 'hook_extension', 'setup', 'context', 'audience', 'problem', 'pain',
              'tension', 'explanation', 'mechanism', 'solution', 'proof', 'example',
              'objection', 'transformation', 'payoff', 'cta', 'closing', 'rehook', 'other'}

FRAME_TYPES = {'A_ROLL_TALKING_HEAD', 'A_ROLL_CLOSE_UP', 'A_ROLL_MEDIUM', 'A_ROLL_WIDE',
               'B_ROLL_CONTEXT', 'B_ROLL_PRODUCT', 'B_ROLL_PROCESS', 'SCREEN_RECORDING',
               'SCREENSHOT', 'UI_DEMO', 'SPLIT_SCREEN', 'TEXT_ONLY', 'DATA_VISUAL', 'MEME',
               'PROOF_VISUAL', 'HOOK_VISUAL', 'CTA_VISUAL', 'TRANSITION', 'MOTION_GRAPHIC',
               'OVERLAY', 'UNKNOWN'}

ROLLS = {'A', 'B', 'SPLIT', 'SCREEN', 'TEXT', 'OTHER'}

TRANSITIONS = {'hard_cut', 'jump_cut', 'zoom_cut', 'match_cut', 'swipe', 'fade',
               'overlay_reveal', 'split_reveal', 'text_punch_in', 'ui_zoom', 'broll_replace',
               'unknown', 'hard_cut_or_more'}

FRAMINGS = {'close_up', 'medium', 'wide', 'screen', 'none'}
DENSITIES = {'low', 'medium', 'high'}

HOOK_TYPES = {'question', 'bold_claim', 'contrarian', 'curiosity_gap', 'number_stat',
              'story_open', 'problem_call_out', 'demo_first', 'result_first', 'warning_fear',
              'identity_call', 'list_promise', 'other'}
PAINS = {'time_waste', 'chaos_no_process', 'dont_know_where_to_start', 'tool_overload',
         'cost_money', 'fear_of_replacement', 'quality_trust', 'missing_skills',
         'slow_response_to_leads', 'manual_repetition', 'scaling_without_hiring',
         'keeping_up_with_ai', 'other'}
SOLUTION_TYPES = {'workflow_recipe', 'tool_walkthrough', 'prompt_technique', 'agent_build',
                  'comparison', 'framework_mental_model', 'case_story', 'warning_dont',
                  'resource_handoff', 'other'}
PROOF_TYPES = {'screen_demo', 'numbers', 'before_after', 'personal_story', 'client_story',
               'authority_claim', 'third_party_data', 'none'}
CTA_TYPES = {'comment_keyword', 'follow', 'save_share', 'link_in_bio', 'dm', 'free_resource',
             'next_video', 'question_to_audience', 'none'}
NARRATIVES = {'problem_solution', 'listicle', 'tutorial_steps', 'story_arc',
              'contrast_before_after', 'myth_bust', 'announcement_news', 'rant_opinion',
              'demo_walkthrough', 'other'}
FUNNEL_ROLES = {'awareness', 'trust', 'conversion'}
POSITIONING_TYPES = {'educator', 'builder', 'news', 'seller', 'entertainer'}

# field -> (vocabulary, fallback)
SEMANTIC_VOCAB = {
    'hook_type': (HOOK_TYPES, 'other'), 'pain': (PAINS, 'other'),
    'solution_type': (SOLUTION_TYPES, 'other'), 'proof_type': (PROOF_TYPES, 'none'),
    'cta_type': (CTA_TYPES, 'none'), 'narrative': (NARRATIVES, 'other'),
    'funnel_role': (FUNNEL_ROLES, None), 'positioning_type': (POSITIONING_TYPES, None),
}


class Warnings:
    """Collected, then appended to data/analysis/ingest_warnings.md in one block."""

    def __init__(self):
        self.lines = []

    def add(self, code, field, value, note=''):
        self.lines.append((code, field, value, note))

    def __len__(self):
        return len(self.lines)

    def flush(self, path=WARN_PATH):
        if not self.lines:
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new = not os.path.exists(path)
        with open(path, 'a', encoding='utf-8') as fh:
            if new:
                fh.write('# Analysis ingest warnings\n\n'
                         'Written by `engine/ingest_analysis.py`. Every line is a label the '
                         'model produced that is not in the SPEC §4 vocabulary. The raw value '
                         'is kept in the row (`labels_json` / `raw_labels_json`); the canonical '
                         'column was set to the fallback. Recurring values here are candidates '
                         'for the vocabulary or for a prompt fix.\n')
            fh.write('\n## %s\n\n' % datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))
            fh.write('| code | field | raw value | note |\n|---|---|---|---|\n')
            for code, field, value, note in self.lines:
                fh.write('| %s | %s | `%s` | %s |\n' % (code, field, value, note))
        return path


def canon(value, vocab, fallback, code, field, warn):
    """Map a label onto the closed vocabulary, warning when it does not fit."""
    if value is None or value == '':
        return None
    v = str(value).strip()
    if v in vocab:
        return v
    upper = v.upper().replace(' ', '_').replace('-', '_')
    lower = v.lower().replace(' ', '_').replace('-', '_')
    for cand in (upper, lower):
        if cand in vocab:
            return cand
    warn.add(code, field, v, 'not in vocabulary -> %s' % fallback)
    return fallback


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# transcripts (ta-v1) -> beats
# ---------------------------------------------------------------------------

def validate_ta(doc, path):
    """Required fields per SPEC §5. Returns a list of problems; empty means loadable."""
    problems = []
    if not isinstance(doc, dict):
        return ['not a JSON object']
    if doc.get('analysis_version') != TA_SCHEMA:
        problems.append('analysis_version is %r, expected %r' % (doc.get('analysis_version'), TA_SCHEMA))
    if not doc.get('code'):
        problems.append('missing code')
    beats = doc.get('beats')
    if not isinstance(beats, list) or not beats:
        problems.append('beats missing or empty')
    else:
        for i, b in enumerate(beats):
            if not isinstance(b, dict):
                problems.append('beat %d is not an object' % i)
                continue
            if not b.get('role'):
                problems.append('beat %d has no role' % i)
            if b.get('text') is None:
                problems.append('beat %d has no text' % i)
    return problems


def ingest_transcript_doc(con, doc, warn):
    """One ta-v1 document -> `beats` rows. INSERT OR REPLACE, so re-running is free."""
    code = doc['code']
    version = doc.get('analysis_version', TA_SCHEMA)
    beats = doc.get('beats') or []

    # share_of_speech divides by the speech seconds of the video, not by its duration:
    # a 60 s reel with 40 s of speech would otherwise never sum to 1.
    durations = []
    for b in beats:
        s, e = _num(b.get('start_s')), _num(b.get('end_s'))
        durations.append((e - s) if (s is not None and e is not None and e >= s) else None)
    speech_seconds = sum(d for d in durations if d) or None
    if speech_seconds is None:
        speech_seconds = _speech_seconds_from_db(con, code)

    rows = []
    for i, b in enumerate(beats):
        idx = int(b.get('idx', i))
        role = canon(b.get('role'), BEAT_ROLES, 'other', code, 'beat.role', warn)
        s, e = _num(b.get('start_s')), _num(b.get('end_s'))
        dur = durations[i]
        text = b.get('text') or ''
        rows.append((
            '%s-B%d' % (code, idx), code, idx, role, s, e,
            round(dur, 3) if dur is not None else None,
            round(dur / speech_seconds, 6) if dur is not None and speech_seconds else None,
            text, len(text.split()), text.count('.') + text.count('!') + text.count('?') or None,
            b.get('audience_function'), b.get('emotion'), b.get('intention'), b.get('persuasion'),
            json.dumps(b.get('key_phrases') or [], ensure_ascii=False),
            json.dumps(b.get('segment_idx') or [], ensure_ascii=False),
            json.dumps(b.get('scene_ids')) if b.get('scene_ids') else None,
            json.dumps(b.get('frame_idx')) if b.get('frame_idx') else None,
            b.get('visual_state'), version))
    con.execute('DELETE FROM beats WHERE code=?', (code,))
    con.executemany(
        'INSERT OR REPLACE INTO beats (beat_id, code, idx, role, start_s, end_s, duration_s,'
        ' share_of_speech, text, words, sentences, audience_function, emotion, intention,'
        ' persuasion, key_phrases_json, segment_idx_json, scene_ids_json, frame_idx_json,'
        ' visual_state, analysis_version) VALUES (%s)' % ','.join('?' * 21), rows)
    return len(rows)


def _speech_seconds_from_db(con, code):
    row = con.execute('SELECT segments FROM transcripts WHERE code=?', (code,)).fetchone()
    if not row:
        return None
    try:
        segs = json.loads(row[0] or '[]')
    except (TypeError, ValueError):
        return None
    tot = sum(float(s.get('e', 0)) - float(s.get('s', 0)) for s in segs
              if s.get('s') is not None and s.get('e') is not None)
    return tot or None


# ---------------------------------------------------------------------------
# frames (fa-v1) -> frame_labels + scenes
# ---------------------------------------------------------------------------

def validate_fa(doc, path):
    problems = []
    if not isinstance(doc, dict):
        return ['not a JSON object']
    if doc.get('analysis_version') != FA_SCHEMA:
        problems.append('analysis_version is %r, expected %r' % (doc.get('analysis_version'), FA_SCHEMA))
    if not doc.get('code'):
        problems.append('missing code')
    frames = doc.get('frames')
    if not isinstance(frames, (list, dict)) or not frames:
        problems.append('frames missing or empty')
    return problems


def _frame_items(doc):
    """fa-v1 allows either a list of frame objects or an {idx: obj} map."""
    frames = doc.get('frames')
    if isinstance(frames, dict):
        return sorted(((int(k), v) for k, v in frames.items()), key=lambda kv: kv[0])
    out = []
    for i, f in enumerate(frames or []):
        out.append((int(f.get('idx', i)), f))
    return sorted(out, key=lambda kv: kv[0])


def ingest_frames_doc(con, doc, warn):
    """One fa-v1 document -> `frame_labels` rows plus legacy `scenes` runs."""
    code = doc['code']
    version = doc.get('analysis_version', FA_SCHEMA)
    model = doc.get('model')
    frames_version = doc.get('frames_version', LEGACY_FRAMES_VERSION)
    t_by_idx = {r[0]: r[1] for r in con.execute(
        'SELECT idx, t_sec FROM frames WHERE code=?', (code,))}
    dur = con.execute('SELECT dur FROM reels WHERE code=? ORDER BY snapshot_id DESC LIMIT 1',
                      (code,)).fetchone()
    dur = dur[0] if dur else None

    items = _frame_items(doc)
    rows, labelled = [], []
    for idx, f in items:
        ftype = canon(f.get('frame_type'), FRAME_TYPES, 'UNKNOWN', code, 'frame_type', warn)
        roll = canon(f.get('roll'), ROLLS, 'OTHER', code, 'roll', warn)
        framing = canon(f.get('framing'), FRAMINGS, 'none', code, 'framing', warn)
        density = canon(f.get('visual_density'), DENSITIES, 'medium', code, 'visual_density', warn)
        t_sec = _num(f.get('t_sec'))
        if t_sec is None:
            t_sec = t_by_idx.get(idx)
        b = lambda k: (None if f.get(k) is None else int(bool(f.get(k))))  # noqa: E731
        rows.append((code, idx, t_sec, ftype, roll, b('speaker_present'), b('face_present'),
                     b('ui_present'), b('text_overlay'), f.get('overlay_text'),
                     f.get('caption_placement'), framing, f.get('dominant_action'), density,
                     b('is_visual_hook'), b('is_cta_visual'), b('is_proof_visual'),
                     json.dumps({'raw': f}, ensure_ascii=False, sort_keys=True, default=str),
                     f.get('confidence'), version, model))
        labelled.append((idx, t_sec, ftype))

    con.executemany(
        'INSERT OR REPLACE INTO frame_labels (code, idx, t_sec, frame_type, roll,'
        ' speaker_present, face_present, ui_present, text_overlay, overlay_text,'
        ' caption_placement, framing, dominant_action, visual_density, is_visual_hook,'
        ' is_cta_visual, is_proof_visual, labels_json, confidence, analysis_version, model)'
        ' VALUES (%s)' % ','.join('?' * 21), rows)

    n_scenes = _write_legacy_scenes(con, code, labelled, doc, frames_version, dur, warn)
    return len(rows), n_scenes


def _transitions_by_to_idx(observed):
    """fa-v1 writes `transitions_observed` as [{from_idx, to_idx, kind}, ...].

    Older drafts used a plain list or a map, so all three shapes are accepted; the
    result is always {to_idx: kind}, because a scene's `transition_in` is the
    transition that lands on its first frame.
    """
    out = {}
    if isinstance(observed, dict):
        for k, v in observed.items():
            try:
                out[int(k)] = v.get('kind') if isinstance(v, dict) else v
            except (TypeError, ValueError):
                continue
    elif isinstance(observed, list):
        for i, v in enumerate(observed):
            if isinstance(v, dict):
                to_idx = v.get('to_idx', v.get('idx', i + 1))
                try:
                    out[int(to_idx)] = v.get('kind')
                except (TypeError, ValueError):
                    continue
            else:
                out[i + 1] = v
    return out


def _write_legacy_scenes(con, code, labelled, doc, frames_version, dur, warn):
    """One scene per run of consecutive samples carrying the same frame_type.

    This is an interpolation between 9 points, not a detection. `boundary_reason` says
    'sampled' and every duration is "from this sample to the next", which is why a
    scene here can be 4.5 s long when the real shot was 0.6 s.
    """
    labelled = [x for x in labelled if x[1] is not None]
    con.execute('DELETE FROM scenes WHERE code=? AND frames_version=?', (code, frames_version))
    if not labelled:
        return 0
    labelled.sort(key=lambda x: x[1])
    observed = _transitions_by_to_idx(doc.get('transitions_observed'))

    runs = []
    for idx, t, ftype in labelled:
        if runs and runs[-1]['scene_type'] == ftype:
            runs[-1]['frame_idx'].append(idx)
            runs[-1]['end_hint'] = t
        else:
            runs.append({'scene_type': ftype, 'start_s': t, 'frame_idx': [idx], 'end_hint': t})

    rows = []
    for i, run in enumerate(runs):
        end = runs[i + 1]['start_s'] if i + 1 < len(runs) else (dur if dur else run['end_hint'])
        if end is None or end < run['start_s']:
            end = run['start_s']
        raw = None
        if i == 0:
            transition = 'unknown'          # nothing precedes the first sample
        else:
            raw = observed.get(run['frame_idx'][0])
            if raw in (None, '', 'same_shot', 'none'):
                # 'same_shot' is fa-v1 for "these two samples are one shot". The label
                # changed but no cut was seen — SPEC §5 says never claim one.
                transition = 'unknown'
            else:
                transition = canon(raw, TRANSITIONS, 'unknown', code, 'transition_in', warn)
        rows.append(('%s-S%02d' % (code, i), code, i, run['start_s'], end,
                     round(end - run['start_s'], 3), 'sampled', run['scene_type'], transition,
                     json.dumps(run['frame_idx']), None, frames_version,
                     json.dumps({'derived_from': 'fa-v1 frame_type runs over %d samples'
                                 % len(labelled), 'boundary_confidence': 'low',
                                 'transition_raw': raw},
                                ensure_ascii=False, sort_keys=True)))
    con.executemany(
        'INSERT OR REPLACE INTO scenes (scene_id, code, idx, start_s, end_s, duration_s,'
        ' boundary_reason, scene_type, transition_in, frame_idx_json, keyframe_path,'
        ' frames_version, detector_json) VALUES (%s)' % ','.join('?' * 13), rows)
    return len(rows)


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def _refresh_state(con, codes):
    """engine/state.py is another owner's module; use it when it exists, skip when not."""
    try:
        from engine import state  # type: ignore
    except ImportError:
        return 0, 'engine.state not available yet — video_state left untouched'
    fn = getattr(state, 'refresh_video_state', None)
    if fn is None:
        return 0, 'engine.state has no refresh_video_state'
    n = 0
    for code in codes:
        try:
            fn(con, code)
            n += 1
        except Exception as exc:                                     # pragma: no cover
            return n, 'refresh_video_state failed on %s: %s' % (code, exc)
    return n, None


def run(con, transcripts=True, frames=True, code=None, ta_dir=TA_DIR, fa_dir=FA_DIR,
        warn_path=WARN_PATH, verbose=True):
    corpus.ensure_tables(con)
    warn = Warnings()
    summary = {'beats': 0, 'beat_codes': 0, 'frame_labels': 0, 'scenes': 0, 'frame_codes': 0,
               'rejected': [], 'warnings': 0, 'touched': []}

    def files(d):
        if not os.path.isdir(d):
            return []
        names = sorted(f for f in os.listdir(d) if f.endswith('.json'))
        if code:
            names = [f for f in names if f[:-5] == code]
        return [os.path.join(d, f) for f in names]

    if transcripts:
        for path in files(ta_dir):
            doc = _load(path, summary)
            if doc is None:
                continue
            problems = validate_ta(doc, path)
            if problems:
                summary['rejected'].append({'file': os.path.basename(path), 'problems': problems})
                for p in problems:
                    warn.add(doc.get('code') or os.path.basename(path), 'ta-v1 validation', p)
                continue
            summary['beats'] += ingest_transcript_doc(con, doc, warn)
            summary['beat_codes'] += 1
            summary['touched'].append(doc['code'])

    if frames:
        for path in files(fa_dir):
            doc = _load(path, summary)
            if doc is None:
                continue
            problems = validate_fa(doc, path)
            if problems:
                summary['rejected'].append({'file': os.path.basename(path), 'problems': problems})
                for p in problems:
                    warn.add(doc.get('code') or os.path.basename(path), 'fa-v1 validation', p)
                continue
            nf, ns = ingest_frames_doc(con, doc, warn)
            summary['frame_labels'] += nf
            summary['scenes'] += ns
            summary['frame_codes'] += 1
            summary['touched'].append(doc['code'])

    con.commit()
    summary['warnings'] = len(warn)
    summary['warnings_path'] = warn.flush(warn_path)
    touched = sorted(set(summary.pop('touched')))
    n_state, state_note = _refresh_state(con, touched)
    summary['video_state_refreshed'] = n_state
    summary['video_state_note'] = state_note
    con.commit()
    if verbose:
        print('ta-v1: %d files -> %d beats | fa-v1: %d files -> %d frame_labels, %d scenes'
              % (summary['beat_codes'], summary['beats'], summary['frame_codes'],
                 summary['frame_labels'], summary['scenes']))
        if summary['rejected']:
            print('rejected %d file(s):' % len(summary['rejected']))
            for r in summary['rejected'][:10]:
                print('  %s — %s' % (r['file'], '; '.join(r['problems'])))
        if summary['warnings']:
            print('%d vocabulary warning(s) -> %s'
                  % (summary['warnings'], summary['warnings_path']))
        if state_note:
            print(state_note)
    return summary


def _load(path, summary):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (ValueError, OSError) as exc:
        summary['rejected'].append({'file': os.path.basename(path), 'problems': ['unreadable: %s' % exc]})
        return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    db = argv[argv.index('--db') + 1] if '--db' in argv else corpus.DB_PATH
    code = argv[argv.index('--code') + 1] if '--code' in argv else None
    want_t = '--transcripts' in argv
    want_f = '--frames' in argv
    if not want_t and not want_f:
        want_t = want_f = True
    con = corpus.connect(db)
    run(con, transcripts=want_t, frames=want_f, code=code)
    con.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
