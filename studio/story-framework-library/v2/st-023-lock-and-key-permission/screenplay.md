# ST-023 — Lock and Key Permission

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A safety reviewer must explain why access and approval differ despite the key exists without permission to turn it, because a capability could be mistaken for authority; the story resolves when the door opens only when both states align.

## Story spine

- Setup: a controlled doorway
- Inciting change: The key changes state before the objective is secure.
- Objective: explain why access and approval differ
- Obstacle: the key exists without permission to turn it
- Stakes: a capability could be mistaken for authority
- Action: notice the key → pairs the key with a separate approval marker → inspect the approval token
- Proof: approval token
- Limitation: The metaphor does not model every permission layer.
- Payoff: the door opens only when both states align

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the key | ENT-trigger changes: ENT-target:opened gate=absent; ENT-proof:approval token=hidden → ENT-target:opened gate=unoriented; ENT-proof:approval token=hidden. | macro / push_in | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to explain why access and approval differ. | locates the opened gate | ENT-target changes: ENT-target:opened gate=unoriented; ENT-proof:approval token=hidden → ENT-target:opened gate=present-unresolved; ENT-proof:approval token=hidden. | wide / pull_out | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | mechanism | The decisive mechanism is to pair the key with a separate approval marker. | pairs the key with a separate approval marker | ENT-hero, ENT-target changes: ENT-target:opened gate=present-unresolved; ENT-proof:approval token=hidden → ENT-target:opened gate=transformed; ENT-proof:approval token=hidden. | medium / tilt_down | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 3–4s | obstacle | But the key exists without permission to turn it. | sees the opened gate blocked | ENT-obstacle, ENT-target changes: ENT-target:opened gate=transformed; ENT-proof:approval token=hidden → ENT-target:opened gate=blocked; ENT-proof:approval token=hidden. | close / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 4–5s | proof | Check the approval token, not the claim. | checks the approval token | ENT-proof, ENT-target changes: ENT-target:opened gate=blocked; ENT-proof:approval token=hidden → ENT-target:opened gate=changed-pending-review; ENT-proof:approval token=visible. | diagram / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | handback | The bounded result: the door opens only when both states align. | returns the resolved target to the viewer | ENT-hero, ENT-target changes: ENT-target:opened gate=changed-pending-review; ENT-proof:approval token=visible → ENT-target:opened gate=resolved-with-boundary; ENT-proof:approval token=visible. | medium / pull_out | return_cut / emotional_texture | Close the visual argument and hand it back. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
