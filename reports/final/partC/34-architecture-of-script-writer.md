# 34. Architecture of the Script Writer

A card is the end of a nine-link chain, every link a real file or table: data →
analysis → insight → hypothesis → ranking → hypothesis-specific references →
transformation → script → review. Nothing after "insight" is invented at write time —
it is assembled from JSON and SQLite rows that already exist before a script-writer
prompt runs.

**Data to analysis.** The corpus starts as `reels`/`transcripts`/`frames` rows in
`db.py`'s legacy schema, passes through `engine/local_pipeline.py`, then two LLM
analysis passes: `engine/prompts/transcript-analysis.md` (schema `ta-v1`: beats,
semantics, hook/pain/proof/cta typing) and `engine/prompts/frame-analysis.md` (schema
`fa-v1`: per-frame labels and visual aggregates). `engine.ingest_analysis` loads both
into `beats`/`frame_labels`/`scenes`; `engine.features.build()` consolidates them plus
`engine.stats.py`'s performance columns into one `video_features` row per code
(`engine/SPEC.md` §5–§6).

**Analysis to insight to hypothesis.** `reports/analysis/08-hypotheses.md`: 30 numeric
insights (`data/analysis/insights.json`, I-01…I-30, each with `statement`,
`limitations`, `confidence` ∈ RELIABLE/PROBABLE/INSUFFICIENT) fed 24 hypotheses — 9 M2
Radar, 9 M2 Builds, 6 M2 Teardown, written before scoring so format mix wasn't an
artefact of ranking. Denominators are carried forward explicitly: 268 analysis-ready
reels for script/visual claims, 266 with both a semantic read and performance data, 132
creators with a stats row (17 CONSISTENT). `engine.ingest_insights` loads the JSON into
`insights`/`hypotheses`/`hypothesis_refs` and opens `jobs` rows at
`entity_kind='hypothesis'`, stages `CONCEPT_GENERATION` and `REFERENCE_SELECTION`
(`engine/ingest_insights.py:279-322`) — the only two jobs stages this whole
content-generation chain writes before Phase 3.

**Ranking.** Fourteen weighted keys (evidence and positioning at 0.12 each, assets and
copy_risk at 0.03), each scored 1–5, summed to a `total_score` on the same 1–5 scale
(`reports/analysis/08-hypotheses.md` §2). The cut to ten landed exactly on the 4 Radar /
4 Builds / 2 Teardown quota with a 0.49-point gap between the lowest selected hypothesis
(H-19, 4.16) and the highest rejected one (H-14, 3.67) — "a coincidence worth naming
rather than a validation of the weights," per the report itself.

**Hypothesis-specific references.** `reports/analysis/09-reference-selection.md`: 41
references across the 10 hypotheses, 27 distinct reels, in
`data/analysis/hypothesis_refs.json` and `hypothesis_refs`, each row carrying one named
`function` (hook/pain/explanation/proof/cta/a_roll/b_roll/split/screen_proof/rhythm/
transition — `engine/SPEC.md` §2.8), real beat/scene ids, a `performance_json` read from
`video_features` at generation time, and a `transformation` field. Seven rules govern
selection: CONSISTENT creators may contribute several references, a HIGH_VARIANCE
creator's multiplier is not comparable across reliability labels, gated CTA rates are
corrected for comment-gate inflation (×2.8 save, ×1.8 share, reach unchanged), a reel
serves two hypotheses only under two different functions, and no reel flagged unsafe on
content grounds is used.

**The input package the writer actually receives.** `engine/prompts/script-writer.md`
names it directly: the selected hypothesis and its `hypothesis_refs` rows (copied
verbatim from `data/analysis/hypothesis_refs.json`), plus `POSITIONING.md`,
`PRODUCTION.md` (the 50–70s one-location template), `RULES.md` §2–§4, and
`design/README.md` + `design/tokens/tokens.json` for overlay/caption constraints. Every
number the script states must come from `insights.json`, `reports/analysis/*.md`, a
reference reel's real metrics, or the team's own runs (`reports/audit/*.md`,
`reports/data/*.json`) — "we do not know yet" is the explicit fallback.

**Hard rules, a violation rejects the card.** The strategic filter is four literal,
non-empty fields (`process`, `friction`, `ai_boundary`, `next_action`); every claim
carries a state (OBSERVED/PLANNED/TO_MEASURE/MISSING); no comment-bait CTA
(`comment_keyword` is banned, per the insight that it inflates comment rate 23× while
reach moves not at all); originality means borrowing structure only, each borrowing
recorded in `references[].transformed_how` and `traceability`; timing runs 2.3–2.6
words/second within a 50–70s band; hooks ship 3 candidates.

**The card-v2 contract.** Output is one `cards/<card_id>.json`, schema `m2radar.card.v2`
(`engine/SPEC.md` §8), validated by `engine/cards_v2.py`'s `validate()` against closed
vocabularies (21-value `frame_type`, 13-value hook `type`, 9-value `cta_type`, the
4-value `layout` set the Remotion EDL contract also enforces) and structural rules
(contiguous storyboard scenes, `script.total_s` a hard error outside 20–120s, a warning
outside 50–70s). `save()` refuses any card with a hard error.

**Reviewer step and `script_versions`.** On save, `cards_v2.save()` appends a `writer`
row to `script_versions` at `script.version`, and — only when `review.revised` is
`true` — a `reviewer` row at `script.version + 1` carrying `review.findings`; both rows
point at the same `script_json`, since the schema keeps only the final text, not the
pre-review draft (a documented simplification, not a bug — `cards/README.md`).

**Traceability, answered from the DB.** For a given hypothesis and card:

```sql
SELECT hypothesis_id, title, total_score, supporting_insights_json, candidate_refs_json
FROM hypotheses WHERE hypothesis_id = 'H-11';

SELECT insight_id, statement, confidence FROM insights WHERE insight_id IN
  (SELECT value FROM json_each(
    (SELECT supporting_insights_json FROM hypotheses WHERE hypothesis_id = 'H-11')));

SELECT code, function, reason, performance_json, transformation
FROM hypothesis_refs WHERE hypothesis_id = 'H-11';

SELECT card_id, title, status, script_json FROM cards_v2 WHERE hypothesis_id = 'H-11';

SELECT version, kind, findings, created_at FROM script_versions
WHERE card_id = (SELECT card_id FROM cards_v2 WHERE hypothesis_id = 'H-11')
ORDER BY version;

SELECT stage, state, started_at, error FROM jobs
WHERE entity_kind = 'hypothesis' AND entity_id = 'H-11' ORDER BY started_at;
```

The last query returns only `CONCEPT_GENERATION`/`REFERENCE_SELECTION` rows today.
`CARD_GENERATION`, `SCRIPT_GENERATION`, `SCRIPT_REVIEW` and `FRAME_PLAN` are named in the
canonical `jobs.stage` list (`engine/state.py:STAGES`) but no module — `engine/cards_v2.py`
included — ever opens a `job()` context around them; the trace for those stages lives
only in `script_versions.created_at` and `cards_v2.updated_at`, not in `jobs`.

**What is not tracked, honestly.** `jobs.cost_json` exists as a column in
`engine/schema.py`, threaded through `engine/state.py`, but no call site in
`engine/ingest_insights.py`, `engine/cards_v2.py` or `engine/production.py` ever
populates it (verified by grep). The hypothesis-generation and script-writing passes are
session-driven LLM prompts (`engine/prompts/*.md`) run outside any scheduled job;
`ingest_insights.py` only loads already-written JSON, it never calls a model or meters
tokens. There is no per-hypothesis or per-card token or dollar figure anywhere in this
pipeline — a real gap, worth closing before this chain justifies its own cost.
