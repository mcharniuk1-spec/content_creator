# claim-bar

1080x1920 transparent overlay, placement `reel`. The bar that stays on screen from
beat 2 until the verdict, so a returning viewer always knows where to look.

| Slot | What it takes |
|---|---|
| `claim` | One statement, Plex Sans SemiBold 46 on 1.35, Paper on an Ink plate. One line, never wrapped, so keep it to about 22 characters. |
| `tag` | Optional Mono caps 32 label at the plate's left, in the first column of the plate. About 8 characters. |

Geometry: plate on the 96 guide at y 1264, 840 wide, 24 px padding on all four sides,
square corners, no shadow. That is 16 px below the Zone A floor (y 1248), inside Zone B,
and its right edge stops at x 936, clear of the 130 px right rail. Tag column is one
grid column (204) plus a 24 gutter, so the claim text starts on the second column guide.

Fix the bar's position for the whole piece and swap only its text, at a beat boundary,
with no transition. Rendered PNG carries no alpha channel because the renderer
screenshots on an opaque canvas; the HTML itself is transparent and composites
correctly in the editor. Example numbers are illustrative, not measured.
