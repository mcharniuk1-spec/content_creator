# -*- coding: utf-8 -*-
"""Темы выведены из чтения ~400 подписей окна, а не придуманы заранее.
Первый проход — якоря, второй — ручной разбор остатка (см. MANUAL)."""
TOPICS = [
 ("Бесплатный доступ и обход платы", r"free llm|omniroute|omni route|token harbor|deepseek harness|for free|completely free|free forever|unlimited .*free|free version|without paying|stop paying|free trial|free access|₹4,000|free gemini|free claude"),
 ("Claude Code: скиллы, плагины, команды", r"claude code|claude skill|skills? for claude|plugin|slash command|/design|agents\.md|claude desktop|settings|setup guide|commands"),
 ("Готовый репозиторий с GitHub", r"github repo|open.?sourced|open source|repo\b|stars\)|\d+,?\d*\+? stars"),
 ("Сборка агентов и мультиагентные системы", r"\bagents?\b.*(build|team|swarm|sub.?agent|orchestr)|team of \d+ ai agents|multi.?agent|agent loop|specialist sub agents|agentic os|build.*agent"),
 ("Лидогенерация, скрейпинг, CRM", r"lead|scrape|scraping|google maps|cold email|crm\b|prospect|outreach|smartlead|follow.?up"),
 ("AI-видео и производство контента", r"video|reel|seedance|heygen|veed|opusclip|faceless|clip|animation|film|shorts|editing|thumbnail|image gener|logo"),
 ("AI-агентство как бизнес", r"agency|consultant|consulting|\$\d+k?/?mo|client|retainer|ghl|gohighlevel|sell ai|first client|make money|side hustle|passive income"),
 ("Токены, стоимость, лимиты", r"token|billed|usage limit|overpay|expensive|cost|cheaper|burns? token|save.*%"),
 ("Новости моделей и лабораторий", r"anthropic|openai|gemini|nvidia|glm|qwen|kimi|minimax|deepseek|sam altman|dario|google just|china just|launched|dropped|announce|update"),
 ("Карьера, резюме, найм", r"resume|job\b|hiring|career|certification|interview|ats\b|salary|\$\d+k (a year|salary)|engineer role"),
 ("Голосовые агенты и телефония", r"voice agent|phone call|receptionist|calls?\b.*(answer|handle)|voice ai|elevenlabs|fish audio|voice clon"),
 ("Память и контекст агентов", r"memory|context window|remembers|forget|context\b"),
 ("Дизайн и сайты через AI", r"website|landing page|figma|design|3d|ui\b|frontend|dashboard"),
 ("Личное, мотивация, влог", r"^i\b|my journey|discipline|mindset|identity|i miss|before anyone|it took me|day \d+ of|vlog|be, do, have|success"),
 ("Развлечение и конспирология", r"teleport|quantum|wormhole|time.?travel|government|aliens|plasma|robot fighting|kevin durant|elon musk on"),
 ("Мемы", r"#meme|#aimeme|pov:|like it's|literally|😭|💀"),
]
# Ручные назначения после чтения остатка — заполняется во втором проходе
MANUAL = {}

EXTRA = [
 ("AI в конкретном бизнес-процессе", r"in your business|for business|business owner|your workflow|sales process|increase sales|every business|worth using in your business|where ai (actually )?fits|business needs|automate (your |the )?(business|process|workflow)|real business|operations|small business"),
 ("Как думать и работать с AI", r"you don.t need better prompt|right skill|think for you|do the thinking|understand(ing)? it|never tell you it.s wrong|two ways to use ai|use ai effectively|prompt(s)? aren.t the problem|blank|default settings|most people (just )?(type|use)"),
 ("Обучение и навыки", r"skill pack|practice plan|30.day|learn(ing)? (ai|to)|course|guide|tutorial|beginner|how i explain|breakdown"),
 ("Продуктивность и офисные инструменты", r"excel|copilot|spreadsheet|slides|pitch deck|notion|slack|calendar|notes|meeting"),
 ("Только призыв, без темы в подписи", r"^comment [\u201c\"']?\w+[\u201d\"']?( and i.ll send( it)?( over)?)?[\s\W]*$|^drop [\u201c\"']?\w+|^comment \w+ and i.ll (send|share)"),
]
EXTRA2 = [
 ("Личное, мотивация, влог", r"habits|surround yourself|perspective|ambition|hustle|discipline|mindset|nobody ever got rich|my life|day in my|gym|excuses|6 months to|it took me|old me|i miss|i.ve been|i used to|best time to be building|saturday build|august \d+:"),
 ("Обзор инструмента", r"wait until the end|might be one of those tools|this tool|new tool|tool that|check (this|it) out|i tested|i tried|found (a|this|something)|just dropped|meet \w+|introducing"),
 ("Критика и скепсис про AI", r"slop|same content|everyone starts producing|dangerous part|problem ye hai|wrong answer|don.t know as much|too easy|panic|scariest|not a thousand dollars|almost none of them test"),
 ("Программирование и код", r"python|syntax|code\b|coding|developer|engineer|frontend|javascript|api\b"),
 ("Стартапы и венчур", r"\bvc\b|pre.?seed|cheque|funding|startup idea|founder|raise|investor|airbnb didn.t start"),
 ("Виральные видеоэффекты", r"#viraleffect|viral .*effect|sky (car )?drop|assemble effect|cinematic|anime scene|logo animation"),
]
TOPICS = TOPICS + EXTRA + EXTRA2
