# Instagram Safe Zones & Format Specs (accessed 2026-09-08)

Method: Meta's official ad-spec pages (`facebook.com/business/ads-guide/...`) publish exact
percentages/pixels only for **paid** Reels/Stories/Feed/Carousel creative. Meta does **not**
publish a pixel spec sheet for organic-post safe zones, avatar sizes, highlight covers, or the
Reels cover crop — those numbers below come from secondary design-blog measurements and are
labelled accordingly. Where Meta's ad numbers are reused for organic content (same UI chrome),
that's marked "derived."

## 1. Reels

**Meta-official ad safe zone** (`facebook.com/business/ads-guide/update/video/instagram-reels`
and `.../image/instagram-reels`, DE locale, accessed 2026-09-08):
canvas **1440×2560 (9:16)**, min width 250px (<30s) / 500px (≥30s), 1% aspect-ratio tolerance.
> "Lasse mindestens 14% oben, 35% unten und 6% auf jeder Seite deines Assets frei von Text,
> Logos oder anderen wichtigen Gestaltungselementen." → **top 14% (358px), bottom 35% (896px),
> sides 6% each (86px)**.

**Derived for the common 1080×1920 organic canvas** (same %, arithmetic shown in JSON):
top 269px, bottom 672px, sides 65px each → safe content box ≈ 950×979px centered.

Multiple 2026 secondary sources (firstpier.com, billo.app, 1clickreport.com, all accessed
2026-09-08) independently report the same 14/35/6 figures and say Meta **unified** Stories and
Reels ad safe zones to this single spec around March 2026 — before that, Stories used a
different (smaller) bottom margin (see §2). This corroborates what the live Meta pages show.

**Right-side action column** (like/comment/share/save/more, audio disc): Meta does not publish
a pixel box for this. It sits inside the bottom-35%/right-6% zone already excluded above, but
secondary sources agree it is visually wider than the minimum 6% margin in practice — one
guide (kreatli.com) flags it only as "high risk," another (firstpier.com) confirms it exists in
that column without giving coordinates. **No confirmed pixel box exists; see §10.**

**Grid preview (3:4) crop of a Reels cover**, cover uploaded at 1080×1920 (9:16): to fill a 3:4
tile at the grid's fixed width, Instagram must crop the *height* down to 1440px (1080 ÷ 0.75).
Centered crop band = **y 240 → y 1660** of the 1080×1920 canvas (derived; math in JSON). This
is arithmetic, not a Meta-published number — treat as an estimate of how a center-weighted crop
would behave.

**Reels tab**: full 9:16, uncropped (qualitative, widely reported, not disputed).

**Reel appearing in the main feed to followers**: reported by several blogs as a further crop
(commonly cited ~4:5), but current behavior is inconsistent across sources and changed
repeatedly through 2025–2026 — **not confirmed**, see §10.

## 2. Stories

**Meta-official ad safe zone** (`.../video/instagram-story` and `.../image/instagram-story`,
accessed 2026-09-08): canvas 1440×2560 (9:16), same figure as Reels — **top 14% (358px),
bottom 35% (896px), sides 6% (86px)**. Derived for 1080×1920: top 269px, bottom 672px, sides
65px.

**Historical/legacy figure**: many older and some current secondary sources (kb.orbee.com-style
aggregators, older Meta cached copies referenced by ignitesocialmedia.com) cite Stories'
older bottom margin as **20% (340px on 1080×1920)** rather than 35%. The live 2026 Meta pages
we fetched show 35% for Stories too, suggesting the 14/20/6 figure is superseded — but flag
this disagreement to the design team since older templates in the wild still use 20%.

**Interactive stickers** (poll, question, quiz, countdown, link): Meta does not publish exact
sticker-zone coordinates. Documented Meta guidance is qualitative — the link sticker help
content and secondary sources agree stickers should sit in the "middle-lower" band, clear of
the very bottom (the reply bar overlay makes bottom-edge stickers unclickable). No pixel box
confirmed — see §10.

## 3. Feed posts

**Meta-official feed image AD spec** (`.../image/instagram-feed`, accessed 2026-09-08):
resolution **1440×1800px, ratio 4:5**, min 400×500, max ratio 1.91:1, 1% tolerance, no
published safe-zone margin (only character limits: 125 primary text, 40 headline).

**Organic sizes** (secondary consensus across socialpilot.co, socialbee.com, buffer.com,
accessed 2026-09-08):
- Square 1:1 → 1080×1080
- Portrait 4:5 → 1080×1350 (most commonly recommended, "safest" size)
- Landscape 1.91:1 → 1080×566 (also cited as 1080×608 by one source — minor rounding
  disagreement between sources)
- New 3:4 upload option, no cropping → 1080×1440, added ~May 30 2025 per alternativeto.net
  (secondary tech-news source, not Meta itself, but describing a real shipped feature)

**2025 profile-grid change to 3:4**: Instagram's Head, Adam Mosseri, announced (per
socialmediatoday.com, Jan 19 2025 — a report of an official Instagram statement, not a Meta
help-center doc) that the profile grid changed from 1:1 to a vertical 3:4 preview because "most
photos and videos uploaded to Instagram... are vertical." No Meta doc gives exact pixel specs
for the grid tile; secondary sources vary between **1080×1440** and **1013×1350** for the
displayed tile — both are the *same* 3:4 ratio at different base resolutions, not a real
disagreement.

**Derived crop bands into a 3:4 grid tile** (arithmetic in JSON):
- From 1:1 (1080×1080) source → crop width to 810px (lose 135px each side), full height kept.
- From 4:5 (1080×1350) source → crop width to 1013px (lose ~33.5px each side), full height kept.
- From 3:4 (1080×1440) source → exact match, **no crop** (this is why Meta added the 3:4
  upload option in 2025).

## 4. Carousels

**Meta-official ad spec** (`.../carousel/instagram-feed`, accessed 2026-09-08):
- Cards: **2 to 10** minimum/maximum.
- Min resolution 1080×1080. Image-only carousels support **4:5**; carousels containing video
  support **1:1 only**. Tolerance 1%.
- Video length per card: 1 second to 2 minutes. Images JPG/PNG ≤30MB, video MP4/MOV/GIF ≤4GB.

**Mixed-ratio rule (organic)**: not found on any Meta doc; consistent secondary reporting
(sproutsocial.com, kapwing.com, contentdrips.com, accessed 2026-09-08) says **the first slide's
aspect ratio is applied to the whole carousel** — later slides with a different ratio are
auto-cropped to match, silently, with no upload error. Recommendation: make every slide the
same pixel dimensions before upload.

## 5. Profile avatar

No Meta help-center page with pixel specs was found. Secondary consensus (socialsizes.io,
expertphotography.com, accessed 2026-09-08): upload as **1:1**, recommend uploading
1000×1000px or larger; Instagram stores/serves at **320×320px**. Displayed circle size varies
by surface and is **not documented by Meta** — secondary sources disagree (110px vs 150px for
"profile view," ~32–40px in feed depending on client). Safe-circle inset (how far to keep
content from the square's edges before the circular crop) has **no confirmed Meta number** —
guidance is qualitative ("keep the subject centered, avoid corners"). See §10.

## 6. Highlight covers

No Meta doc found. Secondary consensus: upload at **1080×1920 (9:16)**, matching a Story
frame. Instagram crops a circle from the image; several sources describe keeping content
inside the **centered 1080×1080 square** of that canvas as safe (this is derivable: the
largest circle that fits a 1080-wide, 1920-tall rectangle has diameter 1080, centered
vertically between y=420 and y=1500 — geometry, not a Meta figure). Displayed circle diameter
on-profile is **disputed between sources** (110px vs 161px vs "~700px safe crop area" cited
by different aggregators) — no single number confirmed, report the disagreement.

## 7. Reels cover / thumbnail crop

Covered under §1 above (grid: crop to 1440px-tall center band of 1080×1920; Reels tab: full
9:16, uncropped). Instagram's own in-app "Edit cover" flow lets the creator manually reposition
inside the profile-grid preview by dragging/pinching before publishing — a workaround for the
absence of a hard published safe-zone number: creators can just look at the live preview.

## 8. Text overlay legibility

Meta's former **"20% text rule"** for Facebook/Instagram image ads (max 20% of the image
covered by text, delivery-gated) was **officially retired** by Meta (widely reported, e.g.
hubspot.com, instapage.com, attnagency.com, accessed 2026-09-08) — it is no longer a hard
delivery gate. Current Meta guidance (from the fetched ads-guide pages) is limited to
character-count limits on ad copy fields (125 chars primary text, 40 chars headline) rather
than an on-image text-density rule. No Meta Creators-page guidance on caption/subtitle
placement was found beyond the general Reels/Stories safe-zone percentages in §1–2.

## 9. Sources

- https://www.facebook.com/business/ads-guide/update/video/instagram-reels (Meta, accessed 2026-09-08)
- https://www.facebook.com/business/ads-guide/update/image/instagram-reels (Meta, accessed 2026-09-08)
- https://www.facebook.com/business/ads-guide/update/video/instagram-story (Meta, accessed 2026-09-08)
- https://www.facebook.com/business/ads-guide/update/image/instagram-story (Meta, accessed 2026-09-08)
- https://www.facebook.com/business/ads-guide/update/image/instagram-feed (Meta, accessed 2026-09-08)
- https://www.facebook.com/business/ads-guide/update/carousel/instagram-feed (Meta, accessed 2026-09-08)
- https://www.facebook.com/business/help/980593475366490/ (Meta — title/topic confirmed, body not retrievable via fetch, accessed 2026-09-08)
- https://www.socialmediatoday.com/news/instagram-rolls-out-vertically-aligned-profile-grid/737777/ (secondary, reporting Mosseri's statement, accessed 2026-09-08)
- https://alternativeto.net/news/2025/5/instagram-adds-3-4-aspect-ratio-photo-uploads-with-no-cropping (secondary, accessed 2026-09-08)
- https://www.firstpier.com/resources/instagram-ad-safe-zones (secondary, updated Aug 11 2026, accessed 2026-09-08)
- https://kreatli.com/guides/instagram-reels-safe-zone (secondary, accessed 2026-09-08)
- https://www.socialpilot.co/instagram-marketing/instagram-image-size-guide (secondary, accessed 2026-09-08)
- https://socialsizes.io/instagram-profile-picture-size/ (secondary, accessed 2026-09-08)
- https://www.sellerpic.ai/blog/instagram-safe-zone, sproutsocial.com/insights/instagram-carousel, kapwing.com grid/carousel guides (secondary, accessed 2026-09-08)

## 10. Numbers we could not confirm from Meta

- Exact pixel box for the Reels right-side action-button column (like/comment/share/save/more,
  audio disc). No Meta doc; no consistent secondary pixel box either.
- Exact coordinates/zone for Stories interactive stickers (poll, quiz, countdown, link) beyond
  qualitative "middle-lower, not bottom-edge" guidance.
- Whether Stories' bottom safe margin is still 20% or has moved to 35% — Meta's live ad-spec
  pages currently show 35% for Stories; older material and some current blogs still say 20%.
- Exact displayed avatar circle size in feed vs. profile (sources disagree: 32–40px feed,
  110–150px profile) and any published "safe circle inset" percentage for avatar uploads.
  No Meta number found.
- Exact displayed highlight-cover circle diameter (disputed 110px / 161px / ~700px across
  secondary sources) — no Meta figure.
- Current crop ratio applied to a Reel when it plays inline in a follower's main feed (vs. the
  Reels tab or profile grid) — secondary sources disagree and describe repeated changes through
  2025–2026.
- Any Meta-published numeric guidance on caption/subtitle placement or "amount of text"
  specific to Reels/Stories beyond the retired 20% ad-image rule.
