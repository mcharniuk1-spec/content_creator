"""Import a reviewed private reconciliation packet using an injected Postgres DSN.
Never prints the DSN or source payloads. No media upload or provider execution.
"""
import argparse, hashlib, json, os
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def load(path):
    return json.loads(path.read_text())

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--packet',type=Path,required=True)
    parser.add_argument('--release',required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True)
    args=parser.parse_args(); packet=args.packet
    frozen={name:(packet/name).read_bytes() for name in ['source-manifest.json','identity-dispositions.json','schemas.json']}
    sources=json.loads(frozen['source-manifest.json']); identities=json.loads(frozen['identity-dispositions.json']); schemas=json.loads(frozen['schemas.json'])
    hashes={name:hashlib.sha256(value).hexdigest() for name,value in frozen.items()}
    hashes['observations.jsonl']=hashlib.file_digest((packet/'observations.jsonl').open('rb'),'sha256').hexdigest()
    review=load(args.review)
    if review.get('status')!='ACCEPTED_MECHANICAL_RECONCILIATION_ONLY': raise ValueError('INDEPENDENT_REVIEW_REQUIRED')
    if any(review.get('reviewed_artifact_hashes',{}).get(k)!=v for k,v in hashes.items()): raise ValueError('REVIEW_HASH_MISMATCH')
    manifest_hash=hashlib.sha256(canonical(hashes).encode()).hexdigest()
    counts={}; imported=0
    with psycopg.connect(os.environ['M2_DATABASE_DSN']) as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO m2_shared.releases VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(args.release,manifest_hash,'candidate',Jsonb(['dated backups; no acoustic acceptance; no live server completeness'])))
            cur.execute('SELECT manifest_sha256 FROM m2_shared.releases WHERE id=%s',(args.release,))
            if cur.fetchone()[0]!=manifest_hash: raise ValueError('RELEASE_INPUT_CHANGED')
            for source in sources:
                if 'table_counts' not in source: continue
                safe_manifest={k:v for k,v in source.items() if k!='path'}
                safe_manifest['native_schemas']=[x for x in schemas if x['source']==source['source']]
                cur.execute('INSERT INTO m2_shared.sources(id,label,capture_precision,manifest) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(source['sha256'],source['source'],'dated_backup',Jsonb(safe_manifest)))
                cur.execute('SELECT manifest FROM m2_shared.sources WHERE id=%s',(source['sha256'],))
                if cur.fetchone()[0]!=safe_manifest: raise ValueError('SOURCE_MANIFEST_CONFLICT')
            # Temp table allows COPY, exact collision checking, then append-only merge.
            cur.execute('CREATE TEMP TABLE incoming_rows (LIKE m2_shared.source_rows INCLUDING DEFAULTS) ON COMMIT DROP')
            with cur.copy('COPY incoming_rows(source_id,table_name,row_key,payload_sha256,payload) FROM STDIN') as cp:
                stream_hash=hashlib.sha256()
                with (packet/'observations.jsonl').open('rb') as f:
                    for line in f:
                        stream_hash.update(line)
                        r=json.loads(line)
                        if hashlib.sha256(canonical(r['payload']).encode()).hexdigest()!=r['payload_sha256']: raise ValueError('PAYLOAD_HASH_MISMATCH')
                        cp.write_row((r['source_sha256'],r['table'],str(r['source_row_ordinal']),r['payload_sha256'],Jsonb(r['payload'])))
                        counts[r['source']+':'+r['table']]=counts.get(r['source']+':'+r['table'],0)+1; imported+=1
            if stream_hash.hexdigest()!=hashes['observations.jsonl']: raise ValueError('REVIEWED_STREAM_CHANGED')
            cur.execute('SELECT count(*) FROM incoming_rows i JOIN m2_shared.source_rows s USING(source_id,table_name,row_key) WHERE i.payload_sha256<>s.payload_sha256 OR i.payload<>s.payload')
            if cur.fetchone()[0]: raise ValueError('IMMUTABLE_SOURCE_CONFLICT')
            cur.execute('INSERT INTO m2_shared.source_rows SELECT * FROM incoming_rows ON CONFLICT DO NOTHING')
            for r in identities:
                cur.execute('INSERT INTO m2_shared.reels VALUES (%s) ON CONFLICT DO NOTHING',(r['code'],))
                cur.execute('INSERT INTO m2_shared.reel_assessments(code,disposition,reason,evidence,release_id) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(r['code'],r['disposition'].lower(),r['reason'],Jsonb(r),args.release))
                cur.execute('SELECT evidence FROM m2_shared.reel_assessments WHERE code=%s AND release_id=%s',(r['code'],args.release))
                if cur.fetchone()[0]!=r: raise ValueError('IDENTITY_VERSION_CONFLICT')
            cur.execute('SELECT count(*) FROM incoming_rows i JOIN m2_shared.source_rows s USING(source_id,table_name,row_key) WHERE i.payload_sha256=s.payload_sha256 AND i.payload=s.payload')
            matched=cur.fetchone()[0]
            if matched!=imported: raise ValueError('ROW_READBACK_MISMATCH')
            cur.execute('SELECT count(*) FROM m2_shared.reel_assessments WHERE release_id=%s',(args.release,)); matched_reels=cur.fetchone()[0]
            if matched_reels!=len(identities): raise ValueError('IDENTITY_READBACK_MISMATCH')
    args.receipt.write_text(json.dumps({'status':'PASS','release':args.release,'input_hashes':hashes,'source_rows_matched':matched,'identities_matched':matched_reels,'source_table_counts':counts,'normalized_entity_projection':'NOT_RUN','media_upload':'NOT_RUN','limits':['source_rows preserves all original fields; typed downstream entities remain pending reviewed projection']},indent=2)+'\n')
    print(json.dumps({'status':'PASS','rows':matched,'identities':matched_reels}))

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        import sys
        code=str(exc) if isinstance(exc,ValueError) and str(exc).isupper() and str(exc).replace('_','').isalnum() else 'IMPORT_FAILED'
        print(json.dumps({'status':'FAIL','code':code}),file=sys.stderr)
        raise SystemExit(1)
