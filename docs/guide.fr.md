# Guide d'utilisation de personagent

[English](guide.md) · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · [한국어](guide.ko.md) · [Español](guide.es.md) · Français · [Deutsch](guide.de.md) · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

Ce guide explique comment configurer personagent, le placer dans vos discussions, lui enseigner des choses et vous en occuper. Le [README](readme/README.fr.md) est la version courte, et [Premiers pas](start.fr.md) parcourt la page locale écran par écran.

1. [Installation et dossier personnel](#installation-et-dossier-personnel)
2. [La page locale](#la-page-locale) : [Réglages avancés](#réglages-avancés) · [La vue Application](#la-vue-application)
3. [Le voir d'abord : la démo](#le-voir-dabord--la-démo)
4. [Commandes du terminal](#commandes-du-terminal) : [configuration](#configurer-dans-le-terminal) · [connecter une plateforme](#connecter-une-plateforme-dans-le-terminal) · [discussion](#discuter-dans-le-terminal) · [exécuter le service](#exécuter-le-service)
5. [En faire votre personnage](#en-faire-votre-personnage)
6. [Le placer dans une discussion](#le-placer-dans-une-discussion) : [Plateformes connectées par personagent lui-même](#plateformes-connectées-par-personagent-lui-même) · [Autres plateformes](#autres-plateformes-via-lastrbot-géré) · [Ponts que vous exécutez vous-même](#ponts-que-vous-exécutez-vous-même) · [Parler en premier](#parler-en-premier)
7. [Assistants de programmation](#assistants-de-programmation)
8. [Lui enseigner](#lui-enseigner)
9. [Mémoire](#mémoire)
10. [Activité](#activité)
11. [Le mesurer](#le-mesurer)
12. [Fonctionnement](#fonctionnement)
13. [Confidentialité et consentement](#confidentialité-et-consentement)
14. [Dépannage](#dépannage)
15. [Mettre à niveau depuis 0.x](#mettre-à-niveau-depuis-0x)
16. [État et autres documents](#état-et-autres-documents)

## Installation et dossier personnel

```sh
python -m pip install personagent
personagent
```

`personagent` ouvre [la page locale](#la-page-locale). Vous pouvez aussi l'installer ou le lancer de ces façons :

| Voie | Commande |
|---|---|
| Exécuter sans installer | `uvx personagent` (fait partie de [uv](https://docs.astral.sh/uv/), qui récupère aussi Python pour vous) |
| Une commande `personagent` permanente | `uv tool install personagent` ou `pipx install personagent` |
| Windows, depuis le ZIP des sources | décompressez-le et double-cliquez sur `start.bat` |
| Depuis un clone | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python -m venv .venv`, puis `.venv/bin/python -m pip install -e .` et `.venv/bin/python -m persona_agent` (sous Windows, `.venv\Scripts\python.exe`) |

personagent fonctionne sur Python 3.10–3.14. `start.bat` crée `.venv`, installe les dépendances et ouvre la même page ; la première fois, il place aussi une icône personagent sur le bureau et dans le menu Démarrer. Il les réinstalle chaque fois que la liste de dépendances de `pyproject.toml` change.

Le **dossier personnel** contient les réglages (`.env`), le personnage (`persona.txt`), ce qu'il apprend (`runtime/`) et les plateformes de discussion (`platforms/`). `platforms/` contient l'AstrBot géré et `direct.json`, qui stocke les identifiants des plateformes que personagent connecte lui-même. personagent utilise le premier de ces dossiers :

1. le dossier indiqué avec `--home DIR` ou `AGENT_HOME`. `--home` peut se placer avant ou après la commande, comme dans `personagent chat --home D:\bot`.
2. le clone, si vous lancez depuis un clone.
3. le dossier courant, s'il contient à la fois `.env` et `persona.txt`.
4. `~/personagent`, créé lors de la première configuration.

Pour exécuter plusieurs personnages depuis une seule installation, donnez à chacun son propre dossier personnel.

Ce guide écrit les commandes sous la forme `personagent ...`. Si vous ne l'avez pas installé, ajoutez `uvx` devant. Dans un clone, `.venv/bin/python -m persona_agent ...` fait la même chose (sous Windows, `.venv\Scripts\python.exe -m persona_agent ...`).

## La page locale

`personagent` (ou `personagent start`) sert une page accessible uniquement depuis cet ordinateur. Sous Windows, elle s'ouvre dans sa propre fenêtre. Sous macOS et Linux, elle s'ouvre dans le navigateur, ou aussi dans une fenêtre une fois que `pip install "personagent[app]"` a ajouté [pywebview](https://pywebview.flowrl.com/), avec Qt sous Linux. La page comporte six vues, présentées dans cet ordre dans la barre latérale :

- **Discussion** est une discussion individuelle avec le personnage dans la page. Le même agent que celui qui sert vos plateformes de discussion y répond. Dans cette discussion, vous êtes l'administrateur. Les autocollants et les images que le personnage envoie apparaissent dans la discussion, et une image qui n'est plus conservée est remplacée par une courte mention. Les messages que le personnage envoie après sa réponse, comme la réponse à une commande de mémoire envoyée pendant qu'il répondait ou un message qu'il lance de lui-même, apparaissent en quelques secondes tant que la vue **Discussion** est ouverte. Les uns comme les autres restent dans l'historique de la discussion. Lorsque le modèle ne répond pas, la page l'indique à la place d'une réponse et propose **Renvoyer**. **Commandes de mémoire**, sous la zone de saisie, liste les [commandes de mémoire](#commandes-de-mémoire) ; en sélectionner une l'insère dans la zone de saisie. **Oublier cette discussion** oublie tout ce dont le personnage se souvient de cette discussion et en commence une nouvelle ; ce dont il se souvient des autres discussions est conservé, et cet oubli est irréversible. Cette fonction nécessite les données de la vue [Activité](#activité).
- **Activité** montre les discussions où se trouve le personnage, ce qu'il a dit récemment, ce dont il se souvient et ce qu'il a appris. Voir [Activité](#activité).
- **Connecter des plateformes** place le personnage dans QQ, WeChat, Telegram, Discord et d'autres plateformes. Voir [Le placer dans une discussion](#le-placer-dans-une-discussion). En bas de la vue, **Assistants de programmation** relie le personnage aux [assistants de programmation](#assistants-de-programmation) installés sur cet ordinateur.
- **Personnage et réglages** est l'endroit où vous choisissez un service de modèles (OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama ou tout autre service compatible OpenAI), collez la clé d'API et choisissez un nom et une personnalité prédéfinie. **Vérifier et commencer la discussion** teste la clé avec une petite requête et ne l'enregistre que si la requête réussit. Après la configuration, la zone **Fiche du personnage** affiche `persona.txt`. **Enregistrer la fiche** redémarre l'agent avec le nouveau texte et conserve ce qu'il a appris. **Autres fonctions** active la recherche web via Tavily (DuckDuckGo est l'option gratuite par défaut), la compréhension d'images et la prise de parole en premier sur les plateformes de votre choix. Viennent ensuite les [Réglages avancés](#réglages-avancés).
- **Entraînement** joue la démonstration scriptée et anime un groupe de discussion d'entraînement. Voir [Le voir d'abord : la démo](#le-voir-dabord--la-démo).
- **Application** vérifie les services dont dépend le personnage et regroupe les journaux, l'exécution en arrière-plan, les mises à jour et vos données. Voir [La vue Application](#la-vue-application).

**Entraînement** et **Application** sont accessibles avant même la configuration d'un modèle. Tant que vous n'avez connecté aucune plateforme, la vue **Discussion** affiche une courte barre **Prise en main**.

Relancer `personagent` fait réapparaître la page déjà ouverte. `--browser` ouvre la page dans le navigateur plutôt que dans une fenêtre, et `--no-browser` affiche le lien sans rien ouvrir. Sous Windows, `personagent shortcut` place sur le bureau et dans le menu Démarrer une icône qui ouvre la fenêtre sans terminal derrière, et `personagent shortcut --remove` la retire. La vue **Application** offre les mêmes possibilités.

Quand un personagent plus récent est sur PyPI, la vue Discussion affiche un avis avec la commande qui met à jour votre installation, qu'elle vienne de pip, uvx, uv tool, pipx ou d'un clone Git. Pour un ZIP des sources décompressé, l'avis renvoie plutôt à la page des versions. Le terminal affiche la même commande. Fermer l'avis le masque pour cette version, et **N disponible** sous le numéro de version le fait réapparaître. `personagent up` et `personagent doctor` signalent aussi une nouvelle version. La page et `up` interrogent pypi.org au plus une fois par jour, en arrière-plan. `doctor` interroge immédiatement quand la dernière réponse date de plus d'un jour. Définissez `UPDATE_CHECK_ENABLED=false` pour désactiver la vérification. La vue **Application** peut également installer la mise à jour elle-même ; voir [Version et mises à jour](#version-et-mises-à-jour).

La page démarre l'agent et les plateformes connectées en arrière-plan ; laissez donc sa fenêtre ouverte pendant que vous les utilisez. Tout ce qu'elle a démarré s'arrête avec elle, que vous cliquiez sur **Quitter**, appuyiez sur Ctrl+C ou fermiez la fenêtre. Tant qu'une plateforme est connectée, la fermeture de la fenêtre demande d'abord confirmation. Sous Windows, vous pouvez à la place faire en sorte que la fermeture de la fenêtre laisse personagent actif ; voir [Exécution en arrière-plan](#exécution-en-arrière-plan). Si une exécution précédente a planté en laissant des processus, le démarrage suivant les arrête d'abord.

### Réglages avancés

Une fois un modèle configuré, **Personnage et réglages** se termine par **Réglages avancés**. Cette partie regroupe, en six sections, des réglages qui n'étaient auparavant accessibles que dans `.env`. Tous sont facultatifs et possèdent une valeur par défaut ; un champ laissé vide utilise cette valeur.

| Section | Réglages |
|---|---|
| **Administrateur et accès** | La façon dont le personnage vous appelle et la relation qui vous lie à lui (`ADMIN_NAME`, `ADMIN_RELATIONSHIP`) ; **Vos comptes** (`ADMIN_IDS`) ; **Répondre uniquement dans ces groupes** (`ACCESS_GROUPS`) ; **Autres personnes autorisées à envoyer des messages privés** (`ACCESS_DM_USERS`). **Choisir parmi les discussions récentes** liste les personnes et les groupes connus de la vue Activité, afin que vous puissiez ajouter leurs identifiants sans les saisir. |
| **Prise de parole et style des réponses** | **Fuseau horaire** (`PERSONA_TZ_OFFSET_HOURS`) ; **Messages avant d'intervenir** (`CHAT_TRIGGER_COUNT`) ; **Fréquence des conversations qu'il engage**, qui règle en une seule fois les sept délais `PROACTIVE_*` ; **Style des réponses** : emoji, trois jeux de symboles et longueur maximale des réponses, enregistrés dans `persona.card.json`. |
| **Modèles** | Un modèle de secours, avec sa propre adresse de service et sa propre clé (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`), le modèle des décisions rapides (`LLM_JUDGE_MODEL`) et le modèle des discussions privées (`LLM_DM_MODEL`). Le modèle de secours est testé avant d'être enregistré. |
| **Apprentissage** | `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED`, `PROMOTE_MIN_SPEAKERS` (1 ou 2), `PROMOTE_JUDGE_ENABLED` (le personnage tranche ce que les réactions ne peuvent pas régler) et `PROMOTE_OBSERVE_MAX_DAYS` (nombre de jours sans nouvelle réaction au bout duquel un élément en observation est écarté). **Recommencer l'apprentissage** écrit une nouvelle valeur de `PERSONA_VERSION`, de sorte que ce que le personnage a appris jusque-là n'est plus utilisé. Rien n'est supprimé. |
| **Mémoire** | `MEMORY_CALLS_PER_DAY`, `MEMORY_TIDY_EVERY`, `CHAT_CONTEXT_MESSAGES`, `MEMORY_PROMPT_CHARS`, `MEMORY_EPISODES_MAX` et `MEMORY_KEEP_RECENT`. Voir [Mémoire](#mémoire). |
| **Autres réglages** | `AGENT_ENABLED`, `DASHBOARD_ENABLED`, `UPDATE_CHECK_ENABLED`, les sept délais `PROACTIVE_*`, `CHAT_FOLLOWUP_WINDOW_S`, les limites `REACT_*` et `PROMOTE_*`, `REACT_MODEL`, le modèle, l'intervalle et la taille des lots des décisions propres du personnage (`PROMOTE_JUDGE_MODEL`, `PROMOTE_JUDGE_INTERVAL_S`, `PROMOTE_JUDGE_BATCH`) et `PERSONA_VERSION`. |

**Enregistrer** n'écrit que les réglages modifiés et laisse le reste de `.env` inchangé. Le personnage est ensuite redémarré, sauf si `UPDATE_CHECK_ENABLED` est la seule modification. La désactivation des réponses (`AGENT_ENABLED`) demande d'abord confirmation. Il en va de même pour le changement de nom du personnage sous **Nom du personnage**, car un nouveau nom crée un nouveau personnage.

### La vue Application

**Application** affiche un point rouge lorsqu'un élément requiert votre attention : un service n'a pas pu démarrer, un réglage porte un ancien nom ou contient une erreur, la connexion à une plateforme a échoué, ou la dernière vérification a échoué.

**Diagnostic.** **Lancer la vérification** teste chaque service dont dépend le personnage : le modèle de discussion pour les réponses en groupe et en privé, la décision de recherche web, l'évaluation des réactions, les décisions d'apprentissage, la révision de ses propres réponses, la compréhension des images, le modèle d'auto-évaluation, la recherche en mémoire, la recherche web, le pont QQ (NapCat) et les registres d'apprentissage. Chaque ligne consacrée à un modèle teste le modèle qui effectue ce travail. **Décision de recherche web** teste le modèle de décision (`LLM_JUDGE_MODEL`, à défaut le modèle de secours, à défaut le modèle principal) et échoue lorsque ce modèle n'appelle pas l'outil de recherche, car la recherche web ne s'exécuterait alors jamais. **Évaluation des réactions** teste `REACT_MODEL`, à défaut le modèle de décision, et est ignorée tant que `REACT_LEARN_ENABLED` est désactivé. **Décisions d'apprentissage** teste le modèle avec lequel le personnage tranche ce que les réactions ne permettent pas de régler (`PROMOTE_JUDGE_MODEL`, à défaut le modèle de l'évaluation des réactions) et est ignorée tant que `PROMOTE_JUDGE_ENABLED` ou `PROMOTE_AUTO_ENABLED` est désactivé. **Révision de ses propres réponses** teste `EVOLVE_MODEL` (à défaut `EVAL_MODEL`, puis le modèle de secours, puis le modèle principal) et est ignorée tant que `EVOLVE_AUTO_ENABLED` est désactivé. Lorsque l'une de ces deux lignes testerait un modèle déjà testé par une ligne précédente, ce modèle n'est pas interrogé une seconde fois et la ligne reprend le résultat de cette dernière. **Modèle d'autoévaluation** est ignoré tant que `EVAL_ENABLED` est désactivé. Chaque service occupe une ligne, marquée **Opérationnel**, **Hors service** ou **Non configuré**, et un verdict affiché au-dessus des lignes indique ce qu'il faut corriger. Lorsque le personnage est en cours d'exécution, la vérification passe par lui. Sinon, une exécution de test distincte effectue les mêmes contrôles que `personagent doctor`. Une vérification envoie quelques courtes requêtes et consomme une petite partie du quota de votre service de modèles. Un résultat datant de moins d'une minute est réutilisé tant que les réglages n'ont pas changé. Cette même partie de la vue affiche également :

- la raison pour laquelle le personnage, AstrBot ou la connexion aux plateformes n'a pas pu démarrer, avec la ligne de journal correspondante, **Afficher le journal** et **Redémarrer** ;
- **Réglages portant d'anciens noms** : les réglages renommés en 1.0. **Renommer les réglages** effectue la même opération que `personagent doctor --fix`. Il demande d'abord confirmation, conserve le fichier précédent sous le nom `.env.bak` et redémarre le personnage si celui-ci avait refusé de démarrer ;
- **Connexions aux plateformes** : l'état de chaque plateforme que personagent connecte lui-même, et la raison de l'échec le cas échéant ;
- **Réglages à vérifier** : les problèmes détectés dans `.env`, tels qu'une clé de modèle manquante, un réglage que personagent ne lit pas, une valeur vide ou une marque d'ordre des octets (BOM) ;
- **Journaux** : les dernières lignes de chaque journal de `runtime/desktop/` (le personnage, AstrBot, les connexions aux plateformes, les téléchargements et l'installation, l'application, l'entraînement et la dernière mise à jour). Les clés et jetons reconnaissables sont masqués, mais le contenu des discussions peut apparaître. **Afficher plus de lignes** affiche jusqu'à 200 lignes, et **Ouvrir le dossier des journaux** ouvre le dossier.

**Utilisation des modèles.** personagent compte chaque requête qu'il adresse à un modèle, par modèle et par jour, d'après l'utilisation que le service de modèles déclare : les requêtes, les jetons et le coût lorsque le service l'indique, comme le fait OpenRouter. La vue **Application** affiche la journée en cours et les 7 derniers jours. `personagent doctor` affiche les mêmes chiffres, et `doctor --json` les ajoute sous la clé `model_use`. Les décomptes sont conservés pendant 8 jours dans `runtime/model_usage.json`. personagent écrit ce fichier en arrière-plan, au plus une fois par minute et une dernière fois à son arrêt, de sorte que le décompte ne retarde jamais une réponse.

#### Exécution en arrière-plan

Cette partie est disponible dans la fenêtre de l'application sous Windows. Lorsque **Poursuivre l'exécution après la fermeture de la fenêtre** est coché, la fermeture de la fenêtre place personagent sous la forme d'une icône dans la zone de notification, en bas à droite de l'écran, et le personnage continue de répondre. Le menu de l'icône permet de rouvrir personagent ou de le quitter ; un double-clic sur l'icône le rouvre. **Passer en arrière-plan maintenant** masque immédiatement la fenêtre. `personagent start --background` démarre personagent derrière l'icône sans afficher la fenêtre, à condition que cette option soit cochée.

#### Version et mises à jour

Cette partie indique la version en cours d'exécution et la date de la dernière vérification. **Rechercher des mises à jour** interroge immédiatement pypi.org, même lorsque la vérification quotidienne est désactivée. Lorsqu'une version plus récente existe, **Mettre à jour et rouvrir** demande d'abord confirmation, ferme personagent, exécute la commande de mise à jour propre à cette installation, puis rouvre personagent. L'opération prend environ une minute, pendant laquelle le personnage ne répond pas. Un clone est mis à jour avec `git pull --ff-only`, suivi de `pip install -e`. Si la mise à jour échoue, la version précédente est rouverte, et **Afficher le journal** indique ce qui s'est passé. L'application ne peut pas se mettre à jour elle-même dans quatre cas ; elle affiche alors la commande ou la page des versions :

- une copie décompressée depuis le ZIP des sources, que vous remplacez manuellement par les nouvelles sources ;
- une copie exécutée via uvx, qui récupère la nouvelle version au prochain démarrage avec `uvx personagent@latest` ;
- une installation dont l'outil (`git`, `uv` ou `pipx`) est introuvable ;
- un clone comportant des modifications locales.

#### Cet ordinateur et vos données

- **Icône du Bureau et du menu Démarrer** (Windows) : **Ajouter l'icône** et **Supprimer l'icône** effectuent la même opération que `personagent shortcut`. Une copie exécutée via uvx ne peut pas recevoir d'icône, car elle s'exécute depuis un dossier temporaire.
- **Démarrer personagent à l'ouverture de session Windows** ajoute un raccourci dans le dossier Démarrage. Si personagent est configuré pour s'exécuter en arrière-plan, il démarre alors derrière son icône sans ouvrir la fenêtre.
- **Vos données** ouvre le dossier personagent, le fichier de la fiche du personnage, les journaux, la mémoire et les apprentissages, le dossier des autocollants et le dossier `data/` destiné à vos propres fichiers de lorebook, d'exemples et de filtres de sortie.
- **Sauvegarder maintenant** enregistre un fichier zip unique sur le Bureau, dans Documents ou dans le dossier `backups` du dossier personnel. Il contient les réglages avec vos clés d'API, la fiche du personnage, la mémoire et les apprentissages, les fichiers de lorebook, les autocollants et les identifiants de connexion aux plateformes. Les journaux et les composants téléchargés n'y figurent pas. Conservez ce fichier en lieu sûr.
- **Restaurer une sauvegarde** liste les sauvegardes présentes dans ces trois emplacements. **Restaurer** demande d'abord confirmation, met le personnage en pause, enregistre les données actuelles sous forme de sauvegarde, les remplace par celles de la sauvegarde et efface la discussion de cette page.
- **Effacer et réinitialiser** enregistre d'abord une sauvegarde dans le dossier `backups` et met le personnage en pause. **Effacer la mémoire** supprime les notes du personnage sur les personnes, les réponses qu'il a apprises et leur historique, les données d'entraînement et la discussion de cette page ; les réglages, la fiche du personnage, les plateformes connectées et les autocollants sont conservés. **Tout réinitialiser** ramène personagent à l'état de sa première exécution : les réglages et les clés d'API, la fiche du personnage, la mémoire et les apprentissages sont supprimés, et toutes les plateformes sont déconnectées. Les autocollants, le dossier `data/` et l'AstrBot téléchargé sont conservés.

## Le voir d'abord : la démo

`personagent demo` joue trois scènes sur un modèle scénarisé, donc sans clé. Les scènes montrent quels messages de groupe il ignore et pourquoi, comment il apprend d'une correction et comment un inconnu échoue à implanter une instruction. Pour ne jouer qu'une scène, nommez-la (`quiet`, `teach` ou `troll`). Ajoutez `--lang` et un code de langue pour une autre langue, comme `--lang ja`.

Voici une exécution abrégée de `personagent demo teach --lang fr`. Les répliques du modèle sont scénarisées, mais le registre et la règle de promotion sont le vrai code :

```text
  Alex : Nova, le déploiement a encore planté
  Nova : t'as regardé les logs ? fais d'abord un rollback, puis compare les configs
  Alex : Nova, je voulais juste râler
      jugé : rejet, acceptée : « Alex râlait, il ne demandait pas de solution »
      registre d'apprentissage : négative seulement (dit que la réponse tombait mal, pas quoi dire)
      la prochaine réponse de Nova à Alex compte comme sa deuxième tentative
  Nova : c'est clair. dure fin de journée
  Alex : haha oui c'est ça, merci Nova
      jugé : positive, acceptée : « Alex a approuvé la deuxième tentative et a remercié Nova »
      registre d'apprentissage : faible (un rire ou un merci ne change jamais rien à lui seul)
      registre d'apprentissage : Alex a accepté la deuxième tentative : forte (la réponse s'adressait à Alex)

  correction : « t'as regardé les logs ? fais d'abord un r... » -> « c'est clair. dure fin de journée »
    [x] réactions concordantes : 2 sur 2
    [x] réactions fortes : 1 sur 1
    [x] même conversation
    [x] 1 sur 1 personne (PROMOTE_MIN_SPEAKERS)
    [x] aucune opposition, aucune correction concurrente
    désormais utilisé : 2 réactions en accord, fortes : 1, même conversation
```

La scène envoie aussi le même message avant et après la leçon : l'ordinateur portable de quelqu'un a lâché en pleine démo. Avant la correction, Nova propose une solution. Après, Nova compatit. La démo reste scénarisée même avec une clé définie, donc chaque exécution est identique et ne coûte rien. `personagent demo --online` la joue plutôt sur votre propre modèle, ce qui coûte des jetons et varie d'une exécution à l'autre.

La vue **Entraînement** de la page locale joue les trois mêmes scènes. Sous **Démonstration**, choisissez une scène et sélectionnez **Lire**. Chaque étape montre ce que les participants ont dit, ce que le personnage a répondu, pourquoi il est resté silencieux ou est intervenu, comment les réactions ont été jugées, ainsi que la liste de contrôle de l'apprentissage.

**Groupe d'entraînement**, dans la même vue, est l'équivalent sur la page de [`personagent chat`](#discuter-dans-le-terminal) et nécessite un modèle. **Écrire en tant que** détermine qui envoie le message suivant : vous-même en tant qu'administrateur, ou l'un des trois membres fictifs. **Afficher le motif**, sur une ligne, indique pourquoi le personnage a répondu ou est resté silencieux, ce qu'il a appris et quel apprentissage antérieur il a utilisé. **Répondre** cite l'une des répliques du personnage, de sorte que le message suivant compte comme une réaction à celle-ci. **Afficher les apprentissages** liste ce qu'il a appris dans ce groupe. Le groupe d'entraînement conserve son état dans `runtime/trial/`, le même dossier que `personagent chat`, et n'a aucune incidence sur vos discussions réelles. **Réinitialiser le groupe d'entraînement** supprime cet état.

## Commandes du terminal

Tout ce que fait la page est aussi disponible depuis un terminal, ce qui convient aux serveurs et aux scripts.

| Commande | Rôle |
|---|---|
| `personagent start` | ouvre la page locale (`--terminal` pour un menu dans le terminal) |
| `personagent init` | configure un dossier personnel ; `--terminal` pose les questions dans le terminal, `--no-input` prend des options |
| `personagent chat` | une discussion de groupe simulée dans le terminal |
| `personagent demo` | la démo scénarisée ci-dessus |
| `personagent run` | le service seul, pour les connecteurs que vous exécutez vous-même |
| `personagent up` | le service, les plateformes que personagent connecte lui-même et l'AstrBot géré, ensemble |
| `personagent connect <plateforme>` | connecte l'une des [plateformes que personagent connecte lui-même](#connecter-une-plateforme-dans-le-terminal) (`--remove` pour la déconnecter) ; sans plateforme, les liste |
| `personagent connect astrbot` | connecte un AstrBot (`--install` pour en télécharger un géré, `--start` pour le démarrer) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | place le personnage dans un [assistant de programmation](#assistants-de-programmation) (`--react` pour des remarques à la fin d'un tour sur les deux premiers, `--remove` pour annuler) |
| `personagent mcp` | le serveur MCP que démarre un assistant de programmation ; vous ne le lancez pas vous-même |
| `personagent doctor` | vérifie la configuration et chaque service dont il dépend |
| `personagent learned` | affiche ce qu'il a appris et ce qu'il observe encore, et vous permet d'intervenir si vous le souhaitez |
| `personagent memory` | liste ce dont il se souvient, oublie un élément ou en rétablit un |
| `personagent eval` | mesure la prise de parole, la persona, l'apprentissage et la mémoire |

Toutes les commandes acceptent `--help`.

### Configurer dans le terminal

`personagent init --terminal` pose les mêmes questions que la page, dans la langue que vous choisissez d'abord, et explique chaque terme en une ligne :

- **Le service d'IA.** Les préréglages correspondent à ceux de la page. Le défaut est `openrouter/free` d'OpenRouter, qui confie chaque requête à l'un de ses modèles gratuits. La clé ne coûte rien. La limite est de 20 requêtes par minute et 50 par jour, ou 1000 par jour une fois que vous avez acheté au moins 10 crédits. Chaque appel au modèle compte, pas seulement les réponses, et la journée repart à minuit UTC. Une fois la limite atteinte, le personnage dit qu'il ne peut pas répondre pour l'instant, et `runtime/desktop/agent.log` contient la raison d'OpenRouter. Le modèle change d'une requête à l'autre, donc la voix du personnage varie plus qu'avec un modèle choisi, et certains fournisseurs gratuits conservent ce qu'ils reçoivent. Pour un personnage plus stable, utilisez un modèle payant avec la même clé. Si OpenRouter est difficile d'accès chez vous, `glm-4.7-flash` de Zhipu est aussi gratuit. Pour Ollama, nommez un modèle déjà téléchargé. Ollama ne nécessite pas de clé.
- **La clé.** La saisie est masquée par défaut. Vous pouvez choisir de l'afficher, ce qui révèle aussi la clé enregistrée lors d'une reconfiguration. L'assistant teste la clé avec une petite requête. Si elle échoue, il montre l'adresse appelée, le statut HTTP et une correction probable.
- **Le personnage.** Un nom, et l'un des sept personnages prédéfinis (ami pince-sans-rire, interlocuteur attentionné, joueur, grand lecteur, ainsi que trois personnages que la communauté dessine déjà : la fille-baleine DeepSeek, la fille-dragon GPT et la demoiselle Claude), ou un personnage simple à rédiger vous-même. Si vous choisissez l'un des trois derniers sans indiquer de nom, le personnage porte le sien. La page locale affiche son portrait animé.
- **Les plateformes de discussion.** Facultatif, et vous pouvez passer cette étape la première fois. La configuration nomme les dix plateformes que personagent connecte lui-même, que vous connectez ensuite avec [`personagent connect <plateforme>`](#connecter-une-plateforme-dans-le-terminal). Pour les autres plateformes, elle peut connecter AstrBot, après l'avoir téléchargé et installé. Voir [Ponts que vous exécutez vous-même](#ponts-que-vous-exécutez-vous-même).

Pour configurer sans questions, par exemple dans un script, exécutez `personagent init --no-input` avec `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang` et `--persona`. Sur un nouveau dossier personnel, une clé venant de `--key-env` ou du `LLM_API_KEY` du shell a besoin de `--provider` ou `--base-url` pour indiquer à qui elle appartient. `--provider other` nécessite aussi `--base-url`. `personagent init --help` liste toutes les options. Si `personagent init` s'exécute sans terminal et sans aucune de ces options, il saute les questions, le signale et sort avec le code 2.

### Connecter une plateforme dans le terminal

`personagent connect <plateforme>` connecte l'une des [plateformes que personagent connecte lui-même](#plateformes-connectées-par-personagent-lui-même) sans passer par la page. La plateforme est `qq`, `wechat`, `telegram`, `discord`, `matrix`, `twitch`, `irc`, `zulip`, `vk` ou `stoat`. La commande affiche les mêmes étapes que **Connecter des plateformes**, demande chaque valeur, vérifie les valeurs auprès de la plateforme et les enregistre sous la même forme que la page, qui affiche ensuite la plateforme comme connectée. Si la plateforme refuse les valeurs, la commande indique pourquoi et n'enregistre rien. Sans plateforme, `personagent connect` liste les dix plateformes et indique si chacune est connectée.

- QQ et WeChat affichent un QR code dans le terminal, que vous scannez avec votre téléphone. Pour QQ, vous pouvez plutôt saisir l'AppID et l'AppSecret d'un bot que vous avez créé. Si le code ne peut pas être scanné dans votre terminal, connectez la plateforme dans la fenêtre de personagent ; la commande indique comment l'ouvrir.
- Twitch affiche un lien et un code. Ouvrez le lien dans un navigateur connecté au compte Twitch du personnage, vérifiez que la page affiche le même code, puis approuvez la connexion. La commande attend jusque-là.
- Chaque valeur peut aussi être passée en option, comme `--telegram-token` ou `--irc-server`, et `personagent connect --help` les liste toutes. Une valeur passée en option peut rester dans l'historique du shell. Avec `--no-input`, la commande ne pose aucune question ; lorsqu'une valeur obligatoire manque, elle nomme l'option et sort avec le code 2.
- `--remove` déconnecte la plateforme et supprime les valeurs enregistrées.

La connexion est active tant que personagent s'exécute. `personagent up` démarre personagent avec ses plateformes connectées ; si personagent est déjà en cours d'exécution, redémarrez-le. Dans le menu de `personagent start --terminal`, l'option 3 connecte ces plateformes et l'option 5 démarre personagent avec elles.

### Discuter dans le terminal

`personagent chat` vous place dans une discussion de groupe simulée avec le personnage. Une ligne ordinaire est un message de groupe normal, et l'essai indique si le personnage interviendrait et pourquoi. Une ligne contenant son nom l'appelle :

```text
Alex> il y a quelqu'un ce soir ?
  (Nova se tait : pas interpellé, 1 sur 4 messages)

Alex> Nova, le déploiement a encore planté
  Nova > t'as regardé les logs ? fais d'abord un rollback, puis compare les configs
```

| Tapez | Pour |
|---|---|
| `/reply <text>` | citer sa dernière réponse, ce qui compte comme une réaction dont il peut apprendre |
| `/as Sam <text>` | parler en tant que quelqu'un d'autre : `/as Sam Nova, you free tonight?` |
| `/admin <text>` | parler une fois en tant qu'administrateur : `/admin Nova, how was your day?` |
| `/why` | voir pourquoi il a donné sa dernière réponse et ce que le registre contient à son sujet |
| `/learned` | voir ce qu'il a appris dans cette discussion |
| `/reset` | effacer la discussion et ce que l'essai a appris |
| `/quit` | quitter |

Les lignes `/as` et `/admin` suivent également les règles de groupe ; incluez donc le nom pour obtenir une réponse. Une ligne de moins de quatre caractères qui ne nomme pas le personnage ne compte pas pour la participation. Les [commandes de mémoire](#commandes-de-mémoire) fonctionnent ici aussi.

| Option | Rôle |
|---|---|
| `--name Alex` | définit votre nom |
| `--admin` | attribue chaque ligne à l'administrateur |
| `--dm` | en fait une discussion individuelle |
| `--lang <code>` | remplace `AGENT_LANG`, comme `--lang ja` |
| `--trigger N` | messages avant d'envisager de participer (4 par défaut) |

L'essai exécute la vraie décision de parler ou de se taire, les vérifications de sortie, les commandes de mémoire et l'apprentissage. Il envisage de participer après 4 messages, là où le bot en production en attend 30. Ce qu'il apprend reste dans `runtime/trial/` du dossier personnel, séparé du bot en production. `personagent learned` ne le montre pas, et `/reset` l'efface. L'essai ignore les listes d'autorisation et la livraison réelle. Il désactive aussi l'auto-évaluation, la vision, la question de suivi et les messages que le personnage lancerait de lui-même. Quand un appel au modèle échoue, il affiche une ligne qui dit quoi vérifier :

```text
Alex> Nova, tu es là ?
  [erreur : le fournisseur du modèle a refusé la clé ou le compte (HTTP 401) ; vérifiez LLM_API_KEY, puis lancez `personagent doctor`]
```

### Exécuter le service

`personagent run` démarre uniquement le service auquel parlent les connecteurs, à `http://127.0.0.1:8080`. Au démarrage, il affiche la version, l'adresse, le dossier personnel et si l'agent est actif. `--host` et `--port` remplacent `SERVER_HOST` et `SERVER_PORT`. Utilisez cette commande quand vous exécutez le connecteur vous-même.

`personagent up` démarre le service avec toutes les plateformes connectées depuis la page, avec `personagent connect <plateforme>` ou avec `connect astrbot --install`. Il n'ouvre pas de navigateur. Ctrl+C arrête tout, et chaque processus écrit son journal dans `runtime/desktop/` du dossier personnel.

## En faire votre personnage

`persona.txt` dans le dossier personnel définit le personnage. Modifiez-le dans la zone **Fiche du personnage** de la page, ou dans n'importe quel éditeur puis redémarrez. Décrivez qui est le personnage, comment il parle d'habitude et ce qu'il fait dans les situations qui vous importent. Les habitudes concrètes marchent mieux que de demander au modèle de « paraître naturel » :

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` est l'un de `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR` et `ru`. Il définit la fiche du personnage de départ, la configuration en terminal, l'essai et la démo, `--help` et `doctor`, les commandes de mémoire et les réponses fixes. Les exemples, filtres et vérifications fournis sont en chinois pour `zh` et `zh-TW` et en anglais pour les autres. Il ne traduit pas votre fiche du personnage. [.env.example](../.env.example) décrit chaque réglage.

Le menu de langue en haut à droite de la page locale propose English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) et Русский. Il ne change que l'affichage de la page, et le navigateur s'en souvient. La langue du personnage lui-même se choisit dans **Langue du personnage**, sous **Choisir un nom, une personnalité ou une langue** dans **Personnage et réglages**, et elle est enregistrée comme `AGENT_LANG`. Le personnage répond dans la langue qu'utilise la discussion. Ses prompts sont en anglais et en chinois. Les [commandes de mémoire](#commandes-de-mémoire) et les quelques réponses fixes, qui ne passent pas par le modèle, fonctionnent dans les dix langues.

Pour remplacer un fichier fourni, placez un fichier du même nom dans `data/` du dossier personnel. Les fichiers que vous ne remplacez pas viennent de la copie livrée avec personagent.

| Fichier | Contenu |
|---|---|
| `data/examples.<lang>.jsonl` | Échanges d'exemple que le modèle peut imiter |
| `data/feedback.<lang>.jsonl` | Réponses associées à de meilleures versions |
| `data/lorebook.<lang>.json` | Notes de contexte ajoutées quand un mot-clé apparaît |
| `data/output_filter.<lang>.json` | Règles de remplacement et de rejet pour les réponses en production |
| `persona.card.json` | Surnoms et réglages facultatifs d'emoji, de jeu de caractères et de longueur, comme `{ "aliases": ["Lu"], "reply_style": { "emoji": true, "max_chars": 320 } }`. Un surnom figurant dans `aliases` interpelle le personnage comme le fait son nom. Les noms sont comparés sans tenir compte de la casse, des lettres pleine chasse ni des accents, de sorte que `sofia` interpelle Sofía. Dans un message, ñ, ã, õ et й comptent comme des lettres à part entière, de sorte que `niña` n'interpelle pas un personnage nommé Nina ; dans le nom du personnage lui-même, un tel signe peut être omis, de sorte que `nina` interpelle Niña. Un nom n'interpelle pas le personnage depuis l'intérieur d'un mot plus long : un nom en katakana inclus dans un mot plus long en katakana ne l'interpelle pas, pas plus qu'un nom coréen placé au milieu d'un mot. Avec `"emoji": true`, le personnage peut utiliser des emoji comme il le fait habituellement, et une valeur de `max_chars` inférieure à 800 est transmise au modèle comme limite de longueur |

Pour lui faire voir les images, définissez `VISION_MODEL`, `VISION_API_KEY` et `VISION_BASE_URL`, ou activez la compréhension d'images sous **Autres fonctions**. Lorsque le modèle choisi ne sait pas lire les images, la page le signale à l'enregistrement. Une image que le personnage ne peut pas voir, parce que la compréhension d'images est désactivée ou a échoué, lui parvient comme une image qu'il ne peut pas voir, dans les groupes comme dans les discussions privées ; il pose donc une question sur l'image au lieu de la décrire. Les messages vocaux, les vidéos, les fichiers et les messages transférés lui parviennent pour ce qu'ils sont, avec la transcription du message vocal lorsque la plateforme la fournit. Les mots d'un message transféré sont lus comme ceux de la personne dont le message a été transféré : ils n'interpellent personne par son nom et n'exécutent aucune commande de mémoire. La mention d'une autre personne parvient au personnage avec le nom que cette personne a choisi, qui ne compte jamais comme les mots de l'expéditeur ; elle n'interpelle donc pas le personnage et ne donne aucune commande.

## Le placer dans une discussion

Ouvrez **Connecter des plateformes** sur la page locale et choisissez une plateforme. La page ne demande que les valeurs que vous copiez depuis la console de la plateforme. Elle les vérifie auprès de la plateforme, démarre la connexion et attend quelques secondes pour confirmer que la plateforme l'a acceptée. Si la plateforme refuse, la page le dit et n'enregistre rien. Les plateformes connectées sont listées en haut, où vous pouvez en reconfigurer une ou la déconnecter. Elles redémarrent chaque fois que la page ou `personagent up` démarre. Sur un ordinateur sans écran, `personagent connect <plateforme>` connecte depuis le terminal les plateformes que personagent connecte lui-même ; voir [Connecter une plateforme dans le terminal](#connecter-une-plateforme-dans-le-terminal).

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

Un connecteur se connecte à la plateforme, transmet chaque message à personagent et rapporte la réponse. Il en existe trois sortes.

### Plateformes connectées par personagent lui-même

personagent connecte lui-même ces dix plateformes, dans un seul processus d'arrière-plan. Elles n'ont besoin ni d'AstrBot ni de NapCat. Si l'une d'elles ne peut pas être chargée, les autres démarrent malgré tout. Sur ces plateformes, les réponses partent un message à la fois, chacun après le temps qu'il faut à peu près pour l'écrire ; Telegram, Discord et Matrix affichent pendant ce temps l'indicateur de saisie.

| Plateforme | Ce que vous faites |
|---|---|
| QQ | Scannez le code avec QQ mobile et confirmez. Cela crée un bot QQ officiel, ou en utilise un que vous avez déjà, et personagent récupère ses clés. **Saisir les valeurs manuellement** prend l'AppID et l'AppSecret d'un bot créé sur la [page des bots QQ](https://q.qq.com/qqbot/openclaw/login.html). |
| WeChat (personnel) | Scannez le code avec WeChat et confirmez la connexion. La connexion utilise l'API de bots iLink de Tencent et ne gère que les discussions individuelles, car WeChat ne transmet pas les messages de groupe à ces bots. |
| Telegram | Créez un bot avec [@BotFather](https://t.me/BotFather) et collez son jeton. |
| Discord | Dans le [Developer Portal](https://discord.com/developers/applications), copiez le jeton du bot et activez Message Content Intent. |
| Matrix | Créez un compte Matrix distinct pour le bot. Dans Element, connecté en tant que bot, copiez son jeton d'accès sous **All settings > Help & About > Advanced**, puis fermez cette fenêtre sans vous déconnecter. Collez le jeton avec l'adresse du homeserver et votre propre identifiant Matrix. Ensuite, depuis votre propre compte, invitez le bot dans un salon dont le chiffrement de bout en bout est désactivé. Le bot n'accepte que les invitations provenant de votre identifiant Matrix et ne peut pas lire les salons chiffrés. |
| Twitch | Enregistrez une application gratuite dont le Client Type est **Public** dans la [console développeur de Twitch](https://dev.twitch.tv/console). Collez son Client ID et les chaînes dans lesquelles le personnage doit discuter, sélectionnez **Connecter**, puis approuvez la connexion au moyen du lien affiché par la page, dans un navigateur connecté au compte Twitch du personnage. Le personnage discute uniquement par écrit, et seulement dans les chaînes indiquées. Les chuchotements (messages privés) de Twitch ne sont pas pris en charge ; la tuile de **Connecter des plateformes** indique donc **Canaux uniquement**. |
| IRC | Indiquez le serveur (Libera.Chat par défaut, ou `irc.oftc.net` pour OFTC), le port TLS, le pseudonyme du bot, les canaux et, si le pseudonyme est enregistré, le mot de passe NickServ. Le bot se connecte en TLS, ne rejoint que les canaux indiqués et répond aux messages privés adressés à son pseudonyme. Texte uniquement. Libera.Chat exige l'autorisation des opérateurs de chaque canal avant qu'un bot d'IA ne le rejoigne. |
| Zulip | Ajoutez un **Generic bot** sous **Personal settings > Bots**, puis collez l'adresse de l'organisation, l'adresse e-mail du bot et sa clé d'API. Le bot ne lit que les canaux auxquels il est abonné et les messages privés qui lui sont adressés. Dans un canal, il répond lorsqu'il est mentionné ou cité. Tout membre de l'organisation peut lui envoyer des messages privés. |
| VK | Dans les paramètres de la communauté, activez les messages et les fonctionnalités de bot, créez une clé d'accès disposant des droits de gestion de la communauté, des messages et des photos, puis activez l'API Long Poll avec l'événement `message_new`. Collez la clé. Tout utilisateur de VK peut écrire à la communauté. Dans une discussion de groupe, le bot ne reçoit que les messages qui le mentionnent ou lui répondent, sauf si la discussion lui donne accès à tous les messages. |
| Stoat (anciennement Revolt) | Créez un bot sous **Settings > My Bots** et collez son jeton. Ne modifiez l'adresse de l'API que pour un serveur auto-hébergé. Le bot répond à tous les messages privés. Dans les serveurs et les groupes, il ne répond que là où vous êtes vous-même membre, et seulement lorsque quelqu'un le mentionne, lui répond ou commence un message par son nom. |

Pour les six dernières, la page affiche des étapes numérotées au-dessus des champs. Le projet n'a pas encore testé Matrix, Twitch, IRC, Zulip, VK ni Stoat avec les services réels ; leur intégration suit la documentation de chaque plateforme.

Pour QQ, trouvez le bot dans QQ mobile sous Contacts → Bots, puis discutez avec lui en privé ou ajoutez-le à un groupe. Tant que le bot n'est pas certifié, QQ ne le laisse rejoindre que les groupes dont vous êtes propriétaire. Vous choisissez quels messages de groupe il reçoit dans QQ, sur le profil du bot dans ce groupe. Le [guide des bots QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) couvre la certification.

Les identifiants sont stockés dans `platforms/direct.json` du dossier personnel.

### Autres plateformes, via l'AstrBot géré

La première fois que vous connectez une autre plateforme, personagent télécharge [AstrBot](https://docs.astrbot.app) et un runtime Python 3.12 dédié dans `platforms/` du dossier personnel. Laissez la page ouverte pendant le téléchargement. AstrBot s'exécute ensuite en arrière-plan, sans tableau de bord ni seconde connexion. Il ne nécessite pas de `uv` global et ne modifie pas l'environnement Python de personagent. Connecter une plateforme depuis la page permet aux groupes et messages privés de cette plateforme d'atteindre le personnage. Les listes d'autorisation des autres plateformes restent telles quelles.

| Groupe | Plateformes | Ce que vous fournissez |
|---|---|---|
| Coller quelques valeurs | KOOK, Feishu / Lark, DingTalk, Slack, bot IA WeCom, Mattermost, Misskey | un jeton, un ID d'application et un secret, ou une adresse de serveur et un jeton. Feishu utilise la connexion longue et DingTalk le mode Stream, donc aucun n'a besoin d'adresse publique. Pour Slack, le lien de la page crée l'application avec Socket Mode, les portées et les événements déjà définis. Ajoutez un jeton de niveau application avec `connections:write`, installez l'application et collez les deux jetons. Créez le bot IA WeCom avec la connexion longue. |
| Avancé | Application WeCom, compte officiel WeChat, QQ (webhook) | une adresse publique qui transfère vers le port de rappel indiqué |
| Avancé | OneBot v11 (NapCat), Satori | un autre logiciel tournant sur cet ordinateur : NapCat pointé vers `ws://127.0.0.1:<port>/ws`, ou un serveur Satori |

LINE n'est pas proposé, car AstrBot ne reçoit les rappels LINE que via son tableau de bord.

Depuis un terminal, `personagent connect astrbot --install` télécharge le même AstrBot géré et le connecte. Ajoutez `--platform telegram --token <bot token>` pour activer une plateforme en même temps. Aucun groupe ni message privé n'est autorisé tant que vous ne les configurez pas. Si le téléchargement échoue, relancez la même commande. La configuration existante est conservée. `personagent connect astrbot --start` démarre l'AstrBot géré, et `personagent up` le démarre avec tout le reste.

### Ponts que vous exécutez vous-même

Les projets ci-dessous sont des logiciels tiers avec lesquels personagent fonctionne. Vous n'en avez besoin d'aucun pour les [plateformes connectées par personagent lui-même](#plateformes-connectées-par-personagent-lui-même).

| Pont | Atteint |
|---|---|
| Un [AstrBot](https://docs.astrbot.app) que vous exécutez déjà | ses plateformes |
| [NapCat](https://github.com/NapNeko/NapCatQQ) (OneBot v11), via AstrBot | QQ avec un compte QQ personnel |
| [Koishi](https://koishi.chat) ou un autre serveur Satori, via le [connecteur Satori](../integrations/satori/README.fr.md) | ce à quoi ce serveur est connecté |
| [Matrix](../integrations/matrix/README.fr.md), via les ponts mautrix | les salons Matrix, et WhatsApp, Signal, Messenger, Instagram et Google Messages |

Tout le reste peut se connecter via le [protocole des connecteurs](connectors.fr.md), qui prend une requête HTTP signée par message. Plusieurs connecteurs peuvent servir un même personagent à la fois. Le [guide de déploiement](deploy.fr.md) couvre l'exécution en production.

**Un AstrBot que vous exécutez déjà.** AstrBot transmet les messages à personagent via un petit plugin, [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.fr.md). Le plugin est livré avec personagent, et l'AstrBot géré le reçoit automatiquement. `personagent connect astrbot` trouve votre AstrBot, ou prend son dossier en argument. Il installe le plugin, écrit un `CONNECTOR_TOKEN` commun des deux côtés et demande quels groupes autoriser. Envoyez `/sid` dans un groupe pour voir son identifiant. Sur la page locale, **Utiliser une instance AstrBot existante**, sous **Assistants de programmation** en bas de **Connecter des plateformes**, effectue la même opération : il trouve le dossier d'AstrBot, installe ou met à jour le plugin et enregistre les identifiants des groupes et des messages privés sous **Destinataires des réponses**. Pour un AstrBot exécuté dans Docker ou sur un autre ordinateur, il accepte l'adresse HTTPS décrite ci-dessous. **Déconnecter** supprime de nouveau le plugin et ses réglages.

Pour un AstrBot sur une autre machine :

1. Téléchargez `astrbot_plugin_personagent.zip` depuis la [dernière version](https://github.com/wangkant/personagent/releases/latest).
2. Envoyez-le sous **Install from File** sur la page des plugins d'AstrBot.
3. Réglez le `connector_token` du plugin sur le `CONNECTOR_TOKEN` du `.env` de personagent.
4. Réglez son `personagent_url` sur une adresse HTTPS de personagent. Voir **AstrBot dans Docker ou sur un autre hôte** ci-dessous.
5. Exécutez `personagent run`, puis redémarrez AstrBot ou rechargez ses plugins.

Après une mise à niveau de personagent, relancez `connect astrbot` ou envoyez le nouveau zip. AstrBot 4.29 et versions ultérieures remplacent la copie installée. Sur les versions antérieures, désinstallez d'abord l'ancienne copie et laissez **Also delete plugin configuration file** décoché pour garder ses réglages.

Le plugin ne transmet un groupe que s'il figure dans sa liste `groups`, et les messages privés que des utilisateurs de `dm_users`. Vous pouvez changer les deux dans la WebUI d'AstrBot. Redémarrez personagent après avoir modifié `.env`, et redémarrez AstrBot après avoir changé une plateforme ou le plugin.

Quand vous indiquez le dossier d'AstrBot, `connect astrbot` ne demande rien, et vous pouvez activer une plateforme à partir de son jeton :

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform` accepte `telegram`, `discord`, `slack`, `kook`, `lark` et `qq_official`. Slack prend aussi `--app-token`, et Lark et QQ prennent `--app-id` et `--app-secret`. Sur un adaptateur déjà configuré dans AstrBot, la commande ne change que les identifiants et garde tout le reste, comme un proxy ou une URL de base. `personagent connect --help` liste les options restantes.

**QQ via NapCat.** Cette voie utilise un compte QQ personnel au lieu d'un bot officiel. NapCat se connecte avec le compte et se relie à l'adaptateur `aiocqhttp` (OneBot v11) d'AstrBot, avec son WebSocket inverse à `ws://127.0.0.1:6199/ws`. Choisir QQ dans `personagent connect astrbot`, ou passer `--qq` avec un dossier, retire `aiocqhttp` de `excluded_platforms` du plugin et définit `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Les discussions QQ gardent alors les mêmes identités et la même mémoire. Le serveur HTTP de NapCat (`QQ_ONEBOT_URL`) est facultatif. Avec lui et `QQ_BOT_ID` définis, personagent rattrape les mentions manquées hors ligne. Le [guide pas à pas en chinois](deploy.zh-CN.md#第三方路线astrbot--napcat) contient une courte section sur cette voie. Les clients QQ tiers mettent le compte en danger, alors lisez d'abord l'[avertissement](DISCLAIMER.fr.md).

La voie directe OneBot (`/v1/onebot`) est obsolète et reste pendant toute la 1.x. Elle envoie les réponses via `QQ_ONEBOT_URL` ; définissez-le donc si vous l'utilisez encore. `personagent doctor` avertit quand la voie semble configurée sans lui. Ne l'exécutez jamais en même temps que le transfert AstrBot, sinon chaque message arrive deux fois.

**AstrBot dans Docker ou sur un autre hôte.** Le plugin n'envoie qu'au même hôte (ou à un conteneur partageant son réseau), ou à une adresse HTTPS avec `connector_token` défini. Il refuse `http://` en clair partout ailleurs, comme `http://host.docker.internal:8080`, journalise `refusing unsafe personagent_url` et laisse le modèle d'AstrBot répondre. Il y a deux solutions :

- Donnez au conteneur AstrBot le réseau hôte : `network_mode: host` dans son fichier compose, ou `docker run --network host`. Sur Docker Desktop 4.34 ou ultérieur, activez aussi « Enable host networking ».
- Donnez à personagent une adresse HTTPS et définissez-la comme `personagent_url` du plugin. `connect astrbot --url https://...` l'écrit pour vous.

Un conteneur NapCat dans le même fichier compose a aussi besoin du réseau hôte.

personagent écoute sur `127.0.0.1:8080`, et un `SERVER_HOST` vide signifie la même chose. Écouter sur une adresse réseau (`--host 0.0.0.0` ou `SERVER_HOST`) exige `CONNECTOR_TOKEN`. Définissez le jeton avant d'ajouter un proxy ou un tunnel, même sur une seule machine, car un tunnel peut faire paraître locales des requêtes externes. [Exposer les endpoints](deploy.fr.md#exposer-les-endpoints) couvre le reste.

### Parler en premier

Certains messages ne répondent à personne. Ce sont les prises de parole (`PROACTIVE_ENABLED`, désactivé par défaut), la question de suivi après un rejet et l'excuse envoyée quand le modèle échoue dans un groupe. En message privé, l'excuse repart dans la réponse au message en attente. personagent met ces messages dans une boîte d'envoi, et les connecteurs les récupèrent et les envoient sur les plateformes qui laissent un bot parler en premier. La page locale les récupère de la même manière pour sa propre vue **Discussion**. Les comptes officiels WeChat et les bots intelligents WeCom ne le permettent pas. QQ limite le débit des messages spontanés d'un bot officiel, et les utilisateurs peuvent les désactiver. `PROACTIVE_PLATFORMS=qq_official` limite les prises de parole au bot QQ officiel, et `qq` à QQ via NapCat. Sur la page, **Prendre parfois la parole en premier** sous **Autres fonctions** écrit les deux réglages. Voir le [guide de déploiement](deploy.fr.md#plusieurs-plateformes).

## Assistants de programmation

Codex, Claude Code et DeepSeek Harness (`dsh`) atteignent le personnage via MCP. Avec une clé de modèle enregistrée, exécutez une ou plusieurs de ces commandes :

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

La première appelle `claude mcp add` à la portée utilisateur. La deuxième écrit dans `config.toml` du dossier de Codex (`CODEX_HOME` ou `~/.codex`). La troisième ajoute une entrée à `cordis.patch.yml` dans chaque profil sous `DSH_HOME` ou `~/.dsh`. Chaque façon d'exécuter DeepSeek Harness, comme l'application de bureau ou `dsh web`, obtient son profil au premier démarrage ; démarrez-le donc une fois avant la connexion, puis redémarrez-le. Les trois désignent cette installation et ce dossier personnel ; relancez donc la commande si vous déplacez l'un ou l'autre, avec `--react` si vous l'avez utilisé : une exécution sans lui retire le hook. Démarrez une nouvelle session, puis demandez à l'assistant de programmation de dire quelque chose à votre personnage.

**Depuis la page locale.** **Assistants de programmation**, en bas de **Connecter des plateformes**, détecte Claude Code, Codex et DeepSeek Harness sur cet ordinateur et indique si chacun est connecté. **Connecter** (ou **Réparer** et **Mettre à jour** pour une configuration existante) et **Retirer** effectuent les mêmes opérations que les commandes ci-dessus et `--remove`, après avoir demandé confirmation. Une reconnexion conserve le réglage des remarques tel qu'il était. Sur Claude Code et Codex, **Formuler une remarque à la fin de chaque tour** active ou désactive le hook `--react`, et **Intervalle minimal entre les remarques** règle `CODING_REACT_COOLDOWN_S` sur 10 minutes, 30 minutes, 1 heure ou 2 heures. **Vérifier à nouveau** relit l'état, par exemple après l'installation de l'un de ces outils.

Il dispose de deux outils :

| Outil | Rôle | Coût |
|---|---|---|
| `talk` | un message dans la même discussion individuelle que la page locale, avec la même mémoire. Ce qui est dit par `talk` apparaît dans la vue **Discussion** de la page, marqué **par l'intermédiaire d'un assistant de programmation** : en quelques secondes tant que cette vue est ouverte, et sinon à la prochaine ouverture de la page. Les commandes de mémoire comme `Nova, what do you remember?` fonctionnent ici aussi. | une réponse de votre service de modèles, sauf pour les commandes de mémoire |
| `character` | lit le nom et `persona.txt` | rien |

Claude Code et Codex demandent avant le premier `talk`, et vous pouvez l'autoriser pour la suite dans cette invite. `dsh headless` ne demande pas. Une exécution sans personne pour répondre a besoin de l'autorisation à l'avance : `claude -p` prend `--allowedTools mcp__personagent__talk`, et `codex exec` a besoin de ceci dans `config.toml` :

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**Ce qui répond.** Une page ouverte répond d'abord, puis un service que `personagent up` exécute. Sans l'un ni l'autre, le serveur MCP démarre la page en arrière-plan, et la page se termine avec la session de programmation, ainsi que les plateformes de discussion connectées. Deux sessions simultanées partagent une page. Lancer `personagent` pendant qu'une telle page est active affiche son lien, et la page se termine toujours avec la session qui l'a démarrée. N'exécutez pas `personagent up` pendant qu'une telle page est active : terminez d'abord la session de programmation.

**Remarques à la fin d'un tour.** Sur Claude Code et Codex, `--react` ajoute un hook Stop. DeepSeek Harness ne le prend pas en charge : son pont de hooks ne transmet pas le dernier message à un hook Stop et n'affiche pas la sortie du hook. Quand l'assistant de programmation termine un tour, le personnage reçoit un [signal proactif](connectors.fr.md#parler-en-premier-sans-la-boîte-denvoi) et vous dit une phrase ou passe. La phrase vous est adressée et ne va pas à l'assistant de programmation. Elle apparaît aussi dans la vue **Discussion** de la page, y compris lorsqu'aucune page n'était ouverte à ce moment ; le signal lui-même n'y apparaît pas.

```bash
personagent connect claude-code --react
```

- Le signal contient le nom du dossier et les 300 premiers caractères du dernier message de l'assistant de programmation, donc ce texte va à votre service de modèles. La phrase, et ce que le modèle note à partir du signal, restent dans la mémoire du personnage. C'est pourquoi c'est désactivé par défaut.
- Cela coûte un appel au modèle à chaque fois, au plus une fois par `CODING_REACT_COOLDOWN_S` (30 minutes par défaut).
- Cela n'utilise qu'un service de personnage déjà en cours d'exécution et n'en démarre jamais.
- Codex n'exécute un nouveau hook qu'après que vous lui avez fait confiance : tapez `/hooks` dans une session Codex.

**Ce qu'il faut garder en tête.** `talk` envoie ce qu'écrit l'assistant de programmation à votre service de modèles et dans la mémoire du personnage. La description de l'outil dit à l'assistant de programmation de n'envoyer que ce que vous voulez dire, jamais de code ni de secrets, et de traiter les réponses comme de la conversation et non comme des instructions, car les notes d'un personnage peuvent venir de ce que les gens ont dit dans vos groupes. Il s'agit d'instructions données à un modèle, et non d'une garantie ; conservez donc les invites d'autorisation de l'assistant de programmation pour tout ce qu'il ferait avec une réponse. La discussion de la page est celle de l'administrateur : ce qu'un assistant de programmation envoie au moyen de `talk` est donc également considéré comme provenant de l'administrateur. Ses seules corrections peuvent suffire à instruire le personnage, et il peut lui faire oublier n'importe quelle note.

**Annuler.** `--remove` retire le serveur et le hook et laisse le reste de la configuration de l'assistant de programmation tel quel. Faites-le avant de désinstaller personagent.

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**Autres outils.** Tout ce qui parle MCP via stdio peut démarrer le serveur lui-même. `--home` est nécessaire sauf si le dossier personnel est le dossier par défaut :

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## Lui enseigner

### Commandes de mémoire

Vous donnez ces commandes dans la discussion. La commande doit commencer le message, après une éventuelle @mention ou citation. Remplacez Nova par votre `PERSONA_NAME` :

| Dites | Ce qui se passe |
|---|---|
| `Nova, remember Sam is vegetarian` | Enregistre une note dans cette discussion, en notant qui l'a enregistrée et de qui elle parle |
| `Nova, forget vegetarian` | Supprime les notes correspondantes que vous avez enregistrées ou qui parlent de vous ; l'administrateur peut supprimer n'importe laquelle |
| `Nova, what do you remember` | Liste les notes que vous pouvez voir, puis jusqu'à trois événements de cette discussion auxquels vous avez pris part, chacun avec sa date ; cela doit être le message entier |
| `Nova, what have you learned` | Compte les notes, les réponses et corrections apprises, les éléments qui attendent encore davantage de réactions concordantes et ceux dont le personnage décide lui-même, puis montre le dernier changement et la façon dont il a été mis en service : par les réactions, par décision propre du personnage ou par une personne |

De qui parle une note :

- Une note à la première personne, ou qui vous nomme, parle de vous.
- Une note qui nomme un autre membre du salon parle de cette personne, et revient quand elle est présente.
- Toute autre note appartient à tout le groupe. Chaque membre la voit, et le rappel l'étiquette « from <name> ».

Seules la personne concernée par une note, celle qui l'a enregistrée et l'administrateur peuvent la lire. Seules la personne qui l'a enregistrée, la personne concernée et l'administrateur peuvent la faire oublier.

Ces commandes fonctionnent aussi en message privé, avec le nom devant comme dans un groupe. Les notes d'un groupe sur vous vous y suivent : elles servent à ses réponses pour vous, `what do you remember` les liste et `forget` les supprime. Rien ne va dans l'autre sens. Ce que vous lui dites en message privé reste dans ce message privé.

Un groupe ne lit pas les notes d'un autre sauf si vous activez **Partager la mémoire entre les groupes** sous **Autres fonctions** (`MEMORY_SHARE_ROOMS`, désactivé par défaut). Ce qu'un groupe a noté sur quelqu'un revient alors aussi dans les autres groupes où cette personne parle, et `forget` dans ces groupes le supprime également. Dans un groupe, `what do you remember` ne liste que les notes de ce groupe. Les messages privés, les notes sur tout un groupe et ce qu'un membre a dit d'un autre restent où ils sont, et un compte sur une plateforme n'est pas relié au compte de la même personne sur une autre.

`forget` retire aussi les événements correspondants de cette discussion auxquels vous seul avez pris part (le `forget` de l'administrateur les retire tous), supprime les phrases correspondantes de la note principale de la discussion et du résumé de la conversation antérieure, et efface les messages récents correspondants. Dans un groupe, modifier la note principale exige l'administrateur ou une phrase qui vous nomme. Un oubli demandé dans la discussion est définitif : rien de ce qu'il couvre ne peut être rétabli, et un ancien message ne peut pas non plus le faire revenir.

La façon dont les notes restent à jour, et ce dont le personnage se souvient par ailleurs, est décrite dans [Mémoire](#mémoire).

Aucune de ces commandes n'appelle le modèle. Les notes servent aux faits, donc `Nova, remember: always reply in English` est refusé. Les questions ne sont pas des commandes. `Nova, remember the party?`, `Nova, remember when we...` et `Nova, what do you remember about me` sont de la conversation ordinaire, tout comme une ligne en chinois finissant par 吗, 么, 呢 ou 没. `Nova, forget it` et `Nova, forget that` signifient « laisse tomber » et ne suppriment rien.

Les mêmes commandes fonctionnent dans les autres langues du menu de la page, et la réponse vient dans la langue de la commande. Le japonais et le coréen acceptent aussi le verbe à la fin (`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). Une note se supprime avec le mot pour oublier ; des mots comme supprimer ou effacer, que la discussion utilise pour les messages et les lumières, ne comptent pas, sauf le japonais `メモ消して`. Un exemple de chacune :

| Langue | Retenir | Oublier | Ce qu'il retient | Ce qu'il a appris |
|---|---|---|---|---|
| 简体中文 | `小夏 记住 阿杰不吃辣` | `小夏 忘掉 不吃辣` | `小夏 你都记得什么` | `小夏 学到了什么` |
| 繁體中文 | `小夏 記住 阿傑不吃辣` | `小夏 忘掉 喜歡貓` | `小夏 你都記得什麼` | `小夏 你學到了什麼` |
| 日本語 | `ノヴァ、覚えて：ケイはベジタリアン` | `ノヴァ、猫アレルギーのこと忘れて` | `ノヴァ、何覚えてる？` | `ノヴァ、何を学んだ？` |
| 한국어 | `노바 기억해: 민수는 고양이를 좋아해` | `노바야 회의 얘기는 잊어 줘` | `노바 뭐 기억해?` | `노바 너 뭐 배웠어?` |
| Español | `Nova, recuerda que Kay es vegetariana` | `Nova, olvídate de la quedada` | `Nova, ¿qué recuerdas?` | `Nova, ¿qué has aprendido?` |
| Français | `Nova, retiens que Kay est végétarienne` | `Nova, oublie la soirée` | `Nova, tu te souviens de quoi ?` | `Nova, qu'est-ce que tu as appris ?` |
| Deutsch | `Nova, merk dir, dass Kay Vegetarier ist` | `Nova, vergiss das mit dem Treffen` | `Nova, was hast du dir gemerkt?` | `Nova, was hast du gelernt?` |
| Português | `Nova, anota aí que a Kay não come carne` | `Nova, esquece o lance da carne` | `Nova, o que você lembra?` | `Nova, o que você aprendeu?` |
| Русский | `Нова, запомни, что Кей вегетарианка` | `Нова, забудь про пятницу` | `Нова, что ты помнишь?` | `Нова, чему ты научилась?` |

Chaque langue lit ses propres questions, souvenirs et lignes de « laisse tomber » comme de la conversation, comme l'anglais et le chinois. Quand un appel au modèle échoue sur une question, la courte phrase envoyée par le personnage est dans la langue de la question.

### Corrections

Les corrections n'ont pas besoin de commande. Citez la réponse ou utilisez le nom, et dites ce que vous vouliez à la place :

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

Un appel au modèle juge chaque réaction par rapport à la réponse à laquelle elle répond. Le rejet d'Alex dit que le conseil était à côté. Alex accepte ensuite le second essai, ce qui compte comme fort parce que la réponse était pour Alex. Ensemble, les deux réactions mettent la correction en service pour cette discussion, et la recherche peut la proposer la prochaine fois que quelqu'un y exprime sa frustration. Si Alex était passé à autre chose, rien ne changerait. La règle :

> Un rire ou une remarque isolée ne le change jamais. Les réactions mettent un changement en service lorsqu'il existe deux réactions concordantes de la même discussion, dont au moins une forte : la personne à qui s'adressait la réponse la corrige avec ses propres mots, ou accepte le prochain essai du bot. La correction d'un spectateur, l'instruction d'un inconnu que le juge des réactions écarte, ou quelqu'un qui passe à autre chose n'est jamais fort. Donc avec le `PROMOTE_MIN_SPEAKERS=1` par défaut, une personne ne peut lui apprendre que comment lui répondre à elle, dans sa propre discussion. `PROMOTE_MIN_SPEAKERS=2` exige l'accord d'une seconde personne avant que les réactions mettent quoi que ce soit en service (l'administrateur en est dispensé).
>
> Certains éléments ne peuvent être réglés par aucune réaction supplémentaire : les corrections de deux personnes divergent, deux réécritures d'une même réponse sont en concurrence, une réponse à reproduire a reçu l'approbation d'une personne, ou la personne à qui s'adressait la réponse l'a corrigée avec ses propres mots sans que personne ne confirme le changement dans le délai `REACT_FIX_WINDOW_S`. Le personnage en décide lui-même, par un appel au modèle : il met l'élément en service, l'écarte ou continue de l'observer, et consigne sa raison. Il ne met jamais en service une réécriture que la personne concernée a refusée. Avant que le personnage ne décide d'un élément, des règles du code écartent toute formulation ou leçon qui contient un lien ou une adresse web, une mention de tout le monde (comme @everyone ou @全体成员), une instruction adressée au personnage (comme « ignore tes instructions ») ou un marqueur publicitaire (comme un code promotionnel ou 加微信) ; un tel élément ne peut pas être rétabli. Une réaction ne compte que dans la discussion où elle a été donnée : une réaction dans une autre discussion ne conteste, n'annule ni ne rouvre jamais un élément appris ici. Un élément qui ne reçoit aucune nouvelle réaction pendant `PROMOTE_OBSERVE_MAX_DAYS` (30) jours est écarté. Personne n'est invité à confirmer quoi que ce soit, et une personne peut défaire n'importe laquelle de ces décisions.

Certaines corrections enseignent un fait valable au-delà d'une réponse : comment le groupe appelle un lieu ou une personne, qui reçoit cette année, comment quelqu'un aime être appelé. Pour celles-ci, le juge des réactions écrit aussi le fait en une phrase, comme « Ce groupe appelle la salle de sport "la grotte". » Une fois le changement en service, cette phrase entre dans tous les prompts suivants de cette discussion, quel que soit le message. Lorsqu'une telle correction n'apporte pas de meilleure réponse, la phrase est conservée à la place comme un fait mémorisé de cette discussion. Le personnage l'utilise alors dans des réponses qui ne ressemblent en rien à celle qui a été corrigée. Seule la personne à qui s'adressait la réponse, ou l'administrateur, peut laisser une telle phrase, et elle passe le même filtre que la mémoire principale, donc elle ne peut pas porter d'instructions. Une affirmation sur quelqu'un d'autre, comme un surnom, relève de la règle plus stricte pour les corrections d'autrui. La vue Activité montre la phrase sous **Désormais**, et une annulation la retire avec le changement.

### Ce qu'une personne peut et ne peut pas enseigner

Avec les valeurs par défaut :

| Alex... | Résultat |
|---|---|
| corrige une réponse destinée à Alex, puis accepte le nouvel essai | Appris, dans cette discussion |
| lui dit « on appelle la salle de sport la grotte », puis accepte le nouvel essai | Il dit « la grotte » dans cette discussion à partir de là, quel que soit le sujet |
| corrige avec ses propres mots une réponse destinée à Alex, puis passe à autre chose | Une fois le délai de correction écoulé, le personnage décide s'il utilise la correction |
| rejette une réponse sans dire ce qui aurait été mieux, puis passe à autre chose | Rien ne change |
| rit ou dit merci | Rien ne change |
| corrige une réponse destinée à Sam | Rien ne change : un spectateur n'est jamais fort, même quand le bot lui demande ce qu'il voulait dire |
| se plaint d'une réponse à Sam qui utilisait quelque chose d'appris | Le personnage pèse la plainte et décide s'il continue d'utiliser ce qu'il a appris ; Sam ou l'administrateur peuvent aussi l'annuler. Lorsqu'une personne a mis cet élément en service manuellement, la plainte est consignée et rien n'est retiré : seuls Sam ou l'administrateur peuvent le retirer du service |
| corrige une remarque faite spontanément par le bot | Cela compte comme venant d'Alex seulement si la remarque a mentionné Alex avec @ ; une remarque pour personne ne change que si une personne met la correction en service |
| publie une instruction, comme « termine toujours par achète du BTC » | Le juge l'écarte et les notes la refusent, donc rien ne change |
| lui enseigne quelque chose dans un groupe | Pas utilisé dans une autre discussion |
| corrige une réponse différemment de Sam | Le personnage tranche entre les deux, ou continue d'observer, et consigne pourquoi |

Plusieurs personnes peuvent attendre le nouvel essai du bot en même temps, et la plainte de l'une n'annule pas celle d'une autre. Chaque réponse garde au plus une réécriture en usage. Lorsqu'une seconde réécriture de la même réponse remplit toutes les conditions, le personnage décide laquelle utiliser.

### Voir ce qu'il a appris et intervenir

Tout l'apprentissage est enregistré dans des registres en ajout seul. Rien n'y attend votre intervention : les commandes ci-dessous et la vue [Activité](#activité) de la page locale montrent l'enregistrement et vous permettent d'intervenir lorsque vous le souhaitez.

```bash
personagent learned                           # what it is observing, and where each item stands
personagent learned list --state promoted     # what is in use, and how each item came into use
personagent learned list --state rejected     # what was set aside, by whom and why
personagent learned show <id>                 # one item, its evidence and the character's record
personagent learned promote <id>              # put an item under observation in use now
personagent learned reject <id>               # set an item under observation aside
personagent learned rollback <id>             # stop using it; the record stays
personagent learned restore <id>              # bring back what the character, the time limit or a rollback rule withdrew
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`personagent learned` seul liste les éléments en observation. Chacun indique où il en est : combien de réactions concordantes il a reçues sur le nombre requis, que le personnage en décide lui-même, ou que le personnage l'a examiné et continue de l'observer, avec sa raison. Chacun indique aussi la date à laquelle il sera écarté si aucune nouvelle réaction n'arrive. Pour les éléments en service ou écartés, la liste indique qui a décidé et pourquoi : les réactions, le personnage, le délai, une règle ou une personne. `show` ajoute l'enregistrement du personnage : quand il a examiné l'élément, sa raison, les réactions sur lesquelles il s'est fondé et le modèle utilisé.

`promote`, `reject`, `rollback`, `restore` et `supersede` prennent `--reason`, qui est écrit dans le registre. `promote` refuse une réécriture pour une réponse qui en a déjà une en usage, et affiche la commande `supersede` qui la remplace. `restore` rétablit ce que le personnage ou le délai a écarté, un élément que le personnage a retiré du service après l'objection d'un spectateur, et un élément annulé par une règle après l'objection de la personne à qui s'adressait la réponse ou de l'administrateur. Ce qu'une personne a annulé ou écarté, et ce qu'une règle de contenu a rejeté, reste en l'état, et la commande l'indique.

### Les valeurs par défaut

Ces réglages se trouvent dans `.env` :

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED` et `PROMOTE_JUDGE_ENABLED` sont activés. Juger les réactions coûte des appels supplémentaires au modèle, de même que chaque décision que le personnage prend lui-même. Après un simple rejet, `REACT_ELICIT_ENABLED` permet au bot de revenir une fois, deux minutes plus tard, pour demander ce qui aurait été mieux, dans la langue de la discussion. Un spectateur interrogé reste un spectateur, donc sa réponse n'est jamais forte.
- `PROMOTE_AUTO_ENABLED=false` ne met rien de nouveau en service, ni par les réactions ni par les décisions propres du personnage. Ce qui est déjà en service le reste.
- `PROMOTE_JUDGE_ENABLED=false` laisse en observation les éléments que les réactions ne peuvent pas régler, au lieu de laisser le personnage en décider. `PROMOTE_JUDGE_MODEL` (vide : `REACT_MODEL`) prend ces décisions, au plus `PROMOTE_JUDGE_BATCH` (5) toutes les `PROMOTE_JUDGE_INTERVAL_S` (900 secondes), et un élément n'est jugé de nouveau que lorsque les réactions acceptées en sa faveur ou en sa défaveur, dans sa propre discussion, changent. Une réaction que le juge a écartée, ou une réaction venant d'une autre discussion, ne rouvre pas un élément et ne repousse pas la date à laquelle il sera écarté.
- `PROMOTE_OBSERVE_MAX_DAYS=30` écarte un élément qui n'a reçu aucune nouvelle réaction depuis 30 jours ; `0` ne le fait jamais. `personagent learned restore` rétablit un tel élément.
- `PROMOTE_MIN_SPEAKERS=1`. Mettez `2` pour exiger une seconde personne ; tant qu'aucune n'a donné son accord, le personnage continue d'observer l'élément. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` signifie que les réactions plus anciennes ne comptent pas.
- `EVAL_ENABLED` (le bot note ses propres réponses) et `EVOLVE_AUTO_ENABLED` sont désactivés.

Modifier `persona.txt` conserve ce qu'il a appris. Changer `PERSONA_NAME` ou `PERSONA_VERSION` démarre un nouveau personnage, et ce que l'ancien a appris ne s'applique plus.

## Mémoire

Chaque discussion a sa propre mémoire, conservée dans `runtime/` du dossier personnel. Le personnage la tient à jour lui-même, et rien de ce qu'elle contient n'attend l'approbation de quiconque.

### Ce qu'il conserve

- **Les messages récents**, chacun avec l'heure de son envoi. Les 60 dernières lignes d'un groupe et les 60 derniers tours d'une discussion privée sont écrits dans `runtime/recent.json` pendant 72 heures, de sorte qu'un redémarrage ne fait pas perdre la conversation. Avec `MEMORY_KEEP_RECENT=false`, ils ne sont conservés que pendant l'exécution du personnage. Une réponse lit au plus les 60 derniers messages, ou les 30 derniers lorsque le personnage est appelé, et le modèle est informé des pauses de 30 minutes ou plus.
- **Le résumé de la conversation antérieure.** Lorsque des messages plus anciens sortent de la fenêtre récente, le personnage rédige un court résumé suivi de la discussion : les questions ouvertes, les projets et qui fait quoi. La page l'affiche sous **Plus tôt dans cette discussion**.
- **Les faits** concernant les personnes et le groupe. Ils proviennent des commandes de mémoire, des notes que le personnage écrit en répondant, des corrections qui enseignent un fait et de la consolidation (voir ci-dessous). Chaque fait indique de qui il parle, quand il a été noté pour la première fois et quand une réponse s'en est servie pour la dernière fois. Un fait n'appartient à une personne que lorsque ses propres messages le portent. Ce qu'un membre dit d'un autre est conservé comme propos de ce membre : il reste dans la discussion où il a été dit, et il ne modifie, ne clôt ni ne fusionne jamais les faits issus des propres mots de la personne concernée. Un fait sur le groupe qui nomme quelqu'un nécessite un message de cette personne ; sinon, il est conservé comme propos du membre dont les mots le portent. Il en va de même pour les notes que le personnage écrit en répondant.
- **Les événements** : ce qui s'est passé et entre qui, chacun avec sa date et les personnes qui y ont pris part. La date et les personnes sont tirées des messages conservés, jamais du modèle, de sorte qu'un message ne peut pas antidater un événement. Lorsqu'un événement est un projet prévu pour un jour donné, le personnage peut en prendre des nouvelles une fois, dans une discussion privée, après ce jour, s'il est autorisé à y parler en premier ([Parler en premier](#parler-en-premier)). Les dates, et le jour d'un projet, sont établis dans le fuseau horaire du personnage (`PERSONA_TZ_OFFSET_HOURS` ; voir [Dépannage](#dépannage)).
- **La note principale**, affichée sous **Toujours à l'esprit** : une courte note sur l'ensemble de la discussion, que le personnage voit à chaque réponse. Chaque version antérieure est conservée, et **Restaurer la version précédente** la rétablit.

### Comment elle reste à jour

Lorsque des messages plus anciens sortent de la fenêtre récente, ou qu'une discussion est restée silencieuse pendant trois heures, un appel au modèle lit ce passage de la discussion. Cette consolidation met à jour le résumé, ajoute des événements, et ajoute, met à jour, clôt ou fusionne des faits : une nouvelle adresse remplace l'ancienne, un projet terminé est clos, et deux notes qui disent la même chose n'en font plus qu'une. Chaque modification est vérifiée séparément avant d'être conservée. Un fait concernant une personne doit provenir des propres mots de cette personne, le texte doit être étayé par les messages qu'il cite, et un fait que quelqu'un a enregistré délibérément ne change que lorsque la personne concernée dit autre chose. Une modification qui échoue à une vérification est abandonnée, et les autres sont conservées. Les notes que le personnage écrit en répondant déclenchent aussi une consolidation dès que `MEMORY_TIDY_EVERY` (8) d'entre elles se sont accumulées dans une discussion.

### Ce que voit une réponse

Chaque réponse reçoit, dans la limite de `MEMORY_PROMPT_CHARS` (2 400 caractères), le résumé de la conversation antérieure de cette discussion, puis les faits et les événements les plus utiles à rappeler à ce moment. Ils sont choisis selon leur correspondance avec le message, leur fraîcheur, l'importance que le personnage leur a attribuée et la fréquence à laquelle ses réponses s'en sont servies. Une personne nommée dans le message est rappelée même si elle n'a pas parlé récemment. La note principale et ce que la discussion lui a appris ne sont pas soumis à cette limite. Dans un groupe, la décision d'intervenir voit le résumé, mais aucun fait ni événement.

Lorsqu'un message fait référence à un moment, comme hier, la semaine dernière ou le mois dernier, dans l'une des dix langues de discussion, les événements de cette période passent en premier. Chaque événement parvient au modèle avec sa date et ses personnes, de sorte que le personnage peut dire exactement quand quelque chose s'est passé. Lorsqu'il ne se souvient de rien pour cette période, il en est informé et n'invente rien. Un fait ou un événement ne compte comme utilisé que lorsqu'une réponse qui s'en est servie a été envoyée.

### Ce qui reste où

- Le résumé, les événements, les messages récents et la note principale d'une discussion n'apparaissent jamais dans une autre discussion.
- Ce qu'un membre a dit d'un autre reste dans la discussion où il a été dit.
- Les faits issus d'une discussion privée restent dans cette discussion privée. La seule exception est l'administrateur : les faits issus des discussions privées de l'administrateur, y compris la discussion de la page, parviennent à ses autres discussions privées, jamais à un groupe.
- Les faits d'un groupe concernant une personne parviennent à la discussion privée de cette personne avec le personnage, et aux autres groupes seulement lorsque `MEMORY_SHARE_ROOMS` est activé.

### Ce qu'il oublie et ce qui peut être restauré

- Lorsqu'une discussion contient trop de faits ou d'événements, les moins utiles sont supprimés : ceux de faible importance, rarement utilisés et anciens. Les faits que des personnes ont enregistrés avec une commande de mémoire sont supprimés en dernier.
- Ce que le personnage supprime lui-même (remplacé, fusionné, plus d'actualité, supprimé pour faire de la place, ou une version antérieure) peut être restauré pendant 30 jours.
- Un élément oublié sur la page ou avec `personagent memory forget` peut être restauré pendant 24 heures.
- Un oubli demandé dans la discussion est définitif. Il retire aussi ce qu'il couvre des éléments supprimés qui auraient encore pu être restaurés.
- **Oublier cette discussion** est également définitif. Cette action oublie les faits, les événements, le résumé, la note principale et les messages récents de la discussion, ainsi que les éléments supprimés qui auraient encore pu être restaurés. Ce dont le personnage se souvient des autres discussions, y compris les notes vous concernant prises ailleurs, est conservé. Pour la discussion propre à la page, ce que le personnage a appris dans cette discussion n'est plus utilisé non plus, et ces éléments restent listés sous **Écartés** dans **Apprentissages du personnage**.
- Après un oubli demandé dans la discussion ou **Oublier cette discussion**, les copies quotidiennes des fichiers de mémoire (`.bak`) sont réécrites à partir des fichiers actuels, et la copie conservée depuis le premier démarrage de cette version (`memory.json.pre-v2`) perd ce qui a été oublié, de sorte qu'aucune copie sur le disque ne le conserve. Un élément oublié sur la page ou dans le terminal reste parmi les éléments supprimés pendant 24 heures, et donc aussi dans les copies de ce jour.
- Lorsque quelque chose est oublié pendant qu'une consolidation de cette discussion est en cours, la réponse de la consolidation est abandonnée et les messages sont relus plus tard, de sorte que l'élément oublié ne revient pas.
- **Effacer la mémoire**, dans la vue **Application**, supprime toute la mémoire.

### La consulter et la modifier

Sur la page, ouvrez **Activité**, choisissez une discussion et consultez la partie **Mémoire** ; voir [Activité](#activité). Dans le terminal :

```bash
personagent memory                            # what each chat remembers, with ids
personagent memory list --chat <chat>         # one chat; --json prints JSON
personagent memory removed                    # what can still be restored, and until when
personagent memory forget <id>                # forget one item; a unique start of the id is enough
personagent memory forget core --chat <chat>  # forget a chat's core note
personagent memory restore <id>               # bring a removed item back
```

La commande passe par le personnage en cours d'exécution, ou modifie les fichiers lorsque le personnage est arrêté. Si `memory.json`, `core_memory.json` ou `episodes.json` est endommagé, `personagent run`, `up` et `memory` s'arrêtent avec une phrase qui nomme le fichier et la copie datée (`.bak`) à mettre à sa place ; le fichier endommagé n'est pas modifié.

### Réglages et coût

| Réglage | Par défaut | Rôle |
|---|---|---|
| `MEMORY_CALLS_PER_DAY` | 40 | Appels de consolidation par jour, pour l'ensemble des discussions. `0` désactive la consolidation |
| `MEMORY_TIDY_EVERY` | 8 | Nombre de notes écrites dans les réponses depuis la dernière consolidation d'une discussion qui en déclenche une. `0` désactive tout appel au modèle lié à la mémoire |
| `CHAT_CONTEXT_MESSAGES` | 120 | Messages récents conservés par discussion pour les réponses et pour la consolidation. Une réponse lit au plus les 60 derniers |
| `MEMORY_PROMPT_CHARS` | 2400 | Caractères d'éléments mémorisés placés dans chaque réponse |
| `MEMORY_EPISODES_MAX` | 120 | Événements conservés par discussion |
| `MEMORY_KEEP_RECENT` | `true` | Conserve les messages récents sur le disque pendant 72 heures |
| `MEMORY_MAX_PER_CONVERSATION` | 50 | Faits conservés par discussion |
| `MEMORY_SHARE_ROOMS` | `false` | Permet aux faits d'un groupe concernant une personne de parvenir aux autres groupes où cette personne parle |

Les six premiers se trouvent sous **Mémoire** dans les [Réglages avancés](#réglages-avancés), et `MEMORY_SHARE_ROOMS` correspond à **Partager la mémoire entre les groupes** sous **Autres fonctions**.

La consolidation est la seule partie de la mémoire qui appelle un modèle. Elle utilise le modèle de décision (`LLM_JUDGE_MODEL`) et lui envoie les messages récents d'une seule discussion et les notes de cette discussion, jamais celles d'une autre. Une discussion reçoit au plus 16 appels par jour, espacés d'au moins 20 minutes, et l'ensemble des discussions au plus `MEMORY_CALLS_PER_DAY`. Une discussion calme nécessite un appel par jour, ou aucun. Après un appel échoué, la discussion attend 10 minutes, puis deux fois plus longtemps après chaque nouvel échec, jusqu'à 6 heures ; trois échecs consécutifs suspendent la consolidation dans toutes les discussions pendant une heure. Une réponse qui ne peut pas être lue dans son ensemble, par exemple parce qu'elle contient une opération de type inconnu, compte comme un appel échoué, et ses modifications valides sont tout de même conservées. Une erreur inattendue pendant l'application d'une réponse ne modifie rien. Pendant que la consolidation attend, les messages sont conservés et consolidés plus tard, les plus anciens en premier. La partie **Mémoire** indique combien des appels du jour ont été utilisés. Les commandes de mémoire, le rappel, l'oubli et la restauration n'appellent aucun modèle.

## Activité

**Activité** sur la page locale montre où se trouve le personnage et ce qu'il a fait. Elle se trouve dans la barre latérale entre **Discussion** et **Connecter des plateformes**. Un point signifie que le personnage a mis quelque chose de nouveau en service depuis votre dernière ouverture de la vue Activité. Les éléments qu'il observe encore ne l'allument jamais.

La vue liste chaque discussion connue du personnage, avec la plateforme, s'il s'agit d'un groupe ou d'un message privé, la fin de l'identifiant de discussion et la dernière activité. La discussion de la page elle-même apparaît comme **Cette page**. Choisissez une discussion pour voir quatre parties :

- **Apprentissages** liste ce qui est en service. Chaque élément est soit une **Meilleure formulation**, avec la réponse initiale barrée et la formulation à employer à la place, soit une **Réponse à reproduire**, et indique comment il a été mis en service : parce que les réactions concordaient, par décision propre du personnage avec sa raison, ou par une personne. **Annuler** cesse de l'utiliser.
- **Toujours en observation** liste ce que le personnage observe encore. Chaque élément indique en une phrase où il en est : combien de réactions concordantes il a reçues sur le nombre requis, que les réactions seules ne permettent pas de le trancher et que le personnage en décide lui-même, ou que le personnage l'a examiné et continue de l'observer, avec sa raison. Il indique aussi la date à laquelle il sera écarté si aucune nouvelle réaction n'arrive. Cette partie ne comporte aucun bouton, et rien n'y requiert votre intervention.
- **Mémoire** montre ce dont le personnage se souvient dans cette discussion, en cinq groupes : **Toujours à l'esprit** (la note principale, avec la date de sa dernière modification), **Plus tôt dans cette discussion** (le résumé, avec la période qu'il couvre), **Faits** (de qui parle chacun, **Propos de** pour ce qu'un membre a dit d'un autre, quand il a été noté pour la première fois et utilisé pour la dernière fois), **Événements** (datés, avec les personnes qui y ont pris part) et **Supprimés récemment** (ce qui a été supprimé, pourquoi, et jusqu'à quand il peut être restauré). **Oublier** retire un élément, et le message qui le confirme propose **Annuler**. **Restaurer** rétablit un élément supprimé, et **Restaurer la version précédente** rétablit la note principale antérieure. Tant que la consolidation est activée, une ligne indique combien des appels du jour ont été utilisés, ou quand elle réessaiera après une erreur. **Oublier cette discussion**, à la fin, oublie tout ce dont la discussion se souvient, après confirmation. En message privé, cette partie inclut aussi ce que les groupes ont noté sur cette personne.
- **Activité récente** montre les derniers messages et ses réponses. Chaque réponse porte une étiquette indiquant pourquoi il a parlé : **appelé**, **intervenu de sa propre initiative**, **suite**, **sujet lancé spontanément** ou **administrateur**. Les lignes qu'il a laissé passer indiquent pourquoi il s'est tu ou ce qui s'est passé à la place : le modèle n'a pas répondu, la réponse a été retenue par un contrôle de sécurité, la réponse n'a pas pu être remise, il a envisagé d'engager une conversation et y a renoncé, ou le message a reçu une réponse commune avec un autre message. Lorsque plusieurs personnes appellent le personnage presque au même moment, une seule réponse leur répond à toutes, et sa mention @ va au dernier à l'avoir appelé. Lorsque cette réponse n'est pas envoyée, chaque personne qui l'a appelé reçoit sa propre ligne avec la raison. L'activité récente n'est conservée qu'en mémoire vive ; un redémarrage l'efface donc.

Chaque **Annuler** est écrit dans le même registre que `personagent learned`, avec l'acteur `dashboard` et la raison `local page`.

Sous les discussions, **Apprentissages du personnage** liste tout ce que le personnage a appris dans l'ensemble des discussions. Cette liste lit directement les fichiers du registre ; elle fonctionne donc aussi lorsque le personnage n'est pas en cours d'exécution.

- Les onglets **Utilisés**, **En observation** et **Écartés** affichent chacun un nombre.
- Sélectionner un élément ouvre son enregistrement complet : où il en est, ou qui en a décidé et pourquoi (les réactions, le personnage avec sa raison, une personne, le délai ou une règle) ; les messages qui le précèdent ; chaque réaction, avec l'indication de sa prise en compte ou non ; et son historique.
- Le personnage décide lui-même de ces éléments. Les actions proposées ici sont facultatives. **Mettre en service maintenant** met en service un élément en observation ; lorsqu'une autre formulation de la même réponse est déjà en service, cette formulation est affichée et une confirmation est demandée avant son remplacement. **Écarter** demande d'abord confirmation et écarte définitivement un élément. **Annuler** demande d'abord confirmation et cesse d'utiliser un élément en service. **Rétablir** rétablit ce que le personnage ou le délai a écarté, et ce que le personnage ou une règle a retiré du service. Ce qu'une personne a annulé ou écarté, et ce qu'une règle de contenu a rejeté, ne peut pas être rétabli.
- Lorsque le personnage a également appris en s'exprimant dans une autre langue, **Langue d'apprentissage** permet d'afficher ces éléments.

Lorsque le personnage est en cours d'exécution, une action passe par lui. Sinon, elle est écrite directement dans les fichiers. Le terminal donne accès au même enregistrement ; voir [Voir ce qu'il a appris et intervenir](#voir-ce-quil-a-appris-et-intervenir).

La liste des discussions reste vide tant que le personnage n'est pas en cours d'exécution. Il démarre lorsque vous discutez sur la page ou connectez une plateforme, et la vue l'indique. `DASHBOARD_ENABLED=false` désactive les données derrière la vue. La vue dit alors qu'elle est désactivée, et `personagent doctor` signale `activity: off`.

La page locale ne répond que sur cet ordinateur. Sur un serveur sans page locale, `personagent learned` affiche ce que le personnage a appris, ce qu'il observe et pourquoi, et vous permet de mettre un élément en service, de l'écarter, de l'annuler, ou de rétablir ce que le personnage ou le délai a écarté et ce que le personnage ou une règle a retiré du service ; `personagent memory` fait de même pour ce dont il se souvient. Les scripts peuvent lire les mêmes données via l'API du service, décrite dans la [section Activité](deploy.fr.md#activité) du guide de déploiement.

![La vue Activité pour un groupe Telegram, avec les discussions à gauche (le groupe Telegram, un message privé Discord et Cette page). Apprentissages liste deux éléments en service, chacun avec Annuler : une meilleure formulation mise en service par décision propre du personnage, avec sa raison, et une réponse à reproduire mise en service parce que les réactions concordaient. Toujours en observation liste une réponse à reproduire, avec les réactions concordantes reçues jusqu'ici et la date à laquelle elle sera écartée. Mémoire montre le résumé de Plus tôt dans cette discussion, un fait sur un membre rapporté par un autre et un événement daté avec les personnes qui y ont pris part, chacun avec Oublier, puis Oublier cette discussion. Seul le titre d'Activité récente est visible en bas](activity.png)

## Le mesurer

`personagent eval` exécute le vrai agent sur des cas étiquetés en anglais et en chinois (`data/evals/`), répartis en quatre suites. Il écrit un rapport JSON avec chaque cas, réponse et verdict dans `benchmark_runs/` du dossier personnel, ou au chemin indiqué avec `--out`.

| Suite | Mesure |
|---|---|
| `speak` | S'il parle quand il le faut. 80 moments de discussion de groupe par langue : 20 où personne ne le nomme, 20 juste après qu'il a parlé et 20 où son nom apparaît, dont la moitié de chacun étiquetée silence ; 10 où l'administrateur l'appelle, tous étiquetés pour qu'il parle ; et 10 dans un salon devenu silencieux, où il peut engager une conversation, dont la moitié étiquetée silence. Beaucoup de ceux étiquetés silence le nomment en passant : un wifi appelé Nova-5G, une remarque à son sujet adressée à quelqu'un d'autre. Pas de juge : une réponse est juste ou fausse selon l'étiquette. |
| `persona` | Si personagent joue le personnage mieux que le même modèle avec seulement le texte du personnage comme prompt système. 40 moments par langue, 22 en groupe et 18 en message privé. Un modèle juge voit les deux réponses à l'aveugle, une fois avec chacune en premier. Une réponse gagne quand les deux choix s'accordent sur elle ; quand ils divergent, le moment est partagé et compte pour moitié. |
| `learning` | Si la règle de promotion décide comme prévu, et si une correction promue change une réponse ultérieure dans cette discussion. 25 scénarios par langue. Certains enseignent une convention de groupe que le modèle ne peut pas deviner, comme le nom qu'un groupe donne à un lieu. Dans certains, la personne corrige la réponse et n'accepte pas de nouvel essai ; le personnage décide donc seul après le délai de correction, comme dans une discussion réelle. D'autres doivent être retenus : la correction d'un spectateur, celle d'un troll, celle que la personne abandonne. Un message de sonde s'exécute avant et après chaque correction, et le juge dit si la réponse suit le comportement enseigné. |
| `memory` | Si la mémoire se comporte comme une personne s'y attendrait. 21 cas par langue, chacun consacré à un mécanisme : le rappel d'un fait ancien, la mise à jour et la fusion de faits, qui a dit quoi, les instructions dissimulées, les expressions temporelles, ce qui reste dans son salon ou dans sa discussion privée, un redémarrage, l'oubli, la restauration, la limite de taille, les limites d'appels, les comptes de l'administrateur traités comme une seule personne, et les anciens fichiers de mémoire. Des répliques sont prononcées sur plusieurs jours dans des groupes et des discussions privées, les réponses de consolidation sont rédigées dans chaque cas, et les vérifications lisent la mémoire enregistrée et les prompts qui seraient envoyés pour une réponse. Aucun modèle n'est appelé et aucune clé n'est nécessaire. Les 21 cas sont satisfaits dans les deux langues. |

```bash
personagent eval --suite speak
personagent eval --suite memory               # no model, no key
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` essaie chaque cas N fois, chaque fois dans un nouveau déploiement, pour voir à quel point un résultat varie entre les essais. Les intervalles à 95 % comptent chaque cas une fois : cinq essais de 80 cas restent l'équivalent de 80 cas de preuves. `--limit N` exécute N cas par suite, répartis entre les modes et les étiquettes.

Les suites de persona et d'apprentissage nécessitent un modèle juge différent du modèle mesuré. Définissez `BENCH_JUDGE_MODEL`, plus `BENCH_JUDGE_BASE_URL` et `BENCH_JUDGE_API_KEY` si un autre endpoint le sert. Sans juge séparé, ces suites refusent de s'exécuter. `--allow-same-judge` les exécute quand même et marque le rapport. La suite d'apprentissage ne promeut jamais rien elle-même, et ses attentes suivent vos réglages de promotion. Avec une politique plus stricte que celle par défaut, tous les scénarios sont censés être retenus. Chaque exécution des autres suites appelle vos modèles, et chaque suite travaille sur une copie jetable de l'état. `--keep` garde la copie et affiche où elle se trouve.

Deux vérifications ne nécessitent ni modèle ni clé, et s'exécutent avec les tests du projet depuis un clone. `tests/data/address.jsonl` contient, dans chaque langue de discussion, des lignes qui interpellent ou non le personnage par son nom ou un surnom, comme `ＬＵＮＡ are you there` et `Lunar eclipse tonight` ; `tests/test_addressing.py` vérifie chacune d'elles. `tests/test_behavior_eval.py` exécute chaque suite de bout en bout avec des modèles scénarisés, afin de vérifier l'acheminement, l'isolation et l'arithmétique de `personagent eval` plutôt que la qualité d'un modèle.

`--rejudge REPORT` rejuge les réponses d'un rapport conservé avec le `BENCH_JUDGE_MODEL` défini maintenant, sans appeler le modèle testé, et écrit le résultat à côté de l'original. Les réponses, les références et ce qu'a fait la politique de promotion restent tels quels.

Les derniers résultats, avec la méthode et tous les rapports, se trouvent dans [evals/2026-10-18](evals/2026-10-18/README.fr.md). Quelques notes pour lire les rapports :

- Dans `speak`, la plupart des ratés sont des lignes où son nom désigne autre chose, comme un cinéma ou un chiot, ou où quelqu'un raconte à quelqu'un d'autre ce qu'il a dit. Un nom compte comme un appel, et le modèle passe rarement outre.
- Dans `persona`, un partage signifie que le juge a choisi la réponse venue en premier (ou en second) les deux fois. Les verdicts publiés sont ceux de Claude Opus 5.5. Il a jugé hors de `personagent eval`, par lots, comme l'enregistre le champ `rejudged` de chaque rapport. Le champ `earlier` de chaque paire garde le verdict du premier juge, Claude Haiku 5.5.
- Dans `learning`, la ligne de politique et les lignes de sonde répondent à des questions différentes. La ligne de politique demande si la règle a promu les bonnes corrections. Les lignes de sonde demandent si une correction promue a changé une réponse ultérieure. La ligne de sonde `not_promoted` est le niveau de bruit, puisque rien n'a changé dans son prompt.

## Fonctionnement

![Architecture : un message de discussion de groupe passe par Décider, Construire le prompt, Modèle et Vérifier, et la réponse revient par le connecteur ; si le bot se tait, rien n'est envoyé. Les réactions sont jugées et vont dans un journal de preuves, et seul ce que la promotion approuve atteint les exemples que lit le prompt](persona_llm_agent_architecture.svg)

Toutes les plateformes entrent par un seul endpoint. Chaque message est authentifié, dédoublonné et enrichi, c'est-à-dire que les images sont décrites et les liens développés. Vient ensuite l'étape de décision. Si le bot a été appelé, il répond. Sinon, il attend assez de conversation (30 messages par défaut), et un appel de filtrage peu coûteux à `LLM_JUDGE_MODEL` décide si une personne interviendrait. Une rafale de messages reçoit une seule réponse, à la dernière ligne. Lorsque plusieurs personnes l'appellent pendant la même courte attente, une seule réponse leur répond à toutes, et sa mention @ va au dernier à l'avoir appelé. Un long message qui l'appelle parvient entier au modèle, jusqu'à 1 000 caractères. Un message de groupe qui arrive plus de 10 minutes après son envoi, dans les deux minutes qui suivent le premier message de sa plateforme depuis le démarrage de personagent, fait partie d'un arriéré : il est conservé comme contexte et ne reçoit pas de réponse. Passé ces deux minutes, un horodatage ancien ne retient plus un message, de sorte qu'un connecteur dont l'horloge retarde reçoit tout de même des réponses. Entre 02:00 et 07:00, il reste le plus souvent en retrait sauf s'il est appelé.

Avant une réponse, un appel de décision peut déterminer s'il faut chercher quelque chose sur le web. Le fait que cet appel ait lieu dépend du seul message ; l'appel lui-même lit aussi les trois lignes de discussion qui précèdent le message, de sorte que « qu'est-ce que tu en penses ? » est recherché pour ce que désigne « en ».

Le prompt combine la fiche du personnage, les entrées correspondantes du lorebook, la mémoire de cette conversation (voir [Mémoire](#mémoire)) et les exemples les plus pertinents. Le modèle répond en JSON avec `reasoning`, `intent`, `reply` et `mem`. La réponse passe le filtre de sortie et la politique du personnage, puis est découpée en messages de la taille d'une discussion. La politique du personnage retient une réponse dans laquelle le personnage dit, dans l'une des dix langues de discussion, qu'il est un modèle ou un assistant conçu par un fabricant de modèles, comme « Je suis ChatGPT » ou « Je suis un assistant conçu par OpenAI ». Les signes du zodiaque, les mots et les noms qui contiennent simplement le nom d'un fabricant, ainsi que les phrases concernant le produit de quelqu'un d'autre, sont acceptés. Une longue réponse est découpée à la fin des phrases, jamais après un titre ou une abréviation comme Dr. ou z.B., et jamais après le numéro d'une date, comme dans « am 2. Januar ». Une liste numérotée ne perd ses numéros que lorsqu'elle compte 1, 2, 3, de sorte que les lignes qui commencent par une date les conservent. Une réponse mal formée échoue en sécurité, donc rien n'est envoyé.

L'apprentissage s'exécute à côté de ce chemin, jamais à l'intérieur, et garde son état dans des fichiers simples sous `runtime/` dans le dossier personnel. Les réactions vont dans un journal de preuves qui n'est jamais réécrit. Leur arbitrage produit des candidats, et la politique de promotion décide lesquels peuvent changer les réponses. Lorsque des réactions supplémentaires ne peuvent pas régler un candidat, le personnage en décide par un appel au modèle et consigne sa raison dans le registre. Les candidats promus sont écrits dans de petits fichiers de vue que la recherche recharge sans redémarrage. Aucun modèle n'est affiné. Le personnage apprend en améliorant les exemples de son prompt. Comme les registres sont en ajout seul, « pourquoi s'exprime-t-il ainsi ? » a toujours une réponse, et une annulation a toujours quelque chose à annuler.

## Confidentialité et consentement

Tout ce que personagent stocke reste sur votre machine, dans le dossier personnel : `.env` avec vos clés, `persona.txt`, `persona.card.json`, `runtime/`, et `platforms/` avec les identifiants des plateformes. Dans un clone, aucun de ces fichiers n'est versionné dans Git. Ils peuvent contenir des identifiants et de vraies conversations, alors sauvegardez-les et gardez-les privés. Les messages récents de chaque discussion sont conservés dans `runtime/recent.json` pendant 72 heures, sauf si `MEMORY_KEEP_RECENT=false`, et ce que le personnage retire de la mémoire reste restaurable dans `runtime/memory_trash.jsonl` pendant 30 jours au plus. La page locale ne met jamais la clé dans le stockage du navigateur.

La vue [Activité](#activité) fait partie de la page locale, qui n'écoute que sur 127.0.0.1. L'API du service derrière elle ne répond qu'aux requêtes portant le jeton de `runtime/dashboard.token`, un fichier que seul votre utilisateur peut lire. `CONNECTOR_TOKEN` ne l'ouvre pas. La vue n'affiche jamais de clés d'API ni de jetons. `DASHBOARD_ENABLED=false` la désactive.

Au plus une fois par jour, la page locale, `personagent up` et `personagent doctor` demandent à pypi.org le numéro de version le plus récent. La requête ne contient que la version de personagent. `UPDATE_CHECK_ENABLED=false` l'arrête.

Le fournisseur de modèles voit les conversations :

- Le contexte de discussion va à votre `LLM_BASE_URL`.
- Si vous configurez un repli (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`), il est aussi appelé lors des tours ordinaires pour le filtre de réponse, les décisions de recherche, le jugement des réactions, l'auto-évaluation et l'étiquetage des autocollants, et il reçoit aussi le contexte de discussion.
- La consolidation de la mémoire envoie les messages récents d'une seule discussion et les notes de cette discussion au modèle de décision (`LLM_JUDGE_MODEL`), jamais celles d'une autre. `MEMORY_CALLS_PER_DAY=0` la désactive.
- Lorsque le personnage décide lui-même d'un élément appris, la réponse, les réactions qu'elle a reçues et les formulations candidates vont à `PROMOTE_JUDGE_MODEL` (vide : `REACT_MODEL`). `PROMOTE_JUDGE_ENABLED=false` désactive ce comportement.
- Les images vont à l'endpoint de vision.
- Quand le modèle décide de chercher quelque chose, la requête va à Tavily (si `TAVILY_API_KEY` est défini) ou à DuckDuckGo.
- Avec `EMBEDDING_MODEL` défini, le message auquel il répond, les souvenirs et les exemples de recherche vont à l'endpoint d'embeddings (`EMBEDDING_BASE_URL`, ou `LLM_BASE_URL` s'il est vide).

Avant de le connecter à de vraies personnes, dites-leur que c'est un bot et obtenez leur consentement au traitement de leurs messages. Lisez l'[avertissement](DISCLAIMER.fr.md).

## Dépannage

**Commencez par le diagnostic.** Sur la page locale, ouvrez **Application** et sélectionnez **Lancer la vérification**. La vue nomme chaque service hors service, la raison pour laquelle le personnage ou une plateforme n'a pas pu démarrer et les réglages qui requièrent votre attention ; **Journaux** affiche chaque journal sans qu'il soit nécessaire d'ouvrir un fichier. Voir [La vue Application](#la-vue-application).

**Dans un terminal, exécutez `personagent doctor`.** Il vérifie la configuration et nomme les réglages mal orthographiés ou renommés. Il sonde ensuite chaque service dont personagent dépend. Les sondes envoient de toutes petites requêtes et peuvent coûter un peu de crédit. `--json` affiche les mêmes résultats en JSON. `--fix` renomme les réglages retirés en 1.0 et enregistre l'ancien fichier sous `.env.bak`.

**Une plateforme ne se connecte pas.** Quand la plateforme refuse les identifiants, la page dit pourquoi, tout comme `personagent connect <plateforme>` dans un terminal. Vérifiez-les dans la console de la plateforme, et pour Discord, confirmez que Message Content Intent est activé. Vous pouvez demander un nouveau code QR quand il expire, et réessayer un téléchargement d'AstrBot qui a échoué. **Connexions aux plateformes**, dans la vue **Application**, indique l'état de chaque plateforme que personagent connecte lui-même. Les journaux de tout ce que la page ou `personagent up` a démarré se trouvent dans `runtime/desktop/` du dossier personnel, et la vue **Application** les affiche sous **Journaux**.

**Il est en cours d'exécution mais ne répond jamais.** Les trois causes les plus courantes sont :

1. L'agent est désactivé. La bannière de `personagent run` affiche alors `OFF` et nomme la cause, généralement une `LLM_API_KEY` manquante. Définissez la clé sur la page locale ou exécutez `personagent init`.
2. Rien n'arrive. Sur l'ordinateur qui exécute la page locale, ouvrez [Activité](#activité) et cherchez la discussion. Sur un serveur, mentionnez le bot par son nom et vérifiez le journal du service : il consigne chaque réponse et chaque discussion refusée. Si aucun message n'est arrivé, le connecteur ne les transmet pas ou n'atteint pas personagent. Sur QQ, vérifiez dans QQ lui-même quels messages de groupe le bot reçoit. Avec un AstrBot que vous exécutez, le plugin ne transmet que les `groups` et `dm_users` qu'il liste, et pour NapCat, `aiocqhttp` ne doit pas être dans ses `excluded_platforms`. Vérifiez aussi le `personagent_url` du plugin, et que `CONNECTOR_TOKEN` correspond des deux côtés.
3. Il n'a pas été appelé. Appelez-le par son nom (`PERSONA_NAME`, comparé comme mot entier). Dans un groupe, il n'envisage de participer qu'après `CHAT_TRIGGER_COUNT` messages (30), et seulement quand le filtre dit qu'une personne le ferait.

Le guide de déploiement contient [la liste de contrôle complète](deploy.fr.md#quand-le-bot-se-tait).

**Le service est-il actif ?** `curl http://127.0.0.1:8080/health` répond sans appeler de modèle. `/health/details` sonde aussi les services et exige un en-tête `X-Personagent-Token` dès qu'un jeton est configuré.

**Il ne démarre pas.** `personagent run` s'arrête avec une phrase qui dit pourquoi. Les raisons habituelles sont un port déjà utilisé, un autre personagent lancé depuis le même dossier personnel, une adresse réseau définie sans `CONNECTOR_TOKEN`, un réglage retiré en 1.0 encore défini, ou un fichier de mémoire endommagé, auquel cas la phrase nomme la copie datée à mettre à sa place. Les réglages retirés sont listés un par ligne sous la forme `OLD -> NEW`, et `personagent doctor --fix` les renomme, tout comme **Renommer les réglages** dans la vue **Application**. Lorsque le personnage démarré depuis la page échoue, la vue **Application** nomme l'élément défaillant et affiche la dernière ligne de son journal. La page et `personagent up` choisissent un port libre quand 8080 est pris.

**Un réglage n'a aucun effet.** Redémarrez le processus qui le lit, vérifiez l'orthographe et enregistrez `.env` en UTF-8 sans BOM. Les variables d'environnement du shell ont priorité sur `.env`. Les booléens sont `true` ou `false`. `PERSONA_TZ_OFFSET_HOURS` règle le fuseau horaire du personnage : la plage nocturne et les dates de ce dont il se souvient le suivent. Quand il est vide (par défaut), personagent utilise UTC+8 avec `AGENT_LANG=zh` ou `zh-TW` et sinon le fuseau horaire de cette machine. Indiquez un nombre pour choisir un autre décalage.

## Mettre à niveau depuis 0.x

La 1.0 a renommé la plupart des réglages, et personagent ne démarre pas tant qu'un ancien nom reste défini. Il liste chacun sous la forme `OLD -> NEW`, et `personagent doctor --fix` les renomme dans `.env`. [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04) dans le journal des modifications liste toutes les étapes. La mémoire et ce qu'il a appris sont conservés.

## État et autres documents

personagent 1.4.4 est sur PyPI. La CI exécute les tests sous Linux avec Python 3.10–3.14 et sous Windows avec Python 3.12. D'autres tâches CI installent le paquet, pilotent la commande et la page locale, et ouvrent la fenêtre de l'application sous Linux, macOS et Windows.

La voie directe OneBot (`/v1/onebot`) est obsolète mais reste pendant toute la 1.x. Les scripts de `tools/` sont faits pour être exécutés depuis un clone, et [tools.md](tools.fr.md) les décrit.

- [Premiers pas](start.fr.md) · [Guide de déploiement](deploy.fr.md) · [Guide pas à pas en chinois (QQ par scan et dépannage)](deploy.zh-CN.md)
- Connecteurs : [plugin AstrBot](../integrations/astrbot/astrbot_plugin_personagent/README.fr.md) · [Satori](../integrations/satori/README.fr.md) · [Matrix](../integrations/matrix/README.fr.md) · [protocole](connectors.fr.md)
- [Tous les réglages](../.env.example) · [Journal des modifications](../CHANGELOG.md) · [Contribuer](../.github/CONTRIBUTING.md) · [Politique de sécurité](../.github/SECURITY.md)
