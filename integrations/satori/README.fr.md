# Connecteur Satori

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · Français · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Ce connecteur relie [personagent](https://github.com/wangkant/personagent) à un serveur [Satori](https://satori.chat). Satori est un protocole de discussion multiplateforme. Un serveur comme [Koishi](https://koishi.chat) (avec son plugin `server-satori`), Chronocat ou LLOneBot se connecte aux plateformes de discussion, et un client comme celui-ci reçoit chaque message de chaque connexion par un seul websocket. Un seul processus de connecteur place donc la persona sur toutes les plateformes pour lesquelles le serveur a un adaptateur.

Satori et Koishi sont des logiciels tiers. personagent n'en a pas besoin pour QQ, WeChat, Telegram ou Discord, qu'il connecte lui-même, ni pour les plateformes que sa page locale configure via AstrBot. Utilisez ce connecteur si vous exécutez déjà Koishi, ou si vous voulez une plateforme que seul Koishi atteint.

Le connecteur transmet chaque message autorisé au `POST /v1/events` de l'agent sous forme d'événement neutre ([docs/connectors.md](../../docs/connectors.fr.md)) et renvoie les réponses via Satori. Il récupère aussi la boîte d'envoi de l'agent, donc les messages programmés, les questions de suivi et les excuses arrivent dans la discussion.

[satori-python](https://github.com/RF-Tar-Railt/satori-python) gère le côté Satori : le websocket, la liste des connexions et l'API HTTP. Ce connecteur fait le lien entre Satori et le format d'événements de personagent, et utilise [`integrations/sdk/personagent_connector.py`](../sdk/personagent_connector.py) pour la signature et la boucle de la boîte d'envoi.

## Configuration, avec Koishi

1. **Koishi.** Installez Koishi avec le lanceur de bureau ou `npm init koishi@latest`. Dans sa console, ajoutez et configurez un adaptateur pour votre plateforme, comme `adapter-telegram` ou `adapter-discord`, et vérifiez que le bot est en ligne. Activez les plugins `server` et `server-satori`. Koishi sert alors Satori à `http://127.0.0.1:5140/satori`. Donnez un `token` à `server-satori` si autre chose que cette machine peut atteindre ce port.

   Koishi continue d'exécuter ses autres plugins. Si l'un d'eux répond aussi aux messages, comme un modèle de discussion ou un plugin de réponse, il répondra en même temps que la persona, et le connecteur ne peut pas le faire taire. Désactivez ce plugin ou excluez-le des conversations que vous transmettez.

2. **L'agent.** Exécutez personagent (`personagent run`, voir son README). Si le connecteur et l'agent sont sur des hôtes différents, définissez `CONNECTOR_TOKEN` dans le `.env` de l'agent et placez l'agent derrière HTTPS. Définissez le jeton avant d'ajouter un proxy ou un tunnel, même sur un seul hôte.

3. **Le connecteur.** Le connecteur est un script de ce dépôt, il lui faut donc une copie du dépôt (un clone ou le ZIP de GitHub) et son propre environnement Python, car `satori-python` n'est pas une dépendance de personagent. Dans un clone qui a déjà le `.venv` de personagent, installez dans cet environnement :

   ```bash
   .venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   Si vous avez installé personagent depuis PyPI avec pip, ou si vous le lancez avec uvx, créez un venv séparé à côté de la copie :

   ```bash
   python -m venv connector-venv
   connector-venv/bin/python -m pip install -r integrations/satori/requirements.txt
   ```

   Sous Windows, l'interpréteur est `.venv\Scripts\python.exe` ou `connector-venv\Scripts\python.exe`. Ensuite, copiez le fichier de réglages :

   ```bash
   cp integrations/satori/.env.example integrations/satori/.env
   ```

   Dans `integrations/satori/.env`, définissez l'URL et le jeton du serveur Satori, l'URL de base et le `CONNECTOR_TOKEN` de l'agent, et les conversations à transmettre (voir [Listes d'autorisation](#listes-dautorisation)). Puis démarrez le connecteur avec le même interpréteur :

   ```bash
   .venv/bin/python integrations/satori/satori_connector.py
   ```

   `--config FILE` lit un autre fichier de réglages. Tout réglage peut aussi être donné en variable d'environnement, qui a priorité sur le fichier.

4. **Vérifiez que ça marche.** Pour chaque bot du serveur, le journal affiche une ligne comme `Satori login telegram:7000 is ONLINE`. Mentionnez le bot dans un groupe transmis. Le journal de l'agent montre le tour, et la réponse apparaît dans la discussion. Si rien ne se passe, définissez `SATORI_LOG_LEVEL=DEBUG`.

## Réglages

| Réglage | Défaut | Signification |
|---|---|---|
| `SATORI_URL` | `http://127.0.0.1:5140/satori` | Le serveur Satori. Le `/v1` final est facultatif. |
| `SATORI_TOKEN` | | Le jeton du serveur (dans Koishi, `server-satori` → `token`). |
| `PERSONAGENT_URL` | `http://127.0.0.1:8080` | L'URL de base de l'agent. `/v1/events` et `/v1/outbox` sont ajoutés. |
| `CONNECTOR_TOKEN` | | Le `CONNECTOR_TOKEN` de l'agent. |
| `SATORI_GROUPS` | | Groupes à transmettre, en ids de canal ou de serveur, éventuellement `platform:id`. Vide n'en transmet aucun, `*` les transmet tous. |
| `SATORI_DM_USERS` | | Personnes dont les messages privés sont transmis, en ids d'utilisateur, éventuellement `platform:id`. Vide n'en transmet aucun, `*` les transmet tous. |
| `SATORI_PLATFORMS` | toutes | Limite le connecteur à ces plateformes Satori. |
| `SATORI_PLATFORM_NAMES` | `qq=qqbot` | Renomme les plateformes telles que l'agent les voit : `satori_name=name, ...` |
| `SATORI_OUTBOX_ENABLED` | `true` | Récupérer la boîte d'envoi de l'agent. |
| `SATORI_CONNECTOR_ID` | d'après `SATORI_URL` | L'id de ce connecteur chez l'agent. Gardez-le stable. |
| `SATORI_TIMEOUT_S` | `420` | Durée maximale d'un tour. Gardez-la au-dessus de 3 × `LLM_TIMEOUT_S` de l'agent. |
| `SATORI_INLINE_IMAGES_ENABLED` | `false` | Télécharger les URL d'images publiques dans le connecteur au lieu de passer l'URL à l'agent. |
| `SATORI_LOG_LEVEL` | `INFO` | |

L'URL de l'agent doit être une adresse de bouclage, ou HTTPS avec `CONNECTOR_TOKEN` défini. Sinon, le connecteur refuse de démarrer. Si `SATORI_TOKEN` devait être envoyé en `http` non chiffré vers un autre hôte, le connecteur journalise un avertissement.

## Listes d'autorisation

Le connecteur refuse par défaut. Avec des listes vides, il ne transmet rien.

- Un groupe est un canal Satori. Il est transmis quand son id de canal ou de serveur figure dans `SATORI_GROUPS`. Sur Discord ou KOOK, un id de serveur admet donc tous les canaux de ce serveur, et chaque canal reste une conversation distincte.
- Un message privé est transmis quand l'id d'utilisateur de l'expéditeur figure dans `SATORI_DM_USERS`.
- Une entrée peut nommer sa plateforme, comme `telegram:-1001234` ou `discord:4242`, et ne correspond alors que sur cette plateforme. Une entrée sans plateforme correspond sur toutes.
- `*` transmet tous les groupes (ou tous les messages privés) et marque l'événement `prefiltered: false`. `ACCESS_GROUPS` et `ACCESS_DM_USERS` de l'agent décident alors, et une plateforme sans entrée y est refusée.

Le plugin `inspect` de Koishi affiche les ids de plateforme, de canal, de serveur et d'utilisateur d'un message.

## Noms de plateforme et QQ

personagent stocke les ids sous la forme `<platform>:<id>`, où la plateforme est celle de la connexion Satori (`telegram`, `discord`, `onebot`, etc.). La ligne de journal de l'étape 4 l'indique. Il y a deux cas particuliers :

- **QQ via OneBot** (le `adapter-onebot` de Koishi, avec NapCat ou LLOneBot derrière) utilise les numéros QQ comme ids. Pour conserver ce que l'agent a appris sur un déploiement QQ existant, ajoutez la plateforme au `CONNECTOR_QQ_PLATFORMS` de l'agent (`CONNECTOR_QQ_PLATFORMS=onebot`). Ses ids sont alors stockés sans préfixe, comme les numéros QQ de NapCat, et les entrées QQ de `ACCESS_GROUPS` et `ACCESS_DM_USERS` s'y appliquent. Ne le faites que pour une plateforme dont les ids sont vraiment des numéros QQ.
- **L'API officielle des bots QQ** (le `adapter-qq` de Koishi) appelle sa plateforme `qq`, mais ses ids sont des openids, pas des numéros QQ. Le connecteur renomme la plateforme en `qqbot`. `SATORI_PLATFORM_NAMES` remplace ce renommage. personagent peut aussi connecter lui-même les bots QQ officiels, sans Koishi.

## Ce qui fonctionne

| Fonction | État |
|---|---|
| Groupes et messages privés | Oui. Un message privé est un canal `DIRECT`, ou un message sans serveur. |
| Détection d'appel (`addressed`) | Un `<at>` du bot (par id, ou par son nom quand le serveur ne donne pas d'id), et une réponse à un message du bot. `@all` compte comme du texte, pas comme une mention. |
| Messages cités | Le texte cité, l'expéditeur et l'id, tirés d'un élément `<quote>` ou de `message.quote`. |
| Images reçues | Les images `data:` et `internal:`, ainsi que celles du serveur Satori, sont intégrées. Les URL publiques sont transmises pour que l'agent les récupère. Les URL de réseau privé sont décrites par `(sent an image)`. Au plus 4 téléchargements par message, de 4 Mo chacun. |
| Stickers et emoji | `<emoji>` et le `<face>` de QQ arrivent comme emoji, et la persona sait qu'elle ne peut pas les voir. |
| Voix, vidéo, fichiers | Décrits en mots : `(sent a voice message)`, `(sent a video)`, `(sent a file: deck.pdf)`. |
| Réponses | Du texte, et des images en URI `data:`, chacun envoyé comme message séparé avec un court intervalle. Dans les groupes, une mention demandée par l'agent devient un `<at>`. |
| Plateformes à réponse passive | Les réponses portent le `referrer` de l'événement, dont l'API officielle des bots QQ a besoin pour répondre à un message. |
| Boîte d'envoi | Les messages programmés, les suivis et les excuses vont au canal via la connexion qui a reçu la conversation. Le connecteur signe chaque identifiant de réponse avec une clé dérivée de `SATORI_TOKEN` et `CONNECTOR_TOKEN`, et n'envoie qu'aux identifiants qu'il a signés. Après le changement de l'un de ces jetons, une conversation redevient joignable une fois qu'elle a envoyé un message. Un agent avec `CONNECTOR_OUTBOX_ENABLED=false` répond 404, et le connecteur réessaie toutes les 10 minutes. |
| Indicateur de saisie | Non. Satori n'a pas d'API de saisie. |
| `owned` | Respecté : le connecteur n'envoie rien d'autre. Il ne peut pas arrêter les autres plugins de Koishi (voir l'étape 1). |

Les règles des plateformes s'appliquent toujours. L'API officielle des bots QQ, par exemple, limite strictement les messages qu'un bot peut envoyer spontanément, donc les livraisons de la boîte d'envoi peuvent y revenir `failed`.

## Tests

`tests/test_satori_connector.py` s'exécute sans satori-python et sans réseau. Il simule les objets d'éléments, le compte et l'agent.
