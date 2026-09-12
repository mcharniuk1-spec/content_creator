# Frame analysis — prompt version fa-v1 (2026-09-11)

You label the visual structure of Instagram reels from 9 sampled frames per reel (fixed timecodes:
0.4 / 1.2 / 2.4 / 4.0 s, then 5 evenly spaced). Inputs per reel: the contact sheet `data/frames/<code>_sheet.jpg`
(3×3 grid, reading order = frame idx 0..8; the grid order equals the `frames` list order) and the individual
frame files. Look at the sheet with the Read tool (it renders images). Open individual frames only when the
sheet is ambiguous. Output ONE JSON file per reel at `data/analysis/frames/<code>.json` — contract `fa-v1`
in `engine/SPEC.md` §5, vocabularies §4.

Rules:
1. Every code in the batch gets a file, even if the sheet is poor (then `limitations` explains).
2. Per frame (key = frame idx as string): `frame_type` (closed list), `roll` (A|B|SPLIT|SCREEN|TEXT|OTHER),
   `speaker_present`, `face_present`, `ui_present`, `text_overlay` (0/1), `overlay_text` (verbatim if legible,
   else ""), `caption_placement` (top|middle|bottom|none), `framing` (close_up|medium|wide|screen|none),
   `dominant_action` (short), `visual_density` (low|medium|high), `is_visual_hook`, `is_cta_visual`,
   `is_proof_visual` (0/1), `notes`.
3. Video-level: `first_frame_type`, `hook_visual` (what the first ~3 s show), `visual_sequence` = list of
   frame_type in order with consecutive duplicates collapsed, `transitions_observed` = list of
   {"from_idx","to_idx","kind"} where kind ∈ hard_cut_or_more | same_shot | unknown (only what is visible
   between two sampled frames — never claim a transition type you cannot see), `a_roll_share_est`,
   `b_roll_share_est`, `split_share_est`, `screen_share_est` (fractions of the 9 samples, must sum ≤ 1),
   `text_overlay_density` (fraction of samples with overlay), `caption_style` (burned captions style, or "none"),
   `background` (short), `cta_visual` (description or "none"), `proof_visuals` (list), `sync_notes`
   (how visuals relate to the caption/transcript if `has_transcript`), `limitations` (always mention that
   these are 9 fixed samples, and anything unreadable), `confidence` RELIABLE|PROBABLE|INSUFFICIENT.
4. `analysis_version`="fa-v1", `model` = your model name, `frames_version`="fixed9-v1".
5. Valid JSON only. Do not describe people's identity; describe shot grammar and on-screen content.
