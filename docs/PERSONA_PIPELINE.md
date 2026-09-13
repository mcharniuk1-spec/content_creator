# Persona pipeline — from what is popular to what we shoot (2026-09-13)

Misha's operating model, set on 13 September 2026:

1. **Research runs on its own.** The radar collects the niche twice a week (Hiker, Monday and
   Thursday 07:00), scores every reel against its author's median, transcribes and frames the
   newest ones locally, and picks the week's references (cards.py: 30-day window, shares + saves
   ladder, all reels of any author with one winner). This tells us **what is popular and what
   people watch**.
2. **Five people stand for our clients.** `personas/*.json` (rendered in `docs/PERSONAS_v2.md`):
   Mary (online product owner), Ray (local services owner), Marta (ops manager told to figure out
   AI), Dana (agency or consultancy owner), Sam (second-generation owner modernising a family
   business). Each carries pains in their own words with the source thread, the questions they
   ask, what they forward and save, what they distrust, how they think about cost, and the
   artefacts they would leave a comment for. Evidence: `reports/audience/01-07`.
3. **The server agent adapts what was found to one of them.** `engine/persona_adapt.py` exports
   this week's references with their analysis and a routing hint (`engine/personas.py match`),
   then runs the unattended agent with `engine/prompts/persona-adapt.md` (contract `pa-v1`). The
   agent decides: which persona would forward this, the question in the persona's words, what we
   borrow (structure only) and what changes for our positioning, the hook, the opening screen,
   the visible human check, the cost line, and the comment call-to-action with its artefact.
   Reels no persona would care about are rejected with a reason and stay references.
4. **Every video ends with a comment call-to-action for a real artefact.** "Comment WORD and I
   send you the price-sheet template." The artefact exists in `artefacts/` before publishing
   (validator warning `card.cta.artefact`, reviewer check 11). This is how the audience is
   collected and can be worked with later.
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
