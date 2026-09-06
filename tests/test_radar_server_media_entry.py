"""Regression checks for the portable Radar timer adapter (no external calls)."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest


def entry():
    path = Path(__file__).parents[1] / 'integrations/radar/server_entry.py'
    spec = importlib.util.spec_from_file_location('radar_server_entry', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config(tmp_path, **extra):
    value = {'source_dir': str(tmp_path / 'export'), 'run_dir': str(tmp_path / 'run'),
             'private_run_root':str(tmp_path),'private_source_roots':[str(tmp_path)],
             'run_id': 'fixture-run', **extra}
    path = tmp_path / 'server.json'; path.write_text(json.dumps(value))
    return path


def test_default_server_replay_never_imports_media_work(tmp_path, capsys):
    module = entry()
    with patch.object(module, 'execute_replay', return_value={'run_id': 'fixture-run'}), \
            patch('m2_orchestrator.server_media.execute_media_job') as media:
        assert module.main(['--config', str(config(tmp_path))]) == 0
        media.assert_not_called()
    assert json.loads(capsys.readouterr().out)['media_job_requested'] is False


def test_opt_in_media_follows_successful_replay(tmp_path, capsys):
    module = entry(); sequence = []
    def replay(*args, **kwargs):
        sequence.append('replay'); return {'run_id': 'fixture-run'}
    def media(*args, **kwargs):
        sequence.append('media'); return {'population': 1, 'fixture': True}
    with patch.object(module, 'execute_replay', side_effect=replay), \
            patch.object(module, 'completed_replay', return_value={'reels_sha256':'fixture'}), \
            patch.object(module, 'file_digest', return_value='fixture'), \
            patch('m2_orchestrator.server_media.execute_media_job', side_effect=media) as hook:
        private=str(tmp_path/'private-media.json')
        assert module.main(['--config', str(config(tmp_path, media_job_config=private))]) == 0
        hook.assert_called_once_with(private, tmp_path / 'run/signal/reels.jsonl', tmp_path / 'run/media-job')
    assert sequence == ['replay', 'media']
    result = json.loads(capsys.readouterr().out)
    assert result['llm_calls'] == 0 and 'model_calls' not in result
    assert result['media_job_result']['population'] == 1


def test_replay_failure_cannot_start_media(tmp_path):
    module = entry()
    with patch.object(module, 'execute_replay', side_effect=ValueError('fixture failure')), \
            patch('m2_orchestrator.server_media.execute_media_job') as media:
        with pytest.raises(ValueError, match='fixture failure'):
            module.main(['--config', str(config(tmp_path, media_job_config=str(tmp_path/'private-media.json')))])
        media.assert_not_called()


@pytest.mark.parametrize('value', [True, None, 1, [], '', '  '])
def test_media_config_must_be_an_explicit_path(tmp_path, value):
    with pytest.raises(ValueError, match='explicit private config path'):
        entry().resolve_config(json.loads(config(tmp_path, media_job_config=value).read_text()))


def test_partial_replay_requires_separate_media_execution(tmp_path):
    with pytest.raises(ValueError, match='requires completed replay'):
        entry().resolve_config(json.loads(config(tmp_path, media_job_config='private.json', until='inventory').read_text()))


@pytest.mark.parametrize('kind',['run','ancestor','lock','hardlinked_lock','outside_source','outside_metric'])
def test_paths_fail_before_replay(tmp_path,kind):
    module=entry(); conf=config(tmp_path); data=json.loads(conf.read_text())
    target=tmp_path/'target';target.mkdir()
    if kind=='run': (tmp_path/'run').symlink_to(target)
    elif kind=='ancestor':
        (tmp_path/'linked').symlink_to(target);data['run_dir']=str(tmp_path/'linked/run')
    elif kind in {'lock','hardlinked_lock'}:
        (tmp_path/'run').mkdir();original=target/'file';original.write_text('preserve')
        lock=tmp_path/'run/server.lock'
        if kind=='lock':lock.symlink_to(original)
        else:lock.hardlink_to(original)
    elif kind=='outside_source':data['source_dir']=str(tmp_path.parent/'outside')
    else:data['metric_config']=str(tmp_path.parent/'outside.json')
    conf.write_text(json.dumps(data))
    with patch.object(module,'execute_replay') as replay:
        with pytest.raises(ValueError,match='SERVER_'): module.main(['--config',str(conf)])
        replay.assert_not_called()


def real_replay(tmp_path):
    module=entry(); source=tmp_path/'source';source.mkdir()
    (source/'reels.csv').write_text('code,user,play,like,comment,reshare,save,duration_s,ts\nCODE1234567,creator,1000,30,2,3,1,20,1788200000\n')
    (source/'accounts.csv').write_text('username,followers,media_count\ncreator,100,20\n')
    (source/'snapshot.json').write_text(json.dumps({'taken':'2026-09-01','accounts':1}))
    root=tmp_path/'run'
    status=module.execute_replay(source,root,'proof-fixture','server')
    return module,root,status


def test_actual_replay_completion_and_unchanged_proof(tmp_path):
    module,root,status=real_replay(tmp_path)
    proof=module.completed_replay(root,status,'proof-fixture')
    assert proof['trace']['state']=='PASS'
    assert proof['reels_sha256']==module.file_digest(root/'signal/reels.jsonl')
    assert module.completed_replay(root,status,'proof-fixture')==proof


@pytest.mark.parametrize('mutation',['missing','partial','config_mismatch','tampered_export'])
def test_media_completion_gate_rejects_invalid_evidence(tmp_path,mutation):
    module,root,status=real_replay(tmp_path)
    if mutation=='missing':status={'run_id':'proof-fixture'}
    elif mutation=='partial':status['stages'][0]['state']='PENDING'
    elif mutation=='config_mismatch':status['config_hash']='0'*64
    else:(root/'signal/reels.jsonl').write_text('{}\n')
    with pytest.raises(ValueError):module.completed_replay(root,status,'proof-fixture')
    assert not (root/'media-replay-completion.json').exists()
