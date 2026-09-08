# M2 Lab imagery rules

Photo, video and generated backgrounds. Every frame serves the visual formula
`Human face + real proof + one labeled verdict`. Canvas reference: 1080x1920, Zone A
(always safe) is y 269 to 1248, Zone B (organic-only) extends to y 1470, side margin 65 px.

## 1. What the camera shows

Three shot types, no fourth.

1. **Person to camera.** One person, static frame, speaking to the lens.
2. **Screen as proof.** The workflow, run or artifact, filmed off a monitor with a phone
   or captured natively.
3. **Split: proof over person.** Screen in the upper half, person in the lower half, one
   horizontal grid line between them.

- Hold the shot and let the frame stay still; the niche median is 0.12 cuts per second and
  44 of 100 top reels run with almost no cuts, so a static shot is the default choice
  [niche evidence 1 Sep 2026].
- Use the split shot for any beat where a number is spoken while it is visible, because
  proof-over-person is one of the two most transferable devices measured in the niche
  [niche evidence 1 Sep 2026].
- Frame the person so the eyes sit at about y 560 on 1080x1920, which is the upper third
  of Zone A and clear of the covered top band [Zone model, 8 Sep 2026].
- Leave headroom of about 80 px above the crown so the head never touches the Zone A
  ceiling at y 269 [Zone model, 8 Sep 2026].
- Keep the speaker's eye line into the lens for hook and verdict beats, and off-lens only
  when a screen is being pointed at [oscilloscope].
- Place the person on a grid column with a visible indent from the left guide, never
  centred in the frame [Swiss grid].
- Compose faces and screens inside the middle band y 269 to 1248 so that Instagram UI
  never lands on a mouth, a cursor or a number [Zone model, 8 Sep 2026].
- Place the mark in the bottom left of Zone A at 120 px, on the same indent as the type
  column, on a flat area of the image, and leave it there for the whole piece [Swiss grid].

## 2. Light and colour on set

- Light from one direction only, so shadows fall consistently across every shot of a piece
  [engineering drawing].
- Set white balance neutral on camera and record the value, so two shooting days match.
- Keep gels off the lights and let the background carry the colour, so Oxide and Signal
  roles keep their single meanings in the frame [engineering drawing].
- Shoot against a flat wall or a real workspace, and keep whatever is behind the person
  free of text, logos and screens that are not the proof [engineering drawing].
- Grade at the timeline, using the Ink and Paper roles as the black and white points, and
  keep the camera profile flat [fixed fact: grade at timeline].
- Apply grain at the timeline at about 30 per cent opacity across the whole piece, never
  baked into a source asset [fixed fact: grain at timeline].
- Reserve the accent for lit data on a dark field, and Oxide for what is broken or KILL,
  in the graded output as in the graphics [oscilloscope, engineering drawing].

## 3. Screens as proof

- Capture at the display's native resolution and scale down only, so UI text stays sharp
  at 1080 wide [engineering drawing].
- Keep the cursor visible in every screen capture, because the cursor is what proves a
  person is driving the run [Builder in public].
- Cover real data with a flat Ink plate at the exact bounds of the field, so the redaction
  reads as a deliberate mark rather than a soft artifact [engineering drawing].
- Film the monitor with a phone when the run is live and the moment matters; the technique
  is recognised in the niche and reads as raw rather than staged
  [niche evidence 1 Sep 2026, Mosseri Dec 2025].
- Snap the screen rectangle to the four-column grid, aligned left on the indent, with its
  top edge on a grid line [Swiss grid].
- Point at a UI element with a thin leader line ending in a dot exactly on the element,
  and set the label outside the screen rectangle [engineering drawing].
- Keep one callout on screen at a time, and let the frame change only when the evidence
  changes [oscilloscope].
- Show every on-screen number with its WAS, NOW or SAVED label, including numbers that are
  part of the captured UI [oscilloscope].

## 4. B-roll and generated backgrounds

- Use generated output for backgrounds and B-roll only; build anything carrying letters or
  the mark from a template, so it is reproducible, editable and positioned exactly
  [fixed fact: templates own letters].
- Keep a generated background flat and textural: paper grain, concrete, brushed metal,
  plotted line work, sensor noise [engineering drawing].
- Keep generated frames free of letters, people, logos and UI, so nothing in them can be
  read as a claim we did not make [Evidence-first].
- Grade a generated background to the Ink and Paper roles and grain it at the timeline at
  about 30 per cent, exactly like camera footage [fixed fact: grade at timeline].
- Record `origin: shot / stock / generated (tool, date)` in the asset's metadata at the
  moment the asset enters the library, and treat that field as the only source of truth
  about the asset's origin [fixed fact: provenance at input].
- Keep the EU AI Act transparency work parked until the account earns revenue, and revisit
  the decision at the first paid engagement (decision 5 Sep 2026).

## 5. Stock

- Use a stock frame only when its `origin` field is filled at import and its licence is
  recorded beside it [fixed fact: provenance at input].
- Hold stock to the same shot, light and grade rules as our own footage, so it is
  indistinguishable in the graded timeline [engineering drawing].
- Choose stock that shows a surface, a tool or a workspace, and let people appear only in
  our own footage [Evidence-first].
- Keep smiling-people-at-a-laptop, handshake and glowing-brain stock out of the library,
  because it is the visual form of a claim with no proof behind it [Evidence-first].

## 6. Photography of the two founders

- Shoot both founders on the same lens, 35 mm equivalent, so face geometry stays constant
  between Michael's business angle and Max's technical angle [engineering drawing].
- Keep the same camera-to-subject distance for both, measured and written into the shoot
  card, so the two read as one system [engineering drawing].
- Keep both at the same frame proportions: same crop, same headroom, same eye line height
  [Isotype].
- Retouch exposure only, and leave skin texture, hair and room as recorded, because raw
  reads as real [Mosseri Dec 2025].
- Shoot a fresh portrait set whenever the light setup changes, rather than mixing setups
  inside one piece [engineering drawing].

## 7. Reject if

- The face or the screen crosses out of the band y 269 to 1248.
- The frame is centred instead of set on the left indent.
- A number appears without WAS, NOW or SAVED.
- Real data is hidden by a soft or gaussian blur instead of a flat Ink plate.
- The cursor is missing from a screen that is presented as a run.
- A generated frame contains letters, a person, a logo or UI.
- The `origin` field is empty, or was filled by guessing from the image.
- Grain or grade is baked into the source asset.
- A radius, a shadow or a gradient appears anywhere in the frame.
- Oxide is used for anything other than what is broken or KILL.
