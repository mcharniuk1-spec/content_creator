#!/usr/bin/env python3
"""Execution kanban + execution review in Notion (requested by Max, 2026-09-13).

Creates, idempotently, two things under the Content Engine Tool dashboard page:

  1. the database **Execution Kanban** — one row per key task from `engine/kanban_tasks.py`,
     with Block / Stage / Status / Owner / Evidence / Note, plus one row per pipeline stage of
     `engine.state.STAGES` carrying the live job counts from the database this runs against;
  2. the page **Execution Review** — a written overview per block: what was built and why
     (argumentation), what the execution showed (review), and the plan.

Status columns make the Notion "board" view a kanban; the row order property keeps the
list view in reading order. Everything is English by construction (the tests refuse
non-ASCII letters in the task file).

    python3 -m engine.notion_kanban --dry            # print the rows and the review, no network
    python3 -m engine.notion_kanban --apply          # create/update in Notion (needs NOTION_TOKEN)

Idempotency: database and page ids are cached in data/notion_ids.json (IdCache); rows are
upserted by their `key` (the title property). Re-running rewrites the review page body and
patches every row; nothing is duplicated.
"""
import argparse, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import db_util, state                    # noqa: E402
from engine import notion_blocks as nb              # noqa: E402
from engine import notion_sync as ns                # noqa: E402
from engine.kanban_tasks import TASKS, BLOCKS, STATUSES, OWNERS, CROSS_STAGES   # noqa: E402

KANBAN_TITLE = 'Execution Kanban'
REVIEW_TITLE = 'Execution Review'
STAGE_CHOICES = tuple(state.STAGES) + CROSS_STAGES

KANBAN_SCHEMA = {
    'Task': {'title': {}},
    'Block': ns._select(*BLOCKS),
    'Stage': ns._select(*STAGE_CHOICES),
    'Status': ns._select(*STATUSES),
    'Owner': ns._select(*OWNERS),
    'Evidence': {'rich_text': {}},
    'Note': {'rich_text': {}},
    'Order': {'number': {}},
    'Updated': {'date': {}},
}


# ---------------------------------------------------------------------------- data
def _count(con, sql, default=0):
    try:
        return con.execute(sql).fetchone()[0] or 0
    except Exception:
        return default


def live_numbers(con):
    """Counts read from the database at apply time; every `{placeholder}` in
    kanban_tasks.TASKS evidence strings resolves against this dict."""
    def files(sub):
        d = ROOT / 'data' / 'analysis' / sub
        return len(list(d.glob('*.json'))) if d.exists() else 0
    n = {
        'n_ingested': _count(con, 'SELECT COUNT(DISTINCT code) FROM reels'),
        'n_transcripts': _count(con, 'SELECT COUNT(*) FROM transcripts'),
        'n_frames': _count(con, 'SELECT COUNT(DISTINCT code) FROM frames'),
        'n_beats': _count(con, 'SELECT COUNT(*) FROM beats'),
        'n_scenes': _count(con, 'SELECT COUNT(*) FROM scenes'),
        'n_features': _count(con, 'SELECT COUNT(*) FROM video_features'),
        'n_creator_stats': _count(con, 'SELECT COUNT(*) FROM creator_stats'),
        'n_insights': _count(con, 'SELECT COUNT(*) FROM insights'),
        'n_reliable': _count(con, "SELECT COUNT(*) FROM insights WHERE confidence='RELIABLE'"),
        'n_hypotheses': _count(con, 'SELECT COUNT(*) FROM hypotheses'),
        'n_refs': _count(con, 'SELECT COUNT(*) FROM hypothesis_refs'),
        'n_cards': _count(con, 'SELECT COUNT(*) FROM cards_v2'),
        'n_card_scenes': _count(con, 'SELECT COUNT(*) FROM card_scenes'),
        'n_runs': _count(con, 'SELECT COUNT(*) FROM runs'),
        'n_jobs': _count(con, 'SELECT COUNT(*) FROM jobs'),
        'n_jobs_done': _count(con, "SELECT COUNT(*) FROM jobs WHERE state='DONE'"),
        'n_jobs_failed': _count(con, "SELECT COUNT(*) FROM jobs WHERE state='FAILED'"),
        'n_jobs_skipped': _count(con, "SELECT COUNT(*) FROM jobs WHERE state='SKIPPED'"),
        'n_ta': files('transcripts'), 'n_fa': files('frames'),
        'n_categories': 0, 'n_pending': 0,
    }
    try:
        from engine import corpus
        t = corpus.tiers(con)
        n['n_pending'] = t['counts'].get('n_newest_unprocessed', 0)
    except Exception:
        pass
    try:
        cache = ns.IdCache()
        n['n_categories'] = len(cache.data['rows'].get('Categories', {}))
    except Exception:
        pass
    return n


def stage_rows(con):
    """One row per engine stage with live job counts. Stages that have never produced a
    jobs row are Planned; stages with only failures are Blocked."""
    counts = {}
    try:
        for stage, st, c in con.execute('SELECT stage, state, COUNT(*) FROM jobs GROUP BY 1, 2'):
            counts.setdefault(stage, {})[st] = c
    except Exception:
        pass
    last = {}
    try:
        for stage, ts in con.execute('SELECT stage, MAX(finished_at) FROM jobs GROUP BY 1'):
            last[stage] = ts
    except Exception:
        pass
    legacy_done = {'DISCOVERED', 'PROFILE_FETCHED', 'VIDEO_METADATA_FETCHED', 'STATS_FETCHED'}
    rows = []
    for i, stage in enumerate(state.STAGES):
        c = counts.get(stage, {})
        done, failed, skipped = c.get('DONE', 0), c.get('FAILED', 0), c.get('SKIPPED', 0)
        if done:
            status = 'Done' if not failed else 'In progress'
        elif failed:
            status = 'Blocked'
        elif stage in legacy_done:
            status = 'Done'
        else:
            status = 'Planned'
        evidence = (f'jobs: {done} DONE, {failed} FAILED, {skipped} SKIPPED'
                    + (f'; last {last.get(stage)}' if last.get(stage) else ''))
        if stage in legacy_done and not c:
            evidence = 'legacy run.py steps (snapshots, roster, scores) — traced in runs, not per-video jobs'
        rows.append({
            'key': f'stage:{stage}', 'block': 'Infra & ops', 'stage': stage, 'status': status,
            'owner': 'cron' if stage in legacy_done or stage in ('MEDIA_FETCHED', 'TRANSCRIPTION',
                                                                   'FRAME_EXTRACTION', 'ALIGNMENT',
                                                                   'TRANSCRIPT_ANALYSIS',
                                                                   'FRAME_ANALYSIS') else 'Fable',
            'evidence': evidence, 'note': 'Pipeline stage (engine.state.STAGES) — live job counts.',
            'order': 900 + i,
        })
    return rows


def task_rows(numbers):
    rows = []
    for order, key, block, stage, status, owner, evidence, note in TASKS:
        rows.append({'key': key, 'block': block, 'stage': stage, 'status': status, 'owner': owner,
                     'evidence': evidence.format(**numbers), 'note': note, 'order': order})
    return rows


def build_rows(con):
    numbers = live_numbers(con)
    return task_rows(numbers) + stage_rows(con), numbers


def row_properties(row, updated=None):
    return {
        'Task': {'title': nb.rich_text(row['key'])},
        'Block': {'select': {'name': row['block']}},
        'Stage': {'select': {'name': row['stage']}},
        'Status': {'select': {'name': row['status']}},
        'Owner': {'select': {'name': row['owner']}},
        'Evidence': {'rich_text': nb.rich_text(row['evidence'][:1900])},
        'Note': {'rich_text': nb.rich_text(row['note'][:1900])},
        'Order': {'number': row['order']},
        'Updated': {'date': {'start': (updated or db_util.now())[:10]}},
    }


# ---------------------------------------------------------------------------- review page
def review_sections(rows, numbers):
    """The written overview per block: argumentation, execution review, plan. Returns a list
    of (heading, [paragraphs]) in reading order. Numbers come from `numbers` so the text never
    disagrees with the board."""
    n = numbers
    by_block = {}
    for r in rows:
        by_block.setdefault(r['block'], []).append(r)

    def tally(block):
        c = {}
        for r in by_block.get(block, []):
            c[r['status']] = c.get(r['status'], 0) + 1
        return ', '.join(f'{v} {k}' for k, v in sorted(c.items()))

    S = []
    S.append(('How to read this page', [
        "This page and the Execution Kanban database above it are generated by engine/notion_kanban.py "
        "from engine/kanban_tasks.py and from the live database on the server. Each block below says "
        "why it was built the way it was, what the execution showed, and what comes next. Status "
        "counts are read from the board, evidence numbers from data/radar.db. Traceability for any "
        "single reel, insight, hypothesis or card runs through the runs and jobs tables "
        "(docs/HANDOFF_MAX_2026-09-12.md §10.1).",
        f"Corpus at generation time: {n['n_ingested']} unique reels ingested, {n['n_transcripts']} "
        f"transcript rows, {n['n_frames']} reels with frames, {n['n_features']} feature rows, "
        f"{n['n_insights']} insights ({n['n_reliable']} RELIABLE), {n['n_hypotheses']} hypotheses, "
        f"{n['n_cards']} cards v2; {n['n_runs']} runs and {n['n_jobs']} jobs traced "
        f"({n['n_jobs_done']} DONE, {n['n_jobs_failed']} FAILED, {n['n_jobs_skipped']} SKIPPED).",
    ]))
    S.append((f'Data gathering — {tally("Data gathering")}', [
        "Argumentation. The radar already had a working Hiker collection, a roster and a relational "
        "SQLite; the engine was built on top of it rather than beside it (engine/SPEC.md decision 1). "
        "Hiker became a committed provider with price receipts and a config check so the pipeline can "
        "run unattended on the server without the key ever entering git. Transcription and frame "
        "extraction are local-first (faster-whisper, ffmpeg) so the marginal cost of a reel is zero and "
        "the only paid call is the metadata fetch. Media is not retained: the CDN links expire in hours, "
        "so processing happens video-by-video right after collection (engine/local_pipeline.py).",
        f"Execution review. {n['n_ingested']} unique reels are ingested with metrics; {n['n_transcripts']} "
        f"have a transcript row and {n['n_frames']} have frames. The analysis-ready set is the top of the "
        "score.py ranking, not a random sample, which biases every conclusion towards strong-vs-strong "
        "comparisons (insight I-01). The newest snapshot's reels were collected before the local "
        f"pipeline existed, so {n['n_pending']} of them wait for the watchdog after the next collection; "
        "Misha declined a paid re-fetch on 12 Sep, so Monday's free run is the plan. Max's 1,062 "
        "transcripts and 19,808 frames are the largest missing input and depend on his export.",
        "Plan. Monday 2026-09-14 07:00: first scheduled run under the new schema; verify the watchdog "
        "selects from fresh URLs and analyze_pending consumes the batches. Then import Max's corpus "
        "through the stable-id path in the handoff §3.1.",
    ]))
    S.append((f'Analysis — {tally("Analysis")}', [
        "Argumentation. Two LLM contracts (ta-v1 transcripts, fa-v1 frames) with closed vocabularies "
        "keep the semantic layer comparable across batches and models; features and statistics are "
        "computed in code, never by the model, with creator-normalised measures because 115 of 132 "
        "creators are high-variance. Insights carry n, comparison and confidence; hypotheses are scored "
        "on 14 keys before any script is written; references are hypothesis-specific with one function "
        "per reel. This is the data -> analysis -> insight -> hypothesis -> reference -> script chain of the "
        "execution spec, and every step leaves a jobs row.",
        f"Execution review. {n['n_ta']} transcript analyses and {n['n_fa']} frame analyses on disk; "
        f"{n['n_insights']} insights of which {n['n_reliable']} RELIABLE; {n['n_hypotheses']} hypotheses, "
        f"{n['n_refs']} references. Headline findings: no single form feature separates the top quartile "
        "from the bottom (p<0.01); reels drive saves and shares, not reach; a screen on camera is the "
        "most reliable visual signal; comment gates lift engagement, not reach; the niche's hook is ~6.7 s. "
        "Two PRODUCTION.md numbers did not reproduce (documented, file not edited). The categorisation "
        "covers 6 of 13 planned dimensions.",
        "Plan. Finish the remaining category dimensions; re-run features and stats after the watchdog "
        "brings the newest reels in; keep the corpus-bias caveat on every report.",
    ]))
    S.append((f'Audience — {tally("Audience")}', [
        "Argumentation. The first ten cards were rejected on 12 Sep because they were derived from the "
        "corpus (what the niche publishes) rather than from what the audience asks. Three agents worked "
        "the question from three lenses (our corpus, founders on the web, employees on the web) in two "
        "rounds of disagreement, then Misha authorised a first-hand Reddit pass through his own browser.",
        "Execution review. 101 threads in 17 subreddits, read in full. 'How do I automate this specific "
        "process' is the largest cluster on both sides (38 of 101), trust and verification second (35), "
        "'what is AI' asked five times and never by an owner in those words. Customer-facing AI is "
        "rejected by customers; back-office is accepted. Three personas survive: Mary (online product "
        "owner), Ray (local services owner, who never says 'AI'), Marta (ops manager evaluated on AI "
        "adoption while forbidden to paste client data).",
        "Plan. Rules are in force (RULES.md §11, writer rule 13, reviewer check 11); the shoot list v2 "
        "waits for Misha's approval; then the ten cards are regenerated under the personas.",
    ]))
    S.append((f'Script — {tally("Script")}', [
        "Argumentation. Cards are a validated JSON contract (m2radar.card.v2) with the four-part editorial "
        "filter as literal fields, every claim with a state and a source, a frame-aware storyboard and a "
        "traceability block; an independent reviewer edits in place and the writer's version is kept in "
        "script_versions. The comment-keyword CTA was re-allowed on 12 Sep on the condition that the "
        "promised artefact exists.",
        f"Execution review. {n['n_cards']} cards v2 with {n['n_card_scenes']} scenes passed validation and "
        "review and exist as a card book; they are v1 and stay for reference. Reviewer findings clustered "
        "on unsupported numbers and on two asks per card, not on weak hooks.",
        "Plan. Ten new cards from docs/SHOOT_LIST_2026-09-13.md, each naming its persona and the question "
        "in the viewer's words, with a one-page artefact behind the CTA; Builds are shot only after the "
        "build has run and broken once.",
    ]))
    S.append((f'Video — {tally("Video")}', [
        "Argumentation. The Remotion EDL contract and the scene-segmentation schema were the two things "
        "worth taking from Max's Latest branch unchanged; storyboard frames are template placeholders "
        "rendered from design tokens because Misha's rule forbids generated text in images and because a "
        "storyboard is a shooting instruction, not a picture.",
        "Execution review. Every card exports a validated PREVIS EDL; one real Remotion render proved the "
        "path. No card has real footage yet, so takes -> edl_with_takes -> render -> receipt has zero real "
        "inputs, and storage (Supabase canonical, Cloudflare delivery) is configured but unused.",
        "Plan. Phase 3 is offered to Max: real owner footage through the take sidecar path, storage wiring, "
        "quality review, then publishing (Misha's call) and feeding results back through our_posts.",
    ]))
    S.append((f'Notion & docs — {tally("Notion & docs")}', [
        "Argumentation. Notion is the shared surface for Misha and Max, so it is generated from the "
        "database, never hand-edited: a dashboard with architecture, coverage, analytics, insights and "
        "hypotheses, seven databases, and now this kanban and review. Documentation inside the tool is "
        "English; the Russian working documents at the repo root keep an English rendering beside them.",
        "Execution review. Two Notion API traps were hit and fixed in code (child pages cannot be archived "
        "through the blocks endpoint; a database link needs database_id). The dashboard rebuilds "
        "idempotently; ids are cached in data/notion_ids.json.",
        "Plan. Re-apply after Monday's run so Runs, coverage and this board reflect the first scheduled "
        "execution; keep the legacy Signal databases labelled, not merged.",
    ]))
    S.append((f'Infra & ops — {tally("Infra & ops")}', [
        "Argumentation. One SQLite as the source of truth, idempotent versioned migrations, a runs/jobs "
        "trace for every step, and a cron chain where a new stage can fail without breaking the old "
        "thirteen steps. No new module spends money without an explicit yes.",
        f"Execution review. {n['n_runs']} runs and {n['n_jobs']} jobs traced; tests green locally and on the "
        "server; the server carries the rules v2 (30-day window, shares + saves ladder, author-level pool, "
        "comment CTA allowed) since 12 Sep. Known gaps: four orphan video_state rows from an August "
        "archive, eight frames flagged as a known broken download.",
        "Plan. Watch Monday's run log; rotate the Notion token when Misha decides; keep the stage rows "
        "below as the live trace of which stages have actually executed.",
    ]))
    return S


def review_blocks(rows, numbers, kanban_db_id=None):
    b = [nb.callout(f"Generated by engine/notion_kanban.py at {db_util.now()} from the live database. "
                    "Do not edit by hand: re-run the module.", icon='🧭')]
    if kanban_db_id:
        b.append(nb.paragraph('The board:'))
        b.append(nb.link_to_database(kanban_db_id))
    for heading, paras in review_sections(rows, numbers):
        b.append(nb.heading(heading, 2))
        for p in paras:
            b.append(nb.paragraph(p))
    b.append(nb.heading('Stage trace', 2))
    stage = [r for r in rows if r['key'].startswith('stage:')]
    b.append(nb.table(['Stage', 'Status', 'Evidence'],
                      [[r['stage'], r['status'], r['evidence'][:160]] for r in stage]))
    return b


# ---------------------------------------------------------------------------- apply
def ensure_kanban(transport, id_cache):
    db_id = id_cache.database_id(KANBAN_TITLE)
    if db_id:
        return db_id
    db = transport.create_database(ns.DASHBOARD_PAGE_ID, KANBAN_TITLE, KANBAN_SCHEMA)
    id_cache.set_database_id(KANBAN_TITLE, db['id'])
    time.sleep(ns.RATE_LIMIT_SLEEP_S)
    return db['id']


def ensure_review_page(transport, id_cache):
    page_id = id_cache.page_id(REVIEW_TITLE)
    if page_id:
        return page_id
    page = transport.create_page({'page_id': ns.DASHBOARD_PAGE_ID},
                                 {'title': {'title': nb.rich_text(REVIEW_TITLE)}})
    id_cache.set_page_id(REVIEW_TITLE, page['id'])
    time.sleep(ns.RATE_LIMIT_SLEEP_S)
    return page['id']


def apply(con, transport=None, id_cache=None):
    transport = transport or ns.LiveTransport()
    id_cache = id_cache or ns.IdCache()
    rows, numbers = build_rows(con)
    db_id = ensure_kanban(transport, id_cache)
    created = updated = 0
    for row in rows:
        props = row_properties(row)
        page_id = id_cache.row_id(KANBAN_TITLE, row['key'])
        if not page_id:
            page_id = transport.find_page_by_key(db_id, 'Task', row['key'])
            time.sleep(ns.RATE_LIMIT_SLEEP_S)
        if page_id:
            transport.update_page_properties(page_id, props)
            id_cache.set_row_id(KANBAN_TITLE, row['key'], page_id)
            updated += 1
        else:
            page = transport.create_page({'database_id': db_id}, props)
            id_cache.set_row_id(KANBAN_TITLE, row['key'], page['id'])
            created += 1
        time.sleep(ns.RATE_LIMIT_SLEEP_S)
    review_id = ensure_review_page(transport, id_cache)
    blocks = review_blocks(rows, numbers, kanban_db_id=db_id)
    transport.replace_children(review_id, blocks)
    return {'kanban_db': db_id, 'review_page': review_id, 'rows': len(rows),
            'created': created, 'updated': updated, 'review_blocks': nb.count_blocks(blocks)}


def render_dry(rows, numbers):
    out = [f'{len(rows)} rows ({len(TASKS)} tasks + {len(rows) - len(TASKS)} stages)\n']
    for r in sorted(rows, key=lambda x: x['order']):
        out.append(f"  [{r['status']:<11}] {r['block']:<14} {r['stage']:<24} {r['key']}")
    out.append('')
    for heading, paras in review_sections(rows, numbers):
        out.append(f'## {heading}')
        out.extend('  ' + p for p in paras)
    return '\n'.join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry', action='store_true', help='print rows and review, no network')
    ap.add_argument('--apply', action='store_true', help='create/update the kanban and review in Notion')
    args = ap.parse_args(argv)
    con = db_util.connect()
    rows, numbers = build_rows(con)
    if args.apply:
        try:
            ns.notion.env('NOTION_TOKEN')
        except SystemExit:
            print('NOTION_TOKEN not configured — nothing applied.', file=sys.stderr)
            return 2
        res = apply(con)
        print(json.dumps(res, indent=1))
        return 0
    print(render_dry(rows, numbers))
    return 0


if __name__ == '__main__':
    sys.exit(main())
