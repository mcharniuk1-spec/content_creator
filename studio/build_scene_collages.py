#!/usr/bin/env python3
"""Build one readable collage per scene-unit from a scene segmentation manifest.

The script only reads the manifest's run-local screenshot pointers and writes
derived review collages. It never downloads media or changes source evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def collage(scene: dict, base: Path, out: Path) -> dict:
    samples = scene["sampled_frames"]
    if len(samples) not in (2, 4, 6):
        raise ValueError(f"{scene['scene_id']}: sample count must be 2, 4, or 6")
    images = []
    for sample in samples:
        source = base / sample["source_pointer"]
        if not source.exists():
            raise FileNotFoundError(source)
        images.append(Image.open(source).convert("RGB"))
    thumb_w, thumb_h = 360, 640
    cols = 2 if len(images) <= 4 else 3
    rows = (len(images) + cols - 1) // cols
    gutter, label_h = 18, 44
    canvas = Image.new("RGB", (cols * thumb_w + (cols + 1) * gutter, rows * (thumb_h + label_h) + (rows + 1) * gutter), "#17191c")
    draw = ImageDraw.Draw(canvas)
    for i, (image, sample) in enumerate(zip(images, samples)):
        x = gutter + (i % cols) * (thumb_w + gutter)
        y = gutter + (i // cols) * (thumb_h + label_h + gutter)
        thumb = ImageOps.fit(image, (thumb_w, thumb_h), method=Image.Resampling.LANCZOS)
        canvas.paste(thumb, (x, y))
        label = f"{sample.get('role', 'sample')} · {sample['timestamp_ms']} ms"
        draw.text((x, y + thumb_h + 10), label, fill="#f4f4f4")
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "JPEG", quality=86, optimize=True, progressive=True)
    return {"path": out.as_posix(), "sha256": digest(out), "sample_count": len(images), "layout": f"{len(images)}-up"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path, help="video-scene-segmentation JSON")
    parser.add_argument("--base", type=Path, default=None, help="base directory for source_pointer paths")
    parser.add_argument("--output", type=Path, required=True, help="collage output directory")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text())
    base = args.base or args.manifest.parent
    receipts = []
    for scene in data["scene_units"]:
        path = args.output / f"{scene['scene_id']}.jpg"
        receipts.append({"scene_id": scene["scene_id"], **collage(scene, base, path)})
    contact = args.output / "VIDEO-CONTACT-SHEET.json"
    contact.write_text(json.dumps({"schema": "content-engine.scene-collage-receipt.v1", "source_analysis_id": data["analysis_id"], "scene_collages": receipts}, indent=2) + "\n")
    print(json.dumps({"scenes": len(receipts), "output": args.output.as_posix()}))


if __name__ == "__main__":
    main()
