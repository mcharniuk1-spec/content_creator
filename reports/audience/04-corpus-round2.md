# CORPUS — Round 2

New queries: `persona_corpus_query5.py`. Baseline: **274 analysis-ready reels, share 0.0152 / save 0.0278 / lift 2.03** (play ≥ 100). That set is the top of `score.py`'s ranking, so it measures **what travels in this niche**, never demand. The web agents measured **demand**. Most disagreements below are that gap — and it is the most useful thing this round produced.

## 1. Six disagreements

| # | Their claim | Corpus number that contradicts or qualifies it |
|---|---|---|
| 1 | FOUNDERS: tool choice (b) is the #2 cluster, 5 of 25 rows | **(b) is the worst cluster measured: n=22, share 0.0068 (−55 %), save 0.0147 (−47 %)**; `comparison` n=12, share 0.0070. Owners ask it; a reel answering it head-to-head dies. `tool_walkthrough` (one tool, shown running) is fine: n=62, save 0.0303. Demand real, format wrong. |
| 2 | WORKERS: W2's first interest is "what AI is, in plain language" | **(a) n=38, share 0.0107, save 0.0220 — both ~25 % under baseline.** `framework_mental_model` n=26, save **0.0135** vs `resource_handoff` n=39, save **0.0429** — 3.2×. WORKERS' §5 concedes the cluster is anonymous; the corpus says worse — as a *promise* it is the weakest thing M2 could publish. |
| 3 | WORKERS ranks **meeting notes #1** by task frequency | n=12, **save 0.0471, highest of any task cell**, but **lift 0.70 vs 2.03**. Kept by those who see it, reaches nobody new. Lead magnet, not growth engine. |
| 4 | FOUNDERS: trust/privacy is cluster (e), 4 rows; OECD 54 % | `quality_trust` n=25, share **0.0133**; (e2) n=29, share **0.0107** — both under baseline. `funnel_role=trust` is the worst role: n=58, share 0.0091 vs 0.0165 awareness / 0.0174 conversion. Real fear, does not travel. |
| 5 | WORKERS W1 #5: "get my boss and team to agree" (6 rows) | Corpus is silent **and** hostile: permission/policy language in **9 of 274** reels; team-adoption **n=6, share 0.00072, lift 0.39** — worst cell in two rounds. White space or proven dead end; do not assume the former. |
| 6 | FOUNDERS frame cost as "what will it cost me per month" | Corpus inverts it: **97 reels sell free access vs 35 quoting a price**. `cost_money` is the largest pain (n=51) but `pain_raw` is bill shock from tools already bought — `DK9pFUjPQcx` "spending hundreds of dollars on API keys to experiment". The travelling frame is *how not to pay*. |

## 2. Six confirmations

| # | Web finding | Corpus number |
|---|---|---|
| 1 | FOUNDERS (c) top cluster 7/25 · WORKERS (c) 5/25, "my boss asked me to create an automation" (https://community.make.com/t/clickup-instagram.../70635) | **(c) n=103 (38 %), lift 3.02 — best of the nine clusters.** Both lenses and the metrics agree. This is the spine. |
| 2 | FOUNDERS rank **customer support #1** (rows 6, 15, 21; Service Direct 46 %) | n=13–17, **share 0.0195 (best mid-size task cell), lift 5.85–12.44.** Highest-conviction overlap of the exercise. |
| 3 | FOUNDERS: no owner asked about replacing staff (0 of 25) | `fear_of_replacement` n=8, **save 0.0126, lowest of any pain**; I-14: fear language negative on share after creator normalisation. Both lenses: do not build on it. |
| 4 | FOUNDERS: where-to-start, 4 rows; 62 % of non-adopters cite lack of understanding (https://servicedirect.com/resources/small-business-ai-report/) | `dont_know_where_to_start` **n=34, #2 pain**, save 0.0346; (e3) n=40, share **0.0176** — one of few above-baseline shares. Demand and distribution line up. |
| 5 | FOUNDERS: "get found inside ChatGPT", rising in 2026 threads (https://community.shopify.com/t/getting-traffic-from-chatgpt-ai-agents-where-do-i-even-start/667253) | Only **5 reels**, but **median lift 18.0**, highest of any probe. `DYSKnz3TxPZ` — "Their search traffic is moving into AI answers they cannot see or influence." Signal, not fact. |
| 6 | WORKERS: 80 % BYOAI at SMEs, 61 % under five hours of training (Microsoft WTI / Slack Workforce Index) | `audience_stage`: **28 "already using AI", 12 "tried it, not systematic", 53 beginner/unaware.** An audience past level 0 with no repeatable method — POSITIONING §4's premise, reached independently. |

## 3. Final three personas

Company size and AI level are **web-only**; no `ta-v1` field records either (corpus silent, both rounds).

### FO1 — "Mary", owner-operator, online product business, 2–10 people, **AI level 4/10**
1. *"Which repeated job should I hand over first?"* — corpus: (c) n=103, lift 3.02 · web: 7 of 25 rows, https://community.shopify.com/t/using-ai-for-running-my-business/630061
2. *"How is my support inbox handled without losing control of what customers are told?"* — corpus: n=13, share 0.0195, lift 12.44 · web: "repetitive support tickets takes up most of my day", https://community.shopify.com/t/ai-tool-recommendations-for-running-store/676450
3. *"What does it cost monthly, and when does it stop being worth it?"* — corpus: subscription n=24, share 0.0219, lift 3.17; `$20/$100/$200 plan` in `numbers_used` · web: £100/mo rejected, median spend $28–31, https://www.jpmorganchase.com/institute/all-topics/business-growth-and-entrepreneurship/understanding-ai-use-by-small-businesses
4. *"Which two or three tools do I need, not twenty?"* — corpus: **counter-evidence**, (b) n=22, share 0.0068 · web: https://community.shopify.com/t/many-ai-choices-which-is-best-at-what/676369
5. *"Is my customer data safe?"* — corpus: (e2) n=29, share 0.0107 · web: "I dont want to share customer names, emails or order ids", https://community.shopify.com/t/chatgpt-shopify-querying-with-privacy/414591
6. *"How do I get found inside ChatGPT?"* — corpus: n=5, lift 18.0, `DYSKnz3TxPZ` · web: https://community.shopify.com/t/getting-traffic-from-chatgpt-ai-agents-where-do-i-even-start/667253

**Seed questions:** (c) yes, primary · (d) yes · (b) yes but must be reframed · (a) no.

### FO2 — "Bruce", owner, local services firm (brokerage / clinic / trades), 6–15 people, **AI level 2/10**
1. *"What do people in my trade use it for?"* — corpus: SMB-audience label n=28, share 0.0174 but **lift 1.12, lowest of any audience label** — hardest persona to reach · web: https://www.biggerpockets.com/forums/48/topics/1236774-how-are-you-using-ai-in-real-estate
2. *"Why did the output sound fake when I tried it?"* — corpus: n=6, lift 0.68 · web: "I don't like the descriptions it pops out", https://www.biggerpockets.com/forums/21/topics/1244728-ai-tools-used-by-realtors
3. *"Where do I start with no technical person?"* — corpus: `dont_know_where_to_start` n=34, save 0.0346 · web: 45 % lack technical expertise, https://www.goldmansachs.com/pressroom/press-releases/2026/small-businesses-embrace-ai-but-need-training-and-support-to-fully-harness-it *(FOUNDERS flagged 403 — verify)*
4. *"How does one job — follow-up, call notes, listing write-ups — get handled?"* — corpus: sales follow-up n=30, share 0.0188; meeting notes n=12, save 0.0471 · web: same BiggerPockets threads
5. *"What does it cost before I commit?"* — corpus: 35 reels quote a price vs 97 selling free access · web: "what are some associated costs around it?", same thread
6. *"Am I safe with client data?"* — corpus: `quality_trust` n=25, share 0.0133 · web: 70 % of adopters report privacy concerns, https://servicedirect.com/resources/small-business-ai-report/

**Seed questions:** (a) yes — the only persona who genuinely asks it, and the corpus says answer it as a *demo*, not a framework · (b) yes · (c) yes · (d) yes.

### NF1 — "Marta", operations / marketing ops manager, 15–60-person services firm, **AI level 3/10**
1. *"My boss named a process — how do I automate it?"* — corpus: (c) n=103, lift 3.02 · web: "I got a job to do, my boss ask me", https://community.make.com/t/crm-with-a-trigger-on-my-fb-campaigns/74956
2. *"How do meetings become notes and actions without retyping?"* — corpus: n=12, save 0.0471 (highest), lift 0.70 · web: https://community.make.com/t/building-an-automated-meeting-minutes-pipeline-in-make-com.../105203
3. *"What will it cost before I commit?"* — corpus: tokens/credits n=27, save 0.0339 · web: "I was surprised when my OpenAI bill came through", https://community.make.com/t/does-anyone-else-spend-too-much-on-ai-costs/89571
4. *"Who is responsible when it gets it wrong?"* — corpus: `quality_trust` n=25; **human-review language in only 3 of 274 reels** — M2's signature move is absent from the niche · web: 56 % have made work mistakes because of AI, https://kpmg.com/xx/en/our-insights/ai-and-technology/trust-attitudes-and-use-of-ai.html
5. *"How do I get my boss and team to agree?"* — corpus: **9 permission reels; team-adoption n=6, share 0.00072, lift 0.39** · web: 6 rows, https://www.askamanager.org/2025/10/i-havent-returned-the-book-a-coworker-lent-me-4-years-ago-boss-wont-let-us-use-ai-transcription-and-more.html
6. *"How do I stop my team producing AI slop?"* — corpus: n=6, lift 0.68 · web: "a ChatGPT wall of text that's hundreds of words long", https://workplace.stackexchange.com/questions/202364/

**Seed questions:** (c) yes, dominant · (d) yes · (b) only as "which one for *this* task" · (a) no.

## 4. Reframes

- **(a) what is AI** → never a promise; the first ten seconds of a demo. I-05: demo-first hooks lift 5.81 vs 1.80.
- **(b) which tool** → not "A vs B" (n=12, share 0.0070) but one tool doing your job, on screen (n=62, save 0.0303). I-08/I-09: a screen on camera is the dataset's most reliable finding.
- **(d) cost** → not a budget estimate. Two travelling shapes: an honest monthly figure on a named plan (n=24, share 0.0219), or the free path (n=97).
- **(c) automate process N** → the one seed question to answer literally. Best cluster in the corpus, top cluster in both web lenses.
