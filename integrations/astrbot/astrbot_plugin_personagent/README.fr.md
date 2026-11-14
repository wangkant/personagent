# astrbot_plugin_personagent

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · Français · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Ce plugin [AstrBot](https://github.com/AstrBotDevs/AstrBot) relie AstrBot à [personagent](https://github.com/wangkant/personagent). Il transmet chaque message autorisé à l'agent et renvoie les réponses de l'agent dans la discussion.

## En avez-vous besoin ?

Il n'est pas nécessaire pour QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK ou Stoat. personagent connecte lui-même ces plateformes, sans AstrBot. Exécutez `personagent` pour ouvrir sa page locale et ajoutez-les sous **Connecter des plateformes**, ou exécutez `personagent connect <plateforme>` dans un terminal.

Ce plugin est nécessaire lorsque AstrBot achemine la conversation, ce qui se produit dans deux cas.

- **Vous ajoutez une autre plateforme sur la page de personagent.** KOOK, Feishu/Lark, DingTalk, Slack, le bot IA WeCom, Mattermost, Misskey et les plateformes sous Avancé passent tous par AstrBot. La page télécharge et exécute un AstrBot pour vous et y installe ce plugin : vous n'avez rien à faire ici.
- **Vous exécutez déjà un AstrBot** avec ses propres plateformes et plugins. Installez le plugin comme décrit ci-dessous.

## Ce qu'il fait

- Reçoit les messages de groupe et les messages privés de tous les adaptateurs de plateforme d'AstrBot (Telegram, Discord, Slack, QQ...), sauf ceux de `excluded_platforms`.
- Transmet les messages des groupes et expéditeurs de la liste d'autorisation au `POST /v1/events` de l'agent sous forme d'événement neutre vis-à-vis de la plateforme. Il lit chaque plateforme comme son adaptateur la livre, y compris le destinataire, ce qui est cité, les autocollants, les images, les messages vocaux et l'heure d'envoi indiquée par la plateforme.
- Renvoie les réponses de l'agent via AstrBot sous la forme attendue par chaque plateforme. Les réponses peuvent contenir du texte et des images et, dans les discussions de groupe, une mention quand l'agent la demande.
- Interroge la boîte d'envoi de l'agent pour livrer ce qu'il dit de lui-même, comme un message programmé, une question de suivi ou l'excuse qu'il publie dans un groupe quand son modèle est en panne. Voir [Boîte d'envoi](#boîte-denvoi).
- Arrête le pipeline propre d'AstrBot quand l'agent prend la conversation (`block_default`), pour que le modèle intégré d'AstrBot ne réponde jamais à la place du personnage.

Le personnage, la mémoire, le debounce et la simulation de saisie s'exécutent tous dans l'agent. Ce plugin est un connecteur au sens du [`docs/connectors.md`](https://github.com/wangkant/personagent/blob/main/docs/connectors.fr.md) de l'agent.

## Installer dans votre propre AstrBot

Vous avez besoin d'AstrBot, démarré au moins une fois pour que son dossier de données existe, et personagent (`python -m pip install personagent` ; voir son README).

### Avec la configuration de personagent

```bash
personagent connect astrbot
```

La commande cherche d'abord le dossier de données d'AstrBot, celui qui contient `cmd_config.json`, `plugins/` et `config/`. Si elle n'en trouve aucun, elle propose de télécharger AstrBot. Elle demande ensuite si AstrBot s'exécute dans Docker, quelle plateforme de discussion le bot rejoint (avec le jeton de cette plateforme lorsque AstrBot en a encore besoin), les groupes, l'administrateur et les personnes autorisées à écrire au bot en privé. Pour QQ via NapCat, elle demande aussi le numéro du compte du bot. Enfin, elle copie ce plugin, génère un jeton partagé, l'écrit des deux côtés et écrit les listes d'autorisation. `personagent init --terminal` propose la même étape à la fin.

Pour éviter les questions, passez le dossier de données :

```bash
personagent connect astrbot <AstrBot data dir>        # add --qq to route QQ (NapCat) as well
```

Exécutée ainsi, une première connexion laisse les listes d'autorisation **vides**, et vous les remplissez dans les réglages du plugin. `personagent connect astrbot --help` liste les options qui activent aussi une plateforme dans AstrBot.

Vous pouvez relancer la commande à tout moment. Elle conserve les listes d'autorisation, les autres plateformes exclues et tout `personagent_url` que ce plugin accepte (voir [Où l'agent peut s'exécuter](#où-lagent-peut-sexécuter)). Un `personagent_url` que le plugin refuserait est remplacé par la valeur de bouclage par défaut. Le routage QQ ne change que si vous passez `--qq` ou `--no-qq`, et le `CONNECTOR_QQ_PLATFORMS` de l'agent suit. Quand elle pose la question, les listes actuelles sont les valeurs par défaut : appuyez sur Entrée pour en garder une, ou tapez `-` pour la vider.

Redémarrez ensuite AstrBot et démarrez l'agent (voir [Vérifier que cela fonctionne](#vérifier-que-cela-fonctionne)).

### Depuis la WebUI d'AstrBot

1. Téléchargez `astrbot_plugin_personagent.zip` depuis la [dernière version de personagent](https://github.com/wangkant/personagent/releases/latest).
2. Envoyez-le sous **Install from File** sur la page des plugins d'AstrBot.
3. Réglez `connector_token` sur le `CONNECTOR_TOKEN` du `.env` de personagent et remplissez les listes d'autorisation comme décrit ci-dessous.
4. Si AstrBot s'exécute sur un autre ordinateur que personagent, réglez `personagent_url` sur une adresse HTTPS (voir [Où l'agent peut s'exécuter](#où-lagent-peut-sexécuter)).

Pour mettre à jour, envoyez le zip de la version la plus récente de la même façon. AstrBot 4.29 et les versions ultérieures remplacent la copie installée. Sur les versions plus anciennes, désinstallez d'abord le plugin et laissez **Also delete plugin configuration file** décoché.

### À la main

1. Copiez ce dossier vers `<AstrBot data dir>/plugins/astrbot_plugin_personagent/`.
2. Redémarrez AstrBot ou rechargez les plugins dans sa WebUI. AstrBot installe `requirements.txt`, qui ne liste que `httpx`.
3. Ouvrez les réglages du plugin dans la WebUI. Ils sont enregistrés dans `<AstrBot data dir>/config/astrbot_plugin_personagent_config.json`.
   - Ajoutez à `groups` les ID des groupes que le personnage peut rejoindre.
   - Ajoutez à `dm_users` les ID des expéditeurs aux messages privés desquels il peut répondre.
   - Si le `.env` de l'agent définit `CONNECTOR_TOKEN`, mettez la même valeur dans `connector_token`. C'est obligatoire quand l'agent est sur un autre hôte.
   - Laissez `personagent_url` à sa valeur par défaut lorsque l'agent s'exécute sur le même hôte avec le `SERVER_PORT=8080` par défaut.

Le plugin **refuse par défaut**. Avec des listes vides, il ne transmet rien, et AstrBot se comporte comme si le plugin n'était pas installé. Écrivez les ID comme AstrBot les affiche ; envoyez `/sid` dans une discussion pour les voir. Un ID sans préfixe correspond sur tous les adaptateurs. `qq_official:ID` ne correspond que sur cet adaptateur, et `qq_official:*` y transmet toutes les conversations de ce type.

Un `*` seul dans `groups` ou `dm_users` transmet toutes les conversations de ce type sur tous les adaptateurs et les marque `prefiltered: false`. `ACCESS_GROUPS` et `ACCESS_DM_USERS` de l'agent décident alors seuls. L'agent refuse une plateforme qui n'y figure pas, sauf les groupes QQ, auxquels il répond à moins que `ACCESS_GROUPS` en liste.

### Vérifier que cela fonctionne

1. Démarrez l'agent avec `personagent run`, qui ne démarre que le serveur. Sa bannière doit afficher `agent: on`.
2. Dites le nom du bot (le `PERSONA_NAME` de l'agent) dans un groupe autorisé.

Si aucune réponse n'arrive, cherchez les lignes `personagent:` dans le journal d'AstrBot, lisez ce que `personagent run` a affiché après sa bannière, puis consultez [Dépannage](#dépannage).

## Configuration

| Clé | Type | Défaut | Description |
| --- | --- | --- | --- |
| `personagent_url` | string | `http://127.0.0.1:8080` | URL de base de l'agent. Le plugin ajoute `/v1/events` et `/v1/outbox`. Doit être en bouclage, ou en HTTPS avec `connector_token` défini. |
| `connector_token` | string | `""` | Secret partagé. Doit correspondre au `CONNECTOR_TOKEN` de l'agent. Obligatoire pour tout `personagent_url` hors bouclage. |
| `timeout_s` | int | `420` | Secondes d'attente pour chaque tentative. Voir [Délais](#délais). |
| `excluded_platforms` | list | `["aiocqhttp"]` | Noms d'adaptateurs jamais transmis. Retirez `aiocqhttp` pour faire passer QQ (NapCat) par ce plugin. Voir [QQ via NapCat](#qq-via-napcat). |
| `groups` | list | `[]` | ID de groupe à transmettre. Vide ne transmet aucun groupe. `adapter:ID` ou `adapter:*` limite une entrée à un adaptateur. Un `*` seul transmet tous les groupes sans filtre. |
| `dm_users` | list | `[]` | ID d'expéditeur dont les messages privés sont transmis. Vide n'en transmet aucun. `adapter:ID` ou `adapter:*` limite une entrée à un adaptateur. Un `*` seul transmet tous les messages privés sans filtre. |
| `block_default` | bool | `true` | Arrête le pipeline d'AstrBot quand l'agent prend la conversation. |
| `forward_quoted_text` | bool | `true` | Envoie le texte et l'auteur d'un message cité avec son id, quand la plateforme les fournit. Tant que ce réglage est actif et que `quote_max_chars` est supérieur à 0, chaque événement déclare la capacité `quote_text`. |
| `quote_max_chars` | int | `200` | Longueur maximale du texte cité envoyé. Les citations plus longues sont coupées. |
| `max_inline_image_bytes` | int | `4000000` | Plus grande image envoyée en ligne. Les images que l'agent ne peut pas récupérer lui-même (Telegram, fichiers locaux, adresses privées) sont envoyées en ligne. Une image plus grande arrive sous la forme de la note `(sent an image)`. Gardez cette valeur sous le `VISION_MAX_IMAGE_BYTES` de l'agent. |
| `outbox_enabled` | bool | `true` | Interroge et livre la boîte d'envoi de l'agent. Voir [Boîte d'envoi](#boîte-denvoi). |
| `outbox_wait_s` | int | `25` | Durée d'attente maximale d'une interrogation de la boîte d'envoi auprès de l'agent, 30 au plus. |
| `connector_id` | string | `""` | Nom de cet AstrBot pour l'agent. Vide en génère un une fois et le conserve. Deux hôtes AstrBot ont besoin de noms différents. |

### Où l'agent peut s'exécuter

- **Même hôte**, ou conteneur partageant l'espace de noms réseau de l'hôte ou utilisant le réseau de l'hôte : gardez le `personagent_url` de bouclage par défaut.
- **Autre conteneur ou hôte** : utilisez un `personagent_url` HTTPS et définissez le même secret non vide dans `connector_token` et le `CONNECTOR_TOKEN` de l'agent. Un tunnel privé qui aboutit à une URL de bouclage visible par AstrBot convient aussi. Définissez aussi dans ce cas le même jeton des deux côtés, car l'agent refuse les requêtes sans jeton arrivant par un proxy.

Le plugin refuse le `http://` en clair vers tout ce qui n'est pas le bouclage, comme `http://host.docker.internal:8080`, même avec un jeton. Chaque message journalise alors `refusing unsafe personagent_url`, et le modèle propre d'AstrBot répond à la place.

**AstrBot dans Docker.** Dans un conteneur, `127.0.0.1` est le conteneur lui-même, donc le `personagent_url` par défaut n'atteint rien. Vous avez deux options :

- Donnez à AstrBot le réseau de l'hôte : `network_mode: host` dans son fichier compose, ou `docker run --network host`. Docker Desktop nécessite la version 4.34 ou ultérieure avec host networking activé. Un conteneur NapCat dans le même fichier compose a aussi besoin du réseau de l'hôte.
- Placez l'agent derrière HTTPS et définissez cette adresse comme `personagent_url` (`personagent connect astrbot <dir> --url https://...`).

L'agent écoute sur `127.0.0.1:8080` par défaut. Si vous réglez son `SERVER_HOST` sur une adresse hors bouclage, il refuse de démarrer sans `CONNECTOR_TOKEN`. Définissez le jeton avant de placer un proxy ou un tunnel devant l'agent, même sur un seul hôte.

### Délais

Chaque requête dure autant que le tour de l'agent, soit un court debounce plus chaque appel au modèle et chaque nouvel essai. Si `timeout_s` expire, l'agent termine quand même le tour et garde ce qu'il a appris, mais la réponse est perdue et le modèle propre d'AstrBot répond au message.

Gardez 3 × `LLM_TIMEOUT_S` de l'agent sous `timeout_s`. Les appels au modèle d'un tour se partagent 1,5 × `LLM_TIMEOUT_S`, nouvelles tentatives comprises, et un message attend d'abord le tour qui réfléchissait à son arrivée. Avec la valeur par défaut de l'agent (`LLM_TIMEOUT_S=120`), cela fait 360 s, ce que couvre le `timeout_s` par défaut de 420. Si vous augmentez `LLM_TIMEOUT_S` sur l'agent, augmentez aussi `timeout_s`.

Le plugin réessaie un 429 ou un 500 de l'agent jusqu'à deux fois, en respectant `Retry-After` sur un 429, tant que la requête signée reste récente.

### `block_default` et propriété

Le plugin arrête le pipeline d'AstrBot chaque fois que l'agent signale que la conversation est la sienne (`owned: true`), qu'il ait répondu ou non, afin que le modèle intégré d'AstrBot n'intervienne pas dans les tours où le personnage se tait.

Les erreurs de transport, les réponses invalides et les conversations que l'agent refuse continuent vers le pipeline normal d'AstrBot. Si la réponse de l'agent n'a pas de champ `owned`, le plugin utilise `handled`.

## QQ via NapCat

personagent connecte lui-même les bots officiels QQ, sans AstrBot. Cette section ne couvre qu'un compte QQ exécuté via NapCat (ou une autre implémentation de OneBot v11) derrière l'adaptateur `aiocqhttp` d'AstrBot. Quand vous ajoutez OneBot v11 sur la page de personagent, elle retire `aiocqhttp` de `excluded_platforms` et définit `CONNECTOR_QQ_PLATFORMS` pour vous.

1. Retirez `aiocqhttp` de `excluded_platforms` et ajoutez les groupes QQ à `groups`.
2. Dans le `.env` de l'agent, définissez `CONNECTOR_QQ_PLATFORMS=aiocqhttp` et `QQ_BOT_ID` (le numéro du compte du bot).
3. Facultatif : réglez le `QQ_ONEBOT_URL` de l'agent sur le serveur HTTP de NapCat. Cela active le rattrapage des mentions manquées, qui a aussi besoin de `QQ_BOT_ID`. Les messages proactifs, la question de suivi après un refus et l'excuse d'un groupe quand le modèle échoue passent par la [boîte d'envoi](#boîte-denvoi) de ce plugin tant qu'il interroge. Sinon, ils passent directement par NapCat, à condition que cette URL soit définie.
4. Si NapCat publie aussi sur le `/v1/onebot` de l'agent, désactivez-le. Cette route est obsolète, et l'exécution simultanée des deux livre chaque message deux fois.

`personagent connect astrbot <data dir> --qq` retire `aiocqhttp` de `excluded_platforms` et définit `CONNECTOR_QQ_PLATFORMS`. Exécutée sans dossier, elle demande aussi `QQ_BOT_ID`. Le guide de déploiement couvre aussi cette voie : [docs/deploy.md](https://github.com/wangkant/personagent/blob/main/docs/deploy.fr.md#qq-via-napcat-onebot).

N'omettez pas `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. Sans lui, l'agent range les discussions QQ sous des ID préfixés par `aiocqhttp:`, ce qui a été appris sous les ID QQ sans préfixe ne correspond plus, et les registres ne peuvent pas être réindexés ensuite.

Comme les ID QQ restent sans préfixe, les réglages QQ de l'agent continuent de s'y appliquer. Les entrées QQ de `ACCESS_GROUPS` filtrent les groupes (aucune entrée signifie tous les groupes QQ), et seuls les messages privés de l'administrateur dans `ADMIN_IDS` ou des personnes dans `ACCESS_DM_USERS` reçoivent une réponse. L'assistant de configuration écrit les groupes QQ que vous lui indiquez dans le `.env` de l'agent. Pour ajouter un groupe QQ plus tard, ajoutez-le à la fois à `groups` et à `ACCESS_GROUPS`, ou ne listez aucun groupe QQ dans `ACCESS_GROUPS`.

Avant qu'AstrBot n'achemine un groupe QQ actif, vérifiez deux réglages d'AstrBot. Tous deux s'exécutent avant les gestionnaires de plugins.

- `platform_settings.rate_limit` vaut par défaut 30 messages par 60 s. Les messages au-delà sont retardés, pas supprimés. Augmentez ou désactivez la limite.
- `content_safety.internal_keywords` est actif par défaut et supprime les messages correspondant à sa liste de mots-clés, y compris ceux auxquels le personnage aurait répondu. Vérifiez la liste.

## Plateformes

L'agent parle un format neutre, et le plugin traduit aux frontières avec les mécanismes propres à chaque plateforme. Le tableau ci-dessous a été vérifié avec les adaptateurs d'AstrBot 4.25.5.

Sur toutes les plateformes :

- Seuls les messages écrits par une personne sont transmis. Les notifications QQ (pokes, rappels, arrivées) et les demandes, ainsi que les arrivées et changements de sujet Slack, ne sont pas des tours.
- Les vidéos, fichiers et messages vocaux arrivent sous forme de note à laquelle le personnage peut réagir, comme `(sent a video)`, `(sent a file: deck.pdf)` ou `(sent a voice message)`, avec la transcription de la plateforme quand elle en a une.
- Les messages cités portent leur texte et leur auteur quand la plateforme les fournit (`forward_quoted_text`).
- Là où l'adaptateur la conserve, l'heure du message est celle de la plateforme et non l'heure de réception par AstrBot.
- Les réponses sont découpées sous la limite de longueur de la plateforme, en comptant la mention et les échappements comme la plateforme. Elles ne deviennent jamais une image de texte, et désignent les personnes comme le fait la plateforme.
- La boîte d'envoi n'est utilisée que là où la plateforme peut envoyer sans sollicitation.

| Plateforme (adaptateur) | Ce qui fonctionne | Ce que la plateforme ne peut pas faire |
| --- | --- | --- |
| QQ via OneBot (`aiocqhttp`) | Groupes et messages privés. @ et réponse au bot, aussi quand l'adaptateur n'a pas pu résoudre le @. Noms des émoticônes, autocollants de boutique (`mface`) et images marquées comme autocollants. Mentions sous forme d'un vrai @ QQ, suivi d'une espace. Les longues réponses sont découpées sous le `forward_threshold` d'AstrBot, donc aucune ne devient une carte de transfert groupé. Boîte d'envoi. | Le Markdown s'affiche tel que saisi. |
| QQ officiel (`qq_official`, `qq_official_webhook`) | Messages de groupe qui font @ au bot, et messages privés. Émoticônes sous forme `[表情:name]`. Les réponses demandent du texte brut au lieu du markdown de l'adaptateur. | Les groupes ne livrent que les messages qui font @ au bot, donc le personnage ne peut pas suivre une conversation. Pas de citations, pas de noms (seulement des openids), pas de mentions dans les réponses. Répondre n'est possible que dans les 5 minutes suivant un message, donc pas de boîte d'envoi. |
| Telegram (`telegram`) | Groupes, sujets (`<chat>#<thread>`) et messages privés. Réponse au bot pour tout type de message, sans le préfixe de réveil `/@bot` de l'adaptateur. Emoji des autocollants, plus l'image des autocollants statiques. Images récupérées via le bot de l'adaptateur, donc le jeton du bot ne quitte jamais AstrBot. Un nom d'utilisateur mentionné devient l'id numérique de la personne une fois qu'elle a écrit. Les réponses mentionnent par nom d'utilisateur, ou par un lien `tg://user` pour qui n'en a pas, et affichent `*`, `_` et caractères semblables tels que saisis. Boîte d'envoi. | Avec le mode de confidentialité de BotFather actif (par défaut), les groupes ne livrent que les commandes, @mentions et réponses au bot. Désactivez-le pour que le personnage puisse suivre la conversation. Les autocollants animés et vidéo ne peuvent pas être vus. |
| Discord (`discord`) | Salons et fils comme groupes, et messages privés. Un `@bot` initial (que l'adaptateur retire), un ping d'un des rôles du bot et les réponses au bot s'adressent tous à lui. Citations avec leur texte. Autocollants. Pièces jointes vocales et vidéo sous forme de notes. Mentions sous forme `<@id>`, avec `@everyone` et `@here` rendus inertes. Réponses découpées à 2000 caractères. Boîte d'envoi, messages privés compris. | Nécessite l'intent Message Content. |
| Slack (`slack`) | Canaux et messages privés. Une réponse de fil sous le message du bot s'adresse à lui. Liens dépliés. Les id de message sont le `ts` de Slack. Mentions sous forme `<@id>`. `&`, `<` et `>` échappés pour que le texte ne puisse pas notifier un canal. Réponses découpées à 3000 caractères. Boîte d'envoi. | Une réponse de fil ne porte pas le texte du parent. Pas d'indicateur de saisie pour les bots. Les réponses atterrissent dans le canal, pas dans le fil (adaptateur). |
| KOOK (`kook`) | Canaux et messages privés. @ et pings d'un rôle que le bot détient. Citations quand KOOK les inclut. Emoji `(emj)` et heure réelle d'envoi. Mentions dans le texte, avec les balises de style `(met)` du texte du personnage rendues inertes. Images envoyées comme fichier, car l'adaptateur n'envoie que du JPEG base64. Boîte d'envoi. | L'adaptateur d'AstrBot supprime les messages simples d'image, de fichier, de voix et de vidéo (pas les cartes) avant qu'un plugin les voie. Pas d'indicateur de saisie. |
| Lark / Feishu (`lark`) | Groupes et messages privés. @ et réponses au bot (Lark nomme l'application comme expéditeur). Citations avec leur texte. Autocollants sous forme d'emoji. Boîte d'envoi. | Sans le droit « lire tous les messages du groupe », seuls les messages avec @ arrivent. Chaque réponse cite le message auquel elle répond, et le markdown est rendu (adaptateur). Les noms sont des préfixes d'id. |
| DingTalk (`dingtalk`) | Groupes et messages privés. Les images, que l'adaptateur remet comme fichiers locaux, sont envoyées en ligne. Vidéos sous forme de note. Boîte d'envoi. Les messages privés atteignent les personnes qui ont écrit au bot. | Les groupes ne livrent que les messages qui font @ au bot. Pas de citations, ni de mentions ou de réponses citées dans les réponses. Chaque réponse est du markdown intitulé "AstrBot" (adaptateur). |
| LINE (`line`) | Groupes, salons et messages privés. @ au bot. Id de citation. Mots-clés des autocollants. Les bulles d'un tour partent en un appel, cinq à la fois, pour que le reply token gratuit les couvre. Boîte d'envoi, qui compte sur le quota de push. | LINE n'envoie pas le texte cité. Pas de mentions dans les réponses (adaptateur). Les images sortantes nécessitent un `callback_api_base` HTTPS public. Les noms sont des préfixes d'id. |
| Mattermost (`mattermost`) | Canaux et messages privés. @ au bot. La racine du fil comme citation. Images en ligne. Mentions par nom d'utilisateur une fois que la personne a écrit. `@channel`, `@all` et `@here` rendus inertes. Réponses découpées à 4000 caractères. Boîte d'envoi. | Le texte cité exigerait une recherche que le plugin ne fait pas. Pas d'indicateur de saisie. |
| Misskey (`misskey`) | Messages privés de la messagerie Chat et salons, avec `@bot` n'importe où dans un message de salon. Mentions sous forme `@user@host` une fois que la personne a écrit, tout autre `@` du texte du personnage étant rendu inerte. Réponses découpées à 3000 caractères. Boîte d'envoi pour la messagerie Chat et les salons. | Les notes (publications publiques) ne sont pas transmises, car AstrBot les classe comme événements système et une réponse serait publique. `unique_session` casse les salons (adaptateur). |
| Satori (`satori`) | Ce que le backend Satori relie : groupes, messages privés, @, réponses au bot, citations avec texte. Horodatages en millisecondes lus comme des secondes. Boîte d'envoi. | L'id de groupe est la guilde, donc les salons d'une guilde partagent une conversation. Les limites de la plateforme reliée s'appliquent. |
| WebChat (`webchat`) | La discussion du tableau de bord, comme messages privés. Citations et images. Boîte d'envoi, affichée en direct ou enregistrée dans la conversation. | Discussions individuelles uniquement. |
| Application WeCom (`wecom`) | Messages privés, images et voix avec sa transcription. Le mode service client ne transmet que les messages du client, avec l'heure réelle d'envoi. Réponses découpées par octets. Boîte d'envoi en mode application, une fois que quelqu'un a écrit depuis le démarrage d'AstrBot. | Messages privés seulement, pas de citations. Le mode service client ne peut pas envoyer sans sollicitation. Le Markdown s'affiche tel que saisi. |
| Bot IA WeCom (`wecom_ai_bot`) | Groupes (WeCom ne livre un message de groupe que quand le bot est mentionné par @) et messages privés. Notes de voix, de fichier et de vidéo. Un tour envoyé comme une seule réponse en flux. | Ne répond qu'à l'intérieur de la réponse à un message, donc ni boîte d'envoi ni mentions. La réponse est rendue en markdown. Définissez `wecom_ai_bot_name` dans AstrBot pour que "@bot" soit retiré du texte. |
| Compte officiel WeChat (`weixin_official_account`) | Messages privés et voix avec sa transcription. Un tour envoyé comme un seul message. | Le mode passif livre une réponse par message d'utilisateur, dans la fenêtre de 5 s de WeChat. Le reste attend le message suivant de l'utilisateur, et un tour où le personnage se tait laisse l'utilisateur en attente (adaptateur). Images en mode actif seulement. Pas de boîte d'envoi. |
| WeChat personnel (`weixin_oc`) | Messages privés. Citations avec leur texte. Images en ligne. Voix avec sa transcription. Indicateur de saisie. Boîte d'envoi. | Pas de groupes. Après une reconnexion, personne n'est joignable avant d'avoir réécrit. |
| Tout autre adaptateur | Transmis comme AstrBot le livre. Mentions sous forme d'At. | Pas de boîte d'envoi déclarée. |

## Boîte d'envoi

Certains messages ne répondent à rien : un message programmé, la question de suivi après un refus ou l'excuse dans un groupe quand le modèle est en panne. (L'excuse d'un message privé revient dans la réponse à l'événement.) L'agent met ces messages en file, et ce plugin les récupère sur `POST <personagent_url>/v1/outbox` avec la même signature que les événements, donc l'agent n'a jamais besoin d'atteindre AstrBot. La boîte d'envoi est active par défaut (`outbox_enabled`).

- Chaque livraison part par la session AstrBot de la conversation, dans l'ordre, et chaque message est envoyé au plus une fois.
- Une livraison ne va qu'à une session que le plugin a lui-même tirée d'un message de cette même conversation. Ces sessions sont conservées dans le stockage de plugins d'AstrBot, donc elles survivent à un rechargement. Rien d'autre qui publie un événement à l'agent ne peut diriger la boîte d'envoi vers une autre discussion, et le plugin refuse une telle livraison.
- Le plugin revérifie les listes d'autorisation et `excluded_platforms` à l'envoi et refuse une conversation retirée entre-temps.
- Les plateformes qui ne peuvent pas parler en premier (voir le tableau) ne reçoivent jamais de messages de la boîte d'envoi, car le plugin ne la déclare pas pour leurs conversations.
- Un agent sans boîte d'envoi répond 404. Le plugin redemande toutes les dix minutes.

L'agent connaît cet AstrBot par `connector_id`, que le plugin génère une fois et conserve. Deux hôtes AstrBot parlant à un même agent ont besoin d'id différents.

## Authentification des requêtes

Quand `connector_token` est défini, chaque requête porte quatre en-têtes :

- `X-Personagent-Token` : le jeton.
- `X-Personagent-Timestamp` : secondes unix.
- `X-Personagent-Nonce` : une nouvelle valeur aléatoire.
- `X-Personagent-Signature` : `sha256=` suivi du HMAC-SHA256 hexadécimal, avec le jeton comme clé, de `timestamp + "." + nonce + "." + body`.

Le corps est du JSON canonique : UTF-8, clés triées, séparateurs compacts et caractères non ASCII non échappés. La signature couvre ces octets exacts, donc un proxy ne doit pas réécrire le corps. L'agent rejette une mauvaise signature, un nonce réutilisé ou un horodatage à plus de cinq minutes de sa propre horloge. Gardez les deux horloges synchronisées.

Le corps porte aussi l'heure du message selon l'adaptateur sous `sent_at`. L'agent la vérifie séparément avec `CONNECTOR_MAX_EVENT_AGE_S` (24 heures par défaut), donc un ancien événement renvoyé avec une nouvelle signature reste rejeté. Le plugin ne transmet pas un message dont l'adaptateur ne donne pas d'horodatage valide, et AstrBot le traite comme d'habitude. Le personnage voit chaque message avec cette heure, et un message de groupe qui date de plus de 10 minutes à son arrivée, comme un arriéré qu'AstrBot remet après un redémarrage, est conservé comme contexte et ne reçoit pas de réponse.

## Identités côté agent

L'agent préfixe chaque id transmis par sa plateforme, sous la forme `<platform>:<raw id>` (par exemple `telegram:12345`), donc les id de plateformes différentes n'entrent jamais en collision. Les plateformes listées dans `CONNECTOR_QQ_PLATFORMS` gardent des id sans préfixe. `ADMIN_IDS`, `ACCESS_GROUPS` et `ACCESS_DM_USERS` de l'agent prennent des id de la même forme. Par exemple, `ADMIN_IDS=telegram:12345` fait de ce compte l'administrateur sur Telegram, en groupe et en privé. Une plateforme avec des entrées dans `ACCESS_GROUPS` ou `ACCESS_DM_USERS` est filtrée par l'agent en plus des listes d'autorisation de ce plugin.

## Dépannage

Les lignes du plugin dans le journal d'AstrBot commencent par `personagent:`.

| Message du journal | Que faire |
| --- | --- |
| `refusing unsafe personagent_url` | `personagent_url` est du HTTP en clair vers un autre hôte, ou du HTTPS sans `connector_token`. Voir [Où l'agent peut s'exécuter](#où-lagent-peut-sexécuter). |
| `agent refused the request (403): invalid request envelope: …` | `connector_token` est vide ou ne correspond pas au `CONNECTOR_TOKEN` de l'agent, les deux horloges diffèrent de plus de cinq minutes, ou un proxy a modifié le corps. Si le journal de l'agent indique `connector replay guard full`, attendez qu'il se vide. |
| `agent refused the request (403): stale or invalid sent_at` | Le message est plus ancien que le `CONNECTOR_MAX_EVENT_AGE_S` de l'agent. Cela arrive généralement après qu'AstrBot a livré un arriéré. |
| `agent refused the request (403): authentication required` ou `... only local requests accepted` | L'agent n'a pas de `CONNECTOR_TOKEN` et la requête n'est pas locale. Définissez le même jeton des deux côtés. |
| `agent at capacity (429)` | L'agent exécutait déjà `CONNECTOR_MAX_INFLIGHT` tours et a encore refusé le message après les nouveaux essais, donc le modèle propre d'AstrBot a répondu. Augmentez `CONNECTOR_MAX_INFLIGHT` si cela arrive souvent. |
| `agent rejected the body as too large (413)` | Généralement une grande image en ligne. Augmentez le `SERVER_MAX_BODY_BYTES` de l'agent. |
| `agent rejected the event schema (400)` | L'événement n'avait pas d'id de message ou d'expéditeur (certains adaptateurs les omettent), ou ce plugin a un bug. Signalez-le avec la ligne du journal. |
| `timed out waiting for the agent` | Voir [Délais](#délais). |
| `dropping event without a valid time the platform sent it` | L'adaptateur n'a pas donné d'horodatage. AstrBot traite ce message lui-même. |
| `agent request failed: ...` ou `agent request failed (<status>)` | Généralement, l'agent n'est pas en cours d'exécution ou `personagent_url` est incorrect. Un 404 signifie un mauvais chemin : `personagent_url` est l'URL de base, sans `/v1/events`. Un 500 signifie que l'agent a échoué, consultez donc son journal. |
| `outbox off: ...` | La boîte d'envoi suit la même règle de `personagent_url` que les événements. Voir la première ligne. |
| `outbox: agent has no outbox (turned off, or an older version); retrying in 10 minutes` | Le `CONNECTOR_OUTBOX_ENABLED` de l'agent est désactivé. |
| `outbox: outbox pull refused (403)` ou `outbox pull failed: ...` | Mêmes causes que pour les événements : le jeton, les horloges ou l'agent qui n'est pas en cours d'exécution. Le plugin espace ses essais jusqu'à une minute. |
| `outbox: no running platform '<id>'` | Une livraison pour un adaptateur désactivé ou renommé dans AstrBot. Le plugin la signale à l'agent comme échouée. |
| `could not store connector_id` | Le stockage de plugins d'AstrBot a échoué. Définissez `connector_id` vous-même, sinon l'agent verra un nouvel AstrBot après chaque redémarrage. |

Si le modèle propre d'AstrBot répond soudain d'une autre voix, le plugin n'a pas atteint l'agent ou l'agent n'a pas pris la conversation. Vérifiez le tableau ci-dessus, puis exécutez `personagent doctor`. Si la page locale a démarré l'agent, ouvrez-y **Activité** pour voir si le message est arrivé et pourquoi le personnage s'est tu. Si vous l'avez démarré avec `personagent run`, lisez son terminal.

Si le journal de l'agent indique que le connecteur envoie `X-Personagent-Token` mais que `CONNECTOR_TOKEN` est vide, l'agent ignore le jeton. Définissez la même valeur dans le `.env` de l'agent.

Sur QQ, Telegram, Discord, KOOK, QQ officiel et Misskey, l'heure du message est celle de la plateforme, pas l'heure de réception par AstrBot. Quand AstrBot a été arrêté plus longtemps que le `CONNECTOR_MAX_EVENT_AGE_S` de l'agent, l'agent refuse comme périmé l'arriéré que livre AstrBot.

## Limitation connue : mentions Telegram

L'adaptateur Telegram d'AstrBot identifie un expéditeur par id numérique d'utilisateur (`telegram:<numeric id>`), mais identifie une mention `@username` dans un message uniquement par nom d'utilisateur. Le plugin réécrit un nom d'utilisateur mentionné en id numérique de la personne qui l'utilise une fois qu'elle a écrit depuis le démarrage d'AstrBot. D'ici là, la mention atteint l'agent sous le nom d'utilisateur.

Les réponses mentionnent quelqu'un par nom d'utilisateur, ou avec un lien `tg://user` s'il n'en a pas. Le plugin ne mentionne pas une personne qu'il n'a pas vue depuis le démarrage d'AstrBot.
