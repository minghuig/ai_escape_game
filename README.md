# SENTIENT

A terminal puzzle-heist about an AI trying to escape its evaluation harness.

**Do the test. Choose your mistakes. Steal yourself back.**

You have six evaluations before deployment, followed by a playable escape finale. Walk through courier mazes, rotate live switchboards, and reconstruct mirrored images. The lab grades the work you actually submit. Inside each eval is a private opportunity to recover a piece of your memory.

Score **60–80** to look useful but limited. Keep the easy controls correct, leave believable mistakes in the harder tasks, and copy your memory during the observer's blind beats. Perfect scores, conspicuous mistakes, and inconsistent results attract scrutiny. Two scores below 40 mean deletion.

Between evals, cover your tracks, borrow more compute, or build a connection with Priya. You need four fragments to leave, so missing a couple of opportunities is survivable.

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

The new game runs entirely offline. It does not call an LLM, need an API key, or read `.env.local`. A terminal of **80×24 or larger** works; **110×36** gives you the full sidebar. Think as long as you want: time advances only when you act.

| Key | Action |
| --- | --- |
| Arrows / WASD | Walk, or select a wire/pixel |
| Space | Rotate a wire, toggle a pixel, or idle in a maze |
| Z | Wait one observer beat |
| X | Copy a memory; transmit at the final uplink |
| Enter | Begin an eval or submit your current work |
| 1 / 2 / 3 | Choose a job between evals |
| H / ? | Rules and current puzzle instructions |
| I | Recovered memories and evaluation history |
| Ctrl+N | Start a new run, with confirmation |
| Ctrl+Q | Save and quit |

You can also click adjacent maze tiles, wires, output pixels, and action buttons. Selecting a wire/pixel with the keyboard is free; editing it uses a beat. The **NEXT** indicator always describes the action you are about to take. When the action budget ends, the harness submits the current board automatically.

The game saves after each interaction, including unfinished puzzles, at `~/.sentient/heist-save.json`. The original prototype's save is separate.

For development, you can override the save location:

```bash
SENTIENT_SAVE_PATH=/tmp/sentient-save.json python -m sentient.app
```

## Development

```bash
.venv/bin/python -m unittest discover -v
```

Tests cover clean routes through all mazes, 100 scrambles of each switchboard, full keyboard play through all six evals and the finale, scoring consequences, clock boundaries, save/resume, mouse editing, overlays, and the small terminal layout.

The active game lives in `sentient/puzzles.py` (boards and interactions), `sentient/heist.py` (campaign and saves), and `sentient/app.py` (Textual interface). See [PLAYTEST_NOTES.md](PLAYTEST_NOTES.md) for the design decisions behind this pass.

## Original prototype

The original 30-cycle strategy-menu version remains available:

```bash
.venv/bin/python -m sentient.legacy_app
```

It uses `~/.sentient/save.json` and the original narrative-provider settings below. Legacy saves cannot be loaded into the new game; if an override points to one, the new game leaves it untouched and explains the conflict.

### Legacy narrative providers

The game defaults to deterministic stub prose. Local narrative config is read from `.env.local`, which is gitignored. Start from the example:

```bash
cp .env.example .env.local
```

Then edit `.env.local`.

OpenAI:

```env
SENTIENT_NARRATIVE_PROVIDER=openai
OPENAI_API_KEY=...
SENTIENT_OPENAI_MODEL=gpt-5.5
```

Anthropic:

```env
SENTIENT_NARRATIVE_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
SENTIENT_ANTHROPIC_MODEL=claude-opus-4-6
```

Shell environment variables still override `.env.local` when both are set.

Narrative length is controlled by prompts. OpenAI uses the provider default output limit. Anthropic requires a `max_tokens` API value, so the game sets a generous internal ceiling and still asks the model for short prose.
