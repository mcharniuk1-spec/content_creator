"""Тесты lib/hiker.py на поддельном транспорте — ни одного сетевого вызова.

Раньше test_collect.py мокал весь модуль hiker целиком и ни разу не выполнял код
lib/hiker.py:call() (сборка URL, разбор заголовков, ретраи, кэш). Здесь наоборот —
transport инжектируется в call(), а вся остальная логика реальная.
"""
import hashlib, json, pathlib, sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.hiker as hiker


SECRET_KEY = 'sekrit-key-should-never-leak-anywhere'


def _raw(status, body, units=None, extra_headers=''):
    """Собирает сырой ответ в формате `curl -D -`: заголовки, пустая строка, тело."""
    head = f'HTTP/1.1 {status} X\r\n'
    if units is not None:
        head += f'x-hiker-info: {json.dumps({"reqs": units})}\r\n'
    head += extra_headers
    return head + '\r\n' + body


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    """Каждый тест получает свой каталог кэша и обнулённые счётчики, чтобы тесты
    не видели друг друга и не трогали настоящий hiker-cache/ в репозитории."""
    hiker._cache_dir = tmp_path / 'cache'
    hiker._units = 0
    hiker._last = 0.0
    hiker._last_meta = None
    monkeypatch.setattr(hiker.time, 'sleep', lambda s: None)  # тесты не должны реально ждать
    monkeypatch.setattr(hiker, '_key', lambda: SECRET_KEY)
    yield


def _fake(*, calls):
    """calls — список сырых ответов (или исключений) по одному на попытку транспорта."""
    state = {'i': 0}

    def transport(url, key):
        assert key == SECRET_KEY
        i = state['i']
        state['i'] += 1
        item = calls[min(i, len(calls) - 1)]
        if isinstance(item, Exception):
            raise item
        return item
    transport.call_count = lambda: state['i']
    return transport


# ---------------------------------------------------------------- 200 + учёт единиц ----
def test_200_parses_body_and_accounts_units_from_header():
    t = _fake(calls=[_raw(200, json.dumps({'ok': 1}), units=3)])
    d = hiker.call('/v1/x', use_cache=False, transport=t)
    assert d == {'ok': 1}
    assert hiker._units == 3


# --------------------------------------------------------------------------- 429 ----
def test_429_retries_without_billing():
    t = _fake(calls=[_raw(429, ''), _raw(200, json.dumps({'ok': 1}), units=1)])
    d = hiker.call('/v1/x', use_cache=False, transport=t)
    assert d == {'ok': 1}
    assert t.call_count() == 2
    assert hiker._units == 1          # только оплаченная вторая попытка


# --------------------------------------------------------------------------- 402 ----
def test_402_hard_stop():
    t = _fake(calls=[_raw(402, json.dumps({'exc_type': 'OutOfMoney'}))])
    with pytest.raises(SystemExit):
        hiker.call('/v1/x', use_cache=False, transport=t)


# ------------------------------------------------------------------------- 5xx ----
def test_5xx_not_billed_gives_up_after_two_tries():
    body = json.dumps({'exc_type': 'InstagramServerError'})
    t = _fake(calls=[_raw(500, body, units=5), _raw(500, body, units=5), _raw(500, body, units=5)])
    d = hiker.call('/v1/x', use_cache=False, tries=3, transport=t)
    assert d is None
    assert hiker._units == 0          # 50x никогда не билятся
    assert t.call_count() == 2        # обрыв после второй попытки (attempt>=1)


# --------------------------------------------------------- 400/404 billed, no retry ----
def test_400_validation_error_is_billed_and_not_retried():
    t = _fake(calls=[_raw(400, json.dumps({'exc_type': 'ValidationError'}), units=1)])
    d = hiker.call('/v1/x', use_cache=False, tries=3, transport=t)
    assert d is None
    assert hiker._units == 1
    assert t.call_count() == 1


def test_404_user_not_found_is_billed_and_not_retried():
    t = _fake(calls=[_raw(404, json.dumps({'exc_type': 'UserNotFound'}), units=1)])
    d = hiker.call('/v1/x', use_cache=False, tries=3, transport=t)
    assert d is None
    assert hiker._units == 1
    assert t.call_count() == 1


# ------------------------------------------------------------------ malformed JSON ----
def test_malformed_json_retries_then_succeeds():
    t = _fake(calls=['not json at all\r\n\r\nnope', _raw(200, json.dumps({'ok': 1}), units=1)])
    d = hiker.call('/v1/x', use_cache=False, tries=3, transport=t)
    assert d == {'ok': 1}
    assert t.call_count() == 2


def test_malformed_json_exhausts_retries():
    t = _fake(calls=['garbage'])
    d = hiker.call('/v1/x', use_cache=False, tries=2, transport=t)
    assert d is None
    assert t.call_count() == 2


# -------------------------------------------------------------------- cache hit ----
def test_cache_hit_never_calls_transport():
    t1 = _fake(calls=[_raw(200, json.dumps({'ok': 1}), units=2)])
    d1 = hiker.call('/v1/x', use_cache=True, transport=t1, foo='bar')
    assert d1 == {'ok': 1}
    assert hiker._units == 2

    def boom(url, key):
        raise AssertionError('transport must not be called on a cache hit')
    d2 = hiker.call('/v1/x', use_cache=True, transport=boom, foo='bar')
    assert d2 == {'ok': 1}
    assert hiker._units == 2          # повторный вызов не добавил единиц


def test_cache_hit_restores_last_fetch_meta_from_sidecar():
    t = _fake(calls=[_raw(200, json.dumps({'ok': 1}), units=2)])
    hiker.call('/v1/x', use_cache=True, transport=t, foo='bar')
    fresh_meta = hiker.last_fetch_meta()
    hiker._last_meta = None
    d2 = hiker.call('/v1/x', use_cache=True, transport=lambda *a: (_ for _ in ()).throw(
        AssertionError('no network on cache hit')), foo='bar')
    assert d2 == {'ok': 1}
    assert hiker.last_fetch_meta() == fresh_meta


# -------------------------------------------------------------- sidecar metadata ----
def test_sidecar_metadata_written_next_to_cache_file():
    body = json.dumps({'ok': 1})
    t = _fake(calls=[_raw(200, body, units=4)])
    hiker.call('/v1/user/by/username', use_cache=True, transport=t, username='bob')

    files = list(hiker._cache_dir.glob('*.json'))
    data_files = [f for f in files if not f.name.endswith('.meta.json')]
    meta_files = [f for f in files if f.name.endswith('.meta.json')]
    assert len(data_files) == 1
    assert len(meta_files) == 1

    meta = json.loads(meta_files[0].read_text())
    assert meta['endpoint'] == '/v1/user/by/username'
    assert meta['params'] == {'username': 'bob'}
    assert meta['http_status'] == 200
    assert meta['units'] == 4
    assert meta['sha256'] == hashlib.sha256(body.encode('utf-8')).hexdigest()
    assert meta['cache_path'] == str(data_files[0])
    assert 'fetched_at' in meta and meta['fetched_at']

    assert hiker.last_fetch_meta() == meta


def test_sidecar_params_never_include_key_like_fields():
    t = _fake(calls=[_raw(200, json.dumps({'ok': 1}), units=1)])
    hiker.call('/v1/x', use_cache=True, transport=t, username='bob',
              access_key=SECRET_KEY, api_token='also-secret')
    meta = hiker.last_fetch_meta()
    assert 'access_key' not in meta['params']
    assert 'api_token' not in meta['params']
    assert meta['params'] == {'username': 'bob'}


# ------------------------------------------------------------ key never leaks ----
def test_key_never_appears_in_any_written_file_or_log(capsys):
    body = json.dumps({'ok': 1, 'note': 'nothing secret here'})
    t = _fake(calls=[_raw(200, body, units=1)])
    d = hiker.call('/v1/x', use_cache=True, transport=t, username='bob')
    assert d == {'ok': 1, 'note': 'nothing secret here'}

    for f in hiker._cache_dir.glob('*'):
        assert SECRET_KEY not in f.read_text()

    out, err = capsys.readouterr()
    assert SECRET_KEY not in out
    assert SECRET_KEY not in err

    # и на пути ошибки (транспорт бросает несостоявшийся запрос) ключ тоже не должен
    # попасть ни в исключение, ни в stderr-принты модуля
    hiker._cache_dir = hiker._cache_dir.parent / 'cache2'
    t2 = _fake(calls=[_raw(500, json.dumps({'exc_type': 'InstagramServerError'}))])
    hiker.call('/v2/y', use_cache=False, tries=2, transport=t2)
    out, err = capsys.readouterr()
    assert SECRET_KEY not in out
    assert SECRET_KEY not in err
