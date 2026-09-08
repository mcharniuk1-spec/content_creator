#!/usr/bin/env node
// M2 Lab template renderer. No dependencies.
//
// A template is a folder with:
//   template.html      HTML with {{slot}} placeholders; loads ../../tokens/out/tokens.css
//   manifest.json      { "canvas": "reel" | "carousel" | ..., "width": 1080, "height": 1920,
//                        "placement": "reel", "slots": { name: { "importance": "primary"|"secondary", "box": {x,y,w,h} } } }
//   examples/*.json    { "slots": { name: value } } one file per example
//
// Usage:
//   node templates/render.mjs <template-dir> [example.json ...]   renders every example (default: all in examples/)
// Output: <template-dir>/out/<example>.html and <example>.png at exact canvas size.
// After rendering, the Instagram zone check runs for the placement using the slot boxes in manifest.json.

import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync } from 'node:fs';
import { resolve, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url))); // fileURLToPath: the folder path may contain spaces

const [dirArg, ...exampleArgs] = process.argv.slice(2);
if (!dirArg) { console.error('usage: node templates/render.mjs <template-dir> [example.json ...]'); process.exit(2); }
const dir = resolve(dirArg);
const manifest = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8'));
const template = readFileSync(join(dir, 'template.html'), 'utf8');
const examples = exampleArgs.length
  ? exampleArgs.map((p) => resolve(p))
  : readdirSync(join(dir, 'examples')).filter((f) => f.endsWith('.json')).map((f) => join(dir, 'examples', f));
mkdirSync(join(dir, 'out'), { recursive: true });

const escape = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
let failed = 0;

for (const ex of examples) {
  const name = basename(ex, '.json');
  const data = JSON.parse(readFileSync(ex, 'utf8'));
  const slots = data.slots || {};
  // {{slot}} -> escaped text with \n -> <br>; {{{slot}}} -> raw HTML; {{#slot}}...{{/slot}} -> block kept only when slot is non-empty
  let html = template.replace(/\{\{#(\w[\w-]*)\}\}([\s\S]*?)\{\{\/\1\}\}/g, (_, k, body) => (slots[k] ? body : ''));
  html = html.replace(/\{\{\{(\w[\w-]*)\}\}\}/g, (_, k) => (slots[k] ?? ''));
  html = html.replace(/\{\{(\w[\w-]*)\}\}/g, (_, k) => escape(slots[k] ?? '').replace(/\n/g, '<br>'));
  const outHtml = join(dir, 'out', `${name}.html`);
  const outPng = join(dir, 'out', `${name}.png`);
  writeFileSync(outHtml, html);
  const r = spawnSync(CHROME, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
    ...(manifest.transparent ? ['--default-background-color=00000000'] : []),
    `--window-size=${manifest.width},${manifest.height}`, `--screenshot=${outPng}`, `file://${outHtml}`,
  ], { encoding: 'utf8' });
  if (r.status !== 0 || !existsSync(outPng)) { console.error(`render failed: ${name}\n${r.stderr}`); failed++; continue; }
  console.log(`rendered ${name} -> ${outPng}`);

  // zone check with the boxes declared in the manifest (only slots present in this example)
  if (manifest.placement && manifest.slots) {
    const boxes = Object.entries(manifest.slots)
      .filter(([k]) => slots[k] !== undefined && slots[k] !== '')
      .map(([k, v]) => ({ name: k, importance: v.importance || 'primary', ...v.box }));
    const boxesPath = join(dir, 'out', `${name}.boxes.json`);
    writeFileSync(boxesPath, JSON.stringify(boxes, null, 2));
    const check = spawnSync('node', [join(ROOT, 'social/overlays/check-overlay.mjs'), outPng, manifest.placement, boxesPath], { encoding: 'utf8' });
    process.stdout.write(check.stdout);
    if (check.status !== 0) { console.error(`zone check failed: ${name}`); failed++; }
  }
}
process.exit(failed ? 1 : 0);
