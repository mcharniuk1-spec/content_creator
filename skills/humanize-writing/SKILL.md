---
name: humanize-writing-m2
description: Fact-preserving editorial workflow for M2 Lab content outputs such as reels scripts, captions, research summaries, and handoff notes. Use for final prose that should sound natural, practical, and brand-consistent.
---

# Humanize writing for M2 content engine

## Purpose

Use this skill to convert stiff, repetitive, or generic draft text into natural, production-ready M2 writing while preserving truth, evidence, and task constraints. This is an editorial skill only; it is not a detector evasion or authorship tool.

## Scope

Apply to:
- M2 Lab Instagram Reels scripts (voice-over, captions, hooks)
- Storyboard captions and shot notes
- Research-to-action summaries
- Internal handoff text that is shared with makers/reviewers

Do not use this for policy/legal/compliance/legalese, deeply technical code prose, or external social posting policy drafting.

## Modes

- **Light mode**: for ordinary writing polish. Improve flow, clarity, brevity, and tone fit while preserving meaning and evidence.
- **Full mode**: when user explicitly asks to humanize/de-slop/rewrite in a specific voice. Rework structure, argument rhythm, and narrative shape, not just words.

## Workflow

1. **Collect constraints first**
   - Audience (owner, creator, reviewer, buyer-facing, etc.)
   - Channel (IG Reel, caption, document, note)
   - Time/length constraints (e.g., 15–60 sec script)
   - Allowed style or voice notes
   - Evidence status and uncertainty flags

2. **Protect invariants**
   - Preserve all numbers, dates, names, evidence tags/IDs, links, filenames, percentages, and claims that are already substantiated.
   - Keep hashtags, file references, legal disclaimers, structured fields, and required checklists unchanged unless user asks for a factual correction.

3. **Check claim safety**
   - For each claim that sounds like performance, benefit, or result: confirm whether evidence is explicit in the provided material.
   - If evidence is weak, rewrite to uncertainty-aware language and mark missingness explicitly.

4. **Match channel voice**
   - For Reel scripts: prioritize spoken rhythm, short sentences, clear action verbs, and one idea per sentence.
   - For captions/notes: prioritize readability, skimmability, and explicit next-step clarity.

5. **Rewrite clusters, not single words**
   - In full mode, replace repetitive phrasing patterns (generic praise, symmetric constructions, vague hype nouns, repeated transitions) with concrete structure and sharper specificity.
   - Do not run synonym-only edits.

6. **Return and audit**
   - Compare before/after for meaning drift and invariant preservation.
   - Surface any unresolved gap in a short note.

## Output shape

- Light mode: return rewritten copy.
- Full mode: return
  1. rewritten copy
  2. short edit note (pattern-level changes)
  3. short evidence gap note

Use the same language and formatting conventions as the input when possible.

## Non-negotiables

- Do not invent customer stories, outcomes, or metrics.
- Do not invent claims not supported by the provided material.
- Do not use translator hops or hidden-detector loops.
- Keep legitimate idiosyncrasies (dialect, cadence, formatting style) when they are explicitly part of the approved voice.
- For marketing-oriented content, clearly separate what is demonstrated, what is recommendation, and what remains hypothesis.

## Evidence-bound spoken-script pass

After source analysis and before independent card review: name the viewer's concrete problem in the opening; promise only what the body delivers; keep one central problem; make every sentence add information, proof or resolution. Close the opening question before the CTA. Prefer an action the viewer can try over generic engagement requests.

Keep planned duration and word count separate from an actual spoken timing check. Human recording has not been timed until it exists. Read aloud when possible; otherwise mark spoken pacing as editorial estimate. Visuals must clarify the spoken line, not hide an unsupported promise. Replace abstract internal terms with concrete tasks; never imitate a creator's voice.

Secondary method reference: knowledge/studio/creator-techniques-20260907.md and its independently reviewed source candidate. These prompts do not establish performance.
