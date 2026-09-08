# M2 Lab motion rules

Captions, overlays and transitions for reels. Canvas reference: 1080x1920, Zone A
(always safe) is y 269 to 1248, Zone B (organic-only) extends to y 1470, side margin 65 px.

## 1. Principle

- Move an element only to point at the evidence being discussed, so every movement has a
  referent in the frame [oscilloscope].
- Change the frame when the evidence changes, and hold it the rest of the time; the niche
  median is 0.12 cuts per second [niche evidence 1 Sep 2026].
- Let the shape and position of an element carry its state, and let motion carry only the
  moment it becomes relevant [checklist].
- Give each element one entrance and one exit per piece [engineering drawing].

## 2. Timing tokens (proposal for tokens.json)

| token | value | used by |
|---|---:|---|
| `motion.duration.instant` | 0 ms | captions, claim bar text swap, hard cuts |
| `motion.duration.quick` | 120 ms | grid wipe, verdict card entrance |
| `motion.duration.standard` | 200 ms | lower third slide |
| `motion.duration.hold` | 400 ms | minimum time any element stays before it may change |
| `motion.easing.default` | `linear` | every animated property |

- Use `linear` as the single easing, because a measurement instrument moves at a constant
  rate and an ease-out curve is what makes motion read as decoration [oscilloscope].
- Keep the set to four durations, because a numeric ceiling is what keeps two editors
  consistent [fixed fact: reproducibility].
- Show a caption in full at 0 ms, never typewriter, never word-by-word bounce, so the line
  can be read as one statement [Swiss grid].
- Keep every entrance out of the fade-and-slide-up pattern, which is the named generic
  default [not-this.md item 14].

## 3. Caption preset

- Set captions at 40 px Plex Sans SemiBold, which clears the 14 CSS px legibility floor on
  a 390 px phone [type-metrics 6c].
- Keep captions to 2 lines maximum, and split the sentence at a clause boundary rather than
  shrinking the type [type-metrics 6c].
- Place the caption block low in the safe band, bottom edge at y 1248 for cross-posted
  reels, or down to y 1470 for organic-only reels [Zone model, 8 Sep 2026].
- Align the caption plate on the left indent of the grid, never centred [Swiss grid].
- Set Paper text on an Ink plate with 24 px padding on all four sides, square corners, no
  shadow [fixed fact: no radius, no shadows].
- Emphasise a keyword by moving it from SemiBold to Bold, and keep every caption one colour
  [Swiss grid].
- Bring a caption in at 0 ms on the cut and take it out at 0 ms on the next cut, so caption
  changes and picture changes are the same event [oscilloscope].

## 4. Claim bar

- Put the claim bar on screen at beat 2 (context, from about 3 s) and keep it there until
  the verdict appears at about 38 s [formats 06, niche evidence 1 Sep 2026].
- Fix its position for the whole piece and for the whole format, so a returning viewer
  knows where to look [engineering drawing].
- Change its text only at a beat boundary, at 0 ms, with no transition on the swap
  [oscilloscope].
- Write one statement per line, one line per beat, and never wrap an item across two lines
  [checklist].

## 5. Verdict card entrance

- Bring the verdict card in on a hard cut, or on a 120 ms wipe travelling from the left
  along a grid line [Swiss grid].
- Draw KEEP as a filled plate, KILL as an outlined plate, TEST as a dashed plate, so the
  state reads from the shape before any colour is seen [checklist].
- Use Oxide only on KILL, and let KEEP and TEST carry no colour of their own
  [engineering drawing].
- Hold the card at least 3 seconds and keep it inside Zone A, so it is readable with the
  sound off [formats 06, Zone model].
- Keep the card static once it has landed; the reason line does not animate [checklist].

## 6. Lower third

- Show a lower third once per person, the first time that person speaks, and not again
  [engineering drawing].
- Slide it in over 200 ms along the baseline, starting from the left indent and travelling
  right, with no fade [Swiss grid].
- Hold it 3 seconds, then remove it at 0 ms on the next cut [checklist].
- Set name and role on two lines, left aligned on the same indent as the caption plate
  [Swiss grid].

## 7. Data animation

- Bring an Isotype count in unit by unit at a fixed 80 ms per glyph, so the interval itself
  reads as counting [Isotype].
- Keep every unit glyph the same size at every moment of the animation, and never scale one
  to mean more [Isotype].
- Draw a unit that is no longer there as an empty outline, appearing in the same sequence
  as the filled ones [Isotype].
- Move the oscilloscope cursor to the value being spoken, arriving as the number is said,
  at 120 ms and linear [oscilloscope].
- Keep the axis labels on screen for the whole of a data shot [oscilloscope].
- Show the number as WAS, NOW or SAVED from the first frame it appears [oscilloscope].

## 8. Transitions between shots

- Cut hard between shots by default [niche evidence 1 Sep 2026].
- Use the 120 ms wipe along a grid line as the single permitted alternative, and only when
  the new shot introduces new evidence [Swiss grid].
- Keep dissolves, zooms, whip pans, push-ins and speed ramps out of the timeline, so the
  picture only changes when the evidence does [oscilloscope].

## 9. What never moves

- Keep the mark fixed in the bottom left of Zone A for the whole piece [Swiss grid].
- Keep the format tag (`RADAR / 04` and its siblings) fixed on its grid position
  [Swiss grid].
- Keep the four-column grid and its indent identical in every shot [Swiss grid].

## 10. Remotion notes for the builder

- Load every font with `waitUntilDone()` and await it before calling `fitText()`, otherwise
  the measurement runs against a fallback face and the layout ships wrong.
- Use `fillTextBox` and read its `exceedsBox` flag as the fit check for the 2-line caption
  and the hook, rather than trusting a character count.
- Plan local renders as sequential jobs; concurrent renders share one browser pool.
- Verify output by rendering a frame with `npx remotion still` and looking at the image,
  never by reading the render log [Evidence-first].
