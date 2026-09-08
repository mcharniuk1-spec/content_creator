# lower-third

1080x1920 transparent overlay, placement `reel`. Shown once per person, the first time
that person speaks, for about 3 seconds.

| Slot | What it takes |
|---|---|
| `name` | Plex Sans SemiBold 46 on 1.35, Paper on an Ink plate. Also the slot that draws the plate. |
| `role` | Mono caps 32, one line, for example `BUILDS THE CASE`. About 15 characters. |
| `accent` | `on` or `off`. On draws a 2 px Signal rule on the plate's left edge. Use it on dark video only; leave it off on Paper footage. Control slot, no box. |

Geometry: plate on the 96 guide, 660 wide (columns 1 to 3), 24 px padding
on all four sides, square corners. Its bottom edge lands exactly on the Zone A floor,
y 1248, so name and role are always inside the always-safe band and share the caption
plate's left indent, x 120.

Name over role, two lines, left aligned. The plate holds a name of about 20 characters
and a role of about 24 before it needs a wider box. Rendered PNG carries no alpha
because the renderer screenshots on an opaque canvas; the HTML itself is transparent.
