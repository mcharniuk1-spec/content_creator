"""Optional, offline OCR of sampled frames; never a speech transcript."""
import json
from pathlib import Path

from m2_studio.media import digest, write_json, safe_path
from .process_budget import bounded_process


def extract_frame_text(frame_root, visual, output, *, executable, executable_sha256):
    root=Path(frame_root).resolve()
    output=Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('OCR_OUTPUT_EXISTS')
    if any(p.is_symlink() and str(p) not in {'/tmp','/var'} for p in output.absolute().parents):
        raise ValueError('OCR_OUTPUT_SYMLINK')
    tool=Path(executable)
    if not tool.is_absolute() or not tool.is_file() or digest(tool)!=executable_sha256:
        raise ValueError('OCR_EXECUTABLE_NOT_BOUND')
    frames=visual.get('sampled_frames',[])
    if not 0<len(frames)<=48:
        raise ValueError('OCR_FRAME_BUDGET')
    paths=[]
    for frame in frames:
        path=safe_path(root,frame['source_pointer'])
        if digest(path)!=frame['sha256']:
            raise ValueError('OCR_FRAME_HASH_CHANGED')
        paths.append(str(path))
    output.mkdir(parents=True)
    request=output/'input.private.json'
    write_json(request,paths)
    process=bounded_process([str(tool),str(request)],timeout=120,stdout_limit=1024**2,
                            stderr_limit=65536,rss_limit_bytes=1024**3)
    raw=output/'raw.private.jsonl';raw.write_bytes(process['stdout'])
    rows=[json.loads(line) for line in process['stdout'].splitlines()]
    if process['returncode'] or len(rows)!=len(frames) or [r.get('index') for r in rows]!=list(range(len(frames))):
        raise ValueError('OCR_OUTPUT_SEQUENCE_INVALID')
    for frame,row in zip(frames,rows):
        row.update(frame_id=frame['frame_id'],timestamp_ms=frame['timestamp_ms'],source_frame_sha256=frame['sha256'])
    observed=sum(r.get('state')=='OBSERVED' for r in rows)
    result={'schema':'m2.frame-ocr.v1','modality':'onscreen_text','is_speech_transcript':False,
            'state':'OBSERVED' if observed==len(rows) else 'PARTIAL' if observed else 'OCR_FAILED',
            'source_media_hash':visual['source_media_hash'],'frames':rows,
            'sampled_frame_count':len(rows),'observed_frame_count':observed,
            'raw_sha256':digest(raw),'input_sha256':digest(request),'executable_sha256':executable_sha256,
            'engine':'apple_vision_local_cpu','review_state':'NOT_REVIEWED',
            'full_video_text_coverage':False,
            'resources':{k:v for k,v in process.items() if k not in {'stdout','stderr'}}}
    write_json(output/'receipt.json',result)
    return result
