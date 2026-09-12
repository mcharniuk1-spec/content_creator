# PRODUCTION.md — reproduction check (2026-09-12)

`PRODUCTION.md` is the approved shooting template and is not edited in place. This note records
which of its measured figures reproduce against the current database (`data/radar.db`, 3 211 unique
reel codes across three snapshots, metrics-only statistics; `engine/stats.py`, `reports/data/*`) and
which do not. The decision whether to update `PRODUCTION.md` belongs to Misha.

| Statement in PRODUCTION.md | Reproduced value (2026-09-12) | Verdict |
|---|---|---|
| "Measured on our own set of 2 352 competitor reels" | 3 211 unique codes (2 352 was the first snapshot only) | outdated denominator |
| "Winners' median is 55 seconds against 47 for the rest" | winners (robust_z ≥ 2, n=375) **46.8 s** vs rest **47.8 s** | does not reproduce |
| "Under twenty seconds: 5 % of winners, 13 % of the rest" | **14.4 %** of winners vs **12.4 %** of the rest | direction reversed |
| "Longer than ninety is 15 % against 8 %" | **9.9 %** vs **8.5 %** | does not reproduce |
| "A share separates a winner 3.6× more reliably than anything else; a save, 2.8×" | share **2.62×**, save **2.09×** (n=2 899 reels with both rates) | weaker than stated, direction holds |
| "Comment bait does not work (28 % of top reels vs 26 %)" | not re-measured on the same definition; in the analysis-ready corpus a comment gate raises saves ×2.8 and shares ×1.8 but leaves reach untouched (p=0.58) — see insight I-12 | different measure; conclusion "does not buy reach" holds |
| "Editing is close to optional (median 0.12 cuts/s; 44 of 100 no cuts)" | cannot be re-measured: the stored cut metric is an ffmpeg scene-change count without timestamps | unavailable |
| "'AI inside a business process' 22 shares per thousand vs 38; ceiling 2 755 shares" | not re-measured in this pass (topic taxonomy changed) | unverified |
| 50–70 s one-take template, banner held, one closing line | not contradicted: duration is flat against performance everywhere (I-02); the template stands on production economy, not on a measured advantage | keep, with the honest rationale |

Sources: `data/analysis/insights.json` (I-02, I-12, I-22), `reports/analysis/01-general-conclusions.md` §C/§H,
`reports/final/partB/33-recommendations-for-our-positioning.md`, `reports/audit/06-final-qa.md` BL-5.
