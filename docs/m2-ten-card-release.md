# Ten-card release handoff

This portable release packages a reviewed editorial slate for Instagram Reels. It contains five introduction cards and five regular cards, with one multi-source, single-problem synthesis in each group. Scripts are original fictional examples for small-business operators; they are not client results, provider outputs or performance predictions.

## Evidence boundary

The release uses 1,062 machine transcript records within a 2,352-Reel canonical export (45.2% text coverage). There are 954 normal outputs and 108 timing-flagged outputs; another 108 attempts failed, 24 produced empty/unverified output, and 1,158 were not attempted. Eighteen selected references received bounded full-text and contact-sheet review, covering 262 samples and 64 exact observations. The other 1,044 transcripts have lexical inventory but still need detailed semantic review. The ten cards contain 70 timed scenes, 30 openings and seven multi-source syntheses (three introductions and four regular cards). Source metrics are dated 1 September 2026, with unequal exposure windows; this is not a current trend census.

The independent review accepts the exact original card candidate with limitations. Ten original illustrated contact sheets provide seven scene panels each. They are composition guides, not product outputs or owner footage. Owner shooting, speech alignment, production QA and publication remain later gates. Planned speech is not recorded speech. Source wording, footage, branded layouts, music, voice and likeness are not cleared for reuse.

## Portable route and switches

- Existing-data replay: `python3 run.py` or `scripts/run_m2.py` with a frozen export. It performs deterministic local stages and makes zero acquisition, provider or Notion calls.
- Local media/ASR: `m2_studio/cli.py media-map` accepts an explicit rights-bearing media map and optional local model. Missing media stays `LOCAL_MEDIA_NOT_SUPPLIED`; a model must already exist locally. `scripts/run_m2_corpus_media.py` and `scripts/run_m2_transcription_recovery.py` are bounded continuation routes.
- HikerAPI: `hiker_server.py` defaults to `PLAN_ONLY`. Live mode is partner-server-only and requires `--execute`, environment-injected `HIKER_KEY` or `HIKERAPI_KEY`, exact config and approval hashes, budget/rights scope, and a one-request pilot until an independently reviewed live schema receipt exists. The adapter's fixture mode is not live proof.
- Loore: `config/m2-loore-optional.v1.json` remains `enabled: false`, `paid_execution: false`, `automatic_tracking: false`, `OPTIONAL_AUTH_UNAVAILABLE`. It is an optional contract, not an authenticated connection or evidence source.

## Stage handoff

Inputs are the frozen canonical export, reviewed source packets, positioning, role contracts, and exact card/source-review artifacts. The supplied creator handbook is a reviewed secondary writing aid. The script, scene and review roles now retrieve it and the humanize-writing skill; both are included in implementation hashes so changing them requires a new run. A distinct reviewer inspected the candidate and selected source evidence.

| Stage | Inputs and parameters | Output and proof boundary |
|---|---|---|
| Replay and metrics | Explicit export; frozen input and implementation hashes; replay mode; source-native counters; nulls preserved | 12 local stages rerun; event-chain verification passed; zero Hiker, provider or Notion calls by the replay |
| Existing local ASR | Retained source/model hashes; hash-bound multilingual model bundle; CPU int8; two inference threads; one worker; beam 5; automatic language; word timestamps | 1,062 nonempty primary records; acoustic accuracy is not established by nonempty text; no new ASR in this release |
| Frames | Retained media; regular samples plus before/after visual-change candidates; default cut threshold 0.32 | 1,194 frame sets; extraction is distinct from semantic review; selected review scope is 262 samples |
| Quantitative comparison | Views / account median; baseline sample size; dated source counters; separate within-available-transcript and corpus ranks | Descriptive reference selection; no causal, predictive or generalized popularity conclusion |
| Qualitative analysis | All 1,062 texts scanned lexically; 18 complete texts and their contact sheets reviewed | Lexical topic indicators for the inventory; explicit rhetorical functions and exact frame pointers only for the reviewed references |
| Writing and review | M2 positioning; one problem and solution; three openings; fictional inputs; source functions; secondary handbook; spoken editing | Five introductions and five regular cards, each with seven contiguous scenes, full speech, CTA, audio/caption plan and owner next step |
| Projection | Connected Notion MCP; proven targets; preserved owner fields; permanent uploads; bounded selected views | Complete CSV/dictionary/dashboard attachments; card body/image/relation readbacks; full backend data kept separate from selected display |
| Editing handoff | Versioned ScriptCard; 30 fps; 1080×1920; 1,800 planned frames; explicit missing owner visual/speech assets | All ten cards compile and validate as PREVIS; production validation refuses them until real assets and reviewed speech alignment exist |

Fresh release verification passed three standard-library integration tests covering all ten card/image hashes, all 70 scene partitions, exact speech-to-caption preservation, editorial dependency hashing, and refusal of premature production. Eleven standard-library pipeline tests also passed. A fresh 12-stage deterministic replay and its event-chain verification passed. The earlier reviewed recovery delivery records 46 focused tests; that pytest suite was not rerun because pytest is unavailable in the present runtime. No installation was performed. The separate R7 pilot remains timing-flagged and unapproved; its overlaps were not added to the primary corpus totals. No partner-host ASR, live Hiker schema, Loore authentication, final-video generation or complete-corpus media result is established.

## Next safe action

Read `examples/ten-card-20260907/manifest.json` and choose a card. This directory contains original scripts and storyboards; private source transcripts, creator frames, account identifiers and Notion IDs are excluded. The source evidence remains available in the authorized Notion delivery.

```bash
python3 -m unittest discover -s tests -p test_editorial_release.py -v
python3 -m m2_studio card-edl --card examples/ten-card-20260907/M2-I01.json --output .local/M2-I01-edl.json
python3 -m m2_studio validate-edl --edl .local/M2-I01-edl.json
```

After owner footage arrives, supply exact asset bindings with `--bindings` and a reviewed speech alignment receipt with `--alignment`. Rebuild the EDL, review the rendered audio/video, and apply the existing production gate. Do not bind a contact sheet as if it were seven owner takes. The Notion projection is complete only when its final readback receipt exists; its external state is not implied by this portable document.

## Notion target migration

The current ten-card database replaces an older deleted Cards database. Before wrapper writeback, the partner operator must set `NOTION_CARDS_DB` to the active target documented in the private Notion release handoff and verify the connected identity and schema. The public package intentionally contains no private database IDs. Existing Reels and Accounts targets remain the same. No partner server environment was changed or deployed by this release.
