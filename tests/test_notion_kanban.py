"""engine/notion_kanban.py + engine/kanban_tasks.py — the board is valid, English, idempotent,
and never talks to Notion unless apply() is called with a transport."""
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import kanban_tasks as kt          # noqa: E402
from engine import notion_kanban as nk         # noqa: E402
from engine import notion_sync as ns           # noqa: E402
from engine import schema, state               # noqa: E402
from engine import notion_blocks as nb         # noqa: E402


@pytest.fixture
def con(tmp_path):
    c = sqlite3.connect(tmp_path / 'k.db')
    c.row_factory = sqlite3.Row
    schema.migrate(c)
    c.execute("INSERT INTO runs (run_id, kind, started_at, status) VALUES ('r1','manual','2026-09-13T00:00:00Z','DONE')")
    for i, st in enumerate(('DONE', 'DONE', 'FAILED')):
        c.execute("INSERT INTO jobs (job_id, run_id, stage, state, entity_kind, entity_id, started_at, finished_at) "
                  "VALUES (?, 'r1', 'CARD_GENERATION', ?, 'card', 'C', '2026-09-13T00:00:00Z', '2026-09-13T00:01:00Z')",
                  (f'j-{i}', st))
    c.commit()
    return c


def test_tasks_are_well_formed():
    keys = [t[1] for t in kt.TASKS]
    assert len(keys) == len(set(keys)), 'task keys must be unique (they are the Notion idempotency key)'
    for order, key, block, stage, status, owner, evidence, note in kt.TASKS:
        assert isinstance(order, int)
        assert block in kt.BLOCKS, key
        assert stage in nk.STAGE_CHOICES, (key, stage)
        assert status in kt.STATUSES, key
        assert owner in kt.OWNERS, key
        assert evidence and note, key
        if status == 'Blocked':
            assert any(w in note.lower() for w in ('waiting', 'decision', 'depend')), \
                f'{key}: a Blocked task must name what it waits for'


def test_tasks_are_english_only():
    text = ' '.join(f'{t[1]} {t[6]} {t[7]}' for t in kt.TASKS)
    non_ascii_letters = [ch for ch in text if ch.isalpha() and ord(ch) > 127]
    assert not non_ascii_letters, f'non-ASCII letters in kanban tasks: {set(non_ascii_letters)}'


def test_placeholders_all_resolve(con):
    rows, numbers = nk.build_rows(con)
    for r in rows:
        assert '{' not in r['evidence'] and '}' not in r['evidence'], r['key']
    assert len(rows) == len(kt.TASKS) + len(state.STAGES)


def test_stage_rows_reflect_jobs(con):
    rows = {r['key']: r for r in nk.stage_rows(con)}
    cg = rows['stage:CARD_GENERATION']
    assert cg['status'] == 'In progress'          # DONE present but also a FAILED
    assert '2 DONE' in cg['evidence'] and '1 FAILED' in cg['evidence']
    assert rows['stage:VIDEO_RENDER']['status'] == 'Planned'
    assert rows['stage:DISCOVERED']['status'] == 'Done'   # legacy steps count as done


def test_row_properties_match_schema(con):
    rows, _ = nk.build_rows(con)
    props = nk.row_properties(rows[0], updated='2026-09-13T10:00:00Z')
    assert set(props) == set(nk.KANBAN_SCHEMA)
    assert props['Task']['title'][0]['text']['content'] == rows[0]['key']
    assert props['Updated']['date']['start'] == '2026-09-13'
    for name, spec in nk.KANBAN_SCHEMA.items():
        kind = next(iter(spec))
        assert kind in props[name], (name, kind)


def test_review_blocks_are_chunkable_and_linked(con):
    rows, numbers = nk.build_rows(con)
    blocks = nk.review_blocks(rows, numbers, kanban_db_id='db-1')
    assert blocks[2]['type'] == 'link_to_page'
    assert blocks[2]['link_to_page']['database_id'] == 'db-1'
    headings = [b for b in blocks if b['type'] == 'heading_2']
    assert len(headings) == 1 + len(kt.BLOCKS) + 1      # how-to-read + blocks + stage trace
    assert all(len(c) <= nb.BLOCKS_PER_REQUEST for c in nb.chunk_blocks(blocks))
    text = ' '.join(rt['text']['content'] for b in blocks for rt in (b.get(b['type']) or {}).get('rich_text', []))
    assert str(numbers['n_insights']) in text


class FakeTransport:
    def __init__(self):
        self.dbs, self.pages, self.props, self.children = [], [], {}, {}
        self.calls = []

    def create_database(self, parent, title, schema):
        self.dbs.append(title); self.calls.append('create_database')
        return {'id': f'db-{len(self.dbs)}'}

    def create_page(self, parent, properties, children=None):
        pid = f'page-{len(self.pages) + 1}'
        self.pages.append((parent, properties)); self.props[pid] = properties
        self.calls.append('create_page')
        return {'id': pid}

    def update_page_properties(self, page_id, properties):
        self.props[page_id] = properties; self.calls.append('update_page_properties')

    def find_page_by_key(self, db_id, key_property, value):
        return None

    def replace_children(self, page_id, blocks):
        self.children[page_id] = blocks; self.calls.append('replace_children')


def test_apply_is_idempotent(con, tmp_path, monkeypatch):
    monkeypatch.setattr(ns, 'RATE_LIMIT_SLEEP_S', 0)
    cache = ns.IdCache(tmp_path / 'ids.json')
    t = FakeTransport()
    res1 = nk.apply(con, transport=t, id_cache=cache)
    assert res1['created'] == len(kt.TASKS) + len(state.STAGES) and res1['updated'] == 0
    assert cache.database_id(nk.KANBAN_TITLE) == 'db-1'
    assert cache.page_id(nk.REVIEW_TITLE) is not None
    res2 = nk.apply(con, transport=t, id_cache=cache)
    assert res2['created'] == 0 and res2['updated'] == res1['created']
    assert t.dbs == [nk.KANBAN_TITLE]                 # no second database
    assert sum(1 for c in t.calls if c == 'replace_children') == 2
