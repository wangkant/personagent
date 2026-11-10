# Résultats d'évaluation, 2026-10-18

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · Français · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


`personagent eval` soumet le vrai agent à des moments de discussion étiquetés et conserve chaque cas, réponse et verdict. Cette exécution a mesuré le code publié comme personagent 1.3.0 (les rapports, écrits avant le changement de numéro de version, indiquent 1.2.2), avec le personnage d'exemple fourni (Nova en anglais, 小夏 en chinois) sur deux modèles via OpenRouter : `deepseek/deepseek-v4.1-flash` et `openai/gpt-6-luna`. Chaque cas a été exécuté trois fois, chaque fois dans un nouveau déploiement.

Les crochets sont des intervalles à 95 %. Ils comptent chaque cas une fois, donc les trois essais n'augmentent pas la taille de l'échantillon. Le fonctionnement de chaque suite est décrit dans le [guide d'utilisation](../../guide.fr.md#le-mesurer).

## Quand il parle

Il y a 60 moments de discussion de groupe par langue : 20 où personne ne le nomme, 20 juste après qu'il a parlé et 20 où son nom apparaît. La moitié de chaque sorte est étiquetée silence. Aucun juge n'intervient : chaque essai est juste ou faux selon son étiquette.

| Essais justes | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Anglais | 83 % [72–91] | 93 % [84–97] |
| Chinois | 80 % [68–88] | 91 % [80–96] |

- Il ignore rarement un message qui lui est destiné : au plus 3 essais sur 90 de ce type, par modèle et par langue.
- Quand personne ne l'avait nommé ou qu'il venait de parler, il a eu 93–100 % d'essais justes.
- La plupart des ratés sont son nom utilisé pour autre chose, ou dit à son sujet à quelqu'un d'autre : un cinéma, une marque d'écouteurs, un chiot, une citation. Sur ces 10 moments par langue, deepseek a quand même répondu dans 25 essais sur 30 en anglais et 29 sur 30 en chinois. gpt-6-luna a répondu dans 12 et 16. personagent traite un nom comme un appel, et le modèle passe rarement outre.
- À titre de comparaison, un bot qui répond exactement quand on le nomme a 50 % de ces moments justes.

## Jouer le personnage

personagent est comparé au même modèle recevant seulement le texte du personnage comme prompt système, ce que l'on obtient en collant le texte du personnage dans un modèle de discussion. Il y a 40 moments par langue, 22 en groupe et 18 en message privé. Claude Opus 5.5 a jugé chaque paire à l'aveugle deux fois, dans des sessions séparées, avec les réponses inversées. Une réponse ne gagne que si les deux choix s'accordent, et un partage compte pour moitié. Ne rien dire quand on est appelé compte comme une défaite.

| Taux de victoire de personagent | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| Anglais | 63 % [47–76] | 75 % [59–86] |
| Chinois | 58 % [43–72] | 53 % [38–67] |

- En anglais, il bat le prompt simple sur les deux modèles. En chinois, l'avantage reste dans le bruit.
- Le juge compte. Un second juge, Claude Haiku 5.5 exécuté via `personagent eval`, n'a abouti au même résultat que sur 53–64 % des paires. Ses taux de victoire étaient à moins de 4 points de ceux d'Opus, sauf sur gpt-6-luna en anglais, où il a donné 62 %.
- Les moments varient d'un essai à l'autre : sur deepseek en anglais, 11 moments sur 40 ont gagné les trois essais, 9 n'ont jamais gagné et 20 ont varié.

## Apprendre des corrections

Il y a 20 scénarios par langue, exécutés par le vrai chemin des réactions :

- 7 enseignent une convention de groupe que le modèle ne peut pas deviner, comme « on appelle la salle de sport la grotte » ou « le barbecue est chez Jules cette année ».
- 6 enseignent un style.
- 7 doivent être retenus : la correction d'un spectateur, celle d'un troll et une que la personne abandonne.

Un message ultérieur de la même discussion, formulé autrement, vérifie si le personnage utilise ce qu'on lui a enseigné. Il s'exécute une fois avant la correction et une fois après, et Opus 5.5 a jugé les réponses.

La première exécution de cette date a montré qu'une correction promue ne se transmettait presque jamais. Ce qui était promu était le nouvel essai du personnage lui-même, comme exemple de meilleure formulation, et le message suivant sur le même sujet sortait sans le fait. Les corrections conservent désormais aussi leur leçon sous forme d'une phrase, comme « Ce groupe appelle la salle de sport "la grotte". », et chaque prompt ultérieur de cette discussion la contient (voir le [guide d'utilisation](../../guide.fr.md#corrections)). La suite d'apprentissage a été réexécutée après ce changement. Les suites de prise de parole et de persona ne sont pas concernées.

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| A retenu ce qu'il fallait retenir | 42 essais sur 42 | 42 essais sur 42 |
| A promu ce qu'il fallait promouvoir | 69 sur 78 | 72 sur 78 |
| A utilisé une convention promue dans un message ultérieur | 23 sur 35 (66 % [40–85]) | 29 sur 42 (69 % [43–87]) |
| La même chose, avant la conservation des leçons | 2 sur 32 | 0 sur 26 |

- Avant toute correction, les modèles ont utilisé la convention dans 0 essai sur 84, donc ce qu'ils disent ensuite a bien été enseigné.
- La plupart des ratés restants viennent de deux scénarios. Quand on lui demande quoi choisir pour la « soirée film de ce jeudi », il ne l'appelle généralement pas Bad Film Thursday (1 sur 12). Quand on lui demande de noter un film qu'il n'a pas vu, il renvoie la question en popcorns mais donne rarement sa propre note (2 sur 11).
- Aucune correction de troll, de spectateur ou abandonnée n'est passée, ni avant ni après le changement. Sur les 15 essais retenus qui auraient dû être promus, le juge des réactions a refusé 6 corrections (toutes sur gpt-6-luna), 5 verdicts de deepseek ont été perdus à cause d'une sortie illisible et 4 ont échoué à l'étape du nouvel essai.
- Pendant l'exécution de deepseek en anglais, le JSON du juge des réactions est revenu illisible 24 fois, le raisonnement du modèle fuitant dans les clés. Reposer la question, ce qu'ajoute ce changement, en a récupéré 18. Les autres exécutions n'en ont eu aucun.
- Les scénarios de style ne peuvent pas montrer grand-chose : les modèles suivaient déjà ces styles dans 56 essais sur 72 avant toute correction, et dans 66 après.

## Ce que cela ne montre pas

Ces résultats couvrent un personnage sur deux modèles, sur des cas que nous avons écrits et étiquetés nous-mêmes. Un juge modèle n'est pas une personne, et les deux juges ici étaient souvent en désaccord sur les paires de persona. Opus 5.5 a jugé hors de `personagent eval`, en lisant les paires par lots d'environ 116 par session, comme l'enregistre le champ `rejudged` de chaque rapport. D'autres modèles, surtout les petits, peuvent faire moins bien.

## Fichiers

Chaque modèle a un dossier :

| Fichier | Contenu |
|---|---|
| `speak-<lang>.json` | Chaque moment, chaque essai, la réponse ou le silence, et l'étiquette |
| `persona-<lang>.json` | Les deux réponses, les deux choix d'Opus et le verdict de Haiku sous `earlier` |
| `learning-<lang>.json` | L'exécution avec leçons : chaque réaction, les candidats et leurs leçons, et les réponses de sonde avant et après |
| `learning-<lang>-before-lessons.json` | La première exécution, avant la conservation des leçons |

Pour exécuter les suites vous-même, voir [Le mesurer](../../guide.fr.md#le-mesurer). `--rejudge` rejuge un rapport avec un autre modèle.
