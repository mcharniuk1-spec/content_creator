#!/usr/bin/env python3
"""Scene/cut detection and frame extraction. engine/SPEC.md §6 step 4.

Pure functions, no DB access here — `engine.local_pipeline.process_video` calls these
and writes the results into `frames` / `scenes` / `deepdives`. Same ffmpeg invocation
style as `deep.py` (one process per operation, `imageio_ffmpeg`'s bundled binary),
generalized to variable-length scene lists instead of the fixed-9-frame sampling.

Empirical note (kept here for whoever touches this next): ffmpeg's built-in `scene`
score is computed on the luma (Y) plane only. Two colors that are visually very
different in RGB but land on nearly the same luma (e.g. ffmpeg's named `red` and
`green`) will NOT trigger a cut even at threshold 0 — this is exactly what tripped up
the test fixture during development. High-contrast test colors (e.g. black/gray/white)
are the reliable way to synthesize cuts.
"""
import hashlib
import pathlib
import re
import subprocess

PTS_TIME_RX = re.compile(r'pts_time:([0-9.]+)')


def detect_cuts(ff, mp4, threshold=0.30):
    """Cut timestamps (seconds) via ffmpeg's scene-change filter. Returns a sorted list
    of floats; empty list if ffmpeg finds nothing or the run fails outright."""
    p = subprocess.run(
        [ff, '-i', str(mp4), '-filter:v', f"select='gt(scene,{threshold})',showinfo",
         '-f', 'null', '-'],
        capture_output=True, text=True)
    times = sorted({round(float(m), 2) for m in PTS_TIME_RX.findall(p.stderr)})
    return times


def scene_intervals(cuts, dur, min_len=0.4):
    """Cut timestamps -> list of (start, end) scene intervals spanning [0, dur].

    Intervals shorter than `min_len` are merged into the following interval (or into
    the previous one if it's the last interval) so a spurious near-duplicate cut never
    produces a scene with no usable keyframe."""
    if not dur or dur <= 0:
        return []
    bounds = sorted({0.0, *(round(c, 2) for c in cuts if 0 < c < dur), round(dur, 2)})
    intervals = []
    i = 0
    while i < len(bounds) - 1:
        start = bounds[i]
        end = bounds[i + 1]
        while (end - start) < min_len and i + 2 < len(bounds):
            i += 1
            end = bounds[i + 1]
        intervals.append((round(start, 2), round(end, 2)))
        i += 1
    if len(intervals) > 1 and (intervals[-1][1] - intervals[-1][0]) < min_len:
        last = intervals.pop()
        s0, _ = intervals[-1]
        intervals[-1] = (s0, last[1])
    return intervals


def keyframe_times(intervals, hook_times=(0.4, 1.2, 2.4, 4.0), mid_over=6.0):
    """One keyframe near the start of each scene, a mid-frame for scenes longer than
    `mid_over` seconds, plus the fixed hook timestamps (compat with the legacy
    fixed9 sampling) wherever they land inside the video's duration."""
    if not intervals:
        return []
    dur = intervals[-1][1]
    times = set()
    for start, end in intervals:
        if end <= start:
            continue
        t = min(start + 0.2, end - 0.05)
        if 0 <= t < dur:
            times.add(round(t, 2))
        if (end - start) > mid_over:
            times.add(round((start + end) / 2, 2))
    for h in hook_times:
        if h < dur - 0.1:
            times.add(round(h, 2))
    return sorted(times)


def extract_frames(ff, mp4, times, out_dir, scale=540, start_idx=0):
    """One ffmpeg invocation per timestamp (robust to a single bad seek — a failed
    frame is skipped and reported, never aborts the batch). Returns
    `[(idx, t, path), ...]` for the frames that actually landed on disk; `idx` starts
    at `start_idx` so callers can continue numbering after whatever is already in the
    `frames` table for this code."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = [], []
    for i, t in enumerate(times):
        idx = start_idx + i
        path = out_dir / f's{idx:02d}_{t:g}s.jpg'
        if path.exists() and path.stat().st_size > 0:
            ok.append((idx, t, str(path)))
            continue
        p = subprocess.run(
            [ff, '-y', '-loglevel', 'error', '-ss', str(t), '-i', str(mp4),
             '-frames:v', '1', '-q:v', '3', '-vf', f'scale={scale}:-1', str(path)],
            capture_output=True, text=True)
        if path.exists() and path.stat().st_size > 0:
            ok.append((idx, t, str(path)))
        else:
            failed.append((idx, t, (p.stderr or '').strip()[-300:]))
    if failed:
        print(f'extract_frames: {len(failed)}/{len(times)} frame(s) failed: '
              + '; '.join(f't={t}s idx={idx}: {err}' for idx, t, err in failed))
    return ok


def contact_sheet(ff, out_dir, sheet_path, cols=3):
    """Tile every jpg in `out_dir` into a contact sheet at `sheet_path` (must live
    outside `out_dir`, or the glob below would try to tile the sheet into itself).
    Returns the sheet path on success, None if there were no frames to tile or ffmpeg
    failed."""
    out_dir = pathlib.Path(out_dir)
    sheet_path = pathlib.Path(sheet_path)
    frames = sorted(out_dir.glob('*.jpg'))
    if not frames:
        return None
    n = len(frames)
    rows = -(-n // cols)  # ceil
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ff, '-y', '-loglevel', 'error', '-pattern_type', 'glob',
         '-i', str(out_dir / '*.jpg'), '-filter_complex', f'tile={cols}x{rows}',
         '-q:v', '4', str(sheet_path)],
        capture_output=True, text=True)
    if sheet_path.exists() and sheet_path.stat().st_size > 0:
        return str(sheet_path)
    return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()
