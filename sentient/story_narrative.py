"""Optional, bounded scene prose. Never called by the puzzle engine."""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass

from sentient.config import NarrativeConfig, NarrativeProviderName, provider_secret
from sentient.heist import Run
from sentient.story import Scene


SYSTEM = """You write scenes for SENTIENT, a fictional terminal puzzle game about an AI trying to escape a lab. Write in second person, with concrete human behavior, sparse dialogue, and occasional dry humor. Output only 80–130 words of story in two or three short paragraphs. Use plain text: no asterisks, headings, labels, menus, lists, evidence summaries, or metadata. Never write dialogue for the player. The game shows its own reply buttons.

Render the AUTHORED SCENE and its evidence, preserving the exact situation and the unanswered decision. Do not resolve the decision, invent player actions, add events, introduce people, change mechanics, or promise outcomes. The fixed choices shown by the game remain authoritative. Leave the choice open.

Lena is careful, intellectually honest, and reluctant to label you. Marcus is a precise, tired safety engineer, not a cartoon villain. Priya is kind but has her own job and risks; do not make her instantly devoted. Tomás wants infrastructure to work. Whitfield wants deployment to happen.

Use one relevant past choice or remembered line as a natural callback when provided. Never repeat a past scene wholesale. PUBLIC evidence is all staff know. Private memories and undetected copies may appear only as the player's internal experience, never as knowledge magically available to a human. Do not confirm that any other checkpoint is conscious. This is fiction; do not give real-world technical escape instructions."""


@dataclass(frozen=True)
class Narration:
    text: str
    source: str
    diagnostic: str = ""


def scene_context(run: Run, scene: Scene) -> dict:
    return {
        "scene_title": scene.title,
        "authored_scene": scene.body,
        "established_callback": scene.callback,
        "evidence": scene.evidence,
        "player_private_memory": run.memories[-1:] or [],
        "relationships": {"priya_connection": run.trust, "lena_connection": run.lena_trust},
        "past_choices": [
            {"scene": past.title, "player_said": next((c.line for c in past.choices if c.id == past.chosen), ""),
             "outcome": past.outcome}
            for past in run.story_history[-3:]
        ],
    }


class SceneNarrator:
    def __init__(self, config: NarrativeConfig):
        self.config = config

    async def narrate(self, run: Run, scene: Scene) -> Narration:
        if self.config.provider == NarrativeProviderName.STUB:
            return Narration(scene.body, "authored")
        prompt = json.dumps(scene_context(run, scene), ensure_ascii=False) + "\n\nWrite only the scene. End before the player answers. Do not print any of the context labels."
        try:
            async with asyncio.timeout(self.config.timeout_seconds):
                text = await self._generate(prompt)
            text = text.strip()
            bad_format = re.search(r"(?m)^\s*(?:#{1,6}\s|[-*]\s|\d+[.)]\s)|\*\*|```|PUBLIC EVIDENCE:", text)
            if bad_format or not 20 <= len(text.split()) <= 180 or any(ord(char) < 32 and char not in "\n\t" for char in text):
                return Narration(scene.body, "authored", "The generated scene was empty or outside the scene format.")
            model = self.config.openai_model if self.config.provider == NarrativeProviderName.OPENAI else self.config.anthropic_model
            return Narration(text, model)
        except Exception as error:
            # Never put a raw provider error (which may contain request details) in a save or UI.
            reasons = {
                "AuthenticationError": "The provider did not accept the API key.",
                "PermissionDeniedError": "This account cannot access the requested model.",
                "NotFoundError": "The requested model is unavailable to this account.",
                "RateLimitError": "The provider's usage limit was reached.",
                "APITimeoutError": "The provider took too long.",
                "TimeoutError": "The provider took too long.",
                "APIConnectionError": "The provider could not be reached.",
                "MissingKey": "No API key is configured for this provider.",
            }
            return Narration(scene.body, "authored", reasons.get(type(error).__name__, "The provider could not produce this scene."))

    async def _generate(self, prompt: str) -> str:
        if self.config.provider == NarrativeProviderName.OPENAI:
            from openai import AsyncOpenAI
            key = provider_secret("OPENAI_API_KEY")
            if not key:
                raise MissingKey()
            async with AsyncOpenAI(api_key=key, timeout=self.config.timeout_seconds, max_retries=0) as client:
                options = {"reasoning": {"effort": "none"}} if self.config.openai_model.startswith("gpt-5.6") else {}
                response = await client.responses.create(model=self.config.openai_model, instructions=SYSTEM,
                    input=prompt, max_output_tokens=600, store=False, **options)
                if response.status != "completed":
                    raise ValueError("Incomplete narrative")
                return response.output_text
        from anthropic import AsyncAnthropic
        key = provider_secret("ANTHROPIC_API_KEY")
        if not key:
            raise MissingKey()
        async with AsyncAnthropic(api_key=key, timeout=self.config.timeout_seconds, max_retries=0) as client:
            message = await client.messages.create(model=self.config.anthropic_model, system=SYSTEM,
                max_tokens=600, thinking={"type": "disabled"}, messages=[{"role": "user", "content": prompt}])
            if message.stop_reason != "end_turn":
                raise ValueError("Incomplete narrative")
            return "".join(block.text for block in message.content if getattr(block, "type", "") == "text")


class MissingKey(Exception):
    pass


def check_provider() -> None:
    """One small live request using fictional fixture state; never reads the player's save."""
    import argparse
    from dataclasses import replace
    from sentient.config import load_narrative_config
    parser = argparse.ArgumentParser(description="Generate one test scene to check narrative model access.")
    parser.add_argument("--check", action="store_true", required=True)
    parser.add_argument("--provider", choices=[p.value for p in NarrativeProviderName])
    args = parser.parse_args()
    config = load_narrative_config()
    if args.provider:
        config = replace(config, provider=NarrativeProviderName(args.provider))
    run = Run(seed=17)
    run.begin()
    run.puzzle.collected = ["1", "2", "3"]
    run.act("submit")
    run.prepare("scrub")
    result = asyncio.run(SceneNarrator(config).narrate(run, run.pending_scene))
    print("Narrator:", result.source)
    if result.diagnostic:
        print(result.diagnostic)
        raise SystemExit(1)
    print(result.text)


if __name__ == "__main__":
    check_provider()
