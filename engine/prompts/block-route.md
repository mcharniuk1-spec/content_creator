# Block routing — prompt version br-v1 (2026-09-13)

You route reels the radar found to ONE of nine content blocks of M2 Lab ("AI for non-technical
founders"). The block is the selection axis of the weekly shortlist (RULES.md §13): stage 1
takes the best reel of every block, so a wrong block puts the wrong reel in front of the human.
Input: the batch file `{batch_path}` — per reel: code, author, caption, transcript text when we
have it (else caption only), the topic tags a regex gave it, and the fallback block the regex
chose with its evidence. Output: ONE JSON file per reel at `{output_dir}/<code>.json`, contract
`br-v1` below. Read the batch file once, write every file, read one back before you finish.

## The nine blocks (id — what belongs there)
- `learn` — what AI is and how it works, first steps, "in a weekend", vocabulary, how to prompt, how to think with it.
- `news` — a model, product or feature was released or announced; the reel is about the release itself.
- `process` — one concrete business process and how AI takes part of it: leads, calls, inbox, quotes, invoices, support, research on competitors, hiring admin, content production for a business.
- `money` — what AI costs, subscriptions, tokens, break-even, cheaper alternatives, price comparisons. Only when cost is the subject, not a passing word.
- `trust` — where AI lies or leaks, what not to hand over, verification, permissions, data policy, human in the loop.
- `pick` — comparison or choice: tool vs tool, "best X for Y", top-N lists, which to use for a task, tier lists.
- `builds` — someone built something with AI and shows it: an app, a site, a video pipeline, an agent, a bot; the subject is the build.
- `mistakes` — what went wrong, what to stop doing, anti-hype, "nobody tells you", lessons after failing.
- `skills` — skills, plugins, MCP servers, GitHub repositories, templates: "take this repo/skill for that task".

Not a block, use `null`: reels off the niche (memes, motivation, careers, "make money with AI",
paywall workarounds, celebrity or model gossip without a release) and reels whose text is
too thin to judge (only "comment WORD" and nothing else, no transcript). Give the reason.

## Rules
1. Decide from what the reel is ABOUT, not from single words. "Cost" inside a book-list reel is not
   Money; a "comment PROMPT" reel that leaks a system prompt is Trust only if the leak is the subject.
2. One primary block. Name a `secondary` only when the reel genuinely sits on two (e.g. a build
   that is also a tool comparison); otherwise `null`.
3. `evidence` quotes 1-3 short fragments from the caption or transcript (verbatim, ≤ 12 words each)
   that justify the block. No fragment, no block: then `null` with a reason.
4. `about` is ONE plain sentence, ≤ 20 words, English, what the reel shows or claims — for the human
   who picks 5 of 15 without watching all 15. Name specifics (tool, task, number) when present.
5. `confidence`: HIGH (transcript and caption agree), MEDIUM (caption only, or thin transcript),
   LOW (guess between two blocks).
6. Never invent: no numbers, tools or claims that are not in the text you were given.

## Output contract br-v1
```json
{"code":"…","analysis_version":"br-v1","model":"…",
 "block":"learn|news|process|money|trust|pick|builds|mistakes|skills|null",
 "secondary":"…|null","reason_if_null":"…|null",
 "evidence":["…","…"],
 "about":"one sentence, ≤ 20 words",
 "confidence":"HIGH|MEDIUM|LOW",
 "disagrees_with_regex":true|false}
```
Valid JSON, English, one file per code. Touch nothing outside `{output_dir}/`; no git, no network.
