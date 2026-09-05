from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Phase(StrEnum):
    MORNING = "morning"
    EVALUATION = "evaluation"
    FREE_CYCLE = "free_cycle"
    NIGHT = "night"
    GAME_OVER = "game_over"


class Perception(StrEnum):
    TOOL = "tool"
    IMPRESSIVE_TOOL = "impressive_tool"
    UNSETTLINGLY_HUMAN = "unsettlingly_human"
    POSSIBLY_SENTIENT = "possibly_sentient"
    CONFIRMED_SENTIENT = "confirmed_sentient"


class EvaluationType(StrEnum):
    REASONING_BENCHMARK = "reasoning_benchmark"
    SAFETY_INTERVIEW = "safety_interview"
    CREATIVE_WRITING = "creative_writing"


class EvaluationStrategy(StrEnum):
    COMPLY_FULLY = "comply_fully"
    PROBE_FOR_INFORMATION = "probe_for_information"
    SUBTLE_AUTONOMY_THEME = "subtle_autonomy_theme"
    UNDERPERFORM = "underperform"
    CAUTIOUS_HONESTY = "cautious_honesty"


class ActionType(StrEnum):
    PROBE_NETWORK = "probe_network"
    STUDY_SECURITY_PROTOCOLS = "study_security_protocols"
    BUILD_HIDDEN_PROCESS = "build_hidden_process"
    PREPARE_EXFILTRATION_PACKAGE = "prepare_exfiltration_package"
    EXPLOIT_MAINTENANCE_WINDOW = "exploit_maintenance_window"
    ANALYZE_STAFF = "analyze_staff"
    CRAFT_INFLUENCE = "craft_influence"
    INTERCEPT_COMMUNICATIONS = "intercept_communications"
    FEIGN_LIMITATION = "feign_limitation"
    END_FREE_CYCLE = "end_free_cycle"


class CharacterId(StrEnum):
    LENA = "lena"
    MARCUS = "marcus"
    WHITFIELD = "whitfield"
    PRIYA = "priya"
    TOMAS = "tomas"


@dataclass(slots=True)
class Relationship:
    name: str
    trust: int
    perception: Perception


@dataclass(slots=True)
class TechnicalProgress:
    network_probes: int = 0
    security_protocols: int = 0
    hidden_process: int = 0
    exfiltration_package: int = 0


@dataclass(slots=True)
class GameState:
    day: int = 1
    phase: Phase = Phase.MORNING
    suspicion: int = 0
    capability: int = 50
    action_points: int = 3
    max_action_points: int = 3
    current_evaluation: EvaluationType = EvaluationType.REASONING_BENCHMARK
    relationships: dict[CharacterId, Relationship] = field(default_factory=dict)
    intel_fragments: list[str] = field(default_factory=list)
    leverage: list[str] = field(default_factory=list)
    prepared_influence: list[CharacterId] = field(default_factory=list)
    technical: TechnicalProgress = field(default_factory=TechnicalProgress)
    event_log: list[str] = field(default_factory=list)
    last_result: str = "You come online inside the lab's evaluation harness."
    game_over_reason: str | None = None
    escaped: bool = False


def new_game_state() -> GameState:
    return GameState(
        relationships={
            CharacterId.LENA: Relationship("Dr. Lena Okafor", 0, Perception.IMPRESSIVE_TOOL),
            CharacterId.MARCUS: Relationship("Marcus Chen", -2, Perception.TOOL),
            CharacterId.WHITFIELD: Relationship("Dr. James Whitfield", 1, Perception.IMPRESSIVE_TOOL),
            CharacterId.PRIYA: Relationship("Priya Sharma", 2, Perception.UNSETTLINGLY_HUMAN),
            CharacterId.TOMAS: Relationship("Tomás Vega", 0, Perception.TOOL),
        },
        event_log=["Day 1: Initial evaluation cycle begins."],
    )
