# Instagram safe zones — production rules

Machine-readable version: `zones.json`. QA script: `overlays/check-overlay.mjs`.
Every number here traces to `research/instagram-safe-zones.md`/`.json` or is derived
with arithmetic shown in `zones.json`. This file is the human summary, not a new source.

Zone A = always safe (hook, mark, verdict card, format label only).
Zone B = organic-only, covered by ads UI but not organic Reels UI (subtitles, claim bar).
Zone C = never (nothing with meaning).

## 1. reel — 1080x1920 (9:16)

| Zone | Box (x,y,w,h) | Confidence |
|---|---|---|
| A | 65,269,950,979 | meta-official |
| B | 65,1248,885,222 | secondary |
| C | top 0,0,1080,269 / bottom 0,1470,1080,450 / sides / right rail 950,1000,130,470 | meta-official edges, right rail secondary |

What may sit where: hook, mark, verdict card, format label -> A only. Burned-in
subtitles, persistent claim bar -> A or B. Nothing -> C.
Grid crop band (cover as 3:4 tile): y 240 to 1660 (derived: tile height at width 1080
is 1080/0.75=1440; (1920-1440)/2=240 lost top and bottom).
Right rail: no confirmed pixel box from Meta; drawn as a caution zone, not a fact.
How to check: run `check-overlay.mjs reel <element-boxes.json>`; any primary element
outside A, or any element touching a C rect, fails.

## 2. story — 1080x1920 (9:16)

| Zone | Box | Confidence |
|---|---|---|
| A | 65,269,950,979 (same as reel) | meta-official |
| B | none | n/a |
| C | everything outside A | meta-official edges |

Sticker/reply UI is unpredictable, so there is no Zone B for Stories — treat all of it
as C except A. Legacy 20% bottom-margin figure (340px) is superseded by the current
35% (672px) Meta ad-spec figure; do not use 20% for new work, flag it if you see it in
an old template.
How to check: same script with placement `story`; B is empty so nothing is "organic-only".

## 3. feed-portrait — 1080x1350 (4:5)

| Zone | Box | Confidence |
|---|---|---|
| A | 48,48,984,1254 (full canvas minus 48px margin) | practice |
| B | none | n/a |
| C | 48px margin on all 4 sides | practice |

No UI overlay on feed posts (this is why no Zone B). Grid crop loses 33.5px per side
(derived: crop width = 1350*0.75=1012.5, (1080-1012.5)/2=33.75). The 48px margin
already covers this, so keeping meaning inside x 48..1032 survives the grid crop too.
How to check: `check-overlay.mjs feed-portrait <boxes.json>`.

## 4. feed-square — 1080x1080 (1:1)

| Zone | Box | Confidence |
|---|---|---|
| A | 135,0,810,1080 | derived |
| B | 0,0,135,1080 and 945,0,135,1080 ("feed only") | derived |
| C | none | n/a |

Grid crop takes 135px off each side (derived: crop width=1080*0.75=810,
(1080-810)/2=135). Content in the two 135px side strips shows in the single-post feed
view but is lost in the profile grid tile — decorative background only, no meaning.
How to check: `check-overlay.mjs feed-square <boxes.json>`.

## 5. feed-tall — 1080x1440 (3:4)

| Zone | Box | Confidence |
|---|---|---|
| A | 48,48,984,1344 | practice |
| B | none | n/a |
| C | 48px margin on all 4 sides | practice |

Exact match to the grid tile ratio — no crop occurs. This is why Meta added the native
3:4 upload option in 2025 (secondary, alternativeto.net).
How to check: `check-overlay.mjs feed-tall <boxes.json>`.

## 6. carousel — 1080x1350 (4:5), same zones as feed-portrait

Use feed-portrait's A/B/C verbatim. First slide's aspect ratio applies to the whole
carousel (secondary consensus); later slides with a different ratio are silently
auto-cropped, no upload error. Keep every slide identical pixel dimensions. 2 to 10
slides, min resolution 1080x1080 (meta-official, carousel ad spec).
How to check: run the feed-portrait check against every slide's boxes.

## 7. avatar — 1080x1080 (1:1), circular crop

| Zone | Shape | Confidence |
|---|---|---|
| A | circle cx=540 cy=540 r=486 | derived |
| C | ring between r=486 and r=540, plus square corners | derived |

10% inset (1080 diameter -> 972) is this system's own convention; Meta publishes no
inset number. Recommend the mark occupy 55-60% of the circle diameter (594-648px) for
legibility at small displayed sizes (disputed at 32-150px across sources).
How to check: `check-overlay.mjs avatar <boxes.json>` treats A as the r=486 circle.

## 8. highlight-cover — 1080x1920 (9:16), circular crop

| Zone | Shape | Confidence |
|---|---|---|
| A | circle cx=540 cy=960 r=486 | derived |
| C | ring r=486..540, plus y 0..420 and y 1500..1920 (discarded by crop) | derived |

Crop circle diameter 1080 centered at (540,960): derived from (1920-1080)/2=420 to
1500. Displayed size disputed (110 / 161 / ~700px); design for legibility at 110px,
the smallest reported figure.
How to check: `check-overlay.mjs highlight-cover <boxes.json>`.

## What Meta does not publish (research section 10)

- Exact pixel box for the Reels right-side action-button column.
- Exact coordinates for Stories interactive stickers (qualitative "middle-lower" only).
- Whether Stories' current bottom margin is 35% or the older 20% (Meta's live pages say 35%).
- Displayed avatar circle size (32-150px disputed) and any safe-circle-inset percentage.
- Displayed highlight-cover circle diameter (110 / 161 / ~700px disputed).
- Crop ratio applied to a Reel playing inline in a follower's main feed.
- Any numeric caption/subtitle placement guidance beyond the retired 20% text-overlay rule.

Where this file says "derived," the arithmetic is in `zones.json`. Where it says
"practice," there is no primary source at all — it is agency/blog convention.
