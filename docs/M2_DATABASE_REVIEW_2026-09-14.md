# M2 database and architecture review — 14 September 2026

## What this review establishes

The thousand local transcripts and roughly nineteen thousand frames are real retained artifacts. They were not the same population or unit as the 91-record export or Michael's approximately 300 transcript rows. The main failure is that different checkpoints and databases were repeatedly presented as one current analytical state, without a code-level union, consistent language qualification or independent transcript acceptance.

The local database is now exported into a documented 22-sheet Excel workbook and a new normalized SQLite evidence snapshot. Original transcript text and segments are preserved. This is a **local evidence reconciliation**, not yet the union with Michael's live database: his runtime `data/radar.db` is excluded from Git, and this machine has no configured server alias. A consistent server backup/access remains the critical missing input.

## Exact local inventory

| Object | Count | Interpretation |
|---|---:|---|
| Canonical Reels | 2,352 | Unique code identities |
| Raw source observations | 2,363 | Repeated/conflicting source rows retained |
| Accounts | 100 | Dated local Signal account population |
| Retained videos | 1,201 | 51.1% of canonical Reels |
| Completed/timing-flagged nonempty ASR | 1,062 | 45.2%; 954 OBSERVED plus 108 SUSPICIOUS_TIMINGS |
| Additional nonempty failed-ASR fragment | 1 | Preserved, not counted as completed |
| Empty/unverified outputs | 24 | Not proof of silence |
| Frame-bearing Reels | 1,194 | 50.8%; primary scene review still pending |
| Individual frames | 19,808 | Frame records, not videos or insights |
| Original raw ASR segments | 18,940 | Segment text, not summaries or inferred word timings |
| Attempts / events | 3,661 / 7,633 | Processing history, not corpus size |

All 4,569 selected JSON artifact bindings exist and match their recorded hashes. All 19,808 frame paths exist; this review did not rehash every frame/video byte. The workbook's 1,243,361 cells match the extracted values and its package relationships validate. The normalized export has 2,352 unique Reel codes and passes SQLite integrity checks.

The active source is the migrated local corpus outside Documents/iCloud, not the old quiescent repository copy. The Excel **Source provenance**, **Artifact verification**, **Transcripts**, **Transcript segments**, **Frames** and **Acquisition** sheets expose the records and paths. The original 91-record source is retained separately as **Legacy ASR segments**, with 1,872 segments; it is not added to the later corpus as new identities. No YouTube rows are included.

## What the language evidence actually says

Every artifact-bearing local request used automatic detection. Within the 1,062 completed/timing-flagged outputs, detector labels are English 963, Hindi 82, Punjabi 4, jw 4, Arabic 3, Portuguese 3, nn 1, Tamil 1 and Urdu 1. Thus 90.7% of that machine-output group is detector-English, and detector-English outputs cover 40.9% of all 2,352 Reels. Neither percentage is a verified full-transcription accuracy rate. The additional failed fragment is labelled Punjabi.

This disproves the broad claim that all old local transcripts were forced English or all were bad. It also proves that non-English material entered the local corpus. The model's language probability and original request parameters are retained in Excel. Accented English must not be rejected based on a creator's country, name or writing style. Mixed/uncertain speech needs review; language detection itself can err.

For future collection, detect language first and stop the ASR iterator when it is non-English. Store EXCLUDED_NON_ENGLISH or LANGUAGE_UNKNOWN and retain the existing evidence. Do not translate. Read the whole English transcript in sequence, attach each insight to actual spans, and verify names and important claims against audio. A last segment reaching 90% of the video is only endpoint reach: it cannot prove that the preceding speech was captured. A three-second ending alone can falsely score 100%; a silent ending can unfairly lower a good transcript's score.

## Account mix, categories and statistics

Ninety-two of the 100 accounts have at least one nonempty raw output; eight have none. Coverage is uneven, so an account with more processed clips can dominate apparent findings. Fifty-seven account profile categories are missing. The remaining labels include Entrepreneur 18, Digital creator 13 and Education 5. These profile labels are not a business-workflow taxonomy.

The dated topic window has 844 rows and 27 multi-valued labels. Examples include programming/code 131, AI video/content production 108, Claude Code skills/plugins/commands 105 and model/lab news 96. Another label, “no topic in caption,” appears 154 times; it is missing classification, not a niche. These are inherited caption-window labels, not new whole-transcript semantic findings. Multi-label counts overlap.

Among 2,340 numerically valid Reels, views range from 52 to 54,962,152 and the median is 12,802.5. That enormous spread makes pooled averages poor editorial guidance. Different prior medians can reflect different eligibility denominators; 2,340 valid records is not the same subset as 2,160 exposure-eligible records. Excel separates per-account distributions, metric definitions, snapshots and quality states. Missing counts remain missing, not zero.

No reliable English-qualified winner ranking can yet be claimed from the current partner report. Its analysed population was selected toward high-ranked Reels and mixes uncertain language/semantics. Retain descriptive account comparisons; rebuild category performance on the new cohort. Prefer median/IQR and p10/p90 alongside means/standard deviations and N creators. Separate shares per 1,000, saves per 1,000 and creator-relative views. Combined shares+saves requires both counts; `views/baseline` is a multiple, while `views/baseline−1` is relative lift.

Recommended ranking is evidence and SME relevance first, then creator/exposure-adjusted share/save performance with creator caps. Alternative two is reach discovery for finding hooks; alternative three is a stratified high/middle/low comparison set for studying categories. They answer different questions and should not be compressed into an unexplained score. Multiple insights per Reel should be child rows, with category, exact transcript span, meaning, confidence and source version.

## Hiker, local ASR and Loore

Michael's collector takes one page of recent Reels per active roster account through Hiker's clips endpoint; roster search/suggested-account discovery is a separate path. His September 14 handoff reports 130 accounts, 1,534 collected observations and 1,529 scored, with 1,400 above its threshold. These are partner-reported run figures, not newly queried database counts. One recent page per creator is not an exhaustive history or a representative niche sample.

Hiker supplies caption/identity/metrics and media locators. Local download/ASR/frame extraction creates the speech and visual evidence. The retained local acquisition records report 1,198 public-Reel routes and three existing-media routes; that does not mean this review called Hiker. No current Loore rows were supplied by these databases, so its use elsewhere remains unknown. Excel labels the gap rather than pretending another source is Loore.

The latest handoff flags a possible 20× error in the assumed Hiker unit price. Do not replace that price using an inferred balance ratio; reconcile a dated billing receipt and actual charged units first. No paid calls were made here.

## Michael's updates, missing work and the failed automation

Reviewed main is `665ecb01a06f57f72352051e099eff63be2cf3bb`, including September 13–14 language detection, evidence gates, shortlist/block routing, PM reports, a 100-minute deep-dive budget and restored 14-day freshness. The failed weekly run reportedly completed collection but hit the two-hour outer watchdog at 60 of 100 deep dives. Its success-only branch skipped the remaining steps. New per-step timing and a six-hour outer limit address that specific problem; a cooperative deadline still cannot kill one hung call without its own timeout.

The merge was not fully consistent. Max's fork retained recovery/server-adapter modules, editorial handoffs and knowledge that were missing from the operational tree. This integration restores those paths and preserves both Git ancestries. Michael's practical operational engine is retained. Raw private data was not magically merged by that code merge. The 1,062 import remained an explicit outstanding item in the dated handoff.

Additional corrected defects: stale PM output could be applied after failure; stale valid shortlist files could count as fresh generation; missing outputs could still produce DONE; language labels could be inferred from old text; missing save/share values became zeros; fallback reporting used stronger labels than the evidence justified. Remaining structural work includes atomic worker leases, robust crash recovery, full corpus import/version selection, acoustic benchmarking and final reference/rights gates. The code release is not full production acceptance.

## Why the cards and Notion report were weak

The older cards often converted internal pipeline problems into generalized AI-governance lessons. A reference URL was sometimes present without a reviewed transcript/visual mechanism explaining why it was selected. Earlier semantic audits also documented truncated CTAs, generic body-as-mechanism labels and a claim transferred between Reels. That can produce confident but unhelpful scripts even when the ASR text exists.

The corrected writing brief chooses one primary viewer—owner/C-level, manager or worker—and one named business task. State the specific pain/result immediately, demonstrate the mechanism, distinguish observed proof from illustration, and give a usable next action. Owner content earns attention through a business decision; manager content supplies technical evidence; worker content reduces complexity. The Luna audience synthesis is an editorial proposal grounded in existing positioning, not new audience-demographic research.

The fetched Notion page was still generated from commit c6ca5dc and explicitly using fallback analytics. Its historical insights, selected-sample statistics and current architecture were presented together, creating an unclear narrative. A reconciliation notice is now inserted and read back. The code labels fallback as coverage-only and suppresses historic recommendations when the analysis release is missing. The next full projection must tell one story: objective → cohort and exclusions → coverage → evidence-linked findings → decisions → plan. It must not overwrite child databases or pretend the server union is complete.

## Production, shared infrastructure and next decisions

The product stages are Research; Scripting/generation/shooting; Post-production. The earlier phrase “three workflows” meant examples to demonstrate, not three required product modules. Choose those examples after the qualified reference review.

fal.ai is the selected API route, replacing Open-Generative-AI as an infrastructure option. There was no installed Open-Generative-AI runtime to remove. The added transport uses exact approved request hashes, explicit model routes, bounded responses and no blind submit retry. Your local key file is ignored and owner-only; a safe loader injects FAL_KEY without printing it. The adapter is disabled. A model-specific schema, measured price, accepted shot and output-ingestion/QA test are still required before paid use. One fal account can expose multiple model endpoints; no assumption that all models share input parameters or quality is valid.

Generated footage and owner footage enter an asset manifest, then Remotion composes captions, layouts and audio against an edit plan. Resolve is optional finishing through a tested bridge/interchange path. Installed MCP is not proof of a functioning editor session, and generated UI is not proof a tool works. No final video was generated or edited during this database review.

Supabase plus Cloudflare is the agreed future platform: relational state/auth in Supabase; private media in R2; interface/gateway/webhooks in Cloudflare; ASR/FFmpeg/Remotion on a supervised VPS/container worker. Keep separate member accounts. Codex and Claude use one scoped project API/MCP, not shared plaintext credentials. No deployment occurred. The executor guide covers backup, normalized import, idempotent jobs, migration rehearsal, object backups and rollback.

At the partner's reported 114 seconds per Reel, 300 clips would be about 9.5 serial hours and 1,000 about 31.7 hours before retries. This is an illustration, not a measured forecast for your eligible backlog. Reuse existing artifacts, reject non-English early, benchmark a stratified sample and then estimate concurrency. Deterministic workers can run unattended; semantic analysis requires a configured bounded model executor, not a permanently open chat agent.

## Reading order

See M2_RECONCILIATION_2026-09-14.md, m2-three-stage-reconciliation.md, m2-shared-server-executor-plan.md, m2-fal-integration.md and m2-legacy-knowledge-summary.md in this directory. Private source exports and detailed audit receipts remain in the owner workspace and are excluded from Git.
