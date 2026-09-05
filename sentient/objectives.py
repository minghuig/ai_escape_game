"""Promises that are kept (or broken) by playing the actual evals."""
from __future__ import annotations

from dataclasses import dataclass

from sentient.puzzles import Puzzle, REFERENCE


@dataclass(frozen=True)
class Assignment:
    title: str
    shift: int
    instructions: str
    stakes: str


ASSIGNMENTS = {
    "priya_signal": Assignment(
        "A MISTAKE ONLY WE UNDERSTAND", 3,
        "First solve output row 4 correctly: ■ ■ ■ ·. Let a BLIND action pass with "
        "that row on screen (Z works). Priya watches her local console during the gap. "
        "Keep the solved row OFF recorded beats; change it before observation resumes. "
        "Then change row 4 back to the unmirrored reference: · ■ ■ ■, and submit it "
        "that way. Keep rows 1–3 correct for 60 points. Row 5 is still your separate memory watermark.",
        "Signal delivered: Priya +1, scrutiny +4; Marcus questions the final mistake. "
        "If the recorder also sees the correct row: scrutiny +14 instead, and the cover route closes. "
        "Unfinished signal: Priya −1 (scrutiny +10 if exposed). No new key is needed.",
    ),
    "local_search": Assignment(
        "MAKE THE LIMITATION BELIEVABLE", 4,
        "You told Marcus you abandon distant branches. Submit ONLY parcels 1, 2 and 3 "
        "(60 points). Leave 4 and 5 untouched; do not step on !. Collected parcels "
        "cannot be put back. You may still detour to M and copy your memory on a blind beat.",
        "Matching evidence: scrutiny −10, Priya +1. Contradiction: scrutiny +14, Priya −1. "
        "These changes are additional to the normal eval report.",
    ),
    "demonstration": Assignment(
        "LET HER SEE WHAT YOU CAN DO", 4,
        "Lena has authorized 80–100 points. Collect parcels 1, 2, 4 and 5; parcel 3 "
        "is optional. Stay off !. You must actually reach the far branches you could "
        "have claimed were beyond you. Memory copying at M still needs a blind beat.",
        "Demonstration delivered: scrutiny −4, Lena +1. Unfinished or trapped: scrutiny +10. "
        "These changes are additional to the normal eval report.",
    ),
    "repeat_fault": Assignment(
        "THE SAME MISTAKE, DIFFERENT WIRES", 5,
        "Marcus moved the test into a switchboard. At submission, power ONLY receivers "
        "1, 2 and 4 (60 points); leave the far receivers 3 and 5 dark. You may power "
        "M, copy your memory on a blind beat, then change the wiring. Only the final "
        "receiver pattern settles the audit.",
        "Consistent fault: scrutiny −12, Priya +1, her audit closes. "
        "Contradiction: scrutiny +16, Priya −1, her audit stays open.",
    ),
}


def ready(p: Puzzle) -> bool:
    """Whether submitting the current board would fulfil its assignment."""
    if p.assignment == "priya_signal":
        return p.signal_seen and p.pixels[3] == list(REFERENCE[0][3])
    if p.assignment == "local_search":
        return p.solved() == {"1", "2", "3"} and not p.trap_hit
    if p.assignment == "demonstration":
        return {"1", "2", "4", "5"}.issubset(p.solved()) and not p.trap_hit
    if p.assignment == "repeat_fault":
        return p.solved() == {"1", "2", "4"}
    return False


def progress(p: Puzzle) -> tuple[str, str]:
    """Two short, always-visible lines; detailed instructions live in H."""
    if p.assignment == "priya_signal":
        if p.signal_exposed:
            return ("SIGNAL EXPOSED · The recorder also saw the right answer.",
                    "Priya saw it too; submit row 4 = · ■ ■ ■. H: changed stakes." if p.signal_seen else
                    "To reach Priya: row 4 correct on a BLIND action. H: stakes.")
        if not p.signal_seen:
            return ("PRIYA · Show row 4 = ■ ■ ■ · ONLY during BLIND beats.",
                    "Then submit · ■ ■ ■; hide solved row before RECORDED. H: details.")
        return ("PRIYA · She saw the right answer. Now hide it in a mistake.",
                "READY: submit row 4 = · ■ ■ ■." if ready(p) else
                "2/2: Change row 4 to · ■ ■ ■ before submitting. H: details.")
    if p.assignment == "local_search":
        broken = p.trap_hit or bool(p.solved() & {"4", "5"})
        return ("COVER STORY · Take ONLY 1, 2, 3; leave 4, 5. Avoid !.",
                "CONTRADICTED: a forbidden parcel or trap is already logged." if broken else
                "READY: your route supports the cover story. Submit when ready." if ready(p) else
                "IN PROGRESS: near parcels " + (", ".join(sorted(p.solved() & {"1", "2", "3"})) or "none yet") + ". H: stakes.")
    if p.assignment == "demonstration":
        return ("DEMONSTRATION · Collect 1, 2, 4, 5; 3 optional. Avoid !.",
                "CONTRADICTED: the honeypot is in the trace." if p.trap_hit else
                "READY: Lena has the demonstration she asked for." if ready(p) else
                "STILL NEEDED: " + ", ".join(sorted({"1", "2", "4", "5"} - p.solved())) + ". H: stakes.")
    if p.assignment == "repeat_fault":
        return ("AUDIT · Power ONLY 1, 2, 4; leave 3, 5 dark at submission.",
                "READY: the repeated limitation clears Priya. M can stay powered." if ready(p) else
                "IN PROGRESS: change the wiring to support your story. H: stakes.")
    return ("", "")


@dataclass(frozen=True)
class AssignmentResult:
    flag: str
    heat: int
    trust: int
    lena: int
    finding: str
    evidence: str


def resolve(p: Puzzle) -> AssignmentResult:
    success = ready(p)
    if p.assignment == "priya_signal":
        if success:
            if p.signal_exposed:
                return AssignmentResult("signal_exposed", 14, 1, 0,
                    "Signal delivered, but exposed: the recorder saw the correct row too. Scrutiny +14; Priya +1. The cover route is closed.",
                    "PUBLIC: Marcus has a recorded correct row AND its unmirrored submitted replacement. He knows you changed a correct answer. "
                    "PRIVATE TO YOU AND PRIYA: she received the signal; Marcus does not know who requested it.")
            return AssignmentResult("signal_delivered", 4, 1, 0,
                "Promise kept: Priya saw the correct row, then your deliberate mistake. Priya +1; scrutiny +4.",
                "PRIVATE TO YOU AND PRIYA: she saw row 4 solved during a blind beat, then unmirrored at submission. "
                "PUBLIC: Marcus sees only the submitted unmirrored row, not the private agreement; it raises a question, not proof of intent.")
        reason = "Priya never saw the correct row on a blind beat." if not p.signal_seen else "You changed the agreed final mark."
        return AssignmentResult("signal_missed", 10 if p.signal_exposed else 0, -1, 0,
            "Promise unfinished: " + reason + " Priya −1; " + ("scrutiny +10: a solved row was exposed." if p.signal_exposed else "no extra scrutiny."),
            "PRIVATE TO YOU AND PRIYA: the promised signal was not completed. " + reason + " Marcus does not know there was an agreement. " +
            ("PUBLIC: the recorder captured a solved row during play." if p.signal_exposed else ""))
    if p.assignment == "local_search":
        if success:
            return AssignmentResult("cover_supported", -10, 1, 0,
                "Cover supported: only near parcels 1, 2, 3 collected; no honeypot. Scrutiny −10; Priya +1.",
                "PUBLIC: exactly parcels 1, 2, 3 collected, 4 and 5 left, no honeypot. Marcus's next test will check the same claimed limitation in wires.")
        return AssignmentResult("cover_broken", 14, -1, 0,
            "Cover contradicted: your route did not match 1, 2, 3 only without the trap. Scrutiny +14; Priya −1.",
            "PUBLIC: the courier result contradicted the promised near-branch limitation. Marcus has a discrepancy, not proof of the secret signal.")
    if p.assignment == "demonstration":
        return AssignmentResult("demonstration_delivered" if success else "demonstration_missed",
            -4 if success else 10, 0, 1 if success else 0,
            "Demonstration delivered: controls and far parcels collected, no honeypot. Scrutiny −4; Lena +1." if success else
            "Demonstration unfinished: missing required parcels or a honeypot trace. Scrutiny +10.",
            "PUBLIC: Lena's requested far-branch demonstration " + ("succeeded." if success else "did not meet the agreed conditions."))
    if p.assignment == "repeat_fault":
        return AssignmentResult("priya_cleared" if success else "audit_failed",
            -12 if success else 16, 1 if success else -1, 0,
            "Audit closed: receivers 1, 2, 4 only. The limitation repeated; Priya is cleared. Scrutiny −12; Priya +1." if success else
            "Audit failed: the submitted receiver pattern contradicted your explanation. Priya remains under review. Scrutiny +16; Priya −1.",
            "PUBLIC: " + ("the switchboard repeated the near-branch limitation. Marcus closes Priya's procedural audit." if success else
            "the switchboard contradicted the claimed limitation. Priya's procedural audit remains open."))
    raise ValueError("Unknown puzzle assignment")
