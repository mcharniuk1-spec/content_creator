#!/usr/bin/env python3
"""Print the public-safe Notion projection for the current top-100 cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def content_type(value: str) -> str:
    return {
        "tutorial_or_build": "Tutorial", "tool_demo": "Demo", "case_study": "Case study",
        "opinion_or_prediction": "Opinion", "news_or_update": "Reaction",
        "framework_or_explainer": "Teardown", "comparison_or_review": "Teardown",
        "prompt_or_template": "Tutorial", "listicle": "Tutorial",
    }.get(value, "Other")


def track(topic: str) -> str:
    if topic in {"business_problem_selection", "product_discovery", "requirements_and_specs", "workflow_design",
                 "adoption_and_change", "analytics_cost_roi", "business_cases_and_operations"}:
        return "Product/company operator"
    if topic in {"api_mcp_system_integration", "agent_building", "rag_and_provenance",
                 "orchestration_and_state", "evaluation_and_observability", "rollback_recovery_failure"}:
        return "Agent-builder/operator"
    return "Mixed"


def review_projection(label: str | None) -> tuple[list[str], str]:
    return {
        "direct_agentic_business": (["Direct competitor"], "Pass"),
        "technical_agentic_authority": (["Technical authority"], "Pass"),
        "adjacent_ai_business": (["Adjacent topic"], "Pass"),
        "format_reference_only": (["Format leader"], "Pass with limitations"),
        "exclude_non_relevant_or_language": (["Noise"], "Blocked"),
        "unresolved": (["Counterexample"], "In review"),
    }.get(label, (["Counterexample"], "In review"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    top = jsonl(run_dir / "derived" / "top-reference-cohort.jsonl")
    analysis = {row["native_video_id"]: row for row in jsonl(run_dir / "derived" / "video-analysis.jsonl")}
    rows = []
    for item in top:
        row = analysis[item["native_video_id"]]
        content_categories, review_status = review_projection(row.get("independent_relevance_label"))
        rows.append({"native_video_id": item["native_video_id"], "properties": {
            "Reference": f"{item['reference_rank']:03d}. {row['creator_title']} — {row['title']}",
            "Platform": "YouTube",
            "userDefined:URL": row["canonical_url"],
            "Creator or Group": row["creator_title"],
            "Views": row["views"],
            "Likes": row["likes"],
            "Comments": row["reported_comments"],
            "Content Type": content_type(row["video_type"]),
            "Content Category": content_categories,
            "PM Track": track(row["primary_topic"]),
            "Analysis Depth": "D3 Multimodal",
            "Evidence State": "Classified",
            "Review Status": review_status,
            "Rights State": "Frame reference",
            "Dataset Version": run_dir.name,
            "Reason": f"Sol relevance={row.get('independent_relevance_label') or 'unreviewed'}; topic={row['primary_topic']}; hook={row['hook_type']}; story={row['storytelling_style']}; creator index={row['creator_view_index']:.2f}x; de-rolled transcript analysis; one creator per reference.",
        }})
    print(json.dumps(rows, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
