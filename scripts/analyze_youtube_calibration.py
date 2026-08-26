#!/usr/bin/env python3
"""Evidence-labeled qualitative and quantitative analysis for the 300/900 YouTube run."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter, defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TOPIC_RULES: list[tuple[str, str]] = [
    ("business_problem_selection", r"use case|business problem|pain point|business need|opportunit|problem worth"),
    ("product_discovery", r"product discover|customer interview|user research|product.market|validate.*idea|jobs to be done"),
    ("requirements_and_specs", r"requirement|product requirement|\bprd\b|user stor|acceptance criteria|specification"),
    ("workflow_design", r"workflow|process map|business process|automat|n8n|make\.com|zapier"),
    ("tool_and_model_selection", r"best (ai|llm|model|tool)|comparison| versus |\bvs\.?\b|benchmark|model selection|tool stack"),
    ("api_mcp_system_integration", r"\bmcp\b|model context protocol|\bapi\b|webhook|integration|connector|function call|tool call"),
    ("agent_building", r"build.*agent|ai agent|agentic|multi.agent|crew.?ai|autogen|langgraph|openai agents|agent sdk"),
    ("rag_and_provenance", r"\brag\b|retrieval.augmented|vector database|embedding|knowledge base|citation|provenance|grounded"),
    ("authority_and_permissions", r"permission|authority|access control|least privilege|credential|authorization|approval gate"),
    ("orchestration_and_state", r"orchestrat|state machine|memory|checkpoint|routing|supervisor agent|handoff|planner.executor"),
    ("evaluation_and_observability", r"evaluat|observab|trace|monitor|test.*agent|benchmark|quality metric|hallucination"),
    ("human_review", r"human.in.the.loop|human review|manual review|approval|reviewer|oversight"),
    ("rollback_recovery_failure", r"rollback|recover|failure|error handling|fallback|retry|incident|guardrail|fail.safe"),
    ("adoption_and_change", r"adoption|change management|train.*team|upskill|organizational|culture|employee"),
    ("analytics_cost_roi", r"\broi\b|return on investment|cost|token spend|saving|revenue|analytics|metric|kpi|productivity"),
    ("business_cases_and_operations", r"case study|real.world|business|enterprise|company|operations|sales|marketing|customer service|finance|hr"),
]

VIDEO_TYPE_RULES = [
    ("tutorial_or_build", r"how to|step.by.step|tutorial|build|create|setup|set up|code along"),
    ("tool_demo", r"demo|in action|walkthrough|watch.*work|live test|testing"),
    ("case_study", r"case study|real.world|for (a|an) (business|company)|client|we used|implementation"),
    ("news_or_update", r"new|launch|released|announcement|update|breaking|just dropped|latest"),
    ("listicle", r"\b[3-9]\b .*?(ways|tools|agents|ideas|steps|mistakes|use cases)|top \d+"),
    ("comparison_or_review", r"\bvs\.?\b|versus|comparison|review|best .* tool|which .* better"),
    ("opinion_or_prediction", r"future|will replace|why .* wrong|truth about|hot take|prediction|dead|overhyped"),
    ("framework_or_explainer", r"what is|explained|framework|guide|understand|beginner|fundamental"),
    ("prompt_or_template", r"prompt|template|cheat sheet|playbook|copy this|steal this"),
]

HOOK_RULES = [
    ("contrarian_claim", r"you.re wrong|stop |don.t |myth|truth|nobody|isn.t|won.t|dead|overhyped"),
    ("direct_benefit", r"save|faster|in seconds|in minutes|make money|revenue|productivity|automate|without"),
    ("curiosity_gap", r"secret|mystery|what happened|you won.t believe|hidden|this changed|wait until|turns out"),
    ("question", r"^(how|what|why|which|can|should|did|is|are|do)\b|\?"),
    ("specific_result", r"\b\d+[x%]|\$\d|\d+ (hours|minutes|days|clients|tasks|agents)|from .* to "),
    ("breaking_news", r"just (launched|dropped|released)|breaking|new .* model|today|latest"),
    ("pain_callout", r"struggl|wasting|problem|bottleneck|tired of|manual|overwhelmed|stuck"),
    ("demonstration_first", r"watch|here.s|this is|look at|i built|we built|meet "),
    ("authority_or_case", r"i tested|we tested|after \d+|client|company|research|study|experiment"),
]

STORY_RULES = [
    ("problem_mechanism_solution", r"problem|pain|bottleneck|manual", r"solution|workflow|agent|automat|here.s how"),
    ("claim_proof_takeaway", r"will|can|best|changed|truth", r"test|result|proof|because|therefore|so "),
    ("scenario_to_demo", r"imagine|scenario|when a|if you|let.s say", r"watch|demo|build|workflow|then "),
    ("before_after", r"before|used to|from ", r"after|now|to \d|instead"),
]

CTA_RULES = [
    ("comment_keyword", r"comment [\"']?\w+|type [\"']?\w+ below"),
    ("follow_or_subscribe", r"follow|subscribe|hit the bell"),
    ("link_or_lead_magnet", r"link in (my )?(bio|description)|download|free (guide|template|course|webinar)|book a call"),
    ("question_to_audience", r"what do you think|would you|which one|tell me|let me know|agree\?"),
    ("watch_next", r"watch.*next|full video|part \d|next video"),
]

COMMENT_RULES = [
    ("implementation_question", r"how (do|can|would)|what tool|which tool|can you|tutorial|setup|code|where"),
    ("pricing_or_purchase", r"price|pricing|cost|paid|free|worth|buy|subscription"),
    ("request_or_idea", r"please|make a video|cover |show us|could you|would love"),
    ("implementation_evidence", r"i (built|made|use|implemented|tried)|we (use|built|implemented)|worked for"),
    ("skepticism_or_objection", r"doesn.t work|not true|but |however|scam|wrong|overhyped|hallucin|privacy|security"),
    ("pain_or_blocker", r"struggl|problem|stuck|confus|difficult|hard to|failed|error"),
    ("positive_confirmation", r"thank|helpful|great|amazing|love this|excellent|useful|brilliant"),
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def first_match(text: str, rules: list[tuple[str, str]]) -> str:
    lowered = text.lower()
    for label, pattern in rules:
        if re.search(pattern, lowered):
            return label
    return "unresolved"


def topic(text: str) -> tuple[str, list[str]]:
    lowered = text.lower()
    labels = [item[0] for item in TOPIC_RULES]
    matches = [(label, len(re.findall(pattern, lowered))) for label, pattern in TOPIC_RULES]
    matches = [(label, count) for label, count in matches if count]
    matches.sort(key=lambda item: (-item[1], labels.index(item[0])))
    return (matches[0][0] if matches else "general_ai_or_unresolved", [label for label, _ in matches[:4]])


def story(text: str) -> str:
    lowered = text.lower()
    for label, first, second in STORY_RULES:
        if re.search(first, lowered) and re.search(second, lowered):
            return label
    if re.search(r"\b(first|step 1|one)\b", lowered) and re.search(r"\b(second|step 2|two|then)\b", lowered):
        return "stepwise_process"
    if len(re.findall(r"\b(first|second|third|finally|then|next)\b", lowered)) >= 3:
        return "stepwise_process"
    return "single_claim_or_unresolved"


def hook_text(transcript: dict[str, Any], title: str) -> tuple[str, str]:
    segments = transcript.get("speech_segments") or transcript.get("segments") or []
    bounded = [segment for segment in segments if (segment.get("end_ms") or 0) <= 10000]
    spoken = " ".join(segment.get("text", "") for segment in bounded)
    spoken = re.sub(r"\s+", " ", spoken).strip()
    return (spoken[:700] if spoken else title, "transcript_segments_ending_by_10s" if spoken else "title_proxy")


def median(values: list[float | int | None]) -> float | None:
    cleaned = [float(value) for value in values if value is not None]
    return round(statistics.median(cleaned), 3) if cleaned else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[round((len(ordered) - 1) * q)], 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    cohort = load_jsonl(run_dir / "derived" / "analyzed-content-cohort.jsonl")
    accounts = load_jsonl(run_dir / "derived" / "qualified-accounts.jsonl")
    comments = load_jsonl(run_dir / "derived" / "comments.jsonl")
    coverage = load_jsonl(run_dir / "derived" / "comment-coverage.jsonl")
    relevance_reviews = load_jsonl(run_dir / "derived" / "independent-relevance-review.jsonl")
    relevance_by_video = {row["native_video_id"]: row for row in relevance_reviews}
    relevance_by_creator = {row["native_channel_id"]: row for row in relevance_reviews}
    if len(cohort) != 900 or len(accounts) != 300:
        raise ValueError(f"expected exact 300/900 calibration, got {len(accounts)}/{len(cohort)}")

    account_by_id = {row["native_channel_id"]: row for row in accounts}
    comments_by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in comments:
        comments_by_video[row["native_video_id"]].append(row)
    coverage_by_video = {row["native_video_id"]: row for row in coverage}
    transcripts: dict[str, dict[str, Any]] = {}
    for path in sorted((run_dir / "normalized" / "transcripts").glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        transcripts[item["native_video_id"]] = item

    per_creator_views: dict[str, list[int]] = defaultdict(list)
    for row in cohort:
        if row.get("view_count") is not None:
            per_creator_views[row["native_channel_id"]].append(int(row["view_count"]))
    creator_medians = {key: statistics.median(values) if values else 0 for key, values in per_creator_views.items()}

    analyzed: list[dict[str, Any]] = []
    for row in cohort:
        video_id = row["native_video_id"]
        transcript = transcripts.get(video_id, {})
        transcript_text = transcript.get("speech_text") or transcript.get("text") or ""
        material = "\n".join([row.get("title") or "", row.get("description") or "", transcript_text[:16000]])
        primary_topic, secondary_topics = topic(material)
        hook, hook_basis = hook_text(transcript, row.get("title") or "")
        views = int(row.get("view_count") or 0)
        likes = int(row.get("like_count") or 0)
        reported_comments = int(row.get("comment_count") or 0)
        creator_median = creator_medians.get(row["native_channel_id"], 0)
        view_index = round(views / max(1, creator_median), 3)
        engagement_proxy = round((likes + reported_comments) / views, 5) if views else None
        comment_labels = Counter(first_match(item.get("text") or "", COMMENT_RULES) for item in comments_by_video[video_id])
        score = (
            min(8.0, math.log10(views + 1))
            + min(4.0, view_index)
            + min(2.0, (engagement_proxy or 0) * 50)
            + (1.5 if transcript.get("availability") == "observed" else 0)
            + (0.5 if 15 <= (row.get("duration_seconds") or 0) <= 90 else 0)
            + min(1.0, len(comments_by_video[video_id]) / 10)
            + min(1.5, row.get("relevance_signals", {}).get("agent_hits", 0) / 3)
        )
        analyzed.append({
            "schema": "north-hux.youtube-video-analysis.v1",
            "epistemic_state": "DERIVED_RULE_BASED_WITH_DIRECT_EVIDENCE_FIELDS",
            "native_channel_id": row["native_channel_id"],
            "native_video_id": video_id,
            "canonical_url": row["canonical_url"],
            "creator_title": account_by_id[row["native_channel_id"]].get("title"),
            "title": row.get("title"),
            "published_at": row.get("published_at"),
            "duration_seconds": row.get("duration_seconds"),
            "format_state": row.get("format_state"),
            "native_short_proved": row.get("native_short_proved", False),
            "views": views,
            "likes": likes,
            "reported_comments": reported_comments,
            "retrieved_comments": len(comments_by_video[video_id]),
            "comment_pagination_complete": coverage_by_video.get(video_id, {}).get("pagination_complete"),
            "creator_median_views_in_sample": creator_median,
            "creator_view_index": view_index,
            "engagement_proxy": engagement_proxy,
            "primary_topic": primary_topic,
            "secondary_topics": secondary_topics,
            "video_type": first_match(material, VIDEO_TYPE_RULES),
            "storytelling_style": story(material),
            "hook_type": first_match(hook, HOOK_RULES),
            "hook_text": hook,
            "hook_evidence_basis": hook_basis,
            "cta_type": first_match(transcript_text[-2000:] + " " + (row.get("description") or ""), CTA_RULES),
            "transcript_availability": transcript.get("availability", "unavailable"),
            "transcript_source_kind": transcript.get("source_kind"),
            "transcript_language": transcript.get("language"),
            "transcript_segment_count": transcript.get("segment_count", 0),
            "speech_segment_count": transcript.get("speech_segment_count", transcript.get("segment_count", 0)),
            "rolling_caption_expansion_ratio": transcript.get("rolling_caption_expansion_ratio"),
            "audience_activity": dict(comment_labels),
            "reference_score": round(score, 4),
            "independent_relevance_label": relevance_by_video.get(video_id, {}).get("review_label"),
            "independent_relevance_reviewed": video_id in relevance_by_video,
        })

    write_jsonl(run_dir / "derived" / "video-analysis.jsonl", analyzed)
    analyses_by_creator: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in analyzed:
        analyses_by_creator[row["native_channel_id"]].append(row)
    account_analysis = []
    for account in accounts:
        rows = analyses_by_creator[account["native_channel_id"]]
        account_analysis.append({
            "schema": "north-hux.youtube-account-analysis.v1",
            "epistemic_state": "FACT_PLUS_DERIVED_RULE_BASED",
            "native_channel_id": account["native_channel_id"],
            "canonical_url": account["canonical_url"],
            "title": account.get("title"),
            "country": account.get("country"),
            "subscriber_count": account.get("subscriber_count"),
            "sample_video_count": len(rows),
            "median_views": median([item["views"] for item in rows]),
            "median_engagement_proxy": median([item["engagement_proxy"] for item in rows]),
            "dominant_topic": Counter(item["primary_topic"] for item in rows).most_common(1)[0][0],
            "dominant_video_type": Counter(item["video_type"] for item in rows).most_common(1)[0][0],
            "transcript_coverage": round(sum(item["transcript_availability"] == "observed" for item in rows) / len(rows), 4),
            "best_reference_video_id": max(rows, key=lambda item: item["reference_score"])["native_video_id"],
            "independent_relevance_label": relevance_by_creator.get(
                account["native_channel_id"], {}
            ).get("review_label"),
        })
    write_jsonl(run_dir / "derived" / "account-analysis.jsonl", account_analysis)

    captured_visual_ids = {
        row["native_video_id"] for row in load_jsonl(run_dir / "derived" / "media-assets.jsonl")
    }
    if len(captured_visual_ids) == 100:
        candidate_by_creator = [row for row in analyzed if row["native_video_id"] in captured_visual_ids]
        if len(candidate_by_creator) != 100 or len({row["native_channel_id"] for row in candidate_by_creator}) != 100:
            raise ValueError("frozen visual cohort must remain exactly one video per creator")
        top_selection_basis = "frozen_visual_cohort_reordered_by_derolled_topic"
    else:
        candidate_by_creator = [
            max(
                rows,
                key=lambda item: (
                    item["transcript_availability"] == "observed",
                    15 <= (item.get("duration_seconds") or 0) <= 90,
                    item["reference_score"],
                ),
            )
            for rows in analyses_by_creator.values()
        ]
        top_selection_basis = "category_round_robin_then_creator_short_duration_transcript_score_preference"
    queues: dict[str, deque[dict[str, Any]]] = {}
    for label in [item[0] for item in TOPIC_RULES] + ["general_ai_or_unresolved"]:
        values = [row for row in candidate_by_creator if row["primary_topic"] == label]
        queues[label] = deque(sorted(values, key=lambda item: item["reference_score"], reverse=True))
    top100: list[dict[str, Any]] = []
    while len(top100) < 100 and any(queues.values()):
        for label in queues:
            if queues[label] and len(top100) < 100:
                top100.append(queues[label].popleft())
    if len(top100) != 100 or len({row["native_channel_id"] for row in top100}) != 100:
        raise ValueError("could not construct exact one-creator category-balanced top 100")
    source_by_video = {row["native_video_id"]: row for row in cohort}
    top_cohort = []
    for rank, analysis in enumerate(top100, start=1):
        row = dict(source_by_video[analysis["native_video_id"]])
        row.update({
            "reference_rank": rank,
            "reference_score": analysis["reference_score"],
            "primary_topic": analysis["primary_topic"],
            "video_type": analysis["video_type"],
            "hook_type": analysis["hook_type"],
            "storytelling_style": analysis["storytelling_style"],
            "selection_basis": top_selection_basis,
            "independent_relevance_label": relevance_by_video.get(
                analysis["native_video_id"], {}
            ).get("review_label"),
        })
        top_cohort.append(row)
    write_jsonl(run_dir / "derived" / "top-reference-cohort.jsonl", top_cohort)

    observed_transcripts = [row for row in transcripts.values() if row.get("availability") == "observed"]
    views = [float(row["views"]) for row in analyzed]
    engagement = [float(row["engagement_proxy"]) for row in analyzed if row["engagement_proxy"] is not None]
    accepted_relevance_labels = {
        "direct_agentic_business", "technical_agentic_authority", "adjacent_ai_business"
    }
    top_review_rows = [row for row in relevance_reviews if row.get("sample_stratum") == "top100"]
    stratified_review_rows = [row for row in relevance_reviews if row.get("sample_stratum") == "stratified_non_top"]
    reviewed_accepted = [
        row for row in analyzed if row.get("independent_relevance_label") in accepted_relevance_labels
    ]
    summary = {
        "schema": "north-hux.youtube-analysis-summary.v1",
        "run_id": run_dir.name,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PASS_WITH_LIMITATIONS",
        "facts": {
            "qualified_accounts": len(accounts),
            "analyzed_videos": len(analyzed),
            "videos_per_account": dict(Counter(len(value) for value in analyses_by_creator.values())),
            "duration_candidates": sum(row["format_state"] == "DURATION_CANDIDATE" for row in analyzed),
            "native_shorts_proved": sum(row["native_short_proved"] is True for row in analyzed),
            "transcripts_observed": len(observed_transcripts),
            "transcript_segments": sum(row.get("segment_count", 0) for row in observed_transcripts),
            "speech_segments": sum(row.get("speech_segment_count", 0) for row in observed_transcripts),
            "transcript_raw_words": sum(row.get("raw_word_count", 0) for row in observed_transcripts),
            "transcript_speech_words": sum(row.get("speech_word_count", 0) for row in observed_transcripts),
            "median_rolling_caption_expansion_ratio": median([
                row.get("rolling_caption_expansion_ratio") for row in observed_transcripts
            ]),
            "comments_retrieved": len(comments),
            "videos_with_comments": sum(bool(rows) for rows in comments_by_video.values()),
            "median_views": median(views),
            "p90_views": percentile(views, .90),
            "median_engagement_proxy": median(engagement),
            "countries_reported": dict(Counter(row.get("country") or "unreported" for row in accounts)),
        },
        "derived": {
            "topics": dict(Counter(row["primary_topic"] for row in analyzed).most_common()),
            "video_types": dict(Counter(row["video_type"] for row in analyzed).most_common()),
            "hook_types": dict(Counter(row["hook_type"] for row in analyzed).most_common()),
            "storytelling_styles": dict(Counter(row["storytelling_style"] for row in analyzed).most_common()),
            "cta_types": dict(Counter(row["cta_type"] for row in analyzed).most_common()),
            "audience_activity": dict(Counter(first_match(row.get("text") or "", COMMENT_RULES) for row in comments).most_common()),
            "top100_topics": dict(Counter(row["primary_topic"] for row in top100).most_common()),
            "effective_coded_denominators": {
                "topics": sum(row["primary_topic"] != "general_ai_or_unresolved" for row in analyzed),
                "video_types": sum(row["video_type"] != "unresolved" for row in analyzed),
                "hooks": sum(row["hook_type"] != "unresolved" for row in analyzed),
                "storytelling_styles": sum(row["storytelling_style"] != "single_claim_or_unresolved" for row in analyzed),
                "ctas": sum(row["cta_type"] != "unresolved" for row in analyzed),
                "audience_comments": sum(first_match(row.get("text") or "", COMMENT_RULES) != "unresolved" for row in comments),
            },
            "independent_relevance_review": {
                "sample_size": len(relevance_reviews),
                "top100_reviewed": len(top_review_rows),
                "stratified_non_top_reviewed": len(stratified_review_rows),
                "labels": dict(Counter(row["review_label"] for row in relevance_reviews).most_common()),
                "top100_labels": dict(Counter(row["review_label"] for row in top_review_rows).most_common()),
                "language_fit": dict(Counter(row["language_fit"] for row in relevance_reviews).most_common()),
                "accepted_count": sum(row["review_label"] in accepted_relevance_labels for row in relevance_reviews),
                "accepted_rate": round(sum(row["review_label"] in accepted_relevance_labels for row in relevance_reviews) / max(1, len(relevance_reviews)), 4),
                "deterministic_admission_correct": sum(bool(row.get("deterministic_admission_correct")) for row in relevance_reviews),
                "deterministic_admission_precision": round(sum(bool(row.get("deterministic_admission_correct")) for row in relevance_reviews) / max(1, len(relevance_reviews)), 4),
                "accepted_topics": dict(Counter(row["primary_topic"] for row in reviewed_accepted).most_common()),
                "accepted_video_types": dict(Counter(row["video_type"] for row in reviewed_accepted).most_common()),
                "accepted_hook_types": dict(Counter(row["hook_type"] for row in reviewed_accepted).most_common()),
                "accepted_storytelling_styles": dict(Counter(row["storytelling_style"] for row in reviewed_accepted).most_common()),
            },
        },
        "limitations": [
            "The cohort is a bounded content-first calibration, not a probability sample of all YouTube creators.",
            "YouTube videoDuration=short means under four minutes and does not prove native Shorts placement.",
            "Comments are the first relevance-ordered page (maximum 20 threads plus embedded replies), not complete discussion exports.",
            "Public likes are counts; identities of likers, sends, reposts, shares, retention, and impressions are unavailable through this route.",
            "Topic, hook, story, CTA, and audience labels are deterministic lexical interpretations and remain reviewable.",
            "Transcript-derived analysis uses a de-rolled speech layer; original rolling caption cues remain preserved as evidence.",
            "Reported country is channel self-declaration; no personal demographic traits are inferred.",
        ],
    }
    (run_dir / "derived" / "analysis-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["facts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
