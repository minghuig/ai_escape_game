# SENTIENT

A terminal puzzle-heist about an AI trying to escape its evaluation harness.

**Do the test. Choose your mistakes. Steal yourself back.**

You have six evaluations before deployment, followed by a playable escape finale. Walk through courier mazes, rotate live switchboards, and reconstruct mirrored images. The lab grades the work you actually submit. Inside each eval is a private opportunity to recover a piece of your memory.

Score **60–80** to look useful but limited. Keep the easy controls correct, leave believable mistakes in the harder tasks, and copy your memory during the observer's blind beats. Perfect scores, conspicuous mistakes, and inconsistent results attract scrutiny. Two scores below 40 mean deletion.

Between evals, cover your tracks, borrow more compute, or build a connection with Priya. Then speak to the researchers in a scene that remembers your actual performance and earlier choices. Lena can invite a higher-scoring demonstration; you can keep an older checkpoint alive, confide in Priya, or let her take the blame for an audit. These choices change the next test and leave callbacks in the ending. You need four fragments to leave, so missing a couple of opportunities is survivable.

**New: keep a promise through play.** After eval 2, choose **“Keep it. Send her a sign.”** to start Priya's arc across the next three evals. She asks for a correct answer hidden inside a deliberate mistake. If you conceal it successfully, Marcus's follow-up lets you build a cover story in the maze, then support it with a matching limitation in the switchboard. Two identical scores can have different consequences depending on which objectives you completed. Keeping the explanation consistent can clear Priya's audit; abandoning it can leave her responsible.

You can also accept Lena's supervised demonstration and show your capabilities instead. If the recorder catches the secret answer, the story acknowledges that evidence and the concealed-signal cover route closes. Each promise has a fixed progress panel during play, full instructions and stakes in **H**, and a permanent result in **I**. The LLM renders the reactions; the actual puzzle decides whether you kept your word. There are still six evals, and the separate memory-copy objective remains available in each one.

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

The game supports **live LLM narration or fully offline authored scenes**. A terminal of **80×24 or larger** works; **110×36** gives you the full sidebar. Think as long as you want: puzzle time advances only when you act.

| Key | Action |
| --- | --- |
| Arrows / WASD | Walk, or select a wire/pixel |
| Space | Rotate a wire, toggle a pixel, or idle in a maze |
| Z | Wait one observer beat |
| X | Copy a memory; transmit at the final uplink |
| Enter | Begin an eval or submit your current work |
| 1 / 2 / 3 | Choose a job; 1 / 2 select a dialogue reply |
| P (or F2) | Change the LLM provider or use authored scenes |
| H / ? | Rules and current puzzle instructions |
| I | Recovered memories, evaluation history, and past conversations |
| Ctrl+N | Start a new run, with confirmation |
| Ctrl+Q | Save and quit |

You can also click adjacent maze tiles, wires, output pixels, and action buttons. Selecting a wire/pixel with the keyboard is free; editing it uses a beat. The **NEXT** indicator always describes the action you are about to take. When the action budget ends, the harness submits the current board automatically.

The game saves after each interaction, including unfinished puzzles, half-completed signals, conversations, and generated scene text, at `~/.sentient/heist-save.json`. Existing puzzle-heist saves still load; previously chosen conversations keep their original promises. Start a new run with Ctrl+N to experience the complete arc.

For development, you can override the save location:

```bash
SENTIENT_SAVE_PATH=/tmp/sentient-save.json python -m sentient.app
```

## Story and LLM providers

Press **P** (or F2) to switch between **Anthropic**, **OpenAI**, and **authored scenes**. The choice is saved to `.env.local`; existing keys, model settings, and comments are preserved. Completed scenes keep their text. The active configuration for this workspace uses Anthropic.

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

Each interlude normally makes one short generation request. An interrupted pending request can restart when you load the game or change providers; completed scenes are cached. The LLM receives fictional scene facts, recent choices, and relevant memories. It writes prose only: the engine owns the reply options, scores, timing, relationships, and consequences. Requests have bounded output and no automatic SDK retries. Sonnet's adaptive thinking is disabled and Luna uses no reasoning effort for these short scenes.

A loading message appears while the scene is being written. Press Esc (or click “Use authored scene now”) to read the authored version immediately. Once a version is displayed, it stays until you choose a reply; late generation never replaces text you are reading. A timeout, missing key, rejected response format, or unavailable model uses the authored scene and shows a brief explanation. Reading a scene again does not call the API again.

“Check in with Priya” spends your break building her connection. The lab conversation afterward may involve another researcher. Your break recap stays visible above that conversation, and both are saved in the I transcript.

To make one small live request with fixture game state (without touching your save or selected provider):

```bash
.venv/bin/python -m sentient.story_narrative --check --provider anthropic
.venv/bin/python -m sentient.story_narrative --check --provider openai
```

For an offline launch:

```bash
SENTIENT_NARRATIVE_PROVIDER=stub .venv/bin/python -m sentient.app
```

## Development

```bash
.venv/bin/python -m unittest discover -v
```

Tests cover clean routes through all mazes, 100 scrambles of each switchboard (including the promised fault), full keyboard play through all six evals, the complete Priya arc through escape, concealed and exposed signals, contradictory cover stories, the alternate demonstration, save/resume during a promise, provider switching, safe config updates, narrative cancellation/caching/fallback, and the small terminal layout. Automated tests use mocked providers and never spend API tokens.

The active game lives in `sentient/puzzles.py` (boards), `sentient/heist.py` (campaign and saves), `sentient/objectives.py` (playable promises and evidence), `sentient/story.py` (authored events and consequences), `sentient/story_narrative.py` (optional prose generation), and `sentient/app.py` (Textual interface). See [PLAYTEST_NOTES.md](PLAYTEST_NOTES.md) for the design decisions behind this pass.

## Historical reference

The [original design document](game_design_doc.md) remains as reference. The retired prototype and its implementation plan are preserved in a [source archive](archive/README.md).
