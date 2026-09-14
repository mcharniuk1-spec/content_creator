"""Typed source projections with immutable lineage and explicit unreviewed states.

Only maps declared source values. Filesystem availability, acoustic acceptance,
scenes and alignment are separate reviewed imports, never inferred here.
"""
import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

TABLES = ('reels', 'snapshots', 'transcripts', 'partner_transcripts', 'august_transcripts', 'transcript_segments', 'transcript_meta', 'video_state', 'frames', 'scenes')
CODE = re.compile(r'^[A-Za-z0-9_-]{11}$')
MAPPING_VERSION = 'm2-typed-source-v2'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def number(value, integer=False):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('INVALID_NONNEGATIVE_NUMBER')
    if integer and int(value) != value:
        raise ValueError('INVALID_INTEGER')
    return int(value) if integer else value


def text(value):
    if value is None or isinstance(value, str):
        return value
    raise ValueError('INVALID_TEXT')


def project_records(records):
    products = {k: [] for k in ['lineage', 'metrics', 'transcripts', 'segments', 'media_pointers', 'frame_pointers', 'scene_candidates']}
    gaps = []
    snapshots = {}
    metadata = {}
    retained_segments = {}
    for source, table, key, payload_hash, p in records:
        if not isinstance(p, dict):
            continue
        if table == 'snapshots':
            snapshots[source, str(p.get('id'))] = p.get('taken')
        if table == 'transcript_meta':
            metadata[source, p.get('code')] = p
        if table == 'transcript_segments':
            retained_segments.setdefault((source, p.get('code'), p.get('part')), []).append(p)
    for source, table, key, payload_hash, p in records:
        if not isinstance(p, dict) or table in ('snapshots', 'transcript_meta', 'transcript_segments'):
            continue
        code = p.get('code')
        if not isinstance(code, str) or not CODE.fullmatch(code):
            gaps.append({'source': source, 'table': table, 'row': key, 'reason': 'NO_CANONICAL_CODE'})
            continue
        identity = digest([source, table, key, payload_hash])
        products['lineage'].append(dict(id=identity, source_id=source, source_table=table, source_row_key=key, code=code))
        try:
            common = {'lineage_id': identity, 'code': code}
            if table == 'reels':
                taken = snapshots.get((source, str(p.get('snapshot_id'))))
                precision = 'date' if isinstance(taken, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', taken) else 'timestamp' if taken else 'unknown'
                products['metrics'].append(dict(common, snapshot_native_id=str(p['snapshot_id']) if p.get('snapshot_id') is not None else None,
                    snapshot_taken=taken, capture_precision=precision, published_unix=number(p.get('ts')),
                    provider_account_id=str(p['pk_user']) if p.get('pk_user') is not None else None,
                    username_observed=text(p.get('username')),
                    views=number(p.get('play'), True), likes=number(p.get('likes'), True), comments=number(p.get('comm'), True),
                    saves=number(p.get('save'), True), reshares=number(p.get('resh'), True), sends=number(p.get('sends'), True),
                    followers=number(p.get('followers'), True), duration_seconds=number(p.get('dur'))))
            elif table in ('transcripts', 'partner_transcripts', 'august_transcripts'):
                original = text(p.get('original_full_text') if 'original_full_text' in p else p.get('text'))
                segments = p.get('segments')
                if 'original_full_text' in p:
                    retained = retained_segments.get((source, code, p.get('part')), [])
                    segments = [{'start': s.get('start_seconds'), 'end': s.get('end_seconds'), 'text': s.get('original_segment_text')}
                                for s in sorted(retained, key=lambda s: s.get('sequence', 0))] or None
                segment_rows = []
                parse_state = 'missing'
                if segments not in (None, ''):
                    try:
                        segments = json.loads(segments) if isinstance(segments, str) else segments
                        if not isinstance(segments, list):
                            raise ValueError('SEGMENTS_NOT_ARRAY')
                        for ordinal, segment in enumerate(segments):
                            start = number(segment.get('start'))
                            end = number(segment.get('end'))
                            body = text(segment.get('text'))
                            if start is None or end is None or end < start or body is None:
                                raise ValueError('INVALID_SEGMENT')
                            segment_rows.append(dict(transcript_id=identity, code=code, ordinal=ordinal,
                                                     start_seconds=start, end_seconds=end, original_text=body))
                        parse_state = 'parsed'
                    except (ValueError, TypeError, AttributeError):
                        segment_rows = []
                        parse_state = 'invalid'
                meta = metadata.get((source, code), {})
                products['transcripts'].append(dict(common, original_text=original,
                    text_sha256=hashlib.sha256(original.encode()).hexdigest() if original is not None else None,
                    language_observed=text(p.get('detected_language') if 'detected_language' in p else p.get('lang')), media_hash_declared=meta.get('media_sha256'), model_observed=meta.get('model', p.get('method')),
                    state='missing' if original is None else 'source_text_unreviewed' if original.strip() else 'empty', segments_parse_state=parse_state))
                products['segments'].extend(segment_rows)
            elif table == 'video_state':
                products['media_pointers'].append(dict(common, path_declared=text(p.get('media_path')), hash_declared=text(p.get('media_sha256')),
                    bytes_declared=number(p.get('media_bytes'), True), state_declared=text(p.get('media_state'))))
            elif table == 'frames':
                products['frame_pointers'].append(dict(common, ordinal=number(p.get('idx'), True), timestamp_seconds=number(p.get('t_sec')),
                    path_declared=text(p.get('path')), image_hash_declared=text(p.get('sha256')), exists_declared=p.get('exists_ok')))
            elif table == 'scenes':
                indices = p.get('frame_idx_json')
                try:
                    indices = json.loads(indices) if isinstance(indices, str) else indices
                except ValueError:
                    indices = {'parse_state': 'invalid'}
                products['scene_candidates'].append(dict(common, native_scene_id=text(p.get('scene_id')), start_seconds=number(p.get('start_s')),
                    end_seconds=number(p.get('end_s')), boundary_method=text(p.get('boundary_reason')), scene_type_declared=text(p.get('scene_type')),
                    frame_indices_declared=indices, state='source_candidate_unreviewed'))
        except ValueError as exc:
            gaps.append({'source': source, 'table': table, 'row': key, 'code': code, 'reason': str(exc)})
    return products, gaps


def append_rows(cur, table, rows):
    if not rows:
        return 0
    columns = list(rows[0])
    target = sql.Identifier('m2_evidence', table)
    temp = sql.Identifier('incoming_' + table)
    cur.execute(sql.SQL('CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP').format(temp, target))
    with cur.copy(sql.SQL('COPY {} ({}) FROM STDIN').format(temp, sql.SQL(',').join(map(sql.Identifier, columns)))) as cp:
        for row in rows:
            cp.write_row([Jsonb(row[k]) if isinstance(row[k], (dict, list)) else row[k] for k in columns])
    cur.execute(sql.SQL('INSERT INTO {} SELECT * FROM {} ON CONFLICT DO NOTHING').format(target, temp))
    added = cur.rowcount
    # Full row equality catches mapping changes hidden by ON CONFLICT.
    cur.execute(sql.SQL('SELECT count(*) FROM (SELECT * FROM {} EXCEPT SELECT * FROM {}) q').format(temp, target))
    if cur.fetchone()[0]:
        raise ValueError('IMMUTABLE_PROJECTION_CONFLICT')
    return added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True)
    parser.add_argument('--projection', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    mapping_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with psycopg.connect(os.environ['M2_DATABASE_DSN']) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM m2_shared.release_seals WHERE release_id=%s',(args.release,))
            if not cur.fetchone(): raise ValueError('SEALED_RELEASE_REQUIRED')
            cur.execute('SELECT r.source_id,r.table_name,r.row_key,r.payload_sha256,r.payload FROM m2_shared.source_rows r JOIN m2_shared.release_source_rows c USING(source_id,table_name,row_key) WHERE c.release_id=%s AND r.table_name=ANY(%s) ORDER BY 1,2,3', (args.release,list(TABLES)))
            records = cur.fetchall()
            if not records:
                raise ValueError('REVIEWED_RELEASE_COHORT_REQUIRED')
            input_hash = digest([r[:4] for r in records])
            products, gaps = project_records(records)
            cur.execute('INSERT INTO m2_evidence.projections(id,release_id,mapping_sha256,input_manifest_sha256) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                        (args.projection, args.release, mapping_hash, input_hash))
            cur.execute('SELECT release_id,mapping_sha256,input_manifest_sha256 FROM m2_evidence.projections WHERE id=%s', (args.projection,))
            if cur.fetchone() != (args.release, mapping_hash, input_hash):
                raise ValueError('PROJECTION_INPUT_CHANGED')
            codes = sorted({r['code'] for r in products['lineage']})
            cur.executemany('INSERT INTO m2_shared.reels VALUES(%s) ON CONFLICT DO NOTHING', [(c,) for c in codes])
            added = {name: append_rows(cur, name, rows) for name, rows in products.items()}
            append_rows(cur, 'projection_members', [{'projection_id': args.projection, 'lineage_id': r['id']} for r in products['lineage']])
    receipt = {'status': 'PASS_TYPED_SOURCE_PROJECTION', 'projection': args.projection, 'release': args.release,
               'mapping_sha256': mapping_hash, 'mapping_version':MAPPING_VERSION, 'input_manifest_sha256': input_hash,
               'counts': {k: len(v) for k, v in products.items()}, 'added': added, 'gaps': gaps,
               'limits': ['source candidates only', 'asset/review/coverage imports are separate', 'source copies and versions are retained; counts are not distinct Reels']}
    args.receipt.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'gaps'}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).replace('_', '').isupper() else 'PROJECTION_FAILED'
        print(json.dumps({'status': 'FAIL', 'code': code}))
        raise SystemExit(1)
