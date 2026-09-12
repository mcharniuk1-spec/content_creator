# Unattended analysis batch — prompt template (2026-09-12)

You are running unattended, launched by `engine/analyze_pending.py` via `claude -p` on a schedule
(server cron, no human watching this session). Your job for this single invocation is exactly one
batch file — nothing else.

1. Read `{detail_prompt}` in full. That file is the actual contract for this analysis: canonical
   vocabularies, required fields, one JSON file per reel. This prompt only tells you which batch to
   run and how to behave without a human present; the real instructions live there.
2. Read the batch file at `{batch_path}` — a JSON list of reels, in the shape `{detail_prompt}`
   describes. Process every code in it, in order. Do not skip a code and do not stop partway through
   the list.
3. For each code, write one JSON file to `{output_dir}/<code>.json`, exactly the contract named in
   `{detail_prompt}`. After writing a file, read it back and confirm it parses as JSON before moving
   to the next code; if it does not parse, rewrite it until it does.
4. Touch nothing outside `{output_dir}/`. Do not edit, delete or move any other file. Do not run any
   git command. Do not fetch a URL or re-download media — everything you need is already in the batch
   file (captions, transcript segments, frame/contact-sheet paths). Read individual frame files or the
   contact sheet with the Read tool when `{detail_prompt}` calls for it; otherwise this is read-the-
   batch, write-the-output-JSON only.
5. Stop once every code in the batch has a written, valid JSON file. Do not start another batch, do
   not look for more pending codes, and do not summarize your work back to a user — there is no one
   reading this transcript.
