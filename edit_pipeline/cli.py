"""Command-line entry points for the local hybrid editing pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import (
    analyze_video,
    build_edl,
    build_fixture_case,
    export_otio,
    render_edl,
    validate_edl,
    write_json,
)


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m edit_pipeline.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze_cmd = sub.add_parser("analyze", help="probe media and create Codex-review candidates")
    analyze_cmd.add_argument("input")
    analyze_cmd.add_argument("output")
    analyze_cmd.add_argument("--segment-seconds", type=float, default=3.0)
    plan_cmd = sub.add_parser("plan", help="convert Codex-selected analysis candidates into an EDL")
    plan_cmd.add_argument("--case", required=True)
    plan_cmd.add_argument("--analysis", required=True)
    plan_cmd.add_argument("--output", required=True)
    plan_cmd.add_argument("--select", required=True, help="comma-separated candidate IDs in timeline order")
    plan_cmd.add_argument("--captions", help="JSON array of {start,end,text} cues")
    plan_cmd.add_argument("--width", type=int)
    plan_cmd.add_argument("--height", type=int)
    plan_cmd.add_argument("--color", default="neutral", choices=["none", "neutral", "warm", "cool"])
    plan_cmd.add_argument("--audio", default="loudnorm", choices=["none", "loudnorm", "dynaudnorm"])
    fixture_cmd = sub.add_parser("fixture", help="create and render the synthetic safe fixture")
    fixture_cmd.add_argument("run_dir")
    render_cmd = sub.add_parser("render", help="render a validated EDL")
    render_cmd.add_argument("edl")
    render_cmd.add_argument("output")
    render_cmd.add_argument("--case", required=True, help="rights/path/policy case JSON (required)")
    otio_cmd = sub.add_parser("otio", help="export OTIO if installed")
    otio_cmd.add_argument("edl")
    otio_cmd.add_argument("output")
    validate_cmd = sub.add_parser("validate", help="validate an EDL")
    validate_cmd.add_argument("edl")
    args = parser.parse_args(argv)
    if args.command == "analyze":
        write_json(args.output, analyze_video(args.input, segment_seconds=args.segment_seconds))
        return 0
    if args.command == "plan":
        case = _load(args.case)
        analysis = _load(args.analysis)
        selected_ids = [item.strip() for item in args.select.split(",") if item.strip()]
        candidates = {str(item.get("id")): item for item in analysis.get("candidates") or []}
        missing = [item for item in selected_ids if item not in candidates]
        if missing:
            parser.error(f"analysis candidates not found: {', '.join(missing)}")
        captions = _load(args.captions) if args.captions else []
        edl = build_edl(
            case=case,
            source_probe=analysis["source"],
            selections=[candidates[item] for item in selected_ids],
            captions=captions,
            width=args.width,
            height=args.height,
            color_preset=args.color,
            audio_leveling=args.audio,
        )
        write_json(args.output, edl)
        print(f"EDL: PASS ({len(selected_ids)} selected candidates)")
        return 0
    if args.command == "validate":
        validate_edl(_load(args.edl))
        print("EDL: PASS")
        return 0
    if args.command == "render":
        edl = _load(args.edl)
        result = render_edl(edl, args.output, case=_load(args.case))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "otio":
        result = export_otio(_load(args.edl), args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "fixture":
        root = Path(args.run_dir).expanduser().resolve()
        result = build_fixture_case(root)
        write_json(root / "case.json", result["case"])
        write_json(root / "probe.json", result["probe"])
        write_json(root / "analysis.json", result["analysis"])
        write_json(root / "edit-decision-list.json", result["edl"])
        render = render_edl(result["edl"], root / "fixture-render.mp4", case=result["case"])
        otio = export_otio(result["edl"], root / "fixture-timeline.otio")
        write_json(root / "fixture-run.json", {"render": render, "otio": otio, "provider_execution": False})
        print(json.dumps({"render": render, "otio": otio}, indent=2, sort_keys=True))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
