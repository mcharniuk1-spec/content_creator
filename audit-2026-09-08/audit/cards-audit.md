# Разбор десяти карточек Макса (релиз 7 сентября)

Вердикт владельца: тексты и предложенный контент написаны плохо, слишком обще, без срочности и без
пользы. Ниже разбор по карточкам и по кадрам, с указанием, почему это произошло в процессе агента.

Что Макс просит дальше (его формулировка): нужна понятная последовательность, как определять тему;
на что ориентироваться при сборке карточки; из транскриптов надо вытаскивать hook, problem,
solution, tool, CTA; кадры важны, потому что показывают хук, CTA и динамику видео. Аудит построен
под эти пять полей и под кадры.

## Файлы против Notion

Проверены `data/max-latest/M2-*.json`, `notion-raw/10..19-card-*.md`, закон в
`~/Desktop/m2lab-brand/brand/01..06`, процесс в `data/max-latest-pipeline.md`. Тексты речи в файлах
и в Notion совпадают до символа во всех десяти карточках. Экранные плейсхолдеры расходятся: в I01
S7 JSON стоит "____", в Notion этой строки нет вовсе; в I05 S7 JSON "____ ____" против Notion
"___ ___"; в P02 S5, P02 S7 и P04 S7 JSON вставляет "____", в Notion заглушки нет. Notion добавляет
три слоя, которых в файлах нет: свойство Format (M2 Radar / Builds / Teardown), список Source Reels
с автором,
просмотрами и кратностью к медиане автора, и блок "The idea in one minute". Расхождение одно:
`data/max-latest/m2-card-editorial-revision-20260908.md:3` заявляет правку сцен S2 и S7 в M2-I01 от
8 сентября, но Notion с отметкой `Last edited: 2026-09-07T22:25:58`
(`notion-raw/10-card-m2-i01-friday-update.md:5`) уже содержит тот же текст. Правка не подтверждается
ни одним артефактом.

## Обозначения вердикта по кадру

OK - кадр работает. GEN - обобщение, подошло бы любому AI-аккаунту. NOURG - нет ни даты, ни числа,
ни ставки. NOUTIL - зритель уходит без действия. NOPROOF - пример выдуман (`fixture.state` во всех
десяти равен `DESIGNED_NOT_MODEL_EXECUTED`). BRAND - нарушение правила бренда. LOGIC - фактическая
или логическая ошибка. STRUCT - нарушение структуры или тайминга.

Сквозной факт, дальше не повторяемый в каждой строке: во всех 70 кадрах нет ни одной измеренной
цифры, ни одной даты и ни одного WAS / NOW / SAVED. Нарушен `04-voice.md:91`. Отдельное наблюдение,
не нарушение (вердикт не обязателен в каждом ролике — решение от 8 сентября): ни одна карточка не
даёт вывода или вердикта в полосе 38-50 с.

## 1. M2-I01. Meet M2 Lab: start with the Friday update

Знакомство с M2 Lab через еженедельный отчет клиенту. Источники (`notion-raw/10-...:84-91`):
@benjamlns 19,520 просмотров, 1.00x медианы автора; @raycfu 27,390, 0.75x; @olivermerrick___ 7,324,
0.80x. Ни один из трех не обогнал собственного автора.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-7 | "Still rebuilding the same Friday update? That is a useful place to start with AI." | "Prop card: WEEKLY CUSTOMER UPDATE; text: START WITH THE WORK." | что отчет по пятницам это неплохая тема | STRUCT NOURG |
| S2 | 7-16 | "We're M2 Lab. We help small-business teams work out where AI fits, and what still needs a person." | "Graphic: messy routine to testable process." | ничего, это пересказ позиционирования | GEN NOUTIL |
| S3 | 16-25 | "Imagine three project notes becoming one customer update." | "Synthetic notes labelled FICTIONAL" | воображаемый вход | NOPROOF |
| S4 | 25-33 | "Then map the steps: collect facts, draft the update, check it, send it." | "Original boundary diagram; text: PREPARE / JUDGE / CHECK." | четыре шага, которые он и так знает | GEN |
| S5 | 33-41 | "AI could help with the draft. The person checking it needs the original notes." | "NOTES BESIDE DRAFT" | ничего нового | STRUCT NOPROOF |
| S6 | 41-50 | "Does an unknown delivery date stay unknown? Can you trace every sentence back to a note?" | "CAN YOU TRACE EACH FACT?" | два вопроса для самопроверки | STRUCT |
| S7 | 50-60 | "Start with one repeated task. Write down its source notes, its reviewer, and the mistake that would matter." | "Text: YOUR ROUTINE: ____" | одно выполнимое действие | OK |

Пять полей: **Hook** WEAK, вопрос вместо утверждения и 7 секунд вместо 3 (`04-voice.md:68` "No
question, no tease", `06-formats.md:19`). **Problem** WEAK, "rebuilding the same Friday update"
названо, но чья это работа и сколько она стоит, не сказано. **Solution** PRESENT, но это дословно
метод из позиционирования. **Tool** MISSING, ни одного инструмента. **CTA** PRESENT, "Write down its
source notes, its reviewer, and the mistake that would matter".

Ошибки процесса. Позиционирование пересказано, а не разыграно: S2 это перефраз
`01-positioning.md:12`. Приемы источников названы в Notion ("five-phase operating-system framework",
"visual task map"), но в карточке их нет ни одного. `information_job` сцен разъехались с текстом: у
S5 стоит "Show a meaningful first-test failure", а провала в сцене нет; у S6 стоит "Deliver the
promised explanation of M2 Lab", а там проверка фактов (`M2-I01.json:85,98`). Notion помечает
карточку как Format: M2 Builds, но ни сборки, ни запуска нет, и полоса 38-50 с не несёт никакого
вывода (Verdict Card не обязательна, но заключения нет вообще). Шесть из семи `on_screen_text`
длиннее 20 символов в строке при лимите 6-8 слов (`04-voice.md:68`).

Три хода до публикуемого: заменить S2 на один измеренный факт с нашей собственной пятницы; в S5
показать реальный сорванный черновик и назвать шаг, который сломался; в полосе 38-50 поставить
карточку вердикта с меткой.

## 2. M2-I02. Meet M2 Lab: who agreed to Friday?

Граница между черновиком и обещанием клиенту. Источники (`notion-raw/11-...`): @joestoltelive 1,766
просмотров, 0.40x медианы; @alliekmiller 35,394, 1.91x; @hamza_automates 1,022,485, 156.46x.
Последний это выброс: медиана автора около 6,500.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-4 | "This reply looks ready. But who agreed to Friday?" | "WHO AGREED TO FRIDAY?" | есть конфликт, это лучший хук слейта | STRUCT |
| S2 | 4-13 | "The note says the team is checking. The draft says Friday." | "SOURCE: DATE UNKNOWN / DRAFT: FRIDAY?" | понятную ставку | NOPROOF |
| S3 | 13-20 | "At M2 Lab, we look for moments like this before connecting AI to everyday work." | "M2 LAB / CHECK THE PROMISE" | ничего | GEN NOUTIL |
| S4 | 20-30 | "AI can work from approved facts; missing facts need a person." | "PREPARE / PROMISE" | правило, но без примера отказа | GEN |
| S5 | 30-40 | "replace the invented date with a question for the order owner" | "QUESTION FOR ORDER OWNER" | конкретный прием | NOPROOF |
| S6 | 40-48 | "The useful output is an editable draft with the gap visible." | "Persistent label: SYNTHETIC DESIGNED DEMO — NOT TESTED." | что это не тест | BRAND NOPROOF |
| S7 | 48-60 | "Underline every promise in the reply. Can you point to the fact and the person behind each one?" | "PROMISE / FACT / PERSON" | выполнимая диагностика | OK |

Пять полей: **Hook** PRESENT по смыслу, WEAK по форме, 4 секунды и вопрос. **Problem** PRESENT, "A
fluent draft can turn an unknown delivery date into a promise" (`notion-raw/11-...:14`).
**Solution** PRESENT. **Tool** MISSING. **CTA** PRESENT.

Ошибки процесса. Плашка `SYNTHETIC DESIGNED DEMO — NOT TESTED` содержит длинное тире, запрещенное в
опубликованном тексте, включая экранный (`05-vocabulary.md:81`), и сама по себе честно сообщает, что
доказательства нет. Один и тот же источник @hamza_automates обслуживает и эту карточку, и M2-P01:
два выпуска из одного приема. Notion Format: M2 Teardown, карточки вердикта нет. S3 это вставка про
бренд посреди разбора, она ломает причинную нить.

Три хода: убрать S3, отдать эти 7 секунд реальному прогону; вместо плашки "NOT TESTED" поставить
снятый экран с реальным черновиком; в 38-50 с дать вердикт с условием.

## 3. M2-I03. Meet M2 Lab: one job before one more subscription

Чек-лист вместо покупки очередной подписки. Источники (`notion-raw/12-...`): @joestoltelive 2,315,
0.52x; @lukebuildsai 835,866, 12.75x; @builders.central 17,660, 1.03x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-7 | "Before your team buys another AI subscription, write down one job it needs to do." | "ONE JOB / ONE CHECKLIST" | тезис, но 7 секунд на хук | STRUCT NOURG |
| S2 | 7-16 | "Suppose customer questions arrive in three places." | "QUESTION to POLICY to CHECKED ANSWER" | абстрактную схему | GEN |
| S3 | 16-22 | "At M2 Lab, our Radar videos look at tools through tasks like this." | "M2 RADAR / TASK FIT" | ничего | BRAND GEN |
| S4 | 22-31 | "use the supplied policy, show missing information, leave the answer editable, and wait before sending" | "CURRENT / VISIBLE GAPS / EDITABLE / NO AUTO-SEND" | рабочий чек-лист из 4 пунктов | OK |
| S5 | 31-40 | "Now try two options with the same fictional question." | "SAME QUESTION / SAME CHECKLIST" | сравнение двух безымянных опций | BRAND LOGIC |
| S6 | 40-51 | "Which answer can your colleague check and correct? What setup would the team have to maintain?" | "CHECK / CORRECT / MAINTAIN" | два верных критерия | OK |
| S7 | 51-60 | "What is one requirement your next subscription would have to pass?" | "MY TASK CHECKLIST" | сохраняемый кадр | OK |

Пять полей: **Hook** WEAK по таймингу. **Problem** PRESENT. **Solution** PRESENT, чек-лист из
четырех критериев это самая полезная сцена слейта. **Tool** MISSING, при том что Notion помечает
карточку Format: M2 Radar, а Radar по `06-formats.md:9` обязан переводить конкретный инструмент в
рабочее решение. **CTA** PRESENT.

Ошибки процесса. Radar без инструмента это формат, вывернутый наизнанку: сравниваются "two options"
A и B, которые нельзя ни назвать, ни проверить, поэтому решение из сцены не вытекает. В S3 сказано
"our Radar videos" без "M2" при первом упоминании (`05-vocabulary.md:87-89`). Прием источника
@lukebuildsai описан как "reactive tool-fit teardown with a self-correction near the end";
самокоррекции в карточке нет.

Три хода: назвать два реальных инструмента и прогнать на них один и тот же вопрос; показать, где
один из них провалился; закрыть меткой TEST с условием.

## 4. M2-I04. Meet M2 Lab: test the awkward enquiry

Три тестовых входа: полный, без срока, с двумя сроками. Источник один (`notion-raw/13-...`):
@heystevetan 13,250 просмотров, 1.01x медианы, прием описан как "demo-led model showcase that moves
from generated game to dashboard".

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-5 | "A perfect example tells you very little about a messy workday." | "Replacement card: TRY THE AWKWARD CASE." | общее наблюдение | STRUCT GEN |
| S2 | 5-14 | "Make three fictional notes before you try it." | "Text: FICTIONAL ENQUIRY to DRAFT." | что примеры выдуманы | NOPROOF |
| S3 | 14-21 | "One has every detail. One has no deadline. The third has two different deadlines." | "COMPLETE / MISSING / CONFLICTING" | готовый набор тест-кейсов | OK |
| S4 | 21-32 | "At M2 Lab, our Builds start with a small test like this." | "PRESERVE FACTS / SHOW UNKNOWNS" | ничего | BRAND NOPROOF |
| S5 | 32-42 | "Conflicting dates should become a question for the person handling the enquiry." | "Label: DESIGNED DEMO — NOT RUN; text: HUMAN REVIEW." | правило эскалации | BRAND |
| S6 | 42-51 | "A tidy paragraph still fails your test if it quietly chooses a date." | "A TIDY DRAFT CAN STILL MISS THE CONFLICT" | критерий провала | OK |
| S7 | 51-60 | "What is the missing detail that catches your team most often?" | "COMPLETE / MISSING / CONFLICTING" | выполнимая подготовка | OK |

Пять полей: **Hook** WEAK и GEN, "A perfect example tells you very little about a messy workday"
подошло бы любому аккаунту. **Problem** PRESENT. **Solution** PRESENT. **Tool** MISSING. **CTA**
PRESENT.

Ошибки процесса. Единственный источник дал прием, не имеющий отношения к теме, и сам он идет ровно
по своей медиане (1.01x), то есть не несет никакого сигнала: карточка опирается на референс, который
ничего не доказал даже своему автору. Плашки `DESIGNED DEMO — NOT RUN` и `DESIGNED DEMO` содержат
длинное тире (`05-vocabulary.md:81`) и признают отсутствие прогона. "our Builds" без "M2" при первом
упоминании. Notion Format: M2 Builds, но сборки нет, вердикта нет.

Три хода: прогнать три заготовленных входа на реальной модели и снять экран; показать, на каком
именно сломалось; заменить плашку "NOT RUN" на карточку вердикта.

## 5. M2-I05. Meet M2 Lab: design the customer handoff

Передача результата клиенту и сотруднику ресепшена. Источники (`notion-raw/14-...`): @benjamlns
19,520, 1.00x; @rence_ur_hands 208,948, 322.20x при медиане около 650.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-6 | "You sent the reminder. Can the customer actually tell what to do next?" | "WHAT SHOULD THE CUSTOMER DO NEXT?" | вопрос без ставки | STRUCT NOURG |
| S2 | 6-17 | "The sending task is done; the customer is stuck." | "DATE KNOWN / NEXT STEP MISSING" | понятный симптом | GEN |
| S3 | 17-26 | "M2 Lab looks at AI adoption from both sides of that handoff." | "CUSTOMER CLARITY / TEAM ACTION" | ничего | GEN NOUTIL |
| S4 | 26-33 | "Map the confirmed facts, the draft reminder, the customer's response, and the staff member who handles changes." | "INPUT to DRAFT to RESPONSE to EXCEPTION" | схема из 4 узлов | OK |
| S5 | 33-42 | "AI could help prepare the wording. Your team still needs to agree what happens." | "AI PREPARES / PERSON DECIDES" | ничего нового | GEN |
| S6 | 42-51 | "Read the message as the customer. ... Then read it as the staff member." | "Designed example only; text: SAME CONFIRMED FACT." | прием двойного чтения | NOPROOF |
| S7 | 51-60 | "At the end of your next process map, draw the person receiving the result." | "RECIPIENT: ____ NEEDS: ____" | одно действие | OK |

Пять полей: **Hook** WEAK, 6 секунд, вопрос. **Problem** PRESENT. **Solution** WEAK, это карта
процесса, а не разобранный шаг. **Tool** MISSING. **CTA** PRESENT.

Ошибки процесса. Фраза "AI could help prepare the wording" в разных видах встречается в пяти
карточках из десяти (I01, I02, I05, P01, P03), это шаблон, а не мысль. Источник с кратностью 322.20x выбран по числу, которое
ничего не значит при медиане в 650 просмотров: процедура самого Макса требует "report the
denominator" (`data/max-latest/primary-editorial-findings-20260907.md:9`), знаменатель показывает,
что это единичный выброс. Notion Format: M2 Teardown; полоса 38-50 с не даёт вывода о том, что
автоматизируем, а что нет (Verdict Card не обязательна — правка 8 сентября, но заключения по
смыслу формата всё равно не хватает). Самая длинная речь слейта, 140 слов на 60 секунд.

Три хода: снять один реальный шаблон напоминания и показать в нем пустое место; назвать роль,
которая обрабатывает исключения, и цену ошибки; закрыть Verdict Card с разметкой автоматизируемых
шагов.

## 6. M2-P01. The appointment reply your workflow forgot

Ветка исключений в записи на прием. Источники (`notion-raw/15-...`): @hamza_automates 1,022,485,
156.46x; @rence_ur_hands 208,948, 322.20x; @kevinfremon 4,202, 0.64x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-4 | "What happens when the customer replies, 'Maybe next week'?" | "Text: TEST THE CHANGE." | конкретный случай | STRUCT |
| S2 | 4-13 | "An appointment demo might show a booking, a reminder, and a happy confirmation." | "Fictional path; text: HAPPY PATH." | чужое демо в пересказе | NOPROOF |
| S3 | 13-20 | "Now draw three branches: confirmed, wants a change, and unclear. Add a fourth for no response." | "CONFIRMED / CHANGE / UNCLEAR / NO RESPONSE" | готовую схему из 4 веток | OK |
| S4 | 20-31 | "AI could suggest a category and draft the next message." | "Text: UNCERTAIN to HUMAN REVIEW." | общая формула | GEN NOPROOF |
| S5 | 31-40 | "Don't quietly turn it into a confirmed date." | "UNCLEAR to ASK" | правило безопасности | OK |
| S6 | 40-49 | "Give each branch an owner and an agreed next step." | "OWNER + NEXT STEP" | верный принцип | OK |
| S7 | 49-60 | "Write the most awkward reply underneath it. Does your process have somewhere for that reply to go?" | "CONFIRMED / CHANGE / UNCLEAR / NO RESPONSE" | выполнимая карта | OK |

Пять полей: **Hook** PRESENT по содержанию, WEAK по форме, 4 секунды и вопрос. **Problem** PRESENT,
"An uncertain reply falls between the happy-path categories" (`notion-raw/15-...`). **Solution**
PRESENT. **Tool** MISSING. **CTA** PRESENT.

Ошибки процесса. S2 строится на пересказе чужого демо, что прямо в списке "не публиковать"
(`06-formats.md:59`). S7 повторяет экранный текст S3 дословно: две сцены из семи несут одну и ту же
надпись. Notion Format: M2 Teardown, вердикта нет. Два источника из трех это те же реелы, из которых
сделана M2-I02 и M2-I05, то есть десять карточек стоят на 16 различных реелах, а обещано 18
отсмотренных (`data/max-latest/m2-ten-card-release.md:7`).

Три хода: заменить пересказ чужого демо на наш собственный скрин ветки исключений; дать цифру,
сколько ответов в неделю попадает в "unclear"; закрыть Verdict Card.

## 7. M2-P02. Turn a competitor post into a customer question

Как читать чужой залетевший пост. Источники (`notion-raw/16-...`): @jasoncooperson 24,544, 1.01x;
@jasoncooperson 7,059, 0.29x; @heystevetan 13,250, 1.01x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-7 | "That competitor post got a lot of views. Which customer question made it worth watching?" | "Original tray label: CUSTOMER QUESTION" | тезис без числа | STRUCT NOURG |
| S2 | 7-16 | "use the number to choose something to inspect. Keep the capture date beside it." | "DATED RESEARCH LEAD" | требование даты без даты | NOURG |
| S3 | 16-26 | "Compare it with the same account's usual views." | "READ THE WORDS / INSPECT THE VISUAL" | верный метод | LOGIC |
| S4 | 26-34 | "Write three notes: the problem introduced, the useful answer, and the visual." | "PROBLEM / ANSWER / VISUAL" | рабочий шаблон разбора | OK |
| S5 | 34-42 | "Pick a question your own customers ask, and answer it with your own example." | "OUR CUSTOMER ASKS: ____" | общее указание | GEN |
| S6 | 42-52 | "A high view count doesn't tell you which detail caused it." | "NEW IDEA to TEST" | верное ограничение | OK |
| S7 | 52-60 | "our customer needs to understand blank. Build the post around that." | "OUR CUSTOMER NEEDS TO UNDERSTAND ____" | одно действие | OK |

Пять полей: **Hook** WEAK, 7 секунд и вопрос. **Problem** PRESENT. **Solution** PRESENT. **Tool**
MISSING при Format: M2 Radar. **CTA** PRESENT.

Ошибки процесса. Логическая дыра в S3: карточка учит сравнивать пост с медианой аккаунта, а сама
построена на трех референсах с кратностью 1.01x, 0.29x и 1.01x, то есть на постах, которые этот тест
не проходят (`notion-raw/16-...`). Карточка про просмотры не показывает ни одного числа на экране,
хотя число это и есть весь предмет разговора. Тема "как смотреть на конкурентов" это внутренняя
кухня контент-мейкера, а не повторяемый рабочий процесс SME, то есть мимо `06-formats.md:32`.

Три хода: вывести на экран реальные два числа, просмотры и медиану аккаунта, с датой съема; показать
наш собственный разбор одного реального поста; закрыть меткой вердикта.

## 8. M2-P03. Give the morning brief a decision owner

Утренняя сводка с колонками "решение" и "владелец". Источники (`notion-raw/17-...`): @alliekmiller
35,394, 1.91x; @joestoltelive 1,766, 0.40x; @olivermerrick___ 8,649, 0.94x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-5 | "Your morning summary has twelve updates. Which one needs you?" | "Text: WHERE DOES THE DECISION GO?" | единственное число во всем слейте, и то выдуманное | STRUCT |
| S2 | 5-15 | "put fictional project notes into three columns: what changed, what needs a decision, and what can wait" | "Persistent label: FICTIONAL INPUTS." | структура сводки | NOPROOF |
| S3 | 15-24 | "AI could group repeated notes and prepare a short draft." | "SUMMARY + SOURCES" | общая формула | GEN |
| S4 | 24-34 | "A line saying 'delivery date unclear' needs a person who can confirm the date, not another summary." | "DECISION NEEDED / OWNER" | сильная мысль карточки | OK |
| S5 | 34-41 | "If two notes disagree, keep both visible." | "DISAGREEMENT to MISSING FACT" | правило | OK |
| S6 | 41-52 | "the owner checks the source, makes the call, and records it" | "CHECK to DECIDE to RECORD" | цикл решения | NOPROOF |
| S7 | 52-60 | "Add 'decision needed' and 'owner.' How many lines actually ask somebody to do something?" | "DECISION NEEDED / OWNER / SOURCE" | выполнимая правка своей сводки | OK |

Пять полей: **Hook** WEAK, вопрос и 5 секунд, "twelve updates" это выдуманное число. **Problem**
PRESENT. **Solution** PRESENT, лучшая по полезности из десяти. **Tool** MISSING. **CTA** PRESENT и
проверяемый.

Ошибки процесса. Notion Format: M2 Builds, но ни собранного, ни запущенного нет, все входы помечены
FICTIONAL. Единственное число в кадре выдумано, тогда как `04-voice.md:7` запрещает публиковать
неизмеренное число. Карточка снова не даёт вывода в полосе 38-50 с; Verdict Card не обязательна
для Builds (правка 8 сентября), но заключения нет вообще.

Три хода: взять нашу реальную утреннюю сводку за неделю и показать, сколько строк из скольких
требовали решения; назвать шаг, где группировка ошиблась; закрыть Verdict Card с WAS / NOW / SAVED
по времени на разбор сводки.

## 9. M2-P04. Ask for the awkward case before buying automation

Что спросить у подрядчика до покупки автоматизации. Источник один (`notion-raw/18-...`):
@bennett.spooner 19,989, 1.00x, прием "sell-before-build narrative".

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-6 | "Someone offers to automate your whole workflow. Ask to see the awkward case first." | "PROPOSAL / AWKWARD CASE" | понятное указание | STRUCT |
| S2 | 6-15 | "Bring a fictional example with a missing detail." | "FICTIONAL ENQUIRY: deadline unknown" | подготовка к встрече | OK |
| S3 | 15-24 | "Ask what goes in, what comes out, and who checks it." | "INPUT to DRAFT to CHECKER" | три вопроса подрядчику | OK |
| S4 | 24-34 | "Does the system stop, ask a question, or quietly guess?" | "DESIGNED EXAMPLE: ASK, DON'T GUESS" | критерий приемки | NOPROOF |
| S5 | 34-43 | "get the open questions in writing: access, running costs, maintenance, and responsibility" | "OPEN QUESTIONS" | четыре пункта в договор | OK |
| S6 | 43-50 | "A successful small example answers a small question." | "ONE TEST / OPEN QUESTIONS" | ограничение вывода | GEN |
| S7 | 50-60 | "add one line: show us how this handles our difficult example" | "OUR DIFFICULT EXAMPLE: ____" | одна строка в запрос | OK |

Пять полей: **Hook** PRESENT по смыслу, WEAK по таймингу, 6 секунд. **Problem** PRESENT.
**Solution** PRESENT. **Tool** MISSING. **CTA** PRESENT, самый практичный в слейте.

Ошибки процесса. Самая полезная карточка десятки и при этом самая слабая по доказательствам: ни
одной цифры про стоимость владения, хотя вся сцена S5 про "running costs". Единственный источник дал
прием, который в карточке не используется. Notion Format: M2 Teardown, вердикта нет. Позиция
говорящего смещена: карточка учит покупателя торговаться с подрядчиком, то есть M2 Lab выступает не
как лаборатория, которая сама строит, а как советчик со стороны, что противоречит
`03-personality.md:22-27`.

Три хода: подставить наши собственные цифры по одному нашему пилоту в строку "running costs";
показать реальный ответ реального инструмента на awkward case; закрыть Verdict Card.

## 10. M2-P05. Add a failure column to your AI shortlist

Колонка отказов в сравнении инструментов. Источники (`notion-raw/19-...`): @builders.central 17,660,
1.03x; @lukebuildsai 835,866, 12.75x; @joestoltelive 2,315, 0.52x.

| Сцена | сек | Речь | На экране | Что уносит зритель | Вердикт |
|---|---|---|---|---|---|
| S1 | 0-4 | "Your AI tool comparison needs a failure column." | "Text: RANK THE FAILURE FIRST." | четкий тезис, лучший хук по форме | STRUCT |
| S2 | 4-12 | "Imagine two tools preparing the same weekly stock note. ... Both leave out an item." | "Label: FICTIONAL STOCK DATA." | воображаемый пример | NOPROOF |
| S3 | 12-22 | "write down how your team would spot that missing item" | "SOURCE LIST / DRAFT" | конкретный способ проверки | OK |
| S4 | 22-31 | "Now test an invented number, a late draft, and a mistaken send instruction." | "WHAT SHOULD HAPPEN?" | три режима отказа | OK |
| S5 | 31-40 | "the same fictional input, the same checks, and a person responsible" | "SAME INPUT / SAME CHECK" | принцип контроля | GEN BRAND |
| S6 | 40-49 | "Include the work needed to correct an error." | "INCLUDE THE COST OF CORRECTION" | верная мысль без цены | GEN |
| S7 | 49-60 | "Add three columns to your shortlist: failure, how we'll notice, and who fixes it." | "FAILURE / HOW WE NOTICE / WHO FIXES IT" | готовая таблица | OK |

Пять полей: **Hook** PRESENT, один из четырех утвердительных хуков без вопроса (наряду с I03, I04,
P04), но 4 секунды вместо 3.
**Problem** PRESENT. **Solution** PRESENT. **Tool** MISSING при Format: M2 Radar. **CTA** PRESENT.

Ошибки процесса. Карточка про сравнение инструментов не называет ни одного инструмента и не приводит
ни одной цифры отказов, хотя весь ее тезис в том, что отказы надо измерять. Данные склада
("notebooks12; pens20; folders7") выдуманы. Radar без инструмента нарушает `06-formats.md:9`.
Полоса вердикта тоже пустая, но само по себе отсутствие Verdict Card не нарушение (правка
8 сентября); в частотной таблице метка BRAND у сцены S5 всё равно сохранена, потому что источник
называет обе причины одним предложением и разделить их нельзя (см. сноску там же).

Три хода: взять два реальных инструмента и один наш реальный отчет; показать, сколько строк каждый
потерял; закрыть карточкой вердикта KEEP или TEST с условием.

# Сквозной разбор

## Частота ошибок по 70 кадрам

| Тип | Кадров | Где особенно |
|---|---|---|
| GEN, обобщение | 16 | сцены 2-5, пересказ позиционирования и формула "AI could help with" |
| NOPROOF, нет доказательства | 14 | все `fixture.state` равны DESIGNED_NOT_MODEL_EXECUTED |
| STRUCT, структура и тайминг | 12 | сцена 1 во всех 10 карточках длится 4-7 с при норме 0-3 с |
| BRAND, нарушение правила бренда | 6 | длинное тире (I02 S6, I04 S5), "Radar"/"Builds" без "M2" (I03 S3, I04 S4), сравнение безымянных инструментов (I03 S5); P05 S5 — причина неоднозначна, метка сохранена (см. сноску в разборе P05) |
| NOURG, нет срочности | 5 | хуки и контекстные сцены, ни одной даты и цифры |
| NOUTIL, нет пользы | 3 | сцены-вставки про бренд: I01 S2, I02 S3, I05 S3 |
| LOGIC, логическая ошибка | 2 | I03 S5 сравнение безымянных опций, P02 S3 медиана |
| OK | 27 | почти все это сцены 3, 4 и 7 |

Итого 27 кадров из 70 работают, 43 несут хотя бы одну ошибку. Пересчитано 8 сентября: 6 BRAND-меток,
поставленных только за отсутствие Verdict Card, сняты (I01 S6, I05 S6, P01 S6, P02 S6, P03 S6,
P04 S6) — карточка не обязана заканчиваться Verdict Card. Два кадра (P01 S6, P02 S6) не несли других
ошибок и перешли в OK; остальные четыре сохранили вторую метку (STRUCT, NOPROOF, NOPROOF, GEN).
Сильные места всегда одни и те же: сцена с готовым списком критериев и финальный кадр с пустым
бланком. Слабые тоже одни и те же: хук и сцена про бренд.

Уровень карточки, не кадра:
- 10 из 10 не называют ни одного инструмента. Поле Tool отсутствует полностью.
- 10 из 10 не содержат ни одной измеренной цифры, ни WAS / NOW / SAVED (`04-voice.md:91`).
- 10 из 10 не содержат Verdict Card и не дают иного вывода взамен неё. Verdict Card не обязательна
  в каждом ролике (решение Миши от 8 сентября, брендбук обновляется параллельно), но отсутствие
  любого вывода в полосе 38-50 с — наблюдение, которое стоит закрыть.
- 10 из 10 не называют ни Михаила, ни Макса, то есть нет "human face" из
  `03-personality.md:40`.
- 6 из 10 хуков это вопрос: I01, I02, I05, P01, P02, P03. Остальные четыре, I03, I04, P04 и P05,
  это утверждение (`04-voice.md:68`).
- 12 из 16 использованных реелов-источников идут на уровне или ниже медианы
  собственного автора. Только 4 выше, и два из них выбросы с кратностью 156x и 322x.

## Корневые причины в конвейере

1. **Карточки написаны из текста позиционирования и учебника, а не из реелов.**
   `data/max-latest-pipeline.md:24` фиксирует, что позиционирование пришло из
   `knowledge/m2-positioning.md` цитатой "Use the five-step method: a repeated task,
   a process map, an AI boundary, human review, and a first test", а
   `pipeline.md:26` описывает второй вход как "bounded intake from the 29-page
   Popular Expert Creators' Techniques and Methods extraction. It is a secondary,
   untrusted reference". В результате у всех десяти карточек одна и та же
   драматургия и один и тот же набор фраз: агент пересказывал метод, а не разыгрывал
   конкретный случай. Отсюда 16 кадров GEN.

2. **Нет извлечения пяти полей из каждого реела.** Ни в одном артефакте нет разбора
   источника по hook, problem, solution, tool, CTA. Есть только одна строка на реел,
   "What informed this script" в Notion, например "demo-led model showcase that moves
   from generated game to dashboard" (`notion-raw/13-...`). Прием назван и не
   использован. Именно этого просит Макс, и именно этого в конвейере нет.

3. **Кадры источников никто не смотрел покадрово.** `pipeline.md:41` фиксирует
   реальный декодинг всего 64 кадров по 3 реелам с состоянием
   "CANDIDATE_NOT_ACCEPTED" и оговоркой "this does not establish complete visual
   coverage, confirmed shots, business claims, or semantic acceptance". А
   раскадровки самих карточек, по `pipeline.md:30,43`, это
   `"kind": "ILLUSTRATED_CONTACT_SHEET"` с пометкой "Composition guide only; not an
   owner take, product output, or production asset binding". То есть в релизе кадры
   выдаются за визуальную часть, хотя это рисованные заглушки. Динамика видео,
   про которую говорит Макс, нигде не измерена.

4. **Транскрипты не прочитаны.** `pipeline.md:53`: покрытие выросло до 45.2%, но
   "The other 1,044 transcripts have lexical inventory but still need detailed
   semantic review", полностью прочитано 18 источников. Ни одной цитаты из
   транскрипта в карточках нет: есть только ссылки на страницы Notion.

5. **Семь сцен и 60 секунд назначены заранее, до темы.** `pipeline.md:30`: "every
   card has hooks (3 strings), a 7-row shots array". Notion подтверждает: у всех
   десяти карточек одинаковые заголовки сцен, "Hook: show the problem",
   "Context: make it familiar", "Build the idea", "Demonstrate the method",
   "Make the decision visible", "Check the result", "Give the viewer a next step".
   Шаблон, а не структура темы. Отсюда сцены-вставки про бренд и хук длиной 7 секунд.

6. **Бренд-пак в этой ветке отсутствует.** `pipeline.md:18,32`: папка `design/`
   удалена, "The M2 Lab visual brand kit does not exist in this branch's checkout at
   all", бренд-пак "NOT consumed". Поэтому ни правила вердикта, ни запрет длинного
   тире, ни правило именования Radar и Builds в карточки не попали. Это же объясняет
   расхождение формулировок: карточки писались под старое позиционирование, где
   единицей были "repeated task" и "process map", а действующее правило
   `05-vocabulary.md:7-8` требует "repeated workflow" как единицу и оставляет
   "repeated task" только за одной задачей внутри процесса. Считаю это одним
   расхождением на весь слейт, а не десятью.

7. **Отбор источников идет по чужой нише.** Все 16 реелов это контент про агентов,
   саб-агентов и автоматизации для технической аудитории: "multi-agent advisory board
   with debate", "fan-out/fan-in sub-agent workflow", "always-on agents"
   (`notion-raw/10,16,17`). `02-audience.md:35-37` прямо выводит эту аудиторию за
   пределы M2. Конвейер брал приемы у тех, кому мы не пишем.

8. **AWAITING_OWNER_ASSET закрывает дыру в идее.** Все 80 ассетов десяти карточек
   помечены `"state": "AWAITING_OWNER_ASSET"` (`M2-I04.json:161`,
   `M2-I01.json:161`). Там, где должно быть доказательство, стоит обещание, что
   владелец что-нибудь снимет. Формально это честно, практически это переносит
   отсутствующую идею на съемочную площадку.

## Три главных исправления на следующий прогон

**1. Схема извлечения из реела, обязательная перед написанием карточки.** Артефакт:
`reel-extraction.v1.json`, по одному файлу на каждый реел-источник. Поля: цитата хука дословно с
таймкодом, кому адресован, проблема одной строкой, решение, названный инструмент, CTA дословно, три
кадра с описанием, что на них видно, момент первой смены плана, число просмотров с датой и медиана
автора со знаменателем. Правило: карточка не начинается, пока для каждого ее источника нет такого
файла. Это закрывает причины 2, 3, 4 и дает Максу ту самую последовательность.

**2. Чек-лист карточки перед сдачей, восемь пунктов, без вариантов трактовки.** Артефакт:
`card-checklist.md` рядом с карточками, заполняется как таблица PASS / FAIL по каждой карточке.
Пункты: назван ли инструмент; есть ли измеренное число в формате WAS / NOW / SAVED с источником;
если ролик выносит вердикт — стоит ли Verdict Card в полосе 38-50 с, если нет — есть ли там один
вывод из доказательства (Verdict Card не обязательна в каждой карточке, решение от 8 сентября); хук
утвердительный и укладывается в 3 секунды и 6-8 слов;
названы ли шаг, который сломался, и человек, который проверяет; ни одного слова из запретного списка
`05-vocabulary.md:28-81` и ни одного длинного тире; первое упоминание пилара в виде "M2 Radar", "M2
Builds", "M2 Teardowns"; экранная строка не длиннее 20 символов. Сегодня по этому чек-листу проходит
0 карточек из 10.

**3. Ворота на источники и на структуру, до генерации.** Артефакт: `source-gate.md` плюс правило в
конвейере. Реел допускается в источники только если он выше медианы своего автора не менее чем в 1.5
раза, знаменатель не меньше 20 реелов, кратность не выше 20 (чтобы отсечь выбросы вроде 156x и
322x), и его тема полезна руководителю малого или среднего бизнеса — процесс, инструмент, приём или
обучение, а не разработка агентов. Число сцен и длина
выбираются под тему после написания тела, а не заданы шаблоном: минимум три сцены отдаются полосе
доказательства 12-38 с, и ни одна сцена не тратится на пересказ позиционирования. Это закрывает
причины 5 и 7.
