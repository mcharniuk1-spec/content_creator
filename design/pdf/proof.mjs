#!/usr/bin/env node
// Proof one or more section files as single A4 landscape pages.
// Usage: node pdf/proof.mjs pdf/sections/brand/10-positioning.html [...more]
// Output: pdf/out/proofs/<part>-<file>.png at 1123x794 (297x210 mm at 96 dpi) plus a .html next to it.
// Anything that overflows the page is clipped in the PNG exactly as it would be in the PDF.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, join, basename, dirname } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PDF_DIR = dirname(fileURLToPath(import.meta.url));
const OUT = join(PDF_DIR, 'out', 'proofs');
const HTML_DIR = join(PDF_DIR, 'out'); // same level as document.html so ../print.css and ../../brand resolve
mkdirSync(OUT, { recursive: true });

const shell = readFileSync(join(PDF_DIR, 'shell.html'), 'utf8');
const head = shell.match(/<head[\s\S]*?<\/head>/i)?.[0] ?? '';
const furniture = shell.match(/<script>[\s\S]*?<\/script>/i)?.[0] ?? '';

let failed = 0;
for (const arg of process.argv.slice(2)) {
  const file = resolve(arg);
  const part = basename(dirname(file));
  const name = `${part}-${basename(file, '.html')}`;
  const sections = readFileSync(file, 'utf8');
  const html = `<!DOCTYPE html>\n<html lang="en">\n${head}\n<body style="padding:0;margin:0">\n${sections}\n${furniture}\n</body>\n</html>\n`;
  const outHtml = join(HTML_DIR, `proof-${name}.html`);
  writeFileSync(outHtml, html);
  // count sections: one PNG per section (Chrome screenshots only the first viewport, so files with several sections are proofed one by one)
  const count = (sections.match(/<section\b/g) || []).length;
  if (count > 1) console.log(`${name}: ${count} sections in one file; only the first is proofed. Split the file.`);
  const outPng = join(OUT, `${name}.png`);
  const r = spawnSync(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
    '--window-size=1123,794', `--screenshot=${outPng}`, `file://${outHtml}`], { encoding: 'utf8' });
  if (r.status !== 0) { console.error(`proof failed for ${name}: ${r.stderr}`); failed++; continue; }
  console.log(`proof ${outPng}`);
}
process.exit(failed ? 1 : 0);
