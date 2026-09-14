# M2 Lab — full execution and architecture report

**Run:** `m2-20260911-reconciled-v2`  
**Language:** English  
**Status:** `PASS_WITH_LIMITATIONS`

## Executive conclusion

The earlier summary was incorrect about transcript coverage. The repository contains the full local execution handoff for the newer run. The authoritative run has **2,352 canonical Reels, 1,201 retained videos, 1,062 non-empty machine transcript outputs, 1,194 frame sets, and 1,158 Reels not yet attempted for transcript/frame processing**. The 91-record package is legacy evidence, not the whole current transcript ledger.

The run materially improved acquisition, identity, hash lineage, ASR attempts, frame extraction, recovery, and resumability. It did not complete the full population, and it did not convert all machine outputs into accepted semantic evidence. Therefore this report uses the complete available run artifacts, but keeps transcript quality, scene review, causal performance, and final-best status explicitly limited.

## What was reviewed

- M2 system architecture, operator guide, role registry, transcript benchmark, positioning, and scriptwriter contract.
- `runs/20260906-media-acquisition-v1/current-status.md` and `handoff-20260907/full-report.md`.
- `pilot-controller-r1/signal/summary.json`, `status.json`, and runtime state.
- `structural-feature-checkpoints/0004/`, recovery overlays, semantic-review receipts, frame/scene pilot artifacts, and the local M2Radar data package.
- M2 Lab audit, content plan, and Brandbook v2.

## Execution chain

1. **Admission and freeze:** provider-disabled, Instagram Reels only, immutable run/config identity, role separation.
2. **Inventory and normalization:** canonical identity manifest, account/reel joins, null-preserving metric normalization, quarantine of conflicts.
3. **Acquisition:** cache-only Hiker response parsing and bounded anonymous media acquisition; no local HikerAPI call in this review.
4. **Transcript processing:** local Faster-Whisper attempts with source audio, model, config, segment, and artifact lineage.
5. **Visual processing:** regular/change-frame extraction and scene candidates. Technical frames are not automatically semantic scenes.
6. **Structural analysis:** hook/body/ending partitions, lexical counts, timing checks, and account-aware descriptive metrics.
7. **Semantic review:** maker/reviewer lanes with source-byte and count binding. Only reviewed subsets can support precise claims.
8. **Studio handoff:** original ScriptCard candidates, timed scenes, proof states, rights state, owner gate, and publication separation.

## Verified population and denominators

| Layer | Count | Meaning |
|---|---:|---|
| Canonical Reels | 2,352 | Fixed population |
| Source observations | 2,363 | Raw normalized observations |
| Retained media | 1,201 | Successfully retained/validated media |
| Acquisition unavailable | 58 | Route outcome, not permanent impossibility |
| Acquisition failed | 7 | Typed failure |
| Acquisition not attempted | 1,086 | Remaining population |
| Non-empty machine transcripts | 1,062 | 954 normal + 108 timing-flagged |
| Empty transcript outputs | 24 | Empty/unverified, not silence |
| ASR failures | 108 | No usable transcript claim |
| Transcript not attempted | 1,158 | Remaining population |
| Frame sets | 1,194 | Technical/visual evidence observed |
| Scene review pending | 1,194 | Not equivalent to accepted scenes |
| Scene/frame not attempted | 1,158 | Remaining population |
| Accepted structural checkpoint | 34 | Strict reviewed subset with limitations |
| Canonical quarantines | 12 | Conflicts blocked from analysis |

The legacy 91-record package remains preserved. A stable-ID overlap audit is still required before describing legacy and primary transcripts as unique additive records.

## Metrics and analytical interpretation

The Signal release uses within-account relative performance, robust-z components, MAD safeguards, exposure eligibility, null-preserving rates, and a diagnostic ranking queue. The observed release contains 2,160 exposure-eligible Reels; median views are 14,491.5, median duration 47.2 seconds, median reshares 6.09 per 1,000 views, and median saves 14.39 per 1,000 among observed saves. These are descriptive snapshot values, not causal or predictive results.

The user's quality hypothesis is operationalized as two separate reference cohorts:

- **Repeatable quality:** high account median, low dispersion around that median, adequate sample size, and stable interaction signal.
- **Breakout example:** unusually high Reel-to-own-median multiplier, used for hook/framing inspiration only.

No final Best Reel is accepted. The run explicitly reports `final_best_reels = 0` and keeps rights, text, scene, and independent-review gaps visible.

## Transcript and frame analysis method

The full machine transcript population was inventoried, not treated as fully reviewed. The safe analytical split is:

- machine output inventory: 1,062 non-empty records;
- timing-valid/quality-filtered subset: calculate from the run manifest, never infer;
- independently reviewed semantic subset: 34 accepted structural records at checkpoint 0004, with earlier annotations requiring revalidation;
- frame-observed population: 1,194;
- accepted semantic scenes: separate and smaller/unfinished;
- transcript-plus-frame intersection: calculate by canonical Reel ID, never sum denominators.

The structural review found generic mechanism labels, truncated CTAs, incorrect proof/implication assignments, and cross-Reel decision claims in earlier annotations. Those labels are not used as promoted statistical truth. The cards use reviewed structural principles and explicitly marked hypotheses.

## Architecture corrections applied to the card release

- Separate legacy transcripts, primary transcripts, and recovery overlays.
- Never add recovery attempts to primary totals without identity reconciliation.
- Require `hook`, `problem`, `mechanism`, `human_boundary`, and `CTA` extraction fields with timecodes and parent hashes.
- Separate technical cuts, frame observation, semantic scenes, and independent scene review.
- Use observed/planned/to-measure/missing proof states.
- Treat every reference as inspiration, not source footage or wording.
- Keep maker complete, independent review pending, and owner approval pending as separate states.

## What Michael's contribution changes

Michael's route contributes the expanded current primary ledger, retained media, frame sets, source/model/config lineage, resumable attempts, and new account/reel observations. It should be integrated incrementally by canonical Reel ID with a crosswalk:

`canonical_reel_id → code → account_id → source_media_hash → transcript_sha256 → frame_manifest_hash`.

Classify each join as `LEGACY_ONLY`, `PRIMARY_ONLY`, `OVERLAP_SAME_SOURCE`, `OVERLAP_DIFFERENT_SOURCE`, or `IDENTITY_UNRESOLVED`. Preserve both artifacts on conflicts and choose an analytical revision only after source, timing, language, and independent review checks.

## Limitations and not run

- Full 2,352-Reel media/transcript/scene completion: not achieved; stopped at storage/cache budget.
- Full semantic review of 1,062 transcripts: not achieved.
- Complete transcript/frame intersection: not yet calculated as an accepted release.
- Causal hook/framing effects, audience fit, ROI, reach, or business outcomes: not established.
- Provider generation, publication, Notion mutation, and live collection: not run in this review.
- Raw Michael 10 September handoff export is not present as a separate local input; its figures remain dated handoff evidence and must be crosswalked if imported.

## Validation receipt

- Source counts and authoritative runtime state inspected.
- Current status, full handoff, signal summary, stage status, and runtime state compared.
- PDF outputs generated from separate Markdown sources.
- No credentials, cookies, provider calls, publication, or remote Git write performed.

## Next safe execution

Create a new immutable continuation run using the authoritative local corpus root, calculate identity-level overlap with the legacy package and Michael's separate export, validate manifests/hashes, complete a bounded reviewed transcript/frame subset, then regenerate rankings and cards with exact evidence IDs. Do not mutate the frozen run or call the provider collector locally.
