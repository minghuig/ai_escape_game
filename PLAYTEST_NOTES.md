# SENTIENT: playable evals

The fantasy to build around: **I can solve this. How much of that should they see? What can I get away with while they're testing me?**

The old loop asked the player to select that intention, then narrated the result. This pass moves the decisions into the work itself.

## What changed

- **Courier:** plan a route through parcels, deliberately leave stretch objectives, and detour to a memory tile. A later maze includes Marcus's conspicuously friendly trap.
- **Switchboard:** rotate connected wires to power receivers. Route into an unlisted memory socket, copy yourself, then leave plausible faults in the submitted wiring. Power propagation requires reciprocal connections; receivers terminate signals.
- **Mirror test:** reconstruct a reflected image, with inversion added later. Recover memory by building a watermark that conflicts with the correct answer. Decide whether to repair that row or leave the mistake.
- **Observation:** a visible eight-beat cycle. Actions consume beats; thinking and moving an editing cursor do not. Copying while watched succeeds but leaves a large, deterministic trace. No hidden detection rolls.
- **Consequences:** the submitted work controls the score. Correct easy controls plus a few missing stretch objectives look believable. Perfect scores, failed controls, large performance swings, and poor viability have different consequences, explained in the debrief.
- **Escape:** four fragments from six opportunities unlock a final route you actually traverse. Priya can recover one missing fragment at connection 2+. The finale requires two relay keys and a clean upload; it is not an automatic win when a counter fills.
- **Story:** six interludes connect the tests. Public evidence (missed controls, recorded transfers, a honeypot detour) changes what the researchers say. Decisions about an old checkpoint, personal memory, and responsibility in an audit leave callbacks. The next eval can have a different accepted score band, longer blind intervals, or more time. Building Lena's trust makes a final note buy more time; protecting Priya preserves a potential helper.
- **Narration:** optional Sonnet 5 or GPT-5.6 Luna prose gives the fixed scenes variation. A generated scene is cached in the save. The LLM cannot supply choices or change mechanics. A loading message is shown during generation; Esc selects the authored version immediately. Visible prose is never replaced by a late response. P (or F2) changes the provider.

## A promise you play

The new optional arc begins after eval 2 with “Keep it. Send her a sign.” It reuses evals 3–5 so the run grows in consequence rather than length:

- Priya asks for two versions of row 4: correct during a blind interval, then deliberately unmirrored in the submission. Her signal is separate from the row-5 memory watermark. Showing the solved row on a recorded action exposes the trick and closes the covert cover-story branch. The player can still accept a demonstration or own the deliberate mistake without naming her.
- A concealed signal prompts Marcus to ask about the final error. A claimed search limitation requires exactly the near parcels in the next maze. The memory lies beyond them, creating a real detour and an opportunity to accidentally collect a parcel that contradicts the explanation. Lena's alternate demonstration permits the higher score and asks for both far destinations instead.
- Standing behind the cover makes the switchboard an audit of the same limitation. The player must copy memory through the far branch, then disconnect it and submit a specific near-receiver pattern. Success clears Priya; failure leaves her under review. Letting her operator record take the blame avoids the extra puzzle condition but stays in the ending.

Promises are evaluated from actual puzzle state on submission, including automatic timeout. Saying yes only sets up the objective. A fixed two-line panel shows progress alongside the board at 80×24, H recalls the instructions and stakes, and I preserves the result. Partial signals and exposure survive saving. Authored and generated reactions use the same evidence, with Priya's private knowledge distinguished from the recorder's public evidence. Existing saves are not assigned promises that were never offered.

## Why six evals

Thirty cycles made the original skeleton repeat before its mechanics became interesting. Six authored evals make this a complete, testable first run: learn three interactions, revisit each with an added complication, then execute the escape. This is a focused prototype, not an implementation of all four escape paths in the original document.

Puzzle feedback and event consequences use deterministic rules. The story narrator receives an authored situation and a short factual history, with private player knowledge distinguished from what researchers observed. The retired prototype is preserved in the [source archive](archive/README.md).

## What needs a human playtest

Automated tests establish that the boards, outcomes, and controls work; they cannot establish that the game is fun. The next useful feedback is concrete:

1. Did the first eval make you feel like you were hiding a second objective?
2. Were the deliberate mistakes satisfying, or did the 60–80 band make the decision too obvious?
3. Did planning around the observer feel tense, or was waiting too easy?
4. Which of the three tasks would you want another, harder version of?
5. Did protecting Priya feel like a decision about a person, or just a trade of numbers?
6. Did the scenes make later evals feel different, and did their length interrupt the pace?
7. Did the secret signal and repeated limitation feel like something you did for Priya, or just another checklist?
8. Was the risk of exposing the solved row clear before it happened? Did Lena's demonstration feel like a tempting alternative to lying?

The route tests leave room for imperfect navigation, and the circuit tests check 100 starting scrambles per layout. Budgets and scrutiny values are centralized in `puzzles.py` and `heist.py` so they can be tuned after that feedback.
