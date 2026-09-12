# 06 — Creators and reference candidates

Spec §19. Consistent creators with numbers, high-variance creators, the best videos across creators, and a
reference-candidate pool of 40 reels for the hypothesis agent to select from.

**Sources.** `reports/data/creators.csv` (132 rows, `creator_stats` at snapshot 3),
`reports/data/analysis_ready.csv` (268 reels, 102 creators), `reports/data/temporal.json`,
`data/analysis/transcripts/*.json`, `data/analysis/frames/*.json`.

**Denominators.** 132 creators have a `creator_stats` row; 102 of them contribute reels to the analysed
set, at a median of 2 reels each (p75 = 4, max 6). `followers` is populated for all 132 but the
`followers` table itself is empty, so creator *growth* cannot be answered at all.

---

## 1. The creator landscape

| | value |
|---|---|
| creators with a `creator_stats` row | 132 |
| `CONSISTENT` (CV<1 **and** n≥8) | **17** (13 %) |
| `HIGH_VARIANCE` | **115** (87 %) |
| `SMALL_SAMPLE` (n<5) | 0 |
| median videos per creator in baseline | 26 |
| median creator median play | 14 936 |
| median consistency score (1/(1+CV)) | **0.352** |
| median log-play slope over last 10 posts | **−0.052** |
| creators with a 10-post window trending up | **34 of 131 (26 %)** |
| posts exceeding 5× their creator's rolling median | 269 of 3 078 (8.7 %), across 101 creators |
| posts exceeding 10× | 150 (4.7 %) |

**The niche runs on lottery tickets.** 87 % of tracked creators are HIGH_VARIANCE, and three quarters of
them are losing reach over their most recent ten posts. `posts_per_week` is a lower bound throughout — the
corpus holds what was visible on a profile page at collection time, not full posting history.

---

## 2. Consistent creators (all 17, sorted by median play)

| username | n videos | median play | CV | consistency | posts/week | high-performer share | outlier share | median share rate | median save rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| angus.sewell | 12 | 89 439 | 0.98 | 0.505 | 4.39 | 0.250 | 0.083 | 0.0096 | 0.0231 |
| harshsharma_ai | 12 | 44 377 | 0.96 | 0.509 | 2.59 | 0.333 | 0.000 | 0.0139 | — |
| chris.raroque | 12 | 36 820 | 0.80 | 0.555 | 5.60 | 0.167 | 0.167 | 0.0068 | 0.0233 |
| decodingai.vs | 29 | 30 932 | 0.73 | 0.580 | 4.09 | 0.138 | 0.069 | 0.0126 | 0.0245 |
| ajsahni.ai | 12 | 28 067 | 0.95 | 0.512 | 1.64 | 0.250 | 0.000 | 0.0044 | — |
| justyn.ai | 30 | 19 173 | 0.91 | 0.524 | 0.72 | 0.133 | 0.033 | 0.0058 | 0.0179 |
| divyannshisharma | 27 | 18 948 | 0.78 | 0.561 | 1.47 | 0.185 | 0.037 | 0.0220 | 0.0361 |
| damini.knows | 14 | 12 678 | 0.64 | 0.609 | 3.06 | 0.143 | 0.000 | 0.0199 | 0.0314 |
| seb.ai | 42 | 8 344 | 0.74 | 0.574 | 14.55 | 0.119 | 0.024 | 0.0135 | 0.0320 |
| umangratani | 23 | 7 825 | 0.51 | 0.663 | 0.13 | 0.000 | 0.000 | 0.0013 | 0.0009 |
| nicholas.puru | 32 | 4 988 | 0.72 | 0.581 | 5.14 | 0.188 | 0.031 | 0.0029 | 0.0116 |
| omarmeski | 24 | 2 979 | 0.37 | 0.727 | 0.81 | 0.042 | 0.042 | 0.0040 | 0.0086 |
| seymourofdevin | 12 | 2 842 | 0.69 | 0.591 | 7.71 | 0.167 | 0.000 | 0.0048 | 0.0207 |
| brycenwood.ai | 24 | 2 572 | 0.42 | 0.705 | 1.39 | 0.000 | 0.000 | 0.0053 | 0.0071 |
| pritam.nagrale | 29 | 1 613 | 0.61 | 0.622 | 3.49 | 0.069 | 0.000 | 0.0023 | 0.0062 |
| automationatlas.co | 48 | 459 | 0.90 | 0.527 | 32.13 | 0.333 | 0.000 | 0.0000 | 0.0004 |
| hcmetellus | 25 | 410 | 0.68 | 0.597 | 0.47 | 0.200 | 0.000 | 0.0000 | 0.0000 |

**Who is actually worth studying.** Only the top seven rows combine a real audience (median play above
~19 000) with consistency. `divyannshisharma` and `damini.knows` are the two most interesting: they are
consistent **and** carry above-median share and save rates (0.0220 / 0.0361 and 0.0199 / 0.0314), which
means their audience both forwards and keeps their work on a predictable basis. `automationatlas.co` and
`hcmetellus` are consistent at a few hundred views — consistency without distribution, and not a model.

**The measurement trap.** Reels by CONSISTENT creators score *lower* on every creator-relative metric
(median robust_z 0.60, view_lift 0.65 across their 28 reels in the analysed set) than reels by
HIGH_VARIANCE creators (1.37, 2.38 across 240 reels), despite identical script shape — same median hook
(6.7 s), same spoken length (53.8 s vs 53.5 s), same words per second. `robust_z` and `view_lift` divide
by the creator's own spread, so steady creators produce small lifts from good reels. A 200× multiplier
from a HIGH_VARIANCE account and a 1.5× from a CONSISTENT one are not comparable quantities.

---

## 3. High-variance creators: the top 20 by dispersion

Creators with n≥8 in their baseline, sorted by CV of play. Their `top1` reel is the single best-performing
code in their known history.

| username | n | median play | CV | consistency | outlier share | top-1 code | top-1 lift | top-1 play |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| adamstewartmarketing | 31 | 6 415 | 4.77 | 0.173 | 0.161 | CrvV4zkMth4 | 218.8× | 1 409 789 |
| mikemeansbusiness_ai | 27 | 1 314 | 4.65 | 0.177 | 0.037 | DVRu6GlDNHO | 281.2× | 370 807 |
| dainikautomates | 27 | 3 619 | 4.53 | 0.181 | 0.148 | Db-3ruzKgzw | 256.8× | 932 923 |
| shrug.manny | 27 | 14 448 | 4.46 | 0.183 | 0.222 | DYQkKkxR3Et | **1 210×** | 17 496 130 |
| gannon.meyer | 26 | 10 939 | 4.36 | 0.187 | 0.154 | DZ5HURtsfez | 26.3× | 298 607 |
| shaurs.ai | 29 | 2 722 | 4.03 | 0.199 | 0.103 | Db8XYL7R_Ak | 108.0× | 296 794 |
| gregisenberg | 26 | 18 949 | 4.01 | 0.200 | 0.077 | Dal9I7KRA1L | 159.1× | 3 033 819 |
| jarvis_ai_spark | 22 | 7 544 | 3.94 | 0.202 | 0.091 | DZgBxjnBzMe | 207.2× | 1 570 719 |
| aiforbusinesses247 | 25 | 3 421 | 3.92 | 0.204 | 0.160 | DYuivWzSj5k | 32.2× | 113 697 |
| valeridoesai | 30 | 4 946 | 3.83 | 0.207 | 0.200 | DYC-x8DogOI | 399.4× | 1 980 128 |
| builders.central | 24 | 17 369 | 3.72 | 0.212 | 0.167 | DFK5FxWTUZG | 50.7× | 898 531 |
| davi.d_roberts | 24 | 3 862 | 3.59 | 0.218 | 0.208 | DKzbAvyoCMJ | 1 190× | 4 597 656 |
| albert.olgaard | 29 | 16 490 | 3.56 | 0.219 | 0.138 | DNgJb4Hs5FZ | 162.9× | 2 703 155 |
| loganwelbaum | 24 | 3 170 | 3.54 | 0.220 | 0.083 | Cq3Lkw1JaBv | **2 381×** | 7 550 238 |
| julian.goldie_ | 42 | 3 335 | 3.48 | 0.223 | 0.119 | DZPYR_0y4VV | 139.3× | 467 951 |
| sharmadhruveshh | 28 | 1 375 | 3.45 | 0.225 | 0.250 | DUJYKENjZc5 | 388.2× | 534 953 |
| buildingwithstring.com_ | 24 | 4 124 | 3.27 | 0.234 | 0.083 | DTCOU9DkRTG | 52.0× | 218 733 |
| kraya.ai | 32 | 28 122 | 3.21 | 0.238 | 0.031 | DcvrU4_xFjU | 37.8× | 1 090 634 |
| justinfineberg_ | 12 | 15 718 | 3.16 | 0.240 | 0.083 | C1CqwLLu-82 | 185.9× | 2 937 559 |
| lvl_aiautomations | 32 | 2 070 | 3.13 | 0.242 | 0.062 | DcPrAD8NqJ3 | 68.3× | 143 370 |

**How to read a multiplier from this table.** `loganwelbaum`'s 2 381× and `davi.d_roberts`'s 1 190× are
statements about a 3 170-view and a 3 862-view median, not about the reel. Per RULES.md the honest label
for these is "резонировало у своих" at best; at worst it is noise. A multiplier is interpretable only
alongside the creator's CV and baseline n.

---

## 4. Creators trending up and down

Latest per-creator OLS slope of ln(1+play) over the last ten posts (131 creators with a full window).

**Rising (top 12):** swapsays_wtf +0.373 · manthanjethwani +0.337 · gannon.meyer +0.198 ·
harshsharma_ai +0.197 · soojintech +0.174 · valeridoesai +0.167 · protips.ai +0.163 ·
gennaroautomates +0.162 · rence_ur_hands +0.159 · wokecoder +0.145 · kayvon.ai +0.144 · chase.h.ai +0.140.

**Falling (top 12):** kraya.ai −0.706 · jackroberts___ −0.428 · cashflow.automations −0.413 ·
andreapalacio −0.403 · kallaway −0.401 · michaelpkocher −0.349 · lukebuildsai −0.311 ·
petergriffin.ai −0.310 · publisity.ai −0.303 · davi.d_roberts −0.282 · sanji.chien −0.275 ·
techflowanjani −0.264.

Only `harshsharma_ai` appears on both the rising list and the CONSISTENT list. Note `manthanjethwani`
(+0.337): the account contributes two reels to the top of the pool below and is the clearest example of
demo-first, screen-evidenced work on a rising trajectory. The slope is a trend line over post index, not
a derivative, and one hit inside the window bends it (method §4); three snapshots only.

---

## 5. Best videos across creators

The single best reel per metric inside the analysed set (n=268):

| metric | reel | creator | value | context |
|---|---|---|---|---|
| highest view_lift | [DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/) | valeridoesai | **399.4×** | 1 980 128 plays on a 4 946 median |
| highest robust_z (tied at the +5.0 clip) | [DK9pFUjPQcx](https://www.instagram.com/reel/DK9pFUjPQcx/), [DLzPQzGNEmY](https://www.instagram.com/reel/DLzPQzGNEmY/), [DWCPx0PkQzA](https://www.instagram.com/reel/DWCPx0PkQzA/) and 22 others (25 rows at the clip) | — | 5.0 (clipped) | the clip means the magnitude is a floor, not a value |
| highest share rate | [Dc_tsSeAjBy](https://www.instagram.com/reel/Dc_tsSeAjBy/) | manthanjethwani | **61.3 / 1 000** | corrected 2026-09-12 against analysis_ready.csv; [Dbi-yxNgrhG](https://www.instagram.com/reel/Dbi-yxNgrhG/) (58.4) is third after DcvBtiNtbYO (59.2) |
| highest save rate | [DbO4zvJR1k8](https://www.instagram.com/reel/DbO4zvJR1k8/) | shrug.manny | **87.4 / 1 000** | terms-of-service writing, 209 121 plays |
| highest absolute play in the analysed set | [Dc9GZ0Gzf6o](https://www.instagram.com/reel/Dc9GZ0Gzf6o/) | anshmehra.in | 6 043 051 | corrected 2026-09-12; [DRXZJeHiAES](https://www.instagram.com/reel/DRXZJeHiAES/) (nateherkai, 3 349 555, 44.6× a 73 457 median, frames only) is second |
| best combined share+save | [DbO4zvJR1k8](https://www.instagram.com/reel/DbO4zvJR1k8/) | shrug.manny | 52.9 / 87.4 (140.3 combined) | corrected 2026-09-12; [Db9MT-axxcO](https://www.instagram.com/reel/Db9MT-axxcO/) (47.9 / 68.9) is third — both at low lift, resonance without reach |

`Db9MT-axxcO` is the instructive one: the best hi-intent rates in the corpus on a reel that barely beat its
author's median. RULES.md §6 already has a label for this case ("резонировало у своих"), and it is exactly
the kind of reference that a views-based filter would drop and a share/save filter would promote.

---

## 6. Reference-candidate pool (40 reels)

Selection rule: mean percentile rank across `robust_z`, `share_rate` and `save_rate` inside the
analysis-ready corpus, capped at **two reels per creator** so the pool is not three accounts. Every row
has a ta-v1 transcript parse and an fa-v1 frame read, so the hypothesis agent can pull a verbatim beat
quote and a frame description for any of them.

**How to use the columns.** `lift` is plays divided by that creator's accumulated median minus one, so
1.9 means "2.9× the author's own median". `share/1k` and `save/1k` are per 1 000 plays. **`cta` is
load-bearing**: a `comment_keyword` reel's share and save rates are inflated by the gate (it moves
comment rate ×23, save ×2.8, share ×1.8 while moving reach not at all), so compare gated reels only
against other gated reels. `rel` is the creator's reliability label — a big lift from a HIGH_VARIANCE
account is a weaker signal than a small lift from a CONSISTENT one. `visual` uses the coarse vocabulary
from `03-visual-patterns.md` (A = A-roll, SCR = screen, SPL = split, B = B-roll, TXT = text/graphic).

| # | code / url | creator | rel | play | creator median | lift | share/1k | save/1k | hook_type | pain | topic | visual | dur | cta | why a candidate, and for which function |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [DK9pFUjPQcx](https://www.instagram.com/reel/DK9pFUjPQcx/) | okaashish | HV | 427,950 | 10,798 | 38.6 | 42.5 | 58.2 | bold_claim | cost_money | free access | SCR>TXT>SCR>TXT>A | 39 s | gate | Top combined share+save in the pool. **hook** (money objection in one sentence), **rhythm** (four names in fast succession then a withholding turn). |
| 2 | [DYuivWzSj5k](https://www.instagram.com/reel/DYuivWzSj5k/) | aiforbusinesses247 | HV | 113,697 | 3,421 | 32.2 | 50.8 | 47.1 | other | manual_repetition | leadgen/CRM | SCR | 18 s | gate | 50.8 shares/1k from 59 words and no tool, step or number. **hook** only — an imagined morning in second person. |
| 3 | [DbO4zvJR1k8](https://www.instagram.com/reel/DbO4zvJR1k8/) | shrug.manny | HV | 209,121 | 14,448 | 13.5 | 52.9 | 87.4 | warning_fear | other | startups | A | 72 s | gate | **Highest save rate in the corpus.** **rhythm** — consequence-then-clause repeated identically four times; simultaneously scary and usable. |
| 4 | [Dc_TX1CttIc](https://www.instagram.com/reel/Dc_TX1CttIc/) | v.i.s.h.ai | HV | 562,094 | 22,421 | 24.1 | 31.7 | n/a | list_promise | keeping_up_with_ai | model news | A>SCR>A | 93 s | none | Ungated, so the rates are clean. **explanation** — agenda announced in nine seconds, each case labelled aloud, verdict earned. |
| 5 | [DZLDk9ySi-7](https://www.instagram.com/reel/DZLDk9ySi-7/) | aiforbusinesses247 | HV | 179,093 | 3,421 | 51.4 | 41.9 | 45.4 | result_first | manual_repetition | leadgen/CRM | TXT>SCR | 48 s | gate | **hook** + **explanation** — outcome first, mechanism second, pain list third, so the pain reads as reward. |
| 6 | [DUJYKENjZc5](https://www.instagram.com/reel/DUJYKENjZc5/) | sharmadhruveshh | HV | 534,953 | 1,374 | 388.2 | 36.6 | 46.3 | list_promise | manual_repetition | AI video | SCR>B>SCR | 33 s | gate | **topic** + **rhythm** — 33 s, four named tools, one per step, deliverable is a file. Beware the 1 374 median. |
| 7 | [DLzPQzGNEmY](https://www.instagram.com/reel/DLzPQzGNEmY/) | leadgenman | HV | 1,626,379 | 22,121 | 72.5 | 31.3 | 51.1 | identity_call | dont_know_where_to_start | agent building | SCR | 100 s | gate | **hook** — the time-swap framing ("instead of watching Netflix for the next two hours"). The identity-call shape is otherwise the corpus's worst. |
| 8 | [DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/) | valeridoesai | HV | 1,980,128 | 4,945 | 399.4 | 23.5 | 59.9 | result_first | cost_money | design/sites | SCR>A>SCR | 43 s | gate | Highest lift in the corpus. **hook**, **rhythm**, **screen_proof** — each step states its own benefit, no fear, no filler, 43 s. |
| 9 | [DbVq4mwz38L](https://www.instagram.com/reel/DbVq4mwz38L/) | heystevetan | HV | 439,974 | 13,009 | 32.8 | 27.9 | 54.0 | bold_claim | cost_money | free access | SPL>TXT>SCR>TXT | 54 s | gate | **proof** — fifteen seconds volunteering every catch before asking for anything. The cleanest objection handling in the pool. |
| 10 | [DVZGBgTk6zz](https://www.instagram.com/reel/DVZGBgTk6zz/) | sharmadhruveshh | HV | 419,000 | 1,374 | 303.8 | 34.8 | 46.2 | problem_call_out | missing_skills | Claude Code | A>SCR>A>SCR | 37 s | gate | **hook** — names an objection the audience has never heard said out loud ("nobody wants to touch terminal"), payoff repeats it back solved. |
| 11 | [DbVKVz0y8xo](https://www.instagram.com/reel/DbVKVz0y8xo/) | olivermerrick___ | HV | 70,474 | 9,734 | 6.2 | 33.0 | 57.6 | bold_claim | chaos_no_process | AI video | B | 87 s | question | **explanation** — thirty seconds killing the obvious answer before offering its own. Ungated CTA. The closest pain label to M2's territory. |
| 12 | [DZ-wujrTJ0u](https://www.instagram.com/reel/DZ-wujrTJ0u/) | kevinfremon | HV | 334,706 | 6,358 | 51.6 | 19.7 | 64.9 | result_first | dont_know_where_to_start | agent building | A>SCR>A | 172 s | follow | Second-highest save rate. **a_roll** + **screen_proof** — demo before the instructions and again after, so the reward bookends a long middle. |
| 13 | [DWCPx0PkQzA](https://www.instagram.com/reel/DWCPx0PkQzA/) | tenfoldmarc | HV | 1,074,517 | 7,471 | 142.8 | 20.7 | 57.3 | bold_claim | cost_money | design/sites | A>SCR>A | 67 s | gate | **transition** — the teach-then-automate reveal at 51 s: the whole recipe given away first, so the shortcut reads as a favour. |
| 14 | [DTCOU9DkRTG](https://www.instagram.com/reel/DTCOU9DkRTG/) | buildingwithstring.com_ | HV | 218,733 | 4,124 | 52.0 | 29.7 | 42.0 | demo_first | missing_skills | agency business | A>SCR>A | 34 s | question | **hook** + **cta** — every second does work: prompt, offer, objection killed, proof, dare. Ungated close ("roast my eyebrows in the comments"). |
| 15 | [DZU9x_1AY2t](https://www.instagram.com/reel/DZU9x_1AY2t/) | badarmunir_official | HV | 1,282,458 | 6,678 | 191.0 | 25.8 | 48.1 | result_first | quality_trust | Claude Code | SPL>SCR>A>SPL>SCR>SPL>SCR>TXT | 38 s | gate | **rhythm** — 37 s, no story, no intro, two identically shaped steps. The densest reel in the pool. |
| 16 | [DczDlj4qQjI](https://www.instagram.com/reel/DczDlj4qQjI/) | liamjohnston.ai | HV | 173,629 | 13,448 | 11.9 | 23.6 | 56.6 | result_first | time_waste | Claude Code | SPL>SCR | 63 s | gate | **proof** — the two objections that would stop this audience answered at 28 s and 43 s, exactly where a viewer would reject the idea. |
| 17 | [DZMqdC0Ronu](https://www.instagram.com/reel/DZMqdC0Ronu/) | wokecoder | HV | 194,409 | 7,281 | 25.7 | 41.6 | 45.3 | curiosity_gap | cost_money | free access | A>SCR | 69 s | gate | **hook** (retention clause) — but note the mechanism is withholding URLs on screen, which M2 cannot copy. Use for the hook shape only. |
| 18 | [Dc_cSU9TbCD](https://www.instagram.com/reel/Dc_cSU9TbCD/) | alassafi.ai | HV | 492,189 | 28,940 | 16.0 | 26.2 | 69.7 | bold_claim | time_waste | GitHub repo | SPL>A>SPL | 54 s | gate | Third-highest save rate. **rhythm** — feature detail ordered by increasing surprise with a rehook at 37 s, so a 54-second list never flattens. |
| 19 | [DZPYR_0y4VV](https://www.instagram.com/reel/DZPYR_0y4VV/) | julian.goldie_ | HV | 467,951 | 3,335 | 139.3 | 22.0 | 47.8 | bold_claim | cost_money | free access | A>B>SCR>A | 28 s | gate | **cta** — 27 s carrying one claim and one ask; the CTA occupies over a third of the runtime. The minimum viable structure. |
| 20 | [DVn-veaD7Ml](https://www.instagram.com/reel/DVn-veaD7Ml/) | codewithnishant | HV | 566,670 | 32,292 | 16.5 | 34.3 | 47.8 | bold_claim | cost_money | free access | TXT>A>B>SCR | 54 s | gate | **explanation** — promise stacked in the first fourteen seconds, then three steps, then the gate. Names specific model weights, which is what makes it read as a real recipe. |
| 21 | [DMQMNNHSJRF](https://www.instagram.com/reel/DMQMNNHSJRF/) | wokecoder | HV | 140,763 | 7,281 | 18.3 | 35.1 | n/a | other | time_waste | design/sites | A>SCR>TXT>SCR | 106 s | gate | **screen_proof** — the spoken hook is flat (a topic announcement) and the screen carries it; a volunteered lag warning near the end makes the recommendation read as honest. |
| 22 | [Dbi-yxNgrhG](https://www.instagram.com/reel/Dbi-yxNgrhG/) | manthanjethwani | HV | 240,255 | 35,050 | 5.9 | **58.4** | 58.9 | warning_fear | other | AI criticism | A>SCR | 57 s | gate | **Third-highest share rate in the corpus (61.3 and 59.2 are higher).** **topic** + **hook** — a universal account (Gmail), a bounded count (four settings), instructions too fast to follow live. |
| 23 | [DVtgbY8Av6A](https://www.instagram.com/reel/DVtgbY8Av6A/) | albert.olgaard | HV | 272,294 | 16,490 | 15.5 | 20.0 | 57.3 | list_promise | dont_know_where_to_start | Claude Code | TXT>SCR>A | 25 s | gate | 57.3 saves/1k from 84 spoken words. **cta** — the purest example of deliberate incompleteness, and therefore the clearest thing M2 must *invert*. |
| 24 | [DcUNlNvy6J9](https://www.instagram.com/reel/DcUNlNvy6J9/) | benkimball.ai | HV | 82,878 | 3,568 | 22.2 | 22.0 | 42.9 | bold_claim | cost_money | free access | SPL>SCR>SPL>SCR>A>SCR>A | 38 s | gate | **cta** — the ask is exactly the action the tool automates, so the viewer experiences the mechanism while converting. |
| 25 | [DX9kWTYzssE](https://www.instagram.com/reel/DX9kWTYzssE/) | vanshh_ai | HV | 99,558 | 8,982 | 10.1 | 41.3 | 36.1 | result_first | scaling_without_hiring | Claude Code | A>SCR | 61 s | dm | **proof** — most agent-dashboard reels stop at "here are my agents"; this one shows contribution per agent, which is what makes it forwardable. |
| 26 | [Dbs2JdJKUDd](https://www.instagram.com/reel/Dbs2JdJKUDd/) | dainikautomates | HV | 16,290 | 3,619 | 3.5 | 29.8 | 42.6 | contrarian | time_waste | AI video | SCR>A>SCR | 50 s | gate | **explanation** — pain block first, demo second, objection third: the three things stopping a switch, answered in the order they arise. Small numbers, clean structure. |
| 27 | [Dc_iv4YKCAh](https://www.instagram.com/reel/Dc_iv4YKCAh/) | kayvon.ai | HV | 1,123,071 | 19,615 | 56.3 | 17.1 | 52.9 | bold_claim | manual_repetition | GitHub repo | B>A>SPL>SCR | 50 s | gate | **transition** — install instructions land at second 16, *before* the benefits. An unusual and aggressive ordering worth testing once. |
| 28 | [Dbvfc67qpCQ](https://www.instagram.com/reel/Dbvfc67qpCQ/) | dainikautomates | HV | 22,626 | 3,619 | 5.3 | 28.2 | 41.1 | question | dont_know_where_to_start | leadgen/CRM | SCR>A>B>SCR | 42 s | gate | **hook** — the rare question hook that works because it targets the exact moment of failure (skill without clients), so the steps read as the missing map. |
| 29 | [DVaBP3wDAFE](https://www.instagram.com/reel/DVaBP3wDAFE/) | tenfoldmarc | HV | 533,528 | 7,471 | 70.4 | 22.4 | 38.4 | demo_first | keeping_up_with_ai | Claude Code | SCR>A | 90 s | gate | **a_roll** + **screen_proof** — two thirds demo, one third threat, gate last. Unusual order: earns the threat with a working artefact first. Contains profanity; copy the order, not the voice. |
| 30 | [DUduffIE5w5](https://www.instagram.com/reel/DUduffIE5w5/) | petergriffin.ai | HV | 1,284,003 | 30,836 | 40.6 | 18.8 | n/a | bold_claim | quality_trust | tool review | TXT>SCR>TXT | 58 s | gate | **Disqualified for content** (cloned cartoon voices, promotes an "uncensored" model) per RULES.md §2а. Kept in the pool only as the negative example of how the §2а check should fire. |
| 31 | [Dbd7VDgP9PR](https://www.instagram.com/reel/Dbd7VDgP9PR/) | codewithnishant | HV | 94,313 | 32,292 | 1.9 | 53.4 | 61.0 | bold_claim | dont_know_where_to_start | AI video | A>SCR>A>SPL>SCR>A | 67 s | gate | Second-highest share rate on a modest lift — a "resonated with its own audience" case. **explanation** — answers the distribution question at the exact midpoint. Income framing; do not copy. |
| 32 | [Db9MT-axxcO](https://www.instagram.com/reel/Db9MT-axxcO/) | shrug.manny | HV | 37,791 | 14,448 | 1.6 | 47.9 | **68.9** | question | manual_repetition | careers | A>SCR>A>SCR>A | 50 s | gate | Third-best combined share+save in the corpus (DbO4zvJR1k8 140.3, Dbi-yxNgrhG 117.3 are higher) at only 1.6× lift. **rhythm** — result at 3 s, three steps in thirty, CTA at forty-three. Simultaneously a story and a procedure. |
| 33 | [DYSKnz3TxPZ](https://www.instagram.com/reel/DYSKnz3TxPZ/) | vanshh_ai | HV | 170,732 | 8,982 | 18.0 | 32.1 | 33.1 | result_first | keeping_up_with_ai | agent building | A>SCR | 71 s | dm | **topic** — names metrics nobody else names (AEO, GEO, citation rate, AI readability). Naming the measurement is what makes it forwardable. |
| 34 | [DcoE5ZsK4I7](https://www.instagram.com/reel/DcoE5ZsK4I7/) | damini.knows | **CONSISTENT** | 30,192 | 12,677 | 1.4 | 36.1 | 62.4 | bold_claim | missing_skills | design/sites | A>SCR>SPL>SCR | 49 s | gate | **The most trustworthy row in the pool**: a CONSISTENT creator with above-median share *and* save. **explanation** — the whole workflow fits in 45 s with the demo as the proof, so nothing is taken on trust. |
| 35 | [DaGTeJNN1GR](https://www.instagram.com/reel/DaGTeJNN1GR/) | aiwithremy | HV | 298,226 | 28,959 | 9.3 | 30.2 | 36.1 | number_stat | cost_money | how to work with AI | A>SCR>B>A>B>A | 42 s | gate | **hook** + **b_roll** — the number in the first four seconds, the mechanism by twenty-five, and the location itself is the visual hook, reused as the closing line. |
| 36 | [DZQZOVhgNvK](https://www.instagram.com/reel/DZQZOVhgNvK/) | jasoncooperson | HV | 124,032 | 24,492 | 4.1 | 25.0 | 50.2 | bold_claim | dont_know_where_to_start | agent building | A>SPL | 81 s | gate | **proof** — proof in the first fifteen seconds, output before architecture, numbered phases after; the viewer never holds an unanswered question. |
| 37 | [DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/) | edhillai | HV | 451,491 | 8,010 | 55.4 | 23.3 | 36.5 | demo_first | scaling_without_hiring | voice agents | SCR | 68 s | **none** | **Best overall template in the pool.** Ungated, screen-first, the artefact speaks the first four words, an explicit 1.8-second rehook at 32 s, then the same build replayed against a real call. **hook**, **explanation**, **proof**, **rhythm**. |
| 38 | [Dct6Op3n6Zd](https://www.instagram.com/reel/Dct6Op3n6Zd/) | valeridoesai | HV | 90,775 | 4,945 | 17.4 | 17.6 | **75.9** | number_stat | tool_overload | GitHub repo | SPL | 38 s | gate | Second-highest save rate in the whole corpus. **rhythm** — countdown with escalating scale keeping retention to the last item, which sits immediately before the CTA. Held split screen; do not copy the layout. |
| 39 | [DbbA7wwTIZ8](https://www.instagram.com/reel/DbbA7wwTIZ8/) | heystevetan | HV | 294,197 | 13,009 | 21.6 | 24.6 | 30.5 | bold_claim | dont_know_where_to_start | agency business | SPL>B>TXT>B>TXT>B | 70 s | gate | **cta** — narrows an enormous market claim down to one industry, one job, one business and one month. The best example of making a big claim actionable. |
| 40 | [Da73u-0ysYU](https://www.instagram.com/reel/Da73u-0ysYU/) | umangratani.ai | HV | 1,160,674 | 17,987 | 63.5 | 41.4 | 28.1 | bold_claim | cost_money | free access | SPL>A>SCR>A | 57 s | gate | **transition** — three numbered steps under forty seconds, then a bonus that beats the original promise in the last ten, so the payoff arrives *after* the method. |

### Pool composition

| | count |
|---|---:|
| reels | 40 |
| distinct creators | 30 |
| CONSISTENT creators represented | 1 (damini.knows) |
| carrying a `comment_keyword` gate | 33 |
| ungated — `none` 2, `question_to_audience` 2, `dm` 2, `follow` 1 | 7 (rows 4, 11, 12, 14, 25, 33, 37) |
| containing a screen state | 34 |
| screen-first opening | 9 (rows 1, 2, 6, 7, 8, 26, 28, 29, 37) |
| containing `A > SCR > A` | 9 (rows 4, 10, 12, 13, 14, 24, 31, 32, 40) |
| median duration | 54 s |
| flagged disqualified on content (RULES.md §2а) | 1 (row 30) |

### Three warnings for the hypothesis agent

1. **33 of 40 rows are gated.** Their share and save rates carry the gate's inflation (×1.8 and ×2.8).
   The ungated rows — especially **DNA7-d3o5sQ**, **Dc_TX1CttIc**, **DbVKVz0y8xo** and **DTCOU9DkRTG** —
   are the only ones whose hi-intent rates can be read at face value, and they should be weighted higher
   for that reason alone.
2. **Only one row is from a CONSISTENT creator.** This is a consequence of the selection rule, not a
   choice: creator-relative metrics systematically favour high-variance accounts (§2). Treat a 300×
   from a 1 374-view median as a curiosity and a 1.4× from a steady 12 677-view median as a finding.
3. **One row must not produce a card.** Row 30 (`DUduffIE5w5`, petergriffin.ai) uses cloned cartoon
   voices and promotes an uncensored model — a double failure of RULES.md §2а. It is in the table so the
   suitability check has something to fire on; `deepdives.suitable` is still NULL for every code in the
   database, which is the compliance gap the existing-cards audit already recorded.
