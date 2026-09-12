"""Tests for engine.pdf_build / tools/pdf/md2pdf.mjs.

Builds a small synthetic 3-chapter markdown set that exercises every
feature the pipeline is supposed to handle: a 12-column table (wide-table
shrink path), an embedded PNG (Pillow-generated, checks base64 data-URI
image embedding), a `::grid::` storyboard line, Cyrillic body text (font
coverage), and a markdown link (kept clickable). Then asserts the PDF
exists, has at least 3 pages (one per chapter, plus cover/TOC), and is
non-trivially sized (> 20 KB -- rules out an near-empty/broken PDF).

No network, no git. Skips with a reason (not a failure) if headless
Chrome isn't present on this machine, per engine.pdf_build.chrome_available().

    python3 -m pytest tests/test_pdf_build.py -q
"""
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine import pdf_build  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is a project dependency elsewhere
    Image = None

CHROME_REASON = f'headless Chrome not found at {pdf_build.CHROME}'
PILLOW_REASON = 'Pillow not installed'


def _make_png(path, size=(320, 180), color=(76, 107, 138)):
    img = Image.new('RGB', size, color)
    img.save(path)


def _twelve_col_table():
    cols = [f'Metric {i}' for i in range(1, 13)]
    header = '| ' + ' | '.join(cols) + ' |'
    sep = '|' + '|'.join(['---'] * 12) + '|'
    rows = []
    for r in range(1, 6):
        cells = [f'{r}.{i}' for i in range(1, 13)]
        rows.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join([header, sep, *rows])


def _write_chapters(tmp_path, chart_png, frame_pngs):
    ch1 = tmp_path / '01-overview.md'
    ch1.write_text(
        '# Overview\n\n'
        'Обзор проекта M2Radar: аналитика рилсов и сторителлинг для команды.\n\n'
        'This chapter has a [link to the repo](https://example.com/m2-radar) that must '
        'stay clickable in the printed PDF.\n\n'
        '## Scope\n\n'
        '- Cyrillic и English text mixed in one paragraph\n'
        '- **bold** and *italic* inline markup\n'
        '- a nested list:\n'
        '  - sub-item one\n'
        '  - sub-item two\n',
        encoding='utf-8',
    )

    ch2 = tmp_path / '02-metrics.md'
    ch2.write_text(
        '# Metrics\n\n'
        'Широкая таблица (12 columns) below must not overflow the page width.\n\n'
        + _twelve_col_table() + '\n\n'
        '## Chart\n\n'
        f'![Sample performance chart]({chart_png.name})\n',
        encoding='utf-8',
    )

    grid_line = '::grid ' + '|'.join(f.name for f in frame_pngs) + '::'
    ch3 = tmp_path / '03-storyboard.md'
    ch3.write_text(
        '# Storyboard\n\n'
        'Раскадровка (storyboard) sample with three frames in a grid.\n\n'
        + grid_line + '\n',
        encoding='utf-8',
    )

    return [str(ch1), str(ch2), str(ch3)]


@pytest.mark.skipif(Image is None, reason=PILLOW_REASON)
@pytest.mark.skipif(not pdf_build.chrome_available(), reason=CHROME_REASON)
def test_build_three_chapter_sample(tmp_path):
    chart_png = tmp_path / 'chart.png'
    _make_png(chart_png, size=(640, 360), color=(76, 107, 138))

    frame_pngs = []
    for i, color in enumerate([(200, 80, 60), (80, 160, 90), (90, 90, 200)]):
        p = tmp_path / f'frame_{i}.png'
        _make_png(p, size=(160, 90), color=color)
        frame_pngs.append(p)

    md_files = _write_chapters(tmp_path, chart_png, frame_pngs)
    out_pdf = tmp_path / 'sample.pdf'

    result = pdf_build.build(
        md_files,
        out_pdf=str(out_pdf),
        title='M2Radar PDF Pipeline Test',
        subtitle='Synthetic 3-chapter sample',
        date='12 September 2026',
    )

    assert result['ok'] is True
    assert os.path.exists(result['out'])
    assert os.path.samefile(result['out'], out_pdf)
    assert result['pages'] >= 3, f"expected >=3 pages, got {result['pages']}"
    assert result['bytes'] > 20_000, f"expected >20KB, got {result['bytes']} bytes"

    # bytes/out must agree with the file actually on disk
    assert os.path.getsize(out_pdf) == result['bytes']

    # the PDF should embed the base64 image data, not merely reference a
    # local file path (self-contained document requirement)
    with open(out_pdf, 'rb') as fh:
        pdf_bytes = fh.read()
    assert b'/Image' in pdf_bytes or b'/XObject' in pdf_bytes, 'no embedded image XObject found in PDF'


@pytest.mark.skipif(Image is None, reason=PILLOW_REASON)
@pytest.mark.skipif(not pdf_build.chrome_available(), reason=CHROME_REASON)
def test_build_raises_on_missing_markdown_file(tmp_path):
    with pytest.raises(pdf_build.PdfBuildError):
        pdf_build.build(
            [str(tmp_path / 'does-not-exist.md')],
            out_pdf=str(tmp_path / 'out.pdf'),
            title='Missing file test',
        )


def test_count_pdf_pages_excludes_pages_tree_root(tmp_path):
    # A minimal synthetic buffer: two leaf /Type /Page markers and one
    # /Type /Pages tree-root marker that must NOT be counted.
    fake_pdf = tmp_path / 'fake.pdf'
    fake_pdf.write_bytes(
        b'%PDF-1.4\n'
        b'1 0 obj << /Type /Pages /Count 2 >> endobj\n'
        b'2 0 obj << /Type /Page /Parent 1 0 R >> endobj\n'
        b'3 0 obj << /Type /Page /Parent 1 0 R >> endobj\n'
        b'%%EOF'
    )
    assert pdf_build.count_pdf_pages(str(fake_pdf)) == 2
