# Notion state audit — M2Radar / Content Engine Tool

Read-only pass. Nothing in Notion was created, updated, moved, or deleted during this audit.
Date: 2026-09-11. Workspace: **Ai Ag Automation** (`89e0bd21-ed6a-81d8-b6e8-0003e21b0a2d`), user `mishaampl@gmail.com`.

Method: Notion MCP (`notion-fetch`, `notion-search`, `notion-ai-search`, `notion-query-data-sources`)
for everything in Notion; `ssh m2vps` for the server's env var **names only** (values were never
read or displayed, per the standing rule on `.env` contents); a read-only `python3 notion.py check`
plus a small ad-hoc read-only script (`GET /databases/{id}`, printing only title + property names,
never the id or token) to confirm what the server's `NOTION_CARDS_DB` / `NOTION_REELS_DB` /
`NOTION_ACCOUNTS_DB` currently resolve to, without ever exposing their literal values.

An earlier, more thorough Notion export already exists at `audit-2026-09-08/notion-raw/` (dated
2026-09-08, INDEX + 21 files). This audit does not repeat that page-by-page dump; it re-verifies
what changed since, cross-checks it against the live server, and adds the one fact that dump
couldn't have (whether the databases the running code actually writes to are the ones on the
dashboard).

---

## 1. Headline finding: two unrelated "Cards / Reels / Accounts" systems live in this workspace

This is the fact the dashboard rebuild has to design around.

| | **Operational** (what `notion.py` / `notion_db.py` write to) | **Analytical / one-off audit** (what the M2 Signal + Studio page links to) |
|---|---|---|
| Cards | `225e60a9-3198-4e3c-a151-b462d20d2e63` — same DB as the other column | **same DB**: `225e60a9-3198-4e3c-a151-b462d20d2e63` |
| Reels | a DB titled plain **"Reels"**, schema = exactly `notion_db.py`'s `reel_props()` fields | `c26c6990-bba9-4ab5-a700-e94bd42e327d` — **"Reels · Signal 2026-09-05 · 2,352 identities"**, totally different schema |
| Accounts | a DB titled plain **"Accounts"**, schema = exactly `notion_db.py`'s `push_accounts()` fields + 2 manual extras | `e45a50d2-a910-47b8-99a0-f2ec9f1a3393` — **"Accounts · Signal 2026-09-05 · 100 accounts"**, totally different schema |
| Built by | the radar's own weekly push (`notion.py push`, `notion_db.py`) | a separate, richer analytical/reconciliation pass (ASR state, Diagnostic z, Wilson intervals — fields that don't exist anywhere in this repo's code) |
| Findable via workspace search? | **No** — title-only search for "Reels"/"Accounts" returns nothing; only reachable via the exact ID stored in the server's `.env` | Yes — linked from the Content Engine Tool dashboard and indexed |

**Cards is the one place these two systems overlap**, and only because the original Cards DB
was trashed on 7 Sep and Max's replacement (`225e60a9…`) was wired back into the same env var —
so today `NOTION_CARDS_DB` and the dashboard's "Cards" both point at the same object. Reels and
Accounts were never reconciled this way: the live pipeline's Reels/Accounts DBs are orphaned from
the dashboard (not linked, not searchable by title), and the dashboard's Reels/Accounts DBs are
a one-time 2,352/100-row analytical export unrelated to the weekly rolling window. A future
dashboard update has to either (a) link the real operational DBs into the visible tree, or
(b) formally retire them in favor of the richer Signal schema and re-point the server's env vars —
this is a decision for Misha/Max, not something to silently pick.

---

## 2. Content Engine Tool (`3d00bd21ed6a800fb0ffda652e539ef1`)

- Icon 📡, parent: **AI Startup Workspace** (workspace root page `8b46efbe-31a4-4dab-8f6e-bd1cc54fc518`).
- `page_last_edited_at`: **2026-09-10T06:05:08Z**.
- No child pages/databases live directly on it besides one **mention-link** to the current release
  page and one **mention-link** to the Cards database (`225e60a9…`) — it is a thin, mostly
  redirecting front door, not a container.
- Structure top to bottom:
  1. "Current release · 7 September 2026" — pointer to the M2 Signal + Studio release page, a note
     that the ten shooting plans live in the Cards DB, and corpus stats (2,352 Reels / 100 named
     accounts / 1,062 non-empty transcripts / 18 deep-reviewed references).
  2. Explicit **staleness warning**, written into the page itself: *"The older 14-day tables and
     scoring descriptions below are retained as historical material. Their former winner,
     reliability and consistency claims are not accepted evidence... Server scheduling has not been
     deployed or verified by this run."* — this is the page telling its own reader not to trust the
     section below at face value.
  3. "How a week runs" — a table of the pipeline's 7 steps + cost (~$2/run for the pull, everything
     else free, ~20 min human time). Correctly describes the intended Monday/Thursday cadence.
  4. "What lands here" — one-paragraph description of each of Cards / Reels / Accounts as concepts
     (not links to the operational ones — the reader has to already know they're separate).
  5. "Numbers behind the picks" — live rolling-window analytics: **snapshot 2026-09-10, 14-day
     window, 677 reels across 114 accounts**. Top-10 tables by Score, by Shares/1k, by Saves/1k, by
     multiple-of-own-norm; top accounts by shares/1k, saves/1k, hit rate, median views; a
     week-over-week topic-drift table.
- **What's stale**: the whole "How a week runs"/"Numbers behind the picks" section is the *old*
  simple local-SQLite radar output (677 reels/114 accounts, a completely different number from the
  2,352/100 "Signal" corpus one section above it references) — the page itself flags this ("retained
  as historical material... not accepted evidence"). This is the strongest signal that the page
  needs a real edit pass, not just a new link glued on top: it currently presents two different,
  contradictory pictures of "how many reels are in scope" without reconciling them for the reader.

## 3. M2 Signal + Studio · 7 September · ten-card release (`3d20bd21ed6a813a9a4cd8f51a28af71`)

- Parent: Content Engine Tool. `page_last_edited_at`: **2026-09-11T12:45:46Z** (edited again today,
  three days after "7 September" in its own title — this is a live-growing audit ledger, not a
  frozen release note).
- This is the big page (~59KB fetched, way past what the fetch tool would inline — saved to a local
  temp file and read in chunks). Roughly 30 `##` sections; the useful ones for IA purposes:
  - **What the research means for M2 · 8 September** — editorial conclusion, which cards to start
    with.
  - **Eight proposed scripts · current slate** / card list.
  - **What is covered** — the 2,352/100/1,062/18 corpus numbers, with the 3 databases embedded as
    real `<database>` blocks: Cards (`225e60a9…`), Reels-Signal (`c26c6990…`), Accounts-Signal
    (`e45a50d2…`), plus an inline database for something else on the page (`3d20bd21ed6a8138…`,
    not investigated further — out of scope for this pass).
  - **Partner operator handoff · active Cards target** — the single most operationally important
    paragraph on the page, quoted in full because it's the ground truth for env-var state:
    > "The current ten cards live in [Cards · 10 reviewed shooting plans · 7 September]. The
    > earlier Cards database is deleted; do not reuse its target. Before wrapper writeback, set
    > `NOTION_CARDS_DB=225e60a9-3198-4e3c-a151-b462d20d2e63` in the partner server environment. The
    > active data source is `0a53ec84-08f1-4e05-b96b-f7a579b9b060`. **Reels and Accounts targets
    > remain unchanged.** Credentials must stay in environment injection. This release did not
    > change the partner server environment or deploy..."

    This confirms directly: only Cards was swapped; Reels/Accounts env vars were deliberately left
    alone by whoever wrote this. It also confirms (see §5) that this instruction was in fact
    followed — the server's `NOTION_CARDS_DB` today does resolve to exactly this database.
  - A long trailing **audit/execution ledger** — "Recovery checkpoint · 6 September, 20/21/22",
    "Handoff checkpoint · 7 September, 08", "Continuation operation ledger", GitHub commit
    references (`mcharniuk1-spec/m2lab-radar` fork and `MickaelAmpl/m2lab-radar` "Latest" branch,
    both at commit `4b771f7`), and a long list of **unresolved CSV/JSON/MD/HTML attachments**
    (`m2-full-snapshot.part-*.csv`, `full2352-reels.csv`, `full100-named-accounts-plus-unknown.csv`,
    `field-dictionary.json`, `dashboard.html`, etc.) — Notion's `fetch` tool cannot resolve these to
    downloadable URLs (they come back as `file://{"source":"attachment:<uuid>:<filename>",...}`,
    and `notion-download-attachment` only serves attachments uploaded by *this* integration, not
    pre-existing ones). This matches exactly what `audit-2026-09-08/notion-raw/INDEX.md` already
    documented as Gap #1 — still unresolved three days later, still the same limitation.

**How the 10 cards are represented**: not as page content on the release page — as rows in the
Cards database (`225e60a9…`, data source `0a53ec84-08f1-4e05-b96b-f7a579b9b060`), each row a full
subpage (M2-I01..I05, M2-P01..P05 — captured in full in `audit-2026-09-08/notion-raw/10-19*.md`).
Card schema below (§4).

**Reusable as information architecture**: the three-tier shape — *release page → embedded
databases (Cards/Reels/Accounts) → per-row subpages* — is sound and worth keeping. What's not
reusable as-is: the release page mixes a stable "current state" section with an ever-growing raw
execution ledger on the same page. A rebuilt dashboard should split those — one page for "what's
true now" (short, gets overwritten each run) and one archived/collapsed page or child for the
ledger (append-only, never the thing a reader opens first).

## 4. Databases — full inventory

All three below are **live, not archived/trashed** (confirmed by direct `notion-fetch` and SQL
`COUNT(*)` today, 2026-09-11). Row counts are unchanged from the 2026-09-08 audit — nothing has
been pushed to them since.

### 4.1 Cards · 10 reviewed shooting plans · 7 September
- ID: `225e60a9-3198-4e3c-a151-b462d20d2e63` · data source `0a53ec84-08f1-4e05-b96b-f7a579b9b060`
- Parent: M2 Signal + Studio release page. Row count: **10**. Not archived.
- Properties: `Name` (title), `Author` (text), `Format` (select: M2 Radar / M2 Builds / M2
  Teardown), `Lead` (select: Max / Misha / Both / Макс / Миша — note the mixed EN/RU option set),
  `Priority` (number), `Publication group` (select: Introduction / Regular), `Reference` (url),
  `Scenes` (number), `Signal` (text), `Source Reels` (relation → Reels-Signal data source), `Spoken
  words` (number), `Status` (select: Proposed / Taking / Rework / Not taking / Shot / Published),
  `Synthesis` (checkbox), `Vs author norm` (number), `Week` (date), `Age at pickup` (number).
- Views: "All ten reviewed shooting plans" (table, sorted by Name), "Introduction · five shooting
  cards" (filtered), "Regular · five shooting cards" (filtered).
- **This is a superset of what `notion.py push()`/`pull()` write/read** (Name, Week, Format,
  Priority, Reference, Author, Signal, Vs author norm, Age at pickup, Lead, Status) — the extra
  fields (Planned seconds — actually named "Scenes"/"Spoken words"/"Publication group"/"Source
  Reels"/"Synthesis") were added by whoever rebuilt it and are simply never touched by the script.
  Confirmed live via `notion.py check` today: `NOTION_CARDS_DB` on the server resolves to a
  database titled "Cards" with exactly this property set.

### 4.2 Reels · Signal 2026-09-05 · 2,352 identities
- ID: `c26c6990-bba9-4ab5-a700-e94bd42e327d` · data source `accf47da-7ef3-4620-bc35-2de11170560b`
- Parent: M2 Signal + Studio release page. Row count: **2,352**. Not archived.
- 38 properties — title `Name`, plus `Account`, `Source`, `Published UTC`, `Snapshot`, `Release`,
  `Seconds`, `Views`, `Likes`, `Comments`, `Reshares`, `Saves`, four "per 1k views" rate columns,
  `View index`, `Baseline n`, `Components`, `Diagnostic z`, `Eligibility`, `Quarantine`, `Final
  Best`, `Best reason`, `ASR state`, `Video transcript`, `Transcript` (legacy), `Transcript
  language`, `Legacy ASR reported words`, `Lexical text words`, `Text evidence`, `Text review`,
  `Text fit candidate`, `Opening candidate`, `Topic indicators`, `Frames`, `Frame observation`,
  `Sample visual review`, `Source function`, `Save state`.
- Views: "18 script references · dated evidence", "18 references · processing and transcript
  checks" — both filtered to the same 18 hand-picked Reel IDs behind the ten cards.
- **Not the same database as the server's `NOTION_REELS_DB`** — see §5.

### 4.3 Accounts · Signal 2026-09-05 · 100 accounts
- ID: `e45a50d2-a910-47b8-99a0-f2ec9f1a3393` · data source `28d920a4-26b1-4b79-906f-79504e5e7b48`
- Parent: M2 Signal + Studio release page. Row count: **100**. Not archived.
- 20 properties — title `Name`, plus `Release`, `Snapshot`, `Followers at export`, `Reels`,
  `Observations`, `Eligible`, `Eligible transcript records`, `Eligible frame sets`, `Median views`,
  `Baseline n`, `Hit count`, `Hit denominator`, `Hit fraction`, `Hit state`, `Wilson lower`, `Wilson
  upper`, `Final Best`, `Best reason`, `Review candidate`.
- View: "15 accounts behind script references" (filtered).
- **Not the same database as the server's `NOTION_ACCOUNTS_DB`** — see §5.

### 4.4 Operational "Reels" and "Accounts" (the ones the server actually writes to)
- Not found by title search or AI search in this workspace under this integration/user session —
  either not shared with this MCP connection, or created directly via the "M2 Lab Radar" bot
  integration's API access and never linked into any page tree, so nothing points at them and
  nothing indexes them. Their IDs were deliberately **not** extracted in this audit (see method
  note above); confirmed to exist and resolve correctly only via a read-only `GET` from the server
  itself.
- **Reels** — properties (37): `Reel` (title), `Author`, `URL`, `Posted`, `Age days`, `Views`,
  `Likes`, `Comments`, `Shares`, `Saves`, `Shares 1k`, `Saves 1k`, `Comments 1k`, `Score`, `Vs own
  norm`, `Axes`, `Baseline`, `Duration s`, `Cuts per s`, `One take`, `Transcript words`, `Hook
  words`, `Body words`, `Ending words`, `Words per min`, `Topics`, `Comment bait`, `DM promise`,
  `Money claim`, `Caption question`, `Caption number`, `Hook question`, `Hook number`, `Hook you`,
  `Hook claim`, `Analysed`, `Usable`, `Picked as card`, `Caption` — an exact match to
  `notion_db.py`'s `reel_props()`.
- **Accounts** — properties (21): `Account` (title), `Followers`, `Posts total`, `Category`, `Bio`,
  `In our set`, `Status`, `Reels in window`, `Median views`, `Median shares 1k`, `Median saves 1k`,
  `Hit rate`, `Median duration`, `Median cuts per s`, `One take share`, `Comment bait share`,
  `Topics`, `Best reel`, `Best reel score`, `Signature moves` — an exact match to
  `notion_db.py`'s `push_accounts()`, **plus two fields the script never writes**: `Verdict` and
  `What to borrow` — someone (Misha or Max) added these by hand directly in Notion, i.e. there is
  already a manual human-annotation layer on this database that a schema rebuild must not clobber.
- Row counts unknown (couldn't query without the ID, and deliberately didn't fetch it by ID to
  avoid needing the env var value). Given `cron.sh` (see §5) never calls `notion_db.py`, these
  are very likely last populated whenever someone last ran `python3 notion_db.py both` by hand —
  worth asking Misha/Max when that last was.

### 4.5 Other databases seen, not part of this system
- `3d20bd21ed6a8138bb38f30722081101` — an inline database embedded further down the M2 Signal +
  Studio page, not investigated (out of the requested scope; flag if it turns out relevant).
- "M2 Kanban" (inline, on the standalone "M2 — Signal-to-Studio Bootstrap Execution Review" page,
  `3c70bd21ed6a81049f12f0f9c1cdc945`) and four "North Hux" databases (on "North Hux M2 Market
  Intelligence — Control Dashboard", `3c70bd21ed6a811a8d9fc1f8312cd8fa`) — both already flagged as
  not dumped in the 08-09 audit; still not investigated here, both live under the older, separate
  **"Content Engine"** page tree (see §6), not "Content Engine Tool".

## 5. Which database IDs the server actually uses

`notion.py` (`push`/`pull` for Cards) and `notion_db.py` (`push_reels`/`push_accounts`) read
`NOTION_TOKEN`, `NOTION_CARDS_DB`, `NOTION_REELS_DB`, `NOTION_ACCOUNTS_DB`, `NOTION_PAGE` from
`.env` via a shared `env()` helper (`notion.py:22-31`), never hard-coded.

Server env var **names** (`ssh m2vps "sed -E 's/=.*/=<redacted>/' /opt/radar/.env"`):
```
HIKER_KEY=<redacted>
NOTION_CARDS_DB=<redacted>
NOTION_PAGE=<redacted>
NOTION_TOKEN=<redacted>
NOTION_REELS_DB=<redacted>
NOTION_ACCOUNTS_DB=<redacted>
```
No new or renamed variables since the 08-09 audit; matches exactly what `notion.py`/`notion_db.py`
expect.

Read-only resolution check (server-side, `notion.py check` plus one throwaway script — both print
only title/property names, never the id or token):
- `NOTION_CARDS_DB` → resolves to a database titled **"Cards"** with the exact property set of
  §4.1 → **confirmed to be `225e60a9-3198-4e3c-a151-b462d20d2e63`**, i.e. the "operator handoff"
  instruction quoted in §3 was in fact carried out on the server.
- `NOTION_REELS_DB` → resolves to a database titled **"Reels"**, schema matches `reel_props()`
  exactly → **this is not** `c26c6990…` (property names don't overlap at all beyond generic ones
  like Views/Likes; the Signal DB's title property is `Name`, not `Reel`). A push from
  `notion_db.py` today would succeed against whatever this is, and would do nothing to the Signal
  Reels DB the dashboard shows.
- `NOTION_ACCOUNTS_DB` → resolves to a database titled **"Accounts"**, schema matches
  `push_accounts()` exactly (+ the two manual fields) → same conclusion, not `e45a50d2…`.

**Server scheduling**: contrary to the Content Engine Tool page's own disclaimer ("Server
scheduling has not been deployed or verified by this run"), the crontab on `m2vps` does have it:
```
0 7 * * 1,4 /opt/radar/cron.sh
```
Monday and Thursday, 07:00 — matches the intended cadence described on the dashboard. Reading
`cron.sh`: it does `git pull`, `run.py --yes` (collect → score → analyze → cards), then, only if
that succeeded, runs a Claude agent to write angles and **`notion.py push` — Cards only**. It
never calls `notion_db.py`. So the operational Reels/Accounts Notion databases are not part of the
automated weekly cycle at all today; they only get updated by a manual `python3 notion_db.py both`.
Local `data/`/`cache/` timestamps on the server (`niche.html`, `radar.html`, `shoot.html` all dated
Sep 10 08:08) confirm the weekly run itself has been executing.

## 6. Legacy pages worth a "Legacy" label

Found via `notion-ai-search`, not requested by name but surfaced while searching for "Cards" /
"Reels" / "Accounts" — two duplicate stub pages, both already self-marked as disposable by
whoever left them:

- **🗑️ M2 Lab — Radar** (`3d00bd21-ed6a-81cb-abdf-d7d0eef5497c`) — no parent (orphaned at
  workspace root). Full content: *"The radar now lives on the page in AI Startup Workspace. This
  one and the other leftover under Content Engine can both be deleted."* Last edited
  2026-09-03.
- **🗑️ M2 Lab — Radar** (`3d00bd21-ed6a-8165-b1f4-d3520940b65a`) — parent: **AI Startup Workspace /
  Content Engine** (the *other*, older Content Engine page tree, not Content Engine Tool). Full
  content: *"Moved. The radar now lives on its own page — this one can be deleted."* Last edited
  2026-09-03.

Both are exactly the kind of thing this task's brief asks to flag with a **Legacy** label rather
than delete outright — the page text itself already says "can be deleted," but per this audit's
read-only scope and the standing rule against destructive Notion actions, no action was taken;
this is a recommendation for Misha/Max to action by hand or explicitly approve.

Also structurally separate and out of scope for this pass, but visible in the same search sweep:
an entire older **"Content Engine"** page tree (`3b90bd21ed6a80edb676ce709d5ffb78`, last touched
around 2026-08-11/08-25) with its own Jira-style task pages (`CE-P1-*`, `CE-M2-10`), the "M2 —
Signal-to-Studio Bootstrap Execution Review" page, and the "North Hux M2 Market Intelligence —
Control Dashboard" page + its 4 databases. This looks like the predecessor workspace structure that
"Content Engine Tool" superseded; worth a deliberate decision (archive under Legacy vs. keep) but
not touched or further inventoried here.

## 7. Notion MCP constraints observed

- **Full Notion MCP is enabled** for this connection (confirmed via `notion-fetch id=self`):
  `search`, `ai_search`, `fetch`, `create_pages`, `update_page`, `create_database`,
  `update_data_source`, `create_view`, `move_pages`, `duplicate_page`, `create_folder`,
  `update_folder`, `create_comment`/`get_comments`, `query_data_sources`,
  `query_multiple_data_sources`, `get_teams`/`get_users`, list-recent/private/shared/favorite pages
  are all `"available"`. Only `download_skill` is `not_enabled`. No paid/full-version upsell was
  triggered.
- **Search**: `ai_search` (semantic, natural-language, ≤~50 words) is the preferred tool per the
  server's own instructions since its status is "available" — plain `notion-search` still works
  and supports `title_only`/`content_status` filters (useful for exact-title lookups, which
  `ai_search` is worse at — it kept surfacing content-relevance matches instead of the literal
  "Reels"/"Accounts" titles).
- **Large pages**: `notion-fetch` on the M2 Signal + Studio page (~59K characters) exceeded the
  inline token budget and was auto-saved to a local file for chunked reading — expect this for any
  page with a long accumulated audit ledger; budget for it when rebuilding (keep the "current
  state" page short and separate from the ledger, per §3).
- **Attachments**: pre-existing file attachments (CSVs, JSON, HTML dashboards) on a page resolve to
  unusable `attachment:<uuid>` references, not downloadable URLs; `notion-download-attachment`
  only serves attachments *this* integration uploaded via `create-attachment`. There is no
  workaround via MCP — this is a hard limitation, already documented once in
  `audit-2026-09-08/notion-raw/INDEX.md` and reconfirmed here.
- **Row enumeration**: `query_data_sources` in `rows` mode caps at 100 rows/call (paginate via
  cursor); `sql` mode has no such cap and is the right tool for counts/aggregates (used here for
  the three row counts). Both were available without hitting a plan-based quota message this
  session.
- Write tools relevant to a rebuild, with their required arguments:
  - `notion-create-pages` — `pages[]` (each with `properties`/`content`/optional `template_id`),
    `parent` (`page_id` / `database_id` / `data_source_id`) or `creation_mode: "draft"`.
  - `notion-update-page` — `page_id`, `command` (`update_properties` / `update_content` /
    `replace_content` / `insert_content` / `apply_template` / `update_verification`) + the
    matching payload field.
  - `notion-create-database` — either `schema` (SQL DDL `CREATE TABLE`) or `database_type`
    (`tasks`/`projects`/`skills`), optional `parent.page_id`.
  - `notion-update-data-source` — `data_source_id` + `statements` (SQL DDL `ADD/DROP/RENAME/ALTER
    COLUMN`), or `title`/`description`/`is_inline`/`in_trash`.
  - `notion-create-view` — `data_source_id`, `name`, `type` (table/board/list/calendar/timeline/
    gallery/form/chart/map/dashboard), one of `database_id` or `parent_page_id`, optional
    `configure` DSL for filters/sorts/grouping.

## 8. Recommended plan for the dashboard rebuild

This is a recommendation, not an action — nothing below was executed.

1. **Decide the Reels/Accounts split first, before touching any page.** Two real options:
   - (a) Re-point the server's `NOTION_REELS_DB`/`NOTION_ACCOUNTS_DB` at the Signal databases
     (`c26c6990…`/`e45a50d2…`) and rewrite `notion_db.py`'s property mapping to match their richer
     schema — folds the two systems into one, but means writing real migration code and deciding
     what happens to the two manual `Verdict`/`What to borrow` values already sitting in the old
     Accounts DB (they'd need to be copied over by hand, since notion_db.py doesn't read them back).
   - (b) Keep them separate on purpose: link the *existing* operational Reels/Accounts databases
     into the visible page tree (as inline linked views under Content Engine Tool, via
     `notion-create-view` with `parent_page_id`) so they're at least navigable, and relabel the
     Signal ones clearly as "one-off audit corpus, 2026-09-05 snapshot — not live" so nobody mistakes
     them for the rolling window.
   Either way, this is Misha/Max's call, not a default to pick silently — flag it as an open question.
2. **Reuse, don't recreate, Cards.** `225e60a9…` is already correctly wired end-to-end (server →
   Notion → dashboard). Leave it as the single Cards source of truth.
3. **Split the M2 Signal + Studio page.** Move the growing "Recovery/Handoff/Continuation" ledger
   sections into a child page (e.g. "M2 Signal + Studio — execution ledger", `is_skill: false`,
   plain page) reachable from, but not the first thing shown on, the release page. Keep the release
   page itself down to: editorial conclusion, which cards to start with, the 3 embedded databases,
   and the "Partner operator handoff" paragraph (that one's load-bearing — don't bury it).
4. **Fix the Content Engine Tool page's internal contradiction** (§2): either drop the stale
   677-reels/114-accounts local-SQLite section entirely, or clearly date/label it as "previous
   scoring run, superseded by the 2,352-Reel Signal corpus" so a reader doesn't have to guess which
   number is current.
5. **Label, don't delete, the two orphan "M2 Lab — Radar" stub pages** (§6) and the older
   "Content Engine" tree — add a "Legacy" tag/prefix and, if there's a home for it, move them under
   an explicit `Legacy` or `Archive` parent page rather than leaving them floating at odd places in
   the tree. Deletion needs Misha's explicit sign-off per the standing red-zone rule on Notion
   changes.
6. **Attachments**: don't rely on Notion attachments for the CSV/JSON/HTML exports going forward —
   MCP can't read them back reliably. If the dashboard needs to link to raw exports, host them
   somewhere fetchable (repo, S3, etc.) and link by URL instead of uploading as page attachments.
