# M2Radar — analysis method

**Status: draft (Wave 2, features/stats owner). Written 2026-09-11.**
Binding definitions for `engine/corpus.py`, `engine/lexical.py`, `engine/stats.py`,
`engine/ingest_analysis.py` and `engine/features.py`. Anything reported by the engine —
a card, a PDF, a Notion row — must be traceable to a definition on this page, and any
number quoted without its denominator is a defect, not a rounding question.

Sources: `engine/SPEC.md` §0, §2, §4, §5, §7; the V4 execution prompt §11, §18, §20–21,
§63, §69–73; the audit in `reports/audit/02-data-inventory.md`.

---

## 1. The corpus is four different corpora

`engine/corpus.py` is the only place these are computed. Every number below reproduces
the independent audit of `data/server-mirror/radar.db`.

### 1.1 Tiers (mutually exclusive, covering every ingested code)

| tier | codes | what it is |
|---|---:|---|
| `ANALYSIS_READY` | 266 | usable transcript (words > 0 **and** timed segments) **and** frames |
| `FRAMES_ONLY` | 22 | frames extracted, no transcript row at all |
| `TRANSCRIPT_UNUSABLE` | 7 | a transcripts row exists but is empty — Whisper with `vad_filter` heard no speech (music-only or text-on-screen reels) |
| `INGESTED_NOT_ANALYZED` | 2 916 | Hiker metadata only: play, likes, comments, reshares, duration, caption, ts |
| **total** | **3 211** | unique reel codes |

The spec's three-way split (§0.4) has no bucket for the 7 empty transcripts. They are
neither analysis-ready nor frames-only, so they get their own tier rather than being
quietly folded into one of the others.

### 1.2 Denominators

| name | n | the only questions it may answer |
|---|---:|---|
| `N_ingested` | 3 211 | anything computed from metrics alone: performance, creator norms, temporal trends |
| `N_transcript` | 273 | "how many transcript rows exist" — nothing else |
| `N_transcript_usable` | 266 | every statement about language, script, wording |
| `N_frames` | 295 | every statement about what is on screen |
| `N_ready` | 266 | every statement that joins script **and** visuals |

`N_ingested ≠ N_transcript ≠ N_frames ≠ N_ready`, and mixing them is the single easiest
way to produce a confident wrong number here. 266 / 3 211 = **8.3 %**: any structural
conclusion about "the niche" rests on that 8.3 %, not on the whole database.

> **Two snapshots of these counts exist.** The tables above were computed against the
> production mirror *before* `engine/migrate_legacy.py` imported the August-2026 archive
> (8 transcripts, 74 frames; 2 of those codes have a `reels` row). After the import, the
> working database and every result in §11–§18 use: `ANALYSIS_READY` **268**,
> `FRAMES_ONLY` 22, `TRANSCRIPT_UNUSABLE` 7, `INGESTED_NOT_ANALYZED` **2 914**,
> `N_transcript` **275**, `N_transcript_usable` **268**, `N_frames` **297**, `N_ready` **268**
> (`python3 -m engine.corpus`, 2026-09-12). Coverage stays 8.3 %. `video_state.corpus_tier`
> is a different, processing-state vocabulary (`FRAMES_ONLY` = frames and transcript not
> DONE = 29) — see `docs/M2RADAR_DATABASE_RECONCILIATION.md`.

### 1.3 The newest unprocessed backlog

Snapshot 3 (2026-09-10) holds 1 535 codes. **1 313** have neither transcript nor frames,
**411** of those were seen for the first time in that snapshot. Their CDN media links
have expired, so reprocessing them costs another Hiker call.

### 1.4 The analysis-ready corpus is not a random sample

`deep.py` only ever processed reels that `score.py` had already ranked near the top of
their creator's output. The median `robust_z` inside `ANALYSIS_READY` is therefore above
zero **by construction** (≈ +1.26 as of this writing). Every feature contrast computed
inside that tier compares strong videos with other strong videos. That is still useful —
§73 asks specifically for the weak-vs-strong contrast — but it is a comparison within the
top of the distribution, and must be reported that way.

---

## 2. Performance metrics

Source of rows: `engine/corpus.latest_metrics()` — one row per code, taken from the
newest snapshot that code appears in. Views only grow, so the newest reading is the most
complete. This is `baseline.py`'s rule.

### 2.1 Rates, with a denominator guard

    like_rate     = likes   / views
    comment_rate  = comments / views
    share_rate    = reshares / views
    save_rate     = saves   / views
    hi_intent_rate = (reshares + saves) / views

**Guard: every rate is NULL when views < 100.** Three of a thousand likes on twelve views
is not an engagement rate, it is a rounding artefact, and left unguarded those rows
dominate any ranking by rate. The constant lives in `stats.MIN_PLAY_FOR_RATE`.

Saves deserve a separate warning: HikerAPI drops the field on roughly 9–10 % of rows in
every snapshot (486 of 5 147). `save_rate` therefore always has a smaller `n` than the
other three, and 226 codes have never had a save value at all.

### 2.2 Creator-relative lift (V4 §70)

    View Lift_i        = Views_i / (median views of the creator) - 1
    Share Rate Lift_i  = share_rate_i / (median share rate of the creator) - 1
    Save Rate Lift_i   = save_rate_i / (median save rate of the creator) - 1

A lift of 0 means "exactly normal for this creator"; +1.0 means "twice the creator's
median". The creator's median is built from their whole known history, not from one
weekly pull: a median standing on ~24 videos moves every week, the accumulated one does
not.

### 2.3 Robust z in log space

    robust_z_i = (ln(1 + views_i) - median_c[ln(1 + views)])
                 / (1.4826 * MAD_c[ln(1 + views)])
    clipped to [-5, +5]

Four decisions, each with a reason:

* **Log space.** Play counts run from a few hundred to several million and are strongly
  right-skewed. On the raw scale one hit swamps every other video in the creator's
  distribution; on the log scale the distance between 1 000 and 10 000 equals the
  distance between 10 000 and 100 000, which is what "did well for this creator" means.
* **MAD, not SD.** The standard deviation is computed from the same outliers it is
  meant to measure against. The median absolute deviation is not. The 1.4826 factor
  rescales MAD so that on normal data the result reads like an ordinary z-score.
* **MAD floor 0.10 (log space).** A creator whose videos all land within a few percent
  of each other has a MAD near zero; dividing by it converts noise into a z of 40.
  `score.py` uses `LOG_MAD_FLOOR = 0.10` and *drops* the component when the spread is
  below it. `engine/stats.py` uses the same constant but *floors* the denominator and
  sets `robust_z_floored = 1` on the row. The reason for the difference: `score.py` is
  ranking candidates and can afford to abstain, whereas a descriptive statistic that is
  missing for a third of the corpus cannot be correlated against anything. When
  `robust_z_floored = 1` the **sign** of z is meaningful and its **magnitude is an upper
  bound**.
* **Clip at ±5.** Same as `score.py`'s `Z_CLIP`, so one component can never decide a
  whole ranking on its own.

### 2.4 What `engine/stats.py` does differently from `score.py`

Both compute a robust z on `ln(1 + play)` against the creator's own distribution. They
are not the same number, on purpose:

| | `score.py` | `engine/stats.py` |
|---|---|---|
| purpose | select candidates for a card | describe the distribution |
| focal row | **excluded** from its own baseline — a big outlier would otherwise partly hide inside its own norm | **included** — leave-one-out makes a creator with 6 videos incomparable to one with 40 |
| age banding | compares only within an age band (7 / 30 / 90 days), because a 2-day-old reel has not finished accruing views | none; chronology is handled separately in `temporal()` |
| low spread | component dropped (returns `None`) | denominator floored, row flagged |
| aggregation | weighted blend of 5 components into one `z` | single-metric, reported per metric |
| minimum baseline | 5 videos or the creator is skipped | 5 videos or `outlier_status = SMALL_SAMPLE`, numbers still produced |

Rule of thumb: `scores.z` answers "should we look at this reel?"; `video_features.robust_z`
answers "how unusual was this reel for its author?".

### 2.5 Percentile and outlier status

    percentile_in_creator = 100 * (#{videos with fewer views} + 0.5 * #{ties}) / n

    outlier_status = SMALL_SAMPLE   if the creator has fewer than 5 videos
                     HIGH           if robust_z >= +2
                     LOW            if robust_z <= -2
                     NORMAL         otherwise

---

## 3. Creator statistics (`creator_stats`, SPEC §7, V4 §18)

One row per `(pk, snapshot_id)`. "As of snapshot *s*" means: every code first seen at or
before *s*, each taken at its newest reading at or before *s*. That makes two snapshots
comparable — the row reads "the creator's norm as we knew it that week".

| field | definition |
|---|---|
| `n_videos` | codes in the creator's accumulated baseline |
| `median_play`, `mean_play` | on raw views |
| `mad_play` | median(\|views − median views\|), raw scale |
| `iqr_play` | p75 − p25 |
| `sd_play`, `cv_play` | sample SD; CV = SD / mean |
| `median_like_rate` … | medians of the guarded per-video rates |
| `posts_per_week` | `n_videos / ((max ts − min ts) / 7 days)`, NULL when the span is under a week |
| `outlier_share` | share of the creator's videos with `robust_z > 2` |
| `high_performer_share` | share with `views ≥ 2 × median views` |
| `consistency_score` | `1 / (1 + CV)`, clipped to [0, 1]. 1.0 = identical every time, → 0 = lottery |
| `reliability` | `SMALL_SAMPLE` if n < 5; `CONSISTENT` if CV < 1 **and** n ≥ 8; else `HIGH_VARIANCE` |

`posts_per_week` is a **lower bound**. The corpus holds the reels visible on a profile
page at collection time, not the creator's full posting history.

`topic_dist_json` comes from the legacy `topics.py` tagger; `hook_dist_json`,
`cta_dist_json` and `visual_dist_json` come from `video_features` and stay NULL until the
ta-v1 / fa-v1 analysis wave has covered that creator.

**Known identity defect:** one code (`DcFm9i5s5q8`) carries two different `pk_user`
values across snapshots — the author renamed the account and the pk changed with it. Any
group-by on `pk_user` splits that author in two. It affects one creator and is recorded
here so no one rediscovers it as a bug.

---

## 4. Temporal measures (V4 §71)

Per creator, videos ordered by publication time:

    delta_play_i             = views_i - views_{i-1}
    delta_play_pct_i         = views_i / views_{i-1} - 1
    ratio_to_rolling_median  = views_i / median(views of the previous 5 posts)
    log_play_slope_last10    = OLS slope of ln(1 + views) on post index,
                               over the last 10 posts ending at i

`log_play_slope_last10` is a **trend line, not a derivative** — §71 is explicit that a
simple difference must not be dressed up as one. It is positive when the creator's recent
posts are trending up in log views; it says nothing about why, and a single hit inside the
window bends it.

`ratio_to_rolling_median` uses only *previous* posts, so it never lets a video contribute
to the baseline it is measured against.

---

## 5. Script parts (V4 §11, SPEC §2.6)

    Part Share_k = duration of part k / total spoken duration

Beat roles fold into the eight part-length columns:

| column | beat roles |
|---|---|
| `hook_s` | hook, hook_extension |
| `setup_s` | setup, audience |
| `problem_s` | problem, pain, tension |
| `explanation_s` | explanation, mechanism, context |
| `solution_s` | solution |
| `proof_s` | proof, example |
| `payoff_s` | payoff, transformation |
| `cta_s` | cta, closing |

`objection`, `rehook` and `other` are deliberately left out of the eight: they are
structural moves that can appear anywhere, and folding them into a part would make the
shares sum to something meaningless. Their seconds are kept in
`features_json.script.role_seconds` and totalled as `unbucketed_s`.

`total_s` is the sum of beat durations — the **spoken** length. It is shorter than the
video for any reel with a silent opening or an outro card. The video's own length lives
in `reels.dur`; the two are never swapped.

`share_of_speech` on a beat divides by the video's speech seconds, not by its duration,
so the beats of one video sum to 1.0.

### 5.1 Timing fallback before the beats exist

`engine/lexical.py` always produces a hook / body / tail split by the clock, using
`blocks.split`: hook = first `min(5 s, 0.3 × dur)`, tail = last
`max(min(6 s, 0.3 × dur), 0.15 × dur)`, body = the remainder. A segment belongs to a
block by its **start**, so a hook segment can run past the hook boundary — which is why
both `hook_span_s` (boundary width) and `hook_speech_s` (sum of segment durations) are
reported.

This block is marked `boundary: "timing"` and lives under `features_json.lexical.blocks`.
It never writes the `*_s` columns. A five-second hook by the clock is not a hook by
meaning, and the two must never end up in the same column.

---

## 6. Lexical features (V4 §63)

Stdlib only — no model downloads, nothing the server cron would have to install. Three
tiers of trustworthiness, and the output labels which is which.

**Exact.** Word, character, sentence and phrase counts; n-grams; repeated phrases;
sentence openings and endings; numbers, percentages and money mentions; questions
(a sentence ending in `?`); and every closed-class count — pronouns, second person,
first person, modals, negations, intensifiers, comparisons, superlatives. These are
finite word lists or regexes over a fixed alphabet; a match is the ground truth.

**Lexicon-defined.** The semantic families — emotional, fear, opportunity, urgency,
identity, novelty, proof, CTA-verb — plus the named-entity list for the AI niche
(ChatGPT, Claude, Gemini, Cursor, n8n, Zapier, Make, Notion, Airtable, Perplexity,
Midjourney, Runway, ElevenLabs, HeyGen, Manus, Lovable, Bolt, Replit, Copilot, Sora,
Veo, Kling, Suno, HubSpot, Shopify, Gmail, Slack, WhatsApp, Excel, Google Sheets, Canva,
Figma, Instagram, TikTok, YouTube, LinkedIn, …). These are exact **against the lexicon**;
their coverage is whatever the lexicon covers, and extending it changes the numbers. The
lexicon is a hierarchy: "Claude Code" also matches "Claude", so `entities_n` counts
mentions-of-anything-known, not distinct products — read `entities_distinct` and the
per-category lists for that.

**Heuristic, and named as such in the output.**

* `imperatives_n` — a sentence-initial verb from a list. Misses "Now go and open it".
* `rhetorical_questions_n` — a question that either opens with a rhetorical formula
  ("what if", "why do", "have you ever", …) or is immediately followed by a declarative
  (self-answered), and does **not** contain comment-bait wording ("comment", "dm",
  "tell me"). Flagged `rhetorical_is_heuristic: true`.
* `claims_n` — a declarative sentence (not a question, not opening with an imperative)
  containing either a number or a copula / future verb. Over-counts narration, under-
  counts fragments. Flagged `claims_is_heuristic: true`.
* `pos_lite_adverbs_ly`, `pos_lite_gerunds_ing`, `pos_lite_past_ed` — suffix counts.
  §63 asks for noun / verb / adjective counts, but a suffix rule is not a POS tagger and
  no NLP download is permitted, so only these three families are reported and the key
  names say what they are. Full POS tagging is out of scope for this wave.

Derived:

    wps                      = words / duration
    ttr                      = distinct words / words          (length-sensitive)
    rttr                     = distinct words / sqrt(words)    (length-robust)
    mattr50                  = mean TTR over a 50-word moving window (NULL under 50 words)
    info_density             = content words (non-stopword) / duration
    specificity              = 100 * (numbers + entity mentions + technical terms) / words
    claims_per_10s           = 10 * claims / duration
    questions_per_10s        = 10 * questions / duration
    direct_address_per_10s   = 10 * second-person tokens / duration
    numeric_evidence_per_10s = 10 * (numbers + percentages + money) / duration

**Sentence splitting.** Whisper punctuates 255 of the 266 usable transcripts. For the
other 11 there is no punctuation at all; each timed segment then becomes one
pseudo-sentence, which is Whisper's own VAD phrase boundary. `sentence_source` on every
row says which happened (`punctuation` / `segments` / `whole_text`), so per-sentence
statistics from the two groups are never silently pooled.

---

## 7. Visual features (SPEC §5, V4 §64)

The legacy corpus has **9 fixed frames** per video (0.4 / 1.2 / 2.4 / 4.0 s, then evenly
spaced). Everything below is an interpolation between nine points.

* `a_roll_share`, `b_roll_share`, `split_share`, `screen_share` — the fraction of
  **labelled samples** carrying that roll, not the fraction of screen time.
  `features_json.visual.share_basis` states this on every row, and the model's own
  estimates from fa-v1 are kept separately under `shares_estimated_by_model` — beside
  ours, never instead of them.
* `scenes` for the legacy corpus = one run of consecutive samples with the same
  `frame_type`. `boundary_reason = 'sampled'`, `detector_json.boundary_confidence = 'low'`.
  A "scene" here can read as 4.5 s long when the real shot was 0.6 s.
* `transition_in` is written only where fa-v1 actually observed a change between two
  samples. `same_shot` and everything unobserved becomes `unknown`. SPEC §5: never claim
  a transition that was not seen.
* `visual_sequence` = frame types in order with consecutive duplicates collapsed,
  joined by `>`.
* `text_overlay_density` = share of labelled samples carrying burned-in text.

### 7.1 The cut metric — read this before quoting `cuts`

`deepdives.cuts` comes from

    ffmpeg -i <mp4> -filter:v "select='gt(scene,0.35)',showinfo" -f null -

counted as the number of `pts_time:` lines. That is **ffmpeg's scene-score threshold, not
shot-boundary detection**. Consequences, all confirmed in the audit:

* It misses hard cuts between visually similar shots — same speaker, same set, same
  framing, which is precisely the talking-head format that dominates this niche.
* It over-counts fast camera motion, flashes, whip pans, heavy zoom transitions and
  screen-recording scrolls.
* The 0.35 threshold is fixed with no per-clip calibration.
* 38 of 282 rows report `cuts = 0`, which is indistinguishable from a detection that
  simply never fired.

Therefore `video_features.cut_metric_quality` carries one of three values into every
downstream table:

| value | meaning |
|---|---|
| `ffmpeg_scene_0.35_count_only` | legacy count above. Usable as a relative "busy vs. calm" signal **inside this dataset only**. Never comparable to any externally reported cut rate, and never quotable as an edit count. |
| `scene-v1` | real scene intervals from the new detector; `cuts = scenes − 1` |
| `unavailable` | no cut information for this code |

---

## 8. Associations (V4 §21, §72)

Everything in this section is **descriptive and associational**. Nothing here identifies
a cause, and no output may be worded as if it did.

### 8.1 Numeric features — Spearman

Spearman's rank correlation (scipy) between each performance metric
(`view_lift`, `share_rate`, `save_rate`, `robust_z`) and each numeric feature. Reported
per pair: `n`, `n_creators`, `rho`, `p`, direction.

**Creator-normalised variant.** Inside each creator with at least 3 videos, both
variables are replaced by their centred rank within that creator, then pooled and
re-correlated. This removes the creator's level while keeping the ordering. The reason it
matters: a pooled correlation can be entirely between-creator — "creators who name tools
happen to get more saves" — which is a statement about *who posts what*, not about the
video. `creator_normalized_survives` is true when the normalised rho keeps the same sign
and at least half the magnitude of the pooled one.

### 8.2 Categorical contrasts

For each category (`topic`, `hook_type`, `pain`, `solution_type`, `cta_type`, `narrative`,
`first_frame_type`, `visual_sequence`) and each performance metric:

    diff_vs_pooled = median(metric | category = value) - median(metric | all rows)

with `n` (videos) and `n_creators` reported alongside.

A code carrying several legacy topic labels is left **unassigned** rather than given one
of them: picking one would invent a fact, and counting the video once per label would let
a nine-label video outvote eight others.

### 8.3 Bootstrap confidence interval

1 000 replicates, seed `20260911`, **resampling creators, not videos**. Videos by the
same creator are not independent draws; one creator with 30 reels in a category would
otherwise drive the interval on their own. Each replicate draws creators with
replacement, pools all their videos, recomputes `diff_vs_pooled`, and the CI is the
2.5 / 97.5 percentile of those 1 000 differences. The seed is fixed, so the interval is
reproducible; changing it changes the interval in the fourth decimal, which is itself a
reminder of how wide these are.

No CI is produced below 3 creators.

### 8.4 Strong vs weak (V4 §73)

Top quartile vs bottom quartile of `robust_z` **within the analysis-ready corpus**. For
every numeric feature: `n` on each side, both medians, the difference, and a
Mann-Whitney U two-sided test. Mann-Whitney rather than a t-test because none of these
distributions is normal and several are counts with a floor at zero.

Remember §1.4: inside `ANALYSIS_READY` the "weak" quartile is not weak content, it is
the least strong of a pre-selected strong set.

### 8.5 Small-sample rules and confidence labels

| label | rule |
|---|---|
| `INSUFFICIENT` | n < 5 videos **or** fewer than 3 creators. Reported with `suppressed_reason`, never dropped — a suppressed cell is a fact about the data, and deleting it hides which categories we cannot speak about. |
| `RELIABLE` | n ≥ 30, creators ≥ 8, p < 0.01 (or a bootstrap CI that excludes 0), **and** — for a correlation — the creator-normalised rho keeps the sign and at least half the magnitude. |
| `PROBABLE` | everything in between. |

`RELIABLE` is a statement about the sample, not about the niche. Section 1.4 still
applies to every one of them.

---

## 9. Where each number is stored

| output | table / column |
|---|---|
| corpus tiers and code lists | computed on demand by `engine/corpus.tiers()`; mirrored per code in `video_state.corpus_tier` |
| creator norms | `creator_stats` (one row per `pk` × `snapshot_id`) |
| per-video performance | `video_features` perf columns **and** `features_json.perf` |
| temporal | `features_json.temporal` |
| lexical | `features_json.lexical` |
| script parts | `video_features.hook_s … cta_s`, detail in `features_json.script` |
| visual | `video_features.first_frame_type … visual_sequence`, detail in `features_json.visual` |
| raw model labels | `video_features.raw_labels_json`, `frame_labels.labels_json`, `scenes.detector_json` |
| vocabulary violations | `data/analysis/ingest_warnings.md` |
| the whole run | `reports/stats/stats-<date>.json` |

`features_json` is written by three modules (`lexical`, `stats`, `features`) through one
read-modify-write helper, `corpus.merge_features`, so no producer can clobber another's
key.

---

## 10. Limitations

1. **8.3 % coverage.** Structural conclusions rest on 266 of 3 211 codes.
2. **That 8.3 % is a selected sample**, not a random one (§1.4).
3. **The legacy cut metric is not a cut count** (§7.1).
4. **Scenes in the legacy corpus are sampled, not detected** — nine points per video.
5. **Saves are intermittently missing** (~9–10 % of rows), so `save_rate` runs on a
   smaller `n` than the other rates.
6. **Three snapshots.** Temporal statements stand on 2026-09-01, -07 and -10; the
   `followers` table is empty, so growth of a creator cannot be answered at all.
7. **Age is not controlled** in `engine/stats.py`. A reel published two days before a
   snapshot has not finished accruing views. `score.py` bands by age; this module does
   not, so `view_lift` for very recent reels is biased downwards.
8. **One creator identity splits in two** across snapshots (§3).
9. **Semantic and visual categories are LLM output.** They are normalised to closed
   vocabularies and the raw label is always kept, but they are judgements, not
   measurements, and `analysis_confidence` from ta-v1 travels with them.
10. **No causal claim is licensed by anything on this page.**

---

## Results

> Filled 2026-09-12 from `reports/stats/stats-2026-09-12.json`, `reports/data/*` and the 266 ta-v1 /
> 295 fa-v1 per-video analyses. The narrative versions live in `reports/analysis/01`–`07`; the numbered
> insights, each with its evidence block, live in `data/analysis/insights.json` (30 records, validated by
> `python3 -m engine.ingest_insights --dry` with 0 rejected). Section 1.4 applies to every number below.

### 11. Corpus and coverage at the time of the run

`engine.corpus.tiers()` at 2026-09-11T22:26Z, db md5 `6834ecb414400838fb17258919a2b442`:

| tier | codes |
|---|---:|
| `ANALYSIS_READY` | **268** |
| `FRAMES_ONLY` | 22 |
| `TRANSCRIPT_UNUSABLE` | 7 |
| `INGESTED_NOT_ANALYZED` | 2 914 |
| total unique codes | **3 211** |

Denominators as used: `N_ingested` 3 211 · `N_transcript` 275 (7 of them empty) · `N_transcript_usable`
268 · `N_frames` 297 · `N_ready` 268. The second vocabulary, `video_state.corpus_tier`, reports
ANALYSIS_READY 268 / FRAMES_ONLY 29 / INGESTED_NOT_ANALYZED 2 914 — it folds the 7 empty transcripts into
frames-only by design (§1.1), and the two vocabularies are not interchangeable.

**Analysis coverage.** `analysis_version` on `video_state`: `ta-v1` on **264** codes, `fa-v1` on 31 (the
fa-v1 reads themselves exist as 295 files; `video_state` records the version only where it was the last
write). Loaded rows: `beats` 1 527 across 264 codes · `frame_labels` 2 645 across 295 codes · `scenes` 960
across 282 codes · `deepdives` 282. `features_json` is populated on all 3 211 rows of `video_features`.

**ta-v1 self-assessed confidence** over the 266 transcript analyses: RELIABLE 161, PROBABLE 94,
INSUFFICIENT 11. The 11 INSUFFICIENT rows are kept rather than dropped — e.g. `DcxV37-CJOC`, where ASR
captured five words ("Did you know that the-") of a 62-second reel that reached 559 515 plays on an
83 168 median. They contribute nothing to any script finding and are a standing reminder of what
transcript-only analysis cannot see.

**What was excluded and why.** Script-part statistics run on **264** codes, not 268: the four excluded have
frames and a transcript but no beat-derived script block (`features_json.script.part_source != 'beats'`),
and the timing-only fallback (§5.1) is never mixed into the `*_s` columns. Save-rate statistics run on
**245** of 268 because HikerAPI drops the field on ~9–10 % of rows (226 codes have never had a save value).
Frame statistics run on 295 or on the 266 that also have a transcript, depending on whether the statement
joins script to visuals.

**The backlog.** Snapshot 3 (2026-09-10) holds 1 535 codes, of which **1 312** have neither transcript nor
frames and **410** were first seen in that snapshot. Their CDN media links have expired, so reprocessing
costs another Hiker call. 6 codes appear in other tables without a `reels` row.

**Flags.** 3 006 of 3 211 codes carry at least one flag: MISSING_TRANSCRIPT 2 936, MISSING_FRAMES 2 914,
STALE_METRICS 1 676, DUPLICATE_VIDEO 56, UNALIGNED_TRANSCRIPT 7, and one each of MISSING_STATS,
MISSING_MEDIA, BROKEN_FRAME_REFERENCE and UNRESOLVED_CREATOR_ID.

**Coverage is 268 / 3 211 = 8.3 %, and it is not a random 8.3 %** (§1.4). Median `robust_z` inside
ANALYSIS_READY is **+1.264** against **0.000** across all 3 211; median `view_lift` +2.025 against 0.000.

### 12. Creator landscape

132 creators have a `creator_stats` row at snapshot 3. `followers` is populated on all 132 but the
`followers` table is empty, so creator growth cannot be answered at all.

| | value |
|---|---|
| `CONSISTENT` (CV<1 and n≥8) | **17** (13 %) |
| `HIGH_VARIANCE` | **115** (87 %) |
| `SMALL_SAMPLE` | 0 |
| median `n_videos` in baseline | 26 |
| median `median_play` | 14 936 (p10 3 099, p90 71 198) |
| median `consistency_score` | **0.352** |
| median MAD-to-median ratio | 0.47 |
| Spearman(median_play, mad_play) | **+0.967** |
| max `cv_play` | 4.77 (adamstewartmarketing) |
| creators contributing to the analysed set | 102, at a median of 2 reels each (p75 4, max 6) |

Dispersion rises almost perfectly with level, which is why both `score.py` and `engine/stats.py` compute
the z on `ln(1 + play)`. `posts_per_week` is a lower bound throughout — the corpus holds what was visible
on a profile page at collection time. The `robust_z_floored` flag is set on **0** rows this run, so no
magnitude in this wave is an upper bound for that reason.

**The seven consistent creators with a real audience** (median play ≥ 19 000): angus.sewell (n=12, median
89 439, CV 0.98), harshsharma_ai (12 / 44 377 / 0.96), chris.raroque (12 / 36 820 / 0.80), decodingai.vs
(29 / 30 932 / 0.73), ajsahni.ai (12 / 28 067 / 0.95), justyn.ai (30 / 19 173 / 0.91), divyannshisharma
(27 / 18 948 / 0.78). The last of these plus damini.knows (14 / 12 678 / 0.64) are the only two creators in
the roster that are consistent **and** carry above-median share and save rates.

**Posting cadence** spans three orders of magnitude: automationatlas.co at 32.1 posts per week and seb.ai
at 14.6 against umangratani at 0.13. Neither extreme correlates with performance.

**A measurement consequence worth recording.** The 28 analysed reels from CONSISTENT creators carry a
median `robust_z` of 0.60 and `view_lift` 0.65; the 240 from HIGH_VARIANCE creators carry 1.37 and 2.38 —
with identical script shape (median hook 6.7 s both, spoken length 53.8 s vs 53.5 s, 3.4 vs 3.5 wps).
Creator-relative lift divides by the creator's own spread, so a steady creator produces small lifts from
good reels. A multiplier is interpretable only alongside the creator's CV and baseline n.

**Known identity defect unchanged:** `DcFm9i5s5q8` carries two `pk_user` values across snapshots (§3).

### 13. Script part lengths (V4 §11)

Medians over the 264 codes with a beat-derived script, reported per part on the codes where that part
exists:

| part | n | % of 264 | median s | mean s | median share | median words |
|---|---:|---:|---:|---:|---:|---:|
| hook | 260 | 98 % | 6.7 | 7.50 | 13.2 % | 21.5 |
| setup | 34 | 13 % | 7.8 | 9.41 | 14.0 % | 29 |
| problem | 64 | 24 % | 8.95 | 12.04 | 16.4 % | 32 |
| explanation | 208 | 79 % | 18.6 | 23.54 | 38.3 % | 64 |
| solution | 70 | 27 % | 10.4 | 12.95 | 20.1 % | 36 |
| proof | 133 | 50 % | 17.0 | 23.19 | 30.5 % | 57 |
| payoff | 150 | 57 % | 8.2 | 10.24 | 17.0 % | 26.5 |
| cta | 216 | 82 % | 4.95 | 6.27 | 9.7 % | 21 |

Whole-reel: median spoken length 53.6 s, 182 words, 3.52 wps. `unbucketed_s` (objection + rehook + other)
is non-zero in only 35 of 264 reels. Distributions: `hook_s` p25 4.6 / p75 9.6 (6 % under 3 s, 31 % under
5 s, 19 % over 10 s); time to first proof beat median 22.0 s (p25 11.1, p75 32.0); time to solution beat
median 19.7 s; CTA start at a median 90 % of spoken length (94 % in the final quarter, 3 of 216 before
halfway); problem start at a median 21 % (56 % inside the first quarter).

**High performers vs the rest** (quartiles on `robust_z`, n=66 per side, q1 +0.581, q3 +2.862): total
spoken length is identical (56.9 s vs 58.0 s, p=0.98) and the allocation shifts — explanation 34.1 % vs
41.9 % (17.3 s vs 19.5 s), solution 21.1 % vs 15.3 % (12.25 s vs 8.4 s, **p=0.0065**, the only part
clearing p<0.01), payoff 18.6 % vs 16.8 %, cta 10.3 % vs 8.4 %, proof 32.9 % vs 37.1 % (p=0.55), problem
unchanged (p=0.81). `hook_words` separates the quartiles (26.5 vs 22.0, p=0.028) while `hook_s` does not
(p=0.162).

**By creator reliability:** shape is the same; consistent creators spend less on proof (11.2 s vs 18.6 s)
and more on the closing line (6.3 s vs 4.8 s). **By topic** and **by narrative archetype**: full tables in
`reports/analysis/05-script-parts.md` §5–6. The archetype worth naming here is `demo_walkthrough` — the
largest (n=62, 42 creators), the highest-lift (median view_lift 3.70) and the most evenly balanced (38 %
explanation, 34 % proof).

### 14. Frequencies

**Orderings.** 1 527 beats over 264 codes, median 6 per reel. Hook is the first beat in 259 of 264; a CTA
or closing beat is last in 215. 146 distinct bucketed orderings; the modal shape
`HOOK > EXPLAIN > PAYOFF > CTA` covers 27 reels (10 %), then `HOOK > EXPLAIN > CTA` 13,
`HOOK > EXPLAIN > PROOF > CTA` 10, `HOOK > PROOF > CTA` 8.

**Hook types** (n=266; only `bold_claim` reaches SUFFICIENT_SAMPLE): bold_claim 67 · result_first 24 ·
contrarian 23 · curiosity_gap 22 · list_promise 21 · number_stat 20 · demo_first 18 · problem_call_out 17 ·
story_open 13 · warning_fear 13 · question 10 · identity_call 9 · other 9.

**Pain** (13 values, two SUFFICIENT_SAMPLE): cost_money 48 · dont_know_where_to_start 34 ·
keeping_up_with_ai 29 · missing_skills 25 · quality_trust 25 · other 24 · time_waste 20 ·
chaos_no_process 17 · manual_repetition 15 · scaling_without_hiring 8 · tool_overload 8 ·
fear_of_replacement 8 · slow_response_to_leads 5.

**Solution type:** tool_walkthrough 60 · workflow_recipe 51 · resource_handoff 38 ·
framework_mental_model 25 · agent_build 23 · other 23 · case_story 18 · comparison 12 ·
prompt_technique 10 · warning_dont 6.

**Proof type:** screen_demo 84 · **none 68** · numbers 36 · personal_story 28 · authority_claim 25 ·
third_party_data 16 · before_after 5 · client_story 4. Half the corpus carries no proof beat and performs
indistinguishably from the half that does.

**CTA type:** comment_keyword **158 (59 %)** · none 58 · follow 17 · link_in_bio 12 ·
question_to_audience 11 · dm 3 · next_video 3 · free_resource 2 · save_share 2.

**Narrative:** demo_walkthrough 62 · tutorial_steps 45 · listicle 43 · problem_solution 34 ·
announcement_news 30 · story_arc 17 · myth_bust 13 · rant_opinion 9 · other 8 ·
contrast_before_after 5. **Positioning:** educator 138 · news 38 · builder 38 · seller 31 ·
entertainer 21. **Funnel role:** awareness 125 · conversion 83 · trust 58.

**Topic clusters** (205 labelled, 63 unassigned because a multi-label code is left unassigned by design,
§8.2): agent building 27 · AI video 23 · Claude Code 22 · free access 21 · model news 21 ·
design and sites 19 · leadgen and CRM 15 · agency business 14, then a tail of 19 cells with n≤12.

**Visual vocabulary.** 2 645 labelled frames: SPLIT_SCREEN 591 (22.3 %) · A_ROLL_MEDIUM 363 ·
A_ROLL_CLOSE_UP 353 · SCREENSHOT 294 · SCREEN_RECORDING 258 · UI_DEMO 127 · OVERLAY 123 ·
B_ROLL_CONTEXT 113 · A_ROLL_WIDE 78 · B_ROLL_PROCESS 72 · DATA_VISUAL 64 · MOTION_GRAPHIC 54 ·
A_ROLL_TALKING_HEAD 47 · TEXT_ONLY 46 · 55 others. Rolls: A 33 %, SPLIT 26 %, SCREEN 26 %, B 7 %.
Per frame: text_overlay 86 %, face_present 65 %, ui_present 58 %, is_proof_visual 41 %,
is_cta_visual 3 %. First-frame types over 266: SPLIT_SCREEN 73 · A_ROLL_MEDIUM 57 · A_ROLL_CLOSE_UP 45 ·
B_ROLL_CONTEXT 18 · SCREEN_RECORDING 16 · OVERLAY 14 · the rest ≤13.

**Transitions.** Only one type is observed anywhere: **663 `hard_cut_or_more`** and 15 `unknown`. Per
SPEC §5 nothing else may be claimed, and the absence of dissolves or whips is a sampling artefact.

**Recurring phrases.** Sentence openings: "this is" 26 · "you can" 23 · "if you" 21 · "it's called" 20 ·
"here's how" 14. Hook trigrams: "you can now" 7 · "if you want" 4 · "I just built" 3 · "most people
think" 2 · "nobody is talking" 2. Sentence endings land on a destination: "right now" 13 · "for free" 11 ·
"for you" 11 · "on github" 10. Imperatives: **comment 41** · follow 14 · go 12 · look 9 · click 7 — the
lexical signature of the keyword gate.

**Rhetorical devices.** `semantics.rhetorical_devices` is free text and produced 975 distinct strings over
266 reels, so no device reaches a countable frequency; the recurring families by repeated wording are
numbered steps/lists (17), borrowed authority (6), price contrast or anchoring (6), future pacing (4),
objection pre-emption (3), rule of three (3), keyword gate (3) and benefit stacking (3). The countable
equivalents are the exact lexical counts: median `questions_n` **0**, `second_person_n` 8,
`first_person_n` 4–5, `imperatives_n` 1, `negations_n` 2, `modals_n` 3, `numbers_n` 3 (strong) vs 1 (weak).

### 15. Associations with performance

460 Spearman pairs (115 numeric features × 4 metrics), `min_n` 10, n=268 rows, 102 creators. 1 135
categorical contrasts with bootstrap CIs (1 000 replicates, seed 20260911, creators resampled, no CI
below 3 creators).

**13 of 460 pairs are RELIABLE.** Nine are save-rate correlations, one share-rate, one view_lift, and
**none is against `robust_z`**:

| feature | metric | n | creators | rho | p | creator-normalised rho |
|---|---|---:|---:|---:|---:|---:|
| `lex_platforms_n` | save_rate | 245 | 95 | +0.331 | 1.1e-07 | +0.173 |
| `lex_cta_verb_n` | save_rate | 245 | 95 | +0.241 | 1.4e-04 | +0.155 |
| `lex_questions_per_10s` | save_rate | 245 | 95 | −0.235 | 2.0e-04 | −0.186 |
| `questions_n` / `lex_questions_n` | save_rate | 245 | 95 | −0.229 | 3.1e-04 | −0.162 |
| `lex_second_person_n` | save_rate | 245 | 95 | +0.206 | 1.2e-03 | +0.177 |
| `blk_hook_wps` | save_rate | 240 | 94 | +0.205 | 1.4e-03 | +0.156 |
| `screen_share` | share_rate | 266 | 102 | +0.203 | 8.5e-04 | +0.129 |
| `blk_hook_segments` | save_rate | 245 | 95 | +0.198 | 1.9e-03 | +0.197 |
| `lex_rhetorical_questions_n` | save_rate | 245 | 95 | −0.186 | 3.5e-03 | −0.151 |
| `lex_first_person_n` | save_rate | 245 | 95 | −0.180 | 4.8e-03 | −0.124 |
| `lex_direct_address_per_100w` | save_rate | 245 | 95 | +0.174 | 6.3e-03 | +0.127 |
| `lex_entities_distinct` | view_lift | 268 | 102 | +0.161 | 8.3e-03 | +0.198 |

Two further pairs computed in this wave from the coarse visual vocabulary clear the same bar and are
recorded as RELIABLE in `insights.json`: **first visual state is a screen → share_rate** (pooled +0.208,
p=6.3e-04; creator-normalised **+0.285**, p=2.5e-04, n=161) and **any screen state present → save_rate**
(pooled +0.210, p=9.8e-04; creator-normalised +0.213, p=9.3e-03).

**Survives normalisation but only PROBABLE** (p<0.05, one RELIABLE condition unmet): `lex_tools_n` →
view_lift +0.157 (cn +0.223), `specificity` → view_lift +0.132 (cn +0.205) and → robust_z +0.121
(cn +0.197), `a_roll_share` → share_rate −0.156 (cn −0.094), `lex_urgency_n` → share_rate −0.150
(cn −0.180), `lex_fear_n` → share_rate −0.157 (cn −0.086), `lex_opportunity_n` → save_rate +0.128
(cn +0.223).

**Categorical contrasts worth quoting** (medians against the pooled median, size-only confidence):
`demo_first` hook view_lift 9.55 (n=18, 14 creators) · `result_first` 4.20 (24/18) · `identity_call` 0.41
(9/8) · `problem_call_out` 0.49 (17/15) · agent-building topic 6.63 (27/19) · business-process topic 0.65
(8/8) · `manual_repetition` pain 6.94 (15/13) · `chaos_no_process` 0.87 (17/14) · `builder` positioning
3.42 (38/27) vs `educator` 1.73 (138/68) · `conversion` funnel role 3.50 (83/51) vs `trust` 1.06 (58/39) ·
`resource_handoff` save rate 0.0429 (38/28) vs `framework_mental_model` 0.0135 (25/16) ·
`B_ROLL_PROCESS` visual sequence view_lift 30.90 (6/4).

### 16. Strong vs weak (V4 §73)

Top vs bottom quartile of `robust_z` inside ANALYSIS_READY: n=**67** each, 41 and 43 creators,
q1 **+0.596**, q3 **+2.855**, Mann-Whitney two-sided across all **115** features.

**Of 115 features, none reaches p<0.01; seven reach p<0.05:**

| feature | strong | weak | diff | p |
|---|---:|---:|---:|---:|
| `solution_s` | 12.25 | 8.4 | +3.85 | 0.0065 |
| `lex_entities_distinct` | 2.0 | 1.0 | +1.0 | 0.0107 |
| `lex_entities_n` | 2.0 | 1.0 | +1.0 | 0.0207 |
| `lex_tools_n` | 0.0 | 0.0 | 0.0 | 0.0254 |
| `hook_words` | 26.5 | 22.0 | +4.5 | 0.0282 |
| `lex_ttr` | 0.605 | 0.628 | −0.023 | 0.0387 |
| `lex_mattr50` | 0.795 | 0.811 | −0.016 | 0.0443 |

Just outside: `lex_urgency_per_100w` 0.683 vs 0.901 (p=0.053), `lex_urgency_n` 1 vs 2 (p=0.056),
`setup_s` 11.0 vs 4.7 (p=0.057), `cta_s` 5.7 vs 4.4 (p=0.075), `specificity` 4.255 vs 3.448 (p=0.080).

**Identical on both sides:** duration 56.9 s vs 58.0 s (p=0.981) · total_words 198 vs 179 (p=0.333) ·
wps 3.53 vs 3.45 (p=0.444) · hook_s 7.6 vs 7.0 (p=0.162) · a_roll_share 0.2222 both (p=0.573) ·
split_share 0.0 both (p=0.628) · text_overlay_density 1.0 both (p=0.418) · cuts_per_min 7.06 vs 6.75
(p=0.420) · scenes_n 4 vs 3 (p=0.110) · avg_sentence_len 13.6 vs 14.5 (p=0.612). Full 115-row table in
`reports/analysis/04-strong-vs-weak.md`.

**§1.4 restated.** The "weak" quartile is not weak content: its median `robust_z` is about **+0.6**, i.e.
these reels still beat their own authors' medians. This is a comparison between the strongest and the
merely strong inside a sample that was pre-selected for strength — so every gap above is a floor, and
every absence of a gap was measured under conditions that should have made it *easier*, not harder, to
find.

### 17. Temporal patterns

3 211 codes with a publish timestamp; 3 078 have a rolling median and 2 947 a slope. Three snapshots only
(2026-09-01, -07, -10) and the `followers` table is empty.

| | value |
|---|---|
| median `log_play_slope_last10` | **−0.052** |
| mean | −0.138 (p10 −0.589, p90 +0.155) |
| creators with a full 10-post window | 131 |
| of those, trending **up** | **34 (26 %)** |
| median `delta_play_pct` vs previous post | −5.2 % |
| median `ratio_to_rolling_median` | 0.885 |
| posts above 5× their creator's rolling median | 269 of 3 078 (**8.7 %**), across 101 creators |
| posts above 10× | 150 (4.7 %) |

**Trending up (top 12):** swapsays_wtf +0.373 · manthanjethwani +0.337 · gannon.meyer +0.198 ·
harshsharma_ai +0.197 · soojintech +0.174 · valeridoesai +0.167 · protips.ai +0.163 ·
gennaroautomates +0.162 · rence_ur_hands +0.159 · wokecoder +0.145 · kayvon.ai +0.144 · chase.h.ai +0.140.

**Trending down (top 12):** kraya.ai −0.706 · jackroberts___ −0.428 · cashflow.automations −0.413 ·
andreapalacio −0.403 · kallaway −0.401 · michaelpkocher −0.349 · lukebuildsai −0.311 ·
petergriffin.ai −0.310 · publisity.ai −0.303 · davi.d_roberts −0.282 · sanji.chien −0.275 ·
techflowanjani −0.264.

Only `harshsharma_ai` is both rising and CONSISTENT. **Emerging formats** cannot be separated from
emerging topics on three snapshots; what the data does support is that the niche is an outlier business —
8.7 % of posts carry the reach, and 87 % of creators cannot repeat them. A competitor's recent reach is
not a stable benchmark, which is the measured justification for the 14-day freshness threshold in
RULES.md. `log_play_slope_last10` is a trend line over post index, not a derivative, and one hit inside
the window bends it (§4).

### 18. What the evidence does not support

**Vanished under creator normalisation** (pooled p<0.05, normalised rho loses sign or more than half its
magnitude): `info_density` → save_rate (+0.303 pooled, cn +0.132) · `lex_technical_n` → save_rate (+0.268,
cn −0.060) · `lex_entities_distinct` → save_rate (+0.256, cn +0.030) · `specificity` → save_rate (+0.237,
cn +0.047) · `wps` → save_rate (+0.213, cn +0.071) · `split_share` → save_rate (+0.193, cn +0.036) ·
`text_overlay_density` → save_rate (+0.180, cn +0.080) · `lex_urgency_n` → view_lift (−0.164, cn −0.028) ·
`lex_platforms_n` → share_rate (+0.187, cn +0.031) · `solution_s` → robust_z (+0.342, cn +0.106) and →
save_rate (+0.343, cn −0.217, sign flip) · `setup_s` → view_lift (+0.395 on n=34, cn −0.318, sign flip).
These are statements about *which creators post what*, not about the videos.

**No signal at all, in any metric:** duration (|rho| ≤ 0.09 over 3 211 reels) · `hook_s` · `hook_words`
against reach · `total_s` · `total_words` · `wps` against reach · `cuts` · `cuts_per_min` · `scenes_n` ·
`avg_scene_s` · `b_roll_share` · `text_overlay_density` against reach · `proof_s` · `problem_s` ·
`explanation_s` against reach · `avg_sentence_len` · every lexical-diversity measure against reach.

**Categories that stayed INSUFFICIENT** (n<5 or <3 creators, reported with `suppressed_reason` rather than
deleted): **all 20** `subtopic` cells (every one n≤2) · 9 of 27 `topic` cells (including
`Голосовые агенты и телефония` n=4 at view_lift 4.55 and `Развлечение и конспирология` n=3 at 18.32) ·
`cta_type` `dm` (n=3), `next_video` (3), `free_resource` (2), `save_share` (2) · `proof_type`
`client_story` (n=4) · 9 of 15 reported `visual_sequence` cells · `first_frame_type` `MEME` (4),
`TEXT_ONLY` (4), `TRANSITION` (1). Of 159 reported categorical cells across the eight vocabularies, 18 are
SUFFICIENT_SAMPLE, 96 PROBABLE and 45 INSUFFICIENT.

**Measurements that cannot support a claim at all, by construction:**

* **The cut metric.** `cut_metric_quality = ffmpeg_scene_0.35_count_only` on all 282 rows; 38 report zero.
  No M2 output may quote a cut rate from it (§7.1).
* **Transcript-to-frame alignment.** 55 of 1 527 beat boundaries (3.6 %) fall within 0.3 s of a sampled
  scene start; 215 of 264 codes have none. With 9 fixed samples this is a measurement floor, so both the
  rate and the null performance result (robust_z 1.45 vs 1.25, p=0.603) are provisional.
* **Transitions other than hard cuts.** 663 `hard_cut_or_more`, 15 `unknown`, nothing else observed.
* **`visual_to_script_sync`.** Free prose, not a category; never tested.
* **Creator growth.** The `followers` table is empty.

**Two previously published numbers that this run does not reproduce.** PRODUCTION.md's "the winners'
median is 55 seconds against 47 for the rest" and "under twenty seconds is 5 % of winners and 13 % of the
rest" become 46.8 s vs 47.8 s and 14 % vs 12 % on 3 211 creator-normalised reels. RULES.md §7's "a share
separates a winner 3.6× more reliably than anything else; a save, 2.8×" becomes **2.62×** and **2.09×** on
the 2 899 reels clearing the 100-play guard. Both originals came from a 100-reel top slice of an earlier
2 352-reel export; neither is wrong about direction, both are wrong about magnitude.

**And the largest negative result of the wave.** Of 115 numeric features, none separates the top from the
bottom `robust_z` quartile at p<0.01, and of 460 correlation pairs none is RELIABLE against `robust_z`.
Within this corpus, **no measured structural property of a reel predicts its reach.** Nine of the 13
RELIABLE pairs predict saves instead. Section 10.10 still stands: nothing on this page licenses a causal
claim.

> **Addendum (2026-09-12, after the report was compiled).** The scheduled semantic-analysis stage
> (`engine/analyze_pending.py`) found 8 archive transcripts without a ta-v1 analysis and they were
> analysed and ingested after the chapters of this report were written: ta-v1 files 266 → 274,
> codes with beats 264 → 270 (two of the eight are music-only, no beats). Two of the eight belong to
> reels in the corpus (`DRXZJeHiAES`, `Db5sXEAP6C4`); six are archive reels with no `reels` row and
> stay outside every denominator. Numbers quoted in the chapters reflect the state at compilation
> (266 analysed / 264 with beats); `reports/data/*` and `reports/charts/*` were regenerated after
> the addition and may differ from the chapter text by these few codes.
