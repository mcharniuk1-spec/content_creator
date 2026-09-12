"""Tests for engine.charts on a synthetic corpus (no dependency on data/radar.db).

Two databases:

    rich_con    5 creators x 10 videos, semantic/visual/script features on most of them
                -> most charts should actually draw and produce a PNG + sidecar.
    thin_con    5 creators x 1 video, no semantic/visual features at all
                -> every category/feature chart must skip gracefully (n<5), no PNG,
                   sidecar carries status='skipped' + reason, and the whole run must not
                   raise even though almost nothing is populated.

    python3 -m pytest tests/test_charts.py -q
"""
import json
import os
import sqlite3
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import db as legacy_db  # noqa: E402
from engine import charts, corpus, schema, stats  # noqa: E402

DAY = 86400
TS0 = 1_750_000_000


def _fresh_db(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(legacy_db.SCHEMA)
    schema.migrate(con)
    con.commit()
    return con


def _insert_reel(con, snapshot_id, code, pk, username, ts, play, dur=30.0):
    con.execute(
        'INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play, likes, comm, '
        'resh, save, dur, cap, followers) VALUES (?,?,?,?,?,"clips",?,?,?,?,?,?,"",?)',
        (snapshot_id, code, pk, username, ts, play,
         int(play * 0.05), int(play * 0.001), int(play * 0.01), int(play * 0.008), dur, 50000))


def _script_json(hook_s, setup_s, total_s, total_words):
    return {
        'part_source': 'beats',
        'hook_s': hook_s, 'hook_words': int(hook_s * 3), 'hook_share': round(hook_s / total_s, 4),
        'setup_s': setup_s, 'setup_words': int(setup_s * 3), 'setup_share': round(setup_s / total_s, 4),
        'total_s': total_s, 'total_words': total_words,
    }


def _visual_json(a_roll, split, transitions):
    return {
        'a_roll_share': a_roll, 'b_roll_share': round(1 - a_roll, 4), 'split_share': split,
        'screen_share': 0.0, 'transitions': transitions,
        'cut_metric_quality': 'ffmpeg_scene_0.35_count_only',
    }


TOPICS = ['topic_a', 'topic_b']
PAINS = ['pain_a', 'pain_b']
HOOKS = ['bold_claim', 'question']
CTAS = ['follow', 'comment_keyword']
NARRATIVES = ['myth_bust', 'tutorial_steps']
FRAMES = ['A_ROLL_CLOSE_UP', 'SCREEN_RECORDING']
SEQUENCES = ['A_ROLL_CLOSE_UP>B_ROLL_CONTEXT', 'SCREEN_RECORDING>A_ROLL_CLOSE_UP']


@pytest.fixture()
def rich_con(tmp_path):
    con = _fresh_db(tmp_path / 'rich.db')
    con.execute("INSERT INTO snapshots (id, taken, done) VALUES (1, '2026-09-10', 1)")

    creators = [(1, 'alpha'), (2, 'beta'), (3, 'gamma'), (4, 'delta'), (5, 'epsilon')]
    n_per_creator = 10
    for pk, name in creators:
        for i in range(n_per_creator):
            code = '%s%02d' % (name, i)
            play = 5000 + i * 900 + (8000 if i == n_per_creator - 1 else 0)
            _insert_reel(con, 1, code, pk, name, TS0 + i * 3 * DAY, play, dur=20.0 + i)
    con.commit()

    # semantic/visual/script features on most codes (28 of 50), varied across the closed
    # vocabularies so every categorical chart clears MIN_N=5.
    idx = 0
    for pk, name in creators:
        for i in range(n_per_creator):
            code = '%s%02d' % (name, i)
            if idx >= 28:
                idx += 1
                continue
            fj = {
                'script': _script_json(2.0 + (i % 4) * 0.5, 3.0, 20.0 + i, 60 + i * 4),
                'visual': _visual_json(0.6 + 0.02 * (i % 3), 0.1 * (i % 2), {'hard_cut_or_more': 3, 'unknown': 1}),
                'semantics_extra': {'tools_mentioned': ['tool_x'] if i % 2 == 0 else ['tool_y']},
            }
            con.execute(
                'INSERT INTO video_features (code, features_version, computed_at, topic, pain, '
                'hook_type, cta_type, narrative, first_frame_type, visual_sequence, hook_s, '
                'total_words, scenes_n, cuts_per_min, cut_metric_quality, a_roll_share, '
                'split_share, features_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (code, 'fv-1', '2026-09-11T00:00:00Z',
                 TOPICS[idx % 2], PAINS[idx % 2], HOOKS[idx % 2], CTAS[idx % 2], NARRATIVES[idx % 2],
                 FRAMES[idx % 2], SEQUENCES[idx % 2], 2.0 + (i % 4) * 0.5, 60 + i * 4, 5 + i % 4,
                 40.0 + i, 'ffmpeg_scene_0.35_count_only', 0.6 + 0.02 * (i % 3), 0.1 * (i % 2),
                 json.dumps(fj)))
            idx += 1
    con.commit()

    stats.creator_stats(con)
    stats.video_perf(con)
    con.commit()
    yield con
    con.close()


@pytest.fixture()
def thin_con(tmp_path):
    """5 creators, 1 video each: enough rows (n=5) for the metric-only charts (duration,
    creator_median_views, corpus_coverage_funnel, ...) but zero semantic/visual/script
    features anywhere, so every category/feature chart must skip."""
    con = _fresh_db(tmp_path / 'thin.db')
    con.execute("INSERT INTO snapshots (id, taken, done) VALUES (1, '2026-09-10', 1)")
    names = ['solo', 'duo', 'trio', 'quad', 'quint']
    for pk, name in enumerate(names, start=1):
        _insert_reel(con, 1, name, pk, name, TS0 + pk * DAY, 1000 + pk * 200, dur=15.0 + pk)
    con.commit()
    stats.creator_stats(con)
    stats.video_perf(con)
    con.commit()
    yield con
    con.close()


# ---------------------------------------------------------------------------
# rich corpus: charts actually draw
# ---------------------------------------------------------------------------

def test_generate_produces_index_and_files(tmp_path, rich_con):
    out_dir = str(tmp_path / 'charts_out')
    index, index_path = charts.generate(rich_con, out_dir)
    assert os.path.exists(index_path)
    with open(index_path) as fh:
        idx_doc = json.load(fh)
    assert idx_doc['charts'] == index
    assert len(index) >= 15  # every named chart in the spec, at least

    ok = [c for c in index if c['status'] == 'ok']
    assert len(ok) >= 10, 'expected most charts to draw on a 30-video, 3-creator corpus'

    for c in ok:
        png = os.path.join(out_dir, c['png'])
        assert os.path.exists(png), c['name']
        assert os.path.getsize(png) > 0
        sidecar_path = os.path.join(out_dir, c['name'] + '.json')
        with open(sidecar_path) as fh:
            sc = json.load(fh)
        for key in ('title', 'n', 'source', 'variables', 'method', 'interpretation', 'limitations'):
            assert key in sc, (c['name'], key)
        assert sc['interpretation'] == ''
        assert 'n=%d' % c['n'] in sc['source'] or str(c['n']) in sc['title'] or c['n'] == sc['n']
        assert sc['n'] == c['n']
        assert 'selection-bias' not in sc['limitations'].lower() or 'not a random sample' in sc['limitations'].lower() \
            or 'construction' in sc['limitations'].lower()


def test_creator_median_views_chart_shape(tmp_path, rich_con):
    out_dir = str(tmp_path / 'charts_out2')
    index, _ = charts.generate(rich_con, out_dir)
    row = next(c for c in index if c['name'] == 'creator_median_views')
    assert row['status'] == 'ok'
    assert row['n'] == 5  # 5 creators in creator_stats


def test_corpus_coverage_funnel_present(tmp_path, rich_con):
    out_dir = str(tmp_path / 'charts_out3')
    index, _ = charts.generate(rich_con, out_dir)
    row = next(c for c in index if c['name'] == 'corpus_coverage_funnel')
    assert row['status'] == 'ok'
    assert row['n'] == 50


# ---------------------------------------------------------------------------
# thin corpus: skip path
# ---------------------------------------------------------------------------

def test_thin_corpus_skips_gracefully(tmp_path, thin_con):
    out_dir = str(tmp_path / 'charts_thin')
    index, index_path = charts.generate(thin_con, out_dir)
    by_name = {c['name']: c for c in index}

    # no semantic/visual features anywhere -> every categorical/script/visual chart skips
    for name in ('topic_vs_performance', 'pain_vs_performance', 'hook_type_vs_performance',
                'cta_type_vs_performance', 'script_length_vs_performance',
                'hook_length_vs_performance', 'scenes_vs_performance',
                'cuts_per_min_vs_performance', 'a_roll_share_vs_performance',
                'split_share_vs_performance', 'script_parts_strong_vs_weak',
                'visual_sequence_top10'):
        assert by_name[name]['status'] == 'skipped', name
        assert 'reason' in by_name[name]
        png = os.path.join(out_dir, name + '.png')
        assert not os.path.exists(png), name
        sidecar_path = os.path.join(out_dir, name + '.json')
        with open(sidecar_path) as fh:
            sc = json.load(fh)
        assert sc['status'] == 'skipped'
        assert sc['reason']

    # duration and share/save-rate charts and creator charts still have enough rows (4 videos,
    # 2 creators) to draw -- n>=MIN_N is per-chart, not per-corpus
    assert by_name['duration_vs_performance']['status'] == 'ok'
    assert by_name['creator_median_views']['status'] == 'ok'

    with open(index_path) as fh:
        idx_doc = json.load(fh)
    assert 'generated_at' in idx_doc


def test_view_lift_distribution_skips_below_min_n(tmp_path):
    con = _fresh_db(tmp_path / 'tiny.db')
    con.execute("INSERT INTO snapshots (id, taken, done) VALUES (1, '2026-09-10', 1)")
    for i in range(2):
        _insert_reel(con, 1, 'only%d' % i, 1, 'onlyone', TS0 + i * DAY, 1000 + i * 50)
    con.commit()
    stats.creator_stats(con)
    stats.video_perf(con)
    con.commit()

    out_dir = str(tmp_path / 'out')
    index, _ = charts.generate(con, out_dir)
    row = next(c for c in index if c['name'] == 'video_view_lift_distribution')
    assert row['status'] == 'skipped'
    assert 'n=2' in row['reason']
    con.close()


def test_charts_generate_does_not_write_to_db(tmp_path, rich_con):
    before = {t: rich_con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
              for t in ('reels', 'video_features', 'creator_stats', 'runs', 'jobs')}
    charts.generate(rich_con, str(tmp_path / 'ro_check'))
    after = {t: rich_con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
            for t in ('reels', 'video_features', 'creator_stats', 'runs', 'jobs')}
    assert before == after
