"""Transaction-consistent, non-overwriting SQLite backup; no credentials/media copy."""
import argparse, hashlib, json, sqlite3
from pathlib import Path
from datetime import datetime, timezone

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args()
    if not a.source.is_file():raise ValueError('SOURCE_MISSING')
    if a.destination.exists() or a.manifest.exists():raise ValueError('OUTPUT_EXISTS')
    a.destination.parent.mkdir(parents=True,exist_ok=True)
    # Reserve destination exclusively before SQLite opens it.
    with a.destination.open('xb'):pass
    with sqlite3.connect(a.source.resolve().as_uri()+'?mode=ro',uri=True) as source, sqlite3.connect(a.destination) as target:
        source.backup(target)
        check=target.execute('pragma integrity_check').fetchall()
        if check!=[('ok',)]:raise ValueError('BACKUP_INTEGRITY_FAILED')
        tables={r[0]:target.execute('select count(*) from "'+r[0].replace('"','""')+'"').fetchone()[0] for r in target.execute("select name from sqlite_master where type='table'").fetchall()}
    with a.manifest.open('x') as f:json.dump({'captured_at':datetime.now(timezone.utc).isoformat(),'method':'sqlite_backup_api','sha256':hashlib.sha256(a.destination.read_bytes()).hexdigest(),'bytes':a.destination.stat().st_size,'integrity':'ok','table_counts':tables,'artifacts':'SEPARATE_MANIFEST_REQUIRED'},f,indent=2)
    print('PASS: consistent backup and integrity check; artifacts require separate manifest')
if __name__=='__main__':main()
