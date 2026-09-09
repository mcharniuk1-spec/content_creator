# M2 Lab report pipeline

Markdown -> A4 portrait PDF, M2 Lab brand. No npm deps: hand-written parser,
rendering via headless Chrome.

## Usage
```
node md2pdf.mjs --title "Report title" --subtitle "Subtitle" \
  --date "8 September 2026" --out /abs/path/report.pdf file1.md file2.md
```
Each `.md` file is one chapter starting on a new page. HTML goes to
`out/<name>.html`, the PDF wherever `--out` points.

## Known limits
- No true page numbers: Chrome's headless print has no CSS Paged-Media
  counters, so the footer's right side shows chapter count, not page number.
- One footer for the whole document: `position:fixed` repeats on every
  page, not scoped to its section, so title/count stay constant throughout.
- Footer can mask a line's tail: tuned against a real 578-line report (25
  collisions down to 1 across 19 pages), but a page whose last line ends
  with near-zero margin space still lands under the footer's opaque plate
  — masked, not garbled. Check pages near a break for a hidden table row.
  See `report.css` `@page` comment for the full story.
- `mdls` page count needs Spotlight indexing; the byte-scan fallback used
  here is exact regardless.
