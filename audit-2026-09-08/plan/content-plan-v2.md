# M2 Lab content plan v2: ten topics, six to choose

8 September 2026. Version 2, written after the scope widened. Structure fixed by Max: 5 introduction posts (4 on a direct reference reel, 1
new scenario) and 5 regular posts (4 replicating a best performer, 1 synthesis). Every number comes from `data/top-reels.csv`,
`data/topics.csv`, `data/radar-data.md`, `radar-0907.db` or `runs/2026-09-07/README.md`, or is marked "to measure". Reference metrics read
as: views, shares per 1,000, saves per 1,000, the multiple of the author's own median, the robust score `z` (capped at 5), duration.

## What changed from version 1

1. **Scope.** Misha, 8 September, night: we cover how small and medium businesses put AI into their processes. Prompting for a real task, a
   repository that builds a deliverable, adding an agent to lead response and a tool walkthrough are all in scope, alongside the workflow
   and economics teardowns version 1 was built on. The plan is now five educational or informative pieces (01, 02, 03, 06, 07) and five
   workflow and economics pieces (04, 05, 08, 09, 10). Out of scope is unchanged: developer-only tutorials, agent infrastructure for
   builders, generated personas, cloned voices, bypassing restrictions, hype, and trading a reply for a file.
2. **The verdict is optional** (`06-formats.md`, changelog 8 Sep). Four of the ten below close on a plain one-sentence conclusion instead of
   a Verdict Card: 03, 05, 10, and 09 until its run decides.
3. **The source gate is applied and it removed most of version 1's references.** A reference now has to sit between 1.5 and 20 times its
   author's own median, on a baseline of 20 reels or more, with a transcript, and carry a topic a small business leader can act on. Nine of
   version 1's ten references fail: `DbVq4mwz38L` (27.8 times, baseline 5), `DcE150pz_Rj` (80.3 times, baseline 13, no transcript),
   `DZLDk9ySi-7` (77.5 times, baseline 13), `DbO4zvJR1k8` (baseline 9), `Dc0-SwfSXDe` (baseline 6), `DczFndzonGV` (baseline 5),
   `Db5e866oSPq` (baseline 19, no transcript), `Dcvt2gcpLMR` (baseline 5), `DbmEt-Zo1ap` (1.03 times, no outperformance); `DbVKVz0y8xo`
   misses on baseline 16. A multiple of 80 on a median of 6,845 is one outlier, not a device that repeats, which is the error the card audit
   found in Max's slate. All ten topics are re-referenced on reels that pass.
4. **Covers.** All ten sit on the Paper surface with the key phrase on an Ink plate carrying Paper text, as `rules/typography.md` requires;
   Oxide appears only where a phrase names something broken, and every sticker named is a Paper-surface file in `stickers/manifest.json`.

## What the data still says

- Shares separate a winner 3.6 times more reliably than any other metric, saves 2.8 times (`stats.py`, quoted in `radar-data.md` section 3).
  Radar is picked on shares, Builds and Teardowns on saves.
- Our territory is still empty. "AI in a specific business process" has 29 scored reels, median score 0.473 and zero of the top 100; "AI
  agency as a business" has 80 reels and 5 of the top 100; "Design and websites via AI" 117 reels and 9 (`topics.csv`).
- Inside the gated set the two strongest forwarding devices are a numbered settings walkthrough that names the stake on step one (58.4
  shares and 58.9 saves per 1,000) and a role board where each agent is a named job (41.4 shares per 1,000). Both are teachable formats, so
  the wider scope is not a softer scope.
- A reply traded for a file appears in 28 percent of top reels and 26 percent of the rest, so it buys nothing. Six of our eight references
  end on that trade; not one of our CTAs does.

## Where we differ from Max's cards

All ten cards of 7 September are in `notion-raw/10..19`. His demonstrations are fictional and labeled `DESIGNED_NOT_MODEL_EXECUTED`, ours
are our own runs and screens; he names no tool and no number, we name the tool or say none and label every figure WAS, NOW, SAVED or to
measure; he builds no card on a reference device, eight of the ten below name the reel whose device we borrow. Thematic overlaps kept on
purpose, with the difference stated: topic 04 and P04 both interrogate an automation before it is bought (ours prices one step and kills the
automatic send, his asks a list of questions); topic 06 and P01 both concern the reply to an inbound message (ours is a build measured on 20
real messages, his is a branch map); topic 07 and P05 both add a check before adoption (ours is a scan with a score on a file we installed,
his is a shortlist column). No hook and no premise is repeated.

---

## 01. One file per job beats a new prompt

- **Type / format** Intro by reference. M2 Builds. Educational: a prompt technique for a concrete task.
- **Reference** `@albert.olgaard`, `DVtgbY8Av6A`, https://www.instagram.com/reel/DVtgbY8Av6A/, 10 Mar 2026. 272,175 views, 20.0 shares/1k,
  57.3 saves/1k, 16.34 times the author's median of 16,656, z 3.61, 25.2 s. Transcript 84 words, frames and contact sheet on disk.
- **Device** Every instruction is named by the job it does, not by the model and not by the wording: "my customer support skill", "my
  researcher skill". A file is an object you can keep; a clever prompt is not.
- **Why it is the reference** 57.3 saves per 1,000 on a 25 second reel with no demonstration at all: the naming alone does the saving, which
  is the cheapest device for us to copy honestly.
- **Gate** Multiple 16.34 inside 1.5 to 20, baseline 25 reels, transcript present, frames present, topic useful to a leader who writes the
  same instructions every week. PASS. The reel is a list of fifteen and ends on a trade for a comment; we take the naming and refuse both.
- **Hook** We stopped writing prompts. We write one file for each job.
- **Problem** The person who answers customer email. Turning an inbound message into a quote request happens three or four times a day, and
  each time somebody retypes the instructions from memory and gets a different shape of answer, with a different fact missing.
- **Solution** One instruction file per job. Ours holds the five facts a quote request needs, the sentence "ask, do not guess" for anything
  absent, and the words we never put in a customer reply. Michael reads the five facts against the original message before it reaches the
  estimator.
- **Tool** The chat assistant we already pay for. The file is plain text. No new purchase.
- **CTA** Take the instruction you retyped three times last week and save it as one file named after the job.
- **Why now** On 3 September the niche started arguing about instruction files as objects, after a security scan of them was published
  (`Dc1oIn8CyDW`, topic 07). The file is the unit of the week.
- **Utility** Our one-page instruction file for a quote request, with the five facts, as a file to copy.
- **Verdict** KEEP. It stays in our workflow on the condition that a person still reads the five facts, since the file makes the answer
  consistent and cannot make it true.
- **Our proof before shooting** One real message run twice on our own screen, as a typed prompt and through the file, with the missing fact
  circled in the first output, plus the file itself.
- **Cover** "One file per job / beats a new prompt"; key phrase `beats a new prompt` on an Ink plate. Visual: `39-screen-document-card` at
  2x holding the file, `15-callout-human-step` under it at a 24 px gutter. Caption word: file. Paper surface.
- **Risk** 1 Yes, turning an inbound message into a quote request, daily. 2 Yes, the instruction is retyped from memory. 3 Yes, the file
  drafts and a person checks the facts. 4 Yes, save one file. Brand rule: this is close to a prompt tips piece, so the framing stays on the
  job and the file, never on clever wording.

## 02. A free repo built our weekly one-pager

- **Type / format** Intro by reference. M2 Radar. Educational: a repository that builds a deliverable.
- **Reference** `@liamjohnston.ai`, `DczDlj4qQjI`, https://www.instagram.com/reel/DczDlj4qQjI/, 2 Sep 2026. 161,211 views, 23.8 shares/1k,
  57.1 saves/1k, 13.5 times the author's median of 11,944, z 4.85, 63.2 s. Transcript 233 words, contact sheet on disk at
  `runs/2026-09-07/DczDlj4qQjI.jpg`.
- **Device** A free repository presented as eleven named jobs, the setup shown as three clicks, and the approval said out loud: "nothing
  gets posted until you say yes. Every skill shows you the draft first."
- **Why it is the reference** The highest scoring reel in the gated set, and the only one that puts a human approval step inside the
  promise. That step is our positioning, to an audience that saved it 57.1 per 1,000.
- **Gate** Multiple 13.5 inside range, baseline 26, transcript present, contact sheet present, topic useful to a leader who wants a
  deliverable rather than a subscription. PASS. Honest note: our own radar proposed this reel on 7 September as card 5 and a person struck
  it out, because we had no proof to show that week. We can produce the proof now, which is why it returns.
- **Hook** A free repository wrote our weekly one-pager. We checked it after.
- **Problem** The owner of a small firm who needs the same document every week, a summary a client or a team can read. It is assembled by
  hand from four places every Monday, and it is dropped first in a busy week.
- **Solution** We install one repository that produces that document, run it on our own week, and show the document it returned next to the
  one we would have written. Max installs and runs it, Michael reads the output and marks every line the document cannot support.
- **Tool** Named on screen at shoot time: the exact repository we installed, with its setup time.
- **CTA** Pick the one document you rebuild by hand every week and write down its four inputs before you install anything.
- **Why now** The reel is six days old, and on 3 September the same author published the security answer to it, which is topic 07. The pair
  is live this fortnight.
- **Utility** The four-input list for a weekly document, and our own before and after pages side by side.
- **Verdict** TEST. It works where the deliverable is one we already need and its inputs are already digital. The condition is written on
  the card, with the setup time measured, not estimated.
- **Our proof before shooting** A screen recording of the install with a stopwatch, the document it produced, and the list of what it got
  wrong on our own data.
- **Cover** "A free repo built / our weekly one-pager"; key phrase `our weekly one-pager` on an Ink plate. Visual: `37-screen-browser` at 2x
  holding the produced page, `22-number-big-with-unit` beside it with the setup time in minutes. Caption word: repo. Paper surface.
- **Risk** 1 Yes, the weekly document, rebuilt by hand. 2 Yes, four inputs collected manually. 3 Yes, the repository drafts and a person
  marks the unsupported lines. 4 Yes, list four inputs. Brand rule: somebody else's demo is never our substance, so we install the thing
  ourselves and show only our own screen.

## 03. Your team turned on AI inside the inbox

- **Type / format** Intro by reference. M2 Radar. Educational: a tool walkthrough with a stake.
- **Reference** `@manthanjethwani`, `Dbi-yxNgrhG`, https://www.instagram.com/reel/Dbi-yxNgrhG/, 3 Aug 2026. 240,255 views, 58.4 shares/1k,
  58.9 saves/1k, 9.92 times the author's median of 24,222, z 2.85, 56.8 s. Transcript 156 words, frames and contact sheet on disk.
- **Device** Four numbered settings shown on the real screen, with the stake in the first sentence: "If you don't have these four settings,
  you can access any private documents or bank statements on your Gmail." The forward comes from the stake, the save from the four steps.
- **Why it is the reference** The best forwarding and the best saving reel in the entire gated set, 58.4 and 58.9 per 1,000 at once. Our own
  radar proposed it independently on 3 September as card 3, an M2 Radar at priority 2, so the topic passed our machine and our rules before
  it passed our taste.
- **Gate** Multiple 9.92 inside range, baseline 23, transcript present, frames present, topic useful to any leader whose team pastes
  customer mail into an assistant. PASS. Its claim is stated more strongly than the evidence carries, so we borrow the four-step shape and
  state our own stake in our own words.
- **Hook** Your team turned on AI in the inbox. Nobody chose what it reads.
- **Problem** The team lead of a five to fifty person company. Assistant features arrive switched on in the mail client the team already
  uses, where customer mail, contracts and invoices sit together. Nobody made a decision, so nobody can answer a customer who asks what
  happens to their data.
- **Solution** Four settings walked through on our own screen, each with the one sentence that says what it changes and who should decide
  it. Then the one line that belongs in the team rule sheet. Michael owns the rule sheet and the answer given to a customer who asks.
- **Tool** Named at shoot time: the exact mail and workspace settings pages, ours, with our own account.
- **CTA** Open the settings page of the mail client your team uses and write down which of these four is on.
- **Why now** Our own radar surfaced this reel on 3 September and it is still the strongest forwarding device in the set on 7 September,
  across two snapshots.
- **Utility** A four-line settings sheet the viewer copies, plus the sentence to give a customer who asks.
- **Conclusion** No verdict card. This piece makes no call on a tool: it ends on one line, that a setting left at its default is still a
  decision, and it is currently being made by the vendor.
- **Our proof before shooting** Our own four settings pages recorded before and after, and our own written rule sheet with the date it was
  agreed.
- **Cover** "Your team turned on / AI inside the inbox"; key phrase `AI inside the inbox` on an Ink plate. Visual: `27-checklist-row-states`
  at 2x with four rows, `50-meta-source-plate` beneath. Caption word: inbox. Paper surface.
- **Risk** 1 Yes, handling customer mail, daily. 2 Yes, features arrive on by default. 3 Yes, the setting is a human decision and stays one.
  4 Yes, open one settings page. Brand rule: no claim without evidence, so we describe what each setting does and never what it allegedly
  leaks.

## 04. The first reply is where the cost hides

- **Type / format** Intro by reference. M2 Teardowns. Workflow and economics.
- **Reference** `@sharmadhruveshh`, `DcvqwODzjpe`, https://www.instagram.com/reel/DcvqwODzjpe/, 1 Sep 2026. 5,955 views, 18.0 shares/1k,
  25.9 saves/1k, 4.33 times the author's median of 1,374, z 3.22, 61.7 s. Transcript 198 words, contact sheet on disk at
  `runs/2026-09-07/DcvqwODzjpe.jpg`.
- **Device** Play the work first, price it second. The reel opens on the recorded call itself, a lead qualified and a visit booked, then
  turns to the per minute price and compares three. The proof is the recording, the reason to save is the arithmetic.
- **Why it is the reference** It is the only reel in the gated set that attaches a per unit price to a process step instead of a monthly
  subscription. Small base, 5,955 views, so it is read as a device and not as a reach case.
- **Gate** Multiple 4.33 inside range, baseline 26, transcript present, contact sheet present, topic useful to any firm that answers inbound
  enquiries. PASS on all four arms, with the small absolute audience stated.
- **Hook** A first reply costs money in four places. Most quotes name one.
- **Problem** The owner of a services firm who answers enquiries personally. The first reply is late because it waits for a person, and the
  price of fixing that is quoted as one subscription line, while the real bill is the tool, the minutes it runs, the review it needs, and
  the enquiry it answers wrongly.
- **Solution** The map on screen, CURRENT, AI LAYER, VERDICT. Collecting facts and drafting the reply go to the model. The send stays with a
  person, because a wrong first reply reaches a stranger under the company name. Each fragment carries a cost line, and the two we have not
  measured are labeled to measure.
- **Tool** None on screen. One page, four columns, and our own spend log for the per unit figures we hold.
- **CTA** Take your last ten enquiries, mark the step that made the reply late, and write what one wrong reply would have cost you.
- **Why now** Our first fully automatic run on 7 September gave us a real per unit price for a workflow of our own, 106 accounts at two
  dollars twelve, so we can show priced fragments instead of describing them.
- **Utility** The four-column fragmentation sheet with a cost line per fragment, as a page.
- **Verdict** Verdict Card: KEEP the fact collection fragment, TEST the drafting fragment, KILL the automatic send. The condition on TEST is
  the number of drafts that were sendable without an edit, from topic 06.
- **Our proof before shooting** Our fragmentation sheet for the first reply, photographed with the AI boundary drawn by hand, and our spend
  rows: 623 units at twelve dollars forty six, 106 at two dollars twelve.
- **Cover** "The first reply is / where the cost hides"; key phrase `where the cost hides` on an Ink plate. Visual: `28-step-chain-3` at 2x
  with the third box marked, `43-human-review-plate` under it. Caption word: reply. Paper surface.
- **Risk** 1 Yes, answering inbound enquiries, daily. 2 Yes, the reply waits for a person. 3 Yes, the send is human owned and named. 4 Yes,
  mark one step in ten enquiries. Brand rule: no cost saving claim without a published baseline, so the two unmeasured lines stay visibly
  empty and labeled to measure.

## 05. You looked for help and found a pitch

- **Type / format** Intro, new scenario. M2 Teardowns. Positioning.
- **Reference** None by design. Derived from `topics.csv` and `top-reels.csv`: "AI in a specific business process" has 29 scored reels,
  median score 0.473 and zero of the top 100, against 80 reels and 5 for "AI agency as a business" and 117 and 9 for "Design and websites
  via AI". Three reels from one agency account hold six of the top 15 rows by score.
- **Device** Ours. Name the search, show what the search returns, then show what was needed instead. The gap is measured, not asserted.
- **Gate** Not applicable: no reference reel is used. The numbers behind it come from the two CSVs and are reproducible with the query in
  `radar-data.md` section 8.
- **Hook** You looked for AI help with one process. You found somebody selling an agency.
- **Problem** The operations lead of a small firm searches for how AI fits one repeated process. The feed answers with income offers and
  agency funnels, so they leave without a decision and the process keeps its hours.
- **Solution** We do what the search does not. One repeated workflow on the table, broken into fragments with input, output, decision and
  risk, the line drawn where the model stops, the approver named. Michael owns the sheet, Max builds only the fragments that survive it.
- **Tool** None. One page, four columns.
- **CTA** Take the workflow you ran three times last week and fill four columns: input, output, decision, risk.
- **Why now** The 7 September snapshot is the first scored across 106 accounts and it confirms the hole: zero of the top 100 reels sit in
  our own topic. This is the week to plant the flag.
- **Utility** The fragmentation sheet as a page, with our radar workflow filled in as the worked example.
- **Conclusion** No verdict card. The piece makes no call on a tool, so it closes on one line: the first decision is not which tool, it is
  which workflow, and that decision belongs to a person with a name.
- **Our proof before shooting** Our own fragmentation sheet for the radar, photographed, with the AI boundary drawn on the page by hand,
  plus the two topic rows on screen from `topics.csv`.
- **Cover** "You looked for help / and found a pitch"; key phrase `and found a pitch` on an Ink plate. Visual: `39-screen-document-card` at
  2x standing for the sheet, `43-human-review-plate` under it. Caption word: process. Paper surface.
- **Risk** 1 Yes, the viewer's own first repeated workflow. 2 Yes, the search returns pitches. 3 Yes, the boundary is drawn on the page and
  the approver named. 4 Yes, four columns to fill. Brand rule: this criticizes a neighboring niche, so we name a pattern and a measurement
  and never an account.

## 06. We drafted the reply, a person sent it

- **Type / format** Regular by reference. M2 Builds. Educational: a how-to for adding an agent to lead response. It is the Build that
  follows the Teardown in topic 04, which is the proof loop in `06-formats.md`.
- **Reference** `@divyannshisharma`, `Dcq0nmpyEUR`, https://www.instagram.com/reel/Dcq0nmpyEUR/, 30 Aug 2026. 57,579 views, 32.0 shares/1k,
  48.8 saves/1k, 3.05 times the author's median of 18,906, z 1.46, 35.7 s. Transcript 119 words, contact sheet at
  `runs/2026-09-07/Dcq0nmpyEUR.jpg`; the 1 Sep snapshot read 2.01 times median at 32.2 shares/1k.
- **Device** The chain named as steps a person can repeat, with the approval inside it: connect, find the list, enrich, build the sequence,
  "review it, approve it and launch". Six steps, 35 seconds, no demo.
- **Why it is the reference** 32.0 shares and 48.8 saves per 1,000 on a mid-size account with no giveaway of the result itself, and the
  approval step is stated as part of the method rather than as a disclaimer.
- **Gate** Multiple 3.05 inside range, baseline 24, transcript present, contact sheet present, topic useful to anyone whose leads wait for a
  reply. PASS. The reel sells an outreach outcome; we take the six step shape and put it on inbound replies, where a wrong message costs
  more.
- **Hook** We drafted the first reply to twenty real messages. A person sent them.
- **Problem** The person answering inbound messages in a small firm. The reply is late, not wrong: it waits for someone to be free. Every
  late first reply is a lead deciding somebody else answered faster.
- **Solution** Our first working version, on screen: the message arrives, the draft is written against the instruction file from topic 01,
  missing facts are listed instead of guessed, and the draft waits. Michael reads and sends. We report how many of twenty went out unedited,
  and why the others did not.
- **Tool** Named at shoot time: the assistant and the mailbox we ran it in. No new subscription.
- **CTA** Count how many hours your last ten first replies took, then set one number you want them under.
- **Why now** Our first automatic run on 7 September proved the pattern on our own tooling: the machine proposes, a person decides, and both
  halves are recorded. This applies the same shape to a reply.
- **Utility** The draft-and-hold checklist as a file, plus our own count of edited and unedited drafts.
- **Verdict** TEST, with the condition being the edit rate we measure on the twenty. If more than half need an edit, the honest label is not
  yet, and we publish that instead.
- **Our proof before shooting** The run on twenty real messages in our own inbox, timestamped, with the edit count, the time to first draft,
  and one draft that was wrong enough to show.
- **Cover** "We drafted the reply / a person sent it"; key phrase `a person sent it` on an Ink plate. Visual: `36-screen-phone-9x16` at 2x
  holding the held draft, `15-callout-human-step` under it. Caption word: drafts. Paper surface.
- **Risk** 1 Yes, replying to inbound messages, daily. 2 Yes, the reply waits for a free person. 3 Yes, the draft is machine written and the
  send is human. 4 Yes, count ten replies. Brand rule: no time saving claim without a baseline, so the before number is counted on our own
  inbox before the build is shown.

## 07. A template runs with the access you have

- **Type / format** Regular by reference. M2 Radar. Educational: a walkthrough of a check before adoption.
- **Reference** `@liamjohnston.ai`, `Dc1oIn8CyDW`, https://www.instagram.com/reel/Dc1oIn8CyDW/, 3 Sep 2026. 222,097 views, 12.9 shares/1k,
  36.8 saves/1k, 18.59 times the author's median of 11,944, z 1.97, 76.1 s. Transcript 287 words, contact sheet at
  `runs/2026-09-07/Dc1oIn8CyDW.jpg`.
- **Device** Redefine the object, then hand over a gate. "A skill is just a text file that runs with everything you have access to", then a
  free scanner returning a risk score out of 100 and a plain answer on whether to install. The score is what makes it saveable.
- **Why it is the reference** 18.59 times its author's median three days after publication, and it is the only reel in the set that pairs a
  named risk with a check the viewer can actually run.
- **Gate** Multiple 18.59 inside range, baseline 26, transcript present, contact sheet present, topic useful to any leader whose team
  installs templates. PASS. Its numbers belong to a vendor report we have not read, so we quote none of them and run the check ourselves.
- **Hook** A template is a text file that runs with your access. We scanned ours first.
- **Problem** The owner sent a link on Monday and told it is free. A template runs with whatever the person installing it can already reach:
  the client folder, the mailbox, the saved keys. Nobody owns the question of what it may touch.
- **Solution** Two steps on our own screen. Run the scanner on the repository we installed in topic 02 and read the score out loud,
  including what it cannot judge. Then the rule we now keep: a template on a work machine gets its own account and never the client folder.
  Max runs the scan, Michael signs the rule.
- **Tool** Named at shoot time: the open scanner we ran, and the repository from topic 02 as its subject.
- **CTA** List every template your team installed this month and write next to each what it can reach today.
- **Why now** The reel is five days old, the pairing with topic 02 is live this fortnight, and our own install from topic 02 is the subject,
  so the check is on our own file and not on an example.
- **Utility** The install rule as three lines, and our scan output with its score visible.
- **Verdict** KEEP. The scan stays in our workflow as a gate before install, with the condition stated: it scores patterns in a file and
  cannot judge what the file is for, which is why a person still reads it.
- **Our proof before shooting** A recorded scan of the topic 02 repository with the score on screen, and our own written install rule with
  the date.
- **Cover** "A template runs with / the access you have"; key phrase `the access you have` on an Ink plate. Visual:
  `25-percentage-with-baseline` at 2x carrying the score against the baseline, `50-meta-source-plate` beneath. Caption word: scan. Paper
  surface. If our scan flags the file, the supporter becomes `20-marker-broke-here` and stays the only accent.
- **Risk** 1 Yes, installing templates on work machines, monthly. 2 Yes, nobody owns what a template may reach. 3 Yes, the scanner scores
  and a person decides. 4 Yes, list this month's installs. Brand rule: this is close to a developer topic, so it stays on the access a file
  gets and never on the code inside it.

## 08. The tool ranked nine, a person cut four

- **Type / format** Regular by reference. M2 Builds. Workflow.
- **Reference** `@vanshh_ai`, `DX9kWTYzssE`, https://www.instagram.com/reel/DX9kWTYzssE/, 5 May 2026. 99,127 views, 41.4 shares/1k, 36.2
  saves/1k, 11.6 times the author's median of 8,546, z 3.16, 60.6 s. Transcript 221 words, frames and contact sheet on disk.
- **Device** The role board. Six agents named as jobs, researcher, competitor, script writer, hook generator, video generator, auto poster,
  each with its own instruction panel, plus a panel showing what each contributed. The screen is a management view, not a technical one.
- **Why it is the reference** 41.4 shares per 1,000, the highest forwarding rate in the gated set after the settings walkthrough, earned by
  showing a process as named jobs a manager recognizes.
- **Gate** Multiple 11.6 inside range, baseline 26, transcript present, frames present, topic useful to a leader who wants to see who does
  what. PASS. Its board has no human step anywhere; ours is the difference.
- **Hook** Our tool ranked nine ideas on Monday. A person cut four of them.
- **Problem** The team lead who automates a selection step, trusts the ranking, and publishes something the company should not have said.
  Ranking is not deciding, and the rejected options usually leave no trace.
- **Solution** The run on screen as named jobs: 1,260 reels collected, 1,255 scored, 1,156 through the entry gate, 97 taken apart frame by
  frame, nine cards proposed, four struck by a person with the rule each one failed. The tool ranks, Michael decides, and the reason is
  written next to the removal.
- **Tool** Our own radar, with the rule that scores a reel against its own author's median, not the crowd.
- **CTA** Find the step where a tool proposes and nobody records why the proposal was rejected. Record it.
- **Why now** The 7 September run is the first that proposed and struck cards with no person in the loop until the review point, so the
  record exists as of this week.
- **Utility** The nine proposals and four removals as a screenshot, plus the rule list that did the removing.
- **Verdict** TEST. The ranking stays, the selection is not automatable, and we do not try again until rejection reasons have been counted
  for four weeks.
- **Our proof before shooting** The `cards` rows for week 2026-09-07 showing nine proposals and four struck, the four reasons from the run
  write-up, and a recording of one removal being written.
- **Cover** "The tool ranked nine / a person cut four"; key phrase `a person cut four` on an Ink plate. Visual: `30-ranked-row` at 2x,
  `15-callout-human-step` pointing at the cut row. Caption word: judgment. Paper surface.
- **Risk** 1 Yes, weekly selection of what to publish or pursue. 2 Yes, rejections are never recorded. 3 Yes, the tool ranks and the person
  decides. 4 Yes, start recording rejections. Brand rule: it is our own tool, so it is told as a process the viewer also has, never as a
  tour of our tooling.

## 09. A new version landed, one step changed

- **Type / format** Regular by reference. M2 Radar. Workflow and economics.
- **Reference** `@manthanjethwani`, `Dc89JaxAhA1`, https://www.instagram.com/reel/Dc89JaxAhA1/, 6 Sep 2026. 174,151 views, 29.7 shares/1k,
  14.7 saves/1k, 6.16 times the author's median of 28,251, z 0.59, 91.6 s. Transcript 290 words. No frames on disk.
- **Device** Refuse the release frame in the first sentence, "not a special model, every month they have a new model", then show one long
  artifact chain built from a single input. The refusal buys the attention, the chain spends it.
- **Why it is the reference** The freshest strong reel in the window, two days old at the time of writing, and picked on shares, which is
  the Radar metric. Its own claim is unverifiable, which is exactly the gap we fill with a fixed task.
- **Gate** Multiple 6.16 inside range, baseline 27, transcript present, topic useful to a leader asked to switch. Frames FAIL, none on disk:
  under the frame gate it ships only if they are re-pulled while the links are alive, otherwise it drops. It is an alternate for that
  reason.
- **Hook** A new version landed. One step of our own week changed, and one did not.
- **Problem** Every release resets the team's confidence. The lead is asked whether to switch and cannot answer, because nobody ran the old
  and the new on the same task.
- **Solution** One fixed task from our own week, unchanged, run on both versions, with the one step where the output differed and the one
  where it did not. Max runs the pair, Michael reads both and writes the condition under which we would switch.
- **Tool** Named at shoot time: the exact versions we ran, both of them, with their version strings visible.
- **CTA** Keep one fixed task and one fixed input, and run it on any version you are asked to switch to before you switch.
- **Why now** The reference is dated 6 September and the argument it answers is two days old. Our Radar rule asks whether a topic survives
  three to seven days: this one does, and then it decays.
- **Utility** Our fixed-task file, so the viewer has a test to reuse at the next release.
- **Verdict** Decided by the run. TEST with a condition if one step improves, KILL if the new version costs more for the same output, and
  the honest label is not yet if nothing separates them.
- **Our proof before shooting** Both runs on our own screen, same task, same input, version strings visible, a stopwatch on each, and the
  re-pulled frames of the reference.
- **Cover** "A new version landed / one step changed"; key phrase `one step changed` on an Ink plate. Visual: `32-bar-compare-card` at 2x
  with two bars on one scale for the same task, `18-verdict-test` at 2x beside it. Caption word: version. Paper surface.
- **Risk** 1 Yes, the recurring switch decision. 2 Yes, no fixed task exists to compare on. 3 Yes, a person writes the condition. 4 Yes,
  keep one fixed task. Brand rule: model news without a work decision is on the do-not-publish list, so the piece opens on the task and
  names the version second.

## 10. Five lines tell you what your run costs

- **Type / format** Regular synthesis. M2 Radar. Workflow and economics.
- **References combined, five devices, all gate-passing** (1) `Dbi-yxNgrhG`, 3 Aug 2026, 58.4 shares/1k, 58.9 saves/1k, 9.92 times median,
  baseline 23: numbered steps with the stake on step one. (2) `DczDlj4qQjI`, 2 Sep 2026, 23.8 shares/1k, 57.1 saves/1k, 13.5 times median,
  baseline 26: named jobs plus a stated approval step. (3) `DVtgbY8Av6A`, 10 Mar 2026, 20.0 shares/1k, 57.3 saves/1k, 16.34 times median,
  baseline 25: instructions named by the job. (4) `DX9kWTYzssE`, 5 May 2026, 41.4 shares/1k, 36.2 saves/1k, 11.6 times median, baseline 26:
  a role board with a contribution panel. (5) `Dcq0nmpyEUR`, 30 Aug 2026, 32.0 shares/1k, 48.8 saves/1k, 3.05 times median, baseline 24:
  review and approve inside the chain.
- **What the five share** Each hands the viewer an object they can keep and check: a setting, a file, a named job, an approval. Not one says
  what the thing costs to keep running, and nothing in the gated set does.
- **Gate** All five pass on all four arms. Frames or contact sheets exist for all five.
- **Hook** Five lines tell you what one AI workflow costs you in a week.
- **Problem** A leader approves a workflow on the subscription price alone, then meets the setup hours, the per run charge, the review
  minutes and the price of one wrong output. The budget was wrong before run one.
- **Solution** The five-line cost sheet filled in live on our own radar: build cost twelve dollars forty six over 623 data requests, weekly
  run two dollars twelve over 106 accounts, wall clock 78 minutes, review minutes to measure, one wrong card to measure. Michael reads it
  before any workflow gets a second week.
- **Tool** The cost sheet itself, one page. No purchase.
- **CTA** Fill the five lines for the workflow you ran three times last week and stop at the line you cannot fill. That line is your next
  measurement.
- **Why now** The 7 September run is the first with a real weekly figure attached, and the niche is arguing about model prices while
  counting none of the other four lines.
- **Utility** The five-line sheet as a file, with our numbers in it and two lines honestly empty.
- **Conclusion** No verdict card. Two of the five lines are unmeasured on our own process, so the piece ends on one line: this is a method
  we are running, not a result we are claiming.
- **Our proof before shooting** The `spend` rows on screen, a stopwatch on one full review pass, and one deliberately wrong card costed in
  minutes of rework.
- **Cover** "Five lines tell you / what your run costs"; key phrase `what your run costs` on an Ink plate. Visual: `26-list-numbered-row`
  stacked at 2x with two rows visibly empty, `50-meta-source-plate` beneath. Caption word: cost. Paper surface.
- **Risk** 1 Yes, approving and renewing an AI workflow. 2 Yes, four of five cost lines are invisible at approval. 3 Yes, the sheet is read
  by a named person. 4 Yes, fill five lines. Brand rule: a cost saving claim without a published baseline is forbidden, so two lines stay
  empty on screen and are labeled to measure.

---

## Closing table

| # | Title | Type | Format | Kind | Close | Pick |
|---|---|---|---|---|---|---|
| 01 | One file per job beats a new prompt | Intro by reference | Builds | Educational | KEEP | **Yes.** Pinned introduction. The whole positioning in one file, and it needs no purchase. |
| 02 | A free repo built our weekly one-pager | Intro by reference | Radar | Educational | TEST | **Yes.** Highest scoring reference in the gated set, and our own struck card finally gets its proof. |
| 03 | Your team turned on AI inside the inbox | Intro by reference | Radar | Educational | Conclusion | **Yes.** The strongest forwarding and saving device in the data, and our radar picked it on its own. |
| 04 | The first reply is where the cost hides | Intro by reference | Teardowns | Workflow | Card | **Yes.** The Teardown that sets up 06, with priced fragments instead of adjectives. |
| 05 | You looked for help and found a pitch | Intro, new scenario | Teardowns | Workflow | Conclusion | No. The measurement is right, but it argues about the niche instead of the viewer's Monday. |
| 06 | We drafted the reply, a person sent it | Regular by reference | Builds | Educational | TEST | **Yes.** Our own measured run on twenty real messages, with the edit rate published. |
| 07 | A template runs with the access you have | Regular by reference | Radar | Educational | KEEP | No, first alternate. Pairs with 02 and is ready as soon as that install exists. |
| 08 | The tool ranked nine, a person cut four | Regular by reference | Builds | Workflow | TEST | **Yes.** Our best own-proof Build: nine proposals, four removals, all in the database. |
| 09 | A new version landed, one step changed | Regular by reference | Radar | Workflow | By the run | No, second alternate. Fails the frame gate today and decays within a week. |
| 10 | Five lines tell you what your run costs | Regular synthesis | Radar | Workflow | Conclusion | No. Strong subject, but it repeats the cost line 04 already carries this week. |

**The recommended six, in publish order.** 01 as the pinned introduction, which sits outside the weekly cadence, then a week of 02 Radar, 06
Builds, 04 Teardowns, 03 Radar, 08 Builds. That is 2 Radar, 2 Builds and 1 Teardown, alternating so no two consecutive pieces answer the
same audience question, with three introduction posts carried inside the week rather than stacked in front of it. Four of the six are
educational (01, 02, 03, 06) and two are workflow pieces (04, 08), which is the mix the scope asks for.

**What has to exist before any of the six is shot.** The instruction file and one message run twice; the repository installed with a
stopwatch and its output page; our four settings pages recorded before and after, with the written rule sheet; the fragmentation sheet for
the first reply with the AI boundary drawn by hand, plus the `spend` rows; the run on twenty real messages with the edit count; the `cards`
export for week 2026-09-07 with nine rows and four struck. Six artifacts, all ours, none borrowed.
