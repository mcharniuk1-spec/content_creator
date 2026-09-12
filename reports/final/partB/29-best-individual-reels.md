# 29. Best Individual Reels

**Denominators.** Every reel below is inside the analysis-ready corpus (**n=268**, 102 creators). Share
rate is available on all 268; **save rate on 245** (HikerAPI drops the field on ~9–10 % of rows). All four
metrics carry the 100-play denominator guard. `robust_z` is clipped at ±5, so **25 reels tie at 5.0** and
the magnitude there is a floor, not a value (`06-creators-and-references.md` §5 says 23; the count in
`reports/data/analysis_ready.csv` is 25). Above all: this is the top of `score.py`'s own ranking, so
"best" means best inside an already-selected set [I-01].

## Best per metric

| metric | reel | creator | value | context |
|---|---|---|---|---|
| highest `view_lift` | [DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/) | valeridoesai | **399.4×** | 1 980 128 plays on a 4 946 median |
| second | [DUJYKENjZc5](https://www.instagram.com/reel/DUJYKENjZc5/) | sharmadhruveshh | 388.2× | 534 953 plays on a **1 374** median |
| highest `robust_z` | **25** reels tied at the ±5 clip | — | 5.0 | the clip makes the magnitude a floor |
| highest share rate | [Dc_tsSeAjBy](https://www.instagram.com/reel/Dc_tsSeAjBy/) | manthanjethwani | **61.3 / 1 000** | 2 350 035 plays, 66× median, ungated (`question_to_audience`) |
| second | [DcvBtiNtbYO](https://www.instagram.com/reel/DcvBtiNtbYO/) | leadgenman | 59.2 / 1 000 | 79 235 plays, 2.6× median, ungated, save rate only 7.3 |
| highest save rate | [DbO4zvJR1k8](https://www.instagram.com/reel/DbO4zvJR1k8/) | shrug.manny | **87.4 / 1 000** | 209 121 plays, 13.5× median, gated |
| second | [Dct6Op3n6Zd](https://www.instagram.com/reel/Dct6Op3n6Zd/) | valeridoesai | 75.9 / 1 000 | 90 775 plays, 17.4× median, gated, held split screen |
| highest absolute play | [Dc9GZ0Gzf6o](https://www.instagram.com/reel/Dc9GZ0Gzf6o/) | anshmehra.in | **6 043 051** | 18.3× median, no save value, topic is entertainment |
| best combined share + save | [DbO4zvJR1k8](https://www.instagram.com/reel/DbO4zvJR1k8/) | shrug.manny | 52.9 + 87.4 = **140.3** | gated; the ungated best is Dc_tsSeAjBy |
| best combined at ordinary reach | [Db9MT-axxcO](https://www.instagram.com/reel/Db9MT-axxcO/) | shrug.manny | 47.9 + 68.9 = 116.7 | only **1.6×** its own median |

Three rows in this table correct
`reports/analysis/06-creators-and-references.md` §5, which was written from the reference pool rather than
from the full analysed set: the highest share rate is Dc_tsSeAjBy at 61.3, not Dbi-yxNgrhG at 58.4; the
highest absolute play is Dc9GZ0Gzf6o at 6 043 051, not DRXZJeHiAES at 3 349 555; and the best combined
share+save is DbO4zvJR1k8 at 140.3, not Db9MT-axxcO at 116.7. All four differences are recorded in this
report's source-verification note.

**The instructive row is the last one.** `Db9MT-axxcO` carries near-best hi-intent rates on a reel that
barely beat its own author's median. RULES §6 already has a label for this case — "резонировало у своих",
resonated with its own audience — and it is exactly the reference a views-based filter drops and a
share/save filter promotes. Both filters are wrong on their own; the card must carry all three numbers.

## The five reels worth studying, and why

**1. [DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/) — edhillai, 451 491 plays, 55.4×,
23.3 shares / 36.5 saves per 1 000, `cta_type: none`.** The best overall template in the corpus, and it is
**ungated**, so every rate can be read at face value. Screen-first: the artefact speaks the first four
words — **"Hello, how can I assist you? This voice assistant can replace your receptionist. I'll show you
how to build it in three easy steps."** (hook, 0.0–6.4 s). The mechanism names each connector at the
moment it becomes necessary ("it uses Google Calendar to check your schedule and Google Sheets to save any
details"). A **1.8-second rehook** — "But how about the results?" (32.0–33.8 s) — sits exactly where the
mechanism stops being new, and is followed by a complete recorded call ending in a confirmed booking. The
closing line is the machine finishing its job. fa-v1 records a held n8n workflow canvas with a small
facecam, `first_frame_type: UI_DEMO`, and Google Calendar showing the booked appointment as the second
proof visual.

**2. [DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/) — valeridoesai, 399.4×, 59.9 saves per
1 000.** The corpus's highest lift, and 43 seconds long. The hook states the result, the exact time and
the step count in one breath — **"I just built a website that looks like it costs $10,000 with literally
one line of code and honestly the whole thing took Claude about two minutes."** (0.0–11.8 s) — and every
step afterwards states its own benefit. `SCREENSHOT > A_ROLL_CLOSE_UP > SCREENSHOT`: eight of eight
observed transitions are hard cuts, and the screen carries the payoff while the face carries only the
interpretation. Caution: our own analysis flags this reel and DWCPx0PkQzA as **the same template running
on two accounts**, so the pair is one structure, not two pieces of evidence.

**3. [Dc_TX1CttIc](https://www.instagram.com/reel/Dc_TX1CttIc/) — v.i.s.h.ai, 562 094 plays, 24.1×,
31.7 shares per 1 000, ungated.** The closest thing in the corpus to an M2 Radar reel. Agenda announced in
nine seconds, four cases labelled aloud, and a verdict that is economic rather than promotional:
**"Very good model for sure, but the API cost has shot up so high that any business trying to build a real
product on Astra is walking into a train wreck"** (payoff, 80.8–92.6 s). Conditions are stated before the
conclusion and the concession comes before the claim — "Every one of these was one shot. And yes, more
context makes it better…" This is what a decision delivered whole looks like.

**4. [DbO4zvJR1k8](https://www.instagram.com/reel/DbO4zvJR1k8/) — shrug.manny, 87.4 saves per 1 000,
the corpus maximum.** Seventy-one seconds, one unbroken `A_ROLL_CLOSE_UP`, **no screen at all**, and it
never flattens because every item has an identical shape: the consequence, then the exact clause that
prevents it. **"Number one and most important, if your terms and service doesn't cap your liability,
there's no limit to how much somebody can sue you for."** (5.6–18.2 s), repeated four times. Proof that a
control reel can hold on a face if the cadence is strict — and a reminder that its save rate carries the
gate's ×2.8 inflation.

**5. [Db9MT-axxcO](https://www.instagram.com/reel/Db9MT-axxcO/) — shrug.manny, 1.6× lift, 47.9 shares /
68.9 saves per 1 000.** Result at 3 seconds, three steps in thirty, ask at forty-three; simultaneously a
story and a procedure. Its question hook works because the same breath answers it: **"What happens when
you ask Claw to apply to 500 jobs for you? I tried this and I landed six interviews in 24 hours."**
(0.0–7.0 s). `A > SCR > A > SCR > A` — the face for interpretation, the screen for the action — with a
phone calendar of booked interviews as the first proof visual.

## Two reels that top a metric and must not be copied

[DcvBtiNtbYO](https://www.instagram.com/reel/DcvBtiNtbYO/) is the corpus's second-highest share rate
(59.2 per 1 000) and a **sung** reel — "I'm maxing out my fable 5 on extra high" (hook, 0.3–4.7 s) — with
no destination, no ask and a save rate of **7.3**. It demonstrates that share and save are different
instructions (chapter 26) and nothing else.
[DUduffIE5w5](https://www.instagram.com/reel/DUduffIE5w5/) is structurally strong and **disqualified on
content** under RULES §2а (cloned cartoon voices, promotion of an uncensored model). It is kept in the
pool solely so the suitability check has something to fire on.

## Strategic implication

Use **DNA7-d3o5sQ as the M2 Builds template** (screen-first, one rehook, ungated close, artefact speaking
first), **Dc_TX1CttIc as the M2 Radar template** (agenda, labelled cases, economic verdict), and
**Db9MT-axxcO as the Teardown clock** (outcome by 5 s, steps in one run, ask in the last tenth). Read
`DbO4zvJR1k8` for cadence and discount its save rate by the gate. And put all three numbers — lift with
its baseline `n`, share per 1 000, save per 1 000, plus `cta_type` and `reliability` — on every card, so
that a 399× on a 4 946 median and a 1.6× on a 14 448 median are never mistaken for the same event.

**Confidence: RELIABLE** for the per-metric maxima (direct measurement over `reports/data/analysis_ready.csv`,
n=268/245). **PROBABLE** for the reading of any individual reel: each is a single case, four of the seven
named are gated, and a reel's structure is a hypothesis about why it worked, never a
measurement of it. **INSUFFICIENT** for anything about the 25 reels tied at `robust_z` 5.0 — the clip
destroys the ordering among them.
