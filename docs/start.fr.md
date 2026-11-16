# Commencer avec personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · Français · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [Guide complet](guide.fr.md)

## L'ouvrir

Rien n'est à installer au préalable : le programme d'installation apporte son propre Python. Collez une seule ligne dans un terminal.

Sous Windows, appuyez sur la touche Windows, tapez `PowerShell`, appuyez sur Entrée et collez :

```powershell
irm https://raw.githubusercontent.com/wangkant/personagent/main/install.ps1 | iex
```

Sous macOS, ouvrez Terminal (dans Applications > Utilitaires) ; sous Linux, n'importe quel terminal. Collez :

```sh
curl -LsSf https://raw.githubusercontent.com/wangkant/personagent/main/install.sh | sh
```

La première exécution prend quelques minutes. Elle installe personagent, l'ouvre et, sous Windows, place une icône personagent sur le bureau et dans le menu Démarrer ; sous macOS, elle laisse `personagent.command` sur le bureau, et sous Linux, une entrée dans le menu des applications. Lorsque PyPI ou GitHub répondent lentement, le programme d'installation utilise de lui-même des miroirs situés en Chine continentale ; `PERSONAGENT_MIRROR=cn` placé devant la commande les lui fait utiliser dès le départ, et `off` jamais. Si `raw.githubusercontent.com` lui-même est injoignable, les deux mêmes fichiers sont servis à `https://cdn.jsdelivr.net/gh/wangkant/personagent@main/install.ps1` et `.../install.sh`. Relancez la même ligne pour mettre à jour, et `uv tool uninstall personagent` pour supprimer le programme ; votre dossier personagent est conservé.

Si Python 3.10 ou une version ultérieure est déjà installé, vous pouvez plutôt installer depuis PyPI :

```sh
python -m pip install personagent
personagent
```

Avec [uv](https://docs.astral.sh/uv/), `uvx personagent` le lance sans étape d'installation séparée.

Sous Windows, la page s'ouvre dans sa propre fenêtre. Sous macOS et Linux, elle s'ouvre dans votre navigateur ; `pip install "personagent[app]"` lui donne là aussi une fenêtre.

Un assistant de programmation peut effectuer la configuration à votre place : demandez-lui de lire [setup-for-agents.md](setup-for-agents.md) et de configurer personagent.

Sous Windows, vous pouvez aussi télécharger le ZIP des sources, le décompresser et double-cliquer sur `start.bat`. Il crée son propre environnement Python dans le dossier, en téléchargeant d'abord Python si l'ordinateur n'en dispose pas, et ouvre la même page. La première fois, il place aussi une icône personagent sur votre bureau et dans le menu Démarrer.

Pour le lancer depuis un clone, donnez-lui son propre venv : `python -m venv .venv`, puis `.venv/bin/python -m pip install -e .` et `.venv/bin/python -m persona_agent`. Sous Windows, l'interpréteur est `.venv\Scripts\python.exe`, ou vous pouvez double-cliquer sur `start.bat`.

## Ajouter une clé et discuter

Choisissez un service de modèles, collez sa clé d'API et cliquez sur **Vérifier et commencer la discussion**. Les modèles gratuits d'OpenRouter et le personnage **Interlocuteur attentionné** sont sélectionnés par défaut. Ces modèles demandent eux aussi une clé, gratuite, qui s'obtient auprès d'OpenRouter via **Obtenir une clé API**. La limite est de 50 requêtes par jour, et la petite requête envoyée pour la vérifier n'est facturée que sur un service payant. **Nom du modèle et adresse** contient le nom du modèle et l'adresse de l'API, et **Choisir un nom, une personnalité ou une langue** contient le nom, la personnalité et la langue dans laquelle parle le personnage. Le menu en haut à droite de la page ne change que la langue d'affichage de la page elle-même.

Si Ollama ou LM Studio tourne déjà sur l'ordinateur avec un modèle chargé, ou si la clé d'un service de modèles est déjà définie dans une variable d'environnement (comme `DEEPSEEK_API_KEY` ou `OPENAI_API_KEY`), la page l'indique au-dessus du service de modèles, et un clic sur **Utiliser Ollama** ou **Utiliser cette clé** la vérifie et lance la discussion. Un modèle local ne demande aucune clé, et rien ne quitte l'ordinateur.

La clé reste sur votre ordinateur ; cliquez sur **Afficher** pour la vérifier. Les messages de la discussion sont transmis au service de modèles que vous choisissez, aux tarifs habituels de ce service.

Votre personnage répond dans la page, avec des autocollants et des images lorsqu'il en envoie. Les messages qu'il envoie plus tard, comme un message qu'il lance de lui-même, apparaissent dans la discussion en quelques secondes. Vos réglages sont enregistrés : au prochain lancement, la discussion s'ouvre directement.

Une fois la configuration faite, **Personnage et réglages** contient une zone **Fiche du personnage** avec le texte sur lequel repose le personnage. Réécrivez qui il est et comment il parle, puis cliquez sur **Enregistrer la fiche**. Le changement s'applique aussitôt et ce que le personnage a appris est conservé. Pour partir d'une idée, décrivez le personnage en une phrase au-dessus de la zone et cliquez sur **Rédiger un brouillon**. Pour importer un personnage partagé sous forme de carte de personnage Tavern (PNG, JSON ou CHARX), utilisez **Importer une carte de personnage** sous la zone ; [le guide](guide.fr.md#cartes-de-personnage-et-brouillons) indique ce que devient chaque partie.

En dessous, **Autres fonctions** active la recherche web, la compréhension des images et la prise de parole spontanée. La recherche utilise DuckDuckGo par défaut ; une clé Tavily la rend plus fiable. Plus bas, **Réglages avancés** regroupe les réglages qui n'étaient auparavant accessibles que dans `.env`. Tant que vous n'avez connecté aucune plateforme, la vue **Discussion** affiche une courte barre **Prise en main**.

Deux autres vues ne nécessitent aucune plateforme. **Répétition** joue une démonstration scriptée et anime un groupe de répétition, dans lequel vous pouvez voir pourquoi le personnage répond ou reste silencieux. **Application** vérifie chaque service dont dépend le personnage, affiche les journaux et regroupe les mises à jour, les sauvegardes et l'icône du Bureau.

**Activité** montre les discussions où se trouve le personnage, ce qu'il a dit récemment, ce dont il se souvient et ce qu'il a appris. Le personnage décide lui-même de ce qu'il apprend et tient sa mémoire à jour ; rien n'y attend votre intervention. Vous pouvez toujours annuler tout ce qu'il a appris, et oublier ou restaurer tout ce dont il se souvient.

## L'emmener sur d'autres plateformes

1. Cliquez sur **Connecter des plateformes** et choisissez une plateforme. Une fois celle-ci connectée, votre personnage répond dans les groupes et les messages privés de cette plateforme.
   - **Scanner pour connecter** : QQ et WeChat personnel. Cliquez sur **Obtenir un QR code** et confirmez sur votre téléphone.
     - QQ : scannez avec QQ sur mobile. QQ crée un bot ou vous laisse en choisir un que vous avez déjà, et personagent récupère ses clés. Si vous avez créé le bot vous-même sur la [page des bots QQ](https://q.qq.com/qqbot/openclaw/login.html), cliquez sur **Saisir les valeurs manuellement** et saisissez son AppID et son AppSecret.
     - WeChat : scannez avec WeChat. Le bot ne discute qu'en tête-à-tête, car WeChat ne transmet pas les messages de groupe à ces bots.
   - **Coller quelques valeurs** : Telegram (un jeton de @BotFather), Discord (un jeton de bot, avec Message Content Intent activé), KOOK, Feishu, DingTalk, Slack, bot IA WeCom, Mattermost, Misskey, Matrix, Twitch, IRC, Zulip, VK et Stoat. La page indique quelles valeurs copier depuis la console de la plateforme. Tout le reste utilise les valeurs par défaut. Twitch demande en outre d'approuver une connexion au moyen d'un lien.
   - **Avancé** : les applications WeCom, les comptes officiels WeChat et les webhooks QQ ont besoin d'une adresse publique qui transfère vers leur port de rappel. OneBot v11 (NapCat) et Satori ont besoin d'un autre logiciel en cours d'exécution sur cet ordinateur.
2. personagent connecte lui-même QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK et Stoat. Les autres plateformes passent par AstrBot, une passerelle tierce. La première fois que vous en connectez une, personagent télécharge AstrBot avec un environnement Python 3.12 distinct : laissez la page ouverte jusqu'à la fin du téléchargement. AstrBot s'exécute ensuite en arrière-plan, sans tableau de bord auquel se connecter.
3. personagent vérifie les identifiants auprès de la plateforme avant de les enregistrer. Si la plateforme les refuse, la page vous l'indique et rien n'est enregistré.
4. Les plateformes connectées sont listées en haut de **Connecter des plateformes**, où vous pouvez les reconfigurer ou les déconnecter.
5. Pour tout autre logiciel acceptant une adresse compatible OpenAI, comme Open WebUI, SillyTavern ou un script, activez **Autres logiciels** en bas de **Connecter des plateformes** et copiez l'adresse, la clé et le modèle indiqués dans ce logiciel. Le [guide complet](guide.fr.md#autres-logiciels) le décrit.
6. Sans la page, par exemple sur un serveur sans écran, `personagent connect <plateforme>` connecte QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK ou Stoat depuis le terminal, avec les mêmes étapes et les mêmes vérifications. `personagent connect` seul les liste. Le [guide complet](guide.fr.md#connecter-une-plateforme-dans-le-terminal) décrit la commande.

Pour trouver un bot QQ, ouvrez QQ sur mobile et allez dans Contacts → Bots. Discutez avec lui en privé ou ajoutez-le à un groupe dont vous êtes propriétaire. Cette voie utilise la plateforme officielle de bots de QQ : il ne vous faut ni compte QQ personnel ni logiciel supplémentaire. QQ décide où le bot peut aller. Tant que le bot n'est pas certifié, il ne peut rejoindre que les groupes dont son administrateur est propriétaire, et il n'y a pas de bac à sable à configurer. Dans un groupe, il ne voit que les messages qui le mentionnent avec @, sauf si le propriétaire du groupe active la réception de tous les messages sur le profil du bot dans ce groupe. Le [guide des bots QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) couvre la certification et le reste côté compte.

Si un QR code expire, demandez-en un nouveau. Si un téléchargement échoue, relancez-le sans refaire la configuration du modèle. Connecter une plateforme n'ouvre au personnage que les groupes et les messages privés de cette plateforme ; les autres adaptateurs gardent leurs listes d'autorisation. LINE n'est pas proposé, car AstrBot ne reçoit les rappels de LINE que par son tableau de bord, que personagent ne lance pas.

## La prochaine fois

Rouvrez personagent. Vos réglages sont conservés et les plateformes connectées se reconnectent automatiquement. S'il est déjà en cours d'exécution, le rouvrir fait réapparaître sa fenêtre. Gardez-la ouverte pendant que vous l'utilisez : les processus qu'il a démarrés s'arrêtent avec lui, que vous cliquiez sur **Quitter** ou que vous fermiez la fenêtre, et ce qu'un plantage a laissé derrière lui est arrêté au démarrage suivant. Sous Windows, `personagent shortcut` place sur votre bureau et dans le menu Démarrer une icône qui l'ouvre sans terminal. Toujours sous Windows, **Exécution en arrière-plan**, dans la vue **Application**, permet de fermer la fenêtre en laissant personagent actif derrière une icône de la zone de notification ; le personnage continue alors de répondre.

Quand une version plus récente est sur PyPI, la vue **Discussion** affiche un avis avec un lien vers les notes de version et la commande de mise à jour adaptée à la façon dont cette copie a été installée. Une copie issue du ZIP des sources reçoit à la place un lien pour télécharger les nouvelles sources depuis la page des versions. **Mettre à jour et rouvrir**, dans la vue **Application**, installe la mise à jour pour la plupart des installations. personagent interroge pypi.org au plus une fois par jour, et la requête ne contient que son numéro de version. Définissez `UPDATE_CHECK_ENABLED=false` dans `.env` pour désactiver la vérification.

Si vous préférez la ligne de commande, utilisez `personagent start --terminal`, `personagent init --terminal`, `personagent up`, ou les commandes `chat`, `demo` (sans clé), `run` et `connect`. Elles conservent votre `.env`, votre fiche du personnage modifiée et les souvenirs appris. Le [guide complet](guide.fr.md) couvre les autres plateformes.
