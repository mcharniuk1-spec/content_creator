#!/usr/bin/env node
// M2 Lab design-system linter. Node 22, no dependencies.
// Usage: node checks/lint.mjs <file-or-dir> [...] [--copy] [--json] [--rules]

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const TOKENS_PATH = path.join(ROOT, 'tokens', 'tokens.json');
const VOCAB_PATH = path.join(ROOT, 'brand', '05-vocabulary.md');
const RULES_PATH = path.join(__dirname, 'lint-rules.json');

const CODE_EXT = new Set(['.html', '.css', '.svg']);
const COPY_EXT = new Set(['.md', '.txt', '.json']);
const SCAN_EXT = new Set(['.html', '.css', '.svg', '.md', '.txt', '.json']);

const DEFAULT_SANS_FONTS = ['inter', 'roboto', 'open sans', 'lato', 'geist', 'space grotesk', 'instrument serif'];
const EMOJI_RE = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu;

// ---------------------------------------------------------------- tokens --

function loadTokens() {
  return JSON.parse(fs.readFileSync(TOKENS_PATH, 'utf8'));
}

function expandHex(hex) {
  let h = hex.replace('#', '').toUpperCase();
  if (h.length === 3 || h.length === 4) h = h.split('').map((c) => c + c).join('');
  if (h.length >= 6) h = h.slice(0, 6);
  return '#' + h;
}

function hexToRgb(hex) {
  const h = expandHex(hex).slice(1);
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

function hexDistance(a, b) {
  const ca = hexToRgb(a);
  const cb = hexToRgb(b);
  return Math.sqrt((ca.r - cb.r) ** 2 + (ca.g - cb.g) ** 2 + (ca.b - cb.b) ** 2);
}

function collectPalette(tokens) {
  const set = new Set();
  for (const v of Object.values(tokens.color.base)) {
    if (typeof v.$value === 'string' && /^#[0-9a-fA-F]{3,8}$/.test(v.$value)) {
      set.add(expandHex(v.$value));
    }
  }
  return set;
}

function collectAllowedFonts(tokens) {
  const set = new Set();
  for (const v of Object.values(tokens.font.family)) {
    if (Array.isArray(v.$value)) v.$value.forEach((n) => set.add(String(n).toLowerCase()));
  }
  return set;
}

function collectMeasure(tokens) {
  return {
    hookChars: tokens.measure['hook-chars'].$value,
    bodyChars: tokens.measure['body-chars'].$value,
    hookWordsReel: tokens.measure['hook-words-reel'].$value,
    hookWords4x5: tokens.measure['hook-words-4x5'].$value,
  };
}

// ------------------------------------------------------------- vocabulary --

function loadVocabulary() {
  const raw = fs.readFileSync(VOCAB_PATH, 'utf8');
  const lines = raw.split('\n');
  let inSection = false;
  const phrases = [];
  for (const line of lines) {
    if (/^##\s+Words and constructions we do not publish/i.test(line)) {
      inSection = true;
      continue;
    }
    if (inSection && /^##\s/.test(line)) break;
    if (!inSection) continue;
    const matches = line.match(/`([^`]+)`/g);
    if (matches) for (const m of matches) phrases.push(m.slice(1, -1));
  }
  return buildVocabMatchers(phrases);
}

// Two phrases in the list carry a placeholder rather than a literal word:
// "comment X below" and "comment [WORD]". Turn those into a wildcard regex;
// everything else is a plain case-insensitive substring match.
function buildVocabMatchers(phrases) {
  return phrases.map((phrase) => {
    const hasPlaceholder = /\bX\b/.test(phrase) || /\[WORD\]/i.test(phrase);
    if (!hasPlaceholder) return { phrase, regex: null };
    const SENTINEL = '\u0000';
    let pattern = phrase.replace(/\[WORD\]/gi, SENTINEL).replace(/\bX\b/g, SENTINEL);
    pattern = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    pattern = pattern.split(SENTINEL).join('\\S+');
    return { phrase, regex: new RegExp(pattern, 'i') };
  });
}

// ------------------------------------------------------------------ files --

function walk(target) {
  const out = [];
  const stat = fs.statSync(target);
  if (stat.isDirectory()) {
    for (const entry of fs.readdirSync(target)) {
      if (entry === 'node_modules' || entry === '.git') continue;
      out.push(...walk(path.join(target, entry)));
    }
  } else if (SCAN_EXT.has(path.extname(target).toLowerCase())) {
    out.push(target);
  }
  return out;
}

function isSlotsFile(filePath) {
  if (path.extname(filePath).toLowerCase() !== '.json') return null;
  try {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    if (data && typeof data === 'object' && data.slots && typeof data.slots === 'object') return data;
  } catch {
    return null;
  }
  return null;
}

// ------------------------------------------------------------- code rules --

function lintCodeFile(filePath, content, ctx) {
  const issues = [];
  const lines = content.split('\n');
  const scoped = /(^|\/)(templates|assets)\//.test(filePath.replace(ROOT, ''));

  lines.forEach((line, i) => {
    const ln = i + 1;

    // (a) hex colour literals
    const hexMatches = line.match(/#[0-9a-fA-F]{3,8}\b/g) || [];
    for (const raw of hexMatches) {
      const norm = expandHex(raw);
      if (ctx.palette.has(norm)) continue;
      if (hexDistance(norm, '#F4F1EA') < 40 || hexDistance(norm, '#D97757') < 40) {
        issues.push(err(ln, 'cream-terracotta', `hex ${raw} sits in the cream/terracotta AI-default cluster`));
      } else if (hexDistance(norm, '#0B0B0B') < 40 || hexDistance(norm, '#111111') < 40) {
        issues.push(err(ln, 'fake-black', `hex ${raw} is a tinted near-black standing in for true black`));
      } else if (hexDistance(norm, '#BFFB4C') < 40 || hexDistance(norm, '#E34234') < 40) {
        issues.push(err(ln, 'near-black-acid-accent', `hex ${raw} is within 40 of the acid-green/vermilion AI-default accent and is not in the palette`));
      } else {
        issues.push(err(ln, 'color-outside-tokens', `hex ${raw} is not a palette colour (tokens.json color.base)`));
      }
    }

    // (b) font-family
    const fontMatch = line.match(/font-family\s*:\s*([^;"'}]+)/i);
    if (fontMatch) {
      const names = fontMatch[1].split(',').map((n) => n.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
      for (const name of names) {
        const lower = name.toLowerCase();
        if (ctx.fonts.has(lower)) continue;
        if (/^var\(--m2-font-family-[a-z-]+\)$/.test(lower)) continue; // token reference resolves to a Plex stack
        if (DEFAULT_SANS_FONTS.includes(lower)) {
          issues.push(err(ln, 'default-sans-fonts', `font "${name}" is a default generative-model font, not IBM Plex`));
        } else {
          issues.push(err(ln, 'font-outside-plex', `font "${name}" is outside IBM Plex Sans / Sans Condensed / Mono and the tokens.json fallbacks`));
        }
      }
    }

    // (c) border-radius
    const radiusMatch = line.match(/border-radius\s*:\s*([^;]+);?/i);
    if (radiusMatch) {
      const values = radiusMatch[1].trim().split(/\s+/);
      const nonZero = values.some((v) => parseFloat(v) !== 0);
      if (nonZero) issues.push(err(ln, 'uniform-radius', `border-radius "${radiusMatch[1].trim()}" — the system has no radius other than 0`));
    }

    // box-shadow
    const shadowMatch = line.match(/box-shadow\s*:\s*([^;]+);?/i);
    if (shadowMatch && shadowMatch[1].trim().toLowerCase() !== 'none') {
      issues.push(err(ln, 'soft-card-shadow', `box-shadow "${shadowMatch[1].trim()}" — the system has no shadow`));
    }

    // gradient
    if (/[\w-]*gradient\s*\(/i.test(line)) {
      const purple = /(linear|radial)-gradient\([^)]*#?(6[0-9a-f]{2}|7[0-9a-f]{2}|8[0-9a-f]{2})[0-9a-f]{3}/i.test(line);
      if (purple) issues.push(err(ln, 'purple-gradient-hero', 'purple/indigo gradient used as a hero background'));
      else issues.push(err(ln, 'any-gradient', 'gradient used as decoration — the system has none'));
    }

    // text-align center / text-anchor middle
    if (/text-align\s*:\s*center/i.test(line) || /text-anchor\s*=\s*["']middle["']/i.test(line)) {
      issues.push(err(ln, 'centered-text', 'centred text — the system is left-set only'));
    }

    // filter: drop-shadow
    if (/filter\s*:\s*[^;]*drop-shadow/i.test(line)) {
      issues.push(err(ln, 'drop-shadow-filter', 'filter: drop-shadow is not part of the system'));
    }

    // (d) emoji
    if (EMOJI_RE.test(line)) {
      issues.push(err(ln, 'emoji-as-icon', 'emoji code point found — icons are outline SVG, never emoji'));
    }
    EMOJI_RE.lastIndex = 0;

    // (e) em dash label / arrow appended
    if (/\s—\s/.test(line)) {
      issues.push(err(ln, 'emdash-label', 'spaced em dash used as a "WORD — fragment" label'));
    }
    if (/→\s*(<|$)/.test(line)) {
      issues.push(err(ln, 'arrow-cta', 'arrow glyph appended to link/button text'));
    }

    // (f) filled icon, templates/ and assets/ only
    if (scoped) {
      const pathTagRe = /<path\b[^>]*\bfill\s*=\s*["']([^"']+)["'][^>]*>/gi;
      let m;
      while ((m = pathTagRe.exec(line))) {
        const fillVal = m[1].trim().toLowerCase();
        if (fillVal !== 'none' && fillVal !== 'currentcolor') {
          issues.push(warn(ln, 'filled-duotone-icon', `filled icon? <path fill="${m[1]}"> — icons should be outline (fill="none" or "currentColor")`));
        }
      }
    }
  });

  return issues;
}

// ------------------------------------------------------------- copy rules --

function lintCopyFile(content, vocabulary) {
  const issues = [];
  const lines = content.split('\n');
  lines.forEach((line, i) => {
    const ln = i + 1;
    const lower = line.toLowerCase();
    for (const { phrase, regex } of vocabulary) {
      const hit = regex ? regex.test(line) : lower.includes(phrase.toLowerCase());
      if (hit) {
        issues.push(err(ln, 'banned-vocabulary', `banned phrase "${phrase}" (brand/05-vocabulary.md)`));
      }
    }
    if (/[—–]/.test(line)) {
      issues.push(err(ln, 'long-dash-copy', 'long dash (— or –) in copy — use a comma or a full stop'));
    }
    if (EMOJI_RE.test(line)) {
      issues.push(err(ln, 'emoji-as-icon', 'emoji in published copy'));
    }
    EMOJI_RE.lastIndex = 0;
  });
  return issues;
}

// ------------------------------------------------------------ slots rules --

function lintSlotsFile(filePath, data, measure) {
  const issues = [];
  const base = path.basename(filePath).toLowerCase();
  const narrow = base.includes('4x5') || base.includes('carousel');
  const wordLimit = narrow ? measure.hookWords4x5 : measure.hookWordsReel;
  const slots = data.slots;

  if (typeof slots.hook === 'string') {
    const words = slots.hook.split(/\s+/).filter(Boolean).length;
    if (words > wordLimit) {
      issues.push(err(null, 'hook-words-limit', `hook has ${words} words, limit ${wordLimit}${narrow ? ' (4x5/carousel)' : ''}`));
    }
    slots.hook.split('\n').forEach((l, idx) => {
      if (l.length > measure.hookChars) {
        issues.push(err(idx + 1, 'hook-line-chars', `hook line ${idx + 1} is ${l.length} chars, limit ${measure.hookChars}: "${l}"`));
      }
    });
  }

  if (typeof slots.body === 'string') {
    slots.body.split('\n').forEach((l, idx) => {
      if (l.length > measure.bodyChars) {
        issues.push(err(idx + 1, 'body-line-chars', `body line ${idx + 1} is ${l.length} chars, limit ${measure.bodyChars}: "${l}"`));
      }
    });
  }

  return issues;
}

// ------------------------------------------------------------------ utils --

function err(line, rule, message) {
  return { line, rule, level: 'error', message };
}
function warn(line, rule, message) {
  return { line, rule, level: 'warn', message };
}

// ------------------------------------------------------------------- main --

function main() {
  const argv = process.argv.slice(2);
  const opts = { json: false, rules: false, copy: false };
  const targets = [];
  for (const a of argv) {
    if (a === '--json') opts.json = true;
    else if (a === '--rules') opts.rules = true;
    else if (a === '--copy') opts.copy = true;
    else targets.push(a);
  }

  if (opts.rules) {
    const rules = fs.readFileSync(RULES_PATH, 'utf8');
    process.stdout.write(rules.endsWith('\n') ? rules : rules + '\n');
    process.exit(0);
  }

  if (targets.length === 0) {
    console.error('usage: node checks/lint.mjs <file-or-dir> [...] [--copy] [--json] [--rules]');
    process.exit(1);
  }

  const tokens = loadTokens();
  const ctx = {
    palette: collectPalette(tokens),
    fonts: collectAllowedFonts(tokens),
    measure: collectMeasure(tokens),
  };
  const vocabulary = loadVocabulary();

  let files = [];
  for (const t of targets) {
    const abs = path.resolve(t);
    if (!fs.existsSync(abs)) {
      console.error(`not found: ${t}`);
      process.exit(1);
    }
    files.push(...walk(abs));
  }
  files = [...new Set(files)].sort();

  const results = [];
  let hasError = false;

  for (const file of files) {
    const rel = path.relative(process.cwd(), file);
    const ext = path.extname(file).toLowerCase();
    let issues = [];

    if (CODE_EXT.has(ext)) {
      const content = fs.readFileSync(file, 'utf8');
      issues = lintCodeFile(file, content, ctx);
    } else {
      const slotsData = isSlotsFile(file);
      if (slotsData) {
        issues = lintSlotsFile(file, slotsData, ctx.measure);
      } else if (opts.copy && COPY_EXT.has(ext)) {
        const content = fs.readFileSync(file, 'utf8');
        issues = lintCopyFile(content, vocabulary);
      } else {
        continue; // nothing applicable to this file
      }
    }

    if (issues.length) {
      results.push({ file: rel, issues });
      if (issues.some((i) => i.level === 'error')) hasError = true;
    }
  }

  if (opts.json) {
    console.log(JSON.stringify({ ok: !hasError, results }, null, 2));
  } else {
    if (results.length === 0) {
      console.log('lint: clean');
    }
    for (const r of results) {
      console.log(r.file);
      for (const issue of r.issues) {
        const loc = issue.line != null ? String(issue.line).padStart(4, ' ') : '   -';
        console.log(`  ${loc}  ${issue.level.padEnd(5)}  ${issue.rule.padEnd(24)}  ${issue.message}`);
      }
    }
    const errCount = results.reduce((n, r) => n + r.issues.filter((i) => i.level === 'error').length, 0);
    const warnCount = results.reduce((n, r) => n + r.issues.filter((i) => i.level === 'warn').length, 0);
    console.log(`\n${errCount} error(s), ${warnCount} warning(s) across ${files.length} file(s) checked.`);
  }

  process.exit(hasError ? 1 : 0);
}

main();
