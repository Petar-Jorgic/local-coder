#!/usr/bin/env python3
"""Have a local Ollama model write exactly one file.

The output on stdout is deliberately short (path, lines, speed) so that the
generated code does not land in the large model's context unasked.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = os.environ.get("LOCAL_CODER_MODEL", "qwen2.5-coder:7b")
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")

SYSTEM = (
    "You are a precise code generator. You write exactly ONE file.\n"
    "Rules:\n"
    "- Output the COMPLETE content of the file in a single fenced code block.\n"
    "- No explanations, no text before or after the code block.\n"
    "- Follow the specification exactly: names, signatures, behaviour.\n"
    "- Do not invent APIs. Only use what the spec or the reference files show,\n"
    "  plus the standard library of the language.\n"
    "- No placeholders, no TODOs, no omitted parts."
)

FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def extract_code(text):
    blocks = FENCE.findall(text)
    if blocks:
        return max(blocks, key=len), True
    # Truncated answer: an opening fence without a closing one
    m = re.search(r"```[^\n]*\n(.*)", text, re.S)
    if m:
        return m.group(1), False
    return text, False


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", required=True, help="file with the task description, '-' for stdin")
    p.add_argument("--out", required=True, help="target file to write")
    p.add_argument("--context", nargs="*", default=[], help="reference files (read only)")
    p.add_argument("--overwrite", action="store_true",
                   help="regenerate an existing target file without showing the old content")
    p.add_argument("--edit", action="store_true",
                   help="revise an existing target file; the old content is passed along")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--num-ctx", type=int, default=8192)
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--timeout", type=int, default=900)
    a = p.parse_args()

    if os.path.exists(a.out) and not (a.overwrite or a.edit):
        sys.exit(
            f"ERROR: {a.out} already exists. --overwrite regenerates it, "
            "--edit revises the existing content."
        )
    if a.edit and not os.path.exists(a.out):
        sys.exit(f"ERROR: --edit given, but {a.out} does not exist.")

    spec = sys.stdin.read() if a.spec == "-" else open(a.spec, encoding="utf-8").read()

    parts = []
    for path in a.context:
        with open(path, encoding="utf-8") as f:
            parts.append(f"### Reference file: {path}\n```\n{f.read()}\n```")
    if a.edit:
        with open(a.out, encoding="utf-8") as f:
            parts.append(
                f"### Current content of the file to revise ({a.out})\n```\n{f.read()}\n```"
            )
    parts.append(f"### File to write: {a.out}\n\n### Specification\n{spec}")
    prompt = "\n\n".join(parts)

    # Rough estimate: 1 token ~ 3 characters. The input must not fill the window.
    est = (len(prompt) + len(SYSTEM)) // 3
    if est > a.num_ctx - 1500:
        sys.exit(
            f"ERROR: input is about {est} tokens, context window is {a.num_ctx}. "
            "Pass fewer reference files, make the step smaller, "
            "or raise --num-ctx (slower, more memory)."
        )

    body = json.dumps({
        "model": a.model,
        "stream": False,
        "keep_alive": "15m",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "options": {"num_ctx": a.num_ctx, "temperature": a.temperature},
    }).encode()

    host = DEFAULT_HOST if DEFAULT_HOST.startswith("http") else f"http://{DEFAULT_HOST}"
    req = urllib.request.Request(
        f"{host}/api/chat", data=body, headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: Ollama answered {e.code}: {e.read().decode(errors='replace')[:300]}")
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit(f"ERROR: Ollama not reachable or timed out ({e}).")

    text = d.get("message", {}).get("content", "")
    if not text.strip():
        sys.exit("ERROR: empty answer from the local model.")

    code, closed = extract_code(text)
    truncated = d.get("done_reason") == "length" or not closed
    if not code.endswith("\n"):
        code += "\n"

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(code)

    n = d.get("eval_count", 0)
    dur = d.get("eval_duration", 0) / 1e9
    rate = n / dur if dur else 0
    print(
        f"OK {a.out}: {code.count(chr(10))} lines, {n} local tokens, "
        f"{rate:.0f} tok/s, {time.time() - t0:.0f}s, model {a.model}"
    )
    if truncated:
        print(
            "WARNING: the answer looks cut off (no clean code block or length "
            "limit reached). Check the file and make the step smaller."
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
