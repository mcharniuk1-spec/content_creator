# Reconciliation implementation receipt — 14 September 2026

Base: Michael main `665ecb01a06f57f72352051e099eff63be2cf3bb`. Portable source ancestry: Content Creator `d5e446ce7cdafbf6d2e3d92ed486ac01347bdecd`, supplemented by retained local media/recovery modules. Partner Latest and Max fork were still `6462f409cd5f5c89cb9bc72e79f93e52f853907b` before this delivery.

## What changed

- Preserved partner operational engine and restored missing portable M2 Signal/Studio/orchestrator modules, schemas and tests. No frozen YouTube runtime is in the active Reel trace.
- Added original-language detection provenance. New local non-English ASR skips remaining lazy transcription. Historical text remains separate evidence. Legacy unknown-language records do not pass card, semantic or statistical-feature selection until reconciled.
- Corrected transcript endpoint labels and malformed/NaN timing acceptance; endpoint reach remains only a screening heuristic, not word-level accuracy or speech completeness.
- Corrected combined share/save missingness. Metric-only observations remain available even when English/relevance evidence is absent.
- Shortlist regeneration requires fresh validated output and preserves earlier bytes; PM output cannot silently reuse an old report after failure. PM synthesis has read-only tools.
- Notion fallback clearly labels coverage-only inventory and does not present missing-release historic insights as current findings.
- Added disabled fal.ai transport through existing request-hash/budget controls and an ignored local credential loader. No paid calls or model-quality claims.

## Validation

Portable and partner suite: **507 passed, 12 skipped, 2 deselected**, plus 30 subtests, using existing Python runtimes. Two real Chrome PDF tests crashed with SIGABRT and were explicitly excluded from the final pass. Local media/production suites could not collect because `imageio_ffmpeg` is absent in the test runtime; they were not certified. No dependency installed. Focused language, stale-output, secret-loader, fal, statistics and projection tests passed. No end-to-end server or provider execution was performed.

## Database evidence and limitations

The separately retained local evidence export contains 2,352 unique Reels and real source-level transcripts and frames. It is private and excluded from Git. The 1,062 completed/timing-flagged ASR count and 19,808 frame records refer to that store. Michael's live `radar.db` is excluded from Git and unavailable here; no current merged-data or server-deployment claim is made. A current consistent backup is required to join the populations and reconcile evidence versions.

This is a reviewed code correction and migration preparation, not final product acceptance. Pending: true speech-coverage/acoustic benchmark, bounded legacy language recheck/import, media-hash binding for all language decisions, review-ready reference gating, scheduler lease/retry hardening, generated-asset persistence/QA, full Notion release replacement and Supabase/R2 migration rehearsal.

Read [three-stage contract](m2-three-stage-reconciliation.md), [executor plan](m2-shared-server-executor-plan.md), [fal integration](m2-fal-integration.md), and [historical knowledge](m2-legacy-knowledge-summary.md). The attached V4 prompt remains design context; current owner instructions defer new card generation, paid generation and deployment until database review and decisions.
