# Reels · Signal 2026-09-05 · 2,352 identities (database schema + views)

- Notion URL: https://app.notion.com/p/c26c6990bba94ab5a700e94bd42e327d
- Page path: AI Startup Workspace / Content Engine Tool / M2 Signal + Studio · 7 September · ten-card release
- Last edited: not reported by fetch (database object)

Note: this is the full 2,352-row Reels database referenced from "Reels · transcripts, references and analysis · 7 September" (file 04). It is bulk relational data (2,352 individual Reel rows, many with full machine transcripts) — the rows themselves are NOT dumped here, only the schema/field definitions and the two configured views (the 18-reference focused view, and an 18-reference processing/transcript-check view). Full row data lives in the CSV attachments referenced in file 01/04 (full2352-reels.csv), which could not be downloaded in this pass — see the attachment-resolution note in 04-reels-transcripts-references-analysis.md.

---

<database url="{{https://app.notion.com/p/c26c6990bba94ab5a700e94bd42e327d}}" inline="false">
Title: Reels · Signal 2026-09-05 · 2,352 identities
<ancestor-path>
<parent-page url="https://app.notion.com/p/3d20bd21ed6a813a9a4cd8f51a28af71" title="M2 Signal + Studio · 7 September · ten-card release"/>
<ancestor-2-page url="https://app.notion.com/p/3d00bd21ed6a800fb0ffda652e539ef1" title="Content Engine Tool"/>
<ancestor-3-page url="https://app.notion.com/p/8b46efbe31a44dab8f6ebd1cc54fc518" title="AI Startup Workspace"/>
</ancestor-path>

Data source: collection://accf47da-7ef3-4620-bc35-2de11170560b

Schema fields (name — type — description):
- Name (title) — Stable Reel code/title used as the projection identity.
- Account (text) — Source account username.
- Source (url) — Canonical public Reel URL captured in the export.
- Published UTC (text) — Source publication timestamp (UTC ISO).
- Snapshot (text) — Date associated with the source metric snapshot.
- Release (text) — Signal release identifier bound to this row.
- Seconds (number) — Source duration of the Reel.
- Views (number) — Observed play/view counter; null is unknown, not zero.
- Likes / Comments / Reshares / Saves (number) — observed counters; null is unknown, not zero (Saves has an explicit Save state field: MISSING vs OBSERVED-including-zero).
- Likes per 1k views / Comments per 1k views / Reshares per 1k views / Saves per 1k views (number) — rate normalized to Views; null when Views<=0, counter unavailable, or eligibility/numeric/quarantine gates suppress it; zero means observed zero with valid positive Views.
- View index (number) — Views relative to the account baseline median (Views / account median views).
- Baseline n (number) — number of account rows used to form the author baseline.
- Components (number) — count (0-5) of robust-z scores for log1p(Views) and the four action rates after eligibility/baseline-support gates.
- Diagnostic z (number) — equal-weight robust diagnostic across available component rates.
- Eligibility (text) — numeric/exposure eligibility gate PASS/FAIL/Unknown.
- Quarantine (text) — conflict/impossibility reason quarantining a row or field.
- Final Best (text) — Final-Best decision enum; UNKNOWN means unresolved, not false.
- Best reason (text) — reason code for the Final Best gate state.
- ASR state (text) — OBSERVED, SUSPICIOUS_TIMINGS, ASR_FAILED, EMPTY_OUTPUT_UNVERIFIED, NOT_ATTEMPTED.
- Video transcript (text) — full primary machine ASR text where available; empty means no usable transcript (check ASR state).
- Transcript (text) — legacy mixed field retained for lineage; prefer Video transcript + ASR state.
- Transcript language (text) — machine language label, no manual accuracy claim.
- Legacy ASR reported words (number) — source-ASR reported word count (not recomputed).
- Lexical text words (number) — lexical word count projected from transcript analysis.
- Text evidence (text) — reference to the local transcript-analysis record.
- Text review (text) — review state for transcript text coding.
- Text fit candidate (text) — maker-coded M2 relevance candidate: core/adjacent/excluded/unknown.
- Opening candidate (text) — maker-coded opening/hook orientation candidate.
- Topic indicators (text) — English keyword-pattern counts over available machine text; overlapping indicators, not validated topics.
- Frames (text) — frame/source-media evidence state enum.
- Frame observation (text) — frame attempt/observation state enum.
- Sample visual review (text) — bounded review state + contact-sheet sample count for the 18 selected references only.
- Source function (text) — reviewed rhetorical-function interpretation for the 18 selected references; empty means not deeply reviewed.

SQLite table definition (verbatim):
```
CREATE TABLE IF NOT EXISTS "collection://accf47da-7ef3-4620-bc35-2de11170560b" (
	url TEXT UNIQUE,
	createdTime TEXT,
	"Saves per 1k views" FLOAT,
	"ASR state" TEXT,
	"Text fit candidate" TEXT,
	"Reshares" FLOAT,
	"Text evidence" TEXT,
	"Source" TEXT,
	"Comments" FLOAT,
	"Opening candidate" TEXT,
	"Likes" FLOAT,
	"Snapshot" TEXT,
	"Published UTC" TEXT,
	"Quarantine" TEXT,
	"Frame observation" TEXT,
	"Comments per 1k views" FLOAT,
	"Sample visual review" TEXT,
	"Baseline n" FLOAT,
	"Best reason" TEXT,
	"Legacy ASR reported words" FLOAT,
	"Release" TEXT,
	"Likes per 1k views" FLOAT,
	"Topic indicators" TEXT,
	"Eligibility" TEXT,
	"Frames" TEXT,
	"Transcript language" TEXT,
	"Lexical text words" FLOAT,
	"Save state" TEXT,
	"Reshares per 1k views" FLOAT,
	"Source function" TEXT,
	"Video transcript" TEXT,
	"Views" FLOAT,
	"Account" TEXT,
	"Seconds" FLOAT,
	"Components" FLOAT,
	"Saves" FLOAT,
	"Final Best" TEXT,
	"Diagnostic z" FLOAT,
	"View index" FLOAT,
	"Text review" TEXT,
	"Transcript" TEXT,
	"Name" TEXT
)
```

Configured views:
1. "18 script references · dated evidence" — filtered to the 18 named Reel IDs used across the M2-I/M2-P cards (C6p0q0SuyZb, C8hVLXpOMrt, DU7c4LOmRXX, DYC4nrEEfI1, DYzfRxHipT_, DZ5H6F1Rz1S, DZArzOwilIl, DZfn7aQRapu, DZgEMj9jBMy, DZisJCRzqXD, Da3SnoUT2Go, Daziw8ExFew, Db7GyVlPmqP, DbQEioCyk_H, Dbdk08yyHqS, DbgM7GFTJDT, DbkzHQbSBkJ, DbnvmVAz06O), sorted by View index descending. Displayed columns: Name, Account, Views, View index, Baseline n, Video transcript, ASR state, Transcript language, Source function, Sample visual review, Final Best.
2. "18 references · processing and transcript checks" — same 18-row filter. Displayed columns: Name, ASR state, Video transcript, Topic indicators, Text review, Frame observation.

Row-level data was not enumerated (2,352 rows; out of scope for this pass — use the full2352-reels.csv attachment, which the fetch tool could not resolve to a downloadable URL in this session).
</database>
