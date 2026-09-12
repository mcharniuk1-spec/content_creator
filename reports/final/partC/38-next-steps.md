# 38. Next Steps

**1. Run the Phase 2 watchdog on the server, after the next Monday collection.**
`engine/watchdog.py` is safe today — it never calls Hiker, only replays already-cached
signed URLs — but 1,312 of the 1,535 newest-snapshot codes have no live cached link left
(`reports/charts/corpus_coverage_funnel.json`), so a run today would mostly mark codes
`EXPIRED`. Correct order: let `cron.sh`'s `run.py` step do its weekly collection first
(re-establishing live URLs for whatever is still reachable), then run

```sh
timeout 3600 python -m engine.watchdog --limit 40 --yes
```

as `cron.sh` already schedules. Cost note: watchdog itself is free; a fresh Hiker fetch
for a live link is billed at Hiker's own per-unit price — $0.02/unit, `"Start"` tariff
(`lib/hiker.py`'s `PRICE_RECEIPT`) — so re-fetching all 1,312 would run roughly $26 at
one unit per reel, worth confirming against the actual unit cost first.

**2. Fix `cards.py`'s ranking contamination by holding `cta_type` constant.**
`01-general-conclusions.md` §4: the comment-gate CTA moves comment rate 23×, save 2.8×
and share 1.8× while reach moves not at all, so "until `cta_type` is held constant in
selection, the radar is partly ranking DM funnels." The fix is mechanical — group or
filter candidates by `cta_type` before comparing `robust_z`/rate columns in the legacy
`cards.py` ranking, matching `09-reference-selection.md`'s rule R3 already done by hand.
Until it lands, any round reusing `cards.py` rather than the hand-curated
`08-hypotheses.md` process inherits the same bias.

**3. Re-tag topics across snapshots.** `topics.py`/`tag_topics.py` apply the 27-label
vocabulary at collection time; `docs/M2RADAR_ANALYSIS_METHOD.md` §3 records at least one
creator identity already splitting across snapshots, and the finding that M2's territory
is thin (`business_process`: n=8 at 0.65× lift) depends on topic labels staying
comparable release to release. Re-running the tagger against the newest snapshot, and
spot-checking `creator_stats.topic_dist_json` for the same creator across snapshots, is
a cheap way to confirm the label set hasn't drifted.

**4. Build decoupled owned measurement (`our_posts`).** `our_posts`/`our_metrics` are
empty (`reports/audit/02-data-inventory.md` §15) — nothing here has ever measured M2
Lab's own published performance; every insight describes someone else's account.
Populating `our_posts` (even manually, one row per published reel, the schema's existing
shape) is the only way a future report can compare "what the corpus says should work"
against what actually worked — the causal question chapter 37 says nothing here can
answer.

**5. Import path for Max's export.** `origin/Latest` holds ~1,062 transcripts and 19,808
frames not in this repo; `reports/audit/01-branch-comparison.md` §5.2 recommends
exporting via the `m2_signal` receipt format rather than a raw dump, and its overlap
check ("a stable-ID overlap audit is still required") is still open. Run that audit
against this branch's `beats`/`scenes` by `code` before importing, so the merge doesn't
duplicate codes already analysed independently.

**6. Notion decision (a) vs (b).** `docs/NOTION_DASHBOARD.md`: this build implemented
option (b) — keep the operational Reels/Accounts DBs separate from the new engine
databases, linking them into the page tree rather than migrating — "as a working
assumption, not Misha's sign-off." Confirm or override before `engine.notion_sync
--apply` ever runs for real; today it has made zero writes to Notion.

**7. Phase 3 first shoot, using the MP4 take contract.** With one of the ten selected
hypotheses (`08-hypotheses.md` §5) as the source card: validate the card, render its
storyboard, build its PREVIS EDL, shoot to `schemas/supplied-take.schema.json`'s fields,
then follow `docs/PRODUCTION_PIPELINE.md` steps 1–6 (`engine.production takes` →
`select_takes` → `edl_with_takes` → `plan --execute` → human QA → `record_render`) —
the first time Phase 3's tested-but-unused code runs against real footage, not a
synthetic fixture.

**8. A provider pilot approval process, if any `OPTIONAL_PROVIDER` is turned on.** Every
non-default provider (`loore`, `supabase`, `cloudflare`, `openai`, `higgsfield`) is
`NOT_CONFIGURED`/`DISABLED` and stays that way until a credential is added to `.env`.
`engine/SPEC.md` §0.8 already states the rule: print the cost estimate and require an
explicit `--yes` before the first paid call. Before piloting a provider from
`config/provider-catalog.json`, its `execution_enabled: false` flag and dated
`recheck_after` should be revisited — the pricing may already be stale.

**9. Monitor the RELIABLE insights as new data lands.** Insights I-01 through I-30 each
carry a `confidence` and a stated denominator; several RELIABLE ones — the
screen-on-camera finding, the comment-gate inflation, the duration null-correlation —
were computed on 266–268 analysis-ready reels. As watchdog and the Max import (item 5)
grow that denominator, re-running `engine/stats.py` and `engine/ingest_insights.py`
against the larger corpus and diffing against `insights.json` checks these findings hold
rather than being an artefact of a small, selected sample.

**10. Open decisions for Misha:**

1. `FRAMES_ONLY` — ratify 29 codes (frames + transcript not DONE, incl. 7
   empty-transcript codes) or the spec's literal 22 (frames + no `transcripts` row at
   all)? (`engine/HANDOFF_NOTES.md`, schema-owner §1.1)
2. The two disagreeing corpus-tier definitions (`video_state.corpus_tier` as processing
   state vs `engine.corpus.tiers()` as evidence tier) — separate names, or collapse to
   one? (`engine/HANDOFF_NOTES.md`, features-owner §1)
3. `check.py`'s one discrepancy — 8 frame rows with no file on disk in `DcxV37-CJOC` —
   re-fetch the reel or delete the rows? (schema-owner §6)
4. Notion decision (a) vs (b) above — confirm (b), or migrate to (a)?
5. The two orphaned "🗑️ M2 Lab — Radar" stub Notion pages — delete, or keep linked
   under Legacy?
6. Approve a pilot budget for any `OPTIONAL_PROVIDER` (Loore, Supabase, Cloudflare, or
   an image/video model from `config/provider-catalog.json`) — and at what ceiling?
7. Priority: items 1–5 versus the first Phase 3 shoot (item 7) — wait on the ranking
   fix (2) and owned-measurement table (4), or run in parallel?
