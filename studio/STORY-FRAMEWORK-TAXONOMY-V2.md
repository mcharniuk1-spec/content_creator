# Sequential Story Framework Taxonomy v2

## Difference from v1

V1 classified hook, visual grammar, B-roll function, proof form, pacing, transition, A-roll, sound, text, and CTA. It was strong as a packaging/provenance system but its SVGs were abstract cards. V2 adds a causal story contract and visible entity continuity.

Every package now has:

- protagonist/POV, objective, obstacle, stakes, setup, inciting change, action chain, proof, limitation, payoff, and handback;
- continuity bible for hero, scene, trigger prop, proof prop, target prop, palette, screen direction, and forbidden changes;
- frame-level cause edges, state-before/state-after, story question, visible hero/object action, scene change, motivated shot/camera movement, information gain, A-roll/B-roll state, transition, audio, emotion, and replacement prompt;
- structured five-entity before/after maps, compound final roles, visible proof/payoff/handback flags, and semantic SVG `data-*` attributes for entity, state, operation, proof, and limitation;
- semantic, causal-graph, and visual-sequence fingerprints;
- clean-room risk notes, source truth, rights truth, and provider truth.

## Ten families × five scenarios = fifty packages

1. `in_medias_res`: start after the inciting state change.
2. `result_rewind`: outcome first, then recover the decisive step.
3. `diagnostic_mystery`: symptom, competing explanation, test, diagnosis.
4. `failed_attempt_correction`: visible failure becomes information.
5. `object_metaphor`: physical mechanism mapped back to a real workflow.
6. `countdown_ladder`: finite sequence whose last rung is a proof/limit check.
7. `before_after_transformation`: contrast plus visible conversion action.
8. `proof_reveal`: claim, missing field, evidence reveal, explicit boundary.
9. `contradiction_resolution`: expectation, contradiction, missing distinction, reframe.
10. `process_handback`: complete an input-to-output action under voice-over and return.

Each family has five different protagonist/objective/obstacle/prop/proof systems. All 50 semantic, causal, and visual fingerprints are unique.

## Hard validator rules

- Exactly 50 packages and 300 contiguous one-second SVG frames.
- Exactly five packages per family.
- Each story contains all mandatory narrative roles even when payoff/handback share a frame.
- Every frame changes declared state and cites the preceding causal frame.
- Every entity-state map is continuous; the affected target transition is exposed in both JSON and SVG semantics.
- Camera movement has an informational motivation.
- A-roll opens, B-roll carries the causal event, and the final state returns to A-roll.
- Every SVG contains visible action and cut-reason annotations.
- All files match package checksums; all paths are project-relative/public-safe.
- Every fingerprint is unique.
- Within each family, variants differ on at least three of operation type, target transformation, proof mechanism, and scene topology.
- Rights stay `original_local_previsualization`; providers and external writes stay `NOT_RUN`.

The validator proves structural consistency, not audience comprehension, originality against the entire internet, retention, virality, conversion, or production readiness. Those need independent review and owned tests.

## Scene-analysis extension

For source-video analysis and production handoff, use the scene-first v3 extension in `SCENE-FIRST-STORY-FRAMEWORK-TAXONOMY-V3.md` and `schemas/video-scene-segmentation.schema.json`. V2's six one-second frames remain a synthetic story scaffold; v3 scene-units carry transcript links, visual boundary reasons, start/end source frames, 2/4/6 screenshots, one collage, and voice/generation/edit/subtitle routes.
