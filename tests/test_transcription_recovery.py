from __future__ import annotations

import pytest

from m2_orchestrator.process_budget import ProcessBudgetError
from m2_orchestrator.transcription_recovery import (
    TranscriptionRecoveryError,
    build_chunk_request,
    completed_chunk_ids,
    merge_chunk_results,
    plan_windows,
    recover_chunks,
)


SOURCE = "a" * 64
MODEL = "b" * 64
CONFIG = "c" * 64


def result(chunk_id, *, start_ms=0, end_ms=1000, text="hello", audio_hash="d" * 64, state="OBSERVED", failure_code=None):
    return {
        "chunk_id": chunk_id,
        "source_media_hash": SOURCE,
        "model_bundle_sha256": MODEL,
        "config_sha256": CONFIG,
        "source_audio_sha256": audio_hash,
        "observation_state": state,
        "failure_code": failure_code,
        "segments": [{"start_ms": start_ms, "end_ms": end_ms, "text": text, "words": [{"start_ms": start_ms, "end_ms": end_ms, "word": text}]}] if state == "OBSERVED" else [],
    }


def test_windows_cover_duration_exactly_with_bounded_context():
    plans = plan_windows(65_000)
    assert [(p["core_interval_ms"]) for p in plans] == [[0, 30_000], [30_000, 60_000], [60_000, 65_000]]
    assert plans[0]["window_interval_ms"] == [0, 31_000]
    assert plans[1]["window_interval_ms"] == [29_000, 61_000]
    assert plans[-1]["window_interval_ms"] == [59_000, 65_000]
    assert all(p["core_duration_ms"] <= 30_000 for p in plans)
    assert all(p["left_padding_ms"] <= 1_000 and p["right_padding_ms"] <= 1_000 for p in plans)


def test_midpoint_ownership_is_half_open_at_boundary():
    plans = plan_windows(60_000)
    requests = [build_chunk_request(p, source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG) for p in plans]
    first = result("C0001", start_ms=29_999, end_ms=30_001)
    second = result("C0002", start_ms=999, end_ms=1_001)
    merged = merge_chunk_results(plans, [first, second], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG)
    assert len(merged["words"]) == 1
    assert len(merged["padding_words"]) == 1
    assert merged["words"][0]["chunk_id"] == "C0002"
    assert merged["words"][0]["global_start_ms"] == 29_999
    assert merged["words"][0]["global_end_ms"] == 30_001
    assert requests[1]["global_offset_ms"] == 29_000


def test_duplicate_context_is_counted_once_and_boundary_review_remains_explicit():
    plans = plan_windows(60_000)
    merged = merge_chunk_results(
        plans,
        [result("C0001", start_ms=29_900, end_ms=30_100), result("C0002", start_ms=900, end_ms=1_100)],
        source_media_hash=SOURCE,
        model_bundle_sha256=MODEL,
        config_sha256=CONFIG,
    )
    assert merged["word_count"] == 1
    assert merged["raw_word_count"] == 2
    assert merged["full_transcript_observed"] is False
    assert "WINDOW_BOUNDARY_TIMING_REVIEW_REQUIRED" in merged["boundary_issues"]
    assert merged["observation_state"] == "SUSPICIOUS_TIMINGS"


def test_padded_word_global_offset_is_preserved_separately():
    plans = plan_windows(60_000)
    merged = merge_chunk_results(
        plans,
        [result("C0001", start_ms=29_000, end_ms=29_500), result("C0002", start_ms=0, end_ms=500, text="context")],
        source_media_hash=SOURCE,
        model_bundle_sha256=MODEL,
        config_sha256=CONFIG,
    )
    context = next(word for word in merged["padding_words"] if word["text"] == "context")
    assert context["global_start_ms"] == 29_000
    assert context["global_end_ms"] == 29_500
    assert context["ownership"] == "padding"


def test_segment_global_offset_is_applied_once_for_nonzero_window():
    plans = plan_windows(60_000)
    merged = merge_chunk_results(
        plans,
        [result("C0002", start_ms=0, end_ms=500, text="offset")],
        source_media_hash=SOURCE,
        model_bundle_sha256=MODEL,
        config_sha256=CONFIG,
    )
    row = next(item for item in merged["raw_segment_text"] if item["chunk_id"] == "C0002")
    assert (row["global_start_ms"], row["global_end_ms"]) == (29_000, 29_500)


def test_unknown_original_audio_requires_bound_audio_source_proof():
    plans = plan_windows(30_000)
    with pytest.raises(TranscriptionRecoveryError, match="ORIGINAL_AUDIO_UNKNOWN_REQUIRES_AUDIO_SOURCE_PROOF"):
        recover_chunks(plans, source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG, original_audio_unknown=True)
    proof = {"proof_id": "audio-receipt", "source_media_hash": SOURCE, "has_audio": True}
    merged = recover_chunks(
        plans,
        source_media_hash=SOURCE,
        model_bundle_sha256=MODEL,
        config_sha256=CONFIG,
        original_audio_unknown=True,
        audio_source_proof=proof,
    )
    assert merged["original_audio_unknown"] is True
    assert merged["original_audio_status"] == "UNKNOWN"
    assert merged["speech_state"] == "UNKNOWN"
    assert merged["no_speech_confirmed"] is False


def test_boundary_text_disagreement_is_review_required():
    plans = plan_windows(60_000)
    merged = merge_chunk_results(
        plans,
        [result("C0001", start_ms=29_900, end_ms=30_100, text="their"), result("C0002", start_ms=900, end_ms=1_100, text="there")],
        source_media_hash=SOURCE,
        model_bundle_sha256=MODEL,
        config_sha256=CONFIG,
    )
    assert "CHUNK_BOUNDARY_SEMANTIC_PHONETIC_REVIEW_REQUIRED" in merged["boundary_issues"]


def test_hash_mismatch_is_rejected_before_merge():
    plans = plan_windows(30_000)
    with pytest.raises(TranscriptionRecoveryError, match="SOURCE_MEDIA_HASH_MISMATCH"):
        merge_chunk_results(plans, [result("C0001")], source_media_hash="e" * 64, model_bundle_sha256=MODEL, config_sha256=CONFIG)
    with pytest.raises(TranscriptionRecoveryError, match="CONFIG_HASH_MISMATCH"):
        completed_chunk_ids(plans, [result("C0001")], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256="e" * 64)


def test_timeout_becomes_explicit_partial_chunk_without_retry():
    plans = plan_windows(30_000)
    calls = []

    def timeout_runner(request):
        calls.append(request["chunk_id"])
        raise ProcessBudgetError("PROCESS_RSS_LIMIT")

    merged = recover_chunks(plans, source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG, chunk_runner=timeout_runner)
    assert calls == ["C0001"]
    assert merged["observation_state"] == "PARTIAL"
    assert merged["incomplete_chunks"] == ["C0001"]
    assert merged["chunks"][0]["failure_code"] == "PROCESS_RSS_LIMIT"


def test_completed_chunk_resume_requires_persisted_artifact_root():
    plans = plan_windows(30_000)
    prior = result("C0001")
    prior.update({key: plans[0][key] for key in ("global_offset_ms", "core_interval_ms", "window_interval_ms")})
    calls = []

    def forbidden_runner(request):
        calls.append(request)
        raise AssertionError("completed chunk must be resumed")

    with pytest.raises(TranscriptionRecoveryError, match="CHUNK_ARTIFACT_ROOT_REQUIRED"):
        recover_chunks(plans, source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG, chunk_runner=forbidden_runner, completed_results=[prior])
    assert calls == []


def test_cached_chunk_must_match_current_plan_intervals_and_offset():
    plans = plan_windows(60_000)
    cached = result("C0002")
    cached.update({"global_offset_ms": 0, "core_interval_ms": [0, 30_000], "window_interval_ms": [0, 30_000]})
    with pytest.raises(TranscriptionRecoveryError, match="CHUNK_PLAN_BINDING_MISMATCH"):
        completed_chunk_ids(plans, [cached], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG)


def test_duplicate_cached_chunk_ids_are_rejected_before_resume_validation():
    plans = plan_windows(30_000)
    cached = result("C0001")
    cached.update({key: plans[0][key] for key in ("global_offset_ms", "core_interval_ms", "window_interval_ms")})
    with pytest.raises(TranscriptionRecoveryError, match="CHUNK_RESULT_ID_DUPLICATE"):
        completed_chunk_ids(plans, [cached, dict(cached)], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG)


def test_missing_runner_is_explicit_partial_and_rights_are_not_implied():
    plans = plan_windows(30_000)
    merged = recover_chunks(plans, source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG)
    assert merged["observation_state"] == "PARTIAL"
    assert merged["rights_state"] == "REQUIRED"
    assert merged["analysis_ready"] is False
    assert merged["no_speech_confirmed"] is False


def test_pilot_metrics_are_preserved_and_quality_promotion_stays_blocked():
    plans = plan_windows(29_400)
    pilot = result("C0001", end_ms=29_400)
    pilot.update({"lexical_word_count": 33, "raw_word_count": 33, "aligned_word_count": 22, "unaligned_word_count": 11,
                  "word_timing": "PARTIAL", "raw": {"language": "hi", "language_probability": 0.9753659963607788, "segments": []}})
    merged = merge_chunk_results(
        plans, [pilot], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG,
        rights={"analysis_allowed": True, "receipt_id": "rights"},
    )
    assert merged["machine_observed"] is True
    assert merged["analysis_approved"] is False
    assert merged["analysis_ready"] is False
    assert merged["full_transcript_observed"] is False
    assert merged["chunk_metrics"][0]["lexical_word_count"] == 33
    assert merged["chunk_metrics"][0]["aligned_word_count"] == 22
    assert merged["chunk_metrics"][0]["unaligned_word_count"] == 11
    assert merged["chunk_metrics"][0]["language"] == "hi"
    assert merged["aggregate_metrics"]["language_probability"] == 0.9753659963607788
    assert merged["aggregate_metrics"]["word_timing"] == "PARTIAL"


def test_quality_promotion_requires_explicit_review_receipt():
    plans = plan_windows(2_000)
    merged = merge_chunk_results(
        plans, [result("C0001", end_ms=2_000)], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG,
        rights={"analysis_allowed": True, "receipt_id": "rights"},
        review_receipt={"review_id": "review", "verdict": "ACCEPTED"},
    )
    assert merged["analysis_approved"] is False
    assert merged["analysis_ready"] is False
    assert merged["full_transcript_observed"] is False


def test_quality_review_binds_exact_evidence_scope_and_separate_reviewer():
    plans = plan_windows(2_000)
    r = result('C0001', end_ms=2_000)
    r.update(lexical_word_count=1, aligned_word_count=1, unaligned_word_count=0, word_timing='OBSERVED')
    kwargs = dict(source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG, rights={'analysis_allowed': True, 'receipt_id': 'rights'})
    candidate = merge_chunk_results(plans, [r], **kwargs)
    receipt = dict(schema='m2.transcription-quality-review.v1', review_id='independent-review', verdict='ACCEPTED',
                   maker_actor='maker', reviewer_actor='reviewer', scope=['transcript_quality','word_timing'],
                   evidence_sha256=candidate['review_evidence_sha256'], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG)
    accepted = merge_chunk_results(plans, [r], review_receipt=receipt, **kwargs)
    assert accepted['analysis_ready'] is True
    for field, value in [('reviewer_actor','maker'), ('evidence_sha256','e'*64), ('source_media_hash','f'*64), ('scope',['word_timing'])]:
        rejected = merge_chunk_results(plans, [r], review_receipt=receipt | {field:value}, **kwargs)
        assert rejected['analysis_approved'] is False
    changed = dict(r, unaligned_word_count=1, lexical_word_count=2, word_timing='PARTIAL')
    assert merge_chunk_results(plans,[changed],review_receipt=receipt,**kwargs)['analysis_ready'] is False


@pytest.mark.parametrize('probability', [float('nan'), float('inf'), -0.1, 1.1, True])
def test_invalid_language_confidence_cannot_enter_aggregate(probability):
    r = result('C0001', end_ms=2_000);r['language_probability']=probability
    with pytest.raises(TranscriptionRecoveryError, match='CHUNK_METRICS_INVALID'):
        merge_chunk_results(plan_windows(2_000), [r], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256=CONFIG)
