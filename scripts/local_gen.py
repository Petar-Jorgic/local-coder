#!/usr/bin/env python3
"""Lässt ein lokales Ollama-Modell genau eine Datei schreiben.

Die Ausgabe auf stdout ist absichtlich kurz (Pfad, Zeilen, Tempo), damit der
generierte Code nicht ungefragt im Kontext des großen Modells landet.
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
    # Abgeschnittene Antwort: öffnender Zaun ohne schließenden
    m = re.search(r"```[^\n]*\n(.*)", text, re.S)
    if m:
        return m.group(1), False
    return text, False


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", required=True, help="Datei mit der Aufgabenbeschreibung, '-' für stdin")
    p.add_argument("--out", required=True, help="Zieldatei, die geschrieben wird")
    p.add_argument("--context", nargs="*", default=[], help="Referenzdateien (nur lesen)")
    p.add_argument("--overwrite", action="store_true",
                   help="vorhandene Zieldatei neu erzeugen, ohne den alten Inhalt zu zeigen")
    p.add_argument("--edit", action="store_true",
                   help="vorhandene Zieldatei überarbeiten; der alte Inhalt wird mitgegeben")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--num-ctx", type=int, default=8192)
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--timeout", type=int, default=900)
    a = p.parse_args()

    if os.path.exists(a.out) and not (a.overwrite or a.edit):
        sys.exit(
            f"FEHLER: {a.out} existiert bereits. --overwrite erzeugt neu, "
            "--edit überarbeitet den vorhandenen Inhalt."
        )
    if a.edit and not os.path.exists(a.out):
        sys.exit(f"FEHLER: --edit, aber {a.out} existiert nicht.")

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

    # Grobe Schätzung: 1 Token ~ 3 Zeichen. Eingabe darf das Fenster nicht füllen.
    est = (len(prompt) + len(SYSTEM)) // 3
    if est > a.num_ctx - 1500:
        sys.exit(
            f"FEHLER: Eingabe ca. {est} Tokens, Kontextfenster {a.num_ctx}. "
            "Weniger Referenzdateien übergeben, den Schritt kleiner schneiden "
            "oder --num-ctx erhöhen (langsamer, mehr Speicher)."
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
        sys.exit(f"FEHLER: Ollama antwortet {e.code}: {e.read().decode(errors='replace')[:300]}")
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit(f"FEHLER: Ollama nicht erreichbar oder Zeitüberschreitung ({e}).")

    text = d.get("message", {}).get("content", "")
    if not text.strip():
        sys.exit("FEHLER: Leere Antwort vom lokalen Modell.")

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
        f"OK {a.out}: {code.count(chr(10))} Zeilen, {n} Tokens lokal, "
        f"{rate:.0f} tok/s, {time.time() - t0:.0f}s, Modell {a.model}"
    )
    if truncated:
        print(
            "WARNUNG: Antwort wirkt abgeschnitten (kein sauberer Code-Block oder "
            "Längenlimit erreicht). Datei prüfen, Schritt kleiner schneiden."
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
