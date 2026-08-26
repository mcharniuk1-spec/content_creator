# North Hux Obsidian and WikiLLM setup

## Design decision

The optimal vault is sparse and AI-first. The 10K raw corpus remains in the project run and PostgreSQL. Obsidian and WikiLLM contain reviewed synthesis, identifiers, aggregate coverage, decisions, gates, artifact links/hashes, and handoffs. This avoids slow vault search, accidental private projection, stale duplicate truth, and context flooding.

## Vault skeleton

```text
North Hux/
  00 Home.md
  01 Cases/
  02 Runs/
  03 Evidence Syntheses/
  04 PM Tracks and Strategy/
  05 Studio/
  06 Reviews and Gaps/
  07 Decisions/
  08 Handoffs/
  _templates/
  _views/
  _maps/
```

Minimum durable notes for this execution:

- one case note for the YouTube AI-agent market;
- one run note for the 10K broad screen;
- one reviewed market synthesis;
- one note for each PM creator track;
- one ten-script campaign slate;
- one Studio method and gate note;
- one database/backup decision;
- one issue note for incomplete transcript/frame evidence if still open;
- one terminal handoff.

## Required note metadata

```yaml
---
project: north-hux-content-engine
case_id: north-hux-youtube-ai-agent-market
run_id: 20260826-youtube-video-census-10k-v1
artifact_ids: []
evidence_state: reviewed-with-limitations
rights_state: aggregate-public-safe
review_state: passed-with-limitations
freshness_date: 2026-08-26
supersedes: []
next_gate: owner-review
---
```

Each note body separates `FACT`, `INTERPRETATION`, `HYPOTHESIS`, and `GAP`. It links to project-relative manifests and hashes, not raw text dumps.

## Base views

The North Hux Base should expose:

1. Current runs and evidence completeness.
2. Open owner decisions and human actions.
3. Strategy releases and creator-track ownership.
4. Script/Studio readiness and blocked gates.
5. Reviews, limitations, and unresolved gaps.
6. Backup and restore receipts.

Recommended properties: case/run ID, artifact ID, object type, status, evidence state, rights state, review state, creator track, owner action, dependency, freshness, next gate, and supersession.

## Canvas map

The Canvas should show the small durable workflow, not 10K source nodes:

`YouTube evidence → market synthesis → opportunity audit → two PM tracks → ten scripts → shot plans → Studio gates → owner media → rough cut → publication → owned analytics`.

Side nodes link PostgreSQL, Notion, GitHub, reviews/gaps, and backup/restore. Red gate nodes represent provider generation, likeness, editing mutation, and publication.

## WikiLLM promotion policy

- `runs/`: bounded task, inputs, outputs, checks, blockers, and next action.
- `issues/`: unresolved evidence, connector, schema, or approval gaps.
- `decisions/`: durable architecture or strategy choices with alternatives.
- `memory.md`: only repeated constraints, corrected assumptions, and future-run implications.
- `insights.md`: only independently reviewed reusable analytical meaning.
- `log.md`: concise append-only run index.

Do not promote raw transcripts, comments, screenshots, public metrics, prompts, or source media. A conclusion is promoted only with evidence parents, reviewer state, freshness, privacy classification, contradiction handling, and supersession.

## Exact-write gate

The external global Obsidian vault already has a North Hux skeleton, Base, and Canvas. Its architecture is sound but some counts and state labels are stale. Updating those external notes requires the exact target-note correction packet; broad vault permission is intentionally insufficient. The project-local setup and packet may be reviewed before that write.
