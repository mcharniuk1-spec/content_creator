#!/usr/bin/env python3
"""Python entry point for tools/pdf/md2pdf.mjs — the dependency-free Markdown ->
A4 portrait PDF pipeline (Node stdlib + headless Chrome, no npm packages).

This module owns none of the rendering itself: it shells out to
`node tools/pdf/md2pdf.mjs ...` and wraps the result in a small, stable
Python contract so other engine modules (report writers, card-book
assembly) don't need to know the CLI's flag names or parse its stdout.

    from engine.pdf_build import build
    result = build(
        ['reports/audit/00-requirements-checklist.md', 'reports/audit/02-data-inventory.md'],
        out_pdf='/tmp/sample.pdf',
        title='M2Radar Audit Sample',
        subtitle='Requirements + data inventory',
    )
    # {'ok': True, 'pages': 7, 'bytes': 812345, 'out': '/tmp/sample.pdf'}

CLI:

    python3 -m engine.pdf_build --title "..." --subtitle "..." --date "..." \\
        --out /abs/path.pdf file1.md file2.md [--no-toc]

Page count is a byte scan of the finished PDF for literal `/Type /Page`
markers (excluding `/Type /Pages`, the tree root) -- exact and independent
of Spotlight/`mdls` indexing, which is not guaranteed to be available or
up to date on this machine (see tools/pdf/README.md).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MD2PDF = os.path.join(ROOT, 'tools', 'pdf', 'md2pdf.mjs')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


class PdfBuildError(RuntimeError):
    """Raised when node/Chrome fail or the PDF was not produced."""


def chrome_available() -> bool:
    """True if the headless Chrome binary md2pdf.mjs depends on exists.

    Used by tests/test_pdf_build.py to skip (with reason) on a machine
    that lacks it, per the project's no-network / real-Chrome constraint.
    """
    return os.path.exists(CHROME)


def count_pdf_pages(pdf_path: str) -> int:
    """Exact page count via a byte scan for `/Type /Page` (not `/Type /Pages`).

    Mirrors the byte-scan fallback already used inside md2pdf.mjs, done
    independently here in Python so engine.pdf_build's contract does not
    depend on Node's stdout formatting.
    """
    with open(pdf_path, 'rb') as fh:
        data = fh.read()
    count = 0
    for needle in (b'/Type /Page', b'/Type/Page'):
        idx = 0
        while True:
            idx = data.find(needle, idx)
            if idx == -1:
                break
            after = data[idx + len(needle):idx + len(needle) + 1]
            if after != b's':  # exclude "/Type /Pages" (the tree root)
                count += 1
            idx += len(needle)
    return count


def build(
    md_files: list,
    out_pdf: str,
    title: str,
    subtitle: str = '',
    date: str = None,
    toc: bool = True,
) -> dict:
    """Build a PDF from one or more markdown files via tools/pdf/md2pdf.mjs.

    Each file in `md_files` becomes one chapter, starting on a new page, in
    the order given. Returns
        {ok: bool, pages: int, bytes: int, out: str}
    on success. Raises PdfBuildError on any failure (missing input file,
    Chrome missing, node/Chrome exiting non-zero, or no PDF produced).
    """
    if not md_files:
        raise PdfBuildError('build() needs at least one markdown file')
    for f in md_files:
        if not os.path.exists(f):
            raise PdfBuildError(f'markdown file not found: {f}')
    if not chrome_available():
        raise PdfBuildError(f'headless Chrome not found at {CHROME}')

    out_abs = os.path.abspath(out_pdf)
    os.makedirs(os.path.dirname(out_abs) or '.', exist_ok=True)

    resolved_date = date if date is not None else datetime.date.today().isoformat()

    cmd = [
        'node', MD2PDF,
        '--title', title,
        '--subtitle', subtitle,
        '--date', resolved_date,
        '--out', out_abs,
    ]
    if not toc:
        cmd.append('--no-toc')
    cmd.extend(os.path.abspath(f) for f in md_files)

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise PdfBuildError(
            f'md2pdf.mjs exited {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}'
        )
    if not os.path.exists(out_abs) or os.path.getsize(out_abs) == 0:
        raise PdfBuildError(f'no PDF produced at {out_abs}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}')

    pages = count_pdf_pages(out_abs)
    size = os.path.getsize(out_abs)
    return {'ok': True, 'pages': pages, 'bytes': size, 'out': out_abs}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Build a PDF from markdown files via tools/pdf/md2pdf.mjs')
    parser.add_argument('--title', required=True)
    parser.add_argument('--subtitle', default='')
    parser.add_argument('--date', default=None)
    parser.add_argument('--out', required=True)
    parser.add_argument('--no-toc', action='store_true', help='skip the generated table of contents')
    parser.add_argument('files', nargs='+', help='markdown files, one chapter each, in order')
    args = parser.parse_args(argv)

    try:
        result = build(
            args.files,
            out_pdf=args.out,
            title=args.title,
            subtitle=args.subtitle,
            date=args.date,
            toc=not args.no_toc,
        )
    except PdfBuildError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
