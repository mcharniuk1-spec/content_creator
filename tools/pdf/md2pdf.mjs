#!/usr/bin/env node
// md2pdf.mjs — dependency-free markdown -> A4 portrait PDF, M2 Lab report style.
//
// Usage:
//   node md2pdf.mjs --title "..." --subtitle "..." --date "..." --out /abs/path.pdf file1.md file2.md ...
//   node md2pdf.mjs ... --no-toc          (skip the generated table of contents)
//
// Forked from audit-2026-09-08/report/md2pdf.mjs (kept there, untouched) for
// tools/pdf — the shared PDF pipeline owned by engine/pdf_build.py. Adds, on
// top of the original hand-written markdown -> HTML -> Chrome print flow:
//
//   - images `![caption](path/to.png)` embedded as base64 data: URIs (so the
//     PDF is fully self-contained), scaled to page width, caption below;
//   - a `::grid a.png|b.png|c.png::` line -> a 3-column image grid, each cell
//     captioned with its filename (storyboard/frame contact sheets);
//   - wide tables (>8 columns) get a shrink class so they don't overflow the
//     page — see chooseTableClass();
//   - a generated table of contents on page 2, built from `# ` and `## `
//     headings, ordered list, no page numbers (Chrome print has none, see
//     below);
//   - a footer with the document title and date on every page.
//
// No npm packages: markdown parsing is hand-written below, and PDF rendering
// is headless Chrome via the CLI (Node only orchestrates it with execFile).

import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const MIME_BY_EXT = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
};

// ---------------------------------------------------------------- CLI args

function parseArgs(argv) {
  const opts = { title: "", subtitle: "", date: "", out: "", toc: true, files: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--title") opts.title = argv[++i] ?? "";
    else if (a === "--subtitle") opts.subtitle = argv[++i] ?? "";
    else if (a === "--date") opts.date = argv[++i] ?? "";
    else if (a === "--out") opts.out = argv[++i] ?? "";
    else if (a === "--no-toc") opts.toc = false;
    else if (a === "--toc") opts.toc = true;
    else if (a.startsWith("--")) throw new Error(`Unknown flag: ${a}`);
    else opts.files.push(a);
  }
  if (!opts.out) throw new Error("--out /abs/path.pdf is required");
  if (opts.files.length === 0) throw new Error("at least one markdown file is required");
  return opts;
}

// ------------------------------------------------------------- HTML escape

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// -------------------------------------------------------- image embedding
// Resolves a markdown image path (relative to the .md file it came from)
// to a base64 data: URI, so the finished PDF carries no external file
// references — it stays byte-identical and openable without the repo
// alongside it. Missing files degrade to a visible placeholder rather than
// throwing, so one bad chart reference doesn't sink the whole build.

function embedImageDataUri(imgPath, baseDir) {
  // Relative paths resolve against the .md file's directory first, then against the
  // current working directory (repo root), so chapters can reference `reports/charts/x.png`.
  let abs = path.isAbsolute(imgPath) ? imgPath : path.resolve(baseDir, imgPath);
  if (!existsSync(abs) && !path.isAbsolute(imgPath)) abs = path.resolve(process.cwd(), imgPath);
  const ext = path.extname(abs).toLowerCase();
  const mime = MIME_BY_EXT[ext] || "application/octet-stream";
  if (!existsSync(abs)) return null;
  const buf = readFileSync(abs);
  return `data:${mime};base64,${buf.toString("base64")}`;
}

// ----------------------------------------------------------- inline markup
// Runs on already HTML-escaped text. Order matters: code spans first (so
// their contents are protected from bold/italic/link parsing), then links,
// then bold, then italic.

function renderInline(text) {
  const placeholders = [];
  const stash = (html) => {
    placeholders.push(html);
    return `${placeholders.length - 1}`;
  };

  // inline code `code`
  text = text.replace(/`([^`]+)`/g, (_, code) => stash(`<code>${code}</code>`));

  // links [text](url)
  text = text.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, url) =>
    stash(`<a href="${url}">${label}</a><span class="link-url">(${url})</span>`)
  );

  // bold **text**
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  // italic *text* (single asterisk, not already consumed by bold)
  text = text.replace(/\*([^*]+)\*/g, "<em>$1</em>");

  // restore stashed fragments
  text = text.replace(/(\d+)/g, (_, i) => placeholders[Number(i)]);

  return text;
}

// ------------------------------------------------------------- list parser
// Consumes a run of list lines (possibly mixed ordered/unordered, nested by
// two-space indents) starting at index i. Returns { html, next }.

function listItemIndent(line) {
  const m = line.match(/^( *)([-*]|\d+\.)\s+(.*)$/);
  if (!m) return null;
  return { indent: m[1].length, ordered: /\d+\./.test(m[2]), text: m[3] };
}

function parseList(lines, i) {
  const first = listItemIndent(lines[i]);
  const baseIndent = first.indent;
  const tag = first.ordered ? "ol" : "ul";
  let html = `<${tag}>`;
  while (i < lines.length) {
    const item = listItemIndent(lines[i]);
    if (!item || item.indent < baseIndent) break;
    if (item.indent > baseIndent) {
      // nested list: recurse
      const nested = parseList(lines, i);
      html += nested.html;
      i = nested.next;
      continue;
    }
    // same-level item: gather this line, then check for a deeper nested
    // list immediately following before closing the <li>
    // lazy continuation: following non-empty lines that are not list items,
    // headings, tables or fences belong to this item (hard-wrapped markdown)
    let text = item.text;
    i++;
    while (i < lines.length && lines[i].trim() !== "" && !listItemIndent(lines[i])
      && !/^(#{1,4})\s/.test(lines[i]) && !/^```/.test(lines[i]) && !lines[i].includes("|")
      && !/^(-{3,}|\*{3,}|_{3,})\s*$/.test(lines[i].trim())) {
      text += " " + lines[i].trim();
      i++;
    }
    let itemHtml = renderInline(text);
    if (i < lines.length) {
      const peek = listItemIndent(lines[i]);
      if (peek && peek.indent > baseIndent) {
        const nested = parseList(lines, i);
        itemHtml += nested.html;
        i = nested.next;
      }
    }
    html += `<li>${itemHtml}</li>`;
  }
  html += `</${tag}>`;
  return { html, next: i };
}

// ------------------------------------------------------------ table parser

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/.test(line) && line.includes("-");
}

function splitRow(line) {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  return s.split("|").map((c) => c.trim());
}

// Wide tables (many columns) overflow an A4 portrait content box at the
// base cell font size. Rather than letting Chrome clip or wrap into an
// unreadable mess, a table with more than 8 columns gets a shrink class:
// CSS (report.css) reduces font-size and cell padding in three steps so
// 9-12 columns, 13-16, and 17+ each get progressively smaller type. This
// is horizontal *scaling by density*, not JS layout math — Chrome's own
// table algorithm still does the column sizing, just at a smaller base
// size, and table-layout:auto plus word-break in report.css handles long
// cell content wrapping instead of overflowing.
function chooseTableClass(colCount) {
  if (colCount > 16) return "table-wide-3";
  if (colCount > 12) return "table-wide-2";
  if (colCount > 8) return "table-wide-1";
  return "";
}

function parseTable(lines, i) {
  const header = splitRow(lines[i]);
  i += 2; // skip header + separator
  const rows = [];
  while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
    rows.push(splitRow(lines[i]));
    i++;
  }
  const cls = chooseTableClass(header.length);
  const classAttr = cls ? ` class="${cls}"` : "";
  let html = `<div class="table-wrap"><table${classAttr}><thead><tr>`;
  for (const h of header) html += `<th>${renderInline(h)}</th>`;
  html += "</tr></thead><tbody>";
  for (const r of rows) {
    html += "<tr>";
    for (const c of r) html += `<td>${renderInline(c)}</td>`;
    html += "</tr>";
  }
  html += "</tbody></table></div>";
  return { html, next: i };
}

// -------------------------------------------------------------- md -> html
// baseDir is the directory of the source .md file, used to resolve relative
// image paths for embedding.

function mdToHtml(md, baseDir, headingSeen) {
  const rawLines = md.replace(/\r\n/g, "\n").split("\n");
  let html = "";
  let i = 0;

  // Two passes are awkward here because escaping happens per-raw-line but
  // image/grid syntax needs the *raw* (unescaped) path before HTML-escaping
  // mangles it (e.g. an `&` in a filename). So detect image/grid lines off
  // the raw text first, everything else off the escaped line as before.

  while (i < rawLines.length) {
    const raw = rawLines[i];

    if (raw.trim() === "") { i++; continue; }

    // storyboard grid: ::grid a.png|b.png|c.png::
    const gridMatch = raw.trim().match(/^::grid\s+(.+?)\s*::$/);
    if (gridMatch) {
      const paths = gridMatch[1].split("|").map((p) => p.trim()).filter(Boolean);
      html += renderGrid(paths, baseDir);
      i++;
      continue;
    }

    // standalone image line: ![caption](path)
    const imgMatch = raw.trim().match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (imgMatch) {
      html += renderFigure(imgMatch[1], imgMatch[2], baseDir);
      i++;
      continue;
    }

    const line = escapeHtml(raw);

    // fenced code block
    const fence = line.match(/^```/);
    if (fence) {
      const buf = [];
      i++;
      while (i < rawLines.length && !/^```/.test(rawLines[i])) { buf.push(escapeHtml(rawLines[i])); i++; }
      i++; // closing fence
      html += `<pre><code>${buf.join("\n")}</code></pre>\n`;
      continue;
    }

    // headings — ids only on h1/h2 (the levels the TOC links to); the same
    // dedupeSlug() sequence, walked in the same file order, is also run by
    // collectHeadings() for the TOC itself, so the two stay in sync without
    // sharing state directly (see dedupeSlug doc comment).
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const level = h[1].length;
      if (level <= 2) {
        const slug = dedupeSlug(headingSeen, slugify(h[2]));
        html += `<h${level} id="${slug}">${renderInline(h[2])}</h${level}>\n`;
      } else {
        html += `<h${level}>${renderInline(h[2])}</h${level}>\n`;
      }
      i++;
      continue;
    }

    // horizontal rule (not a table separator, checked before table/list)
    if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(line.trim())) {
      html += `<hr class="rule-line">\n`;
      i++;
      continue;
    }

    // table: header row with pipes, next line is a separator row
    if (line.includes("|") && i + 1 < rawLines.length && isTableSeparator(escapeHtml(rawLines[i + 1]))) {
      // re-derive the escaped-lines slice starting here for the table parser
      const escapedFrom = rawLines.slice(i).map(escapeHtml);
      const t = parseTable(escapedFrom, 0);
      html += t.html + "\n";
      i += t.next;
      continue;
    }

    // blockquote — lines are already HTML-escaped at this point, so the
    // leading ">" markdown marker is now the entity "&gt;"; match that
    // instead of a literal ">" (a literal ">" never survives escapeHtml).
    if (/^&gt;\s?/.test(line)) {
      const buf = [];
      while (i < rawLines.length && /^&gt;\s?/.test(escapeHtml(rawLines[i]))) {
        buf.push(escapeHtml(rawLines[i]).replace(/^&gt;\s?/, ""));
        i++;
      }
      html += `<blockquote><p>${renderInline(buf.join(" "))}</p></blockquote>\n`;
      continue;
    }

    // list (ordered or unordered, nested by two spaces)
    if (listItemIndent(line)) {
      const escapedFrom = rawLines.slice(i).map(escapeHtml);
      const l = parseList(escapedFrom, 0);
      html += l.html + "\n";
      i += l.next;
      continue;
    }

    // paragraph: gather until blank line or a line that starts a new block
    const buf = [line];
    i++;
    while (
      i < rawLines.length &&
      rawLines[i].trim() !== "" &&
      !/^#{1,4}\s/.test(rawLines[i]) &&
      !/^```/.test(rawLines[i]) &&
      !/^&gt;\s?/.test(escapeHtml(rawLines[i])) &&
      !listItemIndent(escapeHtml(rawLines[i])) &&
      !/^(-{3,}|\*{3,}|_{3,})\s*$/.test(rawLines[i].trim()) &&
      !/^::grid\s+.+::$/.test(rawLines[i].trim()) &&
      !/^!\[([^\]]*)\]\(([^)]+)\)$/.test(rawLines[i].trim())
    ) {
      buf.push(escapeHtml(rawLines[i]));
      i++;
    }
    html += `<p>${renderInline(buf.join(" "))}</p>\n`;
  }

  return html;
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/<[^>]+>/g, "")
    .replace(/&[a-z]+;/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    || "section";
}

// A 38-section report repeats heading text ("Overview", "Findings", ...)
// across chapters; without dedup every repeat would collide on the same
// #id and every TOC link after the first would jump to the wrong place.
// `seen` is a plain object the caller owns — collectHeadings() (building
// the TOC) and mdToHtml() (writing the h1/h2 id attributes) each keep
// their own `seen` map, but because both walk the same heading sequence
// (h1/h2 only, same files, same order) with this same function, they
// independently arrive at identical slugs without needing to share state.
function dedupeSlug(seen, base) {
  const n = (seen[base] = (seen[base] || 0) + 1);
  return n === 1 ? base : `${base}-${n}`;
}

// A single figure: image scaled to page width, caption below. Data-URI
// embedding keeps the PDF self-contained (see embedImageDataUri). A file
// that can't be found renders a visible placeholder box instead of a
// silently-broken <img> or a thrown build error.
function renderFigure(caption, imgPath, baseDir) {
  const uri = embedImageDataUri(imgPath, baseDir);
  const capHtml = caption ? `<figcaption>${renderInline(escapeHtml(caption))}</figcaption>` : "";
  if (!uri) {
    return `<figure class="figure"><div class="figure__missing">[MISSING IMAGE: ${escapeHtml(imgPath)}]</div>${capHtml}</figure>\n`;
  }
  return `<figure class="figure"><img src="${uri}" alt="${escapeHtml(caption || "")}" />${capHtml}</figure>\n`;
}

// Storyboard grid: fixed 3 columns, each cell captioned with its own
// filename (the storyboard convention: frame filenames double as the
// timecode/shot label). Rows wrap automatically via CSS grid.
function renderGrid(paths, baseDir) {
  let html = `<div class="grid grid-3">`;
  for (const p of paths) {
    const uri = embedImageDataUri(p, baseDir);
    const name = escapeHtml(path.basename(p));
    if (!uri) {
      html += `<figure class="grid__cell"><div class="figure__missing">[MISSING: ${escapeHtml(p)}]</div><figcaption>${name}</figcaption></figure>`;
    } else {
      html += `<figure class="grid__cell"><img src="${uri}" alt="${name}" /><figcaption>${name}</figcaption></figure>`;
    }
  }
  html += `</div>\n`;
  return html;
}

// ------------------------------------------------------- table of contents
// Built from `# ` and `## ` headings across all chapter files, in document
// order, as a single ordered list (H2s nested under their H1). No page
// numbers: Chrome's headless print-to-pdf has no CSS Paged-Media counters
// (see report.css / README for the full story), so a TOC entry can only
// link to its heading's #anchor — useful on screen, inert on paper, but
// still the accurate, honest thing to generate.

function collectHeadings(mdFiles) {
  const headings = [];
  const seen = {};
  for (const file of mdFiles) {
    const md = readFileSync(file, "utf8").replace(/\r\n/g, "\n");
    let inFence = false;
    for (const line of md.split("\n")) {
      if (/^```/.test(line)) { inFence = !inFence; continue; }
      if (inFence) continue;
      const h = line.match(/^(#{1,2})\s+(.*)$/);
      if (!h) continue;
      const level = h[1].length;
      const text = h[2].trim();
      headings.push({ level, text, slug: dedupeSlug(seen, slugify(text)) });
    }
  }
  return headings;
}

function renderToc(headings) {
  if (headings.length === 0) return "";
  let html = `<section class="toc">\n<h2 class="toc__title">Table of contents</h2>\n<ol class="toc__list">\n`;
  let openSub = false;
  for (const h of headings) {
    if (h.level === 1) {
      if (openSub) { html += `</ol></li>\n`; openSub = false; }
      html += `<li class="toc__h1"><a href="#${h.slug}">${renderInline(escapeHtml(h.text))}</a>`;
    } else {
      if (!openSub) { html += `<ol class="toc__sub">`; openSub = true; }
      html += `<li class="toc__h2"><a href="#${h.slug}">${renderInline(escapeHtml(h.text))}</a></li>`;
    }
    if (h.level === 1) html += `</li>\n`;
  }
  if (openSub) html += `</ol>\n`;
  html += `</ol>\n</section>\n`;
  return html;
}

// --------------------------------------------------------------- assembly

function buildDocument(opts) {
  const markPath = path.join(__dirname, "mark", "m2-mark-color.svg");
  const markUrl = `file://${markPath}`;

  let body = `
  <section class="cover">
    <img class="cover__mark" src="${markUrl}" alt="" />
    <div class="cover__title">${escapeHtml(opts.title)}</div>
    ${opts.subtitle ? `<p class="cover__subtitle">${escapeHtml(opts.subtitle)}</p>` : ""}
    <div class="cover__date">${escapeHtml(opts.date)}</div>
  </section>
`;

  if (opts.toc) {
    const headings = collectHeadings(opts.files);
    body += renderToc(headings);
  }

  // One shared seen-map across every file's h1/h2 ids, in file order — see
  // dedupeSlug()'s doc comment for why this stays in sync with the TOC's
  // own (separate) seen-map without the two sharing state directly.
  const headingSeen = {};
  opts.files.forEach((file) => {
    const md = readFileSync(file, "utf8");
    const baseDir = path.dirname(path.resolve(file));
    const chapterHtml = mdToHtml(md, baseDir, headingSeen);
    body += `
  <section class="chapter">
    ${chapterHtml}
  </section>
`;
  });

  // Running footer: title (left) + date (right), constant on every page.
  // See report.css for why this is the only position:fixed element allowed
  // in the whole document, and why it cannot carry a true page number.
  body += `
  <div class="page-footer">
    <span class="page-footer__title">${escapeHtml(opts.title)}</span>
    <span class="page-footer__date">${escapeHtml(opts.date)}</span>
  </div>
`;

  const cssPath = path.join(__dirname, "report.css");
  const cssUrl = `file://${cssPath}`;

  return `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(opts.title)}</title>
<link rel="stylesheet" href="${cssUrl}" />
</head>
<body>
${body}
</body>
</html>
`;
}

// ------------------------------------------------------------- page count

function countPdfPages(pdfPath) {
  try {
    const out = execFileSync("mdls", ["-name", "kMDItemNumberOfPages", pdfPath], { encoding: "utf8" });
    const m = out.match(/=\s*(\d+)/);
    if (m) return { count: Number(m[1]), method: "mdls" };
  } catch { /* fall through to byte-scan fallback */ }

  const buf = readFileSync(pdfPath);
  const needle = Buffer.from("/Type /Page");
  const needleTight = Buffer.from("/Type/Page");
  let count = 0;
  for (const n of [needle, needleTight]) {
    let idx = 0;
    while ((idx = buf.indexOf(n, idx)) !== -1) {
      // exclude "/Type /Pages" (the tree root), only count leaf "/Page"
      const after = buf.slice(idx + n.length, idx + n.length + 1).toString("latin1");
      if (after !== "s") count++;
      idx += n.length;
    }
  }
  return { count, method: "byte-scan fallback" };
}

// ------------------------------------------------------------------- main

function main() {
  const opts = parseArgs(process.argv.slice(2));

  const outDir = path.join(__dirname, "out");
  if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

  const baseName = path.basename(opts.out, path.extname(opts.out));
  const htmlPath = path.join(outDir, `${baseName}.html`);

  const html = buildDocument(opts);
  writeFileSync(htmlPath, html, "utf8");

  const outAbs = path.isAbsolute(opts.out) ? opts.out : path.resolve(process.cwd(), opts.out);
  mkdirSync(path.dirname(outAbs), { recursive: true });

  execFileSync(CHROME, [
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    `--print-to-pdf=${outAbs}`,
    "--virtual-time-budget=10000",
    `file://${htmlPath}`,
  ], { stdio: "inherit" });

  if (!existsSync(outAbs) || statSync(outAbs).size === 0) {
    throw new Error(`Chrome did not produce a PDF at ${outAbs}`);
  }

  const { count, method } = countPdfPages(outAbs);
  console.log(`HTML:  ${htmlPath}`);
  console.log(`PDF:   ${outAbs}`);
  console.log(`Pages: ${count} (via ${method})`);
}

main();
