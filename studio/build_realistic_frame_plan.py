#!/usr/bin/env python3
"""Build clean-room six-panel image-generation plans for Studio v2 stories."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "studio" / "story-framework-library" / "v2"
OUTPUT = ROOT / "studio" / "story-framework-library" / "v3-realistic"

CAST = [
    "adult operations professional in their early 30s, short dark hair, teal overshirt over a cream tee",
    "adult product manager in their late 30s, natural wavy brown hair, muted navy knit and stone trousers",
    "adult research analyst in their early 40s, close-cropped black hair, olive work shirt and charcoal trousers",
    "adult technical educator in their mid 30s, shoulder-length dark hair, rust cardigan over a plain white top",
    "adult workflow coordinator in their late 40s, short salt-and-pepper hair, soft blue shirt and dark jeans",
    "adult evidence reviewer in their early 30s, natural curly hair, sand overshirt and black tee",
    "adult systems operator in their mid 40s, cropped auburn hair, charcoal sweater and neutral trousers",
    "adult content strategist in their late 30s, straight dark bob, moss-green blouse and black trousers",
    "adult project lead in their early 50s, short gray hair, cream knit and navy work jacket",
    "adult data steward in their mid 30s, natural coiled hair, slate shirt and warm-gray trousers",
]

LOCATIONS = [
    "modest home-office project room with a cork decision board, wood desk, window and warm practical lamp",
    "small shared studio with a standing desk, paper planning wall, shelf and soft daylight",
    "quiet meeting room with an unbranded whiteboard, task cards, simple table and window light",
    "believable operations workspace with a pinboard, notebook, laptop with blank screen and practical lamp",
    "compact workshop-office with shelves, work table, paper cards and neutral walls",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def prompt_for(story: dict, cast: str, location: str) -> str:
    frames = story["frames"]
    continuity = story["continuity_bible"]
    narrative = story["narrative"]
    panels = []
    for frame in frames:
        panels.append(
            f"{frame['sequence_number']} {frame['shot_scale']} still: {frame['hero_action']}; "
            f"show {frame['visual_state']} Emotional register: {frame['emotion']}."
        )
    return "\n".join([
        "Use case: photorealistic-natural",
        f"Asset type: six-panel vertical social-video storyboard reference for {story['story_id']} {story['title']}",
        "Primary request: create ONE polished contact-sheet image containing exactly six clearly separated sequential photorealistic frames of the same fictional adult in the same environment. It should feel like candid frames captured from a real phone-shot Instagram Reel or YouTube Short while remaining an original clean-room scene.",
        f"Subject continuity: fictional non-identifiable {cast}. Ordinary natural face, realistic skin texture, restrained expression; same person, hair and wardrobe in all six panels.",
        f"Scene continuity: {location}. Same environment, props, time of day and left-to-right screen direction across all panels.",
        f"Persistent target: {continuity['target_prop']}. Trigger prop: {continuity['trigger_prop']}. Proof prop: {continuity['proof_prop']}. Obstacle: {narrative['obstacle']}.",
        "Six panels in reading order:",
        *panels,
        f"Final panel truth boundary: visually preserve room for a later editable limitation overlay meaning '{narrative['limitation']}', but render no words.",
        "Style/medium: realistic phone-native documentary/editorial frame capture, vertical social video, modest sharpening, slight shadow noise, natural highlight rolloff, subtle handheld imperfection, no cinematic LUT and no beauty retouching.",
        "Composition: contact sheet with six equal portrait-oriented cells in a 2-column by 3-row grid with clean neutral gutters. No titles or captions inside cells. Keep the face, hands, persistent target, trigger, obstacle and proof visible and internally consistent.",
        "Lighting/mood: motivated soft window light plus a believable practical source; natural mixed light; emotional progression from recognition/concern to agency and cautious relief.",
        "Constraints: exactly six panels; same fictional adult, wardrobe, environment and prop identities; realistic hands/anatomy; blank or abstract paper/screen surfaces for later editable overlays; no generated text; no logos; no watermark; no platform UI.",
        "Avoid: celebrity or creator likeness, distinctive source composition, influencer reaction face, branded office or software UI, luxury styling, neon tech lighting, cinematic anamorphic effects, plastic skin, warped hands, extra fingers, duplicated/missing props, identity drift, wardrobe changes, impossible reflections, fake metrics, testimonial imagery, unsupported success symbolism, copied creator caption or CTA.",
    ])


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    source_manifest = read_json(SOURCE / "library-manifest.json")
    records = []
    for index, record in enumerate(source_manifest["records"]):
        source_dir = SOURCE / record["path"]
        story = read_json(source_dir / "story.json")
        package = OUTPUT / record["path"]
        package.mkdir()
        cast = CAST[index % len(CAST)]
        location = LOCATIONS[(index // len(CAST) + index) % len(LOCATIONS)]
        prompt = prompt_for(story, cast, location)
        generation = {
            "schema": "content-engine.realistic-storyboard-generation.v1",
            "story_id": story["story_id"],
            "title": story["title"],
            "source_story": f"../v2/{record['path']}/story.json",
            "output_state": "PROMPT_READY_IMAGE_NOT_RUN",
            "provider_route": "codex_builtin_imagegen",
            "reference_images": [],
            "reference_evidence_state": "NO_SOURCE_FRAMES_AVAILABLE",
            "rights_state": "original_fictional_clean_room_previsualization",
            "likeness_state": "fictional_non_identifiable_adult",
            "cast_lock": cast,
            "location_lock": location,
            "prompt": prompt,
            "contact_sheet": "contact-sheet-generated.png",
            "frames": [f"frames/{frame['frame_id']}.png" for frame in story["frames"]],
        }
        (package / "generation.json").write_text(json.dumps(generation, indent=2) + "\n", encoding="utf-8")
        (package / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
        (package / "source-story.json").write_text(json.dumps(story, indent=2) + "\n", encoding="utf-8")
        records.append({
            "story_id": story["story_id"], "title": story["title"], "path": record["path"],
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "state": "PROMPT_READY_IMAGE_NOT_RUN",
        })
    manifest = {
        "schema": "content-engine.realistic-storyboard-library.v1",
        "source_library": "studio/story-framework-library/v2",
        "story_count": 50,
        "planned_frame_count": 300,
        "generation_strategy": "one six-panel clean-room contact sheet per story, then deterministic 9:16 review crops",
        "source_frame_evidence": "NONE_DB_FRAME_COUNT_ZERO",
        "records": records,
    }
    (OUTPUT / "generation-plan.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "stories": len(records), "output": str(OUTPUT.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
