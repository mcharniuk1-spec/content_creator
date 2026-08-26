# ST-004 — Queue Under Pressure

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A support coordinator must route the urgent request correctly despite all tickets look identical, because a time-sensitive request may be buried; the story resolves when the urgent item reaches the correct lane.

## Story spine

- Setup: an intake desk
- Inciting change: The queue ticket changes state before the objective is secure.
- Objective: route the urgent request correctly
- Obstacle: all tickets look identical
- Stakes: a time-sensitive request may be buried
- Action: notice the queue ticket → marks urgency and owner before routing → inspect the priority rule
- Proof: priority rule
- Limitation: Priority is a declared rule, not inferred intent.
- Payoff: the urgent item reaches the correct lane

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the queue ticket | ENT-trigger changes: ENT-target:ordered queue=absent; ENT-proof:priority rule=hidden → ENT-target:ordered queue=unoriented; ENT-proof:priority rule=hidden. | extreme_close / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to route the urgent request correctly. | locates the ordered queue | ENT-target changes: ENT-target:ordered queue=unoriented; ENT-proof:priority rule=hidden → ENT-target:ordered queue=present-unresolved; ENT-proof:priority rule=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But all tickets look identical. | sees the ordered queue blocked | ENT-obstacle, ENT-target changes: ENT-target:ordered queue=present-unresolved; ENT-proof:priority rule=hidden → ENT-target:ordered queue=blocked; ENT-proof:priority rule=hidden. | medium / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | attempt | The first visible move is to mark urgency and owner before routing. | marks urgency and owner before routing | ENT-hero, ENT-target changes: ENT-target:ordered queue=blocked; ENT-proof:priority rule=hidden → ENT-target:ordered queue=acted-on; ENT-proof:priority rule=hidden. | over_shoulder / pan_right | voice_over / demonstrate_process | Show an attempted causal operation on the target. |
| 4–5s | proof | Check the priority rule, not the claim. | checks the priority rule | ENT-proof, ENT-target changes: ENT-target:ordered queue=acted-on; ENT-proof:priority rule=hidden → ENT-target:ordered queue=changed-pending-review; ENT-proof:priority rule=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | handback | The bounded result: the urgent item reaches the correct lane. | returns the resolved target to the viewer | ENT-hero, ENT-target changes: ENT-target:ordered queue=changed-pending-review; ENT-proof:priority rule=visible → ENT-target:ordered queue=resolved-with-boundary; ENT-proof:priority rule=visible. | medium / pull_out | return_cut / emotional_texture | Close the visual argument and hand it back. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
