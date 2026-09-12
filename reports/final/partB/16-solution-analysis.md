# 16. Solution Analysis

**Denominators.** 266 analysis-ready reels carry a ta-v1 `solution_type` from a closed list of ten
values. Three cells clear the SUFFICIENT_SAMPLE threshold (n ≥ 30, ≥ 8 creators): `tool_walkthrough`,
`workflow_recipe` and `resource_handoff`. Save rates divide by 245 (HikerAPI drops the field on ~9–10 %
of rows); everything else by 266. Baselines: median `view_lift` 2.03, `robust_z` 1.26, share 0.0152,
save 0.0278.

| solution_type | n | creators | median view_lift | median robust_z | share/1k | save/1k | confidence |
|---|---:|---:|---:|---:|---:|---:|---|
| tool_walkthrough | 60 | 40 | 1.96 | 1.09 | 16.6 | 30.3 | SUFFICIENT_SAMPLE |
| workflow_recipe | 51 | 35 | 1.60 | 1.11 | 14.7 | 34.7 | SUFFICIENT_SAMPLE |
| resource_handoff | 38 | 28 | 2.05 | 1.29 | 17.2 | **42.9** | SUFFICIENT_SAMPLE |
| framework_mental_model | 25 | 16 | 1.49 | 1.08 | 9.2 | **13.5** | PROBABLE |
| agent_build | 23 | 17 | **6.33** | 2.18 | 17.4 | 33.5 | PROBABLE |
| other | 23 | 17 | 2.36 | 1.22 | 15.9 | 8.3 | PROBABLE |
| case_story | 18 | 15 | 3.74 | 2.35 | 12.6 | 18.9 | PROBABLE |
| comparison | 12 | 10 | **7.85** | 1.93 | 7.0 | 13.4 | PROBABLE |
| prompt_technique | 10 | 10 | **0.71** | 0.67 | 14.0 | 37.2 | PROBABLE |
| warning_dont | 6 | 6 | 0.88 | 0.87 | 8.2 | 19.5 | PROBABLE |

## Two different questions, two different answers

The table answers two questions at once and they do not have the same answer. **What reaches** is
`agent_build` (6.33× on 23 reels) and `comparison` (7.85× on 12) — both PROBABLE, both small, both
driven by a handful of very large multipliers from high-variance accounts. **What is kept** is
`resource_handoff`: **42.9 saves per 1 000**, the highest of any solution type and 1.5× the corpus
median, on the largest cell that is not a walkthrough. Its opposite is `framework_mental_model` —
the "here is how to think about this" answer — at **13.5 saves per 1 000**, less than a third of
`resource_handoff` and the lowest of any cell above n=20.

Stated plainly: **the niche's audience does not save a way of thinking.** It saves a thing it intends to
use. This is the same finding the desire classification produces independently — reels whose stated
desire is a ready-made artefact (repo, file, template, map, prompt pack) carry median save rate
**0.0346 against 0.0270** for the rest (n=27, p=0.052), and reels whose stated desire is *certainty*
that a thing actually works carry **0.0140 against 0.0282** (n=19, p=0.017, negative) [I-29]. Read
together with chapter 26's lexical results — named platforms are the strongest save correlate in the
whole run at rho +0.331 — the picture is consistent: a save is a bet that the viewer will do the thing,
and it requires a destination and an object.

## The mechanism: deliberate incompleteness

The cleanest example of the artefact demand is also the clearest thing M2 must invert.
[DVtgbY8Av6A](https://www.instagram.com/reel/DVtgbY8Av6A/) is **84 spoken words** carrying **57.3 saves
per 1 000**. Its hook is one sentence — **"My 15 favorite Claude skills in 60 seconds."** (0.0–2.3 s) —
followed by a solution beat that is a bare list of skill names ("My cost reducer skill. My internet
skill. My scalability skill…", 2.3–15.3 s), a payoff naming the best one, and then the withholding
turn: **"If you want all of my skills completely for free just come in skills and I'll send them to
you."** (cta, 21.3–25.4 s). A skill name is useless without the file. The reel is a pure demonstration
that the artefact, not the explanation, is the object of desire — and the gate is simply the mechanism
by which the artefact is withheld.

The same move without the gate is [Dc_TX1CttIc](https://www.instagram.com/reel/Dc_TX1CttIc/) (562 094
plays, 24.1×, 31.7 shares per 1 000, ungated, so the rates are clean). It announces its agenda in nine
seconds — **"I tested GPT-6 Astra with four use cases and here's how it went. The four use cases were
3d rendering, animated 3d website, film storyboard and viral content writing."** (hook, 0.0–9.5 s) —
labels each case aloud, and earns a verdict: **"Very good model for sure, but the API cost has shot up
so high that any business trying to build a real product on Astra is walking into a train wreck"**
(payoff, 80.8–92.6 s). The deliverable here is a decision, delivered whole, and it is the closest thing
in the corpus to what an M2 Radar reel should be.

**Visual reading.** `resource_handoff` reels are visually specific: the artefact is on screen and
countable. fa-v1's read of [Dct6Op3n6Zd](https://www.instagram.com/reel/Dct6Op3n6Zd/) (75.9 saves per
1 000, the second-highest in the corpus) records bold repo logo cards appearing above the host as he
opens "4 GitHub Repos went viral this week and barely anyone's actually using them yet", with a
before/after pipeline diagram and an agent-count dashboard as its two proof visuals. `framework_mental_model`
reels have nothing equivalent to show, which is very likely why they are not kept: there is no object.
Note that Dct6Op3n6Zd holds a split screen for all nine samples — copy the ordering, not the layout
(chapter 23).

## The part of the script this lives in

`solution_s` is the **only** script part whose strong-versus-weak difference clears p<0.01: **12.25 s in
the strong `robust_z` quartile against 8.4 s in the weak one (Mann-Whitney p=0.0065)**, and 21.1 % of
speech against 15.3 %. It is present in only 70 of 264 parsed reels (27 %), at a median 10.4 s / 36
words, and the median time to reach it is 19.7 s. The pooled correlation `solution_s` → `view_lift` is
+0.343 (n=70) but it does **not** survive creator normalisation (cn +0.085) and neither does the
`robust_z` version (+0.342 → cn +0.106) — so the quartile contrast is the evidence, and the correlation
is a statement about which creators write long solution statements.

## Strategic implication

**(1) Every M2 reel ships an artefact, and publishes it.** A checklist, a process map, a prompt, a
one-page teardown — named in the reel and available without asking, because RULES.md bans the gate and
chapter 18 shows the ban costs no reach. The save then comes from there being something to collect.
**(2) Never let the solution be a framework.** "Here is how to decide" is the lowest-saved cell in the
table; if M2 has a mental model to teach, it must arrive attached to a downloadable object.
**(3) Give the solution sentence room** — around 12 seconds, taken out of the mechanism block, not added
to the runtime. It is the one part-length instruction this dataset actually supports.

**Confidence: PROBABLE** for the `resource_handoff` versus `framework_mental_model` save contrast — both
cells are large enough to report (38/28 and 25/16 creators) but a categorical median admits no
creator-normalised check, and 33 of the 40 pool reels are gated, which inflates saves ×2.8 unevenly
across cells. **PROBABLE** for `agent_build` and `comparison` reach, which rest on 23 and 12 reels.
The `solution_s` contrast is the strongest single numeric result of the wave (p=0.0065) and travels
inside RELIABLE insight [I-22], but its own cell is 18 reels against 19 inside a 67-per-side split, so on
its own it is **PROBABLE**. No causal claim.
