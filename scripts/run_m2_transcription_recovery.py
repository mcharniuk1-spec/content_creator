"""Explicit operator entry point for the isolated offline ASR recovery lane.

Without ``--run`` this command performs only hash/rights/model/config
preflight.  ``--run`` is intentionally a separate explicit action and should
be used only after the main corpus worker is paused at a reviewed checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import shutil
from pathlib import Path

# Standalone script support: make the repository root importable before the
# package imports below.  Module invocation remains supported as well.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from m2_orchestrator.media_transcription import _rights_and_source, _validate_duration, validate_model_bundle
from m2_orchestrator.transcription_recovery import build_recovery_config, object_hash, plan_windows, recover_chunks

ALLOWED_ALIAS_PATHS = {"/tmp", "/private/tmp", "/var", "/private/var"}


def _load(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("RECORD_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise ValueError("RECORD_JSON_INVALID")
    return value


def _runtime_receipt(python_executable: str | Path) -> dict:
    """Bind the exact interpreter and package/runtime surface into resumes."""

    raw_path = Path(python_executable)
    if not raw_path.is_absolute() and len(raw_path.parts) == 1:
        located = shutil.which(str(raw_path))
        if located is None:
            raise ValueError("PYTHON_EXECUTABLE_INVALID")
        path = Path(located).absolute()
    else:
        path = raw_path.absolute()
    # A normal interpreter launcher (for example pyenv's ``python3``) may be
    # a final symlink; bind both lexical and resolved identities while still
    # rejecting symlinked directory ancestry.
    for ancestor in path.parents:
        if ancestor.is_symlink() and str(ancestor) not in ALLOWED_ALIAS_PATHS:
            raise ValueError("INPUT_SYMLINK_ANCESTOR")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError("PYTHON_EXECUTABLE_INVALID")
    probe = (
        "import importlib.metadata as m, json, sys\n"
        "names=['faster-whisper','ctranslate2','numpy','av']\n"
        "packages={}\n"
        "for n in names:\n"
        "    try:\n"
        "        packages[n]=m.version(n)\n"
        "    except m.PackageNotFoundError:\n"
        "        packages[n]=None\n"
        "print(json.dumps({'python_version':sys.version,'implementation':sys.implementation.name,'packages':packages}, sort_keys=True))"
    )
    try:
        completed = subprocess.run([str(path), "-c", probe], capture_output=True, text=True, timeout=10, check=False)
        runtime = json.loads(completed.stdout) if completed.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, UnicodeError, json.JSONDecodeError):
        runtime = None
    if not isinstance(runtime, dict) or not isinstance(runtime.get("packages"), dict):
        raise ValueError("PYTHON_RUNTIME_PROBE_FAILED")
    module_hashes = {}
    for module_path in (Path(__file__), REPO_ROOT / "m2_orchestrator" / "transcription_recovery.py", REPO_ROOT / "m2_orchestrator" / "transcription_chunk_worker.py", REPO_ROOT / "m2_orchestrator" / "media_transcription.py", REPO_ROOT / "m2_orchestrator" / "process_budget.py", REPO_ROOT / "m2_studio" / "media.py"):
        if not module_path.is_file() or module_path.is_symlink():
            raise ValueError("RUNTIME_MODULE_UNAVAILABLE")
        module_hashes[module_path.name] = hashlib.sha256(module_path.read_bytes()).hexdigest()
    return {
        "schema": "m2.transcription-recovery-runtime-receipt.v1",
        "executable_lexical": str(path),
        "executable_resolved": str(resolved),
        "executable_sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
        "python_version": runtime["python_version"],
        "implementation": runtime["implementation"],
        "packages": runtime["packages"],
        "module_hashes": module_hashes,
    }


def _prepare(args: argparse.Namespace) -> dict:
    def checked_path(value: str | Path) -> Path:
        path = Path(value).absolute()
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink() and str(ancestor) not in ALLOWED_ALIAS_PATHS:
                raise ValueError("INPUT_SYMLINK_ANCESTOR")
        return path

    record_path = checked_path(args.record_json)
    record = _load(record_path)
    lexical_root = checked_path(args.source_root)
    pointer = record.get("source_pointer")
    if not isinstance(pointer, str) or not pointer or Path(pointer).is_absolute() or ".." in Path(pointer).parts:
        raise ValueError("SOURCE_POINTER_INVALID")
    checked_path(lexical_root / pointer)
    lexical_model = checked_path(args.model_dir)
    runtime = _runtime_receipt(args.python_executable)
    root = lexical_root.resolve(strict=True)
    source = _rights_and_source(root, record)
    duration_ms = _validate_duration(record)
    if record.get("original_audio_unknown") is True:
        raise ValueError("ORIGINAL_AUDIO_UNKNOWN_REQUIRES_AUDIO_SOURCE_PROOF")
    if record.get("has_audio") is False:
        raise ValueError("NO_AUDIO_STREAM")
    model = validate_model_bundle(args.model_dir)
    config = build_recovery_config(source_media_hash=record["sha256"], duration_ms=duration_ms, model_bundle_sha256=model["bundle_sha256"])
    config_hash = object_hash(config)
    plans = plan_windows(duration_ms)
    input_paths = {"source_root_lexical": str(lexical_root), "source_root_resolved": str(root),
                   "source_resolved": str(source), "record_lexical": str(record_path),
                   "model_lexical": str(lexical_model), "model_resolved": str(lexical_model.resolve(strict=True))}
    return {"record": record, "root": root, "source": source, "duration_ms": duration_ms, "model": model, "config": config, "config_hash": config_hash, "plans": plans, "input_paths": input_paths, "runtime": runtime}


def _validate_output_path(output: Path) -> None:
    absolute = output.absolute()
    for ancestor in (absolute, *absolute.parents):
        if ancestor.is_symlink() and str(ancestor) not in ALLOWED_ALIAS_PATHS:
            raise ValueError("OUTPUT_SYMLINK_ANCESTOR")
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError("OUTPUT_DIRECTORY_INVALID")


def _run_manifest(prepared: dict) -> dict:
    return {
        "schema": "m2.transcription-recovery-run-manifest.v1",
        "source_media_hash": prepared["record"]["sha256"],
        "source_pointer": prepared["record"]["source_pointer"],
        "model_bundle_sha256": prepared["model"]["bundle_sha256"],
        "config_sha256": prepared["config_hash"],
        "plans": prepared["plans"],
        "plans_sha256": object_hash(prepared["plans"]),
        "source_frame_probe_reused": True,
        "offline_only": True,
        "input_paths": prepared["input_paths"],
        "runtime": prepared["runtime"],
        "source_record_sha256": object_hash(prepared["record"]),
        "source_kind": prepared["record"].get("source_kind"),
        "rights": prepared["record"].get("rights"),
    }


def _open_or_create_run(output: Path, prepared: dict) -> dict:
    """Create or validate the durable run manifest before any child launch."""

    _validate_output_path(output)
    manifest_path = output / "run-manifest.json"
    expected = _run_manifest(prepared)
    if output.exists():
        if not manifest_path.is_file() or manifest_path.is_symlink():
            raise ValueError("RUN_MANIFEST_REQUIRED")
        try:
            persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("RUN_MANIFEST_INVALID") from exc
        if not isinstance(persisted, dict) or any(persisted.get(key) != value for key, value in expected.items()):
            raise ValueError("RUN_MANIFEST_BINDING_MISMATCH")
        return persisted
    output.mkdir(parents=False, exist_ok=False)
    manifest_path.write_text(json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    return expected


def _write_aggregate(path: Path, payload: dict) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("AGGREGATE_PATH_INVALID")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists() or temporary.is_symlink():
        raise ValueError("AGGREGATE_PARTIAL_EXISTS")
    temporary.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-json", required=True, help="Observed media record JSON")
    parser.add_argument("--source-root", required=True, help="Root containing the retained source media")
    parser.add_argument("--model-dir", required=True, help="Frozen local Faster-Whisper model directory")
    parser.add_argument("--output-dir", required=True, help="Fresh private recovery output directory")
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--run", action="store_true", help="Execute one serial chunk at a time after preflight")
    parser.add_argument("--preflight", action="store_true", help="Validate only; this is the default")
    args = parser.parse_args(argv)
    try:
        if args.run and args.preflight:
            raise ValueError("RUN_PREFLIGHT_MUTUALLY_EXCLUSIVE")
        prepared = _prepare(args)
        output = Path(args.output_dir).absolute()
        preflight = {
            "schema": "m2.transcription-recovery-preflight.v1",
            "state": "ADMITTED_FOR_ISOLATED_RUN" if args.run else "PREFLIGHT_ONLY",
            "source_media_hash": prepared["record"]["sha256"],
            "model_bundle_sha256": prepared["model"]["bundle_sha256"],
            "model_manifest_sha256": prepared["model"]["manifest_sha256"],
            "config_sha256": prepared["config_hash"],
            "chunk_count": len(prepared["plans"]),
            "plans": prepared["plans"],
            "source_frame_probe_reused": True,
            "offline_only": True,
            "run_requested": args.run,
            "input_paths": prepared["input_paths"],
            "runtime": prepared["runtime"],
        }
        if not args.run:
            print(json.dumps(preflight, sort_keys=True, separators=(",", ":")))
            return 0
        run_manifest = _open_or_create_run(output, prepared)
        merged = recover_chunks(
            prepared["plans"],
            source_media_hash=prepared["record"]["sha256"],
            model_bundle_sha256=prepared["model"]["bundle_sha256"],
            config_sha256=prepared["config_hash"],
            source_pointer=prepared["record"]["source_pointer"],
            rights=prepared["record"]["rights"],
            config=prepared["config"],
            production={"output_root": output, "source_root": prepared["root"], "model_dir": args.model_dir, "python_executable": args.python_executable},
        )
        aggregate_path = output / "transcription-recovery.json"
        _write_aggregate(aggregate_path, {**preflight, "run_manifest": run_manifest, "state": merged["observation_state"], "result": merged})
        print(json.dumps({"schema": preflight["schema"], "state": merged["observation_state"], "failure_code": merged["failure_code"], "chunk_count": merged["chunk_count"]}, separators=(",", ":")))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"schema": "m2.transcription-recovery-preflight.v1", "state": "BLOCKED", "failure_code": str(exc)}, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
