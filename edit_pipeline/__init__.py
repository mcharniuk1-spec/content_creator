"""Local-first hybrid video editing pipeline.

The JSON EDL is the canonical control artifact. FFmpeg/ffprobe are the only
media execution tools in this package; OTIO and Resolve are optional adapters.
"""

from .core import (
    PipelineError,
    analyze_video,
    build_edl,
    build_fixture_case,
    export_otio,
    probe_media,
    render_edl,
    validate_case,
    validate_edl,
)

__all__ = [
    "PipelineError",
    "analyze_video",
    "build_edl",
    "build_fixture_case",
    "export_otio",
    "probe_media",
    "render_edl",
    "validate_case",
    "validate_edl",
]
