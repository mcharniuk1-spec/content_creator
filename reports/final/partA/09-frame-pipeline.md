# 9. Frame Pipeline

## Legacy fixed-9 sampling vs the new scene-v1 detector

`deep.py`'s legacy method (`timecodes()`) is a fixed sampling schedule, not detection: four early
timestamps (0.4, 1.2, 2.4, 4.0s) to densely cover the hook, then five more spaced evenly across the
remainder, deduplicated and dropped within 0.3s of the end — a 60-second reel yields exactly nine
frames; shorter reels fewer. Extraction uses ffmpeg's approximate `-ss <t> -i` seek, and the source
video is deleted immediately after (SPEC §4.4, "видео не храним"). `deepdives.evidence_state =
'fixed9-v1'` on all 282 rows records this honestly as sampling, not detection.

The new engine method (`engine/scenes.py`, `frames_version='scene-v1'`) is a real detector:
ffmpeg `select='gt(scene,0.30)',showinfo` produces cut timestamps, scenes are the intervals
between them (plus 0 and duration), a keyframe is taken at each scene start +0.2s and, for scenes
over 6s, one additional mid-frame — plus the same four hook-compatibility samples at
0.4/1.2/2.4/4.0s. `boundary_reason='detector'` and a `detector_json` recording the threshold
distinguish this from the legacy sampled scenes at the schema level. As of this migration, **no
scene in the database carries `frames_version='scene-v1'`** — every code remains `DONE_FIXED9`
today, and every visual-share statistic in the analysis chapters is therefore an estimate from 9
samples, not a measurement from detected shots.

## The cut-count caveat

`deepdives.cuts` — whether read from the legacy table or surfaced as `video_features.cuts` /
`cuts_per_min` — comes from ffmpeg's scene-score threshold (`gt(scene, 0.35)`, counted via regex
over `pts_time:` occurrences), not shot-boundary detection. It misses hard cuts between visually
similar shots (same speaker, same set — the dominant talking-head format in this niche), and
over-counts fast camera motion, flashes, whip pans and screen-recording scrolls. The threshold is
fixed at 0.35 with no per-clip calibration, and 38 of 282 deep dives report `cuts = 0`, which is
indistinguishable from a detector that simply never fired. `video_features.cut_metric_quality`
carries this forward explicitly as `ffmpeg_scene_0.35_count_only`, usable only as a relative
"busy vs. calm" signal *inside this dataset* and never comparable to any externally reported cut
rate.

## Contact sheets

Every deep dive produces a 3×3 tiled contact sheet (`data/frames/<code>_sheet.jpg`), the
human-facing visual artifact referenced by `deepdives.sheet` and uploaded directly into the Notion
card body. 295 sheet files exist on the server; all 282 `deepdives.sheet` paths resolve to a real
file. Thirteen sheets have no corresponding `deepdives` row at all (`Db0KA0GIBik`, `DbN7QQsIUrW`
and eleven others) — frames and sheets exist on disk with no cuts, mp4 size or suitability field
recorded for them, a gap named rather than backfilled.

## Frames on disk: 2,645 / 2,653 (+74 archive)

| Set | Rows/files | Note |
|---|---:|---|
| `frames` table, pre-migration | 2,653 rows, 295 unique codes | 293 codes have 9 frames, 2 have 8 (clips too short for the ninth timecode) |
| Files present on server | 2,645 of 2,653 | 8 missing, all one code |
| `frames` table, post-migration | 2,727 rows, 303 unique codes | +74 rows from the August archive import |
| Files verified present, post-migration | 2,719 of 2,727 | Same 8 broken references carried forward |

The local rsync copy of `data/frames/` independently reconciles: 591 entries, 295 sheets, 3,063
jpgs — 2,645 tracked + 9 stale (a re-run at different timecodes left an old set behind under
`DbYh2P-MQnj`) + 114 in a non-reel `web/` directory (leftover from a page build) + 295 sheets.

## The broken code: `DcxV37-CJOC`

All 8 broken frame references belong to one code. The DB holds 9 frame rows; the directory holds
1 jpg. The ffmpeg extraction died after the first frame, but `deep.py` inserts all nine frame rows
unconditionally after the extraction loop, without checking that the files actually landed — a
real bug in the legacy pipeline, not a migration artifact. This same code carries the corpus's
worst transcript (5 words captured from a 62-second reel) and was card id 28, struck out in review.
Post-migration: `frames.exists_ok = 0` on all 8 rows, `frames_state = PARTIAL`,
`media_state = MISSING`, flags `BROKEN_FRAME_REFERENCE` and `MISSING_MEDIA` both set — visible in
the data now, not only in an audit, and unrepairable since the source video is gone by design.

## Alignment features: meaning and limits

`engine/align.py` maps transcript segments/beats to scene intervals by time overlap, writing
`beats.scene_ids_json` or (before beats exist) a segment→scene map into `video_state.flags_json`.
Against the fixed9-v1 legacy corpus this is a measurement floor, not a real alignment: with only
nine sampled points per video, 55 of 1,527 beat boundaries (3.6%) fall within 0.3s of a sampled
scene start, and 215 of 264 codes have no such overlap recorded at all — both the rate itself and
the one downstream comparison drawn from it (aligned vs unaligned robust_z, 1.45 vs 1.25, p=0.603)
are provisional and must be reported as such. `frame_labels.visual_state`
(`a_roll|b_roll|split|screen|text|unknown`) is the practical output of alignment consumed
downstream; it describes what kind of shot a beat's words land on, not a frame-accurate cut.
Alignment only becomes a real measurement once `scene-v1` detected scenes exist to align against —
which, per the section above, is not yet the case for any code in this database.
