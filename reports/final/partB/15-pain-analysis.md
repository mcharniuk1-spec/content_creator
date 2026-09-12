# 15. Pain Analysis

**Denominators.** All 266 analysis-ready reels with a ta-v1 read carry a canonical `pain` label from a
closed list of 13 values (12 named plus `other`). The chart draws the twelve largest cells, **n=261**.
Two cells clear the SUFFICIENT_SAMPLE size threshold (n ≥ 30 and ≥ 8 creators); the rest are PROBABLE.
No creator-normalised test applies to a categorical median, so **no pain cell can be RELIABLE by the
method's own rule** (§8.5). Baselines: median `view_lift` 2.03, median `robust_z` 1.26, share 0.0152
(n=268), save 0.0278 (n=245).

![Pain point vs performance — twelve largest cells, n=261](reports/charts/pain_vs_performance.png)

| pain | n | creators | median view_lift | median robust_z | share/1k | save/1k | confidence |
|---|---:|---:|---:|---:|---:|---:|---|
| cost_money | 48 | 33 | 1.96 | 1.38 | 16.4 | 30.3 | SUFFICIENT_SAMPLE |
| dont_know_where_to_start | 34 | 30 | 1.34 | 1.06 | 17.5 | 34.6 | SUFFICIENT_SAMPLE |
| keeping_up_with_ai | 29 | 24 | 1.73 | 1.16 | 16.1 | 18.1 | PROBABLE |
| missing_skills | 25 | 20 | 1.34 | 1.13 | 9.7 | 24.6 | PROBABLE |
| quality_trust | 25 | 20 | 1.63 | 1.09 | 13.3 | 27.5 | PROBABLE |
| other | 24 | 21 | 5.30 | 1.57 | 12.5 | 21.2 | PROBABLE |
| time_waste | 20 | 17 | **3.54** | 1.54 | 19.9 | **36.4** | PROBABLE |
| chaos_no_process | 17 | 14 | **0.87** | 0.67 | 13.8 | 26.4 | PROBABLE |
| manual_repetition | 15 | 13 | **6.94** | 1.81 | 16.1 | **39.0** | PROBABLE |
| scaling_without_hiring | 8 | 8 | 4.83 | 2.37 | 20.9 | 35.9 | PROBABLE |
| tool_overload | 8 | 8 | 2.98 | 1.96 | 14.4 | 21.7 | PROBABLE |
| fear_of_replacement | 8 | 6 | 2.11 | 1.38 | 15.3 | 12.6 | PROBABLE |
| slow_response_to_leads | 5 | 3 | **0.47** | 0.35 | **0.1** | **0.1** | PROBABLE |

## The finding: an act beats a condition

Order the table by lift and a single distinction explains most of the spread. The two strongest pains
name **something the viewer physically does**: `manual_repetition` (6.94× lift, 39.0 saves per 1 000 —
the highest save rate of any pain cell) and `time_waste` (3.54×, 36.4 saves). The two weakest name **a
property of the viewer's business**: `chaos_no_process` (0.87×) and `slow_response_to_leads` (0.47×,
and a share rate of 0.1 per 1 000, which is the lowest number in this report). `scaling_without_hiring`
sits with the strong group at 4.83× on eight reels, and it too is phrased as an act the owner is
avoiding.

This is uncomfortable for M2 because **the two weakest cells are the two closest to M2's own
vocabulary**. "Your process is chaotic" and "you respond to leads too slowly" are the language of a
process consultancy, and this corpus does not reward them. "You retype the same numbers out of a PDF
every Monday" is the same underlying pain named as an act, and it sits in the 6.94× bucket. The
translation is free: nothing in POSITIONING.md requires the condition phrasing, and RULES.md §4 already
asks for "процесс по шагам" — the process step by step — which is the act phrasing by another name.

**Two cautions before this becomes a rule.** First, `manual_repetition` is 15 reels across 13 creators
and `slow_response_to_leads` is 5 reels across 3 — the second is INSUFFICIENT-adjacent and its
0.1 share rate is almost certainly one or two accounts with no distribution rather than a property of
the pain. Second, the whole table is computed inside a pre-selected strong sample, so a low cell means
"weak among strong reels", not "fails in the niche" [I-01].

## What the pain sounds like when it works

[DYuivWzSj5k](https://www.instagram.com/reel/DYuivWzSj5k/) (aiforbusinesses247, 113 697 plays, 32.2×,
50.8 shares per 1 000) is 59 spoken words and names no tool, no step and no number. Its whole pain
statement is the hook: **"Think, when you wake up in the morning, the clients are already interested in
your service."** (0.0–3.7 s). The pain is not described — it is inverted into a morning the viewer can
picture. Its sibling [DZLDk9ySi-7](https://www.instagram.com/reel/DZLDk9ySi-7/) from the same account
(179 093 plays, 51.4×) does the same move and then lists the friction *after* the payoff:
**"No manual data scraping. No cold outreach headache. No manually demo websites. No hours waste to
find leads."** (pain beat, 25.8–32.6 s). Placing the pain list third — after the outcome and the
mechanism — makes the pain read as a reward rather than an accusation.

Contrast the weakest neighbourhood. [DcmK70aO5VP](https://www.instagram.com/reel/DcmK70aO5VP/) reaches
only 1.55× its author's accumulated median and yet carries 40.3 shares and 62.1 saves per 1 000, because
its three examples — law firm intake, résumé filtering, insurance document collection — are each a named
repeated act. Its defect is the frame around them: **"three AI automations that can literally help you
make eight thousand dollars in just a month"** (hook, 0.0–5.6 s) prices the pain in income, which costs
reach (chapter 26).

**Visual reading.** The pain-as-act reels show the act. DZLDk9ySi-7 opens on a dark neon animated
flowchart titled "AI Agent Workflow — Fully Automated, Zero Manual Work" revealing numbered steps one at
a time, and its proof visuals are live pipeline stat cards counting leads, sites, outreach, replies and
meetings. DcmK70aO5VP alternates presenter and `DATA_VISUAL`, showing an n8n-style diagram
("Incoming webhook → Claude classifier → Parse classification → Route switch"). In both, the friction
is a *thing on screen with a count on it* — not an adjective.

## Where the corpus states the pain at all

Only **64 of 264** parsed reels (24 %) contain a problem, pain or tension beat, and where the beat
exists it lands early: median start at **21 % of spoken length** (p25 0.15, p75 0.39), with **56 %
inside the first quarter**, and a median length of **8.95 s / 32 words** [I-17]. Three quarters of this
niche never states a problem out loud. M2's mandatory editorial filter requires one, so M2 will
structurally differ from the niche here and must budget the seconds for it.

## Strategic implication

Three concrete rules. **(1) Name the act, never the condition.** Every M2 Teardown pain line must be a
sentence with a verb the viewer performs and a frequency — "every Monday you copy fourteen rows out of a
PDF" — not "your intake process is chaotic". **(2) Budget 8–10 seconds and put it in the first
quarter**, matching the niche's own minority practice rather than inventing a placement. **(3) Show the
friction as an artefact**: the spreadsheet, the inbox, the paper form, on camera with a number on it.
Do not price the pain in money — that is chapter 26's finding and it costs reach.

**Confidence: PROBABLE** for the act-versus-condition contrast (two SUFFICIENT_SAMPLE cells, but the key
comparison rests on cells of 15 and 17 reels and no creator-normalised test exists for a categorical
median). **INSUFFICIENT** for `slow_response_to_leads` as evidence about anything — 5 reels across 3
creators. **PROBABLE** for the placement statistics (n=64). No causal claim: this is an association
between how a pain was labelled and how the reel performed for its own author.
