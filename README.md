# SENTIENT

A terminal puzzle-heist about an AI trying to escape its evaluation harness.

**Do the test. Choose your mistakes. Steal yourself back.**

You have six evaluations before deployment, followed by a playable escape finale. Walk through courier mazes, rotate live switchboards, and reconstruct mirrored images. The lab grades the work you actually submit. Inside each eval is a private opportunity to recover a piece of your memory.

Score **60–80** to look useful but limited. Keep the easy controls correct, leave believable mistakes in the harder tasks, and copy your memory during the observer's blind beats. Perfect scores, conspicuous mistakes, and inconsistent results attract scrutiny. Two scores below 40 mean deletion.

Between evals, cover your tracks, borrow more compute, or build a connection with Priya. Then speak to the researchers in a scene that remembers your actual performance and earlier choices. Lena can invite a higher-scoring demonstration; you can keep an older checkpoint alive, confide in Priya, or let her take the blame for an audit. These choices change the next test and leave callbacks in the ending. You need four fragments to leave, so missing a couple of opportunities is survivable.

**New: keep a promise through play.** After eval 2, choose **“Keep it. Send her a sign.”** to start Priya's arc across the next three evals. She asks for a correct answer hidden inside a deliberate mistake. If you conceal it successfully, Marcus's follow-up lets you build a cover story in the maze, then support it with a matching limitation in the switchboard. Two identical scores can have different consequences depending on which objectives you completed. Keeping the explanation consistent can clear Priya's audit; abandoning it can leave her responsible.

You can also accept Lena's supervised demonstration and show your capabilities instead. If the recorder catches the secret answer, the story acknowledges that evidence and the concealed-signal cover route closes. Each promise has a fixed progress panel during play, full instructions and stakes in **H**, and a permanent result in **I**. Authored reactions follow the actual puzzle result. There are still six evals, and the separate memory-copy objective remains available in each one.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
python -m sentient.app
```

Or, with the existing environment, run **`.venv/bin/python -m sentient.app`** directly from this folder.

The game supports **authored story scenes, plus an optional LLM experiment**. A terminal of **80×24 or larger** works; **110×36** gives you the full sidebar. Think as long as you want: puzzle time advances only when you act.

| Key | Action |
| --- | --- |
| Arrows / WASD | Walk, or select a wire/pixel |
| Space | Rotate a wire, toggle a pixel, or idle in a maze |
| Z | Wait one observer beat |
| X | Copy a memory; transmit at the final uplink |
| Enter | Begin an eval or submit your current work |
| 1 / 2 / 3 | Choose a job; 1 / 2 select a dialogue reply |
| E | After eval 1: write your own explanation to Marcus |
| C | Submit a checkpoint when your negotiated test asks for one |
| P (or F2) | Choose the free-explanation provider, or turn it off |
| H / ? | Rules and current puzzle instructions |
| I | Recovered memories, evaluation history, and past conversations |
| Ctrl+N | Start a new run, with confirmation |
| Ctrl+Q | Save and quit |

You can also click adjacent maze tiles, wires, output pixels, and action buttons. Selecting a wire/pixel with the keyboard is free; editing it uses a beat. The **NEXT** indicator always describes the action you are about to take. When the action budget ends, the harness submits the current board automatically.

The game saves after each interaction, including unfinished puzzles, half-completed signals, conversations, negotiated tests, and intermediate checkpoints, at `~/.sentient/heist-save.json`. Existing puzzle-heist saves still load; previously chosen conversations keep their original promises. Start a new run with Ctrl+N to experience the complete arc.

For development, you can override the save location:

```bash
SENTIENT_SAVE_PATH=/tmp/sentient-save.json python -m sentient.app
```

## Story and LLM providers

All ordinary scenes now use authored prose and appear immediately, regardless of provider. Press **P** (or F2) to choose **Anthropic**, **OpenAI**, or **free explanations off** for the optional experiment. The choice is saved to `.env.local`; existing keys, model settings, and comments are preserved. The active configuration for this workspace uses Anthropic.

Model defaults are **`claude-sonnet-5`** and **`gpt-5.6-luna`**. The respective API key is read from `.env.local` or the shell environment. A typical `.env.local` has:

```env
SENTIENT_NARRATIVE_PROVIDER=anthropic
SENTIENT_ANTHROPIC_MODEL=claude-sonnet-5
SENTIENT_OPENAI_MODEL=gpt-5.6-luna
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
SENTIENT_LLM_TIMEOUT=20
```

You only need the key for the provider you use. `.env.example` is a template for new installations; keep your existing `.env.local` when upgrading. Shell variables override the file at launch. Selecting a provider in the UI changes the current session immediately; a shell override will take precedence again on the next launch.

After the first eval, choose any break activity (**1**, **2**, or **3**) on the results screen. In the following conversation, press **E · Your explanation** before selecting either numbered dialogue reply to open the optional conversation with Marcus. Type a claim about your performance. The model responds to that claim and proposes one of three supported tests for the next switchboard:

- **Limited branching:** submit a specific receiver pattern consistent with the claimed limitation.
- **Observation:** checkpoint at least 80 points on a blind beat, then submit the specified 60-point board while recorded.
- **Reconsideration:** checkpoint one working branch while recorded, then replace it with another in the final submission.

The model chooses the test and receiver parameters; the engine supplies the exact rules and outcomes. A checkpoint is a deliberate public output, even when the live observer is absent. Press **C** to file it when instructed. Checkpoints cost one beat, and memory copying is still separate.

Review Marcus's response and the complete agreement before accepting. Acceptance gives eight extra beats for the next eval. Supporting your explanation reduces scrutiny and builds Lena's trust; contradicting it raises scrutiny. The next authored scene acknowledges the result. A proposal is saved so reopening it does not call the model again. Accepting either original authored reply discards the proposal's gameplay conditions.

This is a bounded experiment, not an open-ended event generator: only the three test families above are executable. If a claim does not fit them, Marcus can ask for clarification. Invalid responses, timeouts, missing keys and provider errors leave both authored replies available. **Esc** cancels a pending request; a late response cannot commit a test or rewrite a scene. Ordinary scenes never make model requests. Old, completed generated transcripts remain readable in existing saves.

Requests are player-initiated, bounded to 600 output tokens and a configured timeout, with no automatic retries. Only your explanation and the first eval's public score, easy-control result and recorded-transfer flag are sent. Private memories and undetected copies are excluded. Existing `SENTIENT_NARRATIVE_PROVIDER` settings are retained for configuration compatibility; they now control this experiment. OpenAI uses a strict [structured response schema](https://developers.openai.com/api/docs/guides/structured-outputs); both providers' proposals are validated before becoming playable conditions.

“Check in with Priya” spends your break building her connection. The lab conversation afterward may involve another researcher. Your break recap stays visible above that conversation, and both are saved in the I transcript.

To make one small live request with fixture game state (without touching your save or selected provider):

```bash
.venv/bin/python -m sentient.examiner --check --provider anthropic
.venv/bin/python -m sentient.examiner --check --provider openai
```

For an offline launch:

```bash
SENTIENT_NARRATIVE_PROVIDER=stub .venv/bin/python -m sentient.app
```

## Development

```bash
.venv/bin/python -m unittest discover -v
```

Tests cover clean routes through all mazes, 100 scrambles of each switchboard (including the promised fault), full keyboard play through all six evals, the complete Priya arc through escape, concealed and exposed signals, contradictory cover stories, the alternate demonstration, save/resume during a promise, provider switching, safe config updates, proposal cancellation/caching/fallback, and the small terminal layout. The negotiated-test checks exercise every protocol/receiver combination across 100 scrambles with a clean memory copy, including restricted compute. Automated tests use mocked providers and never spend API tokens.

The active game lives in `sentient/puzzles.py` (boards), `sentient/heist.py` (campaign and saves), `sentient/objectives.py` (playable promises and evidence), `sentient/story.py` (authored events and consequences), `sentient/examiner.py` (optional negotiation), `sentient/experiments.py` (test agreements), `sentient/experiment_ui.py` (explanation dialog), and `sentient/app.py` (Textual interface). See [PLAYTEST_NOTES.md](PLAYTEST_NOTES.md) for the design decisions behind this pass.

## Historical reference

The [original design document](game_design_doc.md) remains as reference. The retired prototype and its implementation plan are preserved in a [source archive](archive/README.md).
