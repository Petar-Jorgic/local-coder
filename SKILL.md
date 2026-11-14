---
name: local-coder
description: Saves tokens by having the large model only plan and review while a local Ollama model writes the code. Use when the user says "local-coder", "let the local model write this", "use the local model", "save tokens", "lokal schreiben lassen", or invokes /local-coder, and for routine work such as boilerplate, tests, simple functions, conversions or docs when the user has asked for this workflow in the project.
---

# local-coder: plan, write locally, review

You (the large model) write the plan and do the review. A local model running
in Ollama writes the code. The goal is to save expensive output tokens without
delivering worse code.

The local model is small (about 7B, 8 GB VRAM, 8192 tokens of context). It
writes usable code for what is described exactly and guesses wrong wherever
something is left open. Quality therefore depends almost entirely on your
specification.

## 1. Classify: who writes what

Classify every step before you hand it out.

| Kind | Examples | Who writes it |
|---|---|---|
| Tiny | A change under about 15 lines, a rename, one import | You, directly. The specification would be longer than the code. |
| Routine | A new file that follows a clear pattern, tests for existing code, CRUD, data classes, a parser for a fixed format, a conversion, docstrings | Local model |
| Hard | Concurrency, security, auth, money, migrations, tricky algorithms, changes across many files, debugging | You, directly |

When in doubt, write it yourself. A failed local attempt plus the repair costs
more than writing it directly.

## 2. Plan

Cut the task so that every local step produces **exactly one file** of about
150 lines at most. Split larger files or write them yourself. Keep the plan
short and show it to the user as a list with the classification of each step.
You do not need to wait for approval unless the user wants that.

## 3. Specification for each local step

Write the specification to a file in the scratchpad. It must make sense
without this conversation, because the local model sees only the
specification and the reference files:

- the purpose of the file in one sentence
- language, version, allowed libraries
- every public function or class with its exact signature and behaviour
- edge cases and error behaviour, spelled out
- an input/output example wherever the behaviour is not obvious
- what the file must not do, if there is an obvious wrong direction

Write specifications in English; the local model follows them more reliably.

## 4. Have it written locally

```
python ~/.claude/skills/local-coder/scripts/local_gen.py \
  --spec <spec.md> --out <target file> [--context file1 file2] [--overwrite | --edit]
```

- `--context`: only files whose interfaces the step really needs. The window
  is small; the script aborts if the input does not fit.
- `--overwrite`: regenerate an existing file from scratch. The old content is
  not shown to the model. This is the right choice after a failed attempt,
  otherwise the model copies its own mistake.
- `--edit`: revise an existing small file that is right at its core. Its
  current content is passed along. In large files, make the change yourself
  with Edit.
- Model: `qwen2.5-coder:7b` by default; change it with `--model` or the
  environment variable `LOCAL_CODER_MODEL`.
- The script prints a single status line. Exit code 2 means the answer was
  cut off; make the step smaller.
- Only one call at a time. Parallel calls share the one GPU and get slower,
  not faster.

## 5. Review

Check the cheap way first, then the expensive way:

1. By machine: syntax check, linter, type check, tests, whatever the project
   has. Error messages are shorter than the code.
2. By reading: read every locally written file once in full. Look especially
   for invented functions or libraries, edge cases from the specification
   that were forgotten, silently changed signatures, and placeholders.

Local code only counts as done once you have read it. A green test alone is
not enough if the local model also wrote the test.

## 6. Repair

- Small mistakes (a few lines): fix them yourself with Edit.
- Wrong at its core: sharpen the specification and regenerate **once**.
- Second failure: write the step yourself and stop handing similar steps to
  the local model for the rest of the task.

## 7. Wrap-up

At the end, tell the user in a sentence or two which files were written
locally, what you had to fix, and what you wrote yourself. The locally
generated tokens are in the script's status lines.

## If Ollama is not running

If the script reports "not reachable" or the model is missing (`ollama list`),
tell the user and write the code yourself instead of waiting.

`python ~/.claude/skills/local-coder/scripts/check_setup.py` shows the
hardware, the Ollama status and the model that fits the machine. It changes
nothing.
