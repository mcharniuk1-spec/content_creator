# 37. Limitations

This chapter consolidates limitations named elsewhere in this project's own documents.
None of it is new; gathering it here means no claim in this report, or in a card built
from this engine, should be read without the caveat that applies to it.

**Coverage is 268 of 3,211, and it is a selected sample.** Every structural conclusion
about scripts or visuals rests on the 268 analysis-ready reels (8.3%), not the full
3,211-reel corpus with metrics. That 268 is the top of `score.py`'s own ranking — median
robust_z +1.26 against 0.00 across all ingested reels — so every contrast compares
strong reels against other strong reels, never strong against average.
`docs/M2RADAR_ANALYSIS_METHOD.md` §10: "That 8.3% is a selected sample, not a random
one." Insight I-01 in `data/analysis/insights.json` names the only fix — "a random
sample of the 2,914 unanalysed codes" — which does not exist today.

**Nine-fixed-frame sampling means shares are estimates, not counts.** The legacy corpus
samples 9 frames per video at fixed offsets, not detected cuts (`frames_version=
'fixed9-v1'`). `engine/SPEC.md` §5: shares are estimates from samples, transitions
between them are `unknown` unless two adjacent frames obviously differ, and
`cut_metric_quality='ffmpeg_scene_0.35_count_only'` marks every legacy cut figure as a
count, never a real cut. `reports/analysis/09-reference-selection.md` §5: "A scene
listed as running 44 seconds may have been four shots. Use the scene ids to locate the
moment, never to plan a cut."

**Media is never retained; the legacy corpus cannot be re-extracted.** Every mp4 is
deleted after frame extraction (`docs/data-lifecycle.md`). `reports/audit/
02-data-inventory.md` §15: whether `cuts=0` on 38 deep dives is a genuine single take or
a failed detection cannot be settled without the original video, only by eye against the
surviving contact sheets; no cut count can be re-measured with a better method because
the source no longer exists.

**ASR damage and provider gaps.** The corpus's own transcript analysis records
mis-transcriptions used as evidence in shipped hypotheses — "Kenwa" for Canva, "cloud
code" for Claude Code, "Chachi BT" for ChatGPT (`reports/analysis/09-reference-selection.md`
rule R7) — borrowing a reel's structure never means borrowing its wording. Separately,
`engine/HANDOFF_NOTES.md`'s schema-owner section records 8 August-archive codes with
`transcript_meta.provider='unknown'`, `asr_version=NULL`: "Do not 'fill in' the unknown
ones."

**Two music-only reels carry no usable transcript, by design, not failure.**
`docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md` §16 names them directly; 7 codes in total
have an empty `transcripts` row because Whisper with `vad_filter` heard no speech —
music-only or text-on-screen — and get their own `TRANSCRIPT_UNUSABLE`/`EMPTY_NO_SPEECH`
tier rather than being folded into "failed."

**Max's corpus (1,062 transcripts, 19,808 frames) is not in this git repo.**
`origin/Latest`'s output exists only on his side. `reports/audit/01-branch-comparison.md`
§7: "Whether Max's 1,062 transcripts overlap main's 273 — a stable-ID overlap audit is
still required." §5.2 recommends exporting them via the `m2_signal` receipt format;
that has not happened.

**1,312–1,313 of the newest 1,535 collected reels are unprocessed, links expired.**
`reports/audit/02-data-inventory.md` §7 counts 1,313 codes with neither transcript nor
frames in the newest snapshot; `reports/charts/corpus_coverage_funnel.json`:
"reprocessing them costs another Hiker call." `engine/watchdog.py` never calls Hiker
again — it only replays already-cached signed URLs — so these codes are stuck until a
fresh, paid collection re-establishes a live link.

**Notion attachments are unreadable via MCP, and owned measurement is empty.**
`reports/audit/05-notion-state.md` §6/§298: pre-existing file attachments on a Notion
page (CSV/JSON/HTML dashboards) resolve only to unusable `attachment:<uuid>` references,
not downloadable URLs — an exhibit already in Notion must be re-published somewhere
fetchable. Separately, `reports/audit/02-data-inventory.md` §15: "`our_posts`,
`our_metrics` and `followers` are empty" — every performance number here describes
someone else's account, never M2 Lab's own.

**Comment-gate contamination of the ranker.** `reports/analysis/01-general-conclusions.md`
§4, verbatim: "The comment gate contaminates our own selection. 59% of the analysed
corpus runs one. It moves reach not at all and moves exactly the two rates the radar
ranks by. Until `cta_type` is held constant in selection, the radar is partly ranking DM
funnels." Not yet fixed in `cards.py`'s ranking — see chapter 38.

**Two PRODUCTION.md numbers do not reproduce on the full corpus.**
`reports/analysis/01-general-conclusions.md` §6: "winners' median 55s vs 47s" and "under
twenty seconds is 5% of winners against 13% of the rest" become 46.8s vs 47.8s and 14%
vs 12% on 3,211 reels; `RULES.md` §7's "a share separates a winner 3.6× more reliably, a
save 2.8×" becomes 2.62× and 2.09×. Both corrections are on record, not silently carried
forward.

**The Teardown evidence base is weak.** `reports/analysis/08-hypotheses.md` §4: of the
four RULES-permitted Teardown sources, only "our own processes" is available today. The
six Teardown candidates scored lowest of the three formats (mean 3.37 against 3.77 for
Radar, 3.93 for Builds); rejected H-17 is named as "precisely the defect the 8 September
audit found in ten of Max's cards — designed fixtures, no owner footage, no measured
number."

**Every semantic and visual label is LLM output, not a human judgement.**
`docs/M2RADAR_ANALYSIS_METHOD.md` §10: "they are normalised to closed vocabularies and
the raw label is always kept, but they are judgements, not measurements," each carrying
its own `ta-v1`/`fa-v1` `confidence` (RELIABLE/PROBABLE/INSUFFICIENT). `data/analysis/
ingest_warnings.md` records the concrete leakage this produces — beat roles like
`thesis`, `demo_first`, `story_open` arriving outside the SPEC §4 vocabulary and coerced
to `other`, and one `frame_type` value coerced to `UNKNOWN`.

**No causal claim is licensed by anything in this pipeline.**
`docs/M2RADAR_ANALYSIS_METHOD.md` §10's final line summarises the above: every number
here describes a corpus built one particular way, not evidence that any script choice
will cause a specific outcome for M2 Lab's own account, which has not published enough
to measure at all.
