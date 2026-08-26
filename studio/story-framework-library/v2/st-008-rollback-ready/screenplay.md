# ST-008 — Rollback Ready

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A local operator must prove a change is reversible despite the forward path has no recovery step, because a small error could become persistent; the story resolves when the change remains bounded.

## Story spine

- Setup: a deployment bench
- Inciting change: The reverse arrow changes state before the objective is secure.
- Objective: prove a change is reversible
- Obstacle: the forward path has no recovery step
- Stakes: a small error could become persistent
- Action: notice the reverse arrow → rewinds from recovery to the missing backup → inspect the rollback test
- Proof: rollback test
- Limitation: A storyboard does not execute deployment.
- Payoff: the change remains bounded

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the reverse arrow | ENT-trigger changes: ENT-target:safe change set=absent; ENT-proof:rollback test=hidden → ENT-target:safe change set=resolved-preview; ENT-proof:rollback test=hidden. | close / pull_out | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to prove a change is reversible. | locates the safe change set | ENT-target changes: ENT-target:safe change set=resolved-preview; ENT-proof:rollback test=hidden → ENT-target:safe change set=present-unresolved; ENT-proof:rollback test=hidden. | wide / whip_pan | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But the forward path has no recovery step. | sees the safe change set blocked | ENT-obstacle, ENT-target changes: ENT-target:safe change set=present-unresolved; ENT-proof:rollback test=hidden → ENT-target:safe change set=blocked; ENT-proof:rollback test=hidden. | medium / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | mechanism | The decisive mechanism is to rewind from recovery to the missing backup. | rewinds from recovery to the missing backup | ENT-hero, ENT-target changes: ENT-target:safe change set=blocked; ENT-proof:rollback test=hidden → ENT-target:safe change set=transformed; ENT-proof:rollback test=hidden. | over_shoulder / pan_right | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 4–5s | proof | Check the rollback test, not the claim. | checks the rollback test | ENT-proof, ENT-target changes: ENT-target:safe change set=transformed; ENT-proof:rollback test=hidden → ENT-target:safe change set=changed-pending-review; ENT-proof:rollback test=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | payoff | Now the change remains bounded. | confirms the changed safe change set | ENT-target changes: ENT-target:safe change set=changed-pending-review; ENT-proof:rollback test=visible → ENT-target:safe change set=resolved-with-boundary; ENT-proof:rollback test=visible. | wide / pull_out | return_cut / contrast | Close the opening question with the changed target. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
