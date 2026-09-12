# 20. Script Frequency Patterns

**Denominators.** Orderings and beat-role counts run on **264** codes and **1 527 beats** (median 6 beats
per reel, min 0, max 12). Phrase, opening and n-gram counts come from `features_json.lexical` over the
same codes; the hook n-grams are the first words of the **264** hook beats. Open-loop and
pattern-interrupt counts are ta-v1's own tallies over **266** reels. Sentence-level counts must be read
against `sentence_source`: **255** transcripts are punctuated by Whisper and split on punctuation, **11**
have no punctuation at all and are split on Whisper's own VAD phrase boundaries; the two groups are never
pooled silently.

## Orderings: two fixed endpoints and chaos in between

Collapsed to the eight script parts and de-duplicated, there are **146 distinct orderings across 264
reels**. The hook is the first beat in **259 of 264**; a CTA or closing beat is last in **215**.

| ordering | n | % of 264 |
|---|---:|---:|
| HOOK > EXPLAIN > PAYOFF > CTA | **27** | 10.2 % |
| HOOK > EXPLAIN > CTA | 13 | 4.9 % |
| HOOK > EXPLAIN > PROOF > CTA | 10 | 3.8 % |
| HOOK > PROOF > CTA | 8 | 3.0 % |
| HOOK > PROOF > PAYOFF > CTA | 6 | 2.3 % |
| HOOK > EXPLAIN > PROOF > PAYOFF > CTA | 6 | 2.3 % |
| HOOK > SOLUTION > PAYOFF > CTA | 5 | 1.9 % |
| HOOK > PROOF (no CTA) | 5 | 1.9 % |
| HOOK > EXPLAIN > PROOF > EXPLAIN > CTA | 5 | 1.9 % |
| HOOK > SETUP > EXPLAIN > PROOF > PAYOFF | 4 | 1.5 % |

**No ordering covers more than 10 % of the corpus.** The stable facts are the two endpoints and the
dominance of explanation in the middle, which is why the honest description of this niche's default is
four moves, not eight: **HOOK > EXPLANATION > PAYOFF > CTA** [I-04]. The eight-part model in the method
doc is a vocabulary for measurement, not a template anyone follows. Raw beat-role frequencies confirm
where the mass sits: hook 259 · mechanism 250 · cta 205 · example 157 · payoff 145 · proof 104 ·
explanation 96 · solution 84 · context 40 · setup 31 · tension 31 · problem 29 · closing 23 ·
objection 19 · rehook 15 · pain 12 · transformation 10 · other 5 · audience 3 · hook_extension 2.

For M2 the implication is permissive rather than restrictive: there is no ordering to copy, so problem,
proof and objection are **deliberate additions that must earn their seconds** — which for M2 they do,
because POSITIONING.md §8 requires friction and an AI boundary that this corpus omits.

## The three hook grammars

| position | most frequent openings, over the 264 hook beats |
|---|---|
| first word | "I" 22 · "this" 18 · "if" 16 · "you" 15 · "so" 11 · "the" 10 · "here's" 8 · "someone" 6 · "I'm" 6 · "Claude" 5 · "hey" 5 |
| first bigram | "you can" 10 · "if you" 9 · "I just" 9 · "this is" 7 · "if you're" 4 · "here's how" 4 · "Claude can" 3 · "most people" 3 |
| first trigram | "you can now" 7 · "if you want" 4 · "this is what" 3 · "I just built" 3 · "Claude can now" 2 · "nobody is talking" 2 · "most people think" 2 |

Three templates carry almost all of it. **"You can now X"** announces a new capability.
**"I just X"** is a first-person demonstration — the builder register, and the register chapter 28 says
M2 should adopt. **"If you X, then Y"** is conditional address, and it is also the identity-call family
that underperforms worst in chapter 17 (`identity_call` median `view_lift` 0.41). That the third template
is both common and weak is the most actionable frequency fact in this chapter: **a shape's popularity in
this niche is not evidence that it works.**

## Sentence openings, endings and imperatives

| family | counts over the analysed codes |
|---|---|
| sentence openings | "this is" 26 · "you can" 23 · "if you" 21 · "it's called" 20 · "here's how" 14 · "so you" 14 · "so this" 10 · "let me" 10 · "i just" 10 · "now you" 7 · "the first" 7 · "but here's" 7 · "you just" 7 · "most people" 7 |
| sentence endings | "right now" 13 · "for free" 11 · "for you" 11 · "on github" 10 · "to you" 7 · "do it" 6 · "use it" 6 · "it works" 5 · "right here" 5 · "the link" 5 |
| imperative verbs | **comment 41** · follow 14 · let 13 · go 12 · look 9 · think 9 · imagine 7 · do 7 · click 7 · tell 6 · make 6 · open 6 · start 5 · write 5 · build 5 · see 5 |
| keyphrase bigrams | "claude code" 11 · "it will" 11 · "you will" 10 · "open source" 8 · "to build" 7 · "click on" 7 · "your business" 7 · **"cloud code" 7** · "chat gpt" 6 · "ai agent" 6 · "gpt 6" 6 |

Two readings. Sentences in this niche **end on a destination or an availability claim, not on a
conclusion** — the same finding chapter 16 reaches from the solution vocabulary and chapter 26 from the
platform-name correlation, arrived at from three independent directions. And "comment" is three times
more frequent than the next imperative: the lexical fingerprint of the keyword gate (chapter 18), and the
clearest measure of how much of this niche's apparent call-to-action vocabulary is one funnel mechanic.
The "cloud code" row is an ASR defect, not a product (chapter 13).

## Repetition: the counter-intuitive result

Deliberate phrase repetition within a reel is **rare**: "if you want to" 3 · "you want to learn" 2 ·
"you don't have to" 2 · "exactly how to use" 2, then a long tail of one-offs. Median
`lex_repeated_phrases_n` is **0** in both the strong and the weak quartile (p=0.286).

What the strong quartile repeats is not phrases but **vocabulary**, and it does so measurably more:
type-token ratio **0.605 against 0.628 (p=0.039)** and MATTR50 **0.795 against 0.811 (p=0.044)** — both
*lower* in the strong quartile. Two of the seven features that separate the quartiles at p<0.05 therefore
run in the direction most writing advice forbids: **winners keep saying the same tool name and the same
step word rather than reaching for variety.** Read alongside the entity findings (distinct entities 2
against 1, p=0.011), the pattern is coherent: name the thing, then name it again.

## Retention devices

| device | frequency |
|---|---|
| reels with ≥1 open loop | **240 of 266**; median exactly 1 (198 reels), 36 carry two, 26 carry none |
| pattern interrupts | 140 reels have none, 110 have one |
| explicit re-hook beat | **15 of 264** (6 %) |
| explicit objection beat | **19 of 264** (7 %) |

**The niche's retention device is a single unresolved promise held from the hook to the payoff, not
repeated re-hooking** [I-26]. Where a re-hook does appear it is very short and placed at the moment the
mechanism stops being new: [DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/) inserts a
**1.8-second** rehook — **"But how about the results?"** (32.0–33.8 s) — between the architecture and the
live call, and carries 36.5 saves per 1 000 on an ungated close.
[DK9pFUjPQcx](https://www.instagram.com/reel/DK9pFUjPQcx/) uses the same move as an escalation — **"And
the best part? It's not just these four. I've collected over 10 such free api platforms"**
(rehook, 31.0–37.0 s) — immediately before its gate.

The counter-example is instructive. [DaDn5L-xKWi](https://www.instagram.com/reel/DaDn5L-xKWi/) opens
**five** loops ("Five AI image tricks top realtors are using…") and closes them in five identically
shaped ten-second blocks; it flattens. [Db3SERzzOqG](https://www.instagram.com/reel/Db3SERzzOqG/), the
corpus's 178-second outlier, also opens four loops in its hook — but closes them **in the exact order
they were opened**, and runs at 88.5× its author's median. Multiple loops are survivable only with
explicit ordering discipline; one loop is the default for a reason.

**Rhetorical devices.** `semantics.rhetorical_devices` is free text and produced **975 distinct strings
across 266 reels**, so no device reaches a countable frequency. The recurring families by repeated
wording: numbered steps or lists (17 combined), borrowed authority (6), price contrast or anchoring (6),
future pacing (4), objection pre-emption (3), rule of three (3), keyword gate (3), benefit stacking (3),
delayed reveal (2), mid-roll rehook (2), myth vs reality (2), share-with-a-peer close (2). The countable
equivalents live in the lexical features: median `questions_n` **0**, `second_person_n` 8,
`first_person_n` 4–5, `imperatives_n` 1, `superlatives_n` 1, `intensifiers_n` 1, `negations_n` 2,
`modals_n` 3, `numbers_n` 3 (strong) against 1 (weak).

## Strategic implication

**(1) Default the M2 script to four moves** — hook, mechanism, payoff, CTA — and add friction, proof and
the AI boundary as deliberate, budgeted insertions. **(2) Write hooks in the "I just X" or "you can now X"
grammar and never in the "if you are a…" grammar.** **(3) Repeat the tool name, the step number and the
promise rather than varying them** — the strong quartile's lower lexical diversity is a finding, not a
flaw. **(4) Open exactly one loop**, and add one short re-hook only past about 45 seconds, placed where
the mechanism stops being new. **(5) End sentences on a destination.**

**Confidence: RELIABLE** for the ordering counts, beat-role frequencies and the two endpoints (n=264,
1 527 beats, direct count). **PROBABLE** for the lexical-diversity reversal (p=0.039 and 0.044, inside a
67-per-side split, and the direction is counter-intuitive enough to deserve replication). **PROBABLE** for
the open-loop description (n=266, ta-v1's own tallies, not an independent measurement). **INSUFFICIENT**
for anything about rhetorical devices as categories — 975 distinct free-text strings is not a vocabulary.
