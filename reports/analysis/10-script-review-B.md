# 10 — Script review, part B

Independent review (prompt version `sr-v1`, spec §28) of the five cards written by Script Writer B:
`C-2026-09-12-02`, `-04`, `-06`, `-08`, `-10`. The reviewer did not write them.

**What was checked, in the order the brief sets.** Every number in every script was recomputed from
`data/radar.db` (`reels`, `video_features`, `creator_stats`, `cards`, `spend`), from
`data/analysis/transcripts/*.json`, from `reports/data/*.json` and from `reports/audit/*.md`, rather
than read back from the card. Every reference's `play`, `creator_median_play`, `view_lift`,
`share_rate` and `save_rate` was re-derived from the raw snapshot rows. Every reference quote was
matched against `beats.text` for the beat id given. Every script was compared with the full beat text
of all four of its references by shared word sequence. Timing arithmetic, storyboard contiguity,
overlay length and the schema were checked mechanically.

**Headline.** The evidence base is unusually solid: of roughly sixty numbers checked, three were wrong
and one was unreproducible. All four are corrected below. Two script lines said more than the data
does and one carried a verbatim sentence from a reference; all three were rewritten. Every card now
validates with 0 errors and 0 warnings and sits inside the 50–70 s band.

| card | hypothesis | verdict | findings | script revised | `total_s` after review |
|---|---|---|---:|---|---:|
| C-2026-09-12-02 | H-12 | READY_WITH_NOTES | 14 | yes (v2) | 65.2 |
| C-2026-09-12-04 | H-01 | PRODUCTION_READY | 13 | yes (v2) | 68.0 |
| C-2026-09-12-06 | H-04 | READY_WITH_NOTES | 13 | yes (v2) | 69.2 |
| C-2026-09-12-08 | H-09 | READY_WITH_NOTES | 13 | yes (v2) | 69.6 |
| C-2026-09-12-10 | H-19 | PRODUCTION_READY | 13 | yes (v2) | 66.4 |

All five are set to `status: "REVIEWED"`, `review.version: 1`, `review.revised: true`,
`script.version: 2`.

---

## The four numeric verdicts the brief asked for

**1. H-12: "27 notes / 118 of 266".** The 27 reproduces exactly; the 118 does not.

Recounting `data/analysis/transcripts/*.json` `notes`, 27 of the 266 notes record the product name
Claude (or Claude Code) written by the machine as `cloud`, `clouds`, `cloth`, `claw`, `clawed` or
`Clawd`. Three further notes match those words but refer to something else — `DVaBP3wDAFE` and
`DcvzztfCabY` are about the separate product OpenClaw, `DbvdNboM_Nn` about Google Cloud — and are
excluded. Widening the rule to any mis-spelling of the same name (`clod code`, `called code`,
`Quad AI`, `Claudecoat`, `Openclaw desktop`, `load code`) gives 34. The counting rule and the three
exclusions are now written into `claims[0].source` so the figure can be re-derived.

The 118 could not be reproduced under any rule tried. Mechanically: 191 of 266 notes mention the
transcription at all (`ASR` appears in the text), 167 contain a mapping of some shape, and 140 contain
an explicit correction on the strictest defensible rule (a quoted token followed by `=`, `is`, `for`
or `means`). None of these is 118, and none of the intermediate rules lands there either. The claim
was rewritten to the two reproducible figures (191 / 140, with the rule stated) and the imprecise
"mangled proper noun, product name or figure" count was added separately as `TO_MEASURE`. The 118 is
not spoken on screen, so the script is unaffected.

**2. H-19: 23 weekly cards (5 / 9 / 9), not 33.** Confirmed. `data/radar.db` `cards` returns 23 rows:
5 in week 2026-09-03, 9 in 09-07, 9 in 09-10; statuses are 9 `вычеркнута`, 5 `Proposed`, 9 `draft`;
`our_posts` and `our_metrics` are both empty; three source codes appear twice across weeks
(`DcvBtiNtbYO`, `Dco1mOJzZ4L`, `DcwCCgivcIQ`). `reports/audit/04-existing-cards-review.md` reaches 33
only by adding Max's separate ten-card lane to our 23, and it classifies two of the three repeats as
"recycled, then cut without a new angle". The writer's correction stands.

**3. H-01: `Dc_TX1CttIc` `save_rate` 0.0.** Confirmed as a placeholder, not a measurement. The reel
appears in one snapshot only (3), with `save` NULL; `video_features.save_rate` is NULL too, and
`reports/analysis/09-reference-selection.md` already prints `save n/a/1k` for it. The writer's reason
field did say so. Per the orchestrator's mid-review update the validator now accepts null, so
`save_rate` is now `null` and the "SAVE RATE NOT MEASURED" note stays at the head of the reason.

**4. `DMQMNNHSJRF` save rate 0.0508 from snapshot 2.** Confirmed exactly. Snapshot 2 returned
`save = 7 146` on `play = 140 686` → 0.050794. Snapshots 1 and 3 returned no save count. The card's
`play` (140 763) and `share_rate` (4 947 / 140 763 = 0.035144) come from snapshot 3, which is the
convention used throughout, and the reason field states the mixed provenance. `save_rate` is
correctly *not* nulled here: the count exists, it is just older than the play figure.

**5. The $17.78 ten-day bill.** Traceable line by line. `reports/data/spend.json` and the `spend` table
in `data/radar.db` agree: 10 entries dated 2026-09-01 to 2026-09-10, 889 units, `price` 0.02 on every
row, `total_usd` 17.78, and 889 × 0.02 = 17.78 exactly. The sixteen cents paid twice are entries 6 and
7, both 2026-09-03 (52 units interrupted, then 8 re-fetched because the answers had left the cache).
The weekly line is entry 10 (130 accounts, $2.60) — but see the finding on card 04: entry 8 shows the
same job at $2.12 a week earlier.

---

## C-02 — "The wrong name in twenty-seven files" (H-12, M2 Builds)

**Verdict: READY_WITH_NOTES.** 14 findings; script revised to version 2; `total_s` 65.2 (unchanged —
the edit swapped one word).

### Revised

*Hook, and the same phrase in both alternative hooks and in storyboard S00:*

- Before: "We ran two hundred and sixty-six recordings through a machine. Twenty-seven came back with
  the **wrong company name** in them."
- After: "We ran two hundred and sixty-six recordings through a machine. Twenty-seven came back with
  the **wrong product name** in them."

Claude is a product; the company behind it is never named anywhere in the reel, and `claims[0]`,
`strategy.concept` and the notes themselves all say product name. Twenty words either way, so the
timing is untouched.

### Findings

1. **[evidence]** `claims[1]`'s "118 of 266" is not reproducible → rewritten to 191 / 140 with the
   counting rule stated, plus a new `TO_MEASURE` claim for the figure that cannot be pinned down.
2. **[evidence]** The 27 of 266 reproduces exactly → kept, with the rule and the three exclusions
   written into the source field.
3. **[evidence]** "wrong company name" → "wrong product name" (above).
4. **[evidence]** The five-field check is presented as something we already run, and the storyboard
   asks for a screen recording of it — but it exists nowhere in the repository, only in the H-12
   planning note and in this card, and no claim recorded it as `PLANNED` (unlike cards 06 and 08,
   which flag their demos) → a `PLANNED` claim added. **The card must not be shot until that footage
   exists.** The script is unchanged: a human checklist read against a real transcript file is
   genuinely filmable.
5. **[evidence]** The hypothesis proof's "11 correct and 7 incorrect" is indeed not reproducible from
   the transcripts; the writer's substitution of the 27 count is confirmed → left.
6. **[evidence]** "Seven of the 273 transcript rows came back with no words at all" matches
   `reports/audit/02-data-inventory.md` §4 (273 rows, 7 empty) → left.
7. **[evidence]** The four named misreads all check out against the files cited: `Kenwa` for Canva in
   `Dbs2JdJKUDd`, `anything` for n8n and `a level lab` for ElevenLabs in `DUJYKENjZc5`, `Chachi BT`
   for ChatGPT in `DTCOU9DkRTG` → left.
8. **[evidence]** All four reference metric sets re-derived from `data/radar.db` and match to the last
   digit; all four function tags match `data/analysis/hypothesis_refs.json` → left.
9. **[source relevance]** `DYC-x8DogOI`'s "highest view_lift in the corpus" is true of the 266-reel
   analysis-ready corpus only; the full 3 211-reel corpus goes higher → qualified in the reason.
10. **[originality]** No shared five-word sequence with any of the four reference transcripts; all four
    quotes are verbatim from the beat ids given and stay inside `useful_transcript` → left.
11. **[originality]** "Every one of the 84 screen-demo reels shows the thing working" was asserted
    without a source. It is in fact supported by `01-general-conclusions.md` §G writing rule 12
    ("Nothing in the corpus shows a failure") → citation added to the rationale and to
    `original_synthesis`.
12. **[visual]** The second screen insert lands at 29.2 s, not the 28.8 s the writer's own note said,
    against rule 12's 20–25 s. Accepted because the reel opens on a screen at 0.0 s (I-09, RELIABLE)
    and the failure is itself the first proof visual → left, note corrected.
13. **[positioning]** No vendor named, no split screen (I-10), no comment gate (RULES.md §1.2, I-12),
    no time-saving or client claim (POSITIONING.md §6); CTA is a single save_share ask with the
    artefact published in the caption → left.
14. **[timing / schema]** 163 words at 2.5 wps, every section = words / wps, storyboard contiguous
    0.0–65.2 s, no scene under 1.5 s, every overlay ≤ 7 words; validator 0 errors → passes.

### Spec §54 checklist

1. **Insights** — I-08, I-09, I-11, I-13, I-15, I-18, I-29; all seven ids exist in `insights.json`.
2. **Hypothesis** — H-12, matches `hypotheses.json`; its unreproducible 11/7 proof was replaced and the
   replacement verified.
3. **Evidence** — our own 266-file transcription run, recounted by the reviewer; 27 / 266, 7 of 273
   empty, four named misreads, all reproducible from files in the repo.
4. **References with reasons** — four, functions `hook` / `explanation` / `screen_proof` /
   `transition`, all matching `hypothesis_refs.json`, each with a reason naming the mechanism borrowed.
5. **Transcripts** — four verbatim beat quotes, all matched against `beats.text`; the template-cluster,
   attribution and lag-warning notes the reasons cite are all present in the analysis files.
6. **Stats signals** — I-09 (screen-first share 0.0213 vs 0.0140, cn +0.285, p=0.00025), I-18 (84
   screen demos of 266), I-29 (resource_handoff save 0.0429, the highest solution type), I-12 (the gate
   buys no reach); all verified against `01-general-conclusions.md`.
7. **Frame patterns** — screen-first opening, four full-frame inserts, one continuous presenter take,
   no split screen; consistent with PRODUCTION.md and I-10.
8. **Transformation** — each `transformed_how` names what is borrowed and what changes; verified as
   structure only, zero shared five-word sequences.
9. **Original synthesis** — showing our own broken output rather than a working one, the five-field
   check, and naming what the check cannot catch; the "nothing in the corpus shows a failure" support
   is now cited.
10. **Why better than generic** — states the exact shape of the failure, publishes the artefact instead
    of gating it, closes on the limitation; all three are evidenced rather than asserted.

---

## C-04 — "Cost per run, not price per month" (H-01, M2 Radar)

**Verdict: PRODUCTION_READY.** 13 findings; script revised to version 2; `total_s` 68.0 (was 67.2).

### Revised

*Proof section, and storyboard S03:*

- Before: "Here is the line that repeats every week. A hundred and thirty accounts, one page each. Two
  dollars sixty. That is the number to defend, not the plan name." (29 words / 11.6 s)
- After: "Here is the line that repeats every week. **Last week,** a hundred and thirty accounts, one
  page each. Two dollars sixty. That is the number to defend, not the plan name." (31 words / 12.4 s)

The ledger shows the same weekly job at $2.12 on 7 September (106 accounts) and $2.60 on 10 September
(130 accounts). $2.60 is not a constant, it is last week's figure, and the line now says so.

### Findings

1. **[schema]** `Dc_TX1CttIc.save_rate` 0.0 was a placeholder for a count the provider never returned
   → set to `null` per the orchestrator's update; the "not measured" note stays in the reason.
2. **[evidence]** The whole ledger reproduces: 10 entries, 1–10 September 2026, 889 units at $0.02,
   $17.78, arithmetic exact → left.
3. **[evidence]** The sixteen cents paid twice are ledger entries 6 and 7, both 2026-09-03 → left.
4. **[evidence]** "The repeating weekly collection run costs $2.60" was stated as a fixed weekly figure
   → claim rewritten to name both runs, and the spoken line dated (above).
5. **[evidence]** `engine/SPEC.md` §0.8 does require a printed estimate and `--yes` before any spend →
   left as OBSERVED.
6. **[evidence]** All four reference metric sets re-derived and matching; all four function tags match
   `hypothesis_refs.json` → left.
7. **[originality]** "84 have a money-shaped desire and every one of them frames it as money not spent
   on somebody else's product" is a universal the sources do not state. §B classifies 84 reels as
   money-saving desire and I-25 counts 71 money-framed reels → rewritten in the rationale and in
   `original_synthesis` to what the sources say. The load-bearing original point — nobody shows their
   own bill — is unchanged.
8. **[positioning]** "Six hundred times a day" is the only unsourced figure spoken; labelled on screen
   as an example and recorded MISSING → left.
9. **[positioning]** No vendor named, no savings claim (POSITIONING.md §6), no comment gate, no split
   screen, one CTA ask → left.
10. **[hook]** 20 words / 8.0 s, three candidates, one question, first one used, money figure in the
    opening sentence over a real screen → left.
11. **[visual]** Opens on the ledger at 0.0 s (I-09); four screen inserts; presenter take continuous;
    overlays ≤ 7 words → left.
12. **[timing / schema]** Recomputed after the edit: 170 words, 68.0 s, storyboard contiguous
    0.0–68.0 s; validator 0 errors → passes.
13. **[scheduling]** This card, C-06 and C-10 all open on our own pipeline artefacts. Keep at least a
    week between them.

### Spec §54 checklist

1. **Insights** — I-05, I-08, I-09, I-13, I-15, I-25, I-29; all exist.
2. **Hypothesis** — H-01, matches; the hypothesis' own $17.78 hook figure verified against the ledger.
3. **Evidence** — our own spend ledger, every line reproducible from `reports/data/spend.json` and the
   `spend` table.
4. **References with reasons** — four, functions `explanation` / `pain` / `proof` / `hook`, matching
   `hypothesis_refs.json`.
5. **Transcripts** — four verbatim quotes, all matched against `beats.text`.
6. **Stats signals** — cost_money the largest pain cell (n=48, 33 creators), money-saving desire save
   0.0306 vs 0.0250 at p=0.007, money framing view_lift 1.19 vs 2.12 (I-25), I-09 for the opening; all
   verified.
7. **Frame patterns** — ledger-first opening, two ledger inserts, A-roll for the arithmetic and the
   verdict, no split screen.
8. **Transformation** — each `transformed_how` names the borrowed shape and the change; verified as
   structure only.
9. **Original synthesis** — the itemised ledger, the single division, the repeating line item and the
   volunteered duplicate charge; all ours and reproducible.
10. **Why better than generic** — one division on a real bill instead of a three-tool price comparison,
    and it refuses the savings claim the format invites.

---

## C-06 — "The pause is the feature" (H-04, M2 Radar)

**Verdict: READY_WITH_NOTES.** 13 findings; script revised to version 2; `total_s` 69.2 (was 68.8).
The two runs do not exist as footage yet.

### Revised

*Hook, and hooks[0], and storyboard S00:*

- Before: "**Watch this.** The reply is written, it is right, and it is going nowhere until somebody
  presses a button." (19 words / 7.6 s)
- After: "**Watch this reply sit here.** It is written, it is right, and it goes nowhere until somebody
  presses the button." (20 words / 8.0 s)

"Watch this." is verbatim the first sentence of `DTCOU9DkRTG` beat B0 — the very beat this card quotes
in `useful_transcript`. Script-writer rule 4 puts verbatim reference wording in the quote field and
nowhere else. The rewrite keeps the hypothesis' own imperative-over-a-running-screen shape.

*Example section, and storyboard S04:*

- Before: "We counted our own. Twenty-five named steps **between a video going in and a plan coming
  out**, and one place where it waits for a person. That person struck out nine of the last
  twenty-three."
- After: "We counted our own. Twenty-five named steps **from a video coming in to the job being
  finished**, and one place where it waits for a person. That person struck out nine of the last
  twenty-three."

`engine/SPEC.md` §3 lists 25 stages from `DISCOVERED` to `COMPLETED`. The plan appears at
`CARD_GENERATION`, the sixteenth; nine more stages follow it. Same 35 words, no timing change.

### Findings

1. **[originality]** Verbatim "Watch this." from a quoted reference beat → hook rewritten (above).
2. **[evidence]** "twenty-five steps between a video going in and a plan coming out" misstates the
   stage list → rewritten (above). `claims[0]`, which said "between a video being discovered and a run
   completing", was already correct and is unchanged.
3. **[evidence]** `Dbi-yxNgrhG` was called "the highest share rate in the entire analysis-ready
   corpus". It is fourth — `Dc_tsSeAjBy` 61.3, `DcvBtiNtbYO` 59.2 and `DMu90OwPzno` 58.9 per 1 000 are
   higher — and the card's own source (`06-creators-and-references.md` §6, row 22) already says
   "third-highest" → corrected to "highest in the 40-reel pool, fourth in the analysis-ready corpus",
   in the reference reason and in `traceability`.
4. **[evidence]** `DTCOU9DkRTG` "52x its author's median" misreads the convention: 52.04 is `view_lift`
   = play / median − 1, so the reel is 53× its author's median → reworded to "52.0x lift".
5. **[evidence]** The 25 stage names, the 23 cards, the 9 struck out and `SPEC` §0.3 (paid provider
   registered but off, no credentials on the default path) all reproduce → left.
6. **[evidence]** `claims[7]` is faithful to the H-04 novelty note in `hypotheses.json` and
   `08-hypotheses.md`, and the single instance really is `DczDlj4qQjI` beat B3 → left.
7. **[evidence]** All four reference metric sets re-derived and matching; functions match
   `hypothesis_refs.json`; all four quotes verbatim from the beat ids given → left.
8. **[evidence]** The demo is `PLANNED`. **The card must not be shot until both runs exist as
   footage** — repeated here so it survives the review → left.
9. **[positioning]** The two runs are full-frame and sequential, never side by side (I-10, and the
   hypothesis reviewer's explicit warning) → left.
10. **[positioning]** No vendor named, no comparison claimed, no comment gate, no time or savings
    claim, one CTA ask → left.
11. **[visual]** Opens on the screen at 0.0 s (I-09) rather than the A>SCREEN>A the hypothesis
    proposed; the A>SCREEN>A run I-11 rewards is preserved from scene 1 on; three of seven scenes are
    screens, which is the fix for the compliance-lecture risk → left.
12. **[timing / schema]** Recomputed: 173 words, 69.2 s, storyboard contiguous 0.0–69.2 s; validator
    0 errors → passes.
13. **[scheduling]** This card describes the Monday as twenty-five named stages while C-10 describes
    the same Monday as five steps. Both are honest at their own level of description; do not publish
    them in the same week.

### Spec §54 checklist

1. **Insights** — I-05, I-08, I-09, I-11, I-13, I-15, I-27; all exist.
2. **Hypothesis** — H-04, matches; its novelty note and its no-split-screen warning are both honoured.
3. **Evidence** — `SPEC` §3's 25 stages, `SPEC` §0.3, and 9 of 23 struck from `data/radar.db`; all
   verified. The on-screen demo is PLANNED and marked as such.
4. **References with reasons** — four, functions `explanation` / `proof` / `topic` / `hook`, matching
   `hypothesis_refs.json`; two superlatives in the reasons corrected.
5. **Transcripts** — four verbatim beat quotes, all matched; the "unverified privacy claim" note the
   `Dbi-yxNgrhG` reason relies on is present in that file.
6. **Stats signals** — I-09 (screen-first), I-11 (A>SCREEN>A 0.0213 vs 0.0140, p=0.00076, n=39 / 32
   creators), I-10 (split penalty); all verified.
7. **Frame patterns** — screen-first, sequential full-frame runs, presenter for the three positions and
   the close; consistent with PRODUCTION.md.
8. **Transformation** — each `transformed_how` names the borrowed element; the one verbatim carry-over
   found in the script has been removed.
9. **Original synthesis** — the pause as the subject rather than as reassurance, the three-positions
   frame, and our own gate ratio offered as an experiment.
10. **Why better than generic** — replaces a feature comparison with one screen to ask for, and refuses
    to claim the gate prevents anything, because we have not measured it.

---

## C-08 — "The paragraph that beat the agents" (H-09, M2 Radar)

**Verdict: READY_WITH_NOTES.** 13 findings; script revised to version 2; `total_s` 69.6 (was 69.2).
The two runs do not exist as footage yet.

### Revised

*Example section, and storyboard S04:*

- Before: "…A hundred and fifteen measurements across two hundred and sixty-eight videos. **Not one
  separated** a strong reel from a weak one. What survived was a question we could have asked on day
  one." (40 words / 16.0 s)
- After: "…A hundred and fifteen measurements across two hundred and sixty-eight videos. **Not one
  reliably separated** a strong reel from a weak one. What survived was a question we could have asked
  on day one." (41 words / 16.4 s)

`01-general-conclusions.md` §C and I-22: none of the 115 features reaches p<0.01, but **seven reach
p<0.05**. Seven of them do separate the quartiles at the weaker bar. "Reliably" is exactly the
project's own RELIABLE threshold and makes the sentence true. One word; the reel goes to 69.6 s, still
inside the band.

### Findings

1. **[evidence]** "Not one separated a strong reel from a weak one" overstates the result → "not one
   reliably separated" (above).
2. **[evidence]** `claims[1]` said "none at all against the reach measure". None is against `robust_z`,
   but one RELIABLE pair (`lex_entities_distinct` → `view_lift`, +0.161, cn +0.198) is against
   view_lift, also a reach measure → claim reworded to name `robust_z` and to state the view_lift pair.
3. **[evidence]** `DbVKVz0y8xo` was credited with "the highest median view_lift of any visual sequence
   in the corpus (30.90 on n=6)". `reports/data/visual_patterns.json` has
   `A_ROLL_CLOSE_UP>SCREENSHOT>A_ROLL_CLOSE_UP` at 52.04 on n=3 → qualified to "the highest of any
   sequence with more than three reels behind it", in the reference reason and in `traceability`.
4. **[evidence]** The other headline numbers all reproduce: 115 features / none at p<0.01 / seven at
   p<0.05 (I-22, §C); 460 pairs and 13 RELIABLE (§C); I-08 (+0.203, p=0.00085, survives normalisation);
   agent building n=27 at 6.63 and 23 `agent_build` solution types (I-25, I-29); contrarian hooks at
   0.0076 share / 0.0139 save, the lowest of the large hook cells (§D); myth_bust at robust_z 1.93 on
   the smallest explanation share (`05-script-parts.md` §6) → left.
5. **[originality]** "Not one of them argues against the build" is the hypothesis' own novelty note,
   but the corpus does contain `DcbPb2yxrTx` ("Please stop building Jarvis dashboards", myth_bust /
   warning_dont, agent-building topic), which argues against the dashboard while defending the
   architecture underneath → the near-counter-example is now named in `traceability` and
   `original_synthesis`, so the novelty claim is falsifiable rather than absolute. Not spoken on
   screen, so no script change.
6. **[evidence]** All four reference metric sets re-derived and matching; functions match
   `hypothesis_refs.json`; all four quotes verbatim; no shared five-word sequence with any of the four
   transcripts → left.
7. **[evidence]** The demo is `PLANNED`. **If the two runs are not both recorded, the card must not be
   shot** — the hypothesis names "sounds like an opinion" as its main risk → left.
8. **[hook]** Demo-first rather than contrarian, per the hypothesis reviewer's note; the disagreement
   is shown and never spoken; 19 words / 7.6 s → left.
9. **[positioning]** No clock or timer overlay, because a speed comparison we have not measured would
   be a claim (recorded TO_MEASURE); the elaborate run is filmed to look as impressive as the genre
   does and the stalled step is not dressed as a failure → left.
10. **[positioning]** No split screen, no comment gate, no income or savings framing, no vendor named →
    left.
11. **[visual]** Coarse sequence SCR>A: the first three sections are one unbroken filmed-monitor take
    and the presenter appears only for the verdict — pattern 4 in `03-visual-patterns.md`. Opens on a
    running screen at 0.0 s (I-09) → left.
12. **[timing / schema]** Recomputed: 174 words, 69.6 s, storyboard contiguous 0.0–69.6 s; validator
    0 errors → passes.
13. **[note]** `01-general-conclusions.md` §C prints twelve rows in its RELIABLE table while its own
    text and §H say thirteen, and then adds two more pairs "reported as RELIABLE in the insights file".
    The card cites 13, which is what the source states; the source's own arithmetic is worth a look by
    the orchestrator.

### Spec §54 checklist

1. **Insights** — I-05, I-08, I-09, I-16, I-22, I-25, I-27; all exist.
2. **Hypothesis** — H-09, matches; its register warning (open on the demo, not the disagreement) is
   honoured.
3. **Evidence** — our own failed measurement: 115 features, 268 analysis-ready videos, none reliable at
   p<0.01; verified against I-22 and §C.
4. **References with reasons** — four, functions `explanation` / `b_roll` / `proof` / `topic`, matching
   `hypothesis_refs.json`; one superlative corrected.
5. **Transcripts** — four verbatim beat quotes, all matched; the 'Kenwa' ASR note the `Dbs2JdJKUDd`
   reason cites is present in that file.
6. **Stats signals** — I-22, I-08, I-25, the contrarian hook cell and the B_ROLL_PROCESS sequence; all
   verified, one qualified.
7. **Frame patterns** — one continuous process shot for the first act, the elaborate run filmed across
   the room, the presenter only for the verdict; no clock overlay.
8. **Transformation** — each `transformed_how` names the borrowed element, including `DVaBP3wDAFE`
   used as a foil rather than a model.
9. **Original synthesis** — a demonstrated "the small version won" with the author's own overbuild as
   the evidence, plus the three questions; the nearest counter-example in the corpus is now named.
10. **Why better than generic** — opens on the demo rather than the disagreement, runs both versions in
    the footage, and uses a thing we did badly as the proof.

---

## C-10 — "Twenty-three plans, nothing made" (H-19, M2 Teardown)

**Verdict: PRODUCTION_READY.** 13 findings; script revised to version 2; `total_s` 66.4 (was 66.8).

### Revised

*Explanation section, and storyboard S02 (script text, overlay, visual and editing note):*

- Before: "**Collecting took the machine sixty-five minutes. Scoring is instant. The shortlist is a
  table.** Striking out is the one step that waits for one of us, and it removed nine of the
  twenty-three." (33 words / 13.2 s)
- After: "**The whole machine run took sixty-five minutes. Collecting, scoring, shortlisting, all of
  it.** Striking out is the one step that waits for one of us, and it removed nine of the
  twenty-three." (32 words / 12.8 s)

`reports/audit/03-server-runtime-hiker.md` times the run of 2026-09-10 as 07:00–08:08, 65 minutes, for
all thirteen steps together — *"прогон занял 65 мин"*. No individual step has a recorded duration, so
the 65 minutes cannot be attached to "collect", and "Scoring is instant" had no source at all. The S02
overlay went from "65 minutes. Instant. Nine struck." to "65 minutes. Nine struck.", and the visual now
brackets the one figure across the four automated rows instead of putting it on the collect row.

### Findings

1. **[evidence]** 65 minutes is the whole weekly run, not the collection step; "Scoring is instant" was
   unsourced → line, claim, overlay, visual and editing note all rewritten (above).
2. **[evidence]** `DYuivWzSj5k` was called "the second-highest share rate in the pool". It is fourth:
   `Dbi-yxNgrhG` 58.4, `Dbd7VDgP9PR` 53.4 and `DbO4zvJR1k8` 52.9 per 1 000 are higher in the same
   40-reel pool → corrected in the reason and in `traceability`.
3. **[evidence]** `Db9MT-axxcO` was called "best combined share and save rates in the corpus". It is
   third, and the card's own source (`06-creators-and-references.md` §6, row 32) already names the two
   higher rows → corrected to "third-best", with both named.
4. **[evidence]** "1.62x its author's median" misreads the lift convention: `view_lift` is
   play / median − 1, so a lift of 1.62 is 2.62× the median → reworded to "on a lift of only 1.62x",
   and "51x multiplier" to "51.4x lift". The point being made — that the reach multiplier is not the
   finding — is unchanged.
5. **[evidence]** The counting that carries the reel reproduces exactly from `data/radar.db`: 23 cards
   across three weeks (5 / 9 / 9), 9 struck out and 14 developed, `our_posts` and `our_metrics` empty,
   three source codes proposed twice → left.
6. **[evidence]** The writer's use of 23 rather than the hypothesis' 33 is confirmed → left.
7. **[evidence]** All four reference metric sets re-derived and matching; functions match
   `hypothesis_refs.json`; quotes verbatim; no shared five-word sequence with any of the four
   transcripts → left.
8. **[positioning]** The Teardown pass criteria are met: a named process with a named owner in shot
   ("the one step that waits for one of us"), and a reason to forward (the count of zero). RULES.md §2
   names our own processes as the only Teardown source available today → left.
9. **[hook]** Opens on the artefact rather than on a recognisable morning, reversing the hook
   reference's direction, because openings spent on the audience carry median robust_z 0.67 against
   1.36, p=0.002 (I-06). 19 words / 7.6 s, three candidates, one question, first one used → left.
10. **[positioning]** No split screen, no comment gate, no stock footage, no invented duration for the
    human step (MISSING), no claim that naming an owner fixes anything (TO_MEASURE) → left.
11. **[visual]** Screenshot at 0.0 s (I-09), two motion-graphic steps of one continuous stack build, a
    real empty table held for two seconds, presenter only for the last fifth; overlays ≤ 7 words →
    left.
12. **[timing / schema]** Recomputed: 166 words, 66.4 s, storyboard contiguous 0.0–66.4 s; validator
    0 errors → passes.
13. **[scheduling]** Do not publish in the same week as C-06, which counts the same Monday as
    twenty-five named stages.

### Spec §54 checklist

1. **Insights** — I-05, I-08, I-09, I-13, I-15, I-17, I-29; all exist.
2. **Hypothesis** — H-19, matches; its 33-card figure was correctly replaced by our own 23 and the
   replacement verified.
3. **Evidence** — our own weekly run, every figure reproducible from `data/radar.db` and the run log;
   the one figure that was misattributed has been fixed.
4. **References with reasons** — four, functions `hook` / `pain` / `rhythm` / `cta`, matching
   `hypothesis_refs.json`; two superlatives corrected.
5. **Transcripts** — four verbatim beat quotes, all matched; the caption-contradiction note the
   `DbbA7wwTIZ8` reason relies on is present in that file.
6. **Stats signals** — I-17 (a problem stated in only 64 of 264 reels), I-06 (setup-first openings),
   the question-hook cell (0.0054 share / 0.0198 save), manual_repetition 6.94 vs chaos_no_process
   0.87; all verified.
7. **Frame patterns** — artefact-first opening, a stack built in two passes, the empty table held, the
   presenter last; no zooms, no counting-up figures.
8. **Transformation** — each `transformed_how` names the borrowed element and the reversal (our last
   counter stays at zero where the reference's climbs).
9. **Original synthesis** — the five-step map with a real count against each step, ending on a count of
   zero, and the failure located in the handover rather than in a manual step.
10. **Why better than generic** — a teardown whose four automated steps all work and which still
    produces nothing, and which refuses the two numbers it does not have.

---

## Notes for the orchestrator

1. **`Dc_TX1CttIc.save_rate` is now `null`.** The same treatment may be needed elsewhere in the card
   set: `DMQMNNHSJRF` is the borderline case — its save count exists in snapshot 2 only, so it is kept
   as a number with the provenance stated in the reason, not nulled.
2. **`01-general-conclusions.md` §C** prints twelve rows in a table its own text calls thirteen, then
   adds two further RELIABLE pairs. Cards cite the stated 13. Worth reconciling at source.
3. **Three of these five cards open on our own pipeline artefacts** (04 the ledger, 06 the stage list,
   10 the weekly plan table). 06 and 10 also give different step counts for the same Monday —
   twenty-five named stages versus five steps. Schedule them apart.
4. **Two cards are gated on footage that does not exist** (06 and 08 flag it themselves; 02 did not and
   now does). None of the three can be shot until the demo is recorded.
5. **The 118 figure in H-12** is not reproducible and should not be reused in any later card or report;
   the reproducible figures are 27 (product-name damage), 140 (notes naming a specific wrong word) and
   191 (notes discussing the transcription).
