#!/usr/bin/env python3
"""Validate the deterministic Studio short-form framework library."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from itertools import combinations
from pathlib import Path

from jsonschema_subset import SchemaValidationError, validate_instance


ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "studio" / "framework-library" / "v1"
SCHEMA = ROOT / "schemas" / "studio-framework.schema.json"
EXPORT_SCHEMA = ROOT / "schemas" / "signal-to-studio.schema.json"
AXES = [
    "hook_mechanism", "viewer_job", "broll_function", "proof_form", "visual_grammar",
    "pacing_profile", "transition_family", "a_roll_integration", "sound_role",
    "text_role", "cta_exit", "risk_class",
]


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_hash(payload: dict) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(material).hexdigest()


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> None:
    schema = load(SCHEMA)
    export_schema = load(EXPORT_SCHEMA)
    manifest = load(LIB / "library-manifest.json")
    if manifest["framework_count"] < 50:
        fail("fewer than 50 frameworks")
    if manifest["framework_count"] != len(manifest["records"]):
        fail("library record count mismatch")
    if manifest["external_provider_state"] != "NOT_RUN":
        fail("library provider state drift")
    allowed = {axis: set(schema["properties"]["taxonomy"]["properties"][axis]["enum"]) for axis in AXES}
    tuples: dict[tuple, str] = {}
    frameworks = []
    svg_sizes = []
    issues = []
    schema_validations = 0
    for record in manifest["records"]:
        package = LIB / record["path"]
        required = ["framework.json", "signal-export.json", "report.md", "prompt.md", "contact-sheet.svg", "manifest.json"]
        for filename in required:
            if not (package / filename).is_file():
                issues.append(f"{record['framework_id']}: missing {filename}")
        framework = load(package / "framework.json")
        export = load(package / "signal-export.json")
        package_manifest = load(package / "manifest.json")
        try:
            validate_instance(framework, schema, SCHEMA)
            validate_instance(export, export_schema, EXPORT_SCHEMA)
            schema_validations += 2
        except SchemaValidationError as exc:
            issues.append(f"{record['framework_id']}: JSON Schema failure: {exc}")
        if framework["framework_id"] != record["framework_id"]:
            issues.append(f"{record['framework_id']}: framework ID mismatch")
        if not re.fullmatch(r"SF-[0-9]{3}", framework["framework_id"]):
            issues.append(f"{record['framework_id']}: invalid ID")
        if framework["external_provider_state"] != "NOT_RUN" or export["external_provider_state"] != "NOT_RUN":
            issues.append(f"{record['framework_id']}: provider state drift")
        if framework["rights_state"] != "original_local_previsualization":
            issues.append(f"{record['framework_id']}: invalid rights state")
        if framework["signal_input"]["record_hash"] != export["provenance"]["record_hash"]:
            issues.append(f"{record['framework_id']}: signal hash link mismatch")
        if record["record_hash"] != export["provenance"]["record_hash"]:
            issues.append(f"{record['framework_id']}: library/export record hash drift")
        if record["taxonomy"] != framework["taxonomy"]:
            issues.append(f"{record['framework_id']}: library/framework taxonomy drift")
        if framework["signal_input"]["source_rights_state"] != export["rights_state"]:
            issues.append(f"{record['framework_id']}: source rights link mismatch")
        check_export = json.loads(json.dumps(export))
        claimed_hash = check_export["provenance"].pop("record_hash")
        if canonical_hash(check_export) != claimed_hash:
            issues.append(f"{record['framework_id']}: export canonical hash mismatch")
        for axis in AXES:
            value = framework["taxonomy"].get(axis)
            if value not in allowed[axis]:
                issues.append(f"{record['framework_id']}: uncontrolled {axis}={value}")
        identity = tuple(framework["taxonomy"][axis] for axis in AXES[:-1])
        if identity in tuples:
            issues.append(f"{record['framework_id']}: duplicate tuple with {tuples[identity]}")
        tuples[identity] = framework["framework_id"]
        frames = framework["frames"]
        if not 4 <= len(frames) <= 12:
            issues.append(f"{record['framework_id']}: frame count out of range")
        if frames[0]["start_ms"] != 0 or frames[-1]["end_ms"] != framework["duration_ms"]:
            issues.append(f"{record['framework_id']}: incomplete duration coverage")
        for index, frame in enumerate(frames):
            if frame["sequence_number"] != index + 1:
                issues.append(f"{record['framework_id']}: sequence mismatch")
            if frame["end_ms"] <= frame["start_ms"]:
                issues.append(f"{record['framework_id']}: non-positive interval")
            if index and frames[index - 1]["end_ms"] != frame["start_ms"]:
                issues.append(f"{record['framework_id']}: interval gap/overlap")
            image = package / frame["image_path"]
            if not image.is_file():
                issues.append(f"{record['framework_id']}: missing frame image {frame['image_path']}")
            else:
                svg_sizes.append(image.stat().st_size)
            if len(frame["acceptance_checks"]) < 2:
                issues.append(f"{record['framework_id']}: insufficient frame checks")
        if frames[0]["end_ms"] > 1000:
            issues.append(f"{record['framework_id']}: hook not present in first second")
        mode = framework["taxonomy"]["a_roll_integration"]
        states = [frame["a_roll_state"] for frame in frames]
        if mode == "full_open" and not (states[0] == "full" and states[-1] == "return_cut"):
            issues.append(f"{record['framework_id']}: invalid full_open sequence")
        if mode == "delayed_reveal" and not (states[0] == "absent" and "full" in states[1:-1] and states[-1] == "return_cut"):
            issues.append(f"{record['framework_id']}: invalid delayed_reveal sequence")
        if mode == "voice_over_broll" and not (all(state == "voice_over" for state in states[:-1]) and states[-1] == "return_cut"):
            issues.append(f"{record['framework_id']}: invalid voice_over_broll sequence")
        if mode == "picture_in_picture" and not all(state == "picture_in_picture" for state in states):
            issues.append(f"{record['framework_id']}: invalid picture_in_picture sequence")
        if mode == "return_cut" and not (all(state == "voice_over" for state in states[:-1]) and states[-1] == "return_cut"):
            issues.append(f"{record['framework_id']}: invalid return_cut sequence")
        if mode == "absent" and not all(state == "absent" for state in states):
            issues.append(f"{record['framework_id']}: invalid absent sequence")
        for relpath, expected in package_manifest["files"].items():
            target = package / relpath
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                issues.append(f"{record['framework_id']}: package hash mismatch {relpath}")
        for md_name in ("report.md", "prompt.md"):
            text = (package / md_name).read_text(encoding="utf-8")
            if "/Users/" in text or "file://" in text:
                issues.append(f"{record['framework_id']}: absolute/private path in {md_name}")
            if "EXTERNAL_PROVIDER_NOT_RUN" not in text and "External image/video/audio provider execution remains NOT RUN" not in text:
                issues.append(f"{record['framework_id']}: missing provider truth in {md_name}")
        frameworks.append(framework)
    minimum_cross_hook_distance = len(AXES)
    for left, right in combinations(frameworks, 2):
        all_differences = {axis for axis in AXES[:-1] if left["taxonomy"][axis] != right["taxonomy"][axis]}
        minimum_cross_hook_distance = min(minimum_cross_hook_distance, len(all_differences))
        if len(all_differences) < 2:
            issues.append(f"cross-hook near duplicate: {left['framework_id']} and {right['framework_id']} differ on {len(all_differences)} axes")
        if left["taxonomy"]["hook_mechanism"] != right["taxonomy"]["hook_mechanism"]:
            continue
        differences = {axis for axis in AXES[:-1] if left["taxonomy"][axis] != right["taxonomy"][axis]}
        if len(differences) < 3:
            issues.append(f"near duplicate: {left['framework_id']} and {right['framework_id']} differ on {len(differences)} axes")
        if "viewer_job" not in differences:
            issues.append(f"near duplicate viewer job: {left['framework_id']} and {right['framework_id']}")
        if not differences.intersection({"broll_function", "proof_form", "visual_grammar"}):
            issues.append(f"near duplicate content form: {left['framework_id']} and {right['framework_id']}")
        if not differences.intersection({"pacing_profile", "transition_family", "a_roll_integration", "text_role", "cta_exit"}):
            issues.append(f"near duplicate delivery: {left['framework_id']} and {right['framework_id']}")
    if issues:
        print(json.dumps({"status": "FAIL", "issues": issues[:100], "issue_count": len(issues)}, indent=2))
        sys.exit(1)
    if manifest["frame_count"] != len(svg_sizes):
        fail("library frame count mismatch")
    duration_seconds = sorted({framework["duration_ms"] // 1000 for framework in frameworks})
    if len(duration_seconds) < 4:
        fail("insufficient duration/frame-count diversity")
    total_bytes = sum(svg_sizes)
    result = {
        "status": "PASS",
        "frameworks": len(frameworks),
        "frames": len(svg_sizes),
        "unique_taxonomy_tuples": len(tuples),
        "json_schema_validations": schema_validations,
        "duration_seconds": duration_seconds,
        "minimum_pairwise_axis_distance": minimum_cross_hook_distance,
        "average_svg_bytes": round(total_bytes / len(svg_sizes), 1),
        "total_svg_bytes": total_bytes,
        "schema_files_parsed": [SCHEMA.relative_to(ROOT).as_posix(), EXPORT_SCHEMA.relative_to(ROOT).as_posix()],
        "provider_calls": 0,
        "external_writes": 0,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
