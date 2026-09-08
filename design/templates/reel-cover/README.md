# reel-cover

1080x1920, placement `reel`. Cover frame for a reel, on Paper or on Ink. Everything sits
between y 272 and y 1218, inside Zone A and inside the 3:4 grid tile band (y 240 to 1660),
so the cover still reads as a frame in the profile grid.

| Slot | What it takes |
|---|---|
| `surface` | `light` (Paper, default) or `dark` (Ink). Control slot, no box. |
| `tag` | Format tag, Mono caps 36, for example `RADAR / 04`. |
| `hook` | Display 96/1.03/-0.01em. 6 to 8 words, up to 3 lines, 20 chars a line, `\n` for the breaks. |
| `proof_frame` | `on` draws the hairline evidence frame. Empty leaves the band deliberately empty. |
| `proof_src` | Image path, drawn inside the frame. Absent, the frame shows the Mono caption `[SCREENSHOT]`. |
| `proof` | Mono caps label under the frame, naming what the frame shows. |
| `episode` | Mono caps 32 metadata next to the mark. |
| `verdict` | `KEEP`, `KILL` or `TEST`. Optional chip, 160x56. |
| `mark` | `on` places the mark. Colour mark on Paper, mono Paper mark on Ink, chosen by `surface`. |

Rules held here: 4 columns of 204 with 24 gutters inside 96 padding; text on the 96
guide plus the 24 indent, objects on the guide itself; one 4 px rule under the hook and
no other ornament; mark 120 px with its quarter-height clear space, bottom edge at
y 1218; KEEP filled, KILL 4 px Oxide outline, TEST dashed at `stroke.dash`; nothing below
y 1248 and nothing right of x 950 below y 1000. The hook block is a fixed 3-line slot, so
the rule and everything under it hold their line whatever the hook says. Example numbers
are illustrative, not measured.
