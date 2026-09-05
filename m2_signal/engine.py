"""Snapshot-isolated, immutable, stdlib-only Signal export adapter.

No network code or credential handling is present. Raw exports and the database
are run-local source evidence; publish only a separately reviewed projection.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sqlite3
import statistics
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .metrics import (FORMULA_VERSION, candidate_key, distribution, metric_definition,
                      rate, robust_z, validate_config, wilson)
from .taxonomy import TOPIC_SLUGS

PACKAGE = Path(__file__).parent
SOURCE_NAMES = {
    'reels': ('reels.csv', 'ролики.csv'),
    'accounts': ('accounts.csv', 'аккаунты.csv'),
    'transcripts': ('transcripts.json', 'расшифровки.json'),
    'cuts': ('cuts.json', 'склейки.json'),
    'topics': ('topics.csv', 'окно-14-дней-с-темами.csv'),
}
COUNTERS = {'views': 'play', 'likes': 'like', 'comments': 'comment', 'reshares': 'reshare', 'saves': 'save'}
MODALITIES = ('transcript', 'cut_summary', 'source_media', 'frames', 'shots', 'semantic_scenes', 'comments')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode()).hexdigest()


def file_hash(path):
    with Path(path).open('rb') as f:
        h = hashlib.file_digest(f, 'sha256') if hasattr(hashlib, 'file_digest') else hashlib.sha256(f.read())
    return h.hexdigest()


def implementation_hash():
    return digest({p.name: file_hash(p) for p in sorted(PACKAGE.iterdir()) if p.suffix in ('.py', '.sql')})


def connect(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=30000')
    db.executescript((PACKAGE/'schema.sql').read_text())
    # SQL-level immutability also protects direct connector users from accidental overwrite.
    for table in ('releases', 'sources', 'release_sources', 'observations', 'release_observations',
                  'reel_analysis', 'account_analysis', 'evidence_attempts', 'metric_observations', 'reel_metric_values'):
        for operation in ('UPDATE', 'DELETE'):
            db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable evidence'); END")
    return db


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('missing or duplicate CSV columns')
        rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError('unexpected CSV column count')
        return rows


def _sources(source_dir):
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise ValueError('source directory does not exist')
    names = defaultdict(list)
    for p in source_dir.iterdir():
        if p.is_file():
            names[unicodedata.normalize('NFC', p.name)].append(p)
    result = {}
    for kind, aliases in SOURCE_NAMES.items():
        matches = [p for alias in aliases for p in names.get(alias, [])]
        if len(matches) > 1:
            raise ValueError('ambiguous source alias: ' + kind)
        if matches:
            result[kind] = matches[0]
    snapshots = [p for name, ps in names.items() if name == 'snapshot.json' or (name.startswith('снимок-') and name.endswith('.json')) for p in ps]
    if len(snapshots) != 1:
        raise ValueError('exactly one snapshot.json or dated snapshot JSON required')
    result['snapshot'] = snapshots[0]
    if not {'reels', 'accounts'} <= set(result):
        raise ValueError('reels and accounts CSV required')
    return result


def ingest_export(db_path, source_dir, config=None):
    """Register one complete export snapshot; unchanged rows dedupe across imports.

    New snapshots/configs are independent releases. Repeated imports of a growing
    export reuse unchanged observation hashes without replacing previous values.
    Snapshot CSV/JSON corroboration is required when snapshot.rows is present.
    """
    cfg = validate_config(config)
    paths = _sources(source_dir)
    manifest = {kind: {'logical_name': p.name, 'sha256': file_hash(p), 'size_bytes': p.stat().st_size}
                for kind, p in sorted(paths.items())}
    data = {kind: read_csv(p) if p.suffix == '.csv' else json.loads(p.read_text(encoding='utf-8-sig'))
            for kind, p in paths.items()}
    snapshot = data['snapshot']
    snapshot_date = date.fromisoformat(snapshot['taken']).isoformat()
    required = {'code', 'user', 'play', 'like', 'comment', 'reshare', 'save', 'duration_s', 'ts'}
    if data['reels'] and not required <= set(data['reels'][0]):
        raise ValueError('reels export missing required source fields')
    if data['accounts'] and 'username' not in data['accounts'][0]:
        raise ValueError('accounts export missing username')
    if 'accounts' in snapshot and snapshot['accounts'] != len(data['accounts']):
        raise ValueError('snapshot account count mismatch')
    if 'rows' in snapshot:
        if len(snapshot['rows']) != len(data['reels']):
            raise ValueError('snapshot observation count mismatch')
        fields = {'code': 'code', 'user': 'user', 'ts': 'ts', 'play': 'play', 'like': 'like',
                  'comm': 'comment', 'resh': 'reshare', 'save': 'save', 'dur': 'duration_s'}
        for left, right in zip(data['reels'], snapshot['rows']):
            for jk, ck in fields.items():
                a, b = left[ck], right.get(jk)
                # Values are corroborated numerically; blank source counters remain null.
                if jk in ('code', 'user'):
                    agrees = a == b
                else:
                    agrees = (a in (None, '') and b is None) or (a not in (None, '') and b is not None and Decimal(str(a)) == Decimal(str(b)))
                if not agrees:
                    raise ValueError('snapshot/csv observation disagreement in ' + ck)
    # Only the explicitly supplied export folder is searched; no device-wide media crawl.
    media = []
    media_root = Path(source_dir).resolve()
    for media_path in sorted(media_root.rglob('*')):
        if not media_path.is_file() or media_path.suffix.lower() not in ('.mp4', '.mov', '.webm', '.mkv', '.m4v'):
            continue
        if not media_path.resolve().is_relative_to(media_root):
            continue
        media.append({'code': media_path.stem, 'evidence': {'relative_path': media_path.relative_to(media_root).as_posix(),
                      'sha256': file_hash(media_path), 'size_bytes': media_path.stat().st_size,
                      'media_decoded': False}})
    data['source_media'] = media
    inventory_data = canonical(media).encode()
    manifest['source_media'] = {'logical_name': 'bounded-media-inventory.v1',
                                'sha256': digest(inventory_data), 'size_bytes': len(inventory_data),
                                'virtual_source': True, 'scope': 'supplied export directory only'}
    corpus_hash = digest(manifest)
    config_hash = digest(cfg)
    code_hash = implementation_hash()
    release_id = 'signal-' + digest([corpus_hash, config_hash, code_hash])[:24]
    db = connect(db_path)
    before = db.execute('SELECT count(*) FROM observations').fetchone()[0]
    try:
        with db:
            db.execute('INSERT OR IGNORE INTO releases VALUES (?,?,?,?,?,?,?)',
                       (release_id, corpus_hash, config_hash, code_hash, snapshot_date, canonical(cfg), canonical(manifest)))
            for kind, entry in manifest.items():
                db.execute('INSERT OR IGNORE INTO sources VALUES (?,?,?)', (entry['sha256'], entry['logical_name'], entry['size_bytes']))
                db.execute('INSERT OR IGNORE INTO release_sources VALUES (?,?,?)', (release_id, kind, entry['sha256']))
            for kind in ('reels', 'accounts', 'topics', 'transcripts', 'cuts', 'source_media'):
                if kind not in data:
                    continue
                values = data[kind]
                if kind in ('transcripts', 'cuts'):
                    if not isinstance(values, dict):
                        raise ValueError('code-keyed JSON object required: ' + kind)
                    values = [{'code': key, 'evidence': value} for key, value in sorted(values.items())]
                for line, payload in enumerate(values, 2 if kind in ('reels', 'accounts', 'topics') else 1):
                    entity = str(payload.get('username' if kind == 'accounts' else 'code', ''))
                    payload_hash = digest(payload)
                    # Duplicate occurrences share immutable values; lineage keeps every source row.
                    observation_id = 'obs-' + digest([snapshot_date, kind, entity, payload_hash])
                    db.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?)',
                               (observation_id, snapshot_date, kind, entity, payload_hash, canonical(payload)))
                    if kind == 'reels':
                        for metric, native in COUNTERS.items():
                            value, error = _number(payload.get(native), integer=True)
                            db.execute('INSERT OR IGNORE INTO metric_observations (observation_id,metric_name,native_field_name,value_integer,observation_state,reason_code) VALUES (?,?,?,?,?,?)',
                                       (observation_id, metric, native, value, 'OBSERVED' if value is not None else 'PARTIAL' if error else 'NOT_ATTEMPTED',
                                        error or ('NULL_IN_EXPORT' if value is None else None)))
                    db.execute('INSERT OR IGNORE INTO release_observations VALUES (?,?,?,?,?)',
                               (release_id, kind, manifest[kind]['sha256'], line, observation_id))
        after = db.execute('SELECT count(*) FROM observations').fetchone()[0]
        return {'schema_version': 'signal-ingest.v1', 'release_id': release_id, 'snapshot_date': snapshot_date,
                'corpus_sha256': corpus_hash, 'config_sha256': config_hash, 'implementation_sha256': code_hash,
                'source_observations': len(data['reels']), 'account_source_rows': len(data['accounts']),
                'new_immutable_records': after-before, 'immutable_records_in_database': after,
                'observation_policy': 'value deduplication with all source-row memberships preserved',
                'collection_state': 'SKIPPED_DISABLED', 'external_calls': 0}
    finally:
        db.close()


def _rows(db, release_id, kind):
    return [dict(r) | {'payload': json.loads(r['payload_json'])} for r in db.execute(
        'SELECT o.*,r.source_row,r.source_sha256 FROM release_observations r JOIN observations o USING(observation_id) '
        'WHERE r.release_id=? AND r.kind=? ORDER BY r.source_row', (release_id, kind))]


def _number(value, integer=False):
    if value is None or str(value).strip() == '':
        return None, None
    try:
        if isinstance(value, bool):
            return None, 'BOOLEAN_IS_NOT_COUNTER'
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or (integer and (number != number.to_integral_value() or number > 9223372036854775807)):
            return None, 'INVALID_NONNEGATIVE_INTEGER' if integer else 'INVALID_NONNEGATIVE_NUMBER'
        result = int(number) if integer else float(number)
        if not integer and not math.isfinite(result):
            return None, 'INVALID_NONNEGATIVE_NUMBER'
        return result, None
    except (ValueError, TypeError, OverflowError, InvalidOperation):
        return None, 'UNPARSEABLE_NUMBER'


def _consensus(rows, field):
    xs = {canonical(row.get(field)) for row in rows}
    return json.loads(next(iter(xs))) if len(xs) == 1 else None


def _iso(epoch):
    try:
        return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace('+00:00', 'Z') if epoch is not None else None
    except (OverflowError, OSError, ValueError):
        return None


def _evidence_attempt(release, reel, modality, legacy):
    code = reel['code']
    record = legacy.get(code)
    result = {'evidence_id': 'ev-' + digest([release['release_id'], reel['reel_id'], modality]),
              'release_id': release['release_id'], 'reel_id': reel['reel_id'], 'modality': modality,
              'observation_state': 'NOT_ATTEMPTED', 'eligibility_state': 'UNKNOWN',
              'review_state': 'NOT_REVIEWED', 'release_state': 'DRAFT',
              'reason_code': 'MISSING_SOURCE_MEDIA' if modality in ('source_media', 'frames', 'shots', 'semantic_scenes') else 'NOT_PRESENT_IN_EXPORT',
              'source_observation_id': None, 'source_sha256': None,
              'words': None, 'segment_count': None, 'cut_count': None,
              'acquisition_attempted': False, 'media_decoded': False}
    if record is not None:
        evidence = record['payload']['evidence']
        result.update(source_observation_id=record['observation_id'], source_sha256=record['payload_sha256'])
        if modality == 'transcript':
            words, error = _number(evidence.get('words'), integer=True)
            segments = evidence.get('segments') or []
            if not isinstance(segments, list):
                segments = []
                error = 'MALFORMED_SEGMENTS'
            result.update(words=words, segment_count=len(segments),
                          observation_state='PARTIAL', reason_code='LEGACY_ASR_PROVENANCE_AND_MEDIA_QA_UNVERIFIED')
            if error:
                result.update(eligibility_state='FAIL', reason_code=error)
            elif not words or not any(str(s.get('t', '')).strip() for s in segments if isinstance(s, dict)):
                result.update(reason_code='EMPTY_ASR_SILENCE_OR_FAILURE_UNRESOLVED')
            result['timecode_validation'] = 'NOT_MEDIA_VERIFIED'
        elif modality == 'source_media':
            result.update(observation_state='PARTIAL', reason_code='LOCAL_FILE_PRESENT_NOT_DECODED',
                          file_sha256=evidence.get('sha256'), relative_path=evidence.get('relative_path'),
                          size_bytes=evidence.get('size_bytes'))
        elif modality == 'cut_summary':
            count, error = _number(evidence.get('cuts'), integer=True)
            result.update(cut_count=count, observation_state='PARTIAL', reason_code=error or 'COARSE_COUNT_ONLY_NO_TIMECODED_SHOTS')
            if error:
                result['eligibility_state'] = 'FAIL'
    if reel['identity_conflict']:
        result['eligibility_state'] = 'FAIL'
        result['attribution_reason'] = 'QUARANTINED_IDENTITY_CONFLICT'
    return result


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n')


def _write_jsonl(path, rows):
    path.write_text(''.join(canonical(row)+'\n' for row in rows))


def _csv(path, rows):
    if not rows:
        path.write_text('')
        return
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            clean = {k: canonical(v) if isinstance(v, (list, dict)) else v for k, v in row.items()}
            # Protect spreadsheet consumers against formula injection in untrusted strings.
            clean = {k: "'"+v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for k, v in clean.items()}
            writer.writerow(clean)


def analyze(db_path, release_id, output_dir):
    """Calculate a snapshot-specific release; never accept strategic Best decisions."""
    db = connect(db_path)
    try:
        release_row = db.execute('SELECT * FROM releases WHERE release_id=?', (release_id,)).fetchone()
        if release_row is None:
            raise ValueError('unknown release')
        release = dict(release_row)
        if release['implementation_sha256'] != implementation_hash():
            raise ValueError('implementation changed; ingest again to create a new release')
        cfg = json.loads(release['config_json'])
        source = _rows(db, release_id, 'reels')
        account_sources = _rows(db, release_id, 'accounts')
        transcripts = {r['entity_key']: r for r in _rows(db, release_id, 'transcripts')}
        cuts = {r['entity_key']: r for r in _rows(db, release_id, 'cuts')}
        media = {r['entity_key']: r for r in _rows(db, release_id, 'source_media')}
        topic_rows = defaultdict(list)
        for r in _rows(db, release_id, 'topics'):
            topic_rows[r['entity_key']].append(r['payload'])
        grouped = defaultdict(list)
        for r in source:
            grouped[r['entity_key'] or 'unresolved:'+r['observation_id']].append(r)
        reels = []
        for code, observations in sorted(grouped.items()):
            rows = [r['payload'] for r in observations]
            fields = sorted(set().union(*(r.keys() for r in rows)))
            conflicts = [k for k in fields if len({canonical(r.get(k)) for r in rows}) > 1]
            # Distinct measurements of the same snapshot require adjudication. Identical values dedupe.
            identity_conflict = bool(conflicts)
            row = {'reel_id': 'instagram:'+code, 'code': code, 'platform': 'instagram_reels',
                   'snapshot_date': release['snapshot_date'], 'observed_at': None, 'capture_time_state': 'DATE_ONLY',
                   'release_id': release_id, 'source_row_count': len(rows),
                   'source_row_numbers': [r['source_row'] for r in observations],
                   'observation_ids': sorted({r['observation_id'] for r in observations}),
                   'identity_conflict': identity_conflict, 'conflicting_fields': conflicts,
                   'account_username': _consensus(rows, 'user'), 'url': _consensus(rows, 'url'),
                   'review_state': 'NOT_REVIEWED', 'release_state': 'DRAFT', 'production_state': 'NOT_RUN',
                   'best_reel_eligibility_state': 'UNKNOWN', 'best_reel_reason': 'MARKET_RIGHTS_TEXT_SCENE_AND_INDEPENDENT_REVIEW_GAPS'}
            reasons = ['IDENTITY_CONFLICT'] if identity_conflict else []
            if code.startswith('unresolved:') or not row['account_username']:
                reasons.append('MISSING_STABLE_IDENTITY')
            for name, key in COUNTERS.items():
                row[name], error = _number(_consensus(rows, key), integer=True)
                if error:
                    reasons.append(name+':'+error)
            row['duration_seconds'], error = _number(_consensus(rows, 'duration_s'))
            if error:
                reasons.append('duration:'+error)
            row['published_epoch_seconds'], error = _number(_consensus(rows, 'ts'), integer=True)
            row['published_at_utc'] = _iso(row['published_epoch_seconds'])
            if error or (row['published_epoch_seconds'] is not None and row['published_at_utc'] is None):
                reasons.append('INVALID_PUBLICATION_TIME')
            if row['views'] == 0 and any((row[k] or 0) > 0 for k in ('likes', 'comments', 'reshares', 'saves')):
                reasons.append('ZERO_VIEWS_WITH_POSITIVE_ACTIONS')
            row['quarantine_reasons'] = reasons
            row['numeric_valid'] = not reasons
            row['metric_missing_fields'] = [k for k in COUNTERS if row[k] is None]
            row['counter_semantics_state'] = 'LEGACY_EXPORT_UNVERSIONED'
            row['topic_codes'] = []
            row['topic_state'] = 'NOT_PRESENT_IN_DATED_WINDOW'
            if not identity_conflict and len(topic_rows[code]) == 1:
                labels = [s.strip() for s in topic_rows[code][0].get('topics', '').split('|') if s.strip()]
                row['topic_codes'] = [TOPIC_SLUGS.get(label, 'unmapped_legacy_topic') for label in labels]
                row['topic_state'] = 'PROVISIONAL_CAPTION_ONLY'
            caption = _consensus(rows, 'caption')
            row['caption_sha256'] = digest(caption.encode()) if caption else None
            reels.append(row)
        raw_source_by_account = defaultdict(list)
        for item in source:
            raw_source_by_account[item['payload'].get('user')].append(item)
        by_account = defaultdict(list)
        for row in reels:
            if row['account_username']:
                by_account[row['account_username']].append(row)
        for user, items in by_account.items():
            baseline = [r['views'] for r in items if r['numeric_valid'] and r['views'] is not None and r['views'] > 0]
            med = statistics.median(baseline) if baseline else None
            for row in items:
                row['author_baseline_n'] = len(baseline)
                row['author_median_views'] = med
                row['creator_view_index'] = row['views']/med if row['numeric_valid'] and row['views'] is not None and med else None
                row['eligibility_state'] = 'UNKNOWN'
                if row['quarantine_reasons']:
                    row['eligibility_state'] = 'FAIL'
                elif row['views'] is not None and len(baseline) >= cfg['minimum_baseline_n']:
                    row['eligibility_state'] = 'PASS' if row['views'] >= max(cfg['absolute_exposure_floor'], cfg['relative_exposure_floor']*med) else 'FAIL'
                row['view_hit'] = row['creator_view_index'] >= cfg['hit_multiplier'] if row['eligibility_state'] == 'PASS' else None
                for key in ('likes', 'comments', 'reshares', 'saves'):
                    row[key+'_per_1k_views'] = rate(row[key], row['views']) if row['numeric_valid'] else None
                row['log_views'] = math.log1p(row['views']) if row['numeric_valid'] and row['views'] else None
            components = ['log_views']+[k+'_per_1k_views' for k in ('likes', 'comments', 'reshares', 'saves')]
            for key in components:
                values = [r[key] for r in items if r['eligibility_state'] == 'PASS' and r[key] is not None]
                for row in items:
                    row[key+'_baseline_n'] = len(values)
                    row[key+'_robust_z'] = robust_z(row[key], values, kind=key, config=cfg) if row['eligibility_state'] == 'PASS' else None
            for row in items:
                zs = [row[key+'_robust_z'] for key in components if row[key+'_robust_z'] is not None]
                row['diagnostic_component_count'] = len(zs)
                row['diagnostic_equal_weight_z'] = statistics.mean(zs) if len(zs) >= cfg['minimum_components'] else None
        attempts = []
        for row in reels:
            # Even unresolved ownership retains a complete audit and modality attempt row.
            row.setdefault('eligibility_state', 'FAIL')
            row.setdefault('diagnostic_component_count', 0)
            row.setdefault('diagnostic_equal_weight_z', None)
            for modality in MODALITIES:
                attempt = _evidence_attempt(release, row, modality, transcripts if modality == 'transcript' else cuts if modality == 'cut_summary' else media if modality == 'source_media' else {})
                if row['code'] in media and modality in ('frames', 'shots', 'semantic_scenes'):
                    attempt['reason_code'] = 'MEDIA_DECODE_AND_SCENE_REVIEW_NOT_RUN'
                attempts.append(attempt)
                if modality in ('transcript', 'cut_summary'):
                    row[modality+'_evidence_id'] = attempt['evidence_id']
                    row[modality+'_state'] = attempt['observation_state']
                    row['transcript_words' if modality == 'transcript' else 'cut_count'] = attempt['words' if modality == 'transcript' else 'cut_count']
        attempt_index = {(a['reel_id'], a['modality']): a for a in attempts}
        accounts = []
        source_accounts = defaultdict(list)
        for r in account_sources:
            source_accounts[r['payload']['username']].append(r['payload'])
        for user in sorted(set(source_accounts)|set(by_account)):
            items = by_account[user]
            eligible = [r for r in items if r['eligibility_state'] == 'PASS']
            valid = [r for r in items if r['numeric_valid']]
            hits = sum(bool(r['view_hit']) for r in eligible)
            n = len(eligible)
            enough = n >= cfg['minimum_baseline_n']
            low, high = wilson(hits, n) if enough else (None, None)
            scoreable = [r for r in eligible if r['diagnostic_equal_weight_z'] is not None]
            selected = max(scoreable, key=candidate_key) if scoreable else None
            unconstrained = max(scoreable, key=lambda r: candidate_key(r)[1:]) if scoreable else None
            account = {'account_username': user, 'release_id': release_id, 'snapshot_date': release['snapshot_date'],
                       'profile_source_rows': len(source_accounts[user]), 'canonical_reels': len(items),
                       'source_observations': len(raw_source_by_account[user]),
                       'source_reel_identities': len({r['entity_key'] for r in raw_source_by_account[user]}),
                       'quarantined_identity_memberships': len({r['entity_key'] for r in raw_source_by_account[user]
                           if any(x['code'] == r['entity_key'] and x['identity_conflict'] for x in reels)}),
                       'numeric_valid_reels': len(valid),
                       'exposure_eligible_reels': n, 'hit_numerator': hits, 'hit_denominator': n,
                       'hit_rate': hits/n if enough else None, 'hit_wilson95_low': low, 'hit_wilson95_high': high,
                       'hit_reason': 'DESCRIPTIVE' if enough else 'INSUFFICIENT_N',
                       'final_best_reel_id': None, 'best_reel_eligibility_state': 'UNKNOWN',
                       'best_reel_reason': 'MARKET_RIGHTS_TEXT_SCENE_AND_INDEPENDENT_REVIEW_GAPS',
                       'candidate_reel_id': selected['reel_id'] if selected else None,
                       'candidate_component_count': selected['diagnostic_component_count'] if selected else None,
                       'candidate_coverage_sensitivity_changed': selected['reel_id'] != unconstrained['reel_id'] if selected else None,
                       'distributions': {}}
            profile_rows = source_accounts[user]
            account['profile_horizon_state'] = _consensus(profile_rows, 'profile_horizon_state') if profile_rows else None
            account['followers'], follower_error = _number(_consensus(profile_rows, 'followers'), integer=True)
            account['media_count'], media_error = _number(_consensus(profile_rows, 'media_count'), integer=True)
            account['profile_category'] = _consensus(profile_rows, 'category')
            account['profile_metric_errors'] = [x for x in [follower_error,media_error] if x]
            bio = _consensus(profile_rows, 'biography')
            account['biography_sha256'] = digest(bio.encode()) if bio else None
            account['candidate_reel_url'] = selected['url'] if selected else None
            account['author_baseline_n'] = len([r for r in valid if r['views'] is not None and r['views'] > 0])
            account['author_median_views'] = statistics.median([r['views'] for r in valid if r['views'] is not None and r['views'] > 0]) if account['author_baseline_n'] else None
            for metric in ['views', 'duration_seconds', 'likes', 'comments', 'reshares', 'saves', 'cut_count', 'transcript_words']+[
                k+'_per_1k_views' for k in ('likes', 'comments', 'reshares', 'saves')]:
                account['distributions'][metric] = distribution([r.get(metric) for r in eligible], n)
            for modality in MODALITIES:
                found = [attempt_index[(r['reel_id'], modality)] for r in eligible]
                observed = sum(a['observation_state'] in ('OBSERVED', 'PARTIAL') for a in found)
                account[modality+'_observed_n'] = observed
                account[modality+'_coverage'] = observed/n if n else None
            accounts.append(account)
        ranking = sorted([r for r in reels if r['diagnostic_equal_weight_z'] is not None], key=candidate_key, reverse=True)
        ranking_rows = [{k: r.get(k) for k in ('reel_id', 'code', 'account_username', 'url', 'views', 'likes', 'comments',
                     'reshares', 'saves', 'creator_view_index', 'diagnostic_component_count', 'diagnostic_equal_weight_z',
                     'topic_codes', 'transcript_words', 'cut_count', 'best_reel_reason', 'snapshot_date')} | {
                         'descriptive_rank': i, 'rank_scope': 'DIAGNOSTIC_REVIEW_QUEUE_NOT_FINAL_BEST'} for i, r in enumerate(ranking, 1)]
        eligible = [r for r in reels if r['eligibility_state'] == 'PASS']
        summary = {'schema_version': 'signal-analysis.v1', 'release_id': release_id,
                   'corpus_sha256': release['corpus_sha256'], 'config_sha256': release['config_sha256'],
                   'implementation_sha256': release['implementation_sha256'], 'formula_version': FORMULA_VERSION,
                   'snapshot_date': release['snapshot_date'], 'collection_state': 'SKIPPED_DISABLED',
                   'stage_state': 'PASS_WITH_LIMITATIONS', 'review_state': 'MAKER_COMPLETE', 'release_state': 'CANDIDATE',
                   'evidence_release_accepted': False, 'production_state': 'NOT_RUN',
                   'population': {'source_observations': len(source), 'canonical_reels': len(reels), 'accounts': len(accounts),
                                  'identity_conflict_groups': sum(r['identity_conflict'] for r in reels),
                                  'quarantined_reels': sum(bool(r['quarantine_reasons']) for r in reels),
                                  'numeric_valid_reels': sum(r['numeric_valid'] for r in reels), 'exposure_eligible_reels': len(eligible),
                                  'eligible_saves_observed': sum(r['saves'] is not None for r in eligible),
                                  'eligible_saves_missing': sum(r['saves'] is None for r in eligible),
                                  'descriptive_hit_rates': sum(r['hit_rate'] is not None for r in accounts), 'final_best_reels': 0},
                   'coverage': {}, 'metric_distributions': {}, 'top_candidates': ranking_rows[:20],
                   'limitations': metric_definition(cfg)['limitations']}
        for modality in MODALITIES:
            records = [a for a in attempts if a['modality'] == modality]
            n = len(records)
            observed = sum(a['observation_state'] in ('OBSERVED', 'PARTIAL') for a in records)
            summary['coverage'][modality] = {'denominator': n, 'observed_or_partial': observed,
                'coverage': observed/n if n else None, 'independently_approved': 0,
                'reason_counts': dict(Counter(a['reason_code'] for a in records))}
        summary['coverage']['transcript']['word_bearing'] = sum(bool(a['words']) for a in attempts if a['modality'] == 'transcript')
        for metric in ['views', 'duration_seconds']+[k+'_per_1k_views' for k in ('likes','comments','reshares','saves')]:
            summary['metric_distributions'][metric] = distribution([r.get(metric) for r in eligible], len(eligible))
        with db:
            for row in reels:
                _insert_immutable(db, 'reel_analysis', ('release_id','reel_id','account_username','eligibility_state','payload_json'),
                                  (release_id,row['reel_id'],row['account_username'],row['eligibility_state'],canonical(row)), ('release_id','reel_id'))
                metric_names = list(COUNTERS)+['duration_seconds','creator_view_index','diagnostic_equal_weight_z']+[
                    key+'_per_1k_views' for key in ('likes','comments','reshares','saves')]
                for metric in metric_names:
                    value = row.get(metric)
                    unit = 'events_per_1000_views' if metric.endswith('_per_1k_views') else 'seconds' if metric == 'duration_seconds' else 'index' if metric == 'creator_view_index' else 'robust_z' if metric == 'diagnostic_equal_weight_z' else 'count'
                    db.execute('INSERT OR IGNORE INTO reel_metric_values VALUES (?,?,?,?,?,?,?,?)',
                               (release_id,row['reel_id'],metric,value,1 if value is not None else 0,
                                row['views'] if metric.endswith('_per_1k_views') else None,unit,FORMULA_VERSION))
            for row in accounts:
                _insert_immutable(db, 'account_analysis', ('release_id','account_username','payload_json'),
                                  (release_id,row['account_username'],canonical(row)), ('release_id','account_username'))
            for row in attempts:
                _insert_immutable(db, 'evidence_attempts', ('release_id','reel_id','modality','observation_state','payload_json'),
                                  (release_id,row['reel_id'],row['modality'],row['observation_state'],canonical(row)), ('release_id','reel_id','modality'))
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        if (out/'summary.json').exists() and json.loads((out/'summary.json').read_text())['release_id'] != release_id:
            raise ValueError('output belongs to another immutable release; select a new output directory')
        for name, rows in [('reels',reels),('accounts',accounts),('evidence-attempts',attempts)]:
            _write_jsonl(out/(name+'.jsonl'), rows)
            if name != 'evidence-attempts':
                _csv(out/(name+'.csv'), rows)
        _csv(out/'candidate-ranking.csv', ranking_rows)
        _write_json(out/'summary.json', summary)
        _write_json(out/'source-manifest.json', json.loads(release['manifest_json']))
        _write_json(out/'metrics-definition.json', metric_definition(cfg))
        _write_json(out/'source-media-inventory.json', {'scope':'supplied export directory only', 'media_decoded':False,
                    'files':[r['payload'] for r in _rows(db, release_id, 'source_media')],
                    'canonical_reels':len(reels), 'matched_reels':sum(r['code'] in media for r in reels)})
        _write_jsonl(out/'quarantine.jsonl', [r for r in reels if r['quarantine_reasons']])
        _write_json(out/'evidence-job-queue.json', {
            'release_id': release_id, 'execution_state': 'BLOCKED_EVIDENCE',
            'jobs': [{'reel_id': r['reel_id'], 'priority': i+1, 'source_url': r['url'],
                      'transcript_action': 'VERIFY_EXISTING_ASR' if r['transcript_words'] else 'ACQUIRE_MEDIA_THEN_ASR',
                      'visual_action': 'ACQUIRE_MEDIA_PROBE_CUT_SHOT_SCENE_2_4_6_FRAMES',
                      'rights_state': 'UNKNOWN', 'provider_calls_enabled': False}
                     for i,r in enumerate(ranking)],
            'denominators': {'all_audit_reels': len(reels), 'scoreable_review_queue': len(ranking),
                             'non_scoreable_or_quarantined': len(reels)-len(ranking)},
            'all_reel_missing_media_attempts': 'evidence-attempts.jsonl',
            'gate': 'Exact permitted public-source acquisition route and media provenance needed before queued jobs execute.'})
        _write_json(out/'artifact-manifest.json', {'release_id': release_id, 'artifacts': [
            {'path': p.name, 'sha256': file_hash(p), 'size_bytes': p.stat().st_size}
            for p in sorted(out.iterdir()) if p.suffix in ('.json','.jsonl','.csv') and p.name != 'artifact-manifest.json']})
        return summary
    finally:
        db.close()


def _insert_immutable(db, table, columns, values, key_columns):
    payload = dict(zip(columns, values))
    previous = db.execute(f"SELECT payload_json FROM {table} WHERE "+' AND '.join(k+'=?' for k in key_columns),
                          [payload[k] for k in key_columns]).fetchone()
    if previous and previous[0] != payload['payload_json']:
        raise ValueError('immutable analysis differs; new implementation/config release required')
    db.execute(f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in values)})", values)


def backup_database(db_path, backup_path):
    """Consistent SQLite online backup; refuse to overwrite an existing target."""
    source, target = Path(db_path), Path(backup_path)
    if not source.is_file() or target.exists() or source.resolve() == target.resolve():
        raise ValueError('source must exist and backup target must be new')
    target.parent.mkdir(parents=True, exist_ok=True)
    from urllib.parse import quote
    with sqlite3.connect('file:'+quote(str(source.resolve()))+'?mode=ro', uri=True) as src:
        with sqlite3.connect(target) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or dst.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('backup integrity failure')
    return {'stage_state': 'PASS', 'sha256': file_hash(target), 'bytes': target.stat().st_size}


def restore_database(backup_path, destination):
    return backup_database(backup_path, destination)
