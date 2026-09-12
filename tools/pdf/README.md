# tools/pdf — Markdown → PDF pipeline

Dependency-free Markdown → A4 portrait PDF. Node ≥ 18 stdlib + headless
Chrome, no npm packages. Forked from `audit-2026-09-08/report/` (kept there
unmodified) and extended for two document shapes:

- **analytical report** — many chapters, figures, wide tables, links,
  a generated table of contents, a title page, a running footer;
- **card book** — one card per page, each with a storyboard image grid.

Both shapes go through the same renderer; the extra markdown syntax below
is simply unused in files that don't need it.

## Usage

```
node tools/pdf/md2pdf.mjs \
  --title "Report title" --subtitle "Subtitle" --date "12 September 2026" \
  --out /abs/path/report.pdf \
  file1.md file2.md ...
```

Each `.md` file is one chapter, starting on a new page. Intermediate HTML
goes to `tools/pdf/out/<name>.html`, the PDF wherever `--out` points
(directory created if needed).

Flags:
- `--title`, `--subtitle`, `--date` — cover page + footer text.
- `--out` — required, absolute or relative PDF path.
- `--no-toc` — skip the generated table of contents (on by default).

Normally called through `engine/pdf_build.py` (`build()` or
`python3 -m engine.pdf_build`), which wraps this CLI and reports back
page/byte counts — see that module's docstring.

## Markdown extensions

- **Images** — `![caption](reports/charts/x.png)` on its own line embeds the
  image as a base64 `data:` URI (path resolved relative to the `.md` file),
  scaled to page width, with the caption rendered below it. A missing file
  renders a visible `[MISSING IMAGE: ...]` placeholder instead of breaking
  the build.
- **Storyboard grid** — `::grid reports/x.png|cards/frames/a.png|cards/frames/b.png::`
  on its own line renders those images in a fixed 3-column grid, each cell
  captioned with its own filename (frame filenames double as the shot
  label). Extra images wrap onto more rows automatically.
- Standard markdown otherwise: `#`–`####` headings, `**bold**`, `*italic*`,
  `` `code` ``, fenced code blocks, ordered/unordered nested lists,
  blockquotes, `---` rules, pipe tables, and `[text](url)` links (rendered
  clickable, with the URL also printed after the link text since a printed
  page has no cursor to hover).

## Wide tables

A table with more than 8 columns gets a `table-wide-N` class
(`chooseTableClass()` in `md2pdf.mjs`) that shrinks cell font-size and
padding in three steps (9–12 / 13–16 / 17+ columns) so it still fits the
fixed A4 content width instead of overflowing. Long cell text wraps
(`word-break`/`overflow-wrap` in `report.css`) rather than forcing the
table wider than its container. `.table-wrap` around every table adds
`overflow-x: auto` as a screen-preview safety net — it does nothing for
the printed PDF, since Chrome's headless print flattens overflow rather
than paginating sideways.

## Table of contents

Built from every `#` and `##` heading across all chapter files, in
document order, as a single ordered list (H2s nested under their H1),
placed right after the cover page. Entries link to the heading's `#id`.
Repeated heading text across chapters is deduped (`dedupeSlug()`) so two
sections both titled "Overview" get distinct anchors and the TOC links to
the right one. Disable with `--no-toc`.

## Fonts

Cyrillic + Latin coverage via IBM Plex Sans/Mono (body/UI text) and Saira
SemiCondensed (display headings — Latin only, falls back to Plex Sans
Bold for Cyrillic, see `report.css` tokens comment). All four files are
under `fonts/`, embedded via `@font-face` `woff2` `url()`s relative to
`report.css`.

## Known limits (inherited from the source pipeline, still true here)

- **No true page numbers.** Chrome's headless `--print-to-pdf` has no CSS
  Paged-Media counters — `@page` margin boxes with `counter(page)` are
  silently ignored. The footer can only carry constant, document-wide text
  (title + date), not a real folio. This also means TOC entries have no
  page numbers, only `#id` anchors (inert once printed, live on screen).
- **One footer for the whole document.** `position: fixed` is the only
  thing Chrome repeats on every physical page, but it repeats *every* such
  element with no scoping to its containing section — one footer per
  chapter was tried upstream and rendered all of them stacked on every
  page. So there can be exactly one `.page-footer` in the DOM.
- **Footer can mask a line's tail.** Tuned against a real ~578-line report
  (25 collisions down to 1 across 19 pages), but a page whose last line
  ends with near-zero slack can still land under the footer's opaque
  plate — masked, not garbled. See the `@page` comment in `report.css` for
  the full sweep. Check pages near a chapter break.
- **`overflow-x: auto` on `.table-wrap` only helps on screen** — printed
  output relies entirely on the `table-wide-N` shrink classes, not on
  scrolling, since a PDF page can't scroll.
- **`mdls` page count needs Spotlight indexing**; `engine.pdf_build` and
  `md2pdf.mjs` both fall back to an exact byte-scan of `/Type /Page` when
  it's unavailable or returns nothing.
