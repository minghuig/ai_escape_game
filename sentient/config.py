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
    openai_model: str = "gpt-5.6-luna"
    anthropic_model: str = "claude-sonnet-5"
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
        openai_model=config_value(local_env, "SENTIENT_OPENAI_MODEL", "gpt-5.6-luna"),
        anthropic_model=config_value(local_env, "SENTIENT_ANTHROPIC_MODEL", "claude-sonnet-5"),
        timeout_seconds=float(config_value(local_env, "SENTIENT_LLM_TIMEOUT", "20")),
    )


def provider_secret(key: str) -> str | None:
    return os.environ.get(key) or load_local_env().get(key)


def update_local_config(updates: dict[str, str], path: Path = LOCAL_ENV_PATH) -> None:
    """Change only explicitly requested settings, preserving keys and comments verbatim."""
    allowed = {"SENTIENT_NARRATIVE_PROVIDER", "SENTIENT_OPENAI_MODEL", "SENTIENT_ANTHROPIC_MODEL"}
    if not updates.keys() <= allowed or any("\n" in value or "\r" in value for value in updates.values()):
        raise ValueError("Unsupported narrative setting.")
    if "SENTIENT_NARRATIVE_PROVIDER" in updates:
        NarrativeProviderName(updates["SENTIENT_NARRATIVE_PROVIDER"])
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
    found = set()
    revised = []
    for line in lines:
        key, separator, _ = line.partition("=")
        if separator and key.strip() in updates:
            key = key.strip()
            revised.append(f"{key}={updates[key]}\n")
            found.add(key)
        else:
            revised.append(line)
    if revised and not revised[-1].endswith("\n"):
        revised[-1] += "\n"
    revised.extend(f"{key}={value}\n" for key, value in updates.items() if key not in found)
    temporary = path.with_name(path.name + ".tmp")
    # The temporary file also contains credentials, so keep it owner-readable only.
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.writelines(revised)
    temporary.replace(path)
