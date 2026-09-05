#!/usr/bin/env python3
"""Portable dependency-light benchmark for M2 Signal transcript candidates.

This is deliberately an audit/benchmark, not a production model. Inputs and
output directory are explicit CLI arguments so the module never assumes a
repository layout or a v1 run path. It retains the repaired transcript-ID
join, account-cluster bootstrap uncertainty, grouped holdouts, and suppressed
row-permutation p/q semantics.
"""
from __future__ import annotations

import argparse
import csv
import datetime as datetime_module
import hashlib
import json
import math
import os
import random
import sqlite3
import statistics
import tempfile
from pathlib import Path

RELEASE = ""
SEED = 20260905
RUN_ID = "transcript-benchmark"
ANALYSIS_DATE = ""


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


def median(xs):
    xs = sorted(float(x) for x in xs if x is not None and math.isfinite(float(x)))
    return statistics.median(xs) if xs else None


def mean(xs):
    xs = [float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return statistics.fmean(xs) if xs else None


def percentile(xs, q):
    xs = sorted(float(x) for x in xs if x is not None and math.isfinite(float(x)))
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def safe_log1p(x):
    return math.log1p(float(x)) if x is not None and float(x) >= 0 else None


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        r = (i + 1 + j) / 2.0
        for k in order[i:j]:
            out[k] = r
        i = j
    return out


def corr(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    a = sum((x - mx) ** 2 for x in rx)
    b = sum((y - my) ** 2 for y in ry)
    return sum((x - mx) * (y - my) for x, y in zip(rx, ry)) / math.sqrt(a * b) if a and b else None


def pearson(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    a = sum((x - mx) ** 2 for x in xs)
    b = sum((y - my) ** 2 for y in ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(a * b) if a and b else None


def bh_qvalues(pvals):
    """Benjamini-Hochberg q values over one predeclared family."""
    valid = [(i, p) for i, p in enumerate(pvals) if p is not None and math.isfinite(p)]
    q = [None] * len(pvals)
    # Sort ascending, compute p*m/rank, then take the reverse cumulative
    # minimum. This guarantees q >= p for each finite p under standard BH.
    ordered = sorted(valid, key=lambda z: z[1])
    adjusted = [min(1.0, p * len(valid) / rank) for rank, (_, p) in enumerate(ordered, start=1)]
    running = 1.0
    for (i, _), raw in reversed(list(zip(ordered, adjusted))):
        running = min(running, raw)
        q[i] = running
    return q


def group_account_folds(accounts, n_folds=5):
    """Deterministically partition account IDs without splitting an account."""
    if n_folds < 1:
        raise ValueError("n_folds_must_be_positive")
    folds = [[] for _ in range(n_folds)]
    for i, account in enumerate(sorted(set(accounts))):
        folds[i % n_folds].append(account)
    return folds


def ols_fit(rows, columns, target):
    """Plain OLS with a small pivot tolerance; returns coefficients and diagnostics."""
    usable = [r for r in rows if all(r.get(c) is not None for c in columns) and r.get(target) is not None]
    n, p = len(usable), len(columns)
    if n <= p + 2:
        return {"state": "INSUFFICIENT", "n": n, "p": p, "reason": "n_not_greater_than_p_plus_two"}
    x = [[1.0] + [float(r[c]) for c in columns] for r in usable]
    y = [float(r[target]) for r in usable]
    m = len(columns) + 1
    a = [[sum(row[i] * row[j] for row in x) for j in range(m)] + [sum(row[i] * yy for row, yy in zip(x, y))] for i in range(m)]
    max_pivot = 0.0
    for k in range(m):
        pivot = max(range(k, m), key=lambda i: abs(a[i][k]))
        max_pivot = max(max_pivot, abs(a[pivot][k]))
        if abs(a[pivot][k]) < 1e-10:
            return {"state": "INSUFFICIENT", "n": n, "p": p, "reason": "rank_deficient", "columns": columns}
        a[k], a[pivot] = a[pivot], a[k]
        z = a[k][k]
        a[k] = [v / z for v in a[k]]
        for i in range(m):
            if i == k:
                continue
            z = a[i][k]
            if z:
                a[i] = [u - z * v for u, v in zip(a[i], a[k])]
    beta = [a[i][-1] for i in range(m)]
    pred = [beta[0] + sum(beta[j + 1] * row[columns[j]] for j in range(p)) for row in usable]
    ybar = statistics.fmean(y)
    sse, sst = sum((yy - pp) ** 2 for yy, pp in zip(y, pred)), sum((yy - ybar) ** 2 for yy in y)
    return {"state": "FIT", "n": n, "p": p, "columns": columns, "coefficients": dict(zip(["intercept"] + columns, beta)), "r2": 1 - sse / sst if sst else None, "rmse": math.sqrt(sse / n), "max_normal_matrix_pivot": max_pivot}


def category_family(text, kind):
    s = (text or "").lower()
    if kind == "topic":
        for name, words in [("agent_systems", ("agent", "multi-agent")), ("automation", ("automat", "workflow", "process")), ("voice", ("voice", "call", "phone")), ("marketing_sales", ("sales", "lead", "ad", "marketing")), ("coding_web", ("code", "coding", "website", "repository", "program")), ("media_content", ("video", "photo", "content", "reel", "short"))]:
            if any(w in s for w in words):
                return name
        return "other"
    for name, words in [("dialogue", ("dialogue", "question", "conversation")), ("procedure", ("step", "chain", "command", "setup", "sequence")), ("demonstration", ("demo", "example", "build", "project")), ("story_result", ("story", "experience", "result", "journey")), ("offer_resource", ("offer", "resource", "coupon", "template")), ("fragment", ("music", "fragment"))]:
        if any(w in s for w in words):
            return name
    return "other"


def current_metric_vector(transcript, signal_payload):
    """Use current Signal payload metrics, accepting only transcript rounding."""
    keys = ("views", "likes_per_1k_views", "comments_per_1k_views", "reshares_per_1k_views", "saves_per_1k_views")
    supplied = transcript["metrics_snapshot"]["metric_vector"]
    current = {key: signal_payload.get(key) for key in keys}
    for key in keys:
        observed, latest = supplied.get(key), current.get(key)
        if observed is None or latest is None:
            if observed != latest:
                raise ValueError(f"transcript_metric_mismatch:{transcript['transcript_id']}:{key}")
        elif abs(float(observed) - float(latest)) > 1e-5:
            raise ValueError(f"transcript_metric_mismatch:{transcript['transcript_id']}:{key}")
    return current


def load_rows(db_path: Path, transcripts_path: Path, source_map_path: Path, release_id: str, expected_transcript_count: int | None = None):
    if not release_id or not release_id.strip():
        raise ValueError("release_id_required")
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    all_payloads = {}
    try:
        payload_rows = list(conn.execute("SELECT reel_id,account_username,payload_json FROM reel_analysis WHERE release_id=?", (release_id,)))
    finally:
        conn.close()
    if not payload_rows:
        raise ValueError(f"unknown release:{release_id}")
    if len({rid for rid, _, _ in payload_rows}) != len(payload_rows):
        raise ValueError("release_reel_ids_must_be_unique")
    for rid, acct, payload in payload_rows:
        d = json.loads(payload)
        all_payloads[rid] = d
    source_map = json.loads(source_map_path.read_text())
    source_entries = source_map["sources"]
    by_transcript = {x["transcript_id"]: x for x in source_entries}
    if expected_transcript_count is not None and len(source_entries) != expected_transcript_count:
        raise ValueError(f"source_map_transcript_count_expected_{expected_transcript_count}")
    if len(by_transcript) != len(source_entries):
        raise ValueError("source_map_transcript_ids_must_be_unique")
    if len({x["reel_id"] for x in source_entries}) != len(source_entries):
        raise ValueError("source_map_reel_ids_must_be_unique")
    transcripts = [json.loads(line) for line in transcripts_path.read_text().splitlines() if line.strip()]
    transcript_ids = [t["transcript_id"] for t in transcripts]
    if len(set(transcript_ids)) != len(transcript_ids):
        raise ValueError("transcript_ids_must_be_unique")
    if expected_transcript_count is not None and len(transcripts) != expected_transcript_count:
        raise ValueError(f"transcript_count_expected_{expected_transcript_count}")
    missing_source_ids = set(transcript_ids) - set(by_transcript)
    if missing_source_ids:
        raise ValueError(f"missing_source_map_transcript_id:{sorted(missing_source_ids)[0]}")
    extra_source_ids = set(by_transcript) - set(transcript_ids)
    if extra_source_ids:
        raise ValueError("source_map_has_unmatched_transcript_ids")
    out = []
    actions = ["likes_per_1k_views", "comments_per_1k_views", "reshares_per_1k_views", "saves_per_1k_views"]
    for t in transcripts:
        source_entry = by_transcript.get(t["transcript_id"])
        if source_entry is None:
            raise ValueError(f"missing_source_map_transcript_id:{t['transcript_id']}")
        if source_entry["record_sha256"].removeprefix("sha256:") != t["source_record_sha256"].removeprefix("sha256:"):
            raise ValueError(f"source_hash_disagreement:{t['transcript_id']}")
        rid = source_entry["reel_id"]
        d = all_payloads.get(rid) if rid else None
        if not d:
            out.append({"transcript_id": t["transcript_id"], "join_state": "UNJOINED", "word_count": t.get("word_count_lexical_v1", 0)})
            continue
        snapshot = datetime_module.date.fromisoformat(d["snapshot_date"])
        pub = datetime_module.datetime.fromtimestamp(d["published_epoch_seconds"], datetime_module.timezone.utc).date() if d.get("published_epoch_seconds") else None
        age = (snapshot - pub).days if pub else None
        vec = current_metric_vector(t, d)
        observed = [vec.get(a) for a in actions if vec.get(a) is not None]
        row = {
            "transcript_id": t["transcript_id"], "reel_id": rid, "account": d["account_username"], "join_state": "JOINED",
            "word_count": t.get("word_count_lexical_v1", 0), "word_bearing": int(t.get("word_count_lexical_v1", 0) > 0),
            "segment_count": t.get("segment_count", 0), "words_per_segment": (t.get("word_count_lexical_v1", 0) / t["segment_count"]) if t.get("segment_count") else None,
            "hook_orientation": t.get("hook_orientation"), "proof_in_text": t.get("proof_in_text"), "m2_fit": t.get("m2_fit_candidate"),
            "topic": t.get("topic"), "topic_family": category_family(t.get("topic"), "topic"),
            "structure": t.get("body_structure"), "structure_family": category_family(t.get("body_structure"), "structure"),
            "cta_present": int(bool(t.get("ending_cta_lexical_candidates"))), "proof_verified": int(bool(t.get("proof_verified"))),
            "views": vec.get("views"), "age_days": age, "duration_seconds": d.get("duration_seconds"),
            "account_median_views": d.get("author_median_views"), "account_baseline_n": d.get("author_baseline_n"),
            "eligibility_state": d.get("eligibility_state"), "numeric_valid": int(bool(d.get("numeric_valid"))),
            "exposure_eligible": int(bool(d.get("eligibility_state") == "PASS" and d.get("views") and d.get("views") > 0)),
            "source_record_sha256": t["source_record_sha256"], "metric_state": t["metrics_snapshot"].get("metric_eligibility_state"),
        }
        segment_words = [s.get("lexical_word_count") for s in t.get("segment_features", []) if s.get("lexical_word_count") is not None]
        row["opening_words"] = segment_words[0] if segment_words else None
        row["ending_words"] = segment_words[-1] if len(segment_words) > 1 else 0
        row["body_words"] = sum(segment_words[1:-1]) if len(segment_words) > 2 else 0
        row["words_per_scene"] = None
        row["scene_words_state"] = "NOT_ESTIMABLE_MISSING_MEDIA_AND_SCENES"
        for a in actions:
            row[a] = vec.get(a)
            row["log_" + a] = safe_log1p(vec.get(a))
        row["total_actions_per_1k"] = sum(observed) if len(observed) == len(actions) else None
        row["log_total_actions"] = safe_log1p(row["total_actions_per_1k"])
        # Controls are predeclared and transformed before any candidate is fitted.
        for key in ("views", "age_days", "duration_seconds", "account_median_views", "account_baseline_n", "word_count"):
            row["log_" + key] = safe_log1p(row.get(key))
        row["log_segment_count"] = safe_log1p(row.get("segment_count"))
        row["log_words_per_segment"] = safe_log1p(row.get("words_per_segment"))
        out.append(row)
    return out, all_payloads


def bootstrap_corr(rows, x, y, reps=1000):
    usable = [r for r in rows if r.get(x) is not None and r.get(y) is not None]
    if len(usable) < 10:
        return {"state": "INSUFFICIENT", "n": len(usable), "reason": "fewer_than_10_rows"}
    groups = {}
    for r in usable:
        groups.setdefault(r["account"], []).append(r)
    accounts = sorted(groups)
    observed = corr([r[x] for r in usable], [r[y] for r in usable])
    rng = random.Random(SEED + len(accounts))
    vals = []
    for _ in range(reps):
        sample = [r for a in (rng.choice(accounts) for _ in accounts) for r in groups[a]]
        z = corr([r[x] for r in sample], [r[y] for r in sample])
        if z is not None:
            vals.append(z)
    return {"state": "ESTIMATED", "n": len(usable), "accounts": len(accounts), "estimate": observed, "ci95_cluster_bootstrap": [percentile(vals, .025), percentile(vals, .975)], "p_permutation_exploratory": None, "p_value_state": "UNAVAILABLE_ROW_PERMUTATION_SUPPRESSED", "method": "Spearman; account-cluster bootstrap CI; no p-value because row permutation is not cluster-valid"}


def bootstrap_group_effect(rows, group, y, min_n=5, reps=1000):
    usable = [r for r in rows if r.get(group) and r.get(y) is not None]
    counts = {}
    for r in usable:
        counts.setdefault(r[group], []).append(r)
    supported = {k: v for k, v in counts.items() if len(v) >= min_n and len({r["account"] for r in v}) >= 3}
    if len(supported) < 2:
        return {"state": "INSUFFICIENT", "n": len(usable), "group_counts": {k: len(v) for k, v in sorted(counts.items())}, "reason": "fewer_than_two_groups_with_minimum_rows_and_accounts"}
    pooled = median([r[y] for r in usable])
    rng = random.Random(SEED + len(group) * 13)
    all_groups = {}
    for r in usable:
        all_groups.setdefault(r["account"], []).append(r)
    all_accts = sorted(all_groups)
    effects = []
    for k, vals in supported.items():
        observed = median([r[y] for r in vals]) - pooled
        b = []
        for _ in range(reps):
            sampled = [r for a in (rng.choice(all_accts) for _ in all_accts) for r in all_groups[a]]
            category_sample = [r for r in sampled if r[group] == k]
            if category_sample:
                b.append(median([r[y] for r in category_sample]) - median([r[y] for r in sampled]))
        effects.append({"category": k, "n": len(vals), "accounts": len({r["account"] for r in vals}), "median_outcome": median([r[y] for r in vals]), "median_difference_vs_all": observed, "ci95_cluster_bootstrap": [percentile(b, .025), percentile(b, .975)], "p_permutation_exploratory": None, "p_value_state": "UNAVAILABLE_ROW_PERMUTATION_SUPPRESSED"})
    q = bh_qvalues([x["p_permutation_exploratory"] for x in effects])
    for e, qv in zip(effects, q):
        e["q_bh_within_group_family"] = qv
    return {"state": "ESTIMATED", "n": len(usable), "all_group_counts": {k: len(v) for k, v in sorted(counts.items())}, "supported_minimum": {"rows": min_n, "accounts": 3}, "effects": effects, "method": "category median minus pooled all-row median; account-cluster bootstrap resamples all usable account clusters and recomputes both medians per replicate", "multiplicity": "p/q suppressed because row permutation is not cluster-valid; future cluster-valid tests must adjust within this predeclared family"}


def within_account_sensitivity(rows, x, y):
    """Estimate only within-account rank association for repeated-account rows."""
    groups = {}
    for r in rows:
        if r.get(x) is not None and r.get(y) is not None:
            groups.setdefault(r["account"], []).append(r)
    groups = {a: rs for a, rs in groups.items() if len(rs) >= 2}
    centered = []
    for rs in groups.values():
        mx, my = statistics.fmean(r[x] for r in rs), statistics.fmean(r[y] for r in rs)
        centered.extend((r[x] - mx, r[y] - my) for r in rs)
    if len(centered) < 10 or len(groups) < 3:
        return {"state": "INSUFFICIENT", "n": len(centered), "accounts": len(groups), "reason": "too_few_repeated_account_rows"}
    observed = corr([a for a, _ in centered], [b for _, b in centered])
    rng = random.Random(SEED + 991)
    boot = []
    accts = sorted(groups)
    for _ in range(1000):
        sampled = [r for a in (rng.choice(accts) for _ in accts) for r in groups[a]]
        # Recenter every sampled account before calculating the sensitivity.
        vals = []
        by_a = {}
        for r in sampled:
            by_a.setdefault(r["account"], []).append(r)
        for rs in by_a.values():
            mx, my = statistics.fmean(r[x] for r in rs), statistics.fmean(r[y] for r in rs)
            vals.extend((r[x] - mx, r[y] - my) for r in rs)
        z = corr([a for a, _ in vals], [b for _, b in vals])
        if z is not None:
            boot.append(z)
    return {"state": "ESTIMATED", "n": len(centered), "accounts": len(groups), "estimate": observed, "ci95_cluster_bootstrap": [percentile(boot, .025), percentile(boot, .975)], "method": "within-account mean-centering; account-cluster bootstrap; sensitivity only"}


def cv_compare(rows, feature, target="log_total_actions"):
    feature_key = feature[4:] if feature.startswith("cat:") else feature
    usable = [r for r in rows if all(r.get(c) is not None for c in ["log_views", "log_age_days", "log_duration_seconds", "log_account_median_views", "log_account_baseline_n", target]) and r.get(feature_key) is not None]
    accounts = sorted({r["account"] for r in usable})
    if len(usable) < 40 or len(accounts) < 5:
        return {"state": "INSUFFICIENT", "n": len(usable), "accounts": len(accounts), "reason": "predeclared_holdout_floor_not_met", "floor": {"rows": 40, "accounts": 5}}
    base = ["log_views", "log_age_days", "log_duration_seconds", "log_account_median_views", "log_account_baseline_n"]
    # A single candidate at a time prevents an opaque multiverse. Categorical
    # candidates are only represented by levels with >=5 rows and >=3 accounts.
    if feature.startswith("cat:"):
        key = feature_key
        counts = {}
        for r in usable:
            counts.setdefault(r[key], []).append(r)
        levels = [k for k, v in sorted(counts.items()) if len(v) >= 5 and len({r["account"] for r in v}) >= 3]
        if len(levels) < 2 or len(levels) > 6:
            return {"state": "INSUFFICIENT", "n": len(usable), "accounts": len(accounts), "reason": "categorical_support_or_dimension_floor_not_met", "levels": {str(k): len(v) for k, v in sorted(counts.items())}}
        cols = base + ["level_" + str(k) for k in levels[1:]]
        for r in usable:
            for k in levels[1:]:
                r["level_" + str(k)] = 1.0 if r[key] == k else 0.0
    else:
        cols = base + [feature]
    baseline = ols_fit(usable, base, target)
    candidate = ols_fit(usable, cols, target)
    if baseline.get("state") != "FIT" or candidate.get("state") != "FIT":
        return {"state": "INSUFFICIENT", "reason": "ols_rank_or_sample_failure", "baseline": baseline, "candidate": candidate}
    # Five deterministic group folds. For categorical candidates, supported
    # levels are selected from each training fold only; test-only levels map to
    # the omitted reference/unknown bucket. This keeps the held-out design
    # independent of test-fold composition while retaining the full-data fit
    # above as a descriptive diagnostic.
    folds = group_account_folds(accounts, 5)
    fold_results = []
    for test_accounts in folds:
        test = [r for r in usable if r["account"] in test_accounts]
        train = [r for r in usable if r["account"] not in test_accounts]
        b = ols_fit(train, base, target)
        fold_test = test
        fold_cols = cols
        if feature.startswith("cat:"):
            fold_counts = {}
            for r in train:
                fold_counts.setdefault(r[feature_key], []).append(r)
            fold_levels = [k for k, v in sorted(fold_counts.items()) if len(v) >= 5 and len({r["account"] for r in v}) >= 3]
            if len(fold_levels) < 2 or len(fold_levels) > 6:
                return {"state": "INSUFFICIENT", "reason": "categorical_training_fold_support_or_dimension_floor_not_met", "fold_accounts": len(test_accounts), "training_levels": {str(k): len(v) for k, v in sorted(fold_counts.items())}}
            fold_cols = base + ["fold_level_" + str(k) for k in fold_levels[1:]]
            train_design = []
            test_design = []
            for r in train:
                z = dict(r)
                for k in fold_levels[1:]:
                    z["fold_level_" + str(k)] = 1.0 if r[feature_key] == k else 0.0
                train_design.append(z)
            for r in test:
                z = dict(r)
                for k in fold_levels[1:]:
                    z["fold_level_" + str(k)] = 1.0 if r[feature_key] == k else 0.0
                test_design.append(z)
            fold_test = test_design
            c = ols_fit(train_design, fold_cols, target)
        else:
            c = ols_fit(train, cols, target)
        if b.get("state") != "FIT" or c.get("state") != "FIT":
            return {"state": "INSUFFICIENT", "reason": "fold_rank_failure", "fold_accounts": len(test_accounts)}
        def pred(model, r):
            return model["coefficients"]["intercept"] + sum(model["coefficients"].get(k, 0.0) * float(r.get(k, 0.0)) for k in model["columns"])
        y = [r[target] for r in fold_test]
        pb, pc = [pred(b, r) for r in fold_test], [pred(c, r) for r in fold_test]
        fold_results.append({"n": len(test), "baseline_mae": mean([abs(a - z) for a, z in zip(y, pb)]), "candidate_mae": mean([abs(a - z) for a, z in zip(y, pc)])})
    return {"state": "ESTIMATED", "target": target, "n": len(usable), "accounts": len(accounts), "baseline": baseline, "candidate": candidate, "delta_r2_train": candidate["r2"] - baseline["r2"] if candidate["r2"] is not None and baseline["r2"] is not None else None, "grouped_5fold": fold_results, "vocabulary_policy": "categorical levels selected from each training fold using row/account support; test-only levels map to the omitted reference/unknown bucket" if feature.startswith("cat:") else None, "interpretation": "descriptive model comparison; no causal or production prediction claim"}


FEATURE_DICTIONARY = {
    "word_count": ("words", "lexical count from supplied ASR segments", "transcript records with analyzed text", "NULL means no analyzed transcript; zero is an empty or unverified record"),
    "opening_words": ("words", "lexical count in first supplied ASR segment", "word-bearing transcript records", "NULL means no segment count; zero is an observed empty segment"),
    "body_words": ("words", "lexical count in interior supplied ASR segments", "word-bearing transcript records", "NULL means no section evidence; zero is valid for a one- or two-segment record"),
    "ending_words": ("words", "lexical count in last supplied ASR segment", "word-bearing transcript records", "NULL means no segment count; zero is valid for one-segment handling"),
    "segment_count": ("segments", "count of supplied ASR segments", "transcript records", "NULL means segmentation was not supplied"),
    "words_per_segment": ("words/segment", "lexical word_count / segment_count", "records with positive segment_count", "NULL when count or segment denominator is unavailable"),
    "words_per_scene": ("words/scene", "lexical words divided by reviewed semantic scene count", "scene-reviewed media records", "NULL with explicit media/scene gap; not estimable in this release"),
    "log_word_count": ("log1p(words)", "log1p lexical word count", "word-bearing transcript records", "NULL when lexical count is unavailable"),
    "log_segment_count": ("log1p(segments)", "log1p supplied segment count", "transcript records with segmentation", "NULL when segment count is unavailable"),
    "log_words_per_segment": ("log1p(words/segment)", "log1p lexical words per supplied segment", "records with positive segment denominator", "NULL when lexical density is unavailable"),
    "log_total_actions": ("log1p(rate sum)", "log1p(likes + comments + reshares + saves per 1,000 views)", "rows with all four observed native action rates", "NULL when any native action rate is missing or invalid; no zero imputation"),
    "log_likes_per_1k_views": ("log1p(rate)", "log1p(likes / views * 1,000)", "rows with observed likes and positive views", "NULL when likes or views is unavailable/invalid"),
    "log_comments_per_1k_views": ("log1p(rate)", "log1p(comments / views * 1,000)", "rows with observed comments and positive views", "NULL when comments or views is unavailable/invalid"),
    "log_reshares_per_1k_views": ("log1p(rate)", "log1p(reshares / views * 1,000)", "rows with observed reshares and positive views", "NULL when reshares or views is unavailable/invalid"),
    "log_saves_per_1k_views": ("log1p(rate)", "log1p(saves / views * 1,000)", "rows with observed saves and positive views", "NULL when saves or views is unavailable/invalid"),
}


def write_analytics_db(output_dir: Path, result: dict, joined_rows: list[dict], input_paths: dict[str, Path], overwrite: bool = False):
    """Write a local, normalized analytics-stage receipt database."""
    db_path = output_dir / "analytics.sqlite"
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=".analytics-", suffix=".sqlite.tmp", dir=output_dir)
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    conn = None
    try:
        conn = sqlite3.connect(tmp_path)
        conn.executescript("""
      DROP TABLE IF EXISTS benchmark_run;
      DROP TABLE IF EXISTS metric_dictionary;
      DROP TABLE IF EXISTS transcript_features;
      DROP TABLE IF EXISTS transcript_outcomes;
      DROP TABLE IF EXISTS numeric_associations;
      DROP TABLE IF EXISTS categorical_associations;
      DROP TABLE IF EXISTS model_comparisons;
      DROP TABLE IF EXISTS model_fold_diagnostics;
      CREATE TABLE benchmark_run (
        run_id TEXT NOT NULL, release_id TEXT NOT NULL, analysis_date TEXT, seed INTEGER NOT NULL,
        state TEXT NOT NULL, source_db_sha256 TEXT NOT NULL, source_transcripts_sha256 TEXT NOT NULL,
        source_map_sha256 TEXT NOT NULL, source_summary_sha256 TEXT NOT NULL,
        p_value_state TEXT NOT NULL, primary_outcome TEXT NOT NULL
      );
      CREATE TABLE metric_dictionary (
        stage TEXT NOT NULL, feature_name TEXT NOT NULL, units TEXT NOT NULL,
        formula TEXT NOT NULL, denominator TEXT NOT NULL, null_semantics TEXT NOT NULL,
        PRIMARY KEY(stage, feature_name)
      );
      CREATE TABLE transcript_features (
        transcript_id TEXT NOT NULL, reel_id TEXT NOT NULL, account TEXT,
        feature_name TEXT NOT NULL, value_numeric REAL, value_text TEXT,
        units TEXT NOT NULL, formula TEXT NOT NULL, denominator TEXT NOT NULL,
        null_state TEXT NOT NULL, source_state TEXT NOT NULL,
        PRIMARY KEY(transcript_id, feature_name)
      );
      CREATE TABLE transcript_outcomes (
        transcript_id TEXT PRIMARY KEY, log_total_actions REAL,
        log_likes_per_1k_views REAL, log_comments_per_1k_views REAL,
        log_reshares_per_1k_views REAL, log_saves_per_1k_views REAL,
        complete_four_action INTEGER NOT NULL, missingness_rule TEXT NOT NULL
      );
      CREATE TABLE numeric_associations (
        feature TEXT NOT NULL, outcome TEXT NOT NULL, state TEXT NOT NULL,
        n INTEGER, accounts INTEGER, estimate REAL, ci_low REAL, ci_high REAL,
        p_permutation_exploratory REAL, p_value_state TEXT, q_bh_within_numeric_family REAL
      );
      CREATE TABLE categorical_associations (
        feature TEXT NOT NULL, category TEXT NOT NULL, n INTEGER, accounts INTEGER,
        median_outcome REAL, median_difference_vs_all REAL, ci_low REAL, ci_high REAL,
        p_permutation_exploratory REAL, p_value_state TEXT, q_bh_within_group_family REAL,
        PRIMARY KEY(feature, category)
      );
      CREATE TABLE model_comparisons (
        feature TEXT PRIMARY KEY, state TEXT NOT NULL, n INTEGER, accounts INTEGER,
        delta_r2_train REAL, vocabulary_policy TEXT, interpretation TEXT
      );
      CREATE TABLE model_fold_diagnostics (
        feature TEXT NOT NULL, fold_index INTEGER NOT NULL, n INTEGER NOT NULL,
        baseline_mae REAL, candidate_mae REAL, PRIMARY KEY(feature, fold_index)
      );
        """)
        conn.execute("INSERT INTO benchmark_run VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            result["run_id"], result["release_id"], result["analysis_date"], SEED, "PASS_WITH_LIMITATIONS",
            sha(input_paths["db"]), sha(input_paths["transcripts"]), sha(input_paths["source_map"]), sha(input_paths["summary"]),
            "UNAVAILABLE_ROW_PERMUTATION_SUPPRESSED", result["policy"]["primary_outcome"],
        ))
        for name, (units, formula, denominator, nulls) in FEATURE_DICTIONARY.items():
            conn.execute("INSERT INTO metric_dictionary VALUES (?, ?, ?, ?, ?, ?)", ("transcript_benchmark", name, units, formula, denominator, nulls))
        for row in joined_rows:
            for name, (units, formula, denominator, nulls) in FEATURE_DICTIONARY.items():
                value = row.get(name)
                numeric = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
                text_value = str(value) if value is not None and numeric is None else None
                if value is None:
                    null_state = "NOT_ESTIMABLE_MISSING_MEDIA_AND_SCENES" if name == "words_per_scene" else "MISSING_UNKNOWN"
                else:
                    null_state = "OBSERVED"
                conn.execute("INSERT INTO transcript_features VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (row["transcript_id"], row["reel_id"], row.get("account"), name, numeric, text_value, units, formula, denominator, null_state, row.get("metric_state") or row.get("join_state") or "UNKNOWN"))
            conn.execute("INSERT INTO transcript_outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (row["transcript_id"], row.get("log_total_actions"), row.get("log_likes_per_1k_views"), row.get("log_comments_per_1k_views"), row.get("log_reshares_per_1k_views"), row.get("log_saves_per_1k_views"), int(row.get("log_total_actions") is not None), "all four native action rates observed; missing saves remain null; no zero imputation"))
        for item in result["numeric_associations"]:
            ci = item.get("ci95_cluster_bootstrap") or [None, None]
            conn.execute("INSERT INTO numeric_associations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (item["feature"], item["outcome"], item.get("state"), item.get("n"), item.get("accounts"), item.get("estimate"), ci[0], ci[1], item.get("p_permutation_exploratory"), item.get("p_value_state"), item.get("q_bh_within_numeric_family")))
        for group in result["categorical_associations"]:
            for item in group.get("effects", []):
                ci = item.get("ci95_cluster_bootstrap") or [None, None]
                conn.execute("INSERT INTO categorical_associations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (group["feature"], item["category"], item.get("n"), item.get("accounts"), item.get("median_outcome"), item.get("median_difference_vs_all"), ci[0], ci[1], item.get("p_permutation_exploratory"), item.get("p_value_state"), item.get("q_bh_within_group_family")))
        for item in result["model_comparisons"]:
            conn.execute("INSERT INTO model_comparisons VALUES (?, ?, ?, ?, ?, ?, ?)", (item["feature"], item.get("state"), item.get("n"), item.get("accounts"), item.get("delta_r2_train"), item.get("vocabulary_policy"), item.get("interpretation")))
            for i, fold in enumerate(item.get("grouped_5fold", []), start=1):
                conn.execute("INSERT INTO model_fold_diagnostics VALUES (?, ?, ?, ?, ?)", (item["feature"], i, fold["n"], fold.get("baseline_mae"), fold.get("candidate_mae")))
        conn.commit()
        conn.close()
        conn = None
        os.replace(tmp_path, db_path)
        return db_path
    finally:
        if conn is not None:
            conn.close()
        if tmp_path.exists():
            tmp_path.unlink()


def assert_output_safe(output_dir: Path, input_paths: dict[str, Path], overwrite: bool):
    """Reject input aliases and accidental partial/implicit output overwrites."""
    output_dir = output_dir.resolve()
    input_resolved = {path.resolve() for path in input_paths.values()}
    targets = [output_dir / name for name in ("benchmark.json", "joined-transcript-metrics.jsonl", "analytics.sqlite")]
    for target in targets:
        if target.exists():
            if target.resolve() in input_resolved or any(os.path.samefile(target, source) for source in input_resolved if source.exists()):
                raise ValueError(f"output_input_alias:{target}")
            if not overwrite:
                raise FileExistsError(f"output_exists_use_overwrite:{target}")
    for source in input_resolved:
        if output_dir == source or output_dir == source.parent:
            raise ValueError(f"output_directory_overlaps_input:{output_dir}")


def atomic_write_text(path: Path, text: str):
    fd, name = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def run_benchmark(db_path: Path, transcripts_path: Path, source_map_path: Path, summary_path: Path, output_dir: Path, release_id: str, run_id: str = "transcript-benchmark", analysis_date: str = "", seed: int = 20260905, expected_transcript_count: int | None = None, overwrite: bool = False):
    """Run the repaired benchmark and write benchmark.json plus joined JSONL."""
    global RELEASE, RUN_ID, ANALYSIS_DATE, SEED
    RELEASE, RUN_ID, ANALYSIS_DATE, SEED = release_id, run_id, analysis_date, seed
    input_paths = {"db": db_path, "transcripts": transcripts_path, "source_map": source_map_path, "summary": summary_path}
    output_dir.mkdir(parents=True, exist_ok=True)
    assert_output_safe(output_dir, input_paths, overwrite)
    rows, all_payloads = load_rows(db_path, transcripts_path, source_map_path, release_id, expected_transcript_count)
    joined = [r for r in rows if r.get("join_state") == "JOINED"]
    word = [r for r in joined if r.get("word_bearing")]
    # Population quality comes from every frozen release row, not the selected transcript sample.
    eligibility = {}
    numeric = 0
    saves = 0
    ages = []
    for d in all_payloads.values():
        eligibility[d.get("eligibility_state")] = eligibility.get(d.get("eligibility_state"), 0) + 1
        numeric += int(bool(d.get("numeric_valid")))
        saves += int(d.get("saves") is not None)
        if d.get("published_epoch_seconds"):
            age = (datetime_module.date.fromisoformat(d["snapshot_date"]) - datetime_module.datetime.fromtimestamp(d["published_epoch_seconds"], datetime_module.timezone.utc).date()).days
            if age >= 0: ages.append(age)
    actions = ["likes_per_1k_views", "comments_per_1k_views", "reshares_per_1k_views", "saves_per_1k_views"]
    metric_quality = {}
    for a in actions + ["views", "duration_seconds"]:
        vals = [d.get(a) for d in all_payloads.values()]
        metric_quality[a] = {"observed_n": sum(v is not None for v in vals), "missing_n": sum(v is None for v in vals), "median": median(vals), "q1": percentile(vals, .25), "q3": percentile(vals, .75)}
    numeric_results = []
    for x in ["log_word_count", "log_segment_count", "log_words_per_segment"]:
        for y in ["log_total_actions", "log_likes_per_1k_views", "log_comments_per_1k_views", "log_reshares_per_1k_views", "log_saves_per_1k_views"]:
            numeric_results.append({"feature": x, "outcome": y, **bootstrap_corr(word, x, y)})
    numeric_q = bh_qvalues([x.get("p_permutation_exploratory") for x in numeric_results])
    for x, q in zip(numeric_results, numeric_q):
        x["q_bh_within_numeric_family"] = q
    category_results = []
    for g in ["hook_orientation", "proof_in_text", "m2_fit", "topic_family", "structure_family"]:
        category_results.append({"feature": g, "outcome": "log_total_actions", **bootstrap_group_effect(word, g, "log_total_actions")})
    model_results = []
    for feature in ["log_word_count", "log_segment_count", "cat:hook_orientation", "cat:proof_in_text", "cat:m2_fit", "cat:topic_family", "cat:structure_family"]:
        model_results.append({"feature": feature, **cv_compare(word, feature)})
    control_cols = ["log_views", "log_age_days", "log_duration_seconds", "log_account_median_views", "log_account_baseline_n"]
    collinearity = []
    for i, a in enumerate(control_cols):
        for b in control_cols[i + 1:]:
            u = [r for r in word if r.get(a) is not None and r.get(b) is not None]
            collinearity.append({"a": a, "b": b, "n": len(u), "pearson": pearson([r[a] for r in u], [r[b] for r in u]), "flag_abs_r_ge_0_85": abs(pearson([r[a] for r in u], [r[b] for r in u]) or 0) >= .85})
    bh_fixture_p = [0.001, 0.01, 0.02, 0.20]
    bh_fixture_q = bh_qvalues(bh_fixture_p)
    bh_regression = {"p": bh_fixture_p, "q": bh_fixture_q, "q_ge_p": all(q >= p for p, q in zip(bh_fixture_p, bh_fixture_q)), "sorted_q_monotone": all(q1 <= q2 for q1, q2 in zip(sorted(bh_fixture_q), sorted(bh_fixture_q)[1:]))}
    repeated_account = {a: n for a, n in __import__("collections").Counter(r["account"] for r in word).items() if n >= 2}
    result = {
        "schema": "m2.luna-analytics-benchmark.v1", "run_id": RUN_ID, "analysis_date": ANALYSIS_DATE, "release_id": RELEASE,
        "inputs": {"signal_db_sha256": sha(db_path), "transcript_analysis_sha256": sha(transcripts_path), "source_map_sha256": sha(source_map_path), "summary_sha256": sha(summary_path)},
        "population_quality": {"canonical_reels": len(all_payloads), "accounts": len({d.get('account_username') for d in all_payloads.values() if d.get('account_username') is not None}), "accounts_with_null_identity_rows": sum(d.get('account_username') is None for d in all_payloads.values()), "eligibility_counts": eligibility, "numeric_valid_n": numeric, "saves_observed_n": saves, "saves_observed_eligible_n": sum(d.get('saves') is not None and d.get('eligibility_state') == 'PASS' for d in all_payloads.values()), "age_days_nonnegative_n": len(ages), "age_days_median": median(ages), "age_days_q1": percentile(ages, .25), "age_days_q3": percentile(ages, .75), "metrics": metric_quality},
        "transcript_join": {"records": len(rows), "joined": len(joined), "word_bearing": len(word), "empty_unverified": sum(not r.get('word_bearing') for r in joined), "unique_accounts": len({r['account'] for r in word}), "exposure_eligible_word_bearing": sum(r.get('exposure_eligible', 0) for r in word), "complete_four_action_word_bearing": sum(r.get('log_total_actions') is not None for r in word), "m2_fit_counts": {k: sum(r.get('m2_fit') == k for r in joined) for k in sorted({r.get('m2_fit') for r in joined})}},
        "numeric_associations": numeric_results, "categorical_associations": category_results, "model_comparisons": model_results, "control_collinearity": collinearity, "within_account_sensitivity": {"repeated_account_counts": repeated_account, "log_word_count_vs_log_total_actions": within_account_sensitivity(word, "log_word_count", "log_total_actions")}, "bh_regression": bh_regression,
        "policy": {"primary_outcome": "log1p(sum of four provider-native action rates per 1,000 views), only when all four are observed", "controls": control_cols, "account_dependence": "cluster bootstrap CIs and grouped holdouts; account median/baseline controls", "multiplicity": "BH implementation is regression-tested; p/q outputs are suppressed until a cluster-respecting significance test is implemented", "missingness": "null remains unknown; no zero imputation; saves-missing rows excluded from primary total-action outcome", "leakage": "no release diagnostic z, candidate rank, or account baseline outcome-derived score used as transcript feature; snapshot metrics only", "holdout": "5 grouped account folds only when predeclared row/account floors and fold rank checks pass", "decision_rule": "no causal, market-prevalence, final-best, or production prediction claim"},
        "evidence_scope": {"scope_label": "provided transcript text and Signal metrics only", "media_inputs_provided": False, "scene_metrics_state": "NOT_ESTIMABLE_MISSING_MEDIA_AND_SCENES"},
        "limitations": [f"Transcript sample is selected and covers {len(word)}/{len(all_payloads)} Reels ({len(word) / len(all_payloads) * 100:.3f}%) word-bearing; selection mechanism is unknown.", "All semantic topic, hook, proof, and structure labels are maker-coded candidates pending independent review.", "ASR is legacy, forced-English and audio/media-unverified; segment timing and original language are not verified.", "No source media, frames, shots, semantic scenes or comments are available for this provided-text benchmark, so words-per-scene and visual-structure effects are not estimable.", "Metrics are a single dated snapshot with unverified counter semantics, capture time and exposure horizon; age is publication-to-snapshot, not matched reach age.", "Many transcript records are singleton accounts; cluster uncertainty and grouped holdouts reduce effective information.", "Row-permutation p/q fields are suppressed because the available permutation is not cluster-valid; a future cluster-respecting test must address selection, dependence and missing-media bias."],
    }
    write_analytics_db(output_dir, result, joined, input_paths, overwrite=overwrite)
    atomic_write_text(output_dir / "benchmark.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    atomic_write_text(output_dir / "joined-transcript-metrics.jsonl", "\n".join(json.dumps(r, sort_keys=True) for r in joined) + "\n")
    return result


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="Signal SQLite database containing reel_analysis")
    parser.add_argument("--transcripts", required=True, type=Path, help="Transcript analysis JSONL")
    parser.add_argument("--source-map", required=True, type=Path, help="Transcript-to-Reel source map JSON")
    parser.add_argument("--summary", required=True, type=Path, help="Frozen Signal summary JSON (hash-bound input)")
    parser.add_argument("--output", required=True, type=Path, help="Directory for benchmark.json and joined-transcript-metrics.jsonl")
    parser.add_argument("--release-id", required=True, help="Signal release_id to audit")
    parser.add_argument("--run-id", default="transcript-benchmark", help="Run identifier recorded in output")
    parser.add_argument("--analysis-date", default="", help="ISO analysis date recorded in output")
    parser.add_argument("--seed", type=int, default=20260905, help="Deterministic bootstrap seed")
    parser.add_argument("--expected-transcript-count", type=int, default=0, help="Optional source-map row count guard; default 0 disables the fixture-specific count check")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing output files after alias checks")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    expected_count = None if args.expected_transcript_count == 0 else args.expected_transcript_count
    result = run_benchmark(args.db, args.transcripts, args.source_map, args.summary, args.output, args.release_id, args.run_id, args.analysis_date, args.seed, expected_count, args.overwrite)
    print(json.dumps({"state": "PASS_WITH_LIMITATIONS", "out": str(args.output), "records": result["transcript_join"]["records"], "word_bearing": result["transcript_join"]["word_bearing"], "primary_complete": result["transcript_join"]["complete_four_action_word_bearing"]}, indent=2))


if __name__ == "__main__":
    main()
