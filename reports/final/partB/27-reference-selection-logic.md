# 27. Reference Selection Logic

**What this chapter is.** Selection is where the analysis becomes an instruction, and it is the place a
measurement error turns into a production error. This chapter states the rules that govern which
competitor reel may be used as a reference, how they are implemented in the engine, and what the
completed selection for this wave looks like. The per-hypothesis tables live in
`reports/analysis/09-reference-selection.md` and in the card book; **41 references across 10 selected
hypotheses, drawn from 27 distinct reels, ingested into `hypothesis_refs` with 0 rejected.**

## The four selection rules

**1. Consistent creators and high-variance creators are not selected the same way.** Only **17 of 132**
creators are CONSISTENT (CV < 1 and n ≥ 8); **115 are HIGH_VARIANCE** [I-23]. A CONSISTENT creator may
contribute several structural references, because their output is predictable and a modest lift from
them is a finding. A HIGH_VARIANCE creator may contribute only reels that clear a meaningfulness floor
(view_lift ≥ 0.5 **or** robust_z ≥ 1.5), and their multipliers may never be read as evidence that an idea
travels. The arithmetic reason is chapter 11's measurement trap: reels by CONSISTENT creators score
*lower* on creator-relative metrics (median robust_z 0.60, view_lift 0.65) than reels by HIGH_VARIANCE
creators (1.37, 2.38) **with identical script shape**, because both metrics divide by the creator's own
spread. Wherever a large multiplier rests on a tiny author median — `DUJYKENjZc5` at 388× on a
1 374-view median, `DVZGBgTk6zz` at 304× on the same, `DZLDk9ySi-7` at 51× on 3 421 — the reference is
used for cadence or ordering only, and the reason field says so.

**2. Gated and ungated rates are not the same quantity.** The comment-keyword gate moves comment rate
×23, save ×2.8 and share ×1.8 while moving reach not at all [I-12], and **33 of the 40 pool rows carry
one**. `cta_type` must therefore be held constant in any comparison of hi-intent rates, or recorded on the
card so the reader can hold it constant. The seven ungated pool rows were weighted up and six are used;
where a gated reel is used, the reason states which of its numbers can be read at face value.

**3. Cross-creator best video, not best account.** The pool is built on **mean percentile rank across
`robust_z`, `share_rate` and `save_rate` inside the analysis-ready corpus, capped at two reels per
creator** — 40 reels from 30 creators — so that the reference set is a survey of the niche rather than a
portrait of three accounts. The cap is the only thing standing between this method and a pool dominated
by whichever account happened to have a good fortnight.

**4. Selection is hypothesis-specific and function-based.** A reel is never adopted whole. It is attached
to one hypothesis for **one named function** from the `hypothesis_refs` vocabulary — `topic`, `hook`,
`pain`, `explanation`, `proof`, `cta`, `a_roll`, `b_roll`, `split`, `screen_proof`, `rhythm`,
`transition` — with the verbatim beat that makes it useful, the real beat and scene ids, the performance
behind it, and an explicit statement of **what is borrowed structurally against what changes** for M2's
positioning. A reel may serve several hypotheses only with a *different* function; no `(code, function)`
pair may appear twice.

## How the rules are implemented

| layer | mechanism |
|---|---|
| candidate pool | `score.py` ranks reels against their own author inside an age band (7/30/90 days), excluding the focal row from its own baseline, minimum baseline 5 videos, `Z_CLIP` ±5, `LOG_MAD_FLOOR` 0.10 |
| freshness and format | `cards.py`: `FRESH_DAYS = 14`; three independent selections — M2 Radar (2 slots, ranked on `resh_1k`), M2 Builds (2 slots, `save_1k`), M2 Teardown (1 slot, `save_1k`) |
| suitability | RULES §2а check **after storyboarding, before the card is written**: not about AI in business processes; other people's characters, cloned voices or IP; promotion of a model-restriction bypass |
| storage | `hypothesis_refs (hypothesis_id, code, function, reason, useful_beat_ids_json, useful_scene_ids_json, performance_json, transformation)`, primary key `(hypothesis_id, code, function)` — the schema itself enforces rule 4 |
| ingest | `engine/ingest_insights.py` loads `data/analysis/hypothesis_refs.json`; a row failing validation is rejected, never silently repaired |

Two defects in the current implementation are worth naming because they are fixable and consequential.
**`cards.py` ranks on `resh_1k` and `save_1k` with no `cta_type` guard**, so with 59 % of the analysed
corpus gated it part-ranks DM funnels rather than ideas (chapter 18). And **`deepdives.suitable` is NULL
for every code except four 2026-09-01 rejections (4 of 282 deep-dive rows; NULL on all 23 drafted cards' sources)**, so the RULES §2а compliance record does not exist anywhere in the database even
though the rule has been on paper since 1 September.

## What the completed selection looks like

| | value |
|---|---|
| hypotheses with references | 10 |
| references written | **41** (4 per hypothesis, 5 for H-11) |
| distinct reels used | **27** — 9 carry two functions each, 18 carry one |
| reels from CONSISTENT creators | **1** (`DcoE5ZsK4I7`, damini.knows) |
| ungated reels used | 6 of the 7 available |
| gated reels used | 21 of 27 |
| reels read and rejected | 13, of which **3 on content grounds** under RULES §2а |

**Transcript reading — the rules doing visible work.** The two highest-rate reels available were both
refused. [DK9pFUjPQcx](https://www.instagram.com/reel/DK9pFUjPQcx/) carries the best combined hi-intent
rates in the pool (42.5 shares and 58.2 saves per 1 000) and is excluded because its solution beat says
**"First, open route up with over 60 free api keys, you can even try the Uncensored ones."**
(8.9–31.0 s) — promotion of a model-restriction bypass, RULES §2а clause 3.
[DUduffIE5w5](https://www.instagram.com/reel/DUduffIE5w5/) is structurally the strongest reel in its batch
and is excluded on two §2а clauses at once. **The rule has to fire on the numbers, not in spite of
them**, and these two rejections are the evidence that it does.

**Visual reading.** Layout is now part of selection, and it changes outcomes.
[Dct6Op3n6Zd](https://www.instagram.com/reel/Dct6Op3n6Zd/) carries the corpus's second-highest save rate
(75.9 per 1 000) and was rejected partly because it is held in `SPLIT_SCREEN` for all 37 samples — the
only roll share with a negative association to `robust_z` clearing p<0.05 [I-10] — and its countdown
rhythm is already better represented without the layout problem. This is the direct fix for the defect
chapter 23 records: **9 of main's 23 legacy source reels opened on split screen**, because the old
selector was blind to visual structure. Every reference now carries its `first_frame_type` and coarse
`visual_sequence`, and each hypothesis carries a planned visual grammar (predominantly `SCR>A>SCR>A` or
`A>SCR>A`, and no split screen anywhere).

## What the selection is weak on

Four weaknesses are recorded rather than hidden. **One CONSISTENT creator in 27** — a consequence of
creator-relative metrics favouring high-variance accounts, which means most quoted lifts describe a
creator's spread rather than a reel; read the rates, not the lifts. **Twenty-one of 27 reels are gated**,
so their save and share rates carry a known inflation. **No reference shows a failure, because none
exists** — `before_after` is the second-rarest proof type (n=5) and not one reel in 266 shows its author's
build breaking, so for the four hypotheses that turn on exactly that the reference set supplies grammar
and never precedent. And **every scene id comes from a nine-sample interpolation** with
`boundary_confidence = 'low'`: use scene ids to locate a moment, never to plan a cut.

## Strategic implication

Three changes to make before the next card run. **(1) Recompute every headline multiplier against the
accumulated creator median and carry the baseline `n`, `robust_z`, `percentile_in_creator`,
`outlier_status` and `reliability` onto the card** — two of 23 legacy cards had materially wrong headline
numbers without it. **(2) Record `cta_type` on every reference and compare hi-intent rates only within
the same `cta_type`.** **(3) Populate `deepdives.suitable` before an angle is written.** Beyond the fixes,
the standing rule is the one the function vocabulary encodes: **borrow a beat, never a topic, and write
down the transformation** — which is RULES §1.2 made executable.

**Confidence: RELIABLE** for the mechanics (schema, ranking code and ingest counts are direct
observations of the engine). **PROBABLE** for the evidence behind individual rules — rule 1 rests on
I-23, rule 2 on I-12 (both RELIABLE), while the visual constraint behind the layout check rests on
I-10 at p=0.044. **INSUFFICIENT** as a claim that this selection produces better reels: `our_posts` is
empty, nothing has been shot or published, and the loop that would test it does not yet have a single
data point.
