# ST-009 — The Clearer Screen

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`

## Logline

A product educator must explain one interface state despite every control is highlighted at once, because the viewer cannot locate the next action; the story resolves when one control carries the explanation.

## Story spine

- Setup: a demo workstation
- Inciting change: The cursor changes state before the objective is secure.
- Objective: explain one interface state
- Obstacle: every control is highlighted at once
- Stakes: the viewer cannot locate the next action
- Action: notice the cursor → rewinds from a clean state to excess overlays → inspect the focus highlight
- Proof: focus highlight
- Limitation: The interface is a generic mock, not branded UI.
- Payoff: one control carries the explanation

## Second-by-second screenplay

| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |
|---|---|---|---|---|---|---|---|
| 0–1s | hook | The state changed before anyone was ready. | notices the cursor | ENT-trigger changes: ENT-target:single-action screen=absent; ENT-proof:focus highlight=hidden → ENT-target:single-action screen=resolved-preview; ENT-proof:focus highlight=hidden. | close / pull_out | full / attention_reset | Open a precise question with a visible changed object. |
| 1–2s | orientation | The objective is to explain one interface state. | locates the single-action screen | ENT-target changes: ENT-target:single-action screen=resolved-preview; ENT-proof:focus highlight=hidden → ENT-target:single-action screen=present-unresolved; ENT-proof:focus highlight=hidden. | wide / whip_pan | voice_over / establish_context | Reveal actor, target, and spatial relationship. |
| 2–3s | obstacle | But every control is highlighted at once. | sees the single-action screen blocked | ENT-obstacle, ENT-target changes: ENT-target:single-action screen=present-unresolved; ENT-proof:focus highlight=hidden → ENT-target:single-action screen=blocked; ENT-proof:focus highlight=hidden. | medium / locked | voice_over / concretize_abstraction | Make resistance and consequence inspectable. |
| 3–4s | mechanism | The decisive mechanism is to rewind from a clean state to excess overlays. | rewinds from a clean state to excess overlays | ENT-hero, ENT-target changes: ENT-target:single-action screen=blocked; ENT-proof:focus highlight=hidden → ENT-target:single-action screen=transformed; ENT-proof:focus highlight=hidden. | over_shoulder / pan_right | voice_over / demonstrate_process | Show the mechanism transforming the persistent target. |
| 4–5s | proof | Check the focus highlight, not the claim. | checks the focus highlight | ENT-proof, ENT-target changes: ENT-target:single-action screen=transformed; ENT-proof:focus highlight=hidden → ENT-target:single-action screen=changed-pending-review; ENT-proof:focus highlight=visible. | macro / rack_focus | voice_over / prove_state | Bind the changed target to an inspectable proof object. |
| 5–6s | payoff | Now one control carries the explanation. | confirms the changed single-action screen | ENT-target changes: ENT-target:single-action screen=changed-pending-review; ENT-proof:focus highlight=visible → ENT-target:single-action screen=resolved-with-boundary; ENT-proof:focus highlight=visible. | wide / pull_out | return_cut / contrast | Close the opening question with the changed target. |

## Read test

Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.
