import json
import sqlite3
from pathlib import Path
import pytest
from m2_orchestrator import media_acquisition as m
from m2_orchestrator.public_media import sources_from_metadata


def manifest(path=None):
    source=[] if path is None else [{'route':'existing_media','path':str(path),'sha256':m.digest(path)}]
    return {'entries':[{'reel_id':'instagram:ABC12','code':'ABC12','sources':source,'quarantine_reasons':[]},
                       {'reel_id':'instagram:DEF34','code':'DEF34','sources':[],'quarantine_reasons':[]}]}


def test_full_dispositions_resume_and_tamper(tmp_path):
    source=tmp_path/'input.mp4';source.write_bytes(b'bounded fixture')
    data=manifest(source);root=tmp_path/'out'
    result=m.acquire(data,root,media_roots=[tmp_path],probe_fn=lambda p:{'has_audio':True,'duration_ms':1000})
    assert result['population']==2
    assert result['states']=={'NO_SOURCE_LOCATOR':1,'OBSERVED':1}
    assert m.acquire(data,root,media_roots=[tmp_path],probe_fn=lambda p:pytest.fail('reprobe'))['processed_this_invocation']==0
    (root/'media/ABC12.mp4').write_bytes(b'changed')
    with pytest.raises(m.AcquisitionError,match='COMPLETED_MEDIA_CHANGED'):
        m.acquire(data,root,media_roots=[tmp_path])


def test_failure_ledger_and_no_source_delete(tmp_path):
    source=tmp_path/'input.mp4';source.write_bytes(b'original')
    result=m.acquire(manifest(source),tmp_path/'out',media_roots=[],probe_fn=lambda p:{})
    assert result['states']['UNAVAILABLE']==1
    assert source.read_bytes()==b'original'
    c=sqlite3.connect(tmp_path/'out/acquisition.sqlite')
    assert c.execute('select error from attempts').fetchone()[0]=='SOURCE_OUTSIDE_ALLOWLIST'
    c.close()


def test_manifest_change_requires_new_run(tmp_path):
    m.acquire(manifest(),tmp_path/'out')
    with pytest.raises(m.AcquisitionError,match='NEW_MANIFEST_REQUIRES_NEW_RUN'):
        m.acquire({'entries':[]},tmp_path/'out')


@pytest.mark.parametrize('url',['http://x.cdninstagram.com/a','https://cdninstagram.com.evil.test/a',
                              'https://user:password@cdninstagram.com/a','https://cdninstagram.com:8080/a',
                              'https://127.0.0.1/a','https://cdninstagram.com/a\nInjected'])
def test_url_boundary(url):
    with pytest.raises(m.AcquisitionError):m.validate_url(url,('cdninstagram.com',))


def test_nonpublic_dns(monkeypatch):
    monkeypatch.setattr(m,'bounded_process',lambda *a,**k:{'returncode':0,'stdout':b'["127.0.0.1"]'})
    with pytest.raises(m.AcquisitionError,match='NONPUBLIC_ADDRESS'):m.public_address('cdninstagram.com')


class Response:
    status=200
    def __init__(self,body=b'video',headers=None):self.body=body;self.headers=headers or {};self.fp=None
    def getheader(self,k,default=None):return self.headers.get(k,default)
    def read(self,n):v=self.body[:n];self.body=self.body[n:];return v


class Connection:
    sock=None
    def connect(self):pass
    def __init__(self,response):self.response=response
    def request(self,*a,**k):pass
    def getresponse(self):return self.response
    def close(self):pass


def transport(monkeypatch,response):
    monkeypatch.setattr(m,'public_address',lambda h,**k:'1.1.1.1')
    monkeypatch.setattr(m,'PinnedHTTPS',lambda *a,**k:Connection(response))


def test_download_bound_and_cleanup(tmp_path,monkeypatch):
    transport(monkeypatch,Response(b'toolarge'))
    target=tmp_path/'part'
    with pytest.raises(m.AcquisitionError,match='DOWNLOAD_SIZE_LIMIT'):
        m.download('https://cdninstagram.com/a',target,max_bytes=3)
    assert not target.exists()


def test_existing_target_preserved(tmp_path,monkeypatch):
    transport(monkeypatch,Response())
    target=tmp_path/'part';target.write_bytes(b'owned by user')
    with pytest.raises(m.AcquisitionError):m.download('https://cdninstagram.com/a',target)
    assert target.read_bytes()==b'owned by user'


def test_truncation(tmp_path,monkeypatch):
    transport(monkeypatch,Response(b'abc',{'Content-Length':'5'}))
    with pytest.raises(m.AcquisitionError,match='TRUNCATED_DOWNLOAD'):
        m.download('https://cdninstagram.com/a',tmp_path/'part')
    assert not (tmp_path/'part').exists()


def test_redirect_revalidated(tmp_path,monkeypatch):
    r=Response(headers={'Location':'https://localhost/a'});r.status=302
    transport(monkeypatch,r)
    with pytest.raises(m.AcquisitionError,match='URL_NOT_ALLOWED'):
        m.download('https://cdninstagram.com/a',tmp_path/'part')


def test_public_metadata_identity_and_muxed_filter():
    with pytest.raises(m.AcquisitionError,match='IDENTITY'):
        sources_from_metadata('ABC12',{'display_id':'BAD12'})
    d={'display_id':'ABC12','formats':[{'ext':'mp4','acodec':'none','url':'https://cdninstagram.com/video'},
                                    {'ext':'mp4','url':'https://cdninstagram.com/muxed'},
                                    {'ext':'mp4','url':'file:///etc/passwd'}]}
    assert [x['url'] for x in sources_from_metadata('ABC12',d)]==['https://cdninstagram.com/muxed']
