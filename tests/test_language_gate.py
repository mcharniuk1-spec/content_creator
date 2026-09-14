import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import deep
from engine.language_gate import decision, record


def test_non_english_generator_never_consumed():
    def forbidden():
        raise AssertionError('non-English generator consumed')
        yield
    model = SimpleNamespace(transcribe=lambda *a, **k: (forbidden(), SimpleNamespace(language='hi')))
    with patch.object(deep, '_whisper', model):
        assert deep.transcribe('unused.mp4') == ([], 'hi')


def test_unknown_is_not_english():
    assert decision(None) == 'LANGUAGE_UNKNOWN'
    assert decision('hi') == 'EXCLUDED_NON_ENGLISH'
    assert decision('en') == 'ENGLISH_DETECTED'


def test_language_record_preserves_raw_transcript():
    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE transcripts(code TEXT,text TEXT)')
    con.execute('INSERT INTO transcripts VALUES (?,?)', ('a', 'original words'))
    assert record(con, 'a', 'hi') == 'EXCLUDED_NON_ENGLISH'
    assert con.execute('SELECT text FROM transcripts').fetchone()[0] == 'original words'
    assert con.execute('SELECT decision FROM language_gate').fetchone()[0] == 'EXCLUDED_NON_ENGLISH'
