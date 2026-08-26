# ST-037 — The Timestamp Test

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A dashboard reviewer must decide whether a metric is current despite the chart title omits observed time, because old data may guide a new decision; the story resolves when the viewer sees whether the metric is usable.

## Story spine

- Setup: a monitor close-up
- Inciting change: The clock changes state before the objective is secure.
- Objective: decide whether a metric is current
- Obstacle: the chart title omits observed time
- Stakes: old data may guide a new decision
- Action: notice the clock → reveals the timestamp before the number → inspect the observed-at field
- Proof: observed-at field
- Limitation: Fresh data can still be incomplete.
- Payoff: the viewer sees whether the metric is usable

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the clock | ENT-trigger changes: ENT-target:freshness verdict=absent; ENT-proof:observed-at field=hidden → ENT-target:freshness verdict=unoriented; ENT-proof:observed-at field=hidden. | close / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to decide whether a metric is current. | locates the freshness verdict | ENT-target changes: ENT-target:freshness verdict=unoriented; ENT-proof:observed-at field=hidden → ENT-target:freshness verdict=present-unresolved; ENT-proof:observed-at field=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But the chart title omits observed time. | sees the freshness verdict blocked | ENT-obstacle, ENT-target changes: ENT-target:freshness verdict=present-unresolved; ENT-proof:observed-at field=hidden → ENT-target:freshness verdict=blocked; ENT-proof:observed-at field=hidden. | macro / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | mechanism | The decisive mechanism is to reveal the timestamp before the number. | reveals the timestamp before the number | ENT-hero, ENT-target changes: ENT-target:freshness verdict=blocked; ENT-proof:observed-at field=hidden → ENT-target:freshness verdict=transformed; ENT-proof:observed-at field=hidden. | over_shoulder / tilt_down | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 4–5s | proof | Check the observed-at field, not the claim. | checks the observed-at field | ENT-proof, ENT-target changes: ENT-target:freshness verdict=transformed; ENT-proof:observed-at field=hidden → ENT-target:freshness verdict=changed-pending-review; ENT-proof:observed-at field=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | limitation | The evidence stops here: Fresh data can still be incomplete. | bounds the result with observed-at field | ENT-proof, ENT-target changes: ENT-target:freshness verdict=changed-pending-review; ENT-proof:observed-at field=visible → ENT-target:freshness verdict=resolved-with-boundary; ENT-proof:observed-at field=visible. | medium / pull_out | return_cut / prove_state | State where the visible evidence stops. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
