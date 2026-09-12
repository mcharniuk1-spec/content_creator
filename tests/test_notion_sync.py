"""Tests for engine.notion_sync / engine.notion_blocks.

Self-contained: every test builds a small synthetic SQLite database (legacy schema +
`engine.schema.migrate`), the same pattern `tests/test_engine_schema.py` uses. Nothing
here reads `data/radar.db`, and nothing here makes a real network call — every Notion
transport is a fake `call(method, path, body)` function, exactly like `test_notion.py`'s
`fake_call`. The one thing every test in this file is ultimately protecting is the hard
rule this module was built under: **--dry must never write to Notion.**

    python3 -m pytest tests/test_notion_sync.py -q
"""
import json
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import db as legacy_db                                     # noqa: E402
from engine import notion_blocks as nb                     # noqa: E402
from engine import notion_sync as ns                        # noqa: E402
from engine import schema, state                            # noqa: E402
from engine.db_util import canonical_json                   # noqa: E402


# --------------------------------------------------------------------------- #
# fixture: a small, fully-migrated database exercising every *_rows() function
# --------------------------------------------------------------------------- #
@pytest.fixture
def con(tmp_path):
    c = sqlite3.connect(tmp_path / 'test.db')
    c.row_factory = sqlite3.Row
    c.executescript(legacy_db.SCHEMA)
    c.commit()
    schema.migrate(c)

    c.execute("INSERT INTO snapshots (id, taken, done) VALUES (1,'2026-09-10',1)")
    c.execute("INSERT INTO accounts (pk, username, follower_count, tag, status) "
             "VALUES (11,'alice',5000,'core','active')")
    c.execute("INSERT INTO accounts (pk, username, follower_count, tag, status) "
             "VALUES (22,'bob',8000,'core','active')")

    def reel(code, pk, user, play=1000, likes=50, comm=5, resh=10, save=20, dur=30.0):
        c.execute("INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play, "
                  "likes, comm, resh, save, dur, cap, followers) "
                  "VALUES (1,?,?,?,1760000000,'clip',?,?,?,?,?,?,'cap',5000)",
                  (code, pk, user, play, likes, comm, resh, save, dur))

    reel('READY001', 11, 'alice', play=5000)
    reel('FRAMESONLY1', 11, 'alice', play=800)
    reel('NOTREADY1', 22, 'bob', play=200)

    c.execute("INSERT INTO scores (snapshot_id, code, z, eligible, weights, resh_1k, save_1k) "
             "VALUES (1,'READY001',1.2,1,'ig',2.0,4.0)")
    c.execute("INSERT INTO scores (snapshot_id, code, z, eligible, weights, resh_1k, save_1k) "
             "VALUES (1,'FRAMESONLY1',0.5,1,'ig',1.0,2.0)")

    segs = canonical_json([{'s': 0.0, 'e': 2.0, 't': 'hello there'}])
    c.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
             "VALUES ('READY001','en',10,'hello there',?)", (segs,))
    c.execute("INSERT INTO frames (code, idx, t_sec, path) VALUES ('READY001',0,0.0,'x.jpg')")
    c.execute("INSERT INTO frames (code, idx, t_sec, path) VALUES ('FRAMESONLY1',0,0.0,'y.jpg')")

    c.execute("""INSERT INTO video_features
        (code, features_version, computed_at, topic, pain, hook_type, solution_type, cta_type,
         hook_text, visual_sequence, first_frame_type, scenes_n, cuts, view_lift, robust_z,
         share_rate, save_rate, features_json)
        VALUES ('READY001','vf-v1','2026-09-10T00:00:00Z','ai_tools','time_waste','question',
                'workflow_recipe','follow','Did you know...','HOOK>BODY','A_ROLL_CLOSE_UP',
                5,8,1.5,2.0,0.01,0.02,'{}')""")

    c.execute("INSERT INTO beats (beat_id,code,idx,role,text,analysis_version) "
             "VALUES ('b1','READY001',0,'hook','hi', 'ta-v1')")
    c.execute("INSERT INTO beats (beat_id,code,idx,role,text,analysis_version) "
             "VALUES ('b2','READY001',1,'cta','bye','ta-v1')")

    c.execute("""INSERT INTO creator_stats
        (pk, snapshot_id, username, followers, n_videos, median_play, mean_play, mad_play,
         iqr_play, sd_play, cv_play, consistency_score, reliability, computed_at, stats_version)
        VALUES (11, 1, 'alice', 5000, 2, 2900, 2900, 100, 200, 300, 0.1, 0.9, 'CONSISTENT',
                '2026-09-10T00:00:00Z', 'cs-v1')""")

    c.execute("""INSERT INTO cards_v2
        (card_id, title, format, status, refs_json, total_s, total_words, script_json,
         created_at, updated_at)
        VALUES ('M2-T01','Test card','M2 Radar','DRAFT','["READY001"]',45.0,120,'{"hook":"hi"}',
                '2026-09-10T00:00:00Z','2026-09-10T00:00:00Z')""")

    run_id = state.make_run_id()
    c.execute("INSERT INTO runs (run_id, started_at, kind, git_commit, status) "
             "VALUES (?,'2026-09-10T00:00:00Z','manual','abc123','DONE')", (run_id,))
    c.commit()
    return c


# --------------------------------------------------------------------------- #
# engine/notion_blocks.py
# --------------------------------------------------------------------------- #
def test_rich_text_chunks_long_strings_under_2000_chars():
    long = 'x' * 4500
    chunks = nb.rich_text(long)
    assert len(chunks) == 3
    assert all(len(o['text']['content']) <= nb.RICH_TEXT_LIMIT for o in chunks)
    assert ''.join(o['text']['content'] for o in chunks) == long


def test_rich_text_empty_string_still_returns_one_object():
    assert nb.rich_text('') == [{'type': 'text', 'text': {'content': ''}}]
    assert nb.rich_text(None) == [{'type': 'text', 'text': {'content': ''}}]


def test_rich_text_annotations_and_link():
    out = nb.rich_text('hi', bold=True, link='https://x.example')
    assert out[0]['annotations'] == {'bold': True}
    assert out[0]['text']['link'] == {'url': 'https://x.example'}


def test_chunk_blocks_respects_100_per_request():
    blocks = [nb.paragraph(str(i)) for i in range(250)]
    chunks = list(nb.chunk_blocks(blocks))
    assert len(chunks) == 3
    assert [len(c) for c in chunks] == [100, 100, 50]
    assert sum(len(c) for c in chunks) == 250


def test_count_blocks_counts_nested_toggle_children():
    inner = [nb.paragraph('a'), nb.paragraph('b')]
    blocks = [nb.heading('H'), nb.toggle('T', inner)]
    assert nb.count_blocks(blocks) == 1 + 1 + len(inner)


def test_toggle_rejects_more_than_100_children():
    with pytest.raises(ValueError):
        nb.toggle('T', [nb.paragraph(str(i)) for i in range(101)])


def test_table_pads_short_rows_to_header_width():
    t = nb.table(['a', 'b', 'c'], [['x']])
    row = t['table']['children'][1]['table_row']['cells']
    assert len(row) == 3
    assert row[1][0]['text']['content'] == ''


def test_heading_rejects_invalid_level():
    with pytest.raises(ValueError):
        nb.heading('x', level=4)


# --------------------------------------------------------------------------- #
# data gathering
# --------------------------------------------------------------------------- #
def test_architecture_section_reports_version_and_providers(con):
    a = ns.architecture_section(con)
    assert a['engine_version']
    assert isinstance(a['providers'], list) and a['providers']
    assert {'name', 'kind', 'role', 'state', 'detail'} <= set(a['providers'][0])


def test_data_coverage_matches_seeded_corpus(con):
    cov = ns.data_coverage_section(con)
    assert cov['creators'] == 2
    assert cov['reels_ingested'] == 3
    assert cov['fully_analyzed'] == 1          # only READY001 has both transcript + frames
    assert cov['cards'] == 1


def test_reels_analysis_rows_excludes_ingested_not_analyzed(con):
    rows = ns.reels_analysis_rows(con)
    codes = {r['code'] for r in rows}
    assert codes == {'READY001', 'FRAMESONLY1'}
    assert 'NOTREADY1' not in codes


def test_reels_analysis_rows_ranks_by_robust_z_then_score(con):
    rows = ns.reels_analysis_rows(con)
    assert rows[0]['code'] == 'READY001'       # robust_z=2.0 beats FRAMESONLY1's z=0.5


def test_reels_analysis_rows_respects_limit(con):
    rows = ns.reels_analysis_rows(con, limit=1)
    assert len(rows) == 1
    assert rows[0]['code'] == 'READY001'


def test_reels_analysis_rows_carries_beats_summary_and_used_in_cards(con):
    rows = {r['code']: r for r in ns.reels_analysis_rows(con)}
    assert rows['READY001']['beats_summary'] == '2 beats: hook > cta'
    assert rows['READY001']['used_in_cards'] == ['M2-T01']
    assert rows['FRAMESONLY1']['beats_summary'] is None
    assert rows['FRAMESONLY1']['hook_type'] is None   # no video_features row for it


def test_accounts_analysis_rows_joins_creator_stats_and_best_reel(con):
    rows = ns.accounts_analysis_rows(con)
    assert len(rows) == 1
    assert rows[0]['username'] == 'alice'
    assert rows[0]['followers'] == 5000
    assert rows[0]['top_reel'] == 'https://instagram.com/reel/READY001'


def test_cards_rows_reads_json_file_when_present(con, tmp_path, monkeypatch):
    cards_dir = tmp_path / 'cards'
    cards_dir.mkdir()
    (cards_dir / 'M2-T01.json').write_text(json.dumps({'script': {'hook': 'from-json'}}))
    monkeypatch.setattr(ns, 'ROOT', tmp_path)
    rows = ns.cards_rows(con)
    assert len(rows) == 1
    assert 'from-json' in rows[0]['script']
    assert rows[0]['json_path'] == 'cards/M2-T01.json'


def test_cards_rows_falls_back_to_db_script_json_without_file(con, tmp_path, monkeypatch):
    monkeypatch.setattr(ns, 'ROOT', tmp_path)   # no cards/ dir here at all
    rows = ns.cards_rows(con)
    assert '"hook"' in rows[0]['script'] or 'hi' in rows[0]['script']


def test_categories_rows_empty_when_video_features_has_no_rows(con):
    con.execute('DELETE FROM video_features')
    con.commit()
    assert ns.categories_rows(con) == []


def test_categories_rows_reports_insufficient_confidence_for_small_n(con):
    rows = ns.categories_rows(con)
    assert rows                                   # our one video_features row produces entries
    assert all(r['confidence'] == 'INSUFFICIENT' for r in rows)  # n=1 everywhere


def test_runs_rows_carries_derived_fields(con):
    rows = ns.runs_rows(con)
    assert len(rows) == 1
    assert rows[0]['date'] == '2026-09-10'
    assert rows[0]['git_commit'] == 'abc123'


# --------------------------------------------------------------------------- #
# property mapping (business row dict -> Notion `properties` JSON)
# --------------------------------------------------------------------------- #
def test_row_to_properties_reels_analysis_maps_mismatched_field_names(con):
    row = ns.reels_analysis_rows(con)[0]
    props, key = ns._row_to_properties('Reels analysis', row)
    assert key == 'READY001'
    assert props['Code']['title'][0]['text']['content'] == 'READY001'
    assert props['Comments']['number'] == row['comm']
    assert props['Reshares']['number'] == row['resh']
    assert props['Saves']['number'] == row['save']
    assert props['Scenes']['number'] == row['scenes_n']
    assert props['View lift']['number'] == row['lift']
    assert props['URL']['url'] == row['url']


def test_row_to_properties_accounts_analysis_maps_mismatched_field_names(con):
    row = ns.accounts_analysis_rows(con)[0]
    props, key = ns._row_to_properties('Accounts analysis', row)
    assert key == 'alice'
    assert props['Videos']['number'] == row['n_videos']
    assert props['Consistency']['number'] == row['consistency_score']
    assert props['Top reels']['rich_text'][0]['text']['content'] == row['top_reel']


def test_row_to_properties_cards_v2_maps_mismatched_field_names(con):
    row = ns.cards_rows(con)[0]
    props, key = ns._row_to_properties('Cards v2', row)
    assert key == 'M2-T01'
    assert props['Hypothesis']['rich_text'][0]['text']['content'] == ''   # hypothesis_id is None
    assert props['Total seconds']['number'] == row['total_s']
    assert props['Words']['number'] == row['total_words']


def test_row_to_properties_select_field_becomes_none_when_value_missing():
    props, _ = ns._row_to_properties('Categories', {'label': 'x', 'kind': None, 'n': 1})
    assert props['Kind']['select'] is None


def test_row_to_properties_select_field_set_when_value_present():
    props, _ = ns._row_to_properties('Categories', {'label': 'x', 'kind': 'topic', 'n': 1})
    assert props['Kind']['select'] == {'name': 'topic'}


def test_row_to_properties_number_ignores_non_numeric_value():
    props, _ = ns._row_to_properties('Categories', {'label': 'x', 'kind': 'topic', 'n': 'oops'})
    assert props['N']['number'] is None


# --------------------------------------------------------------------------- #
# transport — read-only guarantee
# --------------------------------------------------------------------------- #
def test_readonly_transport_only_ever_logs_reads():
    fake_calls = []

    def fake_call(method, path, body=None, **kw):
        fake_calls.append((method, path))
        if path.startswith('/pages'):
            return {'id': 'p1'}
        return {'id': 'd1', 'title': [{'plain_text': 'Cards'}], 'properties': {'Name': {}}}

    t = ns.ReadOnlyTransport(call=fake_call)
    t.get_page('abc')
    t.get_database('def')
    assert t.calls == [('read', 'GET', '/pages/abc'), ('read', 'GET', '/databases/def')]
    assert all(kind == 'read' for kind, _, _ in t.calls)
    assert not hasattr(t, 'create_page')   # the write surface simply does not exist on this class


def test_discover_never_raises_when_transport_fails():
    def boom(method, path, body=None, **kw):
        raise SystemExit('Notion ответил 401: unauthorized')

    orig = ns.ReadOnlyTransport
    ns.ReadOnlyTransport = lambda call=None: orig(call=boom)
    try:
        out = ns._discover(ns.IdCache(path=pathlib.Path('/tmp/does-not-exist-notion-ids.json')))
    finally:
        ns.ReadOnlyTransport = orig
    assert out['error'] is not None
    assert out['dashboard_page'] is None


def test_build_plan_dry_never_constructs_live_transport(con, tmp_path, monkeypatch):
    """The single most important test in this file: --dry's whole code path (`build_plan`,
    with `discover=False`, matching the CLI default) must never touch `LiveTransport` —
    the only class in this module capable of a write. If it did, this test would blow up
    instead of silently passing."""
    def boom(*a, **kw):
        raise AssertionError('LiveTransport must never be constructed during --dry')

    monkeypatch.setattr(ns, 'LiveTransport', boom)
    cache = ns.IdCache(path=tmp_path / 'notion_ids.json')
    plan = ns.build_plan(con, scope='all', discover=False, id_cache=cache)
    assert plan['scope'] == 'all'
    assert 'dashboard' in plan and 'databases' in plan
    assert not cache.path.exists()   # --dry writes no id-cache file either


def test_build_plan_writes_markdown_and_summary_are_consistent(con, tmp_path):
    cache = ns.IdCache(path=tmp_path / 'notion_ids.json')
    plan = ns.build_plan(con, scope='all', discover=False, id_cache=cache)
    md = ns.render_plan_markdown(plan)
    summary = ns.render_plan_summary(plan)
    assert 'DRY (no writes made)' in md
    assert 'Reels analysis' in md
    assert str(plan['reels_analysis']['row_count']) in summary


# --------------------------------------------------------------------------- #
# idempotent upsert (apply-path logic, exercised only against a fake transport)
# --------------------------------------------------------------------------- #
class FakeLiveTransport(ns.LiveTransport):
    """A LiveTransport whose HTTP layer is a Python dict instead of curl+Notion."""

    def __init__(self):
        super().__init__(call=self._route)
        self.created_pages = []
        self.updated_pages = []
        self.existing_by_key = {}   # key -> page_id, simulates rows already in Notion

    def _route(self, method, path, body=None):
        raise AssertionError(f'unexpected raw call {method} {path}')

    # override the higher-level methods directly — simpler than faking raw HTTP bodies
    def create_database(self, parent_page_id, title, properties_schema):
        self.calls.append(('write', 'POST', '/databases'))
        return {'id': f'db-{title}'}

    def find_page_by_key(self, db_id, key_property, value):
        self.calls.append(('read', 'POST', f'/databases/{db_id}/query'))
        return self.existing_by_key.get(value)

    def create_page(self, parent, properties, children=None):
        self.calls.append(('write', 'POST', '/pages'))
        pid = f"new-{len(self.created_pages)}"
        self.created_pages.append((parent, properties))
        return {'id': pid}

    def update_page_properties(self, page_id, properties):
        self.calls.append(('write', 'PATCH', f'/pages/{page_id}'))
        self.updated_pages.append((page_id, properties))
        return {}


def test_upsert_rows_creates_new_and_updates_existing(con, tmp_path):
    rows = ns.reels_analysis_rows(con)   # READY001, FRAMESONLY1
    transport = FakeLiveTransport()
    transport.existing_by_key['FRAMESONLY1'] = 'page-existing-1'
    cache = ns.IdCache(path=tmp_path / 'notion_ids.json')

    result = ns.upsert_rows(transport, cache, 'Reels analysis', rows)

    assert result == {'created': 1, 'updated': 1}
    assert len(transport.created_pages) == 1
    assert transport.updated_pages[0][0] == 'page-existing-1'
    # the write surface was used, but only through the tagged methods — no stray raw calls
    assert all(kind in ('read', 'write') for kind, _, _ in transport.calls)


def test_upsert_rows_caches_new_page_ids_for_resumability(con, tmp_path):
    rows = ns.reels_analysis_rows(con)
    transport = FakeLiveTransport()
    cache_path = tmp_path / 'notion_ids.json'
    cache = ns.IdCache(path=cache_path)

    ns.upsert_rows(transport, cache, 'Reels analysis', rows)
    assert cache.row_id('Reels analysis', 'READY001') == 'new-0'
    assert json.loads(cache_path.read_text())['rows']['Reels analysis']['READY001'] == 'new-0'

    # a second run with a fresh IdCache loaded from disk must not re-query Notion for a
    # row it already knows the page id of
    cache2 = ns.IdCache(path=cache_path)
    transport2 = FakeLiveTransport()
    query_calls_before = len(transport2.calls)
    ns.upsert_rows(transport2, cache2, 'Reels analysis', rows[:1])
    query_paths = [p for kind, m, p in transport2.calls if 'query' in p]
    assert query_paths == []   # cached hit -> straight to update, no find_page_by_key call
    assert transport2.updated_pages[0][0] == 'new-0'


def test_ensure_database_reuses_cached_id(tmp_path):
    transport = FakeLiveTransport()
    cache = ns.IdCache(path=tmp_path / 'notion_ids.json')
    id1 = ns.ensure_database(transport, cache, 'Runs')
    id2 = ns.ensure_database(transport, cache, 'Runs')
    assert id1 == id2
    create_calls = [c for c in transport.calls if c[1] == 'POST' and c[2] == '/databases']
    assert len(create_calls) == 1   # second ensure_database call was a cache hit


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_apply_is_refused_without_running_anything(con, monkeypatch, capsys):
    monkeypatch.setattr(ns.db_util, 'connect', lambda *a, **kw: con)
    monkeypatch.setattr(ns, 'LiveTransport', lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError('must not be constructed')))
    rc = ns.main(['--apply'])
    assert rc == 2
    assert 'refused' in capsys.readouterr().err


def test_cli_dry_writes_plan_file(con, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ns.db_util, 'connect', lambda *a, **kw: con)
    out_file = tmp_path / 'plan.md'
    rc = ns.main(['--dry', '--scope', 'reels', '--out', str(out_file)])
    assert rc == 0
    assert out_file.exists()
    assert 'Reels analysis' in out_file.read_text()
    assert 'plan written to' in capsys.readouterr().out
