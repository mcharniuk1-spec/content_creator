---
date: 2026-08-25
type: decision
tags: [decision, agents, retrieval, signal-to-studio, memory-promotion, clean-room]
related-projects: ["[[ArchFlow Content Engine]]", "[[Signal Research Engine]]", "[[WikiLLM]]"]
confidence: high
sources: ["[[Studio Screenwriting Knowledge Index]]", "runs/20260825-studio-screenplay-v2/agent-handout.md"]
ai-first: true
---

# Studio Agent Retrieval and Learning Contract

## For future Claude
This note defines how research observations become reusable Studio inputs without turning Obsidian into a raw-media database or teaching agents to copy creators. Use it when designing a research query, selecting frameworks, promoting insights, or updating the Signal-to-Studio schema.

## System boundary

```text
public/approved source
→ immutable source + rights + freshness record
→ observation at proved evidence depth
→ multi-axis classification
→ clean-room structural abstraction
→ original story contract
→ local previsualization
→ independent review
→ owner-approved production/experiment
→ reviewed learning candidate
→ WikiLLM/Obsidian promotion
```

- PostgreSQL/raw artifacts are evidence stores after executed ingestion.
- Signal owns source observations, creator/content IDs, rights, freshness, metrics and evidence depth.
- Studio owns original story contracts, continuity, prompts, frame plans and production hypotheses.
- Obsidian/WikiLLM owns curated cross-run meaning, decisions and navigation—not raw captions, comments, frames or note-per-creator dossiers.

## Research agent output contract

For each content observation return:

1. Stable source/content/creator IDs and observed date.
2. Rights and access state.
3. Evidence depth D0–D4 and exact missing layers.
4. Transcript architecture as functions, not copied text.
5. Topic, creator archetype, audience segment/job and knowledge level.
6. Emotional entry, transition and exit with intensity.
7. Hook device/family and the exact answer/payoff relationship.
8. B-roll functions, visual operations and continuity anchors only when D3 evidence exists.
9. Proof/limitation types and unsupported claims.
10. FACT / INTERPRETATION / HYPOTHESIS / GAP separation.

## Studio retrieval recipe

Given a new A-roll transcript or topic:

1. Identify the audience forcing moment and job.
2. Extract only concrete nouns, verbs, constraints and evidence objects.
3. Select an emotional entry→exit pair appropriate to the claim.
4. Retrieve candidate story families by viewer state, not popularity.
5. Retrieve B-roll functions needed to make the argument inspectable.
6. Choose a proof and limitation matching the claim type.
7. Generate at least three combinations varying semantic premise, causal topology and visual mechanism.
8. Reject any combination too close to a source’s wording, characters, branded UI, distinctive metaphor, shot order, composition, music, face, voice or CTA.
9. Build stateful frames and validate continuity, information gain and closure.
10. Preserve all choices and rejected reasons in the package report.

Example query:

```text
audience_job=diagnose_failure
topic=workflow_operations.handoff
creator_archetype=analyst-diagnostician
emotional_arc=confusion>clarity
evidence_depth>=D2
proof_type=process_trace
limitation_type=human-decision
exclude=performance_claims,source_expression
```

## Selection scoring

Score 0–2 on each axis:

- forcing-moment relevance;
- visible causal change;
- audience comprehension;
- proof inspectability;
- limitation honesty;
- A-roll/B-roll complementarity;
- emotional appropriateness;
- clean-room distance;
- asset feasibility/rights;
- experimental clarity.

Reject if any of proof, limitation, rights or clean-room distance scores 0. Do not compensate a safety failure with a high total.

## Learning and promotion gates

Run-local observations remain local. Promote only when:

- the finding repeats across independently sourced examples or a reviewed owned experiment;
- provenance, dates, audience, topic and execution context are preserved;
- contradictions and negative results are retained;
- the conclusion is useful beyond one edit;
- a reviewer distinguishes observation from interpretation;
- older memory is superseded explicitly rather than silently rewritten.

Promotable memory examples:

- stable schema/rights constraints;
- repeated production failure and repair patterns;
- corrected assumptions about evidence depth;
- independently reviewed cross-run relationships between audience job, story form and comprehension.

Do not promote:

- raw transcripts/comments/frames;
- transient public counts;
- isolated creator tactics;
- unreviewed agent output;
- source wording or distinctive creative expression;
- “viral” causality inferred from views;
- private identities, secrets or source access details.

## Experiment contract

For owned tests freeze audience, topic, duration band, caption treatment, publication context and metric window. Change one declared variable such as hook state, proof object or handback. Predefine minimum sample and decision rule. Record retention/skip/rewatch separately from confusion, sentiment and conversion. A result stays local to audience, topic, time and execution until replicated.

## Current GAPs

- No admitted source-frame dataset connects transcript functions to real shot/effect timing.
- No Instagram/Meta synthesis was promoted from the inaccessible registered route.
- No universal cut rate, caption speed, B-roll frequency or hook formula is established.
- No owned experiment validates the 50-framework library’s performance.
- No final production assets, motion/audio, platform-safe-zone QA, publication or feedback ingestion exists.

