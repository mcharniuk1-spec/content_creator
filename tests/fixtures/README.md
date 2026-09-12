# tests/fixtures

No binary fixtures are checked in here. `tests/test_local_pipeline.py` generates its
12-second synthetic test video at run time (via the same `imageio_ffmpeg` binary the
pipeline itself uses — see the `synthetic_video` fixture) rather than shipping an mp4,
so there's nothing to keep in sync with ffmpeg version changes and nothing binary in
the diff.

If a future test needs a static fixture (e.g. a canned `clips*.json` cache response
shaped like HikerAPI's), put it here as plain JSON.
