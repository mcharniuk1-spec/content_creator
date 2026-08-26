# ST-002 — Approval at the Threshold

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A content operator must publish only after review despite the publish control is active before approval, because an unsupported claim could escape; the story resolves when the risky control stays locked.

## Story spine

- Setup: an edit bay
- Inciting change: The lock changes state before the objective is secure.
- Objective: publish only after review
- Obstacle: the publish control is active before approval
- Stakes: an unsupported claim could escape
- Action: notice the lock → moves the draft behind a review gate → inspect the signed review card
- Proof: signed review card
- Limitation: The scene does not authorize real publication.
- Payoff: the risky control stays locked

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the lock | ENT-trigger changes: ENT-target:safe publish gate=absent; ENT-proof:signed review card=hidden → ENT-target:safe publish gate=unoriented; ENT-proof:signed review card=hidden. | extreme_close / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to publish only after review. | locates the safe publish gate | ENT-target changes: ENT-target:safe publish gate=unoriented; ENT-proof:signed review card=hidden → ENT-target:safe publish gate=present-unresolved; ENT-proof:signed review card=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But the publish control is active before approval. | sees the safe publish gate blocked | ENT-obstacle, ENT-target changes: ENT-target:safe publish gate=present-unresolved; ENT-proof:signed review card=hidden → ENT-target:safe publish gate=blocked; ENT-proof:signed review card=hidden. | medium / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | attempt | The first visible move is to move the draft behind a review gate. | moves the draft behind a review gate | ENT-hero, ENT-target changes: ENT-target:safe publish gate=blocked; ENT-proof:signed review card=hidden → ENT-target:safe publish gate=acted-on; ENT-proof:signed review card=hidden. | over_shoulder / pan_right | voice_over / demonstrate_process | Show an attempted causal operation on the target. |
| 4–5s | proof | Check the signed review card, not the claim. | checks the signed review card | ENT-proof, ENT-target changes: ENT-target:safe publish gate=acted-on; ENT-proof:signed review card=hidden → ENT-target:safe publish gate=changed-pending-review; ENT-proof:signed review card=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | handback | The bounded result: the risky control stays locked. | returns the resolved target to the viewer | ENT-hero, ENT-target changes: ENT-target:safe publish gate=changed-pending-review; ENT-proof:signed review card=visible → ENT-target:safe publish gate=resolved-with-boundary; ENT-proof:signed review card=visible. | medium / pull_out | return_cut / emotional_texture | Close the visual argument and hand it back. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
