# 31. What Works

**What "works" can mean here.** Nothing in this chapter is a cause. Every line is an association measured
inside the analysis-ready corpus (**n=268**, 102 creators, median `robust_z` +1.26 against 0.00 across all
3 211), which is the top of `score.py`'s own ranking. "Works" therefore means: **associated with a higher
creator-relative score, or a higher share or save rate, among reels that were already strong** [I-01].
Where a contrast is present it is probably understated; where one is absent, that is not proof the feature
is irrelevant in the niche at large.

## The evidence, ranked by strength

| # | What works | Evidence | Confidence |
|---|---|---|---|
| 1 | **Put a real screen on camera, anywhere in the reel** | `screen_share` → share_rate +0.203 (p=0.00085, cn +0.129); any screen state present → save_rate +0.210 (cn +0.213); any-screen reels share 0.0168 vs 0.0118 (p=0.00013), save 0.0308 vs 0.0220 (p=0.001) | **RELIABLE** |
| 2 | **Open on the screen, not the face** | 35 of 266 first frames are a screen: share 0.0213 vs 0.0140, view_lift 5.25 vs 1.88, robust_z 2.13 vs 1.21; pooled +0.208, **creator-normalised +0.285 (p=0.00025)** — stronger within creators than between them | **RELIABLE** |
| 3 | **Name the exact tool, number and step** | `lex_entities_distinct` → view_lift +0.161 (cn **+0.198**) — the only reach correlation surviving normalisation; strong quartile 2 distinct entities vs 1 (p=0.011); `lex_tools_n` → view_lift +0.157 (cn +0.223); `specificity` → view_lift +0.132 (cn +0.205) | **RELIABLE** (entities) / PROBABLE (rest) |
| 4 | **Write in the second person with concrete asks** | second person → save_rate +0.206 (cn +0.177); CTA verbs +0.241 (cn +0.155); direct address per 100 w +0.174 (cn +0.127); first person −0.180 (cn −0.124) | **RELIABLE** |
| 5 | **Write the hook as a statement, not a question** | `questions_n` → save_rate −0.229 (p=0.00031, cn −0.162); questions per 10 s −0.235 (cn −0.186); rhetorical questions −0.186 (cn −0.151); corpus median `questions_n` = **0** | **RELIABLE** |
| 6 | **Open on the artefact doing the work (show-first)** | demo_first + result_first, n=42, 29 creators: median robust_z **2.17** / view_lift **5.81** vs 1.21 / 1.80 (p=0.021 and 0.008) | PROBABLE |
| 7 | **Come back to the face for the payoff and the close** | `A > SCREEN > A`, 39 reels / 32 creators: share 0.0213 vs 0.0140 (p=0.00076); the exact three-state form (n=11, 11 creators) median robust_z **3.01** | PROBABLE |
| 8 | **Give the solution statement room (~12 s)** | strong quartile `solution_s` 12.25 s vs 8.4 s (**p=0.0065**) — the only script part clearing p<0.01 among 115 features; strong reallocates from explanation (34.1 % vs 41.9 %) rather than extending | PROBABLE |
| 9 | **Hand over an artefact** | `resource_handoff` save rate **0.0429**, highest of any solution type (n=38, 28 creators), vs `framework_mental_model` 0.0135 (n=25); ready-made-artefact desire save 0.0346 vs 0.0270 (p=0.052) | PROBABLE |
| 10 | **Name the pain as an act, not a condition** | `manual_repetition` view_lift **6.94** / save 0.0390 (n=15) and `time_waste` 3.54 / 0.0365 (n=20) vs `chaos_no_process` **0.87** (n=17) and `slow_response_to_leads` **0.47** (n=5) | PROBABLE |
| 11 | **Give the hook 5–10 s and 20–30 words** | median hook 6.7 s / 21.5 words / 13.2 % of speech (n=260); hook *words* separate the quartiles (26.5 vs 22.0, p=0.028) while hook *seconds* do not (p=0.162) | PROBABLE |
| 12 | **Open exactly one loop** | 240 of 266 reels carry ≥1; median exactly 1 (198 reels); only 15 of 264 carry an explicit re-hook | PROBABLE |
| 13 | **Adopt the builder register** | `builder` positioning n=38, 27 creators, median view_lift **3.42** vs `educator` 1.73 (n=138); `demo_walkthrough` is the largest archetype (n=62, 42 creators) and the highest-lift (3.70) | PROBABLE |
| 14 | **Repeat vocabulary rather than varying it** | strong quartile `lex_ttr` 0.605 vs 0.628 (p=0.039), `lex_mattr50` 0.795 vs 0.811 (p=0.044) — winners repeat the tool name and the step word | PROBABLE |
| 15 | **Close in the last 10 %, ~5 s and 20 words, one ask** | CTA starts at a median 90 % of spoken length; 202 of 216 in the final quarter; median 4.95 s / 21 words; strong quartile 5.7 s vs 4.4 s | PROBABLE |
| 16 | **Show a single unbroken process shot when the build really runs** | pure `B_ROLL_PROCESS` n=6, 4 creators: median view_lift **30.90**, robust_z 4.13 — the highest of any visual sequence | INSUFFICIENT |

Rows 1–5 are the only ones that meet the method's RELIABLE bar (n ≥ 30, ≥ 8 creators, p<0.01 **and** a
surviving creator-normalised check). Rows 6–15 are real but weaker: they rest on categorical medians,
which admit no normalisation test, or on cells of 15 to 42 reels. Row 16 is printed because it points the
same way as rows 1 and 2 and because suppressing it would hide a cell, not because six reels can carry an
instruction.

## What this sounds like when a reel does most of it at once

[DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/) — 451 491 plays, 55.4× its author's median,
36.5 saves per 1 000, **ungated** — does rows 1, 2, 3, 6, 7, 9, 12 and 15 in 68 seconds. The artefact
speaks the first four words (**"Hello, how can I assist you? This voice assistant can replace your
receptionist. I'll show you how to build it in three easy steps."**, hook 0.0–6.4 s): show-first, screen
first frame, statement not question, and a bounded promise. The mechanism names each destination at the
moment it becomes necessary — **"it uses Google Calendar to check your schedule and Google Sheets to save
any details"** (6.4–20.0 s) — which is row 3 executed literally. A single 1.8-second re-hook ("But how
about the results?", 32.0–33.8 s) closes the one open loop, and the reel ends on the machine finishing its
job rather than on an ask.

**Visual reading.** fa-v1 records `first_frame_type: UI_DEMO` — the n8n "AI Voice Assistant" canvas with a
pulsing "Listening" widget and the presenter's facecam small at the bottom — and two proof visuals: the
live workflow run and the Google Calendar day view showing the appointment the assistant created. The
screen is the argument; the face is a footnote on it. That is rows 1, 2 and 7 in one storyboard.

## The single clearest same-creator demonstration

`edhillai` published DNA7-d3o5sQ at `robust_z` **+4.69** and
[DXb8P08Dati](https://www.instagram.com/reel/DXb8P08Dati/) — **"Day one of two AI tips to make you an N8N
expert."** — at `robust_z` **−1.04**. Same creator, same subject area, same production quality, both with
`UI_DEMO` first frames. What separates them is which sentence comes first: the artefact, or the programme.
Because it is one creator, the comparison holds the audience, the account and the algorithmic history
constant in a way no pooled statistic can.

## Strategic implication

Rows 1–5 are **binding production rules** for M2 and should be written into the card template as checks:
own screen present, screen in frame one, three distinct named destinations, second person, zero questions.
Rows 6–15 are **defaults to follow unless a specific reel argues otherwise**, and each should carry its
confidence label onto the card so a writer knows which ones are negotiable. Row 16 is a **licence, not an
instruction**: when an M2 build genuinely runs end to end, record it in one take and narrate over it — it
also happens to be the cheapest thing to shoot.

**Confidence: RELIABLE** for rows 1–5 as associations inside this corpus. **PROBABLE** for rows 6–15.
**INSUFFICIENT** for row 16. All of it is associational, all of it is computed inside a pre-selected 8.3 %
of the database, and none of it licenses a causal claim or a promise about reach.
