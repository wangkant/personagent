# Commencer avec personagent

[English](start.md) · [简体中文](start.zh-CN.md) · [繁體中文](start.zh-TW.md) · [日本語](start.ja.md) · [한국어](start.ko.md) · [Español](start.es.md) · Français · [Deutsch](start.de.md) · [Português (Brasil)](start.pt-BR.md) · [Русский](start.ru.md) · [Guide complet](guide.fr.md)

## L'ouvrir

Installez personagent depuis PyPI et ouvrez-le :

```sh
python -m pip install personagent
personagent
```

Avec [uv](https://docs.astral.sh/uv/), `uvx personagent` le lance sans étape d'installation séparée.

Un agent de code peut faire la configuration pour vous : demandez-lui de lire [setup-for-agents.md](setup-for-agents.md) et de configurer personagent.

Sous Windows, vous pouvez aussi télécharger le ZIP des sources, le décompresser et double-cliquer sur `start.bat`. Il crée son propre environnement Python dans le dossier et ouvre la même page.

Pour le lancer depuis un clone, donnez-lui son propre venv : `python -m venv .venv`, puis `.venv/bin/python -m pip install -e .` et `.venv/bin/python -m persona_agent`. Sous Windows, l'interpréteur est `.venv\Scripts\python.exe`, ou vous pouvez double-cliquer sur `start.bat`.

## Ajouter une clé et discuter

Choisissez un service de modèles, collez sa clé d'API et cliquez sur **Vérifier et discuter**. Les modèles gratuits d'OpenRouter et le personnage de l'oreille bienveillante sont sélectionnés au départ. La clé est gratuite et la limite est de 50 requêtes par jour. **Réglages avancés** contient le nom du modèle et l'adresse de l'API, et **Choisir un nom ou une personnalité** contient le nom et la personnalité du personnage.

La clé reste sur votre ordinateur ; cliquez sur **Afficher** pour la vérifier. Les messages du chat vont au service de modèles que vous choisissez, aux tarifs habituels de ce service.

Votre personnage répond dans la page. Vos réglages sont enregistrés : le prochain lancement va directement au chat.

Une fois la configuration faite, **Personnage et réglages** contient une zone **Fiche du personnage** avec le texte sur lequel repose le personnage. Réécrivez qui il est et comment il parle, puis cliquez sur **Enregistrer la fiche**. Le changement s'applique aussitôt et ce que le personnage a appris est conservé.

En dessous, **Autres fonctions** active la recherche web, la compréhension des images et la prise de parole spontanée. La recherche utilise DuckDuckGo par défaut ; une clé Tavily la rend plus fiable. Tant que vous n'avez pas connecté d'application, la vue **Discussion** affiche une courte barre de prise en main.

## L'emmener dans d'autres applications

1. Cliquez sur **Connecter des applis** et choisissez une application. Une fois connectée, votre personnage répond dans les groupes et les messages privés de cette application.
   - **Scanner pour connecter** : QQ et WeChat personnel. Cliquez sur **Obtenir un QR code** et confirmez sur votre téléphone.
     - QQ : scannez avec QQ sur mobile. QQ crée un bot ou vous laisse en choisir un que vous avez déjà, et personagent récupère ses clés. Si vous avez créé le bot vous-même sur la [page des bots QQ](https://q.qq.com/qqbot/openclaw/login.html), cliquez sur **Coller des valeurs à la place** et saisissez son AppID et son AppSecret.
     - WeChat : scannez avec WeChat. Le bot ne discute qu'en tête-à-tête, car WeChat ne transmet pas les messages de groupe à ces bots.
   - **Coller une ou deux valeurs** : Telegram (un jeton de @BotFather), Discord (un jeton de bot, avec Message Content Intent activé), KOOK, Feishu, DingTalk, Slack, bot IA WeCom, Mattermost et Misskey. La page vous indique quelles valeurs copier depuis la console de l'application. Tout le reste utilise les valeurs par défaut.
   - **Avancé** : les applications WeCom, les comptes officiels WeChat et les webhooks QQ ont besoin d'une adresse publique qui transfère vers leur port de rappel. OneBot v11 (NapCat) et Satori ont besoin d'un autre logiciel en cours d'exécution sur cet ordinateur.
2. personagent connecte lui-même QQ, WeChat, Telegram et Discord. Les autres applications passent par AstrBot, une passerelle tierce. La première fois que vous en connectez une, personagent télécharge AstrBot avec un environnement Python 3.12 séparé : gardez la page ouverte jusqu'à la fin. AstrBot tourne ensuite en arrière-plan, sans tableau de bord auquel se connecter.
3. personagent vérifie les identifiants auprès de l'application avant de les enregistrer. Si l'application les refuse, la page vous le dit et rien n'est enregistré.
4. Les applications connectées sont listées en haut de **Connecter des applis**, où vous pouvez les reconfigurer ou les déconnecter.

Pour trouver un bot QQ, ouvrez QQ sur mobile et allez dans Contacts → Bots. Discutez avec lui en privé ou ajoutez-le à un groupe dont vous êtes propriétaire. Cette voie utilise la plateforme officielle de bots de QQ : il ne vous faut ni compte QQ personnel ni logiciel supplémentaire. QQ décide où le bot peut aller. Tant que le bot n'est pas certifié, il ne peut rejoindre que les groupes dont son administrateur est propriétaire, et il n'y a pas de bac à sable à configurer. Dans un groupe, il ne voit que les messages qui le mentionnent avec @, sauf si le propriétaire du groupe active la réception de tous les messages sur le profil du bot dans ce groupe. Le [guide des bots QQ](https://bot.q.qq.com/wiki/bot_new_product-intro/) couvre la certification et le reste côté compte.

Si un QR code expire, demandez-en un nouveau. Si un téléchargement échoue, relancez-le sans refaire la configuration du modèle. Connecter une application n'ouvre au personnage que les groupes et les messages privés de cette application ; les autres adaptateurs gardent leurs listes d'autorisation. LINE n'est pas proposé, car AstrBot ne reçoit les rappels de LINE que par son tableau de bord, que personagent ne lance pas.

## La prochaine fois

Rouvrez personagent. Vos réglages sont conservés et les applications connectées reprennent toutes seules. S'il tourne déjà, le rouvrir réutilise la page en cours. Gardez sa fenêtre de lancement ouverte pendant que vous l'utilisez. Les processus qu'il a démarrés s'arrêtent avec lui, que vous cliquiez sur **Quitter** ou que vous fermiez la fenêtre, et ce qu'un plantage a laissé derrière lui est arrêté au démarrage suivant.

Quand une version plus récente est sur PyPI, la vue **Discussion** affiche un avis avec un lien vers les notes de version et la commande de mise à jour adaptée à la façon dont cette copie a été installée. Une copie issue du ZIP des sources reçoit à la place un lien pour télécharger les nouvelles sources depuis la page des versions. personagent interroge pypi.org au plus une fois par jour, et la requête ne contient que son numéro de version. Définissez `UPDATE_CHECK_ENABLED=false` dans `.env` pour désactiver la vérification.

Si vous préférez la ligne de commande, utilisez `personagent start --terminal`, `personagent init --terminal`, `personagent up`, ou les commandes `chat`, `demo` (sans clé), `run` et `connect`. Elles conservent votre `.env`, votre persona modifiée et les souvenirs appris. Le [guide complet](guide.fr.md) couvre les autres plateformes.
