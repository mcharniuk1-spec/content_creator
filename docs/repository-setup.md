# Reproducible public repository package

## Canonical remote

The owner-designated remote is `mcharniuk1-spec/content_creator`. A remote push is an explicit external write; future runs must obtain exact approval again unless the active owner request already grants it.

## Include

- public-safe `README.md` and compact agent contract;
- ordered SQL migrations and migration tests;
- JSON schemas and small redacted fixtures;
- deterministic collectors/analyzers/loaders/renderers and focused tests;
- architecture, method, database, Studio, restore, and operator documentation;
- configuration templates without secrets;
- reviewed knowledge summaries and public-safe run handoffs;
- ten original script/shot packages and deterministic SVG frame plans;
- validation and public-safety receipts.

## Exclude

- `keys.md`, `.env*`, credentials, cookies, account sessions, and private handoffs;
- `.local/`, PostgreSQL data, dumps, and backups;
- raw transcripts, raw comments, raw API payloads, source media, MHTML storyboards, and source frames;
- user-supplied PDFs and private material;
- large generated reports and raster render folders;
- local absolute paths, private Notion URLs/IDs, and device-specific configuration.

## Clone-and-run contract

The repository is reproducible when a colleague can:

1. clone it without Git LFS or private submodules;
2. inspect the public-safe README and `AGENTS.md`;
3. install dependencies from the pinned manifest in an isolated environment;
4. run tests without provider keys or network access;
5. apply migrations to a disposable PostgreSQL database;
6. execute deterministic fixture analysis and campaign generation;
7. compare expected hashes; and
8. understand exactly which live adapters, credentials, source rights, and owner approvals are still required.

Raw evidence is restored separately and is never silently downloaded by setup.

## Pre-push review

Before every push:

- stage an explicit allowlist, never the whole workspace by habit;
- scan staged files for secrets, local absolute paths, raw transcript/comment text, private IDs, and large binaries;
- run the focused and full test suites;
- verify migration ordering and compile scripts;
- inspect the staged diff and file-size list;
- create a public-safe handoff with limitations and unexecuted gates;
- push, then read the remote head back.

GitHub is a code and knowledge distribution channel. It is not the source evidence store, primary database, backup target, or owner-approval system.
