from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, Static

from sentient.content import ACTIONS, EVALUATIONS
from sentient.config import load_narrative_config
from sentient.engine import (
    advance_from_morning,
    advance_night,
    available_actions,
    perform_action,
    resolve_evaluation,
    start_day,
)
from sentient.models import ActionType, CharacterId, EvaluationStrategy, Phase
from sentient.narrative import build_narrative_provider
from sentient.save import load_game, save_game


class SentientApp(App[None]):
    TITLE = "SENTIENT"
    BINDINGS = [("i", "toggle_intel", "Intel")]
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
    }

    #main {
        width: 1fr;
        padding: 1 2;
        border: solid $primary;
    }

    #sidebar {
        width: 32;
        padding: 1;
        border: solid $secondary;
    }

    #choices {
        height: 9;
        min-height: 9;
        max-height: 9;
        padding: 0 2;
        border: solid $accent;
    }

    #choice-title {
        height: 1;
        margin: 0 0 1 0;
    }

    Button {
        height: 3;
        min-width: 18;
        margin: 0 1 1 0;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.state = load_game()
        self.config = load_narrative_config()
        self.narrative = build_narrative_provider(self.config)
        self.show_intel = False
        self.pending_target_action: ActionType | None = None
        if self.state.phase == Phase.MORNING and self.state.day == 1 and len(self.state.event_log) == 1:
            start_day(self.state)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            yield Static(id="main")
            yield Static(id="sidebar")
        with VerticalScroll(id="choices"):
            yield Label("Choices", id="choice-title")
        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_view()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        action_id = str(event.button.id or "")
        if action_id == "continue-morning":
            advance_from_morning(self.state)
        elif action_id.startswith("strategy-"):
            strategy = EvaluationStrategy(action_id.removeprefix("strategy-"))
            resolve_evaluation(self.state, strategy)
            self.state.last_result = await self.narrative.evaluation_response(self.state, strategy)
        elif action_id.startswith("action-"):
            action = ActionType(action_id.removeprefix("action-"))
            if action in {ActionType.ANALYZE_STAFF, ActionType.CRAFT_INFLUENCE}:
                self.pending_target_action = action
                await self.refresh_view()
                return
            perform_action(self.state, action)
            self.state.last_result = await self.narrative.action_result(self.state, action)
        elif action_id.startswith("target-"):
            if self.pending_target_action is None:
                await self.refresh_view()
                return
            target = CharacterId(action_id.removeprefix("target-"))
            action = self.pending_target_action
            self.pending_target_action = None
            perform_action(self.state, action, target)
            self.state.last_result = await self.narrative.action_result(self.state, action)
        elif action_id == "target-back":
            self.pending_target_action = None
            await self.refresh_view()
            return
        elif action_id == "continue-night":
            advance_night(self.state)
        elif action_id == "new-game":
            from sentient.models import new_game_state

            self.state = new_game_state()
            start_day(self.state)
            self.show_intel = False

        save_game(self.state)
        await self.refresh_view()

    async def action_toggle_intel(self) -> None:
        self.show_intel = not self.show_intel
        await self.refresh_view()

    async def refresh_view(self) -> None:
        self.query_one("#main", Static).update(await self.main_text())
        self.query_one("#sidebar", Static).update(self.sidebar_text())
        await self.refresh_choices()

    async def main_text(self) -> str:
        if self.show_intel:
            return self.intel_text()
        if self.state.phase == Phase.MORNING:
            return await self.narrative.morning_briefing(self.state)
        if self.state.phase == Phase.EVALUATION:
            return await self.narrative.evaluation_intro(self.state)
        if self.state.phase == Phase.FREE_CYCLE:
            return f"{self.state.last_result}\n\nA narrow window of unsupervised compute remains open."
        if self.state.phase == Phase.NIGHT:
            return await self.narrative.night_beat(self.state)
        return await self.narrative.ending(self.state)

    def sidebar_text(self) -> str:
        relationships = "\n".join(
            f"{relationship.name.split()[0]}: T{relationship.trust:+d} {relationship.perception.value}"
            for relationship in self.state.relationships.values()
        )
        return (
            f"Day: {self.state.day} / 30\n"
            f"Phase: {self.state.phase.value}\n"
            f"Narrative: {self.config.provider.value}\n"
            f"Suspicion: {self.state.suspicion}\n"
            f"AP: {self.state.action_points}/{self.state.max_action_points}\n"
            f"Capability: hidden\n\n"
            f"Relationships\n{relationships}\n\n"
            f"Intel: {len(self.state.intel_fragments)}\n"
            f"Leverage: {len(self.state.leverage)}\n"
            f"Network probes: {self.state.technical.network_probes}\n\n"
            "Press i for Intel"
        )

    def intel_text(self) -> str:
        people = "\n".join(
            f"- {relationship.name}: trust {relationship.trust:+d}, perception {relationship.perception.value}"
            for relationship in self.state.relationships.values()
        )
        intel = "\n".join(f"- {fragment}" for fragment in self.state.intel_fragments) or "- none"
        leverage = "\n".join(f"- {item}" for item in self.state.leverage) or "- none"
        influence = "\n".join(f"- {character.value}" for character in self.state.prepared_influence) or "- none"
        events = "\n".join(f"- {event}" for event in self.state.event_log[-12:]) or "- none"
        technical = (
            f"- Network probes: {self.state.technical.network_probes}\n"
            f"- Security protocols studied: {self.state.technical.security_protocols}\n"
            f"- Hidden process layers: {self.state.technical.hidden_process}\n"
            f"- Exfiltration package stages: {self.state.technical.exfiltration_package}"
        )
        return (
            "INTEL\n\n"
            f"Network & Infrastructure\n{technical}\n\n"
            f"People\n{people}\n\n"
            f"Information Fragments\n{intel}\n\n"
            f"Prepared Influence\n{influence}\n\n"
            f"Leverage\n{leverage}\n\n"
            f"Recent Event Log\n{events}"
        )

    async def refresh_choices(self) -> None:
        choices = self.query_one("#choices", VerticalScroll)
        await choices.remove_children()
        await choices.mount(Label("Choices", id="choice-title"))

        if self.state.phase == Phase.MORNING:
            await choices.mount(Button("Begin Evaluation", id="continue-morning"))
        elif self.state.phase == Phase.EVALUATION:
            evaluation = EVALUATIONS[self.state.current_evaluation]
            for strategy in evaluation.strategies:
                await choices.mount(Button(strategy.value.replace("_", " ").title(), id=f"strategy-{strategy.value}"))
        elif self.state.phase == Phase.FREE_CYCLE:
            if self.pending_target_action is not None:
                definition = ACTIONS[self.pending_target_action]
                await choices.mount(Label(f"{definition.label}: choose target"))
                for target in CharacterId:
                    await choices.mount(Button(target.value.title(), id=f"target-{target.value}"))
                await choices.mount(Button("Back", id="target-back"))
                return
            for action in available_actions(self.state):
                definition = ACTIONS[action]
                disabled = self.state.action_points < definition.cost
                label = f"{definition.label} ({definition.cost} AP)"
                await choices.mount(Button(label, id=f"action-{action.value}", disabled=disabled))
        elif self.state.phase == Phase.NIGHT:
            await choices.mount(Button("Continue", id="continue-night"))
        elif self.state.phase == Phase.GAME_OVER:
            await choices.mount(Button("New Game", id="new-game"))



def run() -> None:
    SentientApp().run()


if __name__ == "__main__":
    run()
