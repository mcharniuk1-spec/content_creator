"""Append an independently reviewed expanded source packet; no external providers."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from import_m2_shared import validate_independent_review


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def ingest(packet, review_path, release, conn, parent_release=None):
    names = ['source-manifest.json', 'schemas.json', 'identity-union-reconciliation.json', 'source-observations.jsonl']
    hashes = {name: hashlib.file_digest((packet/name).open('rb'), 'sha256').hexdigest() for name in names}
    review = json.loads(review_path.read_text())
    validate_independent_review(review)
    if any(review.get('reviewed_artifact_hashes', {}).get(k) != v for k, v in hashes.items()):
        raise ValueError('REVIEW_HASH_MISMATCH')
    frozen = {name: (packet/name).read_bytes() for name in names[:-1]}
    if any(hashlib.sha256(data).hexdigest() != hashes[name] for name, data in frozen.items()):
        raise ValueError('REVIEWED_METADATA_CHANGED')
    sources = json.loads(frozen['source-manifest.json'])
    by_label = {s['source']: s for s in sources}
    union = json.loads(frozen['identity-union-reconciliation.json'])['all_current_union_identities']
    if any(not isinstance(c,str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}',c) for c in union) or len(set(union))!=len(union):
        raise ValueError('INVALID_CANONICAL_REEL_SET')
    if json.loads(frozen['identity-union-reconciliation.json'])['prior_reviewed_identity_count'] and not parent_release:
        raise ValueError('PARENT_SOURCE_RELEASE_REQUIRED')
    with conn.cursor() as cur:
        parent_hash = None
        if parent_release:
            cur.execute('SELECT manifest_sha256 FROM m2_shared.releases WHERE id=%s',(parent_release,))
            parent = cur.fetchone()
            cur.execute('SELECT count(*) FROM m2_shared.release_source_rows WHERE release_id=%s',(parent_release,))
            if not parent or not cur.fetchone()[0]:
                raise ValueError('PARENT_SOURCE_COHORT_MISSING')
            parent_hash = parent[0]
            cur.execute('SELECT manifest_sha256 FROM m2_shared.release_seals WHERE release_id=%s',(parent_release,))
            if cur.fetchone()!=(parent_hash,): raise ValueError('SEALED_PARENT_RELEASE_REQUIRED')
        manifest_hash = hashlib.sha256(canonical({'inputs':hashes,'parent_release':parent_release,'parent_manifest_sha256':parent_hash}).encode()).hexdigest()
        cur.execute('INSERT INTO m2_shared.releases VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                    (release, manifest_hash, 'candidate', Jsonb(['source preservation; separate semantic and audiovisual review required'])))
        cur.execute('SELECT manifest_sha256 FROM m2_shared.releases WHERE id=%s', (release,))
        if cur.fetchone()[0] != manifest_hash:
            raise ValueError('RELEASE_INPUT_CHANGED')
        # Aliases remain in the frozen release packet; an existing byte-identical
        # source retains its original manifest, rather than rewriting provenance.
        for source in sources:
            cur.execute('INSERT INTO m2_shared.sources(id,label,capture_precision,manifest) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                        (source['sha256'], source['source'], 'source_snapshot', Jsonb(source)))
        cur.execute('CREATE TEMP TABLE expanded_rows (LIKE m2_shared.source_rows INCLUDING DEFAULTS) ON COMMIT DROP')
        count = 0
        stream_hash = hashlib.sha256()
        with cur.copy('COPY expanded_rows(source_id,table_name,row_key,payload_sha256,payload) FROM STDIN') as cp:
            with (packet/'source-observations.jsonl').open('rb') as stream:
                for line in stream:
                    stream_hash.update(line)
                    row = json.loads(line)
                    if hashlib.sha256(canonical(row['payload']).encode()).hexdigest() != row['payload_sha256']:
                        raise ValueError('SOURCE_PAYLOAD_CHANGED')
                    source_hash = by_label[row['source']]['sha256']
                    key = 'expanded-v1:' + str(row['row_ordinal'])
                    cp.write_row((source_hash, row['location'], key, row['payload_sha256'], Jsonb(row['payload'])))
                    count += 1
        if stream_hash.hexdigest() != hashes['source-observations.jsonl']:
            raise ValueError('REVIEWED_STREAM_CHANGED')
        cur.execute('SELECT count(*) FROM (SELECT source_id,table_name,row_key FROM expanded_rows GROUP BY 1,2,3 HAVING count(DISTINCT payload_sha256)>1) t')
        if cur.fetchone()[0]:
            raise ValueError('SOURCE_ALIAS_CONFLICT')
        cur.execute('SELECT count(*) FROM expanded_rows i JOIN m2_shared.source_rows s USING(source_id,table_name,row_key) WHERE i.payload<>s.payload OR i.payload_sha256<>s.payload_sha256')
        if cur.fetchone()[0]:
            raise ValueError('IMMUTABLE_SOURCE_CONFLICT')
        cur.execute('INSERT INTO m2_shared.source_rows SELECT DISTINCT * FROM expanded_rows ON CONFLICT DO NOTHING')
        added = cur.rowcount
        cur.execute('INSERT INTO m2_shared.release_source_rows SELECT DISTINCT %s,source_id,table_name,row_key FROM expanded_rows ON CONFLICT DO NOTHING',(release,))
        if parent_release:
            cur.execute('INSERT INTO m2_shared.release_parents VALUES(%s,%s) ON CONFLICT DO NOTHING',(release,parent_release))
            cur.execute('INSERT INTO m2_shared.release_source_rows SELECT %s,source_id,table_name,row_key FROM m2_shared.release_source_rows WHERE release_id=%s ON CONFLICT DO NOTHING',(release,parent_release))
        cur.executemany('INSERT INTO m2_shared.reels VALUES (%s) ON CONFLICT DO NOTHING', [(x,) for x in union])
        cur.execute('SELECT count(*) FROM expanded_rows i JOIN m2_shared.source_rows s USING(source_id,table_name,row_key) WHERE i.payload=s.payload AND i.payload_sha256=s.payload_sha256')
        if cur.fetchone()[0] != count:
            raise ValueError('SOURCE_READBACK_MISMATCH')
        cur.execute('SELECT m2_shared.seal_release(%s)',(release,))
        cohort_hash=cur.fetchone()[0]
    return {'status': 'PASS_SOURCE_PRESERVATION', 'release': release, 'input_hashes': hashes,
            'cohort_sha256':cohort_hash,
            'parent_release': parent_release, 'parent_manifest_sha256': parent_hash,
            'release_manifest_sha256': manifest_hash,
            'observation_envelopes_matched': count, 'unique_source_rows_added': added,
            'union_identities': len(union), 'normalized_projection': 'SEPARATE_STAGE'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--release', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--parent-release')
    args = parser.parse_args()
    with psycopg.connect(os.environ['M2_DATABASE_DSN']) as conn:
        receipt = ingest(args.packet, args.review, args.release, conn, args.parent_release)
    args.receipt.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'input_hashes'}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).replace('_', '').isupper() else 'IMPORT_FAILED'
        print(json.dumps({'status': 'FAIL', 'code': code}))
        raise SystemExit(1)
