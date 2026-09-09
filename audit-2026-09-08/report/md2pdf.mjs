#!/usr/bin/env node
// md2pdf.mjs — dependency-free markdown -> A4 portrait PDF, M2 Lab report style.
//
// Usage:
//   node md2pdf.mjs --title "..." --subtitle "..." --date "..." --out /abs/path.pdf file1.md file2.md ...
//
// Each markdown file becomes one chapter starting on a new page. No npm
// packages: markdown parsing is hand-written below, and PDF rendering is
// headless Chrome via the CLI (Node only orchestrates it with execFile).

import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

// ---------------------------------------------------------------- CLI args

function parseArgs(argv) {
  const opts = { title: "", subtitle: "", date: "", out: "", files: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--title") opts.title = argv[++i] ?? "";
    else if (a === "--subtitle") opts.subtitle = argv[++i] ?? "";
    else if (a === "--date") opts.date = argv[++i] ?? "";
    else if (a === "--out") opts.out = argv[++i] ?? "";
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

// ----------------------------------------------------------- inline markup
// Runs on already HTML-escaped text. Order matters: code spans first (so
// their contents are protected from bold/italic/link parsing), then links,
// then bold, then italic.

function renderInline(text) {
  const placeholders = [];
  const stash = (html) => {
    placeholders.push(html);
    return `\uE000${placeholders.length - 1}\uE001`;
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
  text = text.replace(/\uE000(\d+)\uE001/g, (_, i) => placeholders[Number(i)]);

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

function parseTable(lines, i) {
  const header = splitRow(lines[i]);
  i += 2; // skip header + separator
  const rows = [];
  while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
    rows.push(splitRow(lines[i]));
    i++;
  }
  let html = "<table><thead><tr>";
  for (const h of header) html += `<th>${renderInline(h)}</th>`;
  html += "</tr></thead><tbody>";
  for (const r of rows) {
    html += "<tr>";
    for (const c of r) html += `<td>${renderInline(c)}</td>`;
    html += "</tr>";
  }
  html += "</tbody></table>";
  return { html, next: i };
}

// -------------------------------------------------------------- md -> html

function mdToHtml(md) {
  const rawLines = md.replace(/\r\n/g, "\n").split("\n");
  const lines = rawLines.map(escapeHtml);
  let html = "";
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === "") { i++; continue; }

    // fenced code block
    const fence = line.match(/^```/);
    if (fence) {
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i++; }
      i++; // closing fence
      html += `<pre><code>${buf.join("\n")}</code></pre>\n`;
      continue;
    }

    // headings
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const level = h[1].length;
      html += `<h${level}>${renderInline(h[2])}</h${level}>\n`;
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
    if (line.includes("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const t = parseTable(lines, i);
      html += t.html + "\n";
      i = t.next;
      continue;
    }

    // blockquote — lines are already HTML-escaped at this point, so the
    // leading ">" markdown marker is now the entity "&gt;"; match that
    // instead of a literal ">" (a literal ">" never survives escapeHtml).
    if (/^&gt;\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^&gt;\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^&gt;\s?/, ""));
        i++;
      }
      html += `<blockquote><p>${renderInline(buf.join(" "))}</p></blockquote>\n`;
      continue;
    }

    // list (ordered or unordered, nested by two spaces)
    if (listItemIndent(line)) {
      const l = parseList(lines, i);
      html += l.html + "\n";
      i = l.next;
      continue;
    }

    // paragraph: gather until blank line or a line that starts a new block
    const buf = [line];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^#{1,4}\s/.test(lines[i]) &&
      !/^```/.test(lines[i]) &&
      !/^&gt;\s?/.test(lines[i]) &&
      !listItemIndent(lines[i]) &&
      !/^(-{3,}|\*{3,}|_{3,})\s*$/.test(lines[i].trim())
    ) {
      buf.push(lines[i]);
      i++;
    }
    html += `<p>${renderInline(buf.join(" "))}</p>\n`;
  }

  return html;
}

// --------------------------------------------------------------- assembly

function buildDocument(opts) {
  const total = opts.files.length;

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

  opts.files.forEach((file) => {
    const md = readFileSync(file, "utf8");
    const chapterHtml = mdToHtml(md);
    body += `
  <section class="chapter">
    ${chapterHtml}
  </section>
`;
  });

  // Exactly one running footer for the whole document. Chrome repeats
  // every position:fixed element on every printed page with no scoping to
  // the section containing it — one footer per chapter was tried and each
  // instance rendered stacked on every page, garbling the text (see
  // report.css). So the folio can only carry constant, document-wide
  // information: the chapter count, not a true or per-chapter page number.
  const chapterWord = total === 1 ? "chapter" : "chapters";
  body += `
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
