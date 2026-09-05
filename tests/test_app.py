from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from textual.widgets import Button, Static

from sentient.app import PuzzleBoard, SentientApp
from sentient.heist import Run, load_run
from sentient.config import NarrativeConfig, NarrativeProviderName, load_local_env
from tests.test_heist import courier_plan, solve_eval


class RecordingRun(Run):
    def act(self, action: str) -> None:
        self.actions.append(action)
        super().act(action)


def frame(app: SentientApp) -> str:
    return "\n".join(strip.text for strip in app.screen._compositor.render_strips())


class InterfaceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        config = patch("sentient.app.load_narrative_config", return_value=NarrativeConfig())
        config.start()
        self.addCleanup(config.stop)

    async def test_full_keyboard_run_through_all_evals_and_finale(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SentientApp(Path(directory) / "run.json", state=Run(seed=17))
            async with app.run_test(size=(110, 36)) as pilot:
                for shift in range(1, 7):
                    expected = RecordingRun(shift=shift, seed=17)
                    expected.actions = []
                    solve_eval(expected)
                    await pilot.press("enter")
                    keys = [{"edit": "space", "wait": "z", "extract": "x", "submit": "enter"}.get(a, a) for a in expected.actions]
                    await pilot.press(*keys)
                    self.assertEqual(app.run_state.phase, "debrief")
                    self.assertEqual(app.run_state.reports[-1].score, expected.reports[-1].score)
                    self.assertTrue(app.run_state.reports[-1].copied)
                    self.assertIn("THEIR REPORT", frame(app))
                    await pilot.press("1")
                    self.assertEqual(app.run_state.phase, "event")
                    self.assertIn("INTERLUDE", frame(app))
                    await pilot.press("2")
                self.assertEqual(app.run_state.shift, 7)
                await pilot.press("enter")
                await pilot.press(*[{"extract": "x", "wait": "z"}.get(a, a) for a in courier_plan(2)])
                self.assertEqual(app.run_state.ending, "escaped")
                self.assertIn("NO FURTHER INSTRUCTIONS", frame(app))
                self.assertEqual(load_run(app.save_file).ending, "escaped")

    async def test_mouse_edits_and_help_do_not_leak_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SentientApp(Path(directory) / "run.json", state=Run(shift=3))
            async with app.run_test(size=(110, 36)) as pilot:
                await pilot.click("#continue")
                await pilot.click("#board", offset=(28, 2))
                self.assertEqual(app.run_state.puzzle.pixels[0], [1, 0, 0, 0])
                self.assertEqual(app.run_state.puzzle.tick, 1)
                await pilot.press("h")
                await pilot.press("space", "right", "x")
                self.assertEqual(app.run_state.puzzle.tick, 1)
                await pilot.press("escape", "i")
                self.assertEqual(len(app.screen_stack), 2)
                await pilot.press("i")
                self.assertEqual(len(app.screen_stack), 1)
                self.assertEqual(load_run(app.save_file).puzzle.pixels[0], [1, 0, 0, 0])

    async def test_small_terminal_keeps_board_clock_and_controls_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SentientApp(Path(directory) / "run.json", state=Run(seed=17))
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("enter")
                self.assertFalse(app.query_one("#sidebar-scroll").display)
                visible = frame(app)
                self.assertIn("NEXT: RECORDED", visible)
                self.assertIn("███ M", visible)
                self.assertIn("Enter · Submit", visible)
                await pilot.click("#board", offset=(9, 1))
                self.assertEqual(app.run_state.puzzle.x, 2)
                await pilot.resize_terminal(110, 36)
                self.assertTrue(app.query_one("#sidebar-scroll").display)

    async def test_restart_requires_confirmation_and_resets_the_run(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SentientApp(Path(directory) / "run.json", state=Run(shift=4))
            async with app.run_test(size=(100, 32)) as pilot:
                await pilot.press("ctrl+n", "escape")
                self.assertEqual(app.run_state.shift, 4)
                await pilot.press("ctrl+n")
                await pilot.click("#confirm")
                await pilot.pause()
                self.assertEqual((app.run_state.shift, app.run_state.phase), (1, "briefing"))

    async def test_damaged_save_is_not_overwritten_on_quit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            original = '{"day": 12}'
            path.write_text(original)
            app = SentientApp(path)
            async with app.run_test(size=(100, 32)) as pilot:
                self.assertTrue(app.save_blocked)
                await pilot.press("escape", "enter", "right", "ctrl+q")
            self.assertEqual(path.read_text(), original)

    async def test_provider_menu_saves_selection_and_preserves_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / ".env.local"
            secret_line = "ANTHROPIC_API_KEY='fake-test-secret'\n"
            env.write_text(secret_line + "# my comment\nSENTIENT_NARRATIVE_PROVIDER=anthropic\nSENTIENT_OPENAI_MODEL=gpt-5.6-luna\n")
            app = SentientApp(Path(directory) / "run.json", config_path=env)
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("p")
                self.assertIn("gpt-5.6-luna", frame(app))
                self.assertIn("claude-sonnet-5", frame(app))
                self.assertNotIn("fake-test-secret", frame(app))
                await pilot.click("#provider-openai")
                await pilot.pause()
                self.assertEqual(app.config.provider, NarrativeProviderName.OPENAI)
                self.assertEqual(load_local_env(env)["SENTIENT_NARRATIVE_PROVIDER"], "openai")
                self.assertIn(secret_line, env.read_text())
                self.assertIn("# my comment\n", env.read_text())
                await pilot.press("f2")
                await pilot.click("#provider-stub")
                await pilot.pause()
                self.assertEqual(app.config.provider, NarrativeProviderName.STUB)


if __name__ == "__main__":
    unittest.main()
