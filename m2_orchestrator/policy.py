"""Explicit stage DAG. This module never imports a collector or model SDK."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Stage:
    id: str
    engine: str
    role: str
    requires: tuple[str, ...]
    output: str
    gate: str | None = None
    reviewer: bool = False


STAGES = (
    Stage("admit", "control", "integrator", (), "admission"),
    Stage("freeze_config", "control", "integrator", ("admit",), "config"),
    Stage("inventory", "signal", "data_engineer", ("freeze_config",), "inventory"),
    Stage("collect_or_replay", "signal", "data_engineer", ("inventory",), "observations"),
    Stage("normalize", "signal", "data_engineer", ("collect_or_replay",), "entities"),
    Stage("audit_all_rows", "signal", "data_engineer", ("normalize",), "audit"),
    Stage("media_manifest", "signal", "data_engineer", ("audit_all_rows",), "media_manifest"),
    Stage("media_acquire", "signal", "data_engineer", ("media_manifest",), "media_acquisition"),
    Stage("qualify_scope", "signal", "strategy_analyst", ("audit_all_rows",), "scope"),
    Stage("snapshot_metrics", "signal", "quantitative_analyst", ("audit_all_rows",), "metrics"),
    Stage("compute_baselines", "signal", "quantitative_analyst", ("snapshot_metrics",), "baselines"),
    Stage("rank_candidates", "signal", "quantitative_analyst", ("compute_baselines",), "rankings"),
    Stage("transcript_attempt", "signal", "text_analyst", ("audit_all_rows",), "transcript_attempts"),
    Stage("transcript_segment", "signal", "text_analyst", ("transcript_attempt",), "transcript_sections"),
    Stage("visual_attempt", "signal", "scene_analyst", ("audit_all_rows",), "visual_attempts"),
    Stage("scene_segment", "signal", "scene_analyst", ("visual_attempt", "transcript_segment"), "scenes"),
    Stage("comment_attempt", "signal", "comment_analyst", ("audit_all_rows",), "comments"),
    Stage("multimodal_fuse", "signal", "strategy_analyst", ("qualify_scope", "rank_candidates", "scene_segment", "comment_attempt"), "features"),
    Stage("account_aggregate", "signal", "quantitative_analyst", ("multimodal_fuse",), "account_analysis"),
    Stage("review_signal", "signal", "signal_reviewer", ("account_aggregate",), "signal_review", reviewer=True),
    Stage("release_to_studio", "control", "integrator", ("review_signal",), "signal_release"),
    Stage("write_script_cards", "studio", "script_architect", ("release_to_studio",), "script_cards"),
    Stage("plan_scenes", "studio", "scene_planner", ("write_script_cards",), "scene_plans"),
    Stage("review_studio", "studio", "studio_reviewer", ("plan_scenes",), "studio_review", reviewer=True),
    Stage("project_notion", "projection", "projection_engineer", ("review_studio",), "projection_readback", gate="notion_write"),
    Stage("owner_gate", "studio", "owner", ("review_studio",), "shoot_approval", gate="shoot_plan"),
    Stage("await_owner_media", "studio", "owner", ("owner_gate",), "owner_media", gate="owner_media"),
    Stage("probe_owner_media", "studio", "video_engineer", ("await_owner_media",), "media_probe"),
    Stage("lock_edit_plan", "studio", "video_engineer", ("probe_owner_media",), "edit_plan"),
    Stage("plan_generation", "studio", "video_engineer", ("lock_edit_plan",), "generation_plan"),
    Stage("generation_approval", "studio", "owner", ("plan_generation",), "generation_approval", gate="paid_generation"),
    Stage("generate_assets", "studio", "video_engineer", ("generation_approval",), "generated_assets", gate="paid_generation"),
    Stage("review_assets", "studio", "studio_reviewer", ("generate_assets",), "asset_review", reviewer=True),
    Stage("render_remotion", "studio", "video_engineer", ("lock_edit_plan",), "render_receipt", gate="render"),
    Stage("media_qa", "studio", "studio_reviewer", ("render_remotion",), "media_qa", reviewer=True),
    Stage("owner_final", "studio", "owner", ("media_qa",), "final_approval", gate="final_edit"),
    Stage("publish", "distribution", "publisher", ("owner_final",), "publication", gate="publish"),
    Stage("measure_owned_outputs", "signal", "quantitative_analyst", ("publish",), "owned_metrics", gate="owned_analytics"),
    Stage("learn", "knowledge", "knowledge_curator", ("review_signal", "review_studio"), "knowledge_candidates"),
    Stage("promote_knowledge", "knowledge", "knowledge_reviewer", ("learn",), "knowledge_review", reviewer=True),
    Stage("close_run", "control", "integrator", ("review_studio", "promote_knowledge"), "terminal_receipt"),
)
BY_ID = {s.id: s for s in STAGES}
SUCCESS = {"PASS", "PASS_WITH_LIMITATIONS"}
STATES = SUCCESS | {"NOT_STARTED", "RUNNING", "FAIL", "BLOCKED_OWNER", "BLOCKED_EVIDENCE", "SKIPPED_DISABLED"}


def policy():
    return [asdict(s) for s in STAGES]


def dependencies(stage_id, config):
    deps = list(BY_ID[stage_id].requires)
    if stage_id in {"transcript_attempt", "visual_attempt"} and config.get("media_acquisition", {}).get("enabled"):
        deps.append("media_acquire")
    if stage_id == "render_remotion" and config.get("production", {}).get("requires_generation", False):
        deps.append("review_assets")
    return deps

