# 25. Transcript-to-Frame Alignment

**Denominators.** The alignment pass checks **1 527 beat boundaries** across **264** codes — every beat in
the corpus, each with a scene id attached. A boundary counts as **cut-aligned when a scene in the same
code starts within 0.3 s of the beat's `start_s`**. Scenes come from the legacy nine-sample grid (a run of
consecutive samples with the same `frame_type`, `boundary_confidence = 'low'`), so the resolution of this
test is bounded by that grid and not by the editors' actual work. The 264 codes here are the beat-parsed
set, not the full 268.

## The measurement

| | value |
|---|---:|
| beat boundaries checked | **1 527** |
| beats carrying a scene id | 1 527 (100 %) |
| codes with alignment computed | **264** |
| boundaries with a scene start within 0.3 s | **55** |
| **semantic boundary cut rate** | **0.036 — 3.6 %** |
| codes with **no** aligned boundary at all | **215 of 264 (81 %)** |

| performance of reels with ≥1 aligned boundary (n=49) vs none (n=215) | aligned | none | p |
|---|---:|---:|---:|
| median `robust_z` | 1.45 | 1.25 | 0.603 |
| median share rate | 0.0168 | 0.0149 | 0.28 |
| median save rate | — | — | 0.64 |

Two statements, and the order matters. **Descriptively: editors in this niche do not cut on meaning.**
Fewer than four beat boundaries in a hundred coincide with a visible shot change, and four reels in five
contain no coincidence at all. **Evaluatively: nothing follows from that**, because reels that do align
show no advantage on any metric, and the null itself sits on a measurement floor [I-21].

## Why the honest reading is a null, not a finding

With nine samples over a 54-second median runtime, the average gap between observable scene boundaries is
roughly six seconds, while the alignment window is 0.3 seconds — twenty times narrower than the
measurement's own resolution. A perfectly beat-cut reel edited at, say, one cut every four seconds would
still register almost no alignments, because eight of its nine sampled boundaries fall wherever the
sampler happened to land rather than where the editor cut. The 3.6 % is therefore **at least partly an
artefact of the grid**, and the correct label is INSUFFICIENT rather than "editors do not do this".

The same reasoning cuts the other way for the performance test. A null computed on a floor is not evidence
of absence: it is evidence that the question was asked at the wrong resolution. Answering it properly needs
the `scene-v1` detector (real scene intervals, `cuts = scenes − 1`) rather than the count-only legacy
metric, over a corpus that has not been pre-selected for strength.

## What the aligned reels look like, for what it is worth

The 49 codes with at least one alignment are not a coherent group. They include
[DWCPx0PkQzA](https://www.instagram.com/reel/DWCPx0PkQzA/) (1 aligned of 5 checked), the corpus's
best-evidenced `A > SCREEN > A` reel, whose spoken payoff — **"Normandy would take you four steps to
create beautiful websites like this But I've created a github repo where all you need to do is copy one
line of code"** (47.4–58.5 s) — does begin as the frame returns from the screenshot to the presenter's
close-up. They also include [DUduffIE5w5](https://www.instagram.com/reel/DUduffIE5w5/), the one reel in
the reference pool that is disqualified on content grounds under RULES.md §2а. Alignment is not a quality
signal; at this resolution it is close to a coin toss.

Conversely, several of the strongest reels in the corpus register **zero** aligned boundaries:
[DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/) (0 of 7),
[DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/) (0 of 4),
[DLzPQzGNEmY](https://www.instagram.com/reel/DLzPQzGNEmY/) (0 of 6),
[DZgBxjnBzMe](https://www.instagram.com/reel/DZgBxjnBzMe/) (0 of 2). DNA7-d3o5sQ is the most instructive:
its **1.8-second re-hook — "But how about the results?" (32.0–33.8 s)** — is exactly the beat a
meaning-cut editor would cut on, and fa-v1 records a hard cut between samples 3 and 4 of that reel. The
alignment test does not see it because neither the beat boundary nor the cut lands where the sampler
looked. That single case is the clearest available illustration of what the 3.6 % is measuring.

**Visual reading.** The related free-text field `visual_to_script_sync` — fa-v1's own prose judgement of
whether the pictures match the words — was **never tested against performance**, because it holds free
prose rather than a category. Its per-reel content is often precise (DNA7-d3o5sQ: "Captions across the
samples … read as fragments describing the assistant routing a spoken request to an AI agent that books an
appointment in Google Calendar, matching the post caption exactly"), and it is usable when reading a single
reference by hand. It is not usable as a variable, and no statistic in this report rests on it.

## Strategic implication

**(1) Do not spend M2's editing budget aligning cuts to script beats.** There is no measured return, and
under the one-take rule the question does not arise at all — a reel with one speaker change has one cut to
place, and it should be placed where the speaker changes. **(2) Do not read the 3.6 % as a craft
criticism of the niche** and never publish it as one; it is a statement about a nine-sample grid.
**(3) If M2 ever wants this question answered** — for instance to decide whether a screen insert should
land on the solution beat or before it — it must be answered on the new detector, and the decision until
then should follow chapter 22's storyboard (screen enters with the mechanism, face returns for the payoff)
because that pattern *does* have measured support.

**Confidence: INSUFFICIENT**, and deliberately so. Both the 3.6 % alignment rate and the null performance
result (robust_z 1.45 vs 1.25, p=0.603) are provisional: the 0.3-second window is twenty times finer than
the ~6-second resolution of the nine-sample scene grid, 215 of 264 codes contribute a zero by
construction, and the analysed corpus is pre-selected for strength. Nothing in this chapter may be quoted
as a fact about how this niche is edited, and nothing here licenses a causal claim.
