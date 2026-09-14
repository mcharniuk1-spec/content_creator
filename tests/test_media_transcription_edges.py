import hashlib
import json
import sys

from m2_orchestrator import media_transcription as m


def fixture_record(root):
    p = root/'source.mp4'
    p.write_bytes(b'fixture')
    return {'observation_state':'OBSERVED', 'source_kind':'approved_research_copy',
            'rights':{'analysis_allowed':True,'receipt_id':'fixture'},
            'source_pointer':p.name,'sha256':hashlib.sha256(b'fixture').hexdigest(),
            'duration_ms':1000, 'has_audio':False}


def test_no_audio_does_not_load_model_or_claim_verified_silence(tmp_path, monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('No model or child needed for absent audio')
    monkeypatch.setattr(m,'validate_model_bundle',forbidden)
    monkeypatch.setattr(m,'bounded_process',forbidden)
    r=m.transcribe(fixture_record(tmp_path),tmp_path,tmp_path/'out',sys.executable,tmp_path/'missing')
    assert r['observation_state']=='NOT_APPLICABLE'
    assert r['failure_code']=='NO_AUDIO_STREAM'
    assert r['asr_execution'] is False and r['no_speech_confirmed'] is False


def test_interrupted_worker_does_not_claim_inference_never_started(tmp_path, monkeypatch):
    record=fixture_record(tmp_path);record['has_audio']=True
    model=tmp_path/'model';model.mkdir()
    (model/'weights').write_bytes(b'fixture')
    (model/'model-hash-manifest.json').write_text(json.dumps({'files':[{'path':'weights','sha256':record['sha256']}]}))
    def interrupted(*a, **k):
        raise m.ProcessBudgetError('PROCESS_RSS_LIMIT')
    monkeypatch.setattr(m,'bounded_process',interrupted)
    r=m.transcribe(record,tmp_path,tmp_path/'out',sys.executable,model)
    assert r['observation_state']=='ASR_FAILED'
    assert r['asr_execution'] is None
    assert r['execution_state']=='INTERRUPTED_PHASE_UNCONFIRMED'
    assert r['source_media_hash']==record['sha256']
