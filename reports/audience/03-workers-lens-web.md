# M2 Lab — WORKERS lens (non-founder audience)

Scope: operations / marketing / sales / admin managers in small companies told to "figure out AI",
plus individual learners and senior specialists who want AI in their own job. Not developers.

## 0. Source-access note (read first)

**Reddit could not be used.** `reddit.com` is blocked for this agent's fetcher (WebSearch returns
`domains are not accessible to our user agent`; WebFetch returns `unable to fetch`). Every public
Reddit mirror I probed (redlib.catsarch.com, safereddit.com, redlib.privacyredirect.com,
red.artemislena.eu, redlib.nadeko.net and others) now sits behind an Anubis proof-of-work
anti-scraping gate. Bypassing bot protection is out of bounds, so I did not.
`askamanager.org`, `quora.com`, `classcentral.com`, `community.hubspot.com` and
`accountingweb.co.uk` return Cloudflare 403 to the same fetcher.

Substituted, and actually usable:
- **Stack Exchange "The Workplace"** — official public API, full question bodies, exact quotes.
- **community.make.com** (Discourse public search API) — the single richest vein of
  non-technical-worker voice found: office people describing the exact process they were told to
  automate. This is where most cluster (c) and (d) evidence comes from.
- **Ask a Manager** — titles and dates are verbatim from the search index; page bodies were not
  fetchable, so those rows are marked *(title only)*.
- **Google autocomplete** (public suggest endpoint) — real search phrasings, labelled as
  search demand, not as a person.
- Survey PDFs/pages (Gallup, Microsoft, Slack, Pew, KPMG, Coursera, WEF) — fetched directly.

23 distinct sources below; 15 of them are individual people asking a question.

## 1. Evidence table

Clusters: (a) what is AI · (b) which tool for a task · (c) how to automate process N ·
(d) cost · (e) trust/risk/privacy/policy · (f) will it replace me · (g) where do I start /
overwhelmed · (h) convincing boss/team · (i) other

| # | Source URL | Date | Who is asking | Their words (≤15 w) | Cluster |
|---|---|---|---|---|---|
| 1 | https://workplace.stackexchange.com/questions/198277/using-generative-ai-at-work | 2024-07-01 | Employee writing customer letters and reports; seniority/company size not stated | "form letters to customers and to write reports" … "What are my moral and employee responsibilities" | e |
| 2 | https://workplace.stackexchange.com/questions/202364/what-is-the-best-or-at-least-appropriate-way-to-deal-with-ai-slop-messages | 2025-08-05 | Technical team member receiving AI text from "the business or nontechnical side" | "a ChatGPT wall of text that's hundreds of words long" | i |
| 3 | https://workplace.stackexchange.com/questions/202244/startup-basically-mandating-ai-to-improve-velocity | 2025-07-11 | Developer, startup (out of lens; shows the mandate mechanic) | "the CTO has purchased AI coding subscriptions for everyone" | f |
| 4 | https://workplace.stackexchange.com/questions/203117/how-ai-excited-should-i-be-when-applying-for-work-or-in-job-interviews | 2026-01-26 | Fullstack developer, job-seeking (out of lens; shows AI-signalling anxiety) | "what is a smart choice when it comes to 'AI excitement'" | f |
| 5 | https://community.make.com/t/clickup-instagram-the-image-format-is-not-supported-36001-oauthexception/70635 | 2025-02-20 | **Traffic Manager** (marketing, mid-level), "also handle automation tasks" | "my boss asked me to create an automation to connect ClickUp" | c |
| 6 | https://community.make.com/t/crm-with-a-trigger-on-my-fb-campaigns/74956 | 2025-03-12 | Employee running Meta/Google ads + CRM | "I got a job to do, my boss ask me" | c |
| 7 | https://community.make.com/t/problem-connecting-an-elementor-and-brevo-form/77220 | 2025-04-01 | Person running a WordPress site and contact list | "I'm not a technical person, and I'm trying to navigate the various documentation" | g |
| 8 | https://community.make.com/t/how-much-do-ai-tools-cost/70924 | 2025-02-22 | Business user of a no-code tool | "It's not clear to me how much they will cost" | d |
| 9 | https://community.make.com/t/does-anyone-else-spend-too-much-on-ai-costs/89571 | 2025-08-14 | Automation builder with a live bill | "I was surprised when my OpenAI bill came through" | d |
| 10 | https://community.make.com/t/building-an-automated-meeting-minutes-pipeline-in-make-com-using-clova-note-google-drive-claude-ai-google-docs-but-hitting-a-wall-with-personal-google-account-connectivity/105203 | 2026-03-10 | Employee automating minutes for their team | "I want to automate the entire meeting minutes workflow" | c |
| 11 | https://community.make.com/t/how-i-automated-my-intake-meeting-process-end-to-end-recops-hr-use-case-one-trigger-three-outputs/113360 | 2026-08-13 | **Technical Talent Partner** (recruiting ops), first-time poster | "I'm a Technical Talent Partner … it's saved my team" | c |
| 12 | https://community.make.com/t/stripe-payouts-quickbooks-reconciliations-for-a-charity/111494 | 2026-06-29 | Finance/ops person, **small charity** | "I work for a small happiness research charity" | c |
| 13 | https://community.make.com/t/get-full-notion-page-content-ai-meeting-notes/111013 | 2026-06-18 | Notion user trying to reuse AI meeting summaries | "Notion's AI meeting summary block acts as an AI overlay" | b |
| 14 | https://community.make.com/t/i-offer-automation-services-germany-worldwide/81159 | 2025-05-04 | Agency owner selling automation to these people (demand-side proof) | "For the past two years, we've specialized in AI and automation" | i |
| 15 | https://www.askamanager.org/2025/07/can-i-be-fired-for-refusing-to-use-ai.html | 2025-07 | Employee, letter writer *(title only)* | "can I be fired for refusing to use AI?" | f |
| 16 | https://www.askamanager.org/2025/10/i-havent-returned-the-book-a-coworker-lent-me-4-years-ago-boss-wont-let-us-use-ai-transcription-and-more.html | 2025-10 | Employee whose org bought MS Copilot licences *(title only)* | "boss won't let us use AI transcription" | h |
| 17 | https://www.askamanager.org/2026/01/my-coworker-is-using-ai-to-do-her-work-badly.html | 2026-01 | Colleague/manager *(title only)* | "my coworker is using AI to do her work (badly)" | e |
| 18 | https://www.askamanager.org/2026/05/my-boss-has-been-taken-over-by-ai.html | 2026-05 | Employee reporting to an AI-obsessed boss *(title only)* | "my boss has been taken over by AI" | e |
| 19 | https://www.askamanager.org/2026/06/updates-the-ai-writer-mandated-manager-training-and-more.html | 2026-06 | Employees, follow-up letters *(title only)* | "the AI writer, mandated manager training" | h |
| 20 | Google autocomplete, `suggestqueries.google.com`, prefix "how does ai actually" | 2026-09-12 | Search demand, not a named person | "how does ai actually work" | a |
| 21 | Google autocomplete, prefix "what ai tool should i use" | 2026-09-12 | Search demand | "what ai tool can i use to create a powerpoint presentation" | b |
| 22 | Google autocomplete, prefix "how to learn ai for" | 2026-09-12 | Search demand | "how to learn ai for a job", "how to learn ai for accounting and finance" | g |
| 23 | https://www.gallup.com/workplace/699689/ai-use-at-work-rises.aspx | 2025-12-14 | Survey of 23,068 US employees | 26% of individual contributors don't know if their org adopted AI | g |
| 24 | https://slack.com/blog/news/the-fall-2024-workforce-index-shows-executives-and-employees-investing-in-ai-but-uncertainty-holding-back-adoption | 2024-11-12 | 17,372 desk workers, 15 countries | 48% uncomfortable telling their manager they used AI | e |
| 25 | https://www.pewresearch.org/social-trends/2025/02/25/u-s-workers-are-more-worried-than-hopeful-about-future-ai-use-in-the-workplace/ | 2025-02-25 | 5,273 employed US adults | 52% worried about future AI use at work; 33% "overwhelmed" | f |

**Cluster counts (n=25):** (a) 1 · (b) 2 · (c) 5 · (d) 2 · (e) 4 · (f) 4 · (g) 3 · (h) 2 · (i) 2

Read this as: the non-founder audience does **not** mostly ask "what is AI". They ask
*"how do I automate this exact thing my boss named"* (c), then *"am I allowed / will I get in
trouble"* (e) and *"am I safe"* (f). Cluster (a) is almost absent from people and shows up only
as anonymous search demand — which matches POSITIONING §4 ("They know AI exists and may have
tried ChatGPT").

## 2. Concrete tasks these people name, by frequency in my sources

| Rank | Task | Hits | Evidence |
|---|---|---|---|
| 1 | Meeting notes / minutes / transcription | 4 | rows 10, 11, 13, 16 |
| 2 | Reports and documents (drafting, RFPs, generating output docs) | 3 | row 1; https://community.make.com/t/ai-powered-rfp-document-generation-system/92069 (2025-09-16); row 21 (PowerPoint) |
| 3 | Email and customer messages | 2 | rows 1, 2 |
| 4 | CRM / lead capture / campaign routing | 2 | rows 5, 6 |
| 5 | Invoices, payouts, reconciliation | 2 | row 12; row 22 ("ai for accounting and finance") |
| 6 | Recruiting / intake interviews | 1 | row 11 |
| 7 | Document data extraction into a database or spreadsheet | 1 | https://community.make.com/t/app-update-gemini-3-8-flash-in-make/114592 (2026-09-07), user thread on extracting findings into a database (2026-03-04) |
| 8 | Social content planning/publishing | 1 | row 5 |
| 9 | Presentations | 1 | row 21 |
| — | Desk research / competitor research | 0 | **no evidence found** in the accessible sources |

## 3. Survey numbers

| Statistic | Number | Year | Source |
|---|---|---|---|
| US employees using AI at work at least a few times a year | 45% (from 40% in Q2 2025); frequent use 23%; daily 10% | Q3 2025, published 2025-12-14 | https://www.gallup.com/workplace/699689/ai-use-at-work-rises.aspx |
| Individual contributors who don't know whether their org adopted AI | 26% (vs 16% managers, 7% leaders) | 2025 | same |
| Global knowledge workers using gen AI at work | 75% | 2024 (n=31,000, 31 countries) | https://www.microsoft.com/en-us/worklab/work-trend-index/ai-at-work-is-here-now-comes-the-hard-part |
| **Bring-your-own-AI**: AI users using their own tools at work | 78% overall; **80% at small and medium companies** | 2024 | same |
| Hesitate to admit AI use on their most important tasks | 52% | 2024 | same |
| Worry that using AI makes them look replaceable | 53% | 2024 | same |
| Leaders who would not hire someone without AI skills | 66% | 2024 | same |
| Leaders worried their org lacks a plan and vision for AI | 60% | 2024 | same |
| **Training gap**: desk workers with under five hours of AI training | 61%; **30% had no training at all** | 2024 (n=17,372, 15 countries) | https://slack.com/blog/news/the-fall-2024-workforce-index-shows-executives-and-employees-investing-in-ai-but-uncertainty-holding-back-adoption |
| Uncomfortable telling their manager they used AI | 48% — reasons: "cheating" 47%, seen as less competent 46%, seen as lazy 46%, policy discourages it 21% | 2024 | same |
| Self-declared expert AI users | 7% | Aug 2024 | same |
| US workers worried about future AI use at work | 52%; overwhelmed 33%; hopeful 36% | fielded Oct 2024, published 2025-02-25 (n=5,273) | https://www.pewresearch.org/social-trends/2025/02/25/u-s-workers-are-more-worried-than-hopeful-about-future-ai-use-in-the-workplace/ |
| Workers who think AI leads to fewer job opportunities for them | 32% | 2025 | same |
| US workers actually using AI in their job | 21% (from 16% a year earlier); 28% of degree-holders, 16% of some-college-or-less | Sept 2025 (n=5,010 workers) | https://www.pewresearch.org/short-reads/2025/10/06/about-1-in-5-us-workers-now-use-ai-in-their-job-up-since-last-year/ |
| Non-users who think some of their work could be done with AI | 36% (from 31%) | 2025 | same |
| People using AI regularly; relying on output without checking accuracy; who made work mistakes because of AI | 66% / 66% / 56% | Nov 2024–Jan 2025, n=48,000+, 47 countries | https://kpmg.com/xx/en/our-insights/ai-and-technology/trust-attitudes-and-use-of-ai.html |
| Employees fearing they fall behind without AI | 65%; only 26% say leadership is clearly aligned on AI strategy | 2026 (n=20,000, 10 countries) | https://www.microsoft.com/en-us/worklab/work-trend-index/agents-human-agency-and-the-opportunity-for-every-organization |
| Employees treating AI output as a starting point, not the answer | 86%; 50% name quality control of AI output as a top human skill | 2026 | same |
| GenAI course enrolments among enterprise learners | +234% YoY, 14 enrolments per minute | published 2026-01-21 | https://blog.coursera.org/introducing-courseras-job-skills-report-2026-the-most-critical-skills-the-worlds-learners-need-this-year/ |
| Employers who say core skills will change by 2030 / plan AI upskilling | 39% of skills change; 85% plan to upskill | 2025 | https://www.weforum.org/ (Future of Jobs Report 2025, via https://www.shrm.org/topics-tools/flagships/ai-hi/future-of-jobs-report-2025-deep-dive) |

Two numbers matter most for M2 Lab: **80% BYOAI at SMEs** (the audience is already using AI
without permission or guidance) and **61% with under five hours of training / 30% with none**
(nobody has taught them). That is the exact gap POSITIONING §2 claims.

## 4. Two non-founder personas

### Persona W1 — "Marta", Operations & Marketing Ops Manager

- **Seniority:** mid-level manager, 2 direct reports, reports to the owner.
- **Company size:** 15–60 people, services/agency. Evidence: BYOAI is highest at SMEs, 80%
  (Microsoft WTI 2024); Make threads come from exactly this size of employer (row 12, "a small
  happiness research charity").
- **AI level:** 3/10. Uses ChatGPT daily for text, has never built anything repeatable.
- **Current tools:** ChatGPT (personal account), Microsoft Copilot licence bought by the company
  (row 16), Google Workspace, a CRM, ClickUp/Notion, a trial of Make or Zapier (rows 5, 6, 10).

Interests, in her words:

1. **"I want to know how the process my boss named can actually be automated."**
   Evidence: row 5, 2025-02-20 — "my boss asked me to create an automation to connect ClickUp";
   row 6, 2025-03-12 — "I got a job to do, my boss ask me".
2. **"I want to know how to turn our meetings into notes and actions without retyping them."**
   Evidence: row 10, 2026-03-10 — "I want to automate the entire meeting minutes workflow";
   row 16, 2025-10 — "boss won't let us use AI transcription".
3. **"I want to know what it will cost before I commit."**
   Evidence: row 8, 2025-02-22 — "It's not clear to me how much they will cost";
   row 9, 2025-08-14 — "I was surprised when my OpenAI bill came through".
4. **"I want to know what we're allowed to do with client data and who is responsible if it's wrong."**
   Evidence: row 1, 2024-07-01 — "What are my moral and employee responsibilities";
   KPMG 2025 — 66% rely on AI output without checking accuracy, 56% have made work mistakes because of it.
5. **"I want to know how to get my boss and my team to agree to this."**
   Evidence: row 16 (boss refuses transcription despite paid Copilot licences); row 19, 2026-06 —
   "the AI writer, mandated manager training"; Microsoft WTI 2026 — only 26% say leadership is
   clearly aligned on AI strategy.
6. **"I want to know how to stop my team producing AI slop that someone else has to clean up."**
   Evidence: row 2, 2025-08-05 — "a ChatGPT wall of text that's hundreds of words long";
   row 17, 2026-01 — "my coworker is using AI to do her work (badly)".
7. **"I want to know what tool to use for this one task, not a list of fifty."**
   Evidence: row 13, 2026-06-18 (Notion AI summaries can't be reused downstream);
   row 21 — "what ai tool can i use to create a powerpoint presentation".
8. **"I want to know whether I should tell people I used AI."**
   Evidence: Slack 2024 — 48% uncomfortable telling their manager, 47% feel it is "cheating";
   Microsoft WTI 2024 — 52% hesitate to admit AI use on important tasks.

Not evidenced for W1: any interest in ROI dashboards, agent architectures, or model benchmarks —
**no evidence found**.

### Persona W2 — "Tom", coordinator / junior specialist who wants to stay employable

- **Seniority:** junior to mid individual contributor (marketing coordinator, admin, assistant
  accountant, recruiter). Evidence: Gallup 2025 — individual contributors are the least informed
  group, 26% don't know their org's AI position.
- **Company size:** any; often the same 15–60 person company as W1.
- **AI level:** 2/10. Free ChatGPT, phone-first, no company account.
- **Current tools:** ChatGPT free, Google Docs/Sheets, Canva, the company CRM or ATS.

Interests, in his words:

1. **"I want to know what AI is and how it actually works, in plain language."**
   Evidence: row 20 — top autocomplete for "how does ai actually" is "how does ai actually work";
   Slack 2024 — only 7% call themselves expert users, 30% have had no training at all.
2. **"I want to know whether AI will take my job."**
   Evidence: Pew 2025 — 52% worried, 32% expect fewer job opportunities;
   row 15, 2025-07 — "can I be fired for refusing to use AI?".
3. **"I want to know where to start and which course is worth it."**
   Evidence: row 22 — "how to learn ai for a job", "how to learn ai for free with certificate";
   Coursera 2026 — GenAI enrolments +234% YoY, 14 per minute.
4. **"I want to know how to use AI in my specific job, not in tech."**
   Evidence: row 22 — "how to learn ai for accounting and finance";
   row 11, 2026-08-13 — a Talent Partner automating recruiting intake, not a developer.
5. **"I want to know what tool to use for the thing I have to hand in today."**
   Evidence: row 21 — "what ai tool can i use to create a powerpoint presentation";
   row 1, 2024-07-01 — "form letters to customers and to write reports".
6. **"I want to know how to use ChatGPT at work without getting in trouble."**
   Evidence: Slack 2024 — 48% uncomfortable telling a manager; 21% say policy discourages it;
   Microsoft WTI 2024 — 78% bring their own AI tools, 80% at SMEs.
7. **"I want to know how not to get caught out by a wrong answer."**
   Evidence: KPMG 2025 — 66% rely on output without checking accuracy, 56% made mistakes because
   of AI; Microsoft WTI 2026 — 86% treat AI output as a starting point, 50% name quality control
   of AI output as the top human skill.
8. **"I want to know whether being 'AI-excited' helps or hurts me when I apply for jobs."**
   Evidence: row 4, 2026-01-26 — "what is a smart choice when it comes to 'AI excitement'"
   (developer, so directional only for a non-technical role); Microsoft WTI 2024 — 66% of leaders
   would not hire someone without AI skills.

Not evidenced for W2: willingness to pay for tools out of pocket, and any preference between
specific vendors — **no evidence found**.

## 5. Two notes for the persona merge

- The (a) "what is AI" cluster is real but **anonymous**: it appears in search demand, never in a
  post signed by a named worker. Content answering "how does AI work" should be a hook, not the
  promise.
- The strongest single signal in this lens is a **manager handed a named process by a boss**
  (5 of 25 rows, all in cluster c). That is the same person POSITIONING §4 calls the Champion,
  and §8 M2 Teardowns already targets. The gap the evidence exposes is not the teardown itself —
  it is cost (2 rows) and permission (4 rows in e, 2 in h), which the current pillar table
  does not require any card to answer.
