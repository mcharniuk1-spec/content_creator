# Аудит аналитики: транскрипты и кадры в конвейере Макса, и метод на следующий прогон

8 сентября 2026. Читались: `data/max-latest-pipeline.md` и `data/max-latest/`, `data/max-pipeline.md`
и `data/max/`, `notion-raw/01`, `03`, `04`, `90`, `91`, наши `data/radar-data.md`,
`data/transcripts-available.md`, `data/topics.csv`, `data/angles.md`, бренд `06-formats.md` и
`04-voice.md`.

Примеры в разделах 4 и 5 собраны из **настоящих** данных: база `radar-0907.db` и кадры с диска
`data/frames/DbVq4mwz38L/`. Транскрипт прочитан целиком, девять кадров и контактный лист
просмотрены глазами. Английские цитаты приводятся дословно.

---

## 1. Что реально произошло, по стадиям

Ниже ветка `Latest` (6-8 сентября); состояние релиза 5 сентября вынесено под таблицу.

| Стадия | Что запущено | На скольких рилсах | Что проверено | Что не проверено | Статус-коды |
|---|---|---|---|---|---|
| Входные данные | Импорт нашего снимка радара, `import-legacy-db`, живого сбора не было | 2 352 рилса, 100 аккаунтов | Идентичности, дубли, карантин | Свежесть: метрики датированы 1 сентября | `"hikerapi_calls": 0` (`data/max-pipeline.md:62`) |
| ASR | Faster-Whisper small, CPU int8, `word_timestamps=True`, `beam_size` из конфига, хеш-привязка beam | 1 062 непустых машинных транскрипта из 2 352 (45,2 %) | Непустота текста и хеши всех 1 062 | Акустическая точность, язык, реальная длительность речи | 954 normal, 108 timing-flagged, 108 failures, 24 empty/unverified, 1 158 not attempted (`data/max-latest-pipeline.md:53`) |
| Проверка транскриптов | Полное чтение с визуальной сверкой | 18 из 1 062 | 18 референсов, 262 сэмпла контактных листов, 64 точных наблюдения | Остальные 1 044: «lexical inventory», не смысловой разбор | `"The other 1,044 transcripts have lexical inventory but still need detailed semantic review."` (`data/max-latest-pipeline.md:53`) |
| Пилот восстановления ASR | Пять окон, один чанк с ретраем | 1 рилс | Факт исполнения | Границы окон, тайминги, акустика | `"aggregate_observation_state": "SUSPICIOUS_TIMINGS"`, `"analysis_ready": false`, `"approved": false` (`data/max-latest-pipeline.md:55`) |
| Извлечение кадров | Индексированный декод, обычные сэмплы плюс кандидаты смены плана, порог реза 0.32 | 1 194 набора кадров, 19 808 изображений, 9 625 кандидатов реза | Хеши и PTS кадров | Что на кадрах: интерпретация не делалась для корпуса | `"1,194 frame sets; 19,808 extracted images: extraction coverage, not a claim that every image was interpreted."` (`notion-raw/01-m2-signal-studio-7sep-release.md:33`) |
| Чтение кадров | Ручной осмотр контактных листов | 3 рилса, 64 кадра, 17 коллажей | Технические свидетельства | Смысл сцен | `"semantic_state": "CANDIDATE_NOT_ACCEPTED"` (`data/max-latest-pipeline.md:41`) |
| Свидетельства сцен | `scene_media.py`, план 2/4/6 кадров на сцену, максимум 48 на видео | Ограниченный пилот, файлы вне git | Ревью прошло | Приёмка не дана, файлы в gitignore | `"source_media_included": false`, `"raw_transcripts_included": false` (`data/max-latest-pipeline.md:41`, `:57`) |
| Раскадровки карточек | Remotion, иллюстрации к новым сценариям | 10 карточек, 70 сцен | Соответствие сценарию | Ничего из исходных рилсов | `"kind": "ILLUSTRATED_CONTACT_SHEET"`, `"Composition guide only; not an owner take, product output, or production asset binding."` (`data/max-latest-pipeline.md:30`) |
| Генерация карточек | 10 карточек `m2.editorial-scriptcard.v1`, 3 хука, 7 сцен, хеш источника | 10 | Редакционное ревью, 14 локальных проверок | Съёмка, речь, монтаж | `"editorial_review_state": "ACCEPTED_WITH_LIMITATIONS_OWNER_SHOOT_PENDING"`, все ассеты `AWAITING_OWNER_ASSET` (`data/max-latest-pipeline.md:61`) |

Для сравнения, релиз 5 сентября: кадры вообще не извлекались, все 2 352 рилса имели
`'observation_state': 'NOT_ATTEMPTED'`, `'reason_code': 'MISSING_SOURCE_MEDIA'`
(`data/max-pipeline.md:67`), транскрипты были чужие, унаследованные, помеченные
`reason_code='LEGACY_ASR_PROVENANCE_AND_MEDIA_QA_UNVERIFIED'` (`data/max-pipeline.md:74`),
а 64 «кадра» были синтетическим рендером Remotion, а не кадрами конкурентов
(`data/max-pipeline.md:69`).

Главное движение за трое суток: покрытие выросло с 3,784 % до 45,2 %, и впервые появились
настоящие декодированные кадры. Глубина чтения не изменилась: 18 прочитанных транскриптов.

---

## 2. Выводы агента Макса и подтверждаются ли они данными

| Вывод (дословно) | Где | Подтверждается |
|---|---|---|
| `"The strongest direction for this slate is to show a small, recognisable failure and let the viewer see how to handle it"` | `notion-raw/01:23` | **Частично.** Как редакционный выбор допустим, и он сам это оговаривает строкой ниже: `"That is an editorial conclusion from the selected material, not a claim that we measured a winning formula."` Но выбор сделан на 18 рилсах из 1 062, отобранных по индексу просмотров, без контрольной группы. |
| `"concrete work problems can be made legible with an input, a visible gap, and a next decision"` | `notion-raw/04:25` | **Частично.** Структура правдоподобна и совпадает с нашим брендом, но выведена из 18 примеров и не проверена на тех, кто не залетел. Он сам добавляет: `"We have not isolated which feature caused a Reel's views."` |
| `"A high ratio helps identify a post worth inspecting. It cannot establish that the hook caused the result"` | `notion-raw/01:38` | **Подтверждается.** Это корректная и важная оговорка, совпадающая с нашей методикой сравнения с медианой автора. |
| `"1,062 non-empty machine transcripts — 45.2% of Reels"` как показатель покрытия | `notion-raw/01:32` | **Подтверждается как счёт, не как качество.** Это состояние машины: 108 из них с подозрительными таймингами, акустика не проверена ни у одного. |
| `"18 selected Reels from 15 accounts: full-text and sampled-visual review used for the cards"` | `notion-raw/01:34` | **Подтверждается по факту, но не по достаточности.** 18 из 1 062 это 1,7 % корпуса; выводы о структуре формата на такой базе не отделимы от выбора примеров. |
| `"The ten demonstrations are authored fictional examples; they are not recorded model results."` | `notion-raw/01:47` | **Подтверждается.** Честная и правильная пометка; но она же означает, что доказательства в карточках нет вообще. |
| Учебник приёмов как источник структуры: `"It is a secondary, untrusted reference for editorial structure. It does not validate performance, audience demand, platform behavior, creator results"` | `notion-raw/03:41` | **Подтверждается как оговорка, не подтверждается как практика.** Девять приёмов вшиты в `skills/humanize-writing`, то есть влияют на каждую карточку, но ни один не сверен с нашими метриками. |
| `"Read the entire selected transcript and inspect timestamped visual evidence before assigning hook, problem, mechanism, demonstration, transition or CTA functions"` | `notion-raw/03:31` | **Не подтверждается исполнением.** Правило записано верно, но выполнено на 18 рилсах, а в словаре полей нет ни одной колонки под эти функции (раздел 3, пункт 2). |
| `"It proves deterministic data handling, explicit gaps, evidence lineage... It does not prove representative market coverage, creator-relative scoring, trend detection, audience demand, reach, ROI"` | `notion-raw/90:37`, обзор августовского бутстрапа, а не сентябрьский конвейер | **Подтверждается.** Точное описание того, что построено: контур происхождения данных, а не аналитика. |
| `BLOCKED for ... transcript coverage, full-video analysis, and frame-by-frame reference coverage` | `notion-raw/91:69`, дашборд North Hux, более ранний проект Макса | **Подтверждается.** Его собственный дашборд помечает ровно те три вещи, которые нужны для карточек. |

---

## 3. Проблемные места

**3.1. Транскрипты используются как словарный запас, а не как структура.**
Свидетельство: `"The other 1,044 transcripts have lexical inventory but still need detailed
semantic review."` (`data/max-latest-pipeline.md:53`), плюс поля словаря `Lexical text words`
(«Lexical word count projected from transcript analysis») и `Text fit candidate`
(`data/max-latest/m2-field-dictionary.csv:31`, `:34`).
Последствие для карточек: 1 044 транскрипта дают счётчик слов и метку релевантности, но не
дают ни одного ответа на вопрос «как этот рилс устроен». Карточки поэтому опираются на 18
примеров и на позиционирование, а не на корпус.

**3.2. Нет по-рилсового извлечения хук / проблема / решение / инструмент / CTA.**
Свидетельство: в словаре из 65 полей (`data/max-latest/m2-field-dictionary.csv`) поиск по
именам колонок по словам hook, problem, solution, tool, CTA даёт **ноль совпадений**.
Ближайшее, что есть: `Opening candidate`, `"Maker-coded opening/hook orientation candidate"`,
и тут же `"Maker-coded candidate; unreviewed labels do not support prevalence or causal
claims."` (`m2-field-dictionary.csv:32`).
Последствие: пять полей, которые Макс хочет получать, существуют только в голове того, кто
читал 18 транскриптов. Их нельзя ни отсортировать, ни сравнить, ни передать другому человеку.

**3.3. Кадры извлечены, но не просмотрены, поэтому кадр хука и кадр CTA неизвестны.**
Свидетельство: 19 808 изображений извлечено, `"Only the selected 262 samples across 18 Reels
received the detailed review"` (`notion-raw/04:45`), и `"semantic_state":
"CANDIDATE_NOT_ACCEPTED"` (`data/max-latest-pipeline.md:41`).
Последствие: главный тезис Макса («frames show the hook and the CTA and the dynamics») для
1 176 рилсов из 1 194 не выполнен. Динамика видео не измерена ни одним числом.

**3.4. Тайминги сцен придуманы, а не измерены.**
Свидетельство: карточки содержат `start_ms` / `end_ms` на семь сцен по 60 секунд
(`data/max-latest/M2-I01.json`), при том что `"Seven scenes and sixty seconds are this slate's plan, not a universal retention formula."` (`notion-raw/03:36`).
Последствие: ритм карточки задан шаблоном 7 по 8,5 секунды, а не наблюдённым ритмом реальных
рилсов. У нашего реального референса, например, семь резов на 53,5 секунды распределены
крайне неравномерно: пять из них в первые четыре секунды.

**3.5. Тайминги ASR не проверены, и это признано.**
Свидетельство: 108 транскриптов timing-flagged; пилот восстановления закончился
`"SUSPICIOUS_TIMINGS"`, `"analysis_ready": false`, `"approved": false`, и
`"A machine-observed recovery is not acoustic approval"` (`data/max-latest-pipeline.md:55`).
Последствие: любое утверждение «хук длится до 3 секунды» на этих данных недоказуемо. Пятиполевая
схема без флага качества тайминга унаследует эту же проблему.

**3.6. Прочитано 18 из 1 062, и это делает выборку самоподтверждающейся.**
Свидетельство: `notion-raw/01:34`, `notion-raw/04:26`.
Последствие: отобраны рилсы с высоким индексом просмотров, у них найдена общая структура,
и эта структура объявлена направлением слейта. Проигравшие рилсы не читались, поэтому
неизвестно, отличается ли структура победителей от структуры остальных.

**3.7. Учебник приёмов не сверен с результативностью.**
Свидетельство: девять приёмов и список отказов (`notion-raw/03:43-54`), при собственной
пометке `"It does not validate performance, audience demand, platform behavior, creator
results"` (`notion-raw/03:41`).
Последствие: приёмы влияют на каждую карточку через `skills/humanize-writing`, но ни один
не проверен на наших 3 612 строках рилсов, где такая проверка возможна.

**3.8. Позиционирование работает источником сценариев.**
Свидетельство: `"Positioning consumed — knowledge/m2-positioning.md"`
(`data/max-latest-pipeline.md:24`), фикстуры карточек помечены
`"state": "DESIGNED_NOT_MODEL_EXECUTED"` (`data/max-latest/M2-I01.json`), и
`"The ten demonstrations are authored fictional examples"` (`notion-raw/01:47`).
Последствие: карточка рассказывает, во что мы верим, а не то, что мы проверили. По нашему
бренду это прямой отказ: `"Is the proof ours?"` (`m2lab-brand/brand/06-formats.md:94`).

**3.9. Дизайн-пак удалён на ветке.**
Свидетельство: `"the entire design/ brand-pack tree (logos, tokens, templates, palette,
typography, ~90 files) and PRODUCTION.md ... are removed on Latest"`
(`data/max-latest-pipeline.md:18`).
Последствие: карточки нечем визуально проверить, обложки в структуре v2 собрать не из чего,
и раскадровки рисуются вне бренда.

**3.10. Хеш-привязка защищает происхождение, а не качество.**
Свидетельство: `source_candidate_sha256`, `card_sha256`, `storyboard_sha256`
(`data/max-latest-pipeline.md:61`), при том что привязанный источник это те самые 18
транскриптов с непроверенной акустикой.
Последствие: можно доказать, что карточка сделана из конкретного пакета, и нельзя доказать,
что пакет что-то значит. Аккуратность процесса подменяет проверку содержания.

**3.11. То же самое и у нас: наши кадры не покрывают CTA.**
Свидетельство: у реального рилса `DbVq4mwz38L` девять кадров на фиксированных позициях,
последний на 44,6 с, при длительности 53,5 с; речь CTA начинается на 47,8 с
(таблица сегментов, раздел 5). То есть кадр CTA у нас физически отсутствует.
Это ровно та ошибка, о которой Макс предупреждает: `"Do not infer an unseen opening from a
later presenter frame or assume the final sampled frame contains a CTA."` (`notion-raw/03:31`).
Последствие: наша схема кадров тоже требует переделки, а не только его.

---

## 4. Схема транскрипта на следующий прогон

Одна запись на рилс. Заполненный пример ниже собран из **настоящих** данных:
`radar-0907.db`, таблицы `transcripts`, `reels`, `scores`, `deepdives`, код `DbVq4mwz38L`,
автор `@heystevetan`. Транскрипт прочитан целиком (33 сегмента, 213 слов).

```json
{
  "code": "DbVq4mwz38L",
  "author": "heystevetan",
  "duration_s": 53.5,
  "language": "en",
  "words": 213,
  "metrics": {
    "plays": 439974,
    "author_median_play": 15832,
    "z_ig": 5.0,
    "shares_per_1k": 27.86,
    "saves_per_1k": 53.96,
    "comments_per_1k": 26.59,
    "baseline_n": 5
  },
  "extraction": {
    "hook": {
      "text": "This 17 year old fixed Manichat's biggest problem. He made it free.",
      "start_s": 0.0,
      "end_s": 3.2,
      "speaker": "presenter_voiceover",
      "claim_type": "third_party_fact"
    },
    "problem": {
      "text": "Manichat is what most people pay for this, anywhere from $15 to $69 a month. And the price climbs with how many people trigger your automation. So a reel that pops off actually raises your bill.",
      "start_s": 9.9,
      "end_s": 19.8,
      "whose": "creator or SMB running Instagram comment-to-DM automation",
      "workflow": "auto-reply in DM on a comment keyword",
      "friction": "the cost grows exactly when the content works"
    },
    "solution": {
      "text": "OpenReply does the core of it for nothing. Set a keyword on a post and everyone who comments it gets your link in seconds. Swap in a tracked link and you can see exactly who clicked. You can even run several accounts from one dashboard with your whole team on it.",
      "start_s": 19.8,
      "end_s": 32.2,
      "human_step_named": false,
      "limitation_named": "Setup does take some technical work (39.2-42.1 s); hosting a few dollars a month (32.2-39.2 s)"
    },
    "tool": {
      "named": true,
      "primary": "OpenReply (open-source, self-hosted)",
      "incumbent_compared": "ManyChat",
      "assistant_mentioned": "Claude Code",
      "asr_note": "ASR rendered it as 'cloud code' at 45.6-46.6 s; corrected by a human against the on-screen README frame at 44.6 s",
      "start_s": 3.2,
      "end_s": 47.8
    },
    "cta": {
      "text": "Comment auto and I'll send you the entire setup process and follow me to keep track of the best open source AI tools.",
      "start_s": 47.8,
      "end_s": 53.5,
      "action_asked": "write the word 'auto' in the comments; follow the account",
      "class": "comment_bait",
      "m2_allowed": false,
      "m2_rule": "06-formats.md:60 A request for a comment, a word or a tag in exchange for a file or a link."
    }
  },
  "proof_shown": [
    {"kind": "screen", "what": "ManyChat pricing page, $139/mo Advanced and $69/mo Business", "at_s": 1.2},
    {"kind": "screen", "what": "Instagram comment thread with automatic 'Repo' replies", "at_s": 8.9},
    {"kind": "number", "what": "$39 Bill amount on a phone mockup next to a 101K-view reel", "at_s": 17.8},
    {"kind": "screen", "what": "dashboard: weekly counts and Recent Activity Sent / Queued", "at_s": 26.8},
    {"kind": "file", "what": "repo README: Tech stack, Contributing, Set it up with your AI assistant", "at_s": 35.7}
  ],
  "quality": {
    "asr_model": "whisper local via radar deep.py",
    "asr_confidence": null,
    "asr_confidence_note": "our transcripts table stores only lang, words, text, segments; confidence must be added",
    "timings_flagged": false,
    "verified_by_human": true,
    "verified_by": "analytics-audit, 2026-09-08",
    "verified_scope": "all 33 segments read; five fields and timings taken from segment boundaries"
  }
}
```

### Правила извлечения

1. **Хук** это первое произнесённое утверждение, целиком закрывающееся до 3,0 с. Если фраза
   пересекает границу, берём её целиком и записываем реальный `end_s` (здесь 3,2 с), а не
   обрезаем по трём секундам. Вопрос без утверждения хуком не считается: он размечается как
   `claim_type: "question"` и помечается слабым.
2. **Проблема** обязана иметь владельца (`whose`) и процесс (`workflow`). Формулировка «людям
   дорого» без того, кто и в какой работе платит, к заполнению не принимается. Если в речи
   проблемы нет, поле остаётся `null`, и рилс идёт в отдельную корзину «demo without a
   problem»: это тоже наблюдение, а не пропуск.
3. **Решение** это механизм, а не название. Записываются три вещи: что делает машина, что
   остаётся человеку (`human_step_named`), какое ограничение названо вслух
   (`limitation_named`). Если автор не назвал ни ограничения, ни человеческого шага, оба поля
   `false` / `null`, и это сильный сигнал против переноса приёма к нам.
4. **Инструмент** размечается как `named: true/false`. При `true` пишутся: основной инструмент,
   с чем он сравнивается, и упомянутый ассистент. Расхождение ASR и надписи на экране
   разрешается в пользу экрана и фиксируется в `asr_note`, как в примере с `Claude Code`.
5. **CTA** это запрошенное действие, дословно. Классы: `own_work_action` (действие в своей
   работе), `save_or_test`, `open_question_about_process`, `follow`, `comment_bait`,
   `link_in_bio`. Класс `comment_bait` считается отдельно и **никогда** не переносится к нам:
   `06-formats.md:60` и `04-voice.md:48`. Считать его частоту у конкурентов полезно, повторять
   нельзя.
6. Тайминги берутся из границ сегментов ASR, не на глаз. При флаге подозрительных таймингов
   пять полей сохраняются, но `verified_by_human` остаётся `false` до сверки со звуком, и такой
   рилс не может быть единственным основанием карточки.

---

## 5. Схема кадров на следующий прогон

### Какие кадры сохраняем

1. Первый кадр (0,0 с): что видно без звука в момент появления в ленте.
2. Кадр хука: на `end_s` произнесённого хука, из схемы транскрипта.
3. Каждый рез: по одному кадру после каждой смены плана, а не по фиксированной сетке.
4. Кадр CTA: на `start_s` реплики CTA.
5. Последний кадр: `duration_s` минус 0,3 с.

### Что записываем по каждому кадру

`t_s`, `shot_type` (`face` / `screen` / `split` / `text_card`), `on_screen_text` дословно,
`sticker_or_graphic` (да/нет и что), `changed_vs_prev` (что именно изменилось).

### Производные метрики динамики

`cuts_per_second`, доля времени `face` против `screen`, секунды до первого доказательства
на экране, секунды CTA на экране.

### Заполненный пример: реальные кадры `DbVq4mwz38L`

Девять кадров с диска `data/frames/DbVq4mwz38L/` и контактный лист просмотрены. Это
**фактическая** текущая выборка радара, поэтому пример показывает и схему, и её дыру.

| t, с | Тип | Текст на экране (дословно) | Графика | Что изменилось |
|---|---|---|---|---|
| 0,4 | split | `This 17 YEAR OLD` | нет | старт: сверху тёмный портрет подростка, снизу говорящая голова с микрофоном |
| 1,2 | split | `fixed MANYCHAT'S` | нет | верхняя половина сменилась на скриншот прайса ManyChat, `$139/mo Advanced`, `25000 Active Contacts` |
| 2,4 | split | `MANYCHAT'S` | нет | тот же прайс, тариф `$69/mo Business`, `TRY 14 DAYS FOR FREE` |
| 4,0 | text_card | `It is called OpenReply` / `Open-sourced ManyChat for Instagram comment-to-DM automation.` | плашка с иконкой ссылки | говорящая голова ушла, полноэкранная карточка названия |
| 8,9 | screen | `types` / список комментариев: `iamrishabhm_ Repo`, `geetasingh Repo`, `chaimajestea Repo` | нет | доказательство: реальная лента автоответов |
| 17,8 | screen | `$39` / `Bill amount` / `So a reel that pops off` | мокап телефона с рилсом `101K` | доказательство цены поверх мокапа |
| 26,8 | screen | `Swap in a` / `TRACKED LINK` / `Recent Activity` / `Sent`, `Queued` | нет | дашборд с недельными числами и статусами отправок |
| 35,7 | screen | `Tech stack` / `Next.js 16 and React 19...` / `Contributing` | нет | README репозитория |
| 44,6 | text_card | `and THE REPO` / `Set it up with your AI assistant` / `If you use Claude Code, Cursor, or a similar tool...` | нет | README, раздел про ассистента |

Производные метрики по этому рилсу:

- `cuts_per_second` = **0,13** (7 резов на 53,5 с, из таблицы `deepdives`). Число honest,
  но сетка кадров его не показывает: пять резов приходятся на первые четыре секунды.
- Доля `face` против `screen`: по девяти сэмплам 3 кадра `split` (лицо плюс экран) и
  6 кадров `screen` или `text_card`, чистого `face` нет. Это оценка по сэмплам, а не измерение.
- Секунды до первого доказательства: **не позже 1,2 с** (прайс ManyChat на экране).
- Секунды CTA на экране: **не измеримо**. Последний кадр на 44,6 с, речь CTA идёт с 47,8 с.

Последняя строка и есть вывод раздела: сетка из девяти кадров физически не может показать CTA,
а достраивать его нельзя (`notion-raw/03:31`). Схема выше чинит это тремя обязательными
кадрами: хук, CTA, последний.

---

## 6. Последовательность выбора темы

1. Взять срез радара: `weights='ig'`, `eligible=1`, сортировка по `z` по убыванию. Отсечь
   всё, что не прошло входной гейт (`play >= max(1000, 0.30 * author_median_play)`).
2. Отфильтровать по пересылкам: пересылка отделяет победителя в 3,6 раза надёжнее любой
   другой метрики, сохранение в 2,8. Рилс с высоким `z`, но низкими `resh_1k` и `save_1k`,
   ставится ниже.
3. Проверка пригодности до всякого письма (`RULES.md` 2а): содержание не про AI в рабочих
   процессах, чужие персонажи или клонированные голоса, продвижение обхода ограничений.
   Любой из трёх отказов и рилс вычёркивается.
4. Гейт транскрипта: **нет транскрипта, нет темы**. У нас он есть у 85 из топ-150 (57 %);
   остальные 65 перезабираются или выбывают. Восстанавливать смысл по подписи запрещено.
5. Заполнить пять полей по схеме раздела 4 с таймингами. Если проблема или решение не
   заполняются, тема не идёт дальше, каким бы сильным ни был `z`.
6. Гейт кадров: открыть контактный лист и заполнить схему раздела 5. Если кадров на диске
   нет (у нас таких 96 кодов), рилс либо перезабирается, либо выбывает. Кадр CTA
   не додумывается.
7. Сопоставить тему с вопросом аудитории и назначить пилар: `Is this solution relevant to me?`
   значит Radar, `What does a first working version look like?` значит Builds,
   `Is this process suitable for AI, and how would it work?` значит Teardown
   (`06-formats.md:9-11`).
8. Прогнать обязательный фильтр из четырёх вопросов: какой повторяющийся процесс, где трение,
   что делает AI и что остаётся человеку, что зрителю сделать дальше. Четыре «да» или назад
   (`06-formats.md:30-37`).
9. Гейт доказательства: можем ли мы на этой неделе произвести своё доказательство (наш прогон,
   наш экран, наша сломавшаяся часть). Нет доказательства, тема вычёркивается.
10. Сформулировать наш угол: чем мы отвечаем на ту же проблему и чего автор референса не сказал.
    Угол не пересказ референса.
11. Назначить тип вердикта: KEEP, TEST или KILL, и условие при нём.
12. Записать карточку референса: ссылка, превышение медианы, кадры хука, пять полей,
    почему сработало (механика в одно предложение), формат, наш угол, черновик хука, приоритет.

---

## 7. На что ориентироваться при сборке карточки

1. Один референс-приём на карточку. Не склейка трёх чужих механик.
2. Пять полей заполнены из транскрипта, с таймингами и кодом рилса рядом.
3. Наше доказательство названо поимённо: что мы прогнали, на чём, что сломалось.
4. Числа только в формате WAS / NOW / SAVED, с источником и периодом (`04-voice.md:91-98`).
5. Тайминг битов: хук 0-3, контекст 3-12, доказательство 12-38, вердикт 38-50, следующий шаг
   50-60 (`06-formats.md:17-23`). Полосы это цель, а не секундомер.
6. Вердикт KEEP / TEST / KILL написан как ярлык, причина, условие (`04-voice.md:83-89`).
7. Человеческий шаг назван по имени роли: кто проверяет перед отправкой.
8. Ограничение или поломка стоит в теле ролика, а не в комментарии (`04-voice.md:26-32`).
9. Обложка в структуре v2, 6-8 слов на экране, плоско и конкретно, без вопроса и без тизера
   (`04-voice.md:68`).
10. Запрещённые слова и обещания: никакой выручки, конверсии, экономии времени без
    доказательства; никаких «top AI tools»; никакого «результата клиента»
    (`06-formats.md:51-60`).
11. Никакого comment-bait: CTA это действие в своей работе или открытый вопрос про процесс,
    не обмен комментария на файл (`04-voice.md:44-50`).
12. Три читателя: владелец видит свою проблему, чемпион видит решение и путь, пользователь
    понимает и то и другое своими словами (`06-formats.md:43-47`).
13. Проверка без звука: тема и вердикт понятны с выключенным звуком, и ролик узнаваем как M2
    без хэндла (`06-formats.md:92-93`).

---

## 8. Приоритеты на следующий прогон: три изменения

**Изменение 1. Таблица извлечения вместо словарного запаса.**
Артефакт: таблица `extractions` со схемой раздела 4, одна строка на рилс: пять полей,
тайминги, спикер, доказательства, флаги качества.
Владелец: Макс на своих 1 062 транскриптах; агент на наших 188 как эталонный образец.
Как поймём, что сработало: доля рилсов с пятью заполненными полями заменяет метрику «45,2 %
покрытия». Цель: 100 % рилсов, дошедших до шага 5, против нынешних 18 из 1 062. Проверка:
посторонний человек восстанавливает устройство рилса по строке таблицы, не открывая видео.

**Изменение 2. Кадры, привязанные к речи, а не к сетке.**
Артефакт: `deep.py` версии 2 и новые колонки в таблице `frames` (`shot_type`,
`on_screen_text`, `changed_vs_prev`), плюс обязательные кадры хука, каждого реза, CTA и последний.
Производные: `cuts_per_second`, доля face/screen, секунды до первого доказательства и CTA.
Владелец: агент на нашем радаре; после приёмки переносится Максу в `scene_media.py`.
Как поймём, что сработало: у каждого рилса-кандидата есть непустая метка времени кадра CTA.
Конкретная проверка: случай `DbVq4mwz38L` (CTA с 47,8 с, последний кадр 44,6 с) больше не
воспроизводится ни на одном рилсе прогона.

**Изменение 3. Источник сценария это таблица извлечения плюс наше доказательство, а не
позиционирование.**
Артефакт: шаблон карточки с обязательными полями `reference_code`, пять полей референса,
`our_proof` (что мы прогнали и что сломалось), `verdict`, `human_step`. Карточка без
`reference_code` и без `our_proof` не проходит гейт.
Владелец: Макс (шаблон карточки и `skills/m2-script-writer`).
Как поймём, что сработало: ноль карточек со `state: DESIGNED_NOT_MODEL_EXECUTED` в качестве
единственного доказательства. Сейчас таких десять из десяти.

Общее условие ко всем трём: вернуть на ветку дизайн-пак (`data/max-latest-pipeline.md:18`),
иначе обложки в структуре v2 собирать не из чего.
