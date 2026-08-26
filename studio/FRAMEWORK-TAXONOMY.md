# Studio Short-form Taxonomy v1

Framework identity is the tuple of controlled semantic, visual, temporal, and delivery axes—not its title, subject, color, or copy.

## Controlled axes

| Axis | Question answered |
|---|---|
| `hook_mechanism` | What creates the opening information gap or promise? |
| `viewer_job` | What should the viewer be able to do after watching? |
| `broll_function` | Why does the cutaway exist in the story? |
| `proof_form` | What makes the beat inspectable? |
| `visual_grammar` | How is information arranged on the 9:16 canvas? |
| `pacing_profile` | How quickly are meaningful states introduced? |
| `transition_family` | How are adjacent states connected? |
| `a_roll_integration` | Where is the speaking human visible or audible? |
| `sound_role` | What does audio do besides carry dialogue? |
| `text_role` | What job does editable on-screen text perform? |
| `cta_exit` | How does the short insert hand back to the main video? |
| `risk_class` | What claim, source, rights, or identity risk must be reviewed? |

The exact enums are machine-owned by `schemas/studio-framework.schema.json`.

## Timing invariants

- Duration: 4–12 seconds for reusable inserts.
- First state starts at 0 ms; final state ends at `duration_ms`.
- Every interval is positive and contiguous.
- The hook signal appears during 0–1000 ms.
- One frame represents one meaningful visual state, not an arbitrary sample frame.
- B-roll declares its function and A-roll state.
- Text/caption/sound changes align to a state boundary or receive their own timecode.
- The final beat either exits, returns to A-roll, recaps, or intentionally loops.

## Clean-room duplicate rejection

Reject:

- exact taxonomy tuple duplicates;
- variants that only change wording, color, font, soundtrack, or subject;
- the same hook, viewer job, proof form, visual grammar, and beat order;
- any candidate that depends on recognizable source wording, composition, metaphor, sequence, UI, music, voice, likeness, or creator style.

For candidates sharing a hook family, require at least three changed axes, including `viewer_job`, one of `broll_function`/`proof_form`/`visual_grammar`, and one temporal/delivery axis.

## Library composition

Version 1 contains 60 frameworks across 10 families:

1. pattern interrupt;
2. diagnostic question;
3. contradiction;
4. consequence;
5. before/after;
6. countdown/list;
7. object demonstration;
8. proof reveal;
9. story in progress;
10. process B-roll.

Each family has six variants with distinct viewer job, B-roll function, proof form, visual grammar, and delivery treatment.
