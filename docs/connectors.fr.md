# Protocole des connecteurs

[English](connectors.md) · [简体中文](connectors.zh-CN.md) · [繁體中文](connectors.zh-TW.md) · [日本語](connectors.ja.md) · [한국어](connectors.ko.md) · [Español](connectors.es.md) · Français · [Deutsch](connectors.de.md) · [Português (Brasil)](connectors.pt-BR.md) · [Русский](connectors.ru.md)

L'agent ne parle jamais lui-même à une plateforme de discussion. C'est le travail d'un connecteur. Il se connecte à une plateforme, ou à un framework qui en couvre plusieurs, transforme chaque message entrant en événement neutre, envoie l'événement à personagent et livre ce qui revient. Tout ce qui est propre à la plateforme reste dans le connecteur, si bien que l'agent voit le même format quelle que soit la plateforme.

Ce dépôt fournit quatre connecteurs :

| Connecteur | Atteint | Chemin |
|---|---|---|
| Direct | Bots officiels QQ, WeChat personnel (iLink), Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK et Stoat, sans autre logiciel. La page locale et `personagent up` le lancent en un seul processus, `python -m persona_agent.direct`. | `persona_agent/direct/` |
| Plugin AstrBot | Les plateformes d'AstrBot, une passerelle tierce. L'AstrBot que personagent gère pour KOOK, Feishu/Lark, DingTalk, Slack, WeCom, Mattermost, Misskey, OneBot v11 et les autres reçoit le plugin automatiquement. Pour un AstrBot que vous faites déjà tourner, `personagent connect astrbot` le configure. Vous pouvez aussi téléverser `astrbot_plugin_personagent.zip` depuis une GitHub Release avec Installer depuis un fichier d'AstrBot et définir `connector_token` vous-même. | `integrations/astrbot/` |
| Satori | Toutes les implémentations de Satori (Koishi et d'autres, tierces) : QQ, Telegram, Discord, KOOK, Lark, DingTalk, LINE, WhatsApp, Matrix, Zulip, e-mail et plus. | `integrations/satori/` |
| Matrix | Les salons Matrix et, via des passerelles mautrix tierces, WhatsApp, Signal, Messenger, Instagram, Google Messages et plus. | `integrations/matrix/` |

Les agents de code ne sont pas des plateformes de discussion, ils ont donc leur propre voie : un serveur MCP, `personagent mcp`, présenté dans le [guide d'utilisation](guide.fr.md#agents-de-code).

Les quatre parlent le protocole décrit sur cette page. Pour en écrire un nouveau, il vous faut cette page et un client HTTP. L'assistant Python de `integrations/sdk/personagent_connector.py` signe les requêtes et fait tourner la boucle de la boîte d'envoi pour vous. Il prend l'URL de base, le jeton et le `connector_id` du connecteur, et il a besoin de `httpx`.

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

Le corps est du JSON canonique : UTF-8, clés triées, séparateurs compacts et non-ASCII non échappé. Le jeton est aussi la clé de signature, gardez-le donc hors des journaux.

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

Les champs obligatoires sont `platform`, `conversation_type` (`group` ou `dm`), `sender_id`, `message_id` et `sent_at`, plus `conversation_id` pour les groupes. `sent_at` est le moment où la plateforme a horodaté le message, en secondes unix. Envoyez les identifiants bruts de la plateforme. L'agent ajoute le préfixe.

Le connecteur définit `addressed`. Il est vrai quand le message mentionne le bot, répond à l'un des messages du bot ou s'adresse au bot selon les règles propres à la plateforme. L'agent remarque aussi tout seul son nom dans le texte. Il lit une citation de son propre message, ou une @ au bot, comme une réaction dont il peut apprendre : définissez donc `addressed` sur les réponses au bot. Une citation du message d'un autre membre n'est jamais une réaction au bot.

Un événement dont le `sender_id` est égal au `bot_id` est le propre message du bot renvoyé en écho. L'agent le jette sans le lire et répond `{"handled": false, "owned": true, "replies": []}`, si bien que la logique de bot du connecteur reste elle aussi silencieuse. Ignorez ces événements dans le connecteur.

Les segments arrivent dans l'ordre :

| Type | Champs | Remarques |
|---|---|---|
| `text` | `text` | |
| `mention` | `user_id`, `name` | Une mention de quelqu'un. Elle mentionne le bot quand `user_id` est égal à `bot_id`. |
| `image` | `url` ou `b64`, `sticker` (booléen) | `sticker` marque un sticker envoyé comme image. |
| `emoji` | `name`, `id` | Un sticker de plateforme ou un emoji personnalisé que l'agent ne peut pas voir. `name` est le nom qu'une personne lui donnerait. |
| `reply` | `message_id`, `text`, `sender_id`, `sender_name` | Le message que celui-ci cite. Envoyez `text` chaque fois que la plateforme le fournit. |

Décrivez tout le reste avec des mots, sous forme de segment `text` comme `(sent a voice message)` ou `(sent a file: deck.pdf)`. L'agent jette les types de segments inconnus.

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

- `replies` : envoyez-les dans l'ordre, chacune comme un message séparé. Quand `mention_user_id` est présent, c'est l'identifiant préfixé à mentionner. Affichez la mention comme le fait la plateforme.
- `owned` : l'agent a pris cette conversation. Quand il est vrai, empêchez toute autre logique de bot de répondre, même si `replies` est vide, car la persona a choisi de se taire. Quand il est faux, le message est à vous. Soit la conversation n'est pas sur les listes d'autorisation de l'agent, soit l'agent ne peut pas répondre du tout (pas de `LLM_API_KEY`, ou `AGENT_ENABLED=false`). Dans le second cas, le journal de l'agent contient une ligne ERROR qui en indique la cause.
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

`items` a la même forme que `replies`. `reason` vaut `proactive`, `follow_up` ou `excuse`, et `conversation_type` vaut `group` ou `dm`. `conversation_key` est la clé sous laquelle l'agent stocke la conversation, comme `private:telegram:42` pour un message privé. `conversation_id` est l'identifiant brut porté par l'événement, soit l'identifiant de l'utilisateur pour un message privé. L'agent retient `reply_handle`, `connector_id` et `capabilities` du dernier événement admis dans chaque conversation : une conversation devient donc joignable dès qu'elle a envoyé un message.

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

## Parler en premier sans la boîte d'envoi

Un connecteur qui ne peut pas interroger peut quand même ouvrir un message privé. Son propre planificateur, comme une tâche de plugin AstrBot ou une entrée cron, envoie à `/v1/events` un événement de message privé ordinaire avec `"proactive": true`. L'agent lit le texte comme un signal adressé à la persona (« calme depuis un jour ; son examen était ce matin »), le coupe à 500 caractères et ne le stocke jamais comme les mots de la personne. Les instructions proactives du moteur décident toujours du tour et peuvent garder la persona silencieuse. Si la persona parle, la réponse revient dans la réponse HTTP et le planificateur la relaie.

L'événement a besoin de tout ce que portent les événements normaux du connecteur : les en-têtes signés, tous les champs obligatoires, le même `platform` et le même `sender_id` brut que le connecteur envoie pour cette personne, un texte non vide et un nouveau `message_id` à chaque fois. Un événement dont le `message_id` est répété est jeté en silence. Le signal compte dans le même délai de message privé que les ouvertures de l'agent (`PROACTIVE_DM_COOLDOWN_S`), et il ne compte pas comme une activité de la personne.

Définissez toujours l'indicateur ; sans lui, l'agent stocke le signal comme les mots de la personne. Un événement de groupe avec l'indicateur est pris en charge (`owned: true`, pour que le connecteur garde son bot silencieux) et jeté sans être lu.

## Capacités et ce qui se dégrade

| Manquant | Effet |
|---|---|
| `outbox` | Pas d'ouvertures programmées, pas de question de suivi et pas d'excuse pour un appel au modèle raté dans un groupe. Les identifiants QQ les reçoivent quand même par NapCat quand `QQ_ONEBOT_URL` est défini et joignable. L'excuse d'un message privé revient dans les `replies` de la réponse et n'a pas besoin de la boîte d'envoi. |
| `quote_text` | L'agent ne comprend un message cité que s'il a vu ce message lui-même. |
| `reply_handle` | Comme si `outbox` manquait. |
| `addressed` erroné | La persona traite les messages qui lui sont adressés comme un bavardage de fond. |

## Écrire un connecteur

1. Recevez un message de la plateforme. Ignorez les messages du bot lui-même et les événements qui ne sont pas des messages (arrivées, rappels, coups de coude).
2. Construisez l'événement décrit ci-dessus. Définissez `addressed` d'après les règles de mention et de réponse de la plateforme.
3. Signez et envoyez l'événement. Envoyez `replies` dans l'ordre et, quand `owned` est vrai, gardez toute autre logique de bot silencieuse.
4. Si la plateforme peut envoyer de son propre chef, ajoutez `connector_id`, `reply_handle` et `capabilities: ["outbox"]`, puis faites tourner la boucle d'interrogation : interrogez, livrez chaque livraison par son `reply_handle` et confirmez à l'interrogation suivante.

`integrations/sdk/personagent_connector.py` gère les étapes 3 et 4.
