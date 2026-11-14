#!/usr/bin/env python3
"""Check this machine for local-coder: hardware, Ollama, and the best-fitting model.

Standard library only. Read-only: it installs and changes nothing.
"""
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request

HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")

# (minimum memory budget in GB, model tag, download size)
TIERS = [
    (20.0, "qwen2.5-coder:32b", "20 GB"),
    (10.0, "qwen2.5-coder:14b", "9 GB"),
    (5.5, "qwen2.5-coder:7b", "4.7 GB"),
    (3.0, "qwen2.5-coder:3b", "1.9 GB"),
    (0.0, "qwen2.5-coder:1.5b", "1 GB"),
]


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def ram_gb():
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except (ValueError, OSError, AttributeError):
        return None


def gpus():
    """Return a list of (name, vram_gb, kind)."""
    found = []
    if shutil.which("nvidia-smi"):
        out = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
        for line in out.strip().splitlines():
            name, _, mem = line.rpartition(",")
            try:
                found.append((name.strip(), float(mem) / 1024, "nvidia"))
            except ValueError:
                pass
    if not found and sys.platform.startswith("linux"):
        for f in glob.glob("/sys/class/drm/card*/device/mem_info_vram_total"):
            try:
                gb = int(open(f).read()) / 2**30
            except (OSError, ValueError):
                continue
            vendor = ""
            try:
                vendor = open(os.path.join(os.path.dirname(f), "vendor")).read().strip()
            except OSError:
                pass
            kind = {"0x1002": "amd", "0x8086": "intel"}.get(vendor, "other")
            if gb >= 1:
                found.append((f"{kind.upper()} GPU ({f.split('/')[4]})", gb, kind))
    return found


def ollama_models():
    """Return installed model names, or None if the server is not reachable."""
    host = HOST if HOST.startswith("http") else f"http://{HOST}"
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as r:
            return [m["name"] for m in json.load(r).get("models", [])]
    except (OSError, ValueError):
        return None


def main():
    ram = ram_gb()
    apple = sys.platform == "darwin" and platform.machine() == "arm64"
    found = gpus()

    print("== Hardware ==")
    print(f"OS:   {platform.system()} {platform.machine()}")
    print(f"RAM:  {ram:.0f} GB" if ram else "RAM:  unknown")

    notes = []
    if apple and ram:
        budget = ram * 0.6
        print(f"GPU:  Apple Silicon, unified memory (about {budget:.0f} GB usable for a model)")
    elif found:
        name, vram, kind = max(found, key=lambda g: g[1])
        budget = vram
        print(f"GPU:  {name}, {vram:.0f} GB VRAM")
        if kind in ("amd", "intel") and sys.platform.startswith("linux"):
            notes.append(
                "AMD/Intel GPU on Linux: if `ollama ps` shows 100% CPU, enable the Vulkan "
                "backend with OLLAMA_VULKAN=1 (see README, 'GPU not used')."
            )
    else:
        budget = 0.0
        print("GPU:  none detected")
        notes.append(
            "No GPU detected: the model will run on the CPU. That works, but expect "
            "single-digit tokens per second; local-coder is slow to use that way."
        )

    # Without a GPU, system RAM is the limit, but big models are too slow on a CPU.
    if budget == 0.0 and ram:
        budget = 4.0 if ram >= 16 else 1.0

    model, size = next((m, s) for need, m, s in TIERS if budget >= need)

    print("\n== Ollama ==")
    binary = shutil.which("ollama")
    print(f"Binary: {binary or 'NOT INSTALLED -> https://ollama.com/download'}")
    installed = ollama_models()
    if installed is None:
        print(f"Server: not reachable at {HOST}" + (" (start it with `ollama serve`)" if binary else ""))
    else:
        print(f"Server: running at {HOST}, {len(installed)} model(s) installed")

    print("\n== Recommendation ==")
    print(f"Model:  {model} (download {size})")
    if installed is not None and model in installed:
        print("Status: already installed")
    else:
        print(f"Get it: ollama pull {model}")
    if model != "qwen2.5-coder:7b":
        print(f"Use it: export LOCAL_CODER_MODEL={model}")
    for n in notes:
        print(f"Note:   {n}")


if __name__ == "__main__":
    main()
