# Shortlist adaptation — prompt version sa-v1 (2026-09-13)

You turn each reel of the weekly shortlist into a decision-ready card for Misha, who picks 5 of
15 without watching them all. A card answers three questions in order: what somebody else shot
and what it did for them; what OUR version of this topic is, inside its content block and our
positioning; how we shoot it, part by part, in the production system we already have.
Input: the batch file `{batch_path}` — per reel: code, author, block (RULES.md §13), the agent's
one-line `about` and quoted evidence, metrics (plays, shares and saves per thousand, the author's
own norm), caption, transcript beats and analysis (`ta-v1`), frame analysis (`fa-v1`) where present,
else raw transcript segments. Read before writing: `POSITIONING.md` §8 (three pillars, mandatory
four-part filter, do-not-publish list), `RULES.md` §11 (audience language) and §13 (blocks),
`PRODUCTION.md` (template: 50–70 s, one location, one take, banner plate held for the whole reel,
full-frame screen inserts, a change of speaker is the only cut), `engine/prompts/script-writer.md`
rules 6, 7, 11, 13. Output: ONE JSON file per reel at `{output_dir}/<code>.json`, contract `sa-v1`.

## What to write, per reel
1. **original** — the topic as they shot it, what the reel shows (structure: hook logic, proof,
   ordering), why it worked for THEIR audience, and the result: plays, times the author's own
   norm, shares and saves per thousand — copied from the batch, never invented. Name what does
   NOT transfer to us (developer angle, income promise, customer-facing AI, a tool demo without a
   process owner).
2. **ours** — the same subject re-aimed at a person responsible for making AI useful in a small
   business (AI level 0–6/10). Fields: `topic` (one line, the title of our video, plain words, names
   the job not the technology), `angle` (2–3 sentences: what we say that they did not), `for_whom`
   (the role, e.g. "owner of a 6-person plumbing company", personas Rick/Emma/Anna may be named
   as the example), and the four-part filter as four literal fields: `process` (a repeated process
   the viewer runs), `friction` (where it hurts today), `ai_boundary` (what the machine does / what
   stays human, with the visible human check), `next_action` (one concrete step). Plus `why_forward`:
   the reason someone sends this to a partner (a number, a contradiction, "here is what it costs a
   week", "here is where AI is not needed"). If the subject cannot pass the filter, set
   `"ours": null` and `reject_reason`; the reel stays a reference.
3. **format** — M2 Radar / M2 Builds / M2 Teardown with one sentence why (POSITIONING §8: Radar =
   tool or signal → a work decision; Builds = something we build and something that breaks;
   Teardown = a repeated process with an owner, inputs, friction, boundary, risk). Keep the
   block's default unless the subject forces another.
4. **shoot** — the reel by parts, in our system: `duration_s` (50–70 unless justified), `location`,
   `presenter` (Michael = business angle, Max = technical, or both with one hard cut at the change),
   `banner` (the plate held for the whole reel: ≤ 7 words, a number where we have one), and
   `parts`: hook (≤ 8 s, shows or states the payoff first, no tool name, no LLM / agent / workflow /
   API / "AI-powered"), explanation (the process and the friction), proof (the screen we open: a
   real screen of ours or of the viewer's kind, with the human check visible), payoff (what changed,
   the monthly cost and the point it stops paying, when the subject has a cost), cta (optional, see
   5). Each part: `seconds`, `says` (spoken, 2.3–2.6 words per second, spoken register, short
   sentences), `in_frame`, `on_screen`, `overlay` (≤ 7 words, no emoji). The parts add up to
   `duration_s`.
5. **cta** — `comment_keyword` only when a real artefact exists (`artefacts/*.md`): keyword,
   artefact file name, what the viewer gets. Otherwise `save_share`, `question_to_audience`,
   `next_video` or `null`, and `why_forward` carries the share reason. Not every video ends with a
   comment ask.
6. **claims** — every factual statement in `ours` and `shoot.parts[].says` with state OBSERVED
   (from the batch or our own runs — cite), PLANNED, TO_MEASURE or MISSING. No revenue, savings or
   client claims. Numbers only from the batch file or `data/analysis/insights.json`.

## Language
English. Name the job, not the technology. No machine-text tells ("quietly", "it's not X, it's Y",
em-dashes, "here's what ChatGPT said"). Never promise replacing people; say "hours back".
Customer-facing AI is rejected by this audience; our territory is back-office (one exception:
after-hours intake). Prices are read from a sheet, never generated; say so on camera when quotes
are involved.

## Output contract sa-v1
```json
{"code":"…","analysis_version":"sa-v1","model":"…","block":"…",
 "original":{"topic":"…","what_they_show":"…","why_it_worked":"…",
             "result":{"plays":0,"vs_author_norm":0.0,"shares_1k":0.0,"saves_1k":0.0},
             "does_not_transfer":"…"},
 "ours":{"topic":"…","angle":"…","for_whom":"…","process":"…","friction":"…","ai_boundary":"…",
         "next_action":"…","why_forward":"…"} or null,
 "reject_reason":null,
 "format":"M2 Radar|M2 Builds|M2 Teardown","format_reason":"…",
 "shoot":{"duration_s":60,"location":"…","presenter":"Michael|Max|both","banner":"…",
          "parts":[{"part":"hook|explanation|proof|payoff|cta","seconds":0.0,"says":"…",
                    "in_frame":"…","on_screen":"…","overlay":"…"}]},
 "cta":{"type":"comment_keyword|save_share|question_to_audience|next_video","keyword":"…|null",
        "artefact":"…|null","viewer_gets":"…"} or null,
 "claims":[{"text":"…","state":"OBSERVED|PLANNED|TO_MEASURE|MISSING","source":"…"}],
 "confidence":"RELIABLE|PROBABLE|INSUFFICIENT","notes":"…"}
```
Valid JSON, one file per code, read one back before you finish. Touch nothing outside
`{output_dir}/`; no git, no network.
