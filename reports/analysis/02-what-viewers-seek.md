# 02 — What viewers seek

Spec §78. Every statement below is tied to a topic, hook, share rate or save rate with its denominator
and confidence label. Sources: `data/analysis/transcripts/*.json` (266 semantic reads),
`reports/data/category_freq_perf.json`, `reports/data/associations.json`, `reports/data/analysis_ready.csv`.

**Denominators.** 266 reels have both a ta-v1 semantic read and performance data; 245 of those have a
save rate (HikerAPI drops the field on ~9–10 % of rows); 268 have a share rate; 3 211 reels carry
metrics only. The analysed set is the top of `score.py`'s ranking, so all of this describes what the
already-successful part of the niche is selling, not what the niche as a whole is selling.

**One sentence first.** Across 266 semantic reads the demand is not for understanding. It is for a
**thing you can have** — a repo, a file, a workflow, a prompt, a map — that removes a named piece of
manual work, named tool by named tool, with the screen showing it running. Nine of the thirteen
RELIABLE correlations in the whole association run are save-rate correlations, and a save is a bet that
the thing will be used.

---

## 1. Desired outcomes

The `desire` field, classified by keyword across 266 reels (categories overlap):

| desired outcome | n | % | median view_lift | median share | median save | vs rest (save) |
|---|---:|---:|---:|---:|---:|---|
| A ready-made artefact (repo / file / template / map / prompt pack) | 27 | 10 % | 2.40 | 0.0161 | **0.0346** | 0.0270, p=0.052 |
| Time saved on something repeated | 33 | 12 % | 3.52 | 0.0163 | **0.0330** | 0.0275, p=0.025 |
| Money not spent (free access, no subscription, no agency fee) | 84 | 32 % | 1.83 | 0.0160 | **0.0306** | 0.0250, p=0.007 |
| Control / self-hosting / owning the stack | 42 | 16 % | 2.59 | 0.0127 | 0.0246 | 0.0283, n.s. |
| A status edge over people who are behind | 19 | 7 % | 2.42 | 0.0137 | 0.0255 | 0.0277, n.s. |
| Certainty that a thing actually works | 19 | 7 % | 1.49 | 0.0111 | **0.0140** | 0.0282, p=0.017 (negative) |
| Novelty — the thing that just launched | 11 | 4 % | 2.32 | 0.0190 | 0.0229 | 0.0278, n.s. |

Confidence: **PROBABLE** for the artefact, time-saving and money-saving rows (n≥27, ≥23 creators,
p<0.06); **INSUFFICIENT** for status edge, certainty and novelty (n<20 and no creator-normalised check).
The classifier is a regex over free ta-v1 prose, not a closed vocabulary, so the buckets overlap.

The clearest single expression of the artefact demand is `resource_handoff` as a solution type: n=38,
28 creators, the highest save rate of any solution type at **0.0429**, against `framework_mental_model`
— the "here is how to think about it" answer — at **0.0135** on n=25. The niche's audience does not save
a way of thinking.

---

## 2. Unresolved pains

Canonical pain labels across 266 reels, ordered by size. None reaches the RELIABLE threshold (n≥30 and
≥8 creators is met by two, but no creator-normalised test applies to a categorical median).

| pain | n | creators | median view_lift | median share | median save | confidence |
|---|---:|---:|---:|---:|---:|---|
| cost_money | 48 | 33 | 1.96 | 0.0164 | 0.0303 | SUFFICIENT_SAMPLE |
| dont_know_where_to_start | 34 | 30 | 1.34 | 0.0175 | 0.0346 | SUFFICIENT_SAMPLE |
| keeping_up_with_ai | 29 | 24 | 1.73 | 0.0161 | 0.0181 | PROBABLE |
| missing_skills | 25 | 20 | 1.34 | 0.0097 | 0.0246 | PROBABLE |
| quality_trust | 25 | 20 | 1.63 | 0.0133 | 0.0275 | PROBABLE |
| time_waste | 20 | 17 | 3.54 | 0.0199 | 0.0365 | PROBABLE |
| chaos_no_process | 17 | 14 | 0.87 | 0.0138 | 0.0264 | PROBABLE |
| manual_repetition | 15 | 13 | **6.94** | 0.0161 | **0.0390** | PROBABLE |
| scaling_without_hiring | 8 | 8 | 4.83 | 0.0209 | 0.0359 | PROBABLE |
| tool_overload | 8 | 8 | 2.98 | 0.0144 | 0.0217 | PROBABLE |
| fear_of_replacement | 8 | 6 | 2.11 | 0.0153 | 0.0126 | PROBABLE |
| slow_response_to_leads | 5 | 3 | 0.47 | 0.0001 | 0.0001 | PROBABLE |

**The two highest-value pains are the two most concrete ones.** `manual_repetition` (6.94× lift,
0.0390 save) and `time_waste` (3.54×, 0.0365) both name a specific act the viewer performs and would
rather not. The two weakest, `chaos_no_process` (0.87×) and `slow_response_to_leads` (0.47×), name a
condition rather than an act — and they are the two closest to M2's own language.

**Practical reading for M2:** "your process is chaotic" is not a pain the audience responds to. "You
retype the same numbers out of a PDF every Monday" is the same pain named as an act, and it is in the
6.94× bucket.

---

## 3. Tools and models wanted

`tools_mentioned` cells with n≥7 (analysis-ready, n=266). All PROBABLE or INSUFFICIENT — the vocabulary
is free text, so "Claude code", "Claude Code" and "cloud code" appear as separate rows and are reported
as they are rather than silently merged.

| tool | n | creators | median view_lift | median save | confidence |
|---|---:|---:|---:|---:|---|
| Claude | 31 | 25 | 2.61 | 0.0375 | SUFFICIENT_SAMPLE |
| GitHub | 31 | 21 | 3.57 | 0.0390 | SUFFICIENT_SAMPLE |
| Claude Code (all spellings) | 37 | ~30 | 0.87–7.81 | 0.034–0.040 | PROBABLE |
| Google | 14 | 11 | 13.27 | 0.0420 | PROBABLE |
| YouTube | 12 | 11 | 2.23 | 0.0447 | PROBABLE |
| Instagram | 9 | 8 | 2.12 | 0.0382 | PROBABLE |
| LinkedIn | 8 | 8 | 1.81 | 0.0503 | PROBABLE |
| Codex | 7 | 7 | 3.02 | 0.0239 | PROBABLE |

The RELIABLE finding underneath this table is not which tool but **how many distinct ones**:
`lex_platforms_n` → save_rate rho +0.331 (p=1.1e-07, creator-normalised +0.173) and
`lex_entities_distinct` → view_lift +0.161 (creator-normalised +0.198). Naming three different named
destinations beats naming one destination three times.

**What this means for M2:** the audience wants the destination named. A script that says "an AI tool"
where it could say "Claude, then a Google Sheet, then your inbox" is measurably weaker on both saves
and reach.

---

## 4. Status gains

Present but small. 19 of 266 reels frame the outcome as being ahead of other people; they run at median
view_lift 2.42 against 1.95 and show no share or save advantage (p=0.97 and 0.94). **INSUFFICIENT.**

Where status appears it is as a payoff clause rather than a promise — "you now know more about AI agents
than 99 % of the population" (DLzPQzGNEmY, payoff beat 78.6–90.1 s, 1.63M plays on a 22k median). The
reel's reach came from the Netflix time-swap hook and the keyword gate, not from the status line.

`identity_call` as a hook type — the direct "if you are a…" status address — is the **worst-performing
hook in the corpus** (n=9, median view_lift 0.41, robust_z 0.37). Status works as a reward, never as an
entry ticket.

---

## 5. Economic outcomes

32 % of reels (84 of 266) state a money-shaped desire, and it is the largest single desire category. But
the direction depends entirely on which side of the ledger:

- **Money not spent** is the workhorse: `cost_money` is the largest pain (n=48, 33 creators) and sits at
  the corpus median for lift (1.96) with an above-median save rate (0.0303). "Бесплатный доступ и обход
  платы" as a topic carries the corpus's highest topic-level share rate (0.0220, n=21).
- **Money earned** costs reach: the 71 reels whose desire, thesis or pain is stated in income terms run
  at median view_lift **1.19 against 2.12** for the rest, with save rate unchanged (0.0286 vs 0.0264).
  Confidence **PROBABLE**; the classifier is a regex over free prose.

RULES.md §1.2 already refuses to copy income framing on positioning grounds. The data adds that the
refusal is free.

---

## 6. Time saving

33 reels (12 %) promise time back. Median view_lift 3.52 against 1.88, save rate 0.0330 against 0.0275
(p=0.025) — **PROBABLE**. The promise is almost always quantified in the hook and almost always in
minutes: "the whole thing took Claude about two minutes" (DYC-x8DogOI, hook, 399× lift), "I'll show you
how to build it in three easy steps" (DNA7-d3o5sQ, hook, 55× lift), "under 5 minutes" (DVZGBgTk6zz,
hook, 304× lift).

What is never present in this corpus: a before-and-after time measurement. `before_after` is the
second-rarest proof type (n=5) and `numbers` as a proof type sits below the corpus median on lift
(1.81 vs 2.03). The niche promises time and proves nothing.

---

## 7. Uncertainty reduction

This is the demand the corpus **fails** to serve, and the failure is measurable. Reels whose stated
desire is certainty — knowing whether a thing actually works, whether it can be trusted, whether it is
real — carry a **save rate of 0.0140 against 0.0282** for everything else (n=19, p=0.017) and a lower
median view_lift (1.49 vs 1.99).

Read alongside §1, this says: the audience saves things it intends to use and does not save things that
tell it what to believe. `quality_trust` as a pain sits mid-table (n=25, 1.63× lift), and the
`framework_mental_model` solution type — the one that reduces uncertainty by explaining — has the lowest
save rate of any large cell (0.0135, n=25).

**Confidence PROBABLE**, n=19 for the desire grouping. The practical implication for M2 is
uncomfortable: a reel whose whole value is "here is how to decide" will be watched and not kept. The
decision has to be attached to an artefact the viewer can take away.

---

## 8. Proof needs

Weak, in this niche. 68 of 266 reels (26 %) carry **no proof at all** and perform indistinguishably from
the 84 that carry a screen demonstration (median view_lift 2.09 vs 2.64; both cells SUFFICIENT_SAMPLE at
46 and 50 creators).

| proof_type | n | creators | median view_lift | median save |
|---|---:|---:|---:|---:|
| screen_demo | 84 | 50 | 2.64 | 0.0276 |
| none | 68 | 46 | 2.09 | 0.0294 |
| numbers | 36 | 28 | 1.81 | 0.0335 |
| personal_story | 28 | 20 | 1.82 | 0.0299 |
| authority_claim | 25 | 20 | 1.25 | 0.0148 |
| third_party_data | 16 | 12 | 1.72 | 0.0249 |
| before_after | 5 | 5 | 0.78 | 0.0212 |
| client_story | 4 | 3 | 3.82 | 0.0151 |

Where proof exists it is **visual, not spoken**: 41 % of the 2 645 labelled frames are flagged
`is_proof_visual`, against 50 % of reels carrying a proof *beat*. Median time to the first proof beat is
22.0 s (p25 11.1, p75 32.0).

**For M2 this is an opportunity, not a cost.** POSITIONING.md §6 requires evidence M2 owns; the niche
does not supply any and is not penalised for it, which means a reel that shows its own run — including
what broke — is doing something no measured competitor does. It must be delivered as screen footage at
around 20–25 seconds, because that is where this audience expects the evidence to arrive.

---

## 9. Novelty

Smaller than expected. Only 11 of 266 reels frame the desire as newness, at median view_lift 2.32 vs
1.96 — **INSUFFICIENT**. `announcement_news` as a narrative is the fourth-largest archetype (n=30, 21
creators) and among the weakest on reach (view_lift 1.29, robust_z 0.96). "Новости моделей и
лабораторий" as a topic: n=21, view_lift 2.30, but the second-lowest save rate of the large topic cells
(0.0097).

Novelty gets attention and is not kept. This matches POSITIONING.md §8's "model news without a practical
work decision" exclusion, and gives it a number: news reels are saved at roughly a third the rate of
tutorial reels (0.0097 vs 0.0411 for `tutorial_steps`).

---

## 10. Reassurance

Almost absent as an explicit demand and negative where present. Urgency and fear vocabulary track
downward on everything: urgency vs view_lift rho −0.164 (p=0.007), urgency vs share_rate −0.150
(creator-normalised −0.180, survives), fear vs save_rate −0.126 (creator-normalised −0.137, survives).
The weak `robust_z` quartile uses more urgency words than the strong one (median 2 vs 1, p=0.056).

`fear_of_replacement` as a pain is small (n=8, 6 creators) and sits at the corpus median on lift (2.11)
with a below-median save rate (0.0126) — people forward the threat and do not keep it.

The one reassurance move that does appear to work is **objection pre-emption**: 19 of 264 reels carry an
explicit objection beat, and in the strongest of them it sits exactly where a viewer would reject the
idea — "But what if you don't know how to build automations? It doesn't matter because…" (DTCOU9DkRTG,
objection 13.6–20.5 s, 52× lift). **INSUFFICIENT** as a statistical claim (n=19); reported because the
ta-v1 structural reads name it repeatedly as the pivot beat.

---

## 11. Curiosity

Curiosity is the niche's default engine and it is a middling one. `curiosity_gap` as a hook type:
n=22, 19 creators, median view_lift 2.16, robust_z 1.26 — the corpus median on both.
`contrarian` hooks reach a higher robust_z (2.04, n=23) but the corpus's lowest share and save rates
among the large hook cells (0.0076 and 0.0139).

The mechanism that actually converts curiosity into a save is **deliberate incompleteness**: name the
artefact, withhold the file. "My 15 favorite Claude skills in 60 seconds." (DVtgbY8Av6A, hook) is 84
spoken words carrying 57.3 saves per 1 000 — a skill name is useless without the file. This is
inseparable from the comment gate (the gate is how the file is withheld), which raises save rate 2.8×
on its own.

**For M2:** curiosity must be resolved inside the reel, because M2 does not run the gate. The
equivalent move is to name the artefact and publish it — the save then comes from there being something
to collect, not from having to ask.

---

## Summary — the demand M2 can honestly serve

1. **A named repeated act, not a condition.** `manual_repetition` 6.94×, `time_waste` 3.54×,
   `chaos_no_process` 0.87×.
2. **An artefact to take away**, published rather than gated. `resource_handoff` save rate 0.0429, the
   highest of any solution type.
3. **Named destinations.** `lex_platforms_n` → save_rate +0.331, RELIABLE.
4. **Screen evidence at ~22 seconds**, including the failure — which no reel in the corpus shows.
5. **Time in minutes, not money in dollars.** Time-saving desire: save 0.0330, p=0.025. Income framing:
   view_lift 1.19 vs 2.12.
6. **Not** certainty on its own (save 0.0140, p=0.017), **not** news (save 0.0097), **not** status as an
   entry ticket (`identity_call` view_lift 0.41), **not** urgency (all four metrics negative).
