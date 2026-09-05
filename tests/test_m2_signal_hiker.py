"""Only injected fixtures run here; no request reaches HikerAPI."""
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from m2_signal.hiker_adapter import ENDPOINT, _approval, collect,validate_collection_config
from m2_signal.engine import digest,file_hash


class HikerAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.config={'run_id':'fixture-run','snapshot_date':'2026-09-05',
            'accounts':[{'user_id':'123','username':'creator','followers':100,'public_source_authorized':True}],
            'max_pages_per_account':3,'max_requests':3,'request_timeout_seconds':10,
            'maximum_cost_usd':'0.30','request_cost_ceiling_usd':'0.10','price_receipt_sha256':'0'*64,
            'earliest_published_epoch_seconds':1000}
        self.item={'code':'ABCDE','user':{'pk':123,'username':'creator'},'product_type':'clips',
                   'taken_at':2000,'play_count':1500,'like_count':30,'comment_count':None,
                   'reshare_count':5,'save_count':None,'video_duration':20,
                   'caption':{'text':'fixture'},'video_versions':[{'url':'https://example.invalid/video.mp4?temporary=secret'}]}

    def tearDown(self):self.temp.cleanup()

    def test_pages_cursor_nulls_callback_and_idempotent_resume(self):
        calls=[]; callbacks=[]
        def transport(params,timeout):
            calls.append(params)
            if len(calls)==1:return {'items':[self.item],'max_id':'NEXT','more_available':True}
            return {'items':[dict(self.item,code='FGHIJ')],'max_id':None,'more_available':False}
        first=collect(self.config,self.root,transport=transport,on_media=lambda code,refs,ctx:callbacks.append((code,refs,ctx)))
        self.assertEqual(len(calls),2);self.assertEqual(calls[1]['max_id'],'NEXT')
        self.assertEqual(first['observations'],2);self.assertEqual(first['external_calls'],0)
        self.assertEqual(first['source_exhausted_accounts'],1)
        second=collect(self.config,self.root,transport=lambda *_:self.fail('must replay immutable pages'),on_media=lambda *_:self.fail('must not repeat callback'))
        self.assertEqual(first,second);self.assertEqual(len(callbacks),2)
        with (self.root/'fixture-run/export/reels.csv').open() as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(rows[0]['comment'],'');self.assertEqual(rows[0]['save'],'')
        self.assertNotIn('temporary',json.dumps(first))
        self.assertEqual((self.root/'fixture-run/config.json').stat().st_mode&0o777,0o600)

    def test_page_cap_is_not_exhaustion(self):
        config=dict(self.config,max_pages_per_account=1)
        result=collect(config,self.root,transport=lambda *_:{'items':[self.item],'max_id':'NEXT','more_available':True})
        self.assertEqual(result['accounts'][0]['stop_reason'],'PAGE_CAP_REACHED')
        self.assertEqual(result['source_exhausted_accounts'],0)

    def test_budget_reserved_before_dispatch_and_never_exceeded(self):
        config=dict(self.config,maximum_cost_usd='0.05')
        result=collect(config,self.root,transport=lambda *_:self.fail('budget must block before request'))
        self.assertEqual(result['dispatched_requests'],0)
        self.assertEqual(result['accounts'][0]['stop_reason'],'BUDGET_BLOCKED_BEFORE_DISPATCH')

    def test_timeout_no_blind_retry_even_after_resume(self):
        calls=[]
        def transport(*args):calls.append(args);raise TimeoutError('credential text must not leak')
        first=collect(self.config,self.root,transport=transport)
        second=collect(self.config,self.root,transport=transport)
        self.assertEqual(len(calls),1)
        self.assertEqual(first['accounts'][0]['stop_reason'],'TIMEOUT_OUTCOME_UNKNOWN')
        self.assertEqual(second['accounts'][0]['stop_reason'],'UNCERTAIN_PREVIOUS_DISPATCH_REQUIRES_RECONCILIATION')
        self.assertIsNone(first['actual_provider_charge_usd'])
        self.assertNotIn('credential text',''.join(p.read_text() for p in (self.root/'fixture-run/checkpoints').iterdir()))

    def test_window_filter_does_not_assume_sorted_or_pinned_feed(self):
        calls=[]
        def transport(params,timeout):
            calls.append(1)
            if len(calls)==1:return {'items':[dict(self.item,taken_at=500)],'max_id':'NEXT','more_available':True}
            return {'items':[self.item],'max_id':None,'more_available':False}
        result=collect(self.config,self.root,transport=transport)
        self.assertEqual(len(calls),2);self.assertEqual(result['window_excluded'],1)
        self.assertEqual(result['observations'],1)

    def test_malformed_schema_blocks_with_raw_page_preserved(self):
        result=collect(self.config,self.root,transport=lambda *_:{'data':{},'status':'ok'})
        self.assertEqual(result['accounts'][0]['stop_reason'],'RESPONSE_SCHEMA_BLOCKED')
        self.assertEqual(len(list((self.root/'fixture-run/pages').glob('*.json'))),1)

    def test_attribution_and_path_code_quarantined(self):
        items=[dict(self.item,code='../../escape'),dict(self.item,user={'pk':999,'username':'other'}),dict(self.item,user='bad')]
        result=collect(self.config,self.root,transport=lambda *_:{'items':items,'max_id':None,'more_available':False})
        self.assertEqual(len(result['quarantines']),3);self.assertEqual(result['observations'],0)

    def test_live_disabled_and_exact_approval_required_before_transport_creation(self):
        with patch('m2_signal.hiker_adapter.LiveTransport',side_effect=AssertionError('no live transport should be constructed')):
            with self.assertRaisesRegex(ValueError,'disabled'):
                collect(self.config,self.root)
            with self.assertRaisesRegex(ValueError,'approval'):
                collect(self.config,self.root,execute_live=True)

    def test_expired_approval_and_config_drift_block_before_dispatch(self):
        approval=self.root/'approval.json'
        approval.write_text(json.dumps({'scopes':['hikerapi_instagram_reels_collection'],'config_sha256':'different'}))
        with self.assertRaisesRegex(ValueError,'mismatch'):
            collect(self.config,self.root,execute_live=True,approval_path=approval)
        self.assertFalse((self.root/'fixture-run').exists())

    def test_full_server_scope_requires_independent_bound_live_schema_evidence(self):
        response=self.root/'response.json'
        response.write_text(json.dumps({'items':[self.item],'max_id':'NEXT','more_available':True}))
        receipt=self.root/'schema-receipt.json'
        proof={'endpoint':ENDPOINT,'evidence_source':'LIVE','review_state':'APPROVED',
               'maker':'fixture-maker','reviewer':'fixture-reviewer','expires_at':'2099-01-01T00:00:00Z',
               'response_path':'response.json','response_sha256':file_hash(response)}
        receipt.write_text(json.dumps(proof))
        approval=self.root/'approval.json'
        owner={'scopes':['hikerapi_instagram_reels_collection'],'config_sha256':digest(self.config),
               'approved':True,'approved_by':'fixture-owner','approval_id':'fixture-event',
               'expires_at':'2099-01-01T00:00:00Z','schema_receipt_sha256':file_hash(receipt)}
        approval.write_text(json.dumps(owner))
        self.assertEqual(_approval(self.config,approval,schema_receipt_path=receipt)['approval_id'],'fixture-event')
        proof['reviewer']='fixture-maker';receipt.write_text(json.dumps(proof))
        with self.assertRaisesRegex(ValueError,'independent'):
            _approval(self.config,approval,schema_receipt_path=receipt)

    def test_config_rejects_credentials_and_unapproved_sources(self):
        with self.assertRaises(ValueError):validate_collection_config(dict(self.config,api_key='forbidden'))
        changed=copy.deepcopy(self.config);changed['accounts'][0]['public_source_authorized']=False
        with self.assertRaises(ValueError):validate_collection_config(changed)

    def live_fixture_approvals(self):
        response=self.root/'synthetic-response.json'
        response.write_text(json.dumps({'items':[self.item],'max_id':'NEXT','more_available':True}))
        schema=self.root/'synthetic-schema-receipt.json'
        schema.write_text(json.dumps({'endpoint':ENDPOINT,'evidence_source':'LIVE','review_state':'APPROVED',
            'maker':'fixture-maker','reviewer':'fixture-reviewer','expires_at':'2099-01-01T00:00:00Z',
            'response_path':response.name,'response_sha256':file_hash(response)}))
        approval=self.root/'synthetic-owner-approval.json'
        approval.write_text(json.dumps({'approved':True,'approved_by':'fixture-owner','approval_id':'fixture-only',
            'scopes':['hikerapi_instagram_reels_collection'],'config_sha256':digest(self.config),
            'schema_receipt_sha256':file_hash(schema),'expires_at':'2099-01-01T00:00:00Z'}))
        return approval,schema

    def test_revocation_before_second_dispatch_stops_without_another_request(self):
        approval,schema=self.live_fixture_approvals()
        calls=[]
        def transport(*_):
            calls.append(1)
            changed=json.loads(approval.read_text());changed['approved']=False
            approval.write_text(json.dumps(changed))
            return {'items':[self.item],'max_id':'NEXT','more_available':True}
        with patch('m2_signal.hiker_adapter.LiveTransport',return_value=transport):
            with self.assertRaisesRegex(ValueError,'owner approval'):
                collect(self.config,self.root,execute_live=True,approval_path=approval,schema_receipt_path=schema)
        self.assertEqual(len(calls),1)
        self.assertEqual(len(list((self.root/'fixture-run/dispatch').glob('*.json'))),1)

    def test_expiry_before_second_dispatch_stops_without_another_request(self):
        approval,schema=self.live_fixture_approvals()
        calls=[]
        def transport(*_):
            calls.append(1)
            changed=json.loads(approval.read_text());changed['expires_at']='2000-01-01T00:00:00Z'
            approval.write_text(json.dumps(changed))
            return {'items':[self.item],'max_id':'NEXT','more_available':True}
        with patch('m2_signal.hiker_adapter.LiveTransport',return_value=transport):
            with self.assertRaisesRegex(ValueError,'expired'):
                collect(self.config,self.root,execute_live=True,approval_path=approval,schema_receipt_path=schema)
        self.assertEqual(len(calls),1)

    def test_fixture_cache_cannot_be_relabelled_as_live(self):
        collect(self.config,self.root,transport=lambda *_:{'items':[self.item],'max_id':None,'more_available':False})
        approval,schema=self.live_fixture_approvals()
        with patch('m2_signal.hiker_adapter.LiveTransport',return_value=lambda *_:self.fail('no second transport call')):
            with self.assertRaisesRegex(ValueError,'immutable Hiker artifact conflict'):
                collect(self.config,self.root,execute_live=True,approval_path=approval,schema_receipt_path=schema)

    def test_cached_page_checkpoint_and_dispatch_tampering_block(self):
        cases=('page','checkpoint','params','config','mode','orphan')
        for case in cases:
            with self.subTest(case=case):
                private=self.root/case
                collect(self.config,private,transport=lambda *_:{'items':[self.item],'max_id':None,'more_available':False})
                run=private/'fixture-run'
                if case=='orphan':
                    next((run/'dispatch').glob('*.json')).unlink()
                else:
                    folder='pages' if case=='page' else 'checkpoints' if case=='checkpoint' else 'dispatch'
                    path=next((run/folder).glob('*.json'));payload=json.loads(path.read_text())
                    if case=='page':payload['items'][0]['play_count']=9999
                    elif case=='checkpoint':payload['next_cursor']='CORRUPTED'
                    elif case=='params':payload['params']['user_id']='999'
                    elif case=='config':payload['config_sha256']='x'*64
                    elif case=='mode':payload['execution_mode']='LIVE_PILOT'
                    path.write_text(json.dumps(payload))
                with self.assertRaisesRegex(ValueError,'CACHE'):
                    collect(self.config,private,transport=lambda *_:self.fail('tampered cache must not dispatch'))


if __name__=='__main__':unittest.main()
