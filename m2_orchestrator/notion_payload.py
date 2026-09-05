"""Build a private, versioned Notion projection from explicit release artifacts.

This module performs no network writes. Keep its output outside Git: public
creator identifiers and snapshot data are run evidence, not evergreen memory.
"""
import json
from pathlib import Path

from .projection import plan
from .state import StateError


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def build(signal_directory, strategy_directory):
    root = Path(signal_directory)
    summary = json.loads((root / "summary.json").read_text())
    release = summary["release_id"]
    reels = read_rows(root / "reels.jsonl")
    accounts = read_rows(root / "accounts.jsonl")
    if any(r["release_id"] != release for r in reels + accounts):
        raise StateError("PROJECTION_RELEASE_MIXING")
    if len({r["code"] for r in reels}) != len(reels):
        raise StateError("PROJECTION_DUPLICATE_REEL")
    attempts = {(r["reel_id"], r["modality"]): r for r in read_rows(root / "evidence-attempts.jsonl")}
    if any(a["release_id"] != release for a in attempts.values()):
        raise StateError("PROJECTION_EVIDENCE_RELEASE_MIXING")
    strategy = Path(strategy_directory)
    source_map = json.loads((strategy / "private-source-map.json").read_text())["sources"]
    text_rows = {a["transcript_id"]: a for a in read_rows(strategy / "transcript-analysis.jsonl")}
    text_by_reel = {}
    source_manifest = json.loads((root / "source-manifest.json").read_text())
    transcript_file_hash = source_manifest.get("transcripts", {}).get("sha256")
    reel_ids = {r["reel_id"] for r in reels}
    for source in source_map:
        analysis = text_rows[source["transcript_id"]]
        if source["reel_id"] not in reel_ids or analysis["source_artifact_sha256"] != "sha256:" + str(transcript_file_hash):
            raise StateError("PROJECTION_TEXT_CORPUS_MISMATCH")
        if analysis["source_record_sha256"] != source["record_sha256"]:
            raise StateError("PROJECTION_TEXT_SOURCE_HASH_MISMATCH")
        if source["reel_id"] in text_by_reel:
            raise StateError("PROJECTION_TEXT_IDENTITY_DUPLICATE")
        text_by_reel[source["reel_id"]] = analysis
    reel_pages = []
    for r in reels:
        props = {"Name": r["code"], "Release": release, "Account": r["account_username"],
                 "Source": r["url"], "Snapshot": r["snapshot_date"], "Views": r.get("views"),
                 "Likes": r.get("likes"), "Comments": r.get("comments"), "Reshares": r.get("reshares"),
                 "Saves": r.get("saves"), "Seconds": r.get("duration_seconds"),
                 "Published UTC": r.get("published_at_utc"), "Eligibility": r["eligibility_state"],
                 "View index": r.get("creator_view_index"), "Diagnostic z": r.get("diagnostic_equal_weight_z"),
                 "Components": r.get("diagnostic_component_count"), "Baseline n": r.get("author_baseline_n"),
                 "Transcript": r.get("transcript_state"), "Legacy ASR reported words": r.get("transcript_words") if r.get("transcript_words") else None,
                 "Frames": attempts.get((r["reel_id"], "frames"), {}).get("reason_code", "NO_ATTEMPT_RECORD"),
                 "Frame observation": attempts.get((r["reel_id"], "frames"), {}).get("observation_state", "UNKNOWN"),
                 "Final Best": r["best_reel_eligibility_state"], "Best reason": r["best_reel_reason"],
                 "Likes per 1k views": r.get("likes_per_1k_views"),
                 "Comments per 1k views": r.get("comments_per_1k_views"),
                 "Reshares per 1k views": r.get("reshares_per_1k_views"),
                 "Saves per 1k views": r.get("saves_per_1k_views"),
                 "Quarantine": "; ".join(r["quarantine_reasons"]),
                 "Save state": "MISSING" if r.get("saves") is None else "OBSERVED"}
        text = text_by_reel.get(r["reel_id"], {})
        props.update({"Text fit candidate": text.get("m2_fit_candidate", "unknown"),
                      "Opening candidate": text.get("hook_orientation", "unknown"),
                      "Lexical text words": text.get("word_count_lexical_v1") or None,
                      "Text evidence": text.get("transcript_id"),
                      "Text review": "MAKER_CODING_NOT_FULLY_ADJUDICATED" if text else "NO_TEXT_ANALYSIS"})
        body = None
        if text:
            body = "Maker text interpretation; source ASR, rhetorical boundaries, rights and visuals remain unverified.\n\n" + "\n\n".join(str(text.get(k, "")) for k in ["body_structure", "claim_and_originality_risk", "transferable_function_candidate"])
        reel_pages.append({"properties": props, "content": body, "action": plan(release, "reel:"+r["code"], props)})
    account_pages = []
    for a in accounts:
        props = {"Name": a["account_username"], "Release": release, "Snapshot": a["snapshot_date"],
                 "Reels": a["canonical_reels"], "Observations": a["source_observations"],
                 "Eligible": a["exposure_eligible_reels"], "Followers at export": a["followers"],
                 "Median views": a["author_median_views"], "Baseline n": a["author_baseline_n"],
                 "Hit count": a["hit_numerator"], "Hit denominator": a["hit_denominator"],
                 "Hit fraction": a["hit_rate"], "Wilson lower": a["hit_wilson95_low"],
                 "Wilson upper": a["hit_wilson95_high"], "Hit state": a["hit_reason"],
                 "Eligible transcript records": a["transcript_observed_n"], "Eligible frame sets": a["frames_observed_n"],
                 "Review candidate": a["candidate_reel_url"], "Final Best": a["best_reel_eligibility_state"],
                 "Best reason": a["best_reel_reason"]}
        account_pages.append({"properties": props, "action": plan(release, "account:"+a["account_username"], props)})
    strategy = Path(strategy_directory)
    slate = json.loads((strategy / "notion-strategy-projection.json").read_text())
    return {"schema": "m2.notion-package.v1", "release_id": release,
            "review_state": "PENDING", "legacy_merge": False,
            "reels": reel_pages, "accounts": account_pages,
            "strategy": slate, "summary": summary,
            "counts": {"reels": len(reels), "accounts": len(accounts), "cards": len(slate["cards"])}}


def database_schema(kind):
    # Rich text preserves machine states exactly without guessed select options.
    if kind == "reels":
        numbers = ["Views", "Likes", "Comments", "Reshares", "Saves", "Seconds", "View index",
                   "Diagnostic z", "Components", "Baseline n", "Legacy ASR reported words", "Likes per 1k views", "Comments per 1k views", "Reshares per 1k views", "Saves per 1k views", "Lexical text words"]
        texts = ["Release", "Account", "Snapshot", "Published UTC", "Eligibility", "Transcript",
                 "Frames", "Frame observation", "Final Best", "Best reason", "Quarantine", "Save state", "Text fit candidate", "Opening candidate", "Text evidence", "Text review"]
        urls = ["Source"]
    elif kind == "accounts":
        numbers = ["Reels", "Observations", "Eligible", "Followers at export", "Median views", "Baseline n",
                   "Hit count", "Hit denominator", "Hit fraction", "Wilson lower", "Wilson upper",
                   "Eligible transcript records", "Eligible frame sets"]
        texts = ["Release", "Snapshot", "Hit state", "Final Best", "Best reason"]
        urls = ["Review candidate"]
    else:
        raise StateError("PROJECTION_DATABASE_KIND")
    columns = ['"Name" TITLE']
    for names, sql_type in [(numbers, "NUMBER"), (texts, "RICH_TEXT"), (urls, "URL")]:
        columns.extend('"'+name+'" '+sql_type for name in names)
    return "CREATE TABLE (" + ", ".join(columns) + ")"
