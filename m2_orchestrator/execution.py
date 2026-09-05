"""Built-in offline stage handlers; manual and server runs use the same code.

Agent stages export tasks and require explicit reviewed products. No command is
read from input data, and this module cannot import HikerAPI or call a provider.
"""

import json
import shutil
from pathlib import Path

from .policy import STAGES
from .state import Controller, StateError, digest, file_digest, implementation_manifest

DETERMINISTIC_STAGES = ("admit", "freeze_config", "inventory", "collect_or_replay", "normalize",
                        "audit_all_rows", "snapshot_metrics", "compute_baselines", "rank_candidates",
                        "transcript_attempt", "visual_attempt", "comment_attempt")


def default_actors():
    return {"integrator": ["integrator"], "data_engineer": ["data_engineer"],
            "quantitative_analyst": ["quantitative_analyst"], "text_analyst": ["text_analyst"],
            "scene_analyst": ["scene_analyst"], "comment_analyst": ["comment_analyst"],
            "strategy_analyst": ["strategy_analyst"], "signal_reviewer": ["signal_reviewer"],
            "script_architect": ["script_architect"], "scene_planner": ["scene_planner"],
            "studio_reviewer": ["studio_reviewer"], "projection_engineer": ["projection_engineer"],
            "video_engineer": ["video_engineer"], "owner": ["owner"], "publisher": ["publisher"],
            "knowledge_curator": ["knowledge_curator"], "knowledge_reviewer": ["knowledge_reviewer"]}


def prepare(source_dir, run_dir, run_id, mode="replay", settings=None, database=None):
    source = Path(source_dir).resolve()
    root = Path(run_dir).resolve()
    files = sorted(p for p in source.iterdir() if p.is_file() and p.suffix in {".csv", ".json"})
    if not files or any(p.is_symlink() for p in files):
        raise StateError("EXPLICIT_SOURCE_FILES_REQUIRED")
    if any(p.stat().st_size > 256 * 1024 * 1024 for p in files):
        raise StateError("SOURCE_FILE_SIZE_LIMIT")
    manifest = [{"source_id": p.name, "sha256": file_digest(p)} for p in files]
    config = {"schema": "m2.run-config.v1", "platforms": ["instagram_reels"], "mode": mode,
              "provider_execution": False, "hikerapi_execution": False,
              "source_manifest": manifest, "actors": default_actors(), "metric_config": settings or {},
              "production": {"requires_generation": False}, "source_scope": "explicit_supplied_export",
              "ledger_mode": "shared" if database else "run_local",
              "ledger_binding": digest(str(Path(database).resolve())) if database else None,
              "implementation_manifest": implementation_manifest()}
    controller = Controller(root)
    controller.init(run_id, config)
    (root / "inputs").mkdir(exist_ok=True)
    for p, item in zip(files, manifest):
        dest = root / "inputs" / p.name
        if dest.exists():
            if file_digest(dest) != item["sha256"]:
                raise StateError("FROZEN_INPUT_CHANGED")
        else:
            temp = dest.with_suffix(dest.suffix + ".partial")
            shutil.copyfile(p, temp)
            if file_digest(temp) != item["sha256"]:
                raise StateError("SOURCE_CHANGED_DURING_COPY")
            temp.replace(dest)
    config_file = root / "config.json"
    body = json.dumps(config, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if config_file.exists() and config_file.read_text() != body:
        raise StateError("FROZEN_CONFIG_FILE_CHANGED")
    config_file.write_text(body)
    return controller, config


def execute_replay(source_dir, run_dir, run_id, mode="replay", until=None, settings=None, database=None):
    from m2_signal import analyze, ingest_export

    if until is not None and until not in DETERMINISTIC_STAGES:
        raise StateError("UNTIL_STAGE_NOT_EXECUTABLE")
    c, config = prepare(source_dir, run_dir, run_id, mode, settings, database)
    root = c.root
    out = root / "signal"
    (root / "products").mkdir(exist_ok=True)
    (root / "receipts").mkdir(exist_ok=True)
    out.mkdir(exist_ok=True)
    ledger = Path(database).resolve() if database else out / "signal.sqlite"
    release_file = root / "products" / "collect_or_replay.json"
    for stage_id in DETERMINISTIC_STAGES:
        stage = next(s for s in STAGES if s.id == stage_id)
        begun = c.begin(stage_id, stage.role)
        if begun["cached"]:
            if until == stage_id:
                break
            continue
        try:
            for item in config["source_manifest"]:
                if file_digest(root / "inputs" / item["source_id"]) != item["sha256"]:
                    raise StateError("FROZEN_INPUT_CHANGED")
            extra = []
            limits = []
            if stage_id == "admit":
                product = {"schema": "m2.local-admission.v1", "admission": "accepted_offline_execution",
                           "platforms": ["instagram_reels"], "external_authority": False,
                           "config_hash": digest(config), "implementation": "stdlib_sqlite_controller"}
            elif stage_id == "freeze_config":
                product = {"config_hash": digest(config), "source_manifest": config["source_manifest"]}
                extra = ["config.json"]
            elif stage_id == "inventory":
                product = {"files": config["source_manifest"], "source_mode": mode, "media_acquired": False}
            elif stage_id == "collect_or_replay":
                product = ingest_export(ledger, root / "inputs", settings or None)
            elif stage_id == "normalize":
                ingest = json.loads(release_file.read_text())
                product = analyze(ledger, ingest["release_id"], out)
                extra = [str(p.relative_to(root)) for p in out.iterdir() if p.suffix in {".csv", ".jsonl", ".json"}]
                limits = ["Frozen export is descriptive; source-media and market review gaps remain."]
            else:
                summary = json.loads((out / "summary.json").read_text())
                product = {"schema": "m2.deterministic-check.v1", "stage": stage_id,
                           "release_id": summary["release_id"], "summary_sha256": file_digest(out / "summary.json"),
                           "population": summary["population"], "coverage": summary["coverage"],
                           "checks": {"frozen_inputs_reverified": True, "analysis_outputs_hash_bound": True}}
                extra = ["signal/summary.json", "signal/artifact-manifest.json"]
                if stage_id in {"transcript_attempt", "visual_attempt", "comment_attempt"}:
                    product["operation"] = "inventory_existing_evidence_and_missing_evidence_job_queue"
                    product["acquisition_performed"] = False
                    limits = ["Evidence inventory only. Unavailable modalities remain typed gaps; no acquisition or ASR is implied."]
                elif stage_id in {"compute_baselines", "rank_candidates"}:
                    limits = ["Snapshot descriptive diagnostic; no fixed-age forecast, causal effect, or final Best-Reel acceptance."]
                elif stage_id == "audit_all_rows":
                    limits = ["Conflicting or impossible identities remain quarantined and excluded from metric decisions."]
            path = root / "products" / (stage_id + ".json")
            path.write_text(json.dumps(product, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)+"\n")
            receipt = c.finish(stage_id, begun["token"], [str(path.relative_to(root)), *extra],
                               "PASS_WITH_LIMITATIONS" if limits else "PASS", limits)
            (root / "receipts" / (stage_id + ".json")).write_text(json.dumps(receipt, indent=2)+"\n")
        except Exception as exc:
            code = str(exc) if isinstance(exc, StateError) else "LOCAL_HANDLER_FAILED"
            c.fail(stage_id, begun["token"], code)
            raise
        if until == stage_id:
            break
    status = c.status()
    (root / "status.json").write_text(json.dumps(status, indent=2)+"\n")
    (root / "trace.json").write_text(json.dumps(c.trace(), indent=2)+"\n")
    (root / "trace-verification.json").write_text(json.dumps(c.verify(), indent=2)+"\n")
    return status
