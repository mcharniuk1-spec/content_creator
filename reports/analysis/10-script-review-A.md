# 10 — Script review, reviewer A

Prompt version `sr-v1`. Reviewer A, independent of the writer. Cards reviewed:
`C-2026-09-12-01`, `-03`, `-05`, `-07`, `-09` (Script Writer A).

Everything below was recomputed from `data/radar.db`, `data/analysis/insights.json`,
`data/analysis/hypotheses.json`, `data/analysis/hypothesis_refs.json`, `reports/data/alignment.json`,
`reports/analysis/01/06/07/09`, `reports/audit/03/04` and the per-reel transcripts. No number in any
card was accepted on the writer's word.

**A note on the brief.** The reviewer prompt cites `spec §28` and `spec §54`. Neither `SPEC.md`
nor `engine/SPEC.md` has sections numbered that high (`SPEC.md` ends at §11, `engine/SPEC.md` at §9),
and nothing in the repository contains a "ten questions" list. The ten-question checklist below is
therefore taken from the reviewer brief's own item 9 — evidence, hypothesis, references, reasons,
transcripts, stats signals, frame patterns, transformation, original synthesis, why better than
generic — which is exactly ten once "references" and "reasons" are separated. The orchestrator should
either add the section or renumber the citation.

---

## Summary

| Card | Hypothesis | Verdict | Findings | Script changed | `script.version` | `total_s` after review |
|---|---|---|---|---|---|---|
| C-2026-09-12-01 | H-11 | READY_WITH_NOTES | 9 | no | 1 | 68.4 |
| C-2026-09-12-03 | H-18 | READY_WITH_NOTES | 8 | yes | 2 | 69.6 |
| C-2026-09-12-05 | H-13 | READY_WITH_NOTES | 7 | yes | 2 | 68.5 |
| C-2026-09-12-07 | H-20 | READY_WITH_NOTES | 8 | yes | 2 | 69.2 |
| C-2026-09-12-09 | H-05 | READY_WITH_NOTES | 9 | yes | 2 | 68.0 |

Three cards arrived with a hard evidence error — 05, 07 and 09. Two of those, 07 and 09, would have
been NOT_READY as written: card 07's explanation of *why* its two figures disagree was wrong, and
card 09's central distinction contradicted our own audit. Both are fixed and both survive, because in
each case the numbers were right and only their explanation was not.

All five validate with 0 errors and 0 warnings:

```
python3 -m engine.cards_v2 validate cards/C-2026-09-12-01.json   OK
python3 -m engine.cards_v2 validate cards/C-2026-09-12-03.json   OK
python3 -m engine.cards_v2 validate cards/C-2026-09-12-05.json   OK
python3 -m engine.cards_v2 validate cards/C-2026-09-12-07.json   OK
python3 -m engine.cards_v2 validate cards/C-2026-09-12-09.json   OK
```

### What checked out everywhere

- **The writer's three self-reported numbers all reproduce.** H-11: 19 of the top 20 by the pooled
  share+save percentile are `comment_keyword`, and re-ranking inside each `cta_type` puts 8 ungated
  posts in the top 20 — exactly, on the convention percentile = share of the 243 strictly below.
  H-13: `deepdives` has 282 rows, 4 with `suitable` set, all `done_at 2026-09-01`, all rejections, and
  0 of the 23 drafted cards' source reels carry it. H-20: 151 569.5 / 19 624 = 7.72.
- **Reference metrics.** Every `play`, `creator_median_play`, `view_lift`, `share_rate`, `save_rate`
  and `username` in all 21 reference rows matches `video_features` / `reels`. The two `save_rate: -1.0`
  entries on card 03 are genuine NULLs in `video_features` and both `reason` fields disclose the
  sentinel.
- **Corpus counts used in the cards.** Recomputed from `video_features`: `warning_dont` 6, `authority_claim`
  25, `numbers` 36, `demo_walkthrough` 62, `before_after` 5 (second-rarest proof type, behind
  `client_story` at 4). All five cards' "n of 266" statements are correct.
- **Originality.** Zero 5-, 6- or 7-gram overlap between any script line, candidate hook or overlay and
  any beat text of any referenced reel. Every `useful_transcript.quote` is verbatim inside its named
  beat; every `beat_id` and `scene_id` exists in `beats` / `scenes`; every reference matches
  `hypothesis_refs.json` on code and function.
- **Timing arithmetic.** After the edits every `sections[].seconds` equals `words / target_wps` rounded
  to 0.1, every `total_words` and `total_s` sums exactly, every storyboard is contiguous from 0.0 and
  lands on `total_s` to the digit, no scene is under 1.5 s, no overlay exceeds 7 words, no emoji.
- **Positioning.** All five `filter.process` fields are the viewer's own repeated process; our tooling
  appears only as the experiment supplying the evidence. No revenue, savings, time or client claim in
  any script. No service named. No comment gate — `cta_type` is `save_share` (01, 05, 09) or
  `free_resource` (03, 07).

### Two things that were systematically off and are now consistent

1. **The opening frame carried `transition: hard_cut` on all five cards** — a cut into frame one, from
   nothing. Cards 03, 05 and 09 then described their cut counts excluding it while 01 and 07 included
   it, so no two cards counted the same way. All five now open on `none` and every `editing.cut_timing`
   counts only real handovers.
2. **Four of the five CTAs stack two asks** against `01-general-conclusions.md` §G rule 14 (one ask;
   `Da3uSkrNjli` stacks four and lands at view_lift −0.05). Left in place on all four and recorded as a
   finding on each: the filter's `next_action` and PRODUCTION.md's forwarding question are both
   mandatory, and neither can be dropped to satisfy a rule the corpus supports at n=1. This is a
   decision for Misha, not for a reviewer — flagged, not changed.

---

## C-2026-09-12-01 — H-11, "Nineteen of our top twenty were there on a trick"

**Verdict: READY_WITH_NOTES. 9 findings. Script unchanged (`script.version` 1). `total_s` 68.4.**

The strongest card of the five and the only one whose script needed no edit. Every spoken number is
right and reproduces.

### The one that mattered

`claims[0]` said the ranking was "the combined share-and-save percentile **our selection script uses**".
It is not. `score.py` ranks on `W_IG` = views 0.15, engagement 0.15, forwards 0.30, saves 0.30,
comments 0.10, and its own top 20 over the same 243 rows carries **14** gated posts, not 19. The
documented reference-candidate rule (`reports/analysis/06` §6) is different again — the mean percentile
of `robust_z`, `share_rate` and `save_rate` — and gives 17.

The 19-of-20 figure is correct for the ranking the script describes, and the two-rate framing is our
own analysis's reading of our selection (`I-12`: "M2's reference selection ranks by share and save per
1 000"; `01-general` §H item 4: "moves exactly the two rates the radar ranks by"). So the script stands
and the paperwork was fixed instead:

- `claims[0]` and `claims[3]` sources now state the exact ranking and the percentile convention. The
  convention is load-bearing: the midpoint convention gives 62 → 10, not the 61 → 9 in the card.
- Two OBSERVED claims added — the robustness check under the documented pool rule (17/20 gated pooled,
  15/20 after re-ranking within `cta_type`, so the direction holds under both rules) and `score.py`'s
  actual weights.
- `S00` and `assets_required` now specify that the list on screen is ranked on forwards and saves per
  thousand. Shot from the shipped scorer, the top twenty would show 14 gated rows and contradict the
  voice-over.

### Other findings

- `references[0]` called `DZLDk9ySi-7`'s `view_lift` "51.4x". `view_lift` is the ratio minus one, so the
  reel is 52.4× its author's median. Reworded. Not in the script.
- `hooks[1]` restated `hooks[0]` in different words, leaving only two distinct candidates. Replaced with
  a `number_stat` hook built on the rank movement.
- `S07` cited `DczDlj4qQjI`, which is not one of this card's five references (`reports/analysis/09`
  R4/R5 fix the set). Removed; `DTCOU9DkRTG` in the same scene already carries the ungated-close
  borrowing.
- `editing.cut_timing`: six hard cuts → five.
- Left, noted: 21.6–33.2 s asks a level 0–6 viewer to hold three social-media rates at once. The
  mitigation is already in the storyboard — all three pairs on one chart, the flat pair last.
- Left, noted: two asks in the CTA.

### Ten questions

| # | Question | Answer |
|---|---|---|
| 1 | Evidence | I-12's gate multipliers plus a re-ranking of our own 243-row candidate set, recomputed 2026-09-12; every figure reproduces. |
| 2 | Hypothesis | H-11, matches `hypotheses.json`; the card narrows the hypothesis's "six of ten" to the measured 19 of 20. |
| 3 | References | Five, all from `hypothesis_refs.json` for H-11, metrics verified against `video_features`. |
| 4 | Reasons | Each reason names the function and says which of the reel's numbers can be read at face value; three of the five disclose gate inflation. |
| 5 | Transcripts | Five verbatim quotes, each inside its named beat, none reused in the script. |
| 6 | Stats signals | I-12 (2.8× / 1.8× / p=0.578), the CTA-position convergence, the question-vs-save correlation −0.229. |
| 7 | Frame patterns | Screen-first opening (I-09), per-item contribution on screen, A→SCREEN→A, no split state. |
| 8 | Transformation | Ordering, re-hook placement, consequence-then-fix cadence, per-item screen, ungated close — all recorded per reference. |
| 9 | Original synthesis | The failure, the re-ranking and both rank movements; no reel in the corpus shows an author's own system being wrong. |
| 10 | Why better than generic | Names the field that broke the sort, the two multipliers, the thing it does not touch, the fix and the movement the fix produced. |

---

## C-2026-09-12-03 — H-18, "We built it, it worked, and we switched it off"

**Verdict: READY_WITH_NOTES. 8 findings. Script changed (`script.version` 2). `total_s` 69.2 → 69.6.**

Every number reproduces exactly from `reports/data/alignment.json`: 264 codes, 1 527 boundaries checked,
55 aligned (3.60 %), 215 codes with none, and 1 527 of 1 527 beats carrying scene ids.

### Changed line

> **Before:** Two hundred and fifteen videos gave it nothing at all. Some of that is our own measurement
> being coarse. Even so, the videos it matched **performed exactly like** the ones it did not.
>
> **After:** Two hundred and fifteen videos gave it nothing at all. Some of that is our own measurement
> being coarse. And the videos it matched **came out no different from** the ones it did not.

"Performed exactly like" asserts an equality out of a null. The medians are robust_z 1.445 vs 1.251 at
p=0.603, and I-21's own confidence is `INSUFFICIENT` with the interpretation "there is no evidence that
cutting on meaning helps, and no evidence it does not". `claims[3]` was rewritten to say null rather
than same, and `S04`'s overlay "Matched or not, same result" became "Matched or not: no difference
found". Storyboard retimed from S04 (proof 13.8 s → 14.2 s).

### Other findings

- `editing.cut_timing` called everything before the hand-over "a single continuous screen take", but the
  card's own `assets_required` lists four separate screen assets. Rewritten to name two captures plus
  two graphics changed inside the frame, one hard cut kept, now at 48.8 s.
- `claims[0]`'s "never failed" cited only I-21's n=264. There is no `ALIGNMENT` row in the `jobs` table
  at all — the only stages present are `CONCEPT_GENERATION`, `GENERAL_ANALYSIS` and
  `REFERENCE_SELECTION`. The source now also cites `reports/data/alignment.json` and says the claim
  rests on complete coverage of the 264 codes, not on a job-state trace.
- The two `save_rate: -1.0` references verified as genuine NULLs; sentinel disclosed in both reasons.
  Left.
- Hook is 18 words against §G rule 3's 20–30 band. Left: the three sentences are the whole payoff.
- Left, noted: the CTA carries a caption pointer and an action.

### Ten questions

| # | Question | Answer |
|---|---|---|
| 1 | Evidence | I-21 and `reports/data/alignment.json`, recomputed: 55 / 1 527, 215 of 264, all four p-values. |
| 2 | Hypothesis | H-18, matches; the card keeps the hypothesis's stated 3.6 % hit rate. |
| 3 | References | Four, all from `hypothesis_refs.json` for H-18, metrics verified. |
| 4 | Reasons | Each names the function; two disclose that no save count exists; one discloses Hinglish ASR damage. |
| 5 | Transcripts | Four verbatim quotes, each inside its named beat. |
| 6 | Stats signals | Contrarian hook rates, setup-first robust_z 0.67 vs 1.36, split-state 1.03 vs 1.43. |
| 7 | Frame patterns | Subtractive screen opening, one long unbroken take, full-frame rather than inset. |
| 8 | Transformation | Recorded per reference: we remove our own build, state the threshold in advance, concede our own instrument. |
| 9 | Original synthesis | The corpus contains no reel in which an author removes something they built; `warning_dont` is 6 of 266 and all six warn about other people's tools. |
| 10 | Why better than generic | Argues against automation from inside a build, shows the step succeeding first, concedes the measurement, ends on two concrete fields. |

---

## C-2026-09-12-05 — H-13, "The approval box we designed and never ticked"

**Verdict: READY_WITH_NOTES. 7 findings. Script changed (`script.version` 2). `total_s` 68.9 → 68.5.**

### Hard finding — a false clause

`claims[2]`'s source read "20 of the 23 card source codes have a deepdives row". Joined on
`data/radar.db`: **23 of 23** have a row and none has `suitable` set. The script had turned that into a
clause that is simply not true.

> **Before:** All four were filled on the same day, the day we wrote the rule. Every card we have
> drafted since has an empty box behind it, **or no box at all**.
>
> **After:** All four were filled on the same day, the day we wrote the rule. Every card we have drafted
> since **has a row waiting and the box behind it empty**.

Claim rewritten to 23 of 23. Everything else in the card's evidence stands: 282 rows, 4 with `suitable`
set (`DUduffIE5w5`, `DUGghN2E82c`, `DcWCLtCpaKu`, `Dca2CyhJP1B`), all `2026-09-01`, all rejections; and
of the three reels excluded on content grounds in `reports/analysis/09` §4 only `DUduffIE5w5` is in the
field.

### Hard finding — the hook showed nothing

The hook says "Here is the box. Empty." over a close-up of Michael with no box anywhere on screen.
`01-general` §G rule 1 and I-09 both want the artefact first. The hook is now split across two scenes
with no change to a single word:

- `S00` 0.0–5.0 s, face: "We wrote a mandatory check into our own process on the first of September."
- `S01` 5.0–7.3 s, full-frame `UI_DEMO`: "Here is the box. Empty." — the blank column, no presenter.

That also moves the proof screen to 5.0 s instead of 7.3 s. With the box now opening the screen block,
`S02` no longer cuts back out to a document — it is the same take pulling back from the column to the
rule as written, so the whole middle is one continuous screen block between two hard cuts (5.0 s and
49.6 s), exactly as `editing.cut_timing` describes. Scenes renumbered `S00`–`S07`, `idx` 0–7, asset
paths follow; nothing was rendered yet, so no asset is orphaned.

### Other findings

- `claims[0]` rests on `RULES.md`, whose header still marks it a draft awaiting Misha's edits. Left; the
  source now says so. The reel claims we *wrote* the rule, which is what the file records.
- Hook 19 words, one under the §G rule 3 band. Left.
- Left, noted: two asks in the CTA.

### Ten questions

| # | Question | Answer |
|---|---|---|
| 1 | Evidence | `deepdives` (282 / 4 / all 2026-09-01), the 23-card join, `reports/analysis/09` §4 — all recomputed. |
| 2 | Hypothesis | H-13, matches. The card corrects the hypothesis's "3 211 rows, all empty" to the real denominator, 4 of 282, and is right to. |
| 3 | References | Four, all from `hypothesis_refs.json` for H-13, metrics verified. |
| 4 | Reasons | Each names the function and what makes the number readable; `DVaBP3wDAFE`'s fear register and `DczDlj4qQjI`'s gate are both flagged as not reproducible. |
| 5 | Transcripts | Four verbatim quotes, each inside its named beat. |
| 6 | Stats signals | Highest and second-highest save rates in the corpus, the gate multipliers behind deleting `DczDlj4qQjI`'s first ask. |
| 7 | Frame patterns | Long unbroken screen take, persistent title plate, reward bookend, no split. |
| 8 | Transformation | Recorded per reference: three items not four, screen instead of face for the middle, gate deleted rather than softened. |
| 9 | Original synthesis | 25 of 266 reels prove by authority claim and none admits the author's own governance did not run. |
| 10 | Why better than generic | Produces a count — four out of two hundred and eighty-two — instead of advising "keep a human in the loop", and names the difference between a control and a preference. |

---

## C-2026-09-12-07 — H-20, "The same number in two places"

**Verdict: READY_WITH_NOTES. 8 findings. Script changed (`script.version` 2). `total_s` 66.0 → 69.2.**
**As delivered this card was NOT_READY.**

### Hard finding — the mechanism was wrong

The two figures are right. `DdCvFdHsnj1`: 283 515 plays; `scores.author_median_play` 19 624 with
`baseline_n` 11; `video_features.creator_median_play` 151 569.5 with `creator_n` 12. 283 515 / 19 624 =
14.45, 283 515 / 151 569.5 = 1.87, 151 569.5 / 19 624 = 7.72, `percentile_in_creator` 54.17,
`outlier_status` NORMAL. All confirmed against `reports/analysis/07` §1 and `reports/audit/04` row 20.

The **explanation** of why they differ was not right, and it was the whole reel:

> **Before:** Our first number compared this item against eleven others **from one narrow window**.
> Nineteen thousand counted as normal there. / The second compared it against **everything that person
> had ever posted**. There, normal is a hundred and fifty thousand. Same item. Nearly eight times the
> yardstick.

`reels` holds exactly **twelve** reels for `soojintech`, all in snapshot 3. Both yardsticks come from
those same twelve. `score.py` excludes a reel from its own baseline and narrows to an age band *only
when that band itself has enough reels* — `baseline_n` = 11 = 12 − 1 proves the age band was never
applied. So there is no narrow window and no separate history: 19 624 is the middle of the eleven that
are not the item, 151 569.5 is the middle of all twelve.

The real cause is better and is now in the reel. That creator's plays fall into two clumps with nothing
between them — 7 402, 8 231, 9 725, 10 951, 13 057, 19 624, then 283 515, 319 265, 325 781, 326 412,
652 304, 768 383 — so the middle sits in the empty stretch, and removing one high value drops it across
the gap.

> **After:** We hold twelve of this person's videos. Six under twenty thousand views. Six over two
> hundred and eighty thousand. Nothing in between. / Normal is the middle one. Leave this video out and
> the middle is nineteen thousand. Leave it in and the middle falls in the gap, at a hundred and fifty
> thousand.

`claims[1]` rewritten; two OBSERVED claims added (the twelve play counts, and the `HIGH_VARIANCE` label
with the caveat that 115 of 132 creators carry it, so it is not diagnostic on its own); `S02`/`S03`/`S04`
visuals, overlays and `assets_required` rebuilt around the twelve rows and the two middles. The card's
own constraint holds: the words median, baseline and percentile still appear nowhere in the script.

### Other changed lines

> **Before (hook and proof):** … Same item, same week. **We acted on the first one.** / Neither number is
> wrong. Nobody checked which one the decision needed, and the item turned out to be ordinary for its
> author.
>
> **After:** … Same item, same week. **The first one went into the plan.** / Neither number is wrong.
> **Same twelve videos, both times.** Nobody checked which one the decision needed, and the video is
> ordinary for this author.

`reports/audit/04` row 20 records the card as drafted, week 09-10, priority 6, never shot. "Acted on"
implied more than that. `hooks[0]` follows the script.

### Other findings

- `hooks[1]` was `hooks[0]` reordered. Replaced with a distinct `bold_claim`.
- `editing.cut_timing` said "four hard cuts, every one of them a handover"; three are handovers and the
  fourth was the opening frame. `S00` set to `none`, count corrected.
- `strategy.concept` corrected — "two systems compare it against different things" was the same wrong
  mechanism.
- Left, noted: two asks in the CTA.

### Ten questions

| # | Question | Answer |
|---|---|---|
| 1 | Evidence | Both figures, both middles, all twelve play counts, the percentile and the outlier status — recomputed from `scores`, `video_features`, `reels` and `creator_stats`. |
| 2 | Hypothesis | H-20, matches. The hypothesis's "same database" framing is now literally true; its implied two-systems story was not, and the card no longer carries it. |
| 3 | References | Four, all from `hypothesis_refs.json` for H-20, metrics verified. |
| 4 | Reasons | Each names the function; two disclose that the multiplier rests on a tiny author median; one is used explicitly as a negative example. |
| 5 | Transcripts | Four verbatim quotes, each inside its named beat; `DUJYKENjZc5`'s mis-transcribed tool names flagged as not carried. |
| 6 | Stats signals | Money framing 1.19 vs 2.12, the withheld-artefact save rate, `robust_z` per reference. |
| 7 | Frame patterns | Screen-face-screen, the figure spoken over the record it describes, one named thing per beat. |
| 8 | Transformation | Recorded per reference, including the inversion of `DVtgbY8Av6A` — publish the sheet instead of gating it. |
| 9 | Original synthesis | No reel in the corpus corrects its own number; 36 use numbers as proof and all present them as settled. |
| 10 | Why better than generic | Nothing hallucinated — both figures are arithmetically correct on the same twelve rows, which is why reviewing harder does not catch it. |

---

## C-2026-09-12-09 — H-05, "Supported is not the same as connected"

**Verdict: READY_WITH_NOTES. 9 findings. Script changed (`script.version` 2). `total_s` 68.8 → 68.0.**
**As delivered this card was NOT_READY.**

### Hard finding — the card contradicted our own audit

> **Before:** **It was on the list of things that tool supports. The database was simply not shared with
> it.** The one place that was shared saved everything, first time.

`claims[4]` backed that with "the 404 body itself names the cause". It does not — it names a remedy.
`reports/audit/03` §4 reads the same evidence the other way: the three Notion databases were moved to
trash around 7 September and the 404 text is Notion's generic "the integration lost access" message.
§3 shows the same destination *answering* on 2026-09-07 — step 7 "statuses updated: 5", step 10 "9 of 9
uploaded" — and gone by the 10th. The connection existed and was removed. It was never
listed-but-never-made.

> **After:** **Three days earlier that same connection worked. Someone moved the destination and the tool
> lost it.** The one place nobody moved saved everything, first time.

The payoff had to move with it, and the reel is stronger for it:

> **Before:** Supported is not the same as connected. Write down the three systems your work already
> lives in, and check them against the tool's own list before the trial starts.
>
> **After:** Supported is not the same as connected, **and connected is not the same as still
> connected.** Write down the three systems your work lives in and check them by name.

`claims[4]` rewritten as OBSERVED against both runs; `strategy.concept`, `strategy.objective` and
`filter.friction` corrected; `S04` rebuilt as the two runs side by side (overlay "Worked Monday. Gone
Thursday." — 2026-09-07 is a Monday, 2026-09-10 a Thursday, both checked). A MISSING claim was added
recording that no integrations page was ever opened, so the reel makes no claim about what any
published list says.

### Hard finding — the chain was miscounted

> **Before:** Our own weekly run is a chain like that. **Five named places.** On Thursday two of them
> refused us.
>
> **After:** … **Six named places.** …

Step 1 (Hiker, 130 accounts, $2.60) succeeded. The source that went silent in step 5 is `freeprofile.py`,
the free public-profile source — a different system, and it was folded into the same link as the paid
source. `claims[0]`, `S02`'s visual and overlay and `assets_required` all now say six.

### Other findings

- `claims[2]` said "the same 404" on one database. Steps 7 and 10 are the Cards database
  (`d5b6ab42-…`); step 12 is the Reels database (`679fa6d6-…`) — the same message on two destinations.
  Claim reworded. The spoken line, "the notes tool said the same thing three times", is accurate and
  stays.
- **Every source cited `data/runs/2026-09-10_0700.log`, which is not in this repository.** `data/runs/`
  does not exist locally; the log is on the server. All four sources now cite `reports/audit/03` §3,
  which quotes it, and name the server path.
- `S00` opened on `transition: hard_cut` against the card's own "three hard cuts". Set to `none`.
- Left, noted: the script has no problem or friction section, against §G rule 11 and POSITIONING §8's
  second filter item. The friction is carried by the hook's second sentence and by `S04`; adding a
  section would push the reel past 70 s.
- Verified unchanged and quoted verbatim in the audit: five silent attempts, 0 of 130 profiles updated,
  three 404s, the page destination succeeding.

### Ten questions

| # | Question | Answer |
|---|---|---|
| 1 | Evidence | Two run logs three days apart, quoted step by step in `reports/audit/03` §3, plus §4's reading of the cause. |
| 2 | Hypothesis | H-05, matches. The card keeps the hypothesis's connector-list thesis and corrects its failure story. |
| 3 | References | Four, all from `hypothesis_refs.json` for H-05, metrics verified. |
| 4 | Reasons | Each names the function; `Db9MT-axxcO` is flagged as an undisclosed tool partnership we must not reproduce, `DVZGBgTk6zz`'s 304× as resting on a 1 374-view median. |
| 5 | Transcripts | Four verbatim quotes, each inside its named beat. |
| 6 | Stats signals | Distinct entities vs view_lift +0.161 pooled / +0.198 within creators — the only reach correlation that survives normalisation, and the reason this script is built out of names. |
| 7 | Frame patterns | Screen-first held to 49.2 s, the settings screen rather than a marketing page, no split state. |
| 8 | Transformation | Recorded per reference: the viewer's own inbox, sheet and calendar instead of a sponsor's product; no outcome number of any kind. |
| 9 | Original synthesis | The corpus names tools constantly and integrations almost never; the failure is ours, dated, and quotable from two logs. |
| 10 | Why better than generic | Separates supported, connected and still connected out of two real logs, instead of listing five tools that integrate with Gmail. |

---

## For the orchestrator

1. `spec §28` / `spec §54` do not exist. Either add them or fix the reviewer prompt's citation.
2. The one-ask CTA rule (§G rule 14) and the mandatory four-part filter's `next_action` are in direct
   conflict for every card in this batch. Four of five cards ship with two asks. This needs a decision,
   not a per-card judgement.
3. `data/runs/*.log` is server-only and is not in the repository, but the writer brief lists our run
   logs as a permitted evidence source. Either sync the logs into `reports/data/` or restrict the brief
   to the audit reports that quote them.
4. `score.py`'s ranking and `reports/analysis/06` §6's candidate-pool rule are two different rankings,
   and neither is the pooled share+save percentile that card 01 is built on. All three point the same
   way on the gate question, but "our system's list" is ambiguous until one of them is named as the
   list.
