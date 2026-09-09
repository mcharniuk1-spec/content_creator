# Audit of Max's Signal + Studio work and a content plan: orchestration plan

8 September 2026. Orchestrator: Fable. Owner: Misha. Nothing in Notion is changed.

## Final goal (updated after Max's comment, 8 Sep evening)

Max: "make a PDF report (a plan) of what can be changed; I will try the same tomorrow. I will
simplify the analysis and use a clear sequence to define a topic, and what to orient on when
making a card. Transcripts need a bigger focus on extracting: hook, problem, solution, tool, CTA.
Frames are still critical: they show the hook and the CTA and the dynamics of the video."

Deliverables therefore:
1. A PDF report for Max (A4, in the design system's type and colours): what to change in the
   pipeline and in the cards, with (a) a clear sequence for defining a topic, (b) a card
   checklist: what to orient on when making a card, (c) a transcript extraction schema with the
   five fields hook, problem, solution, tool, CTA, plus timing, (d) a frame analysis schema:
   hook frame, CTA frame, cut rhythm, what changes on screen, shot types, (e) the audit findings
   that justify each change, with quotes.
2. A content plan for Misha: ten topics from the data, six to be chosen, each with a hook in the
   reel-cover-v2 structure. Structure fixed by Max (same as his I01–I05 / P01–P05 split):
   - 5 introduction posts: 4 built on a direct reference reel, each presenting the positioning;
     1 new scenario about the positioning with a clear problem and its solution, derived from
     the analysis.
   - 5 regular posts: 4 that replicate a best-performing reference; 1 that combines what the best
     performers share, with an explicit hook, problem, solution, tool and CTA, made unique.
   Every topic names its reference reel(s) with the metrics that justify it.

| # | Task | Model | Input | Output | Gate (Fable) |
|---|---|---|---|---|---|
| 1 | Dump Max's Notion release tree to files | Sonnet | Notion | `notion-raw/` + INDEX | every card present, nothing truncated |
| 2 | Explain Max's pipeline from his repo | Sonnet | content_creator | `data/max-pipeline.md`, `data/max/` | frames viewed or not, ASR coverage, models run are answered with quotes |
| 3 | Inventory our radar data | Sonnet | m2lab-radar | `data/radar-data.md`, `top-reels.csv`, `topics.csv` | row counts, top topics |
| 4 | Audit the ten cards frame by frame | Opus | 1, 2, brand v3 | `audit/cards-audit.md` | every claim quotes the card; errors typed (generic, no urgency, no utility, brand rule, factual, structural); per card: does it show a hook, a problem, a solution, a tool, a CTA, and where |
| 5 | Audit the transcript and frame analytics | Opus | 1, 2 | `audit/analytics-audit.md` | method flaws with evidence; proposes the five-field transcript schema and the frame schema (hook frame, CTA frame, dynamics) with a worked example on real reels |
| 5b | Topic sequence and card checklist | Opus | 4, 5, brand v3, radar rules | `audit/method.md` | a numbered sequence a person or agent follows to pick a topic, and a card checklist |
| 6 | Verify both audits against sources | Sonnet | 4, 5, 1 | `audit/verification.md` | no unsupported claim survives |
| 7 | Content plan, 10 topics: 5 introduction (4 by reference + 1 new positioning scenario) and 5 regular (4 by best-performer reference + 1 synthesis) | Opus | 3, 2, brand v3, design | `plan/content-plan.md` | each topic: reference reel with metrics, format, hook / problem / solution / tool / CTA, cover hook in the v2 structure, why now, utility, verdict type |
| 8 | Check the plan: editorial filter, vocabulary linter, hook length | Sonnet | 7 | `plan/check.md` | zero linter errors, four filter answers per topic |
| 9 | Assemble the report and the plan | Fable + Opus | 4–8 | Desktop: PDF report for Max (A4, design system type and colours), content plan MD for Misha | show / recheck decision written per section |

Rules: agents write only in their output folder; quotes carry the source file and line; Russian for the documents, English quotes kept verbatim.

## Status, 8 September, night

Done. Deliverables on the Desktop: `M2 Lab - Signal+Studio Audit Report (2026-09-08).pdf` (18 pages)
and `.md`; `M2 Lab - Content Plan 10 Topics (2026-09-08).pdf` (11 pages) and `.md`. Gates: both
audits verified by a checker (PASS WITH FIXES, fixes applied), the plan checked against data, brand
rules and Max's cards (PASS WITH FIXES, applied). Working files in `audit/`, `plan/`, `data/`,
`notion-raw/`, `report/` (the md2pdf pipeline). Nothing in Notion was changed.
