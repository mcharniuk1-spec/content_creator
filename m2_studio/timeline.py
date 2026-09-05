"""ScriptCard to deterministic Remotion EDL; asset binding is a separate gate."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import struct

from .media import StudioError, digest, object_hash, safe_id, safe_path


def alignment_plan_hash(edl: dict) -> str:
    """Canonical review scope shared with Remotion's alignmentPlanHash.

    Gain uses IEEE-754 bytes so Python/JS decimal formatting cannot change the digest.
    The receipt itself is excluded: only the exact plan being approved is hashed.
    """
    stems = edl.get("audio_stems", [])
    used = {s["asset_id"] for s in stems}
    plan = {"schema": "m2.speech-alignment-plan.v1", "source_card_hash": edl.get("source_card_hash"),
            "fps": edl["fps"], "duration_frames": edl["duration_frames"], "speech_policy": edl.get("speech_policy"),
            "audio_asset_hashes": {a["asset_id"]: a["sha256"] for a in edl.get("assets", []) if a["asset_id"] in used},
            "audio_stems": [{"asset_id": s["asset_id"], "role": s["role"], "from_frame": s["from_frame"],
                             "duration_frames": s["duration_frames"], "trim_before_frames": s.get("trim_before_frames", 0),
                             "volume_float64_hex": struct.pack(">d", float(s.get("volume", 1))).hex()} for s in stems],
            "captions": [{"from_frame": c["from_frame"], "duration_frames": c["duration_frames"], "text": c["text"]} for c in edl.get("captions", [])]}
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def validate_edl(edl: dict, *, asset_root: Path | None = None, production=False) -> None:
    if edl.get("schema") != "m2.remotion-edl.v1":
        raise StudioError("INVALID_EDL_SCHEMA")
    fps = edl.get("fps")
    if fps not in {24, 25, 30, 50, 60} or type(edl.get("duration_frames")) is not int or not 1 <= edl["duration_frames"] <= fps * 600:
        raise StudioError("INVALID_EDL_TIMEBASE")
    if edl.get("width") not in {540, 1080, 1920} or edl.get("height") not in {960, 1080, 1920}:
        raise StudioError("INVALID_EDL_RESOLUTION")
    if edl.get("render_mode") not in {"PREVIS", "PRODUCTION"}:
        raise StudioError("INVALID_RENDER_MODE")
    if production and (edl.get("review_state") != "APPROVED" or edl.get("render_mode") != "PRODUCTION"):
        raise StudioError("EDIT_NOT_APPROVED")
    assets = edl.get("assets", [])
    asset_map = {a["asset_id"]: a for a in assets}
    if len(asset_map) != len(assets):
        raise StudioError("DUPLICATE_ASSET_ID")
    for asset in assets:
        safe_id(asset["asset_id"])
        if asset["kind"] not in {"video", "image", "audio"}:
            raise StudioError("UNSUPPORTED_ASSET_KIND")
        if asset.get("rights_approved") is not True or not asset.get("rights_receipt_id"):
            raise StudioError("ASSET_RIGHTS_MISSING")
        if asset_root is None:
            # Validate relative URL-free shape even when not checking files yet.
            safe_path(Path("."), asset["path"], must_exist=False)
        else:
            path = safe_path(asset_root, asset["path"])
            if digest(path) != asset.get("sha256"):
                raise StudioError("ASSET_HASH_MISMATCH")
        if len(asset.get("sha256", "")) != 64 or any(c not in "0123456789abcdef" for c in asset.get("sha256", "")):
            raise StudioError("ASSET_HASH_MISSING")
        if Path(asset["path"]).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".m4v", ".mp3", ".wav", ".aac", ".m4a"}:
            raise StudioError("UNSUPPORTED_ASSET_EXTENSION")
    previous = 0
    scene_ids = set()
    for scene in edl.get("scenes", []):
        sid = safe_id(scene["scene_id"])
        a, b = scene["from_frame"], scene["duration_frames"]
        if sid in scene_ids or type(a) is not int or type(b) is not int or a != previous or b <= 0:
            raise StudioError("EDL_PARTITION_INVALID")
        scene_ids.add(sid)
        previous = a + b
        if scene["layout"] not in {"a_roll", "split_screen", "demo", "motion_graphic"}:
            raise StudioError("UNSUPPORTED_LAYOUT")
        if not .2 <= scene.get("split_ratio", .58) <= .8:
            raise StudioError("SPLIT_RATIO_OUTSIDE_RANGE")
        if not scene.get("layers"):
            raise StudioError("EMPTY_SCENE")
        for layer in scene["layers"]:
            if layer["kind"] not in {"video", "image", "text", "placeholder", "graphic"}:
                raise StudioError("UNSUPPORTED_LAYER")
            if layer.get("panel", "full") not in {"full", "top", "bottom", "left", "right", "pip"}:
                raise StudioError("UNSUPPORTED_PANEL")
            if layer["kind"] in {"video", "image"}:
                asset = asset_map.get(layer.get("asset_id"))
                if not asset or asset["kind"] != layer["kind"]:
                    raise StudioError("LAYER_ASSET_UNRESOLVED")
                if layer["kind"] == "video":
                    trim = layer.get("trim_before_frames", 0)
                    if type(trim) is not int or trim < 0 or trim + b > asset.get("duration_frames", 0):
                        raise StudioError("VIDEO_TRIM_EXCEEDS_ASSET")
            if production and layer["kind"] == "placeholder":
                raise StudioError("SHOOT_OR_ASSET_PENDING")
            if production and layer["kind"] == "graphic":
                raise StudioError("UNBUILT_GRAPHIC_PLAN")
    if previous != edl["duration_frames"]:
        raise StudioError("EDL_COVERAGE_INCOMPLETE")
    if production and edl.get("pending_audio_assets"):
        raise StudioError("AUDIO_RECORDING_OR_PLACEMENT_PENDING")
    for caption in edl.get("captions", []):
        if type(caption["from_frame"]) is not int or type(caption["duration_frames"]) is not int or not 0 <= caption["from_frame"] < caption["from_frame"] + caption["duration_frames"] <= previous or not caption.get("text", "").strip():
            raise StudioError("CAPTION_OUTSIDE_TIMELINE")
    for stem in edl.get("audio_stems", []):
        asset = asset_map.get(stem.get("asset_id"))
        if not asset or asset["kind"] != "audio" or stem.get("role") not in {"speech", "music", "ambience", "sfx"}:
            raise StudioError("AUDIO_ASSET_UNRESOLVED")
        a, b = stem.get("from_frame"), stem.get("duration_frames")
        trim = stem.get("trim_before_frames", 0)
        if type(a) is not int or type(b) is not int or type(trim) is not int or trim < 0 or not 0 <= a < a + b <= previous or trim + b > asset.get("duration_frames", 0):
            raise StudioError("AUDIO_OUTSIDE_TIMELINE")
        if not 0 <= stem.get("volume", 1) <= 1:
            raise StudioError("AUDIO_GAIN_OUTSIDE_RANGE")
    if production:
        policy = edl.get("speech_policy")
        if policy not in {"REQUIRED_RECORDED_SPEECH", "NO_SPEECH"}:
            raise StudioError("SPEECH_POLICY_REQUIRED")
        speech_ids = sorted({s["asset_id"] for s in edl.get("audio_stems", []) if s["role"] == "speech"})
        if policy == "REQUIRED_RECORDED_SPEECH":
            if not speech_ids:
                raise StudioError("RECORDED_SPEECH_STEM_REQUIRED")
            alignment = edl.get("speech_alignment", {})
            expected_hashes = {aid: asset_map[aid]["sha256"] for aid in speech_ids}
            if (alignment.get("review_state") != "APPROVED" or not alignment.get("receipt_id")
                    or not edl.get("source_card_hash") or alignment.get("source_card_hash") != edl["source_card_hash"]
                    or alignment.get("audio_asset_hashes") != expected_hashes
                    or alignment.get("alignment_plan_sha256") != alignment_plan_hash(edl)):
                raise StudioError("RECORDED_SPEECH_ALIGNMENT_REQUIRED")


def build_card_edl(card: dict, asset_bindings: dict | None = None, *, speech_alignment: dict | None = None) -> dict:
    bindings = asset_bindings or {}
    fps = card.get("fps", 30)
    scenes = []
    assets = []
    definitions = {a["asset_id"]: a for a in card.get("assets", [])}
    stems = []
    for key, value in sorted(bindings.items()):
        assets.append({"asset_id": key, **{k: v for k, v in value.items() if k != "stem"}})
        if value.get("kind") == "audio" and isinstance(value.get("stem"), dict):
            stems.append({**value["stem"], "asset_id": key})
    for i, shot in enumerate(card["shots"]):
        start, end = round(shot["start_ms"] * fps / 1000), round(shot["end_ms"] * fps / 1000)
        mode = str(shot.get("mode", "")).lower()
        layout = "split_screen" if "split" in mode else "a_roll" if "a_roll" in mode or "creator" in mode else "demo" if "demo" in mode or "screen" in mode else "motion_graphic"
        layers = []
        visual_ids = [aid for aid in shot.get("asset_ids", []) if bindings.get(aid, definitions.get(aid, {})).get("kind") != "audio"]
        panel_map = {p["asset_id"]: p["panel"] for p in shot.get("panel_map", [])}
        for j, aid in enumerate(visual_ids):
            definition = definitions.get(aid, {})
            default_panel = "top" if layout == "split_screen" and (definition.get("kind") == "graphic" or "demo" in aid.lower()) else "bottom" if layout == "split_screen" and definition.get("production_route") == "owner_recording" else "top" if layout == "split_screen" and j == 0 else "bottom" if layout == "split_screen" else "full"
            panel = panel_map.get(aid, default_panel)
            if aid in bindings and bindings[aid]["kind"] != "audio":
                layers.append({"kind": bindings[aid]["kind"], "asset_id": aid, "panel": panel,
                               "trim_before_frames": bindings[aid].get("trim_before_frames", 0), "muted": True})
            elif aid not in bindings and definition.get("kind") == "graphic":
                layers.append({"kind": "graphic", "text": str(shot.get("visual", definition.get("purpose", ""))), "panel": panel})
            elif aid not in bindings:
                layers.append({"kind": "placeholder", "text": f"Awaiting asset: {aid}", "panel": panel})
        if not layers:
            layers = [{"kind": "graphic", "text": str(shot.get("visual", "")), "panel": "full"}]
        text = shot.get("on_screen_text", "")
        if isinstance(text, list):
            text = "\n".join(text)
        if text:
            layers.append({"kind": "text", "text": str(text), "panel": "full"})
        scenes.append({"scene_id": safe_id(str(shot.get("shot_id", f"shot-{i + 1:02}"))), "from_frame": start,
                       "duration_frames": end - start, "layout": layout, "split_ratio": shot.get("split_ratio", .58), "layers": layers})
    captions = [{"from_frame": round(s["start_ms"] * fps / 1000), "duration_frames": round(s["end_ms"] * fps / 1000) - round(s["start_ms"] * fps / 1000), "text": s["spoken_text"]} for s in card["segments"] if s.get("spoken_text")]
    result = {"schema": "m2.remotion-edl.v1", "card_id": card["card_id"], "title": card["title"],
              "fps": fps, "width": 1080, "height": 1920, "duration_frames": round(card["duration_seconds"] * fps),
              "source_card_hash": object_hash(card), "scenes": scenes, "assets": assets, "captions": captions,
              "audio_stems": stems,
              "pending_audio_assets": sorted({a["asset_id"] for a in card.get("assets", []) if a.get("kind") == "audio" and not isinstance(bindings.get(a["asset_id"], {}).get("stem"), dict)}
                                             | {aid for aid, a in bindings.items() if a.get("kind") == "audio" and not isinstance(a.get("stem"), dict)}),
              "speech_policy": "REQUIRED_RECORDED_SPEECH" if captions else "NO_SPEECH",
              "speech_alignment": speech_alignment or {"review_state": "NOT_REVIEWED", "receipt_id": None},
              "render_mode": "PREVIS", "review_state": "REVIEW_PENDING", "provider_execution": False}
    validate_edl(result)
    return result
