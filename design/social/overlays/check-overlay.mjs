#!/usr/bin/env node
/**
 * check-overlay.mjs — QA gate for Instagram safe-zone placement.
 *
 * It does NOT read pixels. It checks element bounding boxes you supply against
 * this design system's zone model (../zones.json):
 *   - "primary" elements (hook, mark, verdict card, format label) must be fully
 *     inside Zone A.
 *   - "secondary" elements (burned-in subtitles, persistent claim bar) may be
 *     inside Zone A union Zone B, but not touch Zone C.
 *   - any element intersecting a Zone C rect or the outer ring of a circular
 *     Zone C fails, regardless of importance.
 *
 * CLI:
 *   node check-overlay.mjs <render.png> <placement-id> <elements.json>
 *
 *   <render.png>      path to the rendered PNG. Only used for the report header
 *                      (this script does not open or analyze the image).
 *   <placement-id>     one of: reel, story, feed-portrait, feed-square,
 *                      feed-tall, carousel, avatar, highlight-cover
 *   <elements.json>    path to a JSON array:
 *                      [{ "name": "hook", "x":100,"y":300,"w":800,"h":120,
 *                         "importance": "primary" }, ...]
 *                      x,y,w,h are in the same pixel space as the placement's
 *                      canvas in zones.json (e.g. 1080x1920 for reel).
 *
 * Exit code: 0 if every element passes, 1 if any element fails.
 *
 * Example:
 *   node check-overlay.mjs render.png reel elements.json
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ZONES_PATH = path.join(__dirname, '..', 'zones.json');

function usageAndExit(msg) {
  if (msg) console.error('Error: ' + msg + '\n');
  console.error('Usage: node check-overlay.mjs <render.png> <placement-id> <elements.json>');
  process.exit(2);
}

const [, , renderPath, placementId, elementsPath] = process.argv;
if (!renderPath || !placementId || !elementsPath) usageAndExit('missing arguments');

let zonesDb, elements;
try {
  zonesDb = JSON.parse(readFileSync(ZONES_PATH, 'utf8'));
} catch (e) {
  usageAndExit(`could not read/parse zones.json at ${ZONES_PATH}: ${e.message}`);
}
try {
  elements = JSON.parse(readFileSync(elementsPath, 'utf8'));
} catch (e) {
  usageAndExit(`could not read/parse elements file ${elementsPath}: ${e.message}`);
}
if (!Array.isArray(elements)) usageAndExit('elements.json must be a JSON array');

let placement = zonesDb.placements.find((p) => p.id === placementId);
if (placement && placement.zones === 'same as feed-portrait') {
  const base = zonesDb.placements.find((p) => p.id === 'feed-portrait');
  placement = { ...placement, zones: base.zones, canvas: base.canvas, crop: base.crop };
}
if (!placement) {
  usageAndExit(
    `unknown placement "${placementId}". Valid ids: ${zonesDb.placements.map((p) => p.id).join(', ')}`
  );
}

// ---- geometry helpers ----
function rectsIntersect(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}
function rectFullyInsideRect(inner, outer) {
  return (
    inner.x >= outer.x &&
    inner.y >= outer.y &&
    inner.x + inner.w <= outer.x + outer.w &&
    inner.y + inner.h <= outer.y + outer.h
  );
}
// distance from box corner farthest from circle center, to know if any part of
// the box lies outside radius r (used to test "fully inside circle")
function rectFullyInsideCircle(box, circle) {
  const corners = [
    [box.x, box.y],
    [box.x + box.w, box.y],
    [box.x, box.y + box.h],
    [box.x + box.w, box.y + box.h],
  ];
  return corners.every(([x, y]) => {
    const dx = x - circle.cx;
    const dy = y - circle.cy;
    return Math.sqrt(dx * dx + dy * dy) <= circle.r;
  });
}
function rectIntersectsCircleRing(box, circle) {
  // conservative: true if the box is not fully inside the inner radius
  // (i.e. any part of the box could be in the ring or beyond)
  const corners = [
    [box.x, box.y],
    [box.x + box.w, box.y],
    [box.x, box.y + box.h],
    [box.x + box.w, box.y + box.h],
  ];
  return corners.some(([x, y]) => {
    const dx = x - circle.cx;
    const dy = y - circle.cy;
    return Math.sqrt(dx * dx + dy * dy) > circle.r;
  });
}

function isFullyInsideZoneA(box, zones) {
  if (zones.A.rects) {
    return zones.A.rects.some((r) => rectFullyInsideRect(box, r));
  }
  if (zones.A.circles) {
    return zones.A.circles.some((c) => rectFullyInsideCircle(box, c));
  }
  return false;
}
function isFullyInsideZoneAorB(box, zones) {
  if (isFullyInsideZoneA(box, zones)) return true;
  const bRects = (zones.B && zones.B.rects) || [];
  // A U B: approximate by checking the box is fully inside the union bounding
  // logic is: fully inside A, or fully inside B, or split across A+B with no
  // part in C. We do the practical check: not touching any C rect/circle, and
  // fully inside the bounding box of (A rects + B rects).
  if (bRects.some((r) => rectFullyInsideRect(box, r))) return true;
  return false;
}
function touchesZoneC(box, zones) {
  const cRects = (zones.C && zones.C.rects) || [];
  if (cRects.some((r) => rectsIntersect(box, r))) return true;
  if (zones.C && zones.C.circles_complement_of) {
    const { cx, cy, r_inner } = zones.C.circles_complement_of;
    if (rectIntersectsCircleRing(box, { cx, cy, r: r_inner })) return true;
  }
  return false;
}

// ---- run checks ----
const rows = [];
let hasFailure = false;

for (const el of elements) {
  const { name = '(unnamed)', x, y, w, h, importance = 'secondary' } = el;
  if ([x, y, w, h].some((v) => typeof v !== 'number')) {
    rows.push({ name, importance, result: 'FAIL', reason: 'invalid box (x,y,w,h must be numbers)' });
    hasFailure = true;
    continue;
  }
  const box = { x, y, w, h };
  const inA = isFullyInsideZoneA(box, placement.zones);
  const inAorB = isFullyInsideZoneAorB(box, placement.zones);
  const inC = touchesZoneC(box, placement.zones);

  let result = 'PASS';
  let reason = '';

  if (inC) {
    result = 'FAIL';
    reason = 'intersects Zone C (never)';
  } else if (importance === 'primary') {
    if (!inA) {
      result = 'FAIL';
      reason = 'primary element not fully inside Zone A';
    }
  } else {
    if (!inAorB) {
      result = 'FAIL';
      reason = 'secondary element not fully inside Zone A or Zone B';
    }
  }

  if (result === 'FAIL') hasFailure = true;
  rows.push({ name, importance, result, reason });
}

// ---- report ----
console.log(`Render:    ${renderPath}`);
console.log(`Placement: ${placementId} (canvas ${placement.canvas?.w ?? '?'}x${placement.canvas?.h ?? '?'})`);
console.log('');
const nameW = Math.max(4, ...rows.map((r) => r.name.length));
const impW = Math.max(10, ...rows.map((r) => r.importance.length));
console.log(`${'NAME'.padEnd(nameW)}  ${'IMPORTANCE'.padEnd(impW)}  RESULT  REASON`);
for (const r of rows) {
  console.log(
    `${r.name.padEnd(nameW)}  ${r.importance.padEnd(impW)}  ${r.result.padEnd(6)}  ${r.reason}`
  );
}
console.log('');
console.log(hasFailure ? 'RESULT: FAIL' : 'RESULT: PASS');

process.exit(hasFailure ? 1 : 0);
