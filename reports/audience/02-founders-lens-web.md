# FOUNDERS lens — what non-technical owners of 1–50-person businesses actually ask about AI

**Method note / limitation, read first.** Reddit is not reachable from this environment: `reddit.com` is blocked for both WebFetch and the search tool ("domains not accessible to our user agent"), and reddit's JSON endpoints return an HTML block page. So none of r/smallbusiness, r/Entrepreneur, r/sweatystartup, r/msp etc. could be mined directly. Substitutes used: Shopify Community (real merchant threads, dated), BiggerPockets forums (agents/investors/property managers), Hacker News, Quora question titles surfaced by search, plus 12 dated surveys. The voice sample therefore skews e-commerce + real estate; trades, clinics and agencies are represented by surveys only, not by their own words — **no direct-voice evidence found** for trades/clinics/agency owners.

## 1. Evidence table

Clusters: (a) what is AI / how it works · (b) which tool for a task · (c) how can process N be automated · (d) cost · (e) trust/risk/privacy · (f) replace people / hiring · (g) where do I start / overwhelmed · (h) other.

| # | Source URL | Date | Who is asking | Their words (≤15 words) | Cluster |
|---|---|---|---|---|---|
| 1 | https://community.shopify.com/t/ai-for-small-business/399379 | 9 Mar 2025 | indigooctopus, US "mom-and-pop" multi-brand retailer | "Our vendors have suggested in 2025 we need to get onto AI" | a / h |
| 2 | same thread | 9 Mar 2025 | same | "What are some steps can we take to make sure we do not become obsolete?" | g |
| 3 | https://community.shopify.com/t/chatgpt-shopify-querying-with-privacy/414591 | 16 May 2025 | marie-lav, store owner with large order dataset | "I dont want to share customer names, emails or order ids" | e |
| 4 | https://community.shopify.com/t/ai-platforms-running-your-business/552674 | 31 Jul 2025 | ScentedAromas, UK small store, low traffic | "Has anyone tried any AI apps that help run your store?" | b |
| 5 | same thread (found Sintra AI at ~£100/month, judged prohibitive) | 31 Jul 2025 | same | reply frame: does it save "more in time/labor than it costs" | d |
| 6 | https://community.shopify.com/t/beyond-chat-bot-what-ai-tools-for-customer-service/570717 | 15 Oct 2025 | WingSpan, merchant | "what other ai tools can help with things like customer behaviour tracking?" | b |
| 7 | https://community.shopify.com/t/how-are-you-using-ai-tools-for-your-marketing-efforts/570719 | 15 Oct 2025 | Jacqui, merchant | "How are you using AI tools for your marketing efforts?" | c |
| 8 | https://community.shopify.com/t/how-can-i-use-ai-tools-to-improve-my-shopify-store-s-product/573208 | 30 Oct 2025 | Osiaro1, merchant | "Has anyone tried specific tools or integrations that work well with Shopify?" | b |
| 9 | https://community.shopify.com/t/using-ai-for-running-my-business/630061 | 30 May 2026 | Ish.entrepreneur, owner running digital ops | wants AI for "monotonous day to day tasks"; "I have to keep asking it questions" | c |
| 10 | https://community.shopify.com/t/getting-traffic-from-chatgpt-ai-agents-where-do-i-even-start/667253 | 16 Aug 2026 | olgapapodoki, individual store owner | "How do I actually get more traffic from ChatGPT?" | g |
| 11 | https://community.shopify.com/t/ai-tools-that-can-build-a-whole-shopify-store/668092 | 18 Aug 2026 | Felicia9, store builder/owner | "Is there anything that actually builds the whole store for you?" | c |
| 12 | same thread | 18 Aug 2026 | same | "looking for a way to speed up that initial build without losing control" | e |
| 13 | https://community.shopify.com/t/how-are-you-using-chatgpt-claude-or-any-other-ai-agent-to-actually-manage-your-shopify-store/675818 | 2 Sep 2026 | vikasmaur13, merchant | "what are you actually using AI for in your Shopify store today?" | c |
| 14 | https://community.shopify.com/t/many-ai-choices-which-is-best-at-what/676369 | 3 Sep 2026 | WingSpan, dropshipping owner | "what tool would you recommend for each category? And what's the pros and cons" | b / g |
| 15 | https://community.shopify.com/t/ai-tool-recommendations-for-running-store/676450 | 4 Sep 2026 | mary123, supplements store owner | "writing compliant product copy and answering repetitive support tickets takes up most of my day" | c |
| 16 | same thread | 4 Sep 2026 | same | wants 2–3 essential tools "without over-complicating my workflow" (paraphrase of stated aim) | g |
| 17 | https://www.biggerpockets.com/forums/21/topics/1244728-ai-tools-used-by-realtors | posted ~2025 ("1 year ago") | Simran Miglani + replying agents/brokers | "What are some of the AI tools that real estate agents are using, in 2025?" | b |
| 18 | same thread | ~2025 | same OP | "How is it providing value, and what are some associated costs around it?" | d |
| 19 | same thread | ~2025 | Bruce Lynn, real-estate broker, Coppell TX | "I've not had much luck with that so far. I don't like the descriptions" | e / h |
| 20 | https://www.biggerpockets.com/forums/48/topics/1236774-how-are-you-using-ai-in-real-estate | ~2025 | Bob Lachance, specialist, West Hartford CT | "How Are You Using AI in Real Estate?" | c |
| 21 | same thread | ~2025 | Michael J., replier | "Some chatbot replies feel… robotic. People still want a human touch." | e |
| 22 | https://news.ycombinator.com/item?id=42629498 | 11 Jan 2025 | Ask HN poster (business-buyer framing) | "Most 'agents' sound like workflow automations that have been around forever." | a |
| 23 | https://www.quora.com/How-do-I-use-AI-to-automate-my-small-business | undated (title only; page 403 on fetch) | Quora asker | "How do I use AI to automate my small business?" | c |
| 24 | https://www.quora.com/How-can-small-businesses-or-startups-practically-use-AI-to-grow-faster | undated (title only) | Quora asker | "How can small businesses or startups practically use AI to grow faster?" | g |
| 25 | https://www.quora.com/How-do-I-integrate-AI-into-small-businesses | undated (title only) | Quora asker | "How do I integrate AI into small businesses?" | c |

**Counts per cluster (25 rows):** (a) 2 · (b) 5 · (c) 7 · (d) 2 · (e) 4 · (f) 0 · (g) 4 · (h) 1 (+2 shared with a/e).

**The (f) hole is real and worth noting:** in this sample no owner asked "will AI replace my staff / should I still hire". Founders asked how to get their own day back, not how to cut headcount. Do not invent this angle — **no evidence found** in owner voices; the only adjacent data point is a survey one (US Chamber: 82% of AI-using small businesses reported workforce expansion).

## 2. Concrete tasks founders name, ranked by frequency in these sources

1. **Customer support / repetitive inbound questions** (rows 6, 15, 21; Service Direct 46%; Shopify threads repeatedly)
2. **Marketing content: product copy, descriptions, ad copy, social posts** (rows 7, 8, 15; US Chamber 46% marketing; NFIB 27%; Verizon 28%)
3. **Written communication — emails, documents, listing descriptions** (row 17 replies; NFIB 29% communications; Verizon 24%)
4. **Catalog / data cleanup in batches — titles, tags, CSV checks** (row 13 replies)
5. **Getting found by AI assistants (ChatGPT/Gemini as a new traffic source)** (rows 10, 14) — newer, ecommerce-specific, rising fast in 2026 threads
6. **Analytics / weekly numbers review, market and deal analysis** (rows 3, 13, 20)
7. **Lead qualification and follow-up** (row 20; Indie Hackers founder-automation lists)
8. **Scheduling / bookings / missed calls** (row 20 replies; property-manager thread)
9. **Quotes, invoices, bookkeeping** — named mostly by vendors and surveys, **not** by owners in the threads I could reach (US Chamber: payroll 44%; QuickBooks invoicing content). Weak owner-voice evidence.
10. **Hiring/HR** — thinnest of all; one secondary stat only.

## 3. Survey numbers (with citations)

| Statistic | Source | Date |
|---|---|---|
| 58% of US small businesses use generative AI (23% in 2023); n=3,870 firms <250 staff, fielded 6–26 Jun 2025 | https://ipwatchdog.com/2025/08/18/us-chamber-report-small-businesses-rapidly-adopting-ai-despite-regulatory-concerns/ (US Chamber C_TEC/Teneo) | Aug 2025 |
| Top AI uses: marketing/promotions 46%, payroll 44%, CRM 42%; 63% use externally built tools, only 8% build in-house | same | Aug 2025 |
| 68% of small businesses use AI regularly (48% in Jul 2024); 28% daily | https://quickbooks.intuit.com/r/small-business-data/april-2025-survey/ | Apr 2025 |
| 77% of US SMBs use AI regularly as of Jan 2026 (QuickBooks 2026 AI Impact Report) | https://quickbooks.intuit.com/r/running-a-business/agentic-ai-for-business/ | 2026 |
| Only 24% of NFIB members use any AI; 27% marketing/advertising, 29% communications; 63% expect AI to matter in their industry within 5 years; n=521, fielded 6–31 Mar 2025 | https://www.nfib.com/news/press-release/new-nfib-report-how-small-businesses-incorporate-tech-and-ai-advancements/ | Jun 2025 |
| 17.7% of US small businesses had adopted AI by end-2025 (1.7% in Jan 2019); construction 8.9%, professional services 30.3% | https://www.jpmorganchase.com/institute/all-topics/business-growth-and-entrepreneurship/understanding-ai-use-by-small-businesses | 2026 |
| Median monthly AI spend by small businesses fell from ~$80 (2022) to $28–31 (2025) as newcomers enter at $20–30 price points | same | 2026 |
| 38% of SMBs actively integrating AI; 28% marketing/social, 24% written communications; n=600 US SMBs | https://www.verizon.com/about/news/2025-state-small-business-survey | May 2025 |
| 76% of small businesses using or exploring AI; 25% integrated into daily operations; 82% say AI is essential to compete; n≈1,000, revenue $25k–$5M | https://www.reimaginemainstreet.org/ai-and-small-business-survey | Jun 2025 |
| 29% of store owners not using AI said they "were not sure what AI tools can do" (2025 Shopify survey) | https://www.shopify.com/blog/ai-for-small-business | 2025 |
| Non-adopters: 62% cite lack of understanding of AI's benefits, 60% lack of in-house resources; adopters: 70% data/privacy concerns | https://servicedirect.com/resources/small-business-ai-report/ | 2025 |
| 31% of SMEs across G7 use generative AI (24% Japan → 39% Germany); 54% worry about copyright/legal issues and what happens to information fed into models | https://www.oecd.org/en/publications/generative-ai-and-the-sme-workforce_2d08b99d-en.html | 2025 |
| EU: 20.0% of enterprises with 10+ staff use AI; only 17% of small firms (10–49 staff) vs 55% of large | https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20251211-2 | 11 Dec 2025 |
| 30% of desk workers have had no AI training; 61% have spent under five hours learning AI | https://www.eweek.com/news/workforce-ai-adoption-slowdown/ (Slack Workforce Index) | 2025 |
| 88% of companies use AI in at least one function, but only 29% of companies under $100M revenue have reached scaling | https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai | 2025 |
| Goldman Sachs 10KSB Voices: 76% use AI, 47% find it hard to choose the right tools, 45% lack technical expertise, 14% fully embedded, 88% want more training | https://www.goldmansachs.com/pressroom/press-releases/2026/small-businesses-embrace-ai-but-need-training-and-support-to-fully-harness-it | Mar 2026 |

Two caveats, stated plainly. (i) The Goldman page returned HTTP 403 on direct fetch; the figures above come from the search index of that page — **verify before publishing**. (ii) The numbers disagree with each other by a wide margin (17.7% JPMC transaction data vs 77% QuickBooks self-report vs 24% NFIB). Self-reported "do you use AI" surveys run 3–4× higher than behaviour-based measures. If M2 Lab ever quotes an adoption number on camera, quote the method with it.

## 4. Two proposed FOUNDER personas

### Persona F1 — "Mary, the supplements store owner" (e-commerce, AI level 4/10)

Owner-operator of a 4-person online supplements brand (Shopify, UK/EU shipping). Tools: Shopify + Shopify Magic/Sidekick, ChatGPT free or Plus, Canva, a helpdesk. Pays for nothing above ~£30/month without a fight. Writes her own product copy and answers her own tickets.

1. **"I want to know which 2–3 tools I actually need, not twenty."** — mary123: wants tools "without over-complicating my workflow"; WingSpan asks "what tool would you recommend for each category?" (https://community.shopify.com/t/ai-tool-recommendations-for-running-store/676450, 4 Sep 2026; https://community.shopify.com/t/many-ai-choices-which-is-best-at-what/676369, 3 Sep 2026)
2. **"I want to know how my support inbox can be automated without me losing control of what customers are told."** — "answering repetitive support tickets takes up most of my day" (same thread); reply guidance: answer "ONLY from the merchant's own catalogue and published policies"
3. **"I want to know what it will cost per month and when it stops being worth it."** — UK owner rejected a £100/month AI platform; thread frame is whether it saves more "in time/labor than it costs" (https://community.shopify.com/t/ai-platforms-running-your-business/552674, 31 Jul 2025). Median small-business AI spend is $28–31/month (JPMC, 2026)
4. **"I want to know if it is safe to put my customer and order data into these tools."** — "I dont want to share customer names, emails or order ids" (https://community.shopify.com/t/chatgpt-shopify-querying-with-privacy/414591, 16 May 2025); 54% of SMEs worry what happens to information fed into models (OECD, 2025)
5. **"I want to know how to get my products found inside ChatGPT and Gemini."** — "How do I actually get more traffic from ChatGPT?" (https://community.shopify.com/t/getting-traffic-from-chatgpt-ai-agents-where-do-i-even-start/667253, 16 Aug 2026)
6. **"I want to know how to do catalogue and content work in batches instead of one product at a time."** — "export 20 to 50 products at a time, have AI clean titles, descriptions, tags" (https://community.shopify.com/t/how-are-you-using-chatgpt-claude-or-any-other-ai-agent-to-actually-manage-your-shopify-store/675818, 2 Sep 2026)
7. **"I want to know which marketing jobs AI can take and which still need me."** — "How are you using AI tools for your marketing efforts?" (https://community.shopify.com/t/how-are-you-using-ai-tools-for-your-marketing-efforts/570719, 15 Oct 2025)
8. **"I want to know whether I am already behind."** — 29% of non-using store owners "were not sure what AI tools can do" (Shopify survey, 2025); 82% of small businesses say AI is essential to compete (PayPal/Reimagine Main Street, Jun 2025)

Not in evidence for F1: hiring/replacement worries, ROI-guarantee questions — **no evidence found**.

### Persona F2 — "Bruce, the local services / property broker" (offline services, AI level 2/10)

Owner of a 6–12 person local services firm (real-estate brokerage, property management, trades or clinic profile). Tools: a CRM he half-uses, WhatsApp/email, spreadsheets, maybe free ChatGPT on his phone. Has tried AI once, been unimpressed, and has no one to ask.

1. **"I want to know what AI actually is, beyond the hype."** — "Most 'agents' sound like workflow automations that have been around forever" (https://news.ycombinator.com/item?id=42629498, 11 Jan 2025); 62% of non-adopters cite lack of understanding of AI's benefits (Service Direct, 2025)
2. **"I want to know what other people in my trade actually use it for."** — "How Are You Using AI in Real Estate?" (https://www.biggerpockets.com/forums/48/topics/1236774, ~2025); "What are some of the AI tools that real estate agents are using, in 2025?" (https://www.biggerpockets.com/forums/21/topics/1244728)
3. **"I want to know what it costs before I commit."** — same BiggerPockets thread: "what are some associated costs around it?"
4. **"I want to know why the output sounded fake when I tried it."** — "I've not had much luck with that so far. I don't like the descriptions it pops out" (Bruce Lynn, broker); "Some chatbot replies feel… robotic. People still want a human touch." (Michael J.)
5. **"I want to know how one repeated job — follow-up, listing write-ups, call notes — can be handled."** — same threads name lead screening, listing content, voice-to-text walkthroughs, CRM follow-up
6. **"I want to know where to start when I have no technical person."** — 47% of small business owners say it is hard to choose the right tools and 45% lack technical expertise; 88% want more training (Goldman Sachs 10KSB Voices, Mar 2026 — verify, page 403)
7. **"I want to know whether I am safe to use this with client data."** — 70% of small-business AI adopters report data and privacy concerns (Service Direct, 2025); 54% of SMEs worry about legal issues and data fed into models (OECD, 2025)
8. **"I want to know whether it is even relevant to a business like mine."** — construction AI adoption is 8.9% vs 30.3% in professional services (JPMorganChase Institute, 2026); NFIB: only 24% of members use AI, yet 63% expect it to matter within five years (Jun 2025)

Not in evidence for F2: pricing sensitivity thresholds in his own words, staff-replacement intent, and any trades/clinic-specific quote — **no evidence found** (Reddit blockade; trades forums either paywalled via tollbit or returned no AI threads).

## 5. What this means for M2 Lab positioning (one paragraph)

The dominant cluster is (c) "how can process N be automated" (7 rows), then (b) tool choice (5) and (g) where-to-start (4). That is exactly the POSITIONING.md method — repeated workflow → fragmentation → AI boundary → human review. The two under-served asks M2 can own without over-claiming: the **cost question** (owners get a £100/month quote and no way to judge it; the honest benchmark is $28–31/month median spend) and the **control question** — "speed up that initial build without losing control", "answer ONLY from the merchant's own catalogue", "people still want a human touch". Nobody in this sample asked to fire anyone.
