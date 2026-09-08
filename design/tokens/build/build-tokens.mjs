#!/usr/bin/env node
// M2 Lab -- token build.
// Input: tokens/tokens.json (DTCG-style groups; a token's $type is either
//        declared on it or inherited from the nearest ancestor group).
// Output: tokens/out/tokens.css, tokens/out/tokens.flat.json,
//         tokens/out/tokens.types.json, tokens/out/palette.md.
// No dependencies on purpose: the token set is small, and a node_modules tree
// is one more thing that can drift or block a teammate without npm access.
//
// Usage: node tokens/build/build-tokens.mjs [path-to-tokens.json]
//        Defaults to tokens/tokens.json next to this script.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..'); // tokens/
const SRC = process.argv[2] ? resolve(process.cwd(), process.argv[2]) : join(ROOT, 'tokens.json');
const OUT = join(ROOT, 'out');

let raw;
try {
  raw = JSON.parse(readFileSync(SRC, 'utf8'));
} catch (err) {
  console.error(`Could not read/parse ${SRC}:\n  ${err.message}`);
  process.exit(1);
}

// -- 1. Flatten the tree to dotted keys, tracking each token's own $type ----
// A group's $type applies to every token beneath it unless a token (or a
// nested group) overrides $type locally.
const flatRaw = {};
const types = {};
const descriptions = {};

(function walk(node, path, inheritedType) {
  for (const [key, value] of Object.entries(node)) {
    if (key.startsWith('$')) continue;
    if (value && typeof value === 'object') {
      const localType = value.$type || inheritedType;
      if ('$value' in value) {
        const fullKey = [...path, key].join('.');
        flatRaw[fullKey] = value.$value;
        types[fullKey] = localType;
        if (value.$description) descriptions[fullKey] = value.$description;
      } else {
        walk(value, [...path, key], localType);
      }
    }
  }
})(raw, [], undefined);

// -- 2. Resolve aliases "{a.b.c}" recursively --------------------------------
// Errors are collected rather than thrown so the build reports every problem
// in one pass instead of stopping at the first one.
const REF = /^\{([^}]+)\}$/;
const resolveErrors = [];

function resolveValue(originKey, value, seen) {
  if (typeof value !== 'string') return value;
  const m = value.match(REF);
  if (!m) return value;
  const refKey = m[1];
  if (seen.has(refKey)) {
    resolveErrors.push(`Circular reference: ${[...seen, refKey].join(' -> ')}`);
    return undefined;
  }
  if (!(refKey in flatRaw)) {
    resolveErrors.push(`Dangling reference: "{${refKey}}" (from ${originKey}) does not resolve to any token`);
    return undefined;
  }
  return resolveValue(originKey, flatRaw[refKey], new Set([...seen, refKey]));
}

const flat = {};
for (const [key, value] of Object.entries(flatRaw)) {
  flat[key] = resolveValue(key, value, new Set([key]));
}

// -- 3. Validate -------------------------------------------------------------
const errors = [...new Set(resolveErrors)];

const HEX = /^#[0-9A-F]{6}$/;
for (const [key, value] of Object.entries(flat)) {
  if (key.startsWith('color.base.') && !HEX.test(String(value))) {
    errors.push(`${key}: colour must match #RRGGBB (uppercase hex) -- got "${value}"`);
  }
}

if (flat['banned.radius'] !== '0px') {
  errors.push(`banned.radius must stay "0px" -- got "${flat['banned.radius']}"`);
}

// Dimension tokens must be whole pixels, except tracking (em-based) and
// stroke.dash (a compound "dash gap" value, not a single length).
const SIMPLE_PX = /^(-?\d+(?:\.\d+)?)px$/;
for (const [key, value] of Object.entries(flat)) {
  if (types[key] !== 'dimension') continue;
  if (key.startsWith('tracking.') || key === 'stroke.dash') continue;
  const m = typeof value === 'string' && value.match(SIMPLE_PX);
  if (!m) continue; // not a plain "Npx" value -- nothing to check here
  const px = Number(m[1]);
  if (!Number.isInteger(px)) {
    errors.push(`${key}: dimension must be a whole pixel value -- got "${value}"`);
  }
}

if (errors.length) {
  console.error(`Build failed with ${errors.length} error(s):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}

// -- 4. Emit ------------------------------------------------------------------
mkdirSync(OUT, { recursive: true });
const STAMP = 'Generated from tokens/tokens.json. Do not edit.';

const cssName = (k) => '--m2-' + k.replace(/\./g, '-');
const cssValue = (v) =>
  Array.isArray(v)
    ? v.map((item) => (typeof item === 'string' && /\s/.test(item) ? `"${item}"` : item)).join(', ')
    : v;

const css =
  `/* ${STAMP} */\n:root {\n` +
  Object.entries(flat)
    .map(([k, v]) => `  ${cssName(k)}: ${cssValue(v)};`)
    .join('\n') +
  `\n}\n`;
writeFileSync(join(OUT, 'tokens.css'), css);

writeFileSync(join(OUT, 'tokens.flat.json'), JSON.stringify(flat, null, 2) + '\n');
writeFileSync(join(OUT, 'tokens.types.json'), JSON.stringify(types, null, 2) + '\n');

// palette.md: color.base swatches, then the semantic aliases and what they
// resolve to -- built for the brand PDF.
const BASE_ORDER = Object.keys(flatRaw).filter((k) => k.startsWith('color.base.'));
const aliasTarget = (key) => {
  const m = flatRaw[key].match(REF);
  return m ? m[1] : null;
};

let md = `# M2 Lab palette\n\nGenerated from tokens/tokens.json. Do not edit.\n\n`;
md += `## Base colours\n\n| Token | Hex | Description |\n|---|---|---|\n`;
for (const key of BASE_ORDER) {
  const name = key.replace('color.base.', '');
  md += `| \`${key}\` | \`${flat[key]}\` | ${descriptions[key] || ''} |\n`;
}

md += `\n## Semantic aliases\n\n| Token | Resolves to | Hex | Description |\n|---|---|---|---|\n`;
for (const key of Object.keys(flatRaw)) {
  if (!key.startsWith('color.') || key.startsWith('color.base.')) continue;
  const target = aliasTarget(key);
  const targetLabel = target ? `\`${target}\`` : `literal \`${flatRaw[key]}\``;
  md += `| \`${key}\` | ${targetLabel} | \`${flat[key]}\` | ${descriptions[key] || ''} |\n`;
}
writeFileSync(join(OUT, 'palette.md'), md);

console.log(`Built ${Object.keys(flat).length} tokens from ${SRC}`);
console.log(`  ${join(OUT, 'tokens.css')}`);
console.log(`  ${join(OUT, 'tokens.flat.json')}`);
console.log(`  ${join(OUT, 'tokens.types.json')}`);
console.log(`  ${join(OUT, 'palette.md')}`);
