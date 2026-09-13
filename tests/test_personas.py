"""personas/*.json + engine/personas.py + engine/persona_adapt.py contracts."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import personas as pm            # noqa: E402
from engine import persona_adapt as pa       # noqa: E402


def test_three_valid_english_personas():
    P = pm.load_all()
    assert set(P) == {'rick', 'emma', 'anna'}
    for p in P.values():
        assert sum(len(v) for v in p['interests'].values()) >= pm.MIN_INTERESTS
    for p in P.values():
        assert pm.validate(p) == [], pm.validate(p)


def test_every_persona_artefact_has_a_file_or_is_named():
    """Each persona lists artefacts; the artefacts index must mention every persona."""
    index = (ROOT / 'artefacts' / 'README.md').read_text(encoding='utf-8')
    for p in pm.load_all().values():
        assert p['name'] in index, f"{p['name']} not in artefacts/README.md"
    files = list((ROOT / 'artefacts').glob('*.md'))
    assert len(files) >= 10


def test_match_routes_obvious_texts():
    assert pm.match('Two-man HVAC shop: estimates, voicemails, scheduling')[0][0] == 'rick'
    assert pm.match('shopify store support tickets product descriptions')[0][0] == 'emma'
    assert pm.match('top 3 tools for market and competitor research for small brands')[0][0] == 'emma'
    assert pm.match('meeting minutes copilot team policy client data')[0][0] == 'anna'
    assert pm.match('brokerage client documents sorted and routed for approval')[0][0] == 'anna'
    top = pm.match('top 3 tools for market and competitor research for small brands')[0]
    assert any('Top 3 tools for market and competitor research' in h for h in top[2])


def test_render_doc_lists_all():
    doc = pm.render_doc()
    for p in pm.load_all().values():
        assert f"## {p['name']}" in doc


def test_concept_contract_validation():
    good = {k: 'x' for k in pa.PA_KEYS}
    good.update({'analysis_version': 'pa-v1', 'persona': 'rick', 'reject_reason': None,
                 'interest': 'Automating my process: Voicemail to draft text reply to one-tap send',
                 'hook': 'Two-man shop. Admin ate the evenings. One loop fixed it and broke on day three.',
                 'cta': {'type': 'comment_keyword', 'keyword': 'PRICES', 'artefact': 'price-sheet template'},
                 'question': 'q', 'why_this_persona': 'w', 'claims': []})
    assert pa.validate_concept(good) == []
    bad = dict(good, hook='Our agentic workflow uses an API and an LLM to automate everything for you today')
    errs = pa.validate_concept(bad)
    assert any('banned word' in e for e in errs)
    rejected = dict(good, persona=None, reject_reason=None)
    assert any('reject_reason' in e for e in pa.validate_concept(rejected))
    no_cta = dict(good, cta=None)                                # optional
    assert pa.validate_concept(no_cta) == []
    bad_cta = dict(good, cta={'type': 'follow'})
    assert any('cta, when present' in e for e in pa.validate_concept(bad_cta))
    no_interest = dict(good, interest='')
    assert any('interest' in e for e in pa.validate_concept(no_interest))


def test_prompt_placeholders_only_ours():
    tpl = (ROOT / 'engine' / 'prompts' / 'persona-adapt.md').read_text(encoding='utf-8')
    rendered = pa._prompt('data/analysis/input/persona-x-1.json')
    assert '{batch_path}' not in rendered and '{output_dir}' not in rendered
    assert 'pa-v1' in rendered and 'personas/*.json' in tpl
