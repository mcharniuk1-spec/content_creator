> English rendering of RULES.md (Russian original is authoritative). Generated 2026-09-13 for Max.

# Rules for selecting topics for M2 Lab

Layer 2: how a radar signal becomes a "take / don't take" decision.
Draft from 1 September 2026. Written after a grilling session, needs edits from Misha.

**Changes on 12 September 2026, decisions by Misha (applied in `cards.py`, the engine prompts,
on the server, and in Notion):**
1. Freshness threshold **30 days** instead of 14 (§1.1, §6, §8).
2. Comment-bait **is allowed and should be used**: a call to "write a word in the comments"
   builds an audience and hooks it. Copying the call itself from the reference video is fine
   (§1.2, §7).
3. All three formats are ranked on **one scale: shares + saves per thousand**.
   The signal "topic repeated across several creators" has been dropped for Teardown as too
   abstract; repetition is now tracked for reference only (§2).
4. **We look at all of a creator's videos in the window**, not just one. A creator enters
   the pool if at least one of their videos exceeded their own baseline by 1.5x; after that,
   a card can also be built from one of their videos that did not perform on its own (§2).

The source of the higher-level decisions is `m2_lab_working_document.docx`, version 3 from
21 August. This document does not restate what is already decided there: positioning, the
three formats, metrics, the list of prohibitions. This document only covers what is not
there: the selection mechanics.

---

## 0. What goes in and what comes out

**Input:** the radar. A hundred English-language accounts at the core of the niche, snapshots
twice a week (Monday and Thursday), each video scored against its own creator's median.

**Output:** 8-10 prioritised cards per week. Misha crosses out what is not needed; the rest
goes into production.

Someone else's video is **an input, not an output**. We watch it and break it down; what goes
out is our own video with our own angle. Publishing other people's clips is prohibited by the
working document.

---

## 1. Two separate lists

Previously everything here was dumped into one filter. That was a mistake: something we
don't do ourselves is not a reason to skip looking at someone else's video.

### 1.1. What does not make the selection

Criteria are objective and checked mechanically.

| Filter | Why |
|---|---|
| Account outside the niche: fashion, finance, trading, real estate, products, geopolitics | Irrelevant reach is not neutral: it hits engagement, and then distribution |
| Humorous or entertainment video | Misha's decision from 1 September |
| Not English-language | Mixing languages within an account is prohibited |
| Topic older than 30 days | Single freshness threshold (14 → 30 as of 12 September 2026) |

**Niche boundary, decision from 1 September.** "How to make money with AI" is an adjacent
niche, not ours. Ours is AI in business processes. An account whose topic is income from AI
does not make the selection. Important not to confuse the two: what disqualifies is **the
account's topic**, not a money-framed phrase in a single video; we simply do not copy the
phrasing (section 1.2).

Everything else is filtered out not here, but by the card's stop-test (section 4), at the
point where it is already visible whether we have anything to add.

### 1.2. What we collect but don't copy

These videos **stay in the selection**. We study their structure, hook and delivery, and
simply don't carry over the mechanics that don't suit us.

| Reference mechanic | What we take | What we don't take |
|---|---|---|
| Comment-bait, "Comment AGENT and I'll send it" | The hook, structure, topic, pace, **and the call itself** (as of 12 September 2026) | (none) |
| Income promise, "$10k a month" | The topic and angle: the interest in the economics is real | The framing of the result as income. We rebuild it in hours and "before / after" |
| Watermarks, letterboxing instead of 9:16, no sound, longer than three minutes | The content | The presentation technique |

**There is a measurement on comment-bait:** it appears in 28% of top videos and 26% of all
others; it does not add reach (across 266 videos analysed, p=0.58), but it lifts comments
×23, saves ×2.8 and shares ×1.8 (insight I-12). **Misha's decision, 12 September 2026:** a
call to comment is allowed and should be used, it builds an audience and hooks it. One
condition: the promised artefact must actually exist; inventing "I'll send the guide"
without a guide is not allowed.

**On income promises:** if a creator frames the result as income, that is their problem,
not ours. The topic itself can still be right, and we have the right to rebuild it for
ourselves.

---

## 2. Selection is done separately for each of the three formats

**Since 13 September 2026 the selection axis is the content block, not the format (§13).**
The format stays as the way we shoot: every block has a default format (`content_blocks.py`)
and the format descriptions below set the frame, screen and banner of a card. The "2 + 2 + 1"
slots no longer apply; the "15 in three stages" scheme replaces them.

A combined top ranking is not used: strong news videos would always win, and within a month
M2 Lab would turn into AI news. So there are three independent selections, each with its own
criteria.

**There is one scale for all three formats (as of 12 September 2026): shares + saves per
thousand views.** The format decides what we talk about and what we must prove, not which
metric we look at.

**Creator, not video (as of 12 September 2026).** A creator enters the pool if at least one
of their videos in the past 30 days exceeded their own baseline by 1.5x. From there we look
at **all** of their videos in the window: out of five posted, a card can also be built from
the one that did not perform on its own, if it has high shares and saves. The "one video per
creator" limit no longer exists.

The format definitions are taken from `POSITIONING.md` §8: there each one has its own
audience question and its own required proof. The metric shows which other video is worth
watching; the format decides what we talk about.

### Mandatory filter: before all other criteria

No card goes into the plan until four things are visible in it (`POSITIONING.md` §8):

1. **Which recurring work process** is being discussed.
2. **Where the real friction** is in that process.
3. **What AI does and what stays with the human.**
4. **What the viewer should do next.**

If it doesn't pass, the card is crossed out, not filled in further. This is not a formatting
recommendation, it is a condition for publication.

### M2 Radar: 2 slots a week

- **Audience question:** "is this solution relevant to me?"
- **What we look for:** a tool, model or market signal that connects to a specific recurring
  task. Metric signal: shares + saves.
- **Required proof:** a specific task, a solution for it, and a limitation.
- **Pass criterion:** the topic **will still be alive in a week**, three to seven days
  between planning and publication.
- **Disqualifies:** model news with no working solution, benchmarks, a review for its own
  sake, a list of tools, a topic with no connection to a process.
- **Our angle:** not "a model was released", but "what this changes in the week of the
  person responsible for this process".
- **Target signal:** shares.

### M2 Builds: 2 slots a week

- **Audience question:** "what does a first working version look like?"
- **What we look for:** a workflow we built and tested ourselves. Metric signal: shares +
  saves.
- **Required proof:** the process, the result, what broke, and where a human checks it.
- **Pass criterion:** built by us, and **there is something that can break**. Without a
  failure there is no Builds, there is just an advert for someone else's product.
- **Disqualifies:** anything that can't be reproduced in a day of preparation; a pure
  demonstration of someone else's tool; an agent demo with no process owner; a build that's
  interesting only to a developer.
- **Our angle:** "we took it into a real recurring process, here's the first version and
  here's where it breaks".
- **Target signal:** saves and follows.

### M2 Teardown: 1 slot a week, 2 every other week

- **Audience question:** "is this process a fit for AI, and how would it work?"
- **What we look for:** a recurring work process, ours, a generalised industry one, or one
  sent in by a viewer. Metric signal: shares + saves, same as the other formats. As of
  12 September 2026, a topic repeating across several creators no longer takes part in
  selection (too abstract a signal); it is printed for reference only, as a demand signal.
- **Required proof:** inputs, friction, the AI boundary, the process owner, and risk.
- **Pass criterion, both required:**
  1. There is a specific process with a named owner.
  2. **There is a reason to share it:** a number, a contradiction, "here's what this costs
     per week", "here's where AI isn't needed at all".
- **Disqualifies:** missing either of the two points; breaking down a tool instead of a
  process.
- **Our angle:** the process step by step → where time is lost → what can be handed to the
  machine → where a human must stay → limitations and risks.
- **Target signal:** saves and search. The title and the first line of the caption are
  worded as a search query.

### The audience all this is being selected for

A non-technical small-business owner, level 0-6 out of ten (`POSITIONING.md` §4). They know
AI exists, have tried ChatGPT, but don't know which task to start with or what can be
trusted. Practical consequence for selection: **a topic that only a developer would
understand is not our topic**, even if the video is superb by the metrics.

Directly from the "don't publish" list (`POSITIONING.md` §8): model news with no working
solution, deep technical tutorials, agent demos with no process owner, savings claims with
no proof, automation for its own sake.

### Where we get processes for Teardown

| Source | When | Limitation |
|---|---|---|
| Our own processes | From day one | The only one we can show without someone else's permission |
| Generalised industry processes | The main volume | "We think so", not "we've seen this", don't pass it off as a case study |
| Processes of clients we've automated | Not before such clients exist | ArchFlow is not a running business right now, this source doesn't exist yet |
| Sent in by viewers | From month two | Requires that the account already has readers |

---

## 2a. Suitability check after storyboarding

Added on 1 September, following the review of the top tier.

Account-level tagging is a necessary step, but **not sufficient**. In the first review, two
videos out of ten turned out to be unsuitable, and both had passed every bio-level filter:

- `@petergriffin.ai`: Family Guy characters parkouring in Minecraft, synthesised voices, an
  ad for an "uncensored" model. Bio: "AI made simple, powerful & clear. Tools + tech + smart
  workflows".
- `@10xoperator`: "9 lessons billionaires live by", has nothing to do with AI. Bio: "The AI
  cheat codes nobody's teaching you".

**Rule.** A video is checked for suitability **after storyboarding, before the card is
written**. Three grounds for rejection:

1. The content isn't about AI in business processes, even though the account fits by its
   bio.
2. Uses someone else's characters, cloned voices, or someone else's intellectual property.
3. Promotes bypassing model restrictions, or anything we don't want to be associated with.

Consequence: reviewing the top tier stops being preparation for a card and becomes part of
selection itself. It is free: ffmpeg cuts the frames, whisper transcribes the speech
locally.

---

## 3. The reference card

One card per proposed video. Fields:

| Field | What's in it |
|---|---|
| Reference link | Direct link to the other person's reel |
| Overperformance | How many times it beat its own creator's median; views; shares and saves per 1000 |
| Hook frames | The first seconds, storyboarded |
| Transcript | The first 10-15 seconds of speech, or a note "no speech" |
| Why it worked | One or two sentences: the mechanic, not a retelling |
| Format | Radar / Builds / Teardown |
| Our angle | What we say on this topic that the reference creator didn't |
| Draft hook | The first line of our video |
| Host | Who's on camera, assigned by topic |
| What we lead to | **Open until the hub decision** |
| Priority | 1-3 |

---

## 4. How someone else's video becomes ours

Formula from the working document:
**popular topic or format → M2 Lab angle → business process → workflow / agent layer →
honest verdict.**

**Retelling check.** If you remove the mention of the source topic from our video, does the
meaning survive? If not, we are retelling someone else's content, and the card needs to be
reworked or dropped.

**Card stop-test.** Three questions. No answer to even one of them, and the card doesn't go
into the plan:

1. **Who specifically will forward this, and why?** Not "this is useful", but "the
   operations director will send this to their IT person because...".
2. **What here is ours?** The angle, the process, or the proof. If nothing, it's someone
   else's content in our packaging.
3. **What will the viewer do afterwards?** Open until the hub decision.

---

## 5. The week

| Day | What happens |
|---|---|
| Monday morning | Radar snapshot, selection, a plan of 8-10 cards |
| Monday afternoon | Misha crosses out |
| Tuesday | Shoot day: all five videos in one block |
| Wednesday-Sunday | Publishing, one a day |
| Thursday | Second radar snapshot: feeds the following week and shows what took off among what's already published |

**Format split:** 2 Radar / 2 Builds / 1 Teardown.
Every other week, a second Teardown replaces the second Radar.
Over a month this gives the stated 35 / 40 / 25.

---

## 6. Edge cases

| Situation | What we do |
|---|---|
| Nothing found for a format within 30 days | We take from the POV list: five theses from the working document, each of which must become a video once a quarter |
| Too many signals | We cut by priority; we don't stockpile the rest, it will go stale within a week |
| Topic repeats for a third week running | Either move it to Teardown with more depth, or close it for a month |
| Reference made the top on the strength of its rates, but fell short on views | We flag it and show it separately: it hasn't «залетело» (blown up), it has «резонировало у своих» (resonated with its own following) |
| Russian-language topic | We don't take it. The account is English-language |

---

## 7. What the first run's data has already shown

Apply when writing up cards:

- **Duration: aim for 45-70 seconds.** Across the top hundred videos the median is 55
  seconds, against 47 for the rest. Under twenty seconds: 5% among the winners, 13% among
  the rest; over ninety seconds: 15% against 8%. A short format isn't just unnecessary, it
  **lands at the top less often**. The 26-44 second stretch seen in August was measured on
  six accounts and wasn't confirmed across the hundred. The thirty seconds from Max's
  package is even less of a benchmark for us.
- **Editing is barely needed.** The median for the top hundred is 0.12 cuts per second, that
  is one every eight seconds. 44 of the 100 videos have almost no cuts, 12 have exactly
  zero. The difference in signals between edited videos and single-take ones is within
  noise. Practical conclusion: with five publications a week and one shoot day, editing is
  not a required condition but a resource to be spent.
- **Shares matter more than saves.** In top videos, shares are four times the baseline,
  saves two and a half times. The question "why send this to a specific person" is stronger
  than "why save this".
- **Comment-bait doesn't add reach, but it adds engagement.** Allowed and used, see
  section 1.
- **Where the niche leads to.** Out of 212 English-language bios: 48% to their own product,
  43% via a link in bio, 23% to a lead form or service, 7% to a community, **2% to a
  newsletter**. The niche has no hub equivalent to Telegram.

---

## 8. How we check that these rules are working

After **12 published videos**: that's a month at a cadence of five a week, the minimum for
any conclusion.

We compare: did the video the radar considered a strong angle land in the top third of our
own videos by shares per thousand views.

We adjust based on the results: the formula's weights, the 30-day freshness threshold, the
formats' pass criteria.

We look at our own statistics, which no competitor measurement has: reach split by followers
and non-followers, retention, and the drop-off point.

---

## 9. Open items

Deliberately marked as open. I will not close them with a decision of my own.

1. **The hub and the "what we lead to" field.** Until this is decided, the field in the card
   stays empty. Niche data is given in section 7. The closest functional equivalent of
   Telegram is Broadcast Channel, already chosen by the working document, but the specifics
   aren't confirmed.
2. **Who edits and who publishes.** Five videos a week means five edits.
3. **The form in Notion:** a task database per video, or a page with the week's plan. A
   separate workspace for M2 Lab, that part is decided.

---

## 10. Discrepancy with the working document

The cadence has changed from "3 publications + 2 Trial Reels" to **5 publications**. Trial
Reels were cancelled by Misha's decision on 1 September. Working document version 3 doesn't
reflect this yet, Misha makes the edit to it himself; I do not edit approved documents.

---

## 11. Language and topics: what real people ask (Reddit pass, 12-13 September 2026)

Source: `reports/audience/07-reddit-pass.md`, 101 threads, 17 subreddits, the last 12 months,
read in full with the top comments through Misha's browser. Personas:
`docs/AUDIENCE_PERSONAS_2026-09-12.md`. Misha's decision: content speaks the language of
ordinary people and answers their actual questions; these rules are mandatory for the angle,
hook, caption and script.

### 11.1. Name the work, not the technology

- The hook and the first 10 seconds describe the task in the viewer's own words: "the same
  20 questions in WhatsApp", "chasing down a lead from a voicemail", "a quote that forgot
  rent and travel", "meeting notes nobody reads". Not "support automation", not "an agent
  for leads".
- Banned in the hook and the first 10 seconds: LLM, RAG, agentic, MCP, API, "agent",
  "workflow", "AI-powered", "revolutionary". The word "AI" is allowed: for the audience it
  means "ChatGPT". The tool's name is said only after the work has been shown.
- We do not use phrases that mark machine-written text, in the script or in the caption:
  "quietly", "it's not X, it's Y", long dashes, "here's what ChatGPT had to say". The
  audience spots posts like this in the first comments and stops trusting them.
- Copy says what the thing does, in simple verbs. Rule from a review of 400+ landing pages:
  "say what the thing does".

### 11.2. What every card must contain (on top of the four fields of the mandatory filter)

1. **An answer to "but is it right the first time?"** Trust is the second-largest request
   (35 of 101 threads). The frame shows a human check step: a queue of drafts, a "yes"
   button, a source document with an owner and a verification date, 20 test questions
   before launch.
2. **A monthly figure, and the point where it stops paying off.** Audience benchmarks: $20
   is the reference point, $100/month is rejected, $200 only if you've hit the limits and
   are counting hours, a $3,000 audit is rejected. The word "free" is not an answer: the
   API bill arrives later.
3. **The boundary of "what stays with the human" is said out loud**, especially: pricing
   (the model doesn't generate a price, it pulls it from a price list), anything that goes
   out to a client, hiring, client data.
4. **We never promise to replace people.** No owner has ever asked for that; employees
   don't save posts like that. We say "hours back", not "without an employee".
5. **Customer-facing use: handle with care.** Chatbots, an AI receptionist, AI images on
   menus and flyers, AI copy are all publicly rejected ("if I see a business using AI, I go
   elsewhere"). The one exception named twice by the audience: handling inquiries outside
   business hours. Our territory is the back office.

### 11.3. Topics people actually ask about (ranked by thread count)

Customer replies and the same questions over and over (9); quotes, pricing, cost of work
(6); chasing down leads, voicemail, appointment booking (6); scheduling, confirmations,
no-shows, spam calls (5); meeting notes to decisions and tasks (6, employees); bookkeeping,
invoices, payroll (4); content and copy (9, but the result isn't trusted); website (5);
product photos (3); internal knowledge base and onboarding (4); one transcript to many
documents (4, employees); candidate screening (2, rejected both times).

"What is AI" was asked 5 times out of 101, and never by an owner in those words. The
owner's own phrasing: "what this actually is, without the hype" and "does it do the job
right the first time".

### 11.4. Mechanics the audience itself upvotes (these are what we show)

Start with one recurring admin task you understand and can check quickly; AI writes a
draft, you approve it with one tap, and the button lives where you already are (in texts,
not in a dashboard); the model doesn't invent a price, it has a price list; one source
document outside the bot, with an owner and a date; 20-30 test questions before launch, a
weekly sample of real conversations; decide first, then AI: this is a fast start, not the
finish line; do it by hand first, automate what worked; one input, one output, so it's
visible when something breaks; the log records decisions and actions, not the conversation;
write down how you calculate a quote and what "done" means, before any tool.

### 11.5. Employees (the Marta persona): three requests of their own

1. "The boss named the process, now how do I automate it": the main one.
2. "The boss uses AI for everything and checks my work through Claude": we answer with the
   move "give that same AI the sources": 69 upvotes in r/msp for "paste in these doc URLs
   as sources".
3. "I'm evaluated on AI adoption, and at the same time forbidden from uploading client
   data": a rule made of four questions (what data, what we scrub, where a human checks,
   are we ready for a confidently wrong answer) as the artefact.

### 11.6. Where this lives in the code

The scriptwriter prompt `engine/prompts/script-writer.md` rule 13, the reviewer
`engine/prompts/script-reviewer.md` check 11, personas
`docs/AUDIENCE_PERSONAS_2026-09-12.md` section "Reddit verdict", shoot list
`docs/SHOOT_LIST_2026-09-13.md`.

---

## 12. Personas and content adaptation (Misha's decision, 13 September 2026)

1. **Three profiles** — `personas/*.json`, readable in `docs/PERSONAS.md`: Rick, 34, owner of a
   plumbing/HVAC company (3-12 people); Emma, 29, founder of a small online business (a Shopify
   brand or a boutique agency, 1-8 people); Anna, 38, operations manager in a 40-person service
   company. Each has a clear profile (age, business, tools, day) and a long list of interests by
   category, derived from the collected data (`reports/audience/01-07`) and written as interests,
   not quotes.
2. **Order of work:** the radar collects what is popular; the server agent finds which of the
   three lists the reel's subject and adapts it to that interest (`engine/persona_adapt.py`,
   prompt `engine/prompts/persona-adapt.md`, contract pa-v1, field `interest`). A reel whose
   subject is in no list stays a reference, not a card.
3. **The comment call-to-action is not mandatory in every video.** It is used where a real
   artefact (`artefacts/`) exists for the viewer to receive.
4. Interest lists grow: new requests from the radar and comments go into the persona JSON.
   Personas are profiles, not real people.

Since 13 September 2026 (§13) personas are no longer the selection axis; they stay as
"on whose example" inside a block.

---

## 13. Content blocks and the "15 in three stages" shortlist (Misha's decision, 13 September 2026)

Personas as a filter cut topics with the potential to take off: expanding the roster per persona
would multiply narrow lanes. Instead the selection axis is the **content block**: what we talk
about at all as "AI for non-technical founders". Personas (§12) live inside a block as the
example (Process, Money, People).

### 13.1. Nine radar blocks and one internal

| # | Block | What it is | Evidence of demand |
|---|---|---|---|
| 1 | Learn | what AI is, how it works, "in a weekend", a jargon-free vocabulary | corpus "learning and skills" 134; Reddit "where to start" 15 |
| 2 | News | a model or feature shipped -> what you do with it tomorrow. News with no job at the end is not taken | corpus "model news" 169 |
| 3 | Process | one business process -> a tool: leads, calls, competitor research, what people write about us | Reddit "automate my process" 38 (largest cluster); corpus 37 — our gap |
| 4 | Money | what it costs, where it stops paying, subscriptions for nothing | Reddit 14; corpus "tokens, cost" 62 |
| 5 | Trust | where AI lies, what not to hand over, checking, policy | Reddit 35 (second cluster); corpus "criticism" 14 — under-served |
| 6 | What to pick | one task, three tools, a winner | Reddit "which tool" 20; corpus "tool review" 118 |
| 7 | Builds | built over a weekend, shown where it broke | corpus "ready repository" 74, "agent building" 61 |
| 8 | Mistakes | anti-hype, "five automations we switched off"; no fear language (I-14) | Reddit "replacing people" 14 |
| 9 | Skills and repos | which skill, MCP or repository to take for a concrete task | corpus "Claude Code skills" 172, "repository" 74 |
| 10 | Answers to comments | internal topic source: comments become the next video. Not in the radar; added when the stream exists | — |

Not blocks (niche filter): coding as such, paywall workarounds, memes, viral effects —
`cards.OFF_TOPICS`.

### 13.2. How a reel gets its block

First path — the **agent** (`engine/block_route.py`, prompt `engine/prompts/block-route.md`,
contract br-v1, files `data/analysis/blocks/<code>.json`): reads caption and transcript, decides
what the reel is about rather than matching single words, quotes 1-3 fragments as evidence and
writes one "about" line for the human who picks 5 of 15 without re-watching all of them. A reel
off the niche or with empty text gets `null` with a reason and stays "Unassigned". Runs on the
server via `claude -p` over every pool reel without a file yet; spends no money.

Fallback — `content_blocks.classify`: the reel's tags (`topics`, dictionary in `topics.py`) plus a
regex pass over the caption and transcript. A tag weighs 2, a word 1 (at most four words). The block with the
highest sum wins; ties go to the earlier block in the list (under-served first: Process, Money,
Trust, Mistakes, What to pick, Learn, Skills, Builds, News). Nothing matched -> "Unassigned":
the reel stays in the pool and competes at stage 2 on strength. The card prints who routed the reel and
on what ("routed by agent: ..." or "routed by tags/regex: ...") plus the "about" line. A hint
with evidence, not a verdict: the human at stage 3 sees the block and may disagree.

### 13.3. The weekly shortlist: 15 in three stages (`cards.select`)

1. **Stage 1, one per block — 9 places.** The block's best reel by shares + saves among those
   that beat their author's own norm by 1.5x. None -> the place is not filled with filler, it
   goes to stage 2. (Trust and Mistakes are rare in the corpus: this will happen.)
2. **Stage 2, by strength — 6 places plus whatever stage 1 left.** Any block, but **at most 3
   reels of one block** in the final fifteen. If the cap leaves candidates short, the shortlist is
   shorter than fifteen — a signal, not an error.
3. **Stage 3, Misha's pick — 5 of 15.** Rule: **at most 2 from one block**. The machine checks
   it rather than enforcing it: `cards.py show` prints a violation from the Notion statuses.

Closed topics (§6) still sink a reel inside its block, never remove it. Used references and
Notion decisions (Not taking, Shot, Published) are excluded.

### 13.4. What the card carries on top of before

Block and stage: "block Money · stage 1: best in block Money" or "stage 2: #3 by strength this
week", the routing evidence, the block's default format. In the database: `cards.block`,
`cards.stage`; in Notion: the Block and Stage properties.

### 13.5. First test run (13 September 2026, local database)

Pool of 580 reels in the window: Builds 130, Unassigned 120, Learn 92, Process 55, Skills 55,
News 50, What to pick 32, Money 28, Mistakes 16, Trust 2. Shortlist 15 of 15: all nine blocks
covered at stage 1. Weak spot: word routing without a tag (a "read these 9 books" reel landed in
Money on the words cost and pay for from its transcript). Next step: routing by an agent over the
transcript with stated evidence; tags and regex stay as the fallback.

### 13.6. What the human sees at stage 3: the decision card (sa-v1, 13 September 2026, evening)

Selection facts were not enough for Misha to decide. Each of the 15 cards goes through an
adaptation stage (`engine/shortlist_adapt.py`, prompt `engine/prompts/shortlist-adapt.md`, files
`data/analysis/shortlist/<code>.json`) and answers three questions in order:
1. **What they shot and what it did:** topic, what the reel shows, why it worked for their audience,
   the result (plays, times the author's own norm, shares and saves per thousand, from our database),
   what does not transfer to us.
2. **Our version:** topic in one line, angle, for whom (a role; §12 personas as the example), and the
   four literal fields of the mandatory filter in `POSITIONING.md` §8: process, friction, AI boundary
   with a visible human check, the viewer's next action; plus the reason to forward. Fails the filter:
   `ours: null` with a reason, the reel stays a reference.
3. **How we shoot it:** format with a reason, 50-70 s, location, presenter, the banner held for the
   whole reel, and the parts per `PRODUCTION.md`: hook ≤ 8 s (payoff first, no technology names),
   explanation, proof (a screen with the human check), payoff (what changed, monthly cost and where it
   stops paying), optional CTA. Each part carries seconds, spoken text, in frame, on screen, overlay
   ≤ 7 words. Parts add up to the duration.
Plus claims with a state (OBSERVED / PLANNED / TO_MEASURE / MISSING). The validator checks the
structure, banned words and length of the hook, the sum of seconds, the CTA artefact file.
Weekly document: `python3 cards.py --dry --md FILE`; the Notion card body is built from the same
file (`notion.py blocks_for`), the card title = our topic.

### 13.7. No evidence, no card (two rules from Misha, 13 September 2026, evening)

1. **No full transcript of the reel and no frames means the reel does not exist for us.** No card,
   no reference, no "shoot it like this". Caption and metrics are not enough: without the spoken
   text and the frames the agent fills the gaps, and things we must not shoot reach the plan.
   **Full** means recognised to the end of the reel: the last speech segment covers at least 90 %
   of the duration (`cards.MIN_COVERAGE`); a fragment does not count. It must also carry something
   to work with (at least 30 words, otherwise there is no speech) and at least one row in `frames`.
2. **English speech only.** An English caption does not count: the language is read from the
   transcript of the whole reel (`ta-v1` `language`, else `transcripts.lang`). Not English, not taken.

**The process this follows from** (`run.py` steps 1 → 2 → 3 → 8):
1. collect reels per blogger (a snapshot over the roster);
2. select the ones that popped: a reel above its author's own norm by 1.5x (`score.py`, `cards.MIN_MULT`);
3. download and **fully** transcribe those reels with frames (`deep.py`, local Whisper, language
   detected) while the video links are alive;
4. only a reel with a full transcript, frames and English speech enters the candidate base that
   blocks, the shortlist and the cards are built from. The `reels` table keeps every collected reel
   as raw material for the author norm; the working base is the pool `cards._pool()`.

Where it lives: `cards.evidence()` and the filter in `cards._pool()`, from which the shortlist,
the blocks, the decision cards and the adaptation all grow. `deep.py` takes the pool **without**
this filter: the deep dive is where a reel acquires its transcript and frames. What was dropped and
why is printed by `cards.py --dry`.

Known cause of the earlier mistakes: until 13 September the local ASR ran with English forced and
**translated** Hindi speech into English, so the base called such reels English (card 8 in the
13 September shortlist). Since 13 September the language is detected (`engine/local_pipeline.py`);
older transcripts without `ta-v1` may carry a wrong language.

Check on the 13 September shortlist: 6 of 15 cards had full evidence (1, 3, 4, 9, 14, 15); 8 were
made from a caption alone, one from Hindi. Under these rules the pool on 13 September is 105 reels
instead of 427 (460 without a full transcript, 4 not English).
