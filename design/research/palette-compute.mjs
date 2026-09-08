#!/usr/bin/env node
// M2 Lab — palette spread computation. No dependencies.
//   node /Users/mihailampleev/Desktop/m2lab-brand/research/palette-compute.mjs
//
// Writes into the same directory:
//   palette-options.json, palette-options.md, palette-sheet.html
//
// Colour science used (all implemented below, nothing guessed):
//  - sRGB <-> linear sRGB: IEC 61966-2-1 transfer function.
//  - linear sRGB <-> OKLab: Björn Ottosson (2020), "A perceptual color space
//    for image processing". OKLCH = polar form of OKLab (C = hypot(a,b),
//    h = atan2(b,a) in degrees).
//  - WCAG 2.x contrast: relative luminance Y = 0.2126R + 0.7152G + 0.0722B on
//    linear sRGB; ratio = (Y_light + 0.05) / (Y_dark + 0.05).
//  - Colour-vision deficiency: Machado, Oliveira & Fernandes (2009),
//    "A physiologically-based model for simulation of color vision deficiency",
//    IEEE TVCG 15(6). Severity 1.0 matrices, applied in LINEAR sRGB.
//  - Colour difference: Euclidean distance in OKLab (dE_OK).

import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Local calendar date (Europe/Vienna), not UTC.
const TODAY = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Vienna' }).format(new Date());

const OUT = dirname(fileURLToPath(import.meta.url));

/* ---------------------------------------------------------------- basics */

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const s2l = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
const l2s = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
}
function rgbToHex(rgb) {
  return '#' + rgb.map((c) => Math.round(clamp01(c) * 255).toString(16).padStart(2, '0').toUpperCase()).join('');
}
const hexToLin = (hex) => hexToRgb(hex).map(s2l);
const linToHex = (lin) => rgbToHex(lin.map((c) => l2s(clamp01(c))));

/* ------------------------------------------------------- OKLab / OKLCH */

function linToOklab([r, g, b]) {
  const l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
  const m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b;
  const s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b;
  const l_ = Math.cbrt(l), m_ = Math.cbrt(m), s_ = Math.cbrt(s);
  return [
    0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
    1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
    0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
  ];
}
function oklabToLin([L, a, b]) {
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.291485548 * b;
  const l = l_ ** 3, m = m_ ** 3, s = s_ ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}
const labToLch = ([L, a, b]) => {
  let h = (Math.atan2(b, a) * 180) / Math.PI;
  if (h < 0) h += 360;
  return [L, Math.hypot(a, b), h];
};
const lchToLab = ([L, C, h]) => [L, C * Math.cos((h * Math.PI) / 180), C * Math.sin((h * Math.PI) / 180)];

const hexToOklch = (hex) => labToLch(linToOklab(hexToLin(hex)));
const hexToOklab = (hex) => linToOklab(hexToLin(hex));

const inGamut = (lin) => lin.every((c) => c >= -1e-4 && c <= 1 + 1e-4);

/** OKLCH -> hex, reducing chroma by bisection until sRGB-representable. */
function oklchToHex([L, C, h]) {
  if (inGamut(oklabToLin(lchToLab([L, C, h])))) return linToHex(oklabToLin(lchToLab([L, C, h])));
  let lo = 0, hi = C;
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (inGamut(oklabToLin(lchToLab([L, mid, h])))) lo = mid; else hi = mid;
  }
  return linToHex(oklabToLin(lchToLab([L, lo, h])));
}

/* ---------------------------------------------------------------- WCAG */

const relLum = (hex) => { const [r, g, b] = hexToLin(hex); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
function contrast(a, b) {
  const [x, y] = [relLum(a), relLum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

/* ------------------------------------------- CVD — Machado et al. 2009 */

const MACHADO = {
  protanopia: [
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281, 0.099216],
    [-0.003882, -0.048116, 1.051998],
  ],
  deuteranopia: [
    [0.367322, 0.860646, -0.227968],
    [0.280085, 0.672501, 0.047413],
    [-0.01182, 0.04294, 0.968881],
  ],
};
function simulate(hex, kind) {
  const M = MACHADO[kind], lin = hexToLin(hex);
  return linToHex(M.map((row) => clamp01(row[0] * lin[0] + row[1] * lin[1] + row[2] * lin[2])));
}

/* ------------------------------------------------------------ metrics */

const dEok = (h1, h2) => {
  const a = hexToOklab(h1), b = hexToOklab(h2);
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
};
const dHue = (h1, h2) => { const d = Math.abs(h1 - h2) % 360; return d > 180 ? 360 - d : d; };
const r2 = (x) => Math.round(x * 100) / 100;
const r3 = (x) => Math.round(x * 1000) / 1000;
const r1 = (x) => Math.round(x * 10) / 10;

/* ------------------------------------------------ reference / clusters */

const REF = {
  acidGreen: '#BFFB4C',   // cluster 1 accent = our current Lime
  vermilion: '#E34234',
  terracotta: '#D97757',  // cluster 2 accent
  cream: '#F4F1EA',       // cluster 2 surface
  tintedBlack: '#0B0B0B', // cluster 3 surface
};

/* ---------------------------------------------------------- palettes */
// kind: paper | ink | accent | stamp | structure | muted | rule
// Variant colours are AUTHORED IN OKLCH and converted; reported OKLCH is
// recomputed from the resulting hex so the tables show the true value.

const CURRENT = {
  id: 'current', name: 'Current (approved 4 Sep 2026)',
  thesis: 'Ink-first, one acid-green accent, one vermilion stamp — all three markers of Anthropic cluster 1.',
  colors: [
    { name: 'Ink',      hex: '#101A17', kind: 'ink',       role: 'Text, dark surface, mark' },
    { name: 'Paper',    hex: '#E9EAE5', kind: 'paper',     role: 'Light surface, documents, carousels' },
    { name: 'Stamp',    hex: '#D8402B', kind: 'stamp',     role: 'Verdict, risk, KILL. Nothing else' },
    { name: 'Lime',     hex: '#BFFB4C', kind: 'accent',    role: 'Mark, rare data indicator; glows on dark only' },
    { name: 'Graphite', hex: '#69706B', kind: 'muted',     role: 'Secondary text, lines, labels' },
    { name: 'Rule',     hex: '#C3C7C1', kind: 'rule',      role: 'Hairline on Paper' },
  ],
  feel: [
    'Reads as the default "dark lab terminal" — the exact silhouette models fall into.',
    'Lime and Stamp are both maximum-chroma, so the system has two shouts and no speaking voice.',
    'Lime L is within 0.01 of Paper L: the mark all but disappears on the light surface.',
    'No structural mid-tone, so diagrams are built from Graphite alone and read flat.',
    'Recognisable and confident on dark; indistinguishable from a hundred AI-brand decks.',
  ],
};

const A = {
  id: 'A', name: 'A — Oxide (Paper-first)',
  thesis: 'Smallest true move: flip the primary surface to Paper, de-neon the green, pull Stamp from vermilion to oxide, add a structural blueprint blue.',
  colors: [
    { name: 'Paper',     kind: 'paper',     lch: [0.930, 0.006, 210], role: 'PRIMARY surface — carousels, covers, documents' },
    { name: 'Ink',       kind: 'ink',       lch: [0.215, 0.022, 195], role: 'Text on Paper; dark surface for accent frames only' },
    { name: 'Signal',    kind: 'accent',    lch: [0.800, 0.160, 142], role: 'Mark, positive verdict, data highlight' },
    { name: 'Oxide',     kind: 'stamp',     lch: [0.550, 0.155, 22],  role: 'Verdict, risk, KILL. Nothing else' },
    { name: 'Blueprint', kind: 'structure', lch: [0.450, 0.075, 250], role: 'Diagrams, arrows, second-level fills, chart series 2' },
    { name: 'Graphite',  kind: 'muted',     lch: [0.500, 0.012, 197], role: 'Secondary text, labels' },
    { name: 'Rule',      kind: 'rule',      lch: [0.820, 0.008, 210], role: 'Hairline on Paper' },
  ],
  feel: [
    'Feels like a printed lab report rather than a terminal — the dark frame becomes a guest, not the host.',
    'Signal drops 0.116 in L and 0.046 in C, so the accent stops reading as neon — but it is still a fill on Paper, not a text colour.',
    'Oxide is a stamped ink, not a warning light; risk now looks archival instead of alarming.',
    'Blueprint gives diagrams a second structural voice, so the system reads "two accents + structure".',
    'BREAKS: every Ink-background template must be re-cut for Paper; the mark loses its glow on dark, and Signal at 0.80 L no longer halates against Ink the way Lime did.',
  ],
};

const B = {
  id: 'B', name: 'B — Amber (Ink-first)',
  thesis: 'Keeps the dark surface but changes what shouts: amber becomes the primary signal, green is demoted to a quiet data tint, Stamp moves to crimson away from both vermilion and terracotta.',
  colors: [
    { name: 'Ink',      kind: 'ink',       lch: [0.190, 0.020, 260], role: 'PRIMARY surface — blue-black, not green-black' },
    { name: 'Paper',    kind: 'paper',     lch: [0.925, 0.007, 240], role: 'Text on Ink; light surface for documents' },
    { name: 'Amber',    kind: 'accent',    lch: [0.820, 0.155, 85],  role: 'Primary signal — mark, headline accent, KEEP' },
    { name: 'Mint',     kind: 'accent2',   lch: [0.850, 0.130, 155], role: 'Data indicator only — charts, deltas, the mark\'s wedge' },
    { name: 'Crimson',  kind: 'stamp',     lch: [0.550, 0.190, 15],  role: 'Verdict, risk, KILL. Nothing else' },
    { name: 'Slate',    kind: 'structure', lch: [0.480, 0.035, 260], role: 'Diagrams, dividers, secondary fills' },
    { name: 'Rule',     kind: 'rule',      lch: [0.800, 0.010, 250], role: 'Hairline on Paper; also line on Ink at low opacity' },
  ],
  feel: [
    'Keeps the current silhouette so nothing has to be re-cut, but the accent hue is ~45 degrees away from acid.',
    'Amber on blue-black reads as instrumentation and sodium light rather than as a chemical.',
    'Mint keeps the mark legible as "the M2 green" while removing its neon claim.',
    'Crimson separates cleanly from both vermilion and terracotta, so cluster 2 is off the table too.',
    'BREAKS: three chromatic colours is one more than the system wants; discipline is required or covers turn into traffic lights. The dark surface still matches cluster 1 geometry — only the hue argues against it.',
  ],
};

const C = {
  id: 'C', name: 'C — Instrument (dual-surface, cyan)',
  thesis: 'Boldest of the three: the bright accent leaves green entirely for cyan, green survives as a deep viridian data colour, and a muted sage carries structure.',
  colors: [
    { name: 'Paper',    kind: 'paper',     lch: [0.935, 0.006, 200], role: 'Primary surface for documents and carousels' },
    { name: 'Ink',      kind: 'ink',       lch: [0.210, 0.030, 220], role: 'Text on Paper; surface for Reel covers' },
    { name: 'Cyan',     kind: 'accent',    lch: [0.800, 0.115, 200], role: 'Primary signal — mark, KEEP, highlight' },
    { name: 'Viridian', kind: 'accent2',   lch: [0.620, 0.120, 155], role: 'Data / positive green, legible on Paper' },
    { name: 'Signal Red', kind: 'stamp',   lch: [0.580, 0.175, 12],  role: 'Verdict, risk, KILL. Nothing else' },
    { name: 'Sage',     kind: 'structure', lch: [0.510, 0.028, 130], role: 'Diagrams, grid, secondary fills' },
    { name: 'Rule',     kind: 'rule',      lch: [0.820, 0.006, 200], role: 'Hairline on Paper' },
  ],
  feel: [
    'Reads as an oscilloscope and a measuring instrument; the laboratory metaphor gets literal.',
    'Cyan is the furthest any of the three variants gets from the acid-green cluster in hue.',
    'Viridian is the first green in the system that is actually readable as text on Paper.',
    'Sage keeps structure warm-neutral so the page does not turn into a single blue wash.',
    'BREAKS: the mark stops being "the lime one". Recognisability against the approved 4 Sep palette is the weakest here, and Max would need the logo re-exported with a hue nobody has seen yet.',
  ],
};

/* ---------------------------------------------------------- resolve */

for (const v of [A, B, C]) for (const c of v.colors) c.hex = oklchToHex(c.lch);
for (const v of [CURRENT, A, B, C]) {
  for (const c of v.colors) {
    const [L, Ch, h] = hexToOklch(c.hex);
    c.oklch = { L: r3(L), C: r3(Ch), h: r1(h) };
  }
  v.paper = v.colors.find((c) => c.kind === 'paper');
  v.ink = v.colors.find((c) => c.kind === 'ink');
  v.stamp = v.colors.find((c) => c.kind === 'stamp');
  v.accent = v.colors.find((c) => c.kind === 'accent');
  v.accent2 = v.colors.find((c) => c.kind === 'accent2') || null;
  v.structure = v.colors.find((c) => c.kind === 'structure') || null;
  v.rule = v.colors.find((c) => c.kind === 'rule');
  v.muted = v.colors.find((c) => c.kind === 'muted') || v.structure;
  v.secondary = v.muted;  // colour carrying secondary text on Paper
}

/* ------------------------------------------------------- contrasts */

function pairsFor(v) {
  const out = [];
  const push = (label, fg, bg, need, byDesign = false) => {
    const ratio = contrast(fg.hex, bg.hex);
    out.push({ pair: label, fg: fg.hex, bg: bg.hex, ratio: r2(ratio), need, pass: ratio >= need, byDesign });
  };
  push('Ink on Paper (body text)', v.ink, v.paper, 4.5);
  push('Paper on Ink (body text)', v.paper, v.ink, 4.5);
  for (const a of [v.accent, v.accent2].filter(Boolean)) {
    push(`${a.name} on Ink (graphic/large)`, a, v.ink, 3);
    // A bright accent on the light surface is a FILL that carries Ink text on
    // top; it is never text itself. Flagged, but marked by-design.
    push(`${a.name} on Paper (graphic/large)`, a, v.paper, 3, true);
  }
  push(`${v.stamp.name} on Ink (graphic/large)`, v.stamp, v.ink, 3);
  push(`${v.stamp.name} on Paper (graphic/large)`, v.stamp, v.paper, 3);
  if (v.structure) push(`${v.structure.name} on Paper (graphic/large)`, v.structure, v.paper, 3);
  if (v.secondary) push(`${v.secondary.name} on Paper (secondary text)`, v.secondary, v.paper, 4.5);
  // A hairline held to 3:1 stops being a hairline. Flagged, but by-design.
  push('Rule on Paper (hairline)', v.rule, v.paper, 3, true);
  return out;
}

/* ------------------------------------------------------------- CVD */
// Heuristic threshold used throughout: two colours are "separable by
// lightness alone" when |dL| in OKLCH >= 0.15 (roughly 15% of the full
// L range) after simulation. Stated as a working threshold, not a standard.
const DL_THRESHOLD = 0.15;

function cvdFor(v) {
  const green = v.accent2 || v.accent;   // the green-family / secondary signal
  const out = {};
  for (const kind of ['deuteranopia', 'protanopia']) {
    const s = simulate(v.stamp.hex, kind), g = simulate(green.hex, kind);
    const dL = Math.abs(hexToOklch(s)[0] - hexToOklch(g)[0]);
    out[kind] = {
      against: green.name, stampSim: s, accentSim: g,
      dL: r3(dL), dEok: r3(dEok(s, g)), separable: dL >= DL_THRESHOLD,
    };
  }
  out.normal = { dL: r3(Math.abs(v.stamp.oklch.L - green.oklch.L)), dEok: r3(dEok(v.stamp.hex, green.hex)) };
  return out;
}

/* ------------------------------------------- distance from clusters */

function clusterFor(v) {
  const acid = hexToOklch(REF.acidGreen);
  const verm = hexToOklch(REF.vermilion);
  const terr = hexToOklch(REF.terracotta);
  const a = v.accent.oklch, a2 = v.accent2 ? v.accent2.oklch : null, s = v.stamp.oklch;
  return {
    accentVsAcidGreen: { name: v.accent.name, dh: r1(dHue(a.h, acid[2])), dC: r3(a.C - acid[1]), dL: r3(a.L - acid[0]) },
    greenVsAcidGreen: a2 ? { name: v.accent2.name, dh: r1(dHue(a2.h, acid[2])), dC: r3(a2.C - acid[1]), dL: r3(a2.L - acid[0]) } : null,
    stampVsVermilion: { dh: r1(dHue(s.h, verm[2])), dC: r3(s.C - verm[1]), dL: r3(s.L - verm[0]) },
    stampVsTerracotta: { dh: r1(dHue(s.h, terr[2])), dC: r3(s.C - terr[1]), dL: r3(s.L - terr[0]) },
    paperVsCream_dEok: r3(dEok(v.paper.hex, REF.cream)),
    inkVsTintedBlack_dEok: r3(dEok(v.ink.hex, REF.tintedBlack)),
  };
}

const VARIANTS = [CURRENT, A, B, C];
for (const v of VARIANTS) { v.contrast = pairsFor(v); v.cvd = cvdFor(v); v.cluster = clusterFor(v); }

const RECOMMENDED = 'A';

/* ------------------------------------------------------------ JSON */

writeFileSync(join(OUT, 'palette-options.json'), JSON.stringify({
  generated: TODAY,
  method: {
    oklab: 'Ottosson 2020 linear-sRGB<->OKLab matrices; OKLCH is the polar form',
    wcag: 'WCAG 2.x relative luminance, (L1+0.05)/(L2+0.05)',
    cvd: 'Machado, Oliveira & Fernandes 2009, severity 1.0, applied in linear sRGB',
    difference: 'Euclidean distance in OKLab (dE_OK)',
    dlThreshold: DL_THRESHOLD,
    script: 'research/palette-compute.mjs',
  },
  references: REF,
  recommendation: RECOMMENDED,
  variants: VARIANTS.map((v) => ({
    id: v.id, name: v.name, thesis: v.thesis, recommended: v.id === RECOMMENDED,
    colors: v.colors.map((c) => ({ name: c.name, hex: c.hex, oklch: c.oklch, kind: c.kind, role: c.role })),
    contrast: v.contrast, colorBlindness: v.cvd, clusterDistance: v.cluster, feel: v.feel,
  })),
}, null, 2));

/* -------------------------------------------------------------- MD */

const flag = (p) => (p.pass ? 'ok' : p.byDesign ? 'below — by design' : '**FAIL**');
const ctable = (v) => [
  '| Pair | Ratio | Needs | |', '|---|---|---|---|',
  ...v.contrast.map((p) => `| ${p.pair} | ${p.ratio.toFixed(2)}:1 | ${p.need}:1 | ${flag(p)} |`),
].join('\n');
const stable = (v) => [
  '| Name | HEX | OKLCH (L, C, h) | Role |', '|---|---|---|---|',
  ...v.colors.map((c) => `| ${c.name} | \`${c.hex}\` | ${c.oklch.L}, ${c.oklch.C}, ${c.oklch.h}° | ${c.role} |`),
].join('\n');
const cvdtable = (v) => {
  const g = v.accent2 || v.accent;
  return [
    `Pair checked: **${v.stamp.name}** vs **${g.name}**. Threshold for "separable by lightness alone": ΔL ≥ ${DL_THRESHOLD}.`, '',
    '| Vision | Stamp → | Accent → | ΔL | ΔE_OK | Separable by L |', '|---|---|---|---|---|---|',
    `| normal | \`${v.stamp.hex}\` | \`${g.hex}\` | ${v.cvd.normal.dL} | ${v.cvd.normal.dEok} | ${v.cvd.normal.dL >= DL_THRESHOLD ? 'yes' : 'no'} |`,
    `| deuteranopia | \`${v.cvd.deuteranopia.stampSim}\` | \`${v.cvd.deuteranopia.accentSim}\` | ${v.cvd.deuteranopia.dL} | ${v.cvd.deuteranopia.dEok} | ${v.cvd.deuteranopia.separable ? 'yes' : 'NO'} |`,
    `| protanopia | \`${v.cvd.protanopia.stampSim}\` | \`${v.cvd.protanopia.accentSim}\` | ${v.cvd.protanopia.dL} | ${v.cvd.protanopia.dEok} | ${v.cvd.protanopia.separable ? 'yes' : 'NO'} |`,
  ].join('\n');
};
const cltable = (v) => {
  const c = v.cluster;
  const rows = [
    `| ${c.accentVsAcidGreen.name} vs acid green \`#BFFB4C\` | ${c.accentVsAcidGreen.dh}° | ${c.accentVsAcidGreen.dC} | ${c.accentVsAcidGreen.dL} |`,
  ];
  if (c.greenVsAcidGreen) rows.push(`| ${c.greenVsAcidGreen.name} vs acid green \`#BFFB4C\` | ${c.greenVsAcidGreen.dh}° | ${c.greenVsAcidGreen.dC} | ${c.greenVsAcidGreen.dL} |`);
  rows.push(`| ${v.stamp.name} vs vermilion \`#E34234\` | ${c.stampVsVermilion.dh}° | ${c.stampVsVermilion.dC} | ${c.stampVsVermilion.dL} |`);
  rows.push(`| ${v.stamp.name} vs terracotta \`#D97757\` | ${c.stampVsTerracotta.dh}° | ${c.stampVsTerracotta.dC} | ${c.stampVsTerracotta.dL} |`);
  return [
    '| Comparison | Δh | ΔC | ΔL |', '|---|---|---|---|', ...rows, '',
    `ΔE_OK Paper vs cream \`#F4F1EA\`: **${c.paperVsCream_dEok}** · ΔE_OK Ink vs tinted black \`#0B0B0B\`: **${c.inkVsTintedBlack_dEok}**`,
  ].join('\n');
};

const section = (v) => `## ${v.name}

${v.thesis}

${stable(v)}

**Contrast**

${ctable(v)}

**Colour blindness (Machado 2009, severity 1.0)**

${cvdtable(v)}

**Distance from the Anthropic clusters**

${cltable(v)}

**What changes, what breaks**

${v.feel.map((f) => `- ${f}`).join('\n')}
`;

const cmpRow = (v) => {
  const fails = v.contrast.filter((p) => !p.pass && !p.byDesign).length;
  const c = v.cluster;
  return `| ${v.id} | ${v.colors.length} | ${v.paper.hex} / ${v.ink.hex} | ${c.accentVsAcidGreen.dh}° | ${c.stampVsVermilion.dh}° / ${c.stampVsTerracotta.dh}° | ${c.paperVsCream_dEok} | ${fails} | ${v.cvd.deuteranopia.separable && v.cvd.protanopia.separable ? 'yes' : 'no'} |`;
};

const md = `# M2 Lab — palette spread options

Generated ${TODAY} by \`research/palette-compute.mjs\`. Every number below is computed by that script; nothing is estimated by eye.

## Problem

Anthropic publishes the default clusters its models collapse into (raw source of \`github.com/anthropics/skills\`, frontend-design skill). Three of them matter to us:

1. Near-black background with **one** bright acid-green or vermilion accent.
2. Cream (~\`#F4F1EA\`) plus contrasting serif plus terracotta (~\`#D97757\`).
3. Tinted black (\`#0B0B0B\` / \`#111\`) with mono captions.

The approved 4 Sep palette carries all three elements of cluster 1 at once: Ink \`#101A17\` as the primary surface, Lime \`#BFFB4C\` as a single acid accent, Stamp \`#D8402B\` sitting almost exactly on vermilion. The brief is to **spread the palette slightly**, not to redesign it. The mark's geometry is untouchable; only its two colour values may change, and the palette must still be recognisable as the same brand.

Five levers were used, in this order of effect:

- **(a) which surface is primary** — Paper-first vs Ink-first
- **(b) hue shift of the bright accent** away from acid green
- **(c) hue and chroma shift of Stamp** away from vermilion
- **(d) one muted structural colour**, so the system reads "two accents + structure" instead of "one shout"
- **(e) a distinct tint on Ink or Paper** — cool-teal, blue-black or neutral-cool

## Method

- **OKLab / OKLCH.** Ottosson (2020) linear-sRGB ↔ OKLab matrices, implemented in the script; OKLCH is the polar form, \`C = hypot(a,b)\`, \`h = atan2(b,a)\` in degrees. Variant colours are authored as OKLCH targets, converted to sRGB with chroma reduced by bisection when out of gamut, then the reported OKLCH is recomputed from the resulting hex so the tables show the true value, not the target.
- **Contrast.** WCAG 2.x: relative luminance \`Y = 0.2126R + 0.7152G + 0.0722B\` on linear sRGB, ratio \`(Y_light + 0.05) / (Y_dark + 0.05)\`. Thresholds applied: **4.5:1** for body text, **3:1** for large text and graphical objects.
- **Colour blindness.** Machado, Oliveira & Fernandes (2009), *A physiologically-based model for simulation of color vision deficiency*, IEEE TVCG 15(6) — severity 1.0 matrices for deuteranopia and protanopia, applied in **linear** sRGB.
- **Colour difference.** Euclidean distance in OKLab (\`ΔE_OK\`). Hue difference is the shortest circular arc.
- **Working threshold.** Two colours count as "separable by lightness alone" at **ΔL ≥ ${DL_THRESHOLD}** in OKLCH. This is a working heuristic chosen here, not a published standard. Verdicts are shape-coded anyway (KEEP filled, KILL outlined, TEST dashed), so this is a second line of defence.
- **Script:** \`/Users/mihailampleev/Desktop/m2lab-brand/research/palette-compute.mjs\` — no dependencies, \`node palette-compute.mjs\`.

${section(CURRENT)}
${section(A)}
${section(B)}
${section(C)}
## Comparison

| Variant | Colours | Paper / Ink | Accent Δh from acid green | Stamp Δh from vermilion / terracotta | Paper ΔE_OK from cream | Blocking contrast failures | CVD-separable |
|---|---|---|---|---|---|---|---|
${[CURRENT, A, B, C].map(cmpRow).join('\n')}

Two pair types are listed in the tables but excluded from the blocking count, in every variant including the approved one: a bright accent on Paper (it is a fill that carries Ink text on top, never text itself) and Rule on Paper (a hairline held to 3:1 stops being a hairline). Everything else is counted.

## Recommendation — Variant ${RECOMMENDED}

**Take A (Oxide, Paper-first).** Reasons, in order:

1. **It attacks the strongest cluster marker first — the surface.** Cluster 1 is defined by a near-black page. Flipping the primary surface to Paper removes the silhouette before any hue argument is needed, and it costs nothing conceptually: "laboratory journal" is a paper object, not a terminal.
2. **It keeps the mark green.** Signal stays in the green family, so recognisability against the approved palette survives. The change is one of chroma and lightness, not identity.
3. **It de-neons the accent measurably, and keeps it strong where it is actually used.** Signal drops chroma from C ${CURRENT.accent.oklch.C} to C ${A.accent.oklch.C} and lightness from L ${CURRENT.accent.oklch.L} to L ${A.accent.oklch.L}. On Ink it still returns ${r2(contrast(A.accent.hex, A.ink.hex)).toFixed(2)}:1, far above any threshold. It does **not** fix the colour mark on Paper — that pair moves only from ${r2(contrast(CURRENT.accent.hex, CURRENT.paper.hex)).toFixed(2)}:1 to ${r2(contrast(A.accent.hex, A.paper.hex)).toFixed(2)}:1, so the monochrome Ink mark stays mandatory on light surfaces. What A fixes is the secondary-text colour: Graphite goes from ${r2(contrast(CURRENT.muted.hex, CURRENT.paper.hex)).toFixed(2)}:1 (below the 4.5:1 text threshold in the approved palette) to ${r2(contrast(A.muted.hex, A.paper.hex)).toFixed(2)}:1.
4. **Two accents plus structure.** Blueprint gives diagrams a voice that is neither Signal nor Oxide, which is what stops a page from reading as "one bright thing on black".
5. **It is the smallest move that works.** B keeps the dark surface, so it only argues with the cluster by hue. C is a genuine redesign of the mark's colour and was not asked for.

Variant B is the fallback if the Ink-first surface turns out to be non-negotiable for Reel covers. Variant C is documented so the direction is on record, not proposed.

## Risks

- **Every existing Ink-background template must be re-cut for Paper.** This is the real cost of A and it is a production cost, not a design one.
- **Signal on Paper is a fill colour, not a text colour.** At ${r2(contrast(A.accent.hex, A.paper.hex)).toFixed(2)}:1 it must always carry Ink text on top, never sit as text itself.
- **The mark loses its halation on dark.** Lime at L ${CURRENT.accent.oklch.L} glowed against Ink; Signal at L ${A.accent.oklch.L} does not. If that glow is what Max recognises the brand by, this is the thing he will object to.
- **Logo minimum size is NOT improved.** The colour mark against Paper is still effectively invisible (${r2(contrast(A.accent.hex, A.paper.hex)).toFixed(2)}:1). The 32 px minimum and the monochrome-Ink-on-Paper rule in \`brand/logo/clearspace.md\` both stand unchanged. If the colour mark is wanted on Paper at all, Signal has to drop to roughly L 0.60, which is a different proposal from this one.
- **Oxide sits close to Stamp in lightness** (L ${A.stamp.oklch.L} vs ${CURRENT.stamp.oklch.L}) but ${A.cluster.stampVsVermilion.dh}° off vermilion and at lower chroma, so on a phone at feed size it reads as a stamped brick red rather than a warning light. That is the intent, and it is also the thing most likely to be called "washed out". Its margin on Ink is ${r2(contrast(A.stamp.hex, A.ink.hex)).toFixed(2)}:1 — clears 3:1, but only just. Verify on a real device before approval; raising L to ~0.60 buys margin at the cost of moving back toward vermilion.
- **Instagram compression.** All numbers here are computed on clean sRGB. Instagram re-encodes; saturated reds and greens shift first. The swatch sheet PNG must be checked after a round-trip through the platform, not only in the browser.
- **The cluster list can change.** These distances are measured against the clusters documented today. If the published defaults move, the argument for these hues moves with them.
`;
writeFileSync(join(OUT, 'palette-options.md'), md);

/* ------------------------------------------------------------ HTML */

const HEADLINE = 'Your AI pilot failed for one reason';
const LABEL = 'M2 LAB / FIELD NOTE 014';

function cover(v, mode) {
  const bg = mode === 'dark' ? v.ink : v.paper;
  const fg = mode === 'dark' ? v.paper : v.ink;
  const acc = v.accent;
  const struct = v.structure || v.muted;
  const meta = mode === 'dark' ? (v.rule) : (v.muted || v.rule);
  return `<div class="cover" style="background:${bg.hex};color:${fg.hex}">
      <div class="lab" style="color:${acc.hex}">${LABEL}</div>
      <div class="hl">${HEADLINE}</div>
      <div class="ln" style="background:${struct.hex}"></div>
      <div class="meta" style="color:${meta.hex}">01 / 03 &nbsp;·&nbsp; ${mode.toUpperCase()} SURFACE</div>
      <div class="chips">
        <span class="chip keep" style="background:${acc.hex};color:${v.ink.hex}">KEEP</span>
        <span class="chip kill" style="border:4px solid ${v.stamp.hex};color:${mode === 'dark' ? v.stamp.hex : v.stamp.hex}">KILL</span>
        <span class="chip test" style="border:3px dashed ${struct.hex};color:${fg.hex}">TEST</span>
      </div>
    </div>`;
}

function column(v) {
  const sw = v.colors.map((c) => `<div class="sw"><i style="background:${c.hex}"></i><b>${c.name}</b><code>${c.hex}</code><s>L ${c.oklch.L} · C ${c.oklch.C} · h ${c.oklch.h}°</s></div>`).join('');
  const key = [
    ['Ink on Paper', contrast(v.ink.hex, v.paper.hex)],
    ['Paper on Ink', contrast(v.paper.hex, v.ink.hex)],
    [`${v.accent.name} on Ink`, contrast(v.accent.hex, v.ink.hex)],
    [`${v.accent.name} on Paper`, contrast(v.accent.hex, v.paper.hex)],
    [`${v.stamp.name} on Ink`, contrast(v.stamp.hex, v.ink.hex)],
    [`${v.stamp.name} on Paper`, contrast(v.stamp.hex, v.paper.hex)],
  ].map(([k, r]) => `<tr><td>${k}</td><td>${r.toFixed(2)}:1</td></tr>`).join('');
  const g = v.accent2 || v.accent;
  const cvdRow = (label, sHex, gHex, dL, ok) =>
    `<div class="cvdrow"><span>${label}</span><i style="background:${sHex}"></i><i style="background:${gHex}"></i>` +
    `<u>ΔL ${dL} ${ok ? '' : '— NOT separable'}</u></div>`;
  const cvd = `<div class="cvd"><h3>${v.stamp.name} / ${g.name} &nbsp;—&nbsp; MACHADO 2009</h3>` +
    cvdRow('normal', v.stamp.hex, g.hex, v.cvd.normal.dL, v.cvd.normal.dL >= DL_THRESHOLD) +
    cvdRow('deuteranopia', v.cvd.deuteranopia.stampSim, v.cvd.deuteranopia.accentSim, v.cvd.deuteranopia.dL, v.cvd.deuteranopia.separable) +
    cvdRow('protanopia', v.cvd.protanopia.stampSim, v.cvd.protanopia.accentSim, v.cvd.protanopia.dL, v.cvd.protanopia.separable) +
    `</div>`;
  return `<section>
    <h2>${v.name}${v.id === RECOMMENDED ? ' <em>— recommended</em>' : ''}</h2>
    <p class="th">${v.thesis}</p>
    <div class="sws">${sw}</div>
    ${cover(v, 'dark')}
    ${cover(v, 'light')}
    <table>${key}</table>
    ${cvd}
  </section>`;
}

const html = `<!doctype html>
<meta charset="utf-8">
<title>M2 Lab — palette spread</title>
<style>
  /* Real project faces, loaded from assets/fonts/woff2 relative to research/. */
  @font-face{font-family:"IBM Plex Sans Condensed";font-weight:700;font-style:normal;
    src:url("../assets/fonts/woff2/IBMPlexSansCondensed-Bold.woff2") format("woff2")}
  @font-face{font-family:"IBM Plex Mono";font-weight:500;font-style:normal;
    src:url("../assets/fonts/woff2/IBMPlexMono-Medium.woff2") format("woff2")}
  @font-face{font-family:"IBM Plex Mono";font-weight:700;font-style:normal;
    src:url("../assets/fonts/woff2/IBMPlexMono-Bold.woff2") format("woff2")}
  @font-face{font-family:"IBM Plex Sans";font-weight:400;font-style:normal;
    src:url("../assets/fonts/woff2/IBMPlexSans-Regular.woff2") format("woff2")}
  @font-face{font-family:"IBM Plex Sans";font-weight:700;font-style:normal;
    src:url("../assets/fonts/woff2/IBMPlexSans-Bold.woff2") format("woff2")}
  body{margin:0;padding:28px;background:#fff;color:#111;font:13px/1.4 "IBM Plex Sans",Helvetica,Arial,sans-serif}
  h1{font:700 20px/1.2 "IBM Plex Sans",Helvetica,Arial,sans-serif;margin:0 0 18px}
  .grid{display:flex;gap:24px;align-items:flex-start}
  section{width:412px}
  h2{font:700 15px/1.3 "IBM Plex Sans",Helvetica,Arial,sans-serif;margin:0 0 6px}
  h2 em{font-style:normal;color:#777}
  .th{margin:0 0 12px;color:#555;min-height:56px}
  .sws{margin-bottom:16px;min-height:292px}
  .sw{display:flex;align-items:center;gap:8px;padding:3px 0}
  .sw i{width:34px;height:34px;flex:0 0 34px;border:1px solid #ccc}
  .sw b{width:78px;font-weight:700}
  .sw code{width:74px;font:11px/1 Menlo,monospace}
  .sw s{text-decoration:none;font:10px/1 Menlo,monospace;color:#777}
  .cover{width:270px;height:480px;padding:22px;box-sizing:border-box;margin:0 0 16px;
    display:flex;flex-direction:column;position:relative;overflow:hidden}
  .lab{font:500 11px/1.2 "IBM Plex Mono",Menlo,monospace;letter-spacing:.12em}
  .hl{font:700 34px/1.02 "IBM Plex Sans Condensed","Arial Narrow",Arial,sans-serif;
    margin-top:16px;letter-spacing:-.01em}
  .ln{height:3px;width:100%;margin-top:16px}
  .meta{font:500 10px/1.2 "IBM Plex Mono",Menlo,monospace;letter-spacing:.1em;margin-top:auto}
  .chips{display:flex;gap:6px;margin-top:12px;flex-wrap:wrap}
  .chip{font:700 11px/1 "IBM Plex Mono",Menlo,monospace;letter-spacing:.08em;
    padding:8px 9px;display:inline-block}
  table{border-collapse:collapse;width:100%;font:11px/1.3 Menlo,monospace}
  td{border-top:1px solid #ddd;padding:3px 0}
  td+td{text-align:right}
  .cvd{margin-top:14px;border-top:1px solid #ddd;padding-top:10px}
  .cvd h3{font:700 11px/1.2 "IBM Plex Mono",Menlo,monospace;letter-spacing:.08em;margin:0 0 8px;color:#333}
  .cvdrow{display:flex;align-items:center;gap:6px;margin-bottom:5px;font:10px/1 Menlo,monospace;color:#666}
  .cvdrow span{width:74px;flex:0 0 74px}
  .cvdrow i{width:52px;height:26px;flex:0 0 52px;border:1px solid #ccc}
  .cvdrow u{text-decoration:none;margin-left:2px}
</style>
<h1>M2 Lab — palette spread. Current vs A / B / C. Reel cover 1080×1920 shown at 270×480.</h1>
<div class="grid">${VARIANTS.map(column).join('')}</div>
`;
writeFileSync(join(OUT, 'palette-sheet.html'), html);

/* ------------------------------------------------------------ stdout */

for (const v of VARIANTS) {
  console.log(`\n=== ${v.name}`);
  console.log(v.colors.map((c) => `${c.name.padEnd(10)} ${c.hex}  L ${c.oklch.L}  C ${c.oklch.C}  h ${c.oklch.h}`).join('\n'));
  console.log('blocking fails:', v.contrast.filter((p) => !p.pass && !p.byDesign).map((p) => `${p.pair}=${p.ratio}`).join(', ') || 'none');
  console.log('cvd deut sep:', v.cvd.deuteranopia.separable, 'prot sep:', v.cvd.protanopia.separable,
    '| dL', v.cvd.deuteranopia.dL, v.cvd.protanopia.dL);
  console.log('accent dh from acid:', v.cluster.accentVsAcidGreen.dh, '| stamp dh verm:', v.cluster.stampVsVermilion.dh,
    'terr:', v.cluster.stampVsTerracotta.dh, '| paper dE cream:', v.cluster.paperVsCream_dEok);
}
console.log('\nwritten: palette-options.json, palette-options.md, palette-sheet.html');
