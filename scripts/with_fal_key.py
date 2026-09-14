"""Launch a command with FAL_KEY injected from the owner-only, ignored local file.

No shell evaluation, no output of values, no network or provider activation.
Usage: python scripts/with_fal_key.py -- command arg ...
"""
import ast
import os
import pathlib
import re
import sys


def load_key(path):
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError('credential file must be a regular owner-only file')
    lines = [s.strip() for s in path.read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
    if len(lines) != 1:
        raise ValueError('expected one credential field')
    match = re.fullmatch(r'(?:falai|FAL_KEY)\s*[:=]\s*(.*)', lines[0])
    if not match:
        raise ValueError('unsupported credential format')
    value = match[1].strip()
    if value.startswith(('"', "'")):
        value = ast.literal_eval(value)
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise ValueError('credential missing or invalid')
    return value


def main():
    args = sys.argv[1:]
    if not args or args[0] != '--' or len(args) < 2:
        print(__doc__)
        return 2
    try:
        key = os.environ.get('FAL_KEY') or load_key(pathlib.Path(__file__).resolve().parents[1] / 'key_fal.yaml')
    except Exception:
        print('FAL credential unavailable or invalid; no command launched.', file=sys.stderr)
        return 2
    env = dict(os.environ, FAL_KEY=key)
    os.execvpe(args[1], args[1:], env)


if __name__ == '__main__':
    raise SystemExit(main())
