"""Explicit opt-in media hook after a completed partner-server replay/export."""
import json
import re
from pathlib import Path

from .media_manifest import build_manifest
from .media_acquisition import stable_hash
from .corpus_media import CorpusMediaDispatcher
from .media_transcription import validate_model_bundle
from m2_studio.media import digest


def _safe(path):
    path = Path(path).absolute()
    if path.is_symlink() or any(p.is_symlink() and str(p) not in {'/tmp', '/var'} for p in path.parents):
        raise ValueError('MEDIA_JOB_SYMLINK')
    return path


def execute_media_job(config_path, reels_path, job_root, *, max_items=None):
    """Freeze inputs once, then invoke the same serial worker used locally.

    The caller must already have completed its replay/export. This does not
    collect counters, call HikerAPI, invoke semantic agents or project Notion.
    """
    config_path, reels_path, root = map(_safe, (config_path, reels_path, job_root))
    if config_path.stat().st_size > 65536 or reels_path.stat().st_size > 256 * 1024**2:
        raise ValueError('MEDIA_JOB_INPUT_LIMIT')
    cfg = json.loads(config_path.read_text())
    required = {'enabled', 'network', 'hikerapi_enabled', 'private_source_root', 'model_dir', 'python_executable',
                'resolver_executable', 'resolver_sha256', 'rights_receipt'}
    optional = {'cache_roots', 'media_roots', 'cache_bytes', 'reserve_bytes', 'batch_size'}
    if not isinstance(cfg, dict) or not required <= cfg.keys() or cfg.keys() - required - optional:
        raise ValueError('MEDIA_JOB_CONFIG_FIELDS_INVALID')
    if cfg['enabled'] is not True or cfg['network'] is not True or cfg['hikerapi_enabled'] is not False:
        raise ValueError('MEDIA_JOB_EXPLICIT_AUTHORITY_REQUIRED')
    for name in ('model_dir', 'python_executable', 'resolver_executable', 'resolver_sha256', 'rights_receipt'):
        if not isinstance(cfg[name], str) or not cfg[name].strip():
            raise ValueError('MEDIA_JOB_CONFIG_VALUE_INVALID')
    for name in ('cache_roots', 'media_roots'):
        if not isinstance(cfg.get(name, []), list) or any(not isinstance(p, str) for p in cfg.get(name, [])):
            raise ValueError('MEDIA_JOB_ROOTS_INVALID')
    source_root = _safe(cfg['private_source_root']).resolve()
    if not source_root.is_dir() or source_root in {Path('/'), Path.home(), Path.home() / 'Documents'}:
        raise ValueError('MEDIA_JOB_SOURCE_AREA_INVALID')
    for value in [reels_path, *cfg.get('cache_roots', []), *cfg.get('media_roots', [])]:
        scoped = _safe(value).resolve()
        if not scoped.is_relative_to(source_root):
            raise ValueError('MEDIA_JOB_SOURCE_OUTSIDE_APPROVED_AREA')
    if not re.fullmatch('[a-f0-9]{64}', cfg['resolver_sha256']):
        raise ValueError('MEDIA_JOB_RESOLVER_HASH_INVALID')
    # Keep the venv entrypoint for execution, while binding the dereferenced
    # executable content. This is provenance, not actor authentication.
    python = Path(cfg['python_executable'])
    resolver = Path(cfg['resolver_executable'])
    if not python.is_absolute() or not resolver.is_absolute() or not python.is_file() or not resolver.is_file():
        raise ValueError('MEDIA_JOB_EXECUTABLE_UNAVAILABLE')
    if digest(resolver) != cfg['resolver_sha256']:
        raise ValueError('MEDIA_JOB_RESOLVER_CHANGED')
    runtime = {'python_sha256': digest(python), 'resolver_sha256': digest(resolver),
               'model_bundle_sha256': validate_model_bundle(cfg['model_dir'])['bundle_sha256']}
    source_hash = digest(reels_path)
    binding = {'schema': 'm2.server-media-binding.v1', 'reels_sha256': source_hash,
               'config_sha256': stable_hash(cfg), 'hook_sha256': digest(__file__),
               'runtime': runtime, 'authority_basis': 'explicit operator configuration plus recorded owner scope; filesystem trust boundary'}
    root.mkdir(parents=True, exist_ok=True)
    # The hook lock covers prepare + execution, including configuration reads
    # on resume; the dispatcher also has its own independent process lock.
    import fcntl
    lock_path = _safe(root / '.media-job.lock')
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('MEDIA_JOB_ALREADY_RUNNING') from None
        binding_path, manifest_path = _safe(root / 'binding.json'), _safe(root / 'manifest.private.json')
        if binding_path.exists():
            saved = json.loads(binding_path.read_text())
            if {k: saved.get(k) for k in binding} != binding:
                raise ValueError('MEDIA_JOB_CHANGED_INPUT_REQUIRES_NEW_RUN')
            if not manifest_path.is_file() or digest(manifest_path) != saved.get('manifest_sha256'):
                raise ValueError('MEDIA_JOB_MANIFEST_CHANGED')
            manifest = json.loads(manifest_path.read_text())
        else:
            if manifest_path.exists():
                raise ValueError('MEDIA_JOB_PARTIAL_PREPARE_REQUIRES_RECOVERY')
            rows = [json.loads(line) for line in reels_path.read_text().splitlines() if line.strip()]
            if not rows:
                raise ValueError('MEDIA_JOB_EMPTY_CORPUS')
            if any(not isinstance(row, dict) for row in rows):
                raise ValueError('MEDIA_JOB_CANONICAL_ROW_INVALID')
            for row in rows:
                reasons = row.get('quarantine_reasons', [])
                if not isinstance(reasons, list) or any(
                        not isinstance(reason, str) or not reason.strip() for reason in reasons):
                    raise ValueError('MEDIA_JOB_QUARANTINE_REASONS_INVALID')
            manifest = build_manifest(rows, [Path(p) for p in cfg.get('cache_roots', [])],
                                      [Path(p) for p in cfg.get('media_roots', [])])
            if len(manifest['entries']) != len(rows):
                raise ValueError('MEDIA_JOB_POPULATION_MISMATCH')
            for entry, source in zip(manifest['entries'], rows):
                entry['research_quarantine_reasons'] = list(source.get('quarantine_reasons', []))
                if not entry.get('quarantine_reasons'):
                    entry['sources'].append({'route': 'public_reel', 'source_code': entry['code']})
            if digest(reels_path) != source_hash:
                raise ValueError('MEDIA_JOB_INPUT_CHANGED_DURING_PREPARE')
            with manifest_path.open('x') as f:
                json.dump(manifest, f, indent=2, allow_nan=False); f.write('\n')
            binding['manifest_sha256'] = digest(manifest_path)
            with binding_path.open('x') as f:
                json.dump(binding, f, indent=2); f.write('\n')
        dispatcher = CorpusMediaDispatcher(
            manifest, root / 'corpus', manifest_sha256=digest(manifest_path),
            model_dir=Path(cfg['model_dir']), python_executable=cfg['python_executable'],
            media_roots=tuple(Path(p) for p in cfg.get('media_roots', [])),
            rights_receipt=cfg['rights_receipt'], resolver_executable=Path(cfg['resolver_executable']),
            resolver_sha256=cfg['resolver_sha256'], batch_size=cfg.get('batch_size', 8),
            cache_bytes=cfg.get('cache_bytes', 8 * 1024**3),
            reserve_bytes=cfg.get('reserve_bytes', 5 * 1024**3))
        return dispatcher.run(network=True, max_items=max_items)
