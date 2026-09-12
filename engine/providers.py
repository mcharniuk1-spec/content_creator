#!/usr/bin/env python3
"""Реестр провайдеров, SPEC §2.10 и §9 (owner: hiker).

    python3 -m engine.providers status     таблица по всем провайдерам, без записи в БД
    python3 -m engine.providers refresh    то же плюс запись в таблицу providers

Default production path (SPEC §0.3): Hiker → local faster-whisper → local ffmpeg scenes →
Remotion render. Всё остальное — OPTIONAL_PROVIDER, без учётных данных не активируется
и никогда не требуется для дефолтного пути.

`providers` — таблица другого владельца (engine/schema.py); пока её нет, refresh() и
CLI просто печатают/возвращают состояние без записи, старый пайплайн не ломается.
"""
import argparse, datetime, os, pathlib, sqlite3, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _read_dotenv(name, root=None):
    f = pathlib.Path(root if root is not None else ROOT) / '.env'
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    return None


def _resolve(env, name):
    return env.get(name) or _read_dotenv(name)


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


class Provider:
    """Одна строка реестра. `resolve` получает env-словарь и возвращает (state, detail);
    detail никогда не содержит значение переменной — только присутствие/длину."""

    def __init__(self, name, kind, role, env_vars=(), resolve=None, note=None):
        self.name = name
        self.kind = kind
        self.role = role                 # DEFAULT | OPTIONAL_PROVIDER | FALLBACK
        self.env_vars = tuple(env_vars)  # может быть больше одной переменной; в БД пишем первую
        self._resolve = resolve or self._default_resolve
        self.note = note

    @property
    def env_var(self):
        return self.env_vars[0] if self.env_vars else None

    def _default_resolve(self, env):
        """CONFIGURED, если все объявленные переменные присутствуют и непустые."""
        if not self.env_vars:
            return 'CONFIGURED', 'local, no credentials required'
        missing = [v for v in self.env_vars if not _resolve(env, v)]
        if missing:
            present = [v for v in self.env_vars if v not in missing]
            detail = f"missing {', '.join(missing)}"
            if present:
                detail += f" (has {', '.join(present)})"
            return 'NOT_CONFIGURED', detail
        lens = ', '.join(f'{v}={len(_resolve(env, v))} chars' for v in self.env_vars)
        return 'CONFIGURED', lens

    def resolve_state(self, env=None):
        env = os.environ if env is None else env
        try:
            state, detail = self._resolve(env)
        except Exception as e:
            state, detail = 'FAILED', f'{type(e).__name__}: {e}'
        if self.note:
            detail = f'{detail} — {self.note}'
        return state, detail


def _resolve_hiker(env):
    from engine.hiker_config import check
    r = check(env)
    return r['state'], r['detail']


def _resolve_loore(env):
    """OPTIONAL_PROVIDER, never required (SPEC §0.3): даже с LOORE_KEY в окружении
    провайдер по умолчанию DISABLED — включить его явно можно через LOORE_ENABLED=1,
    чтобы наличие ключа в .env само по себе не активировало платный путь."""
    enabled = str(_resolve(env, 'LOORE_ENABLED') or '').strip().lower() in ('1', 'true', 'yes')
    key = _resolve(env, 'LOORE_KEY')
    if not enabled:
        return 'DISABLED', 'never required for the default path; set LOORE_ENABLED=1 to opt in'
    if not key:
        return 'NOT_CONFIGURED', 'LOORE_ENABLED=1 but LOORE_KEY missing'
    return 'CONFIGURED', f'LOORE_ENABLED=1, LOORE_KEY={len(key)} chars'


def _resolve_local(env):
    return 'CONFIGURED', 'local tool, no credentials required'


def _resolve_remotion(env):
    """Аудит (reports/audit/01-branch-comparison.md §6.5) отдельно отмечает, что Remotion
    нуждается в Node и в уже установленном Chrome-бинарнике, и ни то ни другое не
    проверено на сервере. В отличие от faster-whisper/ffmpeg (bundled/venv-пакеты),
    здесь дешёвая и честная проверка есть — наличие node/npx на PATH — поэтому делаем
    её, а не молчим CONFIGURED вслепую."""
    import shutil
    found = shutil.which('npx') or shutil.which('node')
    if not found:
        return 'NOT_CONFIGURED', 'node/npx not found on PATH (needed by studio/remotion render)'
    return 'CONFIGURED', f'{found} on PATH; Chrome binary presence not separately verified'


PROVIDERS = [
    Provider('hiker', 'social_data', 'DEFAULT', ['HIKER_KEY'], resolve=_resolve_hiker),
    Provider('local-faster-whisper', 'transcription', 'DEFAULT', [], resolve=_resolve_local),
    Provider('local-ffmpeg-scenes', 'frames', 'DEFAULT', [], resolve=_resolve_local),
    Provider('remotion', 'render', 'DEFAULT', [], resolve=_resolve_remotion,
             note='studio/remotion, PREVIS mode'),
    Provider('loore', 'media', 'OPTIONAL_PROVIDER', ['LOORE_KEY'], resolve=_resolve_loore,
             note='transcription/media fallback, never required'),
    Provider('supabase', 'storage', 'OPTIONAL_PROVIDER',
             ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']),
    Provider('cloudflare', 'storage', 'OPTIONAL_PROVIDER',
             ['CLOUDFLARE_API_TOKEN', 'CF_R2_BUCKET']),
    Provider('openai', 'image_gen', 'OPTIONAL_PROVIDER', ['OPENAI_API_KEY']),
    Provider('higgsfield', 'video_gen', 'OPTIONAL_PROVIDER', ['HIGGSFIELD_API_KEY']),
]


def _table_exists(con, name):
    try:
        return con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None
    except sqlite3.OperationalError:
        return False


def snapshot(env=None):
    """Список (provider, state, detail) без касания БД — то, что печатает status()."""
    return [(p, *p.resolve_state(env)) for p in PROVIDERS]


def refresh(con, env=None):
    """Пишет текущее состояние всех провайдеров в таблицу providers (engine/schema.py,
    другой владелец). Если таблицы ещё нет — ничего не делает и возвращает False; старый
    пайплайн не должен падать из-за того, что схема ещё не докатилась."""
    if not _table_exists(con, 'providers'):
        return False
    now = _now_iso()
    for p, state, detail in snapshot(env):
        try:
            con.execute("""INSERT INTO providers (name,kind,role,state,env_var,checked_at,detail)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(name) DO UPDATE SET
                    kind=excluded.kind, role=excluded.role, state=excluded.state,
                    env_var=excluded.env_var, checked_at=excluded.checked_at, detail=excluded.detail""",
                (p.name, p.kind, p.role, state, p.env_var, now, detail))
        except sqlite3.OperationalError:
            return False
    con.commit()
    return True


def status(env=None):
    rows = snapshot(env)
    name_w = max(len(p.name) for p, _, _ in rows)
    kind_w = max(len(p.kind) for p, _, _ in rows)
    role_w = max(len(p.role) for p, _, _ in rows)
    state_w = max(len(s) for _, s, _ in rows)
    lines = []
    for p, state, detail in rows:
        lines.append(f'{p.name:<{name_w}}  {p.kind:<{kind_w}}  {p.role:<{role_w}}  '
                     f'{state:<{state_w}}  {detail}')
    return '\n'.join(lines)


def _main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', nargs='?', default='status', choices=['status', 'refresh'])
    args = ap.parse_args()
    print(status())
    if args.cmd == 'refresh':
        from db import connect
        con = connect()
        ok = refresh(con)
        print('\nwritten to providers table' if ok else '\nproviders table not found yet — not written')


if __name__ == '__main__':
    _main()
