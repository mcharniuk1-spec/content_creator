#!/usr/bin/env python3
"""Analytical PNG charts for the M2Radar report (V4 execution-prompt §42; engine/SPEC.md §7).

matplotlib, Agg backend, no seaborn, one consistent neutral style. Every chart is
1600x1000 @150dpi, carries a title with `n=`, axis labels and a source line at the
bottom, and gets a sidecar `<name>.json` with
`{title, n, source, variables, method, interpretation: "", limitations}` -- the report
writer fills `interpretation`, everything else is already true when this module writes
it. A chart with n<5 is skipped: no PNG, sidecar carries `status:'skipped', reason`.

Read-only against `data/radar.db` (see `engine/report_data.py` docstring) -- reuses its
row-building and strong/weak-split helpers so a number never disagrees between the two
modules.

    python3 -m engine.charts --out reports/charts
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

from engine import corpus, report_data as rd, stats  # noqa: E402

# ---------------------------------------------------------------------------
# style
# ---------------------------------------------------------------------------

FIGSIZE = (1600 / 150, 1000 / 150)
DPI = 150
MIN_N = 5

INK = '#2b2b2b'
MUTED = '#6b6b6b'
GRID = '#dddddd'
BAR = '#4c6b8a'
ACCENT = '#c1543c'
PALETTE = ['#4c6b8a', '#c1543c', '#7a9e7e', '#b08d57', '#8b6b9c', '#5c8a8a', '#9c5c6b', '#7a7a4c']
RELIABILITY_COLORS = {'CONSISTENT': '#4c6b8a', 'HIGH_VARIANCE': '#c1543c', 'SMALL_SAMPLE': '#b0b0b0'}

plt.rcParams.update({
    'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': INK, 'text.color': INK,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.grid': True, 'grid.color': GRID,
    'grid.linewidth': 0.6, 'axes.axisbelow': True, 'figure.facecolor': 'white',
    'axes.facecolor': 'white', 'savefig.facecolor': 'white',
})


def _new_fig():
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    return fig, ax


def _finish(fig, ax, path, title, source):
    ax.set_title(title, fontsize=13, color=INK, pad=14, loc='left')
    fig.text(0.01, 0.01, source, fontsize=7.5, color=MUTED, ha='left', va='bottom')
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def _source_line(n_ready):
    return ('M2Radar data/radar.db, analysis-ready corpus n=%d, %s'
            % (n_ready, datetime.date.today().isoformat()))


SELECTION_BIAS_NOTE = (
    'The analysis-ready corpus is not a random sample of the niche: deep.py only ever '
    'processed reels that score.py had already ranked near the top of their creator\'s output, '
    'so its median robust_z is above zero by construction. Any contrast computed inside it '
    'compares strong videos with other strong videos, not strong with average '
    '(docs/M2RADAR_ANALYSIS_METHOD.md §1.4).'
)


class ChartSet:
    """Collects one chart's outputs and writes the PNG + sidecar together, or the
    skipped sidecar alone when n<MIN_N."""

    def __init__(self, out_dir, n_ready):
        self.out_dir = out_dir
        self.n_ready = n_ready
        self.index = []

    def skip(self, name, title, reason, n=0):
        sidecar = {
            'title': title, 'n': n, 'status': 'skipped', 'reason': reason,
            'source': _source_line(self.n_ready),
        }
        self._write_sidecar(name, sidecar)
        self.index.append({'name': name, 'title': title, 'status': 'skipped', 'reason': reason, 'n': n})

    def emit(self, name, title, n, variables, method, limitations, draw_fn):
        if n < MIN_N:
            self.skip(name, title, 'n=%d (<%d), suppressed' % (n, MIN_N), n=n)
            return
        fig, ax = _new_fig()
        try:
            draw_fn(fig, ax)
        except Exception as exc:  # a drawing bug must not lose the other 17 charts
            plt.close(fig)
            self.skip(name, title, 'draw error: %r' % (exc,), n=n)
            return
        source = _source_line(self.n_ready)
        png_path = os.path.join(self.out_dir, name + '.png')
        _finish(fig, ax, png_path, '%s (n=%d)' % (title, n), source)
        full_limitations = limitations + ' ' + SELECTION_BIAS_NOTE
        sidecar = {
            'title': title, 'n': n, 'source': source, 'variables': variables,
            'method': method, 'interpretation': '', 'limitations': full_limitations,
        }
        self._write_sidecar(name, sidecar)
        self.index.append({'name': name, 'title': title, 'status': 'ok', 'n': n, 'png': name + '.png'})

    def _write_sidecar(self, name, sidecar):
        path = os.path.join(self.out_dir, name + '.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(sidecar, fh, ensure_ascii=False, sort_keys=True, indent=1, default=str)

    def write_index(self):
        path = os.path.join(self.out_dir, 'index.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({'generated_at': rd.now_iso(), 'charts': self.index}, fh,
                     ensure_ascii=False, sort_keys=True, indent=1, default=str)
        return path


# ---------------------------------------------------------------------------
# individual charts
# ---------------------------------------------------------------------------

def chart_creator_median_views(cs, creator_rows):
    rows = [r for r in creator_rows if r.get('median_play') is not None]
    rows.sort(key=lambda r: -r['median_play'])
    top = rows[:30]

    def draw(fig, ax):
        labels = [r['username'] or str(r['pk']) for r in top]
        vals = [r['median_play'] for r in top]
        colors = [RELIABILITY_COLORS.get(r.get('reliability'), MUTED) for r in top]
        y = range(len(top))
        ax.barh(list(y), vals, color=colors)
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels, fontsize=7)
        ax.invert_yaxis()
        ax.set_xscale('log')
        ax.set_xlabel('median play count (log scale)')
        ax.set_ylabel('creator')

    cs.emit('creator_median_views', 'Creator median views, top 30', len(top),
           variables={'x': 'median_play (log)', 'y': 'username', 'color': 'reliability'},
           method='creator_stats latest snapshot, sorted by median_play desc, top 30 creators.',
           limitations='Only creators with a computed median_play; small creators (SMALL_SAMPLE) are shown but not comparable to CONSISTENT ones.',
           draw_fn=draw)


def chart_creator_dispersion(cs, creator_rows):
    rows = [r for r in creator_rows if r.get('median_play') is not None and r.get('mad_play') is not None]

    def draw(fig, ax):
        by_rel = collections.defaultdict(list)
        for r in rows:
            by_rel[r.get('reliability') or 'UNKNOWN'].append(r)
        for rel, grp in by_rel.items():
            # a single-video creator has mad_play == 0 by construction; log-scale cannot
            # place a zero, so it gets a visible floor rather than silently vanishing.
            ax.scatter([g['median_play'] for g in grp], [max(g['mad_play'], 1e-6) for g in grp],
                      s=22, alpha=0.75, color=RELIABILITY_COLORS.get(rel, MUTED), label=rel)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('median play (log)')
        ax.set_ylabel('MAD of play (log)')
        ax.legend(fontsize=8, frameon=False)

    cs.emit('creator_dispersion', 'Creator median vs MAD (dispersion)', len(rows),
           variables={'x': 'median_play (log)', 'y': 'mad_play (log)', 'color': 'reliability'},
           method='One point per creator, creator_stats latest snapshot. Colour = reliability label (CONSISTENT/HIGH_VARIANCE/SMALL_SAMPLE).',
           limitations='MAD and median both in raw play units, not log(play); a creator with one viral outlier can still show low MAD if the rest of their output is steady.',
           draw_fn=draw)


def chart_view_lift_distribution(cs, video_rows):
    vals = [r['view_lift'] for r in video_rows if r.get('view_lift') is not None]

    def draw(fig, ax):
        ax.hist(vals, bins=40, color=BAR, edgecolor='white', linewidth=0.3)
        ax.set_yscale('log')
        ax.set_xlabel('view_lift  (play / creator_median_play - 1)')
        ax.set_ylabel('videos (log count)')
        ax.axvline(0, color=ACCENT, linewidth=1, linestyle='--')

    cs.emit('video_view_lift_distribution', 'Video performance ratio distribution (view_lift)', len(vals),
           variables={'x': 'view_lift', 'y': 'count (log)'},
           method='Histogram (40 bins) of view_lift across every ingested code with a creator median; y-axis log-scaled because the count itself is heavy-tailed.',
           limitations='view_lift is unbounded below at -1 and unbounded above; extreme creators with very few videos can produce large swings.',
           draw_fn=draw)


def _category_box(cs, name, title, video_rows, field, metric='robust_z', top_k=12):
    groups = collections.defaultdict(list)
    for r in video_rows:
        v = r.get(field)
        m = r.get(metric)
        if v and m is not None:
            groups[v].append(m)
    groups = {k: v for k, v in groups.items() if len(v) >= MIN_N}
    ordered = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:top_k]
    n = sum(len(v) for _, v in ordered)

    def draw(fig, ax):
        labels = [k for k, _ in ordered]
        data = [v for _, v in ordered]
        bp = ax.boxplot(data, vert=False, patch_artist=True, showfliers=False, widths=0.6)
        for patch in bp['boxes']:
            patch.set_facecolor(BAR)
            patch.set_alpha(0.55)
        for med in bp['medians']:
            med.set_color(ACCENT)
        ax.set_yticks(range(1, len(labels) + 1))
        ax.set_yticklabels(['%s (n=%d)' % (l, len(d)) for l, d in zip(labels, data)], fontsize=7)
        ax.invert_yaxis()
        ax.axvline(0, color=GRID, linewidth=1)
        ax.set_xlabel(metric)
        ax.set_ylabel(field)

    cs.emit(name, title, n,
           variables={'x': metric, 'y': field, 'n_per_group': '>= %d' % MIN_N},
           method='Boxplot of %s grouped by %s, groups with fewer than %d videos dropped, top %d groups by size shown, outlier points hidden for readability.'
                  % (metric, field, MIN_N, top_k),
           limitations='Categories are populated only where the ta-v1/fa-v1 semantic analysis has run (analysis-ready-adjacent codes), a small and non-random slice of the corpus.',
           draw_fn=draw)


def chart_script_vs_performance(cs, video_rows):
    rows = [r for r in video_rows if r.get('total_words') is not None and r.get('robust_z') is not None]

    def draw(fig, ax):
        ax.scatter([r['total_words'] for r in rows], [r['robust_z'] for r in rows],
                  s=14, alpha=0.55, color=BAR)
        ax.set_xlabel('total script words')
        ax.set_ylabel('robust_z (creator-relative, log-play)')
        ax.axhline(0, color=GRID, linewidth=1)

    cs.emit('script_length_vs_performance', 'Script length vs performance', len(rows),
           variables={'x': 'total_words', 'y': 'robust_z'},
           method='Scatter of total script word count against robust_z, one point per code with both values.',
           limitations='total_words only exists where a transcript was analysed (ta-v1); silent/no-speech reels are absent from this chart entirely, not at zero.',
           draw_fn=draw)


def chart_hook_length_vs_performance(cs, video_rows):
    rows = [r for r in video_rows if r.get('hook_s') is not None and r.get('robust_z') is not None]

    def draw(fig, ax):
        ax.scatter([r['hook_s'] for r in rows], [r['robust_z'] for r in rows],
                  s=14, alpha=0.55, color=BAR)
        ax.set_xlabel('hook length, seconds')
        ax.set_ylabel('robust_z')
        ax.axhline(0, color=GRID, linewidth=1)

    cs.emit('hook_length_vs_performance', 'Hook length vs performance', len(rows),
           variables={'x': 'hook_s', 'y': 'robust_z'},
           method='Scatter of hook duration (seconds, from the first beat(s) tagged hook/hook_extension) against robust_z.',
           limitations='hook_s is only populated where beats exist; timing-fallback-only codes are excluded.',
           draw_fn=draw)


def chart_duration_vs_performance(cs, video_rows):
    rows = [r for r in video_rows if r.get('dur') is not None and r.get('robust_z') is not None]

    def draw(fig, ax):
        ax.scatter([r['dur'] for r in rows], [r['robust_z'] for r in rows],
                  s=10, alpha=0.4, color=BAR)
        ax.set_xlabel('video duration, seconds')
        ax.set_ylabel('robust_z')
        ax.axhline(0, color=GRID, linewidth=1)

    cs.emit('duration_vs_performance', 'Video duration vs performance', len(rows),
           variables={'x': 'dur (seconds)', 'y': 'robust_z'},
           method='Scatter of reel duration (from reels, newest reading) against robust_z, across the whole ingested corpus (not just analysis-ready).',
           limitations='Uses the metric-only corpus (N_ingested), the widest denominator; duration itself carries no visual or script evidence.',
           draw_fn=draw)


def chart_scenes_vs_performance(cs, video_rows):
    rows = [r for r in video_rows if r.get('scenes_n') is not None and r.get('robust_z') is not None]

    def draw(fig, ax):
        ax.scatter([r['scenes_n'] for r in rows], [r['robust_z'] for r in rows],
                  s=16, alpha=0.55, color=BAR)
        ax.set_xlabel('scene count')
        ax.set_ylabel('robust_z')
        ax.axhline(0, color=GRID, linewidth=1)

    cs.emit('scenes_vs_performance', 'Scene count vs performance', len(rows),
           variables={'x': 'scenes_n', 'y': 'robust_z'},
           method='Scatter of scenes_n (frame_labels/scenes derived) against robust_z.',
           limitations='Legacy corpus scenes are runs of identical frame_type across 9 fixed samples, not detected shot boundaries; scenes_n is a lower bound on real cuts.',
           draw_fn=draw)


def chart_cuts_per_min_vs_performance(cs, video_rows):
    rows = [r for r in video_rows if r.get('cuts_per_min') is not None and r.get('robust_z') is not None]

    def draw(fig, ax):
        colors = [BAR if r.get('cut_metric_quality') == 'scene-v1' else MUTED for r in rows]
        ax.scatter([r['cuts_per_min'] for r in rows], [r['robust_z'] for r in rows],
                  s=14, alpha=0.55, c=colors)
        ax.set_xlabel('cuts per minute')
        ax.set_ylabel('robust_z')
        ax.axhline(0, color=GRID, linewidth=1)
        ax.text(0.02, 0.02,
               'caveat: legacy points (grey) are an ffmpeg scene-score count, not shot-boundary detection',
               transform=ax.transAxes, fontsize=7, color=MUTED, va='bottom')

    cs.emit('cuts_per_min_vs_performance', 'Cut frequency vs performance', len(rows),
           variables={'x': 'cuts_per_min', 'y': 'robust_z', 'color': 'cut_metric_quality (grey=legacy count-only)'},
           method='Scatter of cuts_per_min against robust_z; legacy (ffmpeg_scene_0.35_count_only) and detector (scene-v1) points share the same axis but are not the same measurement.',
           limitations='cut_metric_quality=ffmpeg_scene_0.35_count_only is a relative busy/calm signal inside this dataset only, never an absolute or externally comparable cut rate (docs/M2RADAR_ANALYSIS_METHOD.md §7.1).',
           draw_fn=draw)


def _share_vs_performance(cs, name, title, video_rows, share_col):
    rows = [r for r in video_rows if r.get(share_col) is not None and r.get('robust_z') is not None]

    def draw(fig, ax):
        ax.scatter([r[share_col] for r in rows], [r['robust_z'] for r in rows],
                  s=14, alpha=0.55, color=BAR)
        ax.set_xlabel(share_col + ' (share of labelled samples)')
        ax.set_ylabel('robust_z')
        ax.axhline(0, color=GRID, linewidth=1)

    cs.emit(name, title, len(rows),
           variables={'x': share_col, 'y': 'robust_z'},
           method='Scatter of %s against robust_z, one point per analysed code.' % share_col,
           limitations='Shares are estimated from 9 fixed-timecode samples per legacy video, not true screen-time fractions (docs/M2RADAR_ANALYSIS_METHOD.md §7).',
           draw_fn=draw)


def chart_cta_type_vs_performance(cs, video_rows):
    _category_box(cs, 'cta_type_vs_performance', 'CTA type vs performance', video_rows, 'cta_type')


def chart_topic_vs_performance(cs, video_rows):
    _category_box(cs, 'topic_vs_performance', 'Topic vs performance', video_rows, 'topic')


def chart_pain_vs_performance(cs, video_rows):
    _category_box(cs, 'pain_vs_performance', 'Pain point vs performance', video_rows, 'pain')


def chart_hook_type_vs_performance(cs, video_rows):
    _category_box(cs, 'hook_type_vs_performance', 'Hook type vs performance', video_rows, 'hook_type')


def chart_script_parts_strong_weak(cs, video_rows):
    with_script = [r for r in video_rows if rd.script_block(r).get('part_source') == 'beats']
    strong, weak, cutoffs = rd.split_strong_weak(with_script)
    n = (len(strong) + len(weak)) if strong is not None else 0
    if cutoffs is None:
        cs.skip('script_parts_strong_vs_weak', 'Script part shares, strong vs weak',
               'fewer than %d codes with a script block and robust_z on each side' % (4 * stats.SMALL_CELL_N))
        return
    strong_stats = rd.script_stats_for(strong)
    weak_stats = rd.script_stats_for(weak)

    def draw(fig, ax):
        roles = list(rd.ROLES)
        colors = PALETTE
        for row_idx, (label, st) in enumerate((('strong (top quartile)', strong_stats),
                                                ('weak (bottom quartile)', weak_stats))):
            left = 0.0
            for i, role in enumerate(roles):
                share = st[role]['median_share'] or 0.0
                ax.barh(row_idx, share, left=left, color=colors[i % len(colors)],
                        edgecolor='white', linewidth=0.5,
                        label=role if row_idx == 0 else None)
                left += share
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['strong (n=%d)' % len(strong), 'weak (n=%d)' % len(weak)])
        ax.set_xlabel('median share of script (stacked, per part)')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=4, fontsize=7, frameon=False)

    cs.emit('script_parts_strong_vs_weak', 'Script part shares, strong vs weak', n,
           variables={'roles': list(rd.ROLES), 'split': 'top vs bottom quartile of robust_z'},
           method='Median share of total script time per role (features_json.script.<role>_share), stacked, compared between the top and bottom robust_z quartile inside the analysis-ready-adjacent corpus.',
           limitations='Shares are medians taken independently per role, so the two stacked bars need not sum to exactly 1.0; read each segment on its own, not the total bar length.',
           draw_fn=draw)


def chart_visual_sequence_top10(cs, video_rows):
    with_seq = [r for r in video_rows if r.get('visual_sequence')]
    groups = collections.defaultdict(list)
    for r in with_seq:
        groups[r['visual_sequence']].append(r)
    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:10]
    n = sum(len(v) for _, v in ranked)

    def draw(fig, ax):
        labels = ['%s… (n=%d)' % (seq[:28], len(grp)) for seq, grp in ranked]
        counts = [len(grp) for _, grp in ranked]
        lifts = [rd._median([g.get('view_lift') for g in grp]) or 0 for _, grp in ranked]
        y = range(len(ranked))
        ax.barh(list(y), counts, color=BAR)
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels, fontsize=6.5)
        ax.invert_yaxis()
        ax.set_xlabel('frequency (videos)')
        for i, lift in enumerate(lifts):
            ax.text(counts[i], i, '  median view_lift=%.2f' % lift, va='center', fontsize=6.5, color=MUTED)

    cs.emit('visual_sequence_top10', 'Visual sequence frequency, top 10', n,
           variables={'x': 'frequency', 'y': 'visual_sequence (frame types in order, deduped)', 'annotation': 'median view_lift'},
           method='Top 10 most frequent visual_sequence strings (deduplicated consecutive frame types), with each bar\'s median view_lift annotated.',
           limitations='visual_sequence is built from 9 fixed samples per legacy video; two videos edited differently between samples can produce the same string.',
           draw_fn=draw)


def chart_share_vs_save_rate(cs, video_rows):
    rows = [r for r in video_rows if r.get('share_rate') is not None and r.get('save_rate') is not None]

    def draw(fig, ax):
        by_tier = collections.defaultdict(list)
        for r in rows:
            by_tier[r.get('evidence_tier') or 'UNKNOWN'].append(r)
        tier_colors = {'ANALYSIS_READY': BAR, 'FRAMES_ONLY': ACCENT,
                      'TRANSCRIPT_UNUSABLE': '#7a9e7e', 'INGESTED_NOT_ANALYZED': '#b0b0b0'}
        for tier, grp in by_tier.items():
            ax.scatter([g['share_rate'] for g in grp], [g['save_rate'] for g in grp],
                      s=12, alpha=0.5, color=tier_colors.get(tier, MUTED), label=tier)
        ax.set_xlabel('share_rate')
        ax.set_ylabel('save_rate')
        ax.legend(fontsize=7, frameon=False)

    cs.emit('share_vs_save_rate', 'Share rate vs save rate', len(rows),
           variables={'x': 'share_rate', 'y': 'save_rate', 'color': 'evidence_tier'},
           method='Scatter of share_rate against save_rate for every code where both rates clear the 100-play denominator guard, coloured by evidence tier (engine.corpus.tiers).',
           limitations='Both rates are NULL below 100 plays (denominator guard); coloured only by evidence tier, not creator size.',
           draw_fn=draw)


def chart_corpus_coverage_funnel(cs, t):
    counts = t['counts']
    stages = [
        ('ingested', counts['n_ingested']),
        ('stats (has reels metrics)', counts['n_ingested']),
        ('transcript row', counts['n_transcript_rows']),
        ('usable transcript', counts['n_transcript_usable']),
        ('frames', counts['n_frames']),
        ('analysis-ready', counts['n_ready']),
    ]
    n = counts['n_ingested']

    def draw(fig, ax):
        labels = [s for s, _ in stages]
        vals = [v for _, v in stages]
        y = range(len(stages))
        ax.barh(list(y), vals, color=BAR)
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_xlabel('codes')
        for i, v in enumerate(vals):
            ax.text(v, i, '  %d (%.1f%%)' % (v, 100.0 * v / n if n else 0), va='center', fontsize=8, color=MUTED)

    cs.emit('corpus_coverage_funnel', 'Corpus coverage funnel', n,
           variables={'stages': [s for s, _ in stages]},
           method='Six-stage funnel from engine.corpus.tiers() denominators: ingested -> stats -> transcript row -> usable transcript -> frames -> analysis-ready.',
           limitations='Stages are not strictly nested by pipeline order (frames and transcript are extracted independently); this funnel is a denominator comparison, not a literal drop-off sequence.',
           draw_fn=draw)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def generate(con, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    t = corpus.tiers(con)
    n_ready = t['counts']['n_ready']
    cs = ChartSet(out_dir, n_ready)

    video_rows = rd.build_video_rows(con)
    creator_rows, _snap = rd.build_creator_rows(con, video_rows)

    chart_creator_median_views(cs, creator_rows)
    chart_creator_dispersion(cs, creator_rows)
    chart_view_lift_distribution(cs, video_rows)
    chart_topic_vs_performance(cs, video_rows)
    chart_pain_vs_performance(cs, video_rows)
    chart_hook_type_vs_performance(cs, video_rows)
    chart_script_vs_performance(cs, video_rows)
    chart_hook_length_vs_performance(cs, video_rows)
    chart_duration_vs_performance(cs, video_rows)
    chart_cta_type_vs_performance(cs, video_rows)
    chart_scenes_vs_performance(cs, video_rows)
    chart_cuts_per_min_vs_performance(cs, video_rows)
    _share_vs_performance(cs, 'a_roll_share_vs_performance', 'A-roll share vs performance', video_rows, 'a_roll_share')
    _share_vs_performance(cs, 'split_share_vs_performance', 'Split-screen share vs performance', video_rows, 'split_share')
    chart_script_parts_strong_weak(cs, video_rows)
    chart_visual_sequence_top10(cs, video_rows)
    chart_share_vs_save_rate(cs, video_rows)
    chart_corpus_coverage_funnel(cs, t)

    index_path = cs.write_index()
    return cs.index, index_path


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', default=os.path.join(REPO, 'reports', 'charts'))
    ap.add_argument('--db', default=corpus.DB_PATH)
    args = ap.parse_args(argv)

    con = corpus.connect(args.db)
    try:
        index, index_path = generate(con, args.out)
    finally:
        con.close()
    n_ok = sum(1 for c in index if c['status'] == 'ok')
    n_skipped = len(index) - n_ok
    print('charts: %d ok, %d skipped, index at %s' % (n_ok, n_skipped, index_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
