# 07 — Reddit pass: what real people ask about AI at work (2026-09-12/13)

**Why.** The three-agent persona work (`01`–`06`) could not reach Reddit. Misha authorised a pass
through his own Chrome session, so this file holds the first-hand voice of owners and employees:
101 threads, 17 subreddits, last 12 months, read in full with the top comments. Every row below is a
real post by a real account; quotes are verbatim and ≤ 15 words. Analysis fields (role, cluster,
AI level) are the orchestrator's reading of the post, not something the poster stated, unless the
role was explicit. Raw records with top-comment excerpts: `reddit-pass-2026-09-12.jsonl`.

**Method.** `old.reddit.com` search per subreddit (queries: where to start / which tool / cost or
subscription / automate / boss wants AI / learn AI for my job / replace), then the thread read with
top-sorted comments. After ~80 threads old.reddit started returning error pages; the remainder was
read through the public `.json` endpoints of `www.reddit.com`. No posting, voting or messaging.
Sub rules noted and respected: r/smallbusiness forbids market research, several subs ban pasted AI
output.

**Limits.** Selection is by search relevance and engagement, not random; 17 subs; one pass; 101 of
a much larger population. Vendor replies are frequent and flagged where obvious. Eleven of the 101
threads are themselves suspected AI-written or self-promotional (marked in `quality`).

## 1. What people ask, by cluster (multi-label, n = 101 threads)

| key | cluster | all | owner subs | worker subs |
|---|---|---:|---:|---:|
| c | how do I automate this specific process | 38 | 32 | 6 |
| e | trust: is it right, is my data safe, who checks | 35 | 22 | 13 |
| i | other: backlash, slop, mood | 31 | 22 | 9 |
| b | which tool for a task | 20 | 15 | 5 |
| g | where do I start / overwhelmed | 15 | 11 | 4 |
| d | what does it cost / is it worth paying | 14 | 14 | 0 |
| f | will it replace me / my staff | 14 | 4 | 10 |
| h | boss, team, permission, having to perform AI | 13 | 0 | 13 |
| a | what is AI / how it works | 5 | 2 | 3 |

Owner subs: smallbusiness, Entrepreneur, sweatystartup, agency, ecommerce, msp, ChatGPTPro,
EntrepreneurRideAlong, sales (68 threads). Worker subs: careerguidance, productivity, marketing,
Accounting, humanresources, ExecutiveAssistants, projectmanagement, artificial (33 threads).

**Reading.** (c) "how do I automate this specific thing" is the largest cluster on both sides,
exactly as the corpus and the two web lenses found. (e) trust is second and is not abstract: it is
"does the answer match today's policy", "I can't read the code", "who is responsible when it is
wrong", "did it leak my SSN". (a) "what is AI" is asked five times in 101 threads and never by an
owner in those words; when it appears it is "what is this actually, beyond the hype" or "does it get
the job done right the first time". (f) replacement fear is a worker cluster; the one owner-side
version is agencies and PMs watching clients or CEOs try to swap headcount for agents.

## 2. The words they use (phrasebank for hooks and captions)

Owners name the job, never the technology:
- "a big part of the day is answering the same questions" · "the same 20 questions" · "repetitive support tickets takes up most of my day"
- "following up on voicemails" · "chasing invoices" · "losing jobs because I can't answer fast enough" · "no-shows are killing my margins"
- "managing the AI is starting to feel like a full-time job" · "you're the one who now has to maintain the automation"
- "does it get the job done RIGHT, THE FIRST TIME?" · "using ai the best you can hope for is mostly right"
- "you don't even know where to start, what is effective, and what is worth paying for"
- "I can't read the code… I basically just had to trust that it works"
- "I keep rewriting most of it by hand to sound like me"
- "every part of the process has its own subscription now" · "I'm paying for 12 apps and I've barely launched"
- "I have 10 more ideas than I have time to implement" · "50 open tabs of revolutionary AI tools I'll never use"
- "everything is still managed the old-fashioned way" · "notebooks, memory, manual controls"

Employees:
- "my boss asked me to create an automation" · "boss uses AI for everything" · "have you asked AI what it thinks?"
- "we should double check anything AI-generated before it goes out"
- "What are we allowed to do with client data" · "you cannot put client data into any AI… this is my job"
- "I'm not a programmer" · "I want the technical skills to fall back on"
- "my team members don't read the AI summaries" · "are you minuting the conversation or the decision?"
- "drained by having to perform interest in AI" · "now being evaluated on it"

Words that cost trust (audiences call them out in comments): "AI-powered", "agentic", "RAG",
"revolutionary", "quietly", "it's not X, it's Y", em-dashes, "here's what ChatGPT had to say".
One r/Entrepreneur commenter: "every acronym you put on your pitch loses client interest by 25%".
The tool name is fine **after** the job is shown; "AI" alone means ChatGPT to this audience.

## 3. The advice the crowd upvotes (these are the mechanics our cards should show)

1. Start with one recurring admin task you already understand and can verify quickly; run it with AI for two weeks. (r/smallbusiness)
2. AI drafts, you approve with one tap; put the approval step where you already are, in texts, not a dashboard. (2-person HVAC thread, 55 comments)
3. Never let the model generate prices: give it a fixed price sheet so the worst it can do is pick the wrong line. (same)
4. One source of truth outside the bot, one owner, a last-reviewed date; run 20–30 test questions before it sees customers; sample real conversations weekly. (AI support QA thread)
5. Decide first, then use AI; it is a faster way to start, not to finish. (r/productivity)
6. Do it by hand first, then automate what worked; "the manual phase is where you learn what to automate". (r/Entrepreneur, 52 pts)
7. Automation is a multiplier: a messy process automated is a mess 10x faster; one clear input, one clear output, so you can tell when it breaks. (r/agency)
8. Minute decisions and actions, not conversations; teach the tool your format from 2–3 of your own examples. (r/projectmanagement)
9. Write down how you quote, order, and what "done" looks like before any tool. (r/sweatystartup, r/smallbusiness hardware store: "clean item master first")
10. Say what the thing does; drop "AI-powered". (400+ landing pages reviewed)

## 4. What is rejected

- **Customer-facing AI.** Chatbots, AI receptionists, AI images on menus and flyers, AI copy: "Customers fucking hate them" (25p), "I hang up", "If I can tell a business is using AI, I avoid that business". Exception named twice: after-hours intake.
- **Replacing people as the pitch.** Zero owners asked for it; workers refuse to save it; owners' own top comment: "AI is mostly a margin opener".
- **Comparisons and tool lists.** Every "which tool" thread is colonised by vendors within hours; the genuine replies say "the platform matters less than knowing what to delegate to it".
- **Posts that read as AI.** Commenters flag them in the first replies; r/msp and r/humanresources proposed rules against pasted AI output.

## 5. Cost anchors people actually said

$20 plan is the reference price ("not worth my $20 anymore", "The $20 subscription gets you quite a
lot"); $100/month tool rejected as prohibitive by a UK owner; $200 Pro only "if you hit limits and can
count the hours"; $3,000 audit + $400/month rejected vs £450 + £50 from another agency; virtual
assistant $1,100/month plus bonus; AI intake system $69/month (law firm, 2.6 % phone conversion
before); €3,000 for a 15,000-emails-a-day agent called "wayyyyyyy undercharging"; "teams burn
$2–3K/mo on GPT-4 calls before realizing they could cache 80 %"; subscriptions pile up ("12 apps");
median SMB spend $28–31/month (JPMorganChase, from report 02).

## 6. Tasks named, normalised (owner threads unless marked)

1. Customer replies / the same questions (WhatsApp, tickets, FAQ) — 9 threads
2. Quotes, estimates, pricing, job costing — 6
3. Lead follow-up, voicemails, appointment calls — 6
4. Scheduling, confirmations, no-shows, call screening — 5
5. Meeting notes → actions (workers) — 6
6. Bookkeeping, invoices, payroll, reconciliation — 4
7. Content, copy, social posts, ads — 9 (but see §4: the output is distrusted)
8. Website / landing page build — 5
9. Product photos — 3
10. SOP / internal knowledge bot / onboarding — 4
11. Reports, decks, one transcript into many formats (workers) — 4
12. Hiring screening — 2, both rejected

## 7. Verdict on the three draft personas (`docs/AUDIENCE_PERSONAS_2026-09-12.md`)

- **Mary (online product owner, level 4):** confirmed in r/ecommerce and r/smallbusiness. Add: "a
  backlog of 1,000 automation ideas and no time" (prioritisation, not ignorance), the $3k-audit
  decision, "I can't read the code", product photos. Her (b) question is real but she wants "the one
  I need for this", never a ranking.
- **Bruce (local services owner, level 2):** confirmed strongly in r/sweatystartup and the HVAC /
  hardware-store threads, but **he does not use the word AI**. His questions are quotes, no-shows,
  voicemails, spam calls, exceptions in his head, margins leaking in the estimate. The AI question
  for him is "is it worth paying for and does it get it right the first time". Rename (the draft
  used a real broker's name).
- **Marta (ops manager, level 3):** confirmed in r/humanresources, r/ExecutiveAssistants,
  r/projectmanagement, r/marketing. Two additions the web lenses missed: (1) the boss who "uses AI
  for everything" and checks her work against Claude, (2) being **evaluated** on AI adoption while
  told not to put client data in. Her wins are one transcript → many formats, decisions-not-
  conversations minutes, dashboards from HRIS data.

## 8. Evidence table (101 threads)

| sub | date | author | role (read from post) | cluster | quote | thread |
|---|---|---|---|---|---|---|
| r/Accounting | 2026-02-11 | jnk5260- | accountant | h,e | “stop forcing me to incorporate this into my every day life” | [1r21wsv](https://old.reddit.com/r/Accounting/comments/1r21wsv/) |
| r/Accounting | 2026-04-21 | Practical_Report7328 | tax preparer, SMB clients | e,i | “Had a client run their draft return through ChatGPT and Gemini” | [1sr82s5](https://old.reddit.com/r/Accounting/comments/1sr82s5/) |
| r/Accounting | 2026-08-07 | Spiritual-Beyond-660 | accounting community | f | “How many potential accountants are lost due to AI scares?” | [1vhon8k](https://www.reddit.com/r/Accounting/comments/1vhon8k/) |
| r/ChatGPTPro | 2025-09-20 | Unlucky_Freedom_9960 | small business owner, early to AI | b,d | “I'm pretty early to AI” | [1nlngy5](https://old.reddit.com/r/ChatGPTPro/comments/1nlngy5/) |
| r/ChatGPTPro | 2025-10-10 | According_Craft_5722 | business user + coder | d | “Is ChatGPT Pro currently worth it?” | [1o2wg4b](https://old.reddit.com/r/ChatGPTPro/comments/1o2wg4b/) |
| r/ChatGPTPro | 2025-11-28 | StaLucy | small business owner, non-technical | c,b | “For a non-technical person like me, it's the magic” | [1p8l7jk](https://old.reddit.com/r/ChatGPTPro/comments/1p8l7jk/) |
| r/ChatGPTPro | 2026-02-11 | magnumpl | daily Plus user, business + home | b,d | “I'm wondering if I'm missing out on other options which might be better to pay for” | [1r2990u](https://old.reddit.com/r/ChatGPTPro/comments/1r2990u/) |
| r/ChatGPTPro | 2026-05-06 | mrparallex | curious | i,c | “What AI tools/workflows are genuinely useful vs overhyped?” | [1t5mfjw](https://old.reddit.com/r/ChatGPTPro/comments/1t5mfjw/) |
| r/Entrepreneur | 2025-10-13 | Delicious_Departure8 | curious founder | d,i | “how many of them are actually turning a profit” | [1o5egji](https://old.reddit.com/r/Entrepreneur/comments/1o5egji/) |
| r/Entrepreneur | 2025-11-11 | New_Breakfast9275 | would-be AI services seller | i | “is it still too futuristic for most people?” | [1ou6p0h](https://old.reddit.com/r/Entrepreneur/comments/1ou6p0h/) |
| r/Entrepreneur | 2025-11-25 | Broad-Worry-5395 | business owner receiving AI tool pitches | a,e | “does it get the job done RIGHT, THE FIRST TIME?” | [1p6a1u5](https://old.reddit.com/r/Entrepreneur/comments/1p6a1u5/) |
| r/Entrepreneur | 2026-01-27 | Afraid-Albatross812 | solo founder / developer | i,e | “if you send 1000 emails and get 0 replies, you are not doing sales” | [1qof5yc](https://old.reddit.com/r/Entrepreneur/comments/1qof5yc/) |
| r/Entrepreneur | 2026-02-06 | Ibrasa | technical/business person 15+ yrs, uses AI for content | e,i | “AI doesn't replace judgment. I still decide what's good” | [1qxlfaa](https://old.reddit.com/r/Entrepreneur/comments/1qxlfaa/) |
| r/Entrepreneur | 2026-02-19 | Bing-Crosby23 | bootstrapping founder, product for pregnant women | b,c | “trying to leverage tools where possible” | [1r8l870](https://old.reddit.com/r/Entrepreneur/comments/1r8l870/) |
| r/Entrepreneur | 2026-03-10 | Technical-Apple-2492 | news-style post | b,i | “How many of you people stopped using ChatGPT?” | [1rpowo2](https://old.reddit.com/r/Entrepreneur/comments/1rpowo2/) |
| r/Entrepreneur | 2026-04-22 | boricuajj | consultant auditing founders' AI stacks | c,g | “No owner. No success metric. No home inside an existing workflow.” | [1ssqek0](https://old.reddit.com/r/Entrepreneur/comments/1ssqek0/) |
| r/Entrepreneur | 2026-05-02 | puppyqueen52 | non-technical co-founder, wedding tech | i,c | “I'm the one who got the calls booked” | [1t1bhxf](https://old.reddit.com/r/Entrepreneur/comments/1t1bhxf/) |
| r/Entrepreneur | 2026-07-05 | Embarrassed_Steak309 | founder, small web agency, 5 clients | c | “a company brain inside Cursor with processes, standards, meeting transcripts and client context” | [1unxhry](https://old.reddit.com/r/Entrepreneur/comments/1unxhry/) |
| r/Entrepreneur | 2026-08-25 | hawkfan1296 | marketer/owner | e,i | “the flyers and posts absolutely suck” | [1vy195n](https://old.reddit.com/r/Entrepreneur/comments/1vy195n/) |
| r/EntrepreneurRideAlong | 2025-12-20 | Warm_Abalone_9602 | automation freelancer | c,a | “most businesses don't need complicated systems, they just need less friction” | [1prm2hh](https://www.reddit.com/r/EntrepreneurRideAlong/comments/1prm2hh/) |
| r/EntrepreneurRideAlong | 2026-06-02 | BedDesigner2568 | website copywriter, reviewed 400+ founder sites | i,e | “Just because it has AI, doesn't mean people will... pull out their credit cards” | [1tumnrj](https://www.reddit.com/r/EntrepreneurRideAlong/comments/1tumnrj/) |
| r/EntrepreneurRideAlong | 2026-06-06 | Fabulous-Pea-5366 | AI freelancer | c,d | “Hotel guests don't write clean one-question emails” | [1tylc45](https://www.reddit.com/r/EntrepreneurRideAlong/comments/1tylc45/) |
| r/ExecutiveAssistants | 2025-11-22 | crazyspontaneity | EA to a tech CEO, AI-first company | b,g | “so I can keep leveling up how I support my CEO and my team” | [1p3w8vh](https://old.reddit.com/r/ExecutiveAssistants/comments/1p3w8vh/) |
| r/ExecutiveAssistants | 2026-03-20 | littlemac93 | EA managing four calendars | i,e | “I have not heard back from the robot” | [1ryjnbj](https://www.reddit.com/r/ExecutiveAssistants/comments/1ryjnbj/) |
| r/ExecutiveAssistants | 2026-04-27 | westgoingzax | older EA, uses AI at home | h,i | “cosplay enthusiasm and competence with AI at work” | [1sx2ju3](https://old.reddit.com/r/ExecutiveAssistants/comments/1sx2ju3/) |
| r/ExecutiveAssistants | 2026-07-06 | petitsamours | executive assistant | f,h | “It's not that I don't want to use AI, it's that I'm not a programmer” | [1uoviir](https://old.reddit.com/r/ExecutiveAssistants/comments/1uoviir/) |
| r/ExecutiveAssistants | 2026-07-08 | girlcalledalex | EA in enterprise risk management, ex-receptionist, ADHD, anti-AI | h,f | “I want to have the technical skills to fall back on” | [1ur56fi](https://old.reddit.com/r/ExecutiveAssistants/comments/1ur56fi/) |
| r/agency | 2026-01-04 | Connect-Subject188 | agency owner, non-technical | c,d,e | “is automation something that quietly saves time… or is it mostly hype” | [1q450xv](https://old.reddit.com/r/agency/comments/1q450xv/) |
| r/agency | 2026-02-13 | cmwlegiit | agency owner | f,i | “if we're honest we know it's true” | [1r3jpvm](https://old.reddit.com/r/agency/comments/1r3jpvm/) |
| r/agency | 2026-02-19 | SavannahDaxia | agency owner, ex-programmer | c | “one AI agent that knows everything about each client, so nothing ever falls through the cracks” | [1r96j76](https://old.reddit.com/r/agency/comments/1r96j76/) |
| r/agency | 2026-03-12 | funnelforge | agency founder | c,g,e | “want their teams to use it more but don't know where to start, not sure if they should tell clients they use it” | [1rrt6xf](https://old.reddit.com/r/agency/comments/1rrt6xf/) |
| r/agency | 2026-06-13 | Ill-Professor-472 | agency owner | f,i | “The only content that seems to attract more attention is related to AI and how to use it” | [1u4mtlv](https://old.reddit.com/r/agency/comments/1u4mtlv/) |
| r/agency | 2026-07-28 | j90w | marketing agency owner, 8+ years | c,d | “building in-house applications to replace our annual and monthly subscriptions” | [1v8z05c](https://old.reddit.com/r/agency/comments/1v8z05c/) |
| r/artificial | 2026-04-11 | Typical-Education345 | non-coder knowledge worker, 6 months all-in | c,a,e | “Cursor (powered by Claude) changed what non-technical means” | [1si5uiw](https://www.reddit.com/r/artificial/comments/1si5uiw/) |
| r/careerguidance | 2026-03-18 | Jumpy_Worldliness862 | marketing/graphic design employee, anti-AI | h,e | “She doesn't make any edits to whatever slop ChatGPT spits out” | [1rxbnhh](https://old.reddit.com/r/careerguidance/comments/1rxbnhh/) |
| r/careerguidance | 2026-03-28 | Illustrious-Word-979 | automation engineer, 40s | f | “It feels like we're being told our wisdom doesn't matter if we can't write a prompt” | [1s5znkv](https://old.reddit.com/r/careerguidance/comments/1s5znkv/) |
| r/careerguidance | 2026-07-20 | Longjumping_Wear_547 | 22-year-old job seeker | f,g | “what is a good office desk work that ai won't take” | [1v1o7ag](https://www.reddit.com/r/careerguidance/comments/1v1o7ag/) |
| r/careerguidance | 2026-08-24 | Kind-King1491 | employee, insurance brokerage serving SMBs | e | “we should double check anything AI-generated before it goes out” | [1vx103w](https://old.reddit.com/r/careerguidance/comments/1vx103w/) |
| r/ecommerce | 2025-09-28 | Plus_Ad3379 | commentator/owner | i | “Nobody cancels shopping at your store, saying, If only your product description had been snappier!” | [1nspklg](https://old.reddit.com/r/ecommerce/comments/1nspklg/) |
| r/ecommerce | 2025-12-26 | AccountingAxolotl | ecommerce owner | b,e | “Do you still pay for product photography? or you just use AI?” | [1pvvywd](https://old.reddit.com/r/ecommerce/comments/1pvvywd/) |
| r/ecommerce | 2026-03-15 | agent_zi | ecommerce owner on a budget | b,d | “I need something that looks genuinely professional” | [1rubl90](https://old.reddit.com/r/ecommerce/comments/1rubl90/) |
| r/ecommerce | 2026-05-12 | Intelligent-Fox2082 | builder/store operator | d,c | “I'm paying for 12 apps and I've barely launched” | [1taro12](https://old.reddit.com/r/ecommerce/comments/1taro12/) |
| r/ecommerce | 2026-05-21 | Alien36 | Shopify store owner | g,c | “Every day I feel like I have 10 more ideas that I don't have time to implement” | [1tj52ja](https://old.reddit.com/r/ecommerce/comments/1tj52ja/) |
| r/ecommerce | 2026-08-26 | Beginn-ing0 | co-owner, 2-person Shopify store | d,b | “Kind of hard to justify paying someone a few thousand dollars for an audit” | [1vz1hk0](https://old.reddit.com/r/ecommerce/comments/1vz1hk0/) |
| r/humanresources | 2025-09-22 | SwanAmbitious2347 | HR, company considering AI first-round interviews | e,c | “I can't shake the feeling that something important is being lost” | [1nnlnw7](https://old.reddit.com/r/humanresources/comments/1nnlnw7/) |
| r/humanresources | 2025-11-12 | sweetpotato-jalapeno | head of HR, crypto startup | e,i | “Just give me a status update on your work” | [1ovdyma](https://old.reddit.com/r/humanresources/comments/1ovdyma/) |
| r/humanresources | 2026-02-13 | Grouchy_Flatworm_367 | HR / people analytics | f | “Am I being paranoid about automation threatening HR jobs?” | [1r41yhc](https://www.reddit.com/r/humanresources/comments/1r41yhc/) |
| r/humanresources | 2026-05-28 | Top-Calligrapher6160 | nonprofit HR, team of one, 15 yrs | g,b,c | “I'd like to build my fluency and familiarity” | [1tpue8x](https://old.reddit.com/r/humanresources/comments/1tpue8x/) |
| r/humanresources | 2026-08-11 | Ornery-Mycologist-53 | HR leader reporting to CHRO | h,e | “replying with AI when we ask them for their own thoughts” | [1vlmxlv](https://old.reddit.com/r/humanresources/comments/1vlmxlv/) |
| r/marketing | 2025-12-16 | hrh-sylvanas | head of marketing, 2-person team, B2C 60 stores | f,h | “He thinks that content can now be automated with AI” | [1pnwy1o](https://old.reddit.com/r/marketing/comments/1pnwy1o/) |
| r/marketing | 2026-02-04 | CopySniper | freelance conversion copywriter | i | “AI is garbage and tells me nothing meaningful” | [1qvkhp0](https://old.reddit.com/r/marketing/comments/1qvkhp0/) |
| r/marketing | 2026-03-10 | foxesinthecity | marketing lead reporting to CEO | h,e | “It's exhausting and discouraging to my team.” | [1rqaf5y](https://old.reddit.com/r/marketing/comments/1rqaf5y/) |
| r/marketing | 2026-06-19 | thnksnothnksgiving | senior product marketer, regulated industry | e,h | “Materials have gone out to medical professionals and patients with no review” | [1u9vflw](https://www.reddit.com/r/marketing/comments/1u9vflw/) |
| r/marketing | 2026-08-25 | (redacted by tool) | marketer/copywriter in an AI-forward company | f,h | “using AI to enhance creative work and using it to replace the creative process” | [1vy1lfp](https://www.reddit.com/r/marketing/comments/1vy1lfp/) |
| r/marketing | 2026-08-25 | Character_Chapter998 | junior/mid marketer, 5 years | h,f | “I'm feeling a little depleted and untalented” | [1vxvchr](https://www.reddit.com/r/marketing/comments/1vxvchr/) |
| r/msp | 2026-01-14 | buzaw0nk | MSP | i | “The client pulled out his phone and asked ChatGPT” | [1qcuyhw](https://old.reddit.com/r/msp/comments/1qcuyhw/) |
| r/msp | 2026-02-24 | computerguy0-0 | MSP community | i | “No AI generated comments. No Here's what ChatGPT had to say.” | [1rd1rjk](https://old.reddit.com/r/msp/comments/1rd1rjk/) |
| r/msp | 2026-03-18 | Woolfie_Admin | MSP admin | e | “Getting a lot of requests for Claude lately” | [1rx30g2](https://old.reddit.com/r/msp/comments/1rx30g2/) |
| r/msp | 2026-07-15 | hongkong-it | MSP | e | “We are getting pressure to connect Claude” | [1uwstq4](https://old.reddit.com/r/msp/comments/1uwstq4/) |
| r/msp | 2026-08-17 | Check123ok | MSP owner (IT provider to SMBs) | e,i | “it can give less experienced IT staff enough terminology and confidence to challenge decisions” | [1vr7q7i](https://old.reddit.com/r/msp/comments/1vr7q7i/) |
| r/productivity | 2025-09-22 | Fit_Yam8764 | worker | g,b | “You spend more time debating which tool to use than finishing the actual project” | [1nnv9so](https://www.reddit.com/r/productivity/comments/1nnv9so/) |
| r/productivity | 2025-10-22 | aylim1001 | knowledge worker | c,a | “the agent does this one annoying step, and I still do the rest” | [1ocu9ys](https://old.reddit.com/r/productivity/comments/1ocu9ys/) |
| r/productivity | 2025-11-27 | hhhjin | general worker | a,i | “I still don't really feel the impact in my own daily life” | [1p83lfx](https://old.reddit.com/r/productivity/comments/1p83lfx/) |
| r/productivity | 2026-04-29 | rayraywaha | individual user | i,e | “Every single step is just me wasting time trying to compensate AI's mistakes” | [1sywo2z](https://old.reddit.com/r/productivity/comments/1sywo2z/) |
| r/productivity | 2026-07-31 | iphotographstuff | AI-exposed worker | i,b | “you went back to a notebook or your head” | [1vblphw](https://www.reddit.com/r/productivity/comments/1vblphw/) |
| r/projectmanagement | 2025-12-16 | Fantastic-Nerve7068 | project manager | h,i | “AI makes it easier to generate more artifacts. more decks. more docs.” | [1pnxqtb](https://www.reddit.com/r/projectmanagement/comments/1pnxqtb/) |
| r/projectmanagement | 2026-07-19 | Critical-Promise4984 | PM, overloaded team | f,h | “the data doesn't support hiring more PMs” | [1v0coef](https://www.reddit.com/r/projectmanagement/comments/1v0coef/) |
| r/projectmanagement | 2026-07-31 | GeneralGold2992 | project manager | c,b | “where you always wonder how you were able to exist before” | [1vbp2g8](https://www.reddit.com/r/projectmanagement/comments/1vbp2g8/) |
| r/projectmanagement | 2026-08-27 | dearcamus | PM of very complex projects | c,e | “My team members confirmed that they don't read teams generated summaries” | [1w0383c](https://www.reddit.com/r/projectmanagement/comments/1w0383c/) |
| r/sales | 2025-11-04 | jroberts67 | owner with two telemarketers | c,f | “anything lower level, especially calling to book meetings or appointments, will be completely be replaced by AI” | [1ooeqfx](https://www.reddit.com/r/sales/comments/1ooeqfx/) |
| r/sales | 2026-03-28 | dbSteelyPhil | salesperson | f,c | “Most inbound SDR work is pattern matching” | [1s6496m](https://www.reddit.com/r/sales/comments/1s6496m/) |
| r/sales | 2026-05-26 | duckblobartist | salesperson / buyer | e,i | “I have absolutely no patience for it” | [1to9799](https://www.reddit.com/r/sales/comments/1to9799/) |
| r/sales | 2026-08-28 | ApplePrimary2985 | salesperson, building materials | i | “F*ck AI and Everything Associated” | [1w137j5](https://www.reddit.com/r/sales/comments/1w137j5/) |
| r/smallbusiness | 2025-10-27 | Vivid-Process-5736 | employee/manager tasked with AI at a manufacturer | g,c | “So where do I start?” | [1ohhcv5](https://old.reddit.com/r/smallbusiness/comments/1ohhcv5/) |
| r/smallbusiness | 2025-12-12 | Plus_Importance5612 | online business owner (self-declared), building a tool directory | b | “There are thousands of them, but most directories feel outdated” | [1pkq91j](https://old.reddit.com/r/smallbusiness/comments/1pkq91j/) |
| r/smallbusiness | 2026-01-27 | hggibs11 | owner, small field service business | b,c | “I've only used ChatGPT so far, and it's been helpful” | [1qo267y](https://old.reddit.com/r/smallbusiness/comments/1qo267y/) |
| r/smallbusiness | 2026-02-04 | Sev_Khamani | advisor-style poster | g,c | “Deciding which processes to optimize first... can be overwhelming” | [1qvo56f](https://old.reddit.com/r/smallbusiness/comments/1qvo56f/) |
| r/smallbusiness | 2026-02-08 | Reasonable_Tone4813 | founder, design studio | b,g | “Any tools that you found useful to reduce your stress/workload as a founder?” | [1qzd65j](https://old.reddit.com/r/smallbusiness/comments/1qzd65j/) |
| r/smallbusiness | 2026-02-17 | RegisterBig7923 | owner, small operation | c,e,d | “Would you recommend it to a non-technical owner?” | [1r6r9fg](https://old.reddit.com/r/smallbusiness/comments/1r6r9fg/) |
| r/smallbusiness | 2026-06-27 | Green-Drive-3164 | solo operator writing own marketing copy | e,i | “I keep rewriting most of it by hand to sound like me” | [1ugxq6k](https://old.reddit.com/r/smallbusiness/comments/1ugxq6k/) |
| r/smallbusiness | 2026-07-23 | Aritra001 | edtech startup founder | b,d | “Can anyone suggest which AI I should get?” | [1v45f1n](https://www.reddit.com/r/smallbusiness/comments/1v45f1n/) |
| r/smallbusiness | 2026-07-27 | Careless-Carpet-8474 | owner revamping dated website, no time, no budget | b,g,d | “It's like every part of the process has its own subscription now.” | [1v83bom](https://old.reddit.com/r/smallbusiness/comments/1v83bom/) |
| r/smallbusiness | 2026-07-31 | ogola89 | solopreneur | g,d,b,e | “you don't even know where to start, what is effective” | [1vbz9b3](https://old.reddit.com/r/smallbusiness/comments/1vbz9b3/) |
| r/smallbusiness | 2026-08-08 | Safe_Advertising9449 | second-generation, 23, modernising father's hardware store (Argentina) | g,c | “almost everything is still managed the old-fashioned way” | [1vjat9j](https://old.reddit.com/r/smallbusiness/comments/1vjat9j/) |
| r/smallbusiness | 2026-08-08 | meedo82 | owner who paid a contractor for an AI-built app | e | “I basically just had to trust that it works” | [1vj21cd](https://www.reddit.com/r/smallbusiness/comments/1vj21cd/) |
| r/smallbusiness | 2026-08-15 | Exposethewealth | business owner considering AI website | e,c | “I'm more curious about what happened after launch” | [1vp1150](https://www.reddit.com/r/smallbusiness/comments/1vp1150/) |
| r/smallbusiness | 2026-08-23 | sociallyineptmilk | small business owner | e,i | “was shamed for it at a chamber of commerce event” | [1vwlmtp](https://www.reddit.com/r/smallbusiness/comments/1vwlmtp/) |
| r/smallbusiness | 2026-08-25 | Over_Economics7893 | small business operator using AI support (or researching it) | e,c | “does the answer match your actual policy today?” | [1vxr2l4](https://old.reddit.com/r/smallbusiness/comments/1vxr2l4/) |
| r/smallbusiness | 2026-08-26 | elmahdim | founder/dev-adjacent | i | “It didn't eliminate the business's constraints it just relocated them” | [1vyx0ex](https://old.reddit.com/r/smallbusiness/comments/1vyx0ex/) |
| r/smallbusiness | 2026-09-01 | Super_Bodybuilder773 | vendor (deal-diligence tool), content marketing | e | “Polish and correctness are independent.” | [1w4b19g](https://old.reddit.com/r/smallbusiness/comments/1w4b19g/) |
| r/smallbusiness | 2026-09-03 | Daniel-Plainview96 | co-owner, 2-person HVAC company, does sales+admin | c,g | “managing the AI is starting to feel like a full-time job” | [1w640zy](https://old.reddit.com/r/smallbusiness/comments/1w640zy/) |
| r/smallbusiness | 2026-09-08 | Ok-Homework5533 | unclear (possibly research post) | i,e | “the last 20% is so much manual effort that it's not worth doing” | [1was7y2](https://old.reddit.com/r/smallbusiness/comments/1was7y2/) |
| r/smallbusiness | 2026-09-09 | flavia-f | builder researching WhatsApp SMBs (vendor-side) | c | “a big part of the day is answering the same questions” | [1wbey4m](https://old.reddit.com/r/smallbusiness/comments/1wbey4m/) |
| r/sweatystartup | 2025-10-24 | Justin_3486 | part-time handyman, 8 months in | c,e | “I'm 100% losing jobs because I can't answer fast enough” | [1oex952](https://old.reddit.com/r/sweatystartup/comments/1oex952/) |
| r/sweatystartup | 2025-11-23 | ItchyKnee223 | junk removal owner | c | “Should I have set pricing, rely on photos, or see the place in person” | [1p4qdxr](https://old.reddit.com/r/sweatystartup/comments/1p4qdxr/) |
| r/sweatystartup | 2026-02-23 | kerblamophobe | mobile auto detailing owner | c | “Gas is too expensive to be driving around for nothing.” | [1rcq5vo](https://old.reddit.com/r/sweatystartup/comments/1rcq5vo/) |
| r/sweatystartup | 2026-02-27 | blanssius_56 | HVAC owner, 8 years | c | “I can't figure out if I'm bad at estimating or bad at tracking costs” | [1rg0rml](https://old.reddit.com/r/sweatystartup/comments/1rg0rml/) |
| r/sweatystartup | 2026-07-05 | OverContract3219 | growing service business owner | c,g | “the stuff behind the scenes take even more time” | [1uoh3pw](https://old.reddit.com/r/sweatystartup/comments/1uoh3pw/) |
| r/sweatystartup | 2026-07-30 | nadnerBG | consultant, ex home-services owner | i | “find the profit that's already sitting inside the business” | [1vak6eg](https://old.reddit.com/r/sweatystartup/comments/1vak6eg/) |
| r/sweatystartup | 2026-08-23 | Obvious-Dinner-1082 | side-business auto repair owner | c,b | “I'm looking for recommendations on apps or if I need to call my phone service provider” | [1vvw2kr](https://old.reddit.com/r/sweatystartup/comments/1vvw2kr/) |
| r/sweatystartup | 2026-08-31 | Slight_Vacation1651 | owner, recurring dog-waste removal, now with employees | c | “I'm the one who built a service with 100 little exceptions” | [1w3krwn](https://old.reddit.com/r/sweatystartup/comments/1w3krwn/) |
