# 14. Topic Analysis

**Denominators.** 266 of the 268 analysis-ready reels carry a ta-v1 `topic` label, spread across 27
distinct values. The chart below draws the twelve largest cells, which together hold **205** reels;
groups under 5 reels are dropped from the plot but kept in the table. **No topic cell reaches the
SUFFICIENT_SAMPLE threshold** of n ≥ 30 and ≥ 8 creators, so every row is PROBABLE at best and 9 of the
27 are INSUFFICIENT [I-30]. Baselines for comparison, all inside the analysed set: median `view_lift`
**2.03**, median `robust_z` **1.26**, median share rate **0.0152** (n=268), median save rate **0.0278**
(n=245).

![Topic vs performance — twelve largest cells, n=205](reports/charts/topic_vs_performance.png)

## The full topic table

| topic | n | creators | median view_lift | median robust_z | share/1k | save/1k |
|---|---:|---:|---:|---:|---:|---:|
| Сборка агентов и мультиагентные системы (agent building) | 27 | 19 | **6.63** | 2.06 | 17.4 | 31.7 |
| AI-видео и производство контента | 23 | 19 | 2.12 | 1.75 | 18.0 | 34.3 |
| Claude Code: скиллы, плагины, команды | 22 | 17 | **4.36** | 2.12 | 15.3 | 37.5 |
| Бесплатный доступ и обход платы (free access) | 21 | 16 | 1.17 | 1.05 | **22.0** | 37.3 |
| Новости моделей и лабораторий (model news) | 21 | 17 | 2.30 | 1.16 | 18.3 | **9.7** |
| Дизайн и сайты через AI | 19 | 16 | 2.70 | 1.14 | 13.5 | 23.7 |
| Лидогенерация, скрейпинг, CRM | 15 | 10 | 2.27 | 1.66 | 16.5 | 30.2 |
| AI-агентство как бизнес | 14 | 9 | 0.68 | 1.13 | 12.8 | 21.3 |
| Обзор инструмента (tool review) | 12 | 11 | 5.67 | 1.65 | 17.8 | 21.6 |
| Готовый репозиторий с GitHub | 12 | 8 | 4.03 | 1.54 | 17.4 | **48.7** |
| Как думать и работать с AI | 10 | 8 | **0.44** | 0.69 | 9.4 | 20.8 |
| Карьера, резюме, найм | 9 | 8 | 2.72 | 1.27 | 12.8 | 22.9 |
| Стартапы и венчур | 9 | 9 | 2.49 | 0.71 | 14.4 | 31.0 |
| Программирование и код | 9 | 9 | 1.63 | 1.04 | 10.4 | 22.7 |
| Обучение и навыки | 8 | 8 | **0.57** | 0.38 | 10.6 | 26.2 |
| **AI в конкретном бизнес-процессе** | **8** | **8** | **0.65** | **0.85** | **4.0** | **13.3** |
| Личное, мотивация, влог | 6 | 6 | 1.34 | 0.89 | 6.2 | 7.8 |
| Токены, стоимость, лимиты | 5 | 5 | 0.89 | 0.57 | 5.7 | 14.8 |
| Голосовые агенты и телефония | 4 | 4 | 4.55 | 3.11 | 15.2 | 25.8 (INSUFFICIENT) |
| Развлечение и конспирология | 3 | 3 | 18.32 | 1.48 | 6.5 | 13.6 (INSUFFICIENT) |
| remaining 7 cells (n ≤ 3 each) | ≤3 | ≤3 | — | — | — | INSUFFICIENT |

Read down the `view_lift` column and the niche's shape is unambiguous: **reach concentrates where the
subject is a thing a builder can assemble** — agents (6.63×), Claude Code skills (4.36×), a ready-made
GitHub repo (4.03×), a tool review (5.67×) — and collapses where the subject is a way of thinking:
"how to think and work with AI" (0.44×), "learning and skills" (0.57×). The save column tells a
different and equally consistent story: **the topic people keep is the topic that hands over a file**.
Ready-made GitHub repos carry 48.7 saves per 1 000 against a corpus median of 27.8, while model news —
which reaches perfectly adequately at 2.30× — is saved at **9.7 per 1 000**, roughly a third of the
median. Novelty gets attention and is not kept.

## The cell that matters most to M2 is the weakest one

`AI в конкретном бизнес-процессе` — AI inside a concrete business process, which is M2's declared
territory — is **n=8 across 8 creators, median view_lift 0.65, robust_z 0.85, share rate 0.0040 and
save rate 0.0133**. The share rate is roughly a quarter of the analysed-set median. It is simultaneously
one of the smallest cells that is not suppressed and the weakest on three of four metrics. The
neighbouring cell M2 is positioned to refuse, agent building, is three times larger and ten times higher
on lift [I-25].

The honest reading is that both facts are real and neither is a verdict. The corpus contains eight reels
on M2's subject; eight reels across eight creators cannot establish that the subject fails, and the
selection bias runs the other way — these eight are already among the top of their authors' output. What
the cell does establish is that **nobody in the measured niche is producing this content at volume**,
and PRODUCTION.md's earlier framing of the same gap ("the topic is open for whoever treats it as content
rather than a pitch") is confirmed in direction while its supporting numbers, drawn from a different and
smaller export, are not reproduced here.

**Transcript reading.** The gap is audible in the language. The agent-building topic's own top reel,
[DbYh2P-MQnj](https://www.instagram.com/reel/DbYh2P-MQnj/) (2 771 182 plays, 94.8×), opens "This is what
it looks like when 137 AI agents run an entire company. Seven departments and it's not just a crazy
visual." (hook, 0.0–10.8 s) and never once names a person responsible for anything. Its closest
competitor for shape, [DcbnTAtxb8C](https://www.instagram.com/reel/DcbnTAtxb8C/), describes four
departments and 33 agents in three grammatically identical sentences. The energy is real; the process
owner is absent. That absence is precisely POSITIONING.md §8's "AI-agent demos without a real process
owner" and precisely the space M2 says it will occupy.

**Visual reading.** The topic's visual language is already invented and it is not the niche's default.
DbYh2P-MQnj is a held `B_ROLL_PROCESS`: a camera filming a curved monitor showing a live network diagram
with a hand pointing at labelled clusters. fa-v1 records the proof visual as an openable agent card
naming what each agent replaces. That is a process artefact on camera — the exact visual grammar a
Teardown needs — being used to describe an architecture rather than a workflow.

## Strategic implication

Take the agent-building topic's **energy and its visual grammar** and refuse its **shape**. Build the
same visible artefact, film it the same way, and attach it to one named repeated process with a named
owner and an explicit AI boundary — which is the M2 angle formula in RULES.md §4 and which nobody in
this corpus does. Two corollaries follow from the table. Do not build a pillar on model news: it reaches
and is not kept (9.7 saves/1 000), and POSITIONING.md §8 excludes it anyway. Do not expect the
business-process topic to reach like agent building in its first months; select and judge M2 Teardowns
on shares and saves per 1 000, not on view lift, because the topic's own measured weakness is
concentrated in reach.

**Confidence: PROBABLE** for every individual topic cell (no cell reaches n ≥ 30 with ≥ 8 creators; the
largest is 27 reels across 19 creators). **INSUFFICIENT** for the nine cells at n ≤ 4, which are printed
with their `suppressed_reason` rather than deleted. **RELIABLE** only for the meta-finding that the topic
grid is too thin to answer topic questions [I-30]. Nothing here is causal: these are medians of a
pre-selected sample, and a topic's median says nothing about what would happen if a different creator
made the same reel.
