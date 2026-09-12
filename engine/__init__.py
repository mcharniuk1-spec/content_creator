"""M2Radar Content Engine.

The engine is a state and analysis layer *above* main's SQLite database
(`data/radar.db`, created by `db.py`). Nothing in the legacy 15 tables is
renamed or dropped; `engine.schema` only adds tables and guarded columns
through an idempotent, versioned migration.

Entry points (all stdlib-only):

    python3 -m engine.schema [--db PATH] [--check]
    python3 -m engine.migrate_legacy [--db PATH] [--dry]

See `engine/SPEC.md` for the binding architecture spec.
"""

__version__ = "1.0.0"
