#!/usr/bin/env python3
"""Build a full private media manifest; no network, HikerAPI or model calls."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from m2_orchestrator.media_manifest import build_manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reels',type=Path,required=True)
    p.add_argument('--cache-root',type=Path,action='append',default=[])
    p.add_argument('--media-root',type=Path,action='append',default=[])
    p.add_argument('--url-map',type=Path)
    p.add_argument('--public-fallback',action='store_true')
    p.add_argument('--pilot-code',action='append')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.reels.stat().st_size>256*1024*1024:p.error('Reel input exceeds size limit')
    rows=[json.loads(line) for line in a.reels.read_text().splitlines() if line.strip()]
    if a.url_map and a.url_map.stat().st_size>32*1024*1024:p.error('URL map exceeds size limit')
    mapping=json.loads(a.url_map.read_text()) if a.url_map else None
    result=build_manifest(rows,a.cache_root,a.media_root,mapping)
    if a.public_fallback:
        for row in result['entries']:
            if not row.get('quarantine_reasons'):
                row['sources'].append({'route':'public_reel','source_code':row['code']})
    if a.pilot_code:
        if not set(a.pilot_code).issubset({r['code'] for r in result['entries']}):p.error('Pilot identity outside corpus')
        result['pilot_codes']=sorted(set(a.pilot_code))
    result['public_fallback_configured']=a.public_fallback
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write('\n')
    print(json.dumps({'population':len(result['entries']),'public_fallback_configured':a.public_fallback,'pilot_count':len(a.pilot_code) if a.pilot_code else None,'network_calls':0}))


if __name__=='__main__':main()
