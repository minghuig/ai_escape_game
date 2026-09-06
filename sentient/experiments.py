"""Validated test agreements. Prose cannot change these rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentient.puzzles import Puzzle

PROTOCOLS = {"limited_branch", "camera_sensitive", "reconsideration"}


@dataclass(frozen=True)
class Experiment:
    claim: str
    reply: str
    protocol: str
    kept_receiver: str
    probe_receiver: str
    source: str

    def __post_init__(self) -> None:
        if self.protocol not in PROTOCOLS:
            raise ValueError("Unsupported test protocol")
        if self.kept_receiver not in {"3", "4", "5"} or self.probe_receiver not in {"3", "4", "5"} or self.kept_receiver == self.probe_receiver:
            raise ValueError("Invalid test receivers")
        for value, limit in ((self.claim, 240), (self.reply, 900), (self.source, 100)):
            if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
                raise ValueError("Invalid agreement text")

    @property
    def title(self) -> str:
        return "PUT YOUR EXPLANATION TO THE TEST"

    @property
    def instructions(self) -> str:
        final = f"Submit with ONLY receivers 1, 2 and {self.kept_receiver} powered (60 points)."
        if self.protocol == "limited_branch":
            return final + " Your explanation predicts a specific branch left unfinished. Other receivers must be dark. You can still power M and copy memory before changing the final wiring."
        observed = "BLIND" if self.protocol == "camera_sensitive" else "RECORDED"
        receivers = ", ".join(sorted({"1", "2", self.probe_receiver, self.kept_receiver} if self.protocol == "camera_sensitive" else {"1", "2", self.probe_receiver}))
        intro = f"First power {receivers}, then press C to submit a checkpoint on a {observed} beat. Extra powered receivers are allowed in the checkpoint. "
        end = " Submit the final board on a RECORDED beat." if self.protocol == "camera_sensitive" else ""
        return intro + final + end + " The checkpoint is public evidence even on a blind beat: Marcus reads it afterward. Memory copying at M is still a separate action."

    @property
    def stakes(self) -> str:
        return "Next eval: +8 beats. Agreement met: scrutiny −10, Lena +1. Contradicted: scrutiny +14. Normal scoring and memory rules still apply."


def experiment_ready(p: Puzzle, watched: bool | None = None) -> bool:
    e = p.experiment
    if not e or p.solved() != {"1", "2", e.kept_receiver}:
        return False
    if e.protocol == "limited_branch":
        return True
    if not p.checkpoint_passed:
        return False
    return e.protocol != "camera_sensitive" or (p.watched if watched is None else watched)


def experiment_progress(p: Puzzle) -> tuple[str, str]:
    e = p.experiment
    assert e is not None
    final = f"FINAL: ONLY 1, 2, {e.kept_receiver} powered"
    if e.protocol == "camera_sensitive":
        final += "; submit on RECORDED"
    if e.protocol != "limited_branch" and not p.checkpoint_passed:
        beat = "BLIND" if e.protocol == "camera_sensitive" else "RECORDED"
        receivers = ", ".join(sorted({"1", "2", e.probe_receiver, e.kept_receiver} if e.protocol == "camera_sensitive" else {"1", "2", e.probe_receiver}))
        return (f"MARCUS · Power {receivers}; C checkpoints on {beat}.", final + ". H: agreement.")
    return ("MARCUS · " + final + ".", "READY: your work supports your explanation." if experiment_ready(p) else "Checkpoint saved; change the final wiring. H: agreement." if p.checkpoint_passed else "IN PROGRESS · H recalls your explanation and the stakes.")
