---
date: 2026-08-25
type: synthesis
tags: [research, taxonomy, creators, topics, emotions, hooks, b-roll, studio]
sources: ["[[Studio Screenwriting Knowledge Index]]", "studio/STORY-FRAMEWORK-TAXONOMY-V2.md"]
related-projects: ["[[ArchFlow Content Engine]]", "[[Signal Research Engine]]"]
confidence: high
ai-first: true
---

# Studio Classification Taxonomy

## For future Claude
This note defines the controlled vocabulary used to classify research observations and retrieve suitable Studio story structures. Apply several orthogonal dimensions rather than assigning one vague “style.” Creator classifications describe public content roles, not personal dossiers or stable identity claims.

## Minimum classification record

```text
content_id, source_id, observed_at, platform, duration_band, language,
creator_archetypes[], topic_primary, topic_secondary[], audience_segments[],
audience_jobs[], forcing_moment, knowledge_level, emotional_entry, emotional_exit,
hook_family, hook_device, story_family, transcript_architecture,
broll_functions[], visual_operations[], shot_scales[], camera_motivations[],
proof_type, limitation_type, handback_type, caption_role, sound_role,
rights_state, evidence_depth, confidence, performance_claim_state, gaps[]
```

## Topic taxonomy

| Cluster | Example subtopics | Typical concrete objects |
|---|---|---|
| AI agents and orchestration | roles, routing, tool use, state machines, supervision | work cards, junction, gate, role badge, state receipt |
| Product knowledge | sources, decisions, ownership, freshness, contradictions | source tile, decision board, timestamp, conflict pair |
| Workflow operations | handoffs, queues, approvals, exceptions, SLAs | queue, checklist, lane, approval token, timer |
| Research and evidence | provenance, sampling, transcript analysis, confidence | citation chain, sample grid, transcript segment, evidence slot |
| Safety and governance | permissions, human review, boundaries, audit | lock/key, review gate, exception lane, audit receipt |
| Implementation tutorial | setup, configuration, debugging, integration | terminal step, config card, status light, failing test |
| Product/PM craft | discovery, prioritization, roadmap, acceptance criteria | backlog, decision matrix, user evidence, scope boundary |
| Creator/content operations | ideation, scripting, editing, posting, experiments | storyboard, timeline, caption layer, variant board |
| Business explanation | cost, time, reliability, risk, coordination | before/after state, bottleneck, decision threshold |
| Meta-method | how to reason, compare, diagnose or learn | ladder, map, scale, question/evidence pair |

## Creator archetypes

Assign from observed public content behavior; allow multiple values.

| Archetype | Content promise | Common structure | Reliability risk |
|---|---|---|---|
| builder-demonstrator | watch a thing being built or configured | task → setup → run → inspect | demo may not prove real-world value |
| operator-practitioner | see how recurring work is handled | pain → mechanism → changed workflow | personal experience may not generalize |
| educator-explainer | understand a concept simply | recognition → analogy → examples | analogy can hide constraints |
| analyst-diagnostician | discover why a symptom occurs | symptom → hypotheses → test → diagnosis | confidence may exceed evidence |
| curator-taxonomist | organize a crowded field | category → distinctions → examples | list density and category bias |
| storyteller-character | feel a workplace or personal conflict | burden → contrast character → decision → changed state | fictional resolution is illustrative proof only |
| governance-guide | adopt a capability safely | benefit → control → guardrail → handback | guardrail may be asserted, not demonstrated |
| reviewer-comparator | decide between alternatives | criteria → contrast → proof → recommendation | sponsorship and selection bias |
| founder-thesis | adopt a worldview or strategic claim | thesis → condition → mechanism → implication | authority can replace evidence |
| process-coach | improve a repeatable behavior | friction → steps → check → next action | generic advice without situational fit |

Do not infer demographic traits, private identity, personality or competence from this field. Store creators as stable source IDs in the research system; Obsidian receives cohort/archetype synthesis, not thousands of creator dossiers.

## Audience segments and jobs

Segments: founder, product leader, PM, product operations, engineering leader, agent engineer, researcher, content operator, marketer, implementation owner, reviewer/auditor, novice learner.

Jobs: recognize a problem, understand a term, diagnose a failure, compare options, learn a procedure, inspect proof, reduce risk, make a decision, remember a rule, feel capable of a next step, or challenge an assumption.

Always record knowledge level: `novice`, `working`, `expert`, or `mixed`. A technical detail is relevant only if it advances the selected audience job.

## Emotion taxonomy

| Emotion | Safe trigger | Visual carrier | Desired next emotion |
|---|---|---|---|
| recognition | familiar forcing moment | repeated failed object/state | curiosity or concern |
| curiosity | precise missing information | empty slot, mismatch, incomplete action | clarity |
| surprise | state violates expectation | result first, contradiction, interruption | orientation |
| confusion | competing states or unclear owner | tangled path, duplicate label | clarity/control |
| frustration | visible failed attempt | blocked target, repeated loop | agency |
| concern | bounded consequence | timer, missing proof, unsafe route | guarded action |
| skepticism | unsupported claim | empty receipt or hidden evidence | cautious confidence |
| overload | too many objects/steps | cluttered queue or taxonomy | control |
| tension | obstacle delays objective | gate, collision, countdown | bounded relief |
| agency | understandable action exists | hand changes target state | confidence |
| clarity | missing distinction becomes visible | sorted board, revealed condition | confidence |
| cautious confidence | proof plus boundary | receipt beside LIMIT panel | bounded relief |
| bounded relief | objective resolved within limits | stable target plus visible rule | handback/action |

Emotion intensity: `low`, `medium`, `high`. Default to low/medium. High intensity requires evidence and a non-manipulative reason.

## Hook devices

Controlled devices: `visible_anomaly`, `consequence_first`, `empty_proof_slot`, `contradiction`, `failed_action`, `precise_question`, `finite_count`, `before_after`, `unexpected_object_metaphor`, `time_or_resource_constraint`, `recognition_statement`, `process_already_moving`.

Hook promise type: `answer`, `diagnosis`, `demonstration`, `comparison`, `transformation`, `proof`, `procedure`, or `bounded_reframe`.

Reject `generic_warning`, `unsupported_superlative`, `fake_urgency`, `shame`, `celebrity_borrowing`, `open_loop_without_closure`, and `result_claim_without_evidence`.

## Visual and B-roll taxonomy

- Scene topology: single workspace, split comparison, linear route, branching diagnostic, loop/interruption, ladder, conveyor/process line, claim/evidence reveal, balanced contradiction, metaphor-to-workflow mapping.
- Visual operation: reveal, route, sort, assign, connect, block, remove, compare, transform, count, trace, test, verify, rewind, map, hand back.
- Shot scale: extreme close, close, macro, medium, wide, over-shoulder, top-down, diagram/schematic.
- Camera motive: isolate anomaly, reveal geography, follow action, expose hidden relation, transfer action→proof attention, hold comparison, signal event boundary, return to whole.
- Continuity anchors: persistent target, screen location, direction vector, semantic color, repeated audio phrase, actor gesture, shape/token.
- B-roll function: context, abstraction-to-object, process demonstration, proof, contrast, event reset, emotional texture, interface orientation, transition cover.

## Proof and limitation taxonomy

Proof types: receipt/log, timestamp, source link, before/after target, worked example, process trace, test result, comparison criterion, checklist state, human approval, bounded demonstration, direct observation.

Limitation types: scope, sample, time/freshness, rights/access, mechanism, platform, audience, causality, reliability, human-decision, untested-condition, illustrative-only.

Performance claim state: `not_claimed`, `platform_guidance`, `public_snapshot_only`, `observed_owned_metric`, `owned_comparison`, `causal_not_established`. Never convert views, likes or examples into virality proof.

## Evidence depth

- D0: source URL/identity only.
- D1: metadata and dated public metrics.
- D2: transcript/caption architecture.
- D3: admitted frame/shot/caption/effect observation.
- D4: rights-approved owned analytics or experiment.

Missing deeper evidence stays null/GAP; it is not inferred from lower depth.

