#!/usr/bin/env python3
"""Проверка конфигурации Hiker и Notion, SPEC §9 (owner: hiker).

    python3 -m engine.hiker_config            HIKER_KEY есть/нет + доступность баз Notion
    python3 -m engine.hiker_config --probe    плюс платный(?) звонок /sys/balance —
                                               смотри стоимость в lib.hiker.PRICE_RECEIPT

Никогда не печатает сам ключ/токен — только длину/наличие. Notion DB id не секрет,
но в логах усечён до 8 символов на всякий случай.

Exit code: 0 — HIKER_KEY сконфигурирован, 2 — нет (NOT_CONFIGURED или FAILED).
Notion никогда не влияет на exit code — cron.sh должен продолжать прогон, даже если
Notion недоступен (SPEC/аудит §3: это уже и так поведение run.py).
"""
import argparse, json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_VAR = 'HIKER_KEY'
NOTION_TOKEN_VAR = 'NOTION_TOKEN'
NOTION_DB_VARS = ['NOTION_CARDS_DB', 'NOTION_REELS_DB', 'NOTION_ACCOUNTS_DB']
NOTION_LABELS = {
    'NOTION_CARDS_DB': 'Notion Cards DB',
    'NOTION_REELS_DB': 'Notion Reels DB',
    'NOTION_ACCOUNTS_DB': 'Notion Accounts DB',
}


def _read_dotenv(name, root=None):
    """Тот же .env-фоллбек, что и в lib/hiker.py и notion.py — ключи читаются из
    окружения или из .env рядом с проектом, во всех модулях одинаково."""
    f = pathlib.Path(root if root is not None else ROOT) / '.env'
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    return None


def _resolve(env, name):
    return env.get(name) or _read_dotenv(name)


def check(env=None):
    """CONFIGURED | NOT_CONFIGURED | FAILED для HIKER_KEY. Никогда не возвращает
    значение ключа — только длину и откуда оно взялось (env vs .env)."""
    env = os.environ if env is None else env
    val = env.get(ENV_VAR)
    source = 'env' if val else None
    if not val:
        val = _read_dotenv(ENV_VAR)
        source = '.env' if val else None
    if not val:
        return {'state': 'NOT_CONFIGURED', 'env_var': ENV_VAR,
                'detail': 'not set (checked process env and .env)'}
    return {'state': 'CONFIGURED', 'env_var': ENV_VAR,
            'detail': f'present via {source}, {len(val)} chars'}


def probe(result):
    """Только если явно попросили --probe: реальный вызов lib.hiker.balance().
    Это тот же /sys/balance, который и так дергается перед каждым платным сбором —
    информационный, но не бесплатный по счётчику запросов провайдера (см. документацию
    HikerAPI; сама проверка баланса деньги не тратит, но считается обращением к API)."""
    if result['state'] != 'CONFIGURED':
        return result
    sys.path.insert(0, str(ROOT / 'lib'))
    try:
        import hiker
        b = hiker.balance()
    except SystemExit as e:
        return {**result, 'state': 'FAILED', 'detail': result['detail'] + f'; probe failed: {e}'}
    except Exception as e:
        return {**result, 'state': 'FAILED',
                'detail': result['detail'] + f'; probe failed: {type(e).__name__}: {e}'}
    if b is None:
        return {**result, 'state': 'FAILED',
                'detail': result['detail'] + '; probe: /sys/balance returned no data'}
    return {**result, 'detail': result['detail']
            + f"; probe OK: {b.get('requests')} units left (informational call, see PRICE_RECEIPT)"}


def _curl_get(url, token, timeout=15):
    """Тот же стиль транспорта, что и notion.py: curl, а не urllib (SSL на этой машине)."""
    cmd = ['curl', '-s', '--proto', '=https', '--max-time', str(timeout), '-X', 'GET',
           '-H', f'Authorization: Bearer {token}',
           '-H', 'Notion-Version: 2022-06-28',
           '-w', '\n%{http_code}', '--', url]
    p = subprocess.run(cmd, capture_output=True, text=True)
    text, _, code = p.stdout.rpartition('\n')
    try:
        return int(code.strip())
    except ValueError:
        return 0


def notion_check(env=None, transport=None):
    """Дешёвая проверка живости каждой настроенной базы Notion — GET /v1/databases/<id>.
    Один HTTP-запрос на базу, ничего не пишет и не читает содержимое. Возвращает список
    результатов по каждой переменной *_DB, включая id усечённым до 8 символов (id — не
    секрет, но чтобы не плодить привычку печатать значения переменных в логах)."""
    env = os.environ if env is None else env
    transport = transport or _curl_get
    token = _resolve(env, NOTION_TOKEN_VAR)
    out = []
    for var in NOTION_DB_VARS:
        db_id = _resolve(env, var)
        if not db_id:
            out.append({'env_var': var, 'state': 'NOT_CONFIGURED', 'detail': 'not set'})
            continue
        if not token:
            out.append({'env_var': var, 'state': 'NOT_CONFIGURED',
                        'detail': 'NOTION_TOKEN not set', 'id_prefix': db_id[:8]})
            continue
        code = transport(f'https://api.notion.com/v1/databases/{db_id}', token)
        state = 'CONFIGURED' if code == 200 else 'FAILED'
        out.append({'env_var': var, 'state': state, 'detail': str(code),
                    'id_prefix': db_id[:8]})
    return out


def _main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--probe', action='store_true',
                    help='реальный вызов /sys/balance (см. документацию по стоимости)')
    args = ap.parse_args()

    result = check()
    if args.probe:
        result = probe(result)
    print(f"{result['env_var']}: {result['state']} — {result['detail']}")

    for r in notion_check():
        label = NOTION_LABELS.get(r['env_var'], r['env_var'])
        if r['state'] == 'CONFIGURED':
            print(f'{label}: OK')
        elif r['state'] == 'FAILED':
            print(f"{label}: FAILED({r['detail']})")
        else:
            print(f"{label}: NOT_CONFIGURED ({r['detail']})")

    sys.exit(0 if result['state'] == 'CONFIGURED' else 2)


if __name__ == '__main__':
    _main()
