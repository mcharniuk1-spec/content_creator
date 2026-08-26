# ST-003 — The Stale Dashboard

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A revenue analyst must explain a sudden metric change despite the visible chart is two weeks stale, because the team could act on the wrong period; the story resolves when the stale chart is clearly quarantined.

## Story spine

- Setup: a monitor wall
- Inciting change: The calendar changes state before the objective is secure.
- Objective: explain a sudden metric change
- Obstacle: the visible chart is two weeks stale
- Stakes: the team could act on the wrong period
- Action: notice the calendar → checks the timestamp before interpreting → inspect the freshness timestamp
- Proof: freshness timestamp
- Limitation: Freshness enables analysis; it does not prove causality.
- Payoff: the stale chart is clearly quarantined

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the calendar | ENT-trigger changes: ENT-target:current chart=absent; ENT-proof:freshness timestamp=hidden → ENT-target:current chart=unoriented; ENT-proof:freshness timestamp=hidden. | extreme_close / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to explain a sudden metric change. | locates the current chart | ENT-target changes: ENT-target:current chart=unoriented; ENT-proof:freshness timestamp=hidden → ENT-target:current chart=present-unresolved; ENT-proof:freshness timestamp=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But the visible chart is two weeks stale. | sees the current chart blocked | ENT-obstacle, ENT-target changes: ENT-target:current chart=present-unresolved; ENT-proof:freshness timestamp=hidden → ENT-target:current chart=blocked; ENT-proof:freshness timestamp=hidden. | medium / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | attempt | The first visible move is to check the timestamp before interpreting. | checks the timestamp before interpreting | ENT-hero, ENT-target changes: ENT-target:current chart=blocked; ENT-proof:freshness timestamp=hidden → ENT-target:current chart=acted-on; ENT-proof:freshness timestamp=hidden. | over_shoulder / pan_right | voice_over / demonstrate_process | Show an attempted causal operation on the target. |
| 4–5s | proof | Check the freshness timestamp, not the claim. | checks the freshness timestamp | ENT-proof, ENT-target changes: ENT-target:current chart=acted-on; ENT-proof:freshness timestamp=hidden → ENT-target:current chart=changed-pending-review; ENT-proof:freshness timestamp=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | handback | The bounded result: the stale chart is clearly quarantined. | returns the resolved target to the viewer | ENT-hero, ENT-target changes: ENT-target:current chart=changed-pending-review; ENT-proof:freshness timestamp=visible → ENT-target:current chart=resolved-with-boundary; ENT-proof:freshness timestamp=visible. | medium / pull_out | return_cut / emotional_texture | Close the visual argument and hand it back. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
