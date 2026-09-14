import tempfile
import time
import unittest
from unittest.mock import patch
from m2_orchestrator.policy import STAGES
from m2_orchestrator.state import Controller, StateError

class ExpiredFailureTests(unittest.TestCase):
    def test_expired_fail_cannot_change_stage(self):
        config={'schema':'m2.run-config.v1','platforms':['instagram_reels'],'mode':'replay','hikerapi_execution':False,'provider_execution':False,'source_manifest':[{'source_id':'fixture','sha256':'1'*64}], 'actors':{'maker':list({s.role for s in STAGES if not s.reviewer}),'reviewer':list({s.role for s in STAGES if s.reviewer}),'owner':['owner']}}
        with tempfile.TemporaryDirectory() as directory:
            c=Controller(directory);c.init('fixture',config);begun=c.begin('admit','maker',lease_seconds=30)
            with patch('m2_orchestrator.state.time.time',return_value=time.time()+60):
                with self.assertRaisesRegex(StateError,'STALE_WORKER_TOKEN_OR_LEASE'):
                    c.fail('admit',begun['token'],'FIXTURE_FAILURE')
            self.assertEqual(next(r for r in c.status()['stages'] if r['id']=='admit')['state'],'RUNNING')
            c.fail('admit',begun['token'],'FIXTURE_FAILURE')
            self.assertEqual(next(r for r in c.status()['stages'] if r['id']=='admit')['state'],'FAIL')
if __name__=='__main__':unittest.main()
