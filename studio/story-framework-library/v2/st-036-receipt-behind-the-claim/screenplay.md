# ST-036 — Receipt Behind the Claim

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

An operations narrator must show that a task actually ran despite the spoken claim has no visible artifact, because confidence could replace verification; the story resolves when the execution state is inspectable.

## Story spine

- Setup: a document table
- Inciting change: The receipt changes state before the objective is secure.
- Objective: show that a task actually ran
- Obstacle: the spoken claim has no visible artifact
- Stakes: confidence could replace verification
- Action: notice the receipt → reveals the dated receipt and matching ID → inspect the timestamped output
- Proof: timestamped output
- Limitation: A receipt proves execution, not outcome quality.
- Payoff: the execution state is inspectable

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the receipt | ENT-trigger changes: ENT-target:bounded verdict=absent; ENT-proof:timestamped output=hidden → ENT-target:bounded verdict=unoriented; ENT-proof:timestamped output=hidden. | close / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to show that a task actually ran. | locates the bounded verdict | ENT-target changes: ENT-target:bounded verdict=unoriented; ENT-proof:timestamped output=hidden → ENT-target:bounded verdict=present-unresolved; ENT-proof:timestamped output=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But the spoken claim has no visible artifact. | sees the bounded verdict blocked | ENT-obstacle, ENT-target changes: ENT-target:bounded verdict=present-unresolved; ENT-proof:timestamped output=hidden → ENT-target:bounded verdict=blocked; ENT-proof:timestamped output=hidden. | macro / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | mechanism | The decisive mechanism is to reveal the dated receipt and matching ID. | reveals the dated receipt and matching ID | ENT-hero, ENT-target changes: ENT-target:bounded verdict=blocked; ENT-proof:timestamped output=hidden → ENT-target:bounded verdict=transformed; ENT-proof:timestamped output=hidden. | over_shoulder / tilt_down | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 4–5s | proof | Check the timestamped output, not the claim. | checks the timestamped output | ENT-proof, ENT-target changes: ENT-target:bounded verdict=transformed; ENT-proof:timestamped output=hidden → ENT-target:bounded verdict=changed-pending-review; ENT-proof:timestamped output=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | limitation | The evidence stops here: A receipt proves execution, not outcome quality. | bounds the result with timestamped output | ENT-proof, ENT-target changes: ENT-target:bounded verdict=changed-pending-review; ENT-proof:timestamped output=visible → ENT-target:bounded verdict=resolved-with-boundary; ENT-proof:timestamped output=visible. | medium / pull_out | return_cut / prove_state | State where the visible evidence stops. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
