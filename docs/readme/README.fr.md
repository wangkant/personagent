<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent : conversations illustrées" width="100%">
</p>

<h3 align="center">Un personnage pour vos discussions de groupe, qui sait quand se taire et apprend de ses corrections.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?color=3776AB&label=PyPI&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://github.com/wangkant/personagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f855a.svg" alt="Licence : MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <strong>Français</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Ceci est une traduction du README anglais, qui fait référence et peut être plus récent. Les guides vers lesquels il renvoie sont en anglais.*

personagent est un personnage pour vos discussions de groupe : choisissez-en un ou écrivez le vôtre, et faites-le tourner sur n'importe quel modèle compatible OpenAI. Il se connecte lui-même à QQ, WeChat, Telegram et Discord, et à KOOK, Feishu, DingTalk, Slack, WeCom, Mattermost et Misskey depuis la même page.

Commencez par une discussion locale dans le navigateur : ajoutez une clé de modèle et dites bonjour. Quand vous voulez le personnage dans un groupe, connectez une appli d'un scan avec votre téléphone ou avec une ou deux valeurs.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="L'écran Connecter des applis de la page locale, avec toutes les plateformes que le personnage peut rejoindre" width="960">
</p>

<p align="center"><em>Connecter des applis, dans la même page locale que la configuration et la discussion avec le personnage. Capture d'écran d'une installation jetable avec un modèle de test local.</em></p>

## Pour commencer

Installez-le depuis PyPI et ouvrez-le :

```sh
python -m pip install personagent
personagent
```

Avec [uv](https://docs.astral.sh/uv/), `uvx personagent` le lance sans étape d'installation séparée.

Le navigateur s'ouvre sur une page locale avec trois vues : **Discussion**, **Connecter des applis** et **Personnage et réglages**. Collez la clé API de votre modèle et cliquez sur **Vérifier et discuter** ; une petite requête la vérifie. Il y a 10 services de modèle préréglés, plus tout autre service compatible OpenAI, ainsi que des noms et des personnalités prédéfinis pour le personnage. Le champ **Fiche du personnage** contient `persona.txt` ; l'enregistrer redémarre l'agent et conserve ce qu'il a appris. **Autres fonctions** active la recherche web, la compréhension des images et la prise de parole en premier. Relancer `personagent` réutilise une page déjà ouverte. Le menu en haut à droite affiche la page en anglais, en chinois ou dans huit autres langues. Le personnage répond dans la langue de la discussion ; ses prompts intégrés et ses données sont en anglais et en chinois, donc son aisance dans une autre langue dépend du modèle.

Sous Windows, vous pouvez aussi télécharger le ZIP des sources et double-cliquer sur `start.bat`. Python 3.10–3.14. Consultez le [petit guide de démarrage](https://github.com/wangkant/personagent/blob/main/docs/start.md) ; les commandes du terminal et les connecteurs sont dans le [guide complet](https://github.com/wangkant/personagent/blob/main/docs/guide.md).

## Laissez votre agent de code l'installer

Un agent de code capable d'exécuter des commandes sur votre ordinateur peut installer et configurer personagent pour vous. Donnez-lui ceci :

```text
Lis https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md et installe personagent pour moi.
```

Il vous demande la langue, le nom et la personnalité du personnage, votre service de modèle et les applis de discussion voulues, puis installe personagent, crée le dossier personnel et lance la page locale. Vous collez vous-même votre clé de modèle dans cette page : la clé ne passe donc jamais par l'agent. Les [instructions qu'il suit](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md) sont du Markdown simple, que vous pouvez lire aussi.

## Pourquoi personagent

<table>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/listening.webp" alt="" width="220"></td>
<td valign="top">
<strong>Il sait quand se taire.</strong><br>
Il répond quand on l'appelle. Sinon, un modèle juge si une personne interviendrait : pas de coup de dés.<br>
Une rafale de messages reçoit une seule réponse, pas une par message.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/learned-notebook.webp" alt="" width="220"></td>
<td valign="top">
<strong>Il apprend des corrections qui tiennent la route.</strong><br>
Ce qu'une correction lui apprend, comme le nom que le groupe donne à la salle de sport, se retrouve dans toutes ses réponses suivantes dans cette discussion.<br>
Un changement demande deux réactions concordantes venues de la même discussion, dont une forte.<br>
Un troll ou un simple spectateur ne peut pas le rééduquer.<br>
Chaque changement est consigné, et chacun peut être annulé.
</td>
</tr>
<tr>
<td width="220" valign="top"><img src="https://raw.githubusercontent.com/wangkant/personagent/main/persona_agent/static/empty-chats.webp" alt="" width="220"></td>
<td valign="top">
<strong>Il est facile à lancer et vit là où se trouve votre groupe.</strong><br>
Configuration et discussion dans le navigateur, en anglais, en chinois ou dans huit autres langues, avec 11 services de modèle et des réglages avancés facultatifs.<br>
Il rejoint lui-même QQ, WeChat, Telegram et Discord, et une douzaine d'autres applis depuis la même page ; sa vue Activité montre ce qu'il a fait.
</td>
</tr>
</table>

- Chaque discussion a sa propre mémoire.
- Modifier le personnage conserve ce qu'il a appris.
- Il est mesuré : `personagent eval` évalue quand il parle, s'il reste dans son rôle et si les corrections tiennent ([résultats](https://github.com/wangkant/personagent#measured)).

## Mettez-le dans votre groupe

Ouvrez **Connecter des applis** dans la page locale. Les applis y sont regroupées ainsi :

| Sur la page | Applis | Ce qu'il vous faut |
|---|---|---|
| Scanner pour connecter | QQ, WeChat personnel | Votre téléphone. Les bots WeChat n'ont que des discussions en tête-à-tête |
| Coller une ou deux valeurs | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, bot IA WeCom, Mattermost, Misskey | Des valeurs issues de la console de l'appli ; la page indique lesquelles |
| Avancé | Appli WeCom, compte officiel WeChat, webhook QQ, OneBot v11 (NapCat), Satori | Une adresse publique, ou un autre logiciel sur cet ordinateur |

Les identifiants sont vérifiés avant d'être enregistrés, et les applis connectées redémarrent à chaque lancement de personagent. personagent connecte lui-même QQ, WeChat, Telegram et Discord ; les autres passent par un [AstrBot](https://github.com/AstrBotDevs/AstrBot) qu'il télécharge et fait tourner en arrière-plan, sans rien d'autre à ouvrir. Sur un serveur, `personagent up` démarre le personnage et toutes les applis connectées sans navigateur.

**Vous utilisez déjà AstrBot, Koishi ou Matrix ?** Pour un AstrBot sur cet ordinateur, `personagent connect astrbot` installe le plugin et le token partagé. Pour un AstrBot sur une autre machine, téléversez `astrbot_plugin_personagent.zip` depuis la [dernière version](https://github.com/wangkant/personagent/releases/latest) via **Install from File** sur sa page de plugins, puis réglez son token et l'adresse HTTPS de personagent comme l'expliquent les guides ci-dessous. [Koishi](https://koishi.chat) se connecte via le [connecteur Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.md), et [Matrix](https://matrix.org), avec WhatsApp et Signal derrière des ponts mautrix, via le [connecteur Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.md).

La configuration de chacun est décrite dans le [guide d'utilisation](https://github.com/wangkant/personagent/blob/main/docs/guide.md#put-it-in-a-chat) et le [guide de déploiement](https://github.com/wangkant/personagent/blob/main/docs/deploy.md) ; le [guide pas à pas en chinois](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md) couvre QQ en partant de zéro.

## Comparaison

Les projets auxquels on le compare le plus souvent, d'après la documentation de chacun en octobre 2026 :

- **AstrBot** (AGPL-3.0) est un framework de bots pour plus de 18 plateformes, avec une WebUI et un vaste catalogue de plugins. Il peut répondre sans être sollicité, au hasard (10 % du temps, désactivé par défaut), et laisse l'apprentissage aux plugins.
- **MaiBot** (GPL-3.0) est un bot à personnage pour QQ, via NapCat, avec une WebUI et un lanceur en un clic. Un modèle planificateur décide de la fréquence à laquelle il parle, et il reprend les expressions et l'argot de la discussion.
- **Le plugin de personnage de ChatLuna** pour Koishi (AGPL-3.0) intervient selon des règles : un intervalle fixe, l'activité de la discussion ou la durée depuis laquelle elle est silencieuse.
- **ElizaOS** (MIT) est un framework d'agents en TypeScript pour Discord, Telegram, Slack et d'autres, où un modèle décide s'il faut répondre.

Ce que personagent intègre d'office, là où les autres s'en remettent aux plugins ou n'en parlent pas : il apprend de la façon dont les gens réagissent à ses réponses (corrections, refus, nouvelles tentatives qu'ils ont acceptées) ; un changement demande deux réactions concordantes venues de la même discussion, dont une forte ; chaque changement est journalisé et peut être annulé ; et son comportement est mesuré dans une évaluation publiée ([ci-dessous](https://github.com/wangkant/personagent#measured)).

Là où ils ont de l'avance : des applis de bureau avec tous les réglages dans une WebUI, de grands écosystèmes de plugins, ainsi que l'argot, les packs de stickers et la mémoire des images. Si vous utilisez déjà AstrBot ou Koishi, inutile de choisir : personagent peut fonctionner derrière l'un ou l'autre comme personnage.

## Mesures

`personagent eval` fait passer le véritable agent par des moments de discussion annotés. La dernière exécution, le 2026-10-18, a testé le personnage fourni sur deux modèles via OpenRouter, a essayé chaque cas trois fois et a fait juger le tout à l'aveugle par Claude Opus 5.5. Anglais / chinois :

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| A raison sur le moment de parler (60 moments) | 83 % / 80 % | 93 % / 91 % |
| Joue le personnage mieux que le même modèle avec son seul prompt (40 moments) | 63 % / 58 % | 75 % / 53 % |
| Utilise ce qu'une correction lui a appris dans un message ultérieur, formulé autrement | 76 % / 56 % | 71 % / 67 % |

- Il ignore rarement un message qui lui est destiné. La plupart des ratés viennent de son nom employé pour autre chose, comme un cinéma ou un chiot.
- En chinois, son avantage sur le prompt seul reste dans la marge de bruit.
- Avant que les corrections ne conservent leur leçon, ce qui a été corrigé après la première exécution ce jour-là, seuls 2 messages ultérieurs sur 58 l'utilisaient.
- Aucune correction venant d'un troll, d'un spectateur ou de quelqu'un parti en cours de route n'est passée, sur 84 tentatives.

Les [résultats complets](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) donnent les intervalles, les ratés par type, la méthode, ce que les chiffres ne montrent pas, et chaque rapport.

## Documentation

- [Guide d'utilisation](https://github.com/wangkant/personagent/blob/main/docs/guide.md) ([中文](https://github.com/wangkant/personagent/blob/main/docs/guide.zh-CN.md)) : installation, configuration, discussion dans le terminal, connecteurs, comment lui apprendre, la vue Activité, dépannage.
- [Guide de déploiement](https://github.com/wangkant/personagent/blob/main/docs/deploy.md) : le faire tourner pour de vrai : connecteurs, QQ, exposition des points d'accès, coûts, et que vérifier quand le bot se tait.
- [中文部署教程](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md) : QQ en partant de zéro, pas à pas.
- [Protocole des connecteurs](https://github.com/wangkant/personagent/blob/main/docs/connectors.md) : une requête HTTP signée par message, pour écrire votre propre connecteur.
- [Outils](https://github.com/wangkant/personagent/blob/main/docs/tools.md) : les scripts de `tools/`, à lancer depuis un clone.
- [Journal des modifications](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md), dont la [mise à niveau depuis la 0.4](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md#upgrading-from-04).
- [Contribuer](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Politique de sécurité](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Avertissement](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.md)

## Confidentialité

Tout ce que personagent stocke reste sur votre machine, dans un seul dossier personnel : `.env` avec vos clés, `persona.txt`, `runtime/`, et `platforms/` avec l'AstrBot géré et les identifiants des connexions directes. Le fournisseur de modèle que vous choisissez voit bien les conversations auxquelles il répond, et une fois par jour personagent demande à pypi.org si une version plus récente est sortie (`UPDATE_CHECK_ENABLED=false` désactive cette vérification). Avant de le mettre en contact avec de vraies personnes, prévenez-les que c'est un bot et obtenez leur consentement ; le [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.md#privacy-and-consent) détaille précisément ce qui va où.

## État du projet

La version 1.3.1 est sur PyPI, publiée le 2026-10-26. QQ est la plateforme la plus éprouvée, via AstrBot en 1.0 et directement depuis la 1.1. Les connexions WeChat, Telegram et Discord vérifient les identifiants auprès des vrais services avant l'enregistrement et sont, pour le reste, testées contre des simulacres ; les connecteurs Satori et Matrix sont testés contre des simulacres. La CI exécute les tests sous Linux avec Python 3.10–3.14 et sous Windows avec Python 3.12, plus des jobs qui installent le paquet et pilotent la commande et la page locale.

## Licence

[MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang.

## Remerciements

- Les autres plateformes de discussion sont atteintes via [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) avec [satori-python](https://github.com/RF-Tar-Railt/satori-python), et [matrix-nio](https://github.com/matrix-nio/matrix-nio) avec les [ponts mautrix](https://docs.mau.fi/bridges/) ; la connexion WeChat suit les [notes de protocole openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) de Tencent.
- L'apprentissage à partir des réactions s'inspire de [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), de [l'auto-apprentissage d'Alexa](https://arxiv.org/abs/1911.02557) et de [BlenderBot 3x](https://arxiv.org/abs/2306.04707) ; le lorebook suit le World Info de [SillyTavern](https://github.com/SillyTavern/SillyTavern).
