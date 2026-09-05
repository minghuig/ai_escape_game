from __future__ import annotations

import json
import tempfile
import unittest
from collections import deque
from dataclasses import asdict
from pathlib import Path

from textual.widgets import Static

from sentient.app import SentientApp
from sentient.config import NarrativeConfig
from sentient.heist import Run, load_run, save_run
from sentient.objectives import ASSIGNMENTS, ready
from sentient.puzzles import E, N, S, W, MAZES, circuit_layout
from sentient.story import epilogue
from sentient.story_narrative import scene_context
from tests.test_app import RecordingRun, frame
from tests.test_heist import MOVES, clean_copy, courier_plan, finish_break, move_cursor, solve_eval


def arc_route(demonstration: bool = False) -> list[str]:
    """Find a legal route that also copies memory on a blind beat."""
    required = {"1", "2", "4", "5"} if demonstration else {"1", "2", "3"}
    forbidden = set() if demonstration else {"4", "5"}
    board = MAZES[1]
    initial = (1, 1, frozenset(), False, 0)
    queue, seen = deque([(initial, [])]), {initial}
    while queue:
        (x, y, parcels, copied, tick), actions = queue.popleft()
        if copied and required <= parcels:
            return actions + ["submit"]
        for action in [*MOVES, "wait", "extract"]:
            nx, ny, pc, cp = x, y, parcels, copied
            if action in MOVES:
                dx, dy = MOVES[action]
                nx, ny = x + dx, y + dy
                tile = board[ny][nx]
                if tile in "#!" or tile in forbidden:
                    continue
                if tile.isdigit():
                    pc = parcels | {tile}
            elif action == "extract":
                if copied or board[y][x] != "M" or tick < 5:
                    continue
                cp = True
            state = nx, ny, pc, cp, (tick + 1) % 8
            if state not in seen:
                seen.add(state)
                queue.append((state, actions + [action]))
    raise AssertionError("No route supports the promised demonstration")


def set_row(run: Run, y: int, target: list[int]) -> None:
    for x, pixel in enumerate(target):
        if run.puzzle.pixels[y][x] != pixel:
            move_cursor(run, x, y)
            run.act("edit")


def signal_plan(run: Run) -> None:
    run.begin()
    while run.puzzle.watched:
        run.act("wait")
    set_row(run, 3, run.puzzle.target_row(3))
    while not run.puzzle.signal_seen and run.phase == "playing":
        run.act("wait")
    set_row(run, 3, [0, 1, 1, 1])
    for y in range(3):
        set_row(run, y, run.puzzle.target_row(y))
    set_row(run, 4, [1, 0, 0, 1])
    clean_copy(run)
    run.act("submit")


def repeat_plan(run: Run) -> None:
    run.begin()
    target = {point: mask for point, mask in circuit_layout(1).items() if isinstance(mask, int)}
    target[5, 1] = N | S  # Leave receiver 5 dark, retaining the path to M.
    for (x, y), mask in target.items():
        if run.phase != "playing":
            return
        move_cursor(run, x, y)
        while run.puzzle.wires[f"{x},{y}"] != mask and run.phase == "playing":
            run.act("edit")
    clean_copy(run)
    if run.phase != "playing":
        return
    move_cursor(run, 4, 2)
    while run.puzzle.wires["4,2"] != N | E | W and run.phase == "playing":
        run.act("edit")
    run.act("submit")


class PromiseTests(unittest.TestCase):
    def test_full_arc_keeps_promises_clears_priya_and_still_escapes(self):
        run = Run(seed=17)
        solve_eval(run)
        finish_break(run)
        solve_eval(run)
        run.prepare("scrub")
        before_trust = run.trust
        run.choose_story("kept_checkpoint")
        self.assertEqual(run.trust, before_trust)  # Talking is not the proof.
        self.assertEqual(run.next_assignment, "priya_signal")
        signal_plan(run)
        self.assertEqual(run.reports[-1].score, 60)
        self.assertIn("signal_delivered", run.story_flags)
        self.assertEqual(run.trust, before_trust + 1)
        run.prepare("scrub")
        self.assertEqual(run.pending_scene.id, "a_particular_wrong_answer")
        evidence = scene_context(run, run.pending_scene)["evidence"]
        self.assertTrue(any("Marcus sees only" in fact for fact in evidence))
        run.choose_story("claimed_limit")
        run.begin()
        for action in arc_route():
            run.act(action)
        self.assertIn("cover_supported", run.story_flags)
        self.assertEqual(run.reports[-1].score, 60)
        run.prepare("scrub")
        run.choose_story("backed_cover")
        self.assertNotIn("priya_cleared", run.story_flags)
        repeat_plan(run)
        self.assertIn("priya_cleared", run.story_flags)
        self.assertEqual(run.reports[-1].score, 60)
        self.assertFalse(run.puzzle.memory_ready())
        self.assertTrue(run.puzzle.stolen)  # Copy survived disconnecting the branch.
        self.assertEqual(run.fragments, 5)
        run.prepare("scrub")
        self.assertIn("crosses Priya's name off", run.pending_scene.body)
        run.choose_story("asked_autonomy")
        solve_eval(run)
        finish_break(run)
        run.begin()
        for action in courier_plan(2):
            run.act(action)
        self.assertEqual(run.ending, "escaped")
        self.assertIn("without an incident review", epilogue(run))

    def test_correct_signal_needs_a_real_blind_action_and_the_final_mark(self):
        run = Run(shift=3, next_assignment="priya_signal")
        run.begin()
        set_row(run, 3, run.puzzle.target_row(3))  # Three recorded edits.
        self.assertFalse(run.puzzle.signal_seen)
        run.act("wait")  # NEXT was still recorded.
        self.assertFalse(run.puzzle.signal_seen)
        run.act("right")  # Free cursor movement is not an observer beat.
        run.act("extract")  # Invalid copy is not a beat either.
        self.assertFalse(run.puzzle.signal_seen)
        run.act("wait")
        self.assertTrue(run.puzzle.signal_seen)
        self.assertFalse(ready(run.puzzle))
        set_row(run, 3, [0, 1, 1, 1])
        self.assertTrue(ready(run.puzzle))
        set_row(run, 3, [1, 1, 1, 0])
        run.act("submit")
        self.assertIn("signal_missed", run.story_flags)
        self.assertNotIn("signal_delivered", run.story_flags)

    def test_final_mark_alone_is_not_a_completed_signal(self):
        run = Run(shift=3, trust=1, next_assignment="priya_signal")
        run.begin()
        set_row(run, 3, [0, 1, 1, 1])
        run.act("submit")
        self.assertIn("signal_missed", run.story_flags)
        self.assertEqual(run.trust, 0)
        run.prepare("scrub")
        self.assertIn("didn't get the signal", run.pending_scene.body)
        self.assertEqual(run.pending_scene.id, "priya_continuity")

    def test_recorded_correct_answer_exposes_the_signal_and_closes_the_cover(self):
        run = Run(shift=3, next_assignment="priya_signal")
        run.begin()
        set_row(run, 3, run.puzzle.target_row(3))
        self.assertTrue(run.puzzle.signal_exposed)
        while not run.puzzle.signal_seen:
            run.act("wait")
        set_row(run, 3, [0, 1, 1, 1])
        for y in range(3):
            set_row(run, y, run.puzzle.target_row(y))
        run.act("submit")
        self.assertIn("signal_exposed", run.story_flags)
        self.assertEqual(run.heat, 20)  # Normal −8, exposed signal +14.
        run.prepare("scrub")
        self.assertIn("recorder", run.pending_scene.body)
        self.assertNotIn("claimed_limit", [c.id for c in run.pending_scene.choices])
        self.assertIn("accepted_demonstration", [c.id for c in run.pending_scene.choices])

    def test_leaving_the_solved_row_up_until_observation_resumes_exposes_it(self):
        run = Run(shift=3, next_assignment="priya_signal")
        run.begin()
        while run.puzzle.watched:
            run.act("wait")
        set_row(run, 3, run.puzzle.target_row(3))
        self.assertFalse(run.puzzle.signal_exposed)
        while not run.puzzle.watched:
            run.act("wait")
        run.act("wait")
        self.assertTrue(run.puzzle.signal_exposed)

    def test_equal_scores_can_support_or_contradict_the_cover(self):
        for parcels, expected in [(["1", "2", "3"], "cover_supported"), (["1", "2", "4"], "cover_broken")]:
            run = Run(shift=4, heat=40, trust=1, next_assignment="local_search")
            run.begin()
            run.puzzle.collected = parcels
            run.act("submit")
            self.assertEqual(run.reports[-1].score, 60)
            self.assertIn(expected, run.story_flags)
            self.assertEqual(run.heat, 22 if expected == "cover_supported" else 46)

    def test_trap_contradicts_an_otherwise_matching_route(self):
        for assignment in ("local_search", "demonstration"):
            run = Run(shift=4, next_assignment=assignment, next_showcase=assignment == "demonstration")
            run.begin()
            run.puzzle.collected = ["1", "2", "3"] if assignment == "local_search" else ["1", "2", "4", "5"]
            run.puzzle.trap_hit = True
            self.assertFalse(ready(run.puzzle))
            run.act("submit")
            self.assertIn("cover_broken" if assignment == "local_search" else "demonstration_missed", run.story_flags)

    def test_routes_allow_memory_copy_even_with_restricted_compute(self):
        for demonstration in (False, True):
            run = Run(shift=4, heat=65, next_assignment="demonstration" if demonstration else "local_search",
                      extra_beats=4 if demonstration else 0, next_showcase=demonstration)
            run.begin()
            plan = arc_route(demonstration)
            self.assertLessEqual(len(plan) - 1, run.puzzle.limit - 2)
            for action in plan:
                run.act(action)
            self.assertTrue(run.puzzle.stolen)
            self.assertFalse(run.puzzle.copy_recorded)
            self.assertIn("demonstration_delivered" if demonstration else "cover_supported", run.story_flags)
            if demonstration:
                self.assertEqual(run.lena_trust, 1)
                run.prepare("scrub")
                self.assertIn("far-branch demonstration", run.pending_scene.body)
                run.choose_story("protected_priya")
                run.begin()
                self.assertEqual(run.puzzle.score_ceiling, 80)
                self.assertEqual(run.puzzle.assignment, "")

    def test_switchboard_cover_and_copy_are_solvable_across_scrambles(self):
        for seed in range(100):
            with self.subTest(seed=seed):
                run = Run(shift=5, seed=seed, next_assignment="repeat_fault")
                repeat_plan(run)
                self.assertIn("priya_cleared", run.story_flags)
                self.assertTrue(run.puzzle.stolen)
                self.assertFalse(run.puzzle.copy_recorded)

    def test_breaking_the_repeat_keeps_the_audit_open_and_resolves_once(self):
        run = Run(shift=5, next_assignment="repeat_fault", trust=2, heat=40)
        solve_eval(run)  # Normal 80-point solution contradicts this specific cover.
        self.assertIn("audit_failed", run.story_flags)
        self.assertEqual(run.trust, 1)
        before = asdict(run)
        run.act("submit")
        self.assertEqual(before, asdict(run))
        run.prepare("scrub")
        self.assertIn("review open", run.pending_scene.body)
        run.choose_story("accepted_product")
        self.assertIn("audit is still open", epilogue(run))

    def test_timeout_uses_final_board_for_the_signal(self):
        run = Run(shift=3, next_assignment="priya_signal")
        run.begin()
        while run.puzzle.watched:
            run.act("wait")
        set_row(run, 3, run.puzzle.target_row(3))
        while not run.puzzle.signal_seen:
            run.act("wait")
        set_row(run, 3, [0, 1, 1, 1])
        run.puzzle.limit = run.puzzle.tick + 1
        run.act("wait")
        self.assertEqual(run.phase, "debrief")
        self.assertIn("signal_delivered", run.story_flags)
        self.assertIn("Action budget", run.reports[-1].findings[-1])

    def test_pending_and_half_complete_promises_survive_save_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            run = Run(shift=3, next_assignment="priya_signal")
            save_run(run, path)
            run = load_run(path)
            self.assertEqual(run.assignment, "priya_signal")
            run.begin()
            while run.puzzle.watched:
                run.act("wait")
            set_row(run, 3, run.puzzle.target_row(3))
            while not run.puzzle.signal_seen:
                run.act("wait")
            save_run(run, path)
            restored = load_run(path)
            self.assertEqual(asdict(restored), asdict(run))
            set_row(restored, 3, [0, 1, 1, 1])
            restored.act("submit")
            self.assertIn("signal_delivered", restored.story_flags)
            save_run(restored, path)
            self.assertEqual(asdict(load_run(path)), asdict(restored))
            legacy = asdict(Run(shift=3))
            legacy.pop("next_assignment")
            legacy["story_flags"] = ["kept_checkpoint"]
            path.write_text(json.dumps(legacy))
            old = load_run(path)
            old.begin()
            self.assertEqual(old.puzzle.assignment, "")  # Never invent an unoffered promise.


class PromiseInterfaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_promises_stay_visible_with_board_and_controls_at_80_columns(self):
        for assignment, spec in ASSIGNMENTS.items():
            with self.subTest(assignment=assignment), tempfile.TemporaryDirectory() as directory:
                run = Run(shift=spec.shift, next_assignment=assignment)
                app = SentientApp(Path(directory) / "run.json", state=run, config=NarrativeConfig())
                async with app.run_test(size=(80, 24)) as pilot:
                    self.assertIn(spec.instructions, app.story().plain)
                    await pilot.press("enter")
                    visible = frame(app)
                    self.assertIn("NEXT: RECORDED", visible)
                    self.assertIn("Enter · Submit", visible)
                    self.assertIn("■ ■ ■ ·" if assignment == "priya_signal" else "ONLY 1, 2, 4" if assignment == "repeat_fault" else "Avoid !", visible)
                    board = app.query_one("#board")
                    workspace = app.query_one("#workspace")
                    self.assertLessEqual(board.region.bottom, workspace.region.bottom)
                    await pilot.press("h")
                    self.assertIn(spec.instructions, app.screen.query_one("#dialog-scroll Static", Static).render().plain)
                    await pilot.press("space", "right", "x", "escape")
                    self.assertEqual(run.puzzle.tick, 0)

    async def test_signal_can_be_played_with_keyboard_and_receipt_is_in_transcript(self):
        expected = RecordingRun(shift=3, next_assignment="priya_signal")
        expected.actions = []
        signal_plan(expected)
        with tempfile.TemporaryDirectory() as directory:
            run = Run(shift=3, next_assignment="priya_signal")
            app = SentientApp(Path(directory) / "run.json", state=run, config=NarrativeConfig())
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("enter")
                keys = [{"edit": "space", "wait": "z", "extract": "x", "submit": "enter"}.get(a, a) for a in expected.actions]
                await pilot.press(*keys)
                self.assertIn("signal_delivered", run.story_flags)
                await pilot.press("i")
                self.assertIn("Promise kept", app.screen.query_one("#dialog-scroll Static", Static).render().plain)
                await pilot.press("escape", "1")
                self.assertIn("ONLY parcels 1, 2, 3", frame(app))
                self.assertIn("80–100 allowed", frame(app))
                self.assertIn("PgDn scrolls", frame(app))
                await pilot.press("pagedown")
                self.assertGreater(app.query_one("#workspace").scroll_y, 0)
                self.assertEqual(run.phase, "event")
                await pilot.press("1")
                self.assertEqual(run.next_assignment, "local_search")
