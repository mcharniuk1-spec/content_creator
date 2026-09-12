#!/usr/bin/env python3
"""Notion block-JSON builders shared by `engine/notion_sync.py`.

Two hard limits from the Notion API this module exists to respect everywhere a block
is built, so no caller has to remember them by hand:

  - a `rich_text` object's `text.content` string is capped at 2000 characters;
  - `PATCH /blocks/{id}/children` (and the `children` array on page creation) accepts
    at most 100 block objects per call.

Every builder below chunks long text into multiple `rich_text` runs inside the same
block, rather than truncating it — the block still reads as one paragraph/bullet/etc.
Actual truncation (e.g. Cards v2 · Script capped at 2000 chars with a "see JSON"
pointer) is a decision `notion_sync.py` makes explicitly per field, never something
this module does silently.

No network calls happen here and nothing here talks to Notion — these are pure
functions that build the JSON body `notion.call()` would send.
"""
RICH_TEXT_LIMIT = 2000
BLOCKS_PER_REQUEST = 100


def chunk_text(text, limit=RICH_TEXT_LIMIT):
    """Split `text` into <=`limit`-char pieces. Always returns at least one piece
    (an empty string for falsy input) so callers never have to special-case empty text."""
    text = text or ''
    if not text:
        return ['']
    return [text[i:i + limit] for i in range(0, len(text), limit)]


def rich_text(text, bold=False, italic=False, code=False, color=None, link=None):
    """One or more Notion rich_text objects covering `text`, each <=2000 chars.

    Annotations/link apply to every chunk equally — this is for a single logical
    run of text that happens to be long, not for mixed formatting within one call.
    """
    out = []
    ann = {k: v for k, v in (('bold', bold), ('italic', italic), ('code', code)) if v}
    if color:
        ann['color'] = color
    for chunk in chunk_text(text):
        obj = {'type': 'text', 'text': {'content': chunk}}
        if link:
            obj['text']['link'] = {'url': link}
        if ann:
            obj['annotations'] = dict(ann)
        out.append(obj)
    return out


def _text_block(text, kind):
    return {'object': 'block', 'type': kind, kind: {'rich_text': rich_text(text)}}


def heading(text, level=2):
    """`heading_1` / `heading_2` / `heading_3` block."""
    if level not in (1, 2, 3):
        raise ValueError(f'heading level must be 1, 2 or 3, got {level!r}')
    return _text_block(text, f'heading_{level}')


def paragraph(text):
    return _text_block(text, 'paragraph')


def bulleted_item(text, label=None):
    """A bullet, optionally with a bold `label:` prefix (e.g. 'In frame: <value>')."""
    rt = (rich_text(f'{label}: ', bold=True) if label else []) + rich_text(text)
    return {'object': 'block', 'type': 'bulleted_list_item', 'bulleted_list_item': {'rich_text': rt}}


def numbered_item(text):
    return {'object': 'block', 'type': 'numbered_list_item', 'numbered_list_item': {'rich_text': rich_text(text)}}


def toggle(title, children=None):
    children = list(children or [])
    if len(children) > BLOCKS_PER_REQUEST:
        raise ValueError(
            f'toggle {title!r} has {len(children)} children, over the {BLOCKS_PER_REQUEST}-per-request '
            'cap — split it into multiple toggles or top-level sections instead of nesting them all here')
    return {'object': 'block', 'type': 'toggle', 'toggle': {'rich_text': rich_text(title), 'children': children}}


def callout(text, icon='💡', color='default'):
    return {'object': 'block', 'type': 'callout',
            'callout': {'rich_text': rich_text(text), 'icon': {'type': 'emoji', 'emoji': icon}, 'color': color}}


def code_block(text, language='plain text'):
    return {'object': 'block', 'type': 'code', 'code': {'rich_text': rich_text(text), 'language': language}}


def bookmark(url, caption=None):
    b = {'object': 'block', 'type': 'bookmark', 'bookmark': {'url': url}}
    if caption:
        b['bookmark']['caption'] = rich_text(caption)
    return b


def link_to_page(page_id):
    """A `link_to_page` block — the standard way to embed an existing page/database
    inline without duplicating its content."""
    return {'object': 'block', 'type': 'link_to_page', 'link_to_page': {'type': 'page_id', 'page_id': page_id}}


def link_to_database(database_id):
    """A `link_to_page` block pointing at a database. Notion rejects a database id under
    `page_id` ("page_id must reference a page"); databases need `database_id`."""
    return {'object': 'block', 'type': 'link_to_page',
            'link_to_page': {'type': 'database_id', 'database_id': database_id}}


def child_database(database_id):
    return {'object': 'block', 'type': 'child_database', 'child_database': {'title': ''}, 'id': database_id}


def divider():
    return {'object': 'block', 'type': 'divider', 'divider': {}}


def table(headers, rows, has_row_header=False):
    """A `table` block with `table_row` children. `rows` is a list of row cells
    (list of stringifiable values); rows shorter than `headers` are padded, longer
    rows are truncated to the table's width so every row block stays valid."""
    width = len(headers)

    def row_block(cells):
        cells = list(cells) + [''] * (width - len(cells))
        return {'object': 'block', 'type': 'table_row',
                'table_row': {'cells': [rich_text(str(c)) for c in cells[:width]]}}

    return {'object': 'block', 'type': 'table',
            'table': {'table_width': width, 'has_column_header': True, 'has_row_header': has_row_header,
                      'children': [row_block(headers)] + [row_block(r) for r in rows]}}


def chunk_blocks(blocks, size=BLOCKS_PER_REQUEST):
    """Yield lists of at most `size` top-level blocks — the shape the children-append
    endpoint needs when a page body has more than 100 blocks."""
    blocks = list(blocks)
    for i in range(0, len(blocks), size):
        yield blocks[i:i + size]


def count_blocks(blocks):
    """Recursively count blocks, including nested `children` (toggle) and table rows —
    used by `notion_sync.py`'s --dry plan to report a real block-count estimate instead
    of just len(top_level_blocks)."""
    n = 0
    for b in blocks:
        n += 1
        kind = b.get('type')
        inner = b.get(kind) or {}
        n += count_blocks(inner.get('children') or [])
    return n
