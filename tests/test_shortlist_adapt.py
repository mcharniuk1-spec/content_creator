"""sa-v1 contract: engine/shortlist_adapt.py validator and renderer."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import shortlist_adapt as sa   # noqa: E402

GOOD = {"code": "X", "analysis_version": "sa-v1", "model": "m", "block": "process",
        "original": {"topic": "t", "what_they_show": "w", "why_it_worked": "y",
                     "result": {"plays": 1000, "vs_author_norm": 2.0, "shares_1k": 10, "saves_1k": 20},
                     "does_not_transfer": "d"},
        "ours": {"topic": "Quotes out the same day", "angle": "a", "for_whom": "f", "process": "p", "friction": "fr",
                 "ai_boundary": "b", "next_action": "n", "why_forward": "w"},
        "reject_reason": None, "format": "M2 Teardown", "format_reason": "r",
        "shoot": {"duration_s": 60, "location": "desk", "presenter": "Michael", "banner": "Quotes: 2 days to 2 hours",
                  "parts": [{"part": "hook", "seconds": 6, "says": "Two days per quote. Here is the two-hour version.",
                             "in_frame": "Michael", "on_screen": "quote queue", "overlay": "2 days to 2 hours"},
                            {"part": "explanation", "seconds": 24, "says": "s", "in_frame": "i", "on_screen": "o", "overlay": ""},
                            {"part": "proof", "seconds": 18, "says": "s", "in_frame": "i", "on_screen": "o", "overlay": ""},
                            {"part": "payoff", "seconds": 12, "says": "s", "in_frame": "i", "on_screen": "o", "overlay": ""}]},
        "cta": {"type": "comment_keyword", "keyword": "QUOTE", "artefact": "quote-checklist", "viewer_gets": "the checklist"},
        "claims": [{"text": "c", "state": "OBSERVED", "source": "batch"}], "confidence": "PROBABLE", "notes": ""}


def test_good_card_validates():
    assert sa.validate(GOOD) == [], sa.validate(GOOD)


def test_validator_catches_the_rules():
    bad = json.loads(json.dumps(GOOD)); bad["shoot"]["parts"][0]["says"] = "Our agentic workflow uses an API"
    assert any("banned word" in e for e in sa.validate(bad))
    bad = json.loads(json.dumps(GOOD)); bad["shoot"]["parts"][0]["seconds"] = 12
    assert any("hook longer" in e for e in sa.validate(bad))
    bad = json.loads(json.dumps(GOOD)); bad["shoot"]["duration_s"] = 90
    assert any("add up" in e for e in sa.validate(bad))
    bad = json.loads(json.dumps(GOOD)); bad["cta"]["artefact"] = "no-such-file"
    assert any("artefact file not found" in e for e in sa.validate(bad))
    bad = json.loads(json.dumps(GOOD)); bad["ours"] = None
    assert any("reject_reason" in e for e in sa.validate(bad))
    ok = json.loads(json.dumps(GOOD)); ok["cta"] = None
    assert sa.validate(ok) == []


def test_card_md_has_three_sections():
    card = {"n": 1, "block": "process", "stage": 1, "fmt": "M2 Teardown", "author": "a", "ref": "https://x",
            "age": 3, "stage_note": "best in block Process", "about": "x", "cap": ""}
    md = sa.card_md(card, GOOD)
    for h in ("What they shot and what it did", "Our version", "How we shoot it"):
        assert h in md
    assert "| hook | 6 |" in md
