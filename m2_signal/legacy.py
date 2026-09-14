"""Read-only adapter for the partner Radar SQLite contract.

Independent implementation against the field contract inspected at pinned Radar
commit 02102dd1013b9ed1736b01d8cda8b62563575a14. No upstream private code is copied.
Only allowlisted public-source evidence columns are read. No environment, API key,
spend, note, tool log, internal card, or own-account metric data is imported.
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import date
from pathlib import Path

from .engine import canonical, digest, file_hash


def _csv_bytes(fields, rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode()


def _write_new_or_identical(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('immutable export target differs; choose new directory: '+path.name)
        return
    path.write_bytes(data)


def import_legacy_db(db_path, output_dir, snapshot_date):
    """Export one explicitly selected completed snapshot from a read-only source.

    The caller owns the resulting local data. This function never runs collection
    or touches an existing HikerAPI integration. A consistent read transaction
    observes committed WAL contents; the logical export hash binds those values.
    """
    taken = date.fromisoformat(snapshot_date).isoformat()
    source = Path(db_path)
    if not source.is_file():
        raise ValueError('legacy database does not exist')
    out = Path(output_dir)
    # URI quoting is required for local paths containing # or ?.
    from urllib.parse import quote
    con = sqlite3.connect('file:'+quote(str(source.resolve()))+'?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'snapshots','reels','accounts'} <= tables:
            raise ValueError('unsupported legacy schema: missing required tables')
        snapshots = list(con.execute('SELECT id,taken,accounts_n,reels_n,done FROM snapshots WHERE taken=?', (taken,)))
        if len(snapshots) != 1 or snapshots[0]['done'] != 1:
            raise ValueError('exactly one completed snapshot required')
        snap = dict(snapshots[0])
        rows = [dict(r) for r in con.execute(
            'SELECT code,username,ts,play,likes,comm,resh,save,dur,cap,followers FROM reels WHERE snapshot_id=? ORDER BY code', (snap['id'],))]
        if snap['reels_n'] is not None and snap['reels_n'] != len(rows):
            raise ValueError('completed snapshot reels_n disagrees with stored rows')
        usernames = {r['username'] for r in rows}
        profiles = [dict(r) for r in con.execute('SELECT username,follower_count,media_count,category,biography FROM accounts ORDER BY username') if r['username'] in usernames]
        codes = {r['code'] for r in rows}
        transcript_rows = [dict(r) for r in con.execute('SELECT code,lang,words,segments FROM transcripts ORDER BY code') if r['code'] in codes] if 'transcripts' in tables else []
        cut_rows = [dict(r) for r in con.execute('SELECT code,cuts FROM deepdives WHERE snapshot_id=? ORDER BY code', (snap['id'],)) if r['code'] in codes] if 'deepdives' in tables else []
        topic_rows = [dict(r) for r in con.execute('SELECT code,topic FROM topics ORDER BY code,topic') if r['code'] in codes] if 'topics' in tables else []
        schema = {table: [dict(r) for r in con.execute('PRAGMA table_info('+table+')')]
                  for table in sorted(tables & {'snapshots','reels','accounts','transcripts','deepdives','topics'})}
        payloads = {}
        reel_fields = ['code','user','url','play','like','comment','reshare','save','duration_s','ts','caption','snapshot_followers']
        reel_rows = [{'code':r['code'],'user':r['username'],'url':'https://www.instagram.com/reel/'+r['code']+'/',
                      'play':r['play'],'like':r['likes'],'comment':r['comm'],'reshare':r['resh'],'save':r['save'],
                      'duration_s':r['dur'],'ts':r['ts'],'caption':r['cap'],'snapshot_followers':r['followers']} for r in rows]
        account_fields = ['username','followers','media_count','category','biography','profile_horizon_state']
        account_rows = [{'username':r['username'],'followers':r['follower_count'],'media_count':r['media_count'],
                         'category':r['category'],'biography':r['biography'],
                         'profile_horizon_state':'CURRENT_DB_NOT_HISTORICAL_SNAPSHOT'} for r in profiles]
        payloads['reels.csv'] = _csv_bytes(reel_fields,reel_rows)
        payloads['accounts.csv'] = _csv_bytes(account_fields,account_rows)
        transcripts = {}
        for r in transcript_rows:
            try:
                segments = json.loads(r['segments']) if r['segments'] else []
            except (ValueError, TypeError):
                segments = []
            transcripts[r['code']] = {'segments': segments, 'words':r['words'], 'lang':r['lang'],
                                      'provenance_state':'LEGACY_NO_SOURCE_MEDIA_HASH_OR_ASR_MODEL_ID'}
        payloads['transcripts.json'] = (canonical(transcripts)+'\n').encode()
        payloads['cuts.json'] = (canonical({r['code']:{'cuts':r['cuts']} for r in cut_rows})+'\n').encode()
        # Topic values remain provisional legacy labels and are never accepted as relevance.
        topics = {}
        for r in topic_rows:
            topics.setdefault(r['code'],[]).append(r['topic'])
        payloads['topics.csv'] = _csv_bytes(['code','topics'], [{'code':k,'topics':'|'.join(v)} for k,v in sorted(topics.items())])
        snapshot = {'taken':taken,'accounts':len(account_rows),'observation_horizon':'DATE_ONLY',
                    'upstream_accounts_n':snap['accounts_n'], 'upstream_reels_n':snap['reels_n'],
                    'profile_horizon':'CURRENT_DB_PROFILE_NOT_HISTORICAL_SNAPSHOT'}
        payloads['snapshot.json'] = (canonical(snapshot)+'\n').encode()
        receipt = {'schema_version':'signal-legacy-adapter.v1','snapshot_date':taken,'source_mode':'READ_ONLY_TRANSACTION',
                   'upstream_commit_contract':'02102dd1013b9ed1736b01d8cda8b62563575a14',
                   'source_schema_sha256':digest(schema),'source_rows':len(rows),'account_profiles':len(profiles),
                   'transcript_records':len(transcripts),'cut_summaries':len(cut_rows),
                   'legacy_scores_used':False,'collection_executed':False,
                   'artifacts':{k:{'sha256':digest(v),'size_bytes':len(v)} for k,v in sorted(payloads.items())},
                   'limitations':['Snapshot is a capture date, not a fixed post-age comparison.',
                                  'Account profiles reflect current database; only per-Reel snapshot_followers are dated.',
                                  'Historical accounts with zero Reels cannot be reconstructed from current account table.',
                                  'Transcript table is unversioned by snapshot and lacks source-media/ASR model hashes.',
                                  'Existing frame paths are not imported as verified frame evidence.']}
        receipt['logical_export_sha256'] = digest(receipt['artifacts'])
        payloads['legacy-adapter-receipt.json'] = (json.dumps(receipt, indent=2, sort_keys=True)+'\n').encode()
        out.mkdir(parents=True, exist_ok=True)
        # Validate the entire target before writing, avoiding a partly replaced export.
        for name, data in payloads.items():
            if (out/name).exists() and (out/name).read_bytes() != data:
                raise ValueError('immutable export target differs; choose new directory: '+name)
        for name, data in payloads.items():
            _write_new_or_identical(out/name,data)
        return receipt
    finally:
        con.close()
