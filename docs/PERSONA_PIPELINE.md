# Persona pipeline — from what is popular to what we shoot (2026-09-13)

Misha's operating model, set on 13 September 2026:

1. **Research runs on its own.** The radar collects the niche twice a week (Hiker, Monday and
   Thursday 07:00), scores every reel against its author's median, transcribes and frames the
   newest ones locally, and picks the week's references (cards.py: 30-day window, shares + saves
   ladder, all reels of any author with one winner). This tells us **what is popular and what
   people watch**.
2. **Three people stand for our clients.** `personas/*.json` (rendered in `docs/PERSONAS.md`):
   Rick, 34, plumbing and HVAC owner; Emma, 29, founder of a small online business; Anna, 38,
   operations manager in a 40-person services company. Each is a clear profile (age, business,
   size, tools, a day) with a long list of interests by category, built from the audience data
   (`reports/audience/01-07`) and written as interests, not quotes. The interest list is what a
   found reel is matched against.
3. **The server agent adapts what was found to the persona whose interest list contains it.**
   `engine/persona_adapt.py` exports this week's references with their analysis and a routing
   hint (`engine/personas.py match`, keywords + interest lines), then runs the unattended agent
   with `engine/prompts/persona-adapt.md` (contract `pa-v1`). The agent decides: which persona
   and which interest line exactly, the question as that person would say it, what we borrow
   (structure only) and what changes for our positioning, the hook, the opening screen, the
   visible human check, the cost line, and, when a real artefact exists, a comment
   call-to-action. Reels no interest list covers are rejected with a reason and stay references.
4. **A comment call-to-action is optional.** It is used where an artefact in `artefacts/` fits
   the interest ("comment WORD and I send you the price-sheet template"); when present, the
   artefact exists before publishing (validator warning `card.cta.artefact`, reviewer check 11).
5. **Cards, review, storyboard, EDL** as before (`engine/cards_v2.py`, writer rule 13, reviewer
   check 11), with `strategy.persona` and `cta` filled from the concept.
6. **Results feed back.** Published reels go to `our_posts`; after 12 published reels the rules
   are reviewed against our own share and save rates (RULES.md §8).

## Commands

```
python3 -m engine.personas list | match "text" | doc | validate
python3 -m engine.persona_adapt export            # batch from this week's cards.py picks
python3 -m engine.persona_adapt run --yes         # unattended claude -p, one CONCEPT_GENERATION job per batch
python3 -m engine.persona_adapt list              # concepts on disk, validated against pa-v1
python3 -m engine.notion_sync --apply --scope personas
```

## What is wired and what is not

- Wired: personas, routing hint in the weekly cards output, the adaptation batch and agent
  runner with jobs trace, the pa-v1 validator, artefact library (10 one-pagers), validator
  warnings on cards, Notion Personas database, kanban rows.
- Not yet in cron: the adaptation run. It is launched by hand after Monday's collection until
  Misha approves the first concepts; then it goes into cron.sh after analyze_pending.
- Not yet: ingestion of concepts into a table (they live as files under
  `data/analysis/concepts/`, listed by `persona_adapt list`); card generation from a concept
  (writer prompt takes the concept file as input, to be scripted once the first batch is
  approved).
