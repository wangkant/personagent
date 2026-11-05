# Déployer personagent

[English](deploy.md) · [简体中文](deploy.zh-CN.md) · [繁體中文](deploy.zh-TW.md) · [日本語](deploy.ja.md) · [한국어](deploy.ko.md) · [Español](deploy.es.md) · Français · [Deutsch](deploy.de.md) · [Português (Brasil)](deploy.pt-BR.md) · [Русский](deploy.ru.md)

Le [démarrage rapide](start.fr.md) et le [guide d'utilisation](guide.fr.md) vous amènent jusqu'à une première discussion. Ils couvrent l'installation, le [dossier personnel](guide.fr.md#installation-et-dossier-personnel), la configuration sur la page locale et la connexion d'une plateforme. Ce guide couvre ce dont a besoin un déploiement réel, et ce qu'il faut vérifier quand le bot se tait.

## La configuration la plus courte qui fonctionne

La page locale (`personagent`, ou `personagent init --terminal` pour l'assistant en terminal) vérifie la clé avec une petite requête, puis écrit `.env` dans le dossier personnel. Discuter nécessite une clé, et `.env.example` vous démarre sur les modèles gratuits d'OpenRouter :

```
LLM_API_KEY=...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

Un `.env` qui ne définit que la clé signifie `https://api.deepseek.com` et `deepseek-flash`. Vous pouvez les pointer vers n'importe quel endpoint compatible OpenAI, hébergé ou local (Ollama, llama.cpp). Collez l'adresse de l'API telle que le fournisseur la documente, racine ou base versionnée comme `.../v1` ou `.../api/paas/v4`. Tant que vous n'écrivez pas de `persona.txt`, le `data/persona.example.<lang>.txt` fourni le remplace. Tant que `PERSONA_NAME` n'est pas défini (la configuration le définit), le personnage s'appelle « bot ».

La page écrit aussi `PERSONA_NAME`, `AGENT_LANG` et un `CONNECTOR_TOKEN`. Les plateformes connectées depuis la page n'ont besoin de rien de plus dans `.env`. Leurs identifiants vont dans `<home>/platforms/` : `direct.json` contient les plateformes que personagent connecte lui-même, et l'AstrBot géré conserve les autres dans sa propre configuration. Ajouts facultatifs :

```
ADMIN_IDS=telegram:12345             # the admin's accounts, <platform>:<id>
# QQ through NapCat (OneBot) only
QQ_BOT_ID=...                        # the bot account's number
CONNECTOR_QQ_PLATFORMS=aiocqhttp
```

Les clés restent sur cette machine. Le fournisseur de modèles que vous choisissez voit les conversations. Tout le reste de `.env.example` a une valeur par défaut qui fonctionne. `SERVER_HOST` et `SERVER_PORT` valent `127.0.0.1:8080`, `QQ_ONEBOT_URL` est vide (pas de serveur HTTP NapCat), et un `ACCESS_GROUPS` vide laisse tous les groupes au connecteur.

## Le lancer

`personagent` ouvre la page locale. Tant que la page est ouverte, il exécute l'agent, le processus qui maintient les plateformes connectées directement, et l'AstrBot géré s'il est installé. Relancer `personagent` réutilise une page ouverte. `personagent up` démarre les mêmes processus sans navigateur.

Dans les deux cas, ces processus s'arrêtent avec lui, quelle que soit la façon dont il s'arrête. Ce qu'une exécution précédente plantée a laissé est arrêté au démarrage suivant. Chaque processus écrit son journal dans `<home>/runtime/desktop/` (`agent.log`, `direct.log`, `astrbot.log`).

La page locale et `personagent up` demandent à pypi.org au plus une fois par jour si un personagent plus récent est sorti. Si c'est le cas, la vue Discussion et le terminal affichent la commande qui met à jour cette copie. La requête ne contient que le numéro de version, et `UPDATE_CHECK_ENABLED=false` désactive la vérification.

`personagent run` démarre l'agent seul, comme le décrit [Exécuter le service](guide.fr.md#exécuter-le-service). Utilisez-le quand vos propres connecteurs (un AstrBot que vous exécutez, Satori, Matrix) lui parlent. `personagent doctor` vérifie les réglages et sonde chaque service en amont.

**Réglages renommés en 1.0.** Tant qu'un nom de réglage retiré par la 1.0 reste défini, le démarrage refuse avec le code de sortie 2 et liste chacun sous la forme `OLD -> NEW`. `personagent doctor --fix` les renomme dans `<home>/.env`. Il conserve les valeurs et les commentaires, enregistre l'ancien fichier sous `.env.bak`, et commente une ancienne ligne dont le nouveau nom est déjà défini. Un nom retiré défini dans l'environnement plutôt que dans `.env` doit être renommé là où il est défini. `personagent doctor` sort avec 1 tant qu'il en reste, et `--json` les liste sous `retired_settings`. `HOST`, `PORT` et `LOG_FILE` ne comptent que s'ils sont écrits dans `.env`.

### Activité

[Activité](guide.fr.md#activité) est une vue de la page locale. Elle ne nécessite aucune installation supplémentaire, ne charge rien depuis Internet et n'affiche jamais de clés ni de jetons. Elle lit l'API JSON du service d'agent démarré par la page locale. Avec `personagent run` seul, lisez le journal du service et utilisez plutôt `personagent learned`. `DASHBOARD_ENABLED=false` désactive l'API. La vue l'indique alors, et `personagent doctor` affiche `activity: off (...)`.

L'API se trouve sous `/api/dashboard/` sur le service d'agent :

- `GET status`, `GET conversations` et `GET conversation?id=<chat id>` lisent l'état du service, les discussions qu'il connaît et une discussion en détail.
- `POST candidates/<id>/promote`, `replace`, `reject` et `rollback` modifient ce qu'il a appris. Chaque modification va dans le même registre que `personagent learned`, avec l'acteur `dashboard`.

Chaque appel nécessite l'en-tête `X-Personagent-Dashboard-Token` avec le jeton de `dashboard.token` dans le dossier d'exécution (`<home>/runtime/` sauf si `AGENT_RUNTIME_DIR` le déplace). Seul le propriétaire peut lire le fichier, et le service le crée au démarrage. Un appel sans l'en-tête reçoit 401 (`dashboard_token`), et un mauvais jeton reçoit 403 (`wrong_token`). `CONNECTOR_TOKEN` et `X-Personagent-Token` ne l'ouvrent pas. Ils servent uniquement aux connecteurs et à `/health/details`.

- Les écritures nécessitent aussi `X-Personagent-Dashboard: 1` et `Content-Type: application/json`. Si la requête envoie un `Origin`, il doit être celui du service.
- Les requêtes de navigateur intersites sont refusées.
- Les réponses remplacent chaque identifiant par `***`. Les URL des vérifications de démarrage masquent aussi le nom d'utilisateur, le mot de passe et la requête.
- Les scripts sur le même ordinateur peuvent appeler l'API de la même façon que la page locale.

Le service ne sert aucune page. `GET /` répond par une courte note qui renvoie vers la page locale et vers `personagent learned`, et c'est aussi ce qu'ouvre désormais un ancien lien `?token=`. La page locale n'écoute que sur 127.0.0.1. Sur un serveur sans page locale, examinez et annulez l'apprentissage avec `personagent learned`.

## Ce que l'hôte doit fournir

1. **Un dossier personnel accessible en écriture.** Le démarrage prend un verrou sur `<home>/.personagent.instance.lock`, hors de `runtime/`. Un dossier personnel en lecture seule ne démarre pas.
2. **Un processus par dossier personnel.** Un second `personagent run` sur le même dossier sort avec une phrase qui le dit.
3. **Un port libre.** Un port occupé ou interdit sort aussi avec une phrase. Choisissez-en un autre avec `--port` ou `SERVER_PORT`.

`AGENT_RUNTIME_DIR` doit se résoudre sous le dossier personnel, sinon le démarrage échoue. Un `PERSONA_FILE` ou `PERSONA_CARD_FILE` relatif se résout aussi sous ce dossier, donc une persona gardée ailleurs nécessite un chemin absolu.

## Connecter des plateformes

Ajoutez des plateformes sous **Connecter des applis** sur la page locale. personagent vérifie les identifiants auprès de la plateforme avant d'enregistrer quoi que ce soit. Si la plateforme les refuse, la page affiche le refus et ne conserve rien.

**Connectées par personagent lui-même.** QQ, WeChat personnel, Telegram et Discord fonctionnent dans un seul processus « direct », sans AstrBot ni NapCat.

| Plateforme | Ce que vous faites | Limites |
|---|---|---|
| QQ (bot officiel) | Scannez un code QR avec QQ mobile, qui crée un bot ou en choisit un que vous avez créé. Coller l'AppID et l'AppSecret est la solution de repli. | Tant que le bot n'est pas certifié, QQ ne le laisse rejoindre que les groupes dont vous êtes propriétaire. Les permissions de messages de groupe se règlent dans QQ. |
| WeChat personnel | Scannez avec WeChat (l'API de bots iLink de Tencent). | Discussions individuelles uniquement. WeChat ne donne pas de messages de groupe à ces bots. |
| Telegram | Collez le jeton de @BotFather. | |
| Discord | Collez le jeton du bot, avec Message Content Intent activé. | |

**Via l'AstrBot géré.** Toutes les autres plateformes passent par un AstrBot que personagent télécharge, avec son propre runtime Python 3.12, et exécute sans interface. Il n'a pas de tableau de bord et ne nécessite pas de seconde connexion. KOOK, Feishu/Lark (connexion longue), DingTalk (mode Stream), Slack (Socket Mode, et le lien du guide préremplit l'application), bot IA WeCom (connexion longue), Mattermost et Misskey demandent une ou deux valeurs. Le groupe Avancé nécessite une adresse publique ou un autre logiciel : application WeCom, compte officiel WeChat, webhook QQ, OneBot v11 (NapCat) et Satori. LINE n'est pas proposé.

Sur les deux voies, une plateforme connectée répond à chaque groupe et message privé que la plateforme transmet au bot. Cela change dès que `ACCESS_GROUPS` ou `ACCESS_DM_USERS` contient une entrée pour cette plateforme (voir [les listes d'autorisation de personagent](#via-un-astrbot-que-vous-exécutez-déjà)). Les identifiants arrivent sous la forme `<platform>:<id>`, par exemple `qq_official:<openid>`, `weixin_oc:<id>`, `telegram:<id>` et `discord:<id>`. Le bot QQ officiel voit des openids, pas des numéros QQ. Connecter une plateforme directement supprime la connexion AstrBot de cette même plateforme.

## Via un AstrBot que vous exécutez déjà

AstrBot, NapCat (OneBot), Koishi (via le [connecteur Satori](../integrations/satori/README.fr.md)) et Matrix (via le [connecteur Matrix](../integrations/matrix/README.fr.md) et les ponts mautrix) sont des ponts tiers avec lesquels personagent fonctionne. Aucun n'est nécessaire pour QQ, WeChat, Telegram ou Discord.

AstrBot transmet les messages à personagent via un plugin dans `integrations/astrbot/astrbot_plugin_personagent/`. Le plugin envoie chaque message à `POST /v1/events` et relaie les réponses reçues. Il récupère aussi la boîte d'envoi de personagent (`outbox_enabled`, activé par défaut), donc la persona peut parler en premier là où la plateforme le permet à un bot. Le README du plugin contient le tableau. L'AstrBot géré reçoit le plugin automatiquement. Pour votre propre AstrBot, démarrez-le une fois pour qu'il crée son dossier de données (celui qui contient `cmd_config.json`, `plugins/` et `config/`), puis exécutez :

```
personagent connect astrbot                       # asks, and finds AstrBot's folder itself
personagent connect astrbot <AstrBot data dir>    # asks nothing
```

La commande copie le plugin dans `<data dir>/plugins/` et écrit un même `CONNECTOR_TOKEN` dans `.env` et dans la configuration du plugin. Elle définit `personagent_url` sur `http://127.0.0.1:<SERVER_PORT>` sauf si le plugin a déjà une URL qu'il accepte (une URL de bouclage, tunnels compris, ou HTTPS).

Pour un AstrBot sur une autre machine, téléchargez `astrbot_plugin_personagent.zip` depuis la [dernière version](https://github.com/wangkant/personagent/releases/latest) et envoyez-le sous **Install from File** sur la page des plugins d'AstrBot. Réglez son `connector_token` sur le `CONNECTOR_TOKEN` du `.env` de personagent, et `personagent_url` sur une adresse HTTPS de personagent (voir [Exposer les endpoints](#exposer-les-endpoints)).

Après une mise à niveau de personagent, relancez `connect astrbot` ou envoyez le nouveau zip. AstrBot 4.29 et versions ultérieures remplacent la copie installée. Sur les versions antérieures, désinstallez-le d'abord et laissez **Also delete plugin configuration file** décoché.

Options de `connect astrbot` :

- `--qq` retire `aiocqhttp` de `excluded_platforms`, et `--no-qq` le remet. Sans l'un ni l'autre, le routage QQ reste tel quel. `CONNECTOR_QQ_PLATFORMS` suit ce que le plugin finit par faire.
- `--platform qq_official|telegram|discord|slack|kook|lark --token <token>` active aussi cet adaptateur dans la configuration d'AstrBot. Slack prend aussi `--app-token`, et Lark et QQ prennent `--app-id` et `--app-secret`. Une entrée d'adaptateur existante garde ses autres réglages (proxy, URL de base, interrogation) et ne reçoit que les nouveaux identifiants.
- `--url https://...` définit une adresse HTTPS où le plugin envoie.
- `--install` télécharge plutôt un AstrBot géré, et `--start` le démarre.

La première exécution laisse les listes d'autorisation vides. Une nouvelle exécution les conserve, ainsi que les autres plateformes exclues.

Le plugin refuse par défaut. Remplissez `groups`, et `dm_users` pour les messages privés, dans la WebUI d'AstrBot, ou répondez aux questions de `connect`. Les messages privés sont transmis dès que `dm_users` n'est pas vide. Le [README du plugin](../integrations/astrbot/astrbot_plugin_personagent/README.fr.md) liste toutes les clés. L'AstrBot géré ouvre chaque plateforme que vous connectez avec `<platform>:*`. Une fois le plugin installé, redémarrez AstrBot ou rechargez les plugins dans sa WebUI. Du côté de personagent :

- `CONNECTOR_TOKEN` authentifie chaque requête. La requête porte l'en-tête `X-Personagent-Token` et un HMAC-SHA256, avec le jeton comme clé, sur `timestamp.nonce.body`, et une protection contre le rejeu rejette les nonces réutilisés. Une requête capturée ne peut être ni rejouée ni modifiée. Le jeton est aussi la clé de signature, alors gardez-le hors des journaux et changez-le s'il fuit. Il est facultatif sur un seul hôte et obligatoire entre hôtes.
- `ADMIN_IDS` liste les comptes de l'administrateur sous la forme `<platform>:<id>` (`telegram:12345`, `discord:4242`). Un identifiant seul ou `qq:<id>` est un numéro QQ. `ADMIN_NAME` définit le nom de l'administrateur. Tous les comptes listés appartiennent à une seule personne, qui reçoit la persona plus proche en groupe et en message privé, peut gérer ce que le bot retient d'un groupe et peut lui enseigner seule. Via AstrBot, la plateforme est le nom d'adaptateur qu'affiche AstrBot, et `/sid` dans une discussion affiche un identifiant.
- `ACCESS_GROUPS` et `ACCESS_DM_USERS` permettent à personagent de restreindre lui-même une plateforme, sous la même forme `<platform>:<id>`. Chaque plateforme est restreinte séparément. Une plateforme sans entrée est laissée au connecteur, et une seule entrée limite cette plateforme à ses entrées. Un tour que personagent refuse repart sans être pris en charge, donc le modèle d'AstrBot peut y répondre.

Pour AstrBot dans Docker ou sur un autre hôte, voir [le guide d'utilisation](guide.fr.md#ponts-que-vous-exécutez-vous-même).

### QQ via NapCat (OneBot)

Cette voie utilise un compte QQ personnel au lieu d'un bot officiel. Il vous faut un second compte QQ dans les groupes visés, pas le vôtre (voir [DISCLAIMER.md](DISCLAIMER.fr.md)). Il se connecte, en général par code QR et dans une session qui survit aux redémarrages, à une implémentation de OneBot v11 reliée à l'adaptateur `aiocqhttp` d'AstrBot. [NapCat](https://github.com/NapNeko/NapCatQQ) est testé et s'attache au client de bureau QQ NT. LLOneBot et Lagrange sont d'autres implémentations de OneBot v11.

Sur l'AstrBot géré, ajoutez **Avancé > OneBot v11 (NapCat)** sur la page locale et pointez NapCat vers `ws://127.0.0.1:6199/ws`. Le [guide en chinois](deploy.zh-CN.md) le détaille étape par étape. Avec votre propre AstrBot, retirez `aiocqhttp` de `excluded_platforms` du plugin, définissez `CONNECTOR_QQ_PLATFORMS=aiocqhttp` (`--qq` fait les deux), et définissez `QQ_BOT_ID` (`personagent connect astrbot` le demande).

**`CONNECTOR_QQ_PLATFORMS` est obligatoire ici.** Sans lui, les identifiants QQ arrivent avec un espace de noms (`aiocqhttp:123456`) et chaque conversation semble nouvelle. La mémoire, l'historique et les exemples appris sont indexés par l'identifiant nu, et les registres dérivent les identifiants de ligne de l'identifiant de conversation, donc la séparation ne peut pas être réparée ensuite.

Les identifiants nus portent l'autorité QQ, donc les entrées QQ de `ADMIN_IDS`, `ACCESS_GROUPS` et `ACCESS_DM_USERS` s'appliquent en plus des listes d'autorisation du plugin. Un message privé QQ doit être dans `dm_users` *et* venir de l'administrateur ou d'une entrée de `ACCESS_DM_USERS`. Quand `ACCESS_GROUPS` contient des groupes QQ, un groupe QQ doit être dans les deux. Ne mettez une plateforme dans `CONNECTOR_QQ_PLATFORMS` que si vous confiez cette autorité à son connecteur.

**Le serveur HTTP de NapCat** (`QQ_ONEBOT_URL`, vide par défaut) est facultatif sur cette voie. personagent envoie aussi des messages de sa propre initiative :

- les messages proactifs (`PROACTIVE_ENABLED`, désactivé par défaut) ;
- la question posée deux minutes après un rejet (`REACT_ELICIT_ENABLED`) ;
- l'excuse envoyée dans un groupe quand l'appel au modèle échoue.

Ils repartent par la boîte d'envoi du plugin tant que le plugin la récupère. Sinon, ils vont à `QQ_ONEBOT_URL` si l'URL est définie. Seul le balayage des @mentions manquées hors ligne nécessite le serveur, avec `QQ_BOT_ID`. Le balayage s'exécute au démarrage puis toutes les 30 minutes. Il couvre les groupes QQ de `ACCESS_GROUPS` plus tout groupe actif depuis le dernier redémarrage, et rejoue les @mentions de moins d'une heure. Avec l'URL vide, `personagent doctor` affiche le pont OneBot comme "not configured".

**Perdu sur toutes les voies de connecteur** (direct, AstrBot ou autre connecteur), sans réglage pour le récupérer :

- l'OCR de secours pour les images qu'aucun modèle de vision n'a décrites ;
- la recherche de citations via NapCat. Les citations se résolvent à partir de l'index propre à personagent des messages récents, et du texte cité qu'un connecteur envoie avec la citation ;
- la collecte de nouveaux stickers à partir des images publiées dans les groupes.

## Plusieurs plateformes

Plusieurs connecteurs peuvent fonctionner côte à côte avec un seul personagent, car chacun nomme sa plateforme (`telegram:-1001234`, `matrix:!room:example.org`). Le processus direct, AstrBot, Satori et Matrix peuvent tous tourner en même temps. Ne faites pas entrer une même discussion par deux connecteurs, sinon chaque message arrive deux fois. Les identifiants avec espace de noms n'entrent jamais en collision avec un numéro QQ nu.

Les messages que personne n'a demandés atteignent une plateforme via un connecteur qui récupère la boîte d'envoi de personagent. Ce sont les prises de parole proactives, la question après un rejet et l'excuse quand l'appel au modèle échoue dans un groupe. L'excuse d'un message privé repart dans la réponse à la requête qui a apporté le message.

Le processus direct et les trois connecteurs d'ici récupèrent tous la boîte d'envoi, sur les plateformes où un bot peut écrire en premier. QQ limite le débit des messages spontanés d'un bot officiel, et une personne peut les désactiver. Un connecteur à vous envoie `connector_id`, `reply_handle` et `"capabilities": ["outbox"]` avec ses événements et fait une interrogation longue de `/v1/outbox` (voir [le protocole des connecteurs](connectors.fr.md)). Sans un tel connecteur, personagent ne parle qu'à l'intérieur de la requête qui a apporté un message. Les boucles proactives ignorent ces conversations, et la question et l'excuse ne sont pas envoyées.

`PROACTIVE_PLATFORMS` limite où la boucle proactive peut parler en premier. `PROACTIVE_PLATFORMS=qq_official` la garde sur le bot QQ officiel, et `qq` sur QQ via NapCat. `CONNECTOR_OUTBOX_ENABLED=false` désactive complètement la boîte d'envoi.

Pour parler en premier en message privé sans la boîte d'envoi, votre propre planificateur (une tâche de plugin AstrBot, une entrée cron) peut envoyer un événement de message privé marqué `"proactive": true`. Voir [Parler en premier sans la boîte d'envoi](connectors.fr.md#parler-en-premier-sans-la-boîte-denvoi).

## Exposer les endpoints

Gardez `SERVER_HOST=127.0.0.1` quand le connecteur et personagent partagent une machine. Un conteneur compte comme la même machine seulement avec l'espace de noms réseau de l'hôte ou le réseau hôte. La page locale et `personagent up` écoutent toujours sur `127.0.0.1`. Sinon :

1. Définissez `SERVER_HOST=0.0.0.0` (ou `--host 0.0.0.0`) et `CONNECTOR_TOKEN`. Le démarrage refuse une écoute réseau sans le jeton. Il n'exige pas `QQ_ONEBOT_SECRET`, mais sans lui le `/v1/onebot` obsolète est désactivé sur une écoute réseau. Chaque requête vers lui reçoit 403 `onebot_disabled`, et le journal indique pourquoi une fois.
2. Placez devant un proxy inverse HTTPS ou un tunnel privé. Tous les connecteurs d'ici n'envoient que vers le bouclage, ou vers HTTPS avec un jeton défini. Le plugin AstrBot journalise tout le reste comme `refusing unsafe personagent_url`, et les connecteurs Satori et Matrix refusent de démarrer.
3. Gardez le corps intact à l'octet près, car la signature le couvre, et gardez les horloges à moins de cinq minutes d'écart.

Avec un identifiant vide, son endpoint ne sert que les programmes locaux qui appellent directement `http://127.0.0.1` ou `http://localhost`. Une requête reçoit 403 `non_local_request` si elle contient l'un des éléments suivants :

- un en-tête `Origin` ;
- un `Sec-Fetch-Site` autre que `none` ;
- un `Host` autre que `localhost`, `127.0.0.1` ou `::1` ;
- un en-tête de proxy : `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, `CF-Connecting-IP`, `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` ou `X-Original-Forwarded-For`.

Un proxy sur le même hôte qui n'en ajoute aucun paraît encore local. Définissez `CONNECTOR_TOKEN` (et `QQ_ONEBOT_SECRET` si vous utilisez `/v1/onebot`) avant d'ajouter un proxy ou un tunnel, même sur un seul hôte.

## Endpoints de santé

- `GET /health` est gratuit et ouvert, et n'appelle rien.
- `GET /health/details` sonde les services en amont (en cache 60 s). Avec `CONNECTOR_TOKEN` vide, il ne répond qu'aux requêtes locales. Avec un jeton défini, il ne répond **qu'aux** requêtes portant un en-tête `X-Personagent-Token` correspondant, même depuis le bouclage. Il renvoie 503 quand une sonde critique échoue ou ne peut pas s'exécuter. Les sondes critiques sont les modèles de discussion et, quand QQ utilise l'entrée directe OneBot (`QQ_BOT_ID` et `QQ_ONEBOT_URL` définis, `CONNECTOR_QQ_PLATFORMS` non défini), le pont OneBot.
- `personagent doctor [--json]` exécute les mêmes sondes plus la vérification des réglages, et sort avec un code non nul dans le même cas. Quand la dernière vérification des mises à jour date d'un jour, il demande aussi à pypi.org la version la plus récente (`UPDATE_CHECK_ENABLED=false` l'évite).

## Coûts

- **Les sondes consomment du crédit.** `personagent doctor` et `/health/details` envoient une toute petite complétion de discussion à chaque endpoint de modèle configuré (discussion, message privé, évaluation et vision). Ils envoient aussi un embedding si `EMBEDDING_MODEL` est défini, et une recherche Tavily si `TAVILY_API_KEY` est défini. `/health` et les vérifications des réglages et des registres sont gratuits.
- **Les scripts de `tools/`** diffèrent. Certains sont gratuits et d'autres appellent un modèle. Le tableau de [tools.md](tools.fr.md) indique lesquels.
- **`personagent eval`** appelle le modèle pour chaque cas. Les suites de persona et d'apprentissage nécessitent aussi un second modèle comme juge (`BENCH_JUDGE_MODEL`).
- **Mémoire.** Au-delà de 256 conversations avec espace de noms (hors QQ), la conversation inactive la moins récemment active perd son historique récent et ses réactions en attente. Les souvenirs à long terme, les notes principales et les registres restent. Une conversation au milieu d'une requête n'est jamais évincée. Les souvenirs à long terme sont chargés du disque au démarrage et ne sont pas concernés par ce plafond.
- **Disque.** Le journal de preuves et le registre de candidats dans `runtime/` sont en ajout seul et jamais tronqués. `personagent doctor` signale chacun au-delà de 50 Mo (`LEDGER_EVIDENCE_WARN_BYTES`, `LEDGER_CANDIDATES_WARN_BYTES`). Sauvegardez `runtime/`, car il contient tout ce que le bot a appris.

## Quand le bot se tait

Les causes sont listées de la plus courante à la moins courante. Quand la page locale exécute l'agent, [Activité](guide.fr.md#activité) montre si les messages arrivent et pourquoi il s'est tu. Sur un serveur, lisez le journal du service et utilisez `personagent learned` pour ce qu'il a appris.

1. **Rien ne lui parvient.** Sur la page locale, vérifiez que la plateforme apparaît comme connectée, et lisez `runtime/desktop/direct.log` ou `astrbot.log`. Le bot QQ officiel doit être dans le groupe, et QQ décide quels messages de groupe il reçoit. Un bot WeChat personnel ne reçoit jamais de groupes. Dans un AstrBot que vous exécutez, remplissez `groups` du plugin (et `dm_users` pour les messages privés), et pour NapCat retirez `aiocqhttp` de `excluded_platforms`. Les connecteurs Satori et Matrix ont leurs propres listes d'autorisation dans leur `.env`. Voir leurs README. Dans ce cas, la discussion n'apparaît jamais dans Activité.
2. **L'agent est désactivé.** La bannière de `personagent run` affiche `agent: OFF`, avec la raison et la solution. Sans `LLM_API_KEY`, ajoutez une clé sur la page locale (ou définissez `LLM_API_KEY`) et redémarrez. Avec `AGENT_ENABLED=false`, mettez-le à `true` dans `<home>/.env` et redémarrez. D'ici là, chaque événement reçoit `owned: false`, et le premier journalise une seule ligne ERROR avec le même conseil.
3. **Le modèle d'AstrBot répond à la place.** Le plugin s'est rabattu parce que la requête a échoué, que personagent a écarté le message (point 5) ou que l'agent est désactivé (point 2). Le journal d'AstrBot affiche `refusing unsafe personagent_url`, `agent refused the request (403): <message>` (ou un autre statut, voir le tableau ci-dessous) ou `timed out waiting for the agent`. `timeout_s` doit couvrir l'anti-rebond et chaque appel au modèle du tour, alors gardez `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` en dessous. Sa valeur par défaut (420) couvre celles de l'agent (120 × 3 = 360 s). Augmentez-la quand vous augmentez ces deux-là.
4. **Il n'a pas été appelé.** Dans un groupe, il répond à son nom (`PERSONA_NAME`) ou à un @. Sinon, il attend assez de conversation (`CHAT_TRIGGER_COUNT`, 30 messages par défaut) et peut quand même passer. De 02:00 à 07:00 dans son fuseau horaire, il reste le plus souvent hors des discussions où on ne l'a pas appelé. Le fuseau horaire est `PERSONA_TZ_OFFSET_HOURS`. Laissé vide, c'est UTC+8 quand `AGENT_LANG` vaut `zh` ou `zh-TW`, et sinon le décalage de cette machine. Activité montre la raison de chaque tour récent. Pour observer la même décision hors ligne, exécutez `personagent chat --trigger 4`.
5. **Les listes d'autorisation de personagent.** `ACCESS_GROUPS` et `ACCESS_DM_USERS` s'appliquent sur toutes les voies, et un message privé QQ à identifiant nu nécessite aussi l'administrateur ou une entrée. Un message qu'elles écartent repart sans être pris en charge, donc via AstrBot son modèle peut y répondre. personagent journalise chaque conversation refusée une fois, en INFO, avec le réglage qui l'a refusée.
6. **L'appel au modèle échoue.** Une clé rejetée (401 ou 403) ou un solde vide (402 ou quota épuisé) journalise une ligne ERROR qui nomme l'hôte du fournisseur et le réglage à corriger. Exécutez `personagent doctor`. Il envoie une toute petite requête à chaque endpoint de modèle et affiche le statut, ce qui détecte aussi un `LLM_BASE_URL` ou `LLM_MODEL` erroné. Tant que le modèle est hors service, la persona envoie une courte excuse dans son personnage quand on l'appelle, au plus une fois par conversation toutes les cinq minutes.
7. **Un réglage mal orthographié.** Le journal de démarrage et `personagent doctor` listent chaque clé que `.env.example` ne connaît pas, et toute valeur commençant par `#`.
8. **Un BOM sur `.env`.** Le nom du premier réglage porte le BOM et n'atteint jamais le processus. Le démarrage et `personagent doctor` le signalent. Réenregistrez le fichier en UTF-8 sans BOM.
9. **`QQ_BOT_ID` non défini ou erroné avec NapCat.** Via AstrBot, les @mentions fonctionnent encore, mais le balayage des mentions manquées s'appuie dessus. Sur l'entrée directe OneBot, une @mention n'est jamais reconnue. Le bot démarre sans erreur, ne journalise rien et n'y répond jamais. `personagent doctor` avertit quand `QQ_BOT_ID` est vide et que d'autres réglages QQ sont définis. Le bot QQ officiel ne l'utilise pas.
10. **Il répond, mais a oublié ce qu'il a appris.** Soit NapCat QQ arrive sans `CONNECTOR_QQ_PLATFORMS=aiocqhttp`, soit `PERSONA_NAME` ou `PERSONA_VERSION` a changé, ce qui démarre un nouveau personnage. Le journal avertit quand le matériel promu de l'ancien personnage est refusé en bloc. Modifier `persona.txt`, y compris dans la zone Fiche du personnage de la page, ne démarre pas de nouveau personnage. Ses révisions sous un même `PERSONA_VERSION` partagent une portée d'apprentissage (`runtime/persona_lineage.json`). Pour intégrer des lignes apprises sous un hachage de persona que la lignée ne contient pas, exécutez `personagent learned lineage adopt <hash>`, puis `personagent learned rebuild`. Le hachage se trouve dans la portée du candidat dans `personagent learned show <id>`. Passer `AGENT_LANG` du chinois à une autre langue ou inversement bascule aussi vers les autres fichiers appris de `runtime/`.

Les erreurs de `/v1/events` sont listées ci-dessous. Le plugin AstrBot journalise le message, et `code` est le champ stable sur lequel un client peut se baser.

| Statut | `code` | Message dans le journal d'AstrBot | Cause |
|---|---|---|---|
| 403 | `unauthenticated` | authentication required | pas de `CONNECTOR_TOKEN`, et l'appelant n'est pas sur cette machine |
| 403 | `non_local_request` | no credential is configured; only local requests accepted | pas de `CONNECTOR_TOKEN`, et la requête est passée par un navigateur, un proxy ou un autre nom d'hôte |
| 403 | `invalid_envelope` | invalid, stale, or replayed request envelope | jeton, en-têtes ou signature manquants ou erronés, horloges à plus de 5 min d'écart, nonce réutilisé ou protection contre le rejeu pleine (`connector replay guard full` dans le journal de l'agent) |
| 403 | `stale_event` | stale or invalid sent_at | `sent_at` diffère de maintenant de plus de `CONNECTOR_MAX_EVENT_AGE_S` (24 h), horodatages futurs ou en millisecondes compris |
| 400 | `invalid_schema` | invalid event schema | un champ obligatoire manque : `platform`, `conversation_type`, `sender_id`, `message_id`, `sent_at`, et `conversation_id` pour les groupes |
| 400 | `client_disconnected` | client disconnected | l'appelant a raccroché pendant l'envoi |
| 408 | `body_timeout` | request body not received in time | le corps a mis plus de 30 s à arriver |
| 413 | `body_too_large` | request body too large | dépasse `SERVER_MAX_BODY_BYTES` (8 Mo), en général une image intégrée |
| 429 | `capacity_exceeded` | webhook capacity exceeded | dépasse `CONNECTOR_MAX_INFLIGHT` tours en cours ; réessayez après 3 s |

## Ancienne méthode : l'entrée directe OneBot

Le webhook de NapCat peut encore envoyer des événements à `POST /v1/onebot`, et personagent répond via `QQ_ONEBOT_URL`. Cette route est obsolète et reste pendant toute la 1.x. Utilisez plutôt la connexion du bot QQ officiel, ou NapCat via AstrBot avec `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. La route avertit une fois à la première utilisation et marque chaque réponse avec `Deprecation: true`.

Pour passer à NapCat via AstrBot, ajoutez OneBot v11 (NapCat) sur la page locale, ou exécutez `personagent connect astrbot <AstrBot data dir> --qq` pour votre propre AstrBot et remplissez les listes d'autorisation. Pointez le client WebSocket de NapCat vers lui et désactivez le client HTTP de NapCat (gardez son serveur HTTP). La mémoire et l'apprentissage sont conservés, car `CONNECTOR_QQ_PLATFORMS` conserve les identifiants.

Si vous utilisez encore l'ancienne route :

- Configurez les deux sens comme le décrit la [documentation de NapCat](https://napneko.github.io/). Il vous faut un **serveur HTTP** à `QQ_ONEBOT_URL` pour l'envoi, et un **client HTTP** qui envoie à `http://127.0.0.1:8080/v1/onebot` (`SERVER_HOST`, `SERVER_PORT`). `QQ_ONEBOT_URL` est vide par défaut, alors écrivez-le dans `.env`. Sans lui, le bot reçoit mais ne répond jamais. La vérification préalable et `personagent doctor` avertissent quand cette route semble configurée (`QQ_BOT_ID` ou `QQ_ONEBOT_SECRET` défini, `CONNECTOR_QQ_PLATFORMS` vide) et que `QQ_ONEBOT_URL` est vide.
- Si NapCat est sur une autre machine, réglez `QQ_ONEBOT_SECRET` sur le `secret` du client HTTP. Sinon, quiconque atteint le port peut forger des événements. Les corps doivent alors porter `x-signature: sha1=<hex>` (403 `bad_signature`), et les événements horodatés à plus de cinq minutes d'écart reçoivent 403 `stale_event`. Sans le secret, la route ne répond qu'aux programmes sur cet hôte, et sur une écoute réseau elle est désactivée (403 `onebot_disabled`).
- Avec AstrBot sur le même compte, gardez `aiocqhttp` dans `excluded_platforms`, sinon chaque message arrive deux fois.

Vérifiez l'envoi avec `curl http://127.0.0.1:3000/get_login_info`. Vérifiez la réception en surveillant le journal de personagent pendant que vous écrivez au bot dans un groupe.
