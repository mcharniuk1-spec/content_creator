# 08 — Hypotheses

Spec §21B–C. Twenty-four hypotheses generated against `data/analysis/insights.json` (30 insights, I-01…I-30), scored on the fourteen keys `engine/ingest_insights.py` validates, and cut to ten. Every hypothesis is in `data/analysis/hypotheses.json` and in the `hypotheses` table; the ingest reports 24 ingested, 0 rejected.

**Sources.** `data/analysis/insights.json`, `reports/analysis/01-general-conclusions.md` … `07-existing-cards-verdict.md`, `reports/audit/04-existing-cards-review.md`, `reports/data/category_freq_perf.json`, `reports/data/analysis_ready.csv`, `reports/data/creators.csv`, `reports/data/spend.json`, and the `video_features` / `beats` / `scenes` / `creator_stats` tables of `data/radar.db`.

**Denominators, carried into every claim below.** 3 211 ingested reels for metric-only statements; 268 analysis-ready reels for anything about scripts or visuals; 266 with both a semantic read and performance data; 245 of those with a save rate; 264 with parsed beats; 132 creators with a stats row, 17 of them CONSISTENT. The analysis-ready tier is the top of `score.py`'s own ranking (median robust_z +1.26 against 0.00 across all ingested reels), so every contrast quoted here compares strong reels with other strong reels (I-01).

---

## 1. How the twenty-four were generated

Nine M2 Radar, nine M2 Builds, six M2 Teardown, written before any scoring so that the format mix was not an artefact of ranking. Each format was filled against the positioning-fit topic list: choosing one repeated workflow (H-09, H-19, H-21), the cost of tools and tokens as a business decision (H-01, H-06, H-07, H-14), prompting for work (H-09), drafting, summarising, extracting and classifying (H-10, H-12, H-15), lead-response processes (H-17), human-review boundaries (H-04, H-13, H-22), what not to automate (H-18, H-23), tool comparisons for one specific task (H-02, H-08), and the teardown of an ordinary process (H-19, H-20, H-24). The model-news filter (H-03) and the measurement-null angle (H-16) were written deliberately as tests of the editorial filter, and both failed it.

Three constraints were applied to every hypothesis at the point of writing, not at the point of scoring:

1. **Proof is internal only.** POSITIONING §6 allows "we tested / we built / this broke" and forbids client results. Every hypothesis names a specific artefact we own — the spend ledger, the empty suitability column, the mis-transcribed product name, the 3.6 % alignment hit rate, the 14.4x that was really 1.87x. Two hypotheses (H-07, H-17) name evidence we do **not** have and were rejected for it.

2. **No comment gate, ever.** `cta` is drawn from save_share, follow, question_to_audience, free_resource, none. The gate appears in 158 of 266 analysed reels and moves comment rate x23, save x2.8 and share x1.8 while moving reach not at all (I-12), so refusing it forfeits no distribution and removes the inflation from our own future numbers.

3. **No split screen and no 0–3 second hook rule.** Any split state runs at median robust_z 1.03 against 1.43 (I-10); the niche's median hook is 6.7 seconds and hook length predicts nothing (I-03). Every `visual_structure` field below is written in the frame-type taxonomy of `engine/SPEC.md` §4 and every hook is budgeted at 5–10 seconds.

---

## 2. Scoring

Fourteen keys, each 1–5, the three risk keys inverted so that 5 means low risk. `total_score` is the weighted mean, so it stays on the 1–5 scale.

| key | weight | what a 5 means |
|---|---:|---|
| evidence | 0.12 | the claim rests on a RELIABLE or PROBABLE insight with its denominator, not on a plausible story |
| reference_quality | 0.07 | the references are ungated, statistically meaningful and from explainable creators |
| positioning | 0.12 | all four parts of the POSITIONING §8 filter are visible without being bolted on |
| audience | 0.08 | a level 0–6 non-technical operator recognises their own work in the first fifteen seconds |
| novelty | 0.09 | nothing in the 266 analysed reels does this |
| clarity | 0.07 | one idea, followable without pausing |
| hook | 0.08 | show-first, statement, 5–10 s, no audience address |
| depth | 0.07 | there is a second layer under the headline — a mechanism, a boundary, a threshold |
| visual | 0.06 | there is a real screen of our own to open on and a reason to come back to the face |
| feasibility | 0.08 | shootable in one take on the next filming day with assets that already exist |
| transformation | 0.06 | what is borrowed from the reference is structural and what changes is ours |
| generic_risk | 0.04 | could not be published by any other account in the niche (5 = low risk) |
| copy_risk | 0.03 | no borrowed claim, layout, gate or income framing (5 = low risk) |
| assets | 0.03 | the screen recording, file or table already exists and needs no new build (5 = low risk) |

Weights sum to 1.00. Evidence and positioning carry the most weight (0.12 each) because the two failure modes the existing-cards audit actually found were unsupported claims and cards that skipped the editorial filter — not weak hooks. `assets` and `copy_risk` carry the least (0.03) because both are cheap to fix before shooting.

---

## 3. All twenty-four, ranked

| # | id | format | title | ev | rq | pos | aud | nov | cla | hk | dep | vis | fea | tr | gr | cr | as | total | status |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | H-11 | Builds | Our ranker put the wrong work at the top | 5 | 5 | 5 | 4 | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 4 | 4 | 4 | **4.69** | SELECTED |
| 2 | H-12 | Builds | The extraction that misheard the product name | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | **4.67** | SELECTED |
| 3 | H-18 | Builds | We built it, it worked, and we switched it off | 5 | 4 | 5 | 4 | 5 | 4 | 4 | 5 | 4 | 5 | 5 | 4 | 5 | 5 | **4.60** | SELECTED |
| 4 | H-01 | Radar | Cost per run, not price per month | 5 | 4 | 5 | 5 | 4 | 5 | 4 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | **4.59** | SELECTED |
| 5 | H-13 | Builds | The approval box we designed and never ticked | 5 | 4 | 5 | 4 | 5 | 4 | 4 | 5 | 4 | 5 | 4 | 4 | 5 | 5 | **4.54** | SELECTED |
| 6 | H-04 | Radar | Buy the approval step, not the feature list | 4 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 4 | 4 | **4.49** | SELECTED |
| 7 | H-20 | Teardown | The same number in two places | 5 | 4 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | **4.43** | SELECTED |
| 8 | H-09 | Radar | One prompt beats one agent for a task you do five times a week | 4 | 4 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | **4.29** | SELECTED |
| 9 | H-05 | Radar | The connector list is the decision | 4 | 4 | 5 | 5 | 4 | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 4 | 4 | **4.26** | SELECTED |
| 10 | H-19 | Teardown | Our Monday, taken apart | 4 | 4 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 4 | **4.16** | SELECTED |
| 11 | H-14 | Builds | A price tag on every request | 4 | 3 | 4 | 4 | 3 | 4 | 3 | 3 | 3 | 5 | 3 | 3 | 5 | 5 | **3.67** | REJECTED |
| 12 | H-02 | Radar | Two transcription tools, one meeting-notes job | 4 | 3 | 4 | 4 | 3 | 4 | 3 | 3 | 4 | 4 | 3 | 3 | 4 | 4 | **3.59** | REJECTED |
| 13 | H-10 | Builds | The sorter that could not answer nine of its own questions | 4 | 3 | 4 | 3 | 4 | 3 | 3 | 4 | 3 | 4 | 3 | 3 | 5 | 4 | **3.57** | REJECTED |
| 14 | H-15 | Builds | The weekly one-pager the machine drafts and we sign | 3 | 3 | 4 | 5 | 3 | 4 | 3 | 3 | 4 | 4 | 3 | 2 | 4 | 4 | **3.51** | REJECTED |
| 15 | H-07 | Radar | The free tool's real price is checking time | 3 | 3 | 4 | 4 | 3 | 4 | 3 | 3 | 3 | 4 | 3 | 3 | 4 | 4 | **3.41** | REJECTED |
| 16 | H-22 | Teardown | The step that must stay human: naming the categories | 3 | 3 | 4 | 3 | 3 | 3 | 3 | 4 | 3 | 4 | 3 | 3 | 5 | 4 | **3.36** | REJECTED |
| 17 | H-06 | Radar | Tools that bill you for your own success | 3 | 3 | 4 | 4 | 2 | 4 | 3 | 3 | 4 | 4 | 3 | 2 | 4 | 4 | **3.34** | REJECTED |
| 18 | H-16 | Builds | The comparison the machine could not make | 4 | 2 | 3 | 3 | 4 | 2 | 2 | 4 | 2 | 4 | 2 | 3 | 5 | 4 | **3.11** | REJECTED |
| 19 | H-17 | Builds | First reply to a new enquiry, and the two places we kept a human | 1 | 2 | 4 | 5 | 3 | 4 | 3 | 3 | 4 | 2 | 3 | 3 | 4 | 1 | **2.99** | REJECTED |
| 20 | H-03 | Radar | Three questions before a launch enters your week | 2 | 2 | 3 | 4 | 2 | 4 | 3 | 2 | 3 | 5 | 2 | 2 | 5 | 5 | **2.98** | REJECTED |
| 21 | H-08 | Radar | Read what the tool refuses to do | 2 | 2 | 4 | 4 | 2 | 3 | 2 | 3 | 3 | 4 | 2 | 2 | 5 | 5 | **2.94** | REJECTED |
| 22 | H-21 | Teardown | Time every step before you automate any of them | 2 | 2 | 4 | 4 | 2 | 3 | 2 | 3 | 3 | 4 | 2 | 2 | 5 | 4 | **2.91** | REJECTED |
| 23 | H-23 | Teardown | A process with no named owner cannot be automated | 2 | 3 | 4 | 3 | 2 | 3 | 2 | 3 | 2 | 3 | 2 | 2 | 4 | 3 | **2.70** | REJECTED |
| 24 | H-24 | Teardown | The process that lives in one person's head | 2 | 2 | 3 | 4 | 2 | 3 | 2 | 3 | 3 | 3 | 2 | 2 | 4 | 3 | **2.65** | REJECTED |

**Separation.** The lowest selected hypothesis (H-19, 4.16) sits 0.49 above the highest rejected one (H-14, 3.67), so the cut line is not close anywhere. No rejected hypothesis outscores a selected one, which means the format quota below did not have to override the ranking.

### Reviewer comments, all twenty-four

| id | status | reviewer comment |
|---|---|---|
| H-11 | SELECTED | The strongest card in the set on evidence and the one that most cleanly satisfies the Builds pass criterion in RULES §2 - built by us, and there is something to break. The only real risk is self-absorption; if the second half is still about reels rather than about the viewer's queue, cut it before shooting. |
| H-12 | SELECTED | Second-highest total, a hundredth behind H-11, and the cleanest execution of POSITIONING §6 available to us right now: a real workflow, a real failure, a real boundary and a published artefact. Do not let the hook name a vendor - the moment it does, it becomes a tool review and the editorial filter fails on the first clause. |
| H-18 | SELECTED | The most original card in the set and the one that most directly serves the 'what not to automate' territory. Watch the hook: a contrarian opening carries the lowest share and save rates of the large hook cells, so it must open on the demo of the working step, not on the opinion that automation is overrated. |
| H-01 | SELECTED | The strongest of the four cost angles because it is the only one with a file behind it. Watch the temptation to say 'we saved X' - POSITIONING §6 forbids a savings claim and the reel does not need one. Schedule at least a week apart from H-13, which also opens on our own pipeline. |
| H-13 | SELECTED | Strong and uncomfortable, which is the point. Guard against the anecdote becoming a house catchphrase - the existing-cards audit found five of fourteen drafted cards leaning on the same two internal proof points, and this is exactly the kind of story that gets reused. Once, then retired. |
| H-04 | SELECTED | Best positioning fit of all 24. The one thing that would sink it is filming the two runs as a split screen because they are 'the same task twice' - the corpus says split is the most-used and least-rewarded arrangement (robust_z 1.03 vs 1.43, p=0.044). Full-frame, one after the other. |
| H-20 | SELECTED | The most transferable card in the whole set - every business has this and nobody films it. It only fails if the script explains statistics; write it as two receipts for the same job with different totals and it is finished. |
| H-09 | SELECTED | Highest novelty of the Radar four and the one most likely to be forwarded to a colleague who is about to overbuild. Its danger is register: the corpus punishes contrarian hooks on share and save (0.0076 and 0.0139, the lowest of the large hook cells), so the reel must open on the demo, not on the disagreement. |
| H-05 | SELECTED | Solid but the least surprising of the four selected Radar cards. It earns its slot on specificity - it is the one that most directly executes the single reach finding that survives normalisation. Keep the tool names boring on purpose. |
| H-19 | SELECTED | A real Teardown with a real owner and a real forwardable number, which is more than the other five Teardown candidates can say. Its weakness is subject distance: keep the process map generic enough that an operations lead sees their own Monday inside the first fifteen seconds. |
| H-14 | REJECTED | Same ledger, smaller idea. H-01 makes the decision; this one only describes the instrument. Reject and keep the running-total shot as B-roll for H-01. |
| H-02 | REJECTED | Rejected for overlap, not for quality. Every number it would use is already load-bearing in H-12, and H-12 spends them better because it shows the repair rather than the verdict. Two reels on the same mis-transcription in one plan is exactly the repetition the existing-cards audit criticised. |
| H-10 | REJECTED | The best of the rejected Builds and still a clear no for this cycle: it names a condition rather than an act, which is the exact framing report 02 measures as the weak one, and its parallel to a real business pile has to be asserted rather than shown. Revisit once we have sorted something that is not our own dataset. |
| H-15 | REJECTED | The nearest miss among the Builds. It is rejected on a rule, not on quality: 'без поломки нет Builds'. Run it until it fails, record the failure, then it is the strongest drafting card we have. |
| H-07 | REJECTED | The idea is good and the evidence does not exist. Park it: run the timed review once inside a Builds card and this becomes shootable. Rejected for this cycle on evidence, not on angle. |
| H-22 | REJECTED | Third card on the human-boundary theme in a plan that already has two. Reject on portfolio grounds - the point is fully carried by H-04 and H-13. |
| H-06 | REJECTED | Duplicate of H-01 with a worse register. The data explicitly penalises the pressure framing this angle depends on. Reject and fold the one useful sentence into H-01's pain beat. |
| H-16 | REJECTED | Right instinct, wrong audience. There is no way to make a null result legible to a non-technical operator in sixty seconds without becoming a statistics lesson. Reject; the insight lives inside H-09 where it has a demo attached. |
| H-17 | REJECTED | Hard reject. There is no owned process behind it, and POSITIONING §6 does not allow a staged one to be shown as a build. This is the exact failure mode the 8 September audit recorded - invented fixtures with a real-looking storyboard. Revisit when there is a real inbox. |
| H-03 | REJECTED | This is the reel that will be watched and not kept. Two independent measurements say so: certainty-as-desire saves at half the corpus rate, and the framework solution type is the worst large cell on saves. It also has no screen to open on, which forfeits the only visual finding that survives creator normalisation. Reject. |
| H-08 | REJECTED | Thin. No process, no artefact, no owned evidence - it fails the second question of the RULES §4 stop test ('what here is ours?'). Reject. |
| H-21 | REJECTED | Generic. This is the card that would be indistinguishable from any consultant's reel, and the corpus says the audience does not keep ways of thinking. Reject; it becomes shootable the first time we actually time a process end to end. |
| H-23 | REJECTED | Names a condition, not an act - the precise framing the demand analysis measures as the weak one. No owned evidence either. Reject. |
| H-24 | REJECTED | Built on the two hook mechanics the data most clearly penalises, with no owned evidence underneath. Reject. |

---

## 4. The cut, and why the mix held

The target mix was 4 Radar / 4 Builds / 2 Teardown, matching the weekly slot allocation in RULES §5. The top ten by score are **exactly** 4 Radar (H-01, H-04, H-05, H-09), 4 Builds (H-11, H-12, H-13, H-18) and 2 Teardown (H-19, H-20), so no hypothesis was promoted or demoted to satisfy the quota. That is a coincidence worth naming rather than a validation of the weights.

Two things about the shape of the selection are uncomfortable and are recorded rather than smoothed over:

**The four Builds are all instrumented inside our own research pipeline.** PRODUCTION.md already admits this gap — "everything we have measured so far is our own tooling, which is not what the audience runs on a Monday". The mitigation is that the four were chosen to be four *different generic work steps* rather than four views of one system: triage (H-11), extraction (H-12), sign-off (H-13) and retirement (H-18). Each names its ordinary-business equivalent explicitly — which enquiry to answer first, pulling figures out of a document, who signs before it goes out, when to stop maintaining an automation. If a script drifts back to being about reels, it fails the RULES §4 stop test and should be cut before the filming day.

**Both Teardowns are also our own processes.** RULES §2 lists exactly four Teardown sources and only one is available today: our own processes. Client processes require clients, viewer-submitted processes require an audience that reads us, and generalised industry processes may only be labelled "we think", not "we saw". H-19 and H-20 are the two of our own processes that generalise furthest — a weekly planning ritual and a figure calculated in two places. The six Teardown candidates were the weakest group in the set (mean total 3.37 against 3.77 for Radar and 3.93 for Builds), which is the measured form of the same admission.

**Scheduling constraints that survive the cut.** H-04 and H-13 both live on the human-review boundary and must not be published in the same week. H-13 and H-18 both show a database column on screen and must not be shot with the same framing. H-01's ledger and H-11's ranked list are the two most "about us" openings and should be spaced.

**One rejection that is only a rejection for this cycle.** H-15 (the weekly one-pager the machine drafts and a person signs) fails the Builds pass criterion in RULES §2 — "без поломки нет Builds" — because the drafting step has not broken yet. It is the highest-scoring idea we can rescue simply by continuing to run it and recording the first failure. H-07 (timing the review pass) is in the same position and needs one measurement that does not exist.

**One rejection that is permanent as written.** H-17 (first reply to a new enquiry) would require us to stage a lead-response process we do not have. That is precisely the defect the 8 September audit found in ten of Max's cards — designed fixtures, no owner footage, no measured number — and it is the one failure mode this engine exists to prevent.

---

## 5. The ten selected, in full

### H-11 — Our ranker put the wrong work at the top

**Statement.** If we explain how our own scoring system promoted the wrong items for a month to a non-technical small-business leader through the fear of trusting a list they cannot check, using a result-first hook on the ranked list itself + a screen demo of the same list re-sorted once the trick is removed + an A>SCREEN>A grammar with the rehook before the correction, then the viewer will ask what their own priority list can be gamed by, because they will have watched ours be gamed.

| field | value |
|---|---|
| Format | M2 Builds |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically anyone who runs a queue: enquiries, tickets, applications, invoices. |
| Pain (canonical) | quality_trust |
| Desired outcome | A priority list that can be trusted without re-reading every item, and a way to tell when it has drifted. |
| Hook | "This was our top ten. Six of the ten got there partly on a trick, and we did not notice for a month." - hook_type: result_first |
| Thesis | Any ranking optimises exactly what it measures. Ours measured forwards and saves per thousand views, so it promoted the items that had bought forwards and saves rather than the ones that were good. |
| Mechanism | Show the list. Show the one field we were not holding constant. Re-sort with that field held constant and show the list change. Then the rule we added: record the field on every item and only compare like with like. |
| Proof (internal only) | Internal experiment only. 158 of the 266 analysed videos - 59 % - run a comment-keyword gate. In our own measurement that gate multiplies comment rate by 23, save rate by 2.8 and share rate by 1.8, while leaving reach untouched (p=0.58). Our selection script ranks on shares and saves per thousand, so for a month it was partly ranking the gate rather than the idea. Ranked by the same combined share-and-save percentile the script uses, six of the top ten reels in the corpus carry the gate against 143 of the 2 899 reels that have both rates. The fix - record the CTA type on every candidate and compare only within the same type - is in the pipeline now. |
| CTA | save_share |
| Visual structure | SCREEN (the ranked list mid-scroll, promise burned in as a top banner, 0-10 s) > A_ROLL_MEDIUM (what the score was actually measuring, 10-24 s) > one-line rehook, still on the face (24-26 s) > SCREEN (the same list re-sorted, the movement visible, 26-46 s) > A_ROLL_MEDIUM (the rule we added and what to check in your own queue, 46-62 s). Coarse sequence SCR>A>SCR>A. No split screen. |
| Positioning fit | Process: deciding what to look at first in a recurring queue. Friction: the sort order is produced by a formula nobody re-reads, so the queue quietly optimises the wrong thing. AI boundary: the machine ranks, but a named human owns the definition of 'important' and re-checks it against a handful of items by hand. Next action: take the top five items your system surfaced this week and ask what they have in common that has nothing to do with importance. |
| Strengths | This is the single best-evidenced failure we own: the effect sizes are ours, measured, and large, and the correction is visible as movement on screen - which is the one thing this audience forwards. It is also a genuine general lesson: every queue in every small business is sorted by something nobody re-reads. |
| Risks | The subject is Instagram metrics, which is not the viewer's work. The reel must spend its payoff seconds on their queue, not ours - the parallel has to be stated in their vocabulary within the first twenty seconds or the reel is about us. |
| Novelty | Nothing in the 266-reel corpus shows a system of the author's own producing a wrong answer. before_after is the second-rarest proof type (n=5) and no reel anywhere shows a failure. |
| Confidence | RELIABLE |
| Reviewer comment | The strongest card in the set on evidence and the one that most cleanly satisfies the Builds pass criterion in RULES §2 - built by us, and there is something to break. The only real risk is self-absorption; if the second half is still about reels rather than about the viewer's queue, cut it before shooting. |
| Supporting insights | I-12, I-23, I-09, I-11, I-08, I-26, I-22 |
| Candidate references | [DZLDk9ySi-7](https://www.instagram.com/reel/DZLDk9ySi-7/), [DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/), [DbO4zvJR1k8](https://www.instagram.com/reel/DbO4zvJR1k8/), [DX9kWTYzssE](https://www.instagram.com/reel/DX9kWTYzssE/), [DTCOU9DkRTG](https://www.instagram.com/reel/DTCOU9DkRTG/) |
| Scores | ev 5, rq 5, pos 5, aud 4, nov 5, cla 4, hk 5, dep 5, vis 4, fea 5, tr 5, gr 4, cr 4, as 4 |
| **Total** | **4.69** |

### H-12 — The extraction that misheard the product name

**Statement.** If we explain how our automatic extraction of text from recordings got a name wrong seven times out of eighteen to a non-technical small-business leader through the wish to stop typing up calls and documents by hand, using a result-first hook that puts the wrong word on screen + a screen demo of the raw output beside the repaired one + an A>SCREEN>A grammar that ends on the review rule, then the viewer will add a name check to their own extraction step, because they will have seen the exact shape of the mistake.

| field | value |
|---|---|
| Format | M2 Builds |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically anyone turning calls, forms or documents into text somebody else will act on. |
| Pain (canonical) | manual_repetition |
| Desired outcome | Typed-up notes that can be forwarded without being reread line by line, and a review that takes one minute instead of ten. |
| Hook | "Our transcriber wrote the wrong product name seven times. Here is the one-minute check we added, and what it does not catch." - hook_type: result_first |
| Thesis | Extraction fails predictably, not randomly: it fails on proper nouns and figures. That makes the human check small and fixed rather than a full reread. |
| Mechanism | Show the raw output with the errors highlighted. Show the short list of fields we now check. Run the check on screen. Then name what the check still misses, out loud. |
| Proof (internal only) | Internal experiment only. Across our 266 analysed transcripts the local model wrote the same product name correctly 11 times and incorrectly 7 times, and turned 'n8n' into 'anything', 'ElevenLabs' into 'a level lab' and 'Canva' into 'Kenwa'. 255 of the 266 transcripts came back punctuated and 11 did not, so the same file cannot be split the same way twice. All of it is visible on screen in our own files. |
| CTA | free_resource |
| Visual structure | SCREEN (the wrong word on screen, promise burned in as a persistent top banner, 0-10 s) > A_ROLL_MEDIUM (why it fails on names and numbers specifically, 10-24 s) > SCREEN (the field list and the check running, 24-46 s) > A_ROLL_MEDIUM (what it still misses, plus the closing line, 46-62 s). Coarse sequence SCR>A>SCR>A, first frame a full-frame screenshot mid-action. No split screen. |
| Positioning fit | Process: turning a recording or a document into text that another person will use - meeting notes, an intake form, an invoice line, a call summary. Friction: the output looks finished and is wrong in exactly the places that matter, which are names, numbers and decisions. AI boundary: the machine transcribes and extracts; a person checks a short, fixed list of fields before the text moves on. Next action: write down the five fields in your own documents that must never be wrong, and check only those. |
| Strengths | Extraction is on POSITIONING §9's own list of best-fit workflows, the failure is ours and documented, and the artefact - a five-field check list - can be published in the caption rather than gated, which is what the save-rate evidence says actually earns the save (resource_handoff carries the corpus's highest save rate at 0.0429). |
| Risks | Could drift into an ASR tutorial. The fix is that the reel never names a transcription product as the subject - the subject is the check, and the tool is incidental. |
| Novelty | 84 of 266 reels prove with a screen demo and every one of them shows the thing working. Showing the same screen with the mistake left in is unrepresented in the corpus. |
| Confidence | RELIABLE |
| Reviewer comment | Second-highest total, a hundredth behind H-11, and the cleanest execution of POSITIONING §6 available to us right now: a real workflow, a real failure, a real boundary and a published artefact. Do not let the hook name a vendor - the moment it does, it becomes a tool review and the editorial filter fails on the first clause. |
| Supporting insights | I-08, I-09, I-13, I-18, I-11, I-15, I-29 |
| Candidate references | [DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/), [DcoE5ZsK4I7](https://www.instagram.com/reel/DcoE5ZsK4I7/), [DMQMNNHSJRF](https://www.instagram.com/reel/DMQMNNHSJRF/), [DWCPx0PkQzA](https://www.instagram.com/reel/DWCPx0PkQzA/) |
| Scores | ev 5, rq 4, pos 5, aud 5, nov 4, cla 5, hk 5, dep 4, vis 5, fea 5, tr 4, gr 4, cr 5, as 5 |
| **Total** | **4.67** |

### H-18 — We built it, it worked, and we switched it off

**Statement.** If we explain why we retired an automation that ran correctly to a non-technical small-business leader through the guilt of maintaining something nobody uses, using a contrarian demo-first hook that shows the working thing being turned off + a screen demo of the hit rate that killed it + a single unbroken screen take returning to the face for the rule, then the viewer will put a retirement date on their own automations, because they will have watched a working one be retired for a stated reason.

| field | value |
|---|---|
| Format | M2 Builds |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically anyone maintaining an automation they inherited or built months ago. |
| Pain (canonical) | time_waste |
| Desired outcome | Fewer moving parts to maintain, and a rule for deciding which ones deserve to survive. |
| Hook | "This step works. It ran on every file and it never failed. We turned it off this week, and here is the number that decided it." - hook_type: demo_first |
| Thesis | An automation earns its place by what it changes, not by whether it runs. A step that succeeds and changes nothing is a maintenance cost pretending to be an asset. |
| Mechanism | Show the step running successfully. Show the measurement of what it changed: a hit rate of 3.6 % and no difference in the outcome it was supposed to improve. Then the rule: every automation gets a stated threshold and a review date at the moment it is built. |
| Proof (internal only) | Internal experiment only. We built a step that aligned the spoken script of a video to its visual cuts. It ran on all 264 parsed videos and produced 55 aligned boundaries out of 1 527 - 3.6 % - with 215 of 264 videos producing none at all, and the videos where it did fire performed no differently from the rest. It works and it tells us nothing, so it is off. |
| CTA | free_resource |
| Visual structure | SCREEN, one continuous take: the step running green, then the hit-rate number, then the switch being turned off, promise on a persistent top banner (0-30 s) > A_ROLL_MEDIUM (the retirement rule and the review date, 30-52 s) > A_ROLL closing line. Coarse sequence SCR>A, modelled on the single unbroken process shot rather than on a cut-heavy montage. No split screen. |
| Positioning fit | Process: keeping an existing automation alive - the weekly script, the zap, the rule in the mailbox. Friction: nothing in a small company ever gets switched off, so the maintenance load only grows and the cost of each item is invisible. AI boundary: the machine can report how often a step actually fires and what it changed; the decision to retire it is a human one and needs a stated threshold. Next action: list your automations, find the one that fired least last month, and either state why it stays or turn it off. |
| Strengths | This is the only angle in the set that argues against automation from inside a build, which is the sharpest possible separation from a niche where 62 of 266 reels are demo walkthroughs and none retires anything. The evidence is a single number that can sit on screen unedited. |
| Risks | Reads as a research curiosity unless the retirement rule is stated in the viewer's terms - the second half must be about their zap, not our aligner. There is also a repetition risk with H-13, which also shows a database column; the shots must not look alike. |
| Novelty | Unrepresented. The corpus contains no reel in which the author removes something they built; 'warning_dont' is the smallest solution type at 6 of 266, and every one of those warns about somebody else's tool. |
| Confidence | RELIABLE |
| Reviewer comment | The most original card in the set and the one that most directly serves the 'what not to automate' territory. Watch the hook: a contrarian opening carries the lowest share and save rates of the large hook cells, so it must open on the demo of the working step, not on the opinion that automation is overrated. |
| Supporting insights | I-21, I-20, I-22, I-08, I-09, I-14, I-18 |
| Candidate references | [Dbs2JdJKUDd](https://www.instagram.com/reel/Dbs2JdJKUDd/), [Dc_TX1CttIc](https://www.instagram.com/reel/Dc_TX1CttIc/), [DMQMNNHSJRF](https://www.instagram.com/reel/DMQMNNHSJRF/), [DZQZOVhgNvK](https://www.instagram.com/reel/DZQZOVhgNvK/) |
| Scores | ev 5, rq 4, pos 5, aud 4, nov 5, cla 4, hk 4, dep 5, vis 4, fea 5, tr 5, gr 4, cr 5, as 5 |
| **Total** | **4.60** |

### H-01 — Cost per run, not price per month

**Statement.** If we explain how to price an AI tool by the cost of one run of one repeated task to a non-technical small-business leader through the fear of signing a subscription whose bill grows with use, using a result-first hook read off our own spend ledger + a screen demo of that real ledger with the per-request price visible + a screen-first visual grammar that opens on the ledger and returns to the face only for the verdict, then the viewer will forward it to whoever signs off on software, because it converts a pricing page into one number they can defend.

| field | value |
|---|---|
| Format | M2 Radar |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically the person who approves software spend. |
| Pain (canonical) | cost_money |
| Desired outcome | Money not spent on a tool that does not pay for the task it was bought for, plus a single number the leader can defend to a partner or an accountant. |
| Hook | "We measured three thousand two hundred and eleven competitor videos for seventeen dollars and seventy-eight cents. Here is the arithmetic that told us when to stop paying." - hook_type: result_first |
| Thesis | A tool's price is meaningless until it is divided by the number of times the task runs. Cost per run is the only number that survives a conversation with the person who signs. |
| Mechanism | Show the real ledger: 889 paid requests, $0.02 each, $17.78 total, itemised. Add one column - runs per week - and the monthly price becomes a per-run cost. Then show the guard: the pipeline refuses to spend without an explicit confirmation, so the ceiling is a decision, not a surprise. |
| Proof (internal only) | Internal experiment only. Our own spend ledger (reports/data/spend.json): 10 entries between 1 and 11 September, 889 units at a $0.02 unit price, $17.78 total, including one run recorded as interrupted mid-way. Plus engine/SPEC.md §0.8 - no module in our pipeline may make a paid call by default and any spend must print an estimate and require an explicit --yes. No client results, no savings claims. |
| CTA | save_share |
| Visual structure | SCREEN (the ledger open, the $0.02 unit-price column highlighted, promise burned in as a persistent top banner, 0-12 s) > A_ROLL_MEDIUM (what the division means, 12-30 s) > SCREEN (the same table with a cost-per-run column added, 30-50 s) > A_ROLL_MEDIUM (verdict, limitation, closing line, 50-62 s). Coarse sequence SCR>A>SCR>A. No SPLIT_SCREEN anywhere. One speaker, one take; the screen is a full-frame insert recorded separately, so the reel still contains no speaker cut. |
| Positioning fit | Process: approving and renewing a paid tool for one repeated task. Friction: pricing pages quote per seat or per month while the work happens in runs, so nobody in the company can say whether the tool is expensive. AI boundary: the model performs the run; the human sets the cap, reads the ledger and decides when the price stops being worth it - no tool is allowed to spend without an explicit confirmation. Next action: take one repeated task, count how many times a week it actually runs, divide the monthly bill by that number, and only then renew. |
| Strengths | cost_money is the largest pain in the analysed corpus (n=48, 33 creators) and money-not-spent sits above the corpus median on save rate (0.0306 vs 0.0250, p=0.007), while money-earned framing costs reach (view_lift 1.19 vs 2.12) - this reel is on the profitable side of that line. The proof is a file we own, so it can be shown on screen at 20-25 s where this audience expects evidence. |
| Risks | The ledger is our research spend, not an ordinary business cost, so the parallel has to be drawn explicitly or the reel reads as being about us. The $0.02 unit price belongs to one vendor and will move; the arithmetic must be the message, not the price. |
| Novelty | Nobody in the 266 analysed reels shows their own bill. 84 of 266 reels have a money-shaped desire and every one of them frames it as money not spent on somebody else's product; none shows the ledger of its own run. |
| Confidence | PROBABLE |
| Reviewer comment | The strongest of the four cost angles because it is the only one with a file behind it. Watch the temptation to say 'we saved X' - POSITIONING §6 forbids a savings claim and the reel does not need one. Schedule at least a week apart from H-13, which also opens on our own pipeline. |
| Supporting insights | I-09, I-08, I-13, I-25, I-15, I-29, I-05 |
| Candidate references | [Dc_TX1CttIc](https://www.instagram.com/reel/Dc_TX1CttIc/), [DcUNlNvy6J9](https://www.instagram.com/reel/DcUNlNvy6J9/), [DbVq4mwz38L](https://www.instagram.com/reel/DbVq4mwz38L/), [DaGTeJNN1GR](https://www.instagram.com/reel/DaGTeJNN1GR/) |
| Scores | ev 5, rq 4, pos 5, aud 5, nov 4, cla 5, hk 4, dep 4, vis 5, fea 5, tr 4, gr 4, cr 5, as 5 |
| **Total** | **4.59** |

### H-13 — The approval box we designed and never ticked

**Statement.** If we explain that we wrote a mandatory human check into our own process and then left it empty on 3 211 records to a non-technical small-business leader through the discomfort of realising a written rule is not a working control, using a result-first hook on the empty column + a screen demo of the database field with the count visible + a face-screen-face grammar that ends on the redesign, then the viewer will go and look at their own sign-off step, because they will have watched ours turn out to be decorative.

| field | value |
|---|---|
| Format | M2 Builds |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically anyone who has written an approval step into a process document. |
| Pain (canonical) | quality_trust |
| Desired outcome | Confidence that the sign-off step in the process document is actually happening, and evidence of it if anyone asks. |
| Hook | "We wrote a mandatory check into our own process on the first of September. Here is the column. Three thousand two hundred and eleven rows, all empty." - hook_type: result_first |
| Thesis | A control that is not blocked on is not a control. If the process can complete without the check being recorded, the check is a preference. |
| Mechanism | Show the rule as written. Show the field. Show the count of filled rows: zero. Then the three ways to fix it - make the step block, make it visible on a screen someone already looks at, or delete the rule and admit the risk. We take the first and say why. |
| Proof (internal only) | Internal experiment only. RULES.md §2a has required a suitability check on every candidate video since 1 September - after the storyboard, before the card is written. The field that records it is empty for all 3 211 codes in our database, including all 23 cards that were drafted from them. One reel in our own current shortlist of 40 would have failed that check on content grounds. Nothing was published, which is luck, not control. |
| CTA | save_share |
| Visual structure | A_ROLL_CLOSE_UP (the admission, promise burned in, 0-9 s) > SCREEN (the rule text, then the empty column with the count, one continuous full-frame take, 9-38 s) > A_ROLL_CLOSE_UP (the three fixes, which one we took, and the closing line, 38-60 s). Coarse sequence A>SCR>A, the exact three-state form that carries the corpus's highest median robust_z. One speaker, one take, no split screen. |
| Positioning fit | Process: the sign-off step inside any repeated process - who checks the work before it goes out, and where that check is recorded. Friction: the rule exists in a document, the field exists in the system, and nothing enforces the connection, so the control is invisible until something goes wrong. AI boundary: automation may prepare and queue, but the record that a person checked has to be produced by that person's action, not inferred. Next action: open the place your process says the check is recorded and count how many of the last fifty records have it filled in. |
| Strengths | This is the 'we tried and it broke' standard POSITIONING §6 asks for, on a control rather than on a tool, and there is no reel in the corpus that admits anything comparable. The visual is a single unambiguous number on screen, which is the cheapest possible proof to shoot. |
| Risks | Two dangers. It can read as self-flagellation rather than as a lesson - the fix is that two thirds of the runtime is the redesign, not the confession. And it lands close to H-04 on subject; the two must not be published in the same week. |
| Novelty | Nothing in the corpus shows the author's own governance failing. 25 of 266 reels prove by authority claim; zero prove by admitting a control did not run. |
| Confidence | RELIABLE |
| Reviewer comment | Strong and uncomfortable, which is the point. Guard against the anecdote becoming a house catchphrase - the existing-cards audit found five of fourteen drafted cards leaning on the same two internal proof points, and this is exactly the kind of story that gets reused. Once, then retired. |
| Supporting insights | I-11, I-08, I-09, I-15, I-18, I-14, I-26 |
| Candidate references | [DbO4zvJR1k8](https://www.instagram.com/reel/DbO4zvJR1k8/), [DZ-wujrTJ0u](https://www.instagram.com/reel/DZ-wujrTJ0u/), [DczDlj4qQjI](https://www.instagram.com/reel/DczDlj4qQjI/), [DVaBP3wDAFE](https://www.instagram.com/reel/DVaBP3wDAFE/) |
| Scores | ev 5, rq 4, pos 5, aud 4, nov 5, cla 4, hk 4, dep 5, vis 4, fea 5, tr 4, gr 4, cr 5, as 5 |
| **Total** | **4.54** |

### H-04 — Buy the approval step, not the feature list

**Statement.** If we explain that the first thing to check in any AI tool is whether it will stop and wait for a person to a non-technical small-business leader through the fear of something going out under the company's name unchecked, using a demo-first hook that shows a draft sitting in a queue + a screen demo of the same task run once with the approval step on and once with it off + an A>SCREEN>A visual grammar, then the viewer will forward it to whoever is about to buy the tool, because it replaces a feature comparison with a single question.

| field | value |
|---|---|
| Format | M2 Radar |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically the person choosing a tool that will write or send something. |
| Pain (canonical) | quality_trust |
| Desired outcome | Certainty that nothing leaves the company without a person seeing it, without having to police the team. |
| Hook | "Watch this draft sit here until somebody presses a button. That pause is the only feature worth comparing." - hook_type: demo_first |
| Thesis | For any task whose output leaves the company, the presence and position of a human approval step is a bigger decision than the model behind it. |
| Mechanism | Run one small task twice on screen - once with the tool set to send, once with it set to hold - and show what the queue looks like. Then name the three places an approval step can sit: before the draft is written, before it is sent, after it is sent. Only the middle one is worth paying for. |
| Proof (internal only) | Internal experiment only. Our own pipeline runs its default transcription and frame work on a local path with the paid provider registered but switched off (engine/SPEC.md §0.3), precisely so a run can be stopped, inspected and repeated without a bill; and every processing step writes its own state row, so we can point at the steps that have a human gate and the steps that do not. We show our own gate list, including the gap H-13 is about. |
| CTA | save_share |
| Visual structure | A_ROLL_MEDIUM (promise, 0-8 s) > SCREEN full-frame, the same task run twice, the held draft visible in a queue (8-38 s) > A_ROLL_MEDIUM (the three positions of the gate and what to check before buying, 38-58 s) > A_ROLL closing line. Coarse sequence A>SCR>A. No split screen; the two runs are shown one after the other full-frame, never side by side. |
| Positioning fit | Process: buying or switching an AI tool that produces outward-facing text - replies, posts, quotes, summaries sent to a client. Friction: feature lists never say where the human sits, so the approval step is discovered after the tool is already in the workflow. AI boundary: the tool drafts and queues; a named person releases. Next action: open the tool you are evaluating, find the setting that holds output for review, and if it does not exist, do not buy it for outward-facing work. |
| Strengths | The AI boundary is not an afterthought bolted on to satisfy the editorial filter - it is the whole subject, which no reel in the 266-reel corpus does. A>SCREEN>A is the strongest named visual pattern (share rate 0.0213 vs 0.0140, p=0.00076) and this reel needs exactly that shape. The demo is cheap: any tool with a draft queue will do. |
| Risks | Reads as advice rather than as a build unless the screen genuinely shows two runs. There is a real chance of sounding like a compliance lecture; the fix is that the whole middle is footage, not talk. |
| Novelty | Exactly one reel in the analysed corpus states the boundary out loud - 'nothing gets posted until you say yes' - and it is a throwaway objection beat inside a tool promo. Making it the subject is new in this niche. |
| Confidence | PROBABLE |
| Reviewer comment | Best positioning fit of all 24. The one thing that would sink it is filming the two runs as a split screen because they are 'the same task twice' - the corpus says split is the most-used and least-rewarded arrangement (robust_z 1.03 vs 1.43, p=0.044). Full-frame, one after the other. |
| Supporting insights | I-08, I-11, I-09, I-13, I-15, I-27, I-05 |
| Candidate references | [DbVKVz0y8xo](https://www.instagram.com/reel/DbVKVz0y8xo/), [DczDlj4qQjI](https://www.instagram.com/reel/DczDlj4qQjI/), [Dbi-yxNgrhG](https://www.instagram.com/reel/Dbi-yxNgrhG/), [DTCOU9DkRTG](https://www.instagram.com/reel/DTCOU9DkRTG/) |
| Scores | ev 4, rq 5, pos 5, aud 5, nov 5, cla 4, hk 4, dep 5, vis 4, fea 4, tr 5, gr 4, cr 4, as 4 |
| **Total** | **4.49** |

### H-20 — The same number in two places

**Statement.** If we explain how one figure that lives in two systems produced two different answers in our own work to a non-technical small-business leader through the quiet fear of having quoted a wrong number to somebody, using a result-first hook that shows both numbers on screen at once + a screen demo tracing each one back to its source + an A>SCREEN>A grammar that ends on the single-source rule, then the viewer will find their own duplicated figure, because they will have watched a fourteen-fold error survive a review.

| field | value |
|---|---|
| Format | M2 Teardown |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically anyone who quotes figures that are calculated somewhere else. |
| Pain (canonical) | quality_trust |
| Desired outcome | Confidence that the number in the document and the number in the system are the same number, without recalculating by hand. |
| Hook | "Fourteen times. One point nine times. Same item, same week, same database - and we shipped the first one." - hook_type: result_first |
| Thesis | A number is not a fact, it is the output of a definition. When two definitions are alive at once, the process will use whichever one is nearer, and reviewing harder does not fix it. |
| Mechanism | Put both numbers on screen. Trace each back to its own definition - one was divided by a baseline of eleven items, the other by twenty-seven. Show the moment the two diverge. Then the rule: one definition, written down, carried with the number everywhere it travels. |
| Proof (internal only) | Internal experiment only. Two of our 23 drafted planning cards carried headline figures that were wrong because the number was divided by a short, recent baseline in one system and by the full history in the other. One card said 14.4 times and the honest figure is 1.87 times; the item was ordinary for its author and the card had been prioritised on the strength of that number. Both numbers are still in our files and can be shown side by side. |
| CTA | free_resource |
| Visual structure | SCREEN (both numbers on screen together, promise burned in as a top banner, 0-9 s) > A_ROLL_MEDIUM (what a baseline is, in one sentence, no jargon, 9-20 s) > SCREEN (tracing each number to its own source, one continuous take, 20-44 s) > A_ROLL_MEDIUM (the one-definition rule and the closing line, 44-62 s). Coarse sequence SCR>A>SCR>A. No split screen - the two numbers sit in one full-frame shot, not in two half-frames. |
| Positioning fit | Process: producing a recurring figure that other people act on - a margin, a headline number in a report, a price, a stock count. Friction: the number is calculated in one place and quoted in another, both are defensible, and nobody notices they disagree until a decision has already been made on the wrong one. AI boundary: the machine can recompute the figure and flag the disagreement every time it appears; deciding which definition is the right one is a human decision that has to be written down once. Next action: pick the figure you quote most often, find the second place it is calculated, and write down which one is authoritative. |
| Strengths | The strongest forwardable fact of the two selected Teardowns: a fourteen-fold error that passed a review is exactly the 'вот сколько это стоит' the Teardown pass criterion requires. The process - a figure calculated in two places - is universal and needs no explanation. The artefact, a one-page definition sheet, is publishable rather than gated. |
| Risks | The arithmetic must stay out of the reel. If the words 'baseline' or 'median' need defining, the reel has already lost a level-0-6 viewer; the fix is to say 'we divided by eleven things instead of twenty-seven'. |
| Novelty | No reel in the corpus corrects its own number. 36 of 266 use numbers as proof and every one of them presents the number as settled. |
| Confidence | PROBABLE |
| Reviewer comment | The most transferable card in the whole set - every business has this and nobody films it. It only fails if the script explains statistics; write it as two receipts for the same job with different totals and it is finished. |
| Supporting insights | I-23, I-13, I-08, I-09, I-01, I-29, I-15 |
| Candidate references | [DaGTeJNN1GR](https://www.instagram.com/reel/DaGTeJNN1GR/), [DUJYKENjZc5](https://www.instagram.com/reel/DUJYKENjZc5/), [DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/), [DVtgbY8Av6A](https://www.instagram.com/reel/DVtgbY8Av6A/) |
| Scores | ev 5, rq 4, pos 5, aud 5, nov 4, cla 4, hk 4, dep 4, vis 4, fea 5, tr 4, gr 4, cr 5, as 4 |
| **Total** | **4.43** |

### H-09 — One prompt beats one agent for a task you do five times a week

**Statement.** If we explain when a single written prompt with a checklist outperforms a multi-step agent to a non-technical small-business leader through the pressure to build something impressive before anything works, using a contrarian demo-first hook that runs the simple version first + a screen demo of the same task done both ways + a single unbroken screen take with the face only at the verdict, then the viewer will start with the smaller thing, because they will have watched it win.

| field | value |
|---|---|
| Format | M2 Radar |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically someone who has been told they need an agent. |
| Pain (canonical) | dont_know_where_to_start |
| Desired outcome | A first version that works this week and that the person doing the job can change themselves. |
| Hook | "Here is the same job done twice. The version with six agents lost to a paragraph of text." - hook_type: demo_first |
| Thesis | Complexity is not the same as capability. For a task that runs five times a week, the maintainable version usually wins on total time, and the elaborate version fails quietly. |
| Mechanism | Show the simple version running on screen first, then the elaborate one, then compare on three axes the viewer can check: who can change it, what happens when it is wrong, how long it takes to set up. |
| Proof (internal only) | Internal experiment only. We built 115 numeric features over 268 analysed videos to work out what makes a reel strong; not one of them separated the top from the bottom quartile at p<0.01. The single instruction that did survive - is there a real screen on camera - was one question we could have asked on day one. The elaborate measurement lost to the simple one, and we can show both on screen. |
| CTA | save_share |
| Visual structure | SCREEN, one continuous take of the simple run with narration over it and the promise on a persistent top banner (0-22 s) > SCREEN, the elaborate version and where it stalls (22-42 s) > A_ROLL_MEDIUM (the three questions and the verdict, 42-60 s). Coarse sequence SCR>A. Modelled on the single unbroken process shot, which is the highest-lift visual sequence in the corpus, not on split screen. |
| Positioning fit | Process: a knowledge task the team repeats about five times a week - a quote, a summary, a reply, a status note. Friction: the advice on offer is to build a multi-step agent, which nobody in a small company can maintain. AI boundary: a written prompt plus a checklist keeps the judgement with the person running it; an agent moves that judgement into software nobody owns. Next action: write the task out as one prompt with three checks and run it by hand five times before automating anything. |
| Strengths | It takes the energy of the highest-lift topic in the corpus - agent building, n=27, median view_lift 6.63 - and refuses its shape, which is precisely the instruction in I-25. myth_bust carries the second-highest robust_z of any narrative (1.93) on the smallest explanation share, which is this reel's shape exactly. |
| Risks | Sounds like an opinion unless both runs are genuinely on screen. There is also a real chance of being read as anti-AI; the closing line has to say which tasks do deserve the bigger build. |
| Novelty | The corpus contains 27 agent-build reels and 23 with an agent_build solution type, and not one argues against the build. A demonstrated 'the small version won' is unrepresented. |
| Confidence | PROBABLE |
| Reviewer comment | Highest novelty of the Radar four and the one most likely to be forwarded to a colleague who is about to overbuild. Its danger is register: the corpus punishes contrarian hooks on share and save (0.0076 and 0.0139, the lowest of the large hook cells), so the reel must open on the demo, not on the disagreement. |
| Supporting insights | I-22, I-25, I-08, I-09, I-27, I-16, I-05 |
| Candidate references | [Dbs2JdJKUDd](https://www.instagram.com/reel/Dbs2JdJKUDd/), [DbVKVz0y8xo](https://www.instagram.com/reel/DbVKVz0y8xo/), [DZQZOVhgNvK](https://www.instagram.com/reel/DZQZOVhgNvK/), [DVaBP3wDAFE](https://www.instagram.com/reel/DVaBP3wDAFE/) |
| Scores | ev 4, rq 4, pos 5, aud 5, nov 5, cla 4, hk 4, dep 4, vis 4, fea 4, tr 4, gr 4, cr 4, as 4 |
| **Total** | **4.29** |

### H-05 — The connector list is the decision

**Statement.** If we explain that an AI tool is only as useful as the systems it can already reach to a non-technical small-business leader through the frustration of buying something clever that cannot see the company's inbox, calendar or spreadsheet, using a demo-first hook on a workflow naming each system out loud + a screen demo that follows one piece of data from inbox to sheet to calendar + a screen-first visual grammar, then the viewer will check the integrations page before the feature page, because that list is what decides whether the tool touches their real work.

| field | value |
|---|---|
| Format | M2 Radar |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically anyone about to trial a tool for a process that already lives in email, a spreadsheet or a calendar. |
| Pain (canonical) | manual_repetition |
| Desired outcome | A tool that plugs into the systems the work already lives in, so nothing has to be re-entered by hand. |
| Hook | "Watch one enquiry move from the inbox to the sheet to the calendar. Every one of those three names is a reason a tool can fail." - hook_type: demo_first |
| Thesis | The question is not what the model can do, it is which of your existing systems it can already read and write. That list is short, checkable in two minutes, and decides everything. |
| Mechanism | Follow one item end to end on screen and name each destination aloud as it arrives. Then show the same three names on the tool's own integrations page. Where a name is missing, that step stays manual - say so. |
| Proof (internal only) | Internal experiment only. Our own weekly run is a chain of named systems - the data source, local transcription, local frame extraction, a SQLite file, a Notion page - and it has already failed at exactly this seam: a free source we depended on closed mid-run and the week's collection stopped where the connector was. We show the chain and the point where it broke. |
| CTA | save_share |
| Visual structure | SCREEN (the item arriving, promise burned in as top banner, 0-10 s) > SCREEN continues as the item moves to the sheet and the calendar, each destination named on the banner (10-32 s) > A_ROLL_MEDIUM (the two-minute check to run before a trial, 32-52 s) > A_ROLL closing line. Coarse sequence SCR>A. First frame is a UI_DEMO mid-action, never a face. |
| Positioning fit | Process: any repeated task whose inputs and outputs already sit in Gmail or Outlook, a spreadsheet and a calendar. Friction: a tool that cannot read those systems means the work becomes copy-and-paste, which is more manual work than before. AI boundary: the tool moves and drafts between named systems; the human owns the account access and decides what data it may see. Next action: write down the three systems your process actually touches and check them against the tool's integrations page before the trial starts. |
| Strengths | Naming specific things is the only lexical feature that predicts reach and survives creator normalisation (distinct entities vs view_lift +0.161 pooled, +0.198 within creators), and this reel is built entirely out of names. manual_repetition is the highest-lift pain in the corpus (median view_lift 6.94 on n=15). Screen-first opening carries share rate 0.0213 against 0.0140. |
| Risks | Tips into a tool tutorial if the systems shown are exotic. Use the three most ordinary ones - inbox, spreadsheet, calendar - and nothing else. |
| Novelty | The corpus names tools constantly and integrations almost never; the connector list is treated as plumbing rather than as the decision. Framing plumbing as the buying criterion is the angle. |
| Confidence | PROBABLE |
| Reviewer comment | Solid but the least surprising of the four selected Radar cards. It earns its slot on specificity - it is the one that most directly executes the single reach finding that survives normalisation. Keep the tool names boring on purpose. |
| Supporting insights | I-09, I-13, I-08, I-15, I-02, I-05 |
| Candidate references | [DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/), [DZU9x_1AY2t](https://www.instagram.com/reel/DZU9x_1AY2t/), [Db9MT-axxcO](https://www.instagram.com/reel/Db9MT-axxcO/), [DVZGBgTk6zz](https://www.instagram.com/reel/DVZGBgTk6zz/) |
| Scores | ev 4, rq 4, pos 5, aud 5, nov 4, cla 4, hk 4, dep 4, vis 5, fea 4, tr 4, gr 4, cr 4, as 4 |
| **Total** | **4.26** |

### H-19 — Our Monday, taken apart

**Statement.** If we explain our own weekly planning process step by step to a non-technical small-business leader through the frustration of a Monday that produces decisions nothing ever comes of, using a demo-first hook on the actual artefact the Monday produces + a screen demo of each step with the minutes and the output named + an A>SCREEN>A grammar that ends on the one step where everything stops, then the viewer will time their own weekly ritual, because they will have watched a plausible process leak at the end rather than at the start.

| field | value |
|---|---|
| Format | M2 Teardown |
| Audience | Non-technical small-business leader, AI level 0-6 of 10 (POSITIONING.md §4): an owner, operations lead or team lead in a 5-50 person company who is responsible for one repeated process and has tried ChatGPT but has no repeatable way of using it at work. Specifically whoever runs the weekly planning ritual. |
| Pain (canonical) | manual_repetition |
| Desired outcome | A weekly ritual whose output actually moves, and a way to see the step where it stops. |
| Hook | "This is what our Monday produces. Thirty-three of these were made and not one of them was ever used." - hook_type: demo_first |
| Thesis | Most weekly processes are well built up to the handover and unowned after it. The expensive failure is not the plan, it is the step where the plan becomes somebody's job. |
| Mechanism | Walk the five steps on screen with the artefact each one produces: collect, score, shortlist, strike out, hand over. Name the minutes each takes. Then show where the count drops to zero - and it is the last step, not any of the automated ones. |
| Proof (internal only) | Internal experiment only. Our own weekly run has produced 33 planning cards across three weeks. Zero have been shot and zero published; the table that would record a produced item is empty. Two cards were re-proposed in a later week because a drafted item was never marked as used, so the same work was done twice. All of it is visible in our own files. |
| CTA | save_share |
| Visual structure | SCREEN (the artefact the Monday produces, mid-scroll, promise on a persistent top banner, 0-10 s) > SCREEN continues, one step per beat with the output named on the banner (10-34 s) > A_ROLL_MEDIUM (the step where it stops and the owner question, 34-56 s) > A_ROLL closing line. Coarse sequence SCR>A. No split screen; the process map is a full-frame insert, not a graphic behind a face. |
| Positioning fit | Process: the recurring weekly planning meeting or run that produces a list of things to do. Friction: the effort is spent on producing the list, and the list is not where the process fails - it fails at the handover, where nobody is named. AI boundary: the machine can collect, rank and draft the list; deciding which items are real and who owns them stays with a person, and no step downstream may start without that name. Next action: for last week's list, write the owner's name next to each item and count how many are blank. |
| Strengths | It is a process we genuinely own and may show without anyone's permission, which RULES §2 names as the only Teardown source available from day one. It also carries the forwardable fact the Teardown criterion demands: thirty-three plans, nothing produced. |
| Risks | Our Monday is a content process, not a trade or a service business, so the parallel has to be drawn in the viewer's own vocabulary. The admission is also unflattering and must not become an excuse for the reel to be about us. |
| Novelty | The corpus states a problem in only 64 of 264 reels and never takes apart a process the author runs. A step-by-step of the author's own week with the failure point named is unrepresented. |
| Confidence | PROBABLE |
| Reviewer comment | A real Teardown with a real owner and a real forwardable number, which is more than the other five Teardown candidates can say. Its weakness is subject distance: keep the process map generic enough that an operations lead sees their own Monday inside the first fifteen seconds. |
| Supporting insights | I-17, I-09, I-08, I-15, I-13, I-29, I-05 |
| Candidate references | [DYuivWzSj5k](https://www.instagram.com/reel/DYuivWzSj5k/), [DZLDk9ySi-7](https://www.instagram.com/reel/DZLDk9ySi-7/), [Db9MT-axxcO](https://www.instagram.com/reel/Db9MT-axxcO/), [DbbA7wwTIZ8](https://www.instagram.com/reel/DbbA7wwTIZ8/) |
| Scores | ev 4, rq 4, pos 5, aud 5, nov 4, cla 4, hk 4, dep 4, vis 4, fea 4, tr 4, gr 3, cr 4, as 4 |
| **Total** | **4.16** |

---

## 6. What this set does not contain

- **No reach promise.** Nine of the thirteen RELIABLE correlations in the whole association run are save-rate correlations and none is against `robust_z` (I-22). Every hypothesis above is written to be judged on shares and saves per 1 000, never on views.

- **No claim that a format wins.** Of 115 numeric features, none separates the strong from the weak quartile at p<0.01. The differences between these twenty-four are differences of subject, specificity and evidence, which is where the data says the remaining variance lives.

- **No duration argument.** The 50–70 second band in PRODUCTION.md is kept as a production convenience and is not cited as a reach lever anywhere above (I-02).

- **No claim about our cut rate.** The cut metric is a scene-score threshold, not a shot count (I-20).

