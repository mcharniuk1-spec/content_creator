import json
from pathlib import Path
from unittest.mock import patch

import pytest

from m2_orchestrator.server_media import execute_media_job
from m2_studio.media import digest


@pytest.fixture(autouse=True)
def frozen_fixture_model():
    with patch('m2_orchestrator.server_media.validate_model_bundle',
               return_value={'bundle_sha256': 'b' * 64}):
        yield


def inputs(tmp_path):
    python = tmp_path / 'python'; python.write_text('fixture executable bytes')
    resolver = tmp_path / 'yt-dlp'; resolver.write_text('fixture resolver bytes')
    cfg = tmp_path / 'job.json'
    cfg.write_text(json.dumps({'enabled': True, 'network': True, 'hikerapi_enabled': False,
        'private_source_root': str(tmp_path),
        'model_dir': '/model', 'python_executable': str(python),
        'resolver_executable': str(resolver), 'resolver_sha256': digest(resolver),
        'rights_receipt': 'fixture-authority'}))
    reels = tmp_path / 'reels.jsonl'
    reels.write_text(json.dumps({'reel_id': 'instagram:A1234567890', 'code': 'A1234567890',
                                'quarantine_reasons': ['numeric_conflict']}) + '\n')
    return cfg, reels, tmp_path / 'job'


def test_replay_hook_retains_numeric_quarantine_and_resume(tmp_path):
    cfg, reels, root = inputs(tmp_path)
    with patch('m2_orchestrator.server_media.CorpusMediaDispatcher') as worker:
        worker.return_value.run.return_value = {'population': 1}
        execute_media_job(cfg, reels, root, max_items=1)
        first = (root / 'manifest.private.json').read_bytes()
        execute_media_job(cfg, reels, root)
        assert (root / 'manifest.private.json').read_bytes() == first
        manifest = worker.call_args.args[0]
        assert manifest['entries'][0]['research_quarantine_reasons'] == ['numeric_conflict']
        assert manifest['entries'][0]['quarantine_reasons'] == []
        assert manifest['entries'][0]['sources'][-1]['route'] == 'public_reel'
        assert worker.return_value.run.call_args.kwargs == {'network': True, 'max_items': None}


def test_changed_replay_export_requires_new_job(tmp_path):
    cfg, reels, root = inputs(tmp_path)
    with patch('m2_orchestrator.server_media.CorpusMediaDispatcher') as worker:
        execute_media_job(cfg, reels, root)
        reels.write_text(reels.read_text() + json.dumps({'reel_id': 'instagram:B1234567890', 'code': 'B1234567890'}) + '\n')
        with pytest.raises(ValueError, match='CHANGED_INPUT'):
            execute_media_job(cfg, reels, root)
        assert worker.call_count == 1


@pytest.mark.parametrize('field,value', [('network', False), ('enabled', 'true'), ('hikerapi_enabled', True)])
def test_hook_requires_exact_flags(tmp_path, field, value):
    cfg, reels, root = inputs(tmp_path)
    data = json.loads(cfg.read_text()); data[field] = value; cfg.write_text(json.dumps(data))
    with patch('m2_orchestrator.server_media.CorpusMediaDispatcher') as worker:
        with pytest.raises(ValueError, match='EXPLICIT_AUTHORITY'):
            execute_media_job(cfg, reels, root)
        worker.assert_not_called()
    assert not root.exists()


def test_corrupted_frozen_manifest_is_rejected(tmp_path):
    cfg, reels, root = inputs(tmp_path)
    with patch('m2_orchestrator.server_media.CorpusMediaDispatcher') as worker:
        execute_media_job(cfg, reels, root)
        (root / 'manifest.private.json').write_text('{}')
        with pytest.raises(ValueError, match='MANIFEST_CHANGED'):
            execute_media_job(cfg, reels, root)
        assert worker.call_count == 1


def test_job_output_symlink_rejected(tmp_path):
    cfg, reels, root = inputs(tmp_path)
    destination = tmp_path / 'elsewhere'; destination.mkdir(); root.symlink_to(destination)
    with pytest.raises(ValueError, match='SYMLINK'):
        execute_media_job(cfg, reels, root)
    assert not list(destination.iterdir())


def test_source_root_escape_never_scans_or_runs(tmp_path):
    cfg, reels, root = inputs(tmp_path)
    data = json.loads(cfg.read_text()); data['cache_roots'] = [str(tmp_path.parent)]
    cfg.write_text(json.dumps(data))
    with patch('m2_orchestrator.server_media.build_manifest') as builder:
        with pytest.raises(ValueError, match='OUTSIDE_APPROVED_AREA'):
            execute_media_job(cfg, reels, root)
        builder.assert_not_called()


def test_python_change_rejects_resume_before_worker(tmp_path):
    cfg, reels, root = inputs(tmp_path)
    with patch('m2_orchestrator.server_media.CorpusMediaDispatcher') as worker:
        execute_media_job(cfg, reels, root)
        (tmp_path / 'python').write_text('changed executable')
        with pytest.raises(ValueError, match='CHANGED_INPUT'):
            execute_media_job(cfg, reels, root)
        assert worker.call_count == 1


def test_model_change_rejects_resume_before_worker(tmp_path):
    cfg, reels, root = inputs(tmp_path)
    with patch('m2_orchestrator.server_media.CorpusMediaDispatcher') as worker:
        execute_media_job(cfg, reels, root)
        with patch('m2_orchestrator.server_media.validate_model_bundle', return_value={'bundle_sha256': 'c' * 64}):
            with pytest.raises(ValueError, match='CHANGED_INPUT'):
                execute_media_job(cfg, reels, root)
        assert worker.call_count == 1


@pytest.mark.parametrize('reasons', ['numeric_conflict', {'numeric_conflict': True}, None,
                                   False, 3, [''], ['   '], [1], [['nested']]])
def test_malformed_quarantine_never_freezes_or_dispatches(tmp_path, reasons):
    cfg, reels, root = inputs(tmp_path)
    row = json.loads(reels.read_text()); row['quarantine_reasons'] = reasons
    reels.write_text(json.dumps(row) + '\n')
    with patch('m2_orchestrator.server_media.build_manifest') as builder, \
            patch('m2_orchestrator.server_media.CorpusMediaDispatcher') as worker:
        with pytest.raises(ValueError, match='QUARANTINE_REASONS_INVALID'):
            execute_media_job(cfg, reels, root)
        builder.assert_not_called()
        worker.assert_not_called()
    assert not (root / 'manifest.private.json').exists()
    assert not (root / 'binding.json').exists()
