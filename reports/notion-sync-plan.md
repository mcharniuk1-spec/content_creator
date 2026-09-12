# Notion Sync plan (notion-sync-plan-v1)

Generated: 2026-09-12T08:53:56Z · scope: `all` · mode: DRY (no writes made)

## Dashboard
Action: REPLACE body of Content Engine Tool page (archive old children, append new)
Body: 169 blocks total, 1 append-children call(s).

### Architecture
engine 1.0.0, commit 92e71e7a0543
```json
[
  {
    "name": "hiker",
    "kind": "social_data",
    "role": "DEFAULT",
    "state": "NOT_CONFIGURED",
    "detail": "not set (checked process env and .env)"
  },
  {
    "name": "local-faster-whisper",
    "kind": "transcription",
    "role": "DEFAULT",
    "state": "CONFIGURED",
    "detail": "local tool, no credentials required"
  },
  {
    "name": "local-ffmpeg-scenes",
    "kind": "frames",
    "role": "DEFAULT",
    "state": "CONFIGURED",
    "detail": "local tool, no credentials required"
  },
  {
    "name": "remotion",
    "kind": "render",
    "role": "DEFAULT",
    "state": "CONFIGURED",
    "detail": "/usr/local/bin/npx on PATH; Chrome binary presence not separately verified — studio/remotion, PREVIS mode"
  },
  {
    "name": "loore",
    "kind": "media",
    "role": "OPTIONAL_PROVIDER",
    "state": "DISABLED",
    "detail": "never required for the default path; set LOORE_ENABLED=1 to opt in — transcription/media fallback, never required"
  },
  {
    "name": "supabase",
    "kind": "storage",
    "role": "OPTIONAL_PROVIDER",
    "state": "NOT_CONFIGURED",
    "detail": "missing SUPABASE_URL, SUPABASE_SERVICE_KEY"
  },
  {
    "name": "cloudflare",
    "kind": "storage",
    "role": "OPTIONAL_PROVIDER",
    "state": "NOT_CONFIGURED",
    "detail": "missing CLOUDFLARE_API_TOKEN, CF_R2_BUCKET"
  },
  {
    "name": "openai",
    "kind": "image_gen",
    "role": "OPTIONAL_PROVIDER",
    "state": "NOT_CONFIGURED",
    "detail": "missing OPENAI_API_KEY"
  },
  {
    "name": "higgsfield",
    "kind": "video_gen",
    "role": "OPTIONAL_PROVIDER",
    "state": "NOT_CONFIGURED",
    "detail": "missing HIGGSFIELD_API_KEY"
  }
]
```

### Data coverage
```json
{
  "creators": 132,
  "reels_ingested": 3211,
  "reels_with_stats": 3205,
  "reels_with_transcripts": 275,
  "reels_with_frames": 297,
  "fully_analyzed": 268,
  "hiker_reels_pending_watchdog": 1312,
  "cards": 10,
  "videos_produced": 0,
  "denominators": [
    [
      "N_ingested",
      3211,
      "reel codes with Hiker metadata — the only denominator for metric-only stats"
    ],
    [
      "N_transcript",
      275,
      "codes with a transcripts row (7 of them are empty)"
    ],
    [
      "N_transcript_usable",
      268,
      "words>0 and timed segments — denominator for every language statement"
    ],
    [
      "N_frames",
      297,
      "codes with frames rows (9 fixed samples each, legacy fixed9-v1)"
    ],
    [
      "N_ready",
      268,
      "usable transcript AND frames — denominator for script+visual conclusions"
    ]
  ]
}
```

## Databases (create-if-missing under the dashboard page)

| Database | Action | Key property | Properties |
|---|---|---|---|
| Runs | CREATE (query workspace by title first) | Run ID | Counts, Data scope, Date, Git commit, Issues, Kind, Model/prompt versions, Next steps, Reports links, Run ID, Statuses |
| Insights | CREATE (query workspace by title first) | Insight ID | Confidence, Created, Implication, Insight ID, Metric, N, Statement, Supporting accounts, Supporting reels, Transcript pattern, Visual pattern |
| Hypotheses | CREATE (query workspace by title first) | Title | Evidence, References, Resulting card, Score, Status, Title |
| Cards v2 | CREATE (query workspace by title first) | Card ID | Card ID, Format, Hypothesis, JSON path, PDF page, Refs, Script, Status, Storyboard summary, Title, Total seconds, Words |
| Reels analysis | CREATE (query workspace by title first) | Code | Account, Beats summary, CTA, Code, Comments, Confidence, Cuts, Date, First frame type, Hook text, Hook type, Likes, Pain, Play, Reshares, Robust z, Saves, Scenes, Solution, Topic, URL, Used in cards, View lift, Visual sequence |
| Accounts analysis | CREATE (query workspace by title first) | Username | Consistency, Followers, High performer share, Median play, Reliability, Top reels, Username, Videos |
| Categories | CREATE (query workspace by title first) | Label | Confidence, Kind, Label, Median lift, Median save rate, Median share rate, N, N creators |
| Cards (reused) | reuse, no schema change | — | — |

## Reels analysis
Rows to upsert: 297 (cached from a previous --apply: 0)

Sample rows (first 3):
```json
[
  {
    "code": "DBKJLzavogz",
    "url": "https://instagram.com/reel/DBKJLzavogz",
    "account": "tech_with_tim",
    "date": "2024-10-15",
    "play": 62204,
    "likes": 3045,
    "comm": 24,
    "resh": 400,
    "save": null,
    "lift": 19.126799,
    "robust_z": 5.0,
    "hook_type": "bold_claim",
    "pain": "missing_skills",
    "topic": "Обучение и навыки",
    "solution": "framework_mental_model",
    "cta": "none",
    "hook_text": "The way you get good at programming is by putting in an insane amount of volume.",
    "visual_sequence": "TRANSITION>B_ROLL_CONTEXT>A_ROLL_CLOSE_UP>HOOK_VISUAL>A_ROLL_CLOSE_UP>B_ROLL_CONTEXT>A_ROLL_CLOSE_UP",
    "first_frame_type": "TRANSITION",
    "scenes_n": 7,
    "cuts": 24,
    "beats_summary": "4 beats: hook > problem > mechanism > payoff",
    "confidence": "ANALYSIS_READY",
    "used_in_cards": []
  },
  {
    "code": "DEVIE7sN_ZI",
    "url": "https://instagram.com/reel/DEVIE7sN_ZI",
    "account": "tech_with_tim",
    "date": "2025-01-02",
    "play": 135480,
    "likes": 6439,
    "comm": 20,
    "resh": 1185,
    "save": null,
    "lift": 42.83212,
    "robust_z": 5.0,
    "hook_type": "curiosity_gap",
    "pain": "dont_know_where_to_start",
    "topic": "Карьера, резюме, найм",
    "solution": "case_story",
    "cta": "none",
    "hook_text": "So the next project we're looking at is one of my all-time favorites, and this is an AI learning how to play the game of Flappy Bird.",
    "visual_sequence": "SCREEN_RECORDING>SCREENSHOT>SCREEN_RECORDING",
    "first_frame_type": "SCREEN_RECORDING",
    "scenes_n": 3,
    "cuts": 6,
    "beats_summary": "6 beats: hook > setup > mechanism > explanation > explanation > payoff",
    "confidence": "ANALYSIS_READY",
    "used_in_cards": []
  },
  {
    "code": "DK9pFUjPQcx",
    "url": "https://instagram.com/reel/DK9pFUjPQcx",
    "account": "okaashish",
    "date": "2025-06-16",
    "play": 427610,
    "likes": 14927,
    "comm": 6679,
    "resh": 18190,
    "save": 24882,
    "lift": 38.632339,
    "robust_z": 5.0,
    "hook_type": "bold_claim",
    "pain": "cost_money",
    "topic": "Бесплатный доступ и обход платы",
    "solution": "resource_handoff",
    "cta": "comment_keyword",
    "hook_text": "You don't have to pay hundreds of dollars for api keys anymore.",
    "visual_sequence": "DATA_VISUAL>SCREENSHOT>OVERLAY>SCREENSHOT>MOTION_GRAPHIC>OVERLAY>A_ROLL_CLOSE_UP",
    "first_frame_type": "DATA_VISUAL",
    "scenes_n": 7,
    "cuts": 10,
    "beats_summary": "5 beats: hook > setup > solution > rehook > cta",
    "confidence": "ANALYSIS_READY",
    "used_in_cards": []
  }
]
```

## Accounts analysis
Rows to upsert: 132 (cached from a previous --apply: 0)

Sample rows (first 3):
```json
[
  {
    "username": "askcatgpt",
    "followers": 856916,
    "n_videos": 12,
    "median_play": 483982.0,
    "consistency_score": 0.3613,
    "reliability": "HIGH_VARIANCE",
    "high_performer_share": 0.3333,
    "top_reel": "https://instagram.com/reel/DNQ7bZphUn9",
    "top_reel_score": 1.9108
  },
  {
    "username": "anshmehra.in",
    "followers": 328391,
    "n_videos": 12,
    "median_play": 312738.5,
    "consistency_score": 0.4295,
    "reliability": "HIGH_VARIANCE",
    "high_performer_share": 0.4167,
    "top_reel": "https://instagram.com/reel/Dc9GZ0Gzf6o",
    "top_reel_score": 1.4768
  },
  {
    "username": "kallaway",
    "followers": 453088,
    "n_videos": 12,
    "median_play": 216013.5,
    "consistency_score": 0.362,
    "reliability": "HIGH_VARIANCE",
    "high_performer_share": 0.4167,
    "top_reel": "https://instagram.com/reel/C_iVgDcJLd1",
    "top_reel_score": 1.9916
  }
]
```

## Cards v2
Rows to upsert: 10 (cached from a previous --apply: 0)

Sample rows (first 3):
```json
[
  {
    "card_id": "C-2026-09-12-01",
    "title": "Nineteen of our top twenty were there on a trick",
    "format": "M2 Builds",
    "status": "REVIEWED",
    "hypothesis_id": "H-11",
    "total_s": 68.4,
    "total_words": 171,
    "refs": "[{\"code\":\"DZLDk9ySi-7\",\"creator_median_play\":3421.0,\"function\":\"hook\",\"play\":179093,\"reason\":\"Puts the state of the world first and the mechanism second, so the pain lands as reward rather than as complaint. result_first hook type; result_first and demo_first together are the highest-performing hook family measured (median robust_z 2.17 against 1.21). Its view_lift of 51.35 - that is 52.4x the author's own median, since view_lift is the ratio minus one - rests on a 3 421-view median, so the multiplier is not a finding and the ordering is.\",\"save_rate\":0.04539,\"share_rate\":0.04191,\"transformed_how\":\"Borrowed the ordering only: state of the world first, mechanism second. Changed: our first frame is a real list of our own that was wrong, not an imagined good morning; we delete the second-person future-pacing entirely because setup-first openings run at median robust_z 0.67 against 1.36 (p=0.002); and we replace its invented counters with a screen recording of our own output.\",\"url\":\"https://www.instagram.com/reel/DZLDk9ySi-7/\",\"useful_frame\":{\"scene_id\":\"DZLDk9ySi-7-S00\",\"what\":\"opens with no presenter at all - a full-frame animated pipeline board whose counters climb while the voice talks over it\"},\"useful_transcript\":{\"beat_id\":\"DZLDk9ySi-7-B0\",\"quote\":\"Imagine, a client in the morning is already interested to take your service because your AI Automation Agency system is automatic\"},\"username\":\"aiforbusinesses247\",\"view_lift\":51.35},{\"code\":\"DNA7-d3o5sQ\",\"creator_median_play\":8010.0,\"function\":\"rhythm\",\"play\":451491,\"reason\":\"Carries the corpus's cleanest mid-roll re-hook: a 1.8-second beat at 32.0-33.8 s placed exactly where the mechanism stops being new and immediately before the proof. It is the only ungated reel in the pool (cta_type none), so its 36.5 saves per 1 000 carry no keyword inflation.\",\"save_rate\":0.03652,\"share_rate\":0.02334,\"transformed_how\":\"Borrowed one short re-hook before the evidence, and only one - the corpus median is a single open loop and only 15 of 264 reels carry an explicit re-hook. Changed: ours is a statement, not a question, because questions in the script correlate negatively with saves (-0.229, creator-normalised -0.162, RELIABLE), and it is delivered on the face rather than over the canvas.\",\"url\":\"https://www.instagram.com/reel/DNA7-d3o5sQ/\",\"useful_frame\":{\"scene_id\":\"DNA7-d3o5sQ-S00\",\"what\":\"one 56-second unbroken screen take of the workflow canvas, presenter reduced to a small head at the bottom of frame, so the artefact keeps the whole picture\"},\"useful_transcript\":{\"beat_id\":\"DNA7-d3o5sQ-B3\",\"quote\":\"But how about the results?\"},\"username\":\"edhillai\",\"view_lift\":55.37},{\"code\":\"DbO4zvJR1k8\",\"creator_median_play\":14448.0,\"function\":\"pain\",\"play\":209121,\"reason\":\"The highest save rate in the whole corpus (87.4 per 1 000) bought with a repeated shape: the consequence of not doing it, then the exact clause that closes it, four times without variation, over one unbroken 71-second close-up. It is how a reel about a defect stays usable rather than merely alarming.\",\"save_rate\":0.08735,\"share_rate\":0.0529,\"transformed_how\":\"Borrowed the consequence-then-fix pairing and the persistent title plate. Changed: our cost is stated as work that went the wrong way, never as damages or money, and we drop its warning_fear register after the first sentence - urgency and fear vocabulary track negatively on every metric we measured (urgency vs view_lift -0.164, p=0.007). Its legal claims are recorded in our files as unverified and are irrelevant to us.\",\"url\":\"https://www.instagram.com/reel/DbO4zvJR1k8/\",\"useful_frame\":{\"scene_id\":\"DbO4zvJR1k8-S00\",\"what\":\"single close-up held for the whole reel, one persistent title plate at the top, occasional quoted-text cards dropped in low in the frame as each item is named\"},\"useful_transcript\":{\"beat_id\":\"DbO4zvJR1k8-B2\",\"quote\":\"For example, under CCPA, California has laws that can cost you $750 per user per incident.\"},\"username\":\"shrug.manny\",\"view_lift\":13.47},{\"code\":\"DX9kWTYzssE\",\"creator_median_play\":8982.5,\"function\":\"screen_proof\",\"play\":99558,\"reason\":\"Most dashboard reels stop at 'here are my agents'; this one shows contribution per item, which is exactly the screen a re-sorted priority list needs. The proof beat runs 36.5-56.9 s over a DATA_VISUAL state and the reel is not comment-gated (cta_type dm), so its 41.3 shares per 1 000 carry no keyword inflation.\",\"save_rate\":0.03606,\"share_rate\":0.04132,\"transformed_how\":\"Borrowed showing per-item contribution on screen instead of a summary, so the viewer can watch the re-ranking happen. Changed: our screen shows the same list twice - before and after one field is made comparable - rather than a performance dashboard, and the close is not a DM. Its Hinglish ASR is heavily garbled in our files, so we take the screen idea and none of the wording.\",\"url\":\"https://www.instagram.com/reel/DX9kWTYzssE/\",\"useful_frame\":{\"scene_id\":\"DX9kWTYzssE-S02\",\"what\":\"full-frame analytics page filmed off a monitor, ending on a doughnut chart that attributes the result to each agent by share\"},\"useful_transcript\":{\"beat_id\":\"DX9kWTYzssE-B2\",\"quote\":\"And then you have performance tags here where you can see how many videos you posted, how many views generated, how much average engagement rate, how many followers gain.\"},\"username\":\"vanshh_ai\",\"view_lift\":10.08},{\"code\":\"DTCOU9DkRTG\",\"creator_median_play\":4124.0,\"function\":\"cta\",\"play\":218733,\"reason\":\"The pool's best ungated close - it converts the ask into a bounded, falsifiable test instead of a keyword, and it is the only shape in the pool that invites a reply without gating an artefact, which is the position M2 is in by rule. 29.7 shares and 42.0 saves per 1 000 with cta_type question_to_audience.\",\"save_rate\":0.04202,\"share_rate\":0.02968,\"transformed_how\":\"Borrowed an ungated close that names a bounded test the viewer can run and report back on. Changed: ours asks the viewer to check their own queue's top five and to forward the reel to the person who owns that list, delivered on the face in the last 11 % of the script - the position the whole corpus has converged on (median CTA start at 90 % of spoken length).\",\"url\":\"https://www.instagram.com/reel/DTCOU9DkRTG/\",\"useful_frame\":{\"scene_id\":\"DTCOU9DkRTG-S02\",\"what\":\"cuts back off the laptop screen to a plain close-up against a curtain for the closing line, no overlay left on the frame\"},\"useful_transcript\":{\"beat_id\":\"DTCOU9DkRTG-B4\",\"quote\":\"And if it doesn't work for you within the first five people you reach out to, you can roast my eyebrows in the comments.\"},\"username\":\"buildingwithstring.com_\",\"view_lift\":52.04}]",
    "script": "{\"emotional_effect\": \"the uneasy recognition that the list you work from every morning was never audited\", \"sections\": [{\"role\": \"hook\", \"seconds\": 8.0, \"text\": \"This is the list our system put at the top. Nineteen of the top twenty are there on a trick.\", \"words\": 20}, {\"role\": \"problem\", \"seconds\": 11.2, \"text\": \"You work from a list like this. Something decides which enquiry, which ticket, which invoice gets looked at first, and nobody has re-read the rule that sorts it.\", \"words\": 28}, {\"role\": \"explanation\", \"seconds\": 2.4, \"text\": \"Ours sorted by forwards and saves.\", \"words\": 6}, {\"role\": \"explanation\", \"seconds\": 11.6, \"text\": \"Ask people to comment a word under a post and its saves go up nearly three times, its forwards nearly double, and its reach does not move at all.\", \"words\": 29}, {\"role\": \"rehook\", \"seconds\": 4.8, \"text\": \"So we sorted the same list again, comparing only like with like.\", \"words\": 12}, {\"role\": \"proof\", \"seconds\": 12.8, \"text\": \"Eight of the top twenty are now posts that never asked for a comment. Two of them had been sixty-seventh and sixty-first. Nothing about them changed. Only what we divided by did.\", \"words\": 32}, {\"role\": \"payoff\", \"seconds\": 10.0, \"text\": \"The rule we added: record the habit on every item, and only compare items that share it. A ranking measures exactly what you feed it.\", \"words\": 25}, {\"role\": \"cta\", \"seconds\": 7.6, \"text\": \"Find what your top five have in common that is not importance. Send this to whoever owns that list.\", \"words\": 19}], \"target_wps\": 2.5, \"tone\": \"plain, self-critical, specific - a builder reporting a defect, not confessing\", \"total_s\": 68.4, \"total_words\": 171, \"version\": 1}",
    "storyboard_summary": "{\"assets_required\":[\"Screen recording of our own weekly candidate list ranked on forwards and saves per thousand plays, mid-scroll, real rows (S00)\",\"Chart of save, forward and reach with and without the comment prompt, generated from our own run (S03)\",\"Before/after screen of the same twenty rows re-sorted within cta_type, with the two travelling rows visible (S05)\",\"Michael A-roll, medium shot, one location, four takes\"],\"captions\":\"Burned-in speech captions, IBM Plex Sans SemiBold 600 at 40px",
    "json_path": "cards/C-2026-09-12-01.json",
    "pdf_page": null
  },
  {
    "card_id": "C-2026-09-12-03",
    "title": "We built it, it worked, and we switched it off",
    "format": "M2 Builds",
    "status": "REVIEWED",
    "hypothesis_id": "H-18",
    "total_s": 69.6,
    "total_words": 167,
    "refs": "[{\"code\":\"Dbs2JdJKUDd\",\"creator_median_play\":3619.0,\"function\":\"hook\",\"play\":16290,\"reason\":\"The pool's only genuinely subtractive opening: it tells the viewer to stop using something before it offers a replacement, and at 11.4 s it drops a one-line re-hook straight into the demo. robust_z 3.28 on a small 16 290-play reel, 29.8 shares and 42.6 saves per 1 000.\",\"save_rate\":0.0426,\"share_rate\":0.02983,\"transformed_how\":\"Borrowed the instruction to switch something off as the first words, and the one-line re-hook into the demo. Changed: we switch off something of our own rather than somebody else's product, and the hook shows the working step before the turn, because contrarian openings carry the lowest share and save rates of the large hook cells (0.0076 and 0.0139) and must not be the whole opening. Its Hinglish captions are heavily mis-transcribed in our files, so the structure is borrowed and never the wording.\",\"url\":\"https://www.instagram.com/reel/Dbs2JdJKUDd/\",\"useful_frame\":{\"scene_id\":\"Dbs2JdJKUDd-S00\",\"what\":\"frame one is a full-frame screen recording of the tool being abandoned, still open and still working, with the instruction to stop burned across it - no presenter until 4 s\"},\"useful_transcript\":{\"beat_id\":\"Dbs2JdJKUDd-B2\",\"quote\":\"Now look at this.\"},\"username\":\"dainikautomates\",\"view_lift\":3.5},{\"code\":\"Dc_TX1CttIc\",\"creator_median_play\":22421.0,\"function\":\"proof\",\"play\":562094,\"reason\":\"The most evidentially honest beat in the pool: it states the test conditions before the conclusion and concedes what would improve the result before drawing one. Ungated (cta_type none), 31.7 shares per 1 000, robust_z 5.0 (clipped). It is the shape a 'we measured it and it failed' beat needs in order not to sound like an excuse. save_rate is recorded as -1.0 because the source never returned a save count for this reel; it is a not-measured sentinel, not a rate.\",\"save_rate\":null,\"share_rate\":0.03167,\"transformed_how\":\"Borrowed the ordering: conditions first, concession second, conclusion third. Changed: our conclusion is that the step is being removed, which no reel in the corpus does; we state the threshold in advance so the retirement reads as a rule rather than as a mood; and the concession we make is against ourselves - part of our miss rate is our own coarse measurement, and we say so on screen.\",\"url\":\"https://www.instagram.com/reel/Dc_TX1CttIc/\",\"useful_frame\":{\"scene_id\":\"Dc_TX1CttIc-S01\",\"what\":\"cuts away from the face to a full-frame capture of the actual prompt and the actual output, so the conditions being described are legible on screen while they are spoken\"},\"useful_transcript\":{\"beat_id\":\"Dc_TX1CttIc-B5\",\"quote\":\"Every one of these was one shot. And yes, more context makes it better, but even cold it is clearly ahead of GPT 5.6 while sitting roughly level with fable 5.1.\"},\"username\":\"v.i.s.h.ai\",\"view_lift\":24.07},{\"code\":\"DMQMNNHSJRF\",\"creator_median_play\":7281.0,\"function\":\"cta\",\"play\":140763,\"reason\":\"One of the few spoken save asks in the whole corpus, and it gives the save a reason rather than a keyword. Five seconds, in the last 5 % of the script, no gate. With save_share appearing as a cta_type only twice in 266 reels, this is the closest thing to a working model for the ask M2 is allowed to make. save_rate is -1.0 for the same not-measured reason as above.\",\"save_rate\":null,\"share_rate\":0.03514,\"transformed_how\":\"Borrowed the save ask with a stated reason for saving, placed in the final seconds and returned to the face. Changed: ours names the artefact being published in the caption - the retirement checklist with its threshold and review date - so the save collects something rather than deferring the watch, and we drop the 'next video' series framing entirely, because series preambles and series closes belong to the setup-first family that runs at median robust_z 0.67 against 1.36.\",\"url\":\"https://www.instagram.com/reel/DMQMNNHSJRF/\",\"useful_frame\":{\"scene_id\":\"DMQMNNHSJRF-S03\",\"what\":\"the closing seconds return from the full-frame product page to the presenter inset, so the ask is delivered by a face and not over a screen\"},\"useful_transcript\":{\"beat_id\":\"DMQMNNHSJRF-B6\",\"quote\":\"And save this video so that you can try it later. And we will meet in the next video.\"},\"username\":\"wokecoder\",\"view_lift\":18.33},{\"code\":\"DZQZOVhgNvK\",\"creator_median_play\":24492.0,\"function\":\"a_roll\",\"play\":124032,\"reason\":\"A 40-second unbroken close-up that carries a whole build story before a single cut. It is the pool's evidence that the 'I built this' register holds on one face take - and it is exactly the register our retirement reel has to invert in its second half. 25.0 shares and 50.2 saves per 1 000, robust_z 2.18.\",\"save_rate\":0.05024,\"share_rate\":0.02501,\"transformed_how\":\"Borrowed the builder register and the confidence to hold one long face take for the reasoning half. Changed: our version ends with the build being removed rather than offered, we refuse both of its proof moves - the view-count claim and the paid-community CTA - and the inset is replaced by a full-frame screen, because split states run at median robust_z 1.03 against 1.43 (p=0.044).\",\"url\":\"https://www.instagram.com/reel/DZQZOVhgNvK/\",\"useful_frame\":{\"scene_id\":\"DZQZOVhgNvK-S00\",\"what\":\"one 40-second close-up, single-word captions punched in on the beat, a small screen inset floated above the shoulder rather than cut to full frame\"},\"useful_transcript\":{\"beat_id\":\"DZQZOVhgNvK-B0\",\"quote\":\"I just built this clawed skill that can predict exactly what you need to post in order to go viral. And yeah, it works.\"},\"username\":\"jasoncooperson\",\"view_lift\":4.06}]",
    "script": "{\"emotional_effect\": \"permission to stop maintaining something that never earned its place\", \"sections\": [{\"role\": \"hook\", \"seconds\": 7.5, \"text\": \"This step has never failed. We turned it off this week. Here is the number that decided it.\", \"words\": 18}, {\"role\": \"problem\", \"seconds\": 10.0, \"text\": \"You have one of these. A script, a mailbox rule, something set up months ago. It still runs. Nobody has asked what it changes.\", \"words\": 24}, {\"role\": \"explanation\", \"seconds\": 10.4, \"text\": \"Ours matched what is said in a video to where the picture changes. It ran on two hundred and sixty-four videos. It never crashed once.\", \"words\": 25}, {\"role\": \"proof\", \"seconds\": 6.7, \"text\": \"Out of one thousand five hundred and twenty-seven places it could have matched, it found fifty-five.\", \"words\": 16}, {\"role\": \"proof\", \"seconds\": 14.2, \"text\": \"Two hundred and fifteen videos gave it nothing at all. Some of that is our own measurement being coarse. And the videos it matched came out no different from the ones it did not.\", \"words\": 34}, {\"role\": \"payoff\", \"seconds\": 12.5, \"text\": \"So it is off. Every automation now gets two things written down the day it is built: the number that proves it is worth keeping, and the date we check.\", \"words\": 30}, {\"role\": \"cta\", \"seconds\": 8.3, \"text\": \"The checklist is in the caption. Find the one that fired least last month, then keep it or kill it.\", \"words\": 20}], \"target_wps\": 2.4, \"tone\": \"plain, unsentimental, a builder reporting a decision rather than defending it\", \"total_s\": 69.6, \"total_words\": 167, \"version\": 2}",
    "storyboard_summary": "{\"assets_required\":[\"Continuous screen capture of the alignment step running green and then being switched off (S00-S01)\",\"Capture of the step's own output showing spoken beats against picture changes (S02)\",\"Chart of 1 527 candidate boundaries with 55 lit (S03)\",\"Two-column comparison of matched vs unmatched videos on the same outcome figures (S04)\",\"Max A-roll, medium shot, one take\",\"One-page retirement checklist published in the caption, not gated\"],\"captions\":\"Burned-in speech captions, IBM",
    "json_path": "cards/C-2026-09-12-03.json",
    "pdf_page": null
  },
  {
    "card_id": "C-2026-09-12-05",
    "title": "The approval box we designed and never ticked",
    "format": "M2 Builds",
    "status": "REVIEWED",
    "hypothesis_id": "H-13",
    "total_s": 68.5,
    "total_words": 178,
    "refs": "[{\"code\":\"DbO4zvJR1k8\",\"creator_median_play\":14448.0,\"function\":\"rhythm\",\"play\":209121,\"reason\":\"A 71-second single-take close-up that never flattens, because every item has the identical shape - the consequence of not doing it, then the exact clause that fixes it. Highest save rate in the corpus (87.4 per 1 000) with no screen in it at all, which proves a control reel can hold on a face if the cadence is strict.\",\"save_rate\":0.08735,\"share_rate\":0.0529,\"transformed_how\":\"Borrowed the fixed item shape repeated without variation, and the persistent title plate. Changed: we have three items instead of four, the middle two thirds of our reel is a full-frame screen rather than a face because the empty column is the proof, and the register drops the legal-fear framing after the first line.\",\"url\":\"https://www.instagram.com/reel/DbO4zvJR1k8/\",\"useful_frame\":{\"scene_id\":\"DbO4zvJR1k8-S00\",\"what\":\"one close-up for the entire reel; a persistent two-line title plate at the top and a plain white quote card dropped in low in the frame only when a specific clause is named\"},\"useful_transcript\":{\"beat_id\":\"DbO4zvJR1k8-B1\",\"quote\":\"Number one and most important, if your terms and service doesn't cap your liability, there's no limit to how much somebody can sue you for.\"},\"username\":\"shrug.manny\",\"view_lift\":13.47},{\"code\":\"DZ-wujrTJ0u\",\"creator_median_play\":6358.0,\"function\":\"a_roll\",\"play\":334706,\"reason\":\"Second-highest save rate in the pool (64.9 per 1 000) on a 172-second reel, and it survives that length by bookending: the artefact demonstrates itself early and again at the very end, with the instructions in between. Ungated (cta_type follow). Its 57-second opening close-up is the longest single face take in the pool that still works.\",\"save_rate\":0.06491,\"share_rate\":0.01968,\"transformed_how\":\"Borrowed the reward bookend - something concrete at the start and again at the close, so a long middle is tolerable - and the confidence to hold one face take. Changed: our bookend is the same column shown empty and then shown blocked, not a product demo; we drop the countdown device; and the reel's own conversion target is the creator's product behind a follow-only CTA, which we do not reproduce.\",\"url\":\"https://www.instagram.com/reel/DZ-wujrTJ0u/\",\"useful_frame\":{\"scene_id\":\"DZ-wujrTJ0u-S00\",\"what\":\"57 seconds of one close-up with a black title plate above the head and a live countdown ring in the corner, so a long take still reads as going somewhere\"},\"useful_transcript\":{\"beat_id\":\"DZ-wujrTJ0u-B0\",\"quote\":\"I'm going to show you how you can build your very own AI drivers in under three minutes so you can get something like I have here with Trillian.\"},\"username\":\"kevinfremon\",\"view_lift\":51.64},{\"code\":\"DVaBP3wDAFE\",\"creator_median_play\":7471.0,\"function\":\"screen_proof\",\"play\":533528,\"reason\":\"Holds one unbroken UI_DEMO state from 0.4 s to 60.3 s - two thirds of the reel - and narrates over it continuously before cutting to the face. It is the pool's proof that a long unbroken screen take with live narration holds attention without a single cut, which is exactly what showing one empty column demands. robust_z 5.0 (clipped).\",\"save_rate\":0.03835,\"share_rate\":0.02243,\"transformed_how\":\"Borrowed the unbroken screen take with live narration and the single late cut to the face. Changed: the narration is an admission rather than a boast, the screen shows a control that did not run instead of a dashboard that does, we capture the screen cleanly rather than filming a monitor, and the reel's final third - explicit fear pressure and profanity, flagged as such in our own analysis - is replaced by the redesign.\",\"url\":\"https://www.instagram.com/reel/DVaBP3wDAFE/\",\"useful_frame\":{\"scene_id\":\"DVaBP3wDAFE-S00\",\"what\":\"the screen is filmed off a monitor across the room rather than captured, held unbroken for 60 seconds, with a small persistent badge top-left and sentence captions along the bottom\"},\"useful_transcript\":{\"beat_id\":\"DVaBP3wDAFE-B2\",\"quote\":\"If I have an idea I just drop it in here It's going to go in my pipeline automatically and here I can see the difference in terms of engagement.\"},\"username\":\"tenfoldmarc\",\"view_lift\":70.41},{\"code\":\"DczDlj4qQjI\",\"creator_median_play\":13448.5,\"function\":\"cta\",\"play\":173629,\"reason\":\"Its close carries two asks and only the second is usable: the share-with-a-peer half is the pure form of the question RULES.md §4 makes us answer first - who exactly will forward this, and to whom - and it is why the reel carries 23.6 shares per 1 000 with an explicit share ask at the end.\",\"save_rate\":0.05664,\"share_rate\":0.02361,\"transformed_how\":\"Borrowed the forward-to-a-named-role close, specified by role rather than 'send this to a friend'. Changed: the comment gate half is deleted, not softened - the gate moves save rate 2.8x and share rate 1.8x and reach not at all, so dropping it costs no distribution and removes the inflation from our own future numbers - and the role we name is the person who signs off, not a generic contact.\",\"url\":\"https://www.instagram.com/reel/DczDlj4qQjI/\",\"useful_frame\":{\"scene_id\":\"DczDlj4qQjI-S03\",\"what\":\"returns from the full-frame product screenshots to a plain seated close-up for the closing line, captions in a dark box at the seam\"},\"useful_transcript\":{\"beat_id\":\"DczDlj4qQjI-B5\",\"quote\":\"Just comment Claude and I'll send you the full repo and setup and send this to someone you know who needs to post on LinkedIn more.\"},\"username\":\"liamjohnston.ai\",\"view_lift\":11.91}]",
    "script": "{\"emotional_effect\": \"the urge to go and check your own sign-off step before anyone asks about it\", \"sections\": [{\"role\": \"hook\", \"seconds\": 7.3, \"text\": \"We wrote a mandatory check into our own process on the first of September. Here is the box. Empty.\", \"words\": 19}, {\"role\": \"problem\", \"seconds\": 10.0, \"text\": \"You have one too. Somewhere in your process a document says a person checks this before it goes out. Now find where that check is recorded.\", \"words\": 26}, {\"role\": \"explanation\", \"seconds\": 10.4, \"text\": \"Ours is a single column. It has been there since the rule was written. It is filled in on four rows out of two hundred and eighty-two.\", \"words\": 27}, {\"role\": \"proof\", \"seconds\": 11.5, \"text\": \"All four were filled on the same day, the day we wrote the rule. Every card we have drafted since has a row waiting and the box behind it empty.\", \"words\": 30}, {\"role\": \"proof\", \"seconds\": 10.4, \"text\": \"Three items on this week's shortlist should have failed that check. We caught them by reading. One of the three is in the record. Two are not.\", \"words\": 27}, {\"role\": \"payoff\", \"seconds\": 11.2, \"text\": \"A check nothing stops for is a preference. Three ways out: make the step block, put it where someone already looks, or delete the rule. We took the first.\", \"words\": 29}, {\"role\": \"cta\", \"seconds\": 7.7, \"text\": \"Open where your process says the check is recorded and count the last fifty. Send this to whoever signs off.\", \"words\": 20}], \"target_wps\": 2.6, \"tone\": \"plain, uncomfortable, and specific - the tone of a post-mortem, not an apology\", \"total_s\": 68.5, \"total_words\": 178, \"version\": 2}",
    "storyboard_summary": "{\"assets_required\":[\"Screen capture of the suitability column scrolled to the newest rows, every cell blank (S01)\",\"The same take pulling back to the rule as written in our own process document, with the requiring sentence highlighted (S02)\",\"Continuous screen capture of the table with the suitability column scrolling, blank (S03-S04)\",\"The four filled rows showing the same date (S04)\",\"Three-row comparison of this week's content rejections, one recorded and two not (S05)\",\"Michael A-roll, close",
    "json_path": "cards/C-2026-09-12-05.json",
    "pdf_page": null
  }
]
```

## Runs
Rows to upsert: 7 (cached from a previous --apply: 0)

Sample rows (first 3):
```json
[
  {
    "run_id": "2026-09-12_0853-138ee2",
    "started_at": "2026-09-12T08:53:24Z",
    "finished_at": "2026-09-12T08:53:28Z",
    "kind": "cards",
    "git_commit": "92e71e7a0543",
    "host": "MacBook-Air-Mihail.local",
    "config_json": "{\"cards\":[\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-01.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-02.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-03.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-04.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-05.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-06.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-07.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-08.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-09.json\",\"/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/C-2026-09-12-10.json\"]}",
    "summary_json": "{\"failed\":[],\"ok\":[\"C-2026-09-12-01\",\"C-2026-09-12-02\",\"C-2026-09-12-03\",\"C-2026-09-12-04\",\"C-2026-09-12-05\",\"C-2026-09-12-06\",\"C-2026-09-12-07\",\"C-2026-09-12-08\",\"C-2026-09-12-09\",\"C-2026-09-12-10\"]}",
    "status": "DONE",
    "summary": {
      "run_id": "2026-09-12_0853-138ee2",
      "stages": {
        "CARD_GENERATION": {
          "DONE": 10
        },
        "FRAME_GENERATION": {
          "DONE": 10
        },
        "FRAME_PLAN": {
          "DONE": 10
        },
        "SCRIPT_GENERATION": {
          "DONE": 10
        },
        "SCRIPT_REVIEW": {
          "DONE": 10
        },
        "VIDEO_GENERATION_READY": {
          "DONE": 10
        }
      },
      "totals": {
        "DONE": 60
      },
      "jobs": 60,
      "duration_s": 3.98
    },
    "date": "2026-09-12",
    "model_prompt_versions": "",
    "data_scope": "",
    "counts": "{\"DONE\": 60}",
    "statuses": "DONE",
    "issues": "",
    "reports_links": "",
    "next_steps": ""
  },
  {
    "run_id": "2026-09-12_0844-1baa1c",
    "started_at": "2026-09-12T08:44:17Z",
    "finished_at": "2026-09-12T08:44:18Z",
    "kind": "cards",
    "git_commit": "92e71e7a0543",
    "host": "MacBook-Air-Mihail.local",
    "config_json": "{\"cards\":[\"cards/C-2026-09-12-01.json\",\"cards/C-2026-09-12-03.json\",\"cards/C-2026-09-12-05.json\",\"cards/C-2026-09-12-07.json\",\"cards/C-2026-09-12-09.json\"]}",
    "summary_json": "{\"failed\":[],\"ok\":[\"C-2026-09-12-01\",\"C-2026-09-12-03\",\"C-2026-09-12-05\",\"C-2026-09-12-07\",\"C-2026-09-12-09\"]}",
    "status": "DONE",
    "summary": {
      "run_id": "2026-09-12_0844-1baa1c",
      "stages": {
        "CARD_GENERATION": {
          "DONE": 5
        },
        "FRAME_GENERATION": {
          "DONE": 5
        },
        "FRAME_PLAN": {
          "DONE": 5
        },
        "SCRIPT_GENERATION": {
          "DONE": 5
        },
        "SCRIPT_REVIEW": {
          "DONE": 5
        },
        "VIDEO_GENERATION_READY": {
          "DONE": 5
        }
      },
      "totals": {
        "DONE": 30
      },
      "jobs": 30,
      "duration_s": 1.615
    },
    "date": "2026-09-12",
    "model_prompt_versions": "",
    "data_scope": "",
    "counts": "{\"DONE\": 30}",
    "statuses": "DONE",
    "issues": "",
    "reports_links": "",
    "next_steps": ""
  },
  {
    "run_id": "2026-09-11_2345-04a541",
    "started_at": "2026-09-11T23:45:24Z",
    "finished_at": "2026-09-11T23:45:24Z",
    "kind": "analysis",
    "git_commit": "92e71e7a0543",
    "host": "MacBook-Air-Mihail.local",
    "config_json": null,
    "summary_json": "{\"dry_run\":false,\"hypotheses\":24,\"hypothesis_refs\":41,\"insights\":30,\"rejected_hypotheses\":[],\"rejected_insights\":[],\"rejected_refs\":[],\"run_id\":\"2026-09-11_2345-04a541\"}",
    "status": "DONE",
    "summary": {
      "run_id": "2026-09-11_2345-04a541",
      "stages": {
        "CONCEPT_GENERATION": {
          "DONE": 24
        },
        "GENERAL_ANALYSIS": {
          "DONE": 1
        },
        "REFERENCE_SELECTION": {
          "DONE": 10
        }
      },
      "totals": {
        "DONE": 35
      },
      "jobs": 35,
      "duration_s": 0.004
    },
    "date": "2026-09-11",
    "model_prompt_versions": "",
    "data_scope": "",
    "counts": "{\"DONE\": 35}",
    "statuses": "DONE",
    "issues": "",
    "reports_links": "",
    "next_steps": ""
  }
]
```

## Categories
Rows: 278

```json
[
  {
    "kind": "topic",
    "label": "Сборка агентов и мультиагентные системы",
    "n": 27,
    "median_lift": 22.50710777777777,
    "median_share_rate": 0.017538464716312725,
    "median_save_rate": 0.0319658034818961,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "AI-видео и производство контента",
    "n": 23,
    "median_lift": 22.26648447826087,
    "median_share_rate": 0.01834524142372436,
    "median_save_rate": 0.03340099172831067,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "Claude Code: скиллы, плагины, команды",
    "n": 22,
    "median_lift": 31.79106877272727,
    "median_share_rate": 0.018175517472212646,
    "median_save_rate": 0.039953590745203375,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "Новости моделей и лабораторий",
    "n": 21,
    "median_lift": 9.416928428571428,
    "median_share_rate": 0.018759477765639927,
    "median_save_rate": 0.014486969325321456,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "Бесплатный доступ и обход платы",
    "n": 21,
    "median_lift": 17.41442228571429,
    "median_share_rate": 0.022761001421895022,
    "median_save_rate": 0.0360930872050796,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "Дизайн и сайты через AI",
    "n": 19,
    "median_lift": 33.83750531578948,
    "median_share_rate": 0.0161163143396365,
    "median_save_rate": 0.02897356646161154,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "Лидогенерация, скрейпинг, CRM",
    "n": 15,
    "median_lift": 11.132489866666667,
    "median_share_rate": 0.017763053439272144,
    "median_save_rate": 0.023745691419037335,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "AI-агентство как бизнес",
    "n": 14,
    "median_lift": 12.632814928571426,
    "median_share_rate": 0.015305751268949183,
    "median_save_rate": 0.024624648836886927,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "Обзор инструмента",
    "n": 12,
    "median_lift": 14.190838416666667,
    "median_share_rate": 0.01994181500658006,
    "median_save_rate": 0.02178996740165835,
    "confidence": "PROBABLE"
  },
  {
    "kind": "topic",
    "label": "Готовый репозиторий с GitHub",
    "n": 12,
    "median_lift": 9.280906916666666,
    "median_share_rate": 0.01741253398072615,
    "median_save_rate": 0.04993498202739168,
    "confidence": "PROBABLE"
  }
]
```

## Legacy (label, never delete)
```json
{
  "release_page": "3d20bd21ed6a813a9a4cd8f51a28af71",
  "signal_reels_db": "c26c6990-bba9-4ab5-a700-e94bd42e327d",
  "signal_accounts_db": "e45a50d2-a910-47b8-99a0-f2ec9f1a3393",
  "orphan_stub_pages": [
    "3d00bd21-ed6a-81cb-abdf-d7d0eef5497c",
    "3d00bd21-ed6a-8165-b1f4-d3520940b65a"
  ],
  "operational_reels_db_configured": true,
  "operational_accounts_db_configured": true,
  "decision_open": "audit §8.1: (a) re-point NOTION_REELS_DB/NOTION_ACCOUNTS_DB at the Signal schema and migrate notion_db.py, vs (b) keep them separate, link+label the existing operational DBs into the page tree and mark the Signal DBs as a one-off 2026-09-05 snapshot. This build implements (b) — Misha/Max's call to confirm or override."
}
```
