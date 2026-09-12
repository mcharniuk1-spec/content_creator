# Reference: Files ported from `origin/Latest`

This directory holds files ported verbatim from the `origin/Latest` branch (commit `31ed2d41`, Max's fork at `mcharniuk1-spec/m2lab-radar`) into the canonical `content-engine` branch.

## What these files are

- **Schemas** (`video-scene-segmentation.schema.json`, `m2-corpus-field-dictionary.v1.json`): JSON schemas defining the corpus structure and video scene segmentation contract.
- **Studio/Remotion** (`studio/remotion/*`): Deterministic 9:16 video renderer using Remotion 4.0 + React 19. Includes EDL (Edit Decision List) validation contract and storyboard generation.
- **Provider catalog** (`config/provider-catalog.json`): Registry of media generation providers (gen4.5, veo3.1, etc.) with capability/pricing metadata.
- **Field dictionary** (`docs/m2-field-dictionary.csv`): Data dictionary for the 65 Notion columns (reel, account, card) with meaning, units, source, and permissible inference notes.
- **System documentation** (`m2-system-architecture.md`, `m2-corpus-worker-contract.md`): Architecture overview and contract for corpus workers. 
- **Scene taxonomy** (`SCENE-FIRST-STORY-FRAMEWORK-TAXONOMY-V3.md`): Scene classification framework with 20 categories.
- **Editorial skill** (`m2-script-writer-SKILL.md`): Writing contract with claim-map classification (recommendation / synthetic / observed fact / sourced claim) and anti-fabrication rules.

All files are **ported exactly as they existed at commit 31ed2d41**, with no modifications.

## What was NOT ported from `origin/Latest`

The following were deliberately left behind per the integration audit (`reports/audit/01-branch-comparison.md` §5.2):

1. **`m2_signal/` ledger** — immutable release/observation store with 15× storage cost per snapshot (24 MB vs main's 5.2 MB for three snapshots). Kept as **historical reference only**; main's relational `db.py` remains the canonical store.
2. **`m2_orchestrator/` media stages** — 29 of 41 pipeline stages have no implementation code (agent/human handoffs). Stages for transcription recovery, media acquisition, visual/OCR recovery solve problems not yet needed. Kept as **reference for future architecture**.
3. **`media_ocr.py` + `scripts/m2_vision_ocr.swift`** — Apple Vision integration. MacOS-only; dead on the Linux production server.
4. **`integrations/radar/`** — duplicate of root `server_entry.py`; removed to avoid confusion.
5. **`examples/ten-card-20260907/`, `knowledge/`, `docs/reviews/`** — evidence of Max's process and manual annotations (1,062 transcripts + 19,808 frames). Not in git; cannot be recovered without export from his machine.

## Canonical engine now lives in `engine/`

The current source of truth is defined in `engine/SPEC.md`:

- **SQLite store**: main's `db.py` (15 tables, `data/radar.db`) with new tables added by `engine/schema.py` (state tracing, transcript provenance, beats, video_state).
- **Acquisition**: `lib/hiker.py` + `collect_snapshot.py` (proven, cached, with spend accounting).
- **Local processing**: `deep.py` (Whisper ASR + frame extraction) upgraded with Latest's PTS-indexed decoding and process watchdogs.
- **Analysis**: `score.py` (age-banded baselines, focal-row exclusion, cross-snapshot history) and `cards.py` (format/ranking/exclusion rules from main's POSITIONING).
- **New contracts ported**: Remotion EDL validation (`studio/remotion/contract.mjs`), scene schema, provider escrow pattern.
- **Existing code unchanged**: `run.py`, `cron.sh`, `collect_snapshot.py`, `db.py`, `notion.py/notion_db.py`, all test scripts. Production default path is Hiker → Whisper → local analysis; no breaking changes.

For the integration strategy, see `reports/audit/01-branch-comparison.md` §5.2 ("Concrete integration strategy").
