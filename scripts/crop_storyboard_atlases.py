#!/usr/bin/env python3
"""Split the two approved 2x3 image-generation atlases into 12 portrait plates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "storyboard-base-plates"
ATLASES = {
    "onboarding": OUT / "atlases" / "onboarding-atlas.png",
    "hotel": OUT / "atlases" / "hotel-atlas.png",
}
GENERATIONS = {
    "onboarding": {
        "generation_record_id": "IMGGEN-20260811-ONBOARDING-ATLAS",
        "prompt": (
            "Create one portrait storyboard base-plate atlas arranged as an exact 2-column by "
            "3-row grid with six equally sized square panels and clean dark gutters. No text, "
            "letters, numbers, logos, watermarks, faces, people, hands, branded interfaces, "
            "screenshots, or recognizable third-party design. Original clean-room editorial "
            "motion-graphics style for an enterprise AI onboarding campaign: deep navy and "
            "midnight blue, cobalt-violet, electric cyan, mint accents, soft glass, subtle "
            "volumetric light, crisp geometric depth, sophisticated high contrast, premium but "
            "restrained. Each panel must be visually distinct and centered with generous negative "
            "space for later editable overlays: panel 1 an evidence compass connecting source, "
            "owner, freshness, and supersession as abstract nodes; panel 2 a search result "
            "transforming into a cited receipt and abstention gate; panel 3 many interruption "
            "signals collapsing into one role-safe context packet; panel 4 a broken decision-history "
            "trail reconstructed into an owned timeline; panel 5 conflicting evidence states "
            "resolving through a red-amber-green claim map conveyed with shapes as well as color; "
            "panel 6 four permission chambers representing read, propose, approve, and execute. "
            "Keep every panel purely abstract and source-free. The whole delivered image should be "
            "a single vertical 2x3 atlas suitable for cropping into six local 9:16 storyboard "
            "background plates."
        ),
        "requested_at": "2026-08-11T12:37:34.870Z",
        "completed_at": "2026-08-11T12:38:31.776Z",
    },
    "hotel": {
        "generation_record_id": "IMGGEN-20260811-HOTEL-ATLAS",
        "prompt": (
            "Create one portrait storyboard base-plate atlas arranged as an exact 2-column by "
            "3-row grid with six equally sized square panels and clean dark gutters. No text, "
            "letters, numbers, logos, watermarks, faces, people, hands, branded interfaces, "
            "screenshots, hotel photographs, or recognizable third-party design. Original "
            "clean-room editorial motion-graphics style for governed hotel revenue operations: "
            "deep ink teal and charcoal, luminous turquoise, restrained warm gold, coral warning "
            "accents, soft glass, subtle volumetric light, crisp geometric depth, premium and "
            "operational rather than flashy. Each panel must be visually distinct and centered with "
            "generous negative space for later editable overlays: panel 1 two abstract gauges "
            "proving public rate/availability is not occupancy; panel 2 a transparent recommendation "
            "path through policy, approval, action receipt, and readback; panel 3 a connector "
            "proof-state matrix progressing from catalog to fixture, config, auth, parse, write, and "
            "readback; panel 4 a stale-data timestamp dial stopped by a source-health gate before "
            "optimization; panel 5 an exception-first control grid with a small number of synthetic "
            "alert classes; panel 6 a human-approval timeline separating advisory AI from autonomous "
            "control through idempotent receipt and rollback. Keep every panel purely abstract, "
            "synthetic, source-free, and free of real prices or property data. The whole delivered "
            "image should be a single vertical 2x3 atlas suitable for cropping into six local 9:16 "
            "storyboard background plates."
        ),
        "requested_at": "2026-08-11T12:38:47.848Z",
        "completed_at": "2026-08-11T12:39:41.313Z",
    },
}
MAPPING = {
    "onboarding": ["V01", "V02", "V03", "V05", "V07", "V08"],
    "hotel": ["V09", "V10", "V11", "V12", "V13", "V15"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def plate(cell: Image.Image) -> Image.Image:
    cell = cell.convert("RGB")
    background = cell.resize((1920, 1920), Image.Resampling.LANCZOS).crop((420, 0, 1500, 1920))
    background = background.filter(ImageFilter.GaussianBlur(34)).convert("RGBA")
    veil = Image.new("RGBA", (1080, 1920), (3, 10, 20, 70))
    background.alpha_composite(veil)
    foreground = cell.resize((1000, 1000), Image.Resampling.LANCZOS).convert("RGBA")
    background.alpha_composite(foreground, (40, 460))
    shade = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shade)
    for y in range(390):
        alpha = round(175 * (1 - y / 390))
        draw.line((0, y, 1080, y), fill=(3, 8, 17, alpha))
    for offset in range(390):
        y = 1919 - offset
        alpha = round(190 * (1 - offset / 390))
        draw.line((0, y, 1080, y), fill=(3, 8, 17, alpha))
    background.alpha_composite(shade)
    return background.convert("RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for pillar, atlas_path in ATLASES.items():
        generation = GENERATIONS[pillar]
        atlas = Image.open(atlas_path).convert("RGB")
        if atlas.size != (1024, 1536):
            raise ValueError(f"Unexpected atlas geometry for {atlas_path}: {atlas.size}")
        for index, video_id in enumerate(MAPPING[pillar]):
            row, col = divmod(index, 2)
            cell = atlas.crop((col * 512, row * 512, (col + 1) * 512, (row + 1) * 512))
            output = OUT / f"{video_id}.png"
            plate(cell).save(output, format="PNG", optimize=True)
            records.append({
                "video_id": video_id,
                "pillar": pillar,
                "atlas_path": atlas_path.relative_to(ROOT).as_posix(),
                "atlas_sha256": sha256(atlas_path),
                "panel_index": index + 1,
                "crop_box": [col * 512, row * 512, (col + 1) * 512, (row + 1) * 512],
                "output_path": output.relative_to(ROOT).as_posix(),
                "output_sha256": sha256(output),
                "dimensions": [1080, 1920],
                "generation_record_id": generation["generation_record_id"],
                "generation_route": "Codex imagegen clean-room atlas followed by deterministic local crop/composite",
                "references_used": [],
                "source_reuse": "none",
                "rights_state": "original_local_storyboard_asset",
            })
    manifest = {
        "schema": "content-engine.storyboard-base-plate-manifest.v1",
        "run_id": "20260811-phase1-content-batch",
        "candidate_set_hash": "sha256:7519764ef9d7d296e25613d1ce9a8e79fa5d8aa109636769ac9f732eafe22be4",
        "asset_count": len(records),
        "storyboard_asset_state": "LOCAL_CODEX_EXECUTED",
        "external_provider_generation_state": "NOT_RUN",
        "prompt_boundary": "Source-free abstract 2x3 atlases; no reference images, text, logo, real person, likeness, voice, private data, branded UI, or third-party composition.",
        "generation_records": [
            {
                "generation_record_id": generation["generation_record_id"],
                "pillar": pillar,
                "prompt": generation["prompt"],
                "prompt_sha256": sha256_text(generation["prompt"]),
                "references_used": [],
                "tool_route": "Codex internal image_gen.imagegen",
                "model_name": "gpt-image",
                "model_version": "2.0 (C2PA softwareAgent)",
                "requested_at": generation["requested_at"],
                "completed_at": generation["completed_at"],
                "output_path": ATLASES[pillar].relative_to(ROOT).as_posix(),
                "output_sha256": sha256(ATLASES[pillar]),
                "maker": "root_integrator",
                "reviewer": "Sight",
                "review_result": "PENDING_INDEPENDENT_PREVISUALIZATION_REVIEW",
                "review_result_path": "runs/20260811-phase1-content-batch/independent-previsualization-review.md",
                "rights_state": "original_local_storyboard_asset",
            }
            for pillar, generation in GENERATIONS.items()
        ],
        "records": records,
    }
    manifest_path = OUT / "base-plate-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"plates": len(records), "manifest": str(manifest_path), "manifest_sha256": sha256(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()
