"""База радара. Один файл SQLite, вся история снимков.

Использование:
    from db import connect
    con = connect()            # создаст data/radar.db и схему, если их нет
"""
import os
import re
import sqlite3

CODE_RX = re.compile(r'[A-Za-z0-9_-]{5,30}')


def safe_code(code):
    """Код ролика уходит в HTML, в имена файлов и в пути. Всё, что не подходит
    под формат Instagram, до системы не допускается: одна проверка на входе
    закрывает и разметку страницы, и выход за каталог кадров."""
    return bool(code) and bool(CODE_RX.fullmatch(str(code)))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'radar.db')

SCHEMA = """
PRAGMA foreign_keys = ON;

-- 1. Аккаунты набора. Выбывшие не удаляются: при доборе видно, что аккаунт уже был.
CREATE TABLE IF NOT EXISTS accounts (
    pk              INTEGER PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    full_name       TEXT,
    follower_count  INTEGER,
    following_count INTEGER,
    media_count     INTEGER,
    biography       TEXT,
    category        TEXT,
    is_verified     INTEGER,
    is_private      INTEGER,
    tag             TEXT,                      -- core / neighbor / out
    status          TEXT NOT NULL DEFAULT 'active',  -- active / dropped / candidate
    misses          INTEGER NOT NULL DEFAULT 0,      -- проваленных проверок подряд; 2 = выбыл
    added_at        TEXT,
    last_checked    TEXT,
    checked_snapshot INTEGER,                  -- на каком снимке проверяли живость
    dropped_at      TEXT
);

-- 2. Снимки. Каждый сбор — отдельная строка, снимки не перезаписывают друг друга.
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    taken       TEXT NOT NULL UNIQUE,          -- YYYY-MM-DD
    accounts_n  INTEGER,
    reels_n     INTEGER,
    units       INTEGER,                       -- единиц HikerAPI на этот сбор
    done        INTEGER NOT NULL DEFAULT 0,    -- 1 только у сбора, дошедшего до конца
    note        TEXT
);

-- 3. Ролик в конкретном снимке. Один код встречается в каждом снимке заново.
CREATE TABLE IF NOT EXISTS reels (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    code        TEXT NOT NULL,
    pk_user     INTEGER,
    username    TEXT,
    ts          INTEGER,                       -- дата публикации, unix
    kind        TEXT,
    play        INTEGER,
    likes       INTEGER,
    comm        INTEGER,
    resh        INTEGER,
    save        INTEGER,
    dur         REAL,
    cap         TEXT,
    followers   INTEGER,                       -- подписчиков автора на момент снимка
    PRIMARY KEY (snapshot_id, code)
);

-- 4. Оценка. Компоненты в отдельных колонках; NULL = компонента выброшена.
CREATE TABLE IF NOT EXISTS scores (
    snapshot_id       INTEGER NOT NULL REFERENCES snapshots(id),
    code              TEXT NOT NULL,
    z                 REAL,
    eligible          INTEGER,                 -- прошёл порог отбора
    author_median_play INTEGER,                -- медиана автора на момент расчёта
    c_views REAL, c_eng REAL, c_resh REAL, c_save REAL, c_comm REAL,
    resh_1k REAL, save_1k REAL, comm_1k REAL,
    baseline_n        INTEGER,                 -- роликов автора в базе сравнения
    baseline_snaps    INTEGER,                 -- по скольким снимкам она собрана
    axes              INTEGER,                 -- на скольких компонентах посчитана оценка
    weights           TEXT NOT NULL DEFAULT 'ig',  -- чьи веса считали
    -- веса входят в ключ: без этого второй набор весов физически не сохранить,
    -- а защита от повтора по чужому тегу была фикцией
    PRIMARY KEY (snapshot_id, code, weights)
);

-- 5. Темы. Много к одному.
CREATE TABLE IF NOT EXISTS topics (
    code   TEXT NOT NULL,
    topic  TEXT NOT NULL,
    source TEXT,                               -- manual (верхушка) / sample (выборка)
    PRIMARY KEY (code, topic)
);

-- 6. Разбор верхушки: склейки, вес файла, пригодность после раскадровки.
CREATE TABLE IF NOT EXISTS deepdives (
    code        TEXT PRIMARY KEY,
    snapshot_id INTEGER REFERENCES snapshots(id),
    cuts        INTEGER,
    cuts_ps     REAL,
    mp4_mb      REAL,
    sheet       TEXT,                          -- путь к контактному листу
    suitable    INTEGER,                       -- 1 годен / 0 нет; NULL — не проверяли
    unfit_why   TEXT,
    done_at     TEXT
);

-- 7. Кадры и таймкоды.
CREATE TABLE IF NOT EXISTS frames (
    code  TEXT NOT NULL,
    idx   INTEGER NOT NULL,
    t_sec REAL,
    path  TEXT,
    PRIMARY KEY (code, idx)
);

-- 8. Расшифровки.
CREATE TABLE IF NOT EXISTS transcripts (
    code     TEXT PRIMARY KEY,
    lang     TEXT,
    words    INTEGER,
    text     TEXT,
    segments TEXT                              -- JSON, посегментно с таймкодами
);

-- 9. Что опубликовали мы.
CREATE TABLE IF NOT EXISTS our_posts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    published_at TEXT,
    format       TEXT,
    topic        TEXT,
    url          TEXT,
    lead         TEXT,                         -- кто в кадре
    goal         TEXT,                         -- к чему ведём
    ref_code     TEXT,                         -- референс, с которого шла карточка
    note         TEXT
);

-- 10. Шесть чисел на свой ролик. Руками из встроенной статистики.
CREATE TABLE IF NOT EXISTS our_metrics (
    post_id            INTEGER PRIMARY KEY REFERENCES our_posts(id),
    measured_at        TEXT,
    reach_followers    INTEGER,
    reach_nonfollowers INTEGER,
    retention          REAL,                   -- доля досмотра, 0..1
    dropoff_sec        REAL,                   -- точка отвала
    saves              INTEGER,
    follows            INTEGER
);

-- Ряд подписчиков по датам: без него «кто растёт» посчитать не из чего.
CREATE TABLE IF NOT EXISTS followers (
    pk             INTEGER NOT NULL REFERENCES accounts(pk),
    at             TEXT NOT NULL,
    follower_count INTEGER,
    PRIMARY KEY (pk, at)
);

-- 11. Карточки под съёмку. Фактуру считает машина, угол и хук предлагает агент,
-- человек правит или берёт как есть.
CREATE TABLE IF NOT EXISTS cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    week        TEXT,                          -- дата сборки
    code        TEXT,                          -- референс
    fmt         TEXT,
    pri         INTEGER,
    lead        TEXT,                          -- кто в кадре
    why         TEXT,                          -- почему сработало у автора
    angle       TEXT,                          -- наш угол
    hook        TEXT,                          -- черновик хука
    shot_frame  TEXT,                          -- что в кадре
    shot_screen TEXT,                          -- что на экране
    shot_banner TEXT,                          -- что в плашке
    caption     TEXT,                          -- каркас описания
    goal        TEXT,                          -- к чему ведём
    status      TEXT DEFAULT 'draft',          -- draft / взята / вычеркнута
    UNIQUE (week, code)
);

-- 12. Журнал по самой туле.
CREATE TABLE IF NOT EXISTS tool_log (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    at     TEXT,
    kind   TEXT,                               -- bug / junk / manual / gap
    what   TEXT,
    detail TEXT,
    fixed  INTEGER NOT NULL DEFAULT 0
);

-- 13. Расход единиц по статьям.
CREATE TABLE IF NOT EXISTS spend (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    at    TEXT,
    item  TEXT,
    units INTEGER,
    price REAL,                                -- цена единицы на момент прогона
    usd   REAL,
    note  TEXT
);

CREATE INDEX IF NOT EXISTS ix_reels_code     ON reels(code);
CREATE INDEX IF NOT EXISTS ix_reels_user     ON reels(pk_user);
CREATE INDEX IF NOT EXISTS ix_reels_ts       ON reels(ts);
CREATE INDEX IF NOT EXISTS ix_scores_z       ON scores(snapshot_id, z DESC);
CREATE INDEX IF NOT EXISTS ix_topics_topic   ON topics(topic);
CREATE INDEX IF NOT EXISTS ix_accounts_stat  ON accounts(status);
"""


ADDED = [('scores', 'baseline_n', 'INTEGER'),
         ('scores', 'baseline_snaps', 'INTEGER'),
         ('accounts', 'checked_snapshot', 'INTEGER'),
         ('scores', 'axes', 'INTEGER'),
         ('snapshots', 'done', 'INTEGER'),
         ('accounts', 'why_out', 'TEXT'),
         ('accounts', 'via', 'TEXT')]


def connect(path=DB_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    for table, col, typ in ADDED:          # догоняем базы, созданные до появления колонки
        have = {r[1] for r in con.execute(f'PRAGMA table_info({table})')}
        if col not in have:
            con.execute(f'ALTER TABLE {table} ADD COLUMN {col} {typ}')
    con.commit()
    return con


if __name__ == '__main__':
    con = connect()
    t = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    print(f'{DB_PATH}\nтаблиц: {len(t)}\n' + '\n'.join('  ' + x for x in t))
