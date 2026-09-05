"""Independently executable local states; no implicit acquisition or generation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .media import StudioError, align_scenes, attempt, cut_candidates, extract_scenes, inventory, safe_id, transcribe_local, write_json
from .timeline import build_card_edl, validate_edl


def load(path):
    return json.loads(Path(path).read_text())


def process_media_map(root: Path, media_map: dict, output: Path, *, model_path: Path | None = None) -> dict:
    """One attempt per corpus code, including absent media. Inputs are allowlisted.

    Map has expected_codes and entries [{code,media_id,path,sha256,source_kind,rights}].
    Entries may cover a subset; a missing code never triggers a network request.
    """
    expected = media_map["expected_codes"]
    if len(expected) != len(set(expected)) or any(not isinstance(c, str) or not c for c in expected):
        raise StudioError("INVALID_CORPUS_CODES")
    entries = media_map.get("entries", [])
    mapping = {e["code"]: e for e in entries}
    if len(mapping) != len(entries) or not set(mapping) <= set(expected):
        raise StudioError("MEDIA_MAP_CORPUS_MISMATCH")
    observed = {r["media_id"]: r for r in inventory(root, entries)}
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, code in enumerate(expected):
        entry = mapping.get(code)
        media = observed[entry["media_id"]] if entry else attempt("media", "UNAVAILABLE", failure_code="LOCAL_MEDIA_NOT_SUPPLIED")
        row = {"code": code, "media": media, "transcript": attempt("transcript", "UNAVAILABLE", failure_code="LOCAL_MEDIA_NOT_SUPPLIED"),
               "cuts": attempt("cuts", "UNAVAILABLE", failure_code="LOCAL_MEDIA_NOT_SUPPLIED"),
               "frames": attempt("frames", "NOT_ATTEMPTED", failure_code="SEMANTIC_ANNOTATION_REQUIRED"),
               "scenes": attempt("scenes", "NOT_ATTEMPTED", failure_code="SEMANTIC_ANNOTATION_REQUIRED")}
        if media["observation_state"] == "OBSERVED":
            row["cuts"] = cut_candidates(root, media)
            row["transcript"] = transcribe_local(root, media, model_path, output / f"attempt-{index + 1:05}") if model_path else attempt("transcript", "NOT_ATTEMPTED", failure_code="LOCAL_ASR_MODEL_NOT_SELECTED")
        elif entry:
            for modality in ("transcript", "cuts", "frames", "scenes"):
                row[modality] = attempt(modality, "RIGHTS_BLOCKED" if media["observation_state"] == "RIGHTS_BLOCKED" else "UNAVAILABLE", failure_code=media["failure_code"])
        rows.append(row)
    result = {"schema": "m2.signal-media-attempt-export.v1", "run_id": media_map["run_id"], "corpus_count": len(expected),
              "local_media_observed": sum(r["media"]["observation_state"] == "OBSERVED" for r in rows),
              "transcript_observed": sum(r["transcript"]["observation_state"] == "OBSERVED" for r in rows),
              "scene_reviewed": 0, "provider_execution": False, "hikerapi_execution": False, "rows": rows}
    write_json(output / "media-attempts.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("inventory")
    p.add_argument("--root", type=Path, required=True); p.add_argument("--map", required=True); p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser("media-map")
    p.add_argument("--root", type=Path, required=True); p.add_argument("--map", required=True); p.add_argument("--output", type=Path, required=True); p.add_argument("--model", type=Path)
    p = commands.add_parser("transcribe")
    p.add_argument("--root", type=Path, required=True); p.add_argument("--media", required=True); p.add_argument("--model", type=Path, required=True); p.add_argument("--output", type=Path, required=True); p.add_argument("--language")
    p = commands.add_parser("cuts")
    p.add_argument("--root", type=Path, required=True); p.add_argument("--media", required=True); p.add_argument("--output", type=Path, required=True); p.add_argument("--threshold", type=float, default=.32)
    p = commands.add_parser("scenes")
    p.add_argument("--root", type=Path, required=True); p.add_argument("--media", required=True); p.add_argument("--transcript", required=True); p.add_argument("--annotations", required=True); p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser("card-edl")
    p.add_argument("--card", required=True); p.add_argument("--bindings"); p.add_argument("--alignment"); p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser("validate-edl")
    p.add_argument("--edl", required=True); p.add_argument("--assets", type=Path); p.add_argument("--production", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "inventory":
            result = inventory(args.root, load(args.map)["entries"]); write_json(args.output, result)
        elif args.command == "media-map":
            result = process_media_map(args.root, load(args.map), args.output, model_path=args.model)
            print(json.dumps({k: v for k, v in result.items() if k != "rows"})); return
        elif args.command == "transcribe":
            result = transcribe_local(args.root, load(args.media), args.model, args.output, language=args.language); write_json(args.output / "transcript.json", result)
        elif args.command == "cuts":
            result = cut_candidates(args.root, load(args.media), threshold=args.threshold); write_json(args.output, result)
        elif args.command == "scenes":
            media = load(args.media)
            transcript = load(args.transcript)
            scenes = align_scenes(load(args.annotations), transcript, media["duration_ms"], source_media_hash=media["sha256"])
            result = extract_scenes(args.root, media, scenes, args.output, transcript=transcript); write_json(args.output / "scene-evidence.json", result)
        elif args.command == "card-edl":
            result = build_card_edl(load(args.card), load(args.bindings) if args.bindings else None, speech_alignment=load(args.alignment) if args.alignment else None); write_json(args.output, result)
        else:
            validate_edl(load(args.edl), asset_root=args.assets, production=args.production); result = {"status": "PASS"}
        print(json.dumps({"status": "RECORDED", "command": args.command}))
    except (StudioError, KeyError, ValueError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "failure_code": str(exc) if isinstance(exc, StudioError) else "INVALID_LOCAL_INPUT"}))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
