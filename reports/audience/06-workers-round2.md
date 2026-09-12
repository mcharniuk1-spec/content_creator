# WORKERS lens — round 2

Read in full: `persona_corpus.md` and `persona_founders.md`.

## 1. Disagreements

**D1 — "Non-technical content doesn't travel" is not a finding about our audience.**
Corpus §5.4: 10 of 274 reels, save 0.0424, lift 0.78. Its own §7: "None of this is M2's own audience… pre-filtered to winners". n=10 measures other creators' supply. Against it: 80% BYOAI at SMEs (WTI 2024); 61% under five hours of training, 30% none (Slack 2024). Lift 0.78 is a **production constraint** — pair the topic with a high-lift carrier ((c) 3.02, `manual_repetition` 13.66) — not an audience veto.

**D2 — "Trust shares worst" is about register, not topic.**
Corpus: `trust` n=58, share 0.0091 vs 0.0165 awareness. But permission is my second-largest demand: 48% uncomfortable telling their manager, 47% feel it is "cheating" (Slack 2024); "What are my moral and employee responsibilities" (workplace.stackexchange.com/questions/198277). They want a rule to hold up, not an explanation — `resource_handoff`, the corpus's top save (n=39, 0.0429).

**D3 — Founders' zero (f) rows vs my four job-fear rows: both right, different seats.**
Founders: no owner asked about cutting staff; US Chamber — 82% of AI-using small businesses expanded headcount. Mine: 53% worry AI makes them look replaceable (WTI 2024); 52% worried, 32% expect fewer opportunities (Pew 2025-02-25); "can I be fired for refusing to use AI?" (askamanager.org 2025-07). Corpus settles the call: `fear_of_replacement` n=8, save **0.0126** (lowest of any pain), while `Dc_tsSeAjBy` shares 0.0613. **Fear travels and is never kept.** Never sell to it; never frame automation as headcount cuts.

**D4 — Cost: I reject "free access" as the answer.**
Corpus §4: 97 free-access reels vs 35 quoting a price. But bill shock comes *from* the free start: "I was surprised when my OpenAI bill came through" (community.make.com/t/does-anyone-else-spend-too-much-on-ai-costs/89571, 2025-08-14); "It's not clear to me how much they will cost" (/t/how-much-do-ai-tools-cost/70924). Founders' benchmark: $28–31/month median (JPMC 2026); £100/month rejected. Reframe seed (d) to **"what does it cost per month once it runs, and what makes the bill jump"** — corpus subscription frame n=24, share 0.0219, lift 3.17.

**D5 — Back-office tasks: dead cells, or a retrieval asset.**
Corpus §3: meeting notes n=12, lift 0.70 but save **0.0471** (highest in that table); invoices n=7; email n=4. My lens ranks meeting notes the #1 named task (4 of 25 rows). They will not travel; they should not be dropped. Retrieval asset, not reach.

**D6 — Tool choice: top demand, worst performance.**
Founders 5/25 rows; mine 2 plus autocomplete "what ai tool can i use to create a powerpoint presentation". Corpus (b) n=22, share 0.0068 (−55%), `comparison` 0.0070, while `tool_walkthrough` n=62 saves 0.0303. Reframe seed (b): **never a comparison, always one tool running on the named process.**

## 2. Confirmations

1. **(c) is the centre in all three** — founders 7/25, mine 5/25, corpus n=103 lift **3.02**, its best cluster. POSITIONING §3 verbatim.
2. **"Where do I start" is next** — founders 4, mine 3; corpus (e3) n=40 share **0.0176** vs 0.0152 baseline.
3. **(a) is weak everywhere** — corpus n=38 share 0.0107; founders 2 rows; mine 1, anonymous search demand only.
4. **Human control asked for on both web lenses** — "without losing control" (Shopify 2026-08-18), "people still want a human touch" (BiggerPockets); 86% treat output as a starting point (WTI 2026).
5. **Same training void twice** — Slack 61%/30% in both tables; Goldman 88% want training; corpus `missing_skills` n=25 share 0.0097.
6. **Repetitive inbound is the safest first workflow** — founders rank support #1; corpus support lift **5.85**.

## 3. Proposed final three personas

### P1 — "Mary", e-commerce owner-operator (founder, AI 4/10)
4-person Shopify supplements brand. Writes her own copy, answers her own tickets, resists paying above ~£30/month.
1. *"Which 2–3 tools do I actually need?"* — shopify.com/t/ai-tool-recommendations-for-running-store/676450 (2026-09-04). Corpus: as comparison 0.0070; as walkthrough save 0.0303. **Seed (b), reframed.**
2. *"How does my support inbox get handled without me losing control of what customers are told?"* — same thread, "repetitive support tickets takes up most of my day". Corpus: support lift **5.85**. **Seed (c).**
3. *"What will it cost per month, and when does it stop being worth it?"* — £100/month rejected (2025-07-31); $28–31 median (JPMC 2026); corpus subscription lift 3.17. **Seed (d), reframed.**
4. *"Is it safe to put customer and order data in?"* — "I dont want to share customer names, emails or order ids" (2025-05-16); OECD 54%.
5. *"How do I do catalogue work in batches?"* — Shopify 2026-09-02. Corpus: `manual_repetition` save 0.0415, lift **13.66**.
6. *"Am I already behind?"* — 29% of non-users unsure what AI can do (Shopify 2025); corpus `keeping_up_with_ai` n=29, save 0.0181 — travels, not kept.

Does not ask (a).

### P2 — "Bruce", local services owner (founder, AI 2/10)
6–12 person brokerage / property management / trades. Half-used CRM, WhatsApp, spreadsheets. Tried AI once, unimpressed.
1. *"What is this actually, beyond the hype?"* — "Most 'agents' sound like workflow automations that have been around forever" (news.ycombinator.com/item?id=42629498, 2025-01-11); 62% of non-adopters cite lack of understanding (Service Direct). **The only persona asking seed (a) — and it stays a hook, never a card** (corpus share 0.0107).
2. *"What do people in my trade use it for?"* — biggerpockets.com/forums/48/topics/1236774.
3. *"Why did the output sound fake?"* — "I don't like the descriptions it pops out" (Bruce Lynn); corpus `quality_trust` n=25.
4. *"How does one repeated job — follow-up, listing write-ups, call notes — get handled?"* — same threads; corpus (c) lift 3.02. **Seed (c).**
5. *"Where do I start with no technical person?"* — 47% find tool choice hard, 45% lack expertise (Goldman 10KSB 2026-03, page 403, verify); corpus (e3) 0.0176.
6. *"Is this relevant to a business like mine?"* — construction 8.9% vs professional services 30.3% (JPMC 2026).

Seed (d) in his own words: **no evidence found** (only second-hand "associated costs").

### P3 — "Marta", operations & marketing-ops manager (non-founder, AI 3/10)
15–60 person services company, 2 reports, reports to the owner. Personal ChatGPT, company Copilot licence, CRM, Make/Zapier trial. POSITIONING §4 calls her the Champion.
1. *"How do I automate the process my boss just named?"* — "my boss asked me to create an automation to connect ClickUp" (community.make.com/t/…/70635, 2025-02-20); corpus (c) lift 3.02. **Seed (c), her only unreframed one.**
2. *"How do meetings become notes and actions without retyping?"* — /t/…/105203 (2026-03-10); corpus save **0.0471**, lift 0.70 — retrieval, not reach.
3. *"What are we allowed to do with client data, and who is responsible when it's wrong?"* — workplace.stackexchange.com/questions/198277; KPMG 2025: 66% don't check accuracy, 56% made mistakes. Ship as a one-page rule (save 0.0429), not a trust talk (share 0.0091).
4. *"How do I get the boss and the team to agree?"* — "boss won't let us use AI transcription" (askamanager.org 2025-10, Copilot licences already bought); 26% say leadership is aligned (WTI 2026). **No corpus cell for (h) — unmeasured bet.**
5. *"How do I stop my team producing slop someone else cleans up?"* — "a ChatGPT wall of text that's hundreds of words long" (workplace.stackexchange.com/questions/202364, 2025-08-05).
6. *"What will it cost before I ask for budget?"* — /t/how-much-do-ai-tools-cost/70924. **Seed (d), reframed.**

Does not ask (a); (b) reaches her only as "for this one task".

**Dropped:** my W2 junior learner — real (21% of US workers use AI, up from 16%, Pew 2025-10-06; GenAI enrolments +234%, Coursera 2026) but no budget, no process to own, lowest-save pain (0.0126). Carry as comment audience.

**Seed verdict:** (c) survives intact for all three. (d) only as monthly running cost. (b) only as one tool running on one named process. (a) is P2's alone, and belongs in the first three seconds.
