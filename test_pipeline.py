"""Clean-checkout entry behavior, real local replay and explicit server gates.

Run as a script. Historical private-database tests are not imported by this suite.
"""
import csv
import json
import os
import sqlite3
from contextlib import closing
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io
from pathlib import Path

ROOT=Path(__file__).resolve().parent


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'export';self.source.mkdir()
        self.write_export()
        self.env={k:v for k,v in os.environ.items() if k not in ['HIKER_KEY','HIKERAPI_KEY','NOTION_TOKEN','OPENAI_API_KEY','RUNWAY_API_SECRET']}

    def tearDown(self):self.tmp.cleanup()

    def write_export(self,taken='2026-09-05',n=6):
        fields=['code','user','url','play','like','comment','reshare','save','duration_s','ts','caption']
        with (self.source/'reels.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            for i in range(n):w.writerow(dict(code='FIXTURE'+str(i),user='synthetic_creator',url='https://example.invalid/reel/'+str(i),
                play=1000*(i+1),like=20*(i+1),comment=2,reshare=3,save=None if i==0 else 2,duration_s=20,ts=1788500000+i,caption='Synthetic fixture'))
        (self.source/'accounts.csv').write_text('username,followers,media_count,category,biography\nsynthetic_creator,100,10,test,\n')
        (self.source/'snapshot.json').write_text(json.dumps({'taken':taken,'accounts':1}))

    def command(self,*args,success=True):
        result=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=self.env,text=True,capture_output=True,timeout=60)
        if success:self.assertEqual(result.returncode,0,result.stderr)
        else:self.assertNotEqual(result.returncode,0)
        return result

    def replay_args(self,run_id='synthetic-a',directory=None):
        return ['run.py','--yes','--source-dir',self.source,'--run-id',run_id,'--run-dir',directory or self.root/run_id]

    def test_default_plan_has_no_external_activity_or_input_requirement(self):
        result=json.loads(self.command('run.py').stdout)
        self.assertEqual(result['mode'],'PLAN_ONLY')
        self.assertEqual([result[k] for k in ['hikerapi_requests','provider_requests','notion_writes']],[0,0,0])

    def test_execution_requires_exact_input_and_run_scope(self):
        self.command('run.py','--yes',success=False)
        self.command(*self.replay_args(),'--until','misspelled_stage',success=False)
        self.assertFalse((self.root/'synthetic-a').exists())

    def test_local_replay_resumes_identical_and_exports_future_roles(self):
        first=json.loads(self.command(*self.replay_args()).stdout)
        self.assertEqual(first['stages_completed'],12)
        trace=self.command('-m','m2_orchestrator','--run-dir',self.root/'synthetic-a','verify')
        verified=json.loads(trace.stdout);self.assertEqual(verified['state'],'PASS')
        self.command(*self.replay_args())
        again=json.loads(self.command('-m','m2_orchestrator','--run-dir',self.root/'synthetic-a','verify').stdout)
        self.assertEqual(verified,again)
        tasks=json.loads(self.command('-m','m2_orchestrator','--run-dir',self.root/'synthetic-a','tasks').stdout)
        self.assertIn('review_signal',{t['id'] for t in tasks})
        summary=json.loads((self.root/'synthetic-a/signal/summary.json').read_text())
        self.assertEqual(summary['population']['canonical_reels'],6)
        self.assertFalse(summary['evidence_release_accepted'])

    def test_incremental_snapshots_share_immutable_history_with_scoped_counts(self):
        ledger=self.root/'shared.sqlite'
        self.command(*self.replay_args(),'--mode','incremental','--database',ledger)
        self.write_export('2026-09-06',7)
        self.command(*self.replay_args('synthetic-b'),'--mode','incremental','--database',ledger)
        with closing(sqlite3.connect(ledger)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM releases').fetchone()[0],2)
            counts=sorted(r[0] for r in db.execute('SELECT count(*) FROM reel_analysis GROUP BY release_id'))
            self.assertEqual(counts,[6,7])

    def test_bounded_stop_resume_and_frozen_input_rejection(self):
        result=json.loads(self.command(*self.replay_args(),'--until','rank_candidates').stdout)
        self.assertEqual(result['stages_completed'],9)
        self.command(*self.replay_args())
        self.write_export(n=7)
        self.command(*self.replay_args(),success=False)

    def test_server_same_engine_and_concurrent_lock_rejection(self):
        config=self.root/'server.json';runroot=self.root/'server-run'
        config.write_text(json.dumps({'source_dir':str(self.source),'run_dir':str(runroot),'run_id':'synthetic-server',
                                      'private_run_root':str(self.root),'private_source_roots':[str(self.root)]}))
        result=json.loads(self.command('server_entry.py','--config',config).stdout)
        self.assertEqual(result['hikerapi_calls'],0);self.assertEqual(result['external_writes'],0)
        import fcntl
        with (runroot/'server.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=self.command('server_entry.py','--config',config,success=False)
            self.assertIn('RUN_ALREADY_ACTIVE',result.stderr)

    def test_latest_completed_snapshot_is_explicit_read_only_server_policy(self):
        from server_entry import resolve_config
        legacy=self.root/'legacy.sqlite'
        with closing(sqlite3.connect(legacy)) as db:
            db.executescript("CREATE TABLE snapshots(taken TEXT,done INTEGER);INSERT INTO snapshots VALUES('2026-09-01',1),('2026-09-03',1),('2026-09-04',0);")
        config=resolve_config({'legacy_db':str(legacy),'snapshot_date':'latest_completed','run_id':'s-{snapshot_date}',
                               'run_dir':str(self.root/'out/{snapshot_date}'),
                               'private_run_root':str(self.root),'private_source_roots':[str(self.root)]})
        self.assertEqual(config['snapshot_date'],'2026-09-03');self.assertEqual(config['run_id'],'s-2026-09-03')

    def test_hiker_server_defaults_plan_and_refuses_unauthorized_execution(self):
        config={'run_id':'fixture-pilot','snapshot_date':'2026-09-05','accounts':[{'user_id':'123','username':'fixture_creator','followers':100,'public_source_authorized':True}],
            'max_pages_per_account':1,'max_requests':1,'request_timeout_seconds':10,'maximum_cost_usd':'0.10',
            'request_cost_ceiling_usd':'0.10','price_receipt_sha256':'0'*64,'earliest_published_epoch_seconds':None}
        path=self.root/'hiker.json';path.write_text(json.dumps(config))
        result=json.loads(self.command('hiker_server.py','--config',path).stdout)
        self.assertEqual(result['mode'],'PLAN_ONLY');self.assertEqual(result['hikerapi_requests'],0)
        self.command('hiker_server.py','--config',path,'--execute',success=False)

    def collection_chain(self,blocked=False,allow_partial=False):
        import hiker_server
        from m2_signal.hiker_adapter import collect as fixture_collect
        config={'run_id':'fixture-chain','snapshot_date':'2026-09-05','accounts':[{'user_id':'123','username':'fixture_creator','followers':100,'public_source_authorized':True}],
            'max_pages_per_account':1,'max_requests':1,'request_timeout_seconds':10,'maximum_cost_usd':'0.10',
            'request_cost_ceiling_usd':'0.10','price_receipt_sha256':'0'*64,'earliest_published_epoch_seconds':None}
        path=self.root/'chain.json';path.write_text(json.dumps(config))
        def transport(*_):
            if blocked:raise TimeoutError()
            return {'items':[{'code':'ABCDE','user':{'pk':123,'username':'fixture_creator'},'product_type':'clips',
                'taken_at':1788500000,'play_count':1500,'like_count':10,'comment_count':None,'reshare_count':1,
                'save_count':None,'video_duration':20}],'more_available':False,'max_id':None}
        def injected(config,private_dir,**_):return fixture_collect(config,private_dir,transport=transport)
        args=['--config',str(path),'--private-dir',str(self.root/'private'),'--approval',str(self.root/'synthetic-unused-approval'),
              '--execute','--then-replay-run-id','fixture-offline','--then-replay-run-dir',str(self.root/'offline')]
        if allow_partial:args.append('--allow-partial-replay')
        with patch('hiker_server.collect',side_effect=injected),redirect_stdout(io.StringIO()) as output:
            code=hiker_server.main(args)
        return code,json.loads(output.getvalue())

    def test_fixture_collection_export_chains_to_same_offline_engine(self):
        code,result=self.collection_chain()
        self.assertEqual(code,0);self.assertEqual(result['offline_run_id'],'fixture-offline')
        summary=json.loads((self.root/'offline/signal/summary.json').read_text())
        self.assertEqual(summary['population']['source_observations'],1)
        self.assertFalse(summary['evidence_release_accepted'])

    def test_blocked_collection_exits_nonzero_and_does_not_silently_chain(self):
        code,result=self.collection_chain(blocked=True)
        self.assertEqual(code,2);self.assertTrue(result['partial_capture'])
        self.assertIsNone(result['offline_run_id']);self.assertFalse((self.root/'offline').exists())
        self.assertTrue(list((self.root/'private/fixture-chain').glob('receipt-*.json')))

    def test_partial_replay_requires_explicit_flag_and_preserves_blocked_exit(self):
        code,result=self.collection_chain(blocked=True,allow_partial=True)
        self.assertEqual(code,2);self.assertTrue(result['partial_capture'])
        self.assertEqual(result['offline_run_id'],'fixture-offline')
        self.assertTrue((self.root/'offline/inputs/collection-receipt.json').exists())


if __name__=='__main__':unittest.main()
