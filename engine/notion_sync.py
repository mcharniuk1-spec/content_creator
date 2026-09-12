#!/usr/bin/env python3
"""Notion Sync for the M2Radar Content Engine dashboard (SPEC §85-91, audit §8).

    python3 -m engine.notion_sync --dry [--scope all|dashboard|dbs|reels|accounts|cards|runs] [--limit N]
    python3 -m engine.notion_sync --apply ...      # NOT to be run without explicit review — see below

The Notion side of this repo currently has two unrelated "Cards/Reels/Accounts" systems
(`reports/audit/05-notion-state.md`): the operational databases the weekly cron writes to
(`NOTION_REELS_DB`/`NOTION_ACCOUNTS_DB`, orphaned from the page tree) and a one-off
2026-09-05 analytical export linked from the dashboard. This module does NOT re-point the
operational databases (audit §8 option (b)) — it reuses the existing Cards database, adds
seven new databases under the Content Engine Tool page for the richer per-run analysis this
repo's `engine/*` tables now produce, and replaces the dashboard page body with a current
summary. The old Reels/Accounts Signal databases are relabelled, not deleted (SPEC §90).

--dry is the default and is intentionally the only mode this module has ever been run in:
it prints a plan (pages/databases/properties/row counts) and writes
`reports/notion-sync-plan.md`; it performs zero writes to Notion. The only Notion network
calls --dry can make are read-only schema-discovery GETs on the two already-existing,
already-documented objects (the dashboard page and the reused Cards database), and only
when `--discover` is also passed — plain `--dry` never touches the network and needs no
token, so the plan can always be generated offline from the local database and JSON files.

--apply executes the plan for real (create/update pages, databases and rows). It is fully
implemented here for the orchestrator to run later, after a human has reviewed the --dry
plan — this module itself never calls it. Running --apply requires NOTION_TOKEN in `.env`,
loaded the same way `notion.py` loads it; the token is never logged, printed or written to
any file this module produces.
"""
import argparse, datetime, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:                      # `python3 -m engine.notion_sync` from any cwd
    sys.path.insert(0, str(ROOT))

import notion                                       # noqa: E402  root-level module: env() + call()
from engine import corpus, db_util                  # noqa: E402
from engine import notion_blocks as nb              # noqa: E402
from engine import providers as providers_mod       # noqa: E402

PLAN_VERSION = 'notion-sync-plan-v1'

# ---------------------------------------------------------------------------------------
# Known Notion object IDs (reports/audit/05-notion-state.md). None of these are secrets —
# they are workspace object identifiers already written down in that audit file — but the
# audit itself declined to extract the *operational* Reels/Accounts DB ids (they are read
# only from `.env` at apply time, never hard-coded or printed here, matching the audit's
# own restraint in §1/§4.4).
# ---------------------------------------------------------------------------------------
DASHBOARD_PAGE_ID = '3d00bd21ed6a800fb0ffda652e539ef1'          # Content Engine Tool
CARDS_DB_ID = '225e60a9-3198-4e3c-a151-b462d20d2e63'             # reused, never recreated
RELEASE_PAGE_ID = '3d20bd21ed6a813a9a4cd8f51a28af71'             # M2 Signal + Studio · 7 Sep
SIGNAL_REELS_DB_ID = 'c26c6990-bba9-4ab5-a700-e94bd42e327d'      # one-off 2,352-row export
SIGNAL_ACCOUNTS_DB_ID = 'e45a50d2-a910-47b8-99a0-f2ec9f1a3393'   # one-off 100-row export
LEGACY_STUB_PAGE_IDS = [
    '3d00bd21-ed6a-81cb-abdf-d7d0eef5497c',   # orphaned "M2 Lab — Radar" stub #1
    '3d00bd21-ed6a-8165-b1f4-d3520940b65a',   # orphaned "M2 Lab — Radar" stub #2
]

IDS_CACHE_PATH = ROOT / 'data' / 'notion_ids.json'
PLAN_OUT_PATH = ROOT / 'reports' / 'notion-sync-plan.md'
RATE_LIMIT_SLEEP_S = 0.35     # Notion's documented ~3 req/s average limit

SCOPES = ('dashboard', 'dbs', 'reels', 'accounts', 'cards', 'runs',
          'insights', 'hypotheses', 'categories', 'all')

NEW_DATABASES = ('Runs', 'Insights', 'Hypotheses', 'Cards v2', 'Reels analysis',
                  'Accounts analysis', 'Categories')

# db title -> Notion property name treated as the idempotency key (also the title property)
KEY_PROPERTY = {
    'Runs': 'Run ID', 'Insights': 'Insight ID', 'Hypotheses': 'Title',
    'Cards v2': 'Card ID', 'Reels analysis': 'Code', 'Accounts analysis': 'Username',
    'Categories': 'Label',
}

# db title -> {Notion property name: row-dict field name}, for the (few) properties whose
# natural slug (`name.lower().replace(' ', '_')`) doesn't match the row dict's own field
# name (e.g. reels' DB column is `comm`, not `comments`). Checked against every *_rows()
# function in tests/test_notion_sync.py; keep this in sync when either side's names change.
FIELD_OVERRIDES = {
    'Reels analysis': {'Comments': 'comm', 'Reshares': 'resh', 'Saves': 'save',
                       'View lift': 'lift', 'Scenes': 'scenes_n'},
    'Accounts analysis': {'Videos': 'n_videos', 'Consistency': 'consistency_score',
                          'Top reels': 'top_reel'},
    'Cards v2': {'Hypothesis': 'hypothesis_id', 'Total seconds': 'total_s', 'Words': 'total_words'},
    'Runs': {'Model/prompt versions': 'model_prompt_versions'},
}


def _field_name(db_title, prop_name):
    return FIELD_OVERRIDES.get(db_title, {}).get(prop_name) or prop_name.lower().replace(' ', '_')


def _select(*options):
    return {'select': {'options': [{'name': o} for o in options]}}


def _plain(kind):
    return {kind: {}}


# Notion property schemas for `create_database` (classic REST API `properties` object).
# Kept intentionally close to what `engine/*` tables already hold — see PLAN.md mapping
# in each *_rows()/*_to_properties() pair below.
PROPERTY_SCHEMAS = {
    'Runs': {
        'Run ID': _plain('title'), 'Date': _plain('date'),
        'Kind': _select('weekly', 'watchdog', 'analysis', 'cards', 'manual'),
        'Git commit': _plain('rich_text'), 'Model/prompt versions': _plain('rich_text'),
        'Data scope': _plain('rich_text'), 'Counts': _plain('rich_text'),
        'Statuses': _plain('rich_text'), 'Issues': _plain('rich_text'),
        'Reports links': _plain('rich_text'), 'Next steps': _plain('rich_text'),
    },
    'Insights': {
        'Insight ID': _plain('title'), 'Statement': _plain('rich_text'),
        'Metric': _plain('rich_text'), 'N': _plain('number'),
        'Confidence': _select('RELIABLE', 'PROBABLE', 'INSUFFICIENT'),
        'Supporting reels': _plain('rich_text'), 'Supporting accounts': _plain('rich_text'),
        'Transcript pattern': _plain('rich_text'), 'Visual pattern': _plain('rich_text'),
        'Implication': _plain('rich_text'), 'Created': _plain('date'),
    },
    'Hypotheses': {
        'Title': _plain('title'), 'Score': _plain('number'), 'Evidence': _plain('rich_text'),
        'References': _plain('rich_text'),
        'Status': _select('PROPOSED', 'SELECTED', 'REJECTED'),
        'Resulting card': _plain('rich_text'),
    },
    'Cards v2': {
        'Card ID': _plain('title'), 'Title': _plain('rich_text'),
        'Format': _select('M2 Radar', 'M2 Builds', 'M2 Teardown'),
        'Status': _select('DRAFT', 'REVIEWED', 'APPROVED', 'SHOT', 'PUBLISHED', 'DROPPED'),
        'Hypothesis': _plain('rich_text'), 'Total seconds': _plain('number'),
        'Words': _plain('number'), 'Refs': _plain('rich_text'), 'Script': _plain('rich_text'),
        'Storyboard summary': _plain('rich_text'), 'JSON path': _plain('rich_text'),
        'PDF page': _plain('number'),
    },
    'Reels analysis': {
        'Code': _plain('title'), 'URL': _plain('url'), 'Account': _plain('rich_text'),
        'Date': _plain('date'), 'Play': _plain('number'), 'Likes': _plain('number'),
        'Comments': _plain('number'), 'Reshares': _plain('number'), 'Saves': _plain('number'),
        'View lift': _plain('number'), 'Robust z': _plain('number'),
        'Hook type': _plain('rich_text'), 'Pain': _plain('rich_text'), 'Topic': _plain('rich_text'),
        'Solution': _plain('rich_text'), 'CTA': _plain('rich_text'), 'Hook text': _plain('rich_text'),
        'Beats summary': _plain('rich_text'), 'Visual sequence': _plain('rich_text'),
        'First frame type': _plain('rich_text'), 'Scenes': _plain('number'), 'Cuts': _plain('number'),
        'Confidence': _select('ANALYSIS_READY', 'FRAMES_ONLY', 'TRANSCRIPT_UNUSABLE',
                              'INGESTED_NOT_ANALYZED'),
        'Used in cards': _plain('rich_text'),
    },
    'Accounts analysis': {
        'Username': _plain('title'), 'Followers': _plain('number'), 'Videos': _plain('number'),
        'Median play': _plain('number'), 'Consistency': _plain('number'),
        'Reliability': _select('CONSISTENT', 'HIGH_VARIANCE', 'SMALL_SAMPLE'),
        'High performer share': _plain('number'), 'Top reels': _plain('rich_text'),
    },
    'Categories': {
        'Label': _plain('title'),
        'Kind': _select('topic', 'pain', 'hook', 'solution', 'cta', 'visual'),
        'N': _plain('number'), 'N creators': _plain('number'),
        'Median lift': _plain('number'), 'Median share rate': _plain('number'),
        'Median save rate': _plain('number'),
        'Confidence': _select('RELIABLE', 'PROBABLE', 'INSUFFICIENT'),
    },
}


# =========================================================================================
# id cache — resumable idempotency (data/notion_ids.json)
# =========================================================================================
class IdCache:
    """{"databases": {title: id}, "rows": {db_title: {key: page_id}}}.

    Only written to during --apply (query-by-property-then-create, then cache the id so a
    resumed run does not re-query Notion for rows it already placed). --dry never calls
    any of the `set_*` methods, so it never touches this file.
    """

    def __init__(self, path=IDS_CACHE_PATH):
        self.path = pathlib.Path(path)
        self.data = {'databases': {}, 'rows': {}}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding='utf-8'))
                self.data.update({k: loaded.get(k, {}) for k in ('databases', 'rows')})
            except (ValueError, OSError):
                pass

    def database_id(self, title):
        return self.data['databases'].get(title)

    def set_database_id(self, title, db_id):
        self.data['databases'][title] = db_id
        self._save()

    def row_id(self, db_title, key):
        return self.data['rows'].get(db_title, {}).get(key)

    def set_row_id(self, db_title, key, page_id):
        self.data['rows'].setdefault(db_title, {})[key] = page_id
        self._save()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True, ensure_ascii=False),
                             encoding='utf-8')


# =========================================================================================
# transport — read-only by construction for --dry; writes only exist on LiveTransport
# =========================================================================================
class ReadOnlyTransport:
    """Everything --dry is allowed to do on the network: GET a page, GET a database.

    No method on this class can mutate Notion — there is no `create_page`, no `PATCH`,
    no `create_database` here. `notion_sync.main()` never constructs `LiveTransport`
    unless `--apply` was passed, and this module is never invoked with `--apply`.
    """

    def __init__(self, call=None):
        self._call = call or notion.call
        self.calls = []   # (kind, method, path) — kind is 'read' or 'write', for tests/audits

    def get_page(self, page_id):
        self.calls.append(('read', 'GET', f'/pages/{page_id}'))
        return self._call('GET', f'/pages/{page_id}')

    def get_database(self, db_id):
        self.calls.append(('read', 'GET', f'/databases/{db_id}'))
        return self._call('GET', f'/databases/{db_id}')


class LiveTransport(ReadOnlyTransport):
    """The full transport, used only under --apply. Query endpoints are POST at the
    HTTP level (Notion's API shape) but are read operations — tagged 'read' in `calls`
    so an idempotency check never counts as a write; page/database/block mutation
    methods are tagged 'write'."""

    def query_database(self, db_id, body=None):
        self.calls.append(('read', 'POST', f'/databases/{db_id}/query'))
        return self._call('POST', f'/databases/{db_id}/query', body or {})

    def get_blocks_children(self, page_id):
        out, cur = [], None
        while True:
            path = f'/blocks/{page_id}/children?page_size=100' + (f'&start_cursor={cur}' if cur else '')
            self.calls.append(('read', 'GET', path))
            res = self._call('GET', path)
            out += res.get('results', [])
            cur = res.get('next_cursor')
            if not cur:
                break
        return out

    def create_page(self, parent, properties, children=None):
        body = {'parent': parent, 'properties': properties}
        if children:
            body['children'] = list(children)[:nb.BLOCKS_PER_REQUEST]
        self.calls.append(('write', 'POST', '/pages'))
        return self._call('POST', '/pages', body)

    def update_page_properties(self, page_id, properties):
        self.calls.append(('write', 'PATCH', f'/pages/{page_id}'))
        return self._call('PATCH', f'/pages/{page_id}', {'properties': properties})

    def archive_block(self, block_id):
        self.calls.append(('write', 'PATCH', f'/blocks/{block_id}'))
        return self._call('PATCH', f'/blocks/{block_id}', {'archived': True})

    def append_children(self, page_id, blocks):
        for chunk in nb.chunk_blocks(blocks):
            self.calls.append(('write', 'PATCH', f'/blocks/{page_id}/children'))
            self._call('PATCH', f'/blocks/{page_id}/children', {'children': chunk})

    def replace_children(self, page_id, blocks):
        """Archive every existing top-level child, then append the new body in
        <=100-block chunks. Mirrors `notion.py:push`'s own archive-then-rewrite pattern."""
        kept = 0
        for b in self.get_blocks_children(page_id):
            # Child pages and databases cannot be archived through the blocks endpoint
            # (Notion 400: "Updating a page via the blocks endpoint unsupported") and the
            # dashboard rebuild keeps them anyway (existing release page, Cards DB, the new
            # analysis databases live under this page). Only body blocks are replaced.
            if b.get('type') in ('child_page', 'child_database'):
                kept += 1
                continue
            self.archive_block(b['id'])
        if kept:
            print(f'  kept {kept} child page(s)/database(s) under the dashboard', flush=True)
        self.append_children(page_id, blocks)

    def create_database(self, parent_page_id, title, properties_schema):
        body = {'parent': {'page_id': parent_page_id},
                'title': [{'type': 'text', 'text': {'content': title}}],
                'properties': properties_schema}
        self.calls.append(('write', 'POST', '/databases'))
        return self._call('POST', '/databases', body)

    def find_page_by_key(self, db_id, key_property, value):
        res = self.query_database(db_id, {'filter': {'property': key_property,
                                                      'rich_text' if key_property != 'title' else 'title':
                                                          {'equals': value}}})
        results = res.get('results') or []
        return results[0]['id'] if results else None


# =========================================================================================
# local data gathering — everything the plan is built from
# =========================================================================================
def _env_present(name):
    """Presence only, never the value — matches `engine.db_util.env_present`."""
    return db_util.env_present(name)


def architecture_section(con):
    t = corpus.tiers(con)
    vs_counts = {}
    for col in ('transcript_state', 'frames_state', 'transcript_analysis_state',
               'frame_analysis_state', 'analysis_ready', 'corpus_tier'):
        rows = con.execute(f'SELECT {col}, COUNT(*) FROM video_state GROUP BY {col}').fetchall()
        vs_counts[col] = {str(r[0]): r[1] for r in rows}
    produced = con.execute("SELECT COUNT(*) FROM cards_v2 WHERE status='PUBLISHED'").fetchone()[0]
    return {
        'engine_version': __import__('engine').__version__,
        'git_commit': db_util.git_commit() or 'unknown (no .git found)',
        'providers': [{'name': p.name, 'kind': p.kind, 'role': p.role, 'state': state, 'detail': detail}
                     for p, state, detail in providers_mod.snapshot()],
        'hiker_pending_watchdog': t['counts']['n_newest_unprocessed'],
        'video_state_by_stage': vs_counts,
        'production_state': {'videos_produced': produced},
        'pipeline_stages': [
            'DISCOVERED', 'PROFILE_FETCHED', 'VIDEO_METADATA_FETCHED', 'STATS_FETCHED',
            'MEDIA_FETCHED', 'TRANSCRIPTION', 'TRANSCRIPT_ANALYSIS', 'FRAME_EXTRACTION',
            'FRAME_ANALYSIS', 'ALIGNMENT', 'GENERAL_ANALYSIS', 'STATISTICAL_ANALYSIS',
            'CATEGORIZATION', 'REFERENCE_SELECTION', 'CONCEPT_GENERATION', 'CARD_GENERATION',
            'SCRIPT_GENERATION', 'SCRIPT_REVIEW', 'FRAME_PLAN', 'FRAME_GENERATION',
            'VIDEO_GENERATION_READY', 'VIDEO_RENDER', 'QUALITY_REVIEW', 'NOTION_SYNC', 'COMPLETED',
        ],
    }


def data_coverage_section(con):
    t = corpus.tiers(con)
    creators = con.execute('SELECT COUNT(DISTINCT username) FROM reels').fetchone()[0]
    with_stats = con.execute('SELECT COUNT(DISTINCT code) FROM scores').fetchone()[0]
    cards = con.execute('SELECT COUNT(*) FROM cards_v2').fetchone()[0]
    produced = con.execute("SELECT COUNT(*) FROM cards_v2 WHERE status='PUBLISHED'").fetchone()[0]
    return {
        'creators': creators,
        'reels_ingested': t['counts']['n_ingested'],
        'reels_with_stats': with_stats,
        'reels_with_transcripts': t['counts']['n_transcript_rows'],
        'reels_with_frames': t['counts']['n_frames'],
        'fully_analyzed': t['counts']['n_ready'],
        'hiker_reels_pending_watchdog': t['counts']['n_newest_unprocessed'],
        'cards': cards,
        'videos_produced': produced,
        'denominators': t['denominators'],
    }


def _load_json_dir(path):
    out = {}
    if not path.exists():
        return out
    for f in sorted(path.glob('*.json')):
        try:
            out[f.stem] = json.loads(f.read_text(encoding='utf-8'))
        except (ValueError, OSError) as e:
            out[f.stem] = {'_error': str(e)}
    return out


def analytics_section(con):
    """reports/data/*.json, produced by engine/report_data.py — a module this task does
    not own and that may not exist yet. When missing, fall back to a minimal snapshot
    derived directly from the DB so the plan is never empty for that reason alone."""
    data = _load_json_dir(ROOT / 'reports' / 'data')
    if data:
        return {'source': 'reports/data/*.json', 'files': sorted(data.keys()), 'data': data}
    top_accounts = [dict(r) for r in con.execute(
        'SELECT username, followers, n_videos, median_play, consistency_score, reliability '
        'FROM creator_stats ORDER BY median_play DESC LIMIT 10')]
    n_categorized = con.execute('SELECT COUNT(*) FROM video_features WHERE topic IS NOT NULL').fetchone()[0]
    return {
        'source': "fallback: engine.corpus/creator_stats (reports/data/*.json not found — "
                  "engine/report_data.py has not produced it yet)",
        'top_accounts_by_median_play': top_accounts,
        'note': ('category performance tables (topic/pain/hook/solution/CTA/visual/scene-cut) '
                f'come from video_features — {n_categorized} categorized rows there right now; '
                 'see the Categories section for the actual breakdown.'),
    }


def insights_section(con):
    f = ROOT / 'data' / 'analysis' / 'insights.json'
    if f.exists():
        try:
            return {'source': str(f.relative_to(ROOT)), 'rows': json.loads(f.read_text(encoding='utf-8'))}
        except (ValueError, OSError) as e:
            return {'source': str(f.relative_to(ROOT)), 'rows': [], 'error': str(e)}
    rows = [dict(r) for r in con.execute('SELECT * FROM insights')]
    return {'source': 'insights table (data/analysis/insights.json not found)', 'rows': rows}


def hypotheses_section(con):
    f = ROOT / 'data' / 'analysis' / 'hypotheses.json'
    if f.exists():
        try:
            return {'source': str(f.relative_to(ROOT)), 'rows': json.loads(f.read_text(encoding='utf-8'))}
        except (ValueError, OSError) as e:
            return {'source': str(f.relative_to(ROOT)), 'rows': [], 'error': str(e)}
    rows = [dict(r) for r in con.execute('SELECT * FROM hypotheses')]
    return {'source': 'hypotheses table (data/analysis/hypotheses.json not found)', 'rows': rows}


def cards_rows(con):
    """Business-level rows for the 'Cards v2' database. JSON on disk (cards/*.json) is
    the source of truth per SPEC §2.9; the DB table mirrors it. Prefer the JSON file
    when present (it carries the full script the DB column truncates)."""
    json_dir = ROOT / 'cards'
    by_id = {f.stem: f for f in (json_dir.glob('*.json') if json_dir.exists() else [])}
    out = []
    for r in con.execute('SELECT * FROM cards_v2 ORDER BY created_at'):
        row = dict(r)
        card_id = row['card_id']
        script_text = None
        if card_id in by_id:
            try:
                full = json.loads(by_id[card_id].read_text(encoding='utf-8'))
                script_text = json.dumps(full.get('script', full), ensure_ascii=False)
            except (ValueError, OSError):
                pass
        script_text = script_text or row.get('script_json') or ''
        out.append({
            'card_id': card_id, 'title': row['title'], 'format': row['format'],
            'status': row['status'], 'hypothesis_id': row.get('hypothesis_id'),
            'total_s': row.get('total_s'), 'total_words': row.get('total_words'),
            'refs': row.get('refs_json'),
            'script': script_text[:2000] + (' … see JSON' if len(script_text) > 2000 else ''),
            'storyboard_summary': (row.get('editing_json') or '')[:500],
            'json_path': row.get('json_path') or (str((json_dir / f'{card_id}.json').relative_to(ROOT))
                                                   if card_id in by_id else None),
            'pdf_page': row.get('pdf_page'),
        })
    return out


def reels_analysis_rows(con, limit=None):
    """One row per code that has at least reached ANALYSIS_READY-or-better in the corpus
    tiering (`engine.corpus.tiers`) — SPEC §2 tier vocabulary. Category fields (hook_type,
    pain, topic, ...) come from `video_features` via a LEFT JOIN: whenever the LLM analysis
    wave hasn't reached a given code yet, those fields are simply None on its row — reported
    honestly (via `confidence`, the corpus tier) rather than papered over or guessed."""
    t = corpus.tiers(con)
    tier_of_code = corpus.tier_of(con)
    codes = t['analysis_ready'] + t['frames_only'] + t['transcript_unusable']
    if not codes:
        return []
    placeholders = ','.join('?' * len(codes))
    rows = con.execute(f"""
        SELECT r.code, r.username, r.ts, r.play, r.likes, r.comm, r.resh, r.save,
               s.z, s.resh_1k, s.save_1k,
               vf.hook_type, vf.pain, vf.topic, vf.solution_type, vf.cta_type, vf.hook_text,
               vf.visual_sequence, vf.first_frame_type, vf.scenes_n, vf.cuts, vf.view_lift,
               vf.robust_z
        FROM reels r
        LEFT JOIN scores s ON s.code=r.code
             AND s.snapshot_id=(SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1)
        LEFT JOIN video_features vf ON vf.code=r.code
        WHERE r.code IN ({placeholders})
        GROUP BY r.code ORDER BY COALESCE(vf.robust_z, s.z, 0) DESC""", codes).fetchall()
    used_in_cards = {}
    for r in con.execute('SELECT card_id, refs_json FROM cards_v2'):
        for ref in db_util.loads(r['refs_json'], []) or []:
            # refs_json holds the card's references: either bare codes or reference dicts
            code = ref.get('code') if isinstance(ref, dict) else ref
            if code:
                used_in_cards.setdefault(code, []).append(r['card_id'])
    beats_by_code = {}
    for code, role in con.execute('SELECT code, role FROM beats ORDER BY code, idx'):
        beats_by_code.setdefault(code, []).append(role)
    out = []
    for r in rows:
        row = dict(r)
        code = row['code']
        out.append({
            'code': code, 'url': f'https://instagram.com/reel/{code}', 'account': row['username'],
            'date': datetime.date.fromtimestamp(row['ts']).isoformat() if row['ts'] else None,
            'play': row['play'], 'likes': row['likes'], 'comm': row['comm'], 'resh': row['resh'],
            'save': row['save'],
            'lift': row['view_lift'], 'robust_z': row['robust_z'] if row['robust_z'] is not None else row['z'],
            'hook_type': row['hook_type'], 'pain': row['pain'], 'topic': row['topic'],
            'solution': row['solution_type'], 'cta': row['cta_type'], 'hook_text': row['hook_text'],
            'visual_sequence': row['visual_sequence'], 'first_frame_type': row['first_frame_type'],
            'scenes_n': row['scenes_n'], 'cuts': row['cuts'],
            'beats_summary': (f"{len(beats_by_code[code])} beats: " + ' > '.join(beats_by_code[code]))
                             if code in beats_by_code else None,
            'confidence': tier_of_code.get(code, 'INGESTED_NOT_ANALYZED'),
            'used_in_cards': used_in_cards.get(code, []),
        })
    if limit:
        out = out[:int(limit)]
    return out


def accounts_analysis_rows(con):
    """`creator_stats` (already populated, 132 rows) joined to `accounts` for metadata,
    plus each creator's single best reel (by robust_z when analysed, else raw score)."""
    best_by_user = {}
    for r in con.execute("""
            SELECT r.username, r.code, COALESCE(vf.robust_z, s.z) AS score
            FROM reels r
            LEFT JOIN scores s ON s.code=r.code
            LEFT JOIN video_features vf ON vf.code=r.code"""):
        cur = best_by_user.get(r['username'])
        if r['score'] is not None and (cur is None or r['score'] > cur[1]):
            best_by_user[r['username']] = (r['code'], r['score'])

    rows = con.execute("""
        SELECT cs.*, a.follower_count, a.category, a.biography
        FROM creator_stats cs LEFT JOIN accounts a ON a.username=cs.username
        WHERE cs.snapshot_id=(SELECT MAX(snapshot_id) FROM creator_stats)
        ORDER BY cs.median_play DESC""").fetchall()
    out = []
    for r in rows:
        row = dict(r)
        best = best_by_user.get(row['username'])
        out.append({
            'username': row['username'], 'followers': row['followers'] or row['follower_count'],
            'n_videos': row['n_videos'], 'median_play': row['median_play'],
            'consistency_score': row['consistency_score'], 'reliability': row['reliability'],
            'high_performer_share': row['high_performer_share'],
            'top_reel': f'https://instagram.com/reel/{best[0]}' if best else None,
            'top_reel_score': best[1] if best else None,
        })
    return out


def categories_rows(con):
    """Frequency + performance per canonical category value (SPEC §4/§89), from
    `video_features`. Returns [] (rather than fabricated numbers) whenever no row there
    has been categorized yet — checked live below, never assumed."""
    dims = [('topic', 'topic'), ('pain', 'pain'), ('hook_type', 'hook'),
            ('solution_type', 'solution'), ('cta_type', 'cta'), ('visual_sequence', 'visual')]
    out = []
    n_total = con.execute('SELECT COUNT(*) FROM video_features').fetchone()[0]
    if not n_total:
        return out
    for col, kind in dims:
        for r in con.execute(f"""
                SELECT {col} AS label, COUNT(*) n, COUNT(DISTINCT code) n_creators_proxy,
                       AVG(view_lift) lift, AVG(share_rate) share, AVG(save_rate) save
                FROM video_features WHERE {col} IS NOT NULL GROUP BY {col} ORDER BY n DESC"""):
            out.append({'kind': kind, 'label': r['label'], 'n': r['n'],
                       'median_lift': r['lift'], 'median_share_rate': r['share'],
                       'median_save_rate': r['save'],
                       'confidence': 'PROBABLE' if r['n'] >= 10 else 'INSUFFICIENT'})
    return out


def insights_rows(con):
    """Rows for the 'Insights' database — one per `insights` table row."""
    out = []
    for r in con.execute('SELECT * FROM insights ORDER BY insight_id'):
        row = dict(r)
        codes = db_util.loads(row.get('supporting_codes_json'), []) or []
        creators = db_util.loads(row.get('supporting_creators_json'), []) or []
        out.append({
            'insight_id': row['insight_id'], 'statement': row.get('statement') or '',
            'metric': row.get('metric') or '', 'n': row.get('n'),
            'confidence': row.get('confidence') or 'INSUFFICIENT',
            'supporting_reels': ', '.join(f'https://www.instagram.com/reel/{c}/' for c in codes[:12]),
            'supporting_accounts': ', '.join(str(c) for c in creators[:20]),
            'transcript_pattern': row.get('transcript_pattern') or '',
            'visual_pattern': row.get('frame_pattern') or '',
            'implication': row.get('implication') or '',
            'created': (row.get('created_at') or '')[:10] or None,
        })
    return out


def hypotheses_rows(con):
    """Rows for the 'Hypotheses' database — one per `hypotheses` table row."""
    out = []
    for r in con.execute('SELECT * FROM hypotheses ORDER BY total_score DESC'):
        row = dict(r)
        refs = [x[0] for x in con.execute(
            'SELECT code FROM hypothesis_refs WHERE hypothesis_id=? ORDER BY code', (row['hypothesis_id'],))]
        evidence = row.get('statement') or ''
        sup = db_util.loads(row.get('supporting_insights_json'), []) or []
        if sup:
            evidence += ' | insights: ' + ', '.join(str(x) for x in sup)
        out.append({
            'title': f"{row['hypothesis_id']} · {row.get('title') or ''}".strip(' ·'),
            'score': row.get('total_score'), 'evidence': evidence,
            'references': ', '.join(f'https://www.instagram.com/reel/{c}/' for c in refs),
            'status': row.get('status') or 'PROPOSED',
            'resulting_card': row.get('card_id') or '',
        })
    return out


def runs_rows(con):
    """`runs` rows enriched with the derived, human-readable fields SPEC §91 wants on
    each Notion run page (data scope, counts, statuses, issues, next steps) — none of
    these are literal DB columns, so they are computed here once rather than inline in
    `_row_to_properties`, which stays a dumb field-name mapper."""
    rows = [dict(r) for r in con.execute('SELECT * FROM runs ORDER BY started_at DESC LIMIT 50')]
    from engine import state as state_mod
    for row in rows:
        try:
            summary = state_mod.run_summary(con, row['run_id'])
        except Exception:  # noqa: BLE001 — a summary miss must not break the plan
            summary = None
        row['summary'] = summary
        cfg = db_util.loads(row.get('config_json'), {}) or {}
        smry = db_util.loads(row.get('summary_json'), {}) or {}
        row['date'] = (row.get('started_at') or '')[:10]
        row['model_prompt_versions'] = cfg.get('model_prompt_versions') or smry.get('model_prompt_versions') or ''
        row['data_scope'] = cfg.get('data_scope') or ''
        row['counts'] = json.dumps(summary['totals'], sort_keys=True) if summary else ''
        row['statuses'] = row.get('status') or ''
        row['issues'] = smry.get('issues') or ''
        row['reports_links'] = smry.get('reports_links') or ''
        row['next_steps'] = smry.get('next_steps') or ''
    return rows


def legacy_section():
    """Objects to label 'Legacy', not delete (SPEC §90, audit §6/§8.5)."""
    return {
        'release_page': RELEASE_PAGE_ID,
        'signal_reels_db': SIGNAL_REELS_DB_ID,
        'signal_accounts_db': SIGNAL_ACCOUNTS_DB_ID,
        'orphan_stub_pages': list(LEGACY_STUB_PAGE_IDS),
        'operational_reels_db_configured': _env_present('NOTION_REELS_DB'),
        'operational_accounts_db_configured': _env_present('NOTION_ACCOUNTS_DB'),
        'decision_open': (
            "audit §8.1: (a) re-point NOTION_REELS_DB/NOTION_ACCOUNTS_DB at the Signal "
            "schema and migrate notion_db.py, vs (b) keep them separate, link+label the "
            "existing operational DBs into the page tree and mark the Signal DBs as a "
            "one-off 2026-09-05 snapshot. This build implements (b) — Misha/Max's call to "
            "confirm or override."),
    }


# =========================================================================================
# dashboard body — SPEC §86
# =========================================================================================
def build_dashboard_blocks(sections):
    arch, cov, an, ins, hyp, legacy = (sections['architecture'], sections['data_coverage'],
                                       sections['analytics'], sections['insights'],
                                       sections['hypotheses'], sections['legacy'])
    b = []
    b.append(nb.callout(
        f"Rebuilt by notion_sync.py ({PLAN_VERSION}) — replaces the previous body. "
        f"Engine {arch['engine_version']}, commit {arch['git_commit']}. Generated "
        f"{db_util.now()}.", icon='📡'))

    b.append(nb.heading('Architecture', 2))
    b.append(nb.paragraph(f"Version {arch['engine_version']} · git {arch['git_commit']}"))
    b.append(nb.code_block(' > '.join(arch['pipeline_stages']), language='plain text'))
    b.append(nb.table(['Provider', 'Kind', 'Role', 'State', 'Detail'],
                      [[p['name'], p['kind'], p['role'], p['state'], p['detail'][:180]]
                       for p in arch['providers']]))
    b.append(nb.bulleted_item(str(arch['hiker_pending_watchdog']), label='Hiker reels pending watchdog'))
    b.append(nb.bulleted_item(str(arch['production_state']['videos_produced']), label='Videos produced'))

    b.append(nb.heading('Data coverage', 2))
    for label, key in (('Creators', 'creators'), ('Reels ingested', 'reels_ingested'),
                       ('Reels with stats', 'reels_with_stats'),
                       ('Reels with transcripts', 'reels_with_transcripts'),
                       ('Reels with frames', 'reels_with_frames'),
                       ('Fully analyzed reels', 'fully_analyzed'),
                       ('Hiker reels pending watchdog', 'hiker_reels_pending_watchdog'),
                       ('Cards', 'cards'), ('Videos produced', 'videos_produced')):
        b.append(nb.bulleted_item(str(cov[key]), label=label))

    b.append(nb.heading('Current analytics', 2))
    b.append(nb.paragraph(f"Source: {an['source']}"))
    if an.get('top_accounts_by_median_play'):
        b.append(nb.table(['Account', 'Followers', 'Videos', 'Median play', 'Reliability'],
                          [[a['username'], a.get('followers'), a['n_videos'],
                            round(a['median_play'] or 0), a['reliability']]
                           for a in an['top_accounts_by_median_play'][:10]]))
    if an.get('note'):
        b.append(nb.callout(an['note'], icon='⚠️'))

    b.append(nb.heading('Insights', 2))
    ins_rows = ins.get('rows') or []
    if not ins_rows:
        b.append(nb.paragraph(f"No insights yet ({ins['source']})."))
    for i in ins_rows[:20]:
        title = i.get('statement') or i.get('insight_id') or 'insight'
        body = [nb.paragraph(f"Metric: {i.get('metric')} · N={i.get('n')} · "
                             f"confidence: {i.get('confidence')}"),
                nb.paragraph(f"Transcript pattern: {i.get('transcript_pattern') or '—'}"),
                nb.paragraph(f"Visual pattern: {i.get('frame_pattern') or '—'}"),
                nb.paragraph(f"Implication: {i.get('implication') or '—'}")]
        b.append(nb.toggle(str(title), body))

    b.append(nb.heading('Hypotheses', 2))
    hyp_rows = hyp.get('rows') or []
    if not hyp_rows:
        b.append(nb.paragraph(f"No hypotheses yet ({hyp['source']})."))
    else:
        b.append(nb.table(['Title', 'Score', 'Status', 'Card'],
                          [[h.get('title'), h.get('total_score'), h.get('status'), h.get('card_id')]
                           for h in hyp_rows[:30]]))

    b.append(nb.heading('Cards', 2))
    b.append(nb.link_to_database(CARDS_DB_ID))
    b.append(nb.paragraph("New analysis-backed cards live in the 'Cards v2' database (linked below); "
                          "the 10 reviewed 7 September shooting plans stay in the reused Cards DB above."))

    b.append(nb.heading('Runs', 2))
    b.append(nb.paragraph("Every major execution run gets a row in the 'Runs' database (linked below)."))

    b.append(nb.heading('Legacy', 2))
    b.append(nb.callout(legacy['decision_open'], icon='❗'))
    b.append(nb.bookmark(f"https://app.notion.com/p/{legacy['release_page'].replace('-', '')}",
                         caption='M2 Signal + Studio · 7 September (legacy release ledger)'))
    b.append(nb.bookmark(f"https://app.notion.com/p/{legacy['signal_reels_db'].replace('-', '')}",
                         caption='Reels · Signal 2026-09-05 · one-off audit corpus, not live'))
    b.append(nb.bookmark(f"https://app.notion.com/p/{legacy['signal_accounts_db'].replace('-', '')}",
                         caption='Accounts · Signal 2026-09-05 · one-off audit corpus, not live'))
    for pid in legacy['orphan_stub_pages']:
        b.append(nb.bookmark(f"https://app.notion.com/p/{pid.replace('-', '')}",
                             caption='Legacy — orphaned stub, candidate for deletion (needs sign-off)'))
    return b


# =========================================================================================
# plan assembly
# =========================================================================================
def build_plan(con, scope='all', limit=None, discover=False, id_cache=None):
    id_cache = id_cache or IdCache()
    scope = scope if scope != 'all' else 'all'
    want = (lambda s: scope in ('all', s))

    plan = {'plan_version': PLAN_VERSION, 'generated_at': db_util.now(), 'scope': scope,
           'dashboard_page_id': DASHBOARD_PAGE_ID, 'discovery': None}

    if discover:
        plan['discovery'] = _discover(id_cache)

    if want('dashboard'):
        sections = {
            'architecture': architecture_section(con), 'data_coverage': data_coverage_section(con),
            'analytics': analytics_section(con), 'insights': insights_section(con),
            'hypotheses': hypotheses_section(con), 'legacy': legacy_section(),
        }
        blocks = build_dashboard_blocks(sections)
        plan['dashboard'] = {
            'sections': sections,
            'block_count': nb.count_blocks(blocks),
            'chunks': len(list(nb.chunk_blocks(blocks))),
            'action': 'REPLACE body of Content Engine Tool page (archive old children, append new)',
        }

    if want('dbs'):
        plan['databases'] = {}
        for title in NEW_DATABASES:
            existing = id_cache.database_id(title)
            plan['databases'][title] = {
                'exists_in_cache': bool(existing), 'cached_id': existing,
                'action': 'no-op (cached)' if existing else 'CREATE (query workspace by title first)',
                'key_property': KEY_PROPERTY[title],
                'properties': sorted(PROPERTY_SCHEMAS[title].keys()),
            }
        plan['databases']['Cards (reused)'] = {'id': CARDS_DB_ID, 'action': 'reuse, no schema change'}

    if want('reels'):
        rows = reels_analysis_rows(con, limit=limit)
        plan['reels_analysis'] = {
            'db_title': 'Reels analysis', 'row_count': len(rows), 'limit_applied': limit,
            'sample': rows[:3],
            'existing_cached': len(id_cache.data['rows'].get('Reels analysis', {})),
        }

    if want('accounts'):
        rows = accounts_analysis_rows(con)
        plan['accounts_analysis'] = {
            'db_title': 'Accounts analysis', 'row_count': len(rows), 'sample': rows[:3],
            'existing_cached': len(id_cache.data['rows'].get('Accounts analysis', {})),
        }

    if want('cards'):
        rows = cards_rows(con)
        plan['cards_v2'] = {'db_title': 'Cards v2', 'row_count': len(rows), 'sample': rows[:3],
                            'existing_cached': len(id_cache.data['rows'].get('Cards v2', {}))}

    if want('runs'):
        rows = runs_rows(con)
        plan['runs'] = {'db_title': 'Runs', 'row_count': len(rows), 'sample': rows[:3],
                        'existing_cached': len(id_cache.data['rows'].get('Runs', {}))}

    if scope == 'all':
        plan['categories'] = {'db_title': 'Categories', 'rows': categories_rows(con)}
    if want('insights'):
        plan['insights'] = {'db_title': 'Insights', 'rows': insights_rows(con)}
    if want('hypotheses'):
        plan['hypotheses'] = {'db_title': 'Hypotheses', 'rows': hypotheses_rows(con)}
        plan['insights_standalone'] = insights_section(con)
        plan['hypotheses_standalone'] = hypotheses_section(con)
        plan['legacy'] = legacy_section()

    return plan


def _discover(id_cache):
    """Best-effort, read-only schema discovery on the two well-known existing objects.
    Never required, never fatal — any failure (missing token, no network, workspace
    permission) is caught and reported as a plan note, not an exception."""
    out = {'dashboard_page': None, 'cards_db': None, 'error': None}
    try:
        transport = ReadOnlyTransport()
        page = transport.get_page(DASHBOARD_PAGE_ID)
        out['dashboard_page'] = {'id': page.get('id'), 'last_edited_time': page.get('last_edited_time')}
        db = transport.get_database(CARDS_DB_ID)
        title = ''.join(t.get('plain_text', '') for t in db.get('title', []))
        out['cards_db'] = {'id': db.get('id'), 'title': title, 'properties': sorted(db.get('properties', {}))}
    except SystemExit as e:                      # notion.call() raises SystemExit on non-2xx
        out['error'] = str(e)
    except Exception as e:                        # noqa: BLE001 — discovery must never break --dry
        out['error'] = f'{type(e).__name__}: {e}'
    return out


# =========================================================================================
# rendering — plan.md + console summary
# =========================================================================================
def _fmt_row(row, keys):
    return ' · '.join(f'{k}={row.get(k)}' for k in keys if k in row)


def render_plan_markdown(plan):
    lines = [f"# Notion Sync plan ({plan['plan_version']})", '',
            f"Generated: {plan['generated_at']} · scope: `{plan['scope']}` · mode: DRY (no writes made)",
            '']
    if plan.get('discovery') is not None:
        d = plan['discovery']
        lines += ['## Live schema discovery (read-only)', '```json',
                 json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True), '```', '']

    if 'dashboard' in plan:
        d = plan['dashboard']
        lines += ['## Dashboard', f"Action: {d['action']}",
                 f"Body: {d['block_count']} blocks total, {d['chunks']} append-children call(s).", '',
                 '### Architecture', f"engine {d['sections']['architecture']['engine_version']}, "
                 f"commit {d['sections']['architecture']['git_commit']}",
                 '```json', json.dumps(d['sections']['architecture']['providers'], indent=2,
                                       ensure_ascii=False), '```', '',
                 '### Data coverage', '```json',
                 json.dumps(d['sections']['data_coverage'], indent=2, ensure_ascii=False, default=str),
                 '```', '']

    if 'databases' in plan:
        lines += ['## Databases (create-if-missing under the dashboard page)', '',
                 '| Database | Action | Key property | Properties |', '|---|---|---|---|']
        for title, info in plan['databases'].items():
            if 'properties' in info:
                lines.append(f"| {title} | {info['action']} | {info.get('key_property', '—')} | "
                            f"{', '.join(info['properties'])} |")
            else:
                lines.append(f"| {title} | {info['action']} | — | — |")
        lines.append('')

    for key, title in (('reels_analysis', 'Reels analysis'), ('accounts_analysis', 'Accounts analysis'),
                       ('cards_v2', 'Cards v2'), ('runs', 'Runs')):
        if key not in plan:
            continue
        p = plan[key]
        lines += [f"## {title}", f"Rows to upsert: {p['row_count']} "
                 f"(cached from a previous --apply: {p['existing_cached']})"]
        if p.get('limit_applied'):
            lines.append(f"--limit applied: {p['limit_applied']}")
        lines.append('')
        lines.append('Sample rows (first 3):')
        lines.append('```json')
        lines.append(json.dumps(p['sample'], indent=2, ensure_ascii=False, default=str))
        lines.append('```')
        lines.append('')

    if 'categories' in plan:
        rows = plan['categories']['rows']
        lines += ['## Categories', f"Rows: {len(rows)}"
                 + ('' if rows else ' (video_features is empty — 0 analysed videos today)'), '']
        if rows:
            lines.append('```json')
            lines.append(json.dumps(rows[:10], indent=2, ensure_ascii=False, default=str))
            lines.append('```')
            lines.append('')

    if 'legacy' in plan:
        lines += ['## Legacy (label, never delete)', '```json',
                 json.dumps(plan['legacy'], indent=2, ensure_ascii=False), '```', '']

    return '\n'.join(lines)


def render_plan_summary(plan):
    lines = [f"Notion Sync plan · {plan['plan_version']} · scope={plan['scope']} · DRY (no writes)"]
    if 'dashboard' in plan:
        d = plan['dashboard']
        cov = d['sections']['data_coverage']
        lines.append(f"Dashboard: {d['block_count']} blocks / {d['chunks']} chunk(s) would replace the body of "
                    f"Content Engine Tool ({DASHBOARD_PAGE_ID})")
        lines.append(f"  coverage: {cov['creators']} creators, {cov['reels_ingested']} reels ingested, "
                    f"{cov['reels_with_transcripts']} with transcripts, {cov['reels_with_frames']} with frames, "
                    f"{cov['fully_analyzed']} fully analyzed, {cov['cards']} cards, "
                    f"{cov['videos_produced']} videos produced")
    if 'databases' in plan:
        to_create = sum(1 for v in plan['databases'].values() if v.get('action', '').startswith('CREATE'))
        lines.append(f"Databases: {len(NEW_DATABASES)} new ({to_create} would be created), Cards DB reused")
    for key, label in (('reels_analysis', 'Reels analysis'), ('accounts_analysis', 'Accounts analysis'),
                      ('cards_v2', 'Cards v2'), ('runs', 'Runs')):
        if key in plan:
            lines.append(f"{label}: {plan[key]['row_count']} rows to upsert")
    if 'categories' in plan:
        lines.append(f"Categories: {len(plan['categories']['rows'])} rows")
    if plan.get('discovery') is not None:
        err = plan['discovery'].get('error')
        lines.append('Live discovery: ' + (f'failed — {err}' if err else 'ok (dashboard page + Cards DB reachable)'))
    return '\n'.join(lines)


# =========================================================================================
# apply — real writes. NOT invoked by this module's own tests or by this task's author;
# left fully implemented for the orchestrator to run later, after review.
# =========================================================================================
def ensure_database(transport, id_cache, title):
    cached = id_cache.database_id(title)
    if cached:
        return cached
    db = transport.create_database(DASHBOARD_PAGE_ID, title, PROPERTY_SCHEMAS[title])
    id_cache.set_database_id(title, db['id'])
    time.sleep(RATE_LIMIT_SLEEP_S)
    return db['id']


def _row_to_properties(db_title, row):
    key_prop = KEY_PROPERTY[db_title]
    props = {}
    for name, spec in PROPERTY_SCHEMAS[db_title].items():
        field = _field_name(db_title, name)
        value = row.get(field)
        kind = next(iter(spec))
        if kind == 'title':
            props[name] = {'title': nb.rich_text(str(value if value is not None else row.get(field, '')))}
        elif kind == 'rich_text':
            v = value
            if isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            props[name] = {'rich_text': nb.rich_text('' if v is None else str(v))}
        elif kind == 'number':
            props[name] = {'number': value if isinstance(value, (int, float)) else None}
        elif kind == 'url':
            props[name] = {'url': value}
        elif kind == 'date':
            props[name] = {'date': {'start': value}} if value else {'date': None}
        elif kind == 'select':
            props[name] = {'select': {'name': value}} if value else {'select': None}
    # title property is always keyed off the row's declared key field even if its Notion
    # property name doesn't lowercase-match (e.g. 'Run ID' -> 'run_id')
    key_field = key_prop.lower().replace(' ', '_')
    props[key_prop] = {'title': nb.rich_text(str(row.get(key_field, '')))}
    return props, str(row.get(key_field, ''))


def upsert_rows(transport, id_cache, db_title, rows):
    """Generic idempotent upsert: cache hit -> PATCH; cache miss -> query by key property,
    then PATCH or POST. Shared by reels/accounts/cards/runs so each keeps exactly one
    field-mapping function (`_row_to_properties`) instead of four near-duplicate loops."""
    db_id = ensure_database(transport, id_cache, db_title)
    created = updated = 0
    for row in rows:
        props, key = _row_to_properties(db_title, row)
        page_id = id_cache.row_id(db_title, key)
        if not page_id:
            page_id = transport.find_page_by_key(db_id, KEY_PROPERTY[db_title], key)
            time.sleep(RATE_LIMIT_SLEEP_S)
        if page_id:
            transport.update_page_properties(page_id, props)
            updated += 1
        else:
            page = transport.create_page({'database_id': db_id}, props)
            id_cache.set_row_id(db_title, key, page['id'])
            created += 1
        time.sleep(RATE_LIMIT_SLEEP_S)
    return {'created': created, 'updated': updated}


def apply_plan(con, plan, id_cache=None, limit=None):
    """Executes what `build_plan` described. Requires NOTION_TOKEN; never called by
    this module's CLI in this task, kept ready for the orchestrator's later run."""
    id_cache = id_cache or IdCache()
    transport = LiveTransport()
    result = {}

    if 'dashboard' in plan:
        sections = {
            'architecture': architecture_section(con), 'data_coverage': data_coverage_section(con),
            'analytics': analytics_section(con), 'insights': insights_section(con),
            'hypotheses': hypotheses_section(con), 'legacy': legacy_section(),
        }
        blocks = build_dashboard_blocks(sections)
        transport.replace_children(DASHBOARD_PAGE_ID, blocks)
        result['dashboard'] = {'blocks_written': nb.count_blocks(blocks)}

    if 'databases' in plan:
        for title in NEW_DATABASES:
            ensure_database(transport, id_cache, title)
        result['databases'] = {t: id_cache.database_id(t) for t in NEW_DATABASES}

    if 'reels_analysis' in plan:
        rows = reels_analysis_rows(con, limit=limit)
        result['reels_analysis'] = upsert_rows(transport, id_cache, 'Reels analysis', rows)

    if 'accounts_analysis' in plan:
        result['accounts_analysis'] = upsert_rows(transport, id_cache, 'Accounts analysis',
                                                  accounts_analysis_rows(con))

    if 'cards_v2' in plan:
        result['cards_v2'] = upsert_rows(transport, id_cache, 'Cards v2', cards_rows(con))

    if 'runs' in plan:
        result['runs'] = upsert_rows(transport, id_cache, 'Runs', runs_rows(con))

    if 'insights' in plan:
        result['insights'] = upsert_rows(transport, id_cache, 'Insights', insights_rows(con))

    if 'hypotheses' in plan:
        result['hypotheses'] = upsert_rows(transport, id_cache, 'Hypotheses', hypotheses_rows(con))

    if 'categories' in plan:
        result['categories'] = upsert_rows(transport, id_cache, 'Categories', plan['categories']['rows'])

    return result


# =========================================================================================
# CLI
# =========================================================================================
def build_arg_parser():
    ap = argparse.ArgumentParser(prog='notion_sync', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--dry', action='store_true', help='Print the plan only. Default.')
    mode.add_argument('--apply', action='store_true',
                      help='Execute the plan against Notion. Requires explicit review of a --dry '
                           'plan first — the orchestrator runs this, not this module\'s own tests.')
    ap.add_argument('--scope', choices=SCOPES, default='all')
    ap.add_argument('--limit', type=int, default=None,
                    help='Cap Reels analysis rows to the top N by score.')
    ap.add_argument('--discover', action='store_true',
                    help='--dry only: also do a read-only GET on the dashboard page and the '
                         'reused Cards DB to confirm they are reachable. Off by default so --dry '
                         'never needs the network or a token.')
    ap.add_argument('--out', default=str(PLAN_OUT_PATH), help='Where --dry writes the plan markdown.')
    return ap


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    apply_mode = bool(args.apply)
    con = db_util.connect()
    id_cache = IdCache()

    plan = build_plan(con, scope=args.scope, limit=args.limit, discover=args.discover, id_cache=id_cache)
    md = render_plan_markdown(plan)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding='utf-8')
    print(render_plan_summary(plan))
    rel = out_path.relative_to(ROOT) if out_path.is_absolute() and ROOT in out_path.parents else out_path
    print(f'\nfull plan written to {rel}')
    if not apply_mode:
        return 0

    # --apply: the plan reviewed on 2026-09-12 (reports/notion-sync-plan.md) is approved by the
    # orchestrator; execute it. Requires NOTION_TOKEN in the environment/.env.
    try:
        notion.env('NOTION_TOKEN')          # same loader notion.py uses (environment, then .env)
    except SystemExit:
        print('NOTION_TOKEN not configured — nothing applied.', file=sys.stderr)
        return 2
    print('\napplying plan to Notion ...', flush=True)
    result = apply_plan(con, plan, id_cache=id_cache, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
