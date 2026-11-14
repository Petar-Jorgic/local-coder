---
name: local-coder
description: Spart Tokens, indem das große Modell nur plant und prüft, während ein lokales Ollama-Modell den Code schreibt. Verwenden, wenn der Nutzer "local-coder", "lokal schreiben lassen", "mit dem lokalen Modell", "Tokens sparen" sagt oder /local-coder aufruft, und bei Fleißarbeit wie Boilerplate, Tests, einfachen Funktionen, Konvertierungen oder Doku, wenn der Nutzer diesen Ablauf für das Projekt gewünscht hat.
---

# local-coder: planen, lokal schreiben, prüfen

Du (das große Modell) schreibst den Plan und prüfst. Den Code schreibt ein
lokales Modell über Ollama. Ziel ist, teure Ausgabe-Tokens zu sparen, ohne
schlechteren Code abzuliefern.

Das lokale Modell ist klein (ca. 7B, 8 GB VRAM, Kontext 8192 Tokens). Es
schreibt brauchbar, was genau beschrieben ist, und rät falsch, wo etwas offen
bleibt. Die Qualität hängt deshalb fast ganz an deiner Spezifikation.

## 1. Einstufen: wer schreibt was

Stufe jeden Schritt ein, bevor du ihn vergibst.

| Stufe | Beispiele | Wer schreibt |
|---|---|---|
| Winzig | Änderung unter ca. 15 Zeilen, Umbenennen, ein Import | Du direkt. Die Spezifikation wäre länger als der Code. |
| Fleißarbeit | Neue Datei nach klarem Muster, Tests zu vorhandenem Code, CRUD, Datenklassen, Parser für festes Format, Konvertierung, Docstrings | Lokales Modell |
| Schwierig | Nebenläufigkeit, Sicherheit, Auth, Geld, Migrationen, knifflige Algorithmen, Änderungen quer durch viele Dateien, Fehlersuche | Du direkt |

Im Zweifel selbst schreiben. Ein lokaler Fehlversuch plus Nachbessern kostet
mehr als direktes Schreiben.

## 2. Plan

Zerlege die Aufgabe so, dass jeder lokale Schritt **genau eine Datei** ergibt,
höchstens ca. 150 Zeilen. Größere Dateien teilst du auf oder schreibst sie
selbst. Halte den Plan kurz und zeig ihn dem Nutzer als Liste mit der
Einstufung je Schritt; auf eine Freigabe musst du nicht warten, außer der
Nutzer will das.

## 3. Spezifikation je lokalem Schritt

Schreib die Spezifikation in eine Datei im Scratchpad. Sie muss ohne dieses
Gespräch verständlich sein, denn das lokale Modell sieht nur sie und die
Referenzdateien:

- Zweck der Datei in einem Satz
- Sprache, Version, erlaubte Bibliotheken
- jede öffentliche Funktion oder Klasse mit exakter Signatur und Verhalten
- Randfälle und Fehlerverhalten ausdrücklich
- ein Ein-/Ausgabe-Beispiel, wo das Verhalten nicht offensichtlich ist
- was die Datei nicht tun soll, falls eine naheliegende Fehlrichtung existiert

Spezifikationen auf Englisch schreiben; das lokale Modell folgt dem
zuverlässiger.

## 4. Lokal schreiben lassen

```
python ~/.claude/skills/local-coder/scripts/local_gen.py \
  --spec <spec.md> --out <zieldatei> [--context datei1 datei2] [--overwrite | --edit]
```

- `--context`: nur Dateien, deren Schnittstellen der Schritt wirklich braucht.
  Das Fenster ist klein; das Skript bricht ab, wenn die Eingabe nicht passt.
- `--overwrite`: eine vorhandene Datei von Grund auf neu erzeugen. Der alte
  Inhalt wird dem Modell nicht gezeigt. Das ist die richtige Wahl nach einem
  Fehlversuch, sonst schreibt das Modell seinen Fehler wieder ab.
- `--edit`: eine vorhandene, im Kern richtige kleine Datei überarbeiten. Ihr
  aktueller Inhalt wird mitgegeben. In großen Dateien änderst du selbst mit
  Edit.
- Modell: Standard `qwen2.5-coder:7b`, änderbar mit `--model` oder der
  Umgebungsvariable `LOCAL_CODER_MODEL`.
- Das Skript gibt nur eine Statuszeile aus. Exit-Code 2 heißt: Antwort
  abgeschnitten, Schritt kleiner schneiden.
- Immer nur ein Aufruf gleichzeitig. Parallele Aufrufe teilen sich die eine
  GPU und werden langsamer, nicht schneller.

## 5. Prüfen

Prüfe erst billig, dann teuer:

1. Maschinell: Syntaxprüfung, Linter, Typprüfung, Tests, was das Projekt eben
   hat. Fehlermeldungen sind kürzer als der Code.
2. Lesen: Lies jede lokal geschriebene Datei einmal ganz. Achte besonders auf
   erfundene Funktionen oder Bibliotheken, vergessene Randfälle aus der
   Spezifikation, stillschweigend geänderte Signaturen und Platzhalter.

Der lokale Code gilt erst als fertig, wenn du ihn gelesen hast. Ein grüner
Test allein reicht nicht, wenn das lokale Modell den Test auch geschrieben hat.

## 6. Nachbessern

- Kleine Fehler (wenige Zeilen): selbst mit Edit beheben.
- Grundsätzlich daneben: Spezifikation schärfen und **einmal** neu erzeugen
  lassen.
- Zweiter Fehlversuch: Schritt selbst schreiben und für den Rest der Aufgabe
  ähnliche Schritte nicht mehr lokal vergeben.

## 7. Abschluss

Sag dem Nutzer am Ende in ein, zwei Sätzen, welche Dateien lokal entstanden
sind, was du nachbessern musstest und was du selbst geschrieben hast. Die
lokal erzeugten Tokens stehen in den Statuszeilen des Skripts.

## Wenn Ollama nicht läuft

Meldet das Skript „nicht erreichbar" oder fehlt das Modell (`ollama list`),
sag es dem Nutzer und schreib den Code selbst, statt zu warten.
