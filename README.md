# M2 Lab Radar

Weekly niche radar for the M2 Lab Instagram account. Collects public reel metrics across a
set of accounts, scores each reel against its own author's norm, takes the top of the freshness
window apart frame by frame, transcribes the speech, tags topics, and proposes shooting cards.

**One line: the machine counts and narrows, people read and decide.**

New here? Read [START-HERE.md](START-HERE.md). Positioning lives in [POSITIONING.md](POSITIONING.md)
(the approved playbook) and production in [PRODUCTION.md](PRODUCTION.md) first — the map of the project, what came
from the m2_engine formula and what changed in it.

## Run it

```bash
python3 run.py          # estimate: what happens and what it costs
python3 run.py --yes    # the run itself
```

The order is baked into `run.py` on purpose: collect → score → analyse the top → tag topics →
refresh followers → liveness and dropout → cards → delta → three pages. The analysis has to
follow the collection inside the same run, because Instagram CDN links live hours, not days.

After the run two things are left to a person:

```bash
python3 deep.py check                     # mark reels unusable by looking at their frames
python3 cards.py angle 3 "text"           # write the angle into card #3
python3 pages.py                          # rebuild the pages once the angles are in
```

## What is where

| File | What it does |
| --- | --- |
| `POSITIONING.md` | our angle, formats and rules — the agent reads this to write cards |
| `SPEC.md` | how the tool works and why each decision was made |
| `RULES.md` | topic selection rules |
| `PLAN.md` | what is done, what is not |
| `audit.html` | four-way audit of the tool, 3 September 2026 |
| `db.py` | schema, 14 tables |
| `run.py` | the whole weekly run |
| `collect_snapshot.py` | pulls reels into a dated snapshot |
| `score.py` · `baseline.py` | scoring against the author's own norm, by age band |
| `deep.py` | frames, contact sheet, cuts, local transcription |
| `blocks.py` | splits a transcript into hook / body / ending |
| `tag_topics.py` · `topics.py` | topic tagging by sample |
| `cards.py` | picks the cards and holds the angles |
| `roster.py` | the account set: liveness, dropout, top-up, followers |
| `delta.py` | what moved since the last snapshot |
| `pages.py` | three weekly pages |
| `posts.py` · `review.py` | what we published and how it did |
| `journal.py` | log of everything the tool got wrong |
| `prune.py` | drops frames older than eight weeks |
| `check.py` | health check on the database |
| `archive/2026-08/` | the first pass, before the database. **Do not run anything in there** |

## Checks

```bash
python3 check.py && for t in baseline roster topup posts journal cards deep collect topics score pipeline; do python3 test_$t.py; done
```

162 checks. They are the reason the tool can be trusted with money.

## Money

HikerAPI on the Start tariff, $0.02 per unit. A run over 106 accounts costs about $2.
Everything else — frames, transcription, tagging, pages — is local and free. The balance is
checked before every run and the spend is written to the database.

The key lives outside the repository and is never printed anywhere.

---

## Brand book and design system (added 8 September 2026)

Everything visual and verbal for M2 Lab lives in `design/`. An agent producing any asset or
copy starts at `design/SKILL.md` (router), a person starts at `design/README.md` and the PDF
`design/pdf/out/M2-Lab-Brandbook.pdf`. Values come only from `design/tokens/tokens.json`;
templates in `design/templates/`; stickers in `design/stickers/`; checks in `design/checks/`.
The radar scripts do not read this folder, so it is safe for the cron.
