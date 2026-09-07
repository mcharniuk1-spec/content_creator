from __future__ import annotations

import pytest

from m2_orchestrator.transcription_recovery import build_recovery_config, object_hash, plan_windows
from scripts import run_m2_transcription_recovery as cli


SOURCE = "a" * 64
MODEL = "b" * 64


def _prepared(*, config=None, config_hash=None):
    if config is None:
        config = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL)
    return {
        "record": {"sha256": SOURCE, "source_pointer": "media.mp4"},
        "model": {"bundle_sha256": MODEL},
        "config": config,
        "config_hash": object_hash(config) if config_hash is None else config_hash,
        "plans": plan_windows(2_000),
        "input_paths": {},
        "runtime": {},
    }


def test_missing_config_fails_closed_before_creating_manifest(tmp_path):
    prepared = _prepared()
    del prepared["config"]
    output = tmp_path / "missing-config-run"
    with pytest.raises(ValueError, match="CONFIG_REQUIRED"):
        cli._open_or_create_run(output, prepared)
    assert not output.exists()


def test_invalid_config_fails_closed_before_creating_manifest(tmp_path):
    config = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL)
    config["beam_size"] = True
    prepared = _prepared(config=config)
    output = tmp_path / "invalid-config-run"
    with pytest.raises(ValueError, match="BEAM_SIZE_INVALID"):
        cli._open_or_create_run(output, prepared)
    assert not output.exists()


def test_config_hash_mismatch_fails_closed_before_creating_manifest(tmp_path):
    prepared = _prepared(config_hash="c" * 64)
    output = tmp_path / "hash-mismatch-run"
    with pytest.raises(ValueError, match="CONFIG_HASH_MISMATCH"):
        cli._open_or_create_run(output, prepared)
    assert not output.exists()


def test_valid_manifest_persists_complete_hash_bound_config(tmp_path):
    prepared = _prepared()
    output = tmp_path / "valid-run"
    manifest = cli._open_or_create_run(output, prepared)
    assert manifest["config"] == prepared["config"]
    assert manifest["config_sha256"] == object_hash(manifest["config"])
    assert manifest["beam_size"] == 5
    assert (output / "run-manifest.json").is_file()
