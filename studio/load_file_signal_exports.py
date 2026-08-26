#!/usr/bin/env python3
"""Validate and idempotently persist the active file-backed Studio exports."""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from jsonschema_subset import validate_instance


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "outputs/signal-to-studio/v1/records.jsonl"
SCHEMA = ROOT / "schemas/signal-to-studio.schema.json"
DSN = "host=127.0.0.1 port=55432 dbname=north_hux"
RUN_KEY = "20260825-north-hux-social-adapters-v1"


def records() -> list[dict]:
    return [json.loads(line) for line in RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    rows = records()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for row in rows:
        validate_instance(row, schema, SCHEMA)

    inserted = 0
    existing = 0
    with psycopg.connect(DSN) as connection:
        with connection.transaction():
            connection.execute("SET search_path = north_hux, public")
            run_id = connection.execute(
                """
                INSERT INTO research_run (
                    run_key, status, scope_json, admission_receipt_uri,
                    taxonomy_version, owner_gate, started_at
                ) VALUES (%s, 'validation', %s, %s, 'studio-shortform@1.0.0', 'owner_confirmed_public_collection', now())
                ON CONFLICT (run_key) DO UPDATE
                SET admission_receipt_uri = EXCLUDED.admission_receipt_uri
                RETURNING run_id
                """,
                (
                    RUN_KEY,
                    Jsonb({"purpose": "social adapter validation and Studio bridge", "provider_execution": False}),
                    "runs/20260825-north-hux-social-adapters-v1/admission-receipt.json",
                ),
            ).fetchone()[0]

            for row in rows:
                result = connection.execute(
                    """
                    INSERT INTO studio_signal_export (
                        run_id, source_content_id, export_id, export_version,
                        signal_record_id, schema_version, payload_json, record_hash,
                        taxonomy_version, rights_state, generated_at,
                        supersedes_export_id, public_safe, ingestion_source
                    ) VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s)
                    ON CONFLICT (export_id) DO NOTHING
                    RETURNING studio_signal_export_id
                    """,
                    (
                        run_id,
                        row["export_id"],
                        row["export_version"],
                        row["signal_record_id"],
                        row["schema"],
                        Jsonb(row),
                        row["provenance"]["record_hash"],
                        row["taxonomy_version"],
                        row["rights_state"],
                        row["generated_at"],
                        row["freshness"]["supersedes_export_id"],
                        "outputs/signal-to-studio/v1/records.jsonl",
                    ),
                ).fetchone()
                if result:
                    inserted += 1
                else:
                    existing += 1

    print(json.dumps({"validated": len(rows), "inserted": inserted, "existing": existing}, indent=2))


if __name__ == "__main__":
    main()
