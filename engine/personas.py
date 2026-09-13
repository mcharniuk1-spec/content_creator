#!/usr/bin/env python3
"""Audience personas — the people every card is adapted to.

Source of truth: `personas/<id>.json` (git-tracked, English). Each file is one portfolio:
who the person is, their day, their pains in their own words with the source thread, the
questions they ask, what they forward and save, what they distrust, how they think about
cost, the CTA artefacts they would leave a comment for, and the topic keywords the radar
uses to route a found reel to them. Misha's decision of 2026-09-13: content is made for one
of these people, every video ends with a comment call-to-action for a concrete artefact.

    python3 -m engine.personas list
    python3 -m engine.personas match "caption or transcript text" [--topics a,b]
    python3 -m engine.personas doc > docs/PERSONAS_v2.md     # render the portfolios

`match()` is deliberately simple (keyword overlap on `topics` + question words): it is a
routing hint for the weekly cards and for the adaptation batch, not a judgement. The
adaptation agent (engine/prompts/persona-adapt.md) makes the call and writes why.
"""
import argparse, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PERSONA_DIR = ROOT / 'personas'
ARTEFACT_DIR = ROOT / 'artefacts'

REQUIRED = ('id', 'name', 'age', 'business', 'size', 'ai_level', 'tools', 'day', 'interests',
            'distrusts', 'cost', 'topics', 'evidence')
MIN_INTERESTS = 30


def load_all(directory=PERSONA_DIR):
    out = {}
    for p in sorted(pathlib.Path(directory).glob('*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        out[d['id']] = d
    return out


def validate(persona):
    """Returns a list of problems (empty = valid)."""
    errs = []
    for k in REQUIRED:
        if k not in persona or persona[k] in (None, '', [], {}):
            errs.append(f"{persona.get('id', '?')}: missing {k}")
    if not isinstance(persona.get('ai_level'), int) or not 0 <= persona.get('ai_level', -1) <= 10:
        errs.append(f"{persona.get('id')}: ai_level must be an int 0-10")
    interests = persona.get('interests') or {}
    if not isinstance(interests, dict) or not all(isinstance(v, list) and v for v in interests.values()):
        errs.append(f"{persona.get('id')}: interests must be {{category: [items]}}")
    elif sum(len(v) for v in interests.values()) < MIN_INTERESTS:
        errs.append(f"{persona.get('id')}: fewer than {MIN_INTERESTS} interests")
    if not isinstance(persona.get('age'), int):
        errs.append(f"{persona.get('id')}: age must be an int")
    text = json.dumps(persona, ensure_ascii=False)
    bad = sorted({ch for ch in text if ch.isalpha() and ord(ch) > 127})
    if bad:
        errs.append(f"{persona.get('id')}: non-English letters {bad[:5]}")
    return errs


_WORD = re.compile(r"[a-z][a-z0-9'-]+")
_STOP = {'which', 'their', 'there', 'about', 'without', 'actually', 'whether', 'where', 'other',
         'something', 'someone', 'really', 'every', 'these', 'those', 'should', 'would', 'could',
         'before', 'after', 'while', 'being', 'things', 'thing'}


def all_interests(persona):
    return [(cat, item) for cat, items in (persona.get('interests') or {}).items() for item in items]


def match(text, topics=None, personas=None):
    """Score every persona against a caption/transcript. Returns [(persona_id, score, hits)]
    sorted by score desc. Score = topic-keyword hits (weight 2) + interest-word overlap
    (weight 1, only words of 5+ letters), normalised by the persona's keyword count so a
    persona with a long list is not favoured. `hits` lists keywords first, then the
    matched interest lines (the reel is adapted to one of those)."""
    personas = personas or load_all()
    words = set(_WORD.findall((text or '').lower()))
    topic_text = ' '.join(topics or []).lower()
    out = []
    for pid, p in personas.items():
        hits = []
        for kw in p['topics']:
            k = kw.lower()
            if (' ' in k and k in (text or '').lower()) or k in words or k in topic_text \
                    or (len(k) >= 4 and any(w.startswith(k) for w in words)):
                hits.append(kw)
        interest_hits = []
        for cat, item in all_interests(p):
            iw = {w for w in _WORD.findall(item.lower()) if len(w) >= 5 and w not in _STOP}
            common = words & iw
            if len(common) >= 2 or (len(common) == 1 and any(k in item.lower() for k in hits)):
                interest_hits.append(f'{cat}: {item}')
        score = (2 * len(hits) + 2 * len(interest_hits)) / max(1, len(p['topics'])) * 10
        out.append((pid, round(score, 2), hits + interest_hits[:4]))
    return sorted(out, key=lambda x: -x[1])


def render_doc(personas=None):
    personas = personas or load_all()
    L = ['# Audience personas v3 (2026-09-13)', '',
         'Generated from `personas/*.json` by `python3 -m engine.personas doc`. Edit the JSON, not this file.',
         'Three people who stand for our potential clients. Each has a long list of interests, built from',
         'what real people ask (reports/audience/01-07) and written as their interests, not as quotes.',
         'A found reel is adapted to the persona whose list contains that interest. A comment call-to-action',
         'is used when a real artefact exists (`artefacts/`), not in every video.', '']
    for pid, p in personas.items():
        n = sum(len(v) for v in p['interests'].values())
        L += [f"## {p['name']}, {p['age']}", '',
              f"**{p['business']}.** Size: {p['size']}. AI level {p['ai_level']}/10.",
              f"**Tools today:** {'; '.join(p['tools'])}.",
              f"**A day:** {p['day']}", '', f'**Interests ({n}).**']
        for cat, items in p['interests'].items():
            L.append(f'*{cat}*')
            L += [f'- {it}' for it in items]
        L += ['', f"**Distrusts:** {p['distrusts']}", f"**Cost:** {p['cost']}",
              '**Artefacts for a comment CTA (optional):** ' + '; '.join(p.get('cta_artefacts') or []) + '.',
              f"**Routing keywords:** {', '.join(p['topics'])}.",
              f"**Evidence:** {'; '.join(p['evidence'])}", '']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    m = sub.add_parser('match'); m.add_argument('text'); m.add_argument('--topics', default='')
    sub.add_parser('doc')
    v = sub.add_parser('validate')
    args = ap.parse_args(argv)
    personas = load_all()
    if args.cmd == 'list':
        for pid, p in personas.items():
            print(f"{pid:<6} {p['name']:<6} {p['age']}  level {p['ai_level']}  {p['business'][:70]}")
    elif args.cmd == 'match':
        for pid, score, hits in match(args.text, [t for t in args.topics.split(',') if t]):
            print(f'{pid:<6} {score:>6}  {", ".join(hits[:8])}')
    elif args.cmd == 'doc':
        print(render_doc(personas))
    elif args.cmd == 'validate':
        errs = [e for p in personas.values() for e in validate(p)]
        print('\n'.join(errs) or f'{len(personas)} personas valid')
        return 1 if errs else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
