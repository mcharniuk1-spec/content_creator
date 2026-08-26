# ST-033 — Manual Copy to Checked Export

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A data operator must move records without losing lineage despite manual copy strips IDs and null states, because downstream analysis can misread absence; the story resolves when the receiver can verify the file.

## Story spine

- Setup: a transfer bench
- Inciting change: The clipboard changes state before the objective is secure.
- Objective: move records without losing lineage
- Obstacle: manual copy strips IDs and null states
- Stakes: downstream analysis can misread absence
- Action: notice the clipboard → exports stable IDs, nulls, and checksums → inspect the hash receipt
- Proof: hash receipt
- Limitation: A valid export may still contain weak source data.
- Payoff: the receiver can verify the file

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the clipboard | ENT-trigger changes: ENT-target:versioned export=absent; ENT-proof:hash receipt=hidden → ENT-target:versioned export=unoriented; ENT-proof:hash receipt=hidden. | wide / locked | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to move records without losing lineage. | locates the versioned export | ENT-target changes: ENT-target:versioned export=unoriented; ENT-proof:hash receipt=hidden → ENT-target:versioned export=present-unresolved; ENT-proof:hash receipt=hidden. | wide / locked | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But manual copy strips IDs and null states. | sees the versioned export blocked | ENT-obstacle, ENT-target changes: ENT-target:versioned export=present-unresolved; ENT-proof:hash receipt=hidden → ENT-target:versioned export=blocked; ENT-proof:hash receipt=hidden. | close / push_in | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | mechanism | The decisive mechanism is to export stable IDs, nulls, and checksums. | exports stable IDs, nulls, and checksums | ENT-hero, ENT-target changes: ENT-target:versioned export=blocked; ENT-proof:hash receipt=hidden → ENT-target:versioned export=transformed; ENT-proof:hash receipt=hidden. | medium / pan_right | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 4–5s | proof | Check the hash receipt, not the claim. | checks the hash receipt | ENT-proof, ENT-target changes: ENT-target:versioned export=transformed; ENT-proof:hash receipt=hidden → ENT-target:versioned export=changed-pending-review; ENT-proof:hash receipt=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | payoff | Now the receiver can verify the file. | confirms the changed versioned export | ENT-target changes: ENT-target:versioned export=changed-pending-review; ENT-proof:hash receipt=visible → ENT-target:versioned export=resolved-with-boundary; ENT-proof:hash receipt=visible. | wide / pull_out | return_cut / contrast | Close the opening question with the changed target. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
