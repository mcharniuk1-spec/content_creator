"""Explicit anonymous public Reel URL resolution; no login/cookie import.

This is a directly tested extractor adapter, not an Agent Reach readiness claim.
Full metadata is private evidence. Only allowlisted HTTPS CDN URLs are admitted.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from .media_acquisition import AcquisitionError, validate_url


def sources_from_metadata(code, data, allowed_hosts=('cdninstagram.com', 'fbcdn.net')):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', code):
        raise AcquisitionError('INVALID_CODE')
    if data.get('display_id') != code and data.get('id') != code:
        raise AcquisitionError('EXTRACTOR_IDENTITY_MISMATCH')
    formats = data.get('formats', [])
    if not isinstance(formats, list):
        raise AcquisitionError('INVALID_EXTRACTOR_FORMATS')
    result = []
    seen = set()
    for item in formats:
        if item.get('ext') != 'mp4' or item.get('vcodec') == 'none' or item.get('acodec') == 'none':
            continue  # Separate DASH audio/video requires an explicitly implemented merge route.
        url = item.get('url')
        try:
            validate_url(url, allowed_hosts)
        except AcquisitionError:
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append({'route': 'explicit_url', 'url': url, 'resolver': 'yt_dlp_anonymous',
                       'format_id': str(item.get('format_id')), 'source_code': code})
    return result


def resolve_public(code, evidence_dir, *, executable=None, expected_sha256=None, timeout=60):
    import hashlib
    from .process_budget import bounded_process, ProcessBudgetError
    from .resolver_proxy import Broker
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', code):
        raise AcquisitionError('INVALID_CODE')
    if not executable or not Path(executable).is_absolute() or not expected_sha256:
        raise AcquisitionError('EXTRACTOR_IDENTITY_REQUIRED')
    tool = Path(executable).resolve()
    if not tool.is_file() or hashlib.sha256(tool.read_bytes()).hexdigest()!=expected_sha256:
        raise AcquisitionError('EXTRACTOR_IDENTITY_CHANGED')
    destination = Path(evidence_dir); destination.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise AcquisitionError('OUTPUT_SYMLINK')
    try:
        with tempfile.TemporaryDirectory(dir=destination) as home, Broker(timeout) as broker:
            args = [str(tool), '--ignore-config', '--no-plugin-dirs', '--no-cache-dir', '--skip-download',
                    '--dump-single-json', '--no-playlist', '--socket-timeout', '10', '--retries', '0',
                    '--extractor-retries', '0', '--proxy', broker.url,
                    'https://www.instagram.com/reel/' + code + '/']
            result = bounded_process(args, timeout=timeout, env={'HOME':home,'TMPDIR':home}, rss_limit_bytes=768*1024**2)
            if result['returncode']:
                error=result['stderr'].decode(errors='replace').lower()
                state='AUTH_OR_RATE_OR_UNAVAILABLE' if 'login' in error or 'rate-limit' in error else 'EXTRACTION_FAILED'
                return {'state':state,'sources':[],'code':code,'hikerapi_calls':0}
            if not broker.routes:
                raise AcquisitionError('RESOLVER_PROXY_NOT_USED')
            data=json.loads(result['stdout']);sources=sources_from_metadata(code,data)
            evidence=destination/(code+'.metadata.private.json')
            with evidence.open('xb') as f:f.write(result['stdout'])
            receipt={'state':'RESOLVED' if sources else 'NO_SUPPORTED_MUXED_FORMAT','code':code,'sources':sources,
                     'evidence':evidence.name,'hikerapi_calls':0,'credentials_used':False,'cookies_used':False,
                     'executable_sha256':expected_sha256,'network_policy':'trusted pinned CLI with explicit allowlisted public-DNS CONNECT broker; not arbitrary-code OS sandbox',
                     'network_routes':broker.routes,'network_bytes':broker.bytes,'elapsed_seconds':result['elapsed_seconds']}
            return receipt
    except ProcessBudgetError as exc:
        return {'state':str(exc),'sources':[],'code':code,'hikerapi_calls':0}
    except (OSError,ValueError,TypeError,AttributeError):
        return {'state':'INVALID_EXTRACTOR_OUTPUT','sources':[],'code':code,'hikerapi_calls':0}
