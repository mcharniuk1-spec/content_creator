# Transcript and engagement benchmark

This standard-library CLI analyzes an explicit Signal release and a separately
produced transcript-analysis package. It performs no collection, ASR, media
generation or Notion write. Run one benchmark process at a time; its seeded
calculation context is process-local.

```bash
python3 -m m2_signal.transcript_benchmark \
  --db .local/signal.sqlite \
  --transcripts .local/reviewed-text/transcript-analysis.jsonl \
  --source-map .local/reviewed-text/private-source-map.json \
  --summary .local/signal-release/summary.json \
  --release-id SIGNAL_RELEASE_ID \
  --run-id RUN_ID \
  --analysis-date YYYY-MM-DD \
  --output .local/benchmark-RUN_ID
```

The source-map entries bind unique transcript IDs to unique Reel IDs and source
record SHA-256 values. Transcript analysis supplies lexical/segment counts,
section assignments and provisional semantic labels, with its metric snapshot.
The metric vector must agree with the current Signal payload, allowing only
rounding tolerance. A fresh metric release therefore requires a refreshed,
reviewed transcript-analysis metric binding even when the transcript text is
unchanged. Never silently join old numeric vectors to a new release.

`--expected-transcript-count N` adds an exact inventory assertion; it is
disabled by default. `--seed` defaults to 20260905. Existing output files require
`--overwrite`; use a new run/output directory for a changed corpus or policy.
Input/output aliases are rejected. Output files use atomic replacement, but the
three-file output set is not a distributed transaction: accept it only after
the process succeeds and all hashes and counts are verified.

## Outputs and parameters

- `benchmark.json`: complete population/availability counts, 15 numeric
  associations, supported categorical contrasts, seven baseline-versus-candidate
  model comparisons, fold diagnostics, collinearity screen and limitations.
- `joined-transcript-metrics.jsonl`: one joined record per transcript with
  separate numeric outcomes, word counts and candidate coding.
- `analytics.sqlite`: normalized run provenance, metric dictionary, transcript
  features/outcomes, numeric/categorical associations and model/fold tables.

The current version uses 1,000 account-cluster bootstrap replicates, a 10-row
numeric-association floor, categorical support of at least five rows and three
accounts per category, and five account-disjoint folds with a minimum 40 rows
and five accounts before model comparison. Fold sample and matrix-rank checks
may still suppress a model. These are versioned method constants, not claims
that the sample is sufficient for production. Changing them requires a new
implementation-bound run and review.

The primary outcome is log1p of the sum of four native action rates per 1,000
views, only when all four rates are present. A missing save count remains null.
Secondary outcomes retain the four actions separately. Baseline controls are
log views, publication-to-snapshot age, duration, account median views and
account baseline count. Candidate lexical or semantic families are added one
at a time. Categorical vocabularies are learned within each training fold;
unseen test categories map to the omitted reference/unknown bucket.

Numeric contrasts use Spearman correlation. A categorical contrast is the
category median minus the pooled usable-row median. Each bootstrap replicate
resamples complete account clusters and recomputes both medians. This preserves
within-account dependence but does not remove selection bias or measurement
error. Report the number of rows and account clusters with every estimate.

All live p-values and BH q-values remain null. The available row permutation
was not cluster-valid; the corrected BH utility is tested but does not turn
missing valid p-values into significance evidence. Grouped fold error and
training fit are exploratory diagnostics, not deployment acceptance or a
causal content recommendation.

## Interpretation and next state

For legacy analysis, opening/body/ending word counts refer to first/interior/
last supplied ASR segments. They are not verified rhetorical boundaries. This
benchmark does not ingest media or scene annotations, so words-per-scene remains
unavailable. A future verified scene pipeline needs its own reviewed adapter.

Bind these output hashes to the quantitative/account-analysis task and return
them to the independent Signal reviewer. Review the unique joins, section sums,
current metric binding, missingness, small cells, grouped folds and all claims
before projection or knowledge promotion. Re-run the analysis on each new
dated release. Do not pool repeated observations without a longitudinal design,
or infer corpus-wide topic prevalence from a selected transcript subset.
