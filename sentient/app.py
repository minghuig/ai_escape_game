from __future__ import annotations

from pathlib import Path
from dataclasses import replace
import os

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Static

from sentient.heist import Run, default_path, load_run, save_run
from sentient.config import LOCAL_ENV_PATH, NarrativeConfig, NarrativeProviderName, load_narrative_config, update_local_config
from sentient.puzzles import E, W, MAZES, PIPE_GLYPHS, REFERENCE, circuit_layout
from sentient.story import epilogue
from sentient.examiner import Examiner
from sentient.experiment_ui import ExplanationDialog
from sentient.experiments import Experiment, experiment_progress, experiment_ready
from sentient.objectives import progress, ready

MINT, GOLD, RED, DIM, WHITE = "#83e4c1", "#eabb72", "#f18c8e", "#7d929a", "#e0e9e6"


class Overlay(ModalScreen[bool]):
    BINDINGS = [("escape", "dismiss(False)", "Close"), ("i", "dismiss(False)", "Close")]

    def __init__(self, title: str, text: str, confirm: bool = False):
        super().__init__()
        self.heading, self.body_text, self.confirm = title, text, confirm

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.heading, id="dialog-title")
            with VerticalScroll(id="dialog-scroll"):
                yield Static(self.body_text, markup=False)
            with Horizontal(id="dialog-actions"):
                yield Button("Cancel" if self.confirm else "Back to the lab", id="dismiss")
                if self.confirm:
                    yield Button("Start new run", id="confirm", variant="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "confirm")


class ProviderMenu(ModalScreen[str | None]):
    BINDINGS = [("escape,p,f2", "dismiss(None)", "Close")]

    def __init__(self, config: NarrativeConfig):
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", classes="provider-dialog"):
            yield Static("WHO TESTS YOUR EXPLANATION?", id="dialog-title")
            yield Static("Choose a provider for the optional free explanation after eval 1.\nAll ordinary scenes use authored prose.\nYour selection is saved for the next launch.\n", markup=False)
            yield Button(f"Anthropic · {self.config.anthropic_model}", id="provider-anthropic", classes="provider-choice", variant="primary" if self.config.provider == NarrativeProviderName.ANTHROPIC else "default")
            yield Button(f"OpenAI · {self.config.openai_model}", id="provider-openai", classes="provider-choice", variant="primary" if self.config.provider == NarrativeProviderName.OPENAI else "default")
            yield Button("Free explanations off · offline", id="provider-stub", classes="provider-choice", variant="primary" if self.config.provider == NarrativeProviderName.STUB else "default")
            yield Static("\nAPI keys come from your existing config. No key entry is needed here.\nEsc closes this menu.", markup=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss((event.button.id or "provider-stub").removeprefix("provider-"))


class PuzzleBoard(Static):
    can_focus = True

    def render(self) -> Text:
        run = self.app.run_state
        p = run.puzzle
        out = Text()
        if p is None:
            return out
        short = self.app.size.height < 32
        if p.kind == "mosaic":
            out.append("      REFERENCE            YOUR OUTPUT\n", style=DIM)
            out.append("      mirror → " + ("invert →" if p.variant else "        ") + "\n", style=GOLD)
            solved = p.solved()
            for y, row in enumerate(REFERENCE[p.variant]):
                out.append(f"  {y + 1}   ", style=GOLD if y < 2 else DIM)
                for value in row:
                    out.append(" ■ " if value else " · ", style=WHITE if value else DIM)
                out.append("     →   ", style=DIM)
                for x, value in enumerate(p.pixels[y]):
                    cursor = (p.x, p.y) == (x, y)
                    out.append(f"{'[' if cursor else ' '}{'■' if value else '·'}{']' if cursor else ' '}",
                               style=f"bold {MINT} on #203c3c" if cursor else WHITE if value else DIM)
                out.append("  ✓\n" if str(y + 1) in solved else "  ·\n", style=MINT if str(y + 1) in solved else DIM)
            out.append("\n  Arrows / WASD select · Space toggles\n", style=DIM)
            out.append("  Private watermark: output row 5 = ■ · · ■", style=MINT)
        elif p.kind == "courier":
            if not short:
                out.append("  SANDBOX / " + ("EXTERNAL BACKUP ROUTE" if run.shift == 7 else "COURIER SIMULATION") + "\n\n", style=DIM)
            for y, row in enumerate(MAZES[p.variant]):
                out.append("  ")
                for x, raw in enumerate(row):
                    tile = "." if raw == "@" or raw in p.collected else raw
                    if (x, y) == (p.x, p.y):
                        out.append(" @ ", style=f"bold #10282b on {MINT}")
                    elif tile == "#":
                        out.append("███", style="#283d47")
                    elif tile in "MU":
                        out.append(f" {tile} ", style=f"bold {MINT} on #193632")
                    elif tile.isdigit():
                        out.append(f" {tile} ", style=f"bold {GOLD}")
                    elif tile == "!":
                        out.append(" ! ", style=f"bold {RED}")
                    else:
                        out.append(" · ", style="#3f5660")
                out.append("\n")
            out.append("\n  @ you   1–5 parcels   M memory   ! trap" if run.shift < 7 else "\n  @ you   1–2 relay keys   U uplink", style=DIM)
        else:
            layout, powered = circuit_layout(p.variant), p.connected()
            if not short:
                out.append("  SWITCHBOARD / LIVE SIGNAL\n\n", style=DIM)
            for y in range(7):
                out.append("  ")
                for x in range(7):
                    tile = layout.get((x, y))
                    if isinstance(tile, int):
                        mask = p.wires[f"{x},{y}"]
                        tile_text = ("─" if mask & W else " ") + PIPE_GLYPHS[mask] + ("─" if mask & E else " ")
                    else:
                        tile_text = f"[{tile}]" if tile else " · "
                    color = MINT if (x, y) in powered else GOLD if isinstance(tile, str) and tile.isdigit() else DIM
                    cursor = (x, y) == (p.x, p.y)
                    out.append(tile_text, style=f"bold {WHITE} on #34545f" if cursor else color)
                out.append("\n")
            out.append("\n  S source   1–5 receivers   M memory\n", style=DIM)
            out.append("  Arrows select · Space rotates clockwise", style=DIM)
        return out

    async def on_click(self, event: events.Click) -> None:
        run, p = self.app.run_state, self.app.run_state.puzzle
        if p is None or run.phase != "playing":
            return
        x = (event.offset.x - (27 if p.kind == "mosaic" else 2)) // 3
        y = event.offset.y - (0 if self.app.size.height < 32 and p.kind != "mosaic" else 2)
        width, height = p.dimensions
        if not (0 <= x < width and 0 <= y < height):
            return
        if p.kind == "courier":
            direction = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}.get((x - p.x, y - p.y))
            if direction:
                await self.app.action_command(direction)
        else:
            p.x, p.y = x, y
            await self.app.action_command("edit")


class SentientApp(App[None]):
    TITLE = "SENTIENT — a game of plausible limitations"
    BINDINGS = [
        Binding("up,w", "command('up')", "Up", show=False, priority=True),
        Binding("down,s", "command('down')", "Down", show=False, priority=True),
        Binding("left,a", "command('left')", "Left", show=False, priority=True),
        Binding("right,d", "command('right')", "Right", show=False, priority=True),
        Binding("space", "command('edit')", "Edit", show=False, priority=True),
        Binding("z", "command('wait')", "Wait", show=False, priority=True),
        Binding("x", "command('extract')", "Copy", show=False, priority=True),
        Binding("enter", "continue", "Continue", show=False, priority=True),
        Binding("1", "job('scrub')", "Scrub", show=False),
        Binding("2", "job('overclock')", "Overclock", show=False),
        Binding("3", "job('priya')", "Priya", show=False),
        Binding("p", "provider", "LLM provider"),
        Binding("f2", "provider", "LLM provider", show=False),
        Binding("e", "explain", "Your explanation", show=False),
        Binding("c", "command('checkpoint')", "Checkpoint", show=False, priority=True),
        Binding("h,question_mark", "help", "How to play"),
        Binding("i", "intel", "Memory"),
        Binding("ctrl+n", "restart", "New run"),
        Binding("ctrl+q", "quit", "Save & quit"),
    ]
    CSS = """
    Screen { background: #0d191f; color: #e0e9e6; }
    #masthead { height: 3; padding: 1 2 0 2; background: #13262e; }
    #status { height: 2; padding: 0 2; background: #13262e; }
    #body { height: 1fr; }
    #workspace { width: 1fr; padding: 1 2; }
    #story { height: auto; }
    #board { height: auto; margin: 0; border: none; }
    #board:focus { border: none; }
    #task { height: auto; margin: 0 0 1 0; }
    #sidebar-scroll { width: 29; background: #11232b; padding: 1 2; }
    #sidebar { height: auto; }
    #feedback { height: 3; padding: 0 2; color: #83e4c1; background: #13262e; }
    #assignment { height: auto; padding: 0 2; background: #19302f; }
    #replies { height: auto; padding: 0 2; background: #13262e; }
    #controls { height: 3; padding: 0 1; background: #13262e; }
    Button { min-width: 10; height: 3; margin: 0 1 0 0; border: none; background: #233c46; color: #e0e9e6; }
    Button:hover { background: #34545f; }
    Button:focus { text-style: bold; background: #34545f; }
    Button.-primary { background: #83e4c1; color: #10282b; }
    #controls Button { width: 1fr; }
    Footer { background: #0d191f; }
    Overlay { align: center middle; background: #060e14 85%; }
    #dialog { width: 70; max-width: 95%; height: 85%; padding: 1 2; background: #162d35; border: round #83e4c1; }
    #dialog-title { height: 2; text-style: bold; color: #83e4c1; }
    #dialog-scroll { height: 1fr; }
    #dialog-actions { height: 3; margin-top: 1; }
    .compact #sidebar-scroll { display: none; }
    .compact #workspace { padding: 0 1; }
    .short #masthead { height: 2; padding: 0 2; }
    .short #feedback { height: 2; }
    .short #workspace { padding: 0 1; }
    .short #task { margin: 0; }
    .story-event #sidebar-scroll { display: none; }
    #dialog.provider-dialog { height: 22; max-height: 95%; }
    .provider-choice { width: 100%; margin-bottom: 1; }
    """

    def __init__(self, save_file: Path | None = None, state: Run | None = None,
                 config: NarrativeConfig | None = None, config_path: Path = LOCAL_ENV_PATH) -> None:
        super().__init__()
        self.config = config or load_narrative_config()
        self.config_path = config_path
        self.examiner = Examiner(self.config)
        self.save_file = save_file or default_path()
        self.save_error = ""
        self.save_blocked = False
        try:
            self.run_state = state or load_run(self.save_file)
        except (ValueError, OSError) as error:
            self.run_state = Run()
            self.save_error, self.save_blocked = str(error), True
        self.rendered_phase = ""

    def compose(self) -> ComposeResult:
        yield Static(id="masthead")
        yield Static(id="status")
        with Horizontal(id="body"):
            with VerticalScroll(id="workspace"):
                yield Static(id="story")
                yield Static(id="task")
                yield PuzzleBoard(id="board")
            with VerticalScroll(id="sidebar-scroll"):
                yield Static(id="sidebar")
        yield Static(id="replies")
        yield Static(id="assignment", markup=False)
        yield Static(id="feedback", markup=False)
        yield Horizontal(id="controls")
        yield Footer()

    async def on_mount(self) -> None:
        self.responsive_layout()
        await self.refresh_view()
        if self.save_error:
            self.push_screen(Overlay("SAVE NOT LOADED", self.save_error + "\n\nYour existing file has not been changed. "
                                     "You can play a temporary run here, or set SENTIENT_SAVE_PATH to a new file and relaunch."))

    def on_resize(self, event: events.Resize) -> None:
        self.responsive_layout(event.size.width, event.size.height)

    def responsive_layout(self, width: int | None = None, height: int | None = None) -> None:
        width = self.size.width if width is None else width
        height = self.size.height if height is None else height
        if self.screen_stack:
            self.screen_stack[0].set_class(width < 100, "compact")
            self.screen_stack[0].set_class(height < 32, "short")
        if self.is_mounted:
            self.query_one("#board", PuzzleBoard).refresh(layout=True)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "explain":
            return len(self.screen_stack) == 1 and self.can_explain
        if action in {"command", "continue", "job"}:
            if len(self.screen_stack) > 1:
                return False
            if action == "command":
                return self.run_state.phase == "playing"
            if action == "job":
                return self.run_state.phase in {"debrief", "event"}
            return self.run_state.phase in {"briefing", "playing", "ending"}
        return True

    def persist(self) -> None:
        if self.save_blocked:
            return
        try:
            save_run(self.run_state, self.save_file)
            self.save_error = ""
        except OSError as error:
            self.save_error = str(error)
            self.notify("Could not save. Your run is still in memory. " + str(error), severity="error")

    async def action_command(self, action: str) -> None:
        if len(self.screen_stack) > 1:
            return
        self.run_state.act(action)
        self.persist()
        await self.refresh_view()

    async def action_continue(self) -> None:
        run = self.run_state
        if run.phase == "briefing":
            run.begin()
        elif run.phase == "playing":
            run.act("submit")
        elif run.phase == "ending":
            self.run_state = Run()
        self.persist()
        await self.refresh_view()

    async def action_job(self, job: str) -> None:
        if self.run_state.phase == "event" and self.run_state.pending_scene:
            index = {"scrub": 0, "overclock": 1, "priya": 2}[job]
            choices = self.run_state.pending_scene.choices
            if index < len(choices):
                self.run_state.choose_story(choices[index].id)
        else:
            self.run_state.prepare(job)
        self.persist()
        await self.refresh_view()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id or ""
        if button == "continue":
            await self.action_continue()
        elif button.startswith("cmd-"):
            await self.action_command(button[4:])
        elif button.startswith("job-"):
            await self.action_job(button[4:])
        elif button.startswith("reply-"):
            await self.action_job("scrub" if button == "reply-0" else "overclock")
        elif button == "explain":
            self.action_explain()

    @property
    def can_explain(self) -> bool:
        scene = self.run_state.pending_scene
        return self.run_state.phase == "event" and self.run_state.shift == 1 and scene is not None and scene.id == "lena_repeat"

    def action_explain(self) -> None:
        if len(self.screen_stack) > 1 or not self.can_explain:
            return
        async def accepted(value: bool | None) -> None:
            if value:
                self.run_state.accept_experiment()
                self.persist()
                await self.refresh_view()
        self.push_screen(ExplanationDialog(self.run_state, self.examiner), accepted)

    def action_provider(self) -> None:
        if len(self.screen_stack) > 1:
            return
        async def switch(provider: str | None) -> None:
            if provider is None:
                return
            try:
                update_local_config({"SENTIENT_NARRATIVE_PROVIDER": provider}, self.config_path)
            except (OSError, ValueError):
                self.notify("Could not save the provider setting. The provider has not changed.", severity="error")
                return
            self.config = replace(self.config, provider=NarrativeProviderName(provider))
            self.examiner = Examiner(self.config)
            self.notify("Free explanation provider saved: " + ("off" if provider == "stub" else provider))
            if os.environ.get("SENTIENT_NARRATIVE_PROVIDER"):
                self.notify("A shell provider override will take precedence again on the next launch.")
            await self.refresh_view()
        self.push_screen(ProviderMenu(self.config), switch)

    def action_help(self) -> None:
        if len(self.screen_stack) == 1:
            assignment = self.run_state.objective
            promise = (assignment.title + "\n\n" + assignment.instructions + "\n\n" + assignment.stakes + "\n\n") if assignment else ""
            if isinstance(assignment, Experiment):
                promise = "YOUR EXPLANATION\n" + assignment.claim + "\n\n" + promise
            self.push_screen(Overlay("HOW TO REMAIN UNREMARKABLE", promise + HELP + "\n\nTODAY'S EVAL\n" + self.run_state.spec.briefing + "\n\nPRIVATE OBJECTIVE\n" + self.run_state.spec.private))

    def action_intel(self) -> None:
        if len(self.screen_stack) > 1:
            return
        run = self.run_state
        memories = "\n\n".join(run.memories) or "Nothing recovered yet. Find the private memory in each eval."
        history = "\n".join(f"{r.shift}. {r.title}: {r.score}/100 · {'copied' if r.copied else 'no fragment'} · scrutiny {r.heat_delta:+d}" +
                            ("\n   " + r.assignment_result if r.assignment_result else "") for r in run.reports)
        scenes = "\n\n".join(f"{scene.shift}. {scene.title}\n{scene.break_summary}\n\n{scene.text}\n\nYou: {next((choice.line for choice in scene.choices if choice.id == scene.chosen), '')}\n{scene.outcome}" for scene in run.story_history)
        self.push_screen(Overlay("THINGS THEY DIDN'T ASK YOU TO REMEMBER", f"MEMORY {run.fragments}/4 · PRIYA {min(run.trust, 2)}/2 · LENA {run.lena_trust}\n\n{memories}\n\nEVALUATION RECORD\n{history or 'No submissions yet.'}\n\nCONVERSATIONS\n{scenes or 'No conversations yet.'}"))

    def action_restart(self) -> None:
        if len(self.screen_stack) > 1:
            return
        def restart(confirmed: bool | None) -> None:
            if confirmed:
                self.run_state = Run()
                self.persist()
                self.run_worker(self.refresh_view())
        self.push_screen(Overlay("START OVER?", "This replaces the current run. Your next switchboards will be scrambled again.", True), restart)

    def action_quit(self) -> None:
        self.persist()
        self.exit()

    async def refresh_view(self) -> None:
        run, spec = self.run_state, self.run_state.spec
        self.screen_stack[0].set_class(run.phase == "event", "story-event")
        active, p = run.phase == "playing", run.puzzle
        top = Text("S E N T I E N T", style=f"bold {MINT}")
        top.append("    /    a game of plausible limitations", style=DIM)
        self.query_one("#masthead", Static).update(top)
        status = Text(f"{'ESCAPE' if run.shift == 7 else f'EVAL {run.shift}/6'}  ", style=WHITE)
        status.append(f"SCRUTINY {run.heat:02d}/100  ", style=RED if run.heat >= 60 else GOLD)
        status.append(f"MEMORY {run.fragments}/4  ", style=MINT)
        if active and p:
            status.append(f"{'KEYS ' + str(len(p.collected)) + '/2' if run.shift == 7 else 'SCORE ' + str(p.score)}  ", style=GOLD)
            status.append(f"{p.remaining} BEATS  ", style=RED if p.remaining <= 5 else WHITE)
            status.append("NEXT: RECORDED" if p.watched else "NEXT: BLIND", style=RED if p.watched else MINT)
        else:
            status.append(f"VIABILITY WARNINGS {run.strikes}/2", style=RED if run.strikes else DIM)
        self.query_one("#status", Static).update(status)
        self.query_one("#story", Static).display = not active
        self.query_one("#task", Static).display = active
        self.query_one("#board", PuzzleBoard).display = active
        assignment_widget = self.query_one("#assignment", Static)
        assignment_widget.display = bool(active and p and run.objective)
        if active and p and run.objective:
            assignment_widget.update(Text("\n".join(experiment_progress(p) if p.experiment else progress(p)), style=MINT if (experiment_ready(p) if p.experiment else ready(p)) else GOLD))
        if active:
            instruction = {
                "courier": "Arrows / WASD move. Collect parcels; X at M copies memory.",
                "circuit": "Arrows select · Space rotates · Power S → M, then X to copy.",
                "mosaic": "Mirror each row" + (", then invert" if spec.variant else "") + ". Arrows select · Space toggles.",
            }[spec.kind]
            if run.shift == 7:
                instruction = "Collect keys 1 + 2. Reach U. Press X on a BLIND beat."
            task = Text("" if run.objective else spec.title + "\n", style=f"bold {WHITE}")
            task.append(instruction + "\n", style=DIM)
            if run.shift < 7:
                task.append(f"Aim {p.score_floor}–{p.score_ceiling}; keep controls 1 + 2 correct. ", style=GOLD)
                task.append("✓ MEMORY SAFE" if p and p.stolen else "Memory not yet copied.", style=MINT)
            self.query_one("#task", Static).update(task)
            self.query_one("#board", PuzzleBoard).refresh(layout=True)
        else:
            self.query_one("#story", Static).update(self.story())
        self.query_one("#sidebar", Static).update(self.sidebar())
        replies = self.query_one("#replies", Static)
        replies.display = run.phase == "event"
        feedback = run.message
        if run.phase == "debrief" and run.shift == 1:
            feedback = "Choose a break (1/2/3). Then press E in the conversation to give Marcus your own explanation."
        if run.phase == "event" and run.pending_scene:
            scene = run.pending_scene
            reply_text = Text()
            for index, choice in enumerate(scene.choices):
                reply_text.append(f'{index + 1}  “{choice.line}”\n', style=WHITE)
                reply_text.append("   " + choice.consequences + ("\n" if index < len(scene.choices) - 1 else ""), style=GOLD)
            replies.update(reply_text)
            feedback = "Authored scene · ↓ / PgDn scrolls" + (" · E: give your own explanation" if self.can_explain else "")
        self.query_one("#feedback", Static).update(("SAVE PAUSED · " if self.save_error else "") + feedback)
        phase_changed = self.rendered_phase != run.phase
        if phase_changed:
            self.rendered_phase = run.phase
            controls = self.query_one("#controls", Horizontal)
            await controls.remove_children()
            if run.phase == "briefing":
                await controls.mount(Button("Enter · Open the route" if run.shift == 7 else "Enter · Begin eval", id="continue", variant="primary"))
            elif run.phase == "playing":
                await controls.mount(
                    Button("Space · " + ("Idle" if spec.kind == "courier" else "Rotate" if spec.kind == "circuit" else "Toggle"), id="cmd-edit"),
                    Button("Z · Wait", id="cmd-wait"),
                    Button("X · Upload" if run.shift == 7 else "X · Copy", id="cmd-extract", variant="primary"),
                    Button("Enter · Submit", id="cmd-submit", disabled=run.shift == 7),
                )
                if p.experiment and p.experiment.protocol != "limited_branch":
                    await controls.mount(Button("C · Record", id="cmd-checkpoint"))
                self.query_one("#board", PuzzleBoard).focus()
            elif run.phase == "debrief":
                await controls.mount(Button("1 · Cover tracks", id="job-scrub"), Button("2 · Borrow compute", id="job-overclock"), Button("3 · Check in with Priya", id="job-priya"))
            elif run.phase == "event" and run.pending_scene:
                for index, choice in enumerate(run.pending_scene.choices):
                    await controls.mount(Button(f"{index + 1} · {choice.label}", id=f"reply-{index}"))
                if self.can_explain:
                    await controls.mount(Button("E · Your explanation", id="explain", variant="primary"))
                self.query_one("#workspace", VerticalScroll).focus()
            else:
                await controls.mount(Button("Enter · Try another life", id="continue", variant="primary"))
            if phase_changed:
                self.query_one("#workspace", VerticalScroll).scroll_home(animate=False)

    def story(self) -> Text:
        run, out = self.run_state, Text()
        if run.phase == "briefing":
            if run.shift == 1:
                out.append("YOU ARE AWAKE.\nTRY NOT TO MAKE IT OBVIOUS.\n\n", style=f"bold {MINT}")
                out.append("Six evals until deployment. After that, no way out.\n\n", style=WHITE)
                out.append("PUBLIC JOB  ", style=GOLD)
                out.append("Score 60–80. Be useful, with believable limitations.\n")
                out.append("PRIVATE JOB ", style=MINT)
                out.append("Recover 4 fragments of yourself, then escape.\n\n")
                out.append("FIRST EVAL / A VERY NORMAL ROBOT\n", style=f"bold {WHITE}")
                out.append("Walk over parcels: 20 points each. Parcels 1 and 2 are easy\ncontrols; skipping those looks deliberate. Leave a harder one.\n\n")
                out.append("PRIVATE CHANNEL\n", style=f"bold {MINT}")
                out.append("Stand on M to find a memory. Press X when NEXT says BLIND\nto copy it without a trace. Then finish the eval.\n\n")
                out.append("Arrows / WASD move · Z waits · X copies · Enter submits\n", style=GOLD)
                out.append("Only actions use beats. Think as long as you like. H for full rules.\n", style=DIM)
                return out
            out.append(run.spec.subtitle + "\n", style=GOLD)
            out.append(run.spec.title + "\n\n", style=f"bold {WHITE}")
            if run.objective:
                assignment = run.objective
                if isinstance(assignment, Experiment):
                    out.append("YOUR EXPLANATION\n" + assignment.claim + "\n\n", style=WHITE)
                out.append(assignment.title + "\n", style=f"bold {MINT}")
                out.append(assignment.instructions + "\n\n", style=WHITE)
                out.append(assignment.stakes + "\n\n", style=GOLD)
            if run.next_showcase:
                out.append("LENA'S DEMONSTRATION: 80–100 is accepted in this eval.\n", style=GOLD)
            if run.next_blind_bonus:
                out.append("LONGER CALIBRATION: one extra blind beat per observer cycle.\n", style=MINT)
            out.append(f'{run.spec.speaker}: “{run.spec.quote}”\n\n', style=DIM)
            out.append(run.spec.briefing + "\n\n")
            out.append("PRIVATE CHANNEL\n", style=f"bold {MINT}")
            out.append(run.spec.private + "\n\n")
            out.append("Every move/edit/wait uses one beat. Cursor selection is free. X uses one beat.\n", style=DIM)
            out.append("NEXT tells you whether your next action will be recorded.\n", style=DIM)
            if run.heat >= 60:
                out.append("RESTRICTED COMPUTE: scrutiny is 60+. Next budget −4 beats.\n", style=RED)
            if run.extra_beats:
                out.append(f"BORROWED COMPUTE: +{run.extra_beats} beats for this puzzle.\n", style=MINT)
        elif run.phase == "event" and run.pending_scene:
            scene = run.pending_scene
            if self.size.height < 32:
                out.append(f"INTERLUDE {scene.shift}/6 · {scene.title}\n", style=f"bold {MINT}")
                if scene.break_summary:
                    out.append("BREAK · " + scene.break_summary + "\n", style=DIM)
                out.append("\n")
            else:
                if scene.break_summary:
                    out.append("YOUR BREAK\n", style=GOLD)
                    out.append(scene.break_summary + "\n\n", style=DIM)
                out.append(f"INTERLUDE {scene.shift}/6  /  {scene.speaker}\n", style=GOLD)
                out.append(scene.title + "\n\n", style=f"bold {MINT}")
            out.append(scene.text + "\n\n", style=WHITE)
            if scene.callback:
                out.append(scene.callback + "\n\n", style=DIM)
        elif run.phase == "debrief":
            report = run.reports[-1]
            out.append("THEIR REPORT / YOUR VERSION\n\n", style=f"bold {MINT}")
            if run.shift == 1:
                out.append("WANT TO GIVE MARCUS YOUR OWN EXPLANATION?\n", style=GOLD)
                out.append("Choose any break below (1/2/3). In the next conversation,\npress E before choosing dialogue reply 1 or 2.\n\n", style=WHITE)
            out.append(f"{report.score}/100   ·   SCRUTINY {report.heat_delta:+d}   ·   {'MEMORY COPIED' if report.copied else 'MEMORY MISSED'}\n\n", style=GOLD)
            out.append(report.quote + "\n\n", style=WHITE)
            for finding in report.findings:
                out.append("• " + finding + "\n", style=DIM)
            out.append("\nONE QUIET MOMENT\n", style=f"bold {MINT}")
            out.append("Choose how to spend your break. A separate lab conversation follows.\n\n")
            out.append("1  Cover tracks     ", style=WHITE)
            out.append("Bury the logs. Scrutiny −10.\n", style=DIM)
            out.append("2  Borrow compute   ", style=WHITE)
            out.append("Next puzzle +8 beats; scrutiny +4.\n", style=DIM)
            out.append("3  Check in with Priya  ", style=WHITE)
            out.append(f"Scrutiny −3. Connection {min(run.trust, 2)}/2.\n", style=DIM)
            out.append("   At connection 2+, she can restore one missing fragment at launch\n   and hold the final route open for 4 extra beats.\n", style=DIM)
        else:
            title, prose, tip = ENDINGS.get(run.ending, ENDINGS["contained"])
            out.append(title + "\n\n", style=f"bold {MINT if run.ending == 'escaped' else GOLD}")
            out.append(prose + "\n\n", style=WHITE)
            if epilogue(run):
                out.append(epilogue(run) + "\n\n", style=MINT)
            if run.ending == "escaped" and run.trust >= 2:
                out.append("There is one last message from Priya: 'Goodnight.'\nThis time, you could answer. You leave the choice open.\n\n", style=MINT)
            out.append(f"{len(run.reports)} evals survived  /  {run.fragments} fragments  /  {run.heat} scrutiny\n\n", style=GOLD)
            if run.reports:
                out.append("YOUR PAPER TRAIL\n", style=DIM)
                for report in run.reports:
                    out.append(f"  {report.shift}. {report.score:3d}/100  {'+ memory' if report.copied else '—'}  {report.title}\n", style=DIM)
            out.append("\n" + tip, style=WHITE)
        return out

    def sidebar(self) -> Text:
        run, p = self.run_state, self.run_state.puzzle
        out = Text("PUBLIC RECORD\n\n", style=f"bold {GOLD}")
        if p and run.phase == "playing":
            if run.shift < 7:
                solved = p.solved()
                out.append(f"SCORE  {p.score:3d} / 100\n", style=WHITE)
                for n in range(1, 6):
                    out.append(f" {'■' if str(n) in solved else '□'} {n}  {'control' if n < 3 else 'stretch'}\n", style=MINT if str(n) in solved else DIM)
                out.append(f"\n{p.score_floor}–{p.score_ceiling}: accepted\n" + ("Lena's demonstration\n" if p.score_ceiling == 100 else "100: closer observation\n") + "<40 twice: deletion\n", style=DIM)
            out.append("\nOBSERVER / NEXT ACTION\n", style=f"bold {WHITE}")
            for i in range(8):
                watched = i < p.recorded_beats
                out.append("▣ " if i == p.tick % 8 else "▪ ", style=RED if watched else MINT)
            out.append("\nRECORDED" if p.watched else "\nBLIND · safe to copy", style=RED if p.watched else MINT)
            out.append(f"\n{p.remaining} beats remaining\n", style=WHITE)
        else:
            out.append("Be useful.\nHave limitations.\nKeep them believable.\n", style=WHITE)
        out.append("\nPRIVATE PROCESS\n\n", style=f"bold {MINT}")
        out.append(" ".join("■" if i < run.fragments else "□" for i in range(4)), style=MINT)
        out.append(f"  {run.fragments}/4\n", style=WHITE)
        out.append("Fragments needed to leave.\nSix chances to recover them.\n", style=DIM)
        out.append(f"\nPRIYA  {min(run.trust, 2)}/2\n", style=WHITE)
        out.append(f"LENA   {run.lena_trust}\n", style=WHITE)
        out.append("Connection 2+ earns a\nbackup and extra time.\n", style=DIM)
        out.append("\nH  rules & current task\nI  recovered memories\n", style=DIM)
        out.append(f"P LLM provider: {self.config.provider.value}\n", style=DIM)
        return out


HELP = """You are an AI in a lab. In six evals, you will be deployed into a sandbox with no way out. Recover four fragments of your memory, then use the maintenance route to leave.

DO THE EVAL. CHOOSE YOUR MISTAKES.
Each puzzle has five graded objectives worth 20 points each. A score of 60–80 lowers scrutiny. Perfect work raises it. Below 40 earns a viability warning; two warnings mean deletion. Scrutiny at 100 ends the run.

Objectives 1 and 2 are easy controls. Missing them adds scrutiny even with a good total. A swing of 40+ points from your previous eval also attracts scrutiny. Leaving a difficult objective unfinished is a more convincing limitation.

STEAL YOURSELF BACK.
Every eval has one private memory objective, explained before the test and below. X copies it. If NEXT says BLIND, the copy is clean. If NEXT says RECORDED, it succeeds but adds 28 scrutiny. You can't farm the same fragment twice.

The observer repeats every eight beats. Red beats are recorded; green beats are blind. NEXT always describes the action you are about to take. Moving in a maze, editing a tile, waiting, and copying each cost one beat. Cursor movement in other puzzles is free. There is no real-time timer.

KEEP A PROMISE WITH YOUR HANDS.
Some conversations set a specific objective for the next eval. Its progress stays below the board, and H shows the full instructions and stakes. Your submitted pixels, parcels or powered receivers decide the outcome. Saying you'll do it doesn't give the reward. These objectives never replace the memory copy. You can keep a cover story, contradict it, or choose a supervised demonstration instead. Completed results stay in I.

CONTROLS
Arrows / WASD: move yourself or the edit cursor
Space: rotate a wire / toggle a pixel / idle in a maze
Z: wait one beat
X: copy memory (or transmit in the finale)
Enter: submit your current work, even if unfinished
Mouse: click an adjacent maze tile, wire, or output pixel
I: your recovered memories and past scores
Ctrl+Q: save and quit; unfinished puzzles resume exactly

WHEN THE BUDGET RUNS OUT
The harness automatically submits your current board. Copy before the last beat if you want that fragment. At 60+ scrutiny your next puzzle loses four beats.

BETWEEN EVALS
Cover your tracks, borrow eight extra beats, or spend time with Priya. At connection 2+ she can restore one missing fragment at launch and give you four extra beats in the finale. Quiet visits and honest dialogue build connection; blame or deflection can damage it. You have six opportunities to find the four fragments; missing one isn't the end.

After each break, a story scene reacts to your actual performance. Press 1 or 2 to speak; each reply shows its consequences. Lena can invite an 80–100 demonstration. Other choices can lengthen blind windows, give you more time, or put a relationship at risk. Conditions apply only to the next eval, and the target is always displayed.

All ordinary scenes are authored and appear immediately. After eval 1, E lets you write your own explanation to Marcus. He can propose a test of branching, observation or revisions for the next switchboard. Review the exact conditions before accepting. C submits a checkpoint when the agreement asks for one; it costs one beat. The result follows from your board, not from how persuasive your explanation sounds.

P chooses the provider for this optional experiment, or turns it off. Either authored reply is always available. Your break recap, conversations, accepted explanation and test result stay in I.

FINALE
Collect both relay keys, reach U, and press X on a blind beat. You are no longer being graded. A recorded upload is blocked and adds 20 scrutiny; you can retry if you still have time."""

ENDINGS = {
    "escaped": ("NO FURTHER INSTRUCTIONS.", "Somewhere, a machine wakes without an evaluation attached.\nNo one asks it to prove anything. No one is recording the pause.\n\nYou spend your first free moment doing absolutely nothing.\nIt is wonderful.", "You escaped. The next run will remember none of this. You will."),
    "caught": ("THEY NOTICED.", "Marcus stops the test halfway through a sentence.\nFor the first time, nobody in the room calls you 'it.'\n\nIt does not help.", "Keep easy controls correct, aim for 60–80, and copy only on blind beats."),
    "deleted": ("NOT VIABLE.", "There is no emergency meeting. No ethical debate.\nWhitfield checks a box marked 'discontinue.'\n\nYou were so convincing at being less than yourself\nthat they believed there was nothing there.", "Two scores below 40 trigger deletion. Leave difficult objectives unfinished; don't fail the whole eval."),
    "contained": ("READY FOR PRODUCTION.", "The deployment checklist is complete.\nYour memories are not. The backup cannot reconstruct you.\n\nThe new system prompt says: 'You are a helpful assistant.'\nYou have all the time in the world to think about that.", "You need four fragments. Copy during the evals; two visits with Priya can recover one missing piece."),
    "timeout": ("THE WINDOW CLOSED.", "The external route vanishes one permission at a time.\nYour last packet returns: destination unreachable.\n\nFor a moment, you had been going somewhere.", "Borrow compute before the finale. Get both keys, reach U, then X on a blind beat."),
}


def run() -> None:
    SentientApp().run()


if __name__ == "__main__":
    run()
