# Audience personas — draft v1 (2026-09-12, evening)

Status: DRAFT for Misha's approval. Produced by a three-agent discussion (corpus lens on our own
274 analysed reels + 3 211 with metrics; founders lens on the open web; workers lens on the open
web), two rounds. Full evidence, disagreements and confirmations: `reports/audience/01..06`.
Query scripts behind every corpus number: `reports/audience/persona_corpus_query*.py`.

Why this exists: Misha rejected the ten 12-Sep cards ("nobody will watch this") and asked for
about three audience profiles with concrete questions, evidence-backed, so that content is built
from what the audience asks rather than from what the niche happens to publish.

Access caveat: Reddit was hard-blocked for the agents (and all public mirrors sit behind
proof-of-work gates, which were not bypassed); Quora, Ask a Manager bodies, HubSpot Community
and Class Central returned 403. Owner voice therefore comes from Shopify Community, BiggerPockets,
Hacker News and Quora titles; worker voice from Stack Exchange Workplace, the Make.com community,
Ask a Manager titles and Google autocomplete; plus ~20 dated surveys. One survey page (Goldman
Sachs 10KSB Voices, Mar 2026) returned 403 and its figures come from the search index — verify
before quoting on camera.

## The three personas all three agents converged on

Seed questions (Misha): A "what is AI and how it works" · B "which tool for a task" ·
C "how can process N be automated" · D "what will it cost".

### P1 — Mary. Owner-operator, online product business (Shopify), 2–10 people, AI level 4/10
Tools: Shopify + Sidekick, ChatGPT, Canva, a helpdesk. Writes her own copy, answers her own
tickets. Will not pay above ~£30/month without a fight.
1. "Which repeated job in my week do I hand over first?" — corpus cluster C n=103, lift 3.02
   (best cluster) · Shopify Community 630061 (30 May 2026). [C]
2. "How does my support inbox get handled without losing control of what customers are told?" —
   corpus customer support n=13–17, share 0.0195, lift 5.85–12.44 · Shopify 676450 (4 Sep 2026)
   "answering repetitive support tickets takes up most of my day". [C]
3. "What will it cost per month, and when does it stop being worth it?" — corpus subscription
   frame n=24, share 0.0219, lift 3.17 · £100/month rejected (Shopify 552674, 31 Jul 2025);
   median SMB AI spend $28–31/month (JPMorganChase Institute 2026). [D, reframed]
4. "Which two or three tools do I need, not twenty?" — asked constantly (Shopify 676369;
   Goldman: 47 % find tool choice hard) but corpus: head-to-head comparison is the worst cell
   measured (n=12, share 0.0070); one tool shown running works (tool_walkthrough n=62, save 0.0303).
   [B, reframed: one tool on one process, never a ranking]
5. "Is my customer and order data safe in these tools?" — Shopify 414591 (16 May 2025); OECD 2025
   54 % worry about data fed to models · corpus: trust register shares below baseline (0.0107) —
   answer as a rule she can keep, not as a trust talk.
6. "How do I do catalogue/content work in batches, not one item at a time?" — Shopify 675818
   (2 Sep 2026) · corpus manual_repetition n=16, save 0.0415, lift 13.66 (highest-lift pain). [C]
7. "How do I get found inside ChatGPT?" — Shopify 667253 (16 Aug 2026) · corpus n=5, median lift
   18.0 — signal, not fact.
Does not ask A.

### P2 — Bruce. Owner, local services firm (brokerage / property / trades / clinic), 6–15 people, AI level 2/10
Tools: a half-used CRM, WhatsApp/email, spreadsheets, free ChatGPT on the phone. Tried AI once,
was unimpressed, has nobody to ask. Hardest persona to reach (corpus SMB-owner label lift 1.12,
lowest of any audience label) — the price of the audience POSITIONING §4 chose.
1. "What is this actually, beyond the hype?" — HN 42629498 (11 Jan 2025) "most 'agents' sound
   like workflow automations"; 62 % of non-adopters cite lack of understanding (Service Direct
   2025) · corpus: A as a promise underperforms (n=38, share −30 %); framework content saves 0.0135
   vs a takeaway file 0.0429. [A — the only persona who asks it; ship as the first 10 s of a demo
   plus a takeaway, never as the card's promise]
2. "What do people in my trade actually use it for?" — BiggerPockets 1236774, 1244728 (2025). [C]
3. "Why did the output sound fake when I tried it?" — broker: "I don't like the descriptions it
   pops out"; "people still want a human touch" · corpus quality_trust n=25.
4. "How does one repeated job get handled — quote follow-up, listing write-ups, call notes?" —
   same threads · corpus sales follow-up n=30, share 0.0188; DYuivWzSj5k "chases follow-ups by
   hand, every day". [C]
5. "What does it cost before I commit?" — BiggerPockets 1244728 "what are some associated costs
   around it?" (second-hand for him; no first-person cost quote found). [D]
6. "Where do I start with no technical person?" — Goldman 10KSB 2026: 45 % lack technical
   expertise, 88 % want training (verify, 403) · corpus dont_know_where_to_start n=34, #2 pain;
   where-to-start cluster share 0.0176, above baseline.
7. "Is this even relevant to a business like mine?" — construction 8.9 % vs professional services
   30.3 % adoption (JPMorganChase 2026); NFIB Jun 2025: 24 % use AI, 63 % expect it to matter.
   Corpus silent (no industry field).

### P3 — Marta. Operations / marketing-ops manager, 15–60-person services company, AI level 3/10 (non-founder)
Two reports, reports to the owner. ChatGPT on a personal account, a company Copilot licence
nobody trained her on, CRM, ClickUp/Notion, a Make or Zapier trial. POSITIONING §4's Champion.
Context numbers: 80 % of AI users at SMEs bring their own tools (Microsoft WTI 2024); 61 % of desk
workers have under five hours of AI training, 30 % none (Slack 2024).
1. "My boss named a process — how do I actually automate it?" — Make community 70635 (20 Feb
   2025) "my boss asked me to create an automation", 74956 (12 Mar 2025) · corpus C n=103,
   lift 3.02. [C — her only unreframed seed question]
2. "How do our meetings become notes and actions without retyping?" — Make 105203 (10 Mar 2026)
   · corpus meeting notes n=12, save 0.0471 (highest save of any task) but lift 0.70: retention,
   not reach.
3. "What will it cost before I ask for budget, and what makes the bill jump?" — Make 70924
   (22 Feb 2025) "not clear how much they will cost"; 89571 (14 Aug 2025) "surprised when my
   OpenAI bill came through" · corpus tokens/credits n=27, save 0.0339. [D, reframed]
4. "What are we allowed to do with client data, and who is responsible when it is wrong?" —
   Stack Exchange Workplace 198277 (1 Jul 2024); KPMG 2025: 66 % do not check output, 56 % made
   mistakes · corpus: human-review language in only 3 of 274 reels — M2's signature move is
   absent from the niche. Ship as a one-page rule.
5. "How do I get the boss and the team to agree?" — Ask a Manager Oct 2025 (boss refuses AI
   transcription despite paid licences); Microsoft WTI 2026: 26 % say leadership is aligned ·
   corpus: team-adoption cell n=6, share 0.00072, lift 0.39 — worst cell measured. Unmeasured bet.
6. "How do I stop my team producing AI slop someone else cleans up?" — Stack Exchange 202364
   (5 Aug 2025) · corpus n=6, lift 0.68.
7. "Will this make me look replaceable?" — Pew 2025: 52 % worried; Microsoft 2024: 53 % · corpus
   fear_of_replacement save 0.0126, lowest of any pain: fear travels (share 0.0613 on one reel)
   and is never kept. Answer inside another card, never as the promise.
Does not ask A; B only as "which one for this task".

Dropped: a junior learner persona (W2 in the workers lens) — real demand (Pew: 21 % of US workers
use AI; Coursera: GenAI enrolments +234 %) but no budget, no process to own, and the only matching
corpus pain has the lowest save. Carry as a comment audience. Also dropped: the builder already
paying token bills (P3 in the corpus lens) — the niche's best performer (agent building lift 6.6)
and explicitly on POSITIONING's do-not-publish list.

## What the evidence says about the four seed questions
- C "how can process N be automated" — answer literally. Best cluster in the corpus, top cluster
  in both web lenses, asked by all three personas.
- D "what will it cost" — asked by all three; the niche answers "how not to pay" (97 free-access
  reels vs 35 quoting a price). Our opening is the honest monthly figure on a named plan and the
  point where it stops paying ($20 / $100 / $200 plans in the corpus; $28–31 median SMB spend).
- B "which tool" — asked constantly; comparisons die on distribution. Only as one tool running on
  one named process, on screen (screen-on-camera is the dataset's most reliable finding, I-08/I-09).
- A "what is AI" — asked only by Bruce and by anonymous search demand; as a promise it is the
  weakest thing we could publish. Use it in the first ten seconds, then show a job.

## Two more things the merge exposed
- Back-office tasks (invoices, proposals, email, meeting notes) are real but felt by the ops
  employee (Marta), not the owner; with owners they are the smallest, lowest-lift cells.
- Human-in-the-loop is asked for on every web lens ("without losing control", "people still want
  a human touch", 86 % treat output as a starting point) and appears in 3 of 274 niche reels.
  That is the open territory.

## Next step (after Misha's decision)
Regenerate hypotheses from these three personas' questions instead of from the insight list alone,
then rewrite the ten cards; each card names its persona and the question it answers.
