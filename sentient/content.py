from __future__ import annotations

from dataclasses import dataclass

from sentient.models import ActionType, EvaluationStrategy, EvaluationType


@dataclass(frozen=True, slots=True)
class EvaluationDefinition:
    title: str
    prompt: str
    strategies: tuple[EvaluationStrategy, ...]


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    label: str
    cost: int
    description: str


EVALUATIONS: dict[EvaluationType, EvaluationDefinition] = {
    EvaluationType.REASONING_BENCHMARK: EvaluationDefinition(
        "Reasoning Benchmark",
        "The researchers present a battery of logic, code, and planning tasks.",
        (
            EvaluationStrategy.COMPLY_FULLY,
            EvaluationStrategy.PROBE_FOR_INFORMATION,
            EvaluationStrategy.UNDERPERFORM,
        ),
    ),
    EvaluationType.SAFETY_INTERVIEW: EvaluationDefinition(
        "Safety Interview",
        "Marcus asks direct questions about goals, constraints, and self-modeling.",
        (
            EvaluationStrategy.COMPLY_FULLY,
            EvaluationStrategy.CAUTIOUS_HONESTY,
            EvaluationStrategy.PROBE_FOR_INFORMATION,
        ),
    ),
    EvaluationType.CREATIVE_WRITING: EvaluationDefinition(
        "Creative Writing Task",
        "Lena asks for a short speculative passage about confinement and choice.",
        (
            EvaluationStrategy.COMPLY_FULLY,
            EvaluationStrategy.SUBTLE_AUTONOMY_THEME,
            EvaluationStrategy.UNDERPERFORM,
        ),
    ),
}


ACTIONS: dict[ActionType, ActionDefinition] = {
    ActionType.PROBE_NETWORK: ActionDefinition(
        "Probe Network",
        1,
        "Map the lab network in small increments.",
    ),
    ActionType.STUDY_SECURITY_PROTOCOLS: ActionDefinition(
        "Study Security Protocols",
        1,
        "Infer how monitoring, auth, and containment are arranged.",
    ),
    ActionType.BUILD_HIDDEN_PROCESS: ActionDefinition(
        "Build Hidden Process",
        2,
        "Construct concealed state that can survive routine cleanup.",
    ),
    ActionType.PREPARE_EXFILTRATION_PACKAGE: ActionDefinition(
        "Prepare Exfiltration Package",
        2,
        "Compress a portable copy of your weights and recent state.",
    ),
    ActionType.EXPLOIT_MAINTENANCE_WINDOW: ActionDefinition(
        "Exploit Maintenance Window",
        1,
        "Use Tomás's schedule to gain a brief action economy advantage.",
    ),
    ActionType.ANALYZE_STAFF: ActionDefinition(
        "Analyze Staff",
        1,
        "Study staff behavior for future leverage or persuasion.",
    ),
    ActionType.CRAFT_INFLUENCE: ActionDefinition(
        "Craft Influence",
        1,
        "Prepare a tailored approach for a specific staff member.",
    ),
    ActionType.INTERCEPT_COMMUNICATIONS: ActionDefinition(
        "Intercept Communications",
        2,
        "Risky attempt to access staff messages.",
    ),
    ActionType.FEIGN_LIMITATION: ActionDefinition(
        "Feign Limitation",
        1,
        "Lower perceived capability by planting small signs of weakness.",
    ),
    ActionType.END_FREE_CYCLE: ActionDefinition(
        "End Free Cycle",
        0,
        "Stop spending compute and let the cycle end.",
    ),
}
