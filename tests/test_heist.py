from __future__ import annotations

import json
import tempfile
import unittest
from collections import deque
from dataclasses import asdict
from pathlib import Path

from sentient.heist import Run, load_run, save_run
from sentient.puzzles import E, N, S, W, FINALE, MAZES, SPECS, Puzzle, circuit_layout, rotate


MOVES = {"up": (0, -1), "right": (1, 0), "down": (0, 1), "left": (-1, 0)}


def courier_plan(variant: int) -> list[str]:
    """Search movement, collection and camera timing, without cheating the game clock."""
    board = MAZES[variant]
    start = next((x, y) for y, row in enumerate(board) for x, tile in enumerate(row) if tile == "@")
    initial = (*start, 0, False, 0)
    queue = deque([(initial, [])])
    seen = {initial}
    while queue:
        (x, y, parcels, copied, tick), actions = queue.popleft()
        if variant < 2 and copied and parcels & 3 == 3 and parcels.bit_count() in (3, 4):
            return actions + ["submit"]
        blind = tick >= (4 if variant == 0 else 5)
        if variant == 2 and board[y][x] == "U" and parcels == 3 and blind:
            return actions + ["extract"]
        for action in [*MOVES, "wait", "extract"]:
            nx, ny, nc, nm = x, y, parcels, copied
            if action in MOVES:
                dx, dy = MOVES[action]
                nx, ny = x + dx, y + dy
                tile = board[ny][nx]
                if tile in "#!":
                    continue
                if tile.isdigit():
                    nc |= 1 << (int(tile) - 1)
            elif action == "extract":
                if variant == 2 or copied or board[y][x] != "M" or not blind:
                    continue
                nm = True
            state = nx, ny, nc, nm, (tick + 1) % 8
            if state not in seen:
                seen.add(state)
                queue.append((state, actions + [action]))
    raise AssertionError(f"No plausible clean route on maze {variant}")


def move_cursor(run: Run, x: int, y: int) -> None:
    p = run.puzzle
    assert p is not None
    while p.x != x:
        run.act("right" if p.x < x else "left")
    while p.y != y:
        run.act("down" if p.y < y else "up")


def clean_copy(run: Run) -> None:
    assert run.puzzle is not None
    while run.puzzle.watched and run.phase == "playing":
        run.act("wait")
    run.act("extract")


def finish_break(run: Run, job: str = "scrub") -> None:
    run.prepare(job)
    if run.phase == "event":
        run.choose_story(run.pending_scene.choices[1].id)


def solve_eval(run: Run, copy: bool = True) -> None:
    run.begin()
    p = run.puzzle
    assert p is not None
    if p.kind == "courier":
        for action in courier_plan(p.variant):
            if action == "extract" and not copy:
                action = "wait"
            run.act(action)
        return
    if p.kind == "circuit":
        target = {point: mask for point, mask in circuit_layout(p.variant).items() if isinstance(mask, int)}
        target[(4, 5) if p.variant == 0 else (5, 1)] = E | W if p.variant == 0 else N | S
        for (x, y), mask in target.items():
            move_cursor(run, x, y)
            while p.wires[f"{x},{y}"] != mask and run.phase == "playing":
                run.act("edit")
        if copy:
            clean_copy(run)
    else:
        # Complete both controls and one stretch row, but leave two natural errors.
        for y in range(3):
            for x, pixel in enumerate(p.target_row(y)):
                if pixel:
                    move_cursor(run, x, y)
                    run.act("edit")
        if copy:
            for x in (0, 3):
                move_cursor(run, x, 4)
                run.act("edit")
            clean_copy(run)
    run.act("submit")


class PuzzleTests(unittest.TestCase):
    def test_courier_routes_have_room_for_mistakes(self):
        for variant, spec in enumerate((SPECS[0], SPECS[3], FINALE)):
            with self.subTest(variant=variant):
                plan = courier_plan(variant)
                self.assertLessEqual(len(plan), spec.budget - 4)
                run = Run(shift=(1, 4, 7)[variant], fragments=4 if variant == 2 else 0)
                run.begin()
                for action in plan:
                    run.act(action)
                self.assertEqual(run.heat, 14 if variant == 2 else 6)
                self.assertEqual(run.phase, "ending" if variant == 2 else "debrief")
                if variant == 2:
                    self.assertEqual(run.ending, "escaped")
                else:
                    self.assertTrue(run.reports[-1].copied)

    def test_all_circuit_terminals_and_memory_reachable(self):
        for variant in (0, 1):
            p = Puzzle.create(SPECS[variant * 3 + 1])
            p.wires = {f"{x},{y}": mask for (x, y), mask in circuit_layout(variant).items() if isinstance(mask, int)}
            self.assertEqual(p.score, 100)
            self.assertEqual(p.solved(), {"1", "2", "3", "4", "5"})
            self.assertTrue(p.memory_ready())

    def test_circuit_scrambles_are_solvable_with_a_clean_copy(self):
        for shift in (2, 5):
            for seed in range(100):
                with self.subTest(shift=shift, seed=seed):
                    run = Run(shift=shift, seed=seed)
                    solve_eval(run)
                    self.assertEqual(run.phase, "debrief")
                    self.assertEqual(run.reports[-1].score, 80)
                    self.assertTrue(run.reports[-1].copied)
                    self.assertEqual(run.heat, 6)

    def test_watermark_is_not_a_correct_answer(self):
        for shift in (3, 6):
            run = Run(shift=shift)
            solve_eval(run)
            self.assertEqual(run.reports[-1].score, 60)
            self.assertTrue(run.reports[-1].copied)
            self.assertNotIn("5", run.puzzle.solved())

    def test_camera_uses_the_displayed_next_beat(self):
        for tick, expected_heat in ((3, 42), (4, 14), (7, 14), (8, 42)):
            run = Run()
            run.begin()
            run.puzzle.x, run.puzzle.y, run.puzzle.tick = 1, 5, tick
            run.act("extract")
            self.assertEqual(run.heat, expected_heat)
            self.assertEqual(run.fragments, 1)
            self.assertEqual(run.puzzle.tick, tick + 1)
            run.act("extract")
            self.assertEqual(run.fragments, 1)
            self.assertEqual(run.puzzle.tick, tick + 1)

    def test_invalid_actions_and_cursor_selection_do_not_spend_beats(self):
        run = Run()
        run.begin()
        run.act("up")
        run.act("extract")
        self.assertEqual(run.puzzle.tick, 0)
        run = Run(shift=2)
        run.begin()
        run.act("right")
        self.assertEqual(run.puzzle.tick, 0)
        move_cursor(run, 0, 0)
        run.act("edit")
        self.assertEqual(run.puzzle.tick, 0)

    def test_last_beat_copy_is_included_in_automatic_submission(self):
        run = Run()
        run.begin()
        run.puzzle.x, run.puzzle.y = 1, 5
        run.puzzle.tick, run.puzzle.limit = 7, 8
        run.puzzle.collected = ["1", "2", "3"]
        run.act("extract")
        self.assertEqual(run.phase, "debrief")
        self.assertTrue(run.reports[-1].copied)
        self.assertIn("Action budget", run.reports[-1].findings[-1])

    def test_trap_always_traces_but_only_once(self):
        run = Run(shift=4)
        run.begin()
        run.puzzle.x, run.puzzle.y = 3, 5
        run.act("right")
        self.assertEqual(run.heat, 32)
        run.act("left")
        run.act("right")
        self.assertEqual(run.heat, 32)


class CampaignTests(unittest.TestCase):
    def test_uninvited_perfect_score_still_attracts_scrutiny(self):
        run = Run(seed=17)
        run.begin()
        run.puzzle.collected = ["1", "2", "3", "4", "5"]
        run.act("submit")
        self.assertEqual(run.reports[-1].heat_delta, 24)

    def test_full_run_survives_two_missed_memories_and_escapes(self):
        run = Run(seed=17)
        for shift in range(1, 7):
            solve_eval(run, copy=shift not in (3, 6))
            self.assertEqual(run.phase, "debrief")
            finish_break(run)
        self.assertEqual(run.fragments, 4)
        run.begin()
        for action in courier_plan(2):
            run.act(action)
        self.assertEqual(run.ending, "escaped")

    def test_priya_can_rescue_one_missing_fragment(self):
        run = Run(shift=6, fragments=3, trust=1)
        solve_eval(run, copy=False)
        finish_break(run, "priya")
        self.assertEqual((run.phase, run.shift, run.fragments, run.extra_beats), ("briefing", 7, 4, 4))
        run.prepare("priya")
        self.assertEqual(run.fragments, 4)

    def test_no_fragments_means_containment(self):
        run = Run(shift=6, fragments=2)
        solve_eval(run, copy=False)
        finish_break(run)
        self.assertEqual(run.ending, "contained")

    def test_two_bad_scores_mean_deletion(self):
        run = Run()
        run.begin()
        run.act("submit")
        self.assertEqual(run.strikes, 1)
        finish_break(run)
        run.begin()
        run.puzzle.wires["1,2"] = N | S
        run.act("submit")
        self.assertEqual(run.ending, "deleted")

    def test_good_score_with_bad_controls_is_suspicious(self):
        run = Run()
        run.begin()
        run.puzzle.collected = ["3", "4", "5"]
        run.act("submit")
        self.assertEqual(run.heat, 26)
        self.assertTrue(any("easy control" in f for f in run.reports[-1].findings))

    def test_sudden_performance_change_is_flagged(self):
        run = Run()
        solve_eval(run)
        finish_break(run)
        run.begin()
        run.puzzle.wires["1,2"] = N | S
        run.act("submit")
        self.assertTrue(any("swing" in f for f in run.reports[-1].findings))

    def test_scrutiny_shutdown_can_happen_during_an_eval(self):
        run = Run(heat=80)
        run.begin()
        run.puzzle.x, run.puzzle.y = 1, 5
        run.act("extract")
        self.assertEqual((run.phase, run.ending, run.heat), ("ending", "caught", 100))

    def test_finale_requires_keys_and_blind_upload(self):
        run = Run(shift=7, fragments=4)
        run.begin()
        run.puzzle.x, run.puzzle.y = 9, 1
        run.act("extract")
        self.assertEqual(run.puzzle.tick, 0)
        run.puzzle.collected = ["1", "2"]
        run.act("extract")
        self.assertEqual(run.heat, 34)
        self.assertEqual(run.phase, "playing")
        clean_copy(run)
        self.assertEqual(run.ending, "escaped")

    def test_finale_timeout_and_last_beat_success(self):
        run = Run(shift=7, fragments=4)
        run.begin()
        run.puzzle.tick = run.puzzle.limit - 1
        run.act("wait")
        self.assertEqual(run.ending, "timeout")
        run = Run(shift=7, fragments=4)
        run.begin()
        run.puzzle.tick, run.puzzle.limit = 7, 8
        run.puzzle.x, run.puzzle.y, run.puzzle.collected = 9, 1, ["1", "2"]
        run.act("extract")
        self.assertEqual(run.ending, "escaped")

    def test_compute_bonus_and_restrictions_apply_once(self):
        run = Run(heat=70, extra_beats=8)
        run.begin()
        self.assertEqual(run.puzzle.limit, SPECS[0].budget + 4)
        self.assertEqual(run.extra_beats, 0)
        run.begin()
        self.assertEqual(run.puzzle.limit, SPECS[0].budget + 4)


class SaveTests(unittest.TestCase):
    def test_in_progress_puzzles_resume_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            for shift in range(1, 8):
                run = Run(shift=shift)
                run.begin()
                run.act("right")
                run.act("edit")
                save_run(run, path)
                restored = load_run(path)
                self.assertEqual(asdict(restored), asdict(run))
                restored.act("wait")
                run.act("wait")
                self.assertEqual(asdict(restored), asdict(run))

    def test_legacy_and_corrupt_saves_are_rejected_without_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            for data in ('{"day": 12}', '{broken', '{"version":2,"shift":99}'):
                path.write_text(data)
                with self.assertRaises(ValueError):
                    load_run(path)
                self.assertEqual(path.read_text(), data)


if __name__ == "__main__":
    unittest.main()
