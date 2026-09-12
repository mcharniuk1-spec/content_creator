"""Statistics on a synthetic corpus where the right answer is known by construction.

Three creators, built to trip the three reliability labels:

    steady    12 videos, plays 9 000-11 000          -> CONSISTENT
    spiky     12 videos, ~1 000 with one 900 000 hit -> HIGH_VARIANCE
    tiny       3 videos                              -> SMALL_SAMPLE

On top of that: the arithmetic of lift / robust z / percentile, the <100-play
denominator guard, small-cell suppression in the categorical contrasts, and that the
cluster bootstrap is reproducible from its seed.
"""
import json
import math
import os
import sqlite3
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import db as legacy_db  # noqa: E402
from engine import corpus, stats  # noqa: E402

STEADY = [9000, 9500, 10000, 10500, 11000, 9800, 10200, 9900, 10100, 9700, 10300, 10400]
SPIKY = [900, 1000, 1100, 950, 1050, 1000, 900000, 980, 1020, 1010, 990, 960]
TINY = [5000, 6000, 7000]

CREATORS = [(1, 'steady', STEADY), (2, 'spiky', SPIKY), (3, 'tiny', TINY)]

DAY = 86400


def build_db(tmp_path, creators=CREATORS, topics=None, low_play_code=True):
    path = str(tmp_path / 'radar.db')
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(legacy_db.SCHEMA)
    corpus.ensure_tables(con)
    con.execute("INSERT INTO snapshots (id, taken, done) VALUES (1, '2026-09-10', 1)")
    ts0 = 1_750_000_000
    for pk, name, plays in creators:
        for i, play in enumerate(plays):
            code = '%s%02d' % (name, i)
            con.execute(
                'INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play,'
                ' likes, comm, resh, save, dur, cap, followers)'
                ' VALUES (1,?,?,?,?,"clips",?,?,?,?,?,?,"",?)',
                (code, pk, name, ts0 + i * 3 * DAY, play,
                 int(play * 0.05), int(play * 0.001), int(play * 0.006), int(play * 0.01),
                 30.0 + i, 100000))
    if low_play_code:
        # one video below the denominator guard
        con.execute('INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play,'
                    ' likes, comm, resh, save, dur, cap, followers)'
                    ' VALUES (1,"steadyLOW",1,"steady",?,"clips",50,10,2,3,4,30.0,"",100000)',
                    (ts0 + 99 * DAY,))
    for code, topic in (topics or []):
        con.execute('INSERT INTO topics (code, topic, source) VALUES (?,?,"manual")', (code, topic))
    con.commit()
    return con


# ---------------------------------------------------------------------------
# creator_stats
# ---------------------------------------------------------------------------

@pytest.fixture()
def con(tmp_path):
    c = build_db(tmp_path)
    yield c
    c.close()


def test_reliability_labels(con):
    rows = {r['username']: r for r in stats.creator_stats(con)}
    assert rows['steady']['reliability'] == 'CONSISTENT'
    assert rows['spiky']['reliability'] == 'HIGH_VARIANCE'
    assert rows['tiny']['reliability'] == 'SMALL_SAMPLE'


def test_creator_stats_written_to_table(con):
    stats.creator_stats(con)
    n = con.execute('SELECT COUNT(*) FROM creator_stats').fetchone()[0]
    assert n == 3
    row = con.execute('SELECT * FROM creator_stats WHERE username="steady"').fetchone()
    assert row['snapshot_id'] == 1
    assert row['stats_version'] == stats.STATS_VERSION
    # re-running must replace, not duplicate (PRIMARY KEY (pk, snapshot_id))
    stats.creator_stats(con)
    assert con.execute('SELECT COUNT(*) FROM creator_stats').fetchone()[0] == 3


def test_consistency_and_dispersion_arithmetic(con):
    rows = {r['username']: r for r in stats.creator_stats(con)}
    steady, spiky = rows['steady'], rows['spiky']
    assert steady['cv_play'] < spiky['cv_play']
    assert steady['consistency_score'] > spiky['consistency_score']
    assert steady['consistency_score'] == pytest.approx(1 / (1 + steady['cv_play']), abs=5e-5)
    # the 900k hit is one of 12 videos and at least 2 robust-z above the creator's norm
    assert spiky['outlier_share'] == pytest.approx(1 / 12, abs=5e-5)
    assert spiky['high_performer_share'] == pytest.approx(1 / 12, abs=5e-5)
    assert steady['high_performer_share'] == 0.0


def test_posts_per_week(con):
    rows = {r['username']: r for r in stats.creator_stats(con)}
    # steady has 13 videos (12 + the low-play one) spanning ts0 .. ts0+99 days
    steady = rows['steady']
    assert steady['n_videos'] == 13
    assert steady['posts_per_week'] == pytest.approx(13 / (99 / 7.0), rel=1e-3)


def test_small_sample_creator_still_gets_numbers(con):
    rows = {r['username']: r for r in stats.creator_stats(con)}
    tiny = rows['tiny']
    assert tiny['n_videos'] == 3
    assert tiny['median_play'] == 6000
    assert tiny['reliability'] == 'SMALL_SAMPLE'


# ---------------------------------------------------------------------------
# video_perf
# ---------------------------------------------------------------------------

def test_view_lift_arithmetic(con):
    perf = stats.video_perf(con)
    p = perf['spiky06']                      # the 900 000 hit
    median_play = p['creator_median_play']
    assert p['view_lift'] == pytest.approx(900000 / median_play - 1, rel=1e-6)
    assert perf['steady02']['view_lift'] == pytest.approx(10000 / perf['steady02']['creator_median_play'] - 1,
                                                          rel=1e-6)


def test_robust_z_matches_the_formula(con):
    perf = stats.video_perf(con)
    plays = STEADY + [50]
    logs = sorted(math.log1p(p) for p in plays)
    med = stats.median(logs)
    d = stats.mad(logs, med)
    d = max(d, stats.LOG_MAD_FLOOR)
    expected = (math.log1p(11000) - med) / (1.4826 * d)
    expected = max(-stats.Z_CLIP, min(stats.Z_CLIP, expected))
    assert perf['steady04']['robust_z'] == pytest.approx(round(expected, 4), abs=1e-4)


def test_robust_z_is_clipped_and_flagged(con):
    perf = stats.video_perf(con)
    zs = [p['robust_z'] for p in perf.values() if p['robust_z'] is not None]
    assert max(zs) <= stats.Z_CLIP and min(zs) >= -stats.Z_CLIP
    assert perf['spiky06']['outlier_status'] == 'HIGH'
    assert perf['spiky00']['outlier_status'] in ('NORMAL', 'LOW')


def test_percentile_in_creator(con):
    perf = stats.video_perf(con)
    # steady04 is 11000, the highest of the 13 steady videos
    assert perf['steady04']['percentile_in_creator'] == pytest.approx(100 * 12.5 / 13, abs=0.01)
    assert perf['steadyLOW']['percentile_in_creator'] == pytest.approx(100 * 0.5 / 13, abs=0.01)


def test_small_sample_creator_is_labelled_not_scored(con):
    perf = stats.video_perf(con)
    for i in range(3):
        assert perf['tiny%02d' % i]['outlier_status'] == 'SMALL_SAMPLE'
        assert perf['tiny%02d' % i]['creator_n'] == 3


def test_denominator_guard(con):
    perf = stats.video_perf(con)
    low = perf['steadyLOW']
    assert low['play'] == 50 < stats.MIN_PLAY_FOR_RATE
    for key in ('like_rate', 'comment_rate', 'share_rate', 'save_rate', 'hi_intent_rate'):
        assert low[key] is None, key
    ok = perf['steady00']
    assert ok['like_rate'] == pytest.approx(int(9000 * 0.05) / 9000, rel=1e-6)
    assert ok['share_rate'] is not None


def test_rate_helper_directly():
    assert stats.rate(5, 50) is None
    assert stats.rate(5, 100) == pytest.approx(0.05)
    assert stats.rate(None, 1000) is None
    assert stats.lift(0.02, 0.01) == pytest.approx(1.0)
    assert stats.lift(0.02, 0) is None


def test_perf_is_written_to_columns_and_json(con):
    stats.video_perf(con)
    row = con.execute('SELECT * FROM video_features WHERE code="spiky06"').fetchone()
    assert row['outlier_status'] == 'HIGH'
    assert row['play'] == 900000
    data = json.loads(row['features_json'])
    assert data['perf']['robust_z'] == row['robust_z']


# ---------------------------------------------------------------------------
# temporal
# ---------------------------------------------------------------------------

def test_temporal_deltas_and_slope(con):
    t = stats.temporal(con)
    first = t['steady00']
    assert first['prev_play'] is None and first['delta_play'] is None
    second = t['steady01']
    assert second['delta_play'] == 9500 - 9000
    assert second['delta_play_pct'] == pytest.approx(9500 / 9000 - 1, abs=5e-5)
    assert second['days_since_prev'] == pytest.approx(3.0)
    # the spike sits far above its own rolling median
    assert t['spiky06']['ratio_to_rolling_median'] > 100
    assert t['steady11']['log_play_slope_last10'] is not None


def test_temporal_written_into_features_json(con):
    stats.temporal(con)
    row = con.execute('SELECT features_json FROM video_features WHERE code="steady01"').fetchone()
    assert json.loads(row[0])['temporal']['delta_play'] == 500


# ---------------------------------------------------------------------------
# associations
# ---------------------------------------------------------------------------

def _corpus_with_features(tmp_path):
    """Give every code a lexical block and a topic so associations has something to chew."""
    topics = []
    for pk, name, plays in CREATORS:
        for i in range(len(plays)):
            code = '%s%02d' % (name, i)
            # 'big' on the first three of each creator, 'rare' on exactly two codes
            topics.append((code, 'rare' if (name == 'steady' and i >= 10) else 'big'))
    con = build_db(tmp_path, topics=topics, low_play_code=False)
    stats.creator_stats(con)
    stats.video_perf(con)
    for pk, name, plays in CREATORS:
        for i, play in enumerate(plays):
            code = '%s%02d' % (name, i)
            corpus.merge_features(con, code, 'lexical', {
                'words': 100 + i * 10,
                'numbers_n': i,
                'questions_n': 1,
                'specificity': float(i),
                'lexical_version': 'lex-v1',
            })
    con.commit()
    return con


def test_associations_report_shape(tmp_path):
    con = _corpus_with_features(tmp_path)
    a = stats.associations(con, min_n=5, tier=None)
    assert a['n_rows'] == 27
    assert a['n_creators'] == 3
    assert a['bootstrap'] == {'replicates': stats.BOOTSTRAP_REPLICATES,
                              'seed': stats.BOOTSTRAP_SEED, 'unit': 'creator cluster'}
    assert any(r['feature'] == 'lex_numbers_n' for r in a['spearman'])
    for r in a['spearman']:
        assert r['confidence'] in (stats.RELIABLE, stats.PROBABLE, stats.INSUFFICIENT)
        assert r['n'] >= 5
    con.close()


def test_small_cells_are_suppressed(tmp_path):
    con = _corpus_with_features(tmp_path)
    a = stats.associations(con, min_n=5, tier=None)
    rare = [r for r in a['categorical_contrasts'] if r['value'] == 'rare']
    assert rare, 'the 2-code category must still be reported, labelled'
    for r in rare:
        assert r['n'] == 2
        assert r['confidence'] == stats.INSUFFICIENT
        assert r['ci95'] is None
        assert 'suppressed_reason' in r
    con.close()


def test_a_category_spanning_one_creator_is_insufficient(tmp_path):
    con = _corpus_with_features(tmp_path)
    a = stats.associations(con, min_n=5, tier=None)
    for r in a['categorical_contrasts']:
        if r['n_creators'] < stats.SMALL_CELL_CREATORS:
            assert r['confidence'] == stats.INSUFFICIENT
    con.close()


def test_missing_semantic_columns_are_noted_not_silently_empty(tmp_path):
    con = _corpus_with_features(tmp_path)
    a = stats.associations(con, min_n=5, tier=None)
    joined = ' '.join(a['notes'])
    for cat in ('hook_type', 'pain', 'solution_type', 'cta_type', 'narrative'):
        assert cat in joined
    con.close()


def test_strong_vs_weak_quartiles(tmp_path):
    con = _corpus_with_features(tmp_path)
    a = stats.associations(con, min_n=5, tier=None)
    sw = a['strong_vs_weak']
    assert sw['available'] is True
    assert sw['n_strong'] >= stats.SMALL_CELL_N and sw['n_weak'] >= stats.SMALL_CELL_N
    for f in sw['features']:
        assert 0.0 <= f['p'] <= 1.0
        assert f['diff'] == pytest.approx(f['median_strong'] - f['median_weak'], abs=1e-4)
    con.close()


# ---------------------------------------------------------------------------
# bootstrap
# ---------------------------------------------------------------------------

def _bootstrap_inputs():
    groups = {1: [0.5, 0.4, 0.6], 2: [0.1, 0.2], 3: [0.9, 1.1, 1.0, 0.95], 4: [0.3, 0.35]}
    pooled = {1: [0.5, 0.4, 0.6, 0.1], 2: [0.1, 0.2, 0.7], 3: [0.9, 1.1, 1.0, 0.95, 0.2],
              4: [0.3, 0.35, 0.8]}
    return groups, pooled


def test_bootstrap_is_deterministic_for_a_seed():
    groups, pooled = _bootstrap_inputs()
    a = stats._bootstrap_ci(groups, 'x', pooled, 1000, stats.BOOTSTRAP_SEED)
    b = stats._bootstrap_ci(groups, 'x', pooled, 1000, stats.BOOTSTRAP_SEED)
    assert a == b
    assert a is not None and a[0] <= a[1]


def test_bootstrap_changes_with_the_seed():
    groups, pooled = _bootstrap_inputs()
    a = stats._bootstrap_ci(groups, 'x', pooled, 1000, stats.BOOTSTRAP_SEED)
    c = stats._bootstrap_ci(groups, 'x', pooled, 1000, stats.BOOTSTRAP_SEED + 1)
    assert a != c, 'a fixed CI regardless of seed would mean the resampling is not happening'


def test_bootstrap_refuses_too_few_creators():
    groups = {1: [0.5, 0.4], 2: [0.1]}
    pooled = {1: [0.5, 0.4], 2: [0.1]}
    assert stats._bootstrap_ci(groups, 'x', pooled, 100, 1) is None


# ---------------------------------------------------------------------------
# confidence labelling
# ---------------------------------------------------------------------------

def test_confidence_thresholds():
    assert stats._confidence(3, 0.001, 10) == stats.INSUFFICIENT           # n too small
    assert stats._confidence(50, 0.001, 2) == stats.INSUFFICIENT           # too few creators
    assert stats._confidence(50, 0.2, 10) == stats.PROBABLE                # p too weak
    assert stats._confidence(10, 0.001, 10) == stats.PROBABLE              # n under RELIABLE_N
    assert stats._confidence(50, 0.001, 10) == stats.RELIABLE


def test_a_correlation_that_dies_under_creator_normalisation_is_not_reliable():
    """Between-creator structure must not be sold as a within-creator finding."""
    assert stats._confidence(200, 1e-9, 40, rho=0.4, creator_rho=0.02) == stats.PROBABLE
    assert stats._confidence(200, 1e-9, 40, rho=0.4, creator_rho=0.3) == stats.RELIABLE
    assert stats._confidence(200, 1e-9, 40, rho=0.4, creator_rho=-0.3) == stats.PROBABLE


def test_confidence_needs_a_ci_that_excludes_zero():
    assert stats._confidence(50, None, 10, ci=[-0.1, 0.4]) == stats.PROBABLE
    assert stats._confidence(50, 0.001, 10, ci=[0.1, 0.4]) == stats.RELIABLE


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def test_report_is_json_serializable(tmp_path):
    con = _corpus_with_features(tmp_path)
    rep = stats.report(con, min_n=5, save=False)
    json.dumps(rep, default=str)          # must not raise
    assert rep['creators']['n'] == 3
    assert rep['videos']['n'] == 27
    assert rep['corpus']['counts']['n_ingested'] == 27
    assert rep['videos']['rate_guard_play'] == stats.MIN_PLAY_FOR_RATE
    assert any('Associational only' in x for x in rep['limitations'])
    con.close()
