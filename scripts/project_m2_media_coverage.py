"""Recheck private media bytes and project per-Reel coverage without scene approval."""
import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from project_m2_evidence import append_rows, digest


def within(path, root):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('PATH_OUTSIDE_MEDIA_ROOT')
    return resolved


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--coverage', type=Path, required=True)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--source-projection',required=True)
    p.add_argument('--media-root', type=Path, required=True)
    p.add_argument('--release', required=True)
    p.add_argument('--projection', required=True)
    p.add_argument('--checked-at', required=True)
    p.add_argument('--receipt', type=Path, required=True)
    a = p.parse_args()
    checked_at = datetime.fromisoformat(a.checked_at)
    if checked_at.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    raw = a.coverage.read_bytes()
    coverage_hash = hashlib.sha256(raw).hexdigest()
    inventory_bytes=a.inventory.read_bytes()
    inventory_hash=hashlib.sha256(inventory_bytes).hexdigest()
    input_hash=digest({'coverage':coverage_hash,'inventory':inventory_hash,'source_projection':a.source_projection,'checked_at':checked_at.isoformat()})
    records = json.loads(raw)['records']
    inventory=[json.loads(line) for line in inventory_bytes.splitlines()]
    required_codes={r['identity'] for r in inventory}
    if len(required_codes)!=len(inventory) or {r['code'] for r in records}!=required_codes:
        raise ValueError('TRANSCRIPT_COVERAGE_SET_MISMATCH')
    root = a.media_root.resolve()
    assets, coverage = [], []
    for r in records:
        code = r['code']
        count = 0
        if r.get('media_hash_state') == 'HASH_VALID_COMPUTED':
            path = within(r['media_path'], root)
            actual = file_hash(path)
            if actual != r['actual_media_sha256'] or actual != r['expected_media_sha256']:
                raise ValueError('MEDIA_HASH_CHANGED')
            asset = dict(code=code, kind='video', private_path=str(path), actual_sha256=actual,
                         byte_size=path.stat().st_size, media_sha256=actual, timestamp_seconds=None,
                         state='verified_bytes', receipt_sha256=input_hash, checked_at=checked_at)
            asset['id'] = digest([input_hash, code, 'video', actual])
            assets.append(asset)
            receipt_path = within(r['frame_receipt_path'], root)
            frame_receipt_raw = receipt_path.read_bytes()
            frame_receipt = json.loads(frame_receipt_raw)
            if frame_receipt.get('reel_id') != 'instagram:' + code or frame_receipt.get('retention', {}).get('source_media_hash') != actual:
                raise ValueError('FRAME_RECEIPT_REEL_BINDING')
            receipt_hash = hashlib.sha256(frame_receipt_raw).hexdigest()
            for f in frame_receipt.get('sampled_frames', []):
                if f.get('observation_state') != 'OBSERVED':
                    continue
                image_path = within(receipt_path.parent/f['source_pointer'], root)
                image_hash = file_hash(image_path)
                if image_hash != f['sha256'] or f.get('source_media_hash') != actual:
                    raise ValueError('FRAME_HASH_OR_MEDIA_BINDING')
                timestamp = f['timestamp_ms']/1000
                frame = dict(code=code, kind='frame', private_path=str(image_path), actual_sha256=image_hash,
                             byte_size=image_path.stat().st_size, media_sha256=actual, timestamp_seconds=timestamp,
                             state='verified_bytes', receipt_sha256=receipt_hash, checked_at=checked_at)
                frame['id'] = digest([input_hash, code, actual, timestamp, image_hash, receipt_hash])
                assets.append(frame)
                count += 1
            if count != r['frame_count_local']:
                raise ValueError('FRAME_COUNT_MISMATCH')
        coverage.append(dict(projection_id=a.projection, code=code, transcript_versions=0,
            media_state='verified_bytes' if r.get('media_hash_state') == 'HASH_VALID_COMPUTED' else 'missing',
            frame_state='verified_bytes_unreviewed' if count else 'missing', cut_state=r['cut_state'],
            scene_state='unreviewed', alignment_state='unreviewed', usable_frames=count, reviewed_scenes=0,
            reasons=[r['coverage_reason']], receipt_sha256=input_hash))
    if len({r['code'] for r in coverage}) != len(coverage):
        raise ValueError('DUPLICATE_COVERAGE_IDENTITY')
    mapping_hash = file_hash(Path(__file__))
    with psycopg.connect(os.environ['M2_DATABASE_DSN']) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT release_id FROM m2_evidence.projections WHERE id=%s',(a.source_projection,))
            if cur.fetchone()!=(a.release,): raise ValueError('SOURCE_PROJECTION_RELEASE_MISMATCH')
            cur.execute('SELECT DISTINCT l.code FROM m2_evidence.lineage l JOIN m2_evidence.projection_members m ON m.lineage_id=l.id WHERE m.projection_id=%s',(a.source_projection,))
            if not required_codes.issubset({r[0] for r in cur.fetchall()}): raise ValueError('COVERAGE_CODE_OUTSIDE_RELEASE')
            cur.execute('INSERT INTO m2_evidence.projections(id,release_id,mapping_sha256,input_manifest_sha256) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                        (a.projection, a.release, mapping_hash, input_hash))
            cur.execute('SELECT release_id,mapping_sha256,input_manifest_sha256 FROM m2_evidence.projections WHERE id=%s', (a.projection,))
            if cur.fetchone() != (a.release, mapping_hash, input_hash):
                raise ValueError('PROJECTION_INPUT_CHANGED')
            append_rows(cur,'projection_parents',[{'projection_id':a.projection,'parent_projection_id':a.source_projection}])
            cur.execute('SELECT t.code,count(DISTINCT t.lineage_id) FROM m2_evidence.transcripts t JOIN m2_evidence.projection_members m ON m.lineage_id=t.lineage_id WHERE m.projection_id=%s GROUP BY t.code',(a.source_projection,))
            transcript_counts = dict(cur.fetchall())
            for c in coverage:
                c['transcript_versions'] = transcript_counts.get(c['code'], 0)
            asset_added = append_rows(cur, 'asset_checks', assets)
            append_rows(cur,'projection_assets',[{'projection_id':a.projection,'asset_check_id':asset['id']} for asset in assets])
            coverage_added = append_rows(cur, 'coverage', coverage)
            cur.execute('SELECT count(*),count(*) FILTER(WHERE usable_frames>0),sum(usable_frames),sum(reviewed_scenes) FROM m2_evidence.coverage WHERE projection_id=%s', (a.projection,))
            readback = cur.fetchone()
            expected = (len(coverage), sum(c['usable_frames'] > 0 for c in coverage), sum(c['usable_frames'] for c in coverage), 0)
            if readback != expected:
                raise ValueError('COVERAGE_READBACK_MISMATCH')
    result = dict(status='PASS_PRIVATE_BYTE_AND_COVERAGE_PROJECTION', release=a.release, projection=a.projection,
                  input_sha256=input_hash, mapping_sha256=mapping_hash, asset_records=len(assets), asset_records_added=asset_added,
                  coverage_records_added=coverage_added, transcript_bearing=len(coverage), with_verified_frames=readback[1],
                  verified_frame_files=readback[2], reviewed_scenes=0, limitations=['local private paths; no remote storage', 'no acoustic or scene acceptance'])
    a.receipt.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).replace('_', '').isupper() else 'MEDIA_PROJECTION_FAILED'
        print(json.dumps({'status': 'FAIL', 'code': code}))
        raise SystemExit(1)
