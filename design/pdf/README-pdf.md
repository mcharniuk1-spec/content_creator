# PDF pipeline

A4 landscape brand book, built from HTML with headless Chrome. Everything lives in `pdf/`.

## Adding a section

One printed page is one `<section class="page">`, one section per file. Part 1 goes in
`pdf/sections/brand/`, part 2 in `pdf/sections/system/`. Files are concatenated in filename
order, so name them `10-positioning.html`, `20-audience.html`, leaving gaps of ten for
inserts. A file holds section markup only, no `<html>`, `<head>` or `<style>`.

Classes in `print.css`: `.grid` with `.col-1` to `.col-12`, `.label`, `.figure` plus
`.caption`, `table`, `.swatch-row` with `.swatch`, `.pair` with `.marker--do` and
`.marker--dont`, `.rule-line`, `.avoid-break`. Dark page: `page--dark`. No footer:
`no-folio`. Nothing reflows, so content longer than a page is split into two files. The two
`00-sample.html` proof sheets can be deleted once real content lands.

## Building

    node pdf/build.mjs              assemble, print the PDF, render the proof PNGs
    node pdf/build.mjs --html-only  assemble pdf/out/document.html only

Into `pdf/out/`: `document.html`, `M2-Lab-Brandbook.pdf`, `proof-cover.png`,
`proof-section.png`, `proof-pdf-page-1.png`.

## Known limits

- Asset paths resolve from `pdf/out/`. Preview `pdf/out/document.html`, never `shell.html`.
- Page numbers and the footer come from a script in `shell.html`, run before printing;
  Chrome cannot number pages from CSS. Contents folios update only for rows carrying
  `data-page-of="#page-id"`.
- Needs Google Chrome in `/Applications`. Page count comes from `mdls`. `pdftoppm` is absent
  here, so the PDF raster proof uses `sips`, page 1 only.
- A swatch leader ends in a square point, not a round dot: nothing in the system is rounded.
