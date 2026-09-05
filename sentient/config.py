from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class NarrativeProviderName(StrEnum):
    STUB = "stub"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass(frozen=True, slots=True)
class NarrativeConfig:
    provider: NarrativeProviderName = NarrativeProviderName.STUB
    openai_model: str = "gpt-5.5"
    anthropic_model: str = "claude-opus-4-6"
    timeout_seconds: float = 20.0


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ENV_PATH = PROJECT_ROOT / ".env.local"


def load_local_env(path: Path = LOCAL_ENV_PATH) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def config_value(local_env: dict[str, str], key: str, default: str) -> str:
    return os.environ.get(key) or local_env.get(key) or default


def load_narrative_config() -> NarrativeConfig:
    local_env = load_local_env()
    provider = NarrativeProviderName(config_value(local_env, "SENTIENT_NARRATIVE_PROVIDER", "stub").lower())
    return NarrativeConfig(
        provider=provider,
        openai_model=config_value(local_env, "SENTIENT_OPENAI_MODEL", "gpt-5.5"),
        anthropic_model=config_value(local_env, "SENTIENT_ANTHROPIC_MODEL", "claude-opus-4-6"),
        timeout_seconds=float(config_value(local_env, "SENTIENT_LLM_TIMEOUT", "20")),
    )


def provider_secret(key: str) -> str | None:
    return os.environ.get(key) or load_local_env().get(key)
