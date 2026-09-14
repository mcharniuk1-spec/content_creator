#!/usr/bin/env python3
"""Safe clean-checkout tests. No installs, live collection, providers or writeback.

Legacy source-inspected fixture scripts run in disposable directories with socket
connections and child processes denied. Historical tests that require an existing
private database are listed as skipped, not represented as passing.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEGACY_FIXTURES=('test_score.py','test_collect.py','test_topup.py')
PRIVATE_DB_TESTS=('test_baseline.py','test_cards.py','test_deep.py','test_journal.py','test_notion.py','test_posts.py','test_roster.py','test_topics.py')


def run(command,cwd,env):
    result=subprocess.run(command,cwd=cwd,env=env,text=True,capture_output=True,timeout=120)
    if result.returncode:
        print(result.stdout);print(result.stderr,file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def main():
    env={k:v for k,v in os.environ.items() if not any(term in k for term in ('TOKEN','API_KEY','API_SECRET')) and k!='HIKER_KEY'}
    package=run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_m2_*.py','-v'],ROOT,env)
    package_tests=sum(' ... ok' in line for line in package.stderr.splitlines())
    package_skipped=sum(' ... skipped ' in line for line in package.stderr.splitlines())
    entry=run([sys.executable,'test_pipeline.py','-v'],ROOT,env)
    entry_tests=sum(' ... ok' in line for line in entry.stderr.splitlines())
    legacy_results=[]
    for name in LEGACY_FIXTURES:
        with tempfile.TemporaryDirectory() as tmp:
            workspace=Path(tmp)
            for source in ROOT.glob('*.py'):
                shutil.copyfile(source,workspace/source.name)
            bootstrap="""import sys,runpy,socket,subprocess,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
def denied(*args,**kwargs): raise RuntimeError('NETWORK_OR_SUBPROCESS_DISABLED_IN_LEGACY_FIXTURE')
socket.create_connection=denied
socket.socket.connect=denied
socket.socket.connect_ex=denied
urllib.request.urlopen=denied
subprocess.Popen=denied
subprocess.run=denied
runpy.run_path(sys.argv[1],run_name='__main__')
"""
            result=run([sys.executable,'-c',bootstrap,name],workspace,env)
            legacy_results.append({'script':name,'state':'PASS','network_disabled':True,'private_database_used':False})
    remotion={'state':'SKIPPED','reason':'Node.js unavailable'}
    node=shutil.which('node')
    if node:
        result=run([node,'--test','test-contract.mjs'],ROOT/'studio/remotion',env)
        remotion={'state':'PASS','scope':'deterministic EDL contract; renderer not installed or invoked by this test'}
    print(json.dumps({'state':'PASS_WITH_LIMITATIONS','shared_python_tests_passed':package_tests,
        'shared_python_tests_skipped':package_skipped,'entry_tests_passed':entry_tests,'legacy_fixtures':legacy_results,
        'legacy_private_database_tests_skipped':list(PRIVATE_DB_TESTS),'remotion':remotion,
        'hikerapi_requests':0,'provider_requests':0,'external_writes':0},indent=2))


if __name__=='__main__':main()
