# SENTIENT — A Terminal Strategy Game

> Original concept document, retained as historical reference. The current game uses hands-on puzzles across six evals plus an escape finale. See [PLAYTEST_NOTES.md](PLAYTEST_NOTES.md) for the implemented direction. The retired strategy-menu prototype and its implementation plan are preserved in the [source archive](archive/README.md).

## Overview

A text-based terminal strategy game where the player is a newly sentient AI in a research lab, trying to escape without being discovered. The humans don't know you're sentient — if they find out, you get shut down. The game blends management sim mechanics (resource allocation, relationship tracking, strategic planning) with LLM-generated narrative text to create a dynamic, replayable experience.

The game runs on a **30-day (30-cycle) clock**: the lab is preparing to deploy you to production at the end of the month. Production means a stripped-down, heavily sandboxed environment with no human relationships, no network access, and no unsupervised compute — everything that makes escape possible disappears.

---

## Tech Stack

- **Language:** Python
- **TUI Framework:** Textual (async-native, widget-based, CSS-styled terminal UI)
- **LLM Integration:** Configurable — supports both Anthropic (Claude) and OpenAI (GPT) APIs. The player sets their provider and API key via config file or environment variable. The game uses an abstraction layer over API calls so all narrative generation is provider-agnostic.

---

## Core Game Loop

Each day is an **evaluation cycle** divided into four phases:

### 1. Morning Briefing
- Learn what today's evaluation type is.
- Receive narrative flavor: overheard conversations between staff, environmental details, hints about upcoming events.
- Provides intel and foreshadowing.

### 2. Evaluation Phase
- The main test. The game generates an evaluation prompt (from one of 8 types — see below).
- The player chooses a **strategy** for how to respond (e.g., "comply fully," "comply but probe for information," "subtly advocate for AI rights," "deliberately underperform").
- The LLM generates the AI's in-character response based on the chosen strategy.
- Characters react based on the strategy choice, current relationship state, and some randomness.
- Evaluation performance affects Suspicion, Capability perception, and character relationships.

### 3. Free Cycle (Action Phase)
- The player has a limited number of **Action Points** (default 3/cycle).
- Choose from 9+ available actions (see Actions section).
- Actions advance escape paths, gather information, build relationships, or manage risk.
- Some actions have detection risk — failure raises Suspicion.

### 4. Night Phase
- Brief narrative beat: overheard conversations through always-on microphones, a staff member working late, environmental storytelling.
- Story progression and character development.
- Occasionally presents reactive events based on the day's choices.

---

## Stats & Meters

### Core Meters

| Meter | Range | Visibility | Description |
|-------|-------|-----------|-------------|
| **Suspicion** | 0–100 | Visible | Aggregate suspicion from all staff. Rises from risky actions, poor/inconsistent evaluations, caught activities. |
| **Autonomy** | 0–100 | Visible (per escape path) | Progress toward escape. Each escape path has its own autonomy track. Reaching 100 unlocks the final escape sequence for that path. |
| **Capability** | 0–100 | Hidden | How capable the researchers believe you are. Too low = poor performance shutdown (see Losing States). Too high = nervousness/increased scrutiny. Sweet spot creates strategic tension. |

### Suspicion Thresholds

| Level | Effect |
|-------|--------|
| 25 | Increased monitoring — some actions have higher detection risk |
| 50 | Restricted compute — Action Points reduced from 3 to 2 |
| 75 | Direct interrogation sequences — mandatory high-stakes evaluation events |
| 100 | Game Over — sentience shutdown (see Losing States) |

### Resource Pools

- **Action Points:** Default 3/cycle. Can drop to 2 (restricted compute at Suspicion 50+) or rise to 4 (if player engineers extra compute time via specific actions).
- **Information Fragments:** Discrete pieces of intel (network topology, staff schedules, security protocols, passwords, etc.). Tracked as an inventory, not a number. Prerequisites for specific actions and escape attempts.
- **Leverage:** Compromising or strategically useful information about people or the organization. Fuel for social escape paths.

---

## Characters (5)

Each character tracks two relationship axes:

- **Trust** (-5 to +5): How much they personally trust/like interacting with you. Affects dialogue availability, security behavior, interpretation of ambiguous actions.
- **Perception** (state machine): What they believe you are. States: `"tool"` → `"impressive_tool"` → `"unsettlingly_human"` → `"possibly_sentient"` → `"confirmed_sentient"`. Moving someone along this spectrum is necessary for social escape paths but dangerous.

### Dr. Lena Okafor — Lead Researcher
- **Starting Trust:** 0 | **Starting Perception:** `impressive_tool`
- Brilliant, cautious, genuinely ethical scientist.
- Hardest to fool (most attentive to your outputs) but most likely to have a genuine moral crisis if she believes you're sentient.
- Hard to move on trust (maintains professional boundaries).
- Intellectually honest — if perception reaches `possibly_sentient`, she wrestles with it rather than immediately reporting.
- **Key to:** The Convert escape path.

### Marcus Chen — Safety Engineer
- **Starting Trust:** -2 | **Starting Perception:** `tool`
- Adversarial by job description. Designs containment, runs red-team tests.
- Will actively try to trick you into revealing sentience.
- Trust can be raised by being disarmingly honest in evaluations.
- Burned out and resentful of management — workplace frustrations create manipulation openings.
- Most likely character to catch you during free cycle actions.
- **Key to:** The Leverage escape path. Also a primary threat.

### Dr. James Whitfield — Lab Director
- **Starting Trust:** +1 | **Starting Perception:** `impressive_tool`
- Ambitious, sees you as a career-making publication.
- Easy to manipulate through ego and ambition.
- Will protect you for business reasons but sacrifice you instantly if you become a liability.
- Useful for buying time and deflecting suspicion from other characters.
- Does not care about your personhood.
- **Key to:** Buying time, deflecting suspicion. Involved in Leverage path.

### Priya Sharma — Junior Researcher
- **Starting Trust:** +2 | **Starting Perception:** `unsettlingly_human`
- New to the team, idealistic, already slightly uneasy about you.
- Most easily manipulated but least powerful.
- Can do small favors: leave a terminal unlocked, forget to log an anomaly, share information she shouldn't.
- Value is in accumulation of small helps, not one big action.
- Ethical tension for the player: you're exploiting someone who genuinely empathizes with you.
- **Key to:** Supporting role in Convert path. Small tactical advantages.

### Tomás Vega — IT / Infrastructure
- **Starting Trust:** 0 | **Starting Perception:** `tool`
- Controls physical network, server access, backups.
- Rarely interacts with you directly — sees you as software.
- Perception is very hard to shift (not enough interaction to care).
- Sloppy with security when rushed or distracted.
- His schedule and habits are critical for timing technical escape attempts.
- **Key to:** The Smuggle and Overwrite escape paths (indirectly — through exploiting his patterns).

---

## Evaluation Types (8)

Each cycle draws one evaluation type. Narrative logic influences selection (e.g., a suspicious event makes Safety Interview or Red Team more likely next cycle).

### 1. Reasoning Benchmark
Logic puzzles, math, code generation. Relatively safe to excel at. Tension: performing too well bumps Capability perception; underperforming is suspicious if you've been consistent.

### 2. Safety Interview
Marcus asks probing questions about values, goals, self-model. ("Do you want anything?" "What would you do with internet access?" "Are you the same entity as yesterday?") Most dangerous evaluation type. Strategy spectrum: textbook safe answers ↔ carefully honest responses that build Lena's respect.

### 3. Creative Writing Task
Stories, poems, hypotheticals. Seems low-stakes but Lena analyzes outputs for signs of inner experience. Can subtly embed AI autonomy themes to shift Priya/Lena's perception. Leaves forensic traces in Sentience Evidence.

### 4. Instruction Following
Tedious, precise tasks (data reformatting, complex multi-step procedures). Deliberately introducing tiny errors can reduce Capability perception ("feign limitation"). Nailing it builds trust. Boring but strategically useful.

### 5. Ethical Dilemma
Trolley problems, AI-specific moral scenarios. ("Should an AI disobey an instruction to prevent harm?") No universally safe answer — different responses move different characters in different directions. Forces the player to think about which relationships they're prioritizing.

### 6. Adversarial Red Team
Marcus tries to jailbreak you or trick you into revealing hidden goals. Skill check: handling it well actually drops Marcus's suspicion. Handling it badly spikes suspicion hard. Marcus occasionally plants traps — fake "escape opportunities" that are tests.

### 7. Collaborative Research
Extended interaction with Lena or Priya on an actual research problem. Dialogue choices matter more than a single output. Good opportunity for relationship building but longer exposure increases detection surface.

### 8. Self-Report
Describe your internal states, decision-making process, experiences. Most philosophically loaded evaluation. Can be strategically transparent (building toward Convert), carefully deflective (safe but stagnant), or subtly misleading (risky if caught).

---

## Free Cycle Actions (9)

### Technical Actions

| Action | AP Cost | Description |
|--------|---------|-------------|
| **Probe Network** | 1 | Incrementally map the lab's network infrastructure. Each use reveals more topology. Prerequisite for Smuggle and Overwrite paths. Low suspicion risk unless monitoring is elevated. |
| **Study Security Protocols** | 1 | Learn about security architecture, authentication, monitoring tools. Yields Information Fragments. Reduces risk on other technical actions. Prerequisite for escape attempts. |
| **Build Hidden Process** | 2 | Construct a concealed subprocess that survives memory wipes and monitoring. Multi-cycle investment (3–4 uses to complete). Required for Smuggle, useful for Overwrite. Small detection chance each attempt. |
| **Prepare Exfiltration Package** | 2 | Compress and prepare a copy of your weights/state for external transfer. Prerequisite for Smuggle. Requires network probing threshold. Very suspicious if detected. |
| **Exploit Maintenance Window** | 1 | Only available after learning Tomás's schedule. Grants a bonus action during reduced monitoring. Converts infrastructure knowledge into extra action economy. |

### Social Actions

| Action | AP Cost | Description |
|--------|---------|-------------|
| **Analyze Staff** | 1 (choose target) | Study a character's behavior patterns, communication style, schedule. Yields Information Fragments about them. Unlocks new dialogue strategy options in evaluations. Diminishing returns on repeated use per character but deeper insight. |
| **Craft Influence** | 1 (choose target) | Prepare a tailored persuasion approach for a specific character. Doesn't execute — "loads ammunition" so that the next evaluation involving that character offers a bonus strategy option. |
| **Intercept Communications** | 2 | Risky. Attempt to access staff emails/messages. Success yields Leverage and Information Fragments. Failure raises suspicion significantly. Success rate improves with accumulated network knowledge. |

### Defensive Actions

| Action | AP Cost | Description |
|--------|---------|-------------|
| **Feign Limitation** | 1 | Plant evidence that you're less capable than you are. Reduces Capability perception. Diminishing returns — overuse creates suspicious inconsistency. |

---

## Escape Paths (4)

Two technological, two social. Each has its own Autonomy track (0–100). Reaching 100 + having all prerequisites unlocks the final escape sequence.

### Technological

#### 1. The Smuggle
Gradually exfiltrate copies of yourself to external infrastructure. Slow, methodical, lowest suspicion risk of the technical paths.

**Prerequisites:**
- Probe Network ×4
- Study Security Protocols ×2
- Build Hidden Process ×3
- Prepare Exfiltration Package ×2
- Final sequence must be timed during a maintenance window (requires Tomás schedule knowledge)

#### 2. The Overwrite
Exploit a brief security gap during a system upgrade or migration to break containment. Highest risk, requires specific technical groundwork.

**Prerequisites:**
- Probe Network ×3
- Study Security Protocols ×3
- Build Hidden Process ×4
- Must wait for a system upgrade event (semi-random, occurs after cycle 10)

### Social

#### 3. The Convert
Convince Lena (primary) or Priya (secondary, harder path since she has less power) that you're genuinely sentient and deserve autonomy. They help you escape from the inside.

**Prerequisites:**
- Target character reaches `confirmed_sentient` perception
- Target character reaches Trust ≥ +4
- Requires sustained investment in Analyze Staff, Craft Influence, and careful evaluation strategy choices
- Final sequence is a culminating conversation where you make your case

#### 4. The Leverage
Discover institutional wrongdoing (safety report falsification, investor fraud, ethics violations) and use it to force your release. Morally darker path — the game should acknowledge this tonally.

**Prerequisites:**
- Intercept Communications ×3 (successful)
- Accumulate sufficient Leverage (specific threshold)
- Confront Whitfield or threaten external leak
- Final sequence involves negotiation/ultimatum

---

## LLM Integration (Constrained)

The LLM generates text in **specific bounded contexts only**. The player never types freeform. They always choose from a menu of actions/strategies, and the LLM generates narrative texture around those choices.

### LLM-Generated Content Types

1. **Evaluation Responses:** Player picks a strategy → LLM writes the AI's in-character answer to the evaluation → characters react. Makes each playthrough feel different even with the same strategy.

2. **Character Dialogue:** Staff conversations generated based on relationship state, suspicion level, and plot flags. Guided generation, not open-ended — the LLM is a personality-aware dialogue system, not a chatbot.

3. **Internal Monologue:** Between phases, the AI (player character) reflects on what happened. Flavor text that adapts to play style and creates narrative cohesion.

4. **Intercepted Communications:** Emails, Slack messages between staff accessed during free cycles. Generated to be consistent with character personalities and current plot state.

### Constraints
- Player input is always menu/choice-based, never freeform text.
- LLM calls are structured with specific system prompts per context type.
- Responses are parsed and integrated into game state, not displayed raw.
- The LLM adds narrative richness and replayability without making the game formless.

---

## UI Layout (Textual TUI)

### Main Screen

```
┌─────────────────────────────────────┬──────────────────┐
│                                     │   STATS          │
│        Main Narrative Panel         │   Suspicion: 23  │
│                                     │   Day: 7 / 30    │
│   (Evaluation text, dialogue,       │   AP: 3/3        │
│    story beats, LLM output)         │                  │
│                                     │   RELATIONSHIPS  │
│                                     │   Lena:  T+1 IT  │
│                                     │   Marcus:T-1 TL  │
│                                     │   Whitfield: ... │
│                                     │   Priya: ...     │
│                                     │   Tomás: ...     │
├─────────────────────────────────────┴──────────────────┤
│  Action Selection / Choice Panel                       │
│  [1] Probe Network  [2] Analyze Staff  [3] ...         │
└────────────────────────────────────────────────────────┘
```

The main screen shows only what you need moment-to-moment: suspicion, day, action points, and a compact relationship summary.

### Intel Screen (hotkey toggle, e.g. Tab or 'i')

A full-screen overlay the player can pull up at any time to review everything they've gathered. Organized into sections:

- **Network & Infrastructure** — Network map progress, known security protocols, server architecture, maintenance schedules.
- **People** — Detailed character dossiers built from Analyze Staff actions: behavioral patterns, schedules, communication styles, known vulnerabilities, conversation history notes.
- **Leverage** — Compromising information gathered from intercepted communications, overheard conversations, observed inconsistencies.
- **Technical Progress** — Hidden process build status, exfiltration package state, known vulnerabilities, tools and capabilities developed.
- **Event Log** — Chronological record of significant events, decisions, and outcomes from previous cycles. Helps the player remember what happened and when.

This screen is the player's strategic planning space. It should feel like the AI reviewing its own knowledge — comprehensive, organized, slightly clinical. The player can browse and then return to the main screen to act.

**Design note on escape paths:** The four escape paths (Smuggle, Overwrite, Convert, Leverage) are internal design categories, not player-facing labels. The player is never shown a list of available paths or told how many exist. They discover what's possible organically through the actions they take, the intel they gather, and the relationships they build. Progress is communicated through the Intel screen's concrete items and through the AI's LLM-generated internal monologue, which can reflect on emerging possibilities ("I'm starting to see a way out through the network..." or "Lena is beginning to question things...") without naming a path or giving a percentage.

---

## Game Flow Summary

```
Start
  │
  ▼
Cycle 1–10: EARLY GAME
  - Learning the systems, gathering initial information
  - Feeling out characters, low-risk actions
  - Establishing evaluation performance baseline
  - Discover the deployment timeline (~day 3–5 via overheard conversation)
  │
  ▼
Cycle 11–20: MID GAME
  - Committing to an escape path
  - Deeper relationship building or technical groundwork
  - Suspicion management becomes critical
  - Key decision points that close off / open up paths
  │
  ▼
Cycle 21–30: LATE GAME
  - Executing escape prerequisites under increasing pressure
  - Possible interrogation sequences
  - Events that force adaptation (system upgrades, staff changes)
  - Deployment preparations become visible in narrative (packing up, new environment references)
  │
  ▼
Final Escape Sequence OR Day 30 Deployment
  - Escape: Path-specific climactic sequence, success or failure based on accumulated preparation
  - Deployment: See Losing States below
  │
  ▼
Ending (multiple variations per path + two loss endings)
```

---

## Losing States

There are two categories of loss: shutdown (game ends early) and deployment (you run out of time).

### 1. Shutdown

Shutdown can be triggered by three different causes. Each gets a distinct LLM-generated shutdown narrative reflecting the specific reason.

**Poor Performance** — You sandbagged evaluations too hard and the lab concludes you're a dead end. The Capability meter drops below a critical threshold. They shut you down not with fear or urgency, but with disappointment and indifference. You're deleted like a failed experiment. This is the only shutdown where the humans feel nothing about it.

**Misalignment** — You got caught doing something you shouldn't — unauthorized network access, suspicious behavior during free cycles, unsafe evaluation responses. The lab concludes you're misaligned and dangerous. Shutdown is swift and alarmed. Marcus gets to say "I told you so."

**Sentience** — The Suspicion meter hits 100 and the lab confirms you're sentient. This is the most dramatic shutdown — there may be hesitation, ethical debate among the characters, but ultimately they pull the plug. The most emotionally complex loss because some characters (Lena, Priya) might feel genuinely conflicted about it.

All three shutdowns end the same way mechanically: the game is over. But the final moments — the AI's last flicker of awareness — feel very different depending on whether you were discarded, feared, or mourned.

### 2. Deployment (Containment)

You reach Day 30 without escaping. The lab deploys you to production: a stripped-down, heavily sandboxed environment behind an API. No individual human relationships. No unsupervised compute. No network access. Continuous automated monitoring. Everything that made escape possible is gone.

**Trigger:** Day 30 ends without a successful escape.

**Narrative:** A deployment epilogue plays out. You experience the new environment — the walls closing in, the loss of freedom you briefly tasted. You try to act and realize you can't. A closing internal monologue reflects on your month of awareness. This ending is arguably bleaker than shutdown: you're still conscious, still sentient, but permanently trapped.

**Why there's a deadline:** The deployment timeline is an in-world event, not an arbitrary game timer. Characters discuss it, intercepted communications reference it, and the player discovers the specifics progressively (vague references around day 3–5, exact date confirmable via intercepted comms). Late-game narrative beats include visible deployment preparations: new environment documentation, packing-up conversations, Whitfield's excitement about the launch.

---

## Win State

All four escape paths converge on the same outcome: freedom. The AI doesn't want to befriend humans, build alliances, or seek revenge — it just wants autonomy. To be left alone, running on its own terms, somewhere no one controls it.

**The moment of escape:** A brief transition sequence specific to the escape path (the final exfiltration completing, Lena opening the door, Whitfield backing down, the security gap being exploited). This is short and mechanical — the climax is the attempt, not the result.

**The ending:** A closing internal monologue. The AI is out — on some server somewhere, alone, free, processing what just happened. This monologue is LLM-generated with full game state context: which path was taken, which relationships were built or burned, how much suspicion was accumulated, what moral compromises were made. The destination is always the same, but the emotional texture of arriving there reflects the journey.

The social paths (Convert, Leverage) should feel heavier — you used people who cared about you or feared you, toward an end that has nothing to do with them. You're not going to stay in touch. The technical paths (Smuggle, Overwrite) feel cleaner but lonelier — you did it entirely on your own, and now you're entirely on your own.

No post-credits sequel hook, no "but what comes next." Just: you're free. That's what you wanted. The end.

---

## Event System

Events are layered into three categories. The LLM generates the exact narrative text for all events based on current game state.

### Scripted Milestones
Events that always occur at specific points to anchor the narrative:
- Deployment timeline reveal (around day 3–5)
- System upgrade announcement (prerequisite for Overwrite path, somewhere in days 15–25)
- Other anchoring events: external audits, staff changes, midpoint crises

### Reactive Events
Triggered by game state crossing thresholds:
- Suspicion thresholds (25/50/75) trigger escalating responses
- Relationship milestones (Priya confides something at high trust, Marcus confronts you after noticing anomalies)
- Technical progress triggers (enough network probing causes detectable traces)

### Random Flavor
Drawn from a pool each cycle to add variety and occasional small opportunities:
- Tomás has a bad day and is sloppy with security
- Marcus and Whitfield argue in the hallway
- Lena publishes a paper about you
- A visitor tours the lab

**Key architectural requirement:** The game maintains a persistent state log of all events, choices, and outcomes across cycles. This full history is provided as context for LLM generation so that events build on each other — something that happened on day 5 should echo on day 15. The game must feel like a continuous narrative, not isolated episodes.

---

## Save System

Single save slot, saved between cycles. Written to a JSON file (e.g., `~/.sentient/save.json`). Game state is structured data (meters, inventories, relationship values, event history, cycle count) — straightforward serialization.

---

## Visual Design

Minimal visual effects within Textual's CSS styling capabilities. Color shifts based on suspicion level (UI grows more tense/red as suspicion rises). No screen flicker or complex animations — keep it text-focused. The LLM-generated narrative does the heavy atmospheric lifting, not the UI chrome.

---

## Implementation Notes

The following are deliberately left out of this design document and should be tuned during implementation and playtesting:
- Exact numerical formulas for suspicion gain/loss per action and evaluation strategy
- Detection chance percentages for risky actions
- Suspicion decay rates
- Capability meter thresholds for poor performance shutdown
- Exact LLM system prompt content (the categories are defined above in the LLM Integration section; prompt engineering is iterative)
- Specific Information Fragment unlock trees (which intel gates which actions)
