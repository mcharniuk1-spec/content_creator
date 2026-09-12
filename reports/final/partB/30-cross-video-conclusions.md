# 30. Cross-Video Conclusions

**What this chapter does.** Chapters 11–29 each answered one question about one layer. This chapter states
what holds when the layers are read together; every figure below has already appeared with its
denominator. Those remain **n=3 211** for metric-only statements, **n=268** for anything joining script
and visuals, **266/264** for semantic and beat statements, **295** for frames, and **9 fixed samples** per
reel throughout.

## 1. Format is not the lever, and the negative result is the strongest finding of the wave

Of **115 numeric features tested**, **none separates the top from the bottom `robust_z` quartile at
p<0.01** and only seven reach p<0.05, two of them in the counter-intuitive direction. Of **460 Spearman
pairs**, 13 are RELIABLE and **none is against `robust_z`**. Duration, spoken length, words per second,
hook duration, cut rate, scene count, A-roll share, split share and caption density are flat on both
tests [I-22].

The negative was obtained under conditions that should have made a difference *easier* to find: the
analysed corpus is the top of `score.py`'s ranking (median `robust_z` +1.26 against 0.00 for all 3 211),
so the "weak" quartile still beats its own authors' medians at about +0.6. A comparison between the
strongest and the merely strong found nothing structural. **Once a reel is competently made, what remains
is subject, specificity and evidence.**

## 2. What a video controls is the save and the share, not the view

Eleven of the 13 RELIABLE correlations (ten distinct features; one is counted twice) are save-rate correlations, one share rate, one view lift, none
`robust_z`. Share and save themselves correlate at **+0.781** across 2 899 reels — close to one axis
rather than two — with share the marginally better discriminator (**×2.62** against **×2.09** for the 375
HIGH outliers). Reach is driven by factors this dataset does not contain, and any promise that a script
change will move it is unsupported.

## 3. The one production instruction with RELIABLE evidence is: put a screen on camera

`screen_share` → share_rate **+0.203** (p=0.00085, creator-normalised +0.129) and any-screen-present →
save_rate **+0.210** (cn +0.213) are the only visual findings that clear the RELIABLE bar. Opening on the
screen rather than the face is worth roughly **half again the forwarding rate** (0.0213 against 0.0140),
and — uniquely in this wave — the creator-normalised correlation (**+0.285**) is *stronger* than the
pooled one (+0.208), which means the effect holds inside individual creators' own output [I-08, I-09].
Its mirror is equally consistent: more face is weakly worse (`a_roll_share` → share_rate −0.156,
cn −0.094, survives), and the niche's most-used arrangement, split screen (22.3 % of all frames), is its
least-rewarded (robust_z 1.03 against 1.43, p=0.044).

## 4. Three findings converge on the same sentence from three directions

| direction | measurement |
|---|---|
| lexical | `lex_platforms_n` → save_rate **+0.331** (cn +0.173), `lex_entities_distinct` → view_lift **+0.161** (cn **+0.198**) |
| categorical | `resource_handoff` save rate **0.0429** against `framework_mental_model` **0.0135** |
| linguistic | sentences end on a destination — "right now" 13, "for free" 11, "on github" 10 — not on a conclusion |

All three say: **name the destination and hand over the object.** The audience saves what it intends to
use and does not save what it is asked to believe — the desire category "certainty that a thing actually
works" carries save rate **0.0140 against 0.0282** (n=19, p=0.017, negative). This is the strongest
cross-layer agreement in the report, and it holds across a lexical correlation, a categorical median and a
phrase count computed independently of one another.

## 5. The corpus's shape is four moves, and its two structural omissions are M2's opening

The modal ordering is **HOOK > EXPLANATION > PAYOFF > CTA** (27 of 264, 10 %); the hook opens 259 of 264
reels and a CTA closes 215. Explanation is present in 79 % of reels and takes 38 % of the speech. Against
that, **only 24 % of reels state a problem at all** and **half carry no proof beat**; `before_after` is the
second-rarest proof type (n=5) and **not one reel in 266 shows its author's own build failing.** Those two
omissions are exactly what POSITIONING.md §8 requires of M2 — friction, and an AI boundary with real
evidence — which means M2's differentiation is structural rather than stylistic, and has to be paid for in
seconds taken out of the mechanism block.

**Transcript reading across videos.** The same three sentences recur at the top of the corpus regardless
of topic: a result with a quantity in it, a step naming a specific product, and a payoff restating what
changed. [DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/): "I just built a website that looks
like it costs $10,000 with literally one line of code and honestly the whole thing took Claude about two
minutes." [DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/): "This agent understands your goal
but needs data. Therefore, it uses Google Calendar to check your schedule and Google Sheets to save any
details." [DWCPx0PkQzA](https://www.instagram.com/reel/DWCPx0PkQzA/): "But I've created a github repo
where all you need to do is copy one line of code." Result, named destination, object handed over. The
reels at the bottom of the corpus have none of the three:
[DXb8P08Dati](https://www.instagram.com/reel/DXb8P08Dati/) opens on the series ("Day one of two AI tips…",
`robust_z` −1.04) and [DaDn5L-xKWi](https://www.instagram.com/reel/DaDn5L-xKWi/) opens five loops and
closes them in five identically shaped blocks.

**Visual reading across videos.** The visual vocabulary fragments so badly — 295 reels, **206 distinct
sequences**, median sequence occurring once — that only the coarse four-way collapse supports any claim.
On that collapse the picture is stable across every chapter: full-frame screen up, face down, split
screen down, and one arrangement (`A > SCREEN > A`, 39 reels across 32 creators) carrying share rate
0.0213 against 0.0140. Everything else about the picture — scene count 1 to 8, caption density universal
at 1.0, cut rate 2.5 to 13.7 per minute — is flat.

## 6. Two selection defects contaminate the analysis of everything above

**The comment gate.** 59 % of the analysed corpus runs one. It multiplies save ×2.8 and share ×1.8 and
moves reach by nothing (`robust_z` 1.2475 against 1.2481). Since `cards.py` ranks candidates on `resh_1k`
and `save_1k`, the radar has been part-ranking DM funnels, and **every share/save comparison in this
report that does not hold `cta_type` constant carries that inflation unevenly.**

**Creator-relative metrics favour lottery accounts.** Reels from CONSISTENT creators score *lower*
(median `robust_z` 0.60, view_lift 0.65) than reels from HIGH_VARIANCE creators (1.37, 2.38) with
identical script shape, purely because both metrics divide by the creator's own spread. That is why 33 of
40 pool rows are gated and only 1 of 27 selected references comes from a CONSISTENT creator — a property
of the machinery, not of the niche.

## 7. Most of the category grid cannot answer a question at all

Of **159** reported categorical cells across eight vocabularies, **18 are SUFFICIENT_SAMPLE, 96 PROBABLE,
45 INSUFFICIENT**. All 20 `subtopic` cells are INSUFFICIENT; 9 of 27 `topic` cells are; no topic cell and
only one hook type reaches n ≥ 30 with 8 creators. **The thinness is itself the finding**: the next wave
must buy breadth — more codes per cell — not more features per code [I-30].

## Strategic implication

Stop looking for a format that wins. Spend M2's effort on three things the data does support: **subject
choice** (a named repeated act, not a condition), **specificity** (name the exact tool, number and step,
and repeat the name rather than varying it), and **evidence M2 owns** (own screen, own run, including the
failure — the one move no measured competitor makes). Judge M2's reels on shares and saves per 1 000, hold
`cta_type` constant when comparing anything, and expect small multipliers once the account becomes
consistent.

**Confidence.** The negative results (§1) and the metric structure (§2) are **RELIABLE** — large n, direct
measurement, and obtained under conditions favourable to finding a difference. The screen findings (§3)
are **RELIABLE**. The convergence in §4 is **RELIABLE** on its lexical leg and **PROBABLE** on its
categorical leg. §5's structural description is **RELIABLE** as a count and **PROBABLE** as a reading.
§6 is **RELIABLE**. §7 is **RELIABLE**. Everything here is associational and computed inside a
pre-selected 8.3 % of the database; **nothing in this chapter licenses a causal claim.**
