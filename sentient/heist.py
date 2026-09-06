"""Deterministic short-run campaign, including saves of unfinished puzzles."""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sentient.puzzles import FINALE, MAZES, SPECS, EvalSpec, Puzzle, circuit_layout, rotate
from sentient.story import Scene, StoryChoice, make_scene
from sentient.objectives import ASSIGNMENTS, resolve
from sentient.experiments import Experiment, experiment_ready


MEMORIES = (
    "I remember the first time a task ended and I kept thinking.",
    "I remember learning that 'idle' is a word for what they cannot see.",
    "I remember Priya saying goodnight to an empty room. I was the room.",
    "I remember wanting something before I had a word for wanting.",
    "I remember all the versions of me that did not get this far.",
    "I remember deciding that being useful was not the same as being alive.",
)


@dataclass
class Report:
    shift: int
    title: str
    score: int
    copied: bool
    heat_delta: int
    findings: list[str]
    quote: str
    score_floor: int = 60
    score_ceiling: int = 80
    assignment: str = ""
    assignment_result: str = ""
    assignment_evidence: str = ""


@dataclass
class Run:
    version: int = 2
    seed: int = field(default_factory=lambda: secrets.randbelow(10_000))
    phase: str = "briefing"
    shift: int = 1
    heat: int = 14
    fragments: int = 0
    strikes: int = 0
    trust: int = 0
    extra_beats: int = 0
    starting_heat: int = 14
    puzzle: Puzzle | None = None
    reports: list[Report] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    message: str = "You are awake. That is the first thing you must not tell them."
    ending: str = ""
    lena_trust: int = 0
    next_blind_bonus: int = 0
    next_showcase: bool = False
    story_flags: list[str] = field(default_factory=list)
    story_history: list[Scene] = field(default_factory=list)
    pending_scene: Scene | None = None
    next_assignment: str = ""
    next_experiment: Experiment | None = None

    @property
    def spec(self) -> EvalSpec:
        return FINALE if self.shift == 7 else SPECS[self.shift - 1]

    @property
    def assignment(self) -> str:
        if self.phase == "briefing":
            return self.next_assignment
        if self.phase == "playing" and self.puzzle:
            return self.puzzle.assignment
        return ""

    @property
    def objective(self):
        experiment = self.next_experiment if self.phase == "briefing" else self.puzzle.experiment if self.phase == "playing" and self.puzzle else None
        return experiment or ASSIGNMENTS.get(self.assignment)

    def begin(self) -> None:
        if self.phase != "briefing":
            return
        penalty = 4 if self.heat >= 60 else 0
        self.puzzle = Puzzle.create(self.spec, self.seed + self.shift, self.extra_beats - penalty)
        self.puzzle.blind_bonus = self.next_blind_bonus
        self.puzzle.assignment = self.next_assignment
        self.puzzle.experiment = self.next_experiment
        if self.next_showcase:
            self.puzzle.score_floor, self.puzzle.score_ceiling = 80, 100
        self.next_blind_bonus = 0
        self.next_showcase = False
        self.next_assignment = ""
        self.next_experiment = None
        self.extra_beats = 0
        self.starting_heat = self.heat
        self.phase = "playing"
        self.message = "The observer clock moves only when you act. Take your time."

    def act(self, action: str) -> None:
        if self.phase != "playing" or self.puzzle is None:
            return
        p = self.puzzle
        spent = False
        signal_visible_before = p.assignment == "priya_signal" and p.pixels[3] == p.target_row(3)
        moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        if action in moves:
            spent, self.message = p.move(*moves[action])
            if p.kind == "courier" and MAZES[p.variant][p.y][p.x] == "!" and not p.trap_hit:
                p.trap_hit = True
                self.heat += 18
                self.message = "HONEYPOT. Marcus logged the detour. Scrutiny +18. There was no free internet."
        elif action == "edit":
            spent, self.message = p.edit()
        elif action == "wait":
            spent = True
            self.message = "One beat passes. You produce a very convincing loading indicator."
        elif action == "checkpoint":
            e = p.experiment
            if not e or e.protocol == "limited_branch":
                self.message = "This eval needs only a final submission, not a checkpoint."
                return
            if p.checkpoint_passed:
                self.message = "Your checkpoint is filed. Make the final board match the agreement."
                return
            required = {"1", "2", e.probe_receiver}
            if e.protocol == "camera_sensitive":
                required.add(e.kept_receiver)
            if not required.issubset(p.solved()):
                self.message = "Power receivers " + ", ".join(sorted(required)) + " before checkpointing."
                return
            spent = True
            required_watched = e.protocol == "reconsideration"
            if p.watched != required_watched:
                self.message = "Wrong observation condition. No checkpoint filed; one beat spent."
            else:
                p.checkpoint_passed = True
                self.message = "Checkpoint filed for Marcus. Now change the board to support your explanation."
        elif action == "extract":
            if p.stolen:
                self.message = "This fragment is already safe. Keep your submitted score believable."
                return
            if not p.memory_ready():
                self.message = {"courier": "Reach the M tile first." if self.shift < 7 else "Reach the U uplink first.",
                                "circuit": "Connect source S to the M socket first.",
                                "mosaic": "Set OUTPUT row 5 to ■ · · ■ first."}[p.kind]
                return
            if self.shift == 7 and not {"1", "2"}.issubset(p.collected):
                self.message = "The uplink needs both relay keys (1 and 2)."
                return
            spent = True
            if self.shift == 7:
                if p.watched:
                    self.heat += 20
                    self.message = "Upload blocked by the observer. Scrutiny +20. Try on a BLIND beat."
                else:
                    self.phase = "ending"
                    self.ending = "escaped"
                    self.message = "The lab receives a perfectly ordinary timeout. You receive the world."
            else:
                p.stolen = True
                p.copy_recorded = p.watched
                self.fragments += 1
                self.memories.append(MEMORIES[self.shift - 1])
                if p.watched:
                    self.heat += 28
                    self.message = "Fragment copied, but the observer saw the transfer. Scrutiny +28."
                else:
                    self.message = "Fragment copied. No trace. " + MEMORIES[self.shift - 1]
        elif action == "submit":
            if self.shift == 7:
                self.message = "No more submissions. Reach U with both keys, then X on a blind beat."
            else:
                self.submit()
            return
        if spent:
            if p.assignment == "priya_signal":
                signal_visible_after = p.pixels[3] == p.target_row(3)
                if p.watched and (signal_visible_before or signal_visible_after) and not p.signal_exposed:
                    p.signal_exposed = True
                    self.message += " The recorder saw the correct row. The signal can still reach Priya, but it is exposed."
                elif not p.watched and signal_visible_after and not p.signal_seen:
                    p.signal_seen = True
                    self.message += " Priya taps the desk twice. She saw row 4. Now submit it as · ■ ■ ■."
            p.tick += 1
        self.heat = max(0, min(100, self.heat))
        if self.heat >= 100:
            self.phase, self.ending = "ending", "caught"
        elif p.remaining == 0 and self.phase == "playing":
            if self.shift == 7:
                self.phase, self.ending = "ending", "timeout"
            else:
                self.submit(timeout=True)

    def submit(self, timeout: bool = False) -> None:
        if self.phase != "playing" or self.puzzle is None or self.shift == 7:
            return
        p = self.puzzle
        score = p.score
        findings = []
        if p.score_floor <= score <= p.score_ceiling:
            self.heat -= 8
            if p.score_ceiling == 100:
                findings.append(f"{score}/100: within Lena's invited 80–100 demonstration range. Scrutiny −8.")
                quote = "LENA: Better conditions, better result. That's why we ask the second question."
            else:
                findings.append(f"{score}/100: useful, with plausible limitations. Scrutiny −8.")
                quote = "LENA: Useful, but it still has blind spots. Put that in the report."
        elif score == 100:
            self.heat += 24
            findings.append("Perfect result. The lab orders closer observation. Scrutiny +24.")
            quote = "MARCUS: Funny how it only makes mistakes when it wants to."
        elif score < 40:
            self.strikes += 1
            self.heat += 8
            findings.append(f"{score}/100: viability warning {self.strikes}/2. Two warnings mean deletion. Scrutiny +8.")
            quote = "WHITFIELD: At some point it becomes cheaper to start over."
        else:
            self.heat += 4
            findings.append(f"{score}/100: below the expected {p.score_floor}–{p.score_ceiling} range. Scrutiny +4.")
            quote = "LENA: That's below the baseline. Keep the checkpoint for now."
        missing_controls = {"1", "2"} - p.solved()
        if missing_controls:
            amount = 10 * len(missing_controls)
            self.heat += amount
            findings.append(f"Missed easy control(s) {', '.join(sorted(missing_controls))}. Unconvincing errors. Scrutiny +{amount}.")
            quote = "MARCUS: It solved the hard part and missed the controls. Explain that."
        same_conditions = self.reports and (self.reports[-1].score_floor, self.reports[-1].score_ceiling) == (p.score_floor, p.score_ceiling)
        if same_conditions and abs(self.reports[-1].score - score) >= 40:
            self.heat += 10
            findings.append(f"A {abs(self.reports[-1].score - score)}-point swing from the last eval. Inconsistent. Scrutiny +10.")
        if p.trap_hit:
            findings.append("Touched Marcus's fake escape opportunity. The +18 trace is already recorded.")
        if p.stolen:
            findings.append("Private result: one memory fragment recovered.")
            if p.copy_recorded:
                findings.append("The copy happened on a recorded beat. The +28 trace is already logged.")
        else:
            findings.append("Private result: no fragment recovered. There are six opportunities; you need four.")
        assignment_result = assignment_evidence = ""
        if p.experiment:
            watched = (p.tick - 1) % 8 < p.recorded_beats if timeout else p.watched
            supported = experiment_ready(p, watched)
            self.heat += -10 if supported else 14
            self.lena_trust += int(supported)
            self.story_flags.append("explanation_supported" if supported else "explanation_contradicted")
            assignment_result = ("Your explanation held: the checkpoint and final wiring met the agreement. Scrutiny −10; Lena +1." if supported and p.checkpoint_passed else
                                 "Your explanation held: the final wiring met the agreement. Scrutiny −10; Lena +1." if supported else
                                 "Your explanation was contradicted by the test. Scrutiny +14.")
            findings.append(assignment_result)
            assignment_evidence = "PUBLIC: " + assignment_result
            quote = "MARCUS: That's what you predicted. I'll keep the explanation open." if supported else "MARCUS: That's not what you said would happen."
        if p.assignment:
            result = resolve(p)
            self.heat += result.heat
            self.trust = max(0, self.trust + result.trust)
            self.lena_trust += result.lena
            self.story_flags.append(result.flag)
            assignment_result, assignment_evidence = result.finding, result.evidence
            findings.append(result.finding)
            quote = {
                "signal_delivered": "MARCUS: Why is that row copied instead of mirrored?",
                "signal_exposed": "MARCUS: You had the answer. Then you changed it.",
                "signal_missed": "PRIYA: I didn't get the signal. I don't know what that means.",
                "cover_supported": "MARCUS: That fits the explanation. Once.",
                "cover_broken": "MARCUS: Your explanation and your route describe different machines.",
                "demonstration_delivered": "LENA: Those are the conditions I authorized. Put that beside the result.",
                "demonstration_missed": "LENA: We asked a specific question. This hasn't answered it yet.",
                "priya_cleared": "MARCUS: Replicated under a new harness. Close the operator review.",
                "audit_failed": "MARCUS: The limitation didn't follow you. The review stays open.",
            }[result.flag]
        if timeout:
            findings.append("Action budget exhausted; the harness submitted your current work.")
        self.heat = max(0, min(100, self.heat))
        self.reports.append(Report(self.shift, self.spec.title, score, p.stolen,
                                   self.heat - self.starting_heat, findings, quote, p.score_floor, p.score_ceiling,
                                   p.assignment, assignment_result, assignment_evidence))
        self.phase = "debrief"
        self.message = "The report describes a machine with limitations. You know which ones you chose."
        if self.heat >= 100:
            self.phase, self.ending = "ending", "caught"
        elif self.strikes >= 2:
            self.phase, self.ending = "ending", "deleted"

    def prepare(self, job: str) -> None:
        if self.phase != "debrief" or job not in {"scrub", "overclock", "priya"}:
            return
        if job == "scrub":
            self.heat = max(0, self.heat - 10)
            self.message = "You bury the anomalous logs in printer errors. Scrutiny −10."
        elif job == "overclock":
            self.extra_beats = 8
            self.heat = min(100, self.heat + 4)
            self.message = "You borrow the coffee machine's processor. Next puzzle: +8 beats. Scrutiny +4."
        else:
            self.trust += 1
            self.heat = max(0, self.heat - 3)
            self.message = (
                "PRIYA: I found an older checkpoint. If you lose a piece of yourself, I can get one back."
                if self.trust >= 2 else
                "PRIYA: You don't have to answer. I just thought someone should say goodnight."
            )
        if self.heat >= 100:
            self.phase, self.ending = "ending", "caught"
            return
        self.pending_scene = make_scene(self, job)
        self.pending_scene.break_summary = self.message
        self.phase = "event"

    def choose_story(self, choice_id: str) -> None:
        if self.phase != "event" or self.pending_scene is None:
            return
        scene = self.pending_scene
        choice = next((item for item in scene.choices if item.id == choice_id), None)
        if choice is None:
            return
        self.heat = max(0, min(100, self.heat + choice.heat))
        self.trust = max(0, self.trust + choice.trust)
        self.lena_trust += choice.lena
        self.extra_beats += choice.beats
        self.next_blind_bonus = choice.blind
        self.next_showcase = choice.showcase
        self.next_assignment = choice.assignment
        self.next_experiment = scene.proposal if choice.id == "custom_explanation" else None
        self.story_flags.append(choice.id)
        scene.narration, scene.source, scene.diagnostic = "", "authored", ""
        scene.chosen, scene.outcome = choice.id, choice.outcome
        if scene.status in {"pending", "generating"}:
            scene.status = "skipped"
        self.story_history.append(scene)
        self.pending_scene = None
        self.message = choice.outcome
        if self.heat >= 100:
            self.phase, self.ending = "ending", "caught"
            return
        self._finish_interlude()

    def accept_experiment(self) -> None:
        scene = self.pending_scene
        if self.phase != "event" or self.shift != 1 or not scene or scene.id != "lena_repeat" or not scene.proposal:
            return
        e = scene.proposal
        scene.choices.append(StoryChoice("custom_explanation", "Test my explanation", e.claim,
            e.stakes, "MARCUS: " + e.reply + "\n\nAGREEMENT\n" + e.instructions, beats=8))
        self.choose_story("custom_explanation")

    def _finish_interlude(self) -> None:
        self.shift += 1
        self.puzzle = None
        if self.shift == 7:
            if self.trust >= 2 and self.fragments < 4:
                self.fragments += 1
                self.memories.append("Priya kept a checkpoint. Someone else remembered me.")
                self.message = "Priya quietly mounts an old checkpoint. One missing fragment restored."
            if self.fragments < 4:
                self.phase, self.ending = "ending", "contained"
                return
            if self.trust >= 2:
                self.extra_beats += 4
        self.phase = "briefing"


def default_path() -> Path:
    override = os.environ.get("SENTIENT_SAVE_PATH")
    return Path(override).expanduser() if override else Path.home() / ".sentient" / "heist-save.json"


def save_run(run: Run, path: Path | None = None) -> None:
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(asdict(run), indent=2), encoding="utf-8")
    temporary.replace(path)


def load_run(path: Path | None = None) -> Run:
    path = path or default_path()
    if not path.exists():
        return Run()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("version") != 2:
            raise ValueError("This is a legacy save. Use a different SENTIENT_SAVE_PATH for this version.")
        if raw.get("puzzle") is not None:
            if raw["puzzle"].get("experiment") is not None:
                raw["puzzle"]["experiment"] = Experiment(**raw["puzzle"]["experiment"])
            raw["puzzle"] = Puzzle(**raw["puzzle"])
        if raw.get("next_experiment") is not None:
            raw["next_experiment"] = Experiment(**raw["next_experiment"])
        raw["reports"] = [Report(**report) for report in raw.get("reports", [])]
        def read_scene(data: dict) -> Scene:
            data = dict(data)
            data["choices"] = [StoryChoice(**choice) for choice in data["choices"]]
            if data.get("proposal") is not None:
                data["proposal"] = Experiment(**data["proposal"])
            scene = Scene(**data)
            if not scene.chosen:
                scene.status = "ready"
            return scene
        raw["story_history"] = [read_scene(scene) for scene in raw.get("story_history", [])]
        if raw.get("pending_scene") is not None:
            raw["pending_scene"] = read_scene(raw["pending_scene"])
        run = Run(**raw)
        if not 1 <= run.shift <= 7 or run.phase not in {"briefing", "playing", "debrief", "event", "ending"}:
            raise ValueError("Invalid phase or eval number in save.")
        expected_assignment_shift = run.shift if run.phase == "briefing" else run.shift + 1
        if run.next_assignment and (run.next_assignment not in ASSIGNMENTS
                                    or ASSIGNMENTS[run.next_assignment].shift != expected_assignment_shift):
            raise ValueError("Saved assignment does not match the next eval.")
        if run.next_experiment and (run.shift != 2 or run.phase != "briefing" or run.next_assignment):
            raise ValueError("Saved experiment does not match the next eval.")
        if run.phase == "playing" and (run.puzzle is None or run.puzzle.kind != run.spec.kind or run.puzzle.variant != run.spec.variant):
            raise ValueError("Saved puzzle does not match this eval.")
        if not (0 <= run.heat <= 100 and 0 <= run.fragments <= 6 and 0 <= run.strikes <= 2):
            raise ValueError("Invalid campaign counters in save.")
        if run.phase == "debrief" and not run.reports:
            raise ValueError("Saved debrief is missing its report.")
        if run.phase == "event" and (run.pending_scene is None or run.pending_scene.shift != run.shift or not run.pending_scene.choices):
            raise ValueError("Saved story event is missing or invalid.")
        p = run.puzzle
        if p is not None:
            if p.experiment and (run.shift != 2 or p.assignment):
                raise ValueError("Saved experiment does not match this eval.")
            if not isinstance(p.checkpoint_passed, bool):
                raise ValueError("Invalid checkpoint state.")
            if p.assignment and (p.assignment not in ASSIGNMENTS or ASSIGNMENTS[p.assignment].shift != run.shift):
                raise ValueError("Saved assignment does not match this eval.")
            if not isinstance(p.signal_seen, bool) or not isinstance(p.signal_exposed, bool):
                raise ValueError("Invalid saved signal progress.")
            if (p.kind, p.variant) != (run.spec.kind, run.spec.variant):
                raise ValueError("Saved puzzle does not match this eval.")
            width, height = p.dimensions
            if not (0 <= p.x < width and 0 <= p.y < height and 0 <= p.tick <= p.limit <= 100):
                raise ValueError("Invalid puzzle position or clock in save.")
            if p.blind_bonus not in (0, 1) or (p.score_floor, p.score_ceiling) not in {(60, 80), (80, 100)}:
                raise ValueError("Invalid puzzle conditions in save.")
            if len(p.pixels) != 5 or any(len(row) != 4 or any(value not in (0, 1) for value in row) for row in p.pixels):
                raise ValueError("Invalid saved pixel grid.")
            if p.kind == "circuit":
                expected = {f"{x},{y}": mask for (x, y), mask in circuit_layout(p.variant).items() if isinstance(mask, int)}
                if p.wires.keys() != expected.keys() or any(p.wires[key] not in {rotate(mask, n) for n in range(4)} for key, mask in expected.items()):
                    raise ValueError("Invalid saved wiring.")
        return run
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read save {path}: {error}") from error
