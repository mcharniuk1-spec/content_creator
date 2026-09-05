#!/usr/bin/env python3
"""Pinned M2 Signal/Studio runner. Default is a local plan; HikerAPI is separate."""
import argparse
import json
from pathlib import Path
from m2_orchestrator.execution import DETERMINISTIC_STAGES, execute_replay
from m2_signal import import_legacy_db


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--yes',action='store_true',help='Execute local analysis only; does not enable collection or writeback')
    p.add_argument('--source-dir',type=Path)
    p.add_argument('--legacy-db',type=Path)
    p.add_argument('--snapshot-date')
    p.add_argument('--run-id')
    p.add_argument('--run-dir',type=Path)
    p.add_argument('--database',type=Path)
    p.add_argument('--mode',choices=['replay','incremental','server'],default='replay')
    p.add_argument('--until',choices=DETERMINISTIC_STAGES)
    p.add_argument('--metric-config',type=Path)
    a=p.parse_args(argv)
    if not a.yes:
        print(json.dumps({'mode':'PLAN_ONLY','hikerapi_requests':0,'provider_requests':0,'notion_writes':0,
                          'next':'Select a pinned export or legacy snapshot; add --yes, --run-id and --run-dir for local analysis.'}))
        return 0
    if not a.run_id or not a.run_dir or bool(a.source_dir)==bool(a.legacy_db):
        p.error('--yes requires --run-id, --run-dir and exactly one of --source-dir or --legacy-db')
    source=a.source_dir
    if a.legacy_db:
        if not a.snapshot_date:p.error('--legacy-db requires --snapshot-date')
        source=a.run_dir/'legacy-export'
        import_legacy_db(a.legacy_db,source,a.snapshot_date)
    settings=json.loads(a.metric_config.read_text()) if a.metric_config else None
    result=execute_replay(source,a.run_dir,a.run_id,a.mode,a.until,settings,database=a.database)
    print(json.dumps({'run_id':result['run_id'],'stages_completed':sum(s['state'] in ['PASS','PASS_WITH_LIMITATIONS'] for s in result['stages']),
                      'next':'Export bounded semantic role tasks; independent review precedes Signal release and Studio promotion.',
                      'hikerapi_requests':0,'provider_requests':0,'notion_writes':0}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
