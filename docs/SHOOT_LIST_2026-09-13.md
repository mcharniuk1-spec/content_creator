# Shoot list v2 — ten publications from real questions (2026-09-13)

Status: DRAFT for Misha. Replaces the ten cards of 2026-09-12 (rejected: "nobody will watch this").
Every line here answers a question real people asked, in their words, with the thread it came from
(`reports/audience/07-reddit-pass.md`) and, where the corpus has a number, the corpus signal
(`reports/audience/01-corpus-lens.md`). Personas: Mary (online product owner, AI 4/10), Ray (local
services owner, AI 2/10, renamed from Bruce), Marta (ops manager in a 15–60 person company, AI 3/10).
Rules applied: `RULES.md` §2 (four-part filter), §11 (audience language), writer rule 13.

Format mix for two weeks: 4 Radar, 4 Builds, 2 Teardown (RULES.md §5). Each card: the question in
the viewer's words, the hook, what is on screen, the human check shown, the cost line, the one-page
artefact behind the comment keyword, and the evidence. Builds are shot after the build runs at
least once and breaks once; that is the Builds pass criterion.

## Radar (forward: "is this relevant to me")

**R1 · Mary, Ray · "Which AI do I pay $20 for?"** — question (b) reframed: one job, one tool, shown
running. Hook: "Three subscriptions, one job: writing quotes. I paid for all three for a month." On
screen: the same quote request typed into ChatGPT, Claude, Gemini; the three outputs side by side;
the one that did not invent a price. Human check: the price sheet the tool must read from. Cost line:
$20 is the reference; pay $200 only when you hit limits and can count the hours. Artefact: "Which
one for which job" one-pager. Evidence: r/ChatGPTPro 1r2990u (57 pts, "not worth my $20 anymore"),
1o2wg4b, r/smallbusiness 1qo267y ("I've only used ChatGPT so far"); corpus: comparison n=12 share
0.0070 vs tool_walkthrough n=62 save 0.0303 — so it is a walkthrough, not a ranking.

**R2 · Mary · "Is ChatGPT recommending my shop, and do I need a $3,000 audit to find out?"** —
Hook: "An agency quoted her $3,000 plus $400 a month to check if ChatGPT recommends her store. Here
is the 20-question version for free." On screen: 20 real customer questions typed into ChatGPT and
Gemini, a tally of who gets named, GA4's AI traffic channel. Human check: you write the 20 questions,
not the tool. Cost line: $3,000 + $400/mo vs £450 + £50 vs doing it yourself in an hour. Artefact:
20-question test sheet. Evidence: r/ecommerce 1vz1hk0 (20 pts), Shopify Community 667253 (16 Aug
2026); corpus: only 5 reels, median lift 18.0 — a signal, not a fact, say so on camera.

**R3 · Ray · "Should an AI answer my phone?"** — Hook: "Callers hang up on AI receptionists. I timed
the one hour a day it is still worth it." On screen: a real after-hours voicemail, the missed-call
text-back, Google Voice screening killing the 15 spam calls an hour. Human check: every real lead
still reaches a person by the next morning. Cost line: Google Voice free at his size; VA $1,100/mo;
AI receptionist pitch downvoted. Artefact: after-hours intake script (one page). Evidence: r/sales
1to9799 (167 pts, "I just hang up"), r/sweatystartup 1vvw2kr (16 pts), 1oex952 ("losing jobs because
I can't answer fast enough"); corpus: customer support share 0.0195, lift 5.85.

**R4 · Marta · "My boss checked my work against Claude. Now what?"** — Hook: "Her CHRO ran her
proposal through Claude and sent back a wall of text. Here is the reply that ended it." On screen:
the r/msp tactic — same AI, same question, but with the source documents pasted in first; the answer
flips. Human check: the sources are yours, the verdict is yours. Cost line: none, it is the tool they
already pay for. Artefact: "Ask it again with sources" one-pager. Evidence: r/msp 1vr7q7i (86 pts,
69-pt comment), r/humanresources 1vlmxlv (113 pts), r/marketing 1rqaf5y (436 pts), r/Accounting
1sr82s5 (538 pts); corpus: trust register shares below baseline — so it is shot as a demo, not a talk.

## Builds (save: "how does the first working version look")

**B1 · Ray · "Voicemail → draft text → you tap yes"** — the one loop, nothing else. Hook: "Two-man
HVAC shop. Admin was eating the evenings. We built one loop and it broke on day three." On screen:
phone rings, voicemail transcribed, draft text appears as an SMS to the owner, he replies "yes",
it sends; then the failure (wrong job type / a price it should not have written). Human check: the
yes-tap, and the rule "the model never writes a price, it reads the sheet". Cost line: what the
transcription and drafts cost per week in real numbers from our run. Artefact: price-sheet template.
Evidence: r/smallbusiness 1w640zy (55 comments, "managing the AI is starting to feel like a full-time
job"), r/sweatystartup 1oex952; corpus: manual_repetition save 0.0415, lift 13.66. Build first: our
own number, one week of real voicemails (Misha's or a volunteer owner's), logged.

**B2 · Mary · "The same 20 questions, answered from one document"** — Hook: "Her support inbox is
the same twenty questions. We gave the bot one document with an owner and a date, and it still got
two wrong." On screen: the FAQ doc (owner, last-reviewed date), drafts appearing in the inbox for
approval, the 20-question test before go-live, the two failures. Human check: approve-before-send,
weekly sample of real conversations. Cost line: the tool's monthly price vs the hours; "free" is not
an answer. Artefact: the 20-question go-live checklist. Evidence: r/smallbusiness 1vxr2l4 ("does the
answer match your actual policy today?"), 1wbey4m, r/sweatystartup 1uoh3pw (6-pt "FAQ and a few
automated emails saved me hours"); corpus: customer support lift 5.85–12.44.

**B3 · Marta · "One meeting, three documents, zero retyping"** — Hook: "Her team confirmed they do
not read the AI meeting summaries. So we stopped summarising and started minuting decisions." On
screen: transcript in, then the three outputs — decisions/owners/dates, a Slack recap, an exec
paragraph — and the moment the tool invented an action nobody agreed. Human check: she edits two
examples, the tool learns her format; the decisions list is read aloud at the end of the meeting.
Cost line: the licence they already have (Copilot / Claude $20). Artefact: decision-minutes
template. Evidence: r/projectmanagement 1w0383c (71 pts), 1vbp2g8 (159 pts, "one transcript
becomes a slack recap, exec summary, RAID entries"), r/ExecutiveAssistants 1p3w8vh; corpus: meeting
notes save 0.0471 (highest of any task), lift 0.70 — retention, not reach; pair it with R4 in the
same week.

**B4 · Mary · "Twelve subscriptions, one number: cost per run"** — Hook: "She pays for twelve apps
and has barely launched. We put our own bill on screen and divided it by the number of times the job
actually runs." On screen: our real ledger (889 paid requests, $0.02 each, $17.78 to date), a
column "runs per week", the per-run price of each tool, the guard that refuses to spend without a
yes. Human check: the spending cap is a decision, the tool asks before it spends. Cost line: the
per-run number. Artefact: cost-per-run sheet. Evidence: r/ecommerce 1taro12 (204 pts, "I'm paying
for 12 apps"), r/smallbusiness 1v83bom (55 comments, "every part of the process has its own
subscription"), r/ChatGPTPro 1nlngy5; corpus: subscription frame n=24, share 0.0219, lift 3.17.

## Teardown (save + search: "is this process suitable for AI, and how would it work")

**T1 · Ray · "100 little exceptions in my head"** — the process before any tool. Hook: "He said
yes to every customer request for two years. Then he hired someone, and every yes became a rule
nobody could remember." On screen: the route sheet, the customer card with "knock / don't knock /
gate code", the onboarding questionnaire that captures exceptions once; then where AI fits (drafting
the card from past messages) and where it must not (deciding which exception stays). Owner: the
crew lead. Reason to forward: "this is the list your best guy carries in his head". Artefact:
customer exception card. Evidence: r/sweatystartup 1w3krwn (27 pts, 32-pt comment "systemize the
personal touches"), r/smallbusiness 1vjat9j (35 pts, 73 comments: "clean item master first",
"document exceptions for a month"); corpus: chaos_no_process n=18, below baseline — shoot it as a
concrete card, not a concept.

**T2 · Ray · "Why the job that looked profitable cleared 8 %"** — Hook: "Eighteen techs, eight
years, booked out two weeks, and a commercial job cleared 8 %. The quote forgot four things." On
screen: the estimate with the missing lines (rental, drive time, refrigerant, warranty callback),
then the data he already has — hundreds of past jobs — turned into an incidentals percentage and a
checklist the tool cannot skip. Owner: whoever sends the quote. Reason to forward: "this is what it
costs you per week". Human check: a second person reads every quote before it goes out. Artefact:
quote checklist with the incidentals line. Evidence: r/sweatystartup 1rg0rml (43 pts, 26-pt
"margin leakage is almost always a quoting problem"), 1p4qdxr (quoting from photos), r/smallbusiness
1qo267y; corpus: sales follow-up / quoting share 0.0188 above baseline.

## Sequencing (two weeks, RULES.md §5)

Week 1: R1, R3, B1, B2, T1. Week 2: R2, R4, B3, B4, T2. Builds B1 and B2 need a build day before
the shoot; B3 and B4 can be built from existing material (transcripts we own; our ledger). T1 and
T2 need one real owner's material or our own process; without it they run as "we think", not "we
saw" (RULES.md §2, Teardown sources).

## What is deliberately not on the list

AI images, AI flyers, AI copy, chatbots on the front door, "replace your assistant", "how to make
money with AI", model news, tool rankings. All publicly rejected in the pass (§4 of the report) or
on POSITIONING.md's do-not-publish list.
