"""Gated server-only HikerAPI adapter; no collection runs during import.

Official OpenAPI 1.8.1 verified by integrator 2026-09-05 documents GET parameters,
but not the flat response schema. items/max_id/more_available is a legacy contract
candidate. Strict response checks and an explicitly approved pilot are required.
This module has only fixture execution proof; LIVE_SCHEMA_UNVERIFIED.
"""
from __future__ import annotations

import csv
import json
import os
import re
import socket
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode, urlparse

from .engine import canonical, digest, file_hash

ENDPOINT = 'https://api.hikerapi.com/gql/user/clips'
CODE = re.compile(r'[A-Za-z0-9_-]{5,30}')
REQUIRED_KEYS = {'run_id','snapshot_date','accounts','max_pages_per_account','max_requests',
                 'request_timeout_seconds','maximum_cost_usd','request_cost_ceiling_usd',
                 'price_receipt_sha256','earliest_published_epoch_seconds'}


def validate_collection_config(config):
    if set(config) != REQUIRED_KEYS:
        raise ValueError('exact Hiker collection config fields required')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', config['run_id']):
        raise ValueError('unsafe run_id')
    date.fromisoformat(config['snapshot_date'])
    for key in ('max_pages_per_account','max_requests','request_timeout_seconds'):
        if type(config[key]) is not int or not 1 <= config[key] <= (60 if key == 'request_timeout_seconds' else 10000):
            raise ValueError('bounded positive integer required: '+key)
    for key in ('maximum_cost_usd','request_cost_ceiling_usd'):
        n = Decimal(str(config[key]))
        if not n.is_finite() or n <= 0:
            raise ValueError('positive finite declared cost ceiling required')
    if not re.fullmatch('[0-9a-f]{64}',config['price_receipt_sha256']):
        raise ValueError('dated owner-verified price receipt hash required; never assume a tariff')
    if config['earliest_published_epoch_seconds'] is not None and (type(config['earliest_published_epoch_seconds']) is not int or config['earliest_published_epoch_seconds'] < 0):
        raise ValueError('window lower bound must be a nonnegative epoch or null')
    if not isinstance(config['accounts'],list) or not config['accounts']:
        raise ValueError('explicit source account allowlist required')
    users = set()
    for account in config['accounts']:
        if set(account) != {'user_id','username','followers','public_source_authorized'}:
            raise ValueError('exact allowlisted account fields required')
        if not isinstance(account['user_id'],str) or not account['user_id'].isdigit() or not re.fullmatch(r'[A-Za-z0-9_.]{1,30}',account['username']):
            raise ValueError('invalid public account identifier')
        if account['public_source_authorized'] is not True or account['user_id'] in users:
            raise ValueError('account route not authorized or duplicated')
        users.add(account['user_id'])
    return json.loads(canonical(config))


def _approval(config, approval_path, *, media=False, schema_receipt_path=None):
    if approval_path is None:
        raise ValueError('exact approval file required for live Hiker requests')
    approval = json.loads(Path(approval_path).read_text())
    required = {'hikerapi_instagram_reels_collection'} | ({'immediate_media_acquisition'} if media else set())
    if not required <= set(approval.get('scopes',[])) or approval.get('config_sha256') != digest(config):
        raise ValueError('approval scope/config hash mismatch')
    if not approval.get('approved_by') or not approval.get('approval_id') or approval.get('approved') is not True:
        raise ValueError('explicit owner approval identity and event required')
    try:
        expiry = datetime.fromisoformat(approval['expires_at'].replace('Z','+00:00'))
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise ValueError('expired approval')
    except (KeyError,TypeError):
        raise ValueError('explicit timezone-aware approval expiry required')
    # Response schema has not been verified live in this project. A single-request
    # pilot can collect the proof; broader automatic collection awaits that review.
    if schema_receipt_path is None:
        if approval.get('live_schema_probe_approved') is not True or config['max_requests'] > 1:
            raise ValueError('LIVE_SCHEMA_UNVERIFIED: only exact single-request pilot admitted')
    else:
        _verify_live_schema_receipt(schema_receipt_path)
        if approval.get('schema_receipt_sha256') != file_hash(schema_receipt_path):
            raise ValueError('exact schema receipt must be bound by approval')
    return approval


def _verify_live_schema_receipt(path):
    """A reviewed, hash-bound actual response permits a larger server run."""
    path=Path(path)
    receipt=json.loads(path.read_text())
    if receipt.get('endpoint') != ENDPOINT or receipt.get('evidence_source') != 'LIVE' or receipt.get('review_state') != 'APPROVED':
        raise ValueError('live schema receipt endpoint/source/review invalid')
    if not receipt.get('reviewer') or not receipt.get('maker') or receipt['reviewer']==receipt['maker']:
        raise ValueError('independent live schema reviewer required')
    expires=datetime.fromisoformat(receipt['expires_at'].replace('Z','+00:00'))
    if expires.tzinfo is None or expires<=datetime.now(timezone.utc):
        raise ValueError('live schema receipt expired')
    evidence_path=(path.parent/receipt['response_path']).resolve()
    if not evidence_path.is_relative_to(path.parent.resolve()) or not evidence_path.is_file():
        raise ValueError('live schema response path must stay in receipt package')
    if file_hash(evidence_path) != receipt['response_sha256']:
        raise ValueError('live schema response hash mismatch')
    items,_,_=_validate_page(json.loads(evidence_path.read_text()))
    if not items or not any(isinstance(item,dict) and isinstance(item.get('code'),str) for item in items):
        raise ValueError('nonempty representative flat media response required')
    return receipt


class LiveTransport:
    """One request, no redirects, no retries, no credential-bearing error text."""
    def __init__(self):
        key = os.environ.get('HIKER_KEY') or os.environ.get('HIKERAPI_KEY')
        if not key:
            raise ValueError('HIKER_KEY or HIKERAPI_KEY must be injected by server environment')
        self._key = key

    def __call__(self, params, timeout):
        import urllib.error
        import urllib.request
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        request = urllib.request.Request(ENDPOINT+'?'+urlencode(params),
                                         headers={'x-access-key':self._key,'accept':'application/json'})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=timeout) as response:
                body = response.read(25*1024*1024+1)
                if len(body) > 25*1024*1024:
                    raise RuntimeError('HIKER_RESPONSE_SIZE_LIMIT')
                return json.loads(body)
        except (TimeoutError,socket.timeout):
            raise TimeoutError('HIKER_TIMEOUT_OUTCOME_UNKNOWN') from None
        except Exception:
            raise RuntimeError('HIKER_TRANSPORT_OUTCOME_UNKNOWN') from None


def _private_write(path, payload):
    data = (canonical(payload)+'\n').encode()
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('immutable Hiker artifact conflict')
        return
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())


def _validate_page(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('items'),list) or type(payload.get('more_available')) is not bool:
        raise ValueError('UNVERIFIED_FLAT_RESPONSE_SCHEMA')
    cursor = payload.get('max_id')
    if payload['more_available'] and (not isinstance(cursor,str) or not cursor or not payload['items']):
        raise ValueError('PAGINATION_INCONSISTENT')
    return payload['items'],cursor,payload['more_available']


def _native_row(item, account):
    if not isinstance(item,dict):
        return None,'NON_OBJECT_MEDIA',[]
    if isinstance(item.get('media'),dict):
        item=item['media']
    code=item.get('code')
    if not isinstance(code,str) or not CODE.fullmatch(code):
        return None,'INVALID_REEL_CODE',[]
    owner=item.get('user') or {}
    if not isinstance(owner,dict) or (owner.get('username') is not None and not isinstance(owner.get('username'),str)):
        return None,'MALFORMED_CREATOR_IDENTITY',[]
    if owner and (str(owner.get('pk',account['user_id'])) != account['user_id'] or owner.get('username',account['username']).lower() != account['username'].lower()):
        return None,'CREATOR_ATTRIBUTION_CONFLICT',[]
    if item.get('product_type') not in (None,'clips'):
        return None,'NON_REEL_MEDIA',[]
    caption=item.get('caption') or {}
    text=caption.get('text') if isinstance(caption,dict) else None
    row={'code':code,'user':account['username'],'url':'https://www.instagram.com/reel/'+code+'/',
         'play':item.get('play_count'),'like':item.get('like_count'),'comment':item.get('comment_count'),
         'reshare':item.get('reshare_count'),'save':item.get('save_count'),'duration_s':item.get('video_duration'),
         'ts':item.get('taken_at'),'caption':text,'snapshot_followers':account['followers']}
    refs=[]
    for version in item.get('video_versions') or []:
        if isinstance(version,dict) and isinstance(version.get('url'),str):
            parsed=urlparse(version['url'])
            if parsed.scheme=='https' and parsed.netloc and not parsed.username and not parsed.password:
                refs.append(version['url'])
    return row,None,refs


def collect(config, private_dir, *, transport=None, execute_live=False, approval_path=None, schema_receipt_path=None, on_media=None):
    """Collect to a protected run directory, or replay fixtures with injected transport.

    Injected transport is explicitly FIXTURE mode. Live calls require execute_live,
    exact approval, environment-only auth, and the current single-request pilot cap.
    Raw pages/checkpoints are immutable. Any uncertain dispatched request is blocked
    on restart until human reconciliation; no billable request is silently retried.
    on_media(code, refs, context) is an approved immediate callback; this module does
    not download media or make claims about callback output quality.
    """
    cfg=validate_collection_config(config)
    if transport is None:
        if not execute_live:
            raise ValueError('live collection disabled; explicit server-only execution required')
        _approval(cfg,approval_path,media=on_media is not None,schema_receipt_path=schema_receipt_path)
        transport=LiveTransport()
        mode='LIVE_REVIEWED_SCHEMA' if schema_receipt_path else 'LIVE_PILOT'
    elif execute_live:
        raise ValueError('cannot label injected fixture transport as live')
    else:
        mode='FIXTURE'
    root=Path(private_dir)/cfg['run_id']
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(root,0o700)
    lock=root/'collector.lock'
    try:
        lock_fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        raise ValueError('collector lock exists; inspect interrupted run before recovery') from None
    os.close(lock_fd)
    try:
        for folder in ('pages','dispatch','checkpoints','media-refs'):
            (root/folder).mkdir(exist_ok=True,mode=0o700)
        binding=root/'execution-binding.json'
        if not binding.exists() and any((root/'dispatch').glob('*.json')):
            raise ValueError('LEGACY_CACHE_WITHOUT_EXECUTION_MODE_BINDING')
        _private_write(binding,{'config_sha256':digest(cfg),'execution_mode':mode,'endpoint':ENDPOINT})
        _private_write(root/'config.json',cfg)
        results=[]; all_rows=[]; quarantines=[]; window_excluded=0
        dispatched=len(list((root/'dispatch').glob('*.json')))
        cap=Decimal(str(cfg['maximum_cost_usd'])); unit=Decimal(str(cfg['request_cost_ceiling_usd']))
        for account in cfg['accounts']:
            token=digest(account['user_id'])[:16]
            cursor=None; seen=set(); stop='PAGE_CAP_REACHED'; rows=[]
            for page_index in range(cfg['max_pages_per_account']):
                key=f'{token}-{page_index:05d}'
                dispatch_path=root/'dispatch'/(key+'.json')
                page_path=root/'pages'/(key+'.json')
                checkpoint=root/'checkpoints'/(key+'.json')
                params={'user_id':account['user_id'],'flat':'true','sort_by_views':'false'}
                if cursor is not None:
                    params['max_id']=cursor
                if dispatch_path.exists():
                    dispatch=json.loads(dispatch_path.read_text())
                    if dispatch.get('params')!=params or dispatch.get('config_sha256')!=digest(cfg) or dispatch.get('execution_mode')!=mode:
                        raise ValueError('CACHE_DISPATCH_BINDING_MISMATCH')
                elif page_path.exists() or checkpoint.exists():
                    raise ValueError('ORPHAN_CACHE_WITHOUT_DISPATCH')
                if page_path.exists() and checkpoint.exists():
                    payload=json.loads(page_path.read_text())
                    state=json.loads(checkpoint.read_text())
                    if state.get('state') != 'PAGE_COMMITTED':
                        stop=state['state']; break
                    if state.get('page_sha256')!=digest(payload):
                        raise ValueError('CACHE_PAGE_HASH_MISMATCH')
                    cached_items,cached_cursor,cached_more=_validate_page(payload)
                    if state.get('next_cursor')!=cached_cursor or state.get('more_available') is not cached_more or state.get('items_n')!=len(cached_items):
                        raise ValueError('CACHE_CHECKPOINT_PAGINATION_MISMATCH')
                elif dispatch_path.exists():
                    stop='UNCERTAIN_PREVIOUS_DISPATCH_REQUIRES_RECONCILIATION'; break
                else:
                    if dispatched>=cfg['max_requests'] or (dispatched+1)*unit>cap:
                        stop='BUDGET_BLOCKED_BEFORE_DISPATCH'; break
                    # Authority is checked immediately before EACH billable dispatch.
                    # Revocation/expiry during a long run cannot inherit admission.
                    if mode!='FIXTURE':
                        _approval(cfg,approval_path,media=on_media is not None,schema_receipt_path=schema_receipt_path)
                    _private_write(dispatch_path,{'params':params,'config_sha256':digest(cfg),'request_index':dispatched+1,
                                                  'reserved_upper_cost_usd':str(unit),'execution_mode':mode})
                    dispatched+=1
                    try:
                        payload=transport(params,cfg['request_timeout_seconds'])
                    except TimeoutError:
                        stop='TIMEOUT_OUTCOME_UNKNOWN'
                        _private_write(checkpoint,{'state':stop,'charge_state':'UNVERIFIED_RESERVED','automatic_retry':False})
                        break
                    except Exception:
                        stop='TRANSPORT_OUTCOME_UNKNOWN'
                        _private_write(checkpoint,{'state':stop,'charge_state':'UNVERIFIED_RESERVED','automatic_retry':False})
                        break
                    _private_write(page_path,payload)
                try:
                    items,next_cursor,more=_validate_page(payload)
                except ValueError:
                    stop='RESPONSE_SCHEMA_BLOCKED'
                    if not checkpoint.exists():
                        _private_write(checkpoint,{'state':stop,'automatic_retry':False})
                    break
                page_refs=[]
                for item in items:
                    row,reason,refs=_native_row(item,account)
                    if reason:
                        quarantines.append({'account_token':token,'page':page_index,'reason':reason,'item_sha256':digest(item)})
                        continue
                    ts=row['ts']; lower=cfg['earliest_published_epoch_seconds']
                    # A lower publication bound filters observations. Pagination still
                    # runs to exhaustion/cap because pinned/out-of-order items exist.
                    if lower is not None and isinstance(ts,(int,float)) and ts<lower:
                        window_excluded+=1; continue
                    rows.append(row)
                    if refs:
                        page_refs.append({'code':row['code'],'urls':refs,'expiry_state':'UNKNOWN_ACQUIRE_IMMEDIATELY'})
                        if on_media is not None and not checkpoint.exists():
                            try:
                                if mode!='FIXTURE':
                                    _approval(cfg,approval_path,media=True,schema_receipt_path=schema_receipt_path)
                                on_media(row['code'],refs,{'config_sha256':digest(cfg),'source_page_sha256':digest(payload),'execution_mode':mode})
                            except Exception:
                                quarantines.append({'account_token':token,'page':page_index,'reason':'MEDIA_CALLBACK_FAILED_NO_PROVIDER_RETRY','item_sha256':digest(item)})
                if page_refs:
                    _private_write(root/'media-refs'/(key+'.json'),page_refs)
                if not checkpoint.exists():
                    _private_write(checkpoint,{'state':'PAGE_COMMITTED','page_sha256':digest(payload),'next_cursor':next_cursor,
                                             'more_available':more,'items_n':len(items),'charge_state':'UNVERIFIED_RESERVED'})
                if not more:
                    stop='SOURCE_EXHAUSTED'; break
                if next_cursor in seen:
                    stop='CURSOR_LOOP_BLOCKED'; break
                seen.add(next_cursor); cursor=next_cursor
            all_rows.extend(rows)
            results.append({'account_token':token,'observation_rows':len(rows),'stop_reason':stop,
                            'source_exhausted':stop=='SOURCE_EXHAUSTED','completeness_state':'COMPLETE_DECLARED_ROUTE' if stop=='SOURCE_EXHAUSTED' else 'PARTIAL'})
        export=root/'export'; export.mkdir(exist_ok=True,mode=0o700)
        fields=['code','user','url','play','like','comment','reshare','save','duration_s','ts','caption','snapshot_followers']
        import io
        def csv_data(columns,values):
            f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n',quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(values);return f.getvalue()
        # Complete reruns replay committed pages and must regenerate identical data.
        payloads={'reels.csv':csv_data(fields,all_rows),
                  'accounts.csv':csv_data(['username','followers','media_count','category','biography'],[
                      {'username':a['username'],'followers':a['followers'],'media_count':None,'category':None,'biography':None} for a in cfg['accounts']]),
                  'snapshot.json':canonical({'taken':cfg['snapshot_date'],'accounts':len(cfg['accounts']),
                                           'capture_time_state':'DATE_ONLY','collection_route':'HIKER_GQL_CLIPS_FLAT_CANDIDATE'})+'\n'}
        for name,text in payloads.items():
            p=export/name
            if p.exists() and p.read_text()!=text:
                raise ValueError('export changed during resume; use a new authorized run')
            if not p.exists():
                fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'w') as f:f.write(text)
        summary={'schema_version':'signal-hiker-collection.v1','execution_mode':mode,'live_schema_state':'LIVE_SCHEMA_VERIFIED_BY_BOUND_RECEIPT' if mode=='LIVE_REVIEWED_SCHEMA' else 'LIVE_SCHEMA_UNVERIFIED',
                 'config_sha256':digest(cfg),'accounts':results,'observations':len(all_rows),'window_excluded':window_excluded,
                 'quarantines':quarantines,'dispatched_requests':dispatched,'reserved_cost_upper_bound_usd':str(dispatched*unit),
                 'actual_provider_charge_usd':None,'billing_state':'UNVERIFIED_RESERVATION_ONLY',
                 'automatic_retries':0,'external_calls':0 if mode=='FIXTURE' else dispatched,
                 'source_exhausted_accounts':sum(x['source_exhausted'] for x in results),
                 'stage_state':'PASS_WITH_LIMITATIONS' if all(x['source_exhausted'] for x in results) else 'BLOCKED_EVIDENCE'}
        _private_write(root/('receipt-'+digest(summary)+'.json'),summary)
        return summary
    finally:
        lock.unlink()
