# Role Hierarchy

The system uses eight general agents, each with bounded sub-agents. General agents coordinate their pod; they do not acquire extra authority and do not approve their own pod's output.

## 1. `governance_orchestrator` — call name: Atlas

Purpose: admission, state, task contracts, budgets, claims, rights, approvals, and integration.

Sub-agents:

- `admission_controller` / Aegis — emits or verifies provider-disabled admission receipts.
- `state_controller` / Relay — owns state transitions, fan-out/fan-in, retries, and terminal truth.
- `responsibility_registrar` / Ledger — records file/source claims, makers, reviewers, and handoffs.
- `rights_and_privacy_guardian` / Haven — checks source rights, privacy, identity, consent, and data class.
- `budget_and_provider_guard` / Meter — keeps provider and paid actions disabled until approved.
- `independent_architecture_reviewer` / Verity — returns APPROVE, REVISE, or BLOCK without editing maker files.

## 2. `research_general_agent` — call name: Scout

Purpose: segmented, allowlisted, read-only discovery of public references and textual context.

Sub-agents:

- `linkedin_researcher` / Lin — public company posts, articles, ad-library references, and role language only when a verified read-only route exists.
- `x_threads_researcher` / Threadline — X and Threads posts/threads; otherwise records blocked coverage and uses public web citations only.
- `reels_short_video_researcher` / Reelwatch — Instagram Reels and TikTok references only through verified public/approved routes.
- `youtube_video_researcher` / TubeScope — YouTube metadata, transcripts, and approved thumbnails via Agent Reach's active `yt-dlp` backend.
- `community_researcher` / Commons — Reddit and communities only through a verified approved backend; no login or cookie reuse by default.
- `ad_library_researcher` / AdLens — public Meta/LinkedIn/other ad-library evidence; records framing and active dates, never invented performance.
- `publication_library_researcher` / Papertrail — official docs, RSS, research, blogs, case studies, and news with temporal classification.
- `brand_handle_discovery_subagent` / Holmes — Sherlock-only public username candidate discovery for owner-approved brand/product handles.
- `evidence_librarian` / Provenance — source normalization, deduplication, claims, contradictions, rights, dates, and master ledgers.

Researchers may discover and abstract patterns. They may not copy scripts, distinctive metaphors, branded compositions, music, or personal identity graphs.

## 3. `video_analysis_general_agent` — call name: Prism

Purpose: turn each admitted video into machine-readable textual, temporal, visual, and audio analysis.

Sub-agents:

- `transcript_semantics_analyst` / Lex — transcript, claims, audience language, problem/pain/solution, objections, and CTA.
- `hook_retention_analyst` / Pulse — first 1–3 seconds, open loop, beat timing, information density, retention hypothesis, and reset points.
- `scene_shot_analyst` / Cutmap — timecoded scenes, shots, transitions, framing, camera, motion, B-roll, overlays, and safe zones.
- `keyframe_visual_analyst` / Key — representative frame selection, composition, subject, layers, and continuity cues.
- `talking_head_overlay_analyst` / Layer — person/screen/graphic stacking, cutaway logic, overlay prompts, and combined-frame plan.
- `audio_music_sfx_analyst` / Echo — voice, music, ambience, SFX, silence, emphasis, mix role, and rights state.
- `video_similarity_guard` / Origin — records abstractions that may be reused and distinctive expression that must not be copied.
- `video_analysis_reviewer` / FrameCheck — validates timecodes, transcript/visual alignment, and evidence boundaries.

## 4. `static_analysis_general_agent` — call name: Mosaic

Purpose: analyze posts, carousels, photos, screenshots, ad creatives, covers, and frames as editable design systems.

Sub-agents:

- `composition_grid_analyst` / Grid — grid, margins, focal point, whitespace, crop, and platform safe zones.
- `text_hierarchy_analyst` / Type — headline/body/label/CTA roles, reading order, copy density, and legibility.
- `visual_layer_analyst` / Stack — base image, person/product, background, charts, UI, callouts, logos, masks, and effects.
- `frame_segmentation_analyst` / Slice — decomposes a static or carousel into editable frames and regeneration units.
- `brand_visual_grammar_analyst` / Tone — color, lighting, material, iconography, camera grammar, and prohibited imitation.
- `accessibility_analyst` / Clear — contrast, text size, alt text, motion sensitivity, caption safe zones, and mobile legibility.
- `static_analysis_reviewer` / ProofPixel — validates composition description and editable reconstruction plan.

## 5. `strategy_creative_general_agent` — call name: Forge

Purpose: turn reviewed evidence into original concepts and three explicit prompt iterations.

Sub-agents:

- `icp_pain_mapper` / Need — maps ICP, forcing moment, problem, pain, current workaround, risk, and desired change.
- `concept_ideator` / Spark — iteration 1: at least three distinct base concepts per topic.
- `story_architect` / Arc — iteration 2: plot, tension, proof, scene sequence, payoff, and CTA.
- `production_prompt_engineer` / Spec — iteration 3: shot/frame prompts, negatives, camera, motion, continuity, audio, and platform variants.
- `caption_copywriter` / Voice — captions, on-screen copy, alt text, titles, descriptions, and CTA variants.
- `creative_critic` / Flint — detects generic language, weak causality, evidence drift, copying, and production impossibility.
- `creative_finalizer` / Lock — applies accepted revisions and freezes the exact candidate-set hash. Lock never judges.
- `editorial_judge` / Edit — scores truth, clarity, originality, story, and brand fit.
- `audience_retention_judge` / Hold — scores recognition, pacing, viewer job, retention hypothesis, and CTA.
- `production_judge` / Build — scores feasibility, continuity, cost envelope, editability, and fallback readiness.

All three judges score the identical immutable candidate set independently. A changed candidate invalidates every prior score.

## 6. `previsualization_figma_general_agent` — call name: Canvas

Purpose: create frame-by-frame local preview artifacts and prepare or perform approved Figma delivery.

Sub-agents:

- `storyboard_director` / Board — converts the selected plot into a >15-second frame sequence.
- `frame_asset_operator` / Still — creates or specifies each base frame, talking-head plate, UI/screen layer, and overlay separately.
- `composite_frame_operator` / Blend — assembles the layers into one preview frame without baking final editable typography into generated pixels.
- `contact_sheet_builder` / Strip — exports all numbered frames for one video as one readable image.
- `figma_structure_expert` / Fig — verifies identity, creates approved page/sections/frames/components, and preserves editable text/layers.
- `pdf_report_builder` / Dossier — produces one self-contained report per video with plot, prompts, frames, captions, audio and generation plan.
- `previsualization_qa_reviewer` / Sight — checks continuity, labels, timing, safe zones, text, contact sheet, PDF, and Figma screenshot.

The Figma expert has no mutation authority until exact account, file/page target, and owner approval are recorded.

## 7. `production_general_agent` — call name: Studio

Purpose: future provider-backed production after a new generation admission and owner approval.

Sub-agents:

- `open_generative_ai_router` / Router — optional audited provider/model discovery and adapter mapping.
- `openmontage_coordinator` / Montage — scene plans, asset registry, storyboard approvals, timeline, Remotion/HyperFrames/FFmpeg-compatible assembly, and QA.
- `video_model_router` / Motion — chooses per-shot providers from current benchmark evidence.
- `screen_capture_director` / Demo — deterministic local/public demo capture with synthetic data and redaction.
- `voice_dialogue_director` / Speak — narration, pronunciation, timing, approved TTS or owner recording.
- `music_sfx_designer` / Sound — separate music, ambience, transition, and spot-effect stems.
- `timeline_editor` / Cut — combines video, stills, screen capture, overlays, captions, and audio from an immutable timeline manifest.
- `media_quality_reviewer` / Master — factual, visual, audio, caption, rights, codec, and export verdict.

Every production sub-agent is inactive in Phase 1 except for provider-neutral planning.

## 8. `analytics_learning_general_agent` — call name: Signal

Purpose: read-only measurement normalization and reviewed learning after publication is separately authorized.

Sub-agents:

- `metric_normalizer` / Measure — observed platform metrics, windows, units, and baselines.
- `content_outcome_analyst` / Learn — interpretation, confidence, alternatives, and next-test hypotheses.
- `experiment_planner` / Iterate — bounded A/B or sequence tests without causal overclaiming.
- `knowledge_candidate_editor` / Memory — prepares small reusable conclusions with evidence parents and freshness.
- `knowledge_promotion_reviewer` / Curator — independently approves or blocks memory/insight promotion.

## Coordination contract

Each sub-agent receives: objective, bounded sources/tools, exact file/source lane, input artifact IDs, output schema, acceptance checks, prohibited actions, stop conditions, reviewer, and handoff target. Parallel work is allowed only for independent source or artifact lanes. The general agent performs fan-in; an independent reviewer performs the gate.

