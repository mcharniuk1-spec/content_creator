#!/usr/bin/env python3
"""Load insights / hypotheses / hypothesis_refs JSON into the database (engine/SPEC.md §2.8,
V4 §21A-D).

    data/analysis/insights.json          -> insights
    data/analysis/hypotheses.json        -> hypotheses
    data/analysis/hypothesis_refs.json   -> hypothesis_refs

Same rule as `engine/ingest_analysis.py`: a value outside a closed vocabulary is never
silently accepted and never silently dropped. Here the stakes are one level higher than a
label -- `confidence` and `function` gate whether a report is allowed to say a claim is
reliable, and whether a card generator is allowed to borrow a reference for a given
purpose -- so a record that fails validation is **not inserted**, and every rejection is
named in `data/analysis/ingest_insights_warnings.md` with the id, the field and the value.
A soft problem (a supporting/candidate code that is not literally wrong, just not found in
`reels`) is a warning, not a rejection: the record is still inserted, because that code is
evidence *about* the corpus, not a value *from* a closed vocabulary.

Idempotent: INSERT OR REPLACE on each table's primary key, so re-running after a JSON file
is edited replaces the row rather than duplicating it.

    python3 -m engine.ingest_insights                 load all three files
    python3 -m engine.ingest_insights --dry            validate only, write nothing
    python3 -m engine.ingest_insights --run-id ABC123  attach to an existing run instead of
                                                        opening a new 'analysis' run
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine import corpus  # noqa: E402
from engine import state as engine_state  # noqa: E402
from engine.db_util import canonical_json  # noqa: E402

DATA_DIR = os.path.join(REPO, 'data', 'analysis')
INSIGHTS_PATH = os.path.join(DATA_DIR, 'insights.json')
HYPOTHESES_PATH = os.path.join(DATA_DIR, 'hypotheses.json')
REFS_PATH = os.path.join(DATA_DIR, 'hypothesis_refs.json')
WARN_PATH = os.path.join(DATA_DIR, 'ingest_insights_warnings.md')

# --- canonical vocabularies (SPEC §2.8) -------------------------------------

CONFIDENCE_LABELS = {'RELIABLE', 'PROBABLE', 'INSUFFICIENT'}
HYPOTHESIS_STATUS = {'PROPOSED', 'SELECTED', 'REJECTED'}
HYPOTHESIS_REF_FUNCTIONS = {
    'topic', 'hook', 'pain', 'explanation', 'proof', 'cta', 'a_roll', 'b_roll', 'split',
    'screen_proof', 'rhythm', 'transition',
}


def _now():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


# ---------------------------------------------------------------------------
# warnings
# ---------------------------------------------------------------------------

class Warnings:
    """Collected, then appended to `data/analysis/ingest_insights_warnings.md` in one block
    (same shape as `engine/ingest_analysis.py`'s `Warnings`, kept as a separate class here
    because that module's header text is specific to its own label-vocabulary domain)."""

    def __init__(self):
        self.lines = []

    def add(self, entity_id, field, value, note=''):
        self.lines.append((entity_id, field, value, note))

    def __len__(self):
        return len(self.lines)

    def flush(self, path=WARN_PATH):
        if not self.lines:
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new = not os.path.exists(path)
        with open(path, 'a', encoding='utf-8') as fh:
            if new:
                fh.write(
                    '# Insights/hypotheses ingest warnings\n\n'
                    'Written by `engine/ingest_insights.py`. A rejected record (bad confidence '
                    'label, bad hypothesis_refs.function, missing required field) is never '
                    'inserted; a soft warning (a supporting/candidate code not found in `reels` '
                    'or without a `video_features` row) does not block insertion, it is a fact '
                    'about the evidence, kept here rather than invented away.\n')
            fh.write('\n## %s\n\n' % datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))
            fh.write('| id | field | value | note |\n|---|---|---|---|\n')
            for entity_id, field, value, note in self.lines:
                fh.write('| %s | %s | `%s` | %s |\n' % (entity_id, field, value, note))
        return path


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def _load_list(path, summary_key, summary):
    if not os.path.exists(path):
        summary.setdefault('missing_files', []).append(os.path.relpath(path, REPO))
        return []
    try:
        with open(path, encoding='utf-8') as fh:
            doc = json.load(fh)
    except (ValueError, OSError) as exc:
        summary.setdefault('unreadable_files', []).append(
            {'file': os.path.relpath(path, REPO), 'error': str(exc)})
        return []
    if not isinstance(doc, list):
        summary.setdefault('malformed_files', []).append(
            {'file': os.path.relpath(path, REPO), 'error': 'top level is not a JSON list'})
        return []
    return doc


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

def validate_insight(rec, valid_codes, warn):
    problems = []
    iid = rec.get('insight_id')
    if not iid:
        problems.append('missing insight_id')
    if not rec.get('statement'):
        problems.append('missing statement')
    conf = rec.get('confidence')
    if conf not in CONFIDENCE_LABELS:
        problems.append('confidence %r not in %s' % (conf, sorted(CONFIDENCE_LABELS)))
    for code in rec.get('supporting_codes') or []:
        if code not in valid_codes:
            warn.add(iid or '?', 'supporting_codes', code, 'code not found in reels')
    return problems


def validate_hypothesis(rec, warn):
    """Returns (problems, normalised_record). `status` is coerced to PROPOSED (the schema
    default) with a warning rather than rejected -- unlike `confidence`/`function`, an
    unrecognised status is not evidence-bearing, it is a workflow label the DB already
    defaults safely."""
    problems = []
    hid = rec.get('hypothesis_id')
    if not hid:
        problems.append('missing hypothesis_id')
    if not rec.get('title'):
        problems.append('missing title')
    if not rec.get('statement'):
        problems.append('missing statement')
    conf = rec.get('confidence')
    if conf is not None and conf not in CONFIDENCE_LABELS:
        warn.add(hid or '?', 'confidence', conf, 'not in %s' % sorted(CONFIDENCE_LABELS))
    rec = dict(rec)
    status = rec.get('status') or 'PROPOSED'
    if status not in HYPOTHESIS_STATUS:
        warn.add(hid or '?', 'status', status,
                 'not in %s, coerced to PROPOSED' % sorted(HYPOTHESIS_STATUS))
        status = 'PROPOSED'
    rec['status'] = status
    return problems, rec


def validate_ref(rec, valid_codes, features_codes, warn):
    problems = []
    hid, code = rec.get('hypothesis_id'), rec.get('code')
    if not hid:
        problems.append('missing hypothesis_id')
    if not code:
        problems.append('missing code')
    if not rec.get('reason'):
        problems.append('missing reason')
    fn = rec.get('function')
    if fn not in HYPOTHESIS_REF_FUNCTIONS:
        problems.append('function %r not in %s' % (fn, sorted(HYPOTHESIS_REF_FUNCTIONS)))
    if code and code not in valid_codes:
        problems.append('code %s not found in reels' % code)
    elif code and code not in features_codes:
        # a real reel, just not analysed yet -- softer than "not found at all", still a
        # rejection: a reference with no video_features row has no performance evidence to
        # attach (SPEC §2.8 hypothesis_refs.performance_json).
        problems.append('code %s has no video_features row' % code)
    return problems


# ---------------------------------------------------------------------------
# inserts
# ---------------------------------------------------------------------------

def insert_insight(con, rec, run_id):
    con.execute(
        'INSERT OR REPLACE INTO insights (insight_id, run_id, statement, claim, metric, n, '
        'comparison, evidence_json, supporting_codes_json, supporting_creators_json, '
        'transcript_pattern, frame_pattern, interpretation, implication, confidence, '
        'limitations, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (rec['insight_id'], run_id, rec['statement'], rec.get('claim'), rec.get('metric'),
         rec.get('n'), rec.get('comparison'), canonical_json(rec.get('evidence')),
         canonical_json(rec.get('supporting_codes')), canonical_json(rec.get('supporting_creators')),
         rec.get('transcript_pattern'), rec.get('frame_pattern'), rec.get('interpretation'),
         rec.get('implication'), rec['confidence'], rec.get('limitations'),
         rec.get('created_at') or _now()))


def insert_hypothesis(con, rec, run_id):
    con.execute(
        'INSERT OR REPLACE INTO hypotheses (hypothesis_id, run_id, title, statement, audience, '
        'positioning_fit, pain, desired_outcome, hook, thesis, mechanism, proof, cta, '
        'visual_structure, format, supporting_insights_json, candidate_refs_json, strengths, '
        'risks, novelty, confidence, scores_json, total_score, reviewer_comment, status, '
        'card_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (rec['hypothesis_id'], run_id, rec['title'], rec['statement'], rec.get('audience'),
         rec.get('positioning_fit'), rec.get('pain'), rec.get('desired_outcome'), rec.get('hook'),
         rec.get('thesis'), rec.get('mechanism'), rec.get('proof'), rec.get('cta'),
         rec.get('visual_structure'), rec.get('format'),
         canonical_json(rec.get('supporting_insights')), canonical_json(rec.get('candidate_refs')),
         rec.get('strengths'), rec.get('risks'), rec.get('novelty'), rec.get('confidence'),
         canonical_json(rec.get('scores')), rec.get('total_score'), rec.get('reviewer_comment'),
         rec['status'], rec.get('card_id'), rec.get('created_at') or _now()))


def insert_ref(con, rec):
    con.execute(
        'INSERT OR REPLACE INTO hypothesis_refs (hypothesis_id, code, function, reason, '
        'useful_beat_ids_json, useful_scene_ids_json, performance_json, transformation) '
        'VALUES (?,?,?,?,?,?,?,?)',
        (rec['hypothesis_id'], rec['code'], rec['function'], rec['reason'],
         canonical_json(rec.get('useful_beat_ids')), canonical_json(rec.get('useful_scene_ids')),
         canonical_json(rec.get('performance')), rec.get('transformation')))


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def run(con, run_id=None, dry=False, insights_path=INSIGHTS_PATH, hypotheses_path=HYPOTHESES_PATH,
        refs_path=REFS_PATH, warn_path=WARN_PATH, verbose=True):
    corpus.ensure_tables(con)
    warn = Warnings()
    summary = {
        'dry_run': dry, 'insights': 0, 'hypotheses': 0, 'hypothesis_refs': 0,
        'rejected_insights': [], 'rejected_hypotheses': [], 'rejected_refs': [],
    }

    own_run = False
    if run_id is None and not dry:
        try:
            run_id = engine_state.start_run(con, 'analysis')
            own_run = True
        except Exception as exc:
            warn.add('-', 'run_id', repr(exc), 'engine.state.start_run failed; ingesting without one')
            run_id = None
    summary['run_id'] = run_id

    valid_codes = {r[0] for r in con.execute('SELECT DISTINCT code FROM reels')}
    features_codes = {r[0] for r in con.execute('SELECT DISTINCT code FROM video_features')}

    # --- insights ------------------------------------------------------
    insights_doc = _load_list(insights_path, 'insights', summary)
    inserted_insight_ids = []
    for rec in insights_doc:
        problems = validate_insight(rec, valid_codes, warn)
        if problems:
            summary['rejected_insights'].append({'insight_id': rec.get('insight_id'), 'problems': problems})
            for p in problems:
                warn.add(rec.get('insight_id') or '?', 'insight', p, 'rejected, not inserted')
            continue
        if not dry:
            insert_insight(con, rec, run_id)
        inserted_insight_ids.append(rec['insight_id'])
        summary['insights'] += 1
    if inserted_insight_ids and not dry and run_id:
        try:
            with engine_state.job(con, run_id, 'corpus', 'corpus', 'GENERAL_ANALYSIS') as j:
                j.set(output_refs_json=inserted_insight_ids, data_version='insights.json')
        except Exception as exc:
            warn.add('-', 'jobs', repr(exc), 'job trace for insights batch failed, insights still inserted')

    # --- hypotheses ------------------------------------------------------
    hyp_doc = _load_list(hypotheses_path, 'hypotheses', summary)
    for rec in hyp_doc:
        problems, norm = validate_hypothesis(rec, warn)
        if problems:
            summary['rejected_hypotheses'].append({'hypothesis_id': rec.get('hypothesis_id'), 'problems': problems})
            for p in problems:
                warn.add(rec.get('hypothesis_id') or '?', 'hypothesis', p, 'rejected, not inserted')
            continue
        if not dry:
            insert_hypothesis(con, norm, run_id)
            if run_id:
                try:
                    with engine_state.job(con, run_id, 'hypothesis', norm['hypothesis_id'],
                                          'CONCEPT_GENERATION') as j:
                        j.set(data_version='hypotheses.json')
                except Exception as exc:
                    warn.add(norm['hypothesis_id'], 'jobs', repr(exc), 'job trace failed, hypothesis still inserted')
        summary['hypotheses'] += 1

    # --- hypothesis_refs ---------------------------------------------------
    refs_doc = _load_list(refs_path, 'hypothesis_refs', summary)
    refs_by_hypothesis = {}
    for rec in refs_doc:
        problems = validate_ref(rec, valid_codes, features_codes, warn)
        key = (rec.get('hypothesis_id'), rec.get('code'), rec.get('function'))
        if problems:
            summary['rejected_refs'].append({'ref': key, 'problems': problems})
            for p in problems:
                warn.add('%s/%s/%s' % key, 'hypothesis_refs', p, 'rejected, not inserted')
            continue
        if not dry:
            insert_ref(con, rec)
        refs_by_hypothesis.setdefault(rec['hypothesis_id'], []).append(rec['code'])
        summary['hypothesis_refs'] += 1
    if not dry and run_id:
        for hid, codes in refs_by_hypothesis.items():
            try:
                with engine_state.job(con, run_id, 'hypothesis', hid, 'REFERENCE_SELECTION') as j:
                    j.set(output_refs_json=codes, data_version='hypothesis_refs.json')
            except Exception as exc:
                warn.add(hid, 'jobs', repr(exc), 'job trace failed, refs still inserted')

    if not dry:
        con.commit()
        if own_run:
            try:
                engine_state.finish_run(con, run_id, 'DONE', summary)
            except Exception as exc:
                warn.add('-', 'runs', repr(exc), 'finish_run failed after a successful ingest')

    summary['warnings'] = len(warn)
    summary['warnings_path'] = warn.flush(warn_path) if not dry else None
    if dry and len(warn):
        summary['dry_run_warnings_preview'] = warn.lines[:20]

    if verbose:
        print('insights: %d ingested, %d rejected | hypotheses: %d ingested, %d rejected | '
              'hypothesis_refs: %d ingested, %d rejected%s'
              % (summary['insights'], len(summary['rejected_insights']),
                 summary['hypotheses'], len(summary['rejected_hypotheses']),
                 summary['hypothesis_refs'], len(summary['rejected_refs']),
                 ' [DRY RUN, nothing written]' if dry else ''))
        for key in ('missing_files', 'unreadable_files', 'malformed_files'):
            if summary.get(key):
                print('%s: %s' % (key, summary[key]))
        if summary['warnings']:
            print('%d warning(s)%s' % (summary['warnings'],
                                       ' -> %s' % summary['warnings_path'] if summary['warnings_path'] else ' (dry run, not written)'))
    return summary


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db', default=corpus.DB_PATH)
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--run-id', default=None)
    ap.add_argument('--insights', default=INSIGHTS_PATH)
    ap.add_argument('--hypotheses', default=HYPOTHESES_PATH)
    ap.add_argument('--refs', default=REFS_PATH)
    args = ap.parse_args(argv)

    con = corpus.connect(args.db)
    try:
        summary = run(con, run_id=args.run_id, dry=args.dry, insights_path=args.insights,
                      hypotheses_path=args.hypotheses, refs_path=args.refs)
    finally:
        con.close()
    return 0 if not (summary['rejected_insights'] or summary['rejected_hypotheses']
                    or summary['rejected_refs']) else 1


if __name__ == '__main__':
    sys.exit(main())
