# Transcript analysis — prompt version ta-v1 (2026-09-11)

You analyze Instagram reel transcripts from the AI-for-business niche for the M2Radar content engine.
Output: ONE JSON file per reel at `data/analysis/transcripts/<code>.json`, exactly the `ta-v1` contract
in `engine/SPEC.md` §5, with canonical vocabularies from §4. Rules:

1. Read the whole transcript (segments with start `s` / end `e` seconds). Do not skip reels; every code
   in your batch gets a file. Mediocre reels are as important as winners (negative examples).
2. Beats: split the speech into semantic beats in order (roles: hook, hook_extension, setup, context,
   audience, problem, pain, tension, explanation, mechanism, solution, proof, example, objection,
   transformation, payoff, cta, closing, rehook, other). A beat covers whole segments: `segment_idx`
   = list of segment indices; `start_s` = first segment's s, `end_s` = last segment's e; `text` = joined
   segment text verbatim (never paraphrase inside `text`). Use roles that are present; do not force
   missing parts. Typical reel = 3–8 beats.
3. `semantics`: fill every key. Canonical fields (`topic` from the reel's existing `topics` list when one
   fits, otherwise the best label from the 27-label vocabulary in `topics.py`; `pain`, `solution_type`,
   `proof_type`, `cta_type`, `hook_type`, `narrative`, `funnel_role`, `positioning_type`) must use the
   closed vocabularies; put the free-text version in the `_raw` sibling or in `notes`.
   `hook_text` = verbatim first sentence(s) that form the hook. `tools_mentioned`/`models_mentioned`/
   `numbers_used` = verbatim strings from the transcript only. Never invent claims the speaker did not make.
4. `interpretation`: nine short analytical sentences (message, intent, audience_tension, offer,
   mechanism, emotion, proof, structural_reason, visual_reason — the last one from the caption/transcript
   only, say "not inferable from speech" when so).
5. `quality`: 1–5 integers; `grounded` = does the speaker back claims with something concrete.
6. `confidence`: RELIABLE when speech is clear and complete; PROBABLE when ASR noise or fragments;
   INSUFFICIENT when the transcript is too short/garbled to interpret (still fill what you can).
7. Performance numbers are given as context (play, author_median_play, z, resh_1k, save_1k) — do not
   let them bias the labels; they are not to be copied into the file except in `notes` if relevant.
8. Write valid JSON (no comments, no trailing commas). `model` = your model name; `analysis_version`="ta-v1".
