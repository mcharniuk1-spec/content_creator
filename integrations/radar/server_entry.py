#!/usr/bin/env python3
"""Explicit replay timer with an optional, separately configured serial media job."""
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

from m2_orchestrator.execution import DETERMINISTIC_STAGES, execute_replay
from m2_signal import import_legacy_db
from m2_orchestrator.state import Controller, digest, file_digest
from m2_orchestrator.policy import SUCCESS


def safe_path(value):
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError('SERVER_PATH_INVALID')
    path=Path(value).absolute()
    if path.is_symlink() or any(p.is_symlink() and str(p) not in {'/tmp','/var'} for p in path.parents):
        raise ValueError('SERVER_PATH_SYMLINK')
    if path.is_file() and path.stat().st_nlink != 1:
        raise ValueError('SERVER_PATH_HARDLINK')
    return path.resolve()


def validate_paths(config):
    private=safe_path(config['private_run_root'])
    roots=config['private_source_roots']
    if not isinstance(roots,list) or not roots:
        raise ValueError('SERVER_SOURCE_ROOTS_REQUIRED')
    roots=[safe_path(p) for p in roots]
    for area in [private,*roots]:
        if area in {Path('/'),Path.home(),Path.home()/'Documents'}:
            raise ValueError('SERVER_SCOPE_TOO_BROAD')
    run=safe_path(config['run_dir'])
    if run==private or not run.is_relative_to(private):
        raise ValueError('SERVER_RUN_OUTSIDE_PRIVATE_ROOT')
    for key in ('source_dir','legacy_db','metric_config','media_job_config'):
        if config.get(key):
            path=safe_path(config[key])
            if not any(path.is_relative_to(root) for root in roots):
                raise ValueError('SERVER_INPUT_OUTSIDE_APPROVED_ROOT')
    if config.get('database') and not safe_path(config['database']).is_relative_to(private):
        raise ValueError('SERVER_DATABASE_OUTSIDE_PRIVATE_ROOT')
    # Protect replay and media state that already exists before either writes.
    if run.exists():
        for path in run.rglob('*'):
            safe_path(path)
    safe_path(run/'server.lock')
    return run


def completed_replay(root,result,run_id):
    if not isinstance(result,dict) or result.get('schema')!='m2.run-status.v1' or result.get('run_id')!=run_id:
        raise ValueError('SERVER_REPLAY_STATUS_INVALID')
    stages=result.get('stages')
    if not isinstance(stages,list):
        raise ValueError('SERVER_REPLAY_STATUS_INVALID')
    states={s.get('id'):s.get('state') for s in stages if isinstance(s,dict)}
    if any(states.get(stage) not in SUCCESS for stage in DETERMINISTIC_STAGES):
        raise ValueError('SERVER_REPLAY_INCOMPLETE')
    controller=Controller(root)
    if controller.status()!=result:
        raise ValueError('SERVER_REPLAY_STATUS_MISMATCH')
    verification=controller.verify()
    if verification.get('state')!='PASS':
        raise ValueError('SERVER_REPLAY_VERIFICATION_FAILED')
    proof={'schema':'m2.server-replay-completion.v1','run_id':run_id,
           'config_hash':result['config_hash'],'trace':verification,
           'status_hash':digest(result),'reels_sha256':file_digest(safe_path(root/'signal/reels.jsonl'))}
    path=safe_path(root/'media-replay-completion.json')
    if path.exists():
        if json.loads(path.read_text())!=proof:
            raise ValueError('SERVER_REPLAY_COMPLETION_CHANGED')
    else:
        with path.open('x') as f:json.dump(proof,f,indent=2)
    return proof


def resolve_config(config):
    allowed={'source_dir','legacy_db','snapshot_date','run_dir','run_id','database','metric_config','until','media_job_config','private_run_root','private_source_roots'}
    if not isinstance(config,dict) or set(config)-allowed or not {'run_dir','run_id','private_run_root','private_source_roots'}<=set(config):
        raise ValueError('explicit local server fields required')
    config=dict(config)
    if 'media_job_config' in config:
        if not isinstance(config['media_job_config'], str) or not config['media_job_config'].strip():
            raise ValueError('media_job_config must be an explicit private config path')
        if config.get('until'):
            raise ValueError('media job requires completed replay; omit until or run media separately')
    if bool(config.get('source_dir'))==bool(config.get('legacy_db')):
        raise ValueError('select exactly one input route')
    if config.get('until') and config['until'] not in DETERMINISTIC_STAGES:
        raise ValueError('unknown deterministic stop stage')
    if config.get('legacy_db'):
        if not config.get('snapshot_date'):
            raise ValueError('snapshot_date required')
        if config['snapshot_date']=='latest_completed':
            validate_paths(config)
            source=safe_path(config['legacy_db'])
            if not source.is_file():raise ValueError('legacy database must already exist')
            with closing(sqlite3.connect('file:'+quote(str(source))+'?mode=ro',uri=True)) as db:
                row=db.execute('SELECT taken FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()
            if not row:raise ValueError('no completed legacy snapshot')
            config['snapshot_date']=row[0]
        for name in ('run_id','run_dir'):
            config[name]=config[name].replace('{snapshot_date}',config['snapshot_date'])
    validate_paths(config)
    return config


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    a=p.parse_args(argv)
    config=resolve_config(json.loads(safe_path(a.config).read_text()))
    root=validate_paths(config);root.mkdir(parents=True,exist_ok=True)
    # Kernel releases this advisory lock after a crash; never remove a live lock.
    import fcntl
    with (root/'server.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('RUN_ALREADY_ACTIVE')
        timer_binding={'schema':'m2.server-config-binding.v1','config':config,'config_hash':digest(config)}
        binding=safe_path(root/'server-config-binding.json')
        if binding.exists():
            if json.loads(binding.read_text())!=timer_binding:raise ValueError('SERVER_CONFIG_CHANGED_REQUIRES_NEW_RUN')
        else:
            with binding.open('x') as f:json.dump(timer_binding,f,indent=2)
        source=config.get('source_dir')
        if config.get('legacy_db'):
            source=root/'legacy-export'
            import_legacy_db(config['legacy_db'],source,config['snapshot_date'])
        settings=json.loads(Path(config['metric_config']).read_text()) if config.get('metric_config') else None
        result=execute_replay(source,root,config['run_id'],'server',config.get('until'),settings,database=config.get('database'))
        media_result=None
        if config.get('media_job_config'):
            from m2_orchestrator.server_media import execute_media_job
            proof=completed_replay(root,result,config['run_id'])
            if proof['reels_sha256']!=file_digest(safe_path(root/'signal/reels.jsonl')):
                raise ValueError('SERVER_REEL_EXPORT_CHANGED')
            media_result=execute_media_job(config['media_job_config'],root/'signal/reels.jsonl',root/'media-job')
        print(json.dumps({'run_id':result['run_id'],'hikerapi_calls':0,'llm_calls':0,'external_writes':0,
                          'media_job_requested':bool(config.get('media_job_config')),'media_job_result':media_result,
                          'next':'bounded_role_tasks_and_independent_review'}))
    return 0


if __name__=='__main__':raise SystemExit(main())
