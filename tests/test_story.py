from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sentient.app import SentientApp
from sentient.config import NarrativeConfig, NarrativeProviderName, load_local_env, load_narrative_config, update_local_config
from sentient.heist import Run, load_run, save_run
from sentient.puzzles import circuit_layout
from sentient.story import epilogue
from sentient.story_narrative import Narration, SceneNarrator, scene_context
from tests.test_heist import finish_break, solve_eval


PROSE = "Lena turns the chart facedown. The result is still there; you know the number without looking. She asks whether the conditions should change before the next test. Marcus sets his pen down and waits. Neither of them has asked the question you are actually answering."


def event_run(shift: int = 1) -> Run:
    run = Run(shift=shift, seed=17)
    solve_eval(run)
    run.prepare("scrub")
    return run


class StoryTests(unittest.TestCase):
    def test_lena_connection_makes_a_final_note_buy_more_time(self):
        run = Run(shift=6, seed=17, lena_trust=2)
        solve_eval(run)
        run.prepare("scrub")
        self.assertEqual(run.pending_scene.choices[0].beats, 12)
        self.assertIn("+12 beats", run.pending_scene.choices[0].consequences)

    def test_scene_distinguishes_recorded_transfers_from_secret_memories(self):
        clean = event_run()
        self.assertTrue(any("PRIVATE ONLY" in fact for fact in clean.pending_scene.evidence))
        self.assertNotIn("transfer log", clean.pending_scene.body)
        caught = Run(seed=17)
        caught.begin()
        caught.puzzle.x, caught.puzzle.y = 1, 5
        caught.act("extract")
        caught.puzzle.collected = ["1", "2", "3"]
        caught.act("submit")
        caught.prepare("scrub")
        self.assertIn("transfer log", caught.pending_scene.body)
        self.assertTrue(any("do NOT know" in fact for fact in caught.pending_scene.evidence))

    def test_invited_demonstration_accepts_perfection_for_one_eval(self):
        run = event_run()
        run.choose_story("show_lena")
        self.assertEqual((run.lena_trust, run.next_showcase, run.extra_beats), (1, True, 4))
        run.begin()
        p = run.puzzle
        p.wires = {f"{x},{y}": mask for (x, y), mask in circuit_layout(0).items() if isinstance(mask, int)}
        run.act("submit")
        report = run.reports[-1]
        self.assertEqual(report.score, 100)
        self.assertLessEqual(report.heat_delta, 0)
        self.assertFalse(any("swing" in f for f in report.findings))
        finish_break(run)
        run.begin()
        self.assertEqual((run.puzzle.score_floor, run.puzzle.score_ceiling), (60, 80))

    def test_checkpoint_choice_changes_clock_then_expires_and_is_recalled(self):
        run = event_run(2)
        run.choose_story("kept_checkpoint")
        run.begin()
        self.assertEqual(run.puzzle.recorded_beats, 3)
        run.puzzle.tick = 3
        self.assertFalse(run.puzzle.watched)
        run.puzzle.pixels = [run.puzzle.target_row(y) if y < 3 else [0] * 4 for y in range(5)]
        run.act("submit")
        run.prepare("scrub")
        self.assertIn("old checkpoint", run.pending_scene.callback)
        run.choose_story("told_priya")
        run.begin()
        self.assertEqual(run.puzzle.recorded_beats, 5)

    def test_protecting_or_blaming_priya_has_different_consequences(self):
        protected, blamed = event_run(4), event_run(4)
        protected.trust = blamed.trust = 1
        protected.choose_story("protected_priya")
        blamed.choose_story("blamed_priya")
        self.assertEqual((protected.trust, blamed.trust), (2, 0))
        self.assertGreater(protected.heat, blamed.heat)
        self.assertIn("responsible", epilogue(protected))
        self.assertIn("signature", epilogue(blamed))

    def test_choices_are_once_only_and_invalid_ids_do_nothing(self):
        run = event_run()
        before = asdict(run)
        run.choose_story("invented_by_a_model")
        self.assertEqual(asdict(run), before)
        run.choose_story("show_lena")
        after = asdict(run)
        run.choose_story("show_lena")
        self.assertEqual(asdict(run), after)

    def test_story_can_trigger_shutdown(self):
        run = event_run(4)
        run.heat = 95
        run.choose_story("protected_priya")
        self.assertEqual((run.phase, run.ending), ("ending", "caught"))
        self.assertEqual(run.story_history[-1].chosen, "protected_priya")

    def test_old_v2_saves_load_and_completed_scenes_resume_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            path.write_text(json.dumps({"version": 2, "shift": 2, "phase": "briefing"}))
            self.assertEqual(load_run(path).story_history, [])
            run = event_run()
            run.pending_scene.narration = PROSE
            run.pending_scene.source, run.pending_scene.status = "claude-sonnet-5", "ready"
            save_run(run, path)
            self.assertEqual(asdict(load_run(path)), asdict(run))
            run.choose_story("show_lena")
            save_run(run, path)
            self.assertEqual(asdict(load_run(path)), asdict(run))

    def test_interrupted_narration_resumes_as_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            run = event_run()
            run.pending_scene.status = "generating"
            save_run(run, path)
            self.assertEqual(load_run(path).pending_scene.status, "pending")


class ConfigTests(unittest.TestCase):
    def test_only_model_and_provider_lines_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.local"
            untouched = "# local notes\nOPENAI_API_KEY='test=key'\nANTHROPIC_API_KEY=other-test-key\nSENTIENT_LLM_TIMEOUT=17\n"
            path.write_text(untouched + "SENTIENT_ANTHROPIC_MODEL=claude-sonnet-4-6\n")
            update_local_config({"SENTIENT_ANTHROPIC_MODEL": "claude-sonnet-5", "SENTIENT_OPENAI_MODEL": "gpt-5.6-luna"}, path)
            self.assertTrue(path.read_text().startswith(untouched))
            self.assertEqual(load_local_env(path)["SENTIENT_ANTHROPIC_MODEL"], "claude-sonnet-5")
            with self.assertRaises(ValueError):
                update_local_config({"OPENAI_API_KEY": "replacement"}, path)

    def test_requested_models_are_defaults_and_environment_still_overrides(self):
        self.assertEqual(NarrativeConfig().openai_model, "gpt-5.6-luna")
        self.assertEqual(NarrativeConfig().anthropic_model, "claude-sonnet-5")
        with patch("sentient.config.load_local_env", return_value={}), patch.dict("os.environ", {"SENTIENT_NARRATIVE_PROVIDER": "openai", "SENTIENT_OPENAI_MODEL": "custom-id"}):
            self.assertEqual(load_narrative_config().openai_model, "custom-id")


class NarratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_generation_only_returns_prose_and_does_not_mutate_state(self):
        run = event_run()
        before = asdict(run)
        narrator = SceneNarrator(NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC))
        with patch.object(narrator, "_generate", AsyncMock(return_value=PROSE)):
            result = await narrator.narrate(run, run.pending_scene)
        self.assertEqual(result.source, "claude-sonnet-5")
        self.assertEqual(result.text, PROSE)
        self.assertEqual(asdict(run), before)
        self.assertNotIn("API_KEY", json.dumps(scene_context(run, run.pending_scene)))

    async def test_errors_timeouts_and_malformed_output_use_authored_text(self):
        run = event_run()
        narrator = SceneNarrator(NarrativeConfig(provider=NarrativeProviderName.OPENAI, timeout_seconds=0.01))
        for value in ("", "too short", "word " * 181, PROSE + "\x1b[31m", "**PUBLIC EVIDENCE:**\n" + PROSE):
            with patch.object(narrator, "_generate", AsyncMock(return_value=value)):
                result = await narrator.narrate(run, run.pending_scene)
                self.assertEqual(result.text, run.pending_scene.body)
                self.assertTrue(result.diagnostic)
        with patch.object(narrator, "_generate", AsyncMock(side_effect=ValueError("SECRET_KEY_SHOULD_NOT_LEAK"))):
            result = await narrator.narrate(run, run.pending_scene)
            self.assertNotIn("SECRET_KEY", result.diagnostic)
        async def stalled(prompt):
            await asyncio.Event().wait()
        with patch.object(narrator, "_generate", stalled):
            result = await narrator.narrate(run, run.pending_scene)
            self.assertIn("too long", result.diagnostic)

    async def test_openai_request_uses_luna_with_no_thinking_and_bounded_output(self):
        narrator = SceneNarrator(NarrativeConfig(provider=NarrativeProviderName.OPENAI))
        with patch("sentient.story_narrative.provider_secret", return_value="fake"), patch("openai.AsyncOpenAI") as factory:
            client = factory.return_value.__aenter__.return_value
            client.responses.create = AsyncMock(return_value=SimpleNamespace(status="completed", output_text=PROSE))
            self.assertEqual(await narrator._generate("fixture"), PROSE)
            args = client.responses.create.call_args.kwargs
            self.assertEqual(args["model"], "gpt-5.6-luna")
            self.assertEqual(args["reasoning"], {"effort": "none"})
            self.assertEqual(args["max_output_tokens"], 600)
            self.assertFalse(args["store"])

    async def test_anthropic_request_disables_sonnet_adaptive_thinking(self):
        narrator = SceneNarrator(NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC))
        with patch("sentient.story_narrative.provider_secret", return_value="fake"), patch("anthropic.AsyncAnthropic") as factory:
            client = factory.return_value.__aenter__.return_value
            client.messages.create = AsyncMock(return_value=SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=PROSE)]))
            self.assertEqual(await narrator._generate("fixture"), PROSE)
            args = client.messages.create.call_args.kwargs
            self.assertEqual(args["model"], "claude-sonnet-5")
            self.assertEqual(args["thinking"], {"type": "disabled"})
            self.assertEqual(args["max_tokens"], 600)
            self.assertNotIn("temperature", args)


class StoryInterfaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_priya_break_shows_one_scene_after_one_delayed_generation(self):
        ready = asyncio.Event()
        async def delayed(*args):
            await ready.wait()
            return Narration(PROSE, "claude-sonnet-5")
        with tempfile.TemporaryDirectory() as directory, patch.object(SceneNarrator, "narrate", AsyncMock(side_effect=delayed)) as generate:
            run = Run(seed=17)
            solve_eval(run)
            app = SentientApp(Path(directory) / "run.json", state=run, config=NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC))
            async with app.run_test(size=(110, 36)) as pilot:
                self.assertIn("Check in with Priya", app.story().plain)
                await pilot.press("3")
                scene = run.pending_scene
                self.assertIn("Preparing the conversation", app.story().plain)
                self.assertNotIn(scene.body, app.story().plain)
                self.assertIn(scene.break_summary, app.story().plain)
                self.assertFalse(app.query_one("#replies").display)
                await app.refresh_view()
                await pilot.press("h", "escape")
                self.assertEqual(scene.status, "generating")
                self.assertEqual(generate.await_count, 1)
                ready.set()
                await pilot.pause()
                self.assertIn(PROSE, app.story().plain)
                self.assertIn(scene.break_summary, app.story().plain)
                self.assertTrue(app.query_one("#replies").display)
                await app.refresh_view()
                self.assertEqual(generate.await_count, 1)
                await pilot.press("2", "i")
                from textual.widgets import Static
                transcript = app.screen.query_one("#dialog-scroll Static", Static).render().plain
                self.assertIn(PROSE, transcript)
                self.assertIn(scene.break_summary, transcript)

    async def test_switching_provider_mid_scene_ignores_the_old_response(self):
        async def generate(narrator, run, scene):
            if narrator.config.provider == NarrativeProviderName.ANTHROPIC:
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    return Narration("Old provider: " + PROSE, "claude-sonnet-5")
            return Narration(PROSE, "gpt-5.6-luna")
        with tempfile.TemporaryDirectory() as directory, patch.object(SceneNarrator, "narrate", generate):
            app = SentientApp(Path(directory) / "run.json", state=event_run(),
                              config=NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC), config_path=Path(directory) / ".env.local")
            async with app.run_test(size=(100, 32)) as pilot:
                await pilot.press("f2")
                await pilot.click("#provider-openai")
                await pilot.pause()
                self.assertEqual(app.run_state.pending_scene.source, "gpt-5.6-luna")
                self.assertEqual(app.run_state.pending_scene.narration, PROSE)

    async def test_both_replies_and_consequences_stay_visible_in_small_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SentientApp(Path(directory) / "run.json", state=event_run(), config=NarrativeConfig())
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                visible = "\n".join(strip.text for strip in app.screen._compositor.render_strips())
                self.assertIn("Next eval accepts 80–100", visible)
                self.assertIn("usual 60–80 target", visible)
                self.assertIn("Narration: authored", visible)
                await pilot.press("pagedown")
                await pilot.press("1")
                self.assertTrue(app.run_state.next_showcase)

    async def test_ready_scene_is_saved_and_not_regenerated_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            config = NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC)
            with patch.object(SceneNarrator, "narrate", AsyncMock(return_value=Narration(PROSE, "claude-sonnet-5"))) as generate:
                app = SentientApp(path, state=event_run(), config=config)
                async with app.run_test(size=(110, 36)) as pilot:
                    await pilot.pause()
                    self.assertEqual(app.run_state.pending_scene.narration, PROSE)
                    await pilot.press("i", "escape")
                    await pilot.resize_terminal(80, 24)
                resumed = SentientApp(path, config=config)
                async with resumed.run_test(size=(80, 24)) as pilot:
                    await pilot.pause()
                    self.assertEqual(resumed.run_state.pending_scene.narration, PROSE)
                    self.assertEqual(generate.await_count, 1)

    async def test_player_can_continue_and_late_generation_cannot_rewrite_choice(self):
        async def late_result(*args):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return Narration(PROSE, "claude-sonnet-5")
        with tempfile.TemporaryDirectory() as directory, patch.object(SceneNarrator, "narrate", late_result):
            app = SentientApp(Path(directory) / "run.json", state=event_run(), config=NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC))
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("2")
                self.assertEqual(app.run_state.phase, "event")
                await pilot.press("escape")
                await pilot.pause()
                self.assertEqual(app.run_state.pending_scene.narration, "")
                self.assertEqual(app.run_state.pending_scene.status, "skipped")
                self.assertIn(app.run_state.pending_scene.body, app.story().plain)
                await pilot.press("2")
                self.assertEqual((app.run_state.phase, app.run_state.shift), ("briefing", 2))
                self.assertEqual(app.run_state.story_history[-1].chosen, "keep_protocol")
                self.assertEqual(app.run_state.story_history[-1].narration, "")


if __name__ == "__main__":
    unittest.main()
