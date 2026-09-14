#!/usr/bin/env python3
"""Read one transactionally consistent corpus checkpoint; never mutate its ledger."""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import pathlib
import sqlite3


def snapshot(run_root, output):
    run_root, output = pathlib.Path(run_root), pathlib.Path(output)
    source = run_root / 'corpus-media.sqlite'
    if source.is_symlink() or not source.is_file():
        raise ValueError('LEDGER_UNAVAILABLE_OR_SYMLINK')
    if output.exists() or output.is_symlink() or any(
            p.is_symlink() and str(p) not in {'/tmp', '/var'} for p in output.absolute().parents):
        raise ValueError('NEW_CHECKPOINT_DIRECTORY_REQUIRED')
    db = sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        reels = [dict(r) for r in db.execute('SELECT * FROM reels ORDER BY identity_index')]
        attempts = [dict(r) for r in db.execute('SELECT * FROM attempts ORDER BY id')]
        event = db.execute('SELECT MAX(id) FROM events').fetchone()[0]
        bindings = [list(r) for r in db.execute('SELECT * FROM binding')]
    finally:
        db.close()
    latest = {(a['reel_id'], a['stage']): a for a in attempts}
    rows = []
    for reel in reels:
        row = {k: reel[k] for k in ('reel_id', 'code', 'identity_index', 'acquisition_state',
                                    'transcript_state', 'frames_state', 'scene_review_state')}
        for stage in ('acquisition', 'transcript', 'frames'):
            a = latest.get((reel['reel_id'], stage), {})
            resources = json.loads(a.get('resources_json') or '{}')
            metrics = resources.get('metrics') or {}
            row[stage + '_attempt'] = a.get('attempt')
            row[stage + '_error'] = a.get('error')
            row[stage + '_attempt_state'] = a.get('state')
            row[stage + '_elapsed_seconds'] = resources.get('elapsed_seconds')
            row[stage + '_sampled_peak_rss_bytes'] = resources.get('sampled_peak_rss_bytes')
            if stage == 'transcript':
                for name in ('lexical_word_count', 'aligned_word_count', 'unaligned_word_count',
                             'language', 'word_timing'):
                    row[name] = metrics.get(name)
            if stage == 'frames':
                row['sampled_frame_count'] = resources.get('sample_count')
                row['cut_candidates_count'] = resources.get('cut_candidates')
        rows.append(row)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    states = {field: dict(collections.Counter(r[field] for r in rows)) for field in
              ('acquisition_state', 'transcript_state', 'frames_state', 'scene_review_state')}
    report = {'schema': 'm2.corpus-progress-checkpoint.v1', 'observed_at': now,
              'population': len(rows), 'last_event_id': event, 'bindings': bindings,
              'states': states, 'full_population_denominator': len(rows),
              'speech_bearing_population': None, 'verified_transcript_accuracy': None,
              'notes': ['OBSERVED transcript is machine output, not independently verified accuracy.',
                        'Blank metrics mean unavailable, never zero.',
                        'Cut candidates and sampled frames are not verified semantic scenes.',
                        'Latest attempt may be running; checkpoint is an explicit dated partial state.',
                        'Acquisition route errors remain in the linked acquisition ledger.']}
    output.mkdir(parents=True)
    dataset = output / 'all-reels-progress.csv'
    with dataset.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['reel_id'])
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(
                ('=', '+', '-', '@', '\t', '\r')) else v for k, v in row.items()})
    report['dataset_sha256'] = hashlib.sha256(dataset.read_bytes()).hexdigest()
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.run_root, args.output), indent=2))
