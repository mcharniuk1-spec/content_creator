"""Bounded subprocess capture, minimal environment and process-group cleanup."""
import os
import selectors
import shutil
import signal
import subprocess
import time
from pathlib import Path


class ProcessBudgetError(ValueError):
    pass


def terminate_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def bounded_process(args, *, timeout=60, stdout_limit=4*1024*1024, stderr_limit=256*1024, env=None, rss_limit_bytes=None):
    executable = shutil.which(str(args[0]))
    if not executable:
        raise ProcessBudgetError('EXECUTABLE_UNAVAILABLE')
    minimal = {'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin', 'LANG': 'en_US.UTF-8',
               'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2', 'VECLIB_MAXIMUM_THREADS': '2'}
    if env:
        minimal.update(env)
    started = time.monotonic()
    # Preserve a virtual environment's executable path: resolving its symlink
    # selects the base Python and silently drops the isolated dependencies.
    process = subprocess.Popen([str(Path(executable).absolute()), *args[1:]], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=minimal, start_new_session=True)
    selector = selectors.DefaultSelector(); outputs = {'stdout': bytearray(), 'stderr': bytearray()}
    selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
    selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
    limits = {'stdout': stdout_limit, 'stderr': stderr_limit}
    peak_rss=0; checked=0
    try:
        while selector.get_map():
            if rss_limit_bytes is not None and time.monotonic()-checked >= .2 and process.poll() is None:
                measured = subprocess.run(['/bin/ps' if Path('/bin/ps').exists() else '/usr/bin/ps', '-o', 'rss=', '-p', str(process.pid)], capture_output=True, timeout=2, check=False)
                if measured.returncode and process.poll() is None:
                    raise ProcessBudgetError('RSS_MONITOR_UNAVAILABLE')
                if measured.stdout.strip():
                    peak_rss=max(peak_rss,int(measured.stdout.strip())*1024)
                    if peak_rss>rss_limit_bytes:
                        raise ProcessBudgetError('PROCESS_RSS_LIMIT')
                checked=time.monotonic()
            remaining = timeout - (time.monotonic()-started)
            if remaining <= 0:
                raise ProcessBudgetError('PROCESS_TIMEOUT')
            for key, _ in selector.select(min(remaining, .2)):
                chunk = os.read(key.fileobj.fileno(), min(65536, limits[key.data]-len(outputs[key.data])+1))
                if not chunk:
                    selector.unregister(key.fileobj); continue
                outputs[key.data].extend(chunk)
                if len(outputs[key.data]) > limits[key.data]:
                    raise ProcessBudgetError('PROCESS_OUTPUT_LIMIT')
        remaining = timeout - (time.monotonic()-started)
        if remaining <= 0:
            raise ProcessBudgetError('PROCESS_TIMEOUT')
        code = process.wait(timeout=remaining)
        return {'returncode': code, 'stdout': bytes(outputs['stdout']), 'stderr': bytes(outputs['stderr']),
                'elapsed_seconds': time.monotonic()-started, 'sampled_peak_rss_bytes':peak_rss, 'rss_watchdog_limit_bytes':rss_limit_bytes, 'rss_poll_seconds':.2}
    except BaseException:
        terminate_group(process)
        raise
    finally:
        selector.close();process.stdout.close();process.stderr.close()
