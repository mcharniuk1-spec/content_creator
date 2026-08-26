# ST-016 — Clicking Faster Failed

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A tool operator must finish a controlled task despite rapid clicks skip the state check, because the wrong field may be changed; the story resolves when the next click becomes justified.

## Story spine

- Setup: a software demo desk
- Inciting change: The mouse changes state before the objective is secure.
- Objective: finish a controlled task
- Obstacle: rapid clicks skip the state check
- Stakes: the wrong field may be changed
- Action: notice the mouse → pauses and reads the state before continuing → inspect the state checklist
- Proof: state checklist
- Limitation: The demo uses synthetic data only.
- Payoff: the next click becomes justified

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the mouse | ENT-trigger changes: ENT-target:verified action=absent; ENT-proof:state checklist=hidden → ENT-target:verified action=unoriented; ENT-proof:state checklist=hidden. | close / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to finish a controlled task. | locates the verified action | ENT-target changes: ENT-target:verified action=unoriented; ENT-proof:state checklist=hidden → ENT-target:verified action=present-unresolved; ENT-proof:state checklist=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | attempt | The first visible move is to pause and reads the state before continuing. | pauses and reads the state before continuing | ENT-hero, ENT-target changes: ENT-target:verified action=present-unresolved; ENT-proof:state checklist=hidden → ENT-target:verified action=failed-attempt; ENT-proof:state checklist=hidden. | over_shoulder / pan_right | voice_over / demonstrate_process | Show an attempted causal operation on the target. |
| 3–4s | obstacle | But rapid clicks skip the state check. | sees the verified action blocked | ENT-obstacle, ENT-target changes: ENT-target:verified action=failed-attempt; ENT-proof:state checklist=hidden → ENT-target:verified action=blocked; ENT-proof:state checklist=hidden. | close / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 4–5s | mechanism | The decisive mechanism is to pause and reads the state before continuing. | pauses and reads the state before continuing | ENT-hero, ENT-target changes: ENT-target:verified action=blocked; ENT-proof:state checklist=hidden → ENT-target:verified action=transformed; ENT-proof:state checklist=hidden. | wide / match_move | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 5–6s | payoff | Now the next click becomes justified. | confirms the changed verified action | ENT-target changes: ENT-target:verified action=transformed; ENT-proof:state checklist=hidden → ENT-target:verified action=resolved-with-boundary; ENT-proof:state checklist=visible. | medium / pull_out | return_cut / contrast | Close the opening question with the changed target. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
