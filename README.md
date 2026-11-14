# local-coder

Ein Skill für [Claude Code](https://claude.com/claude-code), der Tokens spart:
Claude plant und prüft, ein lokales Modell über [Ollama](https://ollama.com)
schreibt den Code.

*English: a Claude Code skill that lets Claude plan and review while a local
Ollama model writes the code, to save output tokens. The skill text is in
German.*

## Ablauf

1. **Einstufen:** Winzige Änderungen und schwierige Teile (Sicherheit,
   Nebenläufigkeit, Fehlersuche) schreibt Claude selbst. Fleißarbeit wie
   Boilerplate, Tests, einfache Funktionen und Konvertierungen geht ans lokale
   Modell.
2. **Plan:** Claude zerlegt die Aufgabe in Schritte von je einer Datei und
   schreibt pro Schritt eine genaue Spezifikation.
3. **Lokal schreiben:** `scripts/local_gen.py` schickt die Spezifikation an
   Ollama und schreibt die Datei. Claude sieht nur eine Statuszeile.
4. **Prüfen:** Claude lässt Linter und Tests laufen, liest jede Datei und
   bessert nach. Nach zwei Fehlversuchen schreibt Claude den Schritt selbst.

## Voraussetzungen

- Claude Code
- Ollama, lokal erreichbar unter `127.0.0.1:11434`
- Python 3 (nur Standardbibliothek)
- ein Code-Modell, Standard ist `qwen2.5-coder:7b` (ca. 4,7 GB, läuft mit
  8 GB VRAM)

## Installation

```
git clone https://github.com/Petar-Jorgic/local-coder ~/.claude/skills/local-coder
ollama pull qwen2.5-coder:7b
```

Danach in Claude Code `/local-coder <Aufgabe>` aufrufen oder „lass das lokal
schreiben" sagen.

## Einstellungen

| Was | Wie |
|---|---|
| Anderes Modell | Umgebungsvariable `LOCAL_CODER_MODEL` oder `--model` |
| Anderer Ollama-Host | Umgebungsvariable `OLLAMA_HOST` |
| Größeres Kontextfenster | `--num-ctx` (Standard 8192) |

Das Skript lässt sich auch ohne Claude verwenden:

```
python scripts/local_gen.py --spec spec.md --out modul.py [--context a.py b.py] [--overwrite | --edit]
```

- `--overwrite` erzeugt eine vorhandene Datei neu, ohne dem Modell den alten
  Inhalt zu zeigen.
- `--edit` gibt den alten Inhalt mit und lässt ihn überarbeiten.

## Grenzen

- Ein 7B-Modell macht Fehler, auch bei genauer Spezifikation. Die Prüfung
  durch das große Modell ist kein optionaler Schritt.
- Gespart wird nur bei Fleißarbeit. Bei kniffligem Code kostet Nachbessern
  mehr als direktes Schreiben.
- Ohne GPU ist das lokale Modell für diesen Ablauf zu langsam. Bei
  AMD-Karten ohne ROCm-Unterstützung hilft `OLLAMA_VULKAN=1` im Ollama-Dienst.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
