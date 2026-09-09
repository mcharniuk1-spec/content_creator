# 1. Коротко

Дата: 8 сентября 2026. Кому: Максу. Что аудировано: десять карточек слейта 7 сентября (`M2-I01..I05`, `M2-P01..P05`), конвейер транскриптов и кадров на ветке `Latest` (коммиты 5-8 сентября, tip `31ed2d41`), плюс релиз 5 сентября как база сравнения. Ничего в Notion и в репозитории не менялось: работа только на чтение.

## Вердикт в пяти строках

1. За трое суток покрытие ASR выросло с 3,784 % до 45,2 % корпуса, и впервые появились настоящие декодированные кадры: 1 194 набора, 19 808 изображений (`data/max-latest-pipeline.md:53`, `notion-raw/01-m2-signal-studio-7sep-release.md:33`).
2. Глубина чтения при этом не изменилась: 18 транскриптов из 1 062, то есть 1,7 % (`notion-raw/01:34`). Остальные это `"lexical inventory"` (`data/max-latest-pipeline.md:53`).
3. Из 65 полей словаря ни одно не называется hook, problem, solution, tool или CTA: поиск по именам колонок даёт ноль совпадений (`data/max-latest/m2-field-dictionary.csv`). Пять полей, которые ты хочешь получать, существуют только в голове того, кто читал 18 штук.
4. Кадры извлечены, но не просмотрены: детальный разбор получили только `"the selected 262 samples across 18 Reels"` (`notion-raw/04:45`), состояние `"semantic_state": "CANDIDATE_NOT_ACCEPTED"` (`data/max-latest-pipeline.md:41`). Динамика видео не измерена ни одним числом.
5. Как следствие, карточки написаны из позиционирования, а не из рилсов: 43 кадра из 70 несут хотя бы одну ошибку, 10 из 10 не называют инструмент, 10 из 10 не содержат измеренной цифры, отдельное наблюдение: ни одна карточка не даёт вывода или вердикта в полосе 38-50 с (`audit/cards-audit.md`, сквозной разбор).

## Три изменения на следующий заход

1. **Таблица извлечения вместо словарного запаса.** Одна строка на рилс: пять полей, тайминги, спикер, доказательства на экране, флаги качества. Схема в главе 5.
2. **Кадры, привязанные к речи, а не к сетке.** Обязательны кадр хука, кадр каждого реза, кадр CTA и последний кадр, плюс четыре метрики динамики. Схема в главе 5.
3. **Источник сценария это таблица извлечения плюс наше доказательство, а не позиционирование.** Карточка без `reference_code` и без `our_proof` не проходит гейт.

## Что остаётся как есть

Это сделано правильно, и переделывать не надо.

- **Происхождение данных.** Импорт `import-legacy-db` только на чтение, карантин конфликтных идентичностей, `"hikerapi_calls": 0` зафиксировано в квитанции (`data/max-pipeline.md:62`). Ни одного скрытого источника.
- **Хеш-привязка.** `source_candidate_sha256`, `card_sha256`, `storyboard_sha256`, плюс привязка `beam_size` к хешу конфига, где несовпадение валит прогон (`data/max-latest-pipeline.md:61`, `:74`). Это редкая вещь, и её надо сохранить.
- **Рост покрытия ASR.** Реальный Faster-Whisper small, CPU int8, `word_timestamps=True`, а не унаследованный чужой текст, как было 5 сентября (`data/max-latest-pipeline.md:66`).
- **Квитанции и честные оговорки.** `"analysis_ready": false`, `"approved": false`, `"The ten demonstrations are authored fictional examples; they are not recorded model results."` (`notion-raw/01:47`). Ни одна дыра не спрятана. Весь этот аудит построен на твоих же квитанциях, и это лучшая рекомендация процессу.

Дальше по главам: что произошло по стадиям (2), разбор карточек по кадрам (3), анализ транскриптов и кадров (4), что меняем (5), приоритеты и роли (6), приложение (7).

Правка 8 сентября, вечер: вердикт не обязателен в каждом ролике (решение Миши); подсчёты в главе 3 пересчитаны без этого критерия.

Правка 8 сентября, ночь: граница контента уточнена Мишей: обучающие и информативные ролики для малого бизнеса в скоупе; узкий формат «только разбор с вердиктом» не является нормой.

# 2. Что реально произошло в конвейере

Ветка `Latest`, 6-8 сентября. Состояние релиза 5 сентября вынесено под таблицу.

| Стадия | Что запущено | На скольких рилсах | Что проверено | Что не проверено | Статус-коды |
|---|---|---|---|---|---|
| Входные данные | Импорт нашего снимка радара, `import-legacy-db`, живого сбора не было | 2 352 рилса, 100 аккаунтов | Идентичности, дубли, карантин | Свежесть: метрики датированы 1 сентября | `"hikerapi_calls": 0` (`data/max-pipeline.md:62`) |
| ASR | Faster-Whisper small, CPU int8, `word_timestamps=True`, `beam_size` из конфига, хеш-привязка beam | 1 062 непустых транскрипта из 2 352 (45,2 %) | Непустота текста и хеши всех 1 062 | Акустическая точность, язык, реальная длительность речи | 954 normal, 108 timing-flagged, 108 failures, 24 empty/unverified, 1 158 not attempted (`data/max-latest-pipeline.md:53`) |
| Проверка транскриптов | Полное чтение с визуальной сверкой | 18 из 1 062 | 18 референсов, 262 сэмпла контактных листов, 64 точных наблюдения | Остальные 1 044: словарный запас, не смысловой разбор | `"The other 1,044 transcripts have lexical inventory but still need detailed semantic review."` (`data/max-latest-pipeline.md:53`) |
| Пилот восстановления ASR | Пять окон, один чанк с ретраем | 1 рилс | Факт исполнения | Границы окон, тайминги, акустика | `"aggregate_observation_state": "SUSPICIOUS_TIMINGS"`, `"analysis_ready": false`, `"approved": false` (`data/max-latest-pipeline.md:55`) |
| Извлечение кадров | Индексированный декод, обычные сэмплы плюс кандидаты смены плана, порог реза 0.32 | 1 194 набора, 19 808 изображений, 9 625 кандидатов реза | Хеши и PTS кадров | Что на кадрах: интерпретация для корпуса не делалась | `"1,194 frame sets; 19,808 extracted images: extraction coverage, not a claim that every image was interpreted."` (`notion-raw/01:33`) |
| Чтение кадров | Ручной осмотр контактных листов | 3 рилса, 64 кадра, 17 коллажей | Технические свидетельства | Смысл сцен | `"semantic_state": "CANDIDATE_NOT_ACCEPTED"` (`data/max-latest-pipeline.md:41`) |
| Свидетельства сцен | `scene_media.py`, план 2/4/6 кадров на сцену, максимум 48 на видео | Ограниченный пилот, файлы вне git | Ревью прошло | Приёмка не дана, файлы в gitignore | `"source_media_included": false`, `"raw_transcripts_included": false` (`data/max-latest-pipeline.md:41`, `:57`) |
| Раскадровки карточек | Remotion, иллюстрации к новым сценариям | 10 карточек, 70 сцен | Соответствие сценарию | Ничего из исходных рилсов | `"kind": "ILLUSTRATED_CONTACT_SHEET"` (`:43`), `"Composition guide only; not an owner take, product output, or production asset binding."` (`:30`) |
| Генерация карточек | 10 карточек `m2.editorial-scriptcard.v1`, 3 хука, 7 сцен, хеш источника | 10 | Редакционное ревью, 14 локальных проверок | Съёмка, речь, монтаж | `"editorial_review_state": "ACCEPTED_WITH_LIMITATIONS_OWNER_SHOOT_PENDING"` (`:61`), все ассеты `AWAITING_OWNER_ASSET` (`:30`) |

Для сравнения, релиз 5 сентября: кадры не извлекались вообще, у всех 2 352 рилсов стояло `'observation_state': 'NOT_ATTEMPTED'`, `'reason_code': 'MISSING_SOURCE_MEDIA'` (`data/max-pipeline.md:67`); транскрипты были унаследованные, с пометкой `reason_code='LEGACY_ASR_PROVENANCE_AND_MEDIA_QA_UNVERIFIED'` (`data/max-pipeline.md:74`); а 64 «кадра» были синтетическим рендером Remotion, а не кадрами конкурентов (`data/max-pipeline.md:69`).

Главное движение за трое суток: покрытие с 3,784 % до 45,2 % и первые настоящие кадры. Глубина чтения не изменилась: 18 транскриптов.

## Что квитанции доказывают и чего не доказывают

Квитанции доказывают детерминированную обработку данных: что импорт был только на чтение, что ни один платный вызов не сделан, что конкретная карточка собрана из конкретного пакета источников с конкретным хешем, и что параметры ASR нельзя поменять задним числом, не уронив прогон. Это контур происхождения. Ты сам его описываешь точнее всех: `"It proves deterministic data handling, explicit gaps, evidence lineage"` (`notion-raw/90:37`).

Квитанции не доказывают качества привязанного содержания. Привязанный пакет это те самые 18 транскриптов с непроверенной акустикой, и хеш это никак не меняет. Та же цитата продолжается: `"It does not prove representative market coverage, creator-relative scoring, trend detection, audience demand, reach, ROI"`. Практический вывод: аккуратность процесса сейчас подменяет проверку содержания. Доказать, что карточка сделана из пакета, можно. Доказать, что пакет что-то значит, нельзя.

# 3. Карточки: разбор по кадрам

Проверены `data/max-latest/M2-*.json` против `notion-raw/10..19`, правила в `~/Desktop/m2lab-brand/brand/01..06`, процесс в `data/max-latest-pipeline.md`. Речь в файлах и в Notion совпадает дословно во всех десяти карточках; расходятся только экранные заглушки вида `"____"`, которых в Notion местами нет. Все цитаты речи и экрана ниже дословные.

Обозначения вердикта по кадру: **OK** кадр работает; **GEN** обобщение, подошло бы любому AI-аккаунту; **NOURG** нет ни даты, ни числа, ни ставки; **NOUTIL** зритель уходит без действия; **NOPROOF** пример выдуман, `fixture.state` во всех десяти равен `DESIGNED_NOT_MODEL_EXECUTED`; **BRAND** нарушение правила бренда; **LOGIC** фактическая или логическая ошибка; **STRUCT** нарушение структуры или тайминга.

Сквозной факт, дальше не повторяемый в каждой строке: во всех 70 кадрах нет ни одной измеренной цифры, ни одной даты и ни одного WAS / NOW / SAVED. Нарушен `04-voice.md:91`. Отдельное наблюдение, не нарушение (вердикт не обязателен в каждом ролике, решение от 8 сентября): ни одна карточка не даёт вывода или вердикта в полосе 38-50 с.

## Частота ошибок по 70 кадрам

| Тип | Кадров | Где особенно |
|---|---|---|
| GEN, обобщение | 16 | сцены 2-5, пересказ позиционирования и формула "AI could help with" |
| NOPROOF, нет доказательства | 14 | все `fixture.state` равны `DESIGNED_NOT_MODEL_EXECUTED` |
| STRUCT, структура и тайминг | 12 | сцена 1 во всех 10 карточках длится 4-7 с при норме 0-3 с |
| BRAND, нарушение правила бренда | 6 | длинное тире (I02 S6, I04 S5), "Radar"/"Builds" без "M2" (I03 S3, I04 S4), сравнение безымянных инструментов (I03 S5); P05 S5: причина неоднозначна (см. сноску в 3.10) |
| NOURG, нет срочности | 5 | хуки и контекстные сцены, ни одной даты и цифры |
| NOUTIL, нет пользы | 3 | сцены-вставки про бренд: I01 S2, I02 S3, I05 S3 |
| LOGIC, логическая ошибка | 2 | I03 S5 сравнение безымянных опций, P02 S3 медиана |
| OK | 25 | почти всё это сцены 3, 4 и 7 |

Итого 27 кадров из 70 работают, 43 несут хотя бы одну ошибку. Пересчитано 8 сентября: 6 BRAND-меток, поставленных только за отсутствие Verdict Card, сняты (I01 S6, I05 S6, P01 S6, P02 S6, P03 S6, P04 S6). Карточка не обязана заканчиваться Verdict Card. Два кадра (P01 S6, P02 S6) не несли других ошибок и перешли в OK; остальные четыре сохранили свою вторую метку (STRUCT, NOPROOF, NOPROOF, GEN). Сильные места всегда одни и те же: сцена с готовым списком критериев и финальный кадр с пустым бланком. Слабые тоже одни и те же: хук и сцена про бренд.

Уровень карточки, не кадра:

- 10 из 10 не называют ни одного инструмента. Поле Tool отсутствует полностью.
- 10 из 10 не содержат ни одной измеренной цифры, ни WAS / NOW / SAVED (`04-voice.md:91`).
- 10 из 10 не содержат Verdict Card и не дают иного вывода взамен неё. Verdict Card не обязательна в каждом ролике (решение Миши от 8 сентября, брендбук обновляется параллельно), но отсутствие любого вывода в полосе 38-50 с, и это наблюдение, которое стоит закрыть.
- 10 из 10 не называют ни Михаила, ни Макса, то есть нет «human face» из `03-personality.md:40`.
- 6 из 10 хуков это вопрос: I01, I02, I05, P01, P02, P03. Остальные четыре, I03, I04, P04 и P05, это утверждение (`04-voice.md:68`).
- 12 из 16 использованных реелов-источников идут на уровне или ниже медианы собственного автора. Только 4 выше, и два из них выбросы с кратностью 156x и 322x.

## Пять полей по всем десяти карточкам

| Карточка | Hook | Problem | Solution | Tool | CTA | Format в Notion |
|---|---|---|---|---|---|---|
| M2-I01 | WEAK | WEAK | PRESENT | MISSING | PRESENT | M2 Builds |
| M2-I02 | WEAK | PRESENT | PRESENT | MISSING | PRESENT | M2 Teardown |
| M2-I03 | WEAK | PRESENT | PRESENT | MISSING | PRESENT | M2 Radar |
| M2-I04 | WEAK | PRESENT | PRESENT | MISSING | PRESENT | M2 Builds |
| M2-I05 | WEAK | PRESENT | WEAK | MISSING | PRESENT | M2 Teardown |
| M2-P01 | WEAK | PRESENT | PRESENT | MISSING | PRESENT | M2 Teardown |
| M2-P02 | WEAK | PRESENT | PRESENT | MISSING | PRESENT | M2 Radar |
| M2-P03 | WEAK | PRESENT | PRESENT | MISSING | PRESENT | M2 Builds |
| M2-P04 | WEAK | PRESENT | PRESENT | MISSING | PRESENT | M2 Teardown |
| M2-P05 | PRESENT | PRESENT | PRESENT | MISSING | PRESENT | M2 Radar |

Hook помечен WEAK в девяти случаях из десяти по форме, а не по смыслу: вопрос вместо утверждения и длина сцены 1 от 4 до 7 секунд при норме 0-3 с (`04-voice.md:68`, `06-formats.md:19`). Tool отсутствует во всех десяти, включая три карточки формата Radar, где перевод конкретного инструмента в рабочее решение это определение формата (`06-formats.md:9`).

## 3.1. M2-I01. Meet M2 Lab: start with the Friday update

Знакомство с M2 Lab через еженедельный отчёт клиенту. Источники (`notion-raw/10:84-91`): @benjamlns 19 520 просмотров, 1.00x медианы автора; @raycfu 27 390, 0.75x; @olivermerrick___ 7 324, 0.80x. Ни один из трёх не обогнал собственного автора.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-7 | "Still rebuilding the same Friday update? That is a useful place to start with AI." | "Prop card: WEEKLY CUSTOMER UPDATE; text: START WITH THE WORK." | что отчёт по пятницам это неплохая тема | STRUCT NOURG |
| S2 | 7-16 | "We're M2 Lab. We help small-business teams work out where AI fits, and what still needs a person." | "Graphic: messy routine to testable process." | ничего, это пересказ позиционирования | GEN NOUTIL |
| S3 | 16-25 | "Imagine three project notes becoming one customer update." | "Synthetic notes labelled FICTIONAL" | воображаемый вход | NOPROOF |
| S4 | 25-33 | "Then map the steps: collect facts, draft the update, check it, send it." | "Original boundary diagram; text: PREPARE / JUDGE / CHECK." | четыре шага, которые он и так знает | GEN |
| S5 | 33-41 | "AI could help with the draft. The person checking it needs the original notes." | "NOTES BESIDE DRAFT" | ничего нового | STRUCT NOPROOF |
| S6 | 41-50 | "Does an unknown delivery date stay unknown? Can you trace every sentence back to a note?" | "CAN YOU TRACE EACH FACT?" | два вопроса для самопроверки | STRUCT |
| S7 | 50-60 | "Start with one repeated task. Write down its source notes, its reviewer, and the mistake that would matter." | "Text: YOUR ROUTINE: ____" | одно выполнимое действие | OK |

Ключевое: `information_job` сцен разъехались с текстом. У S5 стоит `"Show a meaningful first-test failure"`, а провала в сцене нет (`M2-I01.json:85,98`).

Три хода до публикуемого: заменить S2 на один измеренный факт с нашей собственной пятницы; в S5 показать реальный сорванный черновик и назвать шаг, который сломался; в полосе 38-50 с поставить карточку вердикта с меткой.

## 3.2. M2-I02. Meet M2 Lab: who agreed to Friday?

Граница между черновиком и обещанием клиенту. Источники (`notion-raw/11`): @joestoltelive 1 766 просмотров, 0.40x медианы; @alliekmiller 35 394, 1.91x; @hamza_automates 1 022 485, 156.46x. Последний это выброс: медиана автора около 6 500.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-4 | "This reply looks ready. But who agreed to Friday?" | "WHO AGREED TO FRIDAY?" | есть конфликт, это лучший хук слейта | STRUCT |
| S2 | 4-13 | "The note says the team is checking. The draft says Friday." | "SOURCE: DATE UNKNOWN / DRAFT: FRIDAY?" | понятную ставку | NOPROOF |
| S3 | 13-20 | "At M2 Lab, we look for moments like this before connecting AI to everyday work." | "M2 LAB / CHECK THE PROMISE" | ничего | GEN NOUTIL |
| S4 | 20-30 | "AI can work from approved facts; missing facts need a person." | "PREPARE / PROMISE" | правило, но без примера отказа | GEN |
| S5 | 30-40 | "replace the invented date with a question for the order owner" | "QUESTION FOR ORDER OWNER" | конкретный приём | NOPROOF |
| S6 | 40-48 | "The useful output is an editable draft with the gap visible." | "Persistent label: SYNTHETIC DESIGNED DEMO — NOT TESTED." | что это не тест | BRAND NOPROOF |
| S7 | 48-60 | "Underline every promise in the reply. Can you point to the fact and the person behind each one?" | "PROMISE / FACT / PERSON" | выполнимая диагностика | OK |

Ключевое: плашка S6 содержит длинное тире, запрещённое в опубликованном тексте, включая экранный (`05-vocabulary.md:81`), и сама сообщает, что доказательства нет.

Три хода: убрать S3 и отдать эти 7 секунд реальному прогону; вместо плашки "NOT TESTED" поставить снятый экран с реальным черновиком; в 38-50 с дать вердикт с условием.

## 3.3. M2-I03. Meet M2 Lab: one job before one more subscription

Чек-лист вместо покупки очередной подписки. Источники (`notion-raw/12`): @joestoltelive 2 315, 0.52x; @lukebuildsai 835 866, 12.75x; @builders.central 17 660, 1.03x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-7 | "Before your team buys another AI subscription, write down one job it needs to do." | "ONE JOB / ONE CHECKLIST" | тезис, но 7 секунд на хук | STRUCT NOURG |
| S2 | 7-16 | "Suppose customer questions arrive in three places." | "QUESTION to POLICY to CHECKED ANSWER" | абстрактную схему | GEN |
| S3 | 16-22 | "At M2 Lab, our Radar videos look at tools through tasks like this." | "M2 RADAR / TASK FIT" | ничего | BRAND GEN |
| S4 | 22-31 | "use the supplied policy, show missing information, leave the answer editable, and wait before sending" | "CURRENT / VISIBLE GAPS / EDITABLE / NO AUTO-SEND" | рабочий чек-лист из 4 пунктов | OK |
| S5 | 31-40 | "Now try two options with the same fictional question." | "SAME QUESTION / SAME CHECKLIST" | сравнение двух безымянных опций | BRAND LOGIC |
| S6 | 40-51 | "Which answer can your colleague check and correct? What setup would the team have to maintain?" | "CHECK / CORRECT / MAINTAIN" | два верных критерия | OK |
| S7 | 51-60 | "What is one requirement your next subscription would have to pass?" | "MY TASK CHECKLIST" | сохраняемый кадр | OK |

Ключевое: Radar без инструмента это формат наизнанку. Сравниваются "two options" A и B, которые нельзя ни назвать, ни проверить, поэтому решение из сцены не вытекает.

Три хода: назвать два реальных инструмента и прогнать на них один и тот же вопрос; показать, где один из них провалился; закрыть меткой TEST с условием.

## 3.4. M2-I04. Meet M2 Lab: test the awkward enquiry

Три тестовых входа: полный, без срока, с двумя сроками. Источник один (`notion-raw/13`): @heystevetan 13 250 просмотров, 1.01x медианы, приём описан как `"demo-led model showcase that moves from generated game to dashboard"`.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-5 | "A perfect example tells you very little about a messy workday." | "Replacement card: TRY THE AWKWARD CASE." | общее наблюдение | STRUCT GEN |
| S2 | 5-14 | "Make three fictional notes before you try it." | "Text: FICTIONAL ENQUIRY to DRAFT." | что примеры выдуманы | NOPROOF |
| S3 | 14-21 | "One has every detail. One has no deadline. The third has two different deadlines." | "COMPLETE / MISSING / CONFLICTING" | готовый набор тест-кейсов | OK |
| S4 | 21-32 | "At M2 Lab, our Builds start with a small test like this." | "PRESERVE FACTS / SHOW UNKNOWNS" | ничего | BRAND NOPROOF |
| S5 | 32-42 | "Conflicting dates should become a question for the person handling the enquiry." | "Label: DESIGNED DEMO — NOT RUN; text: HUMAN REVIEW." | правило эскалации | BRAND |
| S6 | 42-51 | "A tidy paragraph still fails your test if it quietly chooses a date." | "A TIDY DRAFT CAN STILL MISS THE CONFLICT" | критерий провала | OK |
| S7 | 51-60 | "What is the missing detail that catches your team most often?" | "COMPLETE / MISSING / CONFLICTING" | выполнимая подготовка | OK |

Ключевое: единственный источник идёт ровно по своей медиане (1.01x), то есть не несёт никакого сигнала, и его приём в карточке не использован.

Три хода: прогнать три заготовленных входа на реальной модели и снять экран; показать, на каком именно сломалось; заменить плашку "NOT RUN" на карточку вердикта.

## 3.5. M2-I05. Meet M2 Lab: design the customer handoff

Передача результата клиенту и сотруднику ресепшена. Источники (`notion-raw/14`): @benjamlns 19 520, 1.00x; @rence_ur_hands 208 948, 322.20x при медиане около 650.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-6 | "You sent the reminder. Can the customer actually tell what to do next?" | "WHAT SHOULD THE CUSTOMER DO NEXT?" | вопрос без ставки | STRUCT NOURG |
| S2 | 6-17 | "The sending task is done; the customer is stuck." | "DATE KNOWN / NEXT STEP MISSING" | понятный симптом | GEN |
| S3 | 17-26 | "M2 Lab looks at AI adoption from both sides of that handoff." | "CUSTOMER CLARITY / TEAM ACTION" | ничего | GEN NOUTIL |
| S4 | 26-33 | "Map the confirmed facts, the draft reminder, the customer's response, and the staff member who handles changes." | "INPUT to DRAFT to RESPONSE to EXCEPTION" | схема из 4 узлов | OK |
| S5 | 33-42 | "AI could help prepare the wording. Your team still needs to agree what happens." | "AI PREPARES / PERSON DECIDES" | ничего нового | GEN |
| S6 | 42-51 | "Read the message as the customer. Is the next step clear? Then read it as the staff member." | "Designed example only; text: SAME CONFIRMED FACT." | приём двойного чтения | NOPROOF |
| S7 | 51-60 | "At the end of your next process map, draw the person receiving the result." | "RECIPIENT: ____ NEEDS: ____" | одно действие | OK |

Ключевое: источник с кратностью 322.20x выбран по числу, которое ничего не значит при медиане в 650 просмотров. Твоя же процедура требует `"report the denominator"` (`data/max-latest/primary-editorial-findings-20260907.md:9`).

Три хода: снять один реальный шаблон напоминания и показать в нём пустое место; назвать роль, которая обрабатывает исключения, и цену ошибки; закрыть Verdict Card с разметкой автоматизируемых шагов.

## 3.6. M2-P01. The appointment reply your workflow forgot

Ветка исключений в записи на приём. Источники (`notion-raw/15`): @hamza_automates 1 022 485, 156.46x; @rence_ur_hands 208 948, 322.20x; @kevinfremon 4 202, 0.64x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-4 | "What happens when the customer replies, 'Maybe next week'?" | "Text: TEST THE CHANGE." | конкретный случай | STRUCT |
| S2 | 4-13 | "An appointment demo might show a booking, a reminder, and a happy confirmation." | "Fictional path; text: HAPPY PATH." | чужое демо в пересказе | NOPROOF |
| S3 | 13-20 | "Now draw three branches: confirmed, wants a change, and unclear. Add a fourth for no response." | "CONFIRMED / CHANGE / UNCLEAR / NO RESPONSE" | готовую схему из 4 веток | OK |
| S4 | 20-31 | "AI could suggest a category and draft the next message." | "Text: UNCERTAIN to HUMAN REVIEW." | общая формула | GEN NOPROOF |
| S5 | 31-40 | "Don't quietly turn it into a confirmed date." | "UNCLEAR to ASK" | правило безопасности | OK |
| S6 | 40-49 | "Give each branch an owner and an agreed next step." | "OWNER + NEXT STEP" | верный принцип | OK |
| S7 | 49-60 | "Write the most awkward reply underneath it. Does your process have somewhere for that reply to go?" | "CONFIRMED / CHANGE / UNCLEAR / NO RESPONSE" | выполнимая карта | OK |

Ключевое: S2 строится на пересказе чужого демо, что прямо в списке «не публиковать» (`06-formats.md:59`), а S7 дословно повторяет экранный текст S3.

Три хода: заменить пересказ чужого демо на наш собственный скрин ветки исключений; дать цифру, сколько ответов в неделю попадает в "unclear"; закрыть Verdict Card.

## 3.7. M2-P02. Turn a competitor post into a customer question

Как читать чужой залетевший пост. Источники (`notion-raw/16`): @jasoncooperson 24 544, 1.01x; @jasoncooperson 7 059, 0.29x; @heystevetan 13 250, 1.01x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-7 | "That competitor post got a lot of views. Which customer question made it worth watching?" | "Original tray label: CUSTOMER QUESTION" | тезис без числа | STRUCT NOURG |
| S2 | 7-16 | "use the number to choose something to inspect. Keep the capture date beside it." | "DATED RESEARCH LEAD" | требование даты без даты | NOURG |
| S3 | 16-26 | "Compare it with the same account's usual views." | "READ THE WORDS / INSPECT THE VISUAL" | верный метод | LOGIC |
| S4 | 26-34 | "Write three notes: the problem introduced, the useful answer, and the visual." | "PROBLEM / ANSWER / VISUAL" | рабочий шаблон разбора | OK |
| S5 | 34-42 | "Pick a question your own customers ask, and answer it with your own example." | "OUR CUSTOMER ASKS: ____" | общее указание | GEN |
| S6 | 42-52 | "A high view count doesn't tell you which detail caused it." | "NEW IDEA to TEST" | верное ограничение | OK |
| S7 | 52-60 | "our customer needs to understand blank. Build the post around that." | "OUR CUSTOMER NEEDS TO UNDERSTAND ____" | одно действие | OK |

Ключевое: логическая дыра в S3. Карточка учит сравнивать пост с медианой аккаунта, а сама построена на трёх референсах с кратностью 1.01x, 0.29x и 1.01x, то есть на постах, которые этот тест не проходят.

Три хода: вывести на экран реальные два числа, просмотры и медиану аккаунта, с датой съёма; показать наш собственный разбор одного реального поста; закрыть меткой вердикта.

## 3.8. M2-P03. Give the morning brief a decision owner

Утренняя сводка с колонками «решение» и «владелец». Источники (`notion-raw/17`): @alliekmiller 35 394, 1.91x; @joestoltelive 1 766, 0.40x; @olivermerrick___ 8 649, 0.94x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-5 | "Your morning summary has twelve updates. Which one needs you?" | "Text: WHERE DOES THE DECISION GO?" | единственное число во всём слейте, и то выдуманное | STRUCT |
| S2 | 5-15 | "put fictional project notes into three columns: what changed, what needs a decision, and what can wait" | "Persistent label: FICTIONAL INPUTS." | структура сводки | NOPROOF |
| S3 | 15-24 | "AI could group repeated notes and prepare a short draft." | "SUMMARY + SOURCES" | общая формула | GEN |
| S4 | 24-34 | "A line saying 'delivery date unclear' needs a person who can confirm the date, not another summary." | "DECISION NEEDED / OWNER" | сильная мысль карточки | OK |
| S5 | 34-41 | "If two notes disagree, keep both visible." | "DISAGREEMENT to MISSING FACT" | правило | OK |
| S6 | 41-52 | "the owner checks the source, makes the call, and records it" | "CHECK to DECIDE to RECORD" | цикл решения | NOPROOF |
| S7 | 52-60 | "Add 'decision needed' and 'owner.' How many lines actually ask somebody to do something?" | "DECISION NEEDED / OWNER / SOURCE" | выполнимая правка своей сводки | OK |

Ключевое: единственное число в кадре выдумано, тогда как `04-voice.md:7` запрещает публиковать неизмеренное число.

Три хода: взять нашу реальную утреннюю сводку за неделю и показать, сколько строк из скольких требовали решения; назвать шаг, где группировка ошиблась; закрыть Verdict Card с WAS / NOW / SAVED по времени на разбор сводки.

## 3.9. M2-P04. Ask for the awkward case before buying automation

Что спросить у подрядчика до покупки автоматизации. Источник один (`notion-raw/18`): @bennett.spooner 19 989, 1.00x, приём `"sell-before-build narrative"`.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-6 | "Someone offers to automate your whole workflow. Ask to see the awkward case first." | "PROPOSAL / AWKWARD CASE" | понятное указание | STRUCT |
| S2 | 6-15 | "Bring a fictional example with a missing detail." | "FICTIONAL ENQUIRY: deadline unknown" | подготовка к встрече | OK |
| S3 | 15-24 | "Ask what goes in, what comes out, and who checks it." | "INPUT to DRAFT to CHECKER" | три вопроса подрядчику | OK |
| S4 | 24-34 | "Does the system stop, ask a question, or quietly guess?" | "DESIGNED EXAMPLE: ASK, DON'T GUESS" | критерий приёмки | NOPROOF |
| S5 | 34-43 | "get the open questions in writing: access, running costs, maintenance, and responsibility" | "OPEN QUESTIONS" | четыре пункта в договор | OK |
| S6 | 43-50 | "A successful small example answers a small question." | "ONE TEST / OPEN QUESTIONS" | ограничение вывода | GEN |
| S7 | 50-60 | "add one line: show us how this handles our difficult example" | "OUR DIFFICULT EXAMPLE: ____" | одна строка в запрос | OK |

Ключевое: самая полезная карточка десятки и самая слабая по доказательствам. Ни одной цифры про стоимость владения, хотя вся сцена S5 про "running costs".

Три хода: подставить наши собственные цифры по одному нашему пилоту в строку "running costs"; показать реальный ответ реального инструмента на awkward case; закрыть Verdict Card.

## 3.10. M2-P05. Add a failure column to your AI shortlist

Колонка отказов в сравнении инструментов. Источники (`notion-raw/19`): @builders.central 17 660, 1.03x; @lukebuildsai 835 866, 12.75x; @joestoltelive 2 315, 0.52x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-4 | "Your AI tool comparison needs a failure column." | "Text: RANK THE FAILURE FIRST." | чёткий тезис, лучший хук по форме | STRUCT |
| S2 | 4-12 | "Imagine two tools preparing the same weekly stock note. One draft looks sharper. Both leave out an item." | "Label: FICTIONAL STOCK DATA." | воображаемый пример | NOPROOF |
| S3 | 12-22 | "write down how your team would spot that missing item" | "SOURCE LIST / DRAFT" | конкретный способ проверки | OK |
| S4 | 22-31 | "Now test an invented number, a late draft, and a mistaken send instruction." | "WHAT SHOULD HAPPEN?" | три режима отказа | OK |
| S5 | 31-40 | "the same fictional input, the same checks, and a person responsible" | "SAME INPUT / SAME CHECK" | принцип контроля | GEN BRAND |
| S6 | 40-49 | "Include the work needed to correct an error." | "INCLUDE THE COST OF CORRECTION" | верная мысль без цены | GEN |
| S7 | 49-60 | "Add three columns to your shortlist: failure, how we'll notice, and who fixes it." | "FAILURE / HOW WE NOTICE / WHO FIXES IT" | готовая таблица | OK |

Ключевое: карточка про сравнение инструментов не называет ни одного инструмента и не приводит ни одной цифры отказов, хотя весь её тезис в том, что отказы надо измерять. Сноска к пересчёту 8 сентября: метка BRAND у S5 сохранена как есть, причину нельзя однозначно отнести только к отсутствию Verdict Card, а не к отсутствию названного инструмента (оба нарушения указаны в одном предложении источника), поэтому метка не снята.

Три хода: взять два реальных инструмента и один наш реальный отчёт; показать, сколько строк каждый потерял; закрыть карточкой вердикта KEEP или TEST с условием.

# 4. Транскрипты и кадры: анализ

## Выводы агента и подтверждаются ли они данными

| Вывод, дословно | Где | Подтверждается |
|---|---|---|
| `"The strongest direction for this slate is to show a small, recognisable failure and let the viewer see how to handle it"` | `notion-raw/01:23` | **Частично.** Как редакционный выбор допустим, и он сам оговорен строкой ниже. Но сделан на 18 рилсах из 1 062, отобранных по индексу просмотров, без контрольной группы. |
| `"concrete work problems can be made legible with an input, a visible gap, and a next decision"` | `notion-raw/04:25` | **Частично.** Структура правдоподобна и совпадает с брендом, но выведена из 18 примеров и не проверена на тех, кто не залетел. Там же: `"We have not isolated which feature caused a Reel's views."` |
| `"A high ratio helps identify a post worth inspecting. It cannot establish that the hook caused the result"` | `notion-raw/01:38` | **Подтверждается.** Корректная и важная оговорка, совпадает с нашей методикой сравнения с медианой автора. |
| `"1,062 non-empty machine transcripts — 45.2% of Reels"` как показатель покрытия | `notion-raw/01:32` | **Подтверждается как счёт, не как качество.** Это состояние машины: 108 из них с подозрительными таймингами, акустика не проверена ни у одного. |
| `"18 selected Reels from 15 accounts: full-text and sampled-visual review used for the cards"` | `notion-raw/01:34` | **Подтверждается по факту, не по достаточности.** 18 из 1 062 это 1,7 % корпуса; выводы о структуре формата на такой базе не отделимы от выбора примеров. |
| `"The ten demonstrations are authored fictional examples; they are not recorded model results."` | `notion-raw/01:47` | **Подтверждается.** Честная пометка, но она же означает, что доказательства в карточках нет вообще. |
| `"It is a secondary, untrusted reference for editorial structure. It does not validate performance, audience demand, platform behavior, creator results"` | `notion-raw/03:41` | **Подтверждается как оговорка, не подтверждается как практика.** Девять приёмов вшиты в `skills/humanize-writing`, то есть влияют на каждую карточку, но ни один не сверен с метриками. |
| `"Read the entire selected transcript and inspect timestamped visual evidence before assigning hook, problem, mechanism, demonstration, transition or CTA functions"` | `notion-raw/03:31` | **Не подтверждается исполнением.** Правило записано верно, выполнено на 18 рилсах, а в словаре полей нет ни одной колонки под эти функции. |

## Проблемные места и их последствия

**4.1. Транскрипты работают как словарный запас, а не как структура.** `"The other 1,044 transcripts have lexical inventory but still need detailed semantic review."` (`data/max-latest-pipeline.md:53`), плюс поля `Lexical text words` и `Text fit candidate` (`m2-field-dictionary.csv:31`, `:33`). Последствие: 1 044 транскрипта дают счётчик слов и метку релевантности, но ни одного ответа на вопрос «как этот рилс устроен». Карточки поэтому опираются на 18 примеров и на позиционирование.

**4.2. Нет по-рилсового извлечения пяти полей.** В словаре из 65 полей поиск по именам колонок по словам hook, problem, solution, tool, CTA даёт ноль совпадений. Ближайшее это `Opening candidate`, `"Maker-coded opening/hook orientation candidate"`, и тут же `"Maker-coded candidate; unreviewed labels do not support prevalence or causal claims."` (`m2-field-dictionary.csv:32`). Последствие: пять полей нельзя ни отсортировать, ни сравнить, ни передать другому человеку.

**4.3. Кадры извлечены, но не просмотрены, поэтому кадр хука и кадр CTA неизвестны.** 19 808 изображений извлечено, детальный разбор получили `"Only the selected 262 samples across 18 Reels"` (`notion-raw/04:45`). Последствие: твой главный тезис, что кадры показывают хук, CTA и динамику, для 1 176 наборов из 1 194 не выполнен. Динамика видео не измерена ни одним числом.

**4.4. Тайминги сцен придуманы, а не измерены.** Карточки содержат `start_ms` / `end_ms` на семь сцен по 60 секунд (`data/max-latest/M2-I01.json`), при том что `"Seven scenes and sixty seconds are this slate's plan, not a universal retention formula."` (`notion-raw/03:36`). Последствие: ритм карточки задан шаблоном по 8,5 секунды. У нашего реального референса семь резов на 53,5 секунды распределены крайне неравномерно: пять из них в первые четыре секунды.

**4.5. Тайминги ASR не проверены, и это признано.** 108 транскриптов timing-flagged; пилот восстановления закончился `"SUSPICIOUS_TIMINGS"`, `"analysis_ready": false`, `"approved": false`, и `"A machine-observed recovery is not acoustic approval"` (`data/max-latest-pipeline.md:55`). Последствие: утверждение «хук длится до 3 секунды» на этих данных недоказуемо. Пятиполевая схема без флага качества тайминга унаследует ту же проблему, поэтому в схеме главы 5 есть блок `quality`.

**4.6. Прочитано 18 из 1 062, и выборка стала самоподтверждающейся.** Отобраны рилсы с высоким индексом просмотров, у них найдена общая структура, и эта структура объявлена направлением слейта. Проигравшие рилсы не читались, поэтому неизвестно, отличается ли структура победителей от структуры остальных.

**4.7. Позиционирование работает источником сценариев.** `"Positioning consumed — knowledge/m2-positioning.md"` (`data/max-latest-pipeline.md:24`), фикстуры карточек помечены `"state": "DESIGNED_NOT_MODEL_EXECUTED"`. Последствие: карточка рассказывает, во что мы верим, а не то, что мы проверили. По бренду это прямой отказ: `"Is the proof ours?"` (`m2lab-brand/brand/06-formats.md:94`).

**4.8. Дизайн-пак удалён на ветке.** `"the entire design/ brand-pack tree (logos, tokens, templates, palette, typography, ~90 files) and PRODUCTION.md ... are removed on Latest"` (`data/max-latest-pipeline.md:18`). Последствие: карточки нечем визуально проверить, обложки в структуре v2 собрать не из чего, и это объясняет, почему в карточки не попали ни правило вердикта, ни запрет длинного тире, ни правило именования Radar и Builds.

**4.9. То же самое и у нас: наши кадры не покрывают CTA.** У реального рилса `DbVq4mwz38L` девять кадров на фиксированных позициях, последний на 44,6 с при длительности 53,5 с, а речь CTA начинается на 47,8 с. Кадр CTA у нас физически отсутствует. Это ровно та ошибка, о которой ты предупреждаешь:

> "Do not infer an unseen opening from a later presenter frame or assume the final sampled
> frame contains a CTA." (`notion-raw/03:31`)

Последствие: схема кадров требует переделки с обеих сторон, не только у тебя.

# 5. Что меняем

## 5.1. Последовательность определения темы

Двенадцать шагов. Гейты обязательные: если шаг не проходит, тема не идёт дальше, каким бы сильным ни был показатель.

1. Взять срез радара: `weights='ig'`, `eligible=1`, сортировка по `z` по убыванию. Отсечь всё, что не прошло входной гейт (`play >= max(1000, 0.30 * author_median_play)`).
2. Отфильтровать по пересылкам: пересылка отделяет победителя в 3,6 раза надёжнее любой другой метрики, сохранение в 2,8. Рилс с высоким `z`, но низкими `resh_1k` и `save_1k`, ставится ниже.
3. **Гейт пригодности:** ролик остаётся, если он помогает руководителю малого или среднего бизнеса встроить AI в свою работу — рабочий процесс, инструмент, приём, промпт, репозиторий, обучающий разбор. Выбрасываем явно: контент только для разработчиков, агентная инфраструктура для технических строителей, сгенерированные персонажи, клонированные голоса, продвижение обхода ограничений.
4. **Гейт транскрипта: нет транскрипта, нет темы.** У нас он есть у 85 из топ-150 (57 %); остальные 65 перезабираются или выбывают. Восстанавливать смысл по подписи запрещено.
5. Заполнить пять полей по схеме 5.3 с таймингами. Если проблема или решение не заполняются, тема не идёт дальше.
6. **Гейт кадров:** открыть контактный лист и заполнить схему 5.4. Если кадров на диске нет (у нас таких 96 кодов), рилс либо перезабирается, либо выбывает. Кадр CTA не додумывается.
7. Сопоставить тему с вопросом аудитории и назначить пилар: `Is this solution relevant to me?` значит Radar, `What does a first working version look like?` значит Builds, `Is this process suitable for AI, and how would it work?` значит Teardown (`06-formats.md:9-11`).
8. Прогнать обязательный фильтр из четырёх вопросов: какой повторяющийся процесс, где трение, что делает AI и что остаётся человеку, что зрителю сделать дальше. Четыре «да» или назад (`06-formats.md:30-37`).
9. **Гейт доказательства:** можем ли мы на этой неделе произвести своё доказательство, наш прогон, наш экран, наша сломавшаяся часть. Нет доказательства, тема вычёркивается.
10. Сформулировать наш угол: чем мы отвечаем на ту же проблему и чего автор референса не сказал. Угол не пересказ референса.
11. Назначить тип вывода: вердикт KEEP / TEST / KILL с условием, если ролик выносит оценку инструмента или процесса; иначе одно предложение-вывод из доказательства.
12. Записать карточку референса: ссылка, превышение медианы, кадры хука, пять полей, почему сработало (механика в одно предложение), формат, наш угол, черновик хука, приоритет.

## 5.2. На что ориентироваться при сборке карточки

Тринадцать пунктов. Заполняется как таблица PASS / FAIL по каждой карточке. Сегодня по этому списку проходит 0 карточек из 10.

1. Один референс-приём на карточку. Не склейка трёх чужих механик.
2. Пять полей заполнены из транскрипта, с таймингами и кодом рилса рядом.
3. Наше доказательство названо поимённо: что мы прогнали, на чём, что сломалось.
4. Числа только в формате WAS / NOW / SAVED, с источником и периодом (`04-voice.md:91-98`).
5. Тайминг битов: хук 0-3, контекст 3-12, доказательство 12-38, вердикт 38-50, следующий шаг 50-60 (`06-formats.md:17-23`). Полосы это цель, а не секундомер.
6. Если ролик выносит вердикт, он написан как ярлык, причина, условие; если нет, полоса 38-50 с несёт один вывод из доказательства (`04-voice.md:83-89`).
7. Человеческий шаг назван по имени роли: кто проверяет перед отправкой.
8. Ограничение или поломка стоит в теле ролика, а не в комментарии (`04-voice.md:26-32`).
9. Обложка в структуре v2, 6-8 слов на экране, плоско и конкретно, без вопроса и без тизера (`04-voice.md:68`).
10. Запрещённые слова и обещания: никакой выручки, конверсии, экономии времени без доказательства, никаких списков лучших инструментов, никакого «результата клиента» (`06-formats.md:51-60`).
11. Никакого обмена реплики на файл: CTA это действие в своей работе или открытый вопрос про процесс (`04-voice.md:44-50`).
12. Три читателя: владелец видит свою проблему, чемпион видит решение и путь, пользователь понимает и то и другое своими словами (`06-formats.md:43-47`).
13. Проверка без звука: тема и вывод понятны с выключенным звуком, и ролик узнаваем как M2 без хэндла (`06-formats.md:92-93`).

## 5.3. Схема извлечения из транскрипта

Одна запись на рилс. Пример ниже собран из настоящих данных: база `radar-0907.db`, таблицы `transcripts`, `reels`, `scores`, `deepdives`, код `DbVq4mwz38L`, автор @heystevetan. Транскрипт прочитан целиком: 33 сегмента, 213 слов.

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

Правила извлечения:

1. **Хук** это первое произнесённое утверждение, целиком закрывающееся до 3,0 с. Если фраза пересекает границу, берём её целиком и записываем реальный `end_s` (здесь 3,2 с), а не обрезаем по трём секундам. Вопрос без утверждения хуком не считается: размечается как `claim_type: "question"` и помечается слабым.
2. **Проблема** обязана иметь владельца (`whose`) и процесс (`workflow`). Формулировка «людям дорого» без того, кто и в какой работе платит, не принимается. Если проблемы в речи нет, поле остаётся `null`, и рилс идёт в корзину «demo without a problem»: это тоже наблюдение, а не пропуск.
3. **Решение** это механизм, а не название. Записываются три вещи: что делает машина, что остаётся человеку (`human_step_named`), какое ограничение названо вслух (`limitation_named`). Если ни ограничения, ни человеческого шага нет, оба поля пустые, и это сильный сигнал против переноса приёма к нам.
4. **Инструмент** размечается как `named: true/false`. При `true` пишутся основной инструмент, с чем он сравнивается, и упомянутый ассистент. Расхождение ASR и надписи на экране разрешается в пользу экрана и фиксируется в `asr_note`, как здесь с `Claude Code`.
5. **CTA** это запрошенное действие, дословно. Классы: `own_work_action`, `save_or_test`, `open_question_about_process`, `follow`, `comment_bait`, `link_in_bio`. Класс `comment_bait` считается отдельно и никогда не переносится к нам (`06-formats.md:60`, `04-voice.md:48`). Считать его частоту у конкурентов полезно, повторять нельзя.
6. Тайминги берутся из границ сегментов ASR, не на глаз. При флаге подозрительных таймингов пять полей сохраняются, но `verified_by_human` остаётся `false` до сверки со звуком, и такой рилс не может быть единственным основанием карточки.

## 5.4. Схема кадров

Какие кадры сохраняем:

1. Первый кадр (0,0 с): что видно без звука в момент появления в ленте.
2. Кадр хука: на `end_s` произнесённого хука, из схемы 5.3.
3. Каждый рез: по одному кадру после каждой смены плана, а не по фиксированной сетке.
4. Кадр CTA: на `start_s` реплики CTA.
5. Последний кадр: `duration_s` минус 0,3 с.

Что записываем по каждому кадру: `t_s`, `shot_type` (`face` / `screen` / `split` / `text_card`), `on_screen_text` дословно, `sticker_or_graphic` (да или нет и что), `changed_vs_prev` (что именно изменилось).

Производные метрики динамики: `cuts_per_second`, доля времени `face` против `screen`, секунды до первого доказательства на экране, секунды CTA на экране.

Заполненный пример: девять кадров с диска `data/frames/DbVq4mwz38L/` и контактный лист просмотрены глазами. Это фактическая текущая выборка радара, поэтому пример показывает и схему, и её дыру.

| t, с | Тип | Текст на экране, дословно | Графика | Что изменилось |
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

- `cuts_per_second` = **0,13** (7 резов на 53,5 с, из таблицы `deepdives`). Число честное, но сетка кадров его не показывает: пять резов приходятся на первые четыре секунды.
- Доля `face` против `screen`: по девяти сэмплам 3 кадра `split` (лицо плюс экран) и 6 кадров `screen` или `text_card`, чистого `face` нет. Это оценка по сэмплам, а не измерение.
- Секунды до первого доказательства: **не позже 1,2 с** (прайс ManyChat на экране).
- Секунды CTA на экране: **не измеримо**. Последний кадр на 44,6 с, речь CTA идёт с 47,8 с.

Последняя строка и есть вывод: сетка из девяти кадров физически не может показать CTA, а достраивать его нельзя. Схема выше чинит это тремя обязательными кадрами: хук, CTA, последний.

## 5.5. Гейт на источники

Рилс допускается в источники только при выполнении всех четырёх условий.

| Условие | Порог | Зачем |
|---|---|---|
| Превышение медианы автора | не ниже 1.5x | 12 из 16 использованных реелов шли на уровне или ниже медианы, то есть не несли сигнала |
| Потолок превышения | не выше 20x | отсекает выбросы вроде 156.46x и 322.20x при медиане 650 просмотров |
| Знаменатель базы | не меньше 20 рилсов автора | без базы кратность это шум; `"report the denominator"` |
| Тема | полезно руководителю малого или среднего бизнеса: процесс, инструмент, приём, обучение | все 16 реелов были нацелены на технических строителей агентных систем, которых `02-audience.md:35-37` выводит за пределы M2; рилсы про инструменты или промпты для работы малого и среднего бизнеса такой гейт прошли бы |

## 5.6. Шаблон 7 по 60 секунд отменяется

Семь сцен по 60 секунд это план одного слейта, а не структура. Твоя же формулировка: `"Seven scenes and sixty seconds are this slate's plan, not a universal retention formula."` (`notion-raw/03:36`). Вместо него пять битов, как в бренде (`06-formats.md:17-23`):

| Бит | Полоса | Что в нём |
|---|---|---|
| Хук | 0-3 с | одно утверждение про процесс, без вопроса и без тизера |
| Контекст | 3-12 с | задача и кто ей владеет сегодня |
| Доказательство | 12-38 с | наш экран, наш прогон, шаг, который сломался |
| Вердикт | 38-50 с | KEEP, TEST или KILL с условием, Verdict Card на экране |
| Следующий шаг | 50-60 с | одно действие, которое зритель делает в своей работе сегодня |

Число сцен и их длина выбираются под тему после написания тела, а не задаются заранее. Минимум три сцены отдаются полосе доказательства, и ни одна сцена не тратится на пересказ позиционирования. Это убирает сразу два дефекта: хук длиной 7 секунд во всех десяти карточках и сцены-вставки про бренд (I01 S2, I02 S3, I05 S3).

# 6. Приоритеты на следующий заход

## Изменение 1. Таблица извлечения вместо словарного запаса

**Артефакт:** таблица `extractions` со схемой 5.3, одна строка на рилс: пять полей, тайминги, спикер, доказательства, флаги качества.

**Владелец:** Макс на своих 1 062 транскриптах; наш агент на наших 188 как эталонный образец.

**Проверка:** доля рилсов с пятью заполненными полями заменяет метрику «45,2 % покрытия». Цель 100 % рилсов, дошедших до шага 5, против нынешних 18 из 1 062. Контрольный тест: посторонний человек восстанавливает устройство рилса по строке таблицы, не открывая видео.

## Изменение 2. Кадры, привязанные к речи, а не к сетке

**Артефакт:** `deep.py` версии 2 и новые колонки в таблице `frames` (`shot_type`, `on_screen_text`, `changed_vs_prev`), плюс обязательные кадры хука, каждого реза, CTA и последний. Производные: `cuts_per_second`, доля face/screen, секунды до первого доказательства и CTA.

**Владелец:** наш агент на нашем радаре; после приёмки переносится тебе в `scene_media.py`.

**Проверка:** у каждого рилса-кандидата непустая метка времени кадра CTA. Конкретно: случай `DbVq4mwz38L` (CTA с 47,8 с, последний кадр 44,6 с) не воспроизводится ни на одном рилсе прогона.

## Изменение 3. Источник сценария это извлечение плюс наше доказательство

**Артефакт:** шаблон карточки с обязательными полями `reference_code`, пять полей референса, `our_proof` (что мы прогнали и что сломалось), `human_step`, и полем `conclusion` (вердикт KEEP / TEST / KILL с условием, если ролик оценивает инструмент или процесс; иначе одно предложение-вывод из доказательства; Verdict Card не обязательна в каждой карточке, решение от 8 сентября). Карточка без `reference_code` и без `our_proof` не проходит гейт.

**Владелец:** Макс (шаблон карточки и `skills/m2-script-writer`).

**Проверка:** ноль карточек, где `state: DESIGNED_NOT_MODEL_EXECUTED` является единственным доказательством. Сейчас таких десять из десяти.

**Общее условие ко всем трём:** вернуть на ветку дизайн-пак (`data/max-latest-pipeline.md:18`), иначе обложки в структуре v2 собирать не из чего, а правила вердикта, длинного тире и именования пиларов снова не дойдут до карточек.

## Разделение работы

Миша делает:

- Выбирает шесть тем из десяти в контент-плане (документ уходит ему отдельно; структура повторяет твою: 5 вводных и 5 регулярных, каждая тема с реелом-референсом и его метриками).
- Производит наше собственное доказательство под каждую выбранную тему: прогон, экран, сломавшийся шаг, число в формате WAS / NOW / SAVED с периодом.
- Держит гейт доказательства: тема без нашего прогона на этой неделе снимается.

Макс делает:

- Заводит схему 5.3 и схему 5.4 в конвейер как таблицы, а не как инструкцию в тексте.
- Смотрит кадры ради хука и CTA: минимум кадр хука, кадр каждого реза, кадр CTA и последний кадр по каждому рилсу-кандидату.
- Генерирует карточки из таблицы извлечения плюс `our_proof`, а не из позиционирования.
- Применяет гейт 5.5 до генерации и чек-лист 5.2 до сдачи.

# 7. Приложение

## Файлы, по которым сделан аудит

- `audit/analytics-audit.md`, `audit/cards-audit.md` (сами разборы), `audit/verification-cards.md`, `audit/verification-analytics.md` (независимая проверка обоих).
- `data/max-latest-pipeline.md`, `data/max-pipeline.md` (разбор ветки `Latest` и релиза 5 сентября).
- `data/max-latest/` (20 файлов: 10 карточек, `manifest.json`, `editorial-briefs.json`, `m2-ten-card-release.md`, `m2-field-dictionary.csv`, `media-recovery-20260906-v2.json`, `primary-editorial-findings-20260907.md`, `creator-techniques-20260907.md` и прочее).
- `notion-raw/01`, `03`, `04`, `10..19`, `90`, `91` (выгрузка дерева релиза из Notion).
- `data/radar-data.md`, `data/transcripts-available.md`, `data/topics.csv`, `data/angles.md`, база `radar-0907.db`, кадры `data/frames/DbVq4mwz38L/`.
- `m2lab-brand/brand/01-positioning.md` ... `06-formats.md`, линтер `m2lab-brand/checks/lint.mjs`.

## Как делалась проверка

Оба разбора прошли независимую сверку вторым агентом: каждая цитата сверена с файлом и номером строки, каждое число пересчитано. Результат обеих проверок: PASS WITH FIXES, все найденные расхождения исправлены и учтены в этом отчёте. Конкретно пересчитаны и подтверждены частотная таблица по 70 кадрам, все 26 значений просмотров и кратностей по десяти карточкам, разбивка ASR 954 / 108 / 108 / 24 / 1 158 (сумма даёт 2 352), отсутствие инструментов, цифр и Verdict Card во всех десяти карточках. Примеры в главе 5 проверены против живой базы `radar-0907.db` и против самих изображений на диске: все девять кадров существуют на указанных таймкодах, весь процитированный экранный текст сверен глазами с картинкой.

## Известные ограничения этого аудита

- Вложения в Notion не скачиваются через доступный интерфейс, поэтому разбор карточек сделан по выгруженному тексту страниц и по JSON в репозитории, а не по приложенным файлам.
- 15 страниц аккаунтов из дерева релиза не были получены, поэтому картина по аккаунтам неполная и в отчёт не выносится.
- Кадры на диске есть только для нашего радара. Кадры твоего конвейера лежат в gitignore-каталоге `runs/20260906-media-acquisition-v1/` и в аудит не попали: `"source_media_included": false` (`data/max-latest-pipeline.md:41`). Всё, что сказано про твои кадры, опирается на квитанции и счётчики, а не на изображения.
- Две цитаты в главе 4 (`notion-raw/90:37` про детерминированную обработку и `notion-raw/91:69` про `BLOCKED`) взяты из соседних твоих проектов: обзор бутстрапа от 25 августа и дашборд North Hux от 26 августа. Цитаты дословные, но это не тот же самый сентябрьский конвейер, и здесь они приводятся как описание подхода, а не как его замер.
- Акустическая точность ASR не проверялась ни на одном рилсе, ни у тебя, ни у нас. Это общая открытая дыра, и первым шагом её закрывает поле `asr_confidence` в схеме 5.3.
