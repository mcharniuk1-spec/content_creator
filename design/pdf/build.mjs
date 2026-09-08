#!/usr/bin/env node
/* M2 Lab brand book build.
   node pdf/build.mjs             assemble pdf/out/document.html, print the PDF, render proofs
   node pdf/build.mjs --html-only assemble only, no Chrome
   No dependencies. Node 18 or newer. */

import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync, statSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const PDF_DIR = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(PDF_DIR, "out");
const SHELL = join(PDF_DIR, "shell.html");
const DOC_HTML = join(OUT_DIR, "document.html");
const PROOF_HTML = join(OUT_DIR, "proof-section.html");
const PDF_OUT = join(OUT_DIR, "M2-Lab-Brandbook.pdf");
const PNG_COVER = join(OUT_DIR, "proof-cover.png");
const PNG_SECTION = join(OUT_DIR, "proof-section.png");
const PNG_PDF_P1 = join(OUT_DIR, "proof-pdf-page-1.png");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const htmlOnly = process.argv.includes("--html-only");
const log = (...a) => console.log(...a);

function readSections(part) {
  const dir = join(PDF_DIR, "sections", part);
  if (!existsSync(dir)) return { html: "", files: [] };
  const files = readdirSync(dir).filter((f) => f.endsWith(".html")).sort();
  const html = files
    .map((f) => `\n<!-- sections/${part}/${f} -->\n${readFileSync(join(dir, f), "utf8").trim()}\n`)
    .join("\n");
  return { html, files };
}

/* ---------- assemble ---------- */

if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const shell = readFileSync(SHELL, "utf8");
const brand = readSections("brand");
const system = readSections("system");

for (const [part, set] of [["brand", brand], ["system", system]]) {
  if (!shell.includes(`<!-- SECTIONS:${part} -->`)) {
    console.error(`shell.html has no <!-- SECTIONS:${part} --> placeholder`);
    process.exit(1);
  }
  log(`sections/${part}: ${set.files.length} file(s) ${set.files.join(", ") || "(none)"}`);
}

const doc = shell
  .replace("<!-- SECTIONS:brand -->", brand.html)
  .replace("<!-- SECTIONS:system -->", system.html);

writeFileSync(DOC_HTML, doc, "utf8");
log(`wrote ${DOC_HTML} (${(statSync(DOC_HTML).size / 1024).toFixed(1)} kB)`);

/* A single-page file so the component proof can be screenshot without scrolling. */
const head = doc.match(/<head[\s\S]*?<\/head>/i)?.[0] ?? "";
const firstSection = (brand.html.match(/<section[\s\S]*?<\/section>/i) ?? [])[0] ?? "";
const furniture = doc.match(/<script>[\s\S]*?<\/script>/i)?.[0] ?? "";
writeFileSync(
  PROOF_HTML,
  `<!DOCTYPE html>\n<html lang="en">\n${head}\n<body style="padding:0">\n${firstSection}\n${furniture}\n</body>\n</html>\n`,
  "utf8"
);

if (htmlOnly) {
  log("--html-only: stopping before Chrome.");
  process.exit(0);
}

/* ---------- print ---------- */

if (!existsSync(CHROME)) {
  console.error(`Chrome not found at ${CHROME}. Install it, or run with --html-only.`);
  process.exit(1);
}

function chrome(args, label) {
  try {
    execFileSync(CHROME, args, { stdio: ["ignore", "pipe", "pipe"], timeout: 120000 });
    return true;
  } catch (e) {
    console.error(`${label} failed: ${e.message}`);
    if (e.stderr) console.error(String(e.stderr).slice(0, 800));
    return false;
  }
}

const fileUrl = (p) => "file://" + resolve(p);

chrome(
  ["--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
   `--print-to-pdf=${PDF_OUT}`, "--virtual-time-budget=10000", fileUrl(DOC_HTML)],
  "print-to-pdf"
);

if (!existsSync(PDF_OUT)) {
  console.error("PDF was not produced.");
  process.exit(1);
}

/* ---------- report ---------- */

function pageCount(pdfPath) {
  try {
    const out = execFileSync("mdls", ["-name", "kMDItemNumberOfPages", "-raw", pdfPath], { encoding: "utf8" }).trim();
    const n = parseInt(out, 10);
    if (Number.isFinite(n) && n > 0) return { n, how: "mdls" };
  } catch {}
  const buf = readFileSync(pdfPath).toString("latin1");
  const marks = buf.match(/\/Type\s*\/Page(?![s])/g);
  if (marks) return { n: marks.length, how: "/Type /Page count" };
  const count = buf.match(/\/Count\s+(\d+)/);
  if (count) return { n: parseInt(count[1], 10), how: "/Count" };
  return { n: 0, how: "unknown" };
}

const size = statSync(PDF_OUT).size;
const pages = pageCount(PDF_OUT);
log(`PDF   ${PDF_OUT}`);
log(`size  ${(size / 1024).toFixed(1)} kB`);
log(`pages ${pages.n} (via ${pages.how})`);

/* ---------- proofs ---------- */

chrome(
  ["--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
   `--screenshot=${PNG_COVER}`, "--window-size=1400,990",
   "--virtual-time-budget=10000", fileUrl(DOC_HTML)],
  "screenshot (cover)"
);
chrome(
  ["--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
   `--screenshot=${PNG_SECTION}`, "--window-size=1400,990",
   "--virtual-time-budget=10000", fileUrl(PROOF_HTML)],
  "screenshot (sample section)"
);

let pdfPng = null;
function has(bin) {
  try { execFileSync("which", [bin], { stdio: "ignore" }); return true; } catch { return false; }
}
if (has("pdftoppm")) {
  try {
    execFileSync("pdftoppm", ["-png", "-r", "120", "-f", "1", "-l", "1", PDF_OUT, PNG_PDF_P1.replace(/\.png$/, "")]);
    pdfPng = PNG_PDF_P1.replace(/\.png$/, "") + "-1.png";
  } catch (e) { console.error("pdftoppm failed: " + e.message); }
} else if (has("sips")) {
  try {
    execFileSync("sips", ["-s", "format", "png", PDF_OUT, "--out", PNG_PDF_P1], { stdio: "ignore" });
    pdfPng = PNG_PDF_P1;
  } catch (e) { console.error("sips failed: " + e.message); }
} else {
  log("no pdftoppm and no sips: skipping PDF page 1 raster");
}

for (const p of [PNG_COVER, PNG_SECTION, pdfPng]) {
  if (p && existsSync(p)) log(`png   ${p} (${(statSync(p).size / 1024).toFixed(1)} kB)`);
}

/* ---------- font embedding ---------- */

try {
  const strings = execFileSync("bash", ["-lc", `strings "${PDF_OUT}" | grep -i "IBMPlex" | sort -u | head`], { encoding: "utf8" });
  log("embedded font names:");
  log(strings.trim() || "  none found, check the @font-face paths in pdf/print.css");
} catch {
  log("could not run strings on the PDF");
}
