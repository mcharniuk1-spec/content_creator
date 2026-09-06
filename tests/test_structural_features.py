from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from m2_signal.structural_features import StructuralFeatureError, build_structural_features


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def fixture_batch(tmp_path: Path, *, duplicate_primary: bool = False, second_revision: bool = False):
    root = tmp_path / "corpus"
    root.mkdir()
    media_path = root / "acquisition" / "media" / "R0.mp4"
    media_path.parent.mkdir(parents=True)
    media_path.write_bytes(b"fixture-media")
    source_hash = digest(media_path)
    acquisition_path = root / "acquisition" / "R0.media.json"
    write_json(acquisition_path, {"schema": "m2.acquired-media.v1", "reel_id": "instagram:R0", "media_id": "R0", "sha256": source_hash, "source_pointer": "media/R0.mp4"})
    transcript = {
        "schema": "m2.transcript-evidence.v1",
        "observation_state": "OBSERVED",
        "source_media_hash": source_hash,
        "language": "en",
        "segments": [
            {"segment_id": "T1", "start_ms": 0, "end_ms": 1000, "text": "first claim", "words": [{"start_ms": 100, "end_ms": 300, "word": "first"}, {"start_ms": 350, "end_ms": 600, "word": "claim"}]},
            {"segment_id": "T2", "start_ms": 1200, "end_ms": 2000, "text": "next step", "words": [{"start_ms": 1300, "end_ms": 1600, "word": "next"}, {"start_ms": 1650, "end_ms": 1900, "word": "step"}]},
        ],
    }
    transcript_path = root / "transcripts" / "R0.json"
    write_json(transcript_path, transcript)
    asr = [{"segment_id": "T1", "start_ms": 0, "end_ms": 1000, "text": "first claim", "valid_timed_word_count": 2}, {"segment_id": "T2", "start_ms": 1200, "end_ms": 2000, "text": "next step", "valid_timed_word_count": 2}]
    primary = [
        {"partition_order": 1, "primary_section_id": "H01", "source_segment_id": "T1", "start_ms": 0, "end_ms": 1000, "label": "hook", "valid_timed_word_count": 2},
        {"partition_order": 2, "primary_section_id": "M01", "source_segment_id": "T2", "start_ms": 1200, "end_ms": 2000, "label": "mechanism", "valid_timed_word_count": 2},
    ]
    if duplicate_primary:
        primary[1]["source_segment_id"] = "T1"
    annotation = {
        "schema": "m2.transcript-structure-annotation.v2", "identity_index": 0, "reel_id": "instagram:R0", "code": "R0",
        "source_media_hash": source_hash, "input": {"transcript_path": "transcripts/R0.json", "transcript_sha256": digest(transcript_path), "source_media_hash": source_hash, "acquisition_artifacts": {"acquisition/R0.media.json": digest(acquisition_path), "acquisition/media/R0.mp4": source_hash}, "transcript_artifacts": {"transcripts/R0.json": digest(transcript_path)}},
        "asr_segments": asr, "primary_partition": primary,
        "rhetorical_sections": [{"section_id": "H01", "label": "hook", "layer": "secondary_non_additive", "non_additive": True, "asr_segment_ids": ["T1"], "start_ms": 0, "end_ms": 1000}, {"section_id": "M01", "label": "mechanism", "layer": "secondary_non_additive", "non_additive": True, "asr_segment_ids": ["T2"], "start_ms": 1200, "end_ms": 2000}],
        "review_state": "PENDING_INDEPENDENT_REVIEW",
    }
    ann_path = tmp_path / ("annotations-2.jsonl" if second_revision else "annotations.jsonl")
    ann_path.write_text(json.dumps(annotation, sort_keys=True) + "\n", encoding="utf-8")
    ann_hash = digest(ann_path)
    review = {"schema": "m2.transcript-structure-independent-review.v1", "review_id": "review-r0", "maker": "maker", "reviewer": "reviewer", "verdict": "ACCEPT_WITH_LIMITATIONS_FOR_BOUNDED_STRUCTURAL_ANALYSIS", "scope": {"identity_indexes": [0]}, "inputs": {"structural-annotations.jsonl": ann_hash}}
    review_path = tmp_path / ("review-2.json" if second_revision else "review.json")
    write_json(review_path, review)
    canonical = tmp_path / "canonical.json"
    write_json(canonical, {"entries": [
        {"identity_index": 0, "reel_id": "instagram:R0", "code": "R0", "source_media_hash": source_hash},
        {"identity_index": 1, "reel_id": "instagram:R1", "code": "R1", "quarantine_reasons": ["MISSING_MEDIA"]},
        {"identity_index": 2, "reel_id": "instagram:R2", "code": "R2"},
    ]})
    return root, canonical, {"annotations_path": str(ann_path), "annotations_sha256": ann_hash, "review_path": str(review_path), "review_sha256": digest(review_path)}


def test_preserves_full_population_and_separates_primary_secondary_durations(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    result = build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    rows = [json.loads(line) for line in (tmp_path / "out/structural-features.jsonl").read_text().splitlines()]
    assert result["population"]["output_rows"] == 3
    assert rows[0]["disposition"] == "STRUCTURAL_ACCEPTED_WITH_LIMITATIONS"
    assert rows[0]["primary"]["by_label"]["hook"]["valid_timed_word_count"] == 2
    assert rows[0]["primary"]["timeline_span_ms"] == 2000
    assert rows[0]["primary"]["asr_segment_coverage_ms"] == 1800
    assert rows[0]["primary"]["speaking_duration_ms"] is None
    assert rows[0]["primary"]["speaking_duration_state"] == "UNKNOWN_NO_VAD"
    assert rows[0]["secondary"]["non_additive"] is True
    assert rows[1]["disposition"] == "BLOCKED_CANONICAL_QUARANTINE"
    assert rows[1]["quarantine_reasons"] == ["MISSING_MEDIA"]
    assert (tmp_path / "out/structural-features.sqlite").exists()
    assert len(rows) == 3


def test_wrong_review_binding_is_rejected_before_output(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    review = json.loads(Path(spec["review_path"]).read_text())
    review["inputs"]["structural-annotations.jsonl"] = "b" * 64
    Path(spec["review_path"]).write_text(json.dumps(review) + "\n")
    spec["review_sha256"] = digest(Path(spec["review_path"]))
    with pytest.raises(StructuralFeatureError, match="REVIEW_ANNOTATION_HASH_MISMATCH"):
        build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)


def test_invalid_exclusive_partition_is_retained_as_blocked_row(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path, duplicate_primary=True)
    result = build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    row = json.loads((tmp_path / "out/structural-features.jsonl").read_text().splitlines()[0])
    assert result["population"]["blocked_rows"] == 2
    assert row["disposition"] == "BLOCKED_INVALID_STRUCTURAL_BINDING"
    assert row["quarantine_reasons"] == ["PRIMARY_PARTITION_NOT_EXCLUSIVE"]


def test_conflicting_duplicate_revision_requires_explicit_selection(tmp_path):
    root, canonical, first = fixture_batch(tmp_path)
    second_annotation_path = tmp_path / "annotations-2.jsonl"
    second_annotation = json.loads(Path(first["annotations_path"]).read_text().splitlines()[0])
    second_annotation["primary_partition"][1]["label"] = "body"
    second_annotation["rhetorical_sections"][1]["label"] = "body"
    second_annotation_path.write_text(json.dumps(second_annotation, sort_keys=True) + "\n")
    second_review_path = tmp_path / "review-2.json"
    second_review = {"schema": "m2.transcript-structure-independent-review.v1", "review_id": "review-r0-2", "maker": "maker", "reviewer": "reviewer", "verdict": "ACCEPT_WITH_LIMITATIONS_FOR_BOUNDED_STRUCTURAL_ANALYSIS", "scope": {"identity_indexes": [0]}, "inputs": {"structural-annotations.jsonl": digest(second_annotation_path)}}
    write_json(second_review_path, second_review)
    second = {"annotations_path": str(second_annotation_path), "annotations_sha256": digest(second_annotation_path), "review_path": str(second_review_path), "review_sha256": digest(second_review_path)}
    with pytest.raises(StructuralFeatureError, match="CONFLICTING_ANNOTATION_REVISIONS"):
        build_structural_features(canonical, [first, second], root, tmp_path / "out", expected_population=3)
    selected = build_structural_features(canonical, [first, second], root, tmp_path / "selected", selected_revisions={0: second["annotations_sha256"]}, expected_population=3)
    selected_row = json.loads((tmp_path / "selected/structural-features.jsonl").read_text().splitlines()[0])
    assert selected["population"]["accepted_rows"] == 1
    assert selected_row["primary"]["by_label"]["body"]["segment_count"] == 1


def test_transcript_symlink_escape_is_blocked(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    source = root / "transcripts/R0.json"
    moved = root / "outside.json"
    source.unlink(); moved.write_text("{}")
    source.symlink_to(moved)
    result = build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    row = json.loads((tmp_path / "out/structural-features.jsonl").read_text().splitlines()[0])
    assert result["population"]["blocked_rows"] == 2
    assert row["disposition"] == "BLOCKED_INVALID_STRUCTURAL_BINDING"


def test_normalized_sqlite_has_population_and_integrity_tables(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    with sqlite3.connect(tmp_path / "out/structural-features.sqlite") as db:
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"identities", "dispositions", "reviews", "primary_segments", "secondary_sections"} <= names
        assert db.execute("SELECT COUNT(*) FROM identities").fetchone()[0] == 3
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_canonical_reel_id_duplicate_is_rejected(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    value = json.loads(Path(canonical).read_text())
    value["entries"][2]["reel_id"] = value["entries"][1]["reel_id"]
    Path(canonical).write_text(json.dumps(value) + "\n")
    with pytest.raises(StructuralFeatureError, match="CANONICAL_IDENTITY_DUPLICATE"):
        build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)


def test_missing_review_scope_fails_closed(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    review = json.loads(Path(spec["review_path"]).read_text())
    review.pop("scope")
    Path(spec["review_path"]).write_text(json.dumps(review) + "\n")
    spec["review_sha256"] = digest(Path(spec["review_path"]))
    with pytest.raises(StructuralFeatureError, match="REVIEW_SCOPE_REQUIRED"):
        build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)


def test_artifact_hash_mismatch_is_blocked_without_source_body(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    annotation = json.loads(Path(spec["annotations_path"]).read_text())
    annotation["input"]["transcript_artifacts"] = {"transcripts/R0.json": "b" * 64}
    Path(spec["annotations_path"]).write_text(json.dumps(annotation, sort_keys=True) + "\n")
    spec["annotations_sha256"] = digest(Path(spec["annotations_path"]))
    review = json.loads(Path(spec["review_path"]).read_text())
    review["inputs"]["structural-annotations.jsonl"] = spec["annotations_sha256"]
    Path(spec["review_path"]).write_text(json.dumps(review, sort_keys=True) + "\n")
    spec["review_sha256"] = digest(Path(spec["review_path"]))
    result = build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    row = json.loads((tmp_path / "out/structural-features.jsonl").read_text().splitlines()[0])
    assert result["population"]["blocked_rows"] == 2
    assert row["quarantine_reasons"] == ["ARTIFACT_HASH_MISMATCH"]


def test_bracket_only_annotation_is_unverified_speech(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    transcript_path = root / "transcripts/R0.json"
    transcript = json.loads(transcript_path.read_text())
    for segment in transcript["segments"]:
        segment["text"] = "[Pomp and Circumstance]"
    transcript_path.write_text(json.dumps(transcript, sort_keys=True) + "\n")
    annotation = json.loads(Path(spec["annotations_path"]).read_text())
    for segment in annotation["asr_segments"]:
        segment["text"] = "[Pomp and Circumstance]"
    annotation["input"]["transcript_sha256"] = digest(transcript_path)
    annotation["input"]["transcript_artifacts"]["transcripts/R0.json"] = digest(transcript_path)
    Path(spec["annotations_path"]).write_text(json.dumps(annotation, sort_keys=True) + "\n")
    spec["annotations_sha256"] = digest(Path(spec["annotations_path"]))
    review = json.loads(Path(spec["review_path"]).read_text())
    review["inputs"]["structural-annotations.jsonl"] = spec["annotations_sha256"]
    Path(spec["review_path"]).write_text(json.dumps(review, sort_keys=True) + "\n")
    spec["review_sha256"] = digest(Path(spec["review_path"]))
    build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    row = json.loads((tmp_path / "out/structural-features.jsonl").read_text().splitlines()[0])
    assert row["coverage"]["valid_timed_word_count"] == 4
    assert row["coverage"]["spoken_word_count"] is None
    assert row["coverage"]["speech_eligibility"] == "UNKNOWN_UNVERIFIED_ANNOTATION_ONLY"
    assert row["coverage"]["word_timing"] == "UNVERIFIED_ANNOTATION_ONLY"
    assert "ASR_ANNOTATION_ONLY_SPEECH_UNVERIFIED" in row["quality_issues"]


def test_duplicate_asr_segment_id_is_blocked(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    annotation = json.loads(Path(spec["annotations_path"]).read_text())
    annotation["asr_segments"][1]["segment_id"] = "T1"
    Path(spec["annotations_path"]).write_text(json.dumps(annotation, sort_keys=True) + "\n")
    spec["annotations_sha256"] = digest(Path(spec["annotations_path"]))
    review = json.loads(Path(spec["review_path"]).read_text())
    review["inputs"]["structural-annotations.jsonl"] = spec["annotations_sha256"]
    Path(spec["review_path"]).write_text(json.dumps(review, sort_keys=True) + "\n")
    spec["review_sha256"] = digest(Path(spec["review_path"]))
    build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    row = json.loads((tmp_path / "out/structural-features.jsonl").read_text().splitlines()[0])
    assert row["quarantine_reasons"] == ["ANNOTATION_ASR_SEGMENT_DUPLICATE"]


def test_source_segment_overlap_is_blocked(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    transcript_path = root / "transcripts/R0.json"
    transcript = json.loads(transcript_path.read_text())
    transcript["segments"][1]["start_ms"] = 500
    transcript_path.write_text(json.dumps(transcript, sort_keys=True) + "\n")
    annotation = json.loads(Path(spec["annotations_path"]).read_text())
    annotation["input"]["transcript_sha256"] = digest(transcript_path)
    annotation["input"]["transcript_artifacts"]["transcripts/R0.json"] = digest(transcript_path)
    Path(spec["annotations_path"]).write_text(json.dumps(annotation, sort_keys=True) + "\n")
    spec["annotations_sha256"] = digest(Path(spec["annotations_path"]))
    review = json.loads(Path(spec["review_path"]).read_text())
    review["inputs"]["structural-annotations.jsonl"] = spec["annotations_sha256"]
    Path(spec["review_path"]).write_text(json.dumps(review, sort_keys=True) + "\n")
    spec["review_sha256"] = digest(Path(spec["review_path"]))
    build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    row = json.loads((tmp_path / "out/structural-features.jsonl").read_text().splitlines()[0])
    assert row["quarantine_reasons"] == ["TRANSCRIPT_SEGMENT_OVERLAP"]


def test_research_quarantine_is_preserved_and_blocks(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    value = json.loads(Path(canonical).read_text())
    value["entries"][2]["research_quarantine_reasons"] = ["RESEARCH_SCOPE_PENDING"]
    Path(canonical).write_text(json.dumps(value, sort_keys=True) + "\n")
    build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    rows = [json.loads(line) for line in (tmp_path / "out/structural-features.jsonl").read_text().splitlines()]
    assert rows[2]["disposition"] == "BLOCKED_CANONICAL_QUARANTINE"
    assert rows[2]["quarantined"] is True
    assert rows[2]["research_quarantine_reasons"] == ["RESEARCH_SCOPE_PENDING"]


def test_secondary_sqlite_keeps_per_section_counts(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    annotation = json.loads(Path(spec["annotations_path"]).read_text())
    annotation["rhetorical_sections"].append({"section_id": "M02", "label": "hook", "layer": "secondary_non_additive", "non_additive": True, "asr_segment_ids": ["T1", "T2"], "start_ms": 0, "end_ms": 2000})
    Path(spec["annotations_path"]).write_text(json.dumps(annotation, sort_keys=True) + "\n")
    spec["annotations_sha256"] = digest(Path(spec["annotations_path"]))
    review = json.loads(Path(spec["review_path"]).read_text())
    review["inputs"]["structural-annotations.jsonl"] = spec["annotations_sha256"]
    Path(spec["review_path"]).write_text(json.dumps(review, sort_keys=True) + "\n")
    spec["review_sha256"] = digest(Path(spec["review_path"]))
    build_structural_features(canonical, [spec], root, tmp_path / "out", expected_population=3)
    with sqlite3.connect(tmp_path / "out/structural-features.sqlite") as db:
        values = [row[0] for row in db.execute("SELECT valid_timed_word_count FROM secondary_sections WHERE identity_index=0 AND label='hook' ORDER BY section_order")]
        assert values == [2, 4]


def test_declared_counts_and_transcript_hash_are_required_and_checked(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    annotation = json.loads(Path(spec["annotations_path"]).read_text())
    annotation["counts"] = {"lexical_word_count": 99}
    Path(spec["annotations_path"]).write_text(json.dumps(annotation, sort_keys=True) + "\n")
    spec["annotations_sha256"] = digest(Path(spec["annotations_path"]))
    review = json.loads(Path(spec["review_path"]).read_text())
    review["inputs"]["structural-annotations.jsonl"] = spec["annotations_sha256"]
    Path(spec["review_path"]).write_text(json.dumps(review, sort_keys=True) + "\n")
    spec["review_sha256"] = digest(Path(spec["review_path"]))
    build_structural_features(canonical, [spec], root, tmp_path / "counts-out", expected_population=3)
    row = json.loads((tmp_path / "counts-out/structural-features.jsonl").read_text().splitlines()[0])
    assert row["quarantine_reasons"] == ["TRANSCRIPT_COUNT_MISMATCH"]

    (tmp_path / "missing-hash").mkdir()
    root2, canonical2, spec2 = fixture_batch(tmp_path / "missing-hash")
    annotation2 = json.loads(Path(spec2["annotations_path"]).read_text())
    annotation2["input"].pop("transcript_sha256")
    Path(spec2["annotations_path"]).write_text(json.dumps(annotation2, sort_keys=True) + "\n")
    spec2["annotations_sha256"] = digest(Path(spec2["annotations_path"]))
    review2 = json.loads(Path(spec2["review_path"]).read_text())
    review2["inputs"]["structural-annotations.jsonl"] = spec2["annotations_sha256"]
    Path(spec2["review_path"]).write_text(json.dumps(review2, sort_keys=True) + "\n")
    spec2["review_sha256"] = digest(Path(spec2["review_path"]))
    build_structural_features(canonical2, [spec2], root2, tmp_path / "hash-out", expected_population=3)
    row2 = json.loads((tmp_path / "hash-out/structural-features.jsonl").read_text().splitlines()[0])
    assert row2["quarantine_reasons"] == ["TRANSCRIPT_HASH_REQUIRED"]


def test_repository_relative_transcript_path_uses_exact_approved_prefix(tmp_path, monkeypatch):
    import m2_signal.structural_features as module
    repository = tmp_path / 'repository'
    module_path = repository / 'm2_signal/structural_features.py'
    module_path.parent.mkdir(parents=True)
    module_path.write_text('# fixture')
    root = repository / 'runs/approved-corpus'
    root.mkdir(parents=True)
    target = root / 'transcripts/a.json'
    target.parent.mkdir()
    target.write_text('{}')
    monkeypatch.setattr(module, '__file__', str(module_path))
    actual, _, _ = module._safe_relative_file(root, 'runs/approved-corpus/transcripts/a.json')
    assert actual == target
    with pytest.raises(StructuralFeatureError):
        module._safe_relative_file(root, 'runs/unapproved-corpus/transcripts/a.json')


def test_source_declared_counts_cannot_override_actual_word_partition():
    from m2_signal.structural_features import _validated_input_counts
    transcript = {'segments': [{'words': [{}, {}], 'raw_words': [{}, {}, {}], 'unaligned_words': [{}]}], 'lexical_word_count': 3, 'aligned_word_count': 999, 'unaligned_word_count': 1}
    with pytest.raises(StructuralFeatureError, match='TRANSCRIPT_COUNT_MISMATCH'):
        _validated_input_counts({}, {}, transcript, {'lexical': 2, 'valid': 2, 'unaligned': 0})
    transcript['aligned_word_count'] = 2
    counts, _ = _validated_input_counts({}, {'lexical_word_count': 3, 'aligned_word_count': 2, 'unaligned_word_count': 1, 'valid_timed_word_count': 2}, transcript, {'lexical': 2, 'valid': 2, 'unaligned': 0})
    assert counts == {'lexical_word_count': 3, 'aligned_word_count': 2, 'unaligned_word_count': 1, 'word_timing': 'UNKNOWN'}


def test_machine_words_do_not_become_verified_spoken_words(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    build_structural_features(canonical, [spec], root, tmp_path / 'out', expected_population=3)
    row = json.loads((tmp_path / 'out/structural-features.jsonl').read_text().splitlines()[0])
    assert row['coverage']['spoken_word_count'] is None
    assert row['coverage']['speech_eligibility'] == 'NOT_ESTABLISHED'
    assert row['coverage']['primary_valid_timed_word_count'] == sum(x['valid_timed_word_count'] for x in row['primary']['segments'])


def refresh_annotation_spec(spec, annotation):
    path = Path(spec['annotations_path'])
    path.write_text(json.dumps(annotation, sort_keys=True) + '\n')
    spec['annotations_sha256'] = digest(path)
    review_path = Path(spec['review_path'])
    review = json.loads(review_path.read_text())
    review['inputs']['structural-annotations.jsonl'] = spec['annotations_sha256']
    write_json(review_path, review)
    spec['review_sha256'] = digest(review_path)


def test_actual_shaped_export_preserves_section_ids_raw_partition_and_paths(tmp_path, monkeypatch):
    import m2_signal.structural_features as module
    repository = tmp_path / 'repository'
    repository.mkdir()
    root, canonical, spec = fixture_batch(repository)
    module_path = repository / 'm2_signal/structural_features.py'
    module_path.parent.mkdir()
    module_path.write_text('# isolated fixture runtime')
    monkeypatch.setattr(module, '__file__', str(module_path))
    tx_path = root / 'transcripts/R0.json'
    tx = json.loads(tx_path.read_text())
    for segment in tx['segments']:
        segment['raw_words'] = [dict(word) for word in segment['words']]
        segment['unaligned_words'] = []
    tx['segments'][0]['raw_words'].append({'word': 'uncertain', 'start': .7, 'end': .7})
    tx['segments'][0]['unaligned_words'].append({'word_index': 2, 'reason': 'ZERO_DURATION_WORD'})
    counts = {'lexical_word_count': 5, 'aligned_word_count': 4, 'unaligned_word_count': 1}
    tx.update(counts)
    tx['word_timing'] = 'PARTIAL'
    write_json(tx_path, tx)
    annotation = json.loads(Path(spec['annotations_path']).read_text())
    annotation['input'].update(counts)
    annotation['input'].update({'valid_timed_word_count': 4, 'word_timing': 'PARTIAL', 'transcript_path': 'corpus/transcripts/R0.json', 'transcript_sha256': digest(tx_path)})
    annotation['input']['transcript_artifacts']['transcripts/R0.json'] = digest(tx_path)
    for section in annotation['rhetorical_sections']:
        section['valid_timed_word_count'] = 2
    refresh_annotation_spec(spec, annotation)
    build_structural_features(canonical, [spec], root, tmp_path / 'output', expected_population=3)
    row = json.loads((tmp_path / 'output/structural-features.jsonl').read_text().splitlines()[0])
    assert row['disposition'] == 'STRUCTURAL_ACCEPTED_WITH_LIMITATIONS'
    assert row['coverage']['lexical_word_count'] == 5
    assert row['coverage']['aligned_word_count'] == 4
    assert row['coverage']['unaligned_word_count'] == 1
    assert row['coverage']['spoken_word_count'] is None
    assert row['coverage']['word_timing'] == 'PARTIAL'
    assert [x['primary_section_id'] for x in row['primary']['segments']] == ['H01', 'M01']
    assert [x['section_id'] for x in row['secondary']['sections']] == ['H01', 'M01']
    with sqlite3.connect(tmp_path / 'output/structural-features.sqlite') as db:
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert [x[0] for x in db.execute('SELECT primary_section_id FROM primary_segments ORDER BY partition_order')] == ['H01', 'M01']
        assert [x[0] for x in db.execute('SELECT section_id FROM secondary_sections ORDER BY section_order')] == ['H01', 'M01']


@pytest.mark.parametrize('mutation,error', [
    ('wrong_count', 'SECONDARY_SECTION_COUNT_MISMATCH'),
    ('missing_primary_id', 'PRIMARY_SECTION_ID_INVALID'),
    ('wrong_membership', 'PRIMARY_SECTION_LINK_MISMATCH'),
    ('duplicate_section_id', 'SECONDARY_SECTION_ID_INVALID'),
])
def test_section_identity_and_count_failures_preserve_blocked_identity(tmp_path, mutation, error):
    root, canonical, spec = fixture_batch(tmp_path)
    annotation = json.loads(Path(spec['annotations_path']).read_text())
    if mutation == 'wrong_count': annotation['rhetorical_sections'][0]['valid_timed_word_count'] = 99
    if mutation == 'missing_primary_id': annotation['primary_partition'][0].pop('primary_section_id')
    if mutation == 'wrong_membership': annotation['primary_partition'][0]['primary_section_id'] = 'M01'
    if mutation == 'duplicate_section_id': annotation['rhetorical_sections'][1]['section_id'] = 'H01'
    refresh_annotation_spec(spec, annotation)
    build_structural_features(canonical, [spec], root, tmp_path / 'out', expected_population=3)
    rows = [json.loads(line) for line in (tmp_path / 'out/structural-features.jsonl').read_text().splitlines()]
    assert len(rows) == 3
    assert rows[0]['disposition'] == 'BLOCKED_INVALID_STRUCTURAL_BINDING'
    assert rows[0]['quarantine_reasons'] == [error]


def test_empty_output_is_preserved_without_structural_acceptance(tmp_path):
    root, canonical, spec = fixture_batch(tmp_path)
    tx_path = root / 'transcripts/R0.json'
    transcript = json.loads(tx_path.read_text())
    transcript.update({'observation_state': 'EMPTY_OUTPUT_UNVERIFIED', 'failure_code': 'EMPTY_ASR_NOT_PROOF_OF_SILENCE', 'segments': [], 'words': 0, 'no_speech_confirmed': False})
    write_json(tx_path, transcript)
    annotation = json.loads(Path(spec['annotations_path']).read_text())
    annotation.update({'asr_segments': [], 'primary_partition': [], 'rhetorical_sections': []})
    annotation['input']['transcript_sha256'] = digest(tx_path)
    annotation['input']['transcript_artifacts']['transcripts/R0.json'] = digest(tx_path)
    refresh_annotation_spec(spec, annotation)
    result = build_structural_features(canonical, [spec], root, tmp_path / 'out', expected_population=3)
    rows = [json.loads(line) for line in (tmp_path / 'out/structural-features.jsonl').read_text().splitlines()]
    assert result['population'] == {'input_rows': 3, 'output_rows': 3, 'rows_dropped': 0, 'accepted_rows': 0, 'blocked_rows': 1, 'not_analyzable_rows': 1, 'missing_review_rows': 1}
    empty = rows[0]
    assert empty['disposition'] == 'NOT_ANALYZABLE_EMPTY_OUTPUT_UNVERIFIED'
    assert empty['transcript_failure_code'] == 'EMPTY_ASR_NOT_PROOF_OF_SILENCE'
    assert empty['coverage']['spoken_word_count'] is None
    assert empty['coverage']['speech_eligibility'] == 'UNKNOWN'
    assert empty['source']['sha256'] == digest(tx_path)
    with sqlite3.connect(tmp_path / 'out/structural-features.sqlite') as db:
        assert db.execute('SELECT COUNT(*) FROM identities').fetchone()[0] == 3
        assert db.execute('SELECT COUNT(*) FROM primary_segments').fetchone()[0] == 0
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
