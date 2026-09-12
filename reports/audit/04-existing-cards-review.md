# Existing Content Audit — Cards and Scripts

Scope: every card/script that exists anywhere in the M2Radar project as of 2026-09-11 —
main's 23 radar cards (three SQLite files, deduped), Max's 10-card release from 7 Sep plus
his 11 Sep "reconciled" report, Misha's 8 Sep audit of Max's cards (cited, not redone), and
a targeted search for a "GPT-5.6 Luna run". **Zero of these 33 cards have ever been shot or
published** — `our_posts` (the table that would record a produced reel) is empty in every
database on both branches.

Method: `data/server-mirror/radar.db` (23 rows), `dataset/radar.db` (5 rows) and
`dataset/radar-0907.db` (14 rows) were joined and deduped on `(week, code)`.
`dataset/radar.db` and `dataset/radar-0907.db` are strict subsets of `data/server-mirror/radar.db`
(byte-identical rows), so the union is exactly **23 unique cards**, not 42. Each was joined
to `reels`, `scores` (weights='ig'), `transcripts`, `frames`, `deepdives`, `topics`. Max's
cards came from `git show origin/Latest:examples/ten-card-20260907/*.json` and his 11 Sep
report from `git show max/main:outputs/reports/m2-20260911-reconciled-analysis-and-cards.md`.
All quoted numbers are read directly from these sources.

## Summary table

| # | Source | Code / card_id | Format | Status | Statistically justified? | Real transcript? | Real frames? | Classification |
|---|---|---|---|---|---|---|---|---|
| 1 | Main | DbO4zvJR1k8 | Teardown | Proposed (w. 09-03) | Yes, 15.2×, save 87/1k | Yes, 274w | 9 frames, suitable=NULL | Usable with revision |
| 2 | Main | DbVKVz0y8xo | Builds | Proposed (w. 09-03) | Yes, 8.0×, save 58/1k | Yes, 315w | 9 frames, suitable=NULL | Strong |
| 3 | Main | Dbi-yxNgrhG | Radar | Proposed (w. 09-03) | Yes, 9.9×, share 58/1k | Yes, 156w | 9 frames, suitable=NULL | Strong |
| 4 | Main | DcCfMoZRkgW | Teardown | Proposed (w. 09-03) | Yes, 4.7×, share 46/1k | Yes, 258w | 9 frames, suitable=NULL | Usable with revision |
| 5 | Main | Da73u-0ysYU | Radar | Proposed (w. 09-03) | Yes, 34.1×, share 41/1k | Yes, 118w | 9 frames, suitable=NULL | Usable with revision |
| 6 | Main | DcvBtiNtbYO | Radar | draft (w. 09-07, pri1) | Yes, 3.5×, share 60/1k | Yes, 66w | 9 frames, suitable=NULL | Strong |
| 7 | Main | DcvX-lDAhk_ | Radar | draft (w. 09-07, pri2) | Yes, 3.8×, share 39/1k | Yes, 217w | 9 frames, suitable=NULL | Usable with revision |
| 8 | Main | DcoE5ZsK4I7 | Radar | вычеркнута (w. 09-07) | Yes, 1.8× | Yes, 167w | 9 frames, suitable=NULL | Incomplete (cut before writing — by design) |
| 9 | Main | Dco1mOJzZ4L | Builds | draft (w. 09-07, pri4) | Yes, 3.6×, save 57/1k | Yes, 189w | 9 frames, suitable=NULL | Strong |
| 10 | Main | DczDlj4qQjI | Builds | вычеркнута (w. 09-07) | Yes, 13.5× | Yes, 233w | 9 frames, suitable=NULL | Incomplete (cut before writing) |
| 11 | Main | DcU_BdKulGJ | Builds | draft (w. 09-07, pri6) | Yes, 3.2×, save 56/1k | Yes, 336w | 9 frames, suitable=NULL | Usable with revision |
| 12 | Main | DcwCCgivcIQ | Teardown | draft (w. 09-07, pri7) | Yes, 4.1×, save 55/1k, repeated topic ×3 authors | Yes, 196w | 9 frames, suitable=NULL | Strong |
| 13 | Main | Dc326slsdAU | Teardown | вычеркнута (w. 09-07) | Yes, 3.1× | Yes, 269w | 9 frames, suitable=NULL | Incomplete (cut before writing) |
| 14 | Main | DceZCRZIatT | Teardown | вычеркнута (w. 09-07) | Yes, 2.6× | **No transcript** | 9 frames, suitable=NULL | Incomplete (cut before writing) |
| 15 | Main | Dc_tsSeAjBy | Radar | draft (w. 09-10, pri1) | Yes, 9.1×, share 61/1k | Yes, 320w | 9 frames, suitable=NULL | Strong |
| 16 | Main | DcvBtiNtbYO (dup of #6) | Radar | вычеркнута (w. 09-10, pri2) | same as #6 | same | same | Incomplete (recycled, then cut without a new angle) |
| 17 | Main | DcmK70aO5VP | Radar | draft (w. 09-10, pri3) | Yes, 1.9×, save 62/1k | Yes, 185w | 9 frames, suitable=NULL | Strong |
| 18 | Main | Dct6Op3n6Zd | Builds | вычеркнута (w. 09-10) | Yes, 22.5× | Yes, 102w | 9 frames, suitable=NULL | Incomplete (cut before writing) |
| 19 | Main | DcxV37-CJOC | Builds | вычеркнута (w. 09-10) | Yes, 6.7× | 5 words only | 9 frames, suitable=NULL | Incomplete (cut before writing) |
| 20 | Main | DdCvFdHsnj1 | Builds | draft (w. 09-10, pri6) | Yes, 14.4×, save 58/1k | Yes, 196w | 9 frames, suitable=NULL | Unsupported (card admits nothing is built yet) |
| 21 | Main | Dco1mOJzZ4L (dup of #9, new fmt) | Teardown | draft (w. 09-10, pri7) | same source as #9 | same | same | Usable with revision (duplicated effort on one source reel) |
| 22 | Main | DcwCCgivcIQ (dup of #12) | Teardown | вычеркнута (w. 09-10) | same as #12 | same | same | Incomplete (recycled, then cut without a new angle) |
| 23 | Main | Dc_iv4YKCAh | Teardown | вычеркнута (w. 09-10) | Yes, 42.4× | Yes, 172w | 9 frames, suitable=NULL | Incomplete (cut before writing) |
| 24 | Max | M2-I01 | Introduction (synthesis) | SCRIPT_CANDIDATE | **No** | **No** (fictional) | No (illustrated storyboard) | Weak / unsupported |
| 25 | Max | M2-I02 | Introduction (synthesis) | SCRIPT_CANDIDATE | No | No | No | Weak / unsupported |
| 26 | Max | M2-I03 | Introduction (synthesis) | SCRIPT_CANDIDATE | No | No | No | Generic / unsupported |
| 27 | Max | M2-I04 | Introduction (single ref, non-synthesis) | SCRIPT_CANDIDATE | Ref cited at 1.01× (no signal) | No | No | Weak |
| 28 | Max | M2-I05 | Introduction (2 refs, non-synthesis) | SCRIPT_CANDIDATE | One ref cited at 322× vs ~650-view median (uncontrolled outlier) | No | No | Unsupported |
| 29 | Max | M2-P01 | Regular (synthesis) | SCRIPT_CANDIDATE | No | No | No | Weak |
| 30 | Max | M2-P02 | Regular (synthesis) | SCRIPT_CANDIDATE | No (ironically, about reading metrics) | No | No | Weak (self-contradicting: its own 3 refs run 1.01×, 0.29×, 1.01× — exactly what it says not to use) |
| 31 | Max | M2-P03 | Regular (synthesis) | SCRIPT_CANDIDATE | No | No | No | Usable with revision (best of the ten per Misha's audit) |
| 32 | Max | M2-P04 | Regular (single ref, non-synthesis) | SCRIPT_CANDIDATE | No (ref's technique unused) | No | No | Usable with revision (most practical CTA, but zero evidence) |
| 33 | Max | M2-P05 | Regular (synthesis) | SCRIPT_CANDIDATE | No | No | No | Weak |

**Main total:** 14 of 23 developed into a full angle/hook, 9 correctly cut before writing, **0 shot, 0 published.**
**Max total:** 10 of 10 are `PROVIDER_EXECUTION: false`, `AWAITING_OWNER_ASSET` on all 80 assets, 7 of 10 are multi-source "synthesis" (invented composite scenarios), 0 have a statistically justified reference, 0 use a real transcript quote, 0 have real frames (storyboards are AI-illustrated composition guides, explicitly labelled "not an owner take, product output, or production asset binding").

---

## A. Main's radar cards (23, three databases)

### Pipeline as built

`cards.py` (`select()` → `_pool()` → `_card()` → `save()`) pulls the latest snapshot,
requires `eligible=1`, a duration of 20–120s, a multiplier ≥1.5× the author's own median
play count, drops accounts flagged inactive, drops `OFF_TOPICS` genres, and for Teardown
requires the topic to repeat across ≥3 authors (`_repeated_topics`). It writes the
statistical "why" and the three shot-plan columns automatically; **angle and hook are
written by a separate agent** reading `prompts/angles.md`, the contact sheet
(`data/frames/<code>_sheet.jpg`) and `blocks.py <code>` (transcript split into
hook/body/close), per the four-part editorial filter in `POSITIONING.md` §8. This is a
materially different, more evidence-bound process than Max's (see §B).

### What is genuinely strong here

The 14 developed cards are, without exception, built on a real reference reel with a real
`z`-score, a real multiplier against **that author's own** median play count (never a
platform-wide number), and — in 13 of 14 — a real transcript quote. Several angles are
excellent examples of the RULES.md §4 "рерайт-тест" (remove the source topic and see if
anything is left): `Dc_tsSeAjBy` explicitly declines to borrow the source's "4x faster"
claim ("No numbers from us: we have not tested this on our own re-keying, and we say so
instead of borrowing the ... line from the video"); `DcmK70aO5VP` explicitly drops the
comment-bait and the "$8,000/month" promise and swaps the source's high-risk verticals
(law, recruitment, insurance) for a cheap-to-fail one, exactly matching RULES.md §1.2.
`DcvBtiNtbYO` (#6) is the best single card in the set: an honest admission that M2's own
governance rule went unenforced for two days, which is precisely the "we tried / it broke"
evidentiary standard POSITIONING.md §6 requires and Max's cards never reach.

### Four process defects found in the data itself

1. **The genre filter is not actually enforced at selection time.** `cards.py`'s
   `OFF_TOPICS` set (present since the first commit, `f93f607c`, 2026-09-03) explicitly
   excludes `'Развлечение и конспирология'` (entertainment/conspiracy) and
   `'Бесплатный доступ и обход платы'` (free-access/bypass-payment) — yet card #4
   (`DcCfMoZRkgW`, robot-fighting reel) is tagged with exactly the first excluded topic,
   and card #5 (`Da73u-0ysYU`, free-AWS-credits reel) is tagged with exactly the second.
   Both were nonetheless drafted with a full angle. The likely mechanism: `topics` are
   assigned by a separate script (`tag_topics.py`/`tag_candidates.py`) that can run
   **after** `cards.py select()` has already picked the reel, so the exclusion check in
   `_pool()` sees an empty topic list at selection time and never fires. Whether or not
   the resulting cards are good (see below — #4 and #5 both got reasonable angles), the
   filter cannot currently be trusted to have run before a card exists.
2. **A "draft" card is not treated as used, so it can be re-proposed the next week.**
   `DcvBtiNtbYO` got a full angle+hook in week 09-07 (pri 1) and was re-selected in week
   09-10 (pri 2), this time cut with no angle written. `DcwCCgivcIQ` (Teardown) did the
   same across the same two weeks. `_pool()`'s `decided` set only excludes
   `'Not taking','Shot','Published','вычеркнута'` — `'draft'` is not in it — so a fully
   scripted card sits available for re-selection until someone actively rejects or ships
   it. Because nothing has ever shipped, this loop has no natural exit yet.
3. **One source reel produced two unrelated, non-overlapping scripts.** `Dco1mOJzZ4L`
   (a "10 marketing skills for Claude" listicle) was drafted as a **Builds** card in week
   09-07 (angle: we built the "content-plan" skill, $12.46, 2352 reels) and, one week
   later, as a completely different **Teardown** card (angle: the real product is a
   written brand-voice rulebook) from the same code. Both scripts are individually
   reasonable, but this is duplicated agent effort on a single reference rather than two
   references being covered.
4. **`deepdives.suitable` is `NULL` for all 23 cards, in every database.** RULES.md §2а
   (added 1 Sept, "after storyboard, before writing the card") requires exactly this field
   to be set before a card is drafted — it is the record that a human/agent actually
   checked the reel is not e.g. someone else's cloned voice or a jailbreak promotion. It
   has never been populated for a single card. This does not mean the check was skipped in
   spirit (nothing found suggests a genuinely disqualifying reel slipped through), but the
   compliance record the rule asks for does not exist.

### Card-level notes worth carrying forward

- `DdCvFdHsnj1` ("AI cannot answer a single question about your company...") is well
  written but **fails the Builds format's own pass criterion**: RULES.md §2 requires
  "собрано нами и есть чему сломаться" (we built it, and there is something to break), and
  the card's own angle says "We have not built this yet. Before this is shot as a Build we
  run it on our own repeated questions..." — it is a Radar/plan, packaged as a Builds card.
- Cards #6, #7, #9, #11, #12 (five of the fourteen developed cards, all from week 09-07)
  reuse the same two internal proof points — "our ranker put a 654-view reel above a
  25,000-view one" and "a free source closed mid-run" — as their central evidence. Both
  are plausible given the raw data (an exact 654-view reel and multiple ~25,000-view reels
  do coexist in the same eligible pool in `data/server-mirror/radar.db`, and `cards.py`
  ranks by `resh_1k`/`save_1k`, which is not view-normalised, so a low-view/high-ratio reel
  outranking a high-view one is a real weakness of the formula), but there is no run log in
  the repository that pins down a specific selection event producing that exact pair. If
  five reels ship in the same week repeating the same anecdote, the audience sees the same
  "proof" five times.
- `DceZCRZIatT` and `DcxV37-CJOC` were correctly left uncut/cut with almost no transcript
  (0 words and 5 words respectively) — the pipeline's own filters would have struggled to
  ground an angle in either, and both were in fact abandoned (one before, one after
  transcription) rather than forced into a script.

---

## B. Max's ten-card release (7 Sep, `origin/Latest`/`max/main`, `examples/ten-card-20260907/`)

### Format

`m2.editorial-scriptcard.v1`: three candidate hooks, one frozen `full_spoken_english`
script (127–140 words), a `fixture` (input/output/check) whose `state` is
**`DESIGNED_NOT_MODEL_EXECUTED` on every single card** — meaning none of the "AI does X"
claims were ever run through a model, they were authored as prose — 7 timed `shots` with
`mode` (a_roll/demo/motion_graphic), `on_screen_text` and an `information_job`, matching
`segments`, an `audio_plan`, a `caption_plan`, 8 `assets` per card all in state
`AWAITING_OWNER_ASSET`, and a `storyboard` explicitly typed `ILLUSTRATED_CONTACT_SHEET`
("Composition guide only; not an owner take, product output, or production asset
binding"). `manifest.json` confirms `production_state:
OWNER_FOOTAGE_AND_SPEECH_ALIGNMENT_PENDING` and `provider_execution: false` on every card.

`docs/m2-ten-card-release.md` states the evidence base directly: 1,062 of 2,352 reels have
a transcript (45.2%), 18 references got full review, and **7 of the 10 cards are
"multi-source, single-problem" syntheses** — confirmed in the JSON (`synthesis: true` on
I01, I02, I03, P01, P02, P03, P05; `false` on I04, I05, P04). A synthesis card cites no
single reel; it is an invented scenario built to illustrate a positioning point. Grepping
all 10 files for `z-score`, `median` (as data, not as a word in the script) or an Instagram
URL returns nothing outside the copy of M2-P02 itself, and there it appears only as
instructional prose ("Compare it with the same account's usual views"), not as evidence
behind the card's own selection.

### Classification and the 8 Sep audit

Misha's own scene-by-scene audit of these ten cards already exists at
`audit-2026-09-08/audit/cards-audit.md` (454 lines) and was independently fact-checked at
`audit-2026-09-08/audit/verification-cards.md` (verdict: **PASS WITH FIXES**, i.e. its
factual claims hold with six small corrections). This report does not repeat that
scene-by-scene work; the corrected headline numbers are:

- **10 of 10 cards name zero tools.** The `Tool` field the audit checks for is empty in
  every card.
- **10 of 10 cards contain zero measured numbers** and no `WAS/NOW/SAVED` figure
  (`04-voice.md:91`).
- **10 of 10 cards name neither Michael nor Max** on screen.
- Of 70 total scenes: 25 are clean ("OK" per audit, recount confirmed), the rest carry at
  least one defect — 16 generic/positioning-recap, 14 unproven ("NOPROOF" — all traceable
  to `fixture.state: DESIGNED_NOT_MODEL_EXECUTED`), 12 timing/structure violations (every
  card's hook runs 4–7s against a 0–3s house rule), 12 brand-voice violations (recounted;
  the original audit undercounted at 6).
- **16 distinct reels back all 10 cards**, not the 18 the release doc claims.
- 12 of the 16 source reels used perform **at or below their own author's median** — only
  4 beat it, and two of those four are 156× and 322× outliers against a ~650–6,500-view
  median, i.e. noise, not signal, by the selection method Max's own findings doc
  prescribes ("report the denominator").
- All 16 source reels are drawn from the agent/automation-builder niche (`multi-agent
  advisory board`, `fan-out/fan-in sub-agent workflow`), which `POSITIONING.md` §4
  explicitly places outside M2's audience.

Verdict for each of the 10 (already computed by the cited audit; summarised in the table
above): **0 of 10 pass the checklist the audit built from the brand book** ("Today by this
checklist, 0 of 10 cards pass"). The two least-bad by both the 8 Sep audit and this review
are **M2-P03** (a genuinely useful idea — "the owner checks the source, makes the call, and
records it" — undercut only by an invented "twelve updates" number) and **M2-P04** (the
single most actionable CTA in the slate — "add one line: show us how this handles our
difficult example" — undercut by having zero evidence behind it and by never using the one
technique its own cited source actually demonstrated).

### Max's 11 Sep "reconciled" report (`max/main:outputs/reports/m2-20260911-reconciled-analysis-and-cards.md`)

This report's own execution receipt states plainly: **no new collection, transcription,
generation, or dataset replay was run** ("Local dataset replay: not run because Michael's
newer raw export is absent"). Its "ten cards" are prose sketches, not the ScriptCard
format, and cross-checking them against main's own week-of-09-10 selections shows four of
the ten are **verbatim reuses of main's own picks**, relabelled as "handoff" cards, with
Max's copy rewritten on top:

| Max's card (11 Sep) | Signal Max cites | Matches main's card | Main's own number |
|---|---|---|---|
| 01 — "Somebody retypes the same numbers from a PDF every week" | 9.1× own median | `Dc_tsSeAjBy` (#15) | 9.1× (2,350,035 / 257,026) |
| 02 — "Every morning someone decides who each email belongs to" | 1.9× own median, 40 shares/62 saves per 1k | `DcmK70aO5VP` (#17) | 1.9×, 40/62 per 1k |
| 03 — "AI knows a lot. It does not know how your company answers this question" | 14.4× own median | `DdCvFdHsnj1` (#20) | 14.4× |
| 04 — "Ten AI add-ons do not fix a brand rule that nobody wrote down" | 3.6× own median, 57 saves/1k | `Dco1mOJzZ4L`-as-Teardown (#21) | 3.6×, 57/1k |

Cards 05–10 in the same report cite **no signal at all** — no multiplier, no share/save
rate, no reel — they are original but entirely unevidenced (e.g. "05 — Stop asking 'what
tool?'": no reference function, no numbers). So the newest Max artifact is best read as: a
correct diagnosis of his own corpus gap (his local export is 100 accounts/2,352 reels from
before 1 Sept; Michael's 10 Sept export — 1,535 reels/130 accounts — was never handed to
him in a joinable form), four cards borrowed from main's already-existing picks, and six
cards invented with zero grounding — still with no owner footage, no live tool calls, and
the same `provider_execution: false` posture as the 7 Sep release.

---

## C. Misha's 8 Sep audit of Max's cards — pointer, not a repeat

Already exists and was independently verified:
- `audit-2026-09-08/audit/cards-audit.md` — scene-by-scene verdicts, 5 fields per card, root
  causes 1–8, three fixes for the next run.
- `audit-2026-09-08/audit/verification-cards.md` — verdict **PASS WITH FIXES**; every
  brand-file line reference and every reel view/multiplier number was independently
  reproduced and matched; six small corrections listed (a wrong `manifest.json` line
  reference, two miscounted claims, two non-contiguous "verbatim" quotes, one dash/hyphen
  mismatch).
- `audit-2026-09-08/notion-raw/10..19-card-*.md` — the live Notion structure per card
  (`Format`, `Source Reels` with author/views/multiplier, "The idea in one minute"), used
  below for the information-architecture comparison.

This review adopts its numbers as-is (with the six corrections applied) rather than
re-deriving them.

---

## D. The "previous GPT-5.6 Luna run" — searched, does not exist as a run

Commands used:
```
grep -ril "luna" .                                    (this repo, working tree)
git grep -il "luna" origin/Latest max/main             (both remote branches, all history)
grep -ril "luna" ~/Desktop/"M2 Lab"                    (everything on disk for the project)
git log --all --oneline | grep -i luna                 (commit messages)
```

**Finding: there is no Luna run, no Luna-generated card, and no Luna trace anywhere.**
"Luna" (`gpt-5.6-luna` / `luna-high`) is a **model-preference label inside Max's own
pipeline config**, not an external model that was ever called:

- `agents/m2-roles.json` sets `"model_preference": "gpt-5.6-luna"` on several pipeline
  roles (rank_candidates, visual_attempt, transcript_attempt, etc.), but every one of the
  17 occurrences in that file also carries `"model_api_enabled": false` and
  `"execution": "deterministic_or_interactive_codex"` — i.e. those stages actually run as
  deterministic code or an interactive Codex session, and the "Luna" label is never
  invoked via an API.
- `m2_orchestrator/semantic_queue.py` and `m2_signal/transcript_benchmark.py` use
  `maker_model: str = "luna-high"` / `reviewer_model: str = "luna-high"` as default
  parameter values in a queue/benchmark class — again a role name, not a live call.
- `docs/reviews/m2-radar-v3-independent-review-20260906.json` records
  `"maker": "luna-radar-package-maker-r3"` — this is an internal pipeline-stage identity in
  a self-generated review receipt, not a named external reviewer.
- `docs/m2-v2-delivery.md` claims "Independent Luna High review passed all 28 added tests
  (18 benchmark and 10 diagnostic cases)" — these are the repository's own `unittest` cases
  passing, not a review by an actual model called "Luna".
- Three unrelated files matched the grep as false positives: a Lucide icon-tag JSON
  (`design/assets/icons/lucide/tags.json`, matches on "luc" + unrelated text), a base64
  frame blob (`dataset/2026-08-niche-research/frames_b64.json`), and one cached HikerAPI
  response containing a random base64 substring that happens to contain "luna". None
  reference a model or a run.

There is no model called "GPT-5.6" documented anywhere in either branch outside this
placeholder string, and `model_api_enabled` is `false` in every single occurrence found —
so no card, script, transcript, or frame analysis in either branch was ever actually
produced by a model under this name. Treat every "Luna"-attributed review or receipt in
Max's branches as a self-authored/deterministic artifact, not independent model output.

---

## General conclusions

**What worked.** Main's pipeline: a real reel, a real multiplier against that author's own
median, a real transcript, and an agent that is instructed (`prompts/angles.md`) to state
plainly when M2 has no evidence rather than borrow the source's numbers. Half of the 14
developed main cards (`DcvBtiNtbYO` #6, `Dco1mOJzZ4L`-as-Builds #9, `DcwCCgivcIQ` #12,
`Dc_tsSeAjBy` #15, `DcmK70aO5VP` #17) are genuinely strong and are the right templates for
how a card should read: specific number, honest self-experiment, one repeated process, one
human-owned decision, one next action.

**What did not work.** Max's entire output across both dates: two releases, zero
statistically justified references, zero real transcripts quoted, zero real frames (all
storyboards are illustrated placeholders), zero built things, zero owner footage, and — per
his own 11 Sep report — the newest four "his" cards are actually main's own picks with the
copy rewritten. The `DESIGNED_NOT_MODEL_EXECUTED` / `AWAITING_OWNER_ASSET` states are
honestly labelled, but they mean the entire slate is a writing exercise, not a card
inventory ready to shoot.

**What to preserve.** The `_pool()` statistical gate (own-author median, `eligible=1`,
duration window), the requirement that angle/hook be written by reading the actual
transcript and contact sheet rather than the brand book, and the explicit instruction not
to invent numbers — this is the single biggest quality gap between the two branches and
should not be diluted.

**What to change.**
1. Fix the topic-tagging race so `OFF_TOPICS`/`DEV_TOPICS` are guaranteed to be populated
   before `select()` runs, not after.
2. Add `'draft'` to the set of "already decided" statuses `_pool()` excludes, or add an
   explicit `Shot`/`Not taking` transition step, so a scripted card cannot silently loop
   into next week's pool.
3. Populate `deepdives.suitable` before a card gets an angle, as RULES.md §2а already
   requires on paper.
4. Cap how many cards in one week's slate may lean on the same internal proof anecdote
   (currently 5 of 14 developed cards share two anecdotes).
5. For Max's pipeline: no card should reach `SCRIPT_CANDIDATE` without at least one
   reference at ≥1.5× its own author's median (his own `primary-editorial-findings` doc
   already states this rule; it was not applied to 12 of his 16 sources) and without a
   named tool.

**Templates to reuse.** `DcvBtiNtbYO` (#6) and `Dc_tsSeAjBy` (#15) are the cleanest
examples of the intended card shape and should be the reference example the angle-writing
agent is shown first (`prompts/angles.md` currently shows none).

**Templates that must not guide future generation.** Any of Max's 10 cards as a *content*
template (no tool, no number, no owner footage, invented fixtures) — the JSON *schema*
(timed shots, three candidate hooks, explicit claim states) is worth keeping, the content
inside it is not. `DdCvFdHsnj1` (#20) should not be used as a Builds template since it
violates the format's own pass criterion.

## Format comparison and recommended information architecture

| | Main (`cards` table) | Max (`ScriptCard` JSON) | Notion (`audit-2026-09-08/notion-raw`) |
|---|---|---|---|
| Starting point | One specific reel that beat its own author's median | An invented scenario, or (non-synthesis) one reel cited without a pass/fail threshold | Mirrors whichever JSON fed it |
| Proof | Real: multiplier, resh_1k/save_1k, transcript quote | `fixture.state = DESIGNED_NOT_MODEL_EXECUTED` on every card | Adds a "Source Reels" relation with author/views/multiplier — the one thing main's schema lacks as a first-class field |
| Script | Angle (prose) + one-line hook; full script not pre-written, three shot-columns only | Frozen 127–140-word `full_spoken_english`, 3 hook options, 7 timed scenes with `on_screen_text`/`transition` | Full script + scene table, plus a "The idea in one minute" box (for/problem/gives/why) not present in either JSON or `cards` table |
| Duration/pacing control | None — no word-count or seconds field on the card | `duration_seconds`, `fps`, `word_count` fields exist but are template-fixed (60s/7 scenes for all 10, regardless of topic) | Duration shown as a property, inherited from JSON |
| Destination ("к чему ведём") | `goal` field exists, **empty on all 23 cards** — open per RULES.md §9 | Not modelled | Not modelled |

**Recommended field list for the next card format** (combining what each of the three
already does right):

1. `source_reel` — code, username, URL, views, multiplier vs. that author's own median,
   share/save-per-1000, snapshot date (main's `why` + Notion's "Source Reels", made a
   first-class structured field instead of prose).
2. `transcript_hash` / `transcript_quote` — a pinned, dated pointer into `transcripts`, so
   a claim like "the author said X" can be checked without re-opening the source video.
3. `frame_ids` / `suitability_check` — pointer into `frames`/`deepdives`, with
   `deepdives.suitable` populated (currently always NULL) before this record is created.
4. `format` (Radar/Builds/Teardown) with the four-part mandatory filter (process, friction,
   AI boundary, next action) as four required sub-fields, not prose folded into `angle`.
5. `angle` — the transformation prose, kept as-is; this is main's strongest asset.
6. `hooks` — 2–3 candidate hooks (Max's idea), each tagged whether it is a question or a
   statement, since RULES.md's audit already flags "no question, no tease" as a house rule.
7. `script` — the full spoken text, with a live word-count-to-seconds estimate against
   PRODUCTION.md's measured 50–70s band (not a fixed 60s/7-scene template regardless of
   topic).
8. `scenes[]` — timed, with `visual`, `on_screen_text`, `information_job` (Max's structure)
   but scene count driven by the topic, not fixed at 7.
9. `claim_state` per factual statement — `OBSERVED` / `PLANNED` / `TO_MEASURE` / `MISSING`
   (from Max's 11 Sep corrected-architecture proposal — the one part of his newest report
   worth adopting even though his own cards don't yet use it).
10. `goal` / destination — kept open until the накопитель decision (RULES.md §9), but
    should not silently stay blank forever; needs an explicit "unresolved" flag distinct
    from an unfilled field.
11. `status` lifecycle — extend beyond `draft/Proposed/вычеркнута` to include `Shot` and
    `Published`, and make `_pool()`'s exclusion set match the full lifecycle so a scripted
    card cannot resurface (process defect #2 above).
