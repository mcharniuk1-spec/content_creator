#!/usr/bin/env python3
"""Validate the 50-package v2 sequential-story library."""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

from jsonschema_subset import SchemaValidationError, validate_instance


ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "studio" / "story-framework-library" / "v2"
SCHEMA_PATH = ROOT / "schemas" / "studio-story-framework.schema.json"


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrap_for_validation(value: str, width: int) -> list[str]:
    words, lines, current = value.split(), [], []
    for word in words:
        if len(" ".join(current + [word])) > width and current:
            lines.append(" ".join(current)); current = [word]
        else:
            current.append(word)
    if current: lines.append(" ".join(current))
    return lines[:3]


def relative_luminance(hex_color: str) -> float:
    """Return WCAG relative luminance for a six-digit sRGB hex color."""
    components = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [component / 12.92 if component <= 0.04045 else ((component + 0.055) / 1.055) ** 2.4 for component in components]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def main() -> None:
    issues: list[str] = []
    schema = load(SCHEMA_PATH)
    library = load(LIB / "library-manifest.json")
    if not (LIB / "CATALOG.md").is_file():
        issues.append("missing root CATALOG.md")
    if library.get("story_count") != 50:
        issues.append(f"library must contain exactly 50 stories, got {library.get('story_count')}")
    if library.get("frame_count") != 300:
        issues.append(f"library must contain exactly 300 one-second frames, got {library.get('frame_count')}")
    if library.get("external_provider_state") != "NOT_RUN":
        issues.append("library provider state drift")
    required_files = ["story.json", "screenplay.md", "prompt.md", "report.md", "contact-sheet.svg", "manifest.json"]
    fingerprints = {"semantic": set(), "causal": set(), "visual": set()}
    family_counts: Counter[str] = Counter()
    family_visual_signatures: dict[str, tuple] = {}
    family_variations: dict[str, list[tuple[str, dict]]] = {}
    variation_fingerprints: set[str] = set()
    frame_files = 0
    svg_bytes = 0
    schema_validations = 0
    for record in library.get("records", []):
        package = LIB / record["path"]
        for name in required_files:
            if not (package / name).is_file(): issues.append(f"{record['story_id']}: missing {name}")
        if not (package / "story.json").is_file():
            continue
        story = load(package / "story.json")
        try:
            validate_instance(story, schema, SCHEMA_PATH)
            schema_validations += 1
        except SchemaValidationError as exc:
            issues.append(f"{record['story_id']}: schema failure: {exc}")
        if story.get("story_id") != record.get("story_id") or not re.fullmatch(r"ST-[0-9]{3}", story.get("story_id", "")):
            issues.append(f"{record['story_id']}: story ID drift")
        if story.get("external_provider_state") != "NOT_RUN" or story.get("rights_state") != "original_local_previsualization":
            issues.append(f"{record['story_id']}: truth/rights drift")
        if sha(package / "story.json") != record.get("story_sha256"):
            issues.append(f"{record['story_id']}: story hash drift")
        family_counts[story.get("family", "missing")] += 1
        variation = story.get("variation_axes", {})
        family_variations.setdefault(story.get("family", "missing"), []).append((record["story_id"], variation))
        variation_fp = story.get("variation_fingerprint")
        if variation_fp in variation_fingerprints: issues.append(f"{record['story_id']}: duplicate variation fingerprint")
        variation_fingerprints.add(variation_fp)
        entity_ids = {entity.get("entity_id") for entity in story.get("entities", [])}
        required_entities = {"ENT-hero", "ENT-trigger", "ENT-target", "ENT-obstacle", "ENT-proof"}
        if entity_ids != required_entities:
            issues.append(f"{record['story_id']}: entity registry drift {sorted(entity_ids)}")
        for key, field in (("semantic", "semantic_fingerprint"), ("causal", "causal_graph_fingerprint"), ("visual", "visual_sequence_fingerprint")):
            value = story.get(field)
            if value in fingerprints[key]: issues.append(f"{record['story_id']}: duplicate {key} fingerprint")
            fingerprints[key].add(value)
        narrative = story.get("narrative", {})
        for field in ("protagonist", "objective", "obstacle", "stakes", "proof", "limitation", "payoff", "handback"):
            if not narrative.get(field): issues.append(f"{record['story_id']}: missing narrative {field}")
        palette = story.get("continuity_bible", {}).get("palette", [])
        if len(palette) < 2:
            issues.append(f"{record['story_id']}: incomplete continuity palette")
            limit_text_color, limit_panel_color = "#000000", "#000000"
        else:
            limit_text_color, limit_panel_color = palette[0], palette[1]
            if contrast_ratio(limit_text_color, limit_panel_color) < 4.5:
                issues.append(f"{record['story_id']}: LIMIT overlay contrast below 4.5:1")
        frames = story.get("frames", [])
        visual_signature = tuple((f.get("shot_scale"), f.get("camera_motion"), f.get("beat_role")) for f in frames)
        family = story.get("family", "missing")
        if family in family_visual_signatures and family_visual_signatures[family] != visual_signature:
            issues.append(f"{record['story_id']}: visual grammar drift inside {family}")
        family_visual_signatures[family] = visual_signature
        if len(frames) != 6: issues.append(f"{record['story_id']}: expected six frames")
        if frames and (frames[0].get("start_ms") != 0 or frames[-1].get("end_ms") != story.get("duration_ms")):
            issues.append(f"{record['story_id']}: incomplete duration")
        for i, frame in enumerate(frames):
            if frame.get("sequence_number") != i + 1: issues.append(f"{record['story_id']}: sequence drift at {i+1}")
            if frame.get("start_ms") != i * 1000 or frame.get("end_ms") != (i + 1) * 1000: issues.append(f"{record['story_id']}: non-second interval at {i+1}")
            if i and frame.get("state_before") != frames[i-1].get("state_after"): issues.append(f"{record['story_id']}: state discontinuity at {i+1}")
            before_map, after_map = frame.get("entity_state_before", {}), frame.get("entity_state_after", {})
            if set(before_map) != entity_ids or set(after_map) != entity_ids:
                issues.append(f"{record['story_id']}: incomplete entity-state map at {i+1}")
            if i and before_map != frames[i-1].get("entity_state_after"):
                issues.append(f"{record['story_id']}: entity-state discontinuity at {i+1}")
            if before_map == after_map:
                issues.append(f"{record['story_id']}: entity-state map does not change at {i+1}")
            expected_causes = [] if i == 0 else [frames[i-1].get("frame_id")]
            if frame.get("cause_frame_ids") != expected_causes: issues.append(f"{record['story_id']}: causal edge drift at {i+1}")
            if frame.get("state_before") == frame.get("state_after"): issues.append(f"{record['story_id']}: no state change at {i+1}")
            if not set(frame.get("visible_entity_ids", [])).issubset(entity_ids) or not set(frame.get("affected_entity_ids", [])).issubset(entity_ids):
                issues.append(f"{record['story_id']}: unknown entity reference at {i+1}")
            if i >= 1 and "ENT-target" not in frame.get("visible_entity_ids", []):
                issues.append(f"{record['story_id']}: persistent target not visible at {i+1}")
            if frame.get("beat_role") in ("attempt", "mechanism", "proof", "limitation", "payoff", "handback") and "ENT-target" not in frame.get("affected_entity_ids", []):
                issues.append(f"{record['story_id']}: target not causally affected at {i+1}")
            if frame.get("proof_anchor_visible") != (frame.get("beat_role") in ("proof", "limitation", "payoff", "handback")):
                issues.append(f"{record['story_id']}: proof visibility mismatch at {i+1}")
            if i == len(frames)-1 and not frame.get("limitation_visible"):
                issues.append(f"{record['story_id']}: final limitation not visible")
            if i == len(frames)-1:
                final_roles = set(frame.get("beat_roles", []))
                if not {"limitation", "payoff", "handback"}.issubset(final_roles):
                    issues.append(f"{record['story_id']}: final compound roles missing")
                if not (frame.get("payoff_visible") and frame.get("handback_visible")):
                    issues.append(f"{record['story_id']}: final payoff/handback flags missing")
            if not frame.get("camera_motivation") or not frame.get("information_gain"): issues.append(f"{record['story_id']}: unmotivated cut at {i+1}")
            image = package / frame.get("image_path", "")
            if not image.is_file():
                issues.append(f"{record['story_id']}: missing frame image {i+1}")
            else:
                frame_files += 1; size = image.stat().st_size; svg_bytes += size
                body = image.read_text(encoding="utf-8")
                if size > 20000: issues.append(f"{record['story_id']}: frame {i+1} exceeds 20KB")
                expected_state = html.escape(after_map.get("ENT-target", ""), quote=True)
                expected_operation = frame.get("visual_operation", "")
                if 'data-entity-id="ENT-target"' not in body or f'data-state="{expected_state}"' not in body or f'data-operation="{expected_operation}"' not in body:
                    issues.append(f"{record['story_id']}: frame {i+1} lacks semantic SVG entity/state/operation attributes")
                if f'data-proof-visible="{str(frame.get("proof_anchor_visible")).lower()}"' not in body:
                    issues.append(f"{record['story_id']}: frame {i+1} proof data attribute drift")
                target_label = story.get("continuity_bible", {}).get("target_prop", "")[:24]
                if i >= 1 and target_label and target_label not in body:
                    issues.append(f"{record['story_id']}: frame {i+1} does not render persistent target label")
                if frame.get("limitation_visible"):
                    limitation = story.get("narrative", {}).get("limitation", "")
                    expected_limit = html.escape(limitation, quote=True)
                    if f'data-limitation="{expected_limit}"' not in body:
                        issues.append(f"{record['story_id']}: frame {i+1} exact limitation data missing")
                    if f'data-limit-text-color="{limit_text_color}"' not in body or f'data-limit-panel-color="{limit_panel_color}"' not in body:
                        issues.append(f"{record['story_id']}: frame {i+1} LIMIT palette metadata drift")
                    for line in wrap_for_validation(limitation, 48):
                        if html.escape(line) not in body:
                            issues.append(f"{record['story_id']}: frame {i+1} rendered limitation text missing")
        if frames and not (frames[0].get("a_roll_state") == "full" and frames[-1].get("a_roll_state") == "return_cut"):
            issues.append(f"{record['story_id']}: missing A-roll open/handback")
        manifest = load(package / "manifest.json") if (package / "manifest.json").is_file() else {"files": {}}
        for rel, expected in manifest.get("files", {}).items():
            target = package / rel
            if not target.is_file() or sha(target) != expected: issues.append(f"{record['story_id']}: manifest hash drift {rel}")
        for md in ("screenplay.md", "prompt.md", "report.md"):
            path = package / md
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                if "/Users/" in text or "file://" in text: issues.append(f"{record['story_id']}: private path in {md}")
                if "NOT_RUN" not in text and "NOT RUN" not in text: issues.append(f"{record['story_id']}: missing provider truth in {md}")
    if family_counts and (len(family_counts) != 10 or set(family_counts.values()) != {5}):
        issues.append(f"family balance failure: {dict(family_counts)}")
    if len(set(family_visual_signatures.values())) != 10:
        issues.append("ten families do not have ten distinct shot/motion/role grammars")
    variation_axes = ("operation_type", "target_transformation", "proof_mechanism", "scene_topology")
    for family, records in family_variations.items():
        for (left_id, left), (right_id, right) in combinations(records, 2):
            distance = sum(left.get(axis) != right.get(axis) for axis in variation_axes)
            if distance < 3:
                issues.append(f"{family}: weak within-family variation {left_id}/{right_id} distance={distance}")
    if frame_files != 300: issues.append(f"validated frame file count {frame_files}, expected 300")
    if issues:
        print(json.dumps({"status":"FAIL", "issue_count":len(issues), "issues":issues[:120]}, indent=2)); sys.exit(1)
    print(json.dumps({
        "status":"PASS", "stories":50, "families":dict(sorted(family_counts.items())), "frames":frame_files,
        "json_schema_validations":schema_validations, "unique_semantic_fingerprints":len(fingerprints["semantic"]),
        "unique_causal_fingerprints":len(fingerprints["causal"]), "unique_visual_fingerprints":len(fingerprints["visual"]),
        "unique_family_visual_grammars":len(set(family_visual_signatures.values())),
        "unique_variation_fingerprints":len(variation_fingerprints), "minimum_within_family_variation_distance":3,
        "average_svg_bytes":round(svg_bytes/frame_files,1), "total_svg_bytes":svg_bytes,
        "provider_calls":0, "external_writes":0
    }, indent=2))


if __name__ == "__main__": main()
