"""Preserved old transcript text must not bypass audio-language exclusion."""
import json
import sqlite3

from engine import analyze_pending
from engine.language_gate import record


def test_preserved_english_text_excluded_from_both_semantic_routes(tmp_path):
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('''CREATE TABLE transcripts(code,words,segments,text);
        CREATE TABLE beats(code); CREATE TABLE frames(code);
        CREATE TABLE frame_labels(code); CREATE TABLE deepdives(code,sheet);''')
    con.execute('INSERT INTO transcripts VALUES(?,?,?,?)',
                ('X', 40, json.dumps([{'s':0,'e':60,'t':'old English words'}]), 'old English words'))
    sheet = tmp_path / 'sheet.jpg'; sheet.write_bytes(b'fixture')
    con.execute('INSERT INTO frames VALUES(?)', ('X',))
    con.execute('INSERT INTO deepdives VALUES(?,?)', ('X', str(sheet)))
    record(con, 'X', 'hi')
    assert analyze_pending.select_transcript_pending(con) == []
    assert analyze_pending.select_frame_pending(con) == []
    assert con.execute('SELECT text FROM transcripts').fetchone()[0] == 'old English words'
    con.close()
