#!/usr/bin/env python3
"""Creator and video statistics (SPEC §7; V4 §18, §69–73).

Three layers, in the order they have to run:

  creator_stats(con)  what "normal" looks like for each creator      -> creator_stats
  video_perf(con)     where one video sits against its own creator   -> video_features
  temporal(con)       whether a creator is rising or falling         -> features_json
  associations(con)   what travels with performance across the corpus
  report(con)         all of the above as one JSON file

Conventions, stated once
------------------------
* **Baseline = the creator's whole known history**, each code at its newest reading
  (`engine/corpus.latest_metrics`, the rule from `baseline.py`). A median built from a
  single weekly pull stands on ~24 videos and moves every week; the accumulated one
  does not.
* **Log space for views.** Play counts span four orders of magnitude and are
  right-skewed; differences are meaningful as ratios, not as absolute numbers, so the
  robust z-score is computed on ln(1+play).
* **MAD, not SD**, scaled by 1.4826 so that on normal data it reads like a z-score.
* **MAD floor 0.10 in log space** — the same constant `score.py` uses, for the same
  reason: a creator who posts near-identical numbers has a near-zero MAD, and dividing
  by it turns noise into a z of 40. Where `score.py` *drops* the component, this module
  *floors* it and sets `robust_z_floored=1`, because a descriptive statistic that is
  missing for a third of the corpus cannot be correlated against anything.
* **Clipped to ±5**, again as in `score.py`.
* **Focal row is included here.** `score.py` excludes the video from its own baseline
  (it is ranking candidates, and a big outlier would otherwise hide inside its own
  norm). This module describes the distribution, where leave-one-out would make the
  numbers non-comparable between creators with 6 and 40 videos. The two therefore give
  slightly different z values on purpose — `score.py` is for selection, this is for
  description.
* **No age banding here.** `score.py` compares a video only with others in its age
  band (a 2-day-old reel has not finished accruing views). This module reports the raw
  creator-relative position and leaves age out; `temporal()` is where chronology lives.
* **Denominator guard:** every rate is NULL below 100 plays. 3 of 1 000 likes on 12
  views is not an engagement rate, it is a rounding artefact.

    python3 -m engine.stats                 creator_stats + video_perf + temporal
    python3 -m engine.stats --report        the above, then associations -> reports/stats/
    python3 -m engine.stats --associations  associations only, printed
"""
from __future__ import annotations

import collections
import datetime
import json
import math
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine import corpus  # noqa: E402

STATS_VERSION = 'stats-v1'
MIN_BASELINE = 5          # below this a creator has no usable norm (score.py's constant)
MIN_PLAY_FOR_RATE = 100   # denominator guard (SPEC §7)
LOG_MAD_FLOOR = 0.10      # score.py's LOG_MAD_FLOOR
Z_CLIP = 5.0              # score.py's Z_CLIP
OUTLIER_Z = 2.0
CONSISTENT_CV = 1.0
CONSISTENT_N = 8
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 20260911
SMALL_CELL_N = 5
SMALL_CELL_CREATORS = 3
RELIABLE_N = 30
RELIABLE_CREATORS = 8
RELIABLE_P = 0.01

RELIABLE, PROBABLE, INSUFFICIENT = 'RELIABLE', 'PROBABLE', 'INSUFFICIENT'


def _now():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


# ---------------------------------------------------------------------------
# small robust helpers
# ---------------------------------------------------------------------------

def median(xs):
    xs = [x for x in xs if x is not None and not _isnan(x)]
    return statistics.median(xs) if xs else None


def _isnan(x):
    try:
        return isinstance(x, float) and math.isnan(x)
    except TypeError:
        return False


def mad(xs, med=None):
    xs = [x for x in xs if x is not None and not _isnan(x)]
    if not xs:
        return None
    m = median(xs) if med is None else med
    return statistics.median([abs(x - m) for x in xs])


def iqr(xs):
    xs = sorted(x for x in xs if x is not None and not _isnan(x))
    if len(xs) < 2:
        return None
    q = lambda p: xs[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))]  # noqa: E731
    return q(0.75) - q(0.25)


def robust_z_log(play, log_values, med_ln=None, mad_ln=None):
    """(ln(1+play) - median ln) / (1.4826 * MAD ln), MAD floored, clipped to +-5.

    Returns (z, floored_flag). `floored` means the creator's spread was below the floor
    and the denominator was replaced — the sign of z is still meaningful, its size is
    an upper bound.
    """
    if play is None:
        return None, 0
    x = math.log1p(play)
    m = median(log_values) if med_ln is None else med_ln
    d = mad(log_values, m) if mad_ln is None else mad_ln
    if m is None or d is None:
        return None, 0
    floored = 0
    if d < LOG_MAD_FLOOR:
        d, floored = LOG_MAD_FLOOR, 1
    z = (x - m) / (1.4826 * d)
    return max(-Z_CLIP, min(Z_CLIP, round(z, 4))), floored


def percentile_of(value, values):
    """Share of the creator's videos this one is at or above, 0-100."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    below = sum(1 for v in vals if v < value)
    equal = sum(1 for v in vals if v == value)
    return round(100.0 * (below + 0.5 * equal) / len(vals), 2)


def rate(numerator, play):
    if numerator is None or play is None or play < MIN_PLAY_FOR_RATE:
        return None
    return numerator / float(play)


def lift(value, reference):
    if value is None or reference in (None, 0):
        return None
    return round(value / float(reference) - 1.0, 6)


# ---------------------------------------------------------------------------
# 1. creator statistics
# ---------------------------------------------------------------------------

def _creator_rows(con, snapshot_id):
    """Each creator's accumulated baseline as of `snapshot_id`.

    "As of" means: every code first seen at or before that snapshot, taken at its
    newest reading that is also at or before it. The `creator_stats.snapshot_id`
    column therefore reads as "the norm as we knew it that week", which is what makes
    two snapshots comparable.
    """
    sql = """
    SELECT code, pk_user, username, ts, play, likes, comm, resh, save, dur, followers
    FROM (SELECT r.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY snapshot_id DESC) rn
          FROM reels r WHERE r.snapshot_id <= ?)
    WHERE rn = 1
    """
    by = collections.defaultdict(list)
    for r in con.execute(sql, (snapshot_id,)):
        by[r['pk_user']].append(dict(r))
    return by


def creator_stats(con, snapshot_id=None, write=True):
    """Per creator per snapshot: median/MAD/IQR/SD/CV of play, medians of counts and
    rates, posting cadence, outlier share, consistency and a reliability label.

    Writes `creator_stats` (INSERT OR REPLACE on (pk, snapshot_id)) and returns the rows.
    """
    corpus.ensure_tables(con)
    if snapshot_id is None:
        row = con.execute('SELECT id FROM snapshots WHERE done=1 ORDER BY taken DESC LIMIT 1').fetchone()
        snapshot_id = row[0] if row else None
    if snapshot_id is None:
        return []

    by = _creator_rows(con, snapshot_id)

    # category distributions: topics come from the legacy tagger, the rest from
    # video_features (NULL until the ta-v1 wave runs -> written as null, not as {}).
    topics_by_code = collections.defaultdict(list)
    for code, topic in con.execute('SELECT code, topic FROM topics'):
        topics_by_code[code].append(topic)
    vf = {}
    try:
        for r in con.execute('SELECT code, hook_type, cta_type, first_frame_type, positioning_type'
                             ' FROM video_features'):
            vf[r['code']] = dict(r)
    except Exception:
        vf = {}

    out = []
    for pk, rows in by.items():
        plays = [r['play'] for r in rows if r['play'] is not None]
        if not plays:
            continue
        logs = [math.log1p(p) for p in plays]
        med_ln, mad_ln = median(logs), mad(logs)
        n = len(rows)
        med_play = median(plays)
        mean_play = statistics.mean(plays)
        sd_play = statistics.stdev(plays) if n > 1 else 0.0
        cv_play = (sd_play / mean_play) if mean_play else None

        rates = {k: [] for k in ('like_rate', 'comment_rate', 'share_rate', 'save_rate')}
        for r in rows:
            for key, col in (('like_rate', 'likes'), ('comment_rate', 'comm'),
                             ('share_rate', 'resh'), ('save_rate', 'save')):
                v = rate(r.get(col), r.get('play'))
                if v is not None:
                    rates[key].append(v)

        zs = [robust_z_log(r['play'], logs, med_ln, mad_ln)[0] for r in rows]
        zs = [z for z in zs if z is not None]
        outlier_share = (sum(1 for z in zs if z > OUTLIER_Z) / len(zs)) if zs else None
        high_share = (sum(1 for p in plays if med_play and p >= 2 * med_play) / len(plays)) if plays else None

        tss = sorted(r['ts'] for r in rows if r.get('ts'))
        if len(tss) >= 2 and tss[-1] > tss[0]:
            weeks = (tss[-1] - tss[0]) / (7 * 86400.0)
            posts_per_week = round(n / weeks, 3) if weeks >= 1 else None
        else:
            posts_per_week = None

        consistency = None
        if cv_play is not None:
            consistency = round(max(0.0, min(1.0, 1.0 / (1.0 + cv_play))), 4)
        if n < MIN_BASELINE:
            reliability = 'SMALL_SAMPLE'
        elif cv_play is not None and cv_play < CONSISTENT_CV and n >= CONSISTENT_N:
            reliability = 'CONSISTENT'
        else:
            reliability = 'HIGH_VARIANCE'

        codes = [r['code'] for r in rows]
        topic_dist = collections.Counter(t for c in codes for t in topics_by_code.get(c, []))
        def dist(col):
            vals = [vf[c][col] for c in codes if c in vf and vf[c].get(col)]
            return dict(collections.Counter(vals)) if vals else None

        rec = {
            'pk': pk, 'snapshot_id': snapshot_id,
            'username': rows[0].get('username'),
            'followers': rows[0].get('followers'),
            'n_videos': n,
            'median_play': med_play, 'mean_play': round(mean_play, 2),
            'mad_play': mad(plays), 'iqr_play': iqr(plays),
            'sd_play': round(sd_play, 2), 'cv_play': round(cv_play, 4) if cv_play is not None else None,
            'median_likes': median([r['likes'] for r in rows]),
            'median_comm': median([r['comm'] for r in rows]),
            'median_resh': median([r['resh'] for r in rows]),
            'median_save': median([r['save'] for r in rows]),
            'median_like_rate': median(rates['like_rate']),
            'median_comment_rate': median(rates['comment_rate']),
            'median_share_rate': median(rates['share_rate']),
            'median_save_rate': median(rates['save_rate']),
            'posts_per_week': posts_per_week,
            'outlier_share': round(outlier_share, 4) if outlier_share is not None else None,
            'high_performer_share': round(high_share, 4) if high_share is not None else None,
            'consistency_score': consistency,
            'reliability': reliability,
            'topic_dist_json': json.dumps(dict(topic_dist), ensure_ascii=False, sort_keys=True) if topic_dist else None,
            'hook_dist_json': json.dumps(dist('hook_type'), sort_keys=True) if dist('hook_type') else None,
            'cta_dist_json': json.dumps(dist('cta_type'), sort_keys=True) if dist('cta_type') else None,
            'visual_dist_json': json.dumps(dist('first_frame_type'), sort_keys=True) if dist('first_frame_type') else None,
            'positioning_summary': None,
            'computed_at': _now(), 'stats_version': STATS_VERSION,
            # not a column, kept for the callers
            '_median_ln_play': med_ln, '_mad_ln_play': mad_ln,
        }
        out.append(rec)

    if write:
        cols = [c for c in out[0] if not c.startswith('_')] if out else []
        if cols:
            con.executemany(
                'INSERT OR REPLACE INTO creator_stats (%s) VALUES (%s)'
                % (','.join(cols), ','.join('?' * len(cols))),
                [[r[c] for c in cols] for r in out])
            con.commit()
    return out


# ---------------------------------------------------------------------------
# 2. per-video performance
# ---------------------------------------------------------------------------

PERF_COLUMNS = ('play', 'likes', 'comm', 'resh', 'save', 'like_rate', 'comment_rate',
                'share_rate', 'save_rate', 'hi_intent_rate', 'creator_median_play',
                'view_lift', 'share_rate_lift', 'save_rate_lift', 'robust_z',
                'percentile_in_creator', 'outlier_status', 'creator_consistency', 'creator_n')


def video_perf(con, write=True):
    """Where every video sits against its own creator. Returns {code: perf dict}."""
    corpus.ensure_tables(con)
    rows = [dict(r) for r in con.execute(corpus.LATEST_SQL)]
    by = collections.defaultdict(list)
    for r in rows:
        by[r['pk_user']].append(r)

    out = {}
    for pk, rs in by.items():
        plays = [r['play'] for r in rs if r['play'] is not None]
        if not plays:
            continue
        logs = [math.log1p(p) for p in plays]
        med_ln, mad_ln = median(logs), mad(logs)
        med_play = median(plays)
        mean_play = statistics.mean(plays)
        cv = (statistics.stdev(plays) / mean_play) if len(plays) > 1 and mean_play else None
        consistency = round(max(0.0, min(1.0, 1.0 / (1.0 + cv))), 4) if cv is not None else None
        n = len(rs)

        creator_rates = {}
        for key, col in (('share_rate', 'resh'), ('save_rate', 'save'),
                         ('like_rate', 'likes'), ('comment_rate', 'comm')):
            creator_rates[key] = median([rate(r.get(col), r.get('play')) for r in rs])

        for r in rs:
            play = r['play']
            like_rate = rate(r.get('likes'), play)
            comment_rate = rate(r.get('comm'), play)
            share_rate = rate(r.get('resh'), play)
            save_rate = rate(r.get('save'), play)
            hi = None
            if play and play >= MIN_PLAY_FOR_RATE and (r.get('resh') is not None or r.get('save') is not None):
                hi = ((r.get('resh') or 0) + (r.get('save') or 0)) / float(play)
            z, floored = robust_z_log(play, logs, med_ln, mad_ln)
            if n < MIN_BASELINE:
                status = 'SMALL_SAMPLE'
            elif z is None:
                status = 'SMALL_SAMPLE'
            elif z >= OUTLIER_Z:
                status = 'HIGH'
            elif z <= -OUTLIER_Z:
                status = 'LOW'
            else:
                status = 'NORMAL'
            perf = {
                'code': r['code'], 'pk_user': pk, 'username': r.get('username'),
                'ts': r.get('ts'), 'dur': r.get('dur'), 'followers': r.get('followers'),
                'play': play, 'likes': r.get('likes'), 'comm': r.get('comm'),
                'resh': r.get('resh'), 'save': r.get('save'),
                'like_rate': like_rate, 'comment_rate': comment_rate,
                'share_rate': share_rate, 'save_rate': save_rate, 'hi_intent_rate': hi,
                'creator_median_play': med_play,
                'view_lift': lift(play, med_play),
                'share_rate_lift': lift(share_rate, creator_rates['share_rate']),
                'save_rate_lift': lift(save_rate, creator_rates['save_rate']),
                'like_rate_lift': lift(like_rate, creator_rates['like_rate']),
                'comment_rate_lift': lift(comment_rate, creator_rates['comment_rate']),
                'robust_z': z, 'robust_z_floored': floored,
                'percentile_in_creator': percentile_of(play, plays),
                'outlier_status': status,
                'creator_consistency': consistency, 'creator_n': n,
                'creator_median_share_rate': creator_rates['share_rate'],
                'creator_median_save_rate': creator_rates['save_rate'],
                'denominator_guard_play': MIN_PLAY_FOR_RATE,
                'stats_version': STATS_VERSION,
            }
            out[r['code']] = perf

    if write:
        for code, perf in out.items():
            cols = {k: perf[k] for k in PERF_COLUMNS if k in perf}
            corpus.merge_features(con, code, 'perf', perf, columns=cols)
        con.commit()
    return out


# ---------------------------------------------------------------------------
# 3. temporal
# ---------------------------------------------------------------------------

def _slope(ys):
    """OLS slope of ys against 0..n-1. Plain least squares on log play; it is a trend
    line, not a derivative — §71 is explicit that a difference must not be called one."""
    n = len(ys)
    if n < 3:
        return None
    xs = list(range(n))
    mx, my = statistics.mean(xs), statistics.mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den, 6)


def temporal(con, write=True, rolling=5, slope_window=10):
    """Per creator, videos ordered by publication time: change against the previous
    reel, position against a rolling median of the previous `rolling`, and the slope of
    ln(1+play) over the last `slope_window` posts."""
    corpus.ensure_tables(con)
    rows = [dict(r) for r in con.execute(corpus.LATEST_SQL)]
    by = collections.defaultdict(list)
    for r in rows:
        by[r['pk_user']].append(r)

    out = {}
    for pk, rs in by.items():
        rs = sorted([r for r in rs if r.get('ts')], key=lambda r: r['ts'])
        for i, r in enumerate(rs):
            prev = rs[i - 1] if i else None
            window = [x['play'] for x in rs[max(0, i - rolling):i] if x['play'] is not None]
            roll_med = median(window)
            hist = [math.log1p(x['play']) for x in rs[max(0, i - slope_window + 1):i + 1]
                    if x['play'] is not None]
            t = {
                'code': r['code'], 'pk_user': pk,
                'idx_in_creator': i, 'n_in_creator': len(rs), 'ts': r['ts'],
                'days_since_prev': round((r['ts'] - prev['ts']) / 86400.0, 3) if prev else None,
                'play': r['play'], 'prev_play': prev['play'] if prev else None,
                'delta_play': (r['play'] - prev['play']) if prev and r['play'] is not None
                              and prev['play'] is not None else None,
                'delta_play_pct': (round(r['play'] / prev['play'] - 1, 4)
                                   if prev and prev.get('play') else None),
                'delta_share_rate': None, 'delta_save_rate': None,
                'rolling_median_play': roll_med, 'rolling_window': len(window),
                'ratio_to_rolling_median': (round(r['play'] / roll_med, 4)
                                            if roll_med and r['play'] is not None else None),
                'log_play_slope_last10': _slope(hist), 'slope_window_n': len(hist),
                'slope_definition': 'OLS slope of ln(1+play) on post index, last %d posts' % slope_window,
            }
            for key, col in (('delta_share_rate', 'resh'), ('delta_save_rate', 'save')):
                if prev:
                    a, b = rate(r.get(col), r.get('play')), rate(prev.get(col), prev.get('play'))
                    t[key] = round(a - b, 8) if a is not None and b is not None else None
            out[r['code']] = t

    if write:
        for code, t in out.items():
            corpus.merge_features(con, code, 'temporal', t)
        con.commit()
    return out


# ---------------------------------------------------------------------------
# 4. associations
# ---------------------------------------------------------------------------

PERF_METRICS = ('view_lift', 'share_rate', 'save_rate', 'robust_z')

# numeric features that are never treated as predictors (they are performance, or an id)
_NOT_FEATURES = set(PERF_METRICS) | {
    'play', 'likes', 'comm', 'resh', 'save', 'ts', 'pk_user', 'followers',
    'like_rate', 'comment_rate', 'hi_intent_rate', 'creator_median_play',
    'creator_median_share_rate', 'creator_median_save_rate', 'percentile_in_creator',
    'creator_consistency', 'creator_n', 'robust_z_floored', 'like_rate_lift',
    'comment_rate_lift', 'share_rate_lift', 'save_rate_lift', 'denominator_guard_play',
    'idx_in_creator', 'n_in_creator', 'prev_play', 'delta_play', 'delta_play_pct',
    'rolling_median_play', 'rolling_window', 'ratio_to_rolling_median', 'topic_labels_n',
    'log_play_slope_last10', 'slope_window_n', 'days_since_prev',
    'delta_share_rate', 'delta_save_rate', 'snapshot_id', 'lexical_version',
}

CATEGORICAL = ('topic', 'hook_type', 'pain', 'solution_type', 'cta_type', 'narrative',
               'first_frame_type', 'visual_sequence')

_NUMERIC_COLUMNS = ('hook_s', 'hook_words', 'setup_s', 'problem_s', 'explanation_s',
                    'solution_s', 'proof_s', 'payoff_s', 'cta_s', 'total_s', 'total_words',
                    'wps', 'avg_sentence_len', 'info_density', 'specificity', 'numbers_n',
                    'questions_n', 'a_roll_share', 'b_roll_share', 'split_share',
                    'screen_share', 'text_overlay_density', 'scenes_n', 'avg_scene_s',
                    'cuts', 'cuts_per_min')


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not _isnan(v)


def feature_frame(con, tier_codes=None):
    """One row per code: perf metrics + every numeric feature we have for it.

    Lexical features are flattened with a `lex_` prefix, the timing blocks with `blk_`,
    `video_features` key columns keep their own names. Categorical columns come from
    `video_features` and, for `topic`, from the legacy `topics` table when
    `video_features.topic` is still NULL.
    """
    import pandas as pd
    tier_codes = set(tier_codes) if tier_codes is not None else None
    recs = []
    topics_by_code = collections.defaultdict(list)
    for code, topic in con.execute('SELECT code, topic FROM topics'):
        topics_by_code[code].append(topic)
    dur_by_code = {r['code']: r['dur'] for r in con.execute(corpus.LATEST_SQL)}

    for r in con.execute('SELECT * FROM video_features'):
        code = r['code']
        if tier_codes is not None and code not in tier_codes:
            continue
        try:
            fj = json.loads(r['features_json'] or '{}')
        except (TypeError, ValueError):
            fj = {}
        perf = fj.get('perf') or {}
        rec = {'code': code, 'pk_user': perf.get('pk_user'), 'username': perf.get('username'),
               'dur': dur_by_code.get(code)}
        for m in PERF_METRICS:
            rec[m] = perf.get(m) if m in perf else r[m] if m in r.keys() else None
        for k in _NUMERIC_COLUMNS:
            if k in r.keys() and _is_num(r[k]):
                rec[k] = r[k]
        lex = fj.get('lexical') or {}
        for k, v in lex.items():
            if k == 'blocks':
                continue
            if _is_num(v) and k not in _NOT_FEATURES:
                rec['lex_' + k] = v
        for k, v in (lex.get('blocks') or {}).items():
            if _is_num(v):
                rec['blk_' + k] = v
        for cat in CATEGORICAL:
            rec[cat] = r[cat] if cat in r.keys() else None
        if not rec.get('topic'):
            # Legacy tagger fallback. A code with several topic labels is left
            # unassigned: picking one of them would invent a fact, and counting the
            # video once per label would let a 9-label video outvote eight others.
            tl = topics_by_code.get(code) or []
            rec['topic'] = tl[0] if len(tl) == 1 else None
            rec['topic_multi'] = len(tl) > 1
            rec['topic_labels_n'] = len(tl)
        recs.append(rec)
    return pd.DataFrame(recs)


def _sig(x, digits=4):
    """Round to significant digits. round(p, 6) turns 2e-09 into 0.0, which reads as
    "impossible" rather than "very small"."""
    if x is None or _isnan(x):
        return None
    return float('%.*g' % (digits, x))


def _confidence(n, p, n_creators=None, ci=None, rho=None, creator_rho=None):
    if n is None or n < SMALL_CELL_N:
        return INSUFFICIENT
    if n_creators is not None and n_creators < SMALL_CELL_CREATORS:
        return INSUFFICIENT
    ok_p = p is not None and p < RELIABLE_P
    ok_n = n >= RELIABLE_N
    ok_c = n_creators is None or n_creators >= RELIABLE_CREATORS
    ok_ci = ci is None or (ci[0] > 0 and ci[1] > 0) or (ci[0] < 0 and ci[1] < 0)
    # A correlation that disappears once each creator is centred was a statement about
    # which creators post this kind of video, not about the video. It may still be
    # true and useful, but it is not RELIABLE evidence that the feature does anything.
    ok_within = True
    if rho is not None and creator_rho is not None:
        ok_within = (creator_rho * rho > 0) and abs(creator_rho) >= 0.5 * abs(rho)
    elif rho is not None and creator_rho is None:
        ok_within = False
    if ok_p and ok_n and ok_c and ok_ci and ok_within:
        return RELIABLE
    return PROBABLE


def _creator_normalized(df, cols):
    """Within each creator with >=3 rows, replace each value by its centred rank.

    Pooling raw values across creators mixes "this reel did well for its author" with
    "this author is large". Ranking inside the creator and then pooling removes the
    creator's level while keeping the ordering, which is what a Spearman is reading
    anyway.
    """
    import pandas as pd
    parts = []
    for pk, g in df.groupby('pk_user'):
        if len(g) < 3:
            continue
        h = g.copy()
        for c in cols:
            if c in h.columns:
                r = h[c].rank(method='average')
                h[c] = (r - (len(h) + 1) / 2.0) / len(h)
        parts.append(h)
    return pd.concat(parts) if parts else pd.DataFrame(columns=df.columns)


def _spearman(x, y):
    from scipy import stats as sps
    import numpy as np
    m = np.isfinite(x) & np.isfinite(y)
    xs, ys = np.asarray(x)[m], np.asarray(y)[m]
    if len(xs) < 3 or len(set(xs.tolist())) < 2 or len(set(ys.tolist())) < 2:
        return None, None, int(len(xs))
    r = sps.spearmanr(xs, ys)
    return float(r.statistic), float(r.pvalue), int(len(xs))


def _bootstrap_ci(groups_by_creator, category, pooled_metric_by_creator, replicates, seed):
    """Cluster bootstrap: resample *creators*, not videos.

    Videos by the same creator are not independent draws — one creator with 30 reels in
    a category would otherwise drive a confidence interval on their own. Each replicate
    draws creators with replacement, pools their videos, and recomputes
    (category median lift - pooled median lift).
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    creators = sorted(groups_by_creator)
    if len(creators) < SMALL_CELL_CREATORS:
        return None
    idx = np.arange(len(creators))
    diffs = []
    for _ in range(replicates):
        pick = rng.choice(idx, size=len(idx), replace=True)
        cat_vals, all_vals = [], []
        for j in pick:
            c = creators[j]
            cat_vals.extend(groups_by_creator[c])
            all_vals.extend(pooled_metric_by_creator.get(c, []))
        if len(cat_vals) < 2 or len(all_vals) < 2:
            continue
        diffs.append(float(np.median(cat_vals) - np.median(all_vals)))
    if len(diffs) < replicates * 0.5:
        return None
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return [round(float(lo), 6), round(float(hi), 6)]


def associations(con, min_n=10, tier='analysis_ready', metrics=PERF_METRICS,
                 replicates=BOOTSTRAP_REPLICATES, seed=BOOTSTRAP_SEED):
    """Spearman on numeric features, category contrasts with a cluster bootstrap, and a
    strong-vs-weak quartile comparison. Descriptive only — §21 and §72 forbid reading
    causality out of any of it."""
    import numpy as np
    from scipy import stats as sps

    t = corpus.tiers(con)
    codes = set(t[tier]) if tier else None
    df = feature_frame(con, codes)
    notes = []
    if df.empty:
        return {'error': 'no rows in video_features', 'n_rows': 0}

    numeric_cols = [c for c in df.columns
                    if c not in _NOT_FEATURES and c not in CATEGORICAL
                    and c not in ('code', 'username', 'topic_multi')
                    and df[c].dtype.kind in 'if']
    numeric_cols = [c for c in numeric_cols if df[c].notna().sum() >= min_n]
    skipped_numeric = [c for c in _NUMERIC_COLUMNS
                       if c not in numeric_cols and (c not in df.columns or df[c].notna().sum() < min_n)]
    if skipped_numeric:
        notes.append('numeric features with no data yet (semantic/visual wave not run): '
                     + ', '.join(sorted(skipped_numeric)))

    # ---- Spearman ------------------------------------------------------
    cn = _creator_normalized(df, numeric_cols + list(metrics))
    spearman = []
    for metric in metrics:
        if metric not in df.columns or df[metric].notna().sum() < min_n:
            notes.append(f'performance metric {metric} has <{min_n} values, skipped')
            continue
        for col in numeric_cols:
            rho, p, n = _spearman(df[col].astype(float).values, df[metric].astype(float).values)
            if rho is None or n < min_n:
                continue
            crho, cp, cnn = (None, None, 0)
            if not cn.empty and col in cn.columns:
                crho, cp, cnn = _spearman(cn[col].astype(float).values,
                                          cn[metric].astype(float).values)
            n_creators = int(df.loc[df[col].notna() & df[metric].notna(), 'pk_user'].nunique())
            spearman.append({
                'metric': metric, 'feature': col, 'n': n, 'n_creators': n_creators,
                'rho': round(rho, 4), 'p': _sig(p),
                'direction': 'positive' if rho > 0 else 'negative',
                'creator_normalized_rho': round(crho, 4) if crho is not None else None,
                'creator_normalized_p': _sig(cp),
                'creator_normalized_n': cnn,
                'confidence': _confidence(n, p, n_creators, rho=rho, creator_rho=crho),
                'creator_normalized_survives': (crho is not None and crho * rho > 0
                                                and abs(crho) >= 0.5 * abs(rho)),
            })
    spearman.sort(key=lambda d: -abs(d['rho']))

    # ---- categorical contrasts ------------------------------------------
    contrasts = []
    for cat in CATEGORICAL:
        if cat not in df.columns or df[cat].notna().sum() == 0:
            notes.append(f'categorical {cat} is NULL for every code (waiting for ta-v1/fa-v1)')
            continue
        for metric in metrics:
            if metric not in df.columns or df[metric].notna().sum() < min_n:
                continue
            sub = df[df[cat].notna() & df[metric].notna()]
            if sub.empty:
                continue
            pooled_by_creator = collections.defaultdict(list)
            for pk, g in sub.groupby('pk_user'):
                pooled_by_creator[pk] = [float(v) for v in g[metric].values]
            pooled_median = float(np.median(sub[metric].astype(float).values))
            for value, g in sub.groupby(cat):
                n = len(g)
                n_creators = int(g['pk_user'].nunique())
                med = float(np.median(g[metric].astype(float).values))
                rec = {'category': cat, 'value': value, 'metric': metric, 'n': n,
                       'n_creators': n_creators, 'category_median': round(med, 6),
                       'pooled_median': round(pooled_median, 6),
                       'diff_vs_pooled': round(med - pooled_median, 6), 'ci95': None}
                if n < SMALL_CELL_N or n_creators < SMALL_CELL_CREATORS:
                    rec['confidence'] = INSUFFICIENT
                    rec['suppressed_reason'] = f'n={n} (<{SMALL_CELL_N}) or creators={n_creators} (<{SMALL_CELL_CREATORS})'
                else:
                    gb = collections.defaultdict(list)
                    for pk, gg in g.groupby('pk_user'):
                        gb[pk] = [float(v) for v in gg[metric].values]
                    rec['ci95'] = _bootstrap_ci(gb, value, pooled_by_creator, replicates, seed)
                    rec['confidence'] = _confidence(n, None, n_creators, rec['ci95'])
                contrasts.append(rec)
    contrasts.sort(key=lambda d: (d['category'], d['metric'], -abs(d['diff_vs_pooled'])))

    # ---- strong vs weak --------------------------------------------------
    strong_weak = {'available': False, 'note': 'robust_z missing for the corpus'}
    if 'robust_z' in df.columns and df['robust_z'].notna().sum() >= 4 * SMALL_CELL_N:
        z = df['robust_z'].astype(float)
        q1, q3 = float(np.nanpercentile(z, 25)), float(np.nanpercentile(z, 75))
        strong = df[z >= q3]
        weak = df[z <= q1]
        comps = []
        for col in numeric_cols:
            a = strong[col].astype(float).dropna().values
            b = weak[col].astype(float).dropna().values
            if len(a) < SMALL_CELL_N or len(b) < SMALL_CELL_N:
                continue
            try:
                u = sps.mannwhitneyu(a, b, alternative='two-sided')
                stat, p = float(u.statistic), float(u.pvalue)
                if math.isnan(p):
                    # Both groups fully tied against each other (e.g. a feature that is
                    # constant across the whole corpus): the normal-approximation
                    # variance is 0 and some scipy versions divide 0/0 into nan instead
                    # of the older versions' 1.0. Zero spread either side is exactly "no
                    # evidence of a difference" -> p=1.0, not "unknown".
                    p = 1.0
            except ValueError:
                continue
            comps.append({
                'feature': col, 'n_strong': int(len(a)), 'n_weak': int(len(b)),
                'median_strong': round(float(np.median(a)), 4),
                'median_weak': round(float(np.median(b)), 4),
                'diff': round(float(np.median(a) - np.median(b)), 4),
                'mannwhitney_u': round(stat, 2), 'p': _sig(p),
                'confidence': _confidence(min(len(a), len(b)), p,
                                          int(min(strong['pk_user'].nunique(),
                                                  weak['pk_user'].nunique()))),
            })
        comps.sort(key=lambda d: (d['p'] is None, d['p']))
        strong_weak = {
            'available': True,
            'split': 'top vs bottom quartile of robust_z inside the %s corpus' % tier,
            'q1_robust_z': round(q1, 4), 'q3_robust_z': round(q3, 4),
            'n_strong': int(len(strong)), 'n_weak': int(len(weak)),
            'creators_strong': int(strong['pk_user'].nunique()),
            'creators_weak': int(weak['pk_user'].nunique()),
            'features': comps,
        }

    return {
        'tier': tier, 'n_rows': int(len(df)), 'n_creators': int(df['pk_user'].nunique()),
        'min_n': min_n, 'numeric_features_tested': numeric_cols,
        'bootstrap': {'replicates': replicates, 'seed': seed, 'unit': 'creator cluster'},
        'confidence_rule': {
            'INSUFFICIENT': f'n<{SMALL_CELL_N} or creators<{SMALL_CELL_CREATORS}',
            'RELIABLE': f'n>={RELIABLE_N}, creators>={RELIABLE_CREATORS}, '
                        f'p<{RELIABLE_P} (or a bootstrap CI that excludes 0)',
            'PROBABLE': 'everything in between',
        },
        'spearman': spearman,
        'categorical_contrasts': contrasts,
        'strong_vs_weak': strong_weak,
        'notes': notes,
    }


# ---------------------------------------------------------------------------
# 5. report
# ---------------------------------------------------------------------------

def report(con, min_n=10, save=True):
    """Everything above as one JSON-serializable dict, written to reports/stats/."""
    t = corpus.tiers(con)
    cs = creator_stats(con, write=False)
    perf = video_perf(con, write=False)
    temp = temporal(con, write=False)
    assoc = associations(con, min_n=min_n)

    rel = collections.Counter(r['reliability'] for r in cs)
    status = collections.Counter(p['outlier_status'] for p in perf.values())
    rates_present = sum(1 for p in perf.values() if p['share_rate'] is not None)

    rep = {
        'generated_at': _now(),
        'stats_version': STATS_VERSION,
        'corpus': {'counts': t['counts'], 'denominators': t['denominators'],
                   'tiers': t['tier_of_code_totals']},
        'creators': {
            'n': len(cs),
            'snapshot_id': cs[0]['snapshot_id'] if cs else None,
            'reliability': dict(rel),
            'median_n_videos': median([r['n_videos'] for r in cs]),
            'median_median_play': median([r['median_play'] for r in cs]),
            'median_consistency': median([r['consistency_score'] for r in cs]),
            'rows': cs,
        },
        'videos': {
            'n': len(perf),
            'outlier_status': dict(status),
            'with_rates': rates_present,
            'rate_guard_play': MIN_PLAY_FOR_RATE,
            'robust_z_floored': sum(1 for p in perf.values() if p.get('robust_z_floored')),
        },
        'temporal': {
            'n': len(temp),
            'with_rolling_median': sum(1 for x in temp.values()
                                       if x['ratio_to_rolling_median'] is not None),
            'with_slope': sum(1 for x in temp.values() if x['log_play_slope_last10'] is not None),
        },
        'associations': assoc,
        'limitations': [
            'Associational only. Nothing here identifies a cause (V4 §21, §72).',
            'The analysis-ready corpus is NOT a random sample of the niche: deep.py only '
            'ever processed reels that score.py had already ranked near the top, so its '
            'median robust_z is above zero by construction. Feature contrasts inside it '
            'compare strong videos with other strong videos.',
            'Feature-based associations use the %d analysis-ready codes, 8.3%% of the '
            'ingested corpus; they describe that sample, not the niche.' % t['counts']['n_ready'],
            'cuts / cuts_per_min from the legacy corpus are an ffmpeg scene-score count at a '
            'fixed 0.35 threshold, not a shot-boundary count — relative signal only.',
            'Semantic and visual categories are NULL until the ta-v1/fa-v1 analysis wave runs; '
            'every contrast that needs them is reported as skipped, not as a null result.',
            'Saves are missing on ~9-10%% of Hiker rows, so save_rate has a smaller n than the rest.',
        ],
    }
    if save:
        out_dir = os.path.join(REPO, 'reports', 'stats')
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, 'stats-%s.json' % datetime.date.today().isoformat())
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(rep, fh, ensure_ascii=False, sort_keys=True, indent=1, default=str)
        rep['saved_to'] = os.path.relpath(path, REPO)
    return rep


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    db = argv[argv.index('--db') + 1] if '--db' in argv else corpus.DB_PATH
    con = corpus.connect(db)
    if '--associations' in argv:
        a = associations(con)
        print(json.dumps(a, ensure_ascii=False, indent=1, default=str)[:8000])
    elif '--report' in argv:
        r = report(con)
        print('creator_stats rows: %d | video perf rows: %d | saved: %s'
              % (r['creators']['n'], r['videos']['n'], r.get('saved_to')))
    else:
        cs = creator_stats(con)
        print(f'creator_stats: {len(cs)} rows (snapshot {cs[0]["snapshot_id"] if cs else None})')
        p = video_perf(con)
        print(f'video_perf: {len(p)} codes -> video_features')
        t = temporal(con)
        print(f'temporal: {len(t)} codes -> features_json["temporal"]')
    con.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
