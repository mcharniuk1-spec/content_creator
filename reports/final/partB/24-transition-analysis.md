# 24. Transition Analysis

**Denominators, and a warning that is larger than the chapter.** Two different transition counts exist in
this dataset and they are not interchangeable. The **database** records **663 `hard_cut_or_more`** and
**15 `unknown`** — 678 in total, which is exactly `960 scenes − 282 codes`, i.e. one `transition_in` per
scene after the first.[^1] The **raw fa-v1 reads** of the same corpus record **1 306 `hard_cut_or_more`,
844 `same_shot` and 16 `unknown`** across 295 codes, because they judge every adjacent *sample pair* rather
than every scene boundary.[^2] Cut-frequency statistics are a third quantity again, computed by ffmpeg over
**282** codes. Every number below says which of the three it came from.

## Only one transition type is observed anywhere in the corpus

Per SPEC §5 a transition is recorded **only where fa-v1 actually saw two adjacent labelled samples
differ**; `same_shot` and everything unobserved becomes `unknown`. The consequence is absolute and must be
stated before anything else: **there is no evidence in this dataset for any transition type other than a
hard cut.** No dissolves, whips, match cuts, zoom transitions or speed ramps are recorded anywhere across
2 645 labelled frames. **Their absence is a measurement artefact of the nine-sample grid, not a finding
about the niche** — a 0.4-second whip pan between two samples is invisible by construction, and a
dissolve between two visually similar shots is coded `same_shot`.

| source | hard_cut_or_more | same_shot | unknown | unit |
|---|---:|---:|---:|---|
| database (`scenes.transition_in`, 282 codes) | **663** | not stored | 15 | one per scene boundary |
| raw fa-v1 reads (295 codes) | **1 306** | 844 | 16 | one per adjacent sample pair |

The gap between 663 and 1 306 is the cost of the scene collapse: consecutive samples sharing a
`frame_type` are merged into one scene, so a reel that alternates A-roll and screen twice within a run of
identical labels loses its internal changes. **Both numbers are floors on the real cut count**, and the
larger one is still a floor — nine samples over a 54-second median runtime cannot see eight cuts between
samples. Per reel, the raw reads observe a median of **5** hard cuts (mean 4.43, max 8), with **28 of 295**
codes showing none at all.

## Cut frequency: no relationship, and a metric that cannot carry a claim

![Cut frequency vs performance, n=282](reports/charts/cuts_per_min_vs_performance.png)

| | value |
|---|---|
| median `cuts_per_min` | **7.26** (p25 2.49, p75 13.68, max 78.4, n=282) |
| Spearman vs `robust_z` | **+0.056 (p=0.36)** |
| Spearman vs `view_lift` | **+0.003 (p=0.96)** |
| strong vs weak quartile | 7.06 vs 6.75 (p=0.420) |
| rows reporting exactly zero cuts | **38 of 282** |
| `cut_metric_quality` on every row | `ffmpeg_scene_0.35_count_only` |

There is no relationship in any metric, and the distribution is so wide (2.49 to 13.68 at the quartiles,
maximum 78.4) that a target would be meaningless even if one existed. The 38 zero rows are
indistinguishable from a detector that never fired.

**The metric itself is the real finding.** Every point on the chart comes from
`ffmpeg -filter:v "select='gt(scene,0.35)',showinfo"` counted as `pts_time:` lines — a **scene-score
threshold count, not shot-boundary detection**. It misses hard cuts between visually similar shots (same
speaker, same set, same framing — precisely the talking-head format that dominates this niche) and
over-counts whip pans, flashes, heavy zooms and screen-recording scrolls, with a fixed 0.35 threshold and
no per-clip calibration. It is usable as a relative busy-versus-calm signal **inside this dataset only**.
**No M2 output may quote a cut rate from it**, and no claim comparing M2's editing density with the
niche's is permitted from this wave.

## What the reels themselves show

**Visual reading.** The two visual extremes of the corpus are also its transition extremes, and both work.
[DZgBxjnBzMe](https://www.instagram.com/reel/DZgBxjnBzMe/) — 207× its author's median, 1 570 719 plays —
shows **seven `same_shot` transitions and one hard cut** across its nine samples: one continuous take of a
laptop running a Jarvis script beside a phone changing state. At the other end,
[DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/) — the corpus's highest lift at 399.4× — shows
**eight hard cuts out of eight observed pairs**, cutting between website mockups, two Claude Code terminal
sessions and the presenter. Zero observed cuts and maximum observed cuts, both at the top of the
distribution. Whatever separates these reels, it is not their edit.

**Transcript reading.** What the two share is that the cut is never asked to carry meaning. DZgBxjnBzMe
speaks 14 words and lets the artefact act; DYC-x8DogOI's mechanism beat names a step per cut ("Step two,
you add the UI UX Pro Max skill so Claude builds clean modern layouts automatically", 11.8–28.9 s) so each
cut coincides with a new named object rather than with a rhythmic beat. That is the only transition-level
craft observation this dataset supports, and it is an observation, not a measurement.

## Strategic implication

**(1) Keep the one-take rule.** Not because the data argues for it — the data argues for nothing here —
but because nothing argues against it, and at five publications a week with one filming day, editing is a
consumable resource rather than a requirement. A change of speaker stays the only cut M2 allows.
**(2) Never publish a claim about M2's cut rate, or about the niche's.** The metric does not support it,
and quoting it would be the exact kind of confident wrong number this method document exists to prevent.
**(3) Do not spend editing budget aligning cuts to script beats** (chapter 25). **(4) If the transition
question is ever to be answered properly, it needs the new `scene-v1` detector over a random sample of the
2 914 unprocessed codes** — more features on the same 295 reels will not help, because the limitation is
the nine-sample grid, not the feature set.

**Confidence: RELIABLE** for the statement that only hard cuts are observed (direct count, and the reason
for the absence of other types is structural and documented). **RELIABLE** for the cut-frequency null
(n=282, all four metrics, plus the quartile test). **INSUFFICIENT** for any quantitative statement about
*how many* cuts a reel in this niche contains: the DB count (663) and the raw fa-v1 count (1 306) differ by
a factor of two for documented reasons, both are floors, and `cut_metric_quality` is count-only on all 282
rows. No causal claim.

[^1]: Database counts from `reports/data/visual_patterns.json` → `transitions_observed`, built from
`scenes.transition_in`. Row counts from `reports/data/manifest.json` → `row_counts`: `scenes` 960,
`deepdives` 282; 960 − 282 = 678 = 663 + 15.

[^2]: Computed for this chapter over the per-video frame analyses — the source fa-v1 wrote before ingest
collapsed adjacent identical samples into scenes:

    import json, glob, collections
    c = collections.Counter()
    files = glob.glob('data/analysis/frames/*.json')
    for p in files:
        d = json.load(open(p))
        c.update(t['kind'] for t in (d.get('transitions_observed') or []))
    print(c, len(files))

Returns `Counter({'hard_cut_or_more': 1306, 'same_shot': 844, 'unknown': 16})` over 295 files. The
per-reel median (5), mean (4.43), maximum (8) and zero-count (28 codes) come from the same pass.
