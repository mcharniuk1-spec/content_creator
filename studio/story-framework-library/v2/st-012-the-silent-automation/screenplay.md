# ST-012 — The Silent Automation

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A workflow owner must find why a task stopped despite no error appears on the main screen, because work can silently accumulate; the story resolves when the broken trigger becomes visible.

## Story spine

- Setup: an automation console
- Inciting change: The bell changes state before the objective is secure.
- Objective: find why a task stopped
- Obstacle: no error appears on the main screen
- Stakes: work can silently accumulate
- Action: notice the bell → follows the last successful event → inspect the event log
- Proof: event log
- Limitation: A log can reveal sequence, not intent.
- Payoff: the broken trigger becomes visible

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the bell | ENT-trigger changes: ENT-target:restored trigger=absent; ENT-proof:event log=hidden → ENT-target:restored trigger=unoriented; ENT-proof:event log=hidden. | macro / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to find why a task stopped. | locates the restored trigger | ENT-target changes: ENT-target:restored trigger=unoriented; ENT-proof:event log=hidden → ENT-target:restored trigger=present-unresolved; ENT-proof:event log=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But no error appears on the main screen. | sees the restored trigger blocked | ENT-obstacle, ENT-target changes: ENT-target:restored trigger=present-unresolved; ENT-proof:event log=hidden → ENT-target:restored trigger=blocked; ENT-proof:event log=hidden. | close / pan_right | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | attempt | The first visible move is to follow the last successful event. | follows the last successful event | ENT-hero, ENT-target changes: ENT-target:restored trigger=blocked; ENT-proof:event log=hidden → ENT-target:restored trigger=acted-on; ENT-proof:event log=hidden. | over_shoulder / push_in | voice_over / demonstrate_process | Show an attempted causal operation on the target. |
| 4–5s | proof | Check the event log, not the claim. | checks the event log | ENT-proof, ENT-target changes: ENT-target:restored trigger=acted-on; ENT-proof:event log=hidden → ENT-target:restored trigger=changed-pending-review; ENT-proof:event log=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | payoff | Now the broken trigger becomes visible. | confirms the changed restored trigger | ENT-target changes: ENT-target:restored trigger=changed-pending-review; ENT-proof:event log=visible → ENT-target:restored trigger=resolved-with-boundary; ENT-proof:event log=visible. | medium / pull_out | return_cut / contrast | Close the opening question with the changed target. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
