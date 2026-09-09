# Accounts · Signal 2026-09-05 · 100 accounts (database schema + views)

- Notion URL: https://app.notion.com/p/e45a50d2a91047b899a0f2ec9f1a3393
- Page path: AI Startup Workspace / Content Engine Tool / M2 Signal + Studio · 7 September · ten-card release
- Last edited: not reported by fetch (database object)

Note: this is the full 100-account database referenced from "Accounts · coverage and comparison · 7 September" (file 05). Bulk relational data — rows not dumped here, only schema and the one configured view (15 accounts behind the script references). Individual account sub-pages (e.g. joestoltelive, alliekmiller, hamza_automates — each with their own reviewed Reel samples) exist as children of this database but were not separately fetched in this pass; they are linked from the "Why these references" sections of the M2-I/M2-P cards (files 10-19). Full row data lives in the full100-named-accounts-plus-unknown.csv attachment, which could not be downloaded in this pass — see the attachment-resolution note in 04-reels-transcripts-references-analysis.md.

---

<database url="{{https://app.notion.com/p/e45a50d2a91047b899a0f2ec9f1a3393}}" inline="false">
Title: Accounts · Signal 2026-09-05 · 100 accounts
<ancestor-path>
<parent-page url="https://app.notion.com/p/3d20bd21ed6a813a9a4cd8f51a28af71" title="M2 Signal + Studio · 7 September · ten-card release"/>
<ancestor-2-page url="https://app.notion.com/p/3d00bd21ed6a800fb0ffda652e539ef1" title="Content Engine Tool"/>
<ancestor-3-page url="https://app.notion.com/p/8b46efbe31a44dab8f6ebd1cc54fc518" title="AI Startup Workspace"/>
</ancestor-path>

Data source: collection://28d920a4-26b1-4b79-906f-79504e5e7b48

Schema fields (name — type — description):
- Name (title) — stable account username/title.
- Release (text) — Signal release identifier.
- Snapshot (text) — metric snapshot date.
- Followers at export (number) — profile follower counter at export time.
- Reels (number) — number of Reel rows associated with the account.
- Observations (number) — number of source observations associated with the account.
- Eligible (number) — number of eligible Reel rows for the account.
- Eligible transcript records (number) — count of eligible Reels with transcript evidence.
- Eligible frame sets (number) — count of eligible frame sets associated with the account.
- Median views (number) — account median Reel views used by the author baseline.
- Baseline n (number) — number of account rows included in the baseline.
- Hit count / Hit denominator / Hit fraction (number) — release diagnostic hit rule counts and ratio; Hit fraction null when denominator is zero/unknown or Hit state=INSUFFICIENT_N.
- Hit state (text) — whether account hit statistics are interpretable.
- Wilson lower / Wilson upper (number) — Wilson binomial interval bounds for Hit fraction; null under the same INSUFFICIENT_N gate.
- Final Best (text) — account-level Final-Best decision state; UNKNOWN means unresolved gate.
- Best reason (text) — account-level Best gate reason.
- Review candidate (url) — local/projection review candidate link.

SQLite table definition (verbatim):
```
CREATE TABLE IF NOT EXISTS "collection://28d920a4-26b1-4b79-906f-79504e5e7b48" (
	url TEXT UNIQUE,
	createdTime TEXT,
	"Median views" FLOAT,
	"Observations" FLOAT,
	"Reels" FLOAT,
	"Eligible frame sets" FLOAT,
	"Hit count" FLOAT,
	"Release" TEXT,
	"Best reason" TEXT,
	"Review candidate" TEXT,
	"Baseline n" FLOAT,
	"Wilson lower" FLOAT,
	"Final Best" TEXT,
	"Hit denominator" FLOAT,
	"Wilson upper" FLOAT,
	"Hit state" TEXT,
	"Eligible transcript records" FLOAT,
	"Followers at export" FLOAT,
	"Eligible" FLOAT,
	"Snapshot" TEXT,
	"Hit fraction" FLOAT,
	"Name" TEXT
)
```

Configured view:
"15 accounts behind script references" — filtered to: alliekmiller, benjamlns, bennett.spooner, builders.central, divyannshisharma, hamza_automates, heystevetan, jasoncooperson, joestoltelive, kevinfremon, lukebuildsai, olivermerrick___, raycfu, realrileybrown, rence_ur_hands. Displayed columns: Name, Reels, Eligible, Median views, Eligible transcript records, Eligible frame sets, Final Best.

Row-level data (100 accounts) was not enumerated — out of scope for this pass; use the full100-named-accounts-plus-unknown.csv attachment (unresolvable in this session, see note above).
</database>
