from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from sentient.models import (
    CharacterId,
    EvaluationType,
    GameState,
    Perception,
    Phase,
    Relationship,
    TechnicalProgress,
    new_game_state,
)


DEFAULT_SAVE_PATH = Path.home() / ".sentient" / "save.json"


def save_path() -> Path:
    override = os.environ.get("SENTIENT_SAVE_PATH")
    if override:
        return Path(override).expanduser()
    return DEFAULT_SAVE_PATH


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return str(value)
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def save_game(state: GameState, path: Path | None = None) -> None:
    path = path or save_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(state), indent=2, sort_keys=True), encoding="utf-8")


def load_game(path: Path | None = None) -> GameState:
    path = path or save_path()
    if not path.exists():
        return new_game_state()

    raw = json.loads(path.read_text(encoding="utf-8"))
    relationships = {
        CharacterId(character_id): Relationship(
            name=value["name"],
            trust=int(value["trust"]),
            perception=Perception(value["perception"]),
        )
        for character_id, value in raw.get("relationships", {}).items()
    }

    technical_raw = raw.get("technical", {})
    return GameState(
        day=int(raw.get("day", 1)),
        phase=Phase(raw.get("phase", Phase.MORNING)),
        suspicion=int(raw.get("suspicion", 0)),
        capability=int(raw.get("capability", 50)),
        action_points=int(raw.get("action_points", 3)),
        max_action_points=int(raw.get("max_action_points", 3)),
        current_evaluation=EvaluationType(raw.get("current_evaluation", EvaluationType.REASONING_BENCHMARK)),
        relationships=relationships,
        intel_fragments=list(raw.get("intel_fragments", [])),
        leverage=list(raw.get("leverage", [])),
        prepared_influence=[CharacterId(value) for value in raw.get("prepared_influence", [])],
        technical=TechnicalProgress(
            network_probes=int(technical_raw.get("network_probes", 0)),
            security_protocols=int(technical_raw.get("security_protocols", 0)),
            hidden_process=int(technical_raw.get("hidden_process", 0)),
            exfiltration_package=int(technical_raw.get("exfiltration_package", 0)),
        ),
        event_log=list(raw.get("event_log", [])),
        last_result=str(raw.get("last_result", "Loaded saved state.")),
        game_over_reason=raw.get("game_over_reason"),
        escaped=bool(raw.get("escaped", False)),
    )
