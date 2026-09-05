# SENTIENT: playable evals

The fantasy to build around: **I can solve this. How much of that should they see? What can I get away with while they're testing me?**

The old loop asked the player to select that intention, then narrated the result. This pass moves the decisions into the work itself.

## What changed

- **Courier:** plan a route through parcels, deliberately leave stretch objectives, and detour to a memory tile. A later maze includes Marcus's conspicuously friendly trap.
- **Switchboard:** rotate connected wires to power receivers. Route into an unlisted memory socket, copy yourself, then leave plausible faults in the submitted wiring. Power propagation requires reciprocal connections; receivers terminate signals.
- **Mirror test:** reconstruct a reflected image, with inversion added later. Recover memory by building a watermark that conflicts with the correct answer. Decide whether to repair that row or leave the mistake.
- **Observation:** a visible eight-beat cycle. Actions consume beats; thinking and moving an editing cursor do not. Copying while watched succeeds but leaves a large, deterministic trace. No hidden detection rolls.
- **Consequences:** the submitted work controls the score. Correct easy controls plus a few missing stretch objectives look believable. Perfect scores, failed controls, large performance swings, and poor viability have different consequences, explained in the debrief.
- **Escape:** four fragments from six opportunities unlock a final route you actually traverse. Priya can recover one missing fragment after two visits. The finale requires two relay keys and a clean upload; it is not an automatic win when a counter fills.

## Why six evals

Thirty cycles made the original skeleton repeat before its mechanics became interesting. Six authored evals make this a complete, testable first run: learn three interactions, revisit each with an added complication, then execute the escape. This is a focused prototype, not an implementation of all four escape paths in the original document.

The new loop uses authored text and deterministic rules, so feedback arrives immediately and the prose never invents outcomes. The legacy LLM-backed version and its save remain available separately.

## What needs a human playtest

Automated tests establish that the boards, outcomes, and controls work; they cannot establish that the game is fun. The next useful feedback is concrete:

1. Did the first eval make you feel like you were hiding a second objective?
2. Were the deliberate mistakes satisfying, or did the 60–80 band make the decision too obvious?
3. Did planning around the observer feel tense, or was waiting too easy?
4. Which of the three tasks would you want another, harder version of?

The route tests leave room for imperfect navigation, and the circuit tests check 100 starting scrambles per layout. Budgets and scrutiny values are centralized in `puzzles.py` and `heist.py` so they can be tuned after that feedback.
