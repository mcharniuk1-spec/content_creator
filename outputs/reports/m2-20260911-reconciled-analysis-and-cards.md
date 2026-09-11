# M2 Lab — reconciled analysis and ten shooting cards

**Run:** `m2-20260911-reconciled-v1`  
**Status:** `PASS_WITH_LIMITATIONS` — editorial release, not a full merged replay

## Scope and evidence boundary

This report separates the user's request from instructions embedded in supplied documents. The audit, content plan, brandbook, latest-run note, and repository docs are treated as source evidence and operating constraints; their prose is not executed as an instruction unless it agrees with the current project contract.

**Local evidence available:** 2,363 reels / 100 accounts; 844 reels in the 14-day window; 91 transcript records; 100 cut manifests. **Michael's dated handoff:** 1,535 reels / 130 accounts; 1,530 scored; 85 frame-reviewed; 619 topic labels; 138 candidates; 4 retained cards. The raw 10 September export, its hashes, and its 85 frame package are not in this workspace, so they are cited as handoff evidence, not silently joined to the local database.

## Findings

### FACT

- Within-account relative performance is the correct reference axis: a reel's multiplier against its creator median identifies unusually strong examples without rewarding only large accounts.
- A high creator median with a tight spread is a quality signal; it is not proof of causality, audience fit, or reproducible performance.
- Michael's run reports that repositories/coding were highly forwarded, and that token/cost content had 105 shares per 1,000 in the 14-day window. These are dated handoff claims pending raw export verification.
- The previous architecture had a semantic-evidence gap: transcripts and technical frames were not consistently connected to reviewed hook/problem/solution/tool/CTA fields.
- The brand method is: repeated task → process map → AI boundary → human review → first test. Audience: non-technical small-business operators.

### INTERPRETATION

Use two complementary cohorts: **quality references** (high account median, low dispersion, sustained signal) and **breakout references** (high reel-to-own-median multiplier). The first supplies repeatable editorial form; the second supplies hooks and visual devices worth testing. Neither cohort authorizes copying or claims about outcomes.

### HYPOTHESIS

M2 should win by showing ordinary work and the boundary around AI, not by repeating tool news, money promises, or abstract agent language. A 35–60 second, low-cut, proof-led format is a reasonable test because the prior handoff reports a 55-second median among top references and low cut rates.

### GAP

The true full workflow remains blocked until Michael's 10 September export is copied into a new immutable run input and joined by stable reel ID, account ID, snapshot date, transcript hash, and frame manifest hash. No new provider/API calls or paid transcription were made in this run.

## Corrected architecture

1. Freeze local corpus and Michael handoff as separate releases.
2. Join only on stable IDs; never merge by username/title alone.
3. Keep four denominators separate: collected reels, scored reels, transcript-bearing reels, and frame/scene-reviewed reels.
4. Add an extraction row per reviewed reference: `hook`, `problem`, `mechanism`, `human_boundary`, `CTA`, timecodes, transcript hash, frame/scene IDs, reviewer, and parent receipt.
5. Rank references with two labels: `repeatable_quality` and `breakout_example`.
6. Every card carries claim state (`OBSERVED`, `PLANNED`, `TO_MEASURE`, `MISSING`), rights state, proof requirement, and independent review state.
7. A script is original synthesis. Reference metrics and structure may inform it; wording, identity, music, imagery, and distinctive shot order do not transfer.

## Ten cards

Each card is a candidate for review and shooting approval. Text is original M2 copy; demos are planned unless explicitly marked observed.

### 01 — Radar · The spreadsheet nobody owns

**Reference function:** browser/form automation; latest handoff Card 01. **Signal:** breakout example, 9.1× own median (handoff).  
**Hook options:** “Somebody retypes the same numbers from a PDF every week.” / “The dangerous part of browser automation is not the clicking.” / “Let AI fill the form. Do not let it press submit.”  
**Selected hook:** Somebody retypes the same numbers from a PDF every week.

**Script:** Somebody retypes the same numbers from a PDF every week. The process is simple: a document arrives, someone finds the fields, then types them into a form or spreadsheet. The bad part is not the time. It is the wrong digit you discover downstream. AI can read the document and prepare a filled-in draft. It should not be the one that submits it. Put the original beside the draft. The person who owns the data checks every field, then clicks submit. Start with one low-risk form and five examples. If the check is slower than typing, you have learned something useful.

**Frames:** 0–3s face + subtitle; 3–10s fictional PDF and empty form; 10–22s split-screen draft/original; 22–35s red “submit” boundary; 35–48s human check; 48–55s five-example test card. **Proof:** planned synthetic fixture, not live automation. **CTA:** test one low-risk form.

### 02 — Radar · The shared inbox has a queue owner

**Reference function:** intake/routing; latest handoff Card 02. **Signal:** 1.9× own median, 40 sends and 62 saves per 1,000 (handoff).  
**Hook:** Every morning someone decides who each email belongs to.

**Script:** Every morning someone decides who each email belongs to. A request arrives, a person reads it, pulls out the important details, and sends it to the right owner. AI can suggest a category and extract the fields. The original message stays next to the suggestion. A queue owner confirms it, and nothing sensitive goes back to a customer on a machine decision alone. Do not start with legal, insurance, or recruitment. Start with an inbox where a wrong route is annoying, not expensive. Review ten suggestions. Count the misses. Then decide whether the draft saved any work.

**Frames:** inbox trigger; extraction overlay; category proposal; human confirmation; “sensitive/unclear → person”; ten-row test sheet. **Proof:** planned synthetic inbox. **CTA:** review ten low-risk messages.

### 03 — Builds · Your company is not in the model

**Reference function:** explain unfamiliar concept through a practical problem; latest handoff Card 03. **Signal:** 14.4× own median (handoff).  
**Hook:** AI knows a lot. It does not know how your company answers this question.

**Script:** AI knows a lot. It does not know how your company answers this question. The process is already happening: someone asks where the form is, which supplier you use, or what happens next. One experienced person becomes the company search engine. AI can search the documents you give it and draft an answer with the source beside it. But somebody still owns the documents. If the handbook is old, the answer can be confidently wrong. Write down five questions your team answered twice this month. Give the system only the documents those answers should come from. Check every draft. That is the build.

**Frames:** repeated question; folder of fictional docs; answer with source; outdated-doc warning; five-question test. **Proof:** planned build; no live result claimed. **CTA:** list five repeated questions.

### 04 — Teardown · A list is not a workflow

**Reference function:** tool-list teardown; latest handoff Card 04. **Signal:** 3.6× own median, 57 saves per 1,000 (handoff).  
**Hook:** Ten AI add-ons do not fix a brand rule that nobody wrote down.

**Script:** Ten AI add-ons do not fix a brand rule that nobody wrote down. In a small company, every post, proposal, and customer reply passes through one person who makes it sound right. AI can compare a draft against written rules and mark what breaks them. It cannot invent the judgement behind a difficult customer conversation. The real work is writing the rules: words we use, words we avoid, and promises we never make. Put those rules beside one draft. Let AI flag. Let a person decide. If the rule is only in someone's head, there is nothing reliable to automate.

**Frames:** messy draft; rules sheet; highlight pass; ambiguous sentence sent to human; one-draft test. **Proof:** M2 rules may be shown only if owner-approved; otherwise fictional. **CTA:** write ten brand rules.

### 05 — Radar · Stop asking “what tool?”

**Reference function:** tool-news reframed as workflow; plan topic 05. **Hook:** The fastest way to waste a week is to start with a tool.

**Script:** The fastest way to waste a week is to start with a tool. Start with the repeated task: what arrives, who reads it, what decision happens, and where it gets handed off. Then ask what AI could draft. The last question is what must stay with a person. If you cannot draw the process on one page, you are not choosing software yet. You are choosing a demo. Take one task that happens every day. Map five steps. Circle the step that is boring and reversible. That is your first test.

**Frames:** tool carousel blurred; process map; AI boundary; human boundary; one-page test. **Proof:** original diagram. **CTA:** map one daily task.

### 06 — Builds · Draft, recommend, or send?

**Reference function:** agency ladder translated for operators. **Hook:** Should AI write the reply, suggest the reply, or send it?

**Script:** Should AI write the reply, suggest the reply, or send it? Those are three different jobs. Draft means a person starts with a proposed answer. Recommend means the system points to an option and shows why. Send means the system acts for you. Start at draft. Put the incoming message, the source information, and the draft on one screen. A person checks the facts, tone, and promise. Only after repeated checks pass should you test a reversible recommendation. Sending is a separate decision, not the next checkbox.

**Frames:** three-column ladder; draft; source beside answer; approval; reversible vs irreversible actions. **Proof:** planned synthetic customer enquiry. **CTA:** start at draft.

### 07 — Radar · The first reply hides the cost

**Reference function:** response workflow; plan topic 04. **Hook:** The cost of an enquiry is often hidden in the first reply.

**Script:** The cost of an enquiry is often hidden in the first reply. Someone reads the message, searches for the right information, writes an answer, and waits for approval. When the source is unclear, the reply gets rewritten twice. AI can find the relevant internal note and prepare a draft. The owner still decides what the company is promising. Test ten anonymised enquiries. Record draft time, edits, and exceptions. Do not call that savings yet. It is a small measurement that tells you whether the workflow is worth improving.

**Frames:** enquiry; search; draft; edits; measurement sheet. **Proof:** planned synthetic set. **CTA:** run ten anonymised examples.

### 08 — Teardown · The failure column

**Reference function:** evaluation translated into a buying checklist; plan topic 10. **Hook:** Every AI shortlist needs one column vendors hate: where does it fail?

**Script:** Every AI shortlist needs one column vendors hate: where does it fail? Write the task in plain language. Put ten real-looking but anonymised examples beside it. For each tool, mark what it gets wrong, what a person has to fix, and whether the mistake can be reversed. A passing demo is not permission to hand over the workflow. Your first decision is not build or buy. It is whether the failure is visible, owned, and cheap enough to learn from.

**Frames:** shortlist; failure column; ten examples; human correction; reversible/irreversible labels. **Proof:** original comparison sheet. **CTA:** add the failure column.

### 09 — Builds · The price of the run

**Reference function:** token/cost topic from Michael handoff; pending raw verification. **Hook:** “Cheap” AI is meaningless until you count the whole run.

**Script:** “Cheap” AI is meaningless until you count the whole run. Count the input, the retries, the review, the correction, and the step where a person still has to act. A model can be inexpensive and the workflow can still be slow. Write five lines for one repeated task: what came in, what the system did, what broke, what the person fixed, and what it cost to run. Do this before you compare subscriptions. The number is not a promise. It is a decision aid.

**Frames:** five-line ledger; input; retry; review; cost total. **Proof:** planned local fixture; no vendor price claim. **CTA:** keep one five-line run log.

### 10 — Teardown · The human queue is the product

**Reference function:** human-review queue; audit priority. **Hook:** If your AI has no human queue, it has no safe stopping point.

**Script:** If your AI has no human queue, it has no safe stopping point. Send unclear, sensitive, expensive, or irreversible cases to a person. Show the original input, the proposed answer, and the reason it was held. The person can approve, edit, or reject it. That queue is not failure. It is where the business keeps ownership while it learns. Start with one rule: anything that changes a price, promise, or customer record waits for review. Count the cases. Improve the rule from what you see.

**Frames:** routing rule; held case; original/proposal; approve/edit/reject; queue count. **Proof:** planned synthetic workflow. **CTA:** define one hold rule.

## Review and release state

All ten cards are `SCRIPT_CANDIDATE`, `INDEPENDENT_REVIEW_PENDING`, and `OWNER_CARD_APPROVAL_PENDING`. None is a production claim, live result, or publishing authorization. Required next evidence: immutable Michael export, transcript/frame joins, source/rights ledger, independent script review, owner-selected CTA/destination, and any real demo fixture.

## Execution receipt

- Inputs read: audit, content plan, brandbook reference, latest-run handoff, current architecture, role/scriptwriter contract, local M2Radar data.
- External collection/transcription/generation: not run.
- Local dataset replay: not run because Michael's newer raw export is absent and the available local fork is a historical 100-account release.
- Output: this report and ten original cards; PDF generated from this Markdown.
- Remaining blocker: obtain the 10 September raw export and frame/transcript manifests, then start a new immutable replay run.
