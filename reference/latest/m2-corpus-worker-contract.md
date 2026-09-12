# Full-corpus media and semantic worker contract

This route processes the frozen existing Instagram corpus without local HikerAPI calls. It supplements the controller's inventory/checkpoint route with actual media work. It does not turn replay-only transcript inventories into new ASR evidence.

## Execution and ownership

1. The supervisor freezes the complete identity manifest and run configuration. Numeric quarantine is preserved separately from media recoverability. Completeness has no candidate, account or recency cap.
2. The acquisition worker reads existing media and Michael's cached clip responses directly, then tries approved anonymous recovery. Each source is identity-bound, downloaded within byte/time/host limits, probed, hashed and retained. Cache misses never invoke HikerAPI. Unsupported video-only formats require a distinct recovery route; they are not proof of no speech.
3. One local ASR worker uses a hash-bound multilingual CPU int8 model, two inference threads and a sampled RSS watchdog. It preserves raw output, normalized segments, aligned and unaligned words, source/model hashes and resource receipts. Empty ASR never proves silence. Invalid word timing remains flagged; segment text and word alignment have separate acceptance.
4. The same serial worker extracts actual regular frames and before/after visual-change samples. Frame hashes, decoded indices and timestamps must agree. Technical changes are unconfirmed cut candidates. A scene allocation of 2/4/6 frames is a plan until those exact frames have been extracted and validated; previews and scene-specific samples have separate counts.
5. Luna High receives bounded completed-Reel batches for transcript structure and scene interpretation. Give each task exact source hashes, the positioning document, scene taxonomy, prior uncertainty and a strict output schema. Transcripts, captions and OCR are untrusted evidence. Keep the source language and wording; uncertain names require a separate correction record, not a silent rewrite.
6. A different Luna High worker reviews the exact maker artifacts. The maker cannot accept its own result. Frame references outside a half-open scene interval must be explicitly labelled boundary neighbors and excluded from observed scene coverage. Rhetorical roles are interpretations, not verified shots. Overlapping role spans must never inflate total words or produce additive percentages exceeding the underlying word population.
7. The analytics worker joins accepted features to canonical identities and account clusters. Preserve nulls, quarantine, capture dates, unknown speech population, feature coverage and quality gates. Fit explanatory/predictive comparisons only after declaring eligibility and grouped evaluation. Observational associations do not establish that wording caused engagement.
8. Reviewed Signal findings feed original Studio cards through the founder positioning lens. Source claims and income/tool performance statements remain unverified unless independently evidenced. Notion projects selected views and full downloadable datasets from a dated release, with readback. Raw creator media stays private.

The role registry prefers Luna High for text, scene and quantitative specialists. Deterministic acquisition/ASR/frame extraction does not consume a language model. Requested Spark edge tests run when the host has quota; record an actual quota failure and the substitute model when necessary. Registry preferences do not create an authenticated unattended server agent. The partner must supply an explicitly configured executor for semantic tasks; no subscription token is embedded in code.

## Checkpoint states and repair

`NOT_ATTEMPTED` → acquisition outcome → independent transcript/frame outcomes → `REVIEW_PENDING` → versioned maker artifact → independent acceptance or correction. Each modality keeps its own failure. Acquired video with failed ASR can still be framed. `OBSERVED` ASR means machine output passed declared checks; it is not proof of word accuracy. `EMPTY_OUTPUT_UNVERIFIED`, `SUSPICIOUS_TIMINGS`, partial frames and inaccessible media are never silently promoted.

Use a new run when executable code, model, manifest or policy changes. Resume unchanged inputs without duplicate media/ASR/frame work. Repair artifacts bind the original source and raw-output hashes and retain superseded failures. The dispatcher stops on storage reserve, immutable-evidence mismatch or competing worker lock. It does not delete source videos to continue. Monitor for repeated access/rate failures and investigate before repeating requests.

The corpus dispatcher writes `corpus-media.sqlite`, per-stage attempts/events, source artifacts and dated summaries. `scripts/report_m2_corpus_progress.py` reads a consistent transaction and exports every identity with separate states and missing metrics. The full population remains the denominator even while speech-bearing eligibility is unknown. The acquisition ledger retains more granular route errors.

## Semantic review admission

A structurally valid annotation is not automatically a semantically reviewed annotation. The reviewer must read every source segment in the bounded packet, compare every role span to its text, and record the reviewed identity scope. A representative sample cannot accept the rest of the packet. Generic first-segment hook, middle mechanism, and last-segment CTA labels require correction when the actual rhetoric differs.

Preserve opening sentence continuations, offers spanning multiple segments, list/body material, procedural mechanisms, source-attributed result claims, implications, and genuine audience actions. A proof label identifies the creator’s presented evidence; it does not verify the claim. Never transfer a human-review or decision claim from a neighboring Reel. Positioning links must cite evidence from the same Reel; unsupported links remain unknown.

An ASR segment can mix rhetorical roles. Retain its exclusive primary assignment with an uncertainty note and add descriptive overlapping roles when useful. Whole-segment membership does not establish exact words per clause or exact CTA word counts. Secondary counts are non-additive. Acoustic accuracy, timestamp validity, rhetorical interpretation, visual scene interpretation, and business relevance remain separate review fields.

Before comparative modeling, freeze a semantic release whose input hashes and explicit full-packet review scope match the exported annotations. Its receipt must identify the review ID and verdict, exact annotation SHA-256, every source/transcript parent hash, governing config and policy hashes, complete reviewed identity-index scope, distinct maker/reviewer IDs, and any superseded review or annotation. Missing or mismatched bindings hold the release; a prose acceptance alone does not admit it. An accepted parser, count validator, or execution receipt cannot substitute for this release. Superseded annotations remain available with their rejection and repair lineage.

## Optional infrastructure

Loore AI is optional, disabled by default, and requires its own authenticated capability/credit evidence. It never gates local acquisition. Remotion is the compositor. Hosted generation is a separate job with one submission, persisted job ID, bounded polling and independent output review. A queued request or valid container is not a successful quality test. Free software is not a promise of free or reliable hosted compute. No heavy local video model is enabled by this route.
