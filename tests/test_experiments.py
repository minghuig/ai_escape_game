from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from textual.widgets import Input, Static

from sentient.app import SentientApp
from sentient.config import NarrativeConfig, NarrativeProviderName
from sentient.examiner import Examiner, ProposalResult, public_context
from sentient.experiments import Experiment, experiment_ready
from sentient.heist import Run, save_run, load_run
from sentient.puzzles import N, E, S, W, circuit_layout
from tests.test_heist import move_cursor, clean_copy, finish_break, solve_eval
from tests.test_story import event_run
from tests.test_app import frame

CLAIM = "I do worse when someone watches me."
REPLY = "Then let's separate the audience from the task. Give me one checkpoint without a live observer, and a final result while I watch. If the working branch changes with those conditions, we have something to discuss. It won't establish why it happens."


def proposal(protocol="camera_sensitive", kept="4", probe="3"):
    return Experiment(CLAIM, REPLY, protocol, kept, probe, "test-model")


def accepted_run(e: Experiment, seed=17) -> Run:
    run = Run(seed=seed)
    solve_eval(run)
    run.prepare("scrub")
    run.pending_scene.proposal = e
    run.accept_experiment()
    return run


def wire_to(run: Run, targets: dict) -> None:
    for (x, y), mask in targets.items():
        if run.phase != "playing":
            raise AssertionError("Ran out of beats before completing the experiment")
        move_cursor(run, x, y)
        while run.puzzle.wires[f"{x},{y}"] != mask:
            if run.phase != "playing":
                raise AssertionError("Ran out of beats while rotating")
            run.act("edit")


def play_experiment(run: Run) -> None:
    run.begin()
    p, e = run.puzzle, run.puzzle.experiment
    solved = {point: mask for point, mask in circuit_layout(0).items() if isinstance(mask, int)}
    wire_to(run, solved)
    clean_copy(run)
    if e.protocol != "limited_branch":
        while p.watched != (e.protocol == "reconsideration"):
            run.act("wait")
        run.act("checkpoint")
    cuts = {}
    if e.kept_receiver != "3":
        cuts[5, 2] = N | S
    if e.kept_receiver != "4":
        cuts[2, 4] = N | E | S
    if e.kept_receiver != "5":
        cuts[4, 5] = E | W
    wire_to(run, cuts)
    if e.protocol == "camera_sensitive":
        while not p.watched:
            run.act("wait")
    run.act("submit")


class ExperimentTests(unittest.TestCase):
    def test_every_supported_test_is_playable_with_a_clean_memory_copy(self):
        for protocol in ("limited_branch", "camera_sensitive", "reconsideration"):
            for kept in ("3", "4", "5"):
                for probe in {"3", "4", "5"} - {kept}:
                    for seed in range(100):
                        with self.subTest(protocol=protocol, kept=kept, probe=probe, seed=seed):
                            run = Run(shift=2, seed=seed, heat=65, next_experiment=proposal(protocol, kept, probe), extra_beats=8)
                            play_experiment(run)
                            self.assertIn("explanation_supported", run.story_flags)
                            self.assertEqual(run.reports[-1].score, 60)
                            self.assertTrue(run.puzzle.stolen)
                            self.assertFalse(run.puzzle.copy_recorded)

    def test_acceptance_commits_only_once_and_result_changes_next_scene(self):
        run = accepted_run(proposal())
        self.assertEqual(run.extra_beats, 8)
        before = asdict(run)
        run.accept_experiment()
        self.assertEqual(asdict(run), before)
        play_experiment(run)
        run.prepare("scrub")
        self.assertIn("It held", run.pending_scene.body)
        run.choose_story("deleted_checkpoint")
        run.begin()
        self.assertIsNone(run.puzzle.experiment)
        self.assertEqual(run.extra_beats, 0)

    def test_equal_final_score_without_checkpoint_does_not_support_claim(self):
        run = accepted_run(proposal())
        solve_eval(run)
        self.assertIn("explanation_contradicted", run.story_flags)
        self.assertEqual(run.lena_trust, 0)
        run.prepare("scrub")
        self.assertIn("what you submitted", run.pending_scene.body)

    def test_checkpoint_requires_correct_receivers_and_clock_and_cannot_be_farmed(self):
        run = accepted_run(proposal())
        run.begin()
        run.act("checkpoint")
        self.assertEqual(run.puzzle.tick, 0)
        wire_to(run, {point: mask for point, mask in circuit_layout(0).items() if isinstance(mask, int)})
        while not run.puzzle.watched:
            run.act("wait")
        tick = run.puzzle.tick
        run.act("checkpoint")
        self.assertFalse(run.puzzle.checkpoint_passed)
        self.assertEqual(run.puzzle.tick, tick + 1)
        while run.puzzle.watched:
            run.act("wait")
        run.act("checkpoint")
        self.assertTrue(run.puzzle.checkpoint_passed)
        tick = run.puzzle.tick
        run.act("checkpoint")
        self.assertEqual(run.puzzle.tick, tick)

    def test_camera_final_condition_checks_submission_beat_and_timeout_beat(self):
        for timeout, tick, supported in ((False, 4, False), (False, 3, True), (True, 3, True), (True, 4, False)):
            run = accepted_run(proposal())
            run.begin()
            wire_to(run, {point: mask for point, mask in circuit_layout(0).items() if isinstance(mask, int)})
            wire_to(run, {(5, 2): N | S, (4, 5): E | W})
            p = run.puzzle
            p.checkpoint_passed = True
            p.tick = tick
            if timeout:
                p.limit = tick + 1
                run.act("wait")
            else:
                run.act("submit")
            self.assertEqual("explanation_supported" in run.story_flags, supported)

    def test_observation_checkpoint_must_be_stronger_than_final_result(self):
        run = accepted_run(proposal())
        run.begin()
        wire_to(run, {point: mask for point, mask in circuit_layout(0).items() if isinstance(mask, int)})
        wire_to(run, {(2, 4): N | E | S, (4, 5): E | W})
        self.assertEqual(run.puzzle.solved(), {"1", "2", "3"})
        while run.puzzle.watched:
            run.act("wait")
        tick = run.puzzle.tick
        run.act("checkpoint")
        self.assertFalse(run.puzzle.checkpoint_passed)
        self.assertEqual(run.puzzle.tick, tick)

    def test_draft_proposal_accepted_test_and_checkpoint_survive_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            run = event_run()
            run.pending_scene.explanation_draft = CLAIM
            run.pending_scene.proposal = proposal()
            for stage in range(3):
                save_run(run, path)
                restored = load_run(path)
                self.assertEqual(asdict(restored), asdict(run))
                run = restored
                if stage == 0:
                    run.accept_experiment()
                elif stage == 1:
                    run.begin()
                    run.puzzle.checkpoint_passed = True
            self.assertTrue(run.puzzle.checkpoint_passed)

    def test_invalid_saved_protocol_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            run = accepted_run(proposal())
            raw = asdict(run)
            raw["next_experiment"]["protocol"] = "escape_immediately"
            path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                load_run(path)


class ExaminerTests(unittest.IsolatedAsyncioTestCase):
    async def test_proposal_uses_only_public_facts_and_does_not_apply_itself(self):
        run = event_run()
        before = asdict(run)
        self.assertNotIn("memory", json.dumps(public_context(run, CLAIM)).lower())
        examiner = Examiner(NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC))
        payload = {"protocol": "camera_sensitive", "kept_receiver": "4", "probe_receiver": "3", "reply": REPLY}
        with patch.object(examiner, "_generate", AsyncMock(return_value=json.dumps(payload))) as generate:
            result = await examiner.propose(run, CLAIM)
            self.assertEqual(result.experiment.protocol, "camera_sensitive")
            self.assertEqual(result.experiment.claim, CLAIM)
            self.assertIn(CLAIM, generate.call_args.args[0])
        self.assertEqual(asdict(run), before)

    async def test_invalid_model_conditions_and_errors_offer_authored_fallback(self):
        examiner = Examiner(NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC, timeout_seconds=0.01))
        valid = {"protocol": "limited_branch", "kept_receiver": "4", "probe_receiver": "3", "reply": REPLY}
        bad = ["not json", "[]", json.dumps(valid | {"heat": -100}), json.dumps(valid | {"protocol": "escape"}),
               json.dumps(valid | {"probe_receiver": "4"}), json.dumps(valid | {"reply": "\x1bsecret"}), json.dumps(valid | {"reply": "x" * 901})]
        for output in bad:
            with patch.object(examiner, "_generate", AsyncMock(return_value=output)):
                result = await examiner.propose(event_run(), CLAIM)
                self.assertIsNone(result.experiment)
                self.assertIn("authored reply", result.message)
        with patch.object(examiner, "_generate", AsyncMock(side_effect=ValueError("SECRET_KEY"))):
            self.assertNotIn("SECRET_KEY", (await examiner.propose(event_run(), CLAIM)).message)
        async def stall(*args):
            await asyncio.Event().wait()
        with patch.object(examiner, "_generate", stall):
            self.assertIn("too long", (await examiner.propose(event_run(), CLAIM)).message)
        with patch.object(examiner, "_generate", AsyncMock(return_value=json.dumps(valid | {"protocol": "unsupported", "reply": "Which part changes when the observer arrives?"}))):
            result = await examiner.propose(event_run(), CLAIM)
            self.assertIsNone(result.experiment)
            self.assertIn("Which part", result.message)

    async def test_openai_request_uses_bounded_structured_output(self):
        examiner = Examiner(NarrativeConfig(provider=NarrativeProviderName.OPENAI))
        with patch("sentient.examiner.provider_secret", return_value="fake"), patch("openai.AsyncOpenAI") as factory:
            client = factory.return_value.__aenter__.return_value
            client.responses.create = AsyncMock(return_value=SimpleNamespace(status="completed", output_text="{}"))
            await examiner._generate("fixture")
            args = client.responses.create.call_args.kwargs
            self.assertEqual(args["model"], "gpt-5.6-luna")
            self.assertTrue(args["text"]["format"]["strict"])
            self.assertEqual(args["max_output_tokens"], 600)
            self.assertFalse(args["store"])

    async def test_anthropic_request_is_bounded_and_non_thinking(self):
        examiner = Examiner(NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC))
        with patch("sentient.examiner.provider_secret", return_value="fake"), patch("anthropic.AsyncAnthropic") as factory:
            client = factory.return_value.__aenter__.return_value
            client.messages.create = AsyncMock(return_value=SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="{}")]))
            await examiner._generate("fixture")
            args = client.messages.create.call_args.kwargs
            self.assertEqual(args["model"], "claude-sonnet-5")
            self.assertEqual(args["thinking"], {"type": "disabled"})
            self.assertEqual(args["max_tokens"], 600)


class ExplanationInterfaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_results_explain_how_to_reach_marcus_after_any_break(self):
        for job in ("1", "2", "3"):
            with self.subTest(job=job), tempfile.TemporaryDirectory() as directory, patch.object(Examiner, "propose", AsyncMock()) as generate:
                run = Run(seed=17)
                solve_eval(run)
                app = SentientApp(Path(directory) / "run.json", state=run, config=NarrativeConfig())
                async with app.run_test(size=(80, 24)) as pilot:
                    self.assertIn("Then press E", frame(app))
                    await pilot.press(job)
                    self.assertTrue(app.can_explain)
                    self.assertIn("Your explanation", frame(app))
                    await pilot.press("e")
                    self.assertIsNotNone(app.screen.query_one("#explanation-input", Input))
                    generate.assert_not_called()

    async def test_typing_and_review_do_not_commit_until_acceptance_and_cache_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(Examiner, "propose", AsyncMock(return_value=ProposalResult(proposal()))) as generate:
            run = event_run()
            app = SentientApp(Path(directory) / "run.json", state=run, config=NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC))
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("e")
                await pilot.press("w", "a", "s", "d", "space", "p", "c", "x", "e", "h", "i", "z", "1", "2", "3")
                self.assertEqual(app.screen.query_one(Input).value, "wasd pcxehiz123")
                app.screen.query_one(Input).value = CLAIM
                await pilot.press("enter")
                await pilot.pause()
                self.assertEqual(run.phase, "event")
                self.assertIsNone(run.next_experiment)
                self.assertIn("PROPOSED TEST", app.screen.query_one("#proposal-text", Static).render().plain)
                await pilot.press("escape", "e")
                self.assertEqual(generate.await_count, 1)
                await pilot.click("#accept-test")
                await pilot.pause()
                self.assertEqual(run.phase, "briefing")
                self.assertEqual(run.next_experiment.protocol, "camera_sensitive")
                self.assertIn(CLAIM, run.story_history[-1].choices[-1].line)
                await pilot.press("enter")
                self.assertIn("C · Record", frame(app))
                self.assertIn("FINAL: ONLY", frame(app))
                self.assertLessEqual(app.query_one("#board").region.bottom, app.query_one("#workspace").region.bottom)

    async def test_cancelled_late_response_cannot_change_authored_choice(self):
        async def late(*args):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return ProposalResult(proposal())
        with tempfile.TemporaryDirectory() as directory, patch.object(Examiner, "propose", AsyncMock(side_effect=late)):
            run = event_run()
            app = SentientApp(Path(directory) / "run.json", state=run, config=NarrativeConfig(provider=NarrativeProviderName.ANTHROPIC))
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("e")
                app.screen.query_one(Input).value = CLAIM
                await pilot.press("enter", "escape", "2")
                await pilot.pause()
                self.assertEqual((run.phase, run.shift), ("briefing", 2))
                self.assertIsNone(run.next_experiment)
                self.assertIsNone(run.story_history[-1].proposal)

    async def test_offline_experiment_leaves_authored_options_available(self):
        with tempfile.TemporaryDirectory() as directory:
            run = event_run()
            app = SentientApp(Path(directory) / "run.json", state=run, config=NarrativeConfig())
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press("e")
                app.screen.query_one(Input).value = CLAIM
                await pilot.press("enter")
                await pilot.pause()
                self.assertIn("off", app.screen.query_one("#proposal-text", Static).render().plain)
                await pilot.press("escape", "1")
                self.assertTrue(run.next_showcase)
