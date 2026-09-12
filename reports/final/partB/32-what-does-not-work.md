# 32. What Does Not Work

**Three different kinds of "does not work" appear below, and conflating them would be an error.**
**(a) Measured negatives** — the association runs the wrong way. **(b) Measured nulls** — the feature was
tested at adequate power and nothing was found. **(c) Unmeasurable** — the instrument cannot answer, so no
claim is permitted in either direction. Denominators as always: 3 211 for metric-only, 268 for
script-and-visual, 266/264 for semantics and beats, 295 for frames, 9 fixed samples per reel. And the
standing caveat cuts hardest here: a **null** measured inside a corpus pre-selected for strength is weaker
evidence of absence than it looks [I-01].

## (a) Measured negatives

| what | evidence | confidence |
|---|---|---|
| **Split screen** — the niche's most-used arrangement | 22.3 % of all 2 645 frames, 73 of 266 opening frames, 99 reels, 51 creators; any split state median robust_z **1.03 vs 1.43** (p=0.044); pure split (n=27, 18 creators) view_lift **0.94** vs corpus 2.03; the one positive pooled link (`split_share` → save_rate +0.193) collapses under normalisation (cn +0.036) | PROBABLE |
| **Setup-first openings** — series preambles, "if you are a…", story openings | identity_call + story_open + problem_call_out, n=39, 31 creators: median robust_z **0.67** / view_lift **0.80** vs 1.36 / 2.25 (p=0.002 on both); `identity_call` alone 0.41 view_lift (n=9) | PROBABLE |
| **Questions in the script** | `questions_n` → save_rate **−0.229** (p=0.00031, cn −0.162); questions per 10 s −0.235 (cn −0.186); rhetorical questions −0.186 (cn −0.151); question hooks save 0.0130 vs 0.0284 | **RELIABLE** |
| **First person as the subject of the payoff** | `lex_first_person_n` → save_rate **−0.180** (cn −0.124) | **RELIABLE** |
| **Urgency and fear vocabulary** | urgency → view_lift −0.164 (p=0.0072); urgency → share_rate −0.150 (cn **−0.180**, survives); fear → share_rate −0.157 (cn −0.086, survives); weak quartile uses 2 urgency words vs 1 | PROBABLE |
| **Income framing** | the 71 of 266 reels (27 %) framing the outcome as money run at median view_lift **1.19 vs 2.12**; save rate unchanged (0.0286 vs 0.0264) | PROBABLE |
| **More face on camera** | `a_roll_share` → share_rate −0.156 (p=0.011, cn −0.094, survives) | PROBABLE |
| **Frameworks and "how to think about it"** | `framework_mental_model` save rate **0.0135** (n=25) against `resource_handoff` 0.0429; the "certainty" desire carries save **0.0140 vs 0.0282** (n=19, p=0.017) | PROBABLE |
| **News without a work decision** | `announcement_news` n=30, 21 creators: view_lift 1.29, robust_z 0.96; model-news topic save rate **0.0097**, roughly a third of the corpus median | PROBABLE |
| **Stacking asks** | [Da3uSkrNjli](https://www.instagram.com/reel/Da3uSkrNjli/) runs four asks in its last twenty seconds and lands at view_lift **−0.05** | INSUFFICIENT (n=1) |

## (b) Measured nulls — features that simply do not separate

**Of 115 numeric features, none separates the top from the bottom `robust_z` quartile at p<0.01.** The
list of things that show nothing is longer than the list of things that do: duration (|rho| ≤ 0.09 over
3 211 reels; strong 56.9 s vs weak 58.0 s, p=0.981) · spoken length (198 vs 179 words, p=0.333) · words
per second (3.53 vs 3.45, p=0.444) · hook seconds (7.6 vs 7.0, p=0.162) · cuts and cuts per minute (7.06
vs 6.75, p=0.420) · scene count (4 vs 3, p=0.110) · average scene length · A-roll share (0.2222 both,
p=0.573) · B-roll share · split share (0.0 both, p=0.628) · caption density (1.0 both, p=0.418) ·
average sentence length · every lexical-diversity measure against reach · `proof_s`, `problem_s` and
`explanation_s` against reach.

**The comment gate is the most consequential null.** It moves comment rate ×23, save ×2.8 and share ×1.8
— and reach not at all: view_lift 2.08 vs 1.72 (p=0.58), robust_z **1.2475 vs 1.2481** (p=0.63). Nothing
in reach is bought by it, which is why banning it costs M2 nothing.

**A null that vanished on retest** deserves its own line: nine pooled associations disappear under creator
normalisation, including `info_density` → save_rate (+0.303 → cn +0.132), `specificity` → save_rate
(+0.237 → +0.047) and `solution_s` → save_rate (+0.343 → **−0.217**, sign flip). These describe which
creators post what, not what videos do.

## (c) Rules people expect, which this data does not support

**The 0–3 second hook rule.** Median hook is **6.7 s**; only **6 %** of reels close inside 3 seconds; hook
duration correlates with nothing (p ≥ 0.23 on all four metrics). An audit scoring hooks against a
three-second rule is measuring something this niche does not do — which is why the 8 September criticism of
Max's card set on hook timing **should be withdrawn**: the rule was wrong, not the scripts [I-03].

**A fixed scene template.** Max's fixed 60 s / 7-scene template is not wrong about duration (duration
predicts nothing) but is wrong to be fixed: coarse visual states range from 1 to 8 with median `robust_z`
between 1.14 and 1.63 and no trend. Fixing the scene count holds constant the one thing that should vary
with the topic.

**"Cut faster."** No signal in any metric — and the metric itself, `ffmpeg_scene_0.35_count_only`, is a
scene-score threshold count, not shot detection. 38 of 282 rows report zero. **No M2 output may quote a
cut rate from it.**

**Cutting on script beats.** Only **55 of 1 527** beat boundaries (3.6 %) have a scene starting within
0.3 s, 215 of 264 reels have none, and aligned reels show no advantage (robust_z 1.45 vs 1.25, p=0.603).
With a 0.3-second window against a ~6-second sampling resolution this is a measurement floor, so the honest
label is **INSUFFICIENT**, not "editors do not do this".

## What the failures sound like

[DaDn5L-xKWi](https://www.instagram.com/reel/DaDn5L-xKWi/) opens **five** loops — "Five AI image tricks
top realtors are using to sell listings faster" (0.0–6.4 s) — and closes them in five identically shaped
ten-second blocks; the reel flattens because nothing escalates.
[DcbnTAtxb8C](https://www.instagram.com/reel/DcbnTAtxb8C/) describes three departments in three
grammatically identical sentences ("Marketing researches what's going on… Sales takes a lead from our
CRM… Customer handles onboarding…", 13.4–37.8 s) and never names a person responsible for anything.
[DXb8P08Dati](https://www.instagram.com/reel/DXb8P08Dati/) spends its first sentence on the programme
rather than the subject and sits at `robust_z` −1.04, the bottom of this corpus, from a creator whose
demo-first reel sits at +4.69.

**Visual reading.** [DcnHtUGS_tE](https://www.instagram.com/reel/DcnHtUGS_tE/) is the visual failure mode
in one frame: a held split screen with an AI-generated cinematic clip above a reacting host. It reached
**65×** its author's median and carries share rate **0.0016** and save rate **0.0005** — the lowest
hi-intent rates in the top thirty by reach. Attention without intent, and the geometry is why: the thing
the viewer is asked to believe never gets the full frame.

## Strategic implication

Ban four things outright from the M2 template — **split screen, setup-first openings, questions in the
script, and the comment gate** — and drop the urgency and income registers after the hook. Stop enforcing
three rules that the data does not support: the 0–3 second hook, the fixed scene count, and any editing
target. And write the nulls into the card review as *permissions*: a reviewer may not reject a script for
being 43 seconds or 92 seconds, for having three cuts or eleven, or for speaking at 3.1 or 3.9 words per
second, because none of those separates anything in a corpus of 3 211 reels.

**Confidence.** RELIABLE for the question and first-person negatives, for the gate's reach null and for the
115-feature quartile null. PROBABLE for split screen (p=0.044), setup-first (p=0.002 but no
creator-normalised test exists for a categorical median), urgency, income framing and A-roll share.
INSUFFICIENT for the alignment result and for any single-reel example. Absence of evidence here is not
evidence of absence: the corpus is 8.3 % of the database and pre-selected for strength.
