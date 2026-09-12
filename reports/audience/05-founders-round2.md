# FOUNDERS lens — round 2

Read in full: `persona_corpus.md` (274 reels) and `persona_workers.md` (25 rows).

## 1. Disagreements

**D1. "Which tool for X" (corpus n=22, share 0.0068) is a format verdict, not a demand verdict.** Second-largest cluster in my lens (5/25) and the top barrier in the biggest owner survey: 47% say choosing the right tools is difficult (Goldman 10KSB Voices, Mar 2026). Their words: "what tool would you recommend for each category? And what's the pros and cons" (https://community.shopify.com/t/many-ai-choices-which-is-best-at-what/676369, 3 Sep 2026). The corpus splits its own answer: `comparison` n=12, share 0.0070 dies; `tool_walkthrough` (one tool shown running) n=62, save 0.0303 ≈ baseline survives. **The audience asks constantly; the niche answers with rankings, and rankings lose.**

**D2. "What is AI" underperforms (n=38, share 0.0107; `framework_mental_model` n=26, save 0.0135) because the people who need it are not in the niche's audience yet.** 29% of store owners not using AI "were not sure what AI tools can do" (https://www.shopify.com/blog/ai-for-small-business, 2025); 62% of non-adopters cite lack of understanding of benefits (https://servicedirect.com/resources/small-business-ai-report/). The workers lens saw the same: cluster (a) appears only in anonymous autocomplete, never in a signed post. Non-users don't post, they search. **Real demand, unreachable via explainer format.** Reframe to "what AI cannot do on *this* task", shipped as `resource_handoff` (corpus n=39, save 0.0429 — top save of any solution type).

**D3. On cost the niche and the buyer want opposite things.** Corpus: 97 "free/no cost" reels vs 35 quoting a price. Owners want a quote judged, not avoided — a UK owner walked away from ~£100/month (https://community.shopify.com/t/ai-platforms-running-your-business/552674, 31 Jul 2025); realtors ask "what are some associated costs around it?" (https://www.biggerpockets.com/forums/21/topics/1244728). Median spend: $28–31/month (JPMorganChase, 2026). The corpus's best money cell agrees: subscription/per-month n=24, share **0.0219**, lift 3.17.

**D4. "Will AI replace people" must never be aimed at owners.** Zero of my 25 owner rows raise it; workers 4/25; corpus `fear_of_replacement` n=8 has the **lowest save of any pain, 0.0126**. Owner data runs the other way: 82% of AI-using small businesses reported workforce expansion (US Chamber/Teneo, n=3 870, Jun 2025, https://ipwatchdog.com/2025/08/18/us-chamber-report-small-businesses-rapidly-adopting-ai-despite-regulatory-concerns/).

**D5. "Business owner/SMB" looks weak in the corpus (n=28, lift 1.12 vs 2.03) because the corpus is supply, not demand.** 274 winners by 132 creators with developer/creator-shaped distribution (dev 42, creator 50). Off-platform: 76% of small businesses use AI, 88% want training (Goldman, Mar 2026); 17% of EU firms with 10–49 staff use AI vs 55% of large (Eurostat, 11 Dec 2025). Lower lift is the price of the audience POSITIONING §4 already chose.

**D6. `slow_response_to_leads` (n=5, share 0.0001) is a naming failure, not a dead topic.** Owner wording is chasing quotes and follow-ups by hand (corpus `DYuivWzSj5k`; https://www.biggerpockets.com/forums/48/topics/1236774). Test it as "the quote nobody chased".

## 2. Confirmations

| # | Agreement | Corpus | Founders | Workers |
|---|---|---|---|---|
| C1 | (c) automate process N is #1 everywhere | n=103, lift **3.02** | 7/25, largest | 5/25, largest |
| C2 | Where-to-start is #2 | `dont_know_where_to_start` n=34; (e3) n=40 share 0.0176 | 4/25; Shopify 29% | 3/25; "I'm not a technical person" (make.com, 1 Apr 2025) |
| C3 | Human-in-the-loop is the trust answer | `quality_trust` n=25; (e2) save 0.0314 | "answer ONLY from the merchant's own catalogue" (676450); "without losing control" (668092) | KPMG: 66% don't check output, 56% made mistakes |
| C4 | Manual repetition is the highest-value pain | n=16, save **0.0415**, lift **13.66** | "repetitive support tickets takes up most of my day" (676450) | meeting minutes by hand, 4 rows |
| C5 | Cost is top-3 in all lenses | `cost_money` n=51, largest pain | £100/mo refused; $28–31/mo median | "It's not clear to me how much they will cost" (make.com, 22 Feb 2025) |
| C6 | Invoices/quotes/bookkeeping are weak *with owners* | invoices n=7 lift 0.76; proposals n=9 lift 0.81 | rank 9, **no owner-voice evidence** | alive with the employee: Stripe→QuickBooks reconciliation, small charity (make.com, 29 Jun 2026) |

C6 is the sharpest merge finding: POSITIONING's back-office examples are real work, but the person who feels them is the **ops employee**, not the owner.

## 3. Final three personas

Seed key: **A** what is AI · **B** which tool · **C** automate process N · **D** cost.

### P1 — Mary, owner-operator, online supplements brand, 4 people, AI 4/10
Shopify + Sidekick, ChatGPT, Canva, a helpdesk. Writes her own copy, answers her own tickets.
1. *"How do I stop answering the same tickets all day?"* — "repetitive support tickets takes up most of my day" (https://community.shopify.com/t/ai-tool-recommendations-for-running-store/676450, 4 Sep 2026); corpus `manual_repetition` save 0.0415, lift 13.66. **[C]**
2. *"Which 2–3 tools do I need, and what does each fail at?"* — 676369 (3 Sep 2026); Goldman 47%; corpus `tool_walkthrough` n=62 vs `comparison` n=12 share 0.0070. **[B — reframed: one tool running, never a ranking]**
3. *"What will it cost per month, and when does it stop being worth it?"* — 552674 (31 Jul 2025); $28–31/mo median; corpus subscription n=24 share 0.0219. **[D]**
4. *"Is it safe to put customer and order data in?"* — "I dont want to share customer names, emails or order ids" (https://community.shopify.com/t/chatgpt-shopify-querying-with-privacy/414591, 16 May 2025); OECD 2025: 54% worry what happens to data fed in.
5. *"How do I batch catalogue work instead of one product at a time?"* — "export 20 to 50 products at a time, have AI clean titles, descriptions, tags" (675818, 2 Sep 2026). **[C]**
6. *"How do I control what the bot tells my customers?"* — 676450.
7. *"Am I already behind?"* — 82% say AI is essential to compete (PayPal/Reimagine Main Street, Jun 2025).
**A?** No. For her, A becomes "what it cannot do here".

### P2 — Bruce, owner, local services firm (brokerage / trades / clinic), 6–15 people, AI 2/10
CRM he half-uses, WhatsApp, spreadsheets, free ChatGPT on his phone. Tried it once, unimpressed.
1. *"What is this actually, beyond the hype?"* — "Most 'agents' sound like workflow automations that have been around forever" (https://news.ycombinator.com/item?id=42629498, 11 Jan 2025); 62% of non-adopters cite lack of understanding. **[A — reframe to capability boundary on one job, delivered as a takeaway: corpus `resource_handoff` save 0.0429 vs `framework_mental_model` 0.0135]**
2. *"What do people in my trade actually use it for?"* — https://www.biggerpockets.com/forums/48/topics/1236774; corpus roles `DdCgx_ci6zj` realtors, `DZpi9FxoilB` accountants. **[C]**
3. *"Why did it sound fake when I tried it?"* — "I don't like the descriptions it pops out" (broker, BiggerPockets 1244728); "chatbot replies feel… robotic. People still want a human touch."
4. *"What does it cost before I commit?"* — same thread. **[D]**
5. *"How do I handle one repeated job — quote follow-up, listing write-ups, call notes?"* — same threads; corpus `DYuivWzSj5k`. **[C]**
6. *"Where do I start with no technical person?"* — Goldman: 45% lack technical expertise, 88% want training; corpus `missing_skills` n=25, share 0.0097 — worst-sharing large pain, which is why nobody serves him.
7. *"Is this even relevant to a business like mine?"* — construction 8.9% vs professional services 30.3% (JPMorganChase, 2026); NFIB Jun 2025: 24% use AI, 63% expect it to matter in five years.
**B?** Only as "what do people like me use" — not as a comparison.

### P3 — Marta, Operations & Marketing Ops Manager, 15–60-person services company, AI 3/10
From the workers lens; corpus support: employee/manager bucket n=20.
1. *"How do I automate the process my boss just named?"* — "my boss asked me to create an automation to connect ClickUp" (https://community.make.com/t/clickup-instagram-the-image-format-is-not-supported-36001-oauthexception/70635, 20 Feb 2025). **[C]**
2. *"How do meetings become notes and actions without retyping?"* — make.com 105203 (10 Mar 2026); corpus meeting notes n=12, save **0.0471**.
3. *"What will it cost before I commit?"* — make.com 70924 (22 Feb 2025); "I was surprised when my OpenAI bill came through" (14 Aug 2025). **[D]**
4. *"What are we allowed to do with client data, and who is responsible if it's wrong?"* — Slack 2024: 48% uncomfortable telling their manager; KPMG: 56% made mistakes.
5. *"How do I get my boss and team to agree?"* — Microsoft WTI 2026: 26% say leadership is aligned.
6. *"How do I stop my team producing AI slop?"* — "a ChatGPT wall of text that's hundreds of words long" (https://workplace.stackexchange.com/questions/202364, 5 Aug 2025).
7. *"Will this make me replaceable?"* — Pew 2025: 52% worried; corpus `fear_of_replacement` save 0.0126 — answer it inside another card, never as the promise. **[the (f) question lives here and nowhere else]**
**A?** No. **B?** Narrowly: "for this one task, not a list of fifty".

**Seed verdict.** C is universal and carries the format. D is asked by all three; the niche answers "how to not pay", so M2's opening is a decision rule at $20–100/month. B survives only as one tool running on one process. A is asked by P2 alone, reframed to "what it cannot do here" and shipped as something the viewer keeps.
