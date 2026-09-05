#!/usr/bin/env python3
"""Explicit timer adapter; no Git pull, install, provider call or implicit collection."""
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

from m2_orchestrator.execution import DETERMINISTIC_STAGES, execute_replay
from m2_signal import import_legacy_db


def resolve_config(config):
    allowed={'source_dir','legacy_db','snapshot_date','run_dir','run_id','database','metric_config','until'}
    if set(config)-allowed or not {'run_dir','run_id'}<=set(config):
        raise ValueError('explicit local server fields required')
    config=dict(config)
    if bool(config.get('source_dir'))==bool(config.get('legacy_db')):
        raise ValueError('select exactly one input route')
    if config.get('until') and config['until'] not in DETERMINISTIC_STAGES:
        raise ValueError('unknown deterministic stop stage')
    if config.get('legacy_db'):
        if not config.get('snapshot_date'):
            raise ValueError('snapshot_date required')
        if config['snapshot_date']=='latest_completed':
            source=Path(config['legacy_db']).resolve()
            if not source.is_file():raise ValueError('legacy database must already exist')
            with closing(sqlite3.connect('file:'+quote(str(source))+'?mode=ro',uri=True)) as db:
                row=db.execute('SELECT taken FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()
            if not row:raise ValueError('no completed legacy snapshot')
            config['snapshot_date']=row[0]
        for name in ('run_id','run_dir'):
            config[name]=config[name].replace('{snapshot_date}',config['snapshot_date'])
    return config


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    a=p.parse_args(argv)
    config=resolve_config(json.loads(a.config.read_text()))
    root=Path(config['run_dir']);root.mkdir(parents=True,exist_ok=True)
    # Kernel releases this advisory lock after a crash; never remove a live lock.
    import fcntl
    with (root/'server.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('RUN_ALREADY_ACTIVE')
        source=config.get('source_dir')
        if config.get('legacy_db'):
            source=root/'legacy-export'
            import_legacy_db(config['legacy_db'],source,config['snapshot_date'])
        settings=json.loads(Path(config['metric_config']).read_text()) if config.get('metric_config') else None
        result=execute_replay(source,root,config['run_id'],'server',config.get('until'),settings,database=config.get('database'))
        print(json.dumps({'run_id':result['run_id'],'hikerapi_calls':0,'model_calls':0,'external_writes':0,
                          'next':'bounded_role_tasks_and_independent_review'}))
    return 0


if __name__=='__main__':raise SystemExit(main())
