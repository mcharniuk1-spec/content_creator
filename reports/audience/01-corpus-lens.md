# CORPUS evidence for M2 Lab personas

Source: `data/radar.db` + `data/analysis/transcripts/*.json` (274 files, contract `ta-v1`).
Scripts actually run: `persona_corpus_query.py`, `_query2.py`, `_query3.py`, `_query4.py` (this folder).

## 0. Denominators and the one caveat that governs everything

| set | n | med share_rate | med save_rate | med view_lift |
|---|---:|---:|---:|---:|
| Full ingested corpus, play ≥ 100 | 3 209 | 0.00575 | 0.01307 | 0.00 |
| Analysis-ready (274 transcripts; 272 with features, 268 with play ≥ 100) | 268 | 0.01520 | 0.02779 | 2.03 |

The 274 are the **top of `score.py`'s ranking**, not a random sample (I-01). Absolute rates are inflated ~2.6x; only **within-274 differences** carry information.

---

## 1. Who the reels address

`semantics.audience` + `audience_stage` + `interpretation.audience_tension`, regex buckets, overlapping. n = 274.

| audience label named by the speaker | n | med share | med save | med lift |
|---|---:|---:|---:|---:|
| founder / startup / solopreneur | 51 | 0.0161 | 0.0337 | 2.73 |
| creator / content / editor | 50 | 0.0166 | 0.0306 | 2.41 |
| developer / engineer / coder | 49 | 0.0160 | 0.0289 | 1.98 |
| agency / consultant / freelancer | 43 | 0.0174 | 0.0310 | 2.48 |
| beginner / non-technical / student | 32 | 0.0172 | **0.0359** | 1.75 |
| business owner / SMB / local business | 28 | **0.0174** | 0.0273 | 1.12 |
| marketer | 22 | 0.0168 | 0.0343 | 1.90 |
| AI practitioner / agent builder | 15 | 0.0168 | 0.0306 | **4.51** |
| employee / 9-to-5 / manager / professional | 14 | 0.0160 | 0.0285 | 2.01 |
| ai-curious / news follower | 9 | 0.0168 | 0.0103 | 1.15 |
| money / side-hustle seeker | 4 | 0.0163 | 0.0259 | 5.80 |
| **no audience label extractable** | 57 | — | — | — |

Mutually exclusive four-way split (priority founder > employee > developer > learner; 36 reels matched 2+ buckets):

**founder/owner 98 · developer 42 · employee/manager 20 · learner/beginner 16 · none of the four 98.**

Direct second-person address ("if you're…", "for anyone…") appears in **119 of 274** reels, 156 phrases — but 108 of the 156 name no audience: they are comment-gates, not audience definitions.

> `DX9kWTYzssE` — "If you want to implement it for your business, then DM me"
> `DZ5H6F1Rz1S` — "if you're running your Hermes agents on a Mac mini like I am"

**Silent on:** company size, revenue, headcount, industry, seniority — no `ta-v1` field records them.

---

## 2. What questions the reels answer

Regex over hook + thesis + problem + all beats + caption, plus `solution_type`. Overlapping.

| cluster | n | med share | med save | med lift |
|---|---:|---:|---:|---:|
| (c) how can process N be automated | 103 | 0.0169 | 0.0340 | **3.02** |
| (d) cost / price / expenses (broad) | 162 | 0.0167 | 0.0317 | 2.06 |
| (e4) how to make money with AI | 63 | 0.0136 | 0.0308 | 1.58 |
| (e3) how do I start / first step | 40 | **0.0176** | 0.0346 | 2.57 |
| (a) what is AI / how it works | 38 | **0.0107** | **0.0220** | 1.71 |
| (e5) what just shipped | 31 | 0.0160 | **0.0155** | 1.22 |
| (e2) is it safe / can I trust it | 29 | 0.0107 | 0.0314 | 2.36 |
| (b) which tool for a task | 22 | **0.0068** | **0.0147** | 1.19 |
| (e1) will AI replace me | 3 | 0.0233 | 0.0365 | 13.70 |
| **baseline, all 274** | 274 | 0.0152 | 0.0278 | 2.03 |

Canonical `pain` enum (n = 272), which is a closed vocabulary and therefore the harder number:

| pain | n | share | save | lift |
|---|---:|---:|---:|---:|
| cost_money | 51 | 0.0163 | 0.0305 | 1.96 |
| dont_know_where_to_start | 34 | 0.0175 | 0.0346 | 1.34 |
| keeping_up_with_ai | 29 | 0.0161 | 0.0181 | 1.73 |
| quality_trust | 25 | 0.0133 | 0.0275 | 1.63 |
| missing_skills | 25 | 0.0097 | 0.0246 | 1.34 |
| time_waste | 21 | **0.0199** | 0.0365 | 3.54 |
| chaos_no_process | 18 | 0.0138 | 0.0264 | 0.87 |
| manual_repetition | 16 | 0.0166 | **0.0415** | **13.66** |
| scaling_without_hiring | 8 | **0.0209** | 0.0359 | 4.83 |
| tool_overload | 8 | 0.0144 | 0.0217 | 2.98 |
| fear_of_replacement | 8 | 0.0153 | 0.0126 | 2.11 |
| slow_response_to_leads | 5 | 0.0001 | 0.0001 | 0.47 |

Verbatim pains:
> `DYuivWzSj5k` — "sources leads, writes outreach and chases follow-ups by hand, every day"
> `DNA7-d3o5sQ` — "needs someone answering the phone and booking appointments without paying a receptionist"
> `DZpi9FxoilB` — "every additional client requires hiring and training another junior, which caps the practice"
> `Dc16Un-KnPx` — "bouncing between ten different AI tools, several of them paid, for jobs one site can…"

---

## 3. Named tasks and processes

Mentions in beats + captions + semantics, n = 274. Tools from `semantics.tools_mentioned` (440 distinct, 693 mentions; **68 reels name no tool at all**).

| task / process | n | share | save | lift | tools most attached |
|---|---:|---:|---:|---:|---|
| coding / app building | 144 | 0.0148 | 0.0312 | 2.27 | GitHub 31, Claude 21, Claude Code 30 |
| content / video / posts | 130 | 0.0168 | 0.0303 | 2.09 | GitHub 14, YouTube 11, Claude 11 |
| website / landing page / design | 65 | 0.0174 | 0.0261 | 2.11 | Claude Code 9, GitHub 6, 21st.dev 3 |
| research / analysis / reports | 49 | 0.0154 | 0.0305 | 1.57 | Claude 9, GitHub 7 |
| lead gen / outreach / cold email | 48 | 0.0165 | 0.0347 | 1.95 | Claude 9, LinkedIn 5, Apify 3 |
| scheduling / calendar / booking | 35 | 0.0136 | 0.0231 | 1.73 | Google Calendar 5 |
| sales calls / follow-up | 30 | 0.0188 | 0.0261 | 1.80 | CRM 2, Claude 3 |
| hiring / recruiting / HR | 25 | 0.0175 | 0.0320 | **3.47** | Claude 3 |
| customer support / chatbot | 17 | **0.0195** | 0.0242 | **5.85** | WhatsApp 2, Claude 3 |
| data entry / spreadsheets / CRM | 15 | 0.0158 | 0.0285 | 1.90 | Excel 4, Sheets 2, CRM 3 |
| meeting notes / transcription | 12 | 0.0131 | **0.0471** | 0.70 | Apify 2, Claude Code 2 |
| SEO / ads | 12 | 0.0158 | 0.0311 | 1.82 | Claude 2, Reddit 2 |
| voice agents / phone | 10 | 0.0130 | 0.0266 | 4.55 | VAPI 1, n8n 1 |
| proposals / quotes / contracts | 9 | 0.0161 | 0.0305 | 0.81 | VAPI, WAP |
| invoices / bookkeeping / finance | 7 | 0.0150 | 0.0186 | 0.76 | QuickBooks 1 |
| email / inbox management | 4 | 0.0111 | 0.0308 | 3.32 | Gmail 2 |
| social DMs / community | 3 | 0.0220 | 0.0429 | 22.23 | ManyChat 2, OpenReply 2 |

The back-office processes M2's positioning is built on — invoices 7, proposals 9, email 4, meeting notes 12, data entry 15 — are **the smallest cells in the corpus**, and most sit below baseline lift. The corpus is dominated by build-a-thing and make-content.

---

## 4. Cost talk

| pattern | n | share | save | lift |
|---|---:|---:|---:|---:|
| any money talk (broad) | 158 | 0.0165 | 0.0319 | 2.11 |
| "free" / free tier / no cost | 97 | 0.0166 | 0.0307 | 1.96 |
| explicit `$` amount | 35 | 0.0139 | 0.0284 | 2.12 |
| tokens / credits / API bill | 27 | 0.0122 | 0.0339 | 2.06 |
| subscription / per-month | 24 | **0.0219** | 0.0281 | **3.17** |
| replacing a paid human/tool | 3 | 0.0114 | 0.0284 | 0.16 |

`numbers_used` holds **80 money entries** across 72 distinct values. The recurring ones: `$20 plan` (2), `$100 plan` (2), `$200 plan` (2), `$1` (3), `$10,000` (2), `thousands of dollars` (2), `1.6 billion free tokens every month` (2). Long tail: `$5,000 up front`, `$750 a month`, `$15 to $69 a month`, `$22,000 every single year`, `95 rupees per month`, `$8.50`.

> `DU9OIJUCBQz` — "They want to build with AI agents but cannot tell whether that means $20, $100…"
> `DK9pFUjPQcx` — "You don't have to pay hundreds of dollars for api keys anymore." (play 427 950, share 0.0425)
> `DbVq4mwz38L` — "Manichat is what most people pay for this, anywhere from $15 to $69 a month"

The dominant frame is **not** "what will this cost me" — it is **"here is how to not pay"**: 97 free-access reels against 35 that quote a price. `cost_money` is the single largest pain (51) and `pain_raw` reads as *bill shock from the tools*, not *budget for a project*.

---

## 5. What contradicts the seed questions

1. **(a) "what is AI / how it works" underperforms.** n = 38, share 0.0107 vs baseline 0.0152 (−30 %), save 0.0220 vs 0.0278 (−21 %). The strict version, `solution_type = framework_mental_model`, is worse: **n = 26, share 0.0092, save 0.0135** — under half the baseline save, against `resource_handoff` ("take this file") at n = 39, save **0.0429**. I-29 agrees on its own denominator. The niche does not save a way of thinking.
2. **(b) "which tool for X" is the weakest cluster measured.** n = 22, share **0.0068** (−55 %), save **0.0147** (−47 %); `solution_type = comparison` n = 12, share 0.0070. Head-to-head comparison loses; `tool_walkthrough` — one tool, shown running — does not (n = 62, save 0.0303).
3. **(d) cost is a real pain framed the wrong way.** 51 `cost_money` reels perform at baseline (share 0.0163, save 0.0305); the winning treatment is a free-access workaround, not a budget estimate.
4. **The corpus does not serve M2's stated audience.** Only **10 of 274** reels name a non-technical or no-code audience, against 47 naming developers and 27 naming small-business owners (I-27 replicated). Those 10 carry save **0.0424** (vs 0.0278) but view_lift **0.78** (vs 2.03) — non-technical content is *kept*, not *travelled*.
5. **`funnel_role = trust`** — the explain-and-earn-credibility register M2 plans to live in — is the worst-performing role: n = 58, share 0.0091 vs 0.0165 (awareness) and 0.0174 (conversion).
6. **`slow_response_to_leads`** (n = 5) posts share 0.0001 — effectively zero. A classic SMB automation pain that the niche does not know how to make travel.

---

## 6. Candidate personas (from this corpus only)

Company size, revenue and industry are **not in the data**. Where they appear below they are marked `[NO CORPUS EVIDENCE]`.

### P1 — The solo operator who is the bottleneck
Founder / agency owner / consultant doing the delivery work themselves. **AI level 3–5** (evidence: 28 reels classify `audience_stage` as "already using AI", 12 as "tried it, not systematic"). Size `[NO CORPUS EVIDENCE]`.
Largest single bucket in the corpus: **98 of 274** four-way, 51 founder + 43 agency + 28 owner overlapping.

1. *"How do I stop doing this same thing by hand every day?"* — `manual_repetition` n=16, save **0.0415**, lift **13.66** — the highest-lift pain measured. `DYuivWzSj5k` "sources leads, writes outreach and chases follow-ups by hand, every day".
2. *"How do I take on more clients without hiring?"* — `scaling_without_hiring` n=8, share 0.0209, lift 4.83. `DZpi9FxoilB` "every additional client requires hiring and training another junior".
3. *"Which repeated process should I automate first?"* — cluster (c) n=103, lift **3.02**, the best-performing question cluster.
4. *"My tools and agents are scattered — how do I get one map?"* — `chaos_no_process` n=18 but **share 0.0138, lift 0.87, below baseline**. Real pain, weak content record. `DbcPo0dMQ3d`.
5. *"What is this actually going to cost me per month?"* — subscription cluster n=24, share **0.0219**, lift 3.17.
6. *"How do I get leads answered faster?"* — `slow_response_to_leads` n=5, share 0.0001. Named, never landed.

### P2 — The behind-and-hiding non-technical professional
Marketer / realtor / coach / accountant who suspects they are late. **AI level 1–3**. Roles evidenced: `DdCgx_ci6zj` realtors, `DZpi9FxoilB` chartered accountants, `Dc0vBUOjyoQ` coaches, `Dcwk9ebO1qY` freelancers.
Thin but distinctive: **10 reels**, save 0.0424 (+53 % vs baseline), lift 0.78 (−62 %).

1. *"Where do I even start?"* — `dont_know_where_to_start` n=34, save 0.0346; cluster (e3) n=40, share **0.0176**, lift 2.57.
2. *"Am I allowed to do this without knowing how to code?"* — `missing_skills` n=25, share **0.0097**, save 0.0246 — the worst-sharing large pain. `Dc4OPuWRwLQ` "aspiring AI agency founders who think they are not technical enough".
3. *"I don't know the words people are using."* — `DdCvFdHsnj1` "non-technical professionals who feel behind on AI vocabulary" (play 283 515, save 0.0581).
4. *"Can I trust what it produces?"* — `quality_trust` n=25, cluster (e2) n=29, save 0.0314.
5. *"Will this replace my job?"* — `fear_of_replacement` n=8, save **0.0126**, lowest of any pain. Fear travels (`Dc_tsSeAjBy` share 0.0613) and is never kept; I-14 finds fear language negative on share.
6. *"Which of ten tools do I need?"* — `tool_overload` n=8, lift 2.98.

### P3 — The builder-operator already paying token bills
Solo builder / practitioner running agents. **AI level 6–8** — above M2's stated 0–6 ceiling.
**42** developer-bucket + **15** practitioner-labelled. Highest lift of any audience label (4.51).

1. *"How do I cut my token/API bill?"* — `cost_money` n=51 largest pain; tokens cluster n=27, save 0.0339. `DK9pFUjPQcx` "spending hundreds of dollars on API keys to experiment with models".
2. *"Which repo/skill do I install?"* — `resource_handoff` n=39, save **0.0429**, the top save of any solution type. `Dct6Op3n6Zd` "4 GitHub Repos went viral this week and barely anyone's actually using them yet" (save 0.0759).
3. *"How is this agent architected end to end?"* — `agent_build` n=23, lift **6.33**.
4. *"Did I miss something that shipped?"* — cluster (e5) n=31, save **0.0155**, half baseline.
5. *"Is my setup exposed?"* — `Dbi-yxNgrhG` "If you don't have these four settings, you can access any private documents or bank…" (share 0.0584).

**The corpus's strongest performer and the one POSITIONING §4 and §8 explicitly refuse** (I-25: agent building lift 6.63 and Claude Code skills 4.36 are the top-lift topics, both on the do-not-publish list). Carry it as the audience M2 *declines*.

### P4 (weak, flag as thin) — The income-seeker
`money/side-hustle` n=4 (lift 5.80); cluster (e4) n=63 but share **0.0136**, below baseline. Reads as a frame bolted onto other content, not an audience. §5 rules it out — drop unless the web agents find it independently.

---

## 7. Where the corpus is silent

- **Company size, revenue, headcount, industry, country, seniority, budget authority** — no field records any of them.
- **Who the buyer is vs who the user is** (§4's Buyer/Champion/User table) — the corpus records one addressee per reel and never a decision chain.
- **Whether the audience acts.** Every metric is share/save/play. I-12: comment-gates inflate save 2.8x and share 1.8x while suppressing distribution, so saves in gated reels measure the gate, not intent.
- **57 reels (21 %) have no extractable audience; 68 name no tool.**
- **None of this is M2's own audience.** 274 reels by 132 other creators, pre-filtered to winners. It says what the niche's *supply* rewards, not what a non-technical small-business leader wants — the corpus barely contains one (10 of 274).
