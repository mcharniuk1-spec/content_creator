"""Per-invocation allowlisted CONNECT broker for the pinned extractor.

The trusted extractor must honor its explicit --proxy argument. This broker
pins public DNS addresses; it is not an OS sandbox for arbitrary executables.
"""
import select
import socket
import socketserver
import threading
import time
from .media_acquisition import validate_url, public_address


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        client = self.request; client.settimeout(10); remote = None
        try:
            header = b''
            while b'\r\n\r\n' not in header:
                if len(header) >= 8192:
                    return
                part = client.recv(min(1024,8192-len(header)))
                if not part:
                    return
                header += part
            parts = header.split(b'\r\n',1)[0].decode('ascii').split()
            if len(parts) != 3 or parts[0] != 'CONNECT':
                return
            _, host = validate_url('https://'+parts[1]+'/', ('instagram.com','cdninstagram.com','fbcdn.net'))
            remaining = self.server.deadline-time.monotonic()
            if remaining <= 0:
                return
            ip = public_address(host, timeout=min(10,remaining))
            with self.server.guard:
                if len(self.server.routes) >= 12:
                    return
                self.server.routes.append({'host':host,'address':ip})
            remote = socket.create_connection((ip,443),timeout=min(10,remaining))
            client.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            client.setblocking(False);remote.setblocking(False)
            while time.monotonic() < self.server.deadline and not self.server.stopping.is_set():
                ready,_,_=select.select([client,remote],[],[],.2)
                for src in ready:
                    chunk = src.recv(65536)
                    if not chunk:
                        return
                    with self.server.guard:
                        self.server.bytes += len(chunk)
                        if self.server.bytes > 16*1024*1024:
                            self.server.stopping.set();return
                    dest = remote if src is client else client
                    view = memoryview(chunk)
                    while view and time.monotonic()<self.server.deadline:
                        _,writable,_=select.select([], [dest], [], .2)
                        if writable:
                            sent=dest.send(view)
                            if not sent:return
                            view=view[sent:]
        except (OSError,ValueError,UnicodeError):
            return
        finally:
            if remote:remote.close()


class Broker(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 4

    def __init__(self, timeout=60):
        super().__init__(('127.0.0.1',0),Handler)
        self.deadline=time.monotonic()+timeout;self.routes=[];self.bytes=0
        self.guard=threading.Lock();self.stopping=threading.Event()

    def __enter__(self):
        self.thread=threading.Thread(target=self.serve_forever,daemon=True);self.thread.start()
        return self

    def __exit__(self,*args):
        self.stopping.set();self.shutdown();self.server_close();self.thread.join(timeout=2)

    @property
    def url(self):
        return 'http://127.0.0.1:'+str(self.server_address[1])
