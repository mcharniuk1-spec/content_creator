# M2 Content Radar — brief для разработки MVP

Привет. Ниже — понятное описание инструмента, который нужно собрать для M2 Lab. Цель документа: чтобы ты мог понять продукт, разбить его на задачи и начать разработку без дополнительного погружения в предыдущие обсуждения.

---

## 1. Что мы строим

**M2 Content Radar** — внутренний инструмент для ресерча контента в Instagram и TikTok.

Он должен следить за выбранными англоязычными creators, находить их самые сильные свежие ролики, объяснять их механику и каждую субботу выдавать Михаилу и Максу 5–7 оригинальных идей для M2 Lab.

Это **не** автопостер и не фабрика автоматически написанных сценариев. Его главная задача — уменьшить ручной ресерч и помочь быстрее выбрать хорошие темы для съёмки.

### Как выглядит успех MVP

К субботе у команды есть короткий и понятный weekly brief:

- что сильного произошло у наблюдаемых creators за неделю;
- какие механики повторяются;
- почему эти механики могли сработать;
- 5–7 идей, адаптированных под M2 Lab;
- ссылки и доказательства, чтобы можно было быстро проверить выводы.

Время Михаила и Макса на ресерч и выбор тем — не более **3 часов в неделю**.

---

## 2. Контекст M2 Lab

M2 Lab — англоязычный проект Михаила и Макса о практическом применении AI, агентов и автоматизаций в реальной бизнес-работе.

### Аудитория

Люди, отвечающие за процессы в компании: operations, sales, владельцы малого бизнеса. Им нужен не AI-news, а ответ на вопрос: «Стоит ли внедрять это в мой конкретный процесс?»

### M2 point of view

- Workflow важнее инструмента.
- Demo не равно business value.
- Хорошая автоматизация начинается с понимания процесса.
- AI полезен не везде; честный verdict важнее hype.

### Внешние форматы M2

| Формат | Зачем нужен |
|---|---|
| **Radar** | Реакция на актуальную тему или инструмент через бизнес-угол. |
| **Builds** | Собственный тест, сборка workflow, ошибка, comparison или screen demo. |
| **Teardown** | Разбор конкретного бизнес-процесса: где теряются время/деньги и где AI уместен. |

### Нельзя предлагать

- generic AI-news без M2 business angle;
- «top 10 tools» без конкретного процесса;
- обещания дохода или «AI заменит всех»;
- копирование чужого текста, хука, ролика или монтажа;
- идею без собственного M2 proof: теста, экрана, workflow, кейса, позиции Михаила/Макса.

Этот контекст нужно хранить в версии `M2_CONTEXT.md` в репозитории и подмешивать в все AI-вызовы, связанные с генерацией идей.

---

## 3. Пользовательский сценарий

### До запуска

Михаил и Макс вручную создают список из **30 creators**, за которыми хотят следить.

У creator должны быть поля:

```text
platform
handle
profile URL
status: active / paused / candidate
archetype: builder / operator / educator / opinion / news
topics
why we follow
notes
```

### В течение недели

1. Система каждый день собирает новые публикации 30 creators.
2. Михаил/Макс могут вручную отправить ссылку на любой ролик в Telegram-бота.
3. Система сохраняет и полноценно анализирует весь новый контент, который публикуют creators из утверждённого watchlist.

### В субботу

1. Система создаёт страницу Weekly Brief в Notion.
2. Отправляет короткое сообщение в Telegram с итогом и ссылкой на Notion.
3. Михаил и Макс отмечают идеи: `Shoot`, `Hold` или `Reject`.

### После публикации собственного ролика

Михаил/Макс вносят результаты 24ч, 72ч и 7д. Система фиксирует, какие типы идей реально работают для M2, а не только для чужих creators.

---

## 4. Схема работы

```text
                 WATCHLIST: 30 CREATORS
                            +
               TELEGRAM: MANUAL URL INBOX
                            │
                            ▼
                   1. COLLECT POSTS
             Instagram / TikTok / manual links
                            │
                            ▼
                 2. NORMALIZE + DEDUPE
       единый формат данных, snapshots, language/safety filter
                            │
                            ▼
                  3. ANALYZE ALL POSTS
 transcript + frames + caption + comments → structured analysis
                            │
                            ▼
                 4. RANK THE WEEK
     выделить сильные ролики относительно их автора
                            │
                            ▼
                 5. FIND PATTERNS
             повторяемые механики и Opportunity Score
                            │
                            ▼
                  6. M2 IDEA SYNTHESIS
       оригинальная адаптация с proof и target signal
                            │
                            ▼
               NOTION WEEKLY BRIEF + TELEGRAM
                            │
                            ▼
         SHOOT / HOLD / REJECT + M2 RESULTS LOG
                            │
                            └───── feedback loop ─────┘
```

---

## 5. Что собирать по каждому посту

Нужно хранить raw response поставщика отдельно от нормализованных данных. Разные платформы/сборщики возвращают разные поля; raw JSON понадобится при смене источника или отладке.

### Базовая структура Post

```json
{
  "platform": "instagram | tiktok",
  "external_id": "string",
  "permalink": "url",
  "creator_id": "uuid",
  "published_at": "ISO-8601",
  "collected_at": "ISO-8601",
  "caption": "string | null",
  "duration_s": 0,
  "views": null,
  "likes": null,
  "comments": null,
  "shares": null,
  "thumbnail_url": "url | null",
  "video_url": "url | null",
  "raw_json": {},
  "status": "collected | analysed | failed"
}
```

Важно: `null` означает «поставщик не дал метрику». Нельзя заменять `null` на `0`.

### Дополнительно

- временный MP4 ролика, если доступен;
- extracted audio;
- набор кадров: 0s, 1s, 3s, затем каждые 5 секунд;
- транскрипт с таймкодами;
- ограниченная выборка комментариев;
- snapshots публичных метрик при каждом сборе.

Видео и кадры хранить в private S3-compatible storage. Не хранить чужие видео бессрочно; рекомендованный retention — 90 дней. Ссылка на оригинал должна быть постоянной частью записи.

---

## 6. Как ранжировать сильные ролики

Нельзя выбирать ролики только по абсолютному числу views: 100k views у миллионника могут быть слабым результатом, а 20k views у маленького автора — сильным.

Система **не отбрасывает** контент утверждённых creators до AI-анализа: весь их новый контент сохраняется, транскрибируется и разбирается. Ранжирование нужно только для того, чтобы в weekly brief наверху оказались самые перспективные ролики и паттерны.

### Первые 4 недели

Пока нет исторического baseline, использовать простой preliminary score:

- свежесть поста;
- views;
- likes/views;
- comments/views;
- ручная релевантность creator;
- English-only;
- разнообразие авторов: не допускать, чтобы 2 больших creators заняли весь weekly brief.

Все оценки в этот период помечать `low_confidence`.

### После накопления данных

Сравнивать новый ролик с обычными роликами **того же автора** и близкого возраста.

Пример логики:

```text
view_velocity = прирост views / время после первого snapshot
creator_baseline = median velocity прошлых роликов автора
breakout_ratio = view_velocity / creator_baseline

engagement_ratio =
  сравнение likes/views и comments/views с обычным уровнем автора

market_signal = breakout_ratio + engagement_ratio
```

Формула может меняться. Важно правило: один viral post — это кандидат на исследование, но не доказанный паттерн.

Если за неделю появляется слишком много контента, ограничивать нужно не анализ watchlist, а размер итогового брифа: в Notion остаётся полный архив разборов, а в субботний brief попадают только лучшие и наиболее релевантные выводы.

---

## 7. Что должен делать AI-анализатор

AI не должен писать абстрактные выводы вроде «сильный хук». Он должен вернуть валидный JSON с конкретными evidence и таймкодами.

### Пример ожидаемого результата

```json
{
  "language": "en",
  "hook": {
    "text": "...",
    "start_s": 0,
    "end_s": 2.8,
    "type": "contrarian_claim"
  },
  "segments": [
    {
      "role": "process | workflow | test | verdict | return_hook | cta",
      "start_s": 0,
      "end_s": 0,
      "evidence": "..."
    }
  ],
  "visual_mechanic": ["face_to_camera", "screen_demo"],
  "format": "Radar | Build | Teardown | other",
  "target_signal": "reshare | save | follow | search | comment",
  "share_reason": "...",
  "comment_demand": ["..."],
  "claims_to_verify": ["..."],
  "originality_risk": "low | medium | high",
  "analysis_confidence": 0.0
}
```

### Правила для анализатора

- Каждый вывод должен опираться на transcript, кадр, caption, комментарий или публичную метрику.
- Если нет данных — писать `unknown`, а не выдумывать.
- Не утверждать, что ролик «залетел из-за алгоритма».
- Не смешивать caption и spoken transcript.
- Сразу блокировать порнографию и сексуально-откровенный контент до глубокого анализа.

---

## 8. Как превращать паттерн в M2-идею

Главное правило: система не копирует чужие ролики. Она берёт только механику внимания и превращает её в M2 content.

```text
Чужая механика
        ↓
M2 point of view
        ↓
Конкретный бизнес-процесс
        ↓
Собственный тест / screen / спор / мнение
        ↓
Честный verdict
        ↓
Оригинальная M2-идея
```

Пример:

```text
Не делать:
«Этот AI tool переоценён — вот почему»

M2 версия:
«Мы дали AI-агенту сделать lead research для B2B.
Он полезен только в одном шаге — дальше начинает придумывать данные».
```

### Обязательные поля M2-идеи

```text
title
M2 format: Radar / Build / Teardown
target signal: reshare / save / follow / search / comment
one-sentence premise
evidence posts / links
why this is a signal
M2 angle
proof asset: что реально показать
hook direction
honest verdict / limitation
Opportunity Score
status: Shoot / Hold / Reject
```

### Два обязательных гейта

1. **Originality gate** — можно ли снять это своим голосом, на своём экране, со своим тестом и своим выводом?
2. **M2 proof gate** — есть ли process → workflow → test → verdict?

Если ответ на любой из них «нет», идея не входит в weekly brief.

---

## 9. Opportunity Score

Для старта использовать уже согласованную формулу:

```text
30% Market Signal
30% M2 Lab Fit
20% Repeatability
10% Production Feasibility
10% Comment Demand
```

Каждая часть — оценка 1–5 с коротким объяснением.

| Критерий | Вопрос |
|---|---|
| Market Signal | Есть ли реальный относительный успех и/или повторение механики у других? |
| M2 Lab Fit | Усиливает ли идея позиционирование M2, а не превращает нас в AI-news канал? |
| Repeatability | Захотим ли мы снять 30-й ролик такого типа? |
| Production Feasibility | Можно ли снять это нашими силами в ближайшую неделю? |
| Comment Demand | Есть ли реальные вопросы/возражения, на которые идея отвечает? |

---

## 10. Что должно быть в Notion

Notion — интерфейс для Михаила и Макса. Это не место для очереди задач и тяжёлых raw files; техническая память должна жить в backend database.

Нужно создать шесть связанных баз:

| База | Что хранит |
|---|---|
| **Creators** | Watchlist, кандидаты, архетипы, темы, статус. |
| **Posts** | Собранные ролики, метрики, transcript, AI-разбор. |
| **Patterns** | Повторяемые механики и evidence posts. |
| **Ideas** | M2-идеи, scores и решения Shoot/Hold/Reject. |
| **Weekly Briefs** | Итоги конкретной недели. |
| **Produced Log** | Результаты опубликованных M2-роликов. |

### Weekly Brief в Notion

Должен содержать:

```text
Период недели
Сколько постов собрано
Сколько глубоко проанализировано
Главные паттерны недели
5–7 идей
Кандидаты новых creators
Вопросы/спрос из комментариев
Что сработало у M2 на прошлой неделе
```

---

## 11. Telegram-бот

Telegram — быстрый вход и доставка, не основная база.

### Минимальные функции

```text
<URL>
Добавить ролик в ручной inbox.

/add instagram @handle
/add tiktok @handle
Добавить creator в Candidate list.

/approve_creator <id>
/reject_creator <id>

/brief
Отправить текущий weekly brief.
```

### Субботнее сообщение

```text
M2 Radar · 16–22 Aug

Collected: 184 posts
Deep analysis: 67 posts
Patterns: 4

Главный сигнал недели:
Anti-hype workflow verdicts чаще вызывают пересылку,
чем нейтральные tool explainers.

Top ideas:
1. [Build] ... · 86/100
2. [Radar] ... · 82/100
3. [Teardown] ... · 78/100

Открыть полный brief в Notion
```

---

## 12. Feedback loop для M2

После публикации собственного M2 ролика нужно вручную заносить результаты:

```text
24h / 72h / 7d
views
non-follower reach
follows from reel
shares
saves
comments
retention data, если доступно
```

Плюс редакционная метка:

```text
идею сняли / не сняли
почему
что бы изменили в следующий раз
```

Система должна считать на 1,000 views:

```text
shares per 1,000
saves per 1,000
follows per 1,000
```

Это позволит через 8–12 недель менять scoring на основе собственных результатов M2.

---

## 13. Рекомендуемая архитектура

### Почему не только Notion + n8n

Notion и n8n удобны для интерфейса и простых автоматизаций, но неудобны для:

- повторных metric snapshots;
- дедупликации;
- очередей и retry;
- хранения raw data;
- работы с видео;
- тестов и версий логики.

### Предлагаемый стек

```text
Backend:
TypeScript/Node.js или Python — выбрать то, на чём быстрее пишет разработчик.

Database:
PostgreSQL / Supabase.

Background jobs:
один worker + cron. Не нужны Kafka, Temporal и микросервисы.

Object storage:
private S3-compatible bucket для временных video/audio/frame files.

Collection:
SourceAdapter interface.
Отдельные adapters для Instagram, TikTok и manual URL inbox.
Scraper provider должен быть заменяемым.

AI:
1) transcription с timestamps;
2) дешёвая модель для массового extraction;
3) более сильная модель для weekly synthesis и critic pass;
4) отдельный critic pass.

Human interface:
Notion API + Telegram Bot API.

Optional n8n:
cron, Telegram delivery, простые webhooks.
Не использовать как единственное место для основной бизнес-логики.
```

### Ключевой технический принцип

Сделать интерфейс `SourceAdapter`, а не привязывать систему к одному scraper-провайдеру:

```typescript
interface SourceAdapter {
  fetchCreatorRecentPosts(creator: Creator): Promise<RawPost[]>;
  fetchPostByUrl(url: string): Promise<RawPost>;
  fetchMedia?(post: RawPost): Promise<MediaAsset>;
}
```

Причина: официальные API Instagram/TikTok не покрывают в нужном виде постоянный мониторинг произвольных creators. Поставщики публичного сбора могут менять schema, цену и доступность.

---

## 14. Последовательность разработки

### Этап 0 — подготовка

1. Создать репозиторий и `M2_CONTEXT.md`.
2. Создать Notion integration и шесть баз.
3. Создать Telegram-бота и приватную группу.
4. Внести 30 creators.
5. Выбрать scraper provider после теста на 3 аккаунтах.

**Готово, когда:** ссылка, отправленная в Telegram, создаёт запись Post в Notion.

### Этап 1 — вертикальный срез на 10 ссылках

1. Реализовать models/tables: Creator, Post, MetricSnapshot, Analysis, Pattern, Idea, ProducedResult, Job.
2. Реализовать ручной URL ingest.
3. Реализовать extract audio/frames/transcript.
4. Реализовать AI-analysis c JSON schema validation.
5. Запустить на 10 реальных референсах.

**Готово, когда:** Михаил и Макс считают разбор полезным минимум в 8 из 10 случаев: верно выделены hook, структура и M2-adaptation.

### Этап 2 — ежедневный мониторинг 30 creators

1. Реализовать InstagramAdapter и TikTokAdapter.
2. Реализовать cron, job queue, retry/backoff.
3. Реализовать raw storage и dedupe.
4. Добавить metric snapshots.
5. Реализовать preliminary weekly ranking.

**Готово, когда:** новые посты за неделю автоматически появляются без дубликатов; ошибки источника видны и не ломают весь прогон.

### Этап 3 — weekly brief

1. Реализовать outlier/baseline logic.
2. Реализовать Pattern entity.
3. Реализовать M2 Idea synthesis с двумя gates.
4. Реализовать critic pass.
5. Создавать Notion Weekly Brief + Telegram summary.

**Готово, когда:** в субботу команда получает 5–7 проверяемых идей и может выбрать, что снимать, без повторного многочасового ресерча.

### Этап 4 — feedback loop

1. Добавить статусы Shoot/Hold/Reject и причины.
2. Добавить ввод M2 metrics для 24ч / 72ч / 7д.
3. Добавить dashboard/summary по M2 форматам и signals.
4. Через 8–12 недель пересмотреть weights Opportunity Score.

**Готово, когда:** следующий бриф учитывает не только рынок, но и прошлые результаты M2.

---

## 15. Что не делать в первой версии

- Не строить отдельную красивую веб-панель.
- Не делать автоматический поиск сотен creators.
- Не добавлять YouTube, X, Threads и news sources до работающих Instagram/TikTok.
- Не делать full scripts, captions и autopublishing до доказанного качества weekly ideas.
- Не запускать 5–10 независимых «агентов» без общей базы и строгих contracts.
- Не расширять watchlist бесконтрольно: весь контент уже утверждённых creators анализируется полностью, поэтому качество списка важнее его размера.

---

## 16. Риски и обязательные guardrails

| Риск | Что сделать |
|---|---|
| Поставщик данных меняет ответ или перестаёт работать | `SourceAdapter`, raw JSON, manual URL fallback. |
| Дубликаты и плохие данные | stable external ID + permalink + idempotent jobs. |
| AI галлюцинирует | JSON schema, evidence/timestamps, `unknown` вместо догадки, critic pass. |
| Идея слишком похожа на референс | Originality gate и запрет на повтор чужого текста/кадров. |
| Расходы на AI растут | Candidate filter до video/transcript analysis; дешёвая модель для extraction. |
| Система производит шум | Brief только раз в неделю; ежедневные ошибки — только при повторном сбое. |
| Аккаунт M2 подвергается риску | Read-only research; не использовать логин M2 для scraping; не ставить лайки, подписки, комментарии. |

---

## 17. Критерии приёмки MVP

MVP можно считать готовым, если:

- [ ] 30 creators можно добавить, приостановить и просматривать в Notion.
- [ ] Ссылка из Telegram попадает в систему и обрабатывается.
- [ ] Новые посты watchlist собираются по расписанию.
- [ ] Повторные запуски не создают дубликаты.
- [ ] Система хранит snapshots метрик.
- [ ] Для выбранных роликов есть transcript, hook, структура, target signal и evidence.
- [ ] В субботу автоматически появляется Notion Weekly Brief.
- [ ] Telegram получает краткую сводку с ссылкой на brief.
- [ ] Brief содержит 5–7 M2-идей, а не просто список viral posts.
- [ ] Каждая M2-идея проходит Originality gate и M2 proof gate.
- [ ] Можно зафиксировать Shoot/Hold/Reject и результат опубликованного M2 ролика.

---

## 18. Главная мысль

Самый важный первый результат — не «автономный AI-агент», а один надёжный цикл:

```text
реальные посты → качественный разбор → хорошие M2-идеи → съёмка → результат → улучшение следующего выбора
```

Сначала нужно доказать этот цикл на 10 реальных ссылках. После этого масштабирование на 30 creators, weekly brief и дополнительные платформы будет технической работой, а не угадыванием продукта.
