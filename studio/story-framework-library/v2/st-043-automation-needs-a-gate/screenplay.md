# ST-043 — Automation Needs a Gate

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A system owner must let routine work move safely despite the agent cannot recognize every edge case, because an exception could become an external action; the story resolves when speed and review coexist.

## Story spine

- Setup: an automation lane
- Inciting change: The robot arm changes state before the objective is secure.
- Objective: let routine work move safely
- Obstacle: the agent cannot recognize every edge case
- Stakes: an exception could become an external action
- Action: notice the robot arm → routes normal cases forward and exceptions aside → inspect the human gate
- Proof: human gate
- Limitation: The gate requires a real escalation owner.
- Payoff: speed and review coexist

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the robot arm | ENT-trigger changes: ENT-target:controlled flow=absent; ENT-proof:human gate=hidden → ENT-target:controlled flow=unoriented; ENT-proof:human gate=hidden. | wide / locked | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to let routine work move safely. | locates the controlled flow | ENT-target changes: ENT-target:controlled flow=unoriented; ENT-proof:human gate=hidden → ENT-target:controlled flow=present-unresolved; ENT-proof:human gate=hidden. | medium / push_in | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But the agent cannot recognize every edge case. | sees the controlled flow blocked | ENT-obstacle, ENT-target changes: ENT-target:controlled flow=present-unresolved; ENT-proof:human gate=hidden → ENT-target:controlled flow=blocked; ENT-proof:human gate=hidden. | close / pan_left | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | mechanism | The decisive mechanism is to route normal cases forward and exceptions aside. | routes normal cases forward and exceptions aside | ENT-hero, ENT-target changes: ENT-target:controlled flow=blocked; ENT-proof:human gate=hidden → ENT-target:controlled flow=transformed; ENT-proof:human gate=hidden. | diagram / tilt_down | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 4–5s | proof | Check the human gate, not the claim. | checks the human gate | ENT-proof, ENT-target changes: ENT-target:controlled flow=transformed; ENT-proof:human gate=hidden → ENT-target:controlled flow=changed-pending-review; ENT-proof:human gate=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | payoff | Now speed and review coexist. | confirms the changed controlled flow | ENT-target changes: ENT-target:controlled flow=changed-pending-review; ENT-proof:human gate=visible → ENT-target:controlled flow=resolved-with-boundary; ENT-proof:human gate=visible. | wide / pull_out | return_cut / contrast | Close the opening question with the changed target. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
