import io
import json
import fcntl
import multiprocessing
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError

import pytest

import m2_engine.youtube_api as youtube_api
from m2_engine.youtube_api import PersistentStrikeLedger, QuotaLedger, YouTubeAPIError, YouTubeDataAPIClient, classify_http_error, request_fingerprint
from scripts.youtube_census import aggregate_discovery, build_analyzed_content_cohort, build_cells, checkpoint_index, construct_content_cohort, construct_top_references, discover, select_with_creator_cap, validate_config, validate_creator_contribution


def _multiprocess_failure_worker(run_dir: str, queue) -> None:
    from pathlib import Path
    import m2_engine.youtube_api as module
    from m2_engine.youtube_api import QuotaLedger, YouTubeAPIError, YouTubeDataAPIClient

    root = Path(run_dir)
    attempts = root / "external-attempts.jsonl"

    def fail(*_args, **_kwargs):
        with attempts.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.write("{}\n")
            stream.flush()
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        raise TimeoutError("fixture timeout")

    module.urlopen = fail
    client = YouTubeDataAPIClient(
        api_key="AIza" + "m" * 35,
        run_dir=root,
        quota=QuotaLedger(root / "quota.jsonl", daily_unit_budget=100, daily_search_call_budget=100),
        min_interval_seconds=0,
        sleeper=lambda _seconds: None,
    )
    try:
        client.get("channels", "channels.list", {"part": "snippet", "id": "same-process-target"})
    except YouTubeAPIError as exc:
        queue.put(exc.code)


def test_request_fingerprint_never_depends_on_key() -> None:
    first = request_fingerprint("search.list", {"q": "agents", "key": "secret-one"})
    second = request_fingerprint("search.list", {"q": "agents", "key": "secret-two"})
    assert first == second
    assert "secret" not in first


def test_quota_ledger_enforces_search_budget(tmp_path: Path) -> None:
    ledger = QuotaLedger(tmp_path / "quota.jsonl", daily_unit_budget=10, daily_search_call_budget=1)
    ledger.reserve(operation="search.list", fingerprint="sha256:a", estimated_units=1)
    with pytest.raises(YouTubeAPIError, match="search-call budget") as caught:
        ledger.reserve(operation="search.list", fingerprint="sha256:b", estimated_units=1)
    assert caught.value.global_stop


def test_http_error_classification() -> None:
    assert classify_http_error(403, {"quotaExceeded"}) == ("QUOTA_EXHAUSTED", False, True)
    assert classify_http_error(429, set()) == ("RATE_LIMITED", True, False)
    assert classify_http_error(500, set()) == ("UPSTREAM_SERVER_ERROR", True, False)
    assert classify_http_error(404, set()) == ("NOT_FOUND", False, False)
    assert classify_http_error(403, {"rateLimitExceeded"}) == ("RATE_LIMITED", True, False)


def test_build_cells_is_deterministic_and_complete() -> None:
    config = {
        "markets": ["US", "BG"],
        "orders": ["relevance", "date"],
        "query_groups": [{"track": "a", "intent": "b", "queries": ["q1", "q2"]}],
    }
    assert build_cells(config) == build_cells(config)
    assert len(build_cells(config)) == 8


def test_aggregate_discovery_deduplicates_channels(tmp_path: Path) -> None:
    page_dir = tmp_path / "normalized" / "search-pages"
    page_dir.mkdir(parents=True)
    rows = [
        {"native_channel_id": "UC1", "canonical_url": "https://www.youtube.com/channel/UC1", "title": "One", "description": "", "track": "a", "intent": "i", "discovery_market": "US", "order": "relevance", "source_request_fingerprint": "sha256:1", "refresh_or_delete_by": "2026-09-24T00:00:00+00:00"},
        {"native_channel_id": "UC1", "canonical_url": "https://www.youtube.com/channel/UC1", "title": "One", "description": "", "track": "b", "intent": "j", "discovery_market": "BG", "order": "date", "source_request_fingerprint": "sha256:2", "refresh_or_delete_by": "2026-09-24T00:00:00+00:00"},
    ]
    (page_dir / "x.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    result = aggregate_discovery(tmp_path)
    assert len(result) == 1
    assert result[0]["discovery_observation_count"] == 2
    assert result[0]["tracks"] == ["a", "b"]


def test_validate_config_requires_owner_target_and_cap() -> None:
    config = {
        "schema": "north-hux.youtube-census-config.v1",
        "target_accounts": {"minimum": 10000, "maximum": 12000},
        "maximum_creator_contribution_fraction": 0.01,
        "calibration_content": {"qualified_accounts": 300, "videos_per_account": 3, "minimum_videos_per_account": 3, "maximum_videos_per_account": 10, "target_rows": 900},
        "top_references": {"target_rows": 100, "videos_per_creator": 1},
        "daily_limits": {"local_search_call_budget": 99, "search_calls": 100},
        "discovery": {"pages_per_cell": 1, "max_results_per_page": 50},
        "request": {"max_attempts": 5},
        "markets": ["US"],
        "orders": ["relevance"],
    }
    config["discovery"].update({"resource_type": "video", "video_duration": "short"})
    validate_config(config)
    config["maximum_creator_contribution_fraction"] = 0.05
    with pytest.raises(ValueError, match="0.01"):
        validate_config(config)


def test_creator_cap_is_one_item_per_creator_for_top_100() -> None:
    rows = [{"creator": f"C{index}", "rank": index} for index in range(100)]
    selected = select_with_creator_cap(rows, creator_field="creator", fraction=0.01, target_size=100)
    assert len(selected) == 100
    assert len({row["creator"] for row in selected}) == 100


def test_creator_cap_applies_to_content_rows_using_target_denominator() -> None:
    rows = [
        {"creator": creator, "video": f"{creator}-{index}"}
        for creator in ("A", "B", "C", "D")
        for index in range(10)
    ]
    selected = select_with_creator_cap(rows, creator_field="creator", fraction=0.25, target_size=12)
    counts = {creator: sum(row["creator"] == creator for row in selected) for creator in ("A", "B", "C", "D")}
    assert len(selected) == 12
    assert counts == {"A": 3, "B": 3, "C": 3, "D": 3}


def test_creator_cap_rejects_underfilled_selection() -> None:
    with pytest.raises(ValueError, match="underfilled"):
        select_with_creator_cap([{"creator": "A"}], creator_field="creator", fraction=0.01, target_size=100)


def test_creator_contribution_rejects_actual_cohort_overflow() -> None:
    rows = [{"creator": "A"}] * 2 + [{"creator": f"C{index}"} for index in range(98)]
    with pytest.raises(ValueError, match="exceeds"):
        validate_creator_contribution(rows, creator_field="creator", fraction=0.01)


def test_build_analyzed_content_cohort_is_300_by_3_and_config_driven() -> None:
    config = {
        "maximum_creator_contribution_fraction": 0.01,
        "calibration_content": {"qualified_accounts": 300, "videos_per_account": 3, "target_rows": 900},
    }
    accounts = [{"native_channel_id": f"UC{index:03d}", "qualification_state": "qualified"} for index in range(300)]
    videos = [
        {"native_channel_id": f"UC{creator:03d}", "native_video_id": f"V{creator:03d}-{video}", "analysis_eligible": True, "format_state": "NATIVE_SHORT", "view_count": video}
        for creator in range(300)
        for video in range(3)
    ]
    selected = build_analyzed_content_cohort(accounts, videos, config)
    assert len(selected) == 900
    assert len({row["native_channel_id"] for row in selected}) == 300
    assert max(Counter(row["native_channel_id"] for row in selected).values()) == 3


def test_build_analyzed_content_cohort_rejects_account_underfill() -> None:
    config = {
        "maximum_creator_contribution_fraction": 0.01,
        "calibration_content": {"qualified_accounts": 300, "videos_per_account": 3, "target_rows": 900},
    }
    accounts = [{"native_channel_id": f"UC{index:03d}", "qualification_state": "qualified"} for index in range(299)]
    videos = [
        {"native_channel_id": f"UC{creator:03d}", "native_video_id": f"V{creator:03d}-{video}", "analysis_eligible": True}
        for creator in range(299)
        for video in range(3)
    ]
    with pytest.raises(ValueError, match="need 300 creators"):
        build_analyzed_content_cohort(accounts, videos, config)


def test_duplicate_video_snapshots_do_not_satisfy_three_video_gate() -> None:
    config = {
        "maximum_creator_contribution_fraction": 0.01,
        "calibration_content": {"qualified_accounts": 300, "videos_per_account": 3, "target_rows": 900},
    }
    accounts = [{"native_channel_id": f"UC{index:03d}", "qualification_state": "qualified"} for index in range(300)]
    videos = [
        {"native_channel_id": f"UC{creator:03d}", "native_video_id": f"V{creator:03d}", "analysis_eligible": True, "captured_at": f"2026-08-25T00:00:0{snapshot}Z"}
        for creator in range(300)
        for snapshot in range(3)
    ]
    with pytest.raises(ValueError, match="need 300 creators"):
        build_analyzed_content_cohort(accounts, videos, config)


def test_conflicting_native_video_owners_are_rejected() -> None:
    config = {
        "maximum_creator_contribution_fraction": 0.01,
        "calibration_content": {"qualified_accounts": 300, "videos_per_account": 3, "target_rows": 900},
    }
    accounts = [{"native_channel_id": f"UC{index:03d}", "qualification_state": "qualified"} for index in range(300)]
    videos = [
        {"native_channel_id": "UC000", "native_video_id": "SAME", "analysis_eligible": True},
        {"native_channel_id": "UC001", "native_video_id": "SAME", "analysis_eligible": True},
    ]
    with pytest.raises(ValueError, match="conflicting creators"):
        build_analyzed_content_cohort(accounts, videos, config)


def test_operational_cohort_and_top100_outputs_are_config_driven(tmp_path: Path) -> None:
    config = {
        "maximum_creator_contribution_fraction": 0.01,
        "calibration_content": {"qualified_accounts": 300, "videos_per_account": 3, "target_rows": 900},
        "top_references": {"target_rows": 100, "videos_per_creator": 1},
    }
    derived = tmp_path / "derived"
    derived.mkdir()
    accounts = [{"native_channel_id": f"UC{index:03d}", "qualification_state": "qualified"} for index in range(300)]
    videos = [
        {"native_channel_id": f"UC{creator:03d}", "native_video_id": f"V{creator:03d}-{video}", "analysis_eligible": True, "format_state": "NATIVE_SHORT", "view_count": video}
        for creator in range(300)
        for video in range(3)
    ]
    (derived / "qualified-accounts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in accounts), encoding="utf-8")
    (derived / "video-snapshots.jsonl").write_text("".join(json.dumps(row) + "\n" for row in videos), encoding="utf-8")
    assert construct_content_cohort(tmp_path, config) == {"qualified_accounts": 300, "analyzed_content_rows": 900, "maximum_creator_rows": 3}
    assert construct_top_references(tmp_path, config) == {"top_reference_rows": 100, "distinct_creators": 100, "maximum_creator_rows": 1}
    output = [json.loads(line) for line in (derived / "top-reference-cohort.jsonl").read_text().splitlines()]
    assert len(output) == 100
    assert len({row["native_channel_id"] for row in output}) == 100


def test_persistent_strike_blocks_non_retryable_repeat(tmp_path: Path) -> None:
    ledger = PersistentStrikeLedger(tmp_path / "strikes.jsonl")
    event = ledger.record(failure_key="f", error_code="NOT_FOUND", retryable=False, global_stop=False)
    assert event["action"] == "block"
    assert ledger.terminal_action("f") == "block"


def test_client_success_and_resume_verifies_raw_hash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def read(self): return b'{"items": []}'

    monkeypatch.setattr(youtube_api, "urlopen", lambda *_args, **_kwargs: Response())
    client = YouTubeDataAPIClient(
        api_key="AIza" + "x" * 35,
        run_dir=tmp_path,
        quota=QuotaLedger(tmp_path / "quota.jsonl", daily_unit_budget=10, daily_search_call_budget=10),
        min_interval_seconds=0,
        sleeper=lambda _seconds: None,
    )
    first = client.get("search", "search.list", {"part": "snippet", "q": "agents"})
    second = client.get("search", "search.list", {"part": "snippet", "q": "agents"})
    assert first.resumed is False and second.resumed is True
    (tmp_path / first.raw_uri).write_text("{}", encoding="utf-8")
    with pytest.raises(YouTubeAPIError, match="hash"):
        client.get("search", "search.list", {"part": "snippet", "q": "agents"})


def test_non_retryable_http_error_is_durably_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fail(*_args, **_kwargs):
        raise HTTPError("https://redacted.invalid", 404, "not found", {}, io.BytesIO(b'{"error":{"errors":[{"reason":"notFound"}]}}'))
    monkeypatch.setattr(youtube_api, "urlopen", fail)
    client = YouTubeDataAPIClient(
        api_key="AIza" + "y" * 35,
        run_dir=tmp_path,
        quota=QuotaLedger(tmp_path / "quota.jsonl", daily_unit_budget=10, daily_search_call_budget=10),
        min_interval_seconds=0,
        sleeper=lambda _seconds: None,
    )
    with pytest.raises(YouTubeAPIError) as first:
        client.get("channels", "channels.list", {"part": "snippet", "id": "missing"})
    assert first.value.code == "NOT_FOUND"
    with pytest.raises(YouTubeAPIError) as second:
        client.get("channels", "channels.list", {"part": "snippet", "id": "missing"})
    assert second.value.code == "TARGET_BLOCKED"


def test_discover_follows_next_page_and_commits_valid_checkpoints(tmp_path: Path) -> None:
    class FakeClient:
        def __init__(self): self.calls = 0
        def get(self, _resource, _operation, params, estimated_units=1):
            del estimated_units
            self.calls += 1
            token = params.get("pageToken")
            payload = {"items": [{"id": {"channelId": f"UC{self.calls}"}, "snippet": {"title": "x"}}]}
            if token is None:
                payload["nextPageToken"] = "NEXT"
            raw = tmp_path / "raw" / f"{self.calls}.json"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(json.dumps(payload), encoding="utf-8")
            return type("R", (), {"payload": payload, "resumed": False, "fingerprint": f"sha256:{self.calls}", "raw_sha256": __import__('hashlib').sha256(raw.read_bytes()).hexdigest(), "raw_uri": raw.relative_to(tmp_path).as_posix(), "captured_at": "2026-08-25T00:00:00+00:00", "refresh_or_delete_by": "2026-09-24T00:00:00+00:00"})()
    config = {"markets": ["US"], "orders": ["relevance"], "query_groups": [{"track": "a", "intent": "b", "queries": ["q"]}], "discovery": {"resource_type": "video", "video_duration": "short", "pages_per_cell": 2, "max_results_per_page": 50}}
    result = discover(FakeClient(), config, tmp_path, 2)
    assert result["new_search_calls"] == 2
    assert len(checkpoint_index(tmp_path, "search_discovery")) == 2


def test_checkpoint_index_rejects_corrupt_normalized_artifact(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    normalized = tmp_path / "page.jsonl"
    raw.write_text("{}", encoding="utf-8")
    normalized.write_text("{}\n", encoding="utf-8")
    event = {
        "stage": "search_discovery", "status": "page_committed", "target_id": "x", "page_index": 0,
        "raw_uri": "raw.json", "raw_sha256": __import__('hashlib').sha256(raw.read_bytes()).hexdigest(),
        "normalized_uri": "page.jsonl", "normalized_sha256": "0" * 64,
    }
    ledgers = tmp_path / "ledgers"
    ledgers.mkdir()
    (ledgers / "youtube-stage-checkpoints.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    assert checkpoint_index(tmp_path, "search_discovery") == {}


def test_checkpoint_index_rejects_valid_but_wrong_page_chain(tmp_path: Path) -> None:
    ledgers = tmp_path / "ledgers"
    ledgers.mkdir()
    events = []
    for page_index, used, following in ((0, None, "NEXT"), (1, "WRONG", None)):
        raw = tmp_path / f"raw-{page_index}.json"
        normalized = tmp_path / f"page-{page_index}.jsonl"
        raw.write_text("{}", encoding="utf-8")
        normalized.write_text("{}\n", encoding="utf-8")
        events.append({
            "stage": "search_discovery", "status": "page_committed", "target_id": "x", "page_index": page_index,
            "page_token_used": used, "next_page_token": following,
            "raw_uri": raw.name, "raw_sha256": __import__('hashlib').sha256(raw.read_bytes()).hexdigest(),
            "normalized_uri": normalized.name, "normalized_sha256": __import__('hashlib').sha256(normalized.read_bytes()).hexdigest(),
        })
    (ledgers / "youtube-stage-checkpoints.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    assert set(checkpoint_index(tmp_path, "search_discovery")) == {("x", 0)}


def test_fifth_strike_atomically_prevents_sixth_concurrent_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    counter = 0
    counter_lock = threading.Lock()

    def fail(*_args, **_kwargs):
        nonlocal counter
        with counter_lock:
            counter += 1
        raise TimeoutError("fixture timeout")

    monkeypatch.setattr(youtube_api, "urlopen", fail)
    clients = [
        YouTubeDataAPIClient(
            api_key="AIza" + "z" * 35,
            run_dir=tmp_path,
            quota=QuotaLedger(tmp_path / "quota.jsonl", daily_unit_budget=100, daily_search_call_budget=100),
            min_interval_seconds=0,
            sleeper=lambda _seconds: None,
        )
        for _ in range(6)
    ]

    def invoke(client):
        try:
            client.get("channels", "channels.list", {"part": "snippet", "id": "same"})
        except YouTubeAPIError as exc:
            return exc.code
        raise AssertionError("request unexpectedly succeeded")

    with ThreadPoolExecutor(max_workers=6) as executor:
        codes = list(executor.map(invoke, clients))
    assert counter == 5
    assert codes.count("NETWORK_ERROR") == 1
    assert codes.count("TARGET_BLOCKED") == 5


def test_fifth_strike_prevents_sixth_request_across_processes(tmp_path: Path) -> None:
    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    processes = [context.Process(target=_multiprocess_failure_worker, args=(str(tmp_path), queue)) for _ in range(6)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0
    codes = [queue.get(timeout=2) for _ in processes]
    attempts = (tmp_path / "external-attempts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(attempts) == 5
    assert codes.count("NETWORK_ERROR") == 1
    assert codes.count("TARGET_BLOCKED") == 5
