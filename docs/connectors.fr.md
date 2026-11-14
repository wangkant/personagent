# Protocole des connecteurs

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · Français · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

L'agent ne parle jamais lui-même à une plateforme de discussion. C'est le travail d'un connecteur. Il se connecte à une plateforme, ou à un framework qui en couvre plusieurs, transforme chaque message entrant en événement neutre, envoie l'événement à personagent et livre ce qui revient. Tout ce qui est propre à la plateforme reste dans le connecteur, si bien que l'agent voit le même format quelle que soit la plateforme.

Ce dépôt fournit quatre connecteurs :

| Connecteur | Atteint | Chemin |
|---|---|---|
| Direct | Bots officiels QQ, WeChat personnel (iLink), Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK et Stoat, sans autre logiciel. La page locale et `personagent up` le lancent en un seul processus, `python -m persona_agent.direct`. | `persona_agent/direct/` |
| Plugin AstrBot | Les plateformes d'AstrBot, une passerelle tierce. L'AstrBot que personagent gère pour KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 et les autres reçoit le plugin automatiquement. Pour un AstrBot que vous exécutez déjà, `personagent connect astrbot` le configure. Vous pouvez aussi téléverser `astrbot_plugin_personagent.zip` depuis une GitHub Release au moyen de la fonction Install from File d'AstrBot et définir `connector_token` vous-même. | `integrations/astrbot/` |
| Satori | Toutes les implémentations de Satori (Koishi et d'autres, tierces) : QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, e-mail et plus. | `integrations/satori/` |
| Matrix | Les salons Matrix et, via des passerelles mautrix tierces, WhatsApp, Signal, Messenger, Instagram, Google Messages et plus. | `integrations/matrix/` |

Les assistants de programmation ne sont pas des plateformes de discussion ; ils disposent donc de leur propre voie : un serveur MCP, `personagent mcp`, présenté dans le [guide d'utilisation](guide.fr.md#assistants-de-programmation).

Les quatre parlent le protocole décrit sur cette page. Pour en écrire un nouveau, cette page et un client HTTP suffisent. Le module Python `integrations/sdk/personagent_connector.py` signe les requêtes et exécute la boucle de la boîte d'envoi à votre place. Il prend l'URL de base, le jeton et le `connector_id` du connecteur, et il a besoin de `httpx`. Son [README](../integrations/sdk/README.fr.md) donne un exemple complet.

## L'essayer sur votre propre machine

```
personagent run --port 8080
curl http://127.0.0.1:8080/health
```

`personagent run` sert les deux points d'accès décrits plus bas sur `127.0.0.1`. Il lit `CONNECTOR_TOKEN` dans le `.env` du dossier personnel que nomme sa bannière de démarrage ; `--home DIR` en choisit un autre.

- Lorsque `CONNECTOR_TOKEN` est vide, l'agent n'accepte que les programmes de la même machine qui appellent `127.0.0.1` ou `localhost`, et ceux-ci n'envoient aucun en-tête d'authentification. `personagent init` le laisse vide. La page locale, `personagent up` et `personagent connect astrbot` en écrivent un aléatoire lorsqu'il est vide.
- Pour en définir un, inscrivez une longue valeur aléatoire dans `.env`, par exemple la sortie de `python -c "import secrets; print(secrets.token_urlsafe(32))"`, donnez la même valeur au connecteur, puis redémarrez l'agent.
- `GET /health` répond `{"status": "ok", "agent_enabled": true}` et ne coûte rien. `"agent_enabled": false` signifie que l'agent ne peut pas répondre (pas de `LLM_API_KEY`, ou `AGENT_ENABLED=false`), et chaque événement reçoit `owned: false`. `GET /health/details` vérifie en outre le modèle et les autres services, ce qui peut coûter un peu. Il exige l'en-tête `X-Personagent-Token` lorsqu'un jeton est défini et, sinon, une requête venant de la même machine ; toute autre requête reçoit `403` avec le code `forbidden`.

## Configuration

La page locale configure le connecteur direct. Les trois autres utilisent les mêmes noms, donc un réglage signifie la même chose dans chacun :

| Signification | Satori | Matrix | Clé du plugin AstrBot |
|---|---|---|---|
| L'URL de base de personagent, comme `http://127.0.0.1:8080`. Le connecteur ajoute `/v1/events` et `/v1/outbox`. | `PERSONAGENT_URL` | `PERSONAGENT_URL` | `personagent_url` |
| Le jeton partagé, égal au `CONNECTOR_TOKEN` de l'agent | `CONNECTOR_TOKEN` | `CONNECTOR_TOKEN` | `connector_token` |
| L'identifiant de ce connecteur (`connector_id` ci-dessous) | `SATORI_CONNECTOR_ID` | `MATRIX_CONNECTOR_ID` | `connector_id` |
| Durée maximale d'une requête, en secondes | `SATORI_TIMEOUT_S` | `MATRIX_TIMEOUT_S` | `timeout_s` |
| Interroger la boîte d'envoi | `SATORI_OUTBOX_ENABLED` | `MATRIX_OUTBOX_ENABLED` | `outbox_enabled` |
| Groupes à transmettre | `SATORI_GROUPS` | `MATRIX_GROUPS` | `groups` |
| Personnes dont les messages privés sont transmis | `SATORI_DM_USERS` | `MATRIX_DM_USERS` | `dm_users` |
| Le serveur de la plateforme | `SATORI_URL` | `MATRIX_URL` | Celui d'AstrBot |

Une liste de groupes ou de messages privés vide ne transmet rien de ce type. `*` transmet tout et marque les événements `"prefiltered": false`, ce qui laisse la décision aux `ACCESS_GROUPS` et `ACCESS_DM_USERS` de l'agent. Le README de chaque connecteur liste ses autres réglages.

## Adressage

personagent stocke chaque identifiant sous la forme `<platform>:<id>`, par exemple `telegram:-1001234` pour un groupe ou `discord:4242` pour un utilisateur. `platform` est le nom que le connecteur donne à la plateforme, en minuscules et sans `:`.

QQ est la seule exception, conservée pour la compatibilité. Ses identifiants sont stockés nus (`123456`), et `qq:123456` signifie la même chose dans tout réglage. Si un connecteur transporte QQ et que vous voulez aligner son état appris sur un déploiement QQ existant, indiquez sa plateforme dans `CONNECTOR_QQ_PLATFORMS`. L'adaptateur QQ du plugin AstrBot est `aiocqhttp`. Les identifiants des plateformes qui y figurent sont eux aussi stockés nus.

## Authentification

Les deux points d'accès ci-dessous utilisent le même schéma. Quand `CONNECTOR_TOKEN` est défini sur l'agent, chaque requête porte quatre en-têtes :

- `X-Personagent-Token` : le jeton.
- `X-Personagent-Timestamp` : secondes unix. Une valeur à plus de cinq minutes de l'horloge de l'agent est refusée.
- `X-Personagent-Nonce` : une nouvelle valeur aléatoire. Un nonce réutilisé est refusé.
- `X-Personagent-Signature` : `sha256=` suivi du HMAC-SHA256 en hexadécimal de `timestamp + "." + nonce + "." + body`, avec le jeton comme clé.

La signature porte sur les octets du corps tels qu'ils sont envoyés : tout JSON valide en UTF-8 est donc accepté. Le JSON canonique (clés triées, séparateurs compacts et non-ASCII non échappé) est recommandé, et les connecteurs fournis l'envoient, mais l'agent ne l'exige pas. Le jeton sert aussi de clé de signature ; ne le consignez donc jamais dans les journaux.

Sans jeton, l'agent n'accepte que les programmes locaux qui appellent directement `127.0.0.1` ou `localhost`. Un connecteur doit refuser d'envoyer à autre chose qu'une URL de boucle locale, ou qu'une URL HTTPS avec jeton.

## Entrée : `POST /v1/events`

Chaque requête apporte un message et renvoie les réponses à ce message.

```json
{
  "platform": "telegram",
  "conversation_type": "group",
  "conversation_id": "-1001234",
  "sender_id": "42",
  "sender_name": "Alex",
  "bot_id": "7000",
  "message_id": "881",
  "sent_at": 1790320000,
  "addressed": true,
  "text": "Nova, how was your day?",
  "segments": [
    {"type": "text", "text": "Nova, how was your day?"}
  ],
  "connector_id": "astrbot-7f3c",
  "reply_handle": "tg-bot:GroupMessage:-1001234",
  "capabilities": ["outbox", "quote_text"]
}
```

Les champs obligatoires sont `platform`, `conversation_type` (`group` ou `dm`), `sender_id`, `message_id` et `sent_at`, plus `conversation_id` pour les groupes. `sent_at` est le moment où la plateforme a horodaté le message, en secondes unix entières (une chaîne de chiffres est aussi acceptée). Le personnage voit chaque message avec cette heure. Un message de groupe qui date de plus de 10 minutes à son arrivée, dans les deux minutes qui suivent le premier message de la plateforme depuis le démarrage de l'agent, fait partie d'un arriéré remis après un redémarrage : il est conservé comme contexte et ne reçoit pas de réponse. Passé ces deux minutes, un `sent_at` ancien ne retient plus un message, de sorte qu'un connecteur dont l'horloge retarde reçoit tout de même des réponses. Envoyez les identifiants bruts de la plateforme. L'agent ajoute le préfixe.

Le connecteur définit `addressed`. Il est vrai quand le message mentionne le bot, répond à l'un des messages du bot ou s'adresse au bot selon les règles propres à la plateforme. L'agent repère également de lui-même son nom dans le texte. Il lit une citation de son propre message, ou une @ au bot, comme une réaction dont il peut apprendre : définissez donc `addressed` sur les réponses au bot. Une citation du message d'un autre membre n'est jamais une réaction au bot. Une mention du bot à l'intérieur d'un message transféré ne s'adresse pas au bot : ne définissez donc pas `addressed` dans ce cas.

Un événement dont le `sender_id` est égal au `bot_id` est le propre message du bot renvoyé en écho. L'agent l'ignore sans le lire et répond `{"handled": false, "owned": true, "replies": []}`, si bien que la logique de bot du connecteur reste elle aussi silencieuse. Ignorez ces événements dans le connecteur.

Les segments arrivent dans l'ordre :

| Type | Champs | Remarques |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | Une mention de quelqu'un. Elle mentionne le bot quand `user_id` est égal à `bot_id`. Le personnage lit `name` à la place de l'identifiant : envoyez-le donc. `name` parvient au modèle marqué comme un nom que l'expéditeur n'a pas écrit ; il n'interpelle donc jamais le personnage et ne donne aucune commande. Une mention du bot placée après un segment `forward` n'est pas un appel. |
| `image` | `url` ou `b64`, `sticker` (booléen) | `sticker` marque un autocollant envoyé comme image. Une image de groupe envoyée en `b64`, ou marquée par `sticker`, peut être collectée pour la bibliothèque d'autocollants ; une photo envoyée uniquement sous forme d'`url` ne l'est pas. |
| `emoji` | `name`, `id` | Un autocollant de plateforme ou un emoji personnalisé que l'agent ne peut pas voir. `name` est le nom qu'une personne lui donnerait. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | Le message que celui-ci cite. Envoyez `text` chaque fois que la plateforme le fournit. |
| `media` | `kind`, `name`, `transcript`, `emoji` | Un élément que l'agent ne peut pas voir. `kind` vaut `voice`, `video`, `file`, `photo` (une image qui n'a pas pu être récupérée) ou `sticker`. Ajoutez `name` à un fichier, `transcript` à un message vocal que la plateforme a transcrit, et `emoji` à un autocollant. |
| `forward` | `name` | Les segments qui le suivent ont été transférés depuis `name` et n'ont pas été écrits par l'expéditeur. `name` peut être vide. Leur texte est lu comme les mots de la personne dont le message a été transféré : il n'interpelle personne par son nom et n'exécute aucune commande de mémoire. Placez le commentaire de l'expéditeur lui-même avant le segment `forward`, ou envoyez-le dans un message séparé. |

Envoyez les médias sous forme de segment `media`, jamais sous forme de mots comme `(sent a voice message)` : le personnage les lirait comme s'ils avaient été tapés par l'expéditeur. L'agent ignore les types de segments inconnus.

Ces champs facultatifs activent davantage de fonctions de l'agent :

| Champ | Signification |
|---|---|
| `connector_id` | Un identifiant stable pour cette instance du connecteur. La boîte d'envoi l'exige. |
| `reply_handle` | Tout ce dont le connecteur a besoin pour atteindre cette conversation plus tard sans message entrant : le `unified_msg_origin` d'AstrBot, un identifiant de salon Matrix, ou une connexion Satori plus un identifiant de canal. L'agent le traite comme opaque, le stocke par conversation et le rend dans les livraisons de la boîte d'envoi. |
| `capabilities` | Ce que le connecteur sait faire. `outbox` signifie qu'il interroge la boîte d'envoi et peut envoyer de lui-même. `quote_text` signifie que les segments de réponse portent le texte cité. |
| `prefiltered` | `true` (par défaut) quand le connecteur a appliqué sa propre liste d'autorisation. `false` fait des listes de l'agent le seul filtre. |
| `proactive` | Marque un événement de message privé comme un signal écrit par le connecteur, et non les mots de la personne. Voir « Parler en premier sans la boîte d'envoi ». |

La réponse ressemble à ceci :

```json
{"handled": true, "owned": true, "replies": [
  {"type": "text", "text": "not bad, rained all afternoon", "mention_user_id": "telegram:42"},
  {"type": "image", "b64": "..."}
]}
```

- `replies` : envoyez-les dans l'ordre, chacune comme un message séparé. Quand `mention_user_id` est présent, c'est l'identifiant préfixé à mentionner. Affichez la mention comme le fait la plateforme. Un élément portant `"reason": "excuse"` est le court message que le personnage envoie en message privé lorsque le modèle a échoué, et non une réponse. Envoyez-le comme les autres, ou traitez-le comme une erreur.
- `owned` : l'agent a pris le message, parce qu'il a passé les listes d'autorisation de l'agent, quoi que fasse ensuite le personnage. Quand il est vrai, empêchez toute autre logique de bot de répondre, même si `replies` est vide, car le personnage a pu choisir de se taire. Quand il est faux, l'agent n'a pris aucune part au message : la conversation n'est pas sur les listes d'autorisation de l'agent, l'agent ne peut pas répondre du tout (pas de `LLM_API_KEY`, ou `AGENT_ENABLED=false`), ou le `message_id` a déjà été reçu (voir « Messages répétés » plus bas). Lorsque l'agent ne peut pas répondre, son journal contient une ligne ERROR qui en indique la cause.
- `handled` : vrai lorsque le tour propre à cette requête a livré quelque chose, une réponse ou le résultat d'une commande de mémoire. Il sert aux journaux et aux statistiques. Décidez d'après `owned`, et envoyez ce que contient `replies` quelle que soit la valeur de `handled` : un message `excuse`, par exemple, arrive avec `handled: false`.

Les combinaisons qu'un connecteur rencontre :

| Réponse | Quand | Ce que fait le connecteur |
|---|---|---|
| `handled: true`, `owned: true`, avec réponses | Une réponse normale. | Envoyer `replies` et faire taire toute autre logique de bot. |
| `handled: false`, `owned: true`, `replies: []` | Le personnage s'est tu ; l'événement était l'écho du bot lui-même ; le message a été intégré au tour d'un message ultérieur (voir « Messages envoyés à la suite ») ; une commande de mémoire dont le résultat arrivera plus tard par la boîte d'envoi ; un événement de groupe avec `proactive`. | Ne rien envoyer et faire taire toute autre logique de bot. |
| `handled: false`, `owned: true`, une réponse avec `"reason": "excuse"` | Le modèle a échoué en message privé. | L'envoyer, ou la traiter comme une erreur. |
| `handled: false`, `owned: false`, `replies: []` | La conversation n'est pas sur les listes d'autorisation, l'agent ne peut pas répondre, ou le `message_id` est répété. | Pour un `message_id` déjà envoyé, ne rien faire. Sinon, le traitement du message vous revient. |

Autres règles :

- **Messages répétés.** L'agent retient les 2 000 derniers messages qu'il a admis, toutes conversations confondues. La clé est formée de `platform`, de la conversation (le `conversation_id` d'un groupe, le `sender_id` d'un message privé) et de `message_id` ; pour une plateforme de `CONNECTOR_QQ_PLATFORMS`, c'est le `message_id` nu. La liste est enregistrée de temps en temps et à l'arrêt dans le dossier `runtime/` du dossier personnel ; elle survit donc à un redémarrage. Un message envoyé à nouveau, comme une nouvelle livraison de la plateforme ou une nouvelle tentative après un délai dépassé, reçoit aussitôt `{"handled": false, "owned": false, "replies": []}`, même pendant que la première requête est encore en cours, et ses réponses n'arrivent que dans la première. N'y répondez pas : conservez la liste des `message_id` que vous avez envoyés. Un tour se poursuit quand son appelant abandonne ; après un délai dépassé, les réponses sont donc perdues. Prévoyez un délai suffisant plutôt que de réessayer. Un message refusé par les listes d'autorisation n'est pas retenu et sera de nouveau évalué s'il est renvoyé.
- **Messages envoyés à la suite.** Les messages d'une conversation qui arrivent dans un court anti-rebond (2,5 secondes, ou 5 secondes après un message de groupe qui se contente d'appeler le personnage par son nom) forment un seul tour, qui leur répond ensemble. Les messages qui attendent derrière un tour en cours sont de même lus dans le tour suivant. Seule la requête du message le plus récent porte les réponses ; chaque requête antérieure renvoie `{"handled": false, "owned": true, "replies": []}`. Dans un groupe, le `mention_user_id` d'une réponse désigne la personne à qui répond le personnage, qui a pu envoyer un message antérieur plutôt que celui dont la requête porte la réponse. Les commandes de mémoire ne sont pas regroupées ; voir le dernier point.
- La requête dure jusqu'à la fin du tour, soit un court anti-rebond plus le temps du modèle. Les appels au modèle d'un tour se partagent un seul budget de 1,5 × `LLM_TIMEOUT_S`, nouvelles tentatives comprises, dans un groupe comme en message privé, et un message qui arrive pendant qu'un tour précédent de sa conversation réfléchit encore attend la fin de ce tour avant de commencer le sien. Prévoyez au moins 3 × `LLM_TIMEOUT_S` secondes (360 avec la valeur par défaut).
- Une commande de mémoire (comme « remember ... ») qui arrive pendant qu'un tour de sa conversation réfléchit encore reçoit sa réponse après ce tour. Un connecteur qui a déclaré `outbox` reçoit tout de suite `{"handled": false, "owned": true, "replies": []}` puis le résultat plus tard sous forme de livraison `follow_up`. Sans `outbox`, le résultat arrive dans la réponse à une requête : la sienne, ou celle d'une autre requête en attente de la même conversation, si bien qu'une réponse peut porter des `replies` qui mentionnent quelqu'un d'autre que l'expéditeur de l'événement.

## Boîte d'envoi : `POST /v1/outbox`

Certains messages ne répondent pas à une requête. Par exemple une ouverture programmée, la question de suivi après un rejet, la réponse à une commande de mémoire qui a attendu derrière un tour et l'excuse quand le modèle est en panne dans un groupe. L'agent les met en file par conversation, et un connecteur qui a déclaré `outbox` les récupère : un connecteur derrière un NAT ou un pare-feu fonctionne donc de la même façon. Les conversations stockées sous des identifiants QQ nus (voir Adressage) utilisent aussi la boîte d'envoi tant que leur connecteur l'interroge. Sinon, elles passent par l'API HTTP de NapCat, quand `QQ_ONEBOT_URL` est défini.

Requête :

```json
{
  "kind": "outbox.pull",
  "connector_id": "astrbot-7f3c",
  "wait_s": 25,
  "max_deliveries": 10,
  "acks": [
    {"delivery_id": "d_5c1f...", "status": "sent", "sent_items": 2}
  ]
}
```

L'agent retient la requête jusqu'à `wait_s` secondes (30 au plus) le temps que quelque chose soit en file, puis répond :

```json
{
  "deliveries": [
    {
      "delivery_id": "d_9a07...",
      "conversation_key": "telegram:-1001234",
      "reply_handle": "tg-bot:GroupMessage:-1001234",
      "platform": "telegram",
      "conversation_type": "group",
      "conversation_id": "-1001234",
      "reason": "proactive",
      "expires_in_s": 300,
      "items": [{"type": "text", "text": "anyone still up?"}]
    }
  ],
  "next_wait_s": 25
}
```

`items` a la même forme que `replies`. `reason` vaut `proactive`, `follow_up` ou `excuse`, et `conversation_type` vaut `group` ou `dm`. `conversation_key` est la clé sous laquelle l'agent stocke la conversation, comme `private:telegram:42` pour un message privé. `conversation_id` est l'identifiant brut porté par l'événement, soit l'identifiant de l'utilisateur pour un message privé. L'agent retient `reply_handle`, `connector_id` et `capabilities` du dernier événement admis dans chaque conversation : une conversation devient donc joignable dès qu'elle a envoyé un message. Une exception maintient en place un connecteur qui récupère la boîte d'envoi : un événement provenant d'un connecteur sans la capacité `outbox` ne remplace pas ce qu'un autre connecteur doté de cette capacité a enregistré pour la même conversation. Un connecteur qui récupère la boîte d'envoi continue donc de joindre la conversation après qu'un autre programme, comme un assistant de programmation, s'y est exprimé. Un événement provenant du même connecteur, ou de tout connecteur qui déclare `outbox`, remplace les valeurs enregistrées comme auparavant.

La page locale est elle-même un connecteur de boîte d'envoi, avec le `connector_id` `local-welcome`. Elle ne reçoit que les livraisons destinées à la discussion de la page et les affiche dans la vue **Discussion**.

Signalez chaque livraison dans `acks` à l'interrogation suivante :

| `status` | Signification |
|---|---|
| `sent` | Tous les éléments sont partis. |
| `partial` | Les `sent_items` premiers éléments sont partis. |
| `failed` | Rien n'est parti. |
| `expired` | L'envoi n'a pas commencé dans le délai `expires_in_s`. |
| `refused` | Le connecteur n'autorise plus la conversation. |
| `unsupported` | La plateforme ne peut pas envoyer de son propre chef à cette conversation. |

Règles :

- **Au plus une fois.** L'agent remet une livraison une fois et plus jamais, quoi qu'il advienne de l'ack. Gardez les quelques centaines de derniers `delivery_id` et n'en envoyez jamais un deux fois.
- **Dans l'ordre.** Envoyez les livraisons d'une conversation dans l'ordre de réception. Des conversations différentes peuvent partir en parallèle.
- **Seules les livraisons confirmées comptent.** L'agent traite une livraison non confirmée comme non envoyée et n'enregistre comme envoyées que les livraisons confirmées. Il attend l'ack jusqu'à votre prochaine interrogation, et au plus `expires_in_s` plus 60 secondes après la remise. Terminez l'envoi d'un lot avant de réinterroger.
- **Activité.** Un connecteur qui n'a pas interrogé depuis 90 secondes est considéré comme parti. Rien n'est mis en file pour ses conversations jusqu'à ce qu'il réinterroge, et ce qui était en file pour lui, ou remis sans ack, se termine comme non envoyé. Réinterrogez dès qu'un lot est livré. Cette interrogation porte aussi les ack du lot.
- **`unsupported` persiste.** Après cet ack, l'agent cesse de mettre en file pour la conversation jusqu'à ce qu'un événement apporte un `reply_handle` différent.
- **Types de corps.** La signature ne couvre pas le chemin de l'URL. L'agent refuse donc un corps d'événement sur le point d'accès de la boîte d'envoi et un corps `outbox.pull` sur le point d'accès des événements, avec `400` et le code `invalid_schema`. Un événement peut porter `"kind": "event"`. Un événement avec tout autre `kind` est refusé.

Un 404 sans `code` signifie que l'agent ne sert pas la boîte d'envoi. Un `404` avec le code `outbox_disabled` signifie que l'opérateur l'a désactivée avec `CONNECTOR_OUTBOX_ENABLED`. Dans les deux cas, attendez longtemps avant de réinterroger.

## Erreurs

Une erreur répond `{"error": "...", "code": "..."}`. `code` est stable : c'est sur lui qu'il faut se fonder. `error` est une phrase destinée à la personne qui lit un journal, et sa formulation peut changer.

| Statut | `code` | Point d'accès | Cause |
|---|---|---|---|
| 400 | `invalid_schema` | les deux | Le corps n'est pas un objet JSON ; un champ obligatoire manque ou est vide ; `conversation_type` n'est ni `group` ni `dm` ; `segments` n'est pas une liste ; un corps du mauvais type (voir « Types de corps ») ; une interrogation sans `connector_id` utilisable (128 caractères au plus), avec un `wait_s` ou un `max_deliveries` qui n'est pas un nombre, ou avec plus de 1 000 acks. |
| 400 | `client_disconnected` | les deux | L'appelant a raccroché pendant l'envoi du corps. |
| 403 | `unauthenticated` | les deux | Pas de `CONNECTOR_TOKEN`, et l'appelant n'est pas sur la machine de l'agent. |
| 403 | `non_local_request` | les deux | Pas de `CONNECTOR_TOKEN`, et la requête porte un en-tête qu'un programme local n'envoie pas : `Origin`, un `Sec-Fetch-Site` autre que `none`, un `Host` autre que `localhost`, `127.0.0.1` ou `::1`, ou un en-tête de proxy tel que `X-Forwarded-For`. |
| 403 | `invalid_envelope` | les deux | `CONNECTOR_TOKEN` est défini, et le jeton ou un en-tête manque ou est faux, la signature ne correspond pas, l'horodatage s'écarte de plus de cinq minutes, le nonce a déjà servi, ou la protection contre le rejeu est pleine. |
| 403 | `stale_event` | events | `sent_at` n'est pas un nombre entier de secondes, ou s'écarte de plus de `CONNECTOR_MAX_EVENT_AGE_S` (24 heures) de l'horloge de l'agent, dans un sens ou dans l'autre. Une valeur en millisecondes tombe loin dans le futur. |
| 404 | `outbox_disabled` | outbox | `CONNECTOR_OUTBOX_ENABLED=false`, ou l'agent est arrêté (`AGENT_ENABLED=false`). |
| 408 | `body_timeout` | les deux | Le corps a mis plus de 30 secondes à arriver. |
| 413 | `body_too_large` | les deux | Le corps dépasse `SERVER_MAX_BODY_BYTES` (8 000 000 octets), le plus souvent à cause d'une image intégrée. |
| 429 | `capacity_exceeded` | les deux | Trop de requêtes à la fois : plus de `CONNECTOR_MAX_INFLIGHT` tours (64 par défaut) sur le point d'accès des événements, ou 16 interrogations sur la boîte d'envoi. L'en-tête `Retry-After` donne le nombre de secondes à attendre : 3, ou 5 pour la boîte d'envoi. |

Un chemin erroné reçoit `404 {"detail": "Not Found"}` et une méthode erronée, comme `GET /v1/events`, reçoit `405 {"detail": "Method Not Allowed"}`. Ces réponses viennent du framework web et ne portent pas de `code`.

## Parler en premier sans la boîte d'envoi

Un connecteur qui ne peut pas interroger peut quand même ouvrir un message privé. Son propre planificateur, comme une tâche de plugin AstrBot ou une entrée cron, envoie à `/v1/events` un événement de message privé ordinaire avec `"proactive": true`. L'agent lit le texte comme un signal adressé au personnage (« calme depuis un jour ; son examen était ce matin »), le tronque à 500 caractères et ne le stocke jamais comme les propos de la personne. Les instructions proactives du moteur décident toujours du tour et peuvent maintenir le personnage silencieux. Si le personnage s'exprime, la réponse revient dans la réponse HTTP et le planificateur la relaie.

L'événement a besoin de tout ce que portent les événements normaux du connecteur : les en-têtes signés, tous les champs obligatoires, le même `platform` et le même `sender_id` brut que le connecteur envoie pour cette personne, un texte non vide et un nouveau `message_id` à chaque fois. Un événement dont le `message_id` est répété est ignoré sans avertissement. Le signal compte dans le même délai de message privé que les ouvertures de l'agent (`PROACTIVE_DM_COOLDOWN_S`), et il ne compte pas comme une activité de la personne.

Définissez toujours l'indicateur ; sans lui, l'agent stocke le signal comme les mots de la personne. Un événement de groupe avec l'indicateur est pris en charge (`owned: true`, pour que le connecteur garde son bot silencieux) et ignoré sans être lu.

## Capacités et ce qui se dégrade

| Manquant | Effet |
|---|---|
| `outbox` | Pas d'ouvertures programmées, pas de question de suivi et pas d'excuse pour un appel au modèle raté dans un groupe. Les identifiants QQ les reçoivent quand même par NapCat quand `QQ_ONEBOT_URL` est défini et joignable. L'excuse d'un message privé revient dans les `replies` de la réponse et n'a pas besoin de la boîte d'envoi. |
| `quote_text` | L'agent ne comprend un message cité que s'il a vu ce message lui-même. |
| `reply_handle` | Comme si `outbox` manquait. |
| `addressed` erroné | Le personnage traite les messages qui lui sont adressés comme un bavardage de fond. |

## Écrire un connecteur

1. Recevez un message de la plateforme. Ignorez les messages du bot lui-même et les événements qui ne sont pas des messages (arrivées, rappels, coups de coude).
2. Construisez l'événement décrit ci-dessus. Définissez `addressed` d'après les règles de mention et de réponse de la plateforme.
3. Signez et envoyez l'événement. Envoyez `replies` dans l'ordre et, quand `owned` est vrai, gardez toute autre logique de bot silencieuse.
4. Si la plateforme peut envoyer de son propre chef, ajoutez `connector_id`, `reply_handle` et `capabilities: ["outbox"]`, puis exécutez la boucle d'interrogation : interrogez, livrez chaque livraison par son `reply_handle` et confirmez à l'interrogation suivante.

`integrations/sdk/personagent_connector.py` gère les étapes 3 et 4. Son [README](../integrations/sdk/README.fr.md) les montre dans un court programme.
