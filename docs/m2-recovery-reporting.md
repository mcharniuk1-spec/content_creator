# Recovery reports and explicit ASR configurations

Recovery is a separate evidence overlay. It preserves the primary states, all recovery attempts, selected artifact identity, source hashes, typed errors and independent modality denominators. A machine-observed recovery is not acoustic approval and is not added to the primary success count without identity reconciliation. Original-audio uncertainty remains unknown even when a video-only container decodes.

The offline entry point is `python -m m2_orchestrator.recovery_overlay_report --help`. Supply an explicit canonical manifest, primary ledger, bounded acquisition/recovery roots, source snapshot hash, logical ledger snapshot hash and fresh output directory. These are operator-provided local inputs; this command neither collects media nor starts inference. Output includes every canonical identity, all attempts and field definitions. Preserve each report release and its input hashes.

The isolated transcription command now accepts `--beam-size 1` through `--beam-size 5`; the default remains 5. Config, chunk request, persisted run manifest and resume checks bind that exact integer. Missing, boolean, out-of-range or mismatched values fail closed. Changing beam size or model requires a fresh run and an independently admitted pilot under the existing resource limits. A smaller beam does not guarantee lower peak memory or successful transcription.

Partner execution sequence:

1. Review this revision and run the focused tests in the existing approved Python environment.
2. Pause the sole media/model worker and verify its lock is released. Keep source media and previous attempts.
3. Run the existing transcription entry point with `--preflight` and explicit local input/model/runtime paths. Inspect source, model, configuration and interpreter bindings.
4. After exact pilot authority, use a fresh output directory and `--run` for one retained source only. Record resource evidence and classify failures. Do not change limits to hide a failure.
5. Independently review actual results before a broader recovery batch. Build the report overlay without promoting acoustic, scene or analytical eligibility automatically.

Validation for this delivery: 46 focused recovery, beam-binding, manifest-binding and overlay tests passed. These are local fixture/integration checks; no partner-host execution, server deployment, generation-provider quality or complete-corpus result is implied. Local HikerAPI remains disabled. The report layer requires no model, credentials or external service.
