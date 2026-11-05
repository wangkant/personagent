# Connecteur Matrix

[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · Français · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [Русский](README.ru.md)


Ce connecteur place [personagent](https://github.com/wangkant/personagent) dans des salons Matrix et, via les [ponts mautrix](https://docs.mau.fi/bridges/), sur WhatsApp, Signal, Messenger, Instagram, Google Messages et d'autres réseaux. Matrix et les ponts sont des logiciels tiers que vous exécutez vous-même. personagent n'en a pas besoin pour les plateformes qu'il connecte depuis sa page locale.

Le connecteur est un petit processus autonome construit sur [matrix-nio](https://github.com/matrix-nio/matrix-nio), qui prend en charge le chiffrement de bout en bout sans libolm. Il se connecte à un homeserver comme un utilisateur Matrix ordinaire, transmet chaque message autorisé d'un salon au `POST /v1/events` de l'agent sous forme d'événement neutre vis-à-vis de la plateforme ([docs/connectors.md](../../docs/connectors.fr.md)) et publie les réponses de l'agent dans le salon. Il interroge aussi la boîte d'envoi de l'agent, donc les messages programmés, les questions de suivi et les excuses atteignent également Matrix.

## Ce qu'il fait

À la réception, pour chaque message d'un salon autorisé :

- L'événement utilise la plateforme `matrix` et les ids Matrix bruts, donc l'agent stocke `matrix:@alex:example.org` et `matrix:!room:example.org`.
- Un salon compte comme discussion directe quand le `m.direct` du bot le liste, ou quand il a exactement un membre en plus du bot et des utilisateurs de `MATRIX_IGNORE_USERS`. Une discussion directe est identifiée par la personne, un groupe par le salon. Un salon nommé par id dans `MATRIX_GROUPS` est toujours un groupe.
- `addressed` est vrai quand le message mentionne le bot ou répond à l'un de ses messages. Une mention est `m.mentions` ou, venant de clients trop anciens pour envoyer `m.mentions`, une pastille ou l'id d'utilisateur du bot dans le texte.
- Une réponse porte l'expéditeur et le texte du message cité. Le connecteur les prend dans un cache d'événements récents ou récupère l'événement parent. Il retire le texte de repli que préfixent les anciens clients (`> <@alex:example.org> ...`), donc l'agent ne lit jamais les mots de quelqu'un d'autre comme ceux de l'expéditeur.
- Les images et stickers jusqu'à 4 Mo sont téléchargés, déchiffrés dans les salons chiffrés et envoyés à l'agent sous forme d'octets. Les messages vocaux, vidéos et fichiers sont décrits en mots.
- Les messages d'un salon atteignent l'agent dans l'ordre d'envoi. Un message envoyé après une image attend que l'image soit téléchargée. L'agent peut tout de même traiter plusieurs tours à la fois.
- L'horodatage est le `origin_server_ts` du homeserver.
- Le connecteur ignore les messages du bot lui-même, les messages `m.notice` (le type qu'envoient les bots), les modifications, les réactions, les messages de `MATRIX_IGNORE_USERS`, l'arriéré que renvoie la première synchronisation au démarrage et tout ce qui est plus ancien que `MATRIX_MAX_EVENT_AGE_S`, comme l'historique qu'un pont déverse dans un nouveau salon.

À l'envoi :

- Les réponses textuelles sont `m.text`. Quand l'agent demande de mentionner quelqu'un dans un groupe, la réponse commence par une pastille et liste cette personne dans `m.mentions`. Toutes les autres réponses portent un `m.mentions` vide, donc aucun client ne transforme un nom du texte en notification.
- Les réponses en image sont envoyées, et chiffrées dans les salons chiffrés.
- Un avis de saisie s'affiche pendant que l'agent traite un tour.
- Un message dans un fil reçoit sa réponse dans ce fil.
- Une fois que l'agent prend la conversation, le bot marque le message comme lu (`MATRIX_READ_RECEIPTS_ENABLED`). Via un pont, cela apparaît comme la coche de lecture sur l'autre réseau.
- Les livraisons de la boîte d'envoi vont au salon d'où la conversation est venue en dernier. Le `reply_handle` de l'événement est l'id du salon.

## Installation

Il vous faut un personagent en marche et un compte Matrix pour le bot. Créez un compte dédié au lieu d'en partager un avec une personne.

Le connecteur est un script de ce dépôt, il lui faut donc une copie du dépôt (un clone ou le ZIP de GitHub) et son propre environnement Python, car `matrix-nio` n'est pas une dépendance de personagent. Dans un clone qui a déjà le `.venv` de personagent, installez dans cet environnement :

```bash
.venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Si vous avez installé personagent depuis PyPI avec pip, ou si vous le lancez avec uvx, créez un venv séparé à côté de la copie :

```bash
python -m venv connector-venv
connector-venv/bin/python -m pip install -r integrations/matrix/requirements.txt
```

Sous Windows, l'interpréteur est `.venv\Scripts\python.exe` ou `connector-venv\Scripts\python.exe`. Ensuite, copiez le fichier de réglages :

```bash
cp integrations/matrix/.env.example integrations/matrix/.env
```

Modifiez `integrations/matrix/.env` :

```ini
MATRIX_URL=https://matrix.example.org
MATRIX_USER_ID=@nova:example.org
MATRIX_PASSWORD=...
MATRIX_GROUPS=!AbCdEf:example.org
MATRIX_DM_USERS=@alex:example.org
PERSONAGENT_URL=http://127.0.0.1:8080
```

Puis démarrez le connecteur à côté de l'agent, avec le même interpréteur :

```bash
.venv/bin/python integrations/matrix/matrix_connector.py
# or: .venv/bin/python integrations/matrix/matrix_connector.py --config /path/to/matrix.env
```

Invitez le bot dans un salon listé dans `MATRIX_GROUPS`, et il le rejoint. Dans Element, l'id du salon se trouve dans les réglages du salon, sous Avancé.

### Connexion

La connexion par mot de passe est la façon la plus simple de commencer. Le connecteur enregistre la session obtenue (id d'utilisateur, id d'appareil et jeton d'accès) dans `MATRIX_STORE_DIR/session.json` et la réutilise au démarrage suivant, donc un redémarrage ne crée pas de nouvel appareil. Supprimez ce fichier pour vous reconnecter.

Pour utiliser plutôt un jeton d'accès existant, définissez `MATRIX_ACCESS_TOKEN`. Le connecteur demande au homeserver à quel compte appartient le jeton. N'utilisez pas le jeton d'une session que vous utilisez vous-même, car fermer cette session déconnecte aussi le bot.

Quand le homeserver déconnecte le bot (`M_UNKNOWN_TOKEN`), le connecteur s'arrête avec une erreur qui le dit. Après une connexion par mot de passe, le redémarrer reconnecte le bot. Avec `MATRIX_ACCESS_TOKEN`, définissez d'abord un nouveau jeton. Toute autre synchronisation échouée est réessayée après un délai qui double jusqu'à une minute.

### Où l'agent peut tourner

Le protocole fixe la règle. `PERSONAGENT_URL` doit être une adresse de bouclage, ou HTTPS avec `CONNECTOR_TOKEN` réglé sur le `CONNECTOR_TOKEN` de l'agent. Sinon, le connecteur refuse de démarrer. Définissez le jeton des deux côtés avant de placer un proxy ou un tunnel devant l'agent, même sur un seul hôte.

## Réglages

[.env.example](.env.example) liste tous les réglages. Les listes sont séparées par des virgules et acceptent les motifs, donc `@*:example.org` correspond à tout un serveur. Une liste vide ne répond à personne. Un `*` seul correspond à tout le monde et marque l'événement `prefiltered: false`. `ACCESS_GROUPS` / `ACCESS_DM_USERS` de l'agent décident alors seuls, et une plateforme sans entrée y est refusée.

| Réglage | Signification |
|---|---|
| `MATRIX_GROUPS` | Salons de groupe où répondre, par id de salon. `*` signifie tous les salons rejoints par le bot. |
| `MATRIX_DM_USERS` | Personnes qui peuvent parler au bot en discussion directe. `*` signifie tout le monde. |
| `MATRIX_INVITE_FROM` | Utilisateurs dont le bot accepte les invitations. Les invitations aux salons nommés dans `MATRIX_GROUPS` et les invitations de discussion directe de `MATRIX_DM_USERS` sont toujours acceptées. Les autres restent en attente. |
| `MATRIX_IGNORE_USERS` | Jamais de réponse, et pas comptés comme membres quand le connecteur distingue une discussion directe d'un groupe. |
| `MATRIX_E2EE_ENABLED` | Chiffrement de bout en bout. Voir plus bas. |
| `MATRIX_TIMEOUT_S` | Durée maximale d'un tour. Gardez-la au-dessus de `LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)` de l'agent. |
| `MATRIX_OUTBOX_ENABLED` | Interroger la boîte d'envoi de l'agent. |

## Ponts : WhatsApp, Signal, Messenger, Instagram et autres

Un pont mautrix se connecte à un autre réseau avec un compte de ce réseau et reflète ses discussions dans des salons Matrix appelés portails. Chaque personne de l'autre côté apparaît dans Matrix comme un utilisateur fantôme, par exemple `@whatsapp_4912345:example.org`. Quand le compte Matrix du bot est celui connecté au pont, la persona vit sur ce réseau. Un contact WhatsApp écrit au numéro de la persona, le pont publie le message dans un salon portail, ce connecteur le transmet et la réponse revient par le même chemin.

| Réseau | Pont |
|---|---|
| WhatsApp | [mautrix-whatsapp](https://github.com/mautrix/whatsapp) |
| Signal | [mautrix-signal](https://github.com/mautrix/signal) |
| Facebook Messenger, messages privés Instagram | [mautrix-meta](https://github.com/mautrix/meta) |
| Google Messages (RCS et SMS via un téléphone Android) | [mautrix-gmessages](https://github.com/mautrix/gmessages) |
| Google Voice, LinkedIn, messages privés Twitter/X et Bluesky, Google Chat, Zulip, IRC, iMessage | Les autres [ponts mautrix](https://github.com/mautrix) |
| Telegram, Discord, Slack | Des ponts mautrix existent, mais ces réseaux ont des API de bots officielles. personagent connecte lui-même Telegram et Discord, et Slack via l'AstrBot qu'exécute sa page locale. |

Pour en configurer un :

1. Exécutez un homeserver que vous contrôlez (Synapse ou un autre serveur prenant en charge les services d'application) et installez le pont en suivant [sa documentation](https://docs.mau.fi/bridges/). Donnez au compte du bot le niveau de permission `user` dans les `permissions` du pont.
2. Connectez-vous à Element en tant que bot, ouvrez une discussion avec le bot du pont (par exemple `@whatsappbot:example.org`) et envoyez `login`. Liez le compte réseau que la persona utilisera. Pour WhatsApp, Signal et Google Messages, scannez le code QR avec le téléphone de la persona. Pour Messenger et Instagram, donnez la connexion Meta. Voir [Utiliser les ponts](https://docs.mau.fi/bridges/general/using-bridges.html).
3. Laissez le connecteur rejoindre les portails et écartez les messages du pont lui-même :

   ```ini
   MATRIX_INVITE_FROM=@whatsappbot:example.org
   MATRIX_IGNORE_USERS=@whatsappbot:example.org,@whatsapp_4900000000:example.org
   MATRIX_DM_USERS=@whatsapp_*:example.org
   MATRIX_GROUPS=!groupPortal:example.org
   ```

   La seconde entrée de `MATRIX_IGNORE_USERS` est le fantôme du pont pour le numéro de la persona elle-même. Sans [double marionnette](https://docs.mau.fi/bridges/general/double-puppeting.html), un message tapé sur le téléphone de la persona arrive à Matrix depuis ce fantôme, et le bot se répondrait à lui-même. `MATRIX_GROUPS=*` transmet tous les portails de groupe où se trouve le bot, et personagent ne répond alors que dans les salons que son `ACCESS_GROUPS` liste sous la forme `matrix:!room:server`. Listez ici des ids de salon pour choisir les salons dans le connecteur.

### Marionnettes

- Le pont est un client non officiel du réseau, connecté comme un compte utilisateur normal (un appareil lié ou une session web). Il n'utilise pas d'API de bots, et rien sur le réseau ne marque le compte comme un bot.
- La persona a besoin de son propre compte, généralement avec son propre numéro de téléphone, et le téléphone doit rester joignable. WhatsApp déconnecte les appareils liés quand le téléphone est hors ligne depuis environ deux semaines, et Google Messages ne fonctionne que tant que le téléphone Android est en ligne.
- Dans les discussions de groupe, le compte de la persona ressemble à n'importe quel autre membre. Dites aux gens qu'ils parlent à un bot.
- Les réactions, modifications, suppressions, sondages et appels ne sont pas transmis à l'agent.

### Conditions de chaque réseau

Lisez les conditions de chaque réseau avant de le connecter.

- [WhatsApp](https://www.whatsapp.com/legal/terms-of-service) classe l'envoi automatique de messages parmi les communications interdites, interdit l'usage non personnel qu'il n'a pas autorisé et peut bannir les comptes qui font l'un ou l'autre. Sa voie autorisée pour l'automatisation est WhatsApp Business Platform, qu'un pont n'utilise pas.
- [Signal](https://signal.org/legal/) classe aussi l'envoi automatique de messages parmi les usages interdits.
- [Facebook](https://www.facebook.com/terms.php) et [Instagram](https://help.instagram.com/581066165581870) interdisent l'accès automatisé sans la permission de Meta, et Meta peut bloquer un compte qui se connecte depuis un client qu'il ne reconnaît pas.
- Google Messages relève des [conditions de Google](https://policies.google.com/terms) et de celles de votre opérateur mobile pour les SMS et RCS, qui peuvent facturer ou restreindre les messages automatisés.

Utilisez un compte dédié que vous pouvez vous permettre de perdre, uniquement dans des conversations où les gens savent qu'ils parlent à un bot, et lisez [DISCLAIMER.md](../../docs/DISCLAIMER.fr.md).

## Chiffrement de bout en bout

Avec `MATRIX_E2EE_ENABLED=false` (le défaut), le bot ne lit que les salons non chiffrés. Dans un salon chiffré, il journalise qu'il ne peut pas déchiffrer le message, et il n'y envoie jamais de réponse en clair.

Avec `MATRIX_E2EE_ENABLED=true` :

- `MATRIX_STORE_DIR` (par défaut `runtime/` à côté du script, ignoré par git) contient les clés de l'appareil et le jeton de synchronisation. Conservez ce dossier. S'il est perdu, le bot devient un nouvel appareil qui ne peut rien lire de chiffré avant ce moment.
- L'appareil doit rester le même d'un redémarrage à l'autre. Une connexion par mot de passe le conserve grâce à la session enregistrée. Avec un jeton d'accès, réglez `MATRIX_DEVICE_ID` sur l'appareil du jeton.
- Le bot partage ses clés avec tous les appareils du salon, vérifiés ou non. Il ne peut pas se vérifier de façon interactive, donc les gens voient son appareil comme non vérifié. Il n'a ni sauvegarde de clés ni signature croisée.
- Un message dont la clé n'est pas arrivée est journalisé et ignoré, sans nouvel essai.
- Un pont mautrix peut chiffrer ses portails ([chiffrement de bout en pont](https://docs.mau.fi/bridges/general/end-to-bridge-encryption.html)). Le pont garde ces clés sur votre serveur, donc la protection s'arrête là, et l'autre réseau transporte le message avec son propre chiffrement. Si votre pont chiffre les portails, activez `MATRIX_E2EE_ENABLED`.

## Tests

`tests/test_matrix_connector.py` simule le client Matrix et l'agent, donc il s'exécute sans matrix-nio et sans réseau :

```bash
python -m pytest tests/test_matrix_connector.py
```
