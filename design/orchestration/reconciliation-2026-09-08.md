# Reconciliation — brand book v3 vs radar repo and Notion — 2026-09-08

Checker report only. Nothing in Notion or in Max's files was changed. Scope: does the
approved wording from `01-positioning.md`, `06-formats.md`, `07-messaging.md`,
`05-vocabulary.md` and LOG.md iteration 2 (2026-09-08) still appear anywhere in the
radar product repo or in the M2 Lab Notion tree.

## A. Repository — `.../m2-research/radar/`

Grepped: POSITIONING.md, RULES.md, PLAN.md, PRODUCTION.md, SPEC.md, START-HERE.md,
README.md, prompts/angles.md, cards.py, queries.py, topics.py, notion.py, notion_db.py
(`tags.py` does not exist; closest equivalents `tag_topics.py`/`tag_candidates.py`
checked too). No hits for: "builds the case", Unhurried, old hex codes, Space Grotesk,
Instrument Serif, IBM Plex Sans Condensed as display, terracotta, comment-bait
phrases, or any banned vocabulary word used as our own copy. All hits below are
in **POSITIONING.md** and **RULES.md**; PLAN.md/PRODUCTION.md/SPEC.md/START-HERE.md/
README.md/prompts/angles.md/the .py files are clean.

| File:line | Text found | Brand book says instead | Affects |
|---|---|---|---|
| POSITIONING.md:24 | "Start with one repeated **task**. Keep a human in control." | "Start with one repeated **workflow**." | Runtime — this file's header says it is read by the agent before every angle is written |
| POSITIONING.md:30 | "choose one repeated task, map it clearly, and build the first human-controlled workflow" | "choose one repeated workflow, break it into fragments, and build the first human-controlled version of it" | Runtime (same file) |
| POSITIONING.md:34 | `repeated task → process map → AI boundary → human review → first test` | `repeated workflow -> fragmentation -> AI boundary -> human review -> first test` | Runtime — file says every content piece must reinforce this chain |
| POSITIONING.md:59 | table cell: "The person doing the repeated task" | describes the User role; wording follows the old unit | Documentation only |
| POSITIONING.md:133 | Radar question: "Should I test this in my team?" | "Is this solution relevant to me?" | Runtime — RULES.md §2 derives its Radar question from this section |
| POSITIONING.md:135 | Teardown question: "Is this process suitable for AI?" | "...and how would it work?" (missing clause) | Runtime — same |
| POSITIONING.md:183 | "process mapping" listed as a sellable offering | old step name from the retired chain | Documentation only, low priority |
| RULES.md:92 | RU: «стоит ли мне это тестировать у себя в команде?» (Radar audience question) | RU equivalent of "Is this solution relevant to me?" | Runtime — cards.py cites RULES.md §2 directly for selection criteria |
| RULES.md:121 | RU: «подходит ли этот процесс для AI вообще?» (Teardown question, no "and how") | needs the RU equivalent of "...and how would it work?" | Runtime — same |

Note: `design/brand/01-positioning.md` and `design/source/profile-copy.md` inside the
repo still contain "Michael builds the case. Max builds the thing." — that is a mirror
of the master brand book's own internal Purpose statement (allowed there; the rule
only bars the line from published content), so it is not a discrepancy and is outside
the CHECK A file list.

## B. Notion

| Page | Owner | Hits | Brand book says instead | Severity |
|---|---|---|---|---|
| M2 Lab — Radar (3d00…5a) | Radar | none — page says "Moved... can be deleted" | — | none |
| M2 Lab — Radar (3d00…7c) | Radar | none — same, marked for deletion | — | none |
| Content Engine Tool | Content Engine Tool | none found | — | none |
| Content Engine | Content Engine | none found | — | none |
| M2 Signal + Studio · 7 September · ten-card release | Max's release | "What M2 should say" section: *"A repeated task → a process map → an AI boundary → a human check → a first test."* | `repeated workflow -> fragmentation -> AI boundary -> human review -> first test` | wording only — a guiding note on the release page, not itself on-screen/spoken copy, but it is the method statement the pipeline was told to write from |
| Writing knowledge · source analysis and secondary creator techniques (child of the release) | Max's release | *"For M2, bind this to the positioning method: name one repeated task..."* | same chain as above | wording only — working method note, could shape future scripts if left as-is |
| M2-I01 — Meet M2 Lab: start with the Friday update | Max's card | Scene 7, spoken/on-screen closing line: *"Start with one repeated task. Write down its source notes..."* | "Start with one repeated **workflow**." | **blocks a published piece** — this is the card's actual CTA line, ready for shooting |
| M2-I05 — Meet M2 Lab: design the customer handoff | Max's card | Scene 7 closing line: *"At the end of your next process map, draw the person receiving the result."* | avoid "process map" (retired chain step); rephrase as workflow/fragmentation language | wording only — generic English use, borderline, not a banned term itself |
| M2-P04 — Ask for the awkward case before buying automation | Max's card | *"Choose one repeated task, such as turning enquiry notes into a draft response."* | none — this is the allowed literal sense of "repeated task" (one task inside a workflow, not the starting unit) per `05-vocabulary.md` | none |
| M2-I04 — Meet M2 Lab: test the awkward enquiry | Max's card | production note only: "Name the exact repeated task" | same literal-sense allowance | none |
| M2-I02, M2-I03, M2-P01, M2-P02, M2-P03, M2-P05 | Max's cards | no old-brand hits | — | none |

Workspace search for "repeated task", "process map", "Should I test this in my team",
"builds the case"/"builds the thing", "Unhurried", old hex codes, Space Grotesk,
Instrument Serif, terracotta, comment-bait phrases and the banned-vocabulary list
turned up nothing else in our own copy. The only other "repeated task" hits are (a)
third-party Reel captions in the harvested Signal library (competitor copy, excluded
by the brief) and (b) unrelated ArchFlow/outreach pages, not part of M2 Lab.

No comment-bait, no banned vocabulary word, no old hex/typeface, no role line, and no
non-compliant `RADAR / 0x`-style tag appear anywhere in the ten reviewed cards.

## What is safe to change now

- `POSITIONING.md` in the radar repo: replace the method chain (line 34), the
  supporting line (24), the internal operating statement (30), and the two pillar
  questions (133, 135) with the v3 wording. This file is read every run, so fixing it
  is the highest-leverage single edit.
- `RULES.md` lines 92 and 121: update the RU Radar/Teardown questions to match.
- `POSITIONING.md:59` and `:183`: optional cleanup, documentation only.

## What to hand to Max

Two lines in his already-reviewed 10-card release use retired wording and should be
corrected before shooting:

1. **M2-I01**, Scene 7 (spoken + on-screen): "Start with one repeated task." → should
   read "Start with one repeated workflow."
2. **M2-I05**, Scene 7 (spoken + on-screen): "At the end of your next process map,
   draw the person receiving the result." → reword to drop "process map" (e.g. "At the
   end of your next fragmentation pass...").

Also worth a note to Max: the release page's "What M2 should say" summary and the
child "Writing knowledge" method note both still spell out the old chain
(`repeated task → process map → AI boundary → human check → a first test`). Neither
is on-screen copy, but both look like the method statement his pipeline was told to
write from — updating them protects the next batch of cards, not just this one.

## No change needed

- PLAN.md, PRODUCTION.md, SPEC.md, START-HERE.md, README.md, prompts/angles.md,
  cards.py, queries.py, topics.py, notion.py, notion_db.py — clean.
- Content Engine, Content Engine Tool, both trashed "M2 Lab — Radar" stub pages —
  clean.
- M2-I02, M2-I03, M2-I04 (production note only), M2-P01, M2-P02, M2-P03, M2-P04,
  M2-P05 — clean; "repeated task" where it appears in M2-P04/M2-I04 is the allowed
  literal usage, not the retired method unit.
