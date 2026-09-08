# Start here — for Max

Two days of work, 33 scripts, 174 checks. This file is the map, so you do not have to find
your way in by reading code.

---

## What this is

A weekly radar for the M2 Lab Instagram account. It pulls public reel metrics across a set
of accounts, scores every reel **against its own author's norm**, takes the top of the
freshness window apart frame by frame, transcribes the speech, tags topics and proposes
shooting cards — with an angle, a hook and three shooting columns.

It runs itself on Monday and Thursday from a server. About $2 per run; everything except the
API calls is local and free.

**One line: the machine counts and narrows, people read and decide.**

---

## Read in this order

| File | Why |
| --- | --- |
| `POSITIONING.md` | **the approved playbook** — audience, the three pillars, the mandatory editorial filter. The agent reads it before writing any card |
| `PRODUCTION.md` | how a reel is built: length, cuts, the two questions before filming — measured on the set |
| `SPEC.md` | how the tool works and, more useful, **why each decision was made** |
| `audit.html` | four independent audits of this tool, 3 September. Open it in a browser |
| `RULES.md` | topic selection rules |
| `PLAN.md` | what is done and what is not |
| `score.py` | your formula with our changes — probably the first code you will want to see |

---

## What we took from `m2_engine`, and what we changed

**Taken as is:** robust z on `ln(1 + views)` inside the author, MAD instead of standard
deviation, comparison against **that author's** median, minimum baseline of five reels, and
the rule that a missing component is dropped with weights renormalised rather than counted
as zero. That last one is the best part of it and we kept it everywhere.

**Changed, with reasons:**

| Change | Why |
| --- | --- |
| Added **saves** as its own component | Not in yours because YouTube does not expose them. Instagram does, and the niche is save-driven: 38 saves against 20 shares per thousand |
| Turned **early velocity** off | Needs snapshots over time. It comes back on its own once they accumulate — your own missing-component rule makes that safe |
| Reweighted for Instagram | views 0.15 · engagement 0.15 · shares 0.30 · saves 0.30 · comments 0.10. We also ran yours: **the top 40 overlaps on 34 of 40**, so the choice of weights decides almost nothing |
| Score compares inside an **age band** | A fresh reel is still gathering views. Before this the median-to-norm ran 0.70× for reels under three days and 1.54× for reels over three months, and cards drifted to the far edge of the window. After: 0.93× and 1.41× |
| A reel is excluded from **its own** baseline | Otherwise it pulls the median up and partly hides its own outlier |

---

## Three things the formula did wrong — worth porting back

**1. A near-zero MAD explodes the score.** With very even numbers, MAD approaches zero and any
deviation gives an absurd z. A reel with **654 views against an author median of 25 487** came
out on top. Your `epsilon: 1e-9` does not catch this — it only catches an exact zero.

Fix: drop a component whose spread is under 5% of the median, and cap every component at ±5.

**2. That same threshold must not be applied to a logarithm.** We hit this ourselves. `views`
is `ln(1+x)`, where 5% of the median means a spread of nearly two-fold. The main axis of the
formula was being dropped for **41% of reels and 23 of the top 40** — and their weight shifted
onto shares and saves, which are *per thousand views*, i.e. inversely related to reach. Half
the shortlist was ranked on a different scale than the rest. The threshold has to be absolute
in log space.

**3. Ratios are noise on small view counts.** Shares and saves per thousand are meaningless at
a hundred views. Fix: a reel below 30% of its author's median, or below a thousand views,
never enters the shortlist.

---

## What the data said about production

All measured on our set, not copied from someone's report.

- **Length.** Winners' median is **55 seconds** against 47 for the rest. Under twenty seconds:
  5% of winners, 13% of the rest. The thirty-second rule from the Studio pack does not hold
  for Instagram.
- **Editing is close to optional.** Median **0.12 cuts per second**. Of the top hundred, 44
  have effectively none and 12 have exactly zero, and the signal difference against edited
  ones is inside the noise. At five reels a week this decides the whole production model.
- **A share separates a winner 3.6× more reliably than anything else**; a save, 2.8×. Saves
  are larger in volume — so "the niche is save-driven" is true about volume and false about
  what pulls a reel up.
- **Comment bait does not work.** Present in 28% of top reels and 26% of the rest.
- **Our territory sits at the bottom — and that is the good news.** "AI in a business process"
  runs at 22 shares per thousand against 38 for the window. But 29 of the 62 lead-generation
  reels come from two agency accounts advertising their own product, and the ceiling of the
  same topic is **2 755 shares** — a reel that hands over a specific agent instead of
  describing a service. Hundredfold gap. The topic is open for whoever treats it as content.

---

## Run it

```bash
python3 run.py          # estimate: what happens and what it costs
python3 run.py --yes    # the run itself
```

Thirteen steps in a fixed order: collect → score → analyse the top → tag topics → refresh
followers → liveness and dropout → read decisions from Notion → cards → delta → write cards
to Notion → the numbers behind the picks → the full databases → three pages.

The order is baked in on purpose. Analysis has to follow collection **inside the same run**:
Instagram CDN links live hours, and a deferred analysis downloaded zero out of a hundred.

```bash
python3 check.py && for t in baseline roster topup posts journal cards deep collect topics score pipeline notion; do python3 test_$t.py; done
```

174 checks. They are the reason the tool can be trusted with money.

---

## Where things live

- **Code and history** — this repository.
- **Data** — SQLite on the server, 14 tables: accounts, snapshots, reels, scores, topics,
  deepdives, frames, transcripts, our posts and their numbers, the tool's own defect log,
  spend, cards, follower history.
- **What people work with** — Notion: Cards, Reels (597 rows, everything collected and
  everything derived), Accounts (106 rows with what to borrow from each), and the top ten by
  each criterion.
- **`archive/2026-08/`** — the first pass, before the database. **Do not run anything there:**
  three of those scripts corrupt data, one spends money without an estimate.

---

## What we would like from you

1. **Port the three formula fixes** above into `m2_engine` — they will bite there too.
2. **Argue with `POSITIONING.md`.** That file decides what the agent writes in every card.
   If the angle is wrong, everything downstream is wrong.
3. **Take some of the cards.** The lead is assigned by topic: economics and processes to
   Misha, technique and builds to you.
4. **Look at the Accounts table in Notion** — eighteen accounts have a written judgement of
   what to borrow. The other 88 are waiting. If you disagree with any of the eighteen, say so
   in the comments there; the agent reads them on the next run.
