---
project: m2lab
date: 2026-09-05
status: candidate-pending-independent-promotion
scope: reliability-and-interpretation
---

# M2 validation lessons

Related: [[m2-operating-memory]], [[m2-positioning]].

## Facts from the implementation checks

- Evidence IDs and content hashes serve different purposes. Two empty records
  may have the same content hash; joins must use unique record identities and
  independently verify their hashes. Require the source map and analysis IDs
  to form a bijection before quantitative analysis.
- A SQLite source must be opened read-only. Reject output aliases to every
  source, including hard links. A database's main-file hash alone can miss
  committed WAL changes; diagnostics uses a logical transaction snapshot hash.
- A cached export must still recheck bound artifact bytes. Successful export
  means a diagnostic report was written, not that every source stage passed.
- Notion values, source values and presentation nulls are distinct. Preserve
  unknown engagement counters as null. Document validity and minimum-support
  gates for derived nulls, and document any empty-text normalization.

## Statistical interpretation

- Resample complete account clusters when estimating uncertainty across Reels
  from the same account. Compute the same statistic on the observed sample and
  each resample. This does not correct a selected transcript sample or ASR error.
- Keep p/q unavailable when the significance procedure does not respect the
  dependence structure. A correct BH utility cannot repair invalid input
  p-values. Fit categorical vocabularies inside training folds.
- First/interior/last ASR segments are positional sections, not verified
  rhetorical or semantic scene boundaries. Missing source media cannot become
  verified silence, a scene count or words-per-scene through imputation.
- Small improvements in grouped holdout error are exploratory diagnostics.
  They do not establish a causal script rule or justify a production model.

## Resource and production boundary

Local generative-model outputs failed visual review, and a later MPS experiment
was interrupted after resource contention. Keep that backend unaccepted and
local heavy generation disabled. Token-free inference still consumes memory,
storage and compute. A valid video container is insufficient: require finite
outputs, prompt adherence, continuity and independent media QA.

Use one local job at a time and a host-specific measured budget. An advisory
profile cannot enforce total-device RAM. A future worker needs an OS/container
limit, timeout and cleanup path before unattended operation.

## Gaps and permitted reuse

These lessons guide engineering and interpretation. They do not promote any
creator's content, final Best-Reel selection, whole-corpus media coverage,
provider quality, server deployment or causal marketing claim. The full media
cache and a separately validated generation runtime remain necessary inputs.
