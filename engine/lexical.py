#!/usr/bin/env python3
"""Phrase-level and word-class features from a transcript (V4 §63, SPEC §2.6).

Stdlib only, on purpose: no model downloads, no network, nothing the server cron
would have to install. Everything here is either counting, regex matching against a
curated lexicon, or arithmetic on the timecodes that are already in the database.

What that buys and what it costs
--------------------------------
Honest: word/sentence/phrase counts, n-grams, repeated phrases, sentence openings and
endings, numbers, percentages, questions, and every closed-class count (pronouns,
modals, negations, second person) — those are finite word lists, and a lexicon match
is the ground truth for them.

Heuristic, and labelled as such in the output: `imperatives` (sentence-initial verb
from a list — misses "Now go and try it"), `rhetorical_questions`, `claims`, and the
`pos_lite_*` suffix counts. Full POS tagging would need an NLP model; §63 asks for
noun/verb/adjective counts but a suffix rule is not a tagger, so this module reports
only the three suffix families that are reliable enough to be worth anything
(-ly adverbs, -ing gerunds, -ed past forms) and says so in the key names.

    python3 -m engine.lexical                      run over every usable transcript
    python3 -m engine.lexical --code DUGghN2E82c   print one video's features
"""
from __future__ import annotations

import collections
import json
import math
import os
import re
import sqlite3
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine import corpus  # noqa: E402

LEXICAL_VERSION = 'lex-v1'

# ---------------------------------------------------------------------------
# lexicons
# ---------------------------------------------------------------------------

STOPLIST = set("""
a about above after again against all also am an and any are aren't as at be because been
before being below between both but by can cannot could couldn't did didn't do does doesn't
doing don't down during each few for from further had hadn't has hasn't have haven't having
he her here hers herself him himself his how i i'd i'll i'm i've if in into is isn't it it's
its itself just let's me more most mustn't my myself no nor not of off on once only or other
ought our ours ourselves out over own same shan't she should shouldn't so some such than that
the their theirs them themselves then there these they this those through to too under until
up very was wasn't we were weren't what when where which while who whom why with won't would
wouldn't you your yours yourself yourselves gonna wanna got get go going okay ok yeah yep
like really actually literally basically thing things stuff way ways lot lots know see look
right now one two make made take give want need use using used
""".split())

PRONOUNS = set("""i me my mine myself you your yours yourself yourselves he him his she her hers
it its we us our ours they them their theirs this that these those""".split())
SECOND_PERSON = set("""you your yours yourself yourselves you're you'll you've you'd""".split())
FIRST_PERSON = set("""i me my mine myself we us our ours i'm i've i'll i'd we're we've we'll""".split())

# "I built / we tested" — the creator claiming to have done the work themselves.
FIRST_PERSON_AUTHORITY_RX = re.compile(
    r"\b(?:i|we)\s+(?:just\s+|already\s+|actually\s+|literally\s+)?"
    r"(?:built|build|made|make|created|create|tested|test|tried|ran|run|used|spent|shipped|"
    r"launched|analy[sz]ed|studied|found|discovered|figured|learned|reviewed|scraped|"
    r"automated|coded|wrote|designed|trained|measured|benchmarked)\b")

IMPERATIVE_VERBS = set("""go click open type add take use try check stop start look watch listen
save share comment follow drop download copy paste head grab make build create write remember
imagine think notice keep let do pick choose select install run set put send ask tell give find
see read learn forget avoid focus connect hit tap swipe subscribe join sign enter test replace
upload generate prompt plug drag scroll turn switch pause skip repeat delete remove pull push
name call show bring stay come move update change fix""".split())

MODALS = set("""can could will would shall should may might must ought""".split())
MODAL_PHRASES_RX = re.compile(r"\b(?:need to|have to|has to|had to|got to|going to|able to)\b")

NEGATIONS = set("""not no never none nothing nobody nowhere neither nor cannot without don't
doesn't didn't won't can't isn't aren't wasn't weren't shouldn't couldn't wouldn't haven't
hasn't hadn't ain't""".split())

INTENSIFIERS = set("""very really extremely super insanely absolutely completely totally
literally incredibly ridiculously massively seriously entirely hugely wildly crazy insane
way too much far highly deeply""".split())

COMPARISON_WORDS = set("""than more less fewer compared versus vs instead rather similar unlike
twice half double faster cheaper better worse easier harder bigger smaller longer shorter
higher lower stronger weaker quicker slower""".split())
COMPARATIVE_RX = re.compile(r"\b\w{3,}er\s+than\b")

SUPERLATIVES = set("""best worst most least fastest cheapest easiest biggest smallest greatest
hardest strongest ultimate top perfect""".split())
SUPERLATIVE_RX = re.compile(r"\b(?:the\s+)?\w{3,}est\b|\bnumber one\b|\b#1\b")

EMOTIONAL = set("""love hate amazing incredible insane crazy shocking shocked stunning beautiful
painful frustrating annoying excited exciting boring hilarious embarrassing proud angry happy
sad wow unbelievable obsessed brutal wild ridiculous terrible awful awesome fantastic""".split())

FEAR = set("""risk risky danger dangerous warning careful mistake mistakes fail failing failure
lose losing lost replace replaced replacing obsolete behind broke broken wrong trap scam waste
wasted wasting threat fired unemployed disaster nightmare worry worried scared afraid illegal
banned ban penalty punished trouble hurt damage""".split())

OPPORTUNITY = set("""opportunity chance unlock free win winning growth grow growing scale
scaling profit profitable revenue money income earn earning leverage advantage edge potential
10x multiply boost increase easy simple instantly effortless passive automate automated""".split())

URGENCY = set("""now today immediately hurry quick quickly asap soon deadline limited already
still before tomorrow tonight instantly""".split())
URGENCY_RX = re.compile(r"\b(?:right now|last chance|while you can|don't wait|before it's too late|"
                        r"running out|act fast|as soon as possible)\b")

IDENTITY = set("""founder founders creator creators entrepreneur entrepreneurs developer
developers marketer marketers freelancer freelancers agency agencies beginner beginners expert
experts pro professional student students engineer engineers designer designers consultant
owner owners ceo solopreneur builder builders team boss winners losers""".split())
IDENTITY_RX = re.compile(r"\b(?:most people|everyone else|smart people|top 1%|the 1%|"
                         r"if you're a|people who)\b")

NOVELTY = set("""new newest latest just released launched dropped announced introducing finally
breakthrough update updated first ever""".split())
NOVELTY_RX = re.compile(r"\b(?:brand new|just dropped|just launched|just released|never before|"
                        r"changed everything|game changer|first time)\b")

PROOF = set("""proof evidence data study studies research tested testing benchmark benchmarks
measured results result numbers stats statistics experiment receipts screenshot demo source
sources proven proved verified""".split())
PROOF_RX = re.compile(r"\b(?:case study|before and after|i tested|we tested|here's the|look at the|"
                      r"this is what|according to)\b")

CTA_VERBS = set("""comment dm message save share follow subscribe like click tap download grab
join type send drop""".split())
CTA_RX = re.compile(r"\b(?:link in bio|check out|sign up|comment [\"']?\w+|let me know|"
                    r"drop a comment|send you|i'll send|dm me|follow for)\b")

RHETORICAL_OPENERS = re.compile(
    r"^(?:what if|imagine|why (?:is|are|do|does|would|should)|ever wonder|have you ever|"
    r"how many times|who else|what happens|sound familiar|right\?|makes sense)\b")
DIRECT_QUESTION_RX = re.compile(r"\b(?:comment|dm|tell me|let me know|what do you think|"
                                r"which one|drop)\b")

COPULA_RX = re.compile(r"\b(?:is|are|was|were|will|won't|isn't|aren't|means|becomes|gives|makes|"
                       r"takes|costs|works|does|has|have)\b")

NUMBER_RX = re.compile(r"(?<![\w.])(?:\d[\d,]*(?:\.\d+)?)(?![\w])")
PERCENT_RX = re.compile(r"\d[\d,.]*\s*%|\b\d[\d,.]*\s*percent\b")
MONEY_RX = re.compile(r"[$€£]\s?\d[\d,.]*[kKmM]?|\b\d[\d,.]*\s*(?:dollars|bucks|k a month|k/mo)\b")
SPELLED_NUMBER = set("""one two three four five six seven eight nine ten eleven twelve twenty
thirty fifty hundred thousand million billion half double triple""".split())

# Named tools / models / platforms / brands of the AI niche.
# (canonical name, category, regex). Order matters only for readability.
ENTITIES = [
    # models
    ('ChatGPT', 'model', r'\bchat ?gpt\b'),
    ('GPT', 'model', r'\bgpt[- ]?(?:3\.5|4o?|4\.\d|5|o1|o3)?\b'),
    ('Claude', 'model', r'\bclaude\b'),
    ('Claude Code', 'tool', r'\bclaude code\b'),
    ('Gemini', 'model', r'\bgemini\b'),
    ('Nano Banana', 'model', r'\bnano ?banana\b'),
    ('Llama', 'model', r'\bllama\b'),
    ('Mistral', 'model', r'\bmistral\b'),
    ('DeepSeek', 'model', r'\bdeep ?seek\b'),
    ('Qwen', 'model', r'\bqwen\b'),
    ('Kimi', 'model', r'\bkimi\b'),
    ('GLM', 'model', r'\bglm[- ]?\d*\b'),
    ('Grok', 'model', r'\bgrok\b'),
    ('Sora', 'model', r'\bsora\b'),
    ('Veo', 'model', r'\bveo[- ]?\d?\b'),
    ('Kling', 'model', r'\bkling\b'),
    ('Flux', 'model', r'\bflux\b'),
    ('Stable Diffusion', 'model', r'\bstable diffusion\b'),
    ('Seedance', 'model', r'\bseedance\b'),
    ('Whisper', 'model', r'\bwhisper\b'),
    ('Midjourney', 'tool', r'\bmid ?journey\b'),
    ('Runway', 'tool', r'\brunway\b'),
    ('Suno', 'tool', r'\bsuno\b'),
    ('ElevenLabs', 'tool', r'\beleven ?labs?\b|\b11 ?labs\b'),
    ('HeyGen', 'tool', r'\bhey ?gen\b'),
    ('Manus', 'tool', r'\bmanus\b'),
    ('Lovable', 'tool', r'\blovable\b'),
    ('Bolt', 'tool', r'\bbolt\.?(?:new)?\b'),
    ('Replit', 'tool', r'\breplit\b'),
    ('Copilot', 'tool', r'\bco-?pilot\b'),
    ('Cursor', 'tool', r'\bcursor\b'),
    ('Windsurf', 'tool', r'\bwindsurf\b'),
    ('v0', 'tool', r'\bv0(?:\.dev)?\b'),
    ('n8n', 'tool', r'\bn8n\b'),
    ('Zapier', 'tool', r'\bzapier\b'),
    ('Make', 'tool', r'\bmake\.com\b|\bmake\.?com\b|\bintegromat\b'),
    ('Notion', 'tool', r'\bnotion\b'),
    ('Airtable', 'tool', r'\bair ?table\b'),
    ('Perplexity', 'tool', r'\bperplexity\b'),
    ('LangChain', 'tool', r'\blang ?chain\b'),
    ('CrewAI', 'tool', r'\bcrew ?ai\b'),
    ('Apify', 'tool', r'\bapify\b'),
    ('Clay', 'tool', r'\bclay\.com\b|\bclay\b(?= (?:to|for|and|is))'),
    ('Instantly', 'tool', r'\binstantly\.ai\b'),
    ('Smartlead', 'tool', r'\bsmart ?lead\b'),
    ('GoHighLevel', 'tool', r'\bgo ?high ?level\b|\bghl\b'),
    ('Descript', 'tool', r'\bdescript\b'),
    ('CapCut', 'tool', r'\bcap ?cut\b'),
    ('Opus Clip', 'tool', r'\bopus ?clip\b'),
    ('Gamma', 'tool', r'\bgamma\.app\b'),
    ('Loom', 'tool', r'\bloom\b'),
    ('Framer', 'tool', r'\bframer\b'),
    ('Webflow', 'tool', r'\bweb ?flow\b'),
    ('Vercel', 'tool', r'\bvercel\b'),
    ('Supabase', 'tool', r'\bsupabase\b'),
    ('Firebase', 'tool', r'\bfirebase\b'),
    ('Canva', 'tool', r'\bcanva\b'),
    ('Figma', 'tool', r'\bfigma\b'),
    ('Excel', 'platform', r'\bexcel\b'),
    ('Google Sheets', 'platform', r'\bgoogle sheets?\b|\bspreadsheets?\b'),
    ('Gmail', 'platform', r'\bgmail\b'),
    ('Slack', 'platform', r'\bslack\b'),
    ('WhatsApp', 'platform', r'\bwhats ?app\b'),
    ('Telegram', 'platform', r'\btelegram\b'),
    ('Discord', 'platform', r'\bdiscord\b'),
    ('Instagram', 'platform', r'\binstagram\b|\big\b(?!\w)'),
    ('TikTok', 'platform', r'\btik ?tok\b'),
    ('YouTube', 'platform', r'\byou ?tube\b'),
    ('LinkedIn', 'platform', r'\blinked ?in\b'),
    ('X (Twitter)', 'platform', r'\btwitter\b|\bx\.com\b'),
    ('Reddit', 'platform', r'\breddit\b'),
    ('GitHub', 'platform', r'\bgit ?hub\b'),
    ('Shopify', 'platform', r'\bshopify\b'),
    ('HubSpot', 'platform', r'\bhub ?spot\b'),
    ('Salesforce', 'platform', r'\bsales ?force\b'),
    ('Stripe', 'platform', r'\bstripe\b'),
    ('Calendly', 'platform', r'\bcalendly\b'),
    ('Google Maps', 'platform', r'\bgoogle maps\b'),
    # labs / brands
    ('OpenAI', 'brand', r'\bopen ?ai\b'),
    ('Anthropic', 'brand', r'\banthropic\b'),
    ('Google', 'brand', r'\bgoogle\b'),
    ('Meta', 'brand', r'\bmeta\b'),
    ('Microsoft', 'brand', r'\bmicrosoft\b'),
    ('Nvidia', 'brand', r'\bnvidia\b'),
    ('Apple', 'brand', r'\bapple\b'),
    ('Amazon', 'brand', r'\bamazon\b'),
    ('Adobe', 'brand', r'\badobe\b'),
    ('xAI', 'brand', r'\bx ?ai\b'),
    ('ByteDance', 'brand', r'\bbyte ?dance\b'),
]
ENTITY_RX = [(name, cat, re.compile(rx)) for name, cat, rx in ENTITIES]

# Technical vocabulary of the niche — not brands, but domain terms.
TECHNICAL = set("""api apis agent agents workflow workflows automation automate prompt prompts
prompting model models llm llms token tokens context window fine tune fine-tuning rag embedding
embeddings vector database webhook webhooks node nodes endpoint json python javascript code
repo repository github integration integrate pipeline dataset training inference latency
parameters temperature system prompt mcp sdk cli terminal""".split())

# -ly words that are not adverbs
NOT_ADVERB_LY = set("""only family reply apply supply early likely ugly july italy rely holy
silly ally belly rally jelly fully""".split())

WORD_RX = re.compile(r"[a-z0-9']+")
SENT_SPLIT_RX = re.compile(r'(?<=[.!?…])\s+')


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def tokenize(text):
    return WORD_RX.findall((text or '').lower())


def sentences(text, segments=None):
    """Sentences, with a documented fallback.

    Whisper punctuates 255 of the 266 usable transcripts. For the remaining 11 there
    is no punctuation at all, and splitting on nothing would report a 200-word
    "sentence". In that case each timed segment becomes one pseudo-sentence, which is
    what Whisper's own VAD/phrase boundaries give us, and `sentence_source` in the
    output says which of the two happened so no reader mistakes one for the other.
    """
    text = (text or '').strip()
    if not text:
        return [], 'empty'
    if re.search(r'[.!?…]', text):
        out = [s.strip() for s in SENT_SPLIT_RX.split(text) if s.strip()]
        if out:
            return out, 'punctuation'
    if segments:
        out = [str(s.get('t', '')).strip() for s in segments if str(s.get('t', '')).strip()]
        if out:
            return out, 'segments'
    return [text], 'whole_text'


def _top(counter, n):
    return [[k, v] for k, v in counter.most_common(n)]


def _ngrams(tokens, n):
    return [' '.join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _pct(part, whole):
    return round(part / whole, 6) if whole else None


def _per10s(count, dur):
    return round(count * 10.0 / dur, 4) if dur and dur > 0 else None


# ---------------------------------------------------------------------------
# the extractor
# ---------------------------------------------------------------------------

def features(text, segments=None, dur=None):
    """Every lexical feature for one transcript. Returns a JSON-serializable dict."""
    segments = segments or []
    low = (text or '').lower()
    toks = tokenize(text)
    n_tok = len(toks)
    sents, sent_source = sentences(text, segments)
    sent_toks = [tokenize(s) for s in sents]
    sent_lens = [len(t) for t in sent_toks if t]

    out = {
        'lexical_version': LEXICAL_VERSION,
        'sentence_source': sent_source,
        'words': n_tok,
        'chars': len(text or ''),
        'sentences': len(sents),
        'dur_s': dur,
    }
    if not n_tok:
        out['empty'] = True
        return out

    # --- size, pace, diversity -------------------------------------------
    out['wps'] = round(n_tok / dur, 4) if dur and dur > 0 else None
    out['avg_sentence_len'] = round(statistics.mean(sent_lens), 3) if sent_lens else None
    out['median_sentence_len'] = round(statistics.median(sent_lens), 3) if sent_lens else None
    if sent_lens:
        s = sorted(sent_lens)
        q = lambda p: s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))]  # noqa: E731
        out['sentence_len_dist'] = {'min': s[0], 'p25': q(.25), 'median': q(.5),
                                    'p75': q(.75), 'p90': q(.9), 'max': s[-1]}
    types = set(toks)
    out['types'] = len(types)
    out['ttr'] = round(len(types) / n_tok, 4)                       # length-sensitive
    out['rttr'] = round(len(types) / math.sqrt(n_tok), 4)           # root TTR, length-robust
    if n_tok >= 50:                                                  # moving-average TTR, w=50
        windows = [len(set(toks[i:i + 50])) / 50.0 for i in range(n_tok - 49)]
        out['mattr50'] = round(statistics.mean(windows), 4)
    else:
        out['mattr50'] = None
    out['content_words'] = sum(1 for t in toks if t not in STOPLIST)
    out['content_word_share'] = _pct(out['content_words'], n_tok)

    # --- keywords, keyphrases, repetition --------------------------------
    content = [t for t in toks if t not in STOPLIST and len(t) > 2 and not t.isdigit()]
    out['keywords'] = _top(collections.Counter(content), 15)
    bi = collections.Counter(g for g in _ngrams(toks, 2)
                             if not all(w in STOPLIST for w in g.split()))
    tri = collections.Counter(g for g in _ngrams(toks, 3)
                              if not all(w in STOPLIST for w in g.split()))
    out['keyphrases_bigram'] = _top(collections.Counter({k: v for k, v in bi.items() if v >= 2}), 10)
    out['keyphrases_trigram'] = _top(collections.Counter({k: v for k, v in tri.items() if v >= 2}), 10)
    repeated = {}
    for n in range(4, 9):                       # longest repeated phrases first
        for g, c in collections.Counter(_ngrams(toks, n)).items():
            if c >= 2:
                repeated[g] = c
    # drop a phrase that is only a prefix/suffix of a longer repeated one
    keys = sorted(repeated, key=len, reverse=True)
    kept = []
    for k in keys:
        if not any(k in longer and k != longer for longer in kept):
            kept.append(k)
    out['repeated_phrases'] = [[k, repeated[k]] for k in kept[:10]]
    out['repeated_phrases_n'] = len(repeated)

    # --- sentence openings and endings -----------------------------------
    openings = collections.Counter(' '.join(t[:2]) for t in sent_toks if t)
    endings = collections.Counter(' '.join(t[-2:]) for t in sent_toks if t)
    out['sentence_openings'] = _top(openings, 8)
    out['sentence_endings'] = _top(endings, 8)
    out['first_sentence'] = sents[0][:200] if sents else None
    out['last_sentence'] = sents[-1][:200] if sents else None

    # --- word classes (closed-class counts are exact) ---------------------
    c = collections.Counter(toks)
    count_of = lambda lex: sum(c[w] for w in lex)  # noqa: E731
    out['pronouns_n'] = count_of(PRONOUNS)
    out['second_person_n'] = count_of(SECOND_PERSON) + len(re.findall(r"\byou'(?:re|ll|ve|d)\b", low))
    out['first_person_n'] = count_of(FIRST_PERSON) + len(re.findall(r"\bi'(?:m|ve|ll|d)\b", low))
    out['first_person_authority_n'] = len(FIRST_PERSON_AUTHORITY_RX.findall(low))
    out['first_person_authority_examples'] = FIRST_PERSON_AUTHORITY_RX.findall(low)[:5]
    out['modals_n'] = count_of(MODALS) + len(MODAL_PHRASES_RX.findall(low))
    out['negations_n'] = count_of(NEGATIONS) + len(re.findall(r"n't\b", low))
    out['intensifiers_n'] = count_of(INTENSIFIERS)
    out['comparisons_n'] = count_of(COMPARISON_WORDS) + len(COMPARATIVE_RX.findall(low))
    out['superlatives_n'] = count_of(SUPERLATIVES) + len(SUPERLATIVE_RX.findall(low))

    # imperatives: sentence-initial verb from the list. Heuristic, see docstring.
    imps = [t[0] for t in sent_toks if t and t[0] in IMPERATIVE_VERBS]
    out['imperatives_n'] = len(imps)
    out['imperative_verbs'] = _top(collections.Counter(imps), 8)

    # questions
    q_flags = [s.rstrip().endswith('?') for s in sents]
    out['questions_n'] = sum(q_flags)
    rhet = 0
    for i, s in enumerate(sents):
        if not q_flags[i]:
            continue
        sl = s.strip().lower()
        if DIRECT_QUESTION_RX.search(sl):
            continue                     # a question aimed at the comments, not rhetoric
        answered = i + 1 < len(sents) and not q_flags[i + 1]
        if RHETORICAL_OPENERS.match(sl) or answered:
            rhet += 1
    out['rhetorical_questions_n'] = rhet
    out['questions_are_heuristic'] = False
    out['rhetorical_is_heuristic'] = True

    # --- numbers and evidence --------------------------------------------
    nums = NUMBER_RX.findall(text or '')
    out['numbers_n'] = len(nums)
    out['numbers'] = nums[:12]
    out['spelled_numbers_n'] = count_of(SPELLED_NUMBER)
    out['percentages_n'] = len(PERCENT_RX.findall(low))
    out['money_mentions_n'] = len(MONEY_RX.findall(text or ''))

    # --- semantic lexicons ------------------------------------------------
    for name, lex, rx in (('emotional', EMOTIONAL, None), ('fear', FEAR, None),
                          ('opportunity', OPPORTUNITY, None), ('urgency', URGENCY, URGENCY_RX),
                          ('identity', IDENTITY, IDENTITY_RX), ('novelty', NOVELTY, NOVELTY_RX),
                          ('proof', PROOF, PROOF_RX), ('cta_verb', CTA_VERBS, CTA_RX)):
        hits = [w for w in toks if w in lex]
        extra = len(rx.findall(low)) if rx else 0
        out[f'{name}_n'] = len(hits) + extra
        out[f'{name}_terms'] = _top(collections.Counter(hits), 6)
        out[f'{name}_per_100w'] = round((len(hits) + extra) * 100.0 / n_tok, 3)
    out['technical_n'] = sum(1 for w in toks if w in TECHNICAL)

    # --- named entities ---------------------------------------------------
    ents, by_cat = {}, collections.defaultdict(list)
    for name, cat, rx in ENTITY_RX:
        k = len(rx.findall(low))
        if k:
            ents[name] = k
            by_cat[cat].append(name)
    out['entities'] = dict(sorted(ents.items(), key=lambda kv: -kv[1]))
    out['entities_n'] = sum(ents.values())
    out['entities_distinct'] = len(ents)
    for cat in ('tool', 'model', 'platform', 'brand'):
        out[f'{cat}s_mentioned'] = sorted(by_cat.get(cat, []))
        out[f'{cat}s_n'] = len(by_cat.get(cat, []))

    # --- pos-lite (suffix heuristics, explicitly named) -------------------
    out['pos_lite_adverbs_ly'] = sum(1 for w in toks
                                     if w.endswith('ly') and len(w) > 4 and w not in NOT_ADVERB_LY)
    out['pos_lite_gerunds_ing'] = sum(1 for w in toks if w.endswith('ing') and len(w) > 5)
    out['pos_lite_past_ed'] = sum(1 for w in toks if w.endswith('ed') and len(w) > 4)

    # --- claims and rates -------------------------------------------------
    # Claim heuristic: a declarative sentence (not a question, not opening with an
    # imperative) that either carries a number or a copula/future verb. It over-counts
    # narration ("it is easy") and under-counts claims made as a fragment.
    claims = 0
    for i, s in enumerate(sents):
        t = sent_toks[i]
        if not t or q_flags[i] or t[0] in IMPERATIVE_VERBS:
            continue
        if NUMBER_RX.search(s) or COPULA_RX.search(s.lower()):
            claims += 1
    out['claims_n'] = claims
    out['claims_is_heuristic'] = True
    out['claims_per_10s'] = _per10s(claims, dur)
    out['questions_per_10s'] = _per10s(out['questions_n'], dur)
    out['proof_per_10s'] = _per10s(out['proof_n'], dur)
    out['direct_address_per_10s'] = _per10s(out['second_person_n'], dur)
    out['direct_address_per_100w'] = round(out['second_person_n'] * 100.0 / n_tok, 3)
    out['numeric_evidence_n'] = out['numbers_n'] + out['percentages_n'] + out['money_mentions_n']
    out['numeric_evidence_per_10s'] = _per10s(out['numeric_evidence_n'], dur)
    out['numeric_evidence_per_100w'] = round(out['numeric_evidence_n'] * 100.0 / n_tok, 3)
    out['info_density'] = round(out['content_words'] / dur, 4) if dur and dur > 0 else None
    # specificity: the share of tokens that are a number, a named entity or a
    # technical term — "what this video names that a generic video would not"
    out['specificity'] = round((out['numbers_n'] + out['entities_n'] + out['technical_n'])
                               * 100.0 / n_tok, 3)

    # --- timing-based blocks (fallback before LLM beats exist) ------------
    out['blocks'] = timing_blocks(segments, dur, text)
    return out


def timing_blocks(segments, dur, text=None):
    """hook / body / tail by timecode, via `blocks.split` (repo root, SPEC §11).

    This is the stand-in for LLM beats: part-length statistics must exist before the
    ta-v1 analysis wave runs. `boundary='timing'` marks every number here as "by the
    clock", not "by meaning" — `engine/features.py` overwrites them with real beat
    durations once `beats` is populated.
    """
    if not segments:
        return {'boundary': 'timing', 'available': False}
    try:
        import blocks as blocks_mod
        hook, body, tail = blocks_mod.split(segments, dur)
    except Exception:                                       # pragma: no cover
        return {'boundary': 'timing', 'available': False}
    out = {'boundary': 'timing', 'available': True, 'hook_rule': 'blocks.split (5 s / 15 % tail)'}
    for name, segs in (('hook', hook), ('body', body), ('tail', tail)):
        txt = ' '.join(str(s.get('t', '')).strip() for s in segs).strip()
        toks = tokenize(txt)
        speech = sum(float(s.get('e', 0)) - float(s.get('s', 0)) for s in segs)
        span = (max(float(s.get('e', 0)) for s in segs) - min(float(s.get('s', 0)) for s in segs)) if segs else 0.0
        out[f'{name}_words'] = len(toks)
        out[f'{name}_speech_s'] = round(speech, 3)
        out[f'{name}_span_s'] = round(span, 3)
        out[f'{name}_wps'] = round(len(toks) / speech, 3) if speech > 0 else None
        out[f'{name}_segments'] = len(segs)
        out[f'{name}_share_of_words'] = None
        out[f'{name}_text'] = txt[:400]
    total_w = out['hook_words'] + out['body_words'] + out['tail_words']
    for name in ('hook', 'body', 'tail'):
        out[f'{name}_share_of_words'] = _pct(out[f'{name}_words'], total_w)
        out[f'{name}_share_of_dur'] = _pct(out[f'{name}_span_s'], dur) if dur else None
    return out


# ---------------------------------------------------------------------------
# run over the corpus
# ---------------------------------------------------------------------------

def transcript_rows(con, code=None):
    """Usable transcripts joined with the newest known duration."""
    sql = """
    SELECT t.code, t.text, t.segments, m.dur, m.play, m.username, m.pk_user
    FROM transcripts t
    JOIN (%s) m ON m.code = t.code
    WHERE COALESCE(t.words,0) > 0
    """ % corpus.LATEST_SQL
    params = ()
    if code:
        sql += ' AND t.code = ?'
        params = (code,)
    rows = []
    for r in con.execute(sql, params):
        try:
            segs = json.loads(r['segments'] or '[]')
        except (TypeError, ValueError):
            segs = []
        if not segs:
            continue
        rows.append({'code': r['code'], 'text': r['text'], 'segments': segs, 'dur': r['dur'],
                     'username': r['username'], 'pk_user': r['pk_user']})
    return rows


def run_all(con, code=None, verbose=True):
    """Compute lexical features for every usable transcript and merge-write them into
    `video_features.features_json['lexical']`. Other keys in that JSON are preserved."""
    corpus.ensure_tables(con)
    rows = transcript_rows(con, code)
    done = 0
    for r in rows:
        f = features(r['text'], r['segments'], r['dur'])
        corpus.merge_features(con, r['code'], 'lexical', f)
        done += 1
        if verbose and done % 50 == 0:
            print(f'  ... {done}/{len(rows)}')
    con.commit()
    if verbose:
        print(f'lexical: {done} transcripts -> video_features.features_json["lexical"]')
    return done


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    db = argv[argv.index('--db') + 1] if '--db' in argv else corpus.DB_PATH
    code = argv[argv.index('--code') + 1] if '--code' in argv else None
    con = corpus.connect(db)
    if code and '--write' not in argv:
        rows = transcript_rows(con, code)
        if not rows:
            print(f'no usable transcript for {code}')
            return 1
        print(json.dumps(features(rows[0]['text'], rows[0]['segments'], rows[0]['dur']),
                         ensure_ascii=False, indent=1))
    else:
        run_all(con, code)
    con.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
