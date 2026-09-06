"""Serial, resumable full-corpus media acquisition and evidence dispatcher."""

from __future__ import annotations

import fcntl
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path
import re
from typing import Any, Mapping

from m2_studio.media import digest, validate_transcript, StudioError

from .media_acquisition import acquire, AcquisitionError
from .media_transcription import TranscriptionError, transcribe, validate_model_bundle
from .media_visual import extract_preview


SCHEMA = "m2.corpus-media-run.v1"
GI_B = 1024**3
DEFAULT_CACHE_BYTES = 8 * GI_B
DEFAULT_RESERVE_BYTES = 5 * GI_B
MAX_BATCH_SIZE = 8
_SYSTEM_ALIASES = {Path("/tmp"), Path("/private/tmp"), Path("/var"), Path("/private/var")}


class CorpusMediaError(ValueError):
    pass


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise CorpusMediaError("OUTPUT_PARTIAL_EXISTS")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _hash_files(paths: list[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise CorpusMediaError("IMPLEMENTATION_FILE_UNAVAILABLE")
        result[str(path)] = digest(path)
    return result


def _safe_receipt(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise CorpusMediaError("RIGHTS_RECEIPT_REQUIRED")
    return value.strip()


def _safe_error(value: Any) -> str:
    """Keep operational errors useful without persisting URLs or token-like values."""
    text = str(value)
    text = re.sub(r"https?://[^\s'\"]+", "<url-redacted>", text, flags=re.IGNORECASE)
    text = re.sub(r"(?i)(token|secret|password|cookie|api[_-]?key)\s*[=:]\s*[^\s,;]+", r"\1=<redacted>", text)
    return text[:512]


def _guard_path_ancestors(path: Path) -> None:
    """Reject symlinked output ancestors, allowing only OS temp aliases."""
    current = path.absolute()
    while True:
        if current.is_symlink() and current not in _SYSTEM_ALIASES:
            raise CorpusMediaError("OUTPUT_SYMLINK")
        if current == current.parent:
            return
        current = current.parent


def _manifest_entries(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CorpusMediaError("MANIFEST_ENTRIES_REQUIRED")
    seen_ids: set[str] = set()
    seen_codes: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("reel_id"), str) or not entry.get("reel_id") or not isinstance(entry.get("code"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", entry["code"]):
            raise CorpusMediaError("INVALID_MANIFEST_IDENTITY")
        if entry["reel_id"] in seen_ids or entry["code"] in seen_codes:
            raise CorpusMediaError("DUPLICATE_MANIFEST_IDENTITY")
        seen_ids.add(entry["reel_id"])
        seen_codes.add(entry["code"])
    return [dict(entry) for entry in entries]


def _source_record(record: Mapping[str, Any], rights_receipt: str) -> dict[str, Any]:
    enriched = dict(record)
    enriched["source_kind"] = "approved_research_copy"
    enriched["rights"] = {"analysis_allowed": True, "public_display_allowed": False, "receipt_id": rights_receipt}
    return enriched


class CorpusMediaDispatcher:
    """One locked dispatcher run. Network and model execution are caller-gated."""

    def __init__(
        self,
        manifest: dict,
        run_root: Path,
        *,
        model_dir: Path,
        manifest_sha256: str | None = None,
        python_executable: str | Path = sys.executable,
        media_roots: tuple[Path, ...] = (),
        rights_receipt: str,
        resolver_executable: Path | None = None,
        resolver_sha256: str | None = None,
        batch_size: int = MAX_BATCH_SIZE,
        cache_bytes: int = DEFAULT_CACHE_BYTES,
        reserve_bytes: int = DEFAULT_RESERVE_BYTES,
        allowed_hosts: tuple[str, ...] = ("cdninstagram.com", "fbcdn.net"),
    ):
        if not isinstance(manifest, Mapping):
            raise CorpusMediaError("MANIFEST_REQUIRED")
        self.manifest = dict(manifest)
        self.entries = _manifest_entries(self.manifest)
        if type(batch_size) is not int or not 1 <= batch_size <= MAX_BATCH_SIZE:
            raise CorpusMediaError("BATCH_SIZE_LIMIT")
        if type(cache_bytes) is not int or cache_bytes <= 0 or type(reserve_bytes) is not int or reserve_bytes <= 0:
            raise CorpusMediaError("RESOURCE_LIMIT_INVALID")
        self.run_root = Path(run_root).absolute()
        self.acquisition_root = self.run_root / "acquisition"
        self.model_dir = Path(model_dir).resolve()
        self.python_executable = str(python_executable)
        python_path = Path(self.python_executable)
        self.python_executable_sha256 = digest(python_path) if python_path.is_file() and not python_path.is_symlink() else None
        self.media_roots = tuple(Path(item).resolve() for item in media_roots)
        self.rights_receipt = _safe_receipt(rights_receipt)
        self.resolver_executable = Path(resolver_executable).resolve() if resolver_executable else None
        self.resolver_sha256 = resolver_sha256
        if self.resolver_executable and (not self.resolver_executable.is_file() or not isinstance(resolver_sha256, str) or digest(self.resolver_executable) != resolver_sha256):
            raise CorpusMediaError("RESOLVER_HASH_REQUIRED")
        self.batch_size = batch_size
        self.cache_bytes = cache_bytes
        self.reserve_bytes = reserve_bytes
        self.allowed_hosts = tuple(allowed_hosts)
        self.model_receipt = validate_model_bundle(self.model_dir)
        code_paths = [
            Path(__file__),
            Path(__file__).with_name("media_acquisition.py"),
            Path(__file__).with_name("media_transcription.py"),
            Path(__file__).with_name("media_visual.py"),
            Path(__file__).with_name("process_budget.py"),
        ]
        if self.resolver_executable:
            code_paths.append(self.resolver_executable)
        code_paths.extend(
            [
                Path(__file__).with_name("public_media.py"),
                Path(__file__).with_name("resolver_proxy.py"),
                Path(__file__).parents[1] / "m2_studio" / "media.py",
                Path(__file__).parents[1] / "scripts" / "run_m2_corpus_media.py",
            ]
        )
        self.code_hashes = _hash_files(code_paths)
        self.manifest_source_hash = manifest_sha256 or stable_hash(self.manifest)
        self.manifest_object_hash = stable_hash(self.manifest)
        if not isinstance(self.manifest_source_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", self.manifest_source_hash):
            raise CorpusMediaError("MANIFEST_HASH_INVALID")
        self.config = {
            "schema": "m2.corpus-media-config.v1",
            "manifest_sha256": self.manifest_source_hash,
            "manifest_object_sha256": self.manifest_object_hash,
            "code_hashes": self.code_hashes,
            "model": self.model_receipt,
            "rights": {"source_kind": "approved_research_copy", "receipt_id": self.rights_receipt, "analysis_allowed": True, "public_display_allowed": False},
            "python_executable": self.python_executable,
            "python_executable_sha256": self.python_executable_sha256,
            "media_roots": [str(path) for path in self.media_roots],
            "resolver_executable": str(self.resolver_executable) if self.resolver_executable else None,
            "resolver_sha256": self.resolver_sha256,
            "batch_size": self.batch_size,
            "cache_bytes": self.cache_bytes,
            "reserve_bytes": self.reserve_bytes,
            "allowed_hosts": list(self.allowed_hosts),
            "network_policy": "caller_explicit_network_true_only",
            "source_videos_retained": True,
            "visual_public_display_allowed": False,
            "max_attempts": 3,
        }
        self.config_hash = stable_hash(self.config)
        self.db: sqlite3.Connection | None = None
        self.lock = None

    def _open(self) -> None:
        for path in (self.run_root, self.acquisition_root, self.run_root / "transcripts", self.run_root / "frames"):
            _guard_path_ancestors(path)
        self.run_root.mkdir(parents=True, exist_ok=True)
        if any(path.is_symlink() for path in (self.run_root, self.acquisition_root)):
            raise CorpusMediaError("OUTPUT_SYMLINK")
        lock_path = self.run_root / ".dispatcher.lock"
        if lock_path.is_symlink():
            raise CorpusMediaError("OUTPUT_SYMLINK")
        self.lock = lock_path.open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            self.lock = None
            raise CorpusMediaError("DISPATCHER_ALREADY_RUNNING") from None
        for path in (self.acquisition_root, self.run_root / "transcripts", self.run_root / "frames"):
            path.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                raise CorpusMediaError("OUTPUT_SYMLINK")
        self.db = sqlite3.connect(self.run_root / "corpus-media.sqlite", timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS binding (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS reels (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL, identity_index INTEGER NOT NULL, acquisition_state TEXT NOT NULL, transcript_state TEXT NOT NULL, frames_state TEXT NOT NULL, scene_review_state TEXT NOT NULL, acquisition_artifact TEXT, transcript_artifact TEXT, frames_artifact TEXT);"
            "CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, reel_id TEXT NOT NULL, stage TEXT NOT NULL, attempt INTEGER NOT NULL, state TEXT NOT NULL, error TEXT, started REAL NOT NULL, finished REAL, artifacts_json TEXT, resources_json TEXT, FOREIGN KEY(reel_id) REFERENCES reels(reel_id));"
            "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, event TEXT NOT NULL, stage TEXT, reel_id TEXT, observed_at REAL NOT NULL, payload_json TEXT NOT NULL);"
        )
        existing = dict(self.db.execute("SELECT key,value FROM binding"))
        expected = {"config_sha256": self.config_hash, "manifest_sha256": self.manifest_source_hash, "manifest_object_sha256": self.manifest_object_hash}
        if existing and any(existing.get(key) != value for key, value in expected.items()):
            raise CorpusMediaError("FROZEN_CONFIG_CHANGED")
        for key, value in expected.items():
            self.db.execute("INSERT OR IGNORE INTO binding VALUES (?,?)", (key, value))
        config_path = self.run_root / "config.json"
        manifest_path = self.run_root / "manifest.private.json"
        summary_path = self.run_root / "summary.json"
        if any(path.is_symlink() for path in (config_path, manifest_path, summary_path, self.run_root / "corpus-media.sqlite")):
            raise CorpusMediaError("OUTPUT_SYMLINK")
        if config_path.exists():
            try:
                if stable_hash(json.loads(config_path.read_text(encoding="utf-8"))) != self.config_hash:
                    raise CorpusMediaError("FROZEN_CONFIG_CHANGED")
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise CorpusMediaError("FROZEN_CONFIG_CHANGED") from None
        else:
            _json_write(config_path, self.config)
        if manifest_path.exists():
            try:
                if stable_hash(json.loads(manifest_path.read_text(encoding="utf-8"))) != self.manifest_object_hash:
                    raise CorpusMediaError("FROZEN_MANIFEST_CHANGED")
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise CorpusMediaError("FROZEN_MANIFEST_CHANGED") from None
        else:
            _json_write(manifest_path, self.manifest)
        for index, entry in enumerate(self.entries):
            self.db.execute(
                "INSERT OR IGNORE INTO reels (reel_id,code,identity_index,acquisition_state,transcript_state,frames_state,scene_review_state) VALUES (?,?,?,?,?,?,?)",
                (entry["reel_id"], entry["code"], index,
                 "DEFERRED_PILOT" if self.manifest.get('pilot_codes') is not None and entry['code'] not in self.manifest['pilot_codes'] else "NOT_ATTEMPTED",
                 "NOT_ATTEMPTED", "NOT_ATTEMPTED", "NOT_ATTEMPTED"),
            )
        self.db.commit()
        interrupted = self.db.execute("SELECT COUNT(*) FROM attempts WHERE state='RUNNING'").fetchone()[0]
        self.db.execute("UPDATE attempts SET state='INTERRUPTED',error='WORKER_INTERRUPTED',finished=? WHERE state='RUNNING'",(time.time(),))
        self.db.commit()
        if interrupted:
            self._event('interrupted_attempts_recovered',payload={'count':interrupted})
        self._event("identities_registered", payload={"population": len(self.entries)})

    def _event(self, event: str, *, stage: str | None = None, reel_id: str | None = None, payload: Mapping[str, Any] | None = None) -> None:
        assert self.db is not None
        self.db.execute("INSERT INTO events (event,stage,reel_id,observed_at,payload_json) VALUES (?,?,?,?,?)", (event, stage, reel_id, time.time(), json.dumps(dict(payload or {}), sort_keys=True, ensure_ascii=False)))
        self.db.commit()

    def _attempt_start(self, reel_id: str, stage: str) -> tuple[int, int]:
        assert self.db is not None
        row = self.db.execute("SELECT COALESCE(MAX(attempt),0) FROM attempts WHERE reel_id=? AND stage=?", (reel_id, stage)).fetchone()
        attempt = int(row[0]) + 1
        cur = self.db.execute("INSERT INTO attempts (reel_id,stage,attempt,state,started) VALUES (?,?,?,?,?)", (reel_id, stage, attempt, "RUNNING", time.time()))
        self.db.commit()
        contracts = {
            'acquisition': {'role':'data_engineer','executor':'serial_media_adapter','goal':'Recover and validate the retained source video for this identity'},
            'transcript': {'role':'text_analyst','executor':'faster_whisper_small_cpu_int8','goal':'Extract timed spoken text while preserving uncertainty and raw evidence'},
            'frames': {'role':'scene_analyst','executor':'ffmpeg_local','goal':'Extract regular and visual-change frames for independent scene review'},
        }
        self._event("stage_started", stage=stage, reel_id=reel_id, payload={"attempt": attempt, **contracts.get(stage,{})})
        return int(cur.lastrowid), attempt

    def _attempt_finish(self, attempt_id: int, reel_id: str, stage: str, state: str, *, error: str | None = None, artifacts: Mapping[str, Any] | None = None, resources: Mapping[str, Any] | None = None) -> None:
        assert self.db is not None
        safe_error = _safe_error(error) if error else None
        self.db.execute("UPDATE attempts SET state=?,error=?,finished=?,artifacts_json=?,resources_json=? WHERE id=?", (state, safe_error, time.time(), json.dumps(dict(artifacts or {}), sort_keys=True), json.dumps(dict(resources or {}), sort_keys=True), attempt_id))
        self.db.commit()
        self._event("stage_finished", stage=stage, reel_id=reel_id, payload={"state": state, "error": safe_error})

    def _artifact_hashes(self, paths: list[Path]) -> dict[str, str]:
        result: dict[str, str] = {}
        for path in paths:
            if not path.is_file() or path.is_symlink():
                raise CorpusMediaError("ARTIFACT_MISSING")
            result[str(path.relative_to(self.run_root))] = digest(path)
        return result

    def _validate_saved_artifacts(self, value: str | None) -> None:
        if not value:
            return
        try:
            artifacts = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            raise CorpusMediaError("SAVED_ARTIFACT_INDEX_INVALID") from None
        if not isinstance(artifacts, Mapping):
            raise CorpusMediaError("SAVED_ARTIFACT_INDEX_INVALID")
        for relative, expected in artifacts.items():
            raw_path = self.run_root / str(relative)
            path = raw_path.resolve()
            if raw_path.is_symlink() or not path.is_file() or not path.is_relative_to(self.run_root) or not isinstance(expected, str) or digest(path) != expected:
                raise CorpusMediaError("SAVED_ARTIFACT_CHANGED")

    def _attempt_count(self, reel_id: str, stage: str) -> int:
        assert self.db is not None
        row = self.db.execute("SELECT COUNT(*) FROM attempts WHERE reel_id=? AND stage=?", (reel_id, stage)).fetchone()
        return int(row[0])

    def _stage_pending(self, reel_id: str, stage: str, state: str) -> bool:
        if self._attempt_count(reel_id, stage) >= 3:
            return False
        if state == "NOT_ATTEMPTED":
            return True
        if stage == "acquisition":
            return state == "RETRYABLE"
        if stage == "transcript":
            return state in {"ASR_EXECUTION_FAILED", "ASR_TIMEOUT", "ASR_RESOURCE_LIMIT"}
        if stage == "frames":
            return state in {"VISUAL_FAILED", "DECODE_FAILED"}
        return False

    def _load_acquired(self, code: str) -> dict[str, Any] | None:
        database=self.acquisition_root/'acquisition.sqlite'
        if database.is_symlink():
            raise CorpusMediaError('ACQUISITION_DB_SYMLINK')
        uri=database.resolve().as_uri()+'?mode=ro'
        with sqlite3.connect(uri,uri=True) as source:
            source.row_factory=sqlite3.Row
            source.execute('PRAGMA query_only=ON')
            row=source.execute("SELECT * FROM items WHERE code=? AND state='OBSERVED'",(code,)).fetchone()
        if not row:
            return None
        path=self.acquisition_root/row['record_path']
        if path.is_symlink() or not path.resolve().is_relative_to(self.acquisition_root.resolve()) or digest(path)!=row['record_sha256']:
            raise CorpusMediaError('ACQUISITION_ARTIFACT_CHANGED')
        record=json.loads(path.read_text())
        expected=next(e['reel_id'] for e in self.entries if e['code']==code)
        if record.get('reel_id')!=expected or record.get('media_id')!=code or record.get('sha256')!=row['sha256'] or record.get('source_pointer')!=row['artifact']:
            raise CorpusMediaError('ACQUISITION_IDENTITY_MISMATCH')
        return record

    def _validate_frames(self,result,media,root):
        state=result.get('frame_observation_state')
        frames=result.get('sampled_frames',[])
        if not isinstance(frames,list):
            raise CorpusMediaError('FRAME_RESULT_INVALID')
        if state not in {'OBSERVED','PARTIAL','DECODE_FAILED'}:
            raise CorpusMediaError('FRAME_STATE_INVALID')
        if state=='DECODE_FAILED' and not frames:
            return
        if state=='DECODE_FAILED':
            raise CorpusMediaError('FRAME_STATE_INVALID')
        budget=result.get('frame_budget',{})
        requested=budget.get('requested_frames')
        if (result.get('source_media_hash')!=media['sha256'] or not 0<len(frames)<=48
            or type(requested) is not int or not len(frames)<=requested<=48
            or budget.get('observed_frames')!=len(frames)
            or (state=='OBSERVED' and len(frames)!=requested)
            or (state=='PARTIAL' and len(frames)>=requested)):
            raise CorpusMediaError('FRAME_RESULT_INVARIANT_FAILED')
        ids=set();indices=set()
        for frame in frames:
            index=frame.get('frame_index');fid=frame.get('frame_id')
            if (type(index) is not int or not 0<=index<len(media['frame_pts_ms']) or frame.get('timestamp_ms')!=media['frame_pts_ms'][index] or not isinstance(fid,str) or fid in ids or index in indices
                or frame.get('observation_state')!='OBSERVED' or frame.get('decoded_frame_index')!=index or frame.get('source_media_hash')!=media['sha256']):
                raise CorpusMediaError('FRAME_IDENTITY_INVALID')
            path=root/frame.get('source_pointer','')
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()) or digest(path)!=frame.get('sha256'):
                raise CorpusMediaError('FRAME_HASH_INVALID')
            ids.add(fid);indices.add(index)

    def _validate_transcript_result(self,result,media):
        state=result.get('observation_state')
        allowed={'OBSERVED','SUSPICIOUS_TIMINGS','EMPTY_OUTPUT_UNVERIFIED','NOT_APPLICABLE','ASR_FAILED'}
        if state not in allowed:
            raise CorpusMediaError('TRANSCRIPT_STATE_INVALID')
        if state=='ASR_FAILED':
            return
        if result.get('source_media_hash')!=media['sha256']:
            raise CorpusMediaError('TRANSCRIPT_MEDIA_HASH_MISMATCH')
        segments=result.get('segments')
        if not isinstance(segments,list):
            raise CorpusMediaError('TRANSCRIPT_SEGMENTS_INVALID')
        if state in {'OBSERVED','SUSPICIOUS_TIMINGS'}:
            if not segments:
                raise CorpusMediaError('EMPTY_TRANSCRIPT_CANNOT_BE_OBSERVED')
            validate_transcript(segments,media['duration_ms'])
        elif segments or (state=='NOT_APPLICABLE' and media.get('has_audio') is not False):
            raise CorpusMediaError('TRANSCRIPT_STATE_INVARIANT_FAILED')

    def _refresh_acquisition_states(self) -> None:
        assert self.db is not None
        acq_db = self.acquisition_root / "acquisition.sqlite"
        if acq_db.is_symlink():
            raise CorpusMediaError('ACQUISITION_DB_SYMLINK')
        if not acq_db.is_file():
            return
        with sqlite3.connect(acq_db.resolve().as_uri()+'?mode=ro',uri=True) as source:
            source.row_factory = sqlite3.Row
            source.execute('PRAGMA query_only=ON')
            source.execute('BEGIN')
            rows = source.execute("SELECT reel_id,code,state,artifact,sha256,record_path,record_sha256 FROM items").fetchall()
        for row in rows:
            if row["state"] == "OBSERVED":
                if not row["artifact"] or not row["record_path"]:
                    raise CorpusMediaError("ACQUISITION_RECORD_INCOMPLETE")
                media = self.acquisition_root / row["artifact"]
                record_path = self.acquisition_root / row["record_path"]
                if (media.is_symlink() or record_path.is_symlink() or not media.resolve().is_relative_to(self.acquisition_root.resolve()) or not record_path.resolve().is_relative_to(self.acquisition_root.resolve()) or not media.is_file() or digest(media) != row["sha256"] or not record_path.is_file() or digest(record_path) != row["record_sha256"]):
                    raise CorpusMediaError("ACQUISITION_ARTIFACT_CHANGED")
                state = "OBSERVED"
                acquisition_artifact = json.dumps(
                    {
                        str(media.relative_to(self.run_root)): row["sha256"],
                        str(record_path.relative_to(self.run_root)): row["record_sha256"],
                    },
                    sort_keys=True,
                )
            else:
                state = row["state"]
                acquisition_artifact = None
                previous=self.db.execute('SELECT acquisition_state FROM reels WHERE reel_id=?',(row['reel_id'],)).fetchone()
                if previous and previous[0]=='ACQUISITION_FAILED' and state=='NOT_ATTEMPTED':
                    state='ACQUISITION_FAILED'
            self.db.execute("UPDATE reels SET acquisition_state=?,acquisition_artifact=? WHERE reel_id=?", (state, acquisition_artifact, row["reel_id"]))
        self.db.commit()

    def _process_evidence(self, entry: Mapping[str, Any]) -> None:
        assert self.db is not None
        rid, code = entry["reel_id"], entry["code"]
        row = self.db.execute("SELECT acquisition_state,transcript_state,frames_state,transcript_artifact,frames_artifact FROM reels WHERE reel_id=?", (rid,)).fetchone()
        if not row or row["acquisition_state"] != "OBSERVED":
            return
        if row["transcript_artifact"]:
            self._validate_saved_artifacts(row["transcript_artifact"])
        if row["frames_artifact"]:
            self._validate_saved_artifacts(row["frames_artifact"])
        record = self._load_acquired(code)
        if not record:
            return
        record = _source_record(record, self.rights_receipt)
        if self._stage_pending(rid, "transcript", row["transcript_state"]):
            attempt_id, attempt = self._attempt_start(rid, "transcript")
            transcript_output = self.run_root / "transcripts" / code / f"attempt-{attempt}"
            transcript_output.parent.mkdir(parents=True, exist_ok=True)
            try:
                result = transcribe(record, self.acquisition_root, transcript_output, self.python_executable, self.model_dir)
                self._validate_transcript_result(result,record)
                state = result.get("observation_state", "ASR_FAILED")
                final = state if isinstance(state, str) and state else "ASR_FAILED"
                if final == "ASR_FAILED" and result.get("failure_code") in {"ASR_EXECUTION_FAILED", "ASR_TIMEOUT", "ASR_RESOURCE_LIMIT"}:
                    final = result["failure_code"]
                artifacts = self._artifact_hashes([path for path in transcript_output.iterdir() if path.is_file()]) if transcript_output.is_dir() else {}
                self.db.execute("UPDATE reels SET transcript_state=?,transcript_artifact=? WHERE reel_id=?", (final, json.dumps(artifacts, sort_keys=True), rid))
                self.db.commit()
                _json_write(transcript_output/'dispatch-result.json',result)
                artifacts = self._artifact_hashes([path for path in transcript_output.iterdir() if path.is_file()])
                self.db.execute("UPDATE reels SET transcript_artifact=? WHERE reel_id=?",(json.dumps(artifacts,sort_keys=True),rid));self.db.commit()
                resources = {**result.get('resource_receipt',{}), 'metrics':{key:result.get(key) for key in ['lexical_word_count','aligned_word_count','unaligned_word_count','word_timing','language','asr_execution']}, 'model_sha256':result.get('model_sha256'), 'config_sha256':result.get('config_sha256')}
                self._attempt_finish(attempt_id, rid, "transcript", final, error=result.get('failure_code'), artifacts=artifacts, resources=resources)
            except Exception as exc:
                error = _safe_error(exc) if isinstance(exc, (TranscriptionError,CorpusMediaError,StudioError)) else type(exc).__name__
                final = error if error in {"ASR_EXECUTION_FAILED", "ASR_TIMEOUT", "ASR_RESOURCE_LIMIT"} else "ASR_FAILED"
                self.db.execute("UPDATE reels SET transcript_state=? WHERE reel_id=?", (final, rid)); self.db.commit()
                self._attempt_finish(attempt_id, rid, "transcript", final, error=error)

        row = self.db.execute("SELECT frames_state FROM reels WHERE reel_id=?", (rid,)).fetchone()
        if self._stage_pending(rid, "frames", row["frames_state"]):
            attempt_id, attempt = self._attempt_start(rid, "frames")
            frames_output = self.run_root / "frames" / code / f"attempt-{attempt}"
            frames_output.parent.mkdir(parents=True, exist_ok=True)
            try:
                result = extract_preview(self.acquisition_root, record, frames_output)
                self._validate_frames(result,record,frames_output)
                artifacts = self._artifact_hashes([path for path in frames_output.iterdir() if path.is_file()])
                frame_state = result.get("frame_observation_state", "DECODE_FAILED")
                if not isinstance(frame_state, str) or not frame_state:
                    frame_state = "DECODE_FAILED"
                scene_state = "REVIEW_PENDING" if frame_state in {"OBSERVED", "PARTIAL"} else "NOT_REVIEWED"
                self.db.execute("UPDATE reels SET frames_state=?,scene_review_state=?,frames_artifact=? WHERE reel_id=?", (frame_state, scene_state, json.dumps(artifacts, sort_keys=True), rid)); self.db.commit()
                self._attempt_finish(attempt_id, rid, "frames", frame_state, artifacts=artifacts, resources={"sample_count": len(result.get("sampled_frames", [])), "cut_candidates": len(result.get("cut_candidates_ms", [])), 'cut_observation_state':result.get('cut_observation_state'), 'processes':result.get('resources'), 'output_bytes':result.get('output_bytes'), 'frame_budget':result.get('frame_budget')})
            except Exception as exc:
                error = _safe_error(exc) if isinstance(exc, (ValueError, TranscriptionError)) else type(exc).__name__
                self.db.execute("UPDATE reels SET frames_state=? WHERE reel_id=?", ("VISUAL_FAILED", rid)); self.db.commit()
                self._attempt_finish(attempt_id, rid, "frames", "VISUAL_FAILED", error=error)
        _json_write(self.run_root/'summary.json',self._summary(max_items=None))

    def _summary(self, *, max_items: int | None) -> dict[str, Any]:
        assert self.db is not None
        states: dict[str, dict[str, int]] = {}
        for field in ("acquisition_state", "transcript_state", "frames_state", "scene_review_state"):
            states[field] = {row[0]: row[1] for row in self.db.execute(f"SELECT {field},COUNT(*) FROM reels GROUP BY {field}")}
        return {"schema": SCHEMA, "config_sha256": self.config_hash, "manifest_sha256": self.manifest_source_hash, "manifest_object_sha256": self.manifest_object_hash, "population": len(self.entries), "max_items": max_items, "states": states, "source_videos_retained": True, "networked_hikerapi_calls": 0, "asr_and_visual_serial": True, "scene_review_state": "REVIEW_PENDING_OR_NOT_ATTEMPTED"}

    def run(self, *, network: bool = True, max_items: int | None = None) -> dict[str, Any]:
        if network is not True:
            raise CorpusMediaError("EXPLICIT_NETWORK_TRUE_REQUIRED")
        if max_items is not None and (type(max_items) is not int or max_items <= 0):
            raise CorpusMediaError("MAX_ITEMS_INVALID")
        attempted_identities = 0
        recovery_batch_size = self.batch_size
        try:
            self._open()
            assert self.db is not None
            self._refresh_acquisition_states()
            while True:
                if max_items is not None and attempted_identities >= max_items:
                    break
                limit = recovery_batch_size if max_items is None else min(recovery_batch_size, max_items - attempted_identities)
                pending_acquisition = []
                for entry in self.entries:
                    row = self.db.execute("SELECT acquisition_state FROM reels WHERE reel_id=?", (entry["reel_id"],)).fetchone()
                    if row and self._stage_pending(entry["reel_id"], "acquisition", row[0]):
                        pending_acquisition.append(entry)
                acquisition_targets = pending_acquisition[:limit]
                if acquisition_targets:
                    self._event("batch_started", stage="acquisition", payload={"batch_size": len(acquisition_targets), "attempted_identities": attempted_identities})
                    acquisition_attempts = {entry["reel_id"]: self._attempt_start(entry["reel_id"], "acquisition") for entry in acquisition_targets}
                    attempted_identities += len(acquisition_targets)
                    hard_stop = False
                    try:
                        acquisition_summary = acquire(self.manifest, self.acquisition_root, network=True, media_roots=self.media_roots, max_attempts=3, limit=len(acquisition_targets), target_ids=[e['reel_id'] for e in acquisition_targets], cache_bytes=self.cache_bytes, reserve_bytes=self.reserve_bytes, allowed_hosts=self.allowed_hosts, resolver_executable=str(self.resolver_executable) if self.resolver_executable else None, resolver_sha256=self.resolver_sha256)
                        self._refresh_acquisition_states()
                        recovery_batch_size = self.batch_size
                        for rid, (attempt_id, _) in acquisition_attempts.items():
                            state_row = self.db.execute("SELECT acquisition_state,acquisition_artifact FROM reels WHERE reel_id=?", (rid,)).fetchone()
                            state = state_row[0] if state_row else "ACQUISITION_FAILED"
                            artifacts = json.loads(state_row[1]) if state_row and state_row[1] else None
                            self._attempt_finish(attempt_id, rid, "acquisition", state, artifacts=artifacts, resources=acquisition_summary if isinstance(acquisition_summary, Mapping) else {})
                    except Exception as exc:
                        code = str(exc) if isinstance(exc, (CorpusMediaError,AcquisitionError)) else type(exc).__name__
                        hard_stop = code in {'STORAGE_BUDGET_STOP','WORKER_ALREADY_RUNNING','NEW_MANIFEST_REQUIRES_NEW_RUN','COMPLETED_MEDIA_CHANGED','COMPLETED_PROVENANCE_CHANGED','RESOLVER_EVIDENCE_CHANGED','OUTPUT_SYMLINK','OUTPUT_ROOT_SYMLINK','ACQUISITION_ARTIFACT_CHANGED'}
                        self._refresh_acquisition_states()
                        for rid, (attempt_id, _) in acquisition_attempts.items():
                            observed=self.db.execute('SELECT acquisition_state FROM reels WHERE reel_id=?',(rid,)).fetchone()[0]=='OBSERVED'
                            state='OBSERVED' if observed else 'ACQUISITION_FAILED' if hard_stop or self._attempt_count(rid,'acquisition')>=3 else 'RETRYABLE'
                            self.db.execute('UPDATE reels SET acquisition_state=? WHERE reel_id=?',(state,rid));self.db.commit()
                            self._attempt_finish(attempt_id, rid, "acquisition", state, error=None if observed else code)
                        if hard_stop:
                            self._event('hard_stop',stage='acquisition',payload={'error':code})
                        if not hard_stop:
                            recovery_batch_size = 1
                            self._event('retry_as_individual_items',stage='acquisition',payload={'error':code})
                    self._event("batch_finished", stage="acquisition", payload={"attempted_identities": attempted_identities, "population": len(self.entries), "hard_stop": hard_stop})
                    for entry in acquisition_targets:
                        self._process_evidence(entry)
                    if hard_stop:
                        break
                    continue

                modality_targets = []
                for entry in self.entries:
                    row = self.db.execute("SELECT acquisition_state,transcript_state,frames_state FROM reels WHERE reel_id=?", (entry["reel_id"],)).fetchone()
                    if not row or row[0] != "OBSERVED":
                        continue
                    transcript_pending = self._stage_pending(entry["reel_id"], "transcript", row[1])
                    frames_pending = self._stage_pending(entry["reel_id"], "frames", row[2])
                    if transcript_pending or frames_pending:
                        modality_targets.append(entry)
                if not modality_targets:
                    break
                targets = modality_targets[:limit]
                self._event("batch_started", stage="evidence", payload={"batch_size": len(targets), "attempted_identities": attempted_identities})
                attempted_identities += len(targets)
                for entry in targets:
                    self._process_evidence(entry)
                self._event("batch_finished", stage="evidence", payload={"attempted_identities": attempted_identities, "population": len(self.entries)})
            summary = self._summary(max_items=max_items)
            _json_write(self.run_root / "summary.json", summary)
            return summary
        finally:
            if self.db is not None:
                self.db.close()
                self.db = None
            if self.lock is not None:
                fcntl.flock(self.lock, fcntl.LOCK_UN)
                self.lock.close()
                self.lock = None


def run_corpus_media(manifest_path: Path, run_root: Path, *, network: bool = True, max_items: int | None = None, **kwargs: Any) -> dict[str, Any]:
    manifest_path = Path(manifest_path).absolute()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CorpusMediaError("MANIFEST_FILE_UNAVAILABLE")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return CorpusMediaDispatcher(manifest, run_root, manifest_sha256=digest(manifest_path), **kwargs).run(network=network, max_items=max_items)


__all__ = ["CorpusMediaDispatcher", "CorpusMediaError", "run_corpus_media"]
