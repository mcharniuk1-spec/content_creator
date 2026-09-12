"""Тесты engine/providers.py и engine/hiker_config.py — только словари окружения
и поддельные транспорты, ни одного сетевого вызова."""
import pathlib, sqlite3, sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import hiker_config, providers


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    """Настоящий .env рядом с проектом содержит боевые секреты (NOTION_TOKEN и т.д.).
    Без этой изоляции check()/notion_check() тихо проваливались бы во внешний .env
    при неполном env-словаре в тесте — что и произошло один раз при отладке этого
    файла (реальный токен утёк в вывод упавшего теста). Каждый тест получает пустой
    каталог как ROOT, так что .env-фоллбек либо не находит файла, либо находит только
    то, что тест сам туда положил."""
    monkeypatch.setattr(hiker_config, 'ROOT', tmp_path)
    monkeypatch.setattr(providers, 'ROOT', tmp_path)
    yield


# ---------------------------------------------------------------- hiker_config ----
def test_hiker_config_not_configured_when_env_empty():
    r = hiker_config.check(env={})
    assert r['state'] == 'NOT_CONFIGURED'
    assert r['env_var'] == 'HIKER_KEY'


def test_hiker_config_configured_from_env_never_prints_value():
    r = hiker_config.check(env={'HIKER_KEY': 'xyzsekrit'})
    assert r['state'] == 'CONFIGURED'
    assert 'xyzsekrit' not in r['detail']
    assert '9' in r['detail'] or 'chars' in r['detail']


def test_hiker_config_falls_back_to_dotenv(tmp_path):
    (tmp_path / '.env').write_text('HIKER_KEY=fromdotenv123\n')
    r = hiker_config.check(env={})
    assert r['state'] == 'CONFIGURED'
    assert 'fromdotenv123' not in r['detail']


def test_notion_check_missing_token_is_not_configured_without_network_call():
    def boom(url, token):
        raise AssertionError('must not call transport without a token')
    out = hiker_config.notion_check(
        env={'NOTION_CARDS_DB': 'abc123'}, transport=boom)
    row = [r for r in out if r['env_var'] == 'NOTION_CARDS_DB'][0]
    assert row['state'] == 'NOT_CONFIGURED'


def test_notion_check_missing_db_id_is_not_configured():
    out = hiker_config.notion_check(env={'NOTION_TOKEN': 't'})
    for r in out:
        assert r['state'] == 'NOT_CONFIGURED'


def test_notion_check_ok_and_failed_states_from_fake_transport():
    calls = []

    def fake(url, token):
        calls.append((url, token))
        if 'gooddb' in url:
            return 200
        return 404

    env = {'NOTION_TOKEN': 'tok', 'NOTION_CARDS_DB': 'gooddb12345',
           'NOTION_REELS_DB': 'baddb999999', 'NOTION_ACCOUNTS_DB': ''}
    out = hiker_config.notion_check(env=env, transport=fake)
    by_var = {r['env_var']: r for r in out}
    assert by_var['NOTION_CARDS_DB']['state'] == 'CONFIGURED'
    assert by_var['NOTION_CARDS_DB']['id_prefix'] == 'gooddb12'
    assert by_var['NOTION_REELS_DB']['state'] == 'FAILED'
    assert by_var['NOTION_REELS_DB']['detail'] == '404'
    assert by_var['NOTION_ACCOUNTS_DB']['state'] == 'NOT_CONFIGURED'
    assert all(token == 'tok' for _, token in calls)
    assert len(calls) == 2   # ACCOUNTS_DB skipped: no id, no network call


def test_probe_skips_network_when_not_configured():
    r = hiker_config.probe({'state': 'NOT_CONFIGURED', 'env_var': 'HIKER_KEY', 'detail': 'x'})
    assert r['state'] == 'NOT_CONFIGURED'


# -------------------------------------------------------------------- providers ----
@pytest.mark.parametrize('name', ['local-faster-whisper', 'local-ffmpeg-scenes'])
def test_local_providers_always_configured(name):
    p = [p for p in providers.PROVIDERS if p.name == name][0]
    state, detail = p.resolve_state(env={})
    assert state == 'CONFIGURED'


def test_remotion_checked_against_real_node_presence_not_assumed():
    """Аудит нашёл, что remotion нуждается в Node+Chrome и это не проверено — резолвер
    честно смотрит на PATH вместо того, чтобы всегда отвечать CONFIGURED."""
    p = [p for p in providers.PROVIDERS if p.name == 'remotion'][0]
    state, detail = p.resolve_state(env={})
    assert state in ('CONFIGURED', 'NOT_CONFIGURED')
    if state == 'NOT_CONFIGURED':
        assert 'PATH' in detail


def test_hiker_provider_reflects_hiker_config():
    p = [p for p in providers.PROVIDERS if p.name == 'hiker'][0]
    assert p.resolve_state(env={})[0] == 'NOT_CONFIGURED'
    assert p.resolve_state(env={'HIKER_KEY': 'abc'})[0] == 'CONFIGURED'


def test_loore_disabled_by_default_even_with_key_present():
    p = [p for p in providers.PROVIDERS if p.name == 'loore'][0]
    state, detail = p.resolve_state(env={'LOORE_KEY': 'somekey'})
    assert state == 'DISABLED'
    assert 'somekey' not in detail


def test_loore_not_configured_when_enabled_without_key():
    p = [p for p in providers.PROVIDERS if p.name == 'loore'][0]
    state, _ = p.resolve_state(env={'LOORE_ENABLED': '1'})
    assert state == 'NOT_CONFIGURED'


def test_loore_configured_when_enabled_with_key():
    p = [p for p in providers.PROVIDERS if p.name == 'loore'][0]
    state, _ = p.resolve_state(env={'LOORE_ENABLED': '1', 'LOORE_KEY': 'k'})
    assert state == 'CONFIGURED'


@pytest.mark.parametrize('name,env_vars', [
    ('supabase', ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']),
    ('cloudflare', ['CLOUDFLARE_API_TOKEN', 'CF_R2_BUCKET']),
    ('openai', ['OPENAI_API_KEY']),
    ('higgsfield', ['HIGGSFIELD_API_KEY']),
])
def test_optional_providers_not_configured_without_env(name, env_vars):
    p = [p for p in providers.PROVIDERS if p.name == name][0]
    assert p.role == 'OPTIONAL_PROVIDER'
    state, detail = p.resolve_state(env={})
    assert state == 'NOT_CONFIGURED'
    for v in env_vars:
        assert v in detail


@pytest.mark.parametrize('name,env_vars', [
    ('supabase', ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']),
    ('cloudflare', ['CLOUDFLARE_API_TOKEN', 'CF_R2_BUCKET']),
    ('openai', ['OPENAI_API_KEY']),
    ('higgsfield', ['HIGGSFIELD_API_KEY']),
])
def test_optional_providers_configured_with_env(name, env_vars):
    p = [p for p in providers.PROVIDERS if p.name == name][0]
    env = {v: 'x' * 10 for v in env_vars}
    state, detail = p.resolve_state(env=env)
    assert state == 'CONFIGURED'
    for v in env_vars:
        assert 'x' * 10 not in detail  # значение не печатается, только длина/наличие


def test_refresh_no_op_when_providers_table_missing():
    con = sqlite3.connect(':memory:')
    assert providers.refresh(con, env={}) is False


def test_refresh_writes_rows_when_table_exists():
    con = sqlite3.connect(':memory:')
    con.execute("""CREATE TABLE providers (
        name TEXT PRIMARY KEY, kind TEXT NOT NULL, role TEXT NOT NULL, state TEXT NOT NULL,
        env_var TEXT, checked_at TEXT, detail TEXT)""")
    ok = providers.refresh(con, env={'HIKER_KEY': 'abc'})
    assert ok is True
    rows = con.execute('SELECT name, state FROM providers').fetchall()
    by_name = dict(rows)
    assert by_name['hiker'] == 'CONFIGURED'
    assert by_name['loore'] == 'DISABLED'
    assert len(rows) == len(providers.PROVIDERS)


def test_status_returns_one_line_per_provider():
    out = providers.status(env={})
    lines = out.splitlines()
    assert len(lines) == len(providers.PROVIDERS)
    for p in providers.PROVIDERS:
        assert any(p.name in line for line in lines)
