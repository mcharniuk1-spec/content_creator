"""Focused tests for the portable, repaired transcript benchmark."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from m2_signal.transcript_benchmark import (
    bootstrap_corr,
    bootstrap_group_effect,
    bh_qvalues,
    cv_compare,
    current_metric_vector,
    group_account_folds,
    load_rows,
    write_analytics_db,
)


def _metric_vector(saves):
    return {
        "views": 1000,
        "likes_per_1k_views": 10,
        "comments_per_1k_views": 2,
        "reshares_per_1k_views": 1,
        "saves_per_1k_views": saves,
    }


def _transcript(transcript_id, digest, saves, words=0):
    return {
        "transcript_id": transcript_id,
        "source_record_sha256": digest,
        "word_count_lexical_v1": words,
        "segment_count": 1 if words else 0,
        "segment_features": [{"lexical_word_count": words}] if words else [],
        "metrics_snapshot": {"metric_vector": _metric_vector(saves), "metric_eligibility_state": "ELIGIBLE"},
    }


def test_transcript_id_join_preserves_hash_collision_and_null_saves(tmp_path: Path):
    db = tmp_path / "signal.sqlite"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE reel_analysis (release_id TEXT, reel_id TEXT, account_username TEXT, payload_json TEXT)")
    for reel_id, account, saves in [("instagram:one", "acct-one", None), ("instagram:two", "acct-two", 3)]:
        payload = {
            "snapshot_date": "2026-09-01",
            "published_epoch_seconds": None,
            "duration_seconds": 10,
            "author_median_views": 1000,
            "author_baseline_n": 5,
            "eligibility_state": "PASS",
            "numeric_valid": True,
            "account_username": account,
            "views": 1000,
            "likes_per_1k_views": 10,
            "comments_per_1k_views": 2,
            "reshares_per_1k_views": 1,
            "saves_per_1k_views": saves,
        }
        conn.execute("INSERT INTO reel_analysis VALUES (?, ?, ?, ?)", ("release-test", reel_id, account, json.dumps(payload)))
    conn.commit()
    conn.close()

    digest = "sha256:collision"
    transcripts = tmp_path / "transcripts.jsonl"
    transcripts.write_text("\n".join(json.dumps(x) for x in [
        _transcript("TR-005", digest, None),
        _transcript("TR-008", digest, 3),
    ]) + "\n")
    source_map = tmp_path / "source-map.json"
    source_map.write_text(json.dumps({"sources": [
        {"transcript_id": "TR-005", "reel_id": "instagram:one", "record_sha256": digest},
        {"transcript_id": "TR-008", "reel_id": "instagram:two", "record_sha256": digest},
    ]}))
    summary = tmp_path / "summary.json"
    summary.write_text("{}")

    rows, _ = load_rows(db, transcripts, source_map, "release-test", expected_transcript_count=2)
    assert [(r["transcript_id"], r["reel_id"]) for r in rows] == [
        ("TR-005", "instagram:one"),
        ("TR-008", "instagram:two"),
    ]
    assert rows[0]["log_saves_per_1k_views"] is None
    assert rows[0]["log_total_actions"] is None
    assert rows[1]["log_total_actions"] is not None


def test_bh_qvalues_standard_order_and_missing_values():
    p = [0.001, None, 0.01, 0.02, 0.2]
    q = bh_qvalues(p)
    assert q[1] is None
    assert q[0] == 0.004
    assert q[2] == 0.02
    assert q[3] == 0.02666666666666667
    assert q[4] == 0.2
    assert all(qv >= pv for pv, qv in zip(p, q) if pv is not None)


def test_clustered_associations_suppress_permutation_pq():
    rows = [{"account": f"a{i}", "x": float(i), "y": float(i + 1), "kind": "a" if i < 5 else "b"} for i in range(10)]
    numeric = bootstrap_corr(rows, "x", "y", reps=40)
    assert numeric["p_permutation_exploratory"] is None
    assert numeric["p_value_state"] == "UNAVAILABLE_ROW_PERMUTATION_SUPPRESSED"
    categorical = bootstrap_group_effect(rows, "kind", "y", min_n=5, reps=40)
    assert categorical["state"] == "ESTIMATED"
    assert all(effect["p_permutation_exploratory"] is None and effect["q_bh_within_group_family"] is None for effect in categorical["effects"])


def test_current_signal_metrics_reject_non_rounding_transcript_drift():
    transcript = _transcript("TR-X", "sha256:x", 3)
    payload = {"views": 1000, "likes_per_1k_views": 10.2, "comments_per_1k_views": 2, "reshares_per_1k_views": 1, "saves_per_1k_views": 3}
    try:
        current_metric_vector(transcript, payload)
    except ValueError as exc:
        assert str(exc) == "transcript_metric_mismatch:TR-X:likes_per_1k_views"
    else:
        raise AssertionError("non-rounding metric drift must fail closed")


def test_empty_release_id_is_rejected_before_database_io(tmp_path: Path):
    with pytest.raises(ValueError, match="release_id_required"):
        load_rows(tmp_path / "missing.sqlite", tmp_path / "missing.jsonl", tmp_path / "missing-map.json", "")


def test_analytics_db_temp_is_removed_after_insert_failure(tmp_path: Path):
    input_paths = {}
    for name in ("db", "transcripts", "source_map", "summary"):
        path = tmp_path / f"{name}.input"
        path.write_text(name)
        input_paths[name] = path
    result = {
        "run_id": "r", "release_id": "release-test", "analysis_date": "",
        "policy": {"primary_outcome": "test"},
        "numeric_associations": [], "categorical_associations": [], "model_comparisons": [],
    }
    duplicate_rows = [
        {"transcript_id": "duplicate", "reel_id": "reel-1", "account": "acct"},
        {"transcript_id": "duplicate", "reel_id": "reel-2", "account": "acct"},
    ]
    with pytest.raises(sqlite3.IntegrityError):
        write_analytics_db(tmp_path, result, duplicate_rows, input_paths)
    assert list(tmp_path.glob(".analytics-*.sqlite.tmp")) == []


def test_grouped_folds_are_account_disjoint_and_category_vocab_is_training_only():
    folds = group_account_folds([f"a{i}" for i in range(10)], 5)
    assert sorted(x for fold in folds for x in fold) == [f"a{i}" for i in range(10)]
    assert all(set(folds[i]).isdisjoint(set(folds[j])) for i in range(5) for j in range(i + 1, 5))

    rows = []
    for i in range(50):
        kind = "a" if i % 2 == 0 else "b"
        x = 1.0 + i / 100
        rows.append({
            "account": f"a{i % 10}",
            "kind": kind,
            "log_views": x,
            "log_age_days": 0.5 + (i % 7) / 10,
            "log_duration_seconds": 1.0 + (i % 5) / 10,
            "log_account_median_views": 2.0 + (i % 3) / 10,
            "log_account_baseline_n": 1.0 + (i % 4) / 10,
            "log_total_actions": 0.2 * x + (0.1 if kind == "b" else 0),
        })
    result = cv_compare(rows, "cat:kind")
    assert result["state"] == "ESTIMATED"
    assert result["vocabulary_policy"].startswith("categorical levels selected from each training fold")
    assert len(result["grouped_5fold"]) == 5
