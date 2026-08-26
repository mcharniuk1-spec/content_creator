# ST-038 — The Diff Tells the Story

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A software reviewer must explain what changed despite the full file hides the relevant edit, because review time is wasted; the story resolves when the meaningful change stays visible.

## Story spine

- Setup: a code-review board
- Inciting change: The diff marks changes state before the objective is secure.
- Objective: explain what changed
- Obstacle: the full file hides the relevant edit
- Stakes: review time is wasted
- Action: notice the diff marks → peels away unchanged context → inspect the changed lines
- Proof: changed lines
- Limitation: A diff does not prove runtime behavior.
- Payoff: the meaningful change stays visible

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the diff marks | ENT-trigger changes: ENT-target:review decision=absent; ENT-proof:changed lines=hidden → ENT-target:review decision=unoriented; ENT-proof:changed lines=hidden. | close / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to explain what changed. | locates the review decision | ENT-target changes: ENT-target:review decision=unoriented; ENT-proof:changed lines=hidden → ENT-target:review decision=present-unresolved; ENT-proof:changed lines=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But the full file hides the relevant edit. | sees the review decision blocked | ENT-obstacle, ENT-target changes: ENT-target:review decision=present-unresolved; ENT-proof:changed lines=hidden → ENT-target:review decision=blocked; ENT-proof:changed lines=hidden. | macro / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | mechanism | The decisive mechanism is to peel away unchanged context. | peels away unchanged context | ENT-hero, ENT-target changes: ENT-target:review decision=blocked; ENT-proof:changed lines=hidden → ENT-target:review decision=transformed; ENT-proof:changed lines=hidden. | over_shoulder / tilt_down | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 4–5s | proof | Check the changed lines, not the claim. | checks the changed lines | ENT-proof, ENT-target changes: ENT-target:review decision=transformed; ENT-proof:changed lines=hidden → ENT-target:review decision=changed-pending-review; ENT-proof:changed lines=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | limitation | The evidence stops here: A diff does not prove runtime behavior. | bounds the result with changed lines | ENT-proof, ENT-target changes: ENT-target:review decision=changed-pending-review; ENT-proof:changed lines=visible → ENT-target:review decision=resolved-with-boundary; ENT-proof:changed lines=visible. | medium / pull_out | return_cut / prove_state | State where the visible evidence stops. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
