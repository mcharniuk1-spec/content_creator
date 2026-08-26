import pytest

from scripts.youtube_calibration_300 import english_evidence, parse_duration, relevance


@pytest.mark.parametrize(("value", "expected"), [("PT45S", 45), ("PT2M5S", 125), ("PT1H2M3S", 3723), (None, None)])
def test_parse_duration(value, expected):
    assert parse_duration(value) == expected


def test_relevance_requires_agentic_and_business_or_proof_signal():
    direct = {"snippet": {"title": "Build an AI agent for sales operations", "description": "Step-by-step business workflow"}}
    generic = {"snippet": {"title": "AI image prompts", "description": "fun art"}}
    assert relevance(direct)["relevant"] is True
    assert relevance(generic)["relevant"] is False


def test_english_evidence_prefers_official_language():
    assert english_evidence({"snippet": {"defaultAudioLanguage": "en-US", "title": "x"}}) == (True, "official_defaultAudioLanguage=en-US")


def test_english_evidence_has_explicit_gap():
    assert english_evidence({"snippet": {"title": "人工智能代理", "description": "企业工作流"}}) == (False, "english_not_evidenced")
