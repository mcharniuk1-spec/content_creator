"""Original-audio language routing, separate from transcript text or creator identity.

Detection is probabilistic; this gate is not acoustic accuracy certification.
Do not consume a lazy ASR segment generator for non-English/unknown speech.
"""
import datetime


def decision(language):
    if language == 'en':
        return 'ENGLISH_DETECTED'
    return 'LANGUAGE_UNKNOWN' if language in (None, '', 'unknown') else 'EXCLUDED_NON_ENGLISH'


def eligible(con, code):
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='language_gate'").fetchone():
        return False
    row = con.execute('SELECT language,decision FROM language_gate WHERE code=?', (code,)).fetchone()
    return bool(row and row[0] == 'en' and row[1] == 'ENGLISH_DETECTED')


def record(con, code, language):
    con.execute('CREATE TABLE IF NOT EXISTS language_gate (code TEXT PRIMARY KEY, language TEXT, decision TEXT NOT NULL, observed_at TEXT NOT NULL)')
    state = decision(language)
    con.execute('INSERT OR REPLACE INTO language_gate VALUES (?,?,?,?)',
                (code, language, state, datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return state
