# Haftungsausschluss

[English](DISCLAIMER.md) · [简体中文](DISCLAIMER.zh-CN.md) · [繁體中文](DISCLAIMER.zh-TW.md) · [日本語](DISCLAIMER.ja.md) · [한국어](DISCLAIMER.ko.md) · [Español](DISCLAIMER.es.md) · [Français](DISCLAIMER.fr.md) · Deutsch · [Português (Brasil)](DISCLAIMER.pt-BR.md) · [Русский](DISCLAIMER.ru.md)

personagent wird unter der [PolyForm Noncommercial License 1.0.0](../LICENSE) veröffentlicht: Nutzung, Änderung und Weitergabe sind für nichtkommerzielle Zwecke kostenlos, für kommerzielle Zwecke nicht gestattet. Es bringt eine KI-Figur in deine Chats, und du bist derjenige, der es betreibt. Du bist dafür verantwortlich, was es sagt, wo es das sagt und welche Konten es nutzt. Diese Seite ist keine Rechtsberatung.

## Chat-Plattformen und deine Konten

personagent erreicht eine Chat-Plattform auf zwei Wegen. QQ-Bots (offiziell), persönliches WeChat, Telegram und Discord verbindet es selbst. Jede andere Plattform läuft über eine Brücke eines Drittanbieters, meist das AstrBot, das personagent für dich herunterlädt und ausführt. Dein Risiko hängt davon ab, als was sich die Verbindung anmeldet.

- **Offizielle Bot-APIs** sind für Bots gemacht. Dazu gehören die offizielle QQ-Bot-API, Tencents iLink-Bot-API für persönliches WeChat, Telegram, Discord, Slack, KOOK, Feishu/Lark, DingTalk, WeCom und ähnliche Plattformen. Du musst dich trotzdem an die Entwicklerbedingungen und Ratenlimits jeder Plattform halten.
- **Inoffizielle Clients** melden sich als normales Benutzerkonto an und steuern es per Software. Die Plattform erlaubt das nicht und kann es in ihren Bedingungen verbieten. Sie kann das Konto einschränken, einfrieren oder dauerhaft sperren. Das betrifft:
  - **QQ über NapCat, LLOneBot, Lagrange oder eine andere OneBot-Implementierung**, also die fortgeschrittene Option OneBot v11. Ein offizieller QQ-Bot braucht nichts davon. Tencent erlaubt sie nicht, und das Risiko ist bei Cloud- oder ausländischen IP-Adressen am höchsten.
  - **WhatsApp, Signal, Messenger, Instagram, Google Messages und andere über eine mautrix-Brücke**, so erreicht sie der Matrix-Konnektor. Die Brücke ist ein inoffizieller Client des jeweiligen Netzwerks, und einige dieser Netzwerke regeln automatisierte Nachrichten in ihren Bedingungen. Siehe [die Hinweise zum Matrix-Konnektor](../integrations/matrix/README.de.md#bedingungen-der-einzelnen-netzwerke).
  - Alles andere, was sich als Person anmeldet.

Wenn du eines davon nutzt, nimm ein eigenes Konto, dessen Verlust du verkraften kannst, niemals dein Hauptkonto. Betreibe es wenn möglich aus einem Heimnetz statt von einem Cloud-Server. Lies die aktuellen Bedingungen jedes Netzwerks, das du verbindest. Weder der Autor von personagent noch die Betreuer der Drittprojekte, mit denen es arbeitet (AstrBot, NapCat, Koishi, mautrix und andere), haften für ein verlorenes oder eingeschränktes Konto.

## Sag den Leuten, dass es ein Bot ist

- Sag den Leuten in einem Chat, dass sie mit einer KI sprechen, und hol die Zustimmung des Gruppeninhabers oder der Admins ein, bevor du es hinzufügst. Gib dem Konto einen Namen, der das deutlich macht, und schreib es ins Profil, wenn die Plattform eines hat.
- Wenn jemand ernsthaft fragt, ob es eine KI ist, ist personagent so gebaut, dass es das sagt. Bearbeite die Persona nicht so, dass es das leugnet.
- Nutze es nicht, um dich als reale Person auszugeben oder jemanden darüber zu täuschen, mit wem oder was er spricht. Manche Plattformen und Länder verlangen, dass Bots offengelegt werden, oder schränken automatisierte Konten ein. Prüfe die Regeln, die für dich gelten.
- Halte es aus Gruppen heraus, in denen seine Antworten Menschen schaden oder sie irreführen könnten, etwa Gruppen zu medizinischen, rechtlichen, finanziellen oder Krisenthemen und Gruppen mit Kindern.
- Wenn jemand es bittet zu gehen oder fragt, was es über ihn weiß, nimm das ernst. Der Admin kann es eine Notiz vergessen lassen (`<name>, forget ...`), und alles, was es speichert, liegt in seinem Home-Ordner (siehe unten).

## Bildnachweis für die Porträts

Die Porträts des DeepSeek-Walmädchens, des GPT-Drachenmädchens und der Claude-Dame wurden für personagent nach Entwürfen gezeichnet, die die Community bereits zeichnet. Das Walmädchen geht auf 溟月 zurück, eine Originalfigur des Bilibili-Creators 上善无形 (CC BY-NC-SA 4.0), im Dienstmädchen-Outfit, das ZipZipPipe ihr gegeben hat. Das Drachenmädchen folgt ZipZipPipes weißer Drachin. Die Claude-Dame folgt einem Community-Entwurf, bei dem nicht bekannt ist, wer ihn zuerst gezeichnet hat. Die Porträts stehen unter einer eigenen Lizenz, CC BY-NC-SA 4.0: Behalte die Namensnennung bei, nutze sie nicht kommerziell und gib Änderungen unter derselben Lizenz weiter. Siehe `persona_agent/static/characters/LICENSE.md`.

## Was dein Modellanbieter sieht

Jede Antwort schickt dem Modellanbieter einen Prompt aus der Persona, den letzten Nachrichten des Chats (mit Namen), den Notizen, die der Bot über den Chat führt, und dem, was er aus dem Gelernten abgerufen hat. Wenn du ein Vision-Modell einstellst, gehen Bilder dorthin. Andere Dienste, die du einschaltest, sehen ebenfalls Teile davon. Dazu gehören die von dir konfigurierten Endpunkte für Fallback, Richter, Selbstbewertung und Embeddings sowie die Websuche, die eine kurze Anfrage an Tavily schickt, wenn du einen Schlüssel setzt, und sonst an DuckDuckGo. Die Update-Prüfung schickt pypi.org nur die Versionsnummer von personagent, höchstens einmal am Tag; `UPDATE_CHECK_ENABLED=false` schaltet sie ab.

Lies die Richtlinie zur Datenspeicherung jedes Anbieters, bevor du ihn nutzt. Manche Anbieter behalten Prompts, und manche trainieren damit, solange du nicht widersprichst. Die Voreinstellung, die kostenlosen Modelle von OpenRouter, kann solche Anbieter erreichen. Ein lokales Modell (Ollama, llama.cpp) behält die Prompts auf deinem Rechner. Die Leute im Chat haben den Bedingungen keines Anbieters zugestimmt, also sag ihnen, wohin ihre Nachrichten gehen.

## Was es auf deinem Rechner speichert

Alles, was es behält, liegt unter seinem Home-Ordner. Einstellungen und API-Schlüssel stehen in `.env`. Bot-Zugangsdaten und das AstrBot, das es für dich ausführt, liegen in `platforms/`. `runtime/` enthält die Chat-Notizen, die von ihm beurteilten Reaktionen (wörtlich zitiert), das Register des Gelernten und die gelernten Beispiele. Wenn du `SERVER_LOG_FILE` setzt, können auch die Logs Details aus Gesprächen enthalten. Halte den Ordner privat. Veröffentliche ihn nie und hänge ihn nie an ein Issue an, und sichere ihn, wenn dir das Gelernte wichtig ist. Die Gesetze zum Speichern und Verarbeiten fremder Nachrichten unterscheiden sich je nach Land, und deine einzuhalten liegt in deiner Verantwortung.

Es kann etwas Falsches lernen. Eine Änderung braucht zwei übereinstimmende Reaktionen aus demselben Chat, mindestens eine davon von der Person, an die die Antwort ging. Jede Änderung wird in einem Register festgehalten, das nur ergänzt wird und das du mit `personagent learned` oder in der Ansicht Aktivität der lokalen Seite prüfen und rückgängig machen kannst. Sieh ab und zu nach.

## Keine Gewährleistung

Die Software wird „wie besehen“ bereitgestellt, ohne jegliche ausdrückliche oder stillschweigende Gewährleistung. Die Autoren haften nicht für Ansprüche, Schäden oder Verluste, die aus ihrer Nutzung entstehen. Siehe [LICENSE](../LICENSE).
