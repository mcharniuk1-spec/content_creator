"""Feature extraction over three hand-written transcripts with counted-by-hand answers.

The three are chosen to cover the shapes the real corpus contains: a tool walkthrough
full of numbers and a comment-bait CTA, a rhetorical piece to camera with no numbers at
all, and an unpunctuated Whisper output (11 of the 266 usable transcripts have no
sentence punctuation, so the segment fallback is not a corner case).
"""
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine import lexical  # noqa: E402


# --- A: tool walkthrough, numbers, comment CTA -----------------------------
A_TEXT = ("Here's how I built an AI agent in n8n in 10 minutes. "
          "Most people waste 3 hours on this. "
          "Step 1, open n8n and add an OpenAI node. "
          "Step 2, connect your Gmail. "
          "I tested it on 50 emails and it saved 90% of the time. "
          "Comment AGENT and I'll send you the workflow.")
A_SEGMENTS = [{'s': 0.0, 'e': 4.0, 't': "Here's how I built an AI agent in n8n in 10 minutes."},
              {'s': 4.0, 'e': 7.0, 't': 'Most people waste 3 hours on this.'},
              {'s': 7.0, 'e': 11.0, 't': 'Step 1, open n8n and add an OpenAI node.'},
              {'s': 11.0, 'e': 14.0, 't': 'Step 2, connect your Gmail.'},
              {'s': 14.0, 'e': 18.0, 't': 'I tested it on 50 emails and it saved 90% of the time.'},
              {'s': 18.0, 'e': 20.0, 't': "Comment AGENT and I'll send you the workflow."}]
A_DUR = 20.0

# --- B: rhetorical, to camera, no numbers ----------------------------------
B_TEXT = ("Why do most people fail with AI? "
          "Because they never actually build anything. "
          "You watch, you nod, you move on. "
          "Is that really learning? "
          "Stop scrolling and open your laptop.")
B_SEGMENTS = [{'s': 0.0, 'e': 3.0, 't': 'Why do most people fail with AI?'},
              {'s': 3.0, 'e': 6.0, 't': 'Because they never actually build anything.'},
              {'s': 6.0, 'e': 9.0, 't': 'You watch, you nod, you move on.'},
              {'s': 9.0, 'e': 11.0, 't': 'Is that really learning?'},
              {'s': 11.0, 'e': 14.0, 't': 'Stop scrolling and open your laptop.'}]
B_DUR = 14.0

# --- C: no punctuation at all (Whisper without sentence marks) -------------
C_TEXT = ('so this is the thing nobody tells you about claude code '
          'it saves you hours every single week')
C_SEGMENTS = [{'s': 0.0, 'e': 3.0, 't': 'so this is the thing'},
              {'s': 3.0, 'e': 6.0, 't': 'nobody tells you about claude code'},
              {'s': 6.0, 'e': 9.0, 't': 'it saves you hours every single week'}]
C_DUR = 9.0


@pytest.fixture(scope='module')
def fa():
    return lexical.features(A_TEXT, A_SEGMENTS, A_DUR)


@pytest.fixture(scope='module')
def fb():
    return lexical.features(B_TEXT, B_SEGMENTS, B_DUR)


@pytest.fixture(scope='module')
def fc():
    return lexical.features(C_TEXT, C_SEGMENTS, C_DUR)


# ---------------------------------------------------------------------------
# size, pace, sentence splitting
# ---------------------------------------------------------------------------

def test_a_size_and_pace(fa):
    assert fa['sentence_source'] == 'punctuation'
    assert fa['sentences'] == 6
    assert fa['words'] == len(lexical.tokenize(A_TEXT))
    assert fa['wps'] == pytest.approx(fa['words'] / A_DUR, rel=1e-6)
    assert fa['dur_s'] == A_DUR


def test_c_falls_back_to_segments(fc):
    """No punctuation anywhere -> each timed segment becomes one pseudo-sentence."""
    assert fc['sentence_source'] == 'segments'
    assert fc['sentences'] == 3
    assert fc['words'] == 18
    assert fc['wps'] == pytest.approx(2.0)


def test_empty_transcript_is_flagged_not_crashed():
    f = lexical.features('', [], 12.0)
    assert f['empty'] is True
    assert f['words'] == 0


# ---------------------------------------------------------------------------
# numbers and evidence
# ---------------------------------------------------------------------------

def test_a_numbers(fa):
    # 10 minutes, 3 hours, Step 1, Step 2, 50 emails, 90%
    assert fa['numbers_n'] == 6
    assert fa['percentages_n'] == 1
    assert fa['numeric_evidence_n'] == 7                       # numbers + percent + money
    assert fa['numeric_evidence_per_10s'] == pytest.approx(7 * 10.0 / A_DUR, rel=1e-4)


def test_b_has_no_numbers(fb):
    assert fb['numbers_n'] == 0
    assert fb['percentages_n'] == 0
    assert fb['numeric_evidence_per_10s'] == 0.0


# ---------------------------------------------------------------------------
# questions
# ---------------------------------------------------------------------------

def test_b_questions_and_rhetoric(fb):
    assert fb['questions_n'] == 2
    # both are self-answered by the next declarative, and the first also opens "Why do"
    assert fb['rhetorical_questions_n'] == 2
    assert fb['questions_per_10s'] == pytest.approx(2 * 10.0 / B_DUR, rel=1e-4)


def test_a_has_no_questions(fa):
    assert fa['questions_n'] == 0
    assert fa['rhetorical_questions_n'] == 0


def test_direct_question_is_not_counted_as_rhetorical():
    """A question aimed at the comments is a CTA, not a rhetorical device."""
    f = lexical.features('Which one do you use? Tell me in the comments. I use Claude.',
                         None, 10.0)
    assert f['questions_n'] == 1
    assert f['rhetorical_questions_n'] == 0


# ---------------------------------------------------------------------------
# word classes
# ---------------------------------------------------------------------------

def test_a_authority_and_address(fa):
    assert fa['first_person_authority_n'] == 2               # "I built", "I tested"
    assert fa['second_person_n'] == 2                        # "your Gmail", "send you"
    assert fa['direct_address_per_10s'] == pytest.approx(2 * 10.0 / A_DUR, rel=1e-4)


def test_b_address_and_negation(fb):
    assert fb['second_person_n'] == 4                        # you x3 + your
    assert fb['negations_n'] == 1                            # never


def test_imperatives_are_sentence_initial(fa, fb):
    assert fa['imperatives_n'] == 1                           # "Comment AGENT ..."
    assert dict(fa['imperative_verbs'])['comment'] == 1
    assert fb['imperatives_n'] == 1                           # "Stop scrolling ..."
    assert dict(fb['imperative_verbs'])['stop'] == 1


def test_imperative_heuristic_misses_a_led_imperative():
    """Documented blind spot: the verb has to start the sentence."""
    f = lexical.features('Now go and open your terminal.', None, 5.0)
    assert f['imperatives_n'] == 0


# ---------------------------------------------------------------------------
# named entities
# ---------------------------------------------------------------------------

def test_a_entities(fa):
    ents = fa['entities']
    assert ents['n8n'] == 2
    assert ents['OpenAI'] == 1
    assert ents['Gmail'] == 1
    assert 'n8n' in fa['tools_mentioned']
    assert 'Gmail' in fa['platforms_mentioned']
    assert 'OpenAI' in fa['brands_mentioned']


def test_c_product_and_its_family_both_match(fc):
    """`Claude Code` and `Claude` are both true statements about one mention, so both
    are counted. Anything reading entities_n as "distinct products named" would be
    wrong; entities_distinct and the per-category lists are the honest readings."""
    assert fc['entities']['Claude Code'] == 1
    assert fc['entities']['Claude'] == 1
    assert 'Claude Code' in fc['tools_mentioned']


def test_b_has_no_named_entities(fb):
    """Bare "AI" is not a product name and must not be counted as one."""
    assert fb['entities'] == {}
    assert fb['entities_n'] == 0


# ---------------------------------------------------------------------------
# lexicons and derived rates
# ---------------------------------------------------------------------------

def test_a_cta_language(fa):
    assert fa['cta_verb_n'] >= 2
    assert fa['claims_is_heuristic'] is True
    assert fa['claims_per_10s'] is not None


def test_specificity_rises_with_names_and_numbers(fa, fb):
    """A walkthrough that names tools and quantities must score above a pep talk."""
    assert fa['specificity'] > fb['specificity']


def test_lexical_diversity_shapes(fa):
    assert 0 < fa['ttr'] <= 1
    assert fa['rttr'] > 0
    assert fa['types'] <= fa['words']


def test_repeated_phrases_finds_the_repetition():
    text = ('you do not need a better prompt. you do not need a better prompt. '
            'you need a better process.')
    f = lexical.features(text, None, 10.0)
    phrases = dict(f['repeated_phrases'])
    assert any(p.startswith('you do not need a better prompt') for p in phrases)


def test_sentence_openings_are_two_word_prefixes(fa):
    openings = dict(fa['sentence_openings'])
    assert openings['step 1'] == 1
    assert openings['step 2'] == 1


# ---------------------------------------------------------------------------
# timing blocks (the pre-beats fallback)
# ---------------------------------------------------------------------------

def test_timing_blocks_split_by_the_clock(fc):
    b = fc['blocks']
    assert b['available'] is True
    assert b['boundary'] == 'timing'
    # dur 9 s -> hook ends at min(5, 2.7)=2.7, tail starts at max(2.7, 9-2.7)=6.3
    assert b['hook_segments'] == 1
    assert b['body_segments'] == 2
    assert b['tail_segments'] == 0
    assert b['hook_words'] + b['body_words'] + b['tail_words'] == fc['words']
    assert b['hook_share_of_words'] + b['body_share_of_words'] == pytest.approx(1.0)


def test_timing_blocks_absent_without_segments():
    f = lexical.features('a few words with no timing at all', None, 12.0)
    assert f['blocks']['available'] is False


# ---------------------------------------------------------------------------
# the corpus path
# ---------------------------------------------------------------------------

def test_run_all_merges_without_clobbering(tmp_path):
    """run_all must add features_json['lexical'] and leave another owner's key alone."""
    import json
    import sqlite3
    import db as legacy_db
    from engine import corpus

    path = str(tmp_path / 'radar.db')
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(legacy_db.SCHEMA)
    corpus.ensure_tables(con)
    con.execute("INSERT INTO snapshots (id, taken, done) VALUES (1, '2026-09-10', 1)")
    con.execute('INSERT INTO reels (snapshot_id, code, pk_user, username, ts, play, likes, comm,'
                ' resh, save, dur) VALUES (1, "AAA", 7, "x", 1000, 5000, 10, 1, 2, 3, ?)', (A_DUR,))
    con.execute('INSERT INTO transcripts (code, lang, words, text, segments) VALUES (?,?,?,?,?)',
                ('AAA', 'en', len(A_TEXT.split()), A_TEXT, json.dumps(A_SEGMENTS)))
    corpus.merge_features(con, 'AAA', 'perf', {'play': 5000})
    con.commit()

    assert lexical.run_all(con, verbose=False) == 1
    row = con.execute('SELECT features_json FROM video_features WHERE code="AAA"').fetchone()
    data = json.loads(row[0])
    assert data['perf'] == {'play': 5000}
    assert data['lexical']['words'] == len(lexical.tokenize(A_TEXT))
    assert data['lexical']['lexical_version'] == lexical.LEXICAL_VERSION
    con.close()
