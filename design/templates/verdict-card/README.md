# verdict-card

1080x1920 transparent overlay, placement `reel`. The labeled conclusion of a piece,
readable with the sound off.

| Slot | What it takes |
|---|---|
| `verdict` | `KEEP`, `KILL` or `TEST`. Draws the card and the shape around the word. Empty means no card. |
| `why` | The reason, Plex Sans Regular 46 on 1.35, up to 3 lines, `\n` for the breaks, about 31 characters a line. |
| `surface` | `light` (Paper plate with a hairline border, default) or `dark` (Ink plate). Control slot, no box. |

Layout: header `M2 VERDICT` in Mono caps, the verdict word in Display 96 inside its
shape (432x131, word on the 24 indent), then `WHY:` and the reason. Card is the 888
text column on the 96 guide, 48 px padding, square corners.

State reads from the shape before any colour: KEEP filled (Ink on light, Signal on
dark), KILL a 4 px Oxide outline, TEST a 2 px dashed outline at `stroke.dash` 12/8.
Oxide appears on KILL only.

Vertical position: centred in Zone A, then raised so the card bottom lands on y 1000,
the line where the right action rail starts. Rendered PNG carries no alpha because the
renderer screenshots on an opaque canvas; the HTML itself is transparent. Example
numbers are illustrative, not measured.
