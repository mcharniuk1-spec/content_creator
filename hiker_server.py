#!/usr/bin/env python3
"""Explicit future HikerAPI pilot/collection entry; default is a local plan.

Credentials are injected through HIKER_KEY or HIKERAPI_KEY by the server. This
command does not inspect environment credentials unless all live gates pass.
"""
import argparse
import json
from pathlib import Path

from m2_signal.engine import digest
from m2_signal.hiker_adapter import collect, validate_collection_config


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--private-dir',type=Path)
    p.add_argument('--approval',type=Path)
    p.add_argument('--schema-receipt',type=Path)
    p.add_argument('--then-replay-run-id')
    p.add_argument('--then-replay-run-dir',type=Path)
    p.add_argument('--allow-partial-replay',action='store_true',help='Explicitly analyze an incomplete capture; blocked collection still exits nonzero')
    p.add_argument('--database',type=Path)
    p.add_argument('--execute',action='store_true',help='Request gated server-only live execution; may incur separately approved charges')
    a=p.parse_args(argv)
    config=validate_collection_config(json.loads(a.config.read_text()))
    if not a.execute:
        print(json.dumps({'mode':'PLAN_ONLY','config_sha256':digest(config),'accounts':len(config['accounts']),
            'max_requests':config['max_requests'],'maximum_cost_usd':config['maximum_cost_usd'],
            'live_schema_state':'LIVE_SCHEMA_UNVERIFIED','hikerapi_requests':0,
            'next':'Review exact one-request pilot approval; inject server secret; add --execute only after authorization.'}))
        return 0
    if not a.private_dir or not a.approval:
        p.error('--execute requires --private-dir and --approval')
    if bool(a.then_replay_run_id)!=bool(a.then_replay_run_dir):
        p.error('offline replay chain requires both --then-replay-run-id and --then-replay-run-dir')
    result=collect(config,a.private_dir,execute_live=True,approval_path=a.approval,schema_receipt_path=a.schema_receipt)
    blocked=result['stage_state'] not in {'PASS','PASS_WITH_LIMITATIONS'}
    if a.then_replay_run_dir and (not blocked or a.allow_partial_replay):
        from m2_orchestrator.execution import execute_replay
        source=a.private_dir/config['run_id']/'export'
        # The collection completeness/budget receipt is frozen with the export
        # before the offline controller hashes its source manifest.
        receipt_path=source/'collection-receipt.json'
        body=json.dumps(result,sort_keys=True,indent=2)+'\n'
        if receipt_path.exists() and receipt_path.read_text()!=body:
            raise ValueError('collection receipt changed; create a new exact run')
        if not receipt_path.exists():receipt_path.write_text(body)
        offline=execute_replay(source,a.then_replay_run_dir,a.then_replay_run_id,'server',database=a.database)
        result['offline_run_id']=offline['run_id']

    report={k:result[k] for k in ['execution_mode','stage_state','observations','dispatched_requests',
           'reserved_cost_upper_bound_usd','actual_provider_charge_usd','billing_state','automatic_retries','live_schema_state']}
    report['offline_run_id']=result.get('offline_run_id')
    report['partial_capture']=blocked
    print(json.dumps(report))
    return 2 if blocked else 0


if __name__=='__main__':raise SystemExit(main())
