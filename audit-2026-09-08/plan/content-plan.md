# M2 Lab content plan: ten topics, six to choose

8 September 2026. Structure fixed by Max: 5 introduction posts (4 on a direct reference reel, 1 new positioning
scenario) and 5 regular posts (4 replicating a best performer, 1 synthesis). Every number comes from
`data/top-reels.csv`, `data/topics.csv`, `data/radar-data.md` or the database `radar-0907.db`, or is marked
"to measure". Reference metrics read as: views, shares per 1,000, saves per 1,000, the multiple of the author's
own median views, the robust score `z` (capped at 5), duration.

## What the data decided

- Shares separate a winner 3.6 times more reliably than any other metric, saves 2.8 times (`stats.py`, quoted in
  `radar-data.md` section 3). Radar is picked on shares, Builds and Teardowns on saves.
- A reply traded for a file appears in 28 percent of top reels and 26 percent of the rest. No advantage, so we
  take the structure of those reels and never the trade.
- Our territory is empty, not saturated. The tag "AI in a specific business process" has 29 scored reels, median
  score 0.473, and zero entries in the top 100. Next to it "AI agency as a business" has 80 reels and 5 of the
  top 100, "Design and websites via AI" 117 reels and 9. Three reels from one agency account hold six of the top
  15 rows.
- The ceiling in this data is the multiple of the author's own median: 80.3 times (`@nocode.joshua`), 77.5 times
  (`@aiforbusinesses247`), 63.3 times (`@okaashish`). All three gave something away.
- Winners cluster near 55 seconds, which is our five-beat structure already.
- The angle nobody occupies: the economics of adoption. Nothing in the top 150 prices a workflow honestly except
  `@heystevetan`, and that reel is the fourth strongest in the set.

This plan leans on workflow and economics topics because that angle is the one the data shows as under-served,
not because it is the only content that counts. Misha's scope note of 8 September (night) confirms educational
and informative pieces for a small or medium business leader are in scope too: prompting for a task, a
repository that builds a deliverable, adding an agent to answer leads faster. None of the ten below is one of
these; they are named here as candidates for the next plan, each with its account and metric from
`data/topics.csv` / `data/top-reels.csv`:

- Prompting/setup technique: `@badarmunir_official`, DZU9x_1AY2t, z 3.56, 1,277,918 views, 32,925 shares, a
  skill-and-MCP setup that changes what the same prompt gets you.
- Repository that builds a deliverable: `@liamjohnston.ai`, DczDlj4qQjI, z 4.85, 161,211 views, 3,833 shares,
  offering a full repo and setup guide to anyone who asks for it in the comments.
- Agent for faster lead/customer response: `@edhillai`, DNA7-d3o5sQ, z 4.03, 451,472 views, 10,536 shares, a
  voice assistant that books appointments straight into the calendar.

## Where we deliberately differ from Max's cards

All ten 7 September cards (M2-I01 to I05, M2-P01 to P05) are in `notion-raw/10..19`. Against them: (1) Max's
cards are fictional throughout, every demonstration is `DESIGNED_NOT_MODEL_EXECUTED` and the scripts say
"imagine" or "suppose", while ours use our own runs, screens and spend log, which the brand requires under "Is the
proof ours?"; (2) Max names no tool and no number, ours names the tool or says none and labels every figure WAS,
NOW, SAVED or to measure; (3) Max's cards carry no verdict, every card below carries KEEP, TEST or KILL; (4) Max
builds no card on a reference device, eight of ten below name the reel whose device we borrow. Two thematic
overlaps exist and are kept on purpose: topic 08 and M2-P04 both start from a vendor pitch (ours ends on the one
irreversible step and a KILL condition, his on a checklist of questions); topic 09 and M2-P05 both touch a
failure column in a shortlist (ours is our own machine-first read of the radar with a person cutting cards, his
is advice to the viewer). No hook or premise is repeated.

All ten covers sit on the Paper surface. "Plate" below means the title's key-phrase plate: Ink with Paper text
by default, Oxide only where the phrase names something broken. Stickers are the Paper-surface files; the Ink
variants 51 to 65 are for dark covers only, which this plan does not use.

---

## 01. Somebody now owns AI, and nobody wrote the job

- **Type / format** Intro by reference. M2 Radar.
- **Reference** `@nicksadler.io`, `Db5e866oSPq`, https://www.instagram.com/reel/Db5e866oSPq/, 11 Aug 2026.
  206,966 views, 12.1 shares/1k, 35.0 saves/1k, 11.6 times the author's median of 17,919, z 3.38, 39.1 s. No
  transcript and no frames on disk, caption only.
- **Device** It turns a vendor release into a job description: it names a role a small business now has to fill,
  then attaches it to a named product shipping a fixed count of prebuilt workflows. The viewer pictures a person.
- **Why it is the reference** The only reel in the top 150 that says "small business" and still lands 35 saves per
  1,000 against an author median of 17,919. It proves our audience is reachable through a role, not a tool.
- **Hook** Somebody in your company now owns AI. Nobody wrote the job.
- **Problem** The person told to figure out AI for a team of five to fifty. No brief, no budget line, no
  definition of done. They open a chat window on Monday and guess.
- **Solution** We write that job in public, one repeated workflow at a time: pick the workflow, break it into
  fragments, draw the AI boundary, name who approves. Michael is the named approver and signs every verdict.
- **Tool** None. This episode names no product on screen.
- **CTA** Write the one sentence your AI owner is missing: which workflow, whose approval, what a wrong answer
  costs.
- **Why now** A vendor shipped prebuilt small-business workflows on 11 Aug 2026 and that reel is still the highest
  saving small-business reel in the window. The open question this fortnight is who operates them.
- **Utility** A three-line role definition the viewer writes in the last beat.
- **Verdict / proof** TEST. It is our own working practice and has never been tried outside a two-person team.
  Before shooting: our filled-in three-line definition for the radar workflow, on screen, Michael named.
- **Cover** "Somebody now owns AI / Nobody wrote the job"; key phrase `Nobody wrote the job` on an Oxide plate, it
  names what is broken. Visual: `42-role-chip` at 2x with an empty name slot, `15-callout-human-step` under it at
  a 24 px gutter. Caption word: owner.
- **Risk** 1 Yes, who operates an AI workflow, decided weekly. 2 Yes, the brief does not exist. 3 Yes, the
  approver is on screen. 4 Yes, three lines to write. Brand rule: naming a vendor in an introduction can read as a
  tool review, so the product stays in the caption and never on screen.

## 02. Before AI touches it, write the cost down

- **Type / format** Intro by reference. M2 Teardowns.
- **Reference** `@shrug.manny`, `DbO4zvJR1k8`, https://www.instagram.com/reel/DbO4zvJR1k8/, 25 Jul 2026. 209,121
  views, 52.9 shares/1k, 87.4 saves/1k, 15.2 times the author's median of 13,729, z 3.39, 71.5 s. Transcript 274
  words, frames and contact sheet on disk.
- **Device** Credential first, then a numbered checklist where every line names the cost of getting it wrong.
  Transcript opens "My app has over 17,000 users", then item two attaches a figure to the omission. The reason to
  forward is the consequence, not the tip.
- **Why it is the reference** Highest saves per 1,000 in the entire top 150 and second highest shares per 1,000.
  It is the strongest single device in our data: a checklist with a price on each line.
- **Hook** Before AI touches a process, we write down what a wrong answer costs.
- **Problem** A team lead connects a chat model to something customer-facing and learns the cost of an error after
  the error. The fear in our audience file is an AI mistake reaching a customer.
- **Solution** Our four-question filter run out loud on one process: which repeated workflow, where the friction
  is, what the model does and what stays human, what the viewer does next. Each answer gets a cost line. Max reads
  the filter, Michael signs the sheet.
- **Tool** None. Paper and our own filter.
- **CTA** Take the workflow you ran three times last week and write one line: what does one wrong output cost, in
  money or in trust.
- **Why now** Our 7 September run proposed nine cards and struck four against exactly these questions. The filter
  has teeth we can show this week.
- **Utility** The four-question sheet as a file, with our own four cost lines filled in.
- **Verdict / proof** KEEP; the filter stays in our workflow and the evidence is the four cards it removed on 7
  September. Before shooting: a screenshot of the nine proposed cards with the four struck rows visible, from the
  `cards` table of `radar-0907.db`.
- **Cover** "Before AI touches it / write the cost down"; key phrase `write the cost down` on an Ink plate.
  Visual: `27-checklist-row-states` at 2x, three rows, `50-meta-source-plate` beneath. Caption word: checklist.
- **Risk** 1 Yes, the decision to connect a model to a live process. 2 Yes, cost of error is unpriced. 3 Yes, the
  filter's third question is the boundary. 4 Yes, one line to write. Brand rule: the reference is a legal
  checklist and we are not lawyers, so we borrow the shape and never the legal content.

## 03. Same prompt twice, one answer is wrong

- **Type / format** Intro by reference. M2 Builds.
- **Reference** `@tech_with_tim`, `Dc0-SwfSXDe`, https://www.instagram.com/reel/Dc0-SwfSXDe/, 3 Sep 2026. 5,378
  views, 3.9 shares/1k, 20.3 saves/1k, 2.24 times the author's median of 2,398, z 3.62, 62.6 s. Transcript 219
  words, no frames on disk, needs a re-pull.
- **Device** The same-input comparison, shown rather than claimed. Transcript: "Same model, same prompt, but no
  agent. I get a wall of text... the model was never the problem. It's everything around the model that was
  missing." One cut carries the whole proof.
- **Why it is the reference** It beat its author's median by 2.24 times on a small base five days ago, with no
  giveaway and no trade for a reply. The device carries it alone.
- **Hook** Same request, twice. One went through a chat box, one went through our workflow.
- **Problem** A manager tries a model on a real task, gets a fluent paragraph, cannot tell whether it is right,
  and concludes AI is not ready. The missing piece is the wrapper, not the model.
- **Solution** We run one real request from our own week twice on camera: bare chat, then the same request inside
  our workflow with the source attached and the review step. Max runs both, Michael reads the two outputs and
  marks the sentence that is unsupported.
- **Tool** The chat model we already pay for, plus our own workflow file. No new purchase.
- **CTA** Take one request you sent to a chat window last week and run it again with the source document
  attached. Compare the two answers.
- **Why now** Three of the freshest reels in the window (1 and 2 Sep) react to a new model version. This piece
  answers them with the opposite claim: the version is not the variable this week.
- **Utility** The two outputs side by side as a screenshot, plus the one-line instruction that made the difference.
- **Verdict / proof** KEEP; the wrapper stays in our own workflow, and the published failure is that it does not
  help when the source document itself is wrong. Before shooting: both runs recorded on our own screen, same
  prompt, same model, timestamped, with the unsupported sentence circled.
- **Cover** "Same prompt twice / One answer is wrong"; key phrase `One answer is wrong` on an Oxide plate.
  Visual: `37-screen-browser` at 2x holding the split output, `20-marker-broke-here` on the wrong line. Caption
  word: wrapper.
- **Risk** 1 Yes, any repeated request a manager sends to a chat window. 2 Yes, the output cannot be checked.
  3 Yes, the review step is on screen. 4 Yes, rerun one request. Brand rule: this sits close to a technical demo,
  so the framing stays on the work request and never on the mechanism.

## 04. What our AI workflow really costs to run

- **Type / format** Intro by reference. M2 Radar.
- **Reference** `@heystevetan`, `DbVq4mwz38L`, https://www.instagram.com/reel/DbVq4mwz38L/, 28 Jul 2026. 439,974
  views, 27.9 shares/1k, 54.0 saves/1k, 27.8 times the author's median of 15,832, z 5.0 (capped), 53.5 s.
  Transcript 213 words, frames and contact sheet on disk.
- **Device** Price arithmetic as the whole story, including the part that stays expensive. The transcript names
  the incumbent price band, then "the price climbs with how many people trigger your automation", then the honest
  cost of the free alternative: hosting, a few dollars a month, and setup work that is real.
- **Why it is the reference** 27.8 times its author's median and 54 saves per 1,000, earned by naming the ongoing
  cost instead of hiding it. That honesty is the exact angle our data shows nobody else occupies.
- **Hook** Our weekly AI run cost two dollars and twelve cents. Here is the rest of the bill.
- **Problem** A leader is quoted a subscription price and budgets that number. The real bill is setup hours, run
  cost, review minutes and one wrong output.
- **Solution** We open our own spend log on screen: 623 data requests and 12 dollars 46 to build the radar between
  1 and 3 September, then 2 dollars 12 for the 7 September run over 106 accounts and 1,260 reels, 78 minutes wall
  clock. The line we have not measured is human review time, and we say so. Max owns the run, Michael reviews it.
- **Tool** Our own radar, built on a data API charged per request.
- **CTA** Open your last AI invoice and add the two lines it does not show: setup hours and review minutes.
- **Why now** The first fully automatic run happened on 7 September, so a weekly figure exists for the first time
  and can be shown as a receipt.
- **Utility** Our spend log as a screenshot, and a five-line cost sheet the viewer copies.
- **Verdict / proof** KEEP, on the condition that review time is still unmeasured. Before shooting: a screenshot
  of the `spend` table showing 623 units at 12.46 and 106 units at 2.12, plus a stopwatch on one review pass.
- **Cover** "What our AI workflow / really costs to run"; key phrase `really costs to run` on an Ink plate.
  Visual: `21-numbers-was-now-saved` at 2x with the third plate empty and labeled to measure,
  `19-stamp-tested-own-process` beside it. Caption word: receipt.
- **Risk** 1 Yes, running a weekly AI workflow. 2 Yes, the invoice hides two lines. 3 Yes, the review line is
  human and unmeasured. 4 Yes, open one invoice. Brand rule: a bare number never ships, so every figure on screen
  carries WAS, NOW, SAVED or the label to measure.

## 05. You looked for help and found a pitch

- **Type / format** Intro, new positioning scenario. M2 Teardowns.
- **Reference** None. Derived from `data/topics.csv` and `data/top-reels.csv`: "AI in a specific business process"
  has 29 scored reels, median score 0.473 and zero entries in the top 100, while "AI agency as a business" has 80
  reels and 5 of the top 100 and "Design and websites via AI" 117 reels and 9. Three reels from one agency account
  occupy six of the top 15 rows.
- **Device** Ours. Name the search, show what the search returns, then show what was actually needed. The tension
  is the gap between the two, and the gap is measured rather than asserted.
- **Hook** You looked for AI help with your process. What you found was somebody selling an agency.
- **Problem** The operations lead of a small firm searches for how AI fits one repeated process and the feed
  answers with income offers and agency funnels. They leave with no decision, and next quarter the same process
  eats the same hours.
- **Solution** We do what the search does not: put one repeated workflow on the table, break it into fragments
  with inputs, outputs, decisions and risks, mark where the model stops, name who approves. Michael owns the
  fragmentation sheet, Max builds only what survives it.
- **Tool** None. One page, four columns.
- **CTA** Take the workflow you ran three times last week and fill four columns: input, output, decision, risk.
- **Why now** The 7 September snapshot is the first scored across 106 accounts and it confirms the hole: zero of
  the top 100 reels sit in our own topic. This is the week to plant the flag.
- **Utility** The fragmentation sheet as a page, with our radar workflow filled in as the worked example.
- **Verdict / proof** Teardown verdict card: KEEP the collection and drafting fragments as AI-assisted, KILL the
  automatic send, mark the acceptance decision human-owned. Before shooting: our own fragmentation sheet for the
  radar, photographed, with the AI boundary drawn on the page by hand.
- **Cover** "You looked for help / and found a pitch"; key phrase `and found a pitch` on an Ink plate. Visual:
  `39-screen-document-card` at 2x standing for the fragmentation sheet, `43-human-review-plate` under it. Caption
  word: process.
- **Risk** 1 Yes, the viewer's own first repeated workflow. 2 Yes, the search returns pitches. 3 Yes, the boundary
  is drawn on the page. 4 Yes, four columns to fill. Brand rule: this criticizes a neighboring niche, so we name a
  pattern and a measurement and never an account.

## 06. It ranked nine ideas, a person cut four

- **Type / format** Regular by reference. M2 Builds.
- **Reference** `@olivermerrick___`, `DbVKVz0y8xo`, https://www.instagram.com/reel/DbVKVz0y8xo/, 28 Jul 2026.
  61,507 views, 32.6 shares/1k, 56.0 saves/1k, 6.7 times the author's median of 9,181, z 3.71, 87.4 s. Transcript
  315 words, frames and contact sheet on disk. Already chosen as a reference by our own radar, card 1 of week
  2026-09-03.
- **Device** Name the easy part, then name precisely what the model cannot do. Transcript: "if clipping is so easy
  why isn't everyone going viral... Because the AI knows how to cut a video but it doesn't know the exact moment
  that needs to be a clip. It has no context." The reason to forward is the sentence identifying the missing
  judgment.
- **Why it is the reference** 32.6 shares and 56.0 saves per 1,000, the best combined pair in the top 150 outside
  the checklist reel, on a mid-sized account, with no giveaway.
- **Hook** Our tool ranked nine ideas this Monday. A person cut four of them.
- **Problem** A team automates a selection step, trusts the ranking, and publishes something the company should
  not have said. Ranking is not deciding.
- **Solution** We show the run: 1,260 reels collected, 1,255 scored, 1,156 through the entry gate, 97 taken apart
  frame by frame, nine cards proposed. Then the four a person removed and the rule each failed. The tool ranks,
  Michael decides, and the reason is written next to the removal.
- **Tool** Our own radar, with the scoring rule that compares a reel against its own author's median rather than
  against the crowd.
- **CTA** Find the step where a tool proposes and nobody records why the proposal was rejected. Start recording it.
- **Why now** The 7 September run is the first that proposed and struck cards with no person in the loop until the
  review point. The record exists as of this week.
- **Utility** The nine proposals and four removals as a screenshot, plus the rule list that did the removing.
- **Verdict / proof** TEST; the ranking stays, the selection is not automatable, and we will not try again until
  rejection reasons are counted for four weeks. Before shooting: the `cards` export for week 2026-09-07 showing
  nine rows and four struck, plus a screen recording of one removal being written.
- **Cover** "It ranked nine ideas / A person cut four"; key phrase `A person cut four` on an Ink plate. Visual:
  `30-ranked-row` at 2x, `15-callout-human-step` pointing at the cut row. Caption word: judgment.
- **Risk** 1 Yes, weekly selection of what to publish or pursue. 2 Yes, rejections are never recorded. 3 Yes, the
  tool ranks and the person decides. 4 Yes, start recording rejections. Brand rule: it is our own process, so it
  must be told as a process the viewer also has, not as a tour of our tooling.

## 07. A new model shipped, here is what changed

- **Type / format** Regular by reference. M2 Radar.
- **Reference** `@nicksadler.io`, `DczFndzonGV`, https://www.instagram.com/reel/DczFndzonGV/, 2 Sep 2026. 24,622
  views, 8.3 shares/1k, 36.3 saves/1k, 4.05 times the author's median of 6,081, z 3.24, 47.6 s. Transcript 170
  words, no frames on disk. Supporting: `@nivedan.ai`, `Dcvt2gcpLMR`, 1 Sep 2026, 61,975 views, 17.3 shares/1k,
  1.82 times its author's median, same week, same trigger.
- **Device** The bounded test window: "I've tested it for the last 24 hours", one exact prompt on screen, the
  version named, plus one setup detail the viewer would otherwise miss. The bound makes the claim checkable.
- **Why it is the reference** Four times its author's median within a day of a version landing, on saves. It is
  also the clearest example of what we must not copy: it claims a revenue plan with no baseline and closes by
  trading a reply for a file.
- **Hook** A new model version landed last week. Here is the one step it changed in our week.
- **Problem** Every release resets the team's confidence. The lead asks whether to switch and nobody can answer,
  because nobody ran the old and the new on the same task.
- **Solution** We run one fixed task from our own week, unchanged, on both versions, and report the one step where
  the output differed and the one where it did not. Max runs the pair, Michael reads both and writes the condition.
- **Tool** Named at shoot time: the exact model versions we ran, both of them.
- **CTA** Keep one fixed task and one fixed input. Run it on every version you are asked to switch to, before you
  switch.
- **Why now** Three reels in the freshest part of the window (1 and 2 Sep) react to the same version. Our Radar
  rule asks whether the topic survives three to seven days; this one does, and it decays straight after.
- **Utility** Our fixed-task file, so the viewer has a test to reuse on the next release.
- **Verdict / proof** TEST, with the condition written on the card. Before shooting: both runs on our own screen
  with the version string visible and a stopwatch on each.
- **Cover** "A new model shipped / here is what changed"; key phrase `here is what changed` on an Ink plate.
  Visual: `32-bar-compare-card` at 2x, two bars on one scale for the same task, `18-verdict-test` chip at 2x under
  it. Caption word: verdict.
- **Risk** 1 Yes, the recurring switch decision. 2 Yes, no fixed task exists to compare on. 3 Yes, a person writes
  the verdict condition. 4 Yes, keep one fixed task. Brand rule: model news without a work decision is on the
  do-not-publish list, so the piece opens on the task and names the version second.

## 08. This pitch skips one step you cannot undo

- **Type / format** Regular by reference. M2 Teardowns.
- **Reference** `@aiforbusinesses247`, `DZLDk9ySi-7`, https://www.instagram.com/reel/DZLDk9ySi-7/, 4 Jun 2026.
  176,465 views, 42.1 shares/1k, 45.6 saves/1k, 77.5 times the author's median of 2,277, z 5.0 (capped), 47.5 s.
  Transcript 140 words, frames and contact sheet on disk.
- **Device** End-to-end outcome narration with the frictions listed as removals: find local businesses without a
  website, build a demo, send a personalized email, book the meeting. No proof at any step, and the second highest
  multiple in the whole set.
- **Why it is the reference** This is the account that makes our own topic read as a sales funnel. Answering the
  process it describes, honestly, is the fastest way to claim the territory. We rebuild the process on paper and
  use none of its footage.
- **Hook** This pitch automates finding a lead, writing a demo and sending it. One of those steps we do not
  automate.
- **Problem** A small services firm wires up outbound and finds the failure mode late: a wrong output goes out
  under the company name, to a stranger, and cannot be recalled.
- **Solution** The map on screen, CURRENT, AI LAYER, VERDICT. Research and drafting go to the model. The send
  stays human, because the cost of error is a customer who never replies again. Michael presses send.
- **Tool** Named at shoot time for the research step only. The send step uses no tool.
- **CTA** In your outbound process, mark the last step before something leaves the building and write the name of
  the person who owns it.
- **Why now** This reel returns in both snapshots and the pattern repeats across the niche's top rows this
  fortnight. The demand is proven; the honest version is missing.
- **Utility** The three-column map as a file, and the one-line rule for where a send stops.
- **Verdict / proof** Teardown verdict card: KEEP the research fragment, TEST the drafting fragment, KILL the
  automatic send. Before shooting: our own run of the research fragment on ten real companies with a count of the
  rows that came back wrong. If nothing comes back wrong, the piece does not ship.
- **Cover** "This pitch skips one / step you cannot undo"; key phrase `you cannot undo` on an Oxide plate. Visual:
  `28-step-chain-3` at 2x with the third box marked, `17-verdict-kill` chip at 2x beside it. Caption word:
  boundary.
- **Risk** 1 Yes, outbound to a list, run weekly. 2 Yes, the irreversible step. 3 Yes, the send is human-owned.
  4 Yes, name the owner of the last step. Brand rule: somebody else's footage may never be the substance of a
  piece, so we rebuild the process from its transcript and shoot our own screens.

## 09. A machine reads it before a person does

- **Type / format** Regular by reference. M2 Builds.
- **Reference** `@nocode.joshua`, `DcE150pz_Rj`, https://www.instagram.com/reel/DcE150pz_Rj/, 15 Aug 2026.
  549,700 views, 14.6 shares/1k, 66.7 saves/1k, 80.3 times the author's median of 6,845, z 3.42, 90.5 s. No
  transcript and no frames on disk, caption only. Supporting: `@nicksadler.io`, `DbmEt-Zo1ap`, 3 Aug 2026, 42.9
  saves/1k, 40.5 s, transcript 123 words, the giveaway device in its cleanest form.
- **Device** The time budget. The caption converts intent into a scheduled slot and the list becomes a saveable
  object. Highest multiple of an author's median in the whole set and 66.7 saves per 1,000. We take the time
  budget and refuse the list, because a generic tool list is on our do-not-publish page.
- **Why it is the reference** It proves a stated time budget plus one saveable artifact is the strongest save
  device available to us without a trade for a reply.
- **Hook** Every line we publish is read by a machine before a person sees it.
- **Problem** Any team with a style rule, a compliance line or a banned claim relies on a person remembering it at
  the end of a long day. The rule is written once and enforced never.
- **Solution** We show our own pre-publication check running on this very script: it reads the copy against the
  banned list, the hook length and the punctuation rule, and returns the failures. Then it hands over to Michael,
  who checks the one thing it cannot, whether the claim is true.
- **Tool** Our own copy checker, a small script over a written rule list. No subscription.
- **CTA** Write down the three things you always fix by hand in outgoing copy. That list is the check.
- **Why now** The rule list was finalized on 8 September and the script now runs on every piece we ship, including
  this plan.
- **Utility** The rule list as a file the viewer copies, and the run output on screen with its error count.
- **Verdict / proof** KEEP; the failure published in the same piece is that it catches a forbidden word and cannot
  catch a false claim, which is exactly why the human step stays. Before shooting: a recorded run of the check on
  this content plan showing the error count before and after, and one error it misses on purpose.
- **Cover** "A machine reads it / before a person does"; key phrase `before a person does` on an Ink plate.
  Visual: `40-screen-terminal-card` at 2x on an Ink surface holding the run output, `54-callout-human-step-ink`
  under it. Caption word: check.
- **Risk** 1 Yes, publishing or sending copy, weekly or daily. 2 Yes, the rule is remembered and not enforced.
  3 Yes, the machine catches words and the person catches claims. 4 Yes, write three rules down. Brand rule: it is
  our own tool, so it is presented as a practice and never as a product we are selling.

## 10. Five lines tell you what your run costs

- **Type / format** Regular synthesis. M2 Radar.
- **References combined, five devices** (1) `@shrug.manny` `DbO4zvJR1k8`, 25 Jul 2026, 52.9 shares/1k, 87.4
  saves/1k, 15.2 times median, 71.5 s: a numbered line with a named cost on each. (2) `@heystevetan`
  `DbVq4mwz38L`, 28 Jul 2026, 27.9 shares/1k, 54.0 saves/1k, 27.8 times median, 53.5 s: price arithmetic that
  includes the cost that does not go away. (3) `@nocode.joshua` `DcE150pz_Rj`, 15 Aug 2026, 66.7 saves/1k, 80.3
  times median, 90.5 s: the stated time budget. (4) `@tech_with_tim` `Dc0-SwfSXDe`, 3 Sep 2026, 20.3 saves/1k,
  2.24 times median, 62.6 s: proof shown in one cut rather than asserted. (5) `@olivermerrick___` `DbVKVz0y8xo`,
  28 Jul 2026, 32.6 shares/1k, 56.0 saves/1k, 6.7 times median, 87.4 s: name the judgment the model lacks.
- **What the five share** Every one hands the viewer a number or a comparison they can check themselves, and not
  one requires trusting the author. That is the mechanic we combine, and the subject nobody in the top 150 covers
  is what a workflow costs to keep running.
- **Hook** Five lines tell you what one AI workflow costs you in a week.
- **Problem** A leader approves a workflow on the subscription price alone, then meets the setup hours, the
  per-run charge, the review minutes and the price of one wrong output. The budget was wrong before the first run.
- **Solution** The five-line cost sheet filled in live on our own radar: build cost 12 dollars 46 over 623 data
  requests, weekly run 2 dollars 12 over 106 accounts, wall clock 78 minutes, review minutes to measure, cost of
  one wrong card to measure. Michael reads the sheet before any workflow gets a second week.
- **Tool** The cost sheet itself, one page. No purchase.
- **CTA** Fill the five lines for the workflow you ran three times last week. Stop at the line you cannot fill;
  that line is your next measurement.
- **Why now** The 7 September run is the first with a real weekly figure attached, and the niche is arguing about
  model prices without counting the other four lines.
- **Utility** The five-line sheet as a file, with our numbers in it and two lines honestly empty.
- **Verdict / proof** TEST; two of the five lines are unmeasured on our own process, so the sheet is a method we
  are running and not a result we are claiming. Before shooting: a stopwatch on one full review pass, and one
  deliberately wrong card costed in minutes of rework.
- **Cover** "Five lines tell you / what your run costs"; key phrase `what your run costs` on an Ink plate. Visual:
  `26-list-numbered-row` stacked at 2x with two rows visibly empty, `50-meta-source-plate` beneath. Caption word:
  cost.
- **Risk** 1 Yes, approving and renewing an AI workflow. 2 Yes, four of five cost lines are invisible at approval.
  3 Yes, the sheet is read by a named person. 4 Yes, fill five lines. Brand rule: a cost-saving claim without a
  published baseline is forbidden, so two lines stay empty on screen and are labeled to measure.

---

## Closing table

| # | Title | Type | Format | Verdict | Pick |
|---|---|---|---|---|---|
| 01 | Somebody now owns AI, and nobody wrote the job | Intro by reference | Radar | TEST | No. Strong role framing, but the proof is a definition and not a run. Hold for week 2. |
| 02 | Before AI touches it, write the cost down | Intro by reference | Teardowns | KEEP | **Yes.** Strongest device in the data at 87.4 saves/1k, and our four cost lines already exist. |
| 03 | Same prompt twice, one answer is wrong | Intro by reference | Builds | KEEP | **Yes.** Pinned introduction. One cut proves the whole positioning and needs no tool. |
| 04 | What our AI workflow really costs to run | Intro by reference | Radar | KEEP | **Yes.** Owns the empty angle with a receipt we already hold. |
| 05 | You looked for help and found a pitch | Intro, new scenario | Teardowns | Card | No. The measurement is right, but it argues about the niche instead of the viewer's Monday. |
| 06 | It ranked nine ideas, a person cut four | Regular by reference | Builds | TEST | **Yes.** Our best own-proof Build: nine proposals, four removals, all in the database. |
| 07 | A new model shipped, here is what changed | Regular by reference | Radar | TEST | No, first alternate. Freshest signal in the window and the fastest to decay; publish within seven days or drop it. |
| 08 | This pitch skips one step you cannot undo | Regular by reference | Teardowns | Card | No. Highest-demand topic, but it needs our own ten-company run first. |
| 09 | A machine reads it before a person does | Regular by reference | Builds | KEEP | **Yes.** Real tool, real failure, real file, and the check runs on the script itself. |
| 10 | Five lines tell you what your run costs | Regular synthesis | Radar | TEST | **Yes.** The synthesis of five winning devices on the one subject the niche does not cover. |

**The recommended six, in publish order.** 03 as the pinned introduction, which sits outside the weekly cadence,
then a week of 04 Radar, 09 Builds, 02 Teardowns, 10 Radar, 06 Builds. That is 2 Radar, 2 Builds and 1 Teardown,
alternating, with three introduction posts carried inside the week rather than stacked in front of it. Formats
alternate so that no two consecutive pieces answer the same audience question.

**What has to exist before any of the six is shot.** A screenshot of the `spend` table; a screenshot of the nine
cards with four struck; one recorded double run of the same prompt; one recorded run of the copy check with its
error count; a stopwatch on one review pass. Five artifacts, all from our own work, none of them borrowed.
