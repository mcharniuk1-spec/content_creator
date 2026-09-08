#!/usr/bin/env node
// M2 Lab -- WCAG 2.x contrast check over the built tokens.
// Input: tokens/out/tokens.flat.json (run tokens/build/build-tokens.mjs first).
// Output: checks/out/contrast.json, plus a printed table.
// No dependencies on purpose, matching the token build.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const FLAT_PATH = join(ROOT, 'tokens', 'out', 'tokens.flat.json');
const OUT = join(HERE, 'out');

let flat;
try {
  flat = JSON.parse(readFileSync(FLAT_PATH, 'utf8'));
} catch (err) {
  console.error(`Could not read ${FLAT_PATH} -- run the token build first.\n  ${err.message}`);
  process.exit(1);
}

// -- WCAG 2.x relative luminance / contrast ratio ----------------------------
function hexToRgb(hex) {
  const h = String(hex).replace('#', '');
  return [0, 2, 4].map((i) => parseInt(h.substr(i, 2), 16));
}
function srgbToLinear(c) {
  const v = c / 255;
  return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}
function relativeLuminance(hex) {
  const [r, g, b] = hexToRgb(hex).map(srgbToLinear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrastRatio(hexA, hexB) {
  const la = relativeLuminance(hexA);
  const lb = relativeLuminance(hexB);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

// -- Pairs to check -----------------------------------------------------------
// threshold: 4.5 = WCAG AA normal text, 3 = WCAG AA large text / UI components,
// null = report only, no pass/fail gate.
const PAIRS = [
  { fg: 'text.on-light', bg: 'surface.primary', threshold: 4.5 },
  { fg: 'text.on-dark', bg: 'surface.dark', threshold: 4.5 },
  { fg: 'text.secondary', bg: 'surface.primary', threshold: 4.5 },
  { fg: 'text.secondary-on-dark', bg: 'surface.dark', threshold: 4.5 },
  { fg: 'accent.data', bg: 'surface.dark', threshold: 3 },
  { fg: 'accent.alert', bg: 'surface.primary', threshold: 3 },
  { fg: 'accent.alert', bg: 'surface.dark', threshold: 3 },
  { fg: 'accent.structure', bg: 'surface.primary', threshold: 3 },
  { fg: 'line.on-dark', bg: 'surface.dark', threshold: 3 },
  { fg: 'line.on-dark-muted', bg: 'surface.dark', threshold: null },
  { fg: 'line.on-light', bg: 'surface.primary', threshold: null },
  {
    fg: 'color.base.ink',
    bg: 'color.base.signal',
    threshold: 4.5,
    note: 'chip label on KEEP fill on dark',
  },
];

// Colour keys in the DTCG file are prefixed "color." except color.base.*,
// which is already fully qualified -- normalise the lookup either way.
function lookup(key) {
  if (key in flat) return flat[key];
  const withPrefix = `color.${key}`;
  if (withPrefix in flat) return flat[withPrefix];
  return undefined;
}

const results = [];
let missing = false;
for (const pair of PAIRS) {
  const fgHex = lookup(pair.fg);
  const bgHex = lookup(pair.bg);
  if (!fgHex || !bgHex) {
    console.error(`Missing token for pair ${pair.fg} on ${pair.bg} (fg=${fgHex}, bg=${bgHex})`);
    missing = true;
    continue;
  }
  const ratio = contrastRatio(fgHex, bgHex);
  const pass = pair.threshold === null ? null : ratio >= pair.threshold;
  results.push({
    fg: pair.fg,
    fgHex,
    bg: pair.bg,
    bgHex,
    ratio: Math.round(ratio * 100) / 100,
    threshold: pair.threshold,
    result: pair.threshold === null ? 'report only' : pass ? 'PASS' : 'FAIL',
    note: pair.note || null,
  });
}
if (missing) process.exit(1);

// -- Print table ---------------------------------------------------------------
const col = (s, w) => String(s).padEnd(w);
console.log(
  col('FG', 20) + col('BG', 18) + col('FG hex', 10) + col('BG hex', 10) + col('Ratio', 8) + col('Threshold', 10) + 'Result'
);
for (const r of results) {
  console.log(
    col(r.fg, 20) +
      col(r.bg, 18) +
      col(r.fgHex, 10) +
      col(r.bgHex, 10) +
      col(r.ratio + ':1', 8) +
      col(r.threshold === null ? '--' : r.threshold + ':1', 10) +
      r.result
  );
}
console.log('\nNote: accent.data on surface.primary is intentionally not a pair -- Signal is never used on Paper.');

mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, 'contrast.json'), JSON.stringify(results, null, 2) + '\n');

const failed = results.filter((r) => r.result === 'FAIL');
if (failed.length) {
  console.error(`\n${failed.length} pair(s) failed their threshold.`);
  process.exit(1);
}
console.log(`\nAll thresholded pairs pass. Wrote ${join(OUT, 'contrast.json')}`);
