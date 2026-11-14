# Die Skripte in `tools/`

[English](tools.md) · [简体中文](tools.zh-CN.md) · [繁體中文](tools.zh-TW.md) · [日本語](tools.ja.md) · [한국어](tools.ko.md) · [Español](tools.es.md) · [Français](tools.fr.md) · Deutsch · [Português (Brasil)](tools.pt-BR.md) · [Русский](tools.ru.md)

Die Skripte in `tools/` richten sich an alle, die personagent aus einem Klon starten. Sie werden nicht mit dem Paket installiert und lesen `.env` und `runtime/` aus dem Klon. Führen Sie sie mit dem Interpreter des Klons im Wurzelverzeichnis des Repositorys aus:

```bash
.venv/bin/python tools/<script>.py --help     # Windows: .venv\Scripts\python.exe
```

Alltägliche Aufgaben sind Unterbefehle von `personagent` und keine Skripte: `personagent doctor`, `personagent learned` und `personagent eval`. Um eine Prompt-Änderung zu erproben, verwenden Sie `personagent chat`. Um sie zu messen, verwenden Sie `personagent eval`. `personagent eval --suite memory` läuft offline mit vorgegebenen Antworten der Konsolidierung, 21 Fälle pro Sprache, und benötigt keinen Schlüssel; in dieser Version bestehen alle. Die anderen Suiten rufen ein Modell auf.

| Skript | Funktion | Voraussetzungen | Ruft ein Modell auf | Status |
|---|---|---|---|---|
| `import_stickers_folder.py` | Importiert einen Bilderordner in die Sticker-Bibliothek und versieht jedes Bild mit Tags, damit eine neue Bibliothek nicht leer beginnt. `--dry-run` zeigt die Anzahl an, `--no-tag` kopiert nur die Dateien | Ein Bilderordner sowie `VISION_MODEL`, `VISION_API_KEY` und `VISION_BASE_URL` für die Tags | Ja, ein Vision-Aufruf pro Bild, außer mit `--dry-run` oder `--no-tag` | Unterstützt |
| `bootstrap_from_history.py` | Verschafft einer neuen Bereitstellung einen einmaligen Start aus dem Verlauf einer QQ-Gruppe. Es erstellt das Sticker- und Nachrichtenlängen-Profil des Administrators und speichert die gesehenen Sticker in der Bibliothek | Der HTTP-Server von NapCat, einem QQ-Client eines Drittanbieters, unter `QQ_ONEBOT_URL` (erforderlich), sowie QQ-Gruppen in `ACCESS_GROUPS` oder `--group` | Nein. Das Vision-Modell des laufenden Bots versieht die gespeicherten Sticker später mit Tags | Experimentell, nur QQ und NapCat |
| `sticker_holdout_eval.py` | Misst, wie stabil und genau die Sticker-Freigabe bei von Hand beschrifteten Stickern ist | `runtime/holdout.jsonl` (Format in `tools/holdout.example.jsonl`) und die drei `VISION_*`-Einstellungen | Ja, Bilder × `--runs` (Standard 5) Vision-Aufrufe, etwa 150 bei 30 Bildern | Experimentell |
| `package_smoke.py` | Prüft einen installierten `personagent`-Befehl vollständig: Version, `init --no-input`, `chat`, `run` mit `/health` und `doctor --json` | Ein installiertes `personagent` (`--personagent PATH`), sonst nichts | Nein, ein Ersatzserver antwortet | Unterstützt. Die CI führt es unter Linux und Windows aus |
| `welcome_smoke.py` | Prüft die installierte lokale Seite vollständig: `start --no-browser`, das Speichern eines Schlüssels, ein Chat mit der echten Figur, ein zweiter Start, der die Seite wiederverwendet, und ein ordnungsgemäßes Beenden | Ein installiertes `personagent` (`--personagent PATH`), sonst nichts | Nein, derselbe Ersatzserver antwortet | Unterstützt. Die CI führt es unter Linux und Windows aus |
| `window_smoke.py` | Öffnet das echte App-Fenster mit einem temporären Home-Ordner, richtet die Seite ein, chattet im Fenster und schließt es anschließend | Unter macOS und Linux ein mit dem App-Extra installiertes `personagent` (`pip install "personagent[app]"`); unter Linux zusätzlich eine Anzeige, etwa `xvfb-run` | Nein, derselbe Ersatzserver antwortet | Unterstützt. Die CI führt es unter Linux, macOS und Windows aus |
| `release_notes.py` | Prüft ein Release-Tag gegen `pyproject.toml` und gibt den CHANGELOG-Abschnitt dieser Version aus | Das Tag, zum Beispiel `v1.1.0` | Nein | Unterstützt. Der Release-Workflow führt es aus |
| `locale_gaps.py` | Zählt für jede Sprache in `persona_agent/locales/`, wie viele Sätze des Einrichtungsassistenten, des Chats im Terminal und der Demo übersetzt sind. Mit einem Sprachcode wie `ja` gibt es die noch fehlenden Sätze aus, die auf Englisch erscheinen würden | Nichts | Nein | Unterstützt. `tests/test_locales.py` schlägt fehl, wenn einer fehlt |

Experimentelle Skripte sind Hilfsmittel für Forschung und Wartung und können sich ohne Übergangsfrist ändern oder entfallen. Skripte, die ein Modell aufrufen, verbrauchen Guthaben des Kontos in Ihrer `.env`; lesen Sie daher zuerst `--help` und probieren Sie `--dry-run` aus, sofern verfügbar.
