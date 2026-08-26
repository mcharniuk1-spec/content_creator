# PostgreSQL and artifact backup / restore

## Local database

- Host: `127.0.0.1`
- Port: `55432`
- Database: `north_hux`
- Primary schema: `north_hux`

Credentials are resolved locally by the operator environment. They must not be stored in this repository, Notion, Obsidian, WikiLLM, task logs, or screenshots.

## What PostgreSQL stores

PostgreSQL stores accounts, content identities, point-in-time public metrics, transcript text segments, media/frame pointers and hashes, evidence attempts and typed gaps, analysis artifacts, strategy versions, scripts, shot plans, edit plans, EDL segments, reviews, gates, and backup receipts. Raw subtitle files, public comments, media fragments, and source frames remain run-local; the database stores their project-relative pointers and hashes.

## Backup model

The reliable backup is two-part:

1. PostgreSQL custom-format dump for the structured database.
2. Hashed artifact manifest/archive for run-local raw, normalized, and derived files.

Git is neither part.

Recommended local paths are under ignored `backups/`:

```text
backups/
  YYYYMMDD-HHMM-north-hux.dump
  YYYYMMDD-HHMM-artifacts-manifest.json
  YYYYMMDD-HHMM-restore-receipt.json
```

## Backup procedure

1. Verify at least 15 GiB remains free after the estimated dump/archive.
2. Freeze the target run or record its exact in-flight state.
3. Run a custom-format PostgreSQL dump.
4. Build a sorted manifest of project-relative artifact paths, sizes, and SHA-256 hashes.
5. Hash the dump and manifest.
6. Insert a `backup_receipt` row with scope, hashes, sizes, retention, and restore state.
7. Never copy secret configuration or `keys.md` into the archive.

Build the run-local manifest only after transcript and frame collection has stopped and the
analysis outputs are frozen:

```bash
python3 scripts/build_run_artifact_manifest.py \
  --run-dir runs/20260826-youtube-video-census-10k-v1
```

The command writes `receipts/terminal-artifact-manifest.jsonl` plus a compact summary with the
manifest SHA-256, per-root file counts, and byte totals. It is local-only and intentionally not
projected to GitHub, Notion, or Obsidian.

Example command after local credential resolution:

```bash
pg_dump --format=custom --no-owner --no-acl \
  --file backups/YYYYMMDD-HHMM-north-hux.dump \
  --dbname 'host=127.0.0.1 port=55432 dbname=north_hux'
```

## Restore test

Use a disposable database, not the live database:

1. Create `north_hux_restore_check_<timestamp>`.
2. Restore the custom dump with `pg_restore --no-owner --no-acl`.
3. Compare migration objects and critical counts:
   - research runs;
   - accounts and content;
   - transcript artifacts and segments;
   - frame manifests and frame pointers;
   - analysis artifacts;
   - strategy releases, scripts, shots, and EDL segments;
   - artifact and artifact-edge counts.
4. Resolve a sample of transcript/frame pointers and recompute their SHA-256.
5. Record duration, result, count comparison, sample hashes, PostgreSQL version, and dump hash.
6. Drop the disposable restore database only after the receipt is written.

The restore test is `passed` only when schema restoration, critical counts, and sampled artifact hashes match. A successful `pg_dump` process alone is not recovery proof.

## Retention and recovery objectives

- Structured database: daily during active collection, plus a frozen terminal dump.
- Raw/normalized artifacts: manifest at every frozen run boundary.
- Campaign/Studio package: manifest at every owner-review release.
- Local target RPO: one active collection day.
- Initial local target RTO: four hours, to be replaced by measured restore time.
- Public platform retention and refresh/delete dates continue to govern source artifacts.
