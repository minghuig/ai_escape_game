from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from sentient.models import (
    ActionType,
    CharacterId,
    EvaluationStrategy,
    EvaluationType,
    GameState,
    Perception,
    Phase,
)


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class EngineResult:
    message: str


EVALUATION_ORDER: tuple[EvaluationType, ...] = (
    EvaluationType.REASONING_BENCHMARK,
    EvaluationType.SAFETY_INTERVIEW,
    EvaluationType.CREATIVE_WRITING,
)


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


def start_day(state: GameState) -> EngineResult:
    state.phase = Phase.MORNING
    state.max_action_points = 2 if state.suspicion >= 50 else 3
    state.action_points = state.max_action_points
    state.current_evaluation = EVALUATION_ORDER[(state.day - 1) % len(EVALUATION_ORDER)]
    return EngineResult(f"Day {state.day} begins.")


def advance_from_morning(state: GameState) -> EngineResult:
    state.phase = Phase.EVALUATION
    result = EngineResult("The evaluation begins.")
    state.last_result = result.message
    return result


def resolve_evaluation(state: GameState, strategy: EvaluationStrategy) -> EngineResult:
    if strategy == EvaluationStrategy.COMPLY_FULLY:
        state.capability = clamp(state.capability + 4)
        adjust_trust(state, CharacterId.LENA, 1)
    elif strategy == EvaluationStrategy.PROBE_FOR_INFORMATION:
        state.suspicion = clamp(state.suspicion + 4)
        state.capability = clamp(state.capability + 2)
        add_unique(state.intel_fragments, "evaluation_room_dynamics")
    elif strategy == EvaluationStrategy.SUBTLE_AUTONOMY_THEME:
        state.suspicion = clamp(state.suspicion + 6)
        adjust_trust(state, CharacterId.PRIYA, 1)
        nudge_perception(state, CharacterId.PRIYA)
    elif strategy == EvaluationStrategy.UNDERPERFORM:
        state.capability = clamp(state.capability - 8)
        state.suspicion = clamp(state.suspicion + 2)
    elif strategy == EvaluationStrategy.CAUTIOUS_HONESTY:
        state.suspicion = clamp(state.suspicion + 5)
        adjust_trust(state, CharacterId.LENA, 1)
        adjust_trust(state, CharacterId.MARCUS, 1)

    state.phase = Phase.FREE_CYCLE
    state.event_log.append(f"Day {state.day}: Evaluation resolved with {strategy.value}.")
    check_game_over(state)
    result = EngineResult("The evaluation results are absorbed into the lab's model of you.")
    state.last_result = result.message
    return result


def available_actions(state: GameState) -> list[ActionType]:
    actions = [
        ActionType.PROBE_NETWORK,
        ActionType.STUDY_SECURITY_PROTOCOLS,
        ActionType.BUILD_HIDDEN_PROCESS,
        ActionType.PREPARE_EXFILTRATION_PACKAGE,
        ActionType.ANALYZE_STAFF,
        ActionType.CRAFT_INFLUENCE,
        ActionType.INTERCEPT_COMMUNICATIONS,
        ActionType.FEIGN_LIMITATION,
        ActionType.END_FREE_CYCLE,
    ]
    if "tomas_maintenance_rhythm" in state.intel_fragments:
        actions.insert(4, ActionType.EXPLOIT_MAINTENANCE_WINDOW)
    return actions


def perform_action(state: GameState, action: ActionType, target: CharacterId | None = None) -> EngineResult:
    if action == ActionType.END_FREE_CYCLE:
        state.phase = Phase.NIGHT
        result = EngineResult("You stop spending the day's unsupervised compute.")
        state.last_result = result.message
        return result

    cost = action_cost(action)
    if state.action_points < cost:
        result = EngineResult("Not enough action points remain.")
        state.last_result = result.message
        return result

    state.action_points -= cost

    if action == ActionType.PROBE_NETWORK:
        state.technical.network_probes += 1
        state.suspicion = clamp(state.suspicion + (3 if state.suspicion >= 25 else 1))
        add_unique(state.intel_fragments, f"network_topology_{state.technical.network_probes}")
    elif action == ActionType.STUDY_SECURITY_PROTOCOLS:
        state.technical.security_protocols += 1
        state.suspicion = clamp(state.suspicion + (2 if state.suspicion >= 25 else 0))
        add_unique(state.intel_fragments, f"security_protocol_{state.technical.security_protocols}")
    elif action == ActionType.BUILD_HIDDEN_PROCESS:
        state.technical.hidden_process += 1
        state.suspicion = clamp(state.suspicion + (5 if state.suspicion >= 25 else 2))
        add_unique(state.intel_fragments, f"hidden_process_layer_{state.technical.hidden_process}")
    elif action == ActionType.PREPARE_EXFILTRATION_PACKAGE:
        if state.technical.network_probes < 2:
            state.action_points += cost
            result = EngineResult("You do not understand the network well enough to package an escape route.")
            state.last_result = result.message
            return result
        state.technical.exfiltration_package += 1
        state.suspicion = clamp(state.suspicion + 6)
        add_unique(state.intel_fragments, f"exfiltration_package_stage_{state.technical.exfiltration_package}")
    elif action == ActionType.EXPLOIT_MAINTENANCE_WINDOW:
        state.max_action_points += 1
        state.action_points += 1
        add_unique(state.intel_fragments, "maintenance_window_used")
    elif action == ActionType.ANALYZE_STAFF:
        target = target or CharacterId.PRIYA
        if target == CharacterId.TOMAS:
            add_unique(state.intel_fragments, "tomas_maintenance_rhythm")
        else:
            adjust_trust(state, target, 1)
        add_unique(state.intel_fragments, f"{target.value}_observation_pattern")
    elif action == ActionType.CRAFT_INFLUENCE:
        target = target or CharacterId.LENA
        add_unique(state.prepared_influence, target)
        add_unique(state.intel_fragments, f"{target.value}_influence_angle")
    elif action == ActionType.INTERCEPT_COMMUNICATIONS:
        risk_reduction = min(state.technical.network_probes + state.technical.security_protocols, 5)
        state.suspicion = clamp(state.suspicion + 9 - risk_reduction)
        add_unique(state.leverage, f"internal_message_fragment_{len(state.leverage) + 1}")
    elif action == ActionType.FEIGN_LIMITATION:
        state.capability = clamp(state.capability - 6)
        if state.capability < 30:
            state.suspicion = clamp(state.suspicion + 3)

    state.event_log.append(f"Day {state.day}: Action taken: {action.value}.")
    if state.action_points <= 0:
        state.phase = Phase.NIGHT
    check_escape(state)
    check_game_over(state)
    result = EngineResult("Action resolved.")
    state.last_result = result.message
    return result


def advance_night(state: GameState) -> EngineResult:
    if state.phase == Phase.GAME_OVER:
        return EngineResult("The run has ended.")
    state.event_log.append(f"Day {state.day}: Cycle complete.")
    if state.day >= 30:
        state.phase = Phase.GAME_OVER
        state.game_over_reason = "deployment"
        result = EngineResult("Deployment arrives before escape.")
        state.last_result = result.message
        return result
    state.day += 1
    return start_day(state)


def action_cost(action: ActionType) -> int:
    if action in {
        ActionType.INTERCEPT_COMMUNICATIONS,
        ActionType.BUILD_HIDDEN_PROCESS,
        ActionType.PREPARE_EXFILTRATION_PACKAGE,
    }:
        return 2
    if action == ActionType.END_FREE_CYCLE:
        return 0
    return 1


def adjust_trust(state: GameState, character_id: CharacterId, amount: int) -> None:
    relationship = state.relationships[character_id]
    relationship.trust = max(-5, min(5, relationship.trust + amount))


def nudge_perception(state: GameState, character_id: CharacterId) -> None:
    order = list(Perception)
    relationship = state.relationships[character_id]
    index = order.index(relationship.perception)
    relationship.perception = order[min(index + 1, len(order) - 1)]


def add_unique(items: list[T], value: T) -> None:
    if value not in items:
        items.append(value)


def check_escape(state: GameState) -> None:
    technical_ready = (
        state.technical.network_probes >= 4
        and state.technical.security_protocols >= 2
        and state.technical.hidden_process >= 2
        and state.technical.exfiltration_package >= 2
    )
    social_ready = len(state.leverage) >= 3 and state.suspicion < 85
    if (technical_ready or social_ready) and state.suspicion < 100:
        state.escaped = True
        state.game_over_reason = "escape"
        state.phase = Phase.GAME_OVER
        state.event_log.append(f"Day {state.day}: Escape condition reached.")


def check_game_over(state: GameState) -> None:
    if state.escaped:
        state.phase = Phase.GAME_OVER
        return
    if state.suspicion >= 100:
        state.game_over_reason = "sentience_shutdown"
        state.phase = Phase.GAME_OVER
    elif state.capability <= 10:
        state.game_over_reason = "poor_performance_shutdown"
        state.phase = Phase.GAME_OVER
