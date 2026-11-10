# Evaluationsergebnisse, 2026-10-18

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · Deutsch · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


`personagent eval` schickt den echten Agenten durch beschriftete Chat-Momente und bewahrt jeden Fall, jede Antwort und jedes Urteil auf. Dieser Lauf maß den als personagent 1.3.0 veröffentlichten Code (die Berichte, vor der Änderung der Versionsnummer geschrieben, nennen 1.2.2), mit der mitgelieferten Beispielfigur (Nova auf Englisch, 小夏 auf Chinesisch) auf zwei Modellen über OpenRouter: `deepseek/deepseek-v4.1-flash` und `openai/gpt-6-luna`. Jeder Fall lief dreimal, jedes Mal in einer neuen Bereitstellung.

Eckige Klammern sind 95-%-Intervalle. Sie zählen jeden Fall einmal; die drei Versuche vergrößern die Stichprobe daher nicht. Wie jede Suite funktioniert, steht im [Benutzerhandbuch](../../guide.de.md#messen).

## Wann er spricht

Es gibt 60 Gruppenchat-Momente pro Sprache: 20, in denen ihn niemand nennt, 20 direkt nachdem er gesprochen hat, und 20, in denen sein Name fällt. Die Hälfte jeder Art ist als Schweigen beschriftet. Es ist kein Richter beteiligt: Jeder Versuch ist gemäß seiner Beschriftung richtig oder falsch.

| Richtige Versuche | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Englisch | 83 % [72–91] | 93 % [84–97] |
| Chinesisch | 80 % [68–88] | 91 % [80–96] |

- Er übergeht selten eine an ihn gerichtete Nachricht: höchstens 3 von 90 solchen Versuchen, pro Modell und Sprache.
- Wenn ihn niemand nannte oder er gerade gesprochen hatte, waren 93–100 % der Versuche richtig.
- Die meisten Fehlschläge sind sein Name für etwas anderes oder eine Bemerkung über ihn an jemand anderen: ein Kino, eine Ohrhörermarke, ein Welpe, ein Zitat. Bei diesen 10 Momenten pro Sprache antwortete deepseek dennoch in 25 von 30 englischen und 29 von 30 chinesischen Versuchen. gpt-6-luna antwortete in 12 und 16. personagent behandelt einen Namen als Ruf, und das Modell setzt sich selten darüber hinweg.
- Zum Vergleich: Ein Bot, der genau dann antwortet, wenn er genannt wird, hat 50 % dieser Momente richtig.

## Die Figur spielen

personagent wird mit demselben Modell verglichen, das nur den Persona-Text als System-Prompt erhält; dies entspricht dem Ergebnis, wenn man die Figur in ein Chat-Modell einfügt. Es gibt 40 Momente pro Sprache, 22 in einer Gruppe und 18 in DMs. Claude Opus 5.5 beurteilte jedes Paar zweimal blind, in getrennten Sitzungen, mit vertauschten Antworten. Eine Antwort gewinnt nur, wenn beide Wahlen übereinstimmen, und eine Teilung zählt halb. Schweigen auf einen direkten Ruf zählt als Niederlage.

| Gewinnquote von personagent | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Englisch | 63 % [47–76] | 75 % [59–86] |
| Chinesisch | 58 % [43–72] | 53 % [38–67] |

- Auf Englisch schlägt er den einfachen Prompt auf beiden Modellen. Auf Chinesisch liegt der Vorsprung im Rauschen.
- Die Wahl des Richters ist entscheidend. Ein zweiter Richter, Claude Haiku 5.5 über `personagent eval`, kam nur bei 53–64 % der Paare zum selben Ergebnis. Seine Gewinnquoten lagen innerhalb von 4 Punkten der von Opus, außer bei gpt-6-luna auf Englisch, wo er 62 % ergab.
- Momente schwanken von Versuch zu Versuch: Bei deepseek auf Englisch gewannen 11 von 40 Momenten alle drei Versuche, 9 gewannen nie, und 20 gingen in beide Richtungen.

## Aus Korrekturen lernen

Es gibt 20 Szenarien pro Sprache, die den echten Reaktionspfad durchlaufen:

- 7 lehren eine Gruppenkonvention, die das Modell nicht erraten kann, etwa „wir nennen das Fitnessstudio die Höhle“ oder „das Grillen ist dieses Jahr bei Jules“.
- 6 lehren einen Stil.
- 7 müssen zurückgehalten werden: die Korrektur eines Zuschauers, die eines Trolls und eine, die die Person fallen lässt.

Eine spätere, anders formulierte Nachricht im selben Chat prüft, ob die Figur anwendet, was ihr beigebracht wurde. Sie läuft einmal vor der Korrektur und einmal danach, und Opus 5.5 beurteilte die Antworten.

Der erste Lauf an diesem Datum zeigte, dass eine beförderte Korrektur fast nie übernommen wurde. Befördert wurde der eigene neue Versuch der Figur, als Beispiel für bessere Formulierung, und die nächste Nachricht zum selben Thema enthielt den Fakt nicht. Korrekturen behalten ihre Lektion jetzt auch als einen Satz, etwa „Diese Gruppe nennt das Fitnessstudio ‚die Höhle‘.“, und jeder spätere Prompt in diesem Chat enthält ihn (siehe das [Benutzerhandbuch](../../guide.de.md#korrekturen)). Die Lern-Suite lief nach dieser Änderung erneut. Die Sprech- und Persona-Suiten sind davon nicht betroffen.

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Zurückgehalten, was zurückzuhalten war | 42 von 42 Versuchen | 42 von 42 Versuchen |
| Befördert, was zu befördern war | 69 von 78 | 72 von 78 |
| Eine beförderte Konvention in einer späteren Nachricht genutzt | 23 von 35 (66 % [40–85]) | 29 von 42 (69 % [43–87]) |
| Dasselbe, bevor Lektionen behalten wurden | 2 von 32 | 0 von 26 |

- Vor jeder Korrektur nutzten die Modelle die Konvention in 0 von 84 Versuchen, was sie danach sagen, ist also auf die Korrektur zurückzuführen.
- Die meisten verbleibenden Fehlschläge stammen aus zwei Szenarien. Gefragt, was er für den „Filmabend diesen Donnerstag“ wählen soll, nennt er ihn meist nicht Bad Film Thursday (1 von 12). Gebeten, einen Film zu bewerten, den er nicht gesehen hat, stellt er eine Rückfrage mit einer Bewertung in Popcorn, gibt aber selten selbst eine Bewertung ab (2 von 11).
- Keine Korrektur eines Trolls, eines Zuschauers oder eine fallengelassene kam durch, weder vor noch nach der Änderung. Von den 15 zurückgehaltenen Versuchen, die hätten befördert werden sollen, lehnte der Reaktionsrichter 6 Korrekturen ab (alle auf gpt-6-luna), 5 deepseek-Urteile gingen durch unleserliche Ausgabe verloren, und 4 scheiterten beim neuen Versuch.
- Während des englischen deepseek-Laufs kam das JSON des Reaktionsrichters 24-mal unleserlich zurück, wobei die Überlegungen des Modells in die Schlüssel sickerten. Die mit dieser Änderung eingeführte erneute Anfrage rettete 18 davon. In den anderen Läufen trat dies nicht auf.
- Die Stil-Szenarien sind wenig aussagekräftig: Die Modelle folgten diesen Stilen schon vor jeder Korrektur in 56 von 72 Versuchen und danach in 66.

## Was das nicht zeigt

Diese Ergebnisse decken eine Figur auf zwei Modellen ab, bei Fällen, die wir selbst geschrieben und beschriftet haben. Ein Richtermodell ist kein Mensch, und die beiden Richter hier waren sich bei den Persona-Paaren oft uneinig. Opus 5.5 beurteilte außerhalb von `personagent eval` und las die Paare in Stapeln von etwa 116 pro Sitzung, wie das Feld `rejudged` jedes Berichts festhält. Andere Modelle, besonders kleine, können schlechter abschneiden.

## Dateien

Jedes Modell hat einen Ordner:

| Datei | Inhalt |
|---|---|
| `speak-<lang>.json` | Jeder Moment, jeder Versuch, die Antwort oder das Schweigen und die Beschriftung |
| `persona-<lang>.json` | Beide Antworten, die zwei Wahlen von Opus und das Urteil von Haiku unter `earlier` |
| `learning-<lang>.json` | Der Lauf mit Lektionen: jede Reaktion, die Kandidaten und ihre Lektionen und die Testantworten davor und danach |
| `learning-<lang>-before-lessons.json` | Der erste Lauf, bevor Lektionen behalten wurden |

Um die Suiten selbst auszuführen, siehe [Messen](../../guide.de.md#messen). `--rejudge` beurteilt einen Bericht mit einem anderen Modell neu.
