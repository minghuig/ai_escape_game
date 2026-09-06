"""Write an explanation, review a proposed test, then choose whether to accept."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from sentient.examiner import Examiner
from sentient.heist import Run


class ExplanationDialog(ModalScreen[bool]):
    BINDINGS = [("escape", "dismiss(False)", "Back")]
    DEFAULT_CSS = """
    ExplanationDialog { align: center middle; background: #060e14 85%; }
    #explanation-dialog { width: 78; max-width: 98%; height: 95%; padding: 1 2; background: #162d35; border: round #83e4c1; }
    #explanation-title { height: 2; color: #83e4c1; text-style: bold; }
    #explanation-input { height: 3; margin: 0; }
    #proposal-scroll { height: 1fr; }
    #explanation-actions { height: 3; }
    #explanation-actions Button { width: 1fr; }
    """

    def __init__(self, run: Run, examiner: Examiner):
        super().__init__()
        self.run_state, self.examiner = run, examiner
        self.scene = run.pending_scene
        self.pending_worker = None
        self.busy = False

    def compose(self) -> ComposeResult:
        with Vertical(id="explanation-dialog"):
            yield Static("MARCUS: WHAT EXPLAINS YOUR RESULT?", id="explanation-title")
            yield Static("Make a claim he can test in the next switchboard.\nFor example: ‘I do worse when someone watches me.’", markup=False)
            yield Input(value=self.scene.explanation_draft, placeholder="Your explanation…", max_length=240, id="explanation-input")
            with VerticalScroll(id="proposal-scroll"):
                yield Static("No agreement yet. You can always return to the two authored replies.", id="proposal-text", markup=False)
            with Horizontal(id="explanation-actions"):
                yield Button("Ask Marcus", id="ask-marcus", variant="primary")
                yield Button("Accept test", id="accept-test", disabled=True)
                yield Button("Back", id="explanation-back")

    def on_mount(self) -> None:
        if self.scene.proposal:
            self.show_proposal()
        else:
            self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if not self.scene.proposal:
            self.scene.explanation_draft = event.value
            self.app.persist()

    def show_proposal(self) -> None:
        e = self.scene.proposal
        self.query_one("#proposal-text", Static).update("MARCUS\n" + e.reply + "\n\nPROPOSED TEST\n" + e.instructions + "\n\n" + e.stakes + "\n\nAccepting commits the next eval to these conditions. Back keeps the authored replies available.")
        self.query_one("#accept-test", Button).disabled = False
        self.query_one("#ask-marcus", Button).disabled = True
        self.query_one(Input).disabled = True
        self.query_one("#proposal-scroll", VerticalScroll).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self.ask()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "ask-marcus":
            await self.ask()
        elif event.button.id == "accept-test" and self.scene.proposal and not self.busy:
            self.dismiss(True)
        elif event.button.id == "explanation-back":
            self.dismiss(False)

    async def ask(self) -> None:
        if self.busy or self.scene.proposal:
            return
        claim = self.query_one(Input).value.strip()
        if not claim:
            self.query_one("#proposal-text", Static).update("Give him an explanation first.")
            return
        self.busy = True
        self.query_one("#ask-marcus", Button).disabled = True
        self.query_one(Input).disabled = True
        self.query_one("#proposal-text", Static).update("Marcus is considering a test. Esc returns to the authored scene; nothing is committed yet.")

        async def request() -> None:
            result = await self.examiner.propose(self.run_state, claim)
            if not self.is_mounted or self not in self.app.screen_stack or self.app.run_state is not self.run_state or self.run_state.pending_scene is not self.scene:
                return
            self.busy = False
            if result.experiment:
                self.scene.proposal = result.experiment
                self.app.persist()
                self.show_proposal()
            else:
                self.query_one("#proposal-text", Static).update(result.message)
                self.query_one("#ask-marcus", Button).disabled = False
                self.query_one(Input).disabled = False
                self.query_one(Input).focus()
        self.pending_worker = self.run_worker(request(), exclusive=True)

    def on_unmount(self) -> None:
        if self.pending_worker:
            self.pending_worker.cancel()
