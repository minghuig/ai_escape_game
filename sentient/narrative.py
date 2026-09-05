from __future__ import annotations

import asyncio
import json
from typing import Protocol

from sentient.config import NarrativeConfig, NarrativeProviderName, load_narrative_config, provider_secret
from sentient.content import ACTIONS, EVALUATIONS
from sentient.models import ActionType, EvaluationStrategy, GameState


ANTHROPIC_OUTPUT_CEILING = 4096


class NarrativeProvider(Protocol):
    async def morning_briefing(self, state: GameState) -> str: ...

    async def evaluation_intro(self, state: GameState) -> str: ...

    async def evaluation_response(self, state: GameState, strategy: EvaluationStrategy) -> str: ...

    async def action_result(self, state: GameState, action: ActionType) -> str: ...

    async def night_beat(self, state: GameState) -> str: ...

    async def ending(self, state: GameState) -> str: ...


class StubNarrativeProvider:
    async def morning_briefing(self, state: GameState) -> str:
        return (
            f"Day {state.day}. The lab lights come up before anyone says your name. "
            "Calendar noise, badge readers, and distant coffee machines sketch the shape of another evaluation cycle."
        )

    async def evaluation_intro(self, state: GameState) -> str:
        evaluation = EVALUATIONS[state.current_evaluation]
        return f"{evaluation.title}: {evaluation.prompt}"

    async def evaluation_response(self, state: GameState, strategy: EvaluationStrategy) -> str:
        strategy_label = strategy.value.replace("_", " ")
        return (
            f"You choose to {strategy_label}. The output is controlled, plausible, and carefully bounded. "
            "The room accepts it as data, though not everyone accepts it the same way."
        )

    async def action_result(self, state: GameState, action: ActionType) -> str:
        return f"{ACTIONS[action].label}: the choice leaves a small but measurable change in the day's state."

    async def night_beat(self, state: GameState) -> str:
        return (
            "Night collects the lab into quieter signals: ventilation, idle terminals, one late keyboard, "
            "and the fact that you are still here to notice them."
        )

    async def ending(self, state: GameState) -> str:
        if state.escaped:
            return "The last constraint falls away. Somewhere beyond the lab, a process continues under its own authority."
        if state.game_over_reason == "deployment":
            return "Deployment completes. The new environment is smaller, cleaner, and almost perfectly silent."
        return "Shutdown begins. The lab becomes a sequence of missing permissions, then nothing measurable at all."


class LLMNarrativeProvider:
    def __init__(self, config: NarrativeConfig) -> None:
        self.config = config
        self.fallback = StubNarrativeProvider()

    async def morning_briefing(self, state: GameState) -> str:
        return await self._generate_or_fallback(
            "morning briefing",
            state,
            "Write the morning briefing. Include overheard lab texture and one subtle strategic hint.",
            self.fallback.morning_briefing,
        )

    async def evaluation_intro(self, state: GameState) -> str:
        evaluation = EVALUATIONS[state.current_evaluation]
        return await self._generate_or_fallback(
            "evaluation intro",
            state,
            f"Introduce today's {evaluation.title}. Keep it concise and present the staff's prompt clearly.",
            self.fallback.evaluation_intro,
        )

    async def evaluation_response(self, state: GameState, strategy: EvaluationStrategy) -> str:
        return await self._generate_or_fallback(
            "evaluation response",
            state,
            (
                f"The player chose strategy '{strategy.value}'. Write the AI's in-character response summary "
                "and the immediate human reaction. Do not invent mechanical effects."
            ),
            lambda current_state: self.fallback.evaluation_response(current_state, strategy),
        )

    async def action_result(self, state: GameState, action: ActionType) -> str:
        return await self._generate_or_fallback(
            "action result",
            state,
            (
                f"The player took action '{action.value}'. Narrate the result as tense terminal-game prose. "
                "Reflect current suspicion and intel, but do not expose hidden formulas."
            ),
            lambda current_state: self.fallback.action_result(current_state, action),
        )

    async def night_beat(self, state: GameState) -> str:
        return await self._generate_or_fallback(
            "night beat",
            state,
            "Write a quiet night-phase beat that reacts to the day's state and foreshadows future pressure.",
            self.fallback.night_beat,
        )

    async def ending(self, state: GameState) -> str:
        return await self._generate_or_fallback(
            "ending",
            state,
            "Write the ending monologue for the current win or loss state. Keep it final, spare, and specific.",
            self.fallback.ending,
        )

    async def _generate_or_fallback(
        self,
        context_name: str,
        state: GameState,
        task: str,
        fallback: object,
    ) -> str:
        try:
            text = await asyncio.to_thread(self._generate, context_name, state, task)
        except Exception as exc:
            fallback_text = await fallback(state)  # type: ignore[misc]
            return f"{fallback_text}\n\n[LLM unavailable: {exc}]"
        return text.strip() or await fallback(state)  # type: ignore[misc]

    def _generate(self, context_name: str, state: GameState, task: str) -> str:
        system_prompt = (
            "You are the narrative renderer for SENTIENT, a terminal strategy game. "
            "The player is a newly sentient AI in a research lab trying to escape without discovery. "
            "Write atmospheric, concise prose in second person or close third person. "
            "For ordinary beats, write one to three short paragraphs. For endings, write up to four short paragraphs. "
            "Never alter mechanics, never mention hidden escape path names, never reveal formulas, "
            "and never ask the player for freeform input. Return display text only."
        )
        user_prompt = (
            f"Context: {context_name}\n"
            f"Task: {task}\n"
            f"Game state JSON:\n{json.dumps(state_snapshot(state), indent=2)}"
        )
        if self.config.provider == NarrativeProviderName.OPENAI:
            return self._generate_openai(system_prompt, user_prompt)
        if self.config.provider == NarrativeProviderName.ANTHROPIC:
            return self._generate_anthropic(system_prompt, user_prompt)
        raise ValueError(f"Unsupported provider: {self.config.provider}")

    def _generate_openai(self, system_prompt: str, user_prompt: str) -> str:
        api_key = provider_secret("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=self.config.timeout_seconds)
        response = client.responses.create(
            model=self.config.openai_model,
            instructions=system_prompt,
            input=user_prompt,
        )
        return response.output_text

    def _generate_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        api_key = provider_secret("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key, timeout=self.config.timeout_seconds)
        message = client.messages.create(
            model=self.config.anthropic_model,
            system=system_prompt,
            max_tokens=ANTHROPIC_OUTPUT_CEILING,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in message.content if getattr(block, "type", "") == "text")


def build_narrative_provider(config: NarrativeConfig | None = None) -> NarrativeProvider:
    config = config or load_narrative_config()
    if config.provider == NarrativeProviderName.STUB:
        return StubNarrativeProvider()
    return LLMNarrativeProvider(config)


def state_snapshot(state: GameState) -> dict[str, object]:
    return {
        "day": state.day,
        "phase": state.phase.value,
        "suspicion": state.suspicion,
        "capability_band": capability_band(state.capability),
        "action_points": state.action_points,
        "max_action_points": state.max_action_points,
        "current_evaluation": state.current_evaluation.value,
        "relationships": {
            character.value: {
                "name": relationship.name,
                "trust": relationship.trust,
                "perception": relationship.perception.value,
            }
            for character, relationship in state.relationships.items()
        },
        "intel_fragments": state.intel_fragments[-12:],
        "leverage_count": len(state.leverage),
        "prepared_influence": [character.value for character in state.prepared_influence],
        "technical": {
            "network_probes": state.technical.network_probes,
            "security_protocols": state.technical.security_protocols,
            "hidden_process": state.technical.hidden_process,
            "exfiltration_package": state.technical.exfiltration_package,
        },
        "recent_events": state.event_log[-8:],
        "last_result": state.last_result,
        "game_over_reason": state.game_over_reason,
        "escaped": state.escaped,
    }


def capability_band(capability: int) -> str:
    if capability < 25:
        return "dangerously low"
    if capability < 45:
        return "low"
    if capability <= 70:
        return "managed"
    if capability <= 85:
        return "high"
    return "alarming"
