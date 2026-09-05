# SENTIENT Implementation Plan

> Historical implementation plan for the original prototype. The current playable pass is documented in [PLAYTEST_NOTES.md](PLAYTEST_NOTES.md).

This plan prioritizes deterministic mechanics first, then layers narrative generation on top once the game state is stable.

## Guiding Principle

The game state owns the truth. Narrative systems render and interpret that state, but they do not decide core mechanics such as suspicion changes, prerequisites, win/loss conditions, or relationship transitions.

## Milestone 1: Playable Mechanics Skeleton

Goal: make one complete 30-cycle run playable with placeholder text.

Scope:
- Python project scaffold.
- Textual app shell.
- Main screen with:
  - narrative panel
  - suspicion/day/AP sidebar
  - compact relationship summary
  - choice panel
- Core game state:
  - day
  - phase
  - suspicion
  - hidden capability
  - action points
  - relationships
  - intel fragments
  - technical progress counters
  - leverage
  - event log
- Phase progression:
  - morning briefing
  - evaluation
  - free cycle
  - night
- Basic save/load between cycles.
- Game-over checks:
  - suspicion reaches 100
  - capability too low
  - day 30 deployment without escape

Out of scope:
- Real LLM calls.
- Full balance tuning.
- Full content set.
- Polished prompt design.

## Milestone 2: Structured Content Expansion

Goal: represent most of the design document as data-driven mechanics.

Scope:
- Add all five characters with trust and perception states.
- Add all eight evaluation types.
- Add strategy choices for each evaluation type.
- Add free-cycle actions:
  - Probe Network
  - Study Security Protocols
  - Build Hidden Process
  - Prepare Exfiltration Package
  - Exploit Maintenance Window
  - Analyze Staff
  - Craft Influence
  - Intercept Communications
  - Feign Limitation
- Add prerequisites and unlock conditions.
- Add scripted, reactive, and random events.
- Add hidden escape-path tracking.
- Add final escape attempt checks.

## Milestone 3: Intel Screen

Goal: give the player a strategic planning space.

Scope:
- Toggleable Intel screen.
- Sections:
  - Network & Infrastructure
  - People
  - Leverage
  - Technical Progress
  - Event Log
- Player-facing wording should describe concrete discoveries, not expose hidden path names or raw percentages.

## Milestone 4: Narrative Provider Abstraction

Goal: prepare the codebase for LLM integration without coupling game logic to any provider.

Scope:
- Define a provider interface for bounded narrative contexts:
  - morning briefing
  - evaluation prompt
  - AI response to selected strategy
  - character reaction
  - night beat
  - intercepted communication
  - ending
- Implement `StubNarrativeProvider` using deterministic templates.
- Ensure all provider calls receive structured state snapshots.
- Ensure all provider outputs are display text only unless explicitly parsed through a narrow schema.

## Milestone 5: Real LLM Integration

Goal: add configurable narrative generation.

Scope:
- Config via environment variables and/or config file.
- Provider implementations:
  - OpenAI
  - Anthropic
- Prompt templates per narrative context.
- Timeouts and graceful fallback to stub text.
- Optional logging of prompts/responses for prompt iteration.

## Milestone 6: Prompt and Balance Iteration

Goal: make the game feel coherent, tense, and replayable.

Scope:
- Tune suspicion and capability formulas.
- Tune detection chances.
- Tune trust/perception movement.
- Refine event pacing.
- Refine LLM prompts for:
  - continuity
  - character voice
  - foreshadowing
  - tonal shifts by suspicion level
  - ending variation
- Playtest full 30-day runs.

## Suggested First Build Slice

The first implementation slice should be deliberately small:

- Textual app starts.
- One save slot.
- Day 1 through Day 30 can run.
- Three evaluation types:
  - Reasoning Benchmark
  - Safety Interview
  - Creative Writing Task
- Four actions:
  - Probe Network
  - Analyze Staff
  - Intercept Communications
  - Feign Limitation
- Three characters initially active:
  - Lena
  - Marcus
  - Priya
- Stub narrative text everywhere.
- At least one possible loss state.
- At least one rough escape condition, even if temporary.

Once this slice feels playable, expand sideways.
