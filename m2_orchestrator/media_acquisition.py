"""Serial cache-based acquisition. No Hiker client, cookies, credentials or ASR.

URLs remain in the private frozen manifest; the attempt database stores hashes.
Downloads pin a public DNS result to the TLS connection and validate redirects.
"""
from __future__ import annotations
import hashlib
import fcntl
import http.client
import ipaddress
import json
import math
import os
import shutil
import socket
import sqlite3
import ssl
import tempfile
import time
import sys
from fractions import Fraction
from .process_budget import bounded_process, ProcessBudgetError
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from m2_studio.media import StudioError, digest, probe, run_tool, write_json


class AcquisitionError(ValueError):
    pass


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_url(url, allowed_hosts):
    try:
        p = urlsplit(url)
        host = (p.hostname or '').lower()
        if p.scheme != 'https' or p.username or p.password or p.port not in (None, 443) or p.fragment:
            raise ValueError()
        if not host or not any(host == h or host.endswith('.' + h) for h in allowed_hosts):
            raise ValueError()
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in url) or len(url) > 8192:
            raise ValueError()
    except (TypeError, ValueError):
        raise AcquisitionError('URL_NOT_ALLOWED') from None
    return p, host


def public_address(host, timeout=15):
    script = "import socket,json,sys; print(json.dumps(sorted({x[4][0] for x in socket.getaddrinfo(sys.argv[1],443,type=socket.SOCK_STREAM)})))"
    try:
        result = bounded_process([sys.executable, '-c', script, host], timeout=timeout, stdout_limit=16384, stderr_limit=4096)
        if result['returncode']:
            raise AcquisitionError('DNS_UNAVAILABLE')
        ips = json.loads(result['stdout'])
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise AcquisitionError('NONPUBLIC_ADDRESS')
        return ips[0]
    except (ProcessBudgetError, ValueError, OSError) as exc:
        if isinstance(exc, AcquisitionError):
            raise
        raise AcquisitionError('DNS_UNAVAILABLE') from None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        deadline = time.monotonic()+self.timeout
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            raw.settimeout(max(.01,deadline-time.monotonic()))
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def download(url, target, *, allowed_hosts=('cdninstagram.com', 'fbcdn.net'), max_bytes=128*1024*1024,
             timeout=90, redirects=2):
    """Write an exclusive staging path; caller promotes only decoded content."""
    start = time.monotonic()
    target = Path(target)
    current = url
    owned = False
    hops = []
    try:
        for hop in range(redirects + 1):
            p, host = validate_url(current, allowed_hosts)
            address = public_address(host, timeout=max(.01, min(15, timeout-(time.monotonic()-start))))
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                raise AcquisitionError('DOWNLOAD_TIMEOUT')
            con = PinnedHTTPS(host, address, min(remaining, 15))
            try:
                con.connect()
                if con.sock:
                    con.sock.settimeout(max(.01,timeout-(time.monotonic()-start)))
                con.request('GET', (p.path or '/') + ('?' + p.query if p.query else ''),
                            headers={'User-Agent': 'M2-MediaResearch/1.0', 'Accept-Encoding': 'identity'})
                response = con.getresponse()
                status = response.status
                hops.append({"host":host,"address":address,"http_status":status,"url_sha256":hashlib.sha256(current.encode()).hexdigest()})
                if status in (301, 302, 303, 307, 308):
                    location = response.getheader('Location')
                    if not location or hop == redirects:
                        raise AcquisitionError('REDIRECT_LIMIT')
                    current = urljoin(current, location)
                    continue
                if status != 200:
                    raise AcquisitionError('HTTP_' + str(status))
                if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                    raise AcquisitionError('ENCODING_NOT_ALLOWED')
                declared = response.getheader('Content-Length')
                try:
                    size = int(declared) if declared is not None else None
                except ValueError:
                    raise AcquisitionError('INVALID_CONTENT_LENGTH') from None
                if size is not None and not 0 < size <= max_bytes:
                    raise AcquisitionError('DOWNLOAD_SIZE_LIMIT')
                total = 0
                with target.open('xb') as output:
                    owned = True
                    while True:
                        remaining = timeout - (time.monotonic() - start)
                        if remaining <= 0:
                            raise AcquisitionError('DOWNLOAD_TIMEOUT')
                        sock = con.sock or getattr(getattr(response.fp, 'raw', None), '_sock', None)
                        if sock:
                            sock.settimeout(min(remaining, 15))
                        chunk = response.read(min(65536, max_bytes - total + 1))
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_bytes:
                            raise AcquisitionError('DOWNLOAD_SIZE_LIMIT')
                        output.write(chunk)
                if total == 0 or (size is not None and size != total):
                    raise AcquisitionError('TRUNCATED_DOWNLOAD')
                return {'http_status': 200, 'bytes': total, 'redirects': hop,
                        'url_sha256': hashlib.sha256(url.encode()).hexdigest(), 'hops':hops}
            finally:
                con.close()
        raise AcquisitionError('REDIRECT_LIMIT')
    except (OSError, http.client.HTTPException):
        if owned:
            target.unlink(missing_ok=True)
        raise AcquisitionError('NETWORK_FAILURE') from None
    except BaseException:
        if owned:
            target.unlink(missing_ok=True)
        raise


def bounded_probe(path, max_duration_ms=180000):
    deadline = time.monotonic()+60
    def command(extra, output_limit=4*1024*1024):
        result = bounded_process(['ffprobe', '-v', 'error', '-threads', '1', '-protocol_whitelist', 'file,pipe', *extra],
                                 timeout=max(.01, deadline-time.monotonic()), stdout_limit=output_limit, rss_limit_bytes=512*1024**2)
        if result['returncode']:
            raise AcquisitionError('DECODE_FAILED')
        return json.loads(result['stdout'])
    try:
        metadata = command(['-show_streams', '-show_format', '-of', 'json', str(path)])
        video = next((x for x in metadata.get('streams', []) if x.get('codec_type') == 'video'), None)
        if not video:
            raise AcquisitionError('NO_VIDEO_STREAM')
        w, h = video.get('width', 0), video.get('height', 0)
        duration_ms = round(float(video.get('duration', metadata.get('format', {}).get('duration', 0)))*1000)
        fps = float(Fraction(video.get('avg_frame_rate', '0/1')))
        if type(w) is not int or type(h) is not int or not 0 < w*h <= 8294400 or max(w,h)>4096:
            raise AcquisitionError('MEDIA_RESOURCE_LIMIT')
        if not 0 < duration_ms <= max_duration_ms or not 0 < fps <= 120:
            raise AcquisitionError('MEDIA_RESOURCE_LIMIT')
        frames = command(['-select_streams', 'v:0', '-show_frames', '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', str(path)], 8*1024*1024)['frames']
        if not 0 < len(frames) <= 21600:
            raise AcquisitionError('FRAME_LIMIT')
        pts = [float(x['best_effort_timestamp_time']) for x in frames]
        first = pts[0];norm = [round((x-first)*1000) for x in pts]
        if not all(math.isfinite(x) for x in pts) or any(b<=a for a,b in zip(norm,norm[1:])) or norm[-1]>=duration_ms:
            raise AcquisitionError('FRAME_TIMEBASE_INVALID')
        audio = next((x for x in metadata['streams'] if x.get('codec_type')=='audio'),None)
        offset = round((float(audio.get('start_time',first))-first)*1000) if audio else None
        return {'duration_ms':duration_ms,'width':w,'height':h,'fps':fps,'has_audio':audio is not None,'frame_pts_ms':norm,
                'timebase_provenance':{'source_time_base':video.get('time_base'),'source_start_time':video.get('start_time'),
                                      'first_decoded_pts_seconds':first,'normalization_offset_ms':round(-first*1000),
                                      'audio_offset_ms':offset,'raw_frame_pts_seconds':pts,'source_media_hash':digest(path)},
                'probe_budget':{'total_timeout_seconds':60,'threads':1,'frame_output_limit_bytes':8*1024*1024,'rss_watchdog_limit_bytes':512*1024**2,'rss_watchdog_poll_seconds':.2,'hard_os_memory_cap':False}}
    except (ProcessBudgetError, ValueError, KeyError, TypeError, OverflowError) as exc:
        if isinstance(exc, AcquisitionError):
            raise
        raise AcquisitionError('PROBE_BUDGET_OR_FORMAT_FAILURE') from None


def acquire(manifest, root, *, network=False, media_roots=(), allowed_hosts=('cdninstagram.com', 'fbcdn.net'),
            max_bytes=128*1024*1024, timeout=90, max_attempts=3, limit=None, probe_fn=bounded_probe, progress=None, reserve_bytes=5*1024**3, cache_bytes=8*1024**3, resolver_executable=None, resolver_sha256=None, target_ids=None):
    """Resume a frozen manifest; terminal gaps are records, not media success.

    limit bounds work per invocation, never the declared population. A changed
    manifest requires a new acquisition directory. Run only one worker.
    """
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3 or timeout <= 0 or max_bytes <= 0:
        raise AcquisitionError('INVALID_LIMITS')
    if limit is not None and (type(limit) is not int or limit <= 0):
        raise AcquisitionError('INVALID_LIMIT')
    requested_root = Path(root).absolute()
    if requested_root.is_symlink() or any(p.is_symlink() and str(p) not in ('/tmp','/var') for p in requested_root.parents):
        raise AcquisitionError('OUTPUT_ROOT_SYMLINK')
    root = requested_root.resolve(); root.mkdir(parents=True, exist_ok=True)
    for name in ('.worker.lock', 'acquisition.sqlite', 'summary.json', 'media', 'resolver'):
        if (root/name).is_symlink():
            raise AcquisitionError('OUTPUT_SYMLINK')
    binding = stable_hash({'manifest': manifest, 'network': network, 'roots': [str(Path(p).resolve()) for p in media_roots],
                           'hosts': list(allowed_hosts), 'max_bytes': max_bytes, 'timeout': timeout, 'max_attempts': max_attempts, 'reserve_bytes':reserve_bytes,'cache_bytes':cache_bytes,'resolver_executable':resolver_executable,'resolver_sha256':resolver_sha256})
    lock = (root / '.worker.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise AcquisitionError('WORKER_ALREADY_RUNNING') from None
    db = sqlite3.connect(root / 'acquisition.sqlite', timeout=5)
    db.row_factory = sqlite3.Row
    try:
        db.executescript('CREATE TABLE IF NOT EXISTS binding (digest TEXT PRIMARY KEY);'
                         'CREATE TABLE IF NOT EXISTS items (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE, state TEXT, artifact TEXT, sha256 TEXT, record_path TEXT, record_sha256 TEXT);'
                         'CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, reel_id TEXT, route_hash TEXT, route TEXT, attempt INTEGER, state TEXT, error TEXT, started REAL, finished REAL);')
        old = db.execute('SELECT digest FROM binding').fetchone()
        if old and old[0] != binding:
            raise AcquisitionError('NEW_MANIFEST_REQUIRES_NEW_RUN')
        db.execute('INSERT OR IGNORE INTO binding VALUES (?)', (binding,))
        entries = manifest['entries']
        ids, codes = set(), set()
        pilot_codes = manifest.get('pilot_codes')
        if pilot_codes is not None and (not isinstance(pilot_codes,list) or not pilot_codes or len(pilot_codes)!=len(set(pilot_codes))):
            raise AcquisitionError('INVALID_PILOT_SCOPE')
        import re
        for entry in entries:
            rid, code = entry['reel_id'], entry['code']
            if not isinstance(rid, str) or not rid or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', code) or rid in ids or code in codes:
                raise AcquisitionError('INVALID_IDENTITY')
            ids.add(rid); codes.add(code)
            db.execute('INSERT OR IGNORE INTO items (reel_id,code,state,artifact,sha256) VALUES (?,?,?,?,?)', (rid, code, 'DEFERRED_PILOT' if pilot_codes is not None and code not in pilot_codes else 'NOT_ATTEMPTED', None, None))
        if pilot_codes is not None and not set(pilot_codes).issubset(codes):
            raise AcquisitionError('PILOT_CODE_OUTSIDE_CORPUS')
        if target_ids is not None and (not isinstance(target_ids,list) or not target_ids or not set(target_ids).issubset(ids) or len(target_ids)!=len(set(target_ids))):
            raise AcquisitionError('TARGET_OUTSIDE_MANIFEST')
        db.commit()
        db.execute("UPDATE attempts SET state='FAILED',error='WORKER_INTERRUPTED',finished=? WHERE state='RUNNING'", (time.time(),))
        db.commit()
        processed = 0
        for entry in entries:
            row = db.execute('SELECT * FROM items WHERE reel_id=?', (entry['reel_id'],)).fetchone()
            if row['state'] == 'OBSERVED':
                pointer = root / row['artifact']
                if not pointer.resolve().is_relative_to(root) or not pointer.is_file() or digest(pointer) != row['sha256']:
                    raise AcquisitionError('COMPLETED_MEDIA_CHANGED')
                record_path = root / row['record_path']
                if not record_path.resolve().is_relative_to(root) or record_path.is_symlink() or digest(record_path) != row['record_sha256']:
                    raise AcquisitionError('COMPLETED_PROVENANCE_CHANGED')
                record = json.loads(record_path.read_text())
                ev = record.get('acquisition_provenance', {}).get('resolver_evidence')
                if ev:
                    p = root / ev['path']
                    if not p.resolve().is_relative_to(root) or p.is_symlink() or digest(p) != ev['sha256']:
                        raise AcquisitionError('RESOLVER_EVIDENCE_CHANGED')
                continue
            if row['state'] not in ('NOT_ATTEMPTED', 'RETRYABLE'):
                continue
            if target_ids is not None and entry['reel_id'] not in target_ids:
                continue
            if limit is not None and processed >= limit:
                break
            used = sum(p.stat().st_size for p in (root/'media').glob('*.mp4')) if (root/'media').exists() else 0
            if shutil.disk_usage(root).free < reserve_bytes+max_bytes or used+max_bytes > cache_bytes:
                raise AcquisitionError('STORAGE_BUDGET_STOP')
            processed += 1
            if progress:
                progress({'processed': processed, 'population': len(entries)})
            rid, code = entry['reel_id'], entry['code']
            if (root/(code+'.media.json')).is_symlink():
                raise AcquisitionError('OUTPUT_SYMLINK')
            if entry.get('quarantine_reasons'):
                db.execute('UPDATE items SET state=? WHERE reel_id=?', ('IDENTITY_QUARANTINED', rid)); db.commit(); continue
            sources = entry.get('sources', [])
            final = 'NO_SOURCE_LOCATOR' if not sources else 'UNAVAILABLE'
            for source in sources:
                route = source.get('route'); rh = stable_hash(source)
                count = db.execute('SELECT COUNT(*) FROM attempts WHERE reel_id=? AND route_hash=?', (rid, rh)).fetchone()[0]
                if count >= max_attempts:
                    continue
                started = time.time(); staging = None; provenance = {}
                cursor = db.execute('INSERT INTO attempts VALUES (NULL,?,?,?,?,?,?,?,?)', (rid, rh, route, count+1, 'RUNNING', None, started, None))
                attempt_id = cursor.lastrowid
                db.commit()
                try:
                    folder = root / 'media'; folder.mkdir(exist_ok=True)
                    if folder.is_symlink():
                        raise AcquisitionError('OUTPUT_SYMLINK')
                    fd, temp = tempfile.mkstemp(prefix=code+'-', suffix='.partial', dir=folder)
                    os.close(fd); staging = Path(temp); staging.unlink()
                    if route == 'existing_media':
                        source_path = Path(source['path']).resolve()
                        if not any(source_path.is_relative_to(Path(p).resolve()) for p in media_roots):
                            raise AcquisitionError('SOURCE_OUTSIDE_ALLOWLIST')
                        if source_path.stat().st_size > max_bytes:
                            raise AcquisitionError('DOWNLOAD_SIZE_LIMIT')
                        if digest(source_path) != source['sha256']:
                            raise AcquisitionError('SOURCE_HASH_CHANGED')
                        shutil.copyfile(source_path, staging)
                        if digest(staging) != source['sha256']:
                            raise AcquisitionError('SOURCE_CHANGED_DURING_COPY')
                    elif route in ('cached_hiker_url', 'explicit_url'):
                        if not network:
                            raise AcquisitionError('NETWORK_DISABLED')
                        provenance['download'] = download(source['url'], staging, allowed_hosts=allowed_hosts, max_bytes=max_bytes, timeout=timeout)
                    elif route == 'public_reel':
                        if not network:
                            raise AcquisitionError('NETWORK_DISABLED')
                        from .public_media import resolve_public
                        evidence_root = root / 'resolver' / code / str(count+1)
                        resolved = resolve_public(code, evidence_root, executable=resolver_executable, expected_sha256=resolver_sha256)
                        if resolved['state'] != 'RESOLVED':
                            raise AcquisitionError(resolved['state'])
                        ev = evidence_root / resolved['evidence']
                        provenance['resolver_evidence'] = {'path':str(ev.relative_to(root)), 'sha256':digest(ev)}
                        provenance['download'] = download(resolved['sources'][0]['url'], staging, allowed_hosts=allowed_hosts, max_bytes=max_bytes, timeout=timeout)
                    else:
                        raise AcquisitionError('UNSUPPORTED_ROUTE')
                    data = probe_fn(staging); sha = digest(staging)
                    target = folder / (code + '.mp4')
                    if target.is_symlink():
                        raise AcquisitionError('OUTPUT_SYMLINK')
                    if target.exists():
                        if digest(target) != sha:
                            raise AcquisitionError('TARGET_COLLISION')
                        staging.unlink()
                    else:
                        staging.replace(target)
                    record = {'schema': 'm2.acquired-media.v1', 'media_id': code, 'reel_id': rid, 'observation_state': 'OBSERVED',
                              'source_pointer': str(target.relative_to(root)), 'sha256': sha, 'route': route, 'source_route_hash': rh,
                              'review_state': 'NOT_REVIEWED', 'speech_state': 'UNKNOWN', 'acquisition_provenance':provenance, **data}
                    record_path = root / (code+'-attempt-'+str(attempt_id)+'.media.json')
                    if record_path.exists() or record_path.is_symlink():
                        raise AcquisitionError('RECORD_COLLISION')
                    write_json(record_path, record)
                    db.execute('UPDATE items SET state=?,artifact=?,sha256=?,record_path=?,record_sha256=? WHERE reel_id=?', ('OBSERVED', str(target.relative_to(root)), sha, record_path.name, digest(record_path), rid))
                    db.execute('UPDATE attempts SET state=?,error=?,finished=? WHERE id=?', ('OBSERVED', None, time.time(), attempt_id))
                    final = 'OBSERVED'; db.commit(); break
                except (AcquisitionError, StudioError, OSError, ValueError, KeyError) as exc:
                    error = str(exc) if isinstance(exc, (AcquisitionError, StudioError)) else type(exc).__name__
                    retryable = error in ('NETWORK_FAILURE', 'DNS_UNAVAILABLE', 'DOWNLOAD_TIMEOUT', 'HTTP_429', 'HTTP_500', 'HTTP_502', 'HTTP_503')
                    if retryable and count+1 < max_attempts:
                        final = 'RETRYABLE'
                    db.execute('UPDATE attempts SET state=?,error=?,finished=? WHERE id=?', ('FAILED', error, time.time(), attempt_id))
                    db.commit()
                finally:
                    if staging:
                        staging.unlink(missing_ok=True)
            if final != 'OBSERVED':
                db.execute('UPDATE items SET state=? WHERE reel_id=?', (final, rid)); db.commit()
        states = {x[0]: x[1] for x in db.execute('SELECT state,COUNT(*) FROM items GROUP BY state')}
        result = {'schema': 'm2.acquisition-summary.v1', 'manifest_binding': binding, 'population': len(entries), 'states': states,
                  'processed_this_invocation': processed, 'hikerapi_calls': 0, 'asr_executed': False,
                  'network_enabled': network, 'complete_media_coverage': states.get('OBSERVED', 0) == len(entries) and bool(entries)}
        write_json(root / 'summary.json', result)
        return result
    finally:
        db.close()
        lock.close()
