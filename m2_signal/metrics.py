"""Versioned descriptive formulas, adapted from the accepted September 4 replay.

These formulas include the focal Reel in its Account baseline and therefore are
NOT a predictive/causal estimator or an accepted final Best-Reel selector.
"""
from __future__ import annotations

import math
import statistics

FORMULA_VERSION = 'm2-signal-descriptive.v1'
DEFAULT_CONFIG = {
    'platform': 'instagram_reels', 'minimum_baseline_n': 5,
    'absolute_exposure_floor': 1000, 'relative_exposure_floor': 0.30,
    'hit_multiplier': 2.0, 'minimum_components': 4, 'z_scale': 0.67448975,
    'z_clip': 5.0, 'rate_floor_absolute': 0.10, 'rate_floor_fraction': 0.05,
    'log_views_mad_floor': 0.10, 'collection_enabled': False,
}


def validate_config(overrides=None):
    overrides = overrides or {}
    unknown = set(overrides) - set(DEFAULT_CONFIG)
    if unknown:
        raise ValueError('unknown config keys: ' + ','.join(sorted(unknown)))
    c = DEFAULT_CONFIG | overrides
    if c['platform'] != 'instagram_reels' or c['collection_enabled'] is not False:
        raise ValueError('only provider-disabled Instagram export replay is supported')
    for name in ['minimum_baseline_n', 'minimum_components']:
        if type(c[name]) is not int or c[name] < 1:
            raise ValueError('positive integer required: ' + name)
    if c['minimum_components'] > 5 or c['minimum_baseline_n'] < 2:
        raise ValueError('minimum_components <=5 and minimum_baseline_n >=2 required')
    for name in set(c) - {'platform', 'collection_enabled', 'minimum_baseline_n', 'minimum_components'}:
        if isinstance(c[name], bool) or not isinstance(c[name], (int, float)) or not math.isfinite(c[name]) or c[name] <= 0:
            raise ValueError('positive finite number required: ' + name)
    return c


def rate(count, views):
    return None if count is None or views is None or views <= 0 else 1000.0 * count / views


def quantile(values, p):
    ordered = sorted(values)
    if not ordered:
        return None
    h = (len(ordered) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    return ordered[lo] + (h-lo) * (ordered[hi]-ordered[lo])


def distribution(values, denominator):
    xs = [x for x in values if x is not None]
    q1, q3 = quantile(xs, .25), quantile(xs, .75)
    return {'observed_n': len(xs), 'eligible_n': denominator,
            'coverage': len(xs)/denominator if denominator else None,
            'mean': statistics.mean(xs) if xs else None,
            'median': quantile(xs, .5), 'q1': q1, 'q3': q3,
            'iqr': q3-q1 if q1 is not None else None}


def wilson(successes, n):
    if not n:
        return None, None
    z = 1.9599639845
    p = successes/n
    den = 1+z*z/n
    centre = (p+z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return centre-half, centre+half


def robust_z(value, baseline, *, kind, config):
    if value is None or len(baseline) < config['minimum_baseline_n']:
        return None
    centre = statistics.median(baseline)
    mad = statistics.median(abs(x-centre) for x in baseline)
    floor = config['log_views_mad_floor'] if kind == 'log_views' else max(config['rate_floor_fraction']*abs(centre), config['rate_floor_absolute'])
    z = config['z_scale']*(value-centre)/max(mad, floor, 1e-9)
    return max(-config['z_clip'], min(config['z_clip'], z))


def candidate_key(row):
    return (row['diagnostic_component_count'], row['diagnostic_equal_weight_z'],
            row['published_epoch_seconds'] or 0, row['views'] or 0, row['code'])


def metric_definition(config):
    return {
        'formula_version': FORMULA_VERSION, 'config': config,
        'population': 'one canonical identity per code within one immutable export release',
        'snapshot_policy': 'separate snapshot releases; no implicit cross-snapshot union or latest-row overwrite',
        'baseline': 'within-account, valid positive-view rows, includes focal row; diagnostic only',
        'exposure': 'baseline_n >= minimum_baseline_n and views >= max(absolute_exposure_floor,relative_exposure_floor*account_median)',
        'hit': 'exposure-eligible views/account_median >= hit_multiplier',
        'hit_interval': 'Wilson 95%; descriptive nonrandom within-account sample',
        'engagement_rates': '1000*observed_count/views; missing remains null; raw counts and rates differ',
        'robust_z': 'clip(z_scale*(x-median)/max(MAD,floor,1e-9),-z_clip,z_clip); baseline is exposure-eligible account rows',
        'components': ['log1p(views)', 'likes_per_1k_views', 'comments_per_1k_views', 'reshares_per_1k_views', 'saves_per_1k_views'],
        'diagnostic_mean': 'equal-weight mean of non-null robust z components when minimum_components met',
        'candidate_policy': 'highest component coverage first, then diagnostic mean, publication time, views, code descending',
        'null_denominator': 'coverage and summary value remain null when denominator is zero',
        'limitations': ['Unknown collector counter semantics, capture time and post-exposure horizons.',
                        'Profile followers measured at export horizon cannot normalize historical posts as same-age reach.',
                        'Caption taxonomy and transcripts remain provisional; source-media verification absent.',
                        'No causal, predictive, market-prevalence, ROI, or final Best-Reel inference.'],
    }
