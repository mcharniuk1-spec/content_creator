# ST-013 — Duplicate in the Queue

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A data steward must find why counts disagree despite one entity appears under two labels, because reports may double-count the same object; the story resolves when the duplicate is resolved without deleting evidence.

## Story spine

- Setup: a record desk
- Inciting change: The two tags changes state before the objective is secure.
- Objective: find why counts disagree
- Obstacle: one entity appears under two labels
- Stakes: reports may double-count the same object
- Action: notice the two tags → matches stable identifiers before merging → inspect the canonical ID
- Proof: canonical ID
- Limitation: Entity resolution may require human review.
- Payoff: the duplicate is resolved without deleting evidence

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the two tags | ENT-trigger changes: ENT-target:merged record=absent; ENT-proof:canonical ID=hidden → ENT-target:merged record=unoriented; ENT-proof:canonical ID=hidden. | macro / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to find why counts disagree. | locates the merged record | ENT-target changes: ENT-target:merged record=unoriented; ENT-proof:canonical ID=hidden → ENT-target:merged record=present-unresolved; ENT-proof:canonical ID=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But one entity appears under two labels. | sees the merged record blocked | ENT-obstacle, ENT-target changes: ENT-target:merged record=present-unresolved; ENT-proof:canonical ID=hidden → ENT-target:merged record=blocked; ENT-proof:canonical ID=hidden. | close / pan_right | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | attempt | The first visible move is to match stable identifiers before merging. | matches stable identifiers before merging | ENT-hero, ENT-target changes: ENT-target:merged record=blocked; ENT-proof:canonical ID=hidden → ENT-target:merged record=acted-on; ENT-proof:canonical ID=hidden. | over_shoulder / push_in | voice_over / demonstrate_process | Show an attempted causal operation on the target. |
| 4–5s | proof | Check the canonical ID, not the claim. | checks the canonical ID | ENT-proof, ENT-target changes: ENT-target:merged record=acted-on; ENT-proof:canonical ID=hidden → ENT-target:merged record=changed-pending-review; ENT-proof:canonical ID=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | payoff | Now the duplicate is resolved without deleting evidence. | confirms the changed merged record | ENT-target changes: ENT-target:merged record=changed-pending-review; ENT-proof:canonical ID=visible → ENT-target:merged record=resolved-with-boundary; ENT-proof:canonical ID=visible. | medium / pull_out | return_cut / contrast | Close the opening question with the changed target. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
