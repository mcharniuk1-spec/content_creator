#!/usr/bin/env python3
"""Derive lightweight 9:16 review frames and receipts from generated sheets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import mean

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "studio/story-framework-library/v3-realistic"
TARGET = (540, 960)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fitted_frame(cell: Image.Image) -> Image.Image:
    cell = cell.convert("RGB")
    bg = ImageOps.fit(cell, TARGET, method=Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(22))
    bg = ImageEnhance.Brightness(bg).enhance(0.56)
    fg = ImageOps.contain(cell, (TARGET[0], 820), method=Image.Resampling.LANCZOS)
    canvas = bg.copy()
    canvas.paste(fg, ((TARGET[0] - fg.width) // 2, (TARGET[1] - fg.height) // 2))
    return canvas


def main() -> None:
    records = json.loads((LIB / "generation-plan.json").read_text())["records"]
    manifest = []
    for record in records:
        folder = LIB / record["path"]
        sheet_path = folder / "contact-sheet-generated.png"
        if not sheet_path.exists():
            raise SystemExit(f"missing {sheet_path}")
        sheet = Image.open(sheet_path).convert("RGB")
        sw, sh = sheet.size
        frames_dir = folder / "frames"
        frames_dir.mkdir(exist_ok=True)
        frame_rows = []
        thumbs = []
        for idx in range(6):
            col, row = idx % 2, idx // 2
            x0, x1 = round(col * sw / 2), round((col + 1) * sw / 2)
            y0, y1 = round(row * sh / 3), round((row + 1) * sh / 3)
            pad = max(2, round(min(sw, sh) * 0.003))
            cell = sheet.crop((x0 + pad, y0 + pad, x1 - pad, y1 - pad))
            frame = fitted_frame(cell)
            frame_id = f"{record['story_id']}-F{idx + 1:02d}"
            out = frames_dir / f"{frame_id}.png"
            frame.save(out, "PNG", optimize=True, compress_level=9)
            stat = ImageStat.Stat(cell.convert("L"))
            frame_rows.append({
                "frame_id": frame_id,
                "file": f"frames/{out.name}",
                "sha256": sha256(out),
                "dimensions": list(TARGET),
                "luma_mean": round(stat.mean[0], 2),
                "luma_stddev": round(stat.stddev[0], 2),
                "heuristic_blank_risk": stat.stddev[0] < 12,
            })
            thumbs.append(frame.resize((270, 480), Image.Resampling.LANCZOS))
        review = Image.new("RGB", (810, 960), "#17191c")
        for idx, thumb in enumerate(thumbs):
            review.paste(thumb, ((idx % 3) * 270, (idx // 3) * 480))
        review_path = folder / "contact-sheet-final.png"
        review.save(review_path, "PNG", optimize=True, compress_level=9)
        generation_path = folder / "generation.json"
        generation = json.loads(generation_path.read_text())
        generation.update({
            "output_state": "GENERATED_CONTACT_SHEET_AND_DERIVED_FRAMES",
            "generation_date": "2026-08-26",
            "provider_model_version": "NOT_REPORTED_BY_BUILTIN_TOOL",
            "source_sheet_sha256": sha256(sheet_path),
            "review_sheet": "contact-sheet-final.png",
            "review_sheet_sha256": sha256(review_path),
            "frame_receipts": frame_rows,
            "qa_scope": "mechanical_and_heuristic_only; human_visual_review_required",
        })
        generation_path.write_text(json.dumps(generation, indent=2) + "\n")
        manifest.append({
            "story_id": record["story_id"],
            "path": record["path"],
            "source_sheet_sha256": generation["source_sheet_sha256"],
            "review_sheet_sha256": generation["review_sheet_sha256"],
            "frames": frame_rows,
        })
    receipt = {
        "schema": "content-engine.realistic-frame-manifest.v1",
        "generated_at": "2026-08-26",
        "story_count": len(manifest),
        "frame_count": sum(len(x["frames"]) for x in manifest),
        "dimensions": list(TARGET),
        "source_frame_evidence": "NONE_DB_FRAME_COUNT_ZERO",
        "interpretation_boundary": "fictional clean-room previsualizations, not observed-source reconstructions",
        "blank_risk_count": sum(f["heuristic_blank_risk"] for x in manifest for f in x["frames"]),
        "mean_luma_stddev": round(mean(f["luma_stddev"] for x in manifest for f in x["frames"]), 2),
        "stories": manifest,
    }
    (LIB / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("story_count", "frame_count", "blank_risk_count", "mean_luma_stddev")}))


if __name__ == "__main__":
    main()
