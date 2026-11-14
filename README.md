# local-coder

A skill for [Claude Code](https://claude.com/claude-code) that splits coding
work between two models to save tokens:

- **Claude** (the large cloud model) plans the work and reviews the result.
- **A local model** running in [Ollama](https://ollama.com) on your own PC
  writes the code, at no token cost.

> The skill instructions (`SKILL.md`) and the messages of `local_gen.py` are
> written in German. Claude follows them in any language; this README and
> `check_setup.py` are in English.

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Step 1: Install Ollama](#step-1-install-ollama)
- [Step 2: Install the skill](#step-2-install-the-skill)
- [Step 3: Pick the model for your PC](#step-3-pick-the-model-for-your-pc)
- [Step 4: Use it](#step-4-use-it)
- [Settings](#settings)
- [Using the script without Claude](#using-the-script-without-claude)
- [Troubleshooting](#troubleshooting)
- [What to expect](#what-to-expect)
- [License](#license)

## How it works

1. **Classify.** Claude sorts every step of the task:

   | Kind of step | Examples | Who writes it |
   |---|---|---|
   | Tiny | a change under about 15 lines, a rename, one import | Claude |
   | Routine | a new file that follows a clear pattern, tests for existing code, CRUD, data classes, parsers for a fixed format, conversions, docstrings | local model |
   | Hard | concurrency, security, auth, money, migrations, tricky algorithms, changes across many files, debugging | Claude |

2. **Plan.** Claude cuts the routine work into steps of exactly one file each
   (about 150 lines at most) and writes a precise specification per step:
   purpose, exact signatures, behaviour, edge cases, an example.
3. **Write locally.** `scripts/local_gen.py` sends the specification and any
   reference files to Ollama and writes the result to disk. Claude only sees a
   one-line status, so the generated code does not fill its context unasked.
4. **Review.** Claude runs syntax checks, linters and tests, then reads every
   locally written file. Small mistakes it fixes itself. If a file is wrong at
   its core, it sharpens the specification and regenerates once. After a
   second failure Claude writes that step itself.

## Requirements

- Claude Code
- Ollama
- Python 3.10 or newer (standard library only, nothing to `pip install`)
- A GPU with 6 GB of VRAM or more is strongly recommended. It runs on a CPU,
  but slowly.

## Step 1: Install Ollama

| System | How |
|---|---|
| Linux | `curl -fsSL https://ollama.com/install.sh \| sh` |
| macOS | Download the app from <https://ollama.com/download> or run `brew install ollama` |
| Windows | Download the installer from <https://ollama.com/download> |

The Linux installer sets Ollama up as a system service that starts on boot.
Check that it runs:

```
ollama --version
curl http://127.0.0.1:11434/api/version
```

If the second command fails, start the server by hand with `ollama serve`.

## Step 2: Install the skill

Clone the repository into your personal Claude Code skills folder:

```
git clone https://github.com/Petar-Jorgic/local-coder ~/.claude/skills/local-coder
```

On Windows the folder is `%USERPROFILE%\.claude\skills\local-coder`.

Start a new Claude Code session afterwards so the skill is picked up.

## Step 3: Pick the model for your PC

The fastest way is to let the included script look at your machine. It reads
your RAM and GPU, checks that Ollama is reachable, and prints the model that
fits. It only reads; it installs and changes nothing.

```
python ~/.claude/skills/local-coder/scripts/check_setup.py
```

Example output:

```
== Hardware ==
OS:   Linux x86_64
RAM:  31 GB
GPU:  AMD GPU (card1), 8 GB VRAM

== Ollama ==
Binary: /usr/local/bin/ollama
Server: running at 127.0.0.1:11434, 4 model(s) installed

== Recommendation ==
Model:  qwen2.5-coder:7b (download 4.7 GB)
Get it: ollama pull qwen2.5-coder:7b
```

The recommendation follows this table. What counts is the memory of your
graphics card (VRAM), because a model that does not fit into it spills over to
the CPU and gets much slower.

| Your hardware | Model | Download | Notes |
|---|---|---|---|
| No GPU, less than 16 GB RAM | `qwen2.5-coder:1.5b` | 1 GB | Runs anywhere; only good for very simple files |
| No GPU with 16 GB RAM or more, or a GPU with 3–5 GB VRAM | `qwen2.5-coder:3b` | 1.9 GB | Usable for docstrings and simple tests |
| GPU with 6–8 GB VRAM | `qwen2.5-coder:7b` | 4.7 GB | **Default.** The setup this skill was tested on |
| GPU with 10–16 GB VRAM | `qwen2.5-coder:14b` | 9 GB | Noticeably fewer mistakes |
| GPU with 20 GB VRAM or more | `qwen2.5-coder:32b` | 20 GB | Best quality in this family |
| Apple Silicon Mac | by 60 % of your RAM | | 16 GB Mac: `7b`; 32 GB Mac: `14b`; 64 GB Mac: `32b` |

Download the model and, if it is not the default `7b`, tell the skill to use
it:

```
ollama pull qwen2.5-coder:14b
export LOCAL_CODER_MODEL=qwen2.5-coder:14b    # add this line to ~/.bashrc or ~/.zshrc
```

Any other Ollama model works too. Prefer models trained for code, and pick the
largest one that still fits completely into your VRAM. To see whether it fits,
load it once and look at the `PROCESSOR` column:

```
ollama run qwen2.5-coder:7b "hello"
ollama ps
```

`100% GPU` is ideal. A split such as `22%/78% CPU/GPU` still works but is
slower; if the CPU share is large, go one model size down.

## Step 4: Use it

In Claude Code, either call the skill directly:

```
/local-coder write unit tests for src/parser.py
```

or just say that you want the local model to do the writing, for example
"let the local model write this" or "save tokens on this one".

Claude shows a short plan with the classification of each step, has the local
model write the routine files, reviews them, and finishes with a summary of
what was written locally, what it had to fix, and what it wrote itself.

## Settings

| What | How |
|---|---|
| Different model | environment variable `LOCAL_CODER_MODEL`, or `--model` on the script |
| Ollama on another host or port | environment variable `OLLAMA_HOST` (for example `192.168.1.20:11434`) |
| Larger context window | `--num-ctx` on the script (default `8192`; larger needs more memory) |
| Creativity | `--temperature` on the script (default `0.2`) |

## Using the script without Claude

`local_gen.py` is a normal command line tool:

```
python scripts/local_gen.py --spec spec.md --out module.py [--context a.py b.py] [--overwrite | --edit]
```

| Option | Meaning |
|---|---|
| `--spec FILE` | Text file with the task description. `-` reads from standard input |
| `--out FILE` | The file to write |
| `--context FILE...` | Reference files the model may read, for example a module to write tests for |
| `--overwrite` | Regenerate an existing file from scratch. The old content is **not** shown to the model, so it cannot copy its earlier mistake |
| `--edit` | Revise an existing file. The old content is shown to the model |

Without `--overwrite` or `--edit` the script refuses to replace an existing
file. Exit code `2` means the answer was cut off; make the step smaller.

## Troubleshooting

**GPU not used (`ollama ps` shows `100% CPU`).**
Some AMD and Intel cards are not covered by Ollama's default GPU backends. On
Linux, switch on the Vulkan backend for the Ollama service:

```
sudo mkdir -p /etc/systemd/system/ollama.service.d
printf '[Service]\nEnvironment="OLLAMA_VULKAN=1"\n' | sudo tee /etc/systemd/system/ollama.service.d/vulkan.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

On the test machine (Radeon RX 5700 XT) this raised a 7B model from 6.5 to 23
tokens per second.

**"Ollama nicht erreichbar" (Ollama not reachable).**
The server is not running or listens somewhere else. Run `ollama serve`, or
set `OLLAMA_HOST`.

**"Eingabe ca. N Tokens, Kontextfenster 8192" (input too large).**
The specification plus reference files do not fit into the model's context
window. Pass fewer `--context` files, split the step, or raise `--num-ctx`.

**The model is slow even on the GPU.**
Your desktop and browser also use VRAM. Close GPU-heavy programs or use the
next smaller model.

## What to expect

Measured on a Ryzen 9 3900XT with 32 GB RAM and a Radeon RX 5700 XT (8 GB),
using `qwen2.5-coder:7b` at 13–14 tokens per second:

A small command line notes app was built as a test: four files, about 265
lines, 18 unit tests.

| File | Local attempts | Fixes by Claude |
|---|---|---|
| `storage.py` | 1 | 3 lines |
| `cli.py` | 2 | first attempt unusable; second attempt needed 2 more lines |
| `test_storage.py` | 1 | 1 wrong assertion removed |
| `test_cli.py` | 1 | 1 missing import |

All 18 tests passed in the end. The local model wrote about 2,700 tokens in a
little under 4 minutes.

The honest summary:

- **A 7B model makes mistakes** even with a precise specification. The review
  by the large model is not optional.
- **The saving depends on the task.** In the test above it was small: writing
  specifications precise enough for a 7B model took almost as many tokens as
  writing the code directly. It pays off where a short description yields a lot
  of code: tests for existing code, many similar files, docstrings,
  conversions.
- **Logic with several connected parts** is cheaper for Claude to write
  itself. The skill tells Claude to do exactly that.
- **A larger local model shifts the balance.** With 12 GB of VRAM or more,
  specifications can be shorter and fewer fixes are needed.

## License

MIT, see [LICENSE](LICENSE).
