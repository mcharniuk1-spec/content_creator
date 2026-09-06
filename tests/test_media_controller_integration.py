import csv
import json
import sqlite3
import sys
from pathlib import Path
import pytest
from m2_orchestrator.execution import execute_replay, default_actors
from m2_orchestrator.state import file_digest, Controller, StateError
from m2_orchestrator.process_budget import bounded_process, ProcessBudgetError


def export(root):
    root.mkdir()
    rows=[dict(code='CODE'+str(i),user='creator',play=1000*(i+1),like=30,comment=2,reshare=3,save=1,duration_s=20,ts=1788200000+i) for i in range(6)]
    with (root/'reels.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (root/'accounts.csv').write_text('username,followers,media_count\ncreator,100,20\n')
    (root/'snapshot.json').write_text(json.dumps({'taken':'2026-09-01','accounts':1}))


def test_acquisition_executes_inside_controller_and_preserves_denominator(tmp_path):
    source=tmp_path/'source';export(source)
    # First obtain the canonical IDs through the actual normalizer.
    execute_replay(source,tmp_path/'baseline','baseline',until='audit_all_rows')
    reels=[json.loads(s) for s in (tmp_path/'baseline/signal/reels.jsonl').read_text().splitlines()]
    mf=tmp_path/'manifest.json';mf.write_text(json.dumps({'entries':[{'reel_id':r['reel_id'],'code':r['code'],'sources':[],'quarantine_reasons':[]} for r in reels]}))
    conf={'enabled':True,'manifest_path':str(mf),'manifest_sha256':file_digest(mf),'network':False,'media_roots':[]}
    status=execute_replay(source,tmp_path/'run','fixture',until='media_acquire',media_config=conf)
    assert next(s for s in status['stages'] if s['id']=='media_acquire')['state']=='PASS_WITH_LIMITATIONS'
    product=json.loads((tmp_path/'run/products/media_acquire.json').read_text())
    assert product['population']==6 and product['states']=={'NO_SOURCE_LOCATOR':6}
    assert product['hikerapi_calls']==0 and not product['complete_media_coverage']
    assert Controller(tmp_path/'run').verify()['state']=='PASS'
    assert execute_replay(source,tmp_path/'run','fixture',until='media_acquire',media_config=conf)['run_id']=='fixture'


def test_subprocess_output_limit_and_timeout():
    with pytest.raises(ProcessBudgetError,match='OUTPUT_LIMIT'):
        bounded_process([sys.executable,'-c','import sys;sys.stdout.write("x"*100000)'],stdout_limit=100)
    with pytest.raises(ProcessBudgetError,match='TIMEOUT'):
        bounded_process([sys.executable,'-c','import time;time.sleep(30)'],timeout=.1)


def test_environment_does_not_inherit_secrets(monkeypatch):
    monkeypatch.setenv('M2_TEST_CREDENTIAL','must-not-inherit')
    r=bounded_process([sys.executable,'-c','import os;print(os.getenv("M2_TEST_CREDENTIAL"))'])
    assert r['stdout'].strip()==b'None'


def test_heartbeat_cannot_revive_expired_worker(tmp_path):
    c=Controller(tmp_path/'controller')
    c.init('heartbeat',{'schema':'m2.run-config.v1','platforms':['instagram_reels'],'mode':'replay','provider_execution':False,'hikerapi_execution':False,'actors':default_actors(),'source_manifest':[{'source_id':'fixture','sha256':'0'*64}]})
    start=c.begin('admit','integrator')
    c.heartbeat('admit',start['token'],progress={'processed':1})
    with sqlite3.connect(c.db) as db:db.execute("UPDATE stages SET lease_until=0 WHERE id='admit'")
    with pytest.raises(StateError,match='STALE'):c.heartbeat('admit',start['token'])
