"""Provider-disabled M2 Signal-to-Studio vertical slice."""

from .engine import (
    FORMULA_REGISTRY,
    AdapterResult,
    DisabledProviderAdapter,
    M2Error,
    build_studio_package,
    canonical_hash,
    import_golden_cohort,
    import_registered_sources,
    normalize_metric_snapshots,
    robust_score_records,
    run_vertical_slice,
    validate_daily_route_collection,
)

__all__ = [
    "FORMULA_REGISTRY",
    "AdapterResult",
    "DisabledProviderAdapter",
    "M2Error",
    "build_studio_package",
    "canonical_hash",
    "import_golden_cohort",
    "import_registered_sources",
    "normalize_metric_snapshots",
    "robust_score_records",
    "run_vertical_slice",
    "validate_daily_route_collection",
]
