<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Un agent qui se comporte comme une personne, sur toutes les plateformes que vous utilisez.<br>Il a un caractère qui lui est propre, se souvient, apprend des personnes avec qui il parle et juge par lui-même quand prendre la parole.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-0969da?style=flat-square&labelColor=24292f" alt="Licence : PolyForm Noncommercial"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <strong>Français</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Ceci est une traduction du README anglais, qui fait référence et peut être plus récent.*

personagent est un agent qui se comporte comme une personne : il a un caractère qui lui est propre, se souvient, apprend des personnes avec qui il parle et juge par lui-même quand prendre la parole. Il fonctionne partout où vous en avez besoin : dans les discussions de groupe et les discussions privées sur QQ, WeChat, Telegram, Discord et dix-huit autres plateformes, dans une fenêtre sur votre ordinateur et au sein d'assistants de programmation tels que Claude Code et Codex. Vous choisissez ou rédigez son caractère, et il fonctionne avec n'importe quel modèle compatible OpenAI.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="La vue Connecter des plateformes de la page locale : les plateformes qui se connectent en scannant un code ou en collant une ou deux valeurs, les plateformes avancées repliées et les assistants de programmation que le personnage peut rejoindre" width="960">
</p>

<p align="center"><em>Connecter des plateformes, dans la même page locale que la configuration et la discussion avec le personnage.</em></p>

## Pourquoi personagent

<table>
<tr>
<td width="220" valign="top"><strong>Il a un caractère qui lui est propre.</strong></td>
<td valign="top">
Sept personnalités prédéfinies. Trois sont des personnages que la communauté dessine déjà : la fille-baleine DeepSeek, la fille-dragon GPT et la demoiselle Claude, avec des portraits qui clignent des yeux, réfléchissent et parlent.<br>
Vous pouvez réécrire la fiche du personnage à tout moment. Ce qu'il a appris est conservé.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Il se souvient.</strong></td>
<td valign="top">
Chaque discussion a sa propre mémoire : des messages récents qui survivent à un redémarrage, un résumé de la conversation antérieure, des événements datés et des faits concernant les personnes, qu'il tient à jour lui-même.<br>
Tout ce dont il se souvient figure dans la vue **Activité**, où chaque élément peut être oublié ou rétabli.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Il apprend des corrections confirmées.</strong></td>
<td valign="top">
Ce qu'une correction lui apprend, comme le nom que le groupe donne à la salle de sport, se retrouve dans toutes ses réponses suivantes dans cette discussion.<br>
Un troll ou un simple spectateur ne peut pas le rééduquer.<br>
Lorsque les réactions ne permettent pas de trancher un changement, il décide lui-même et consigne pourquoi ; personne n'a rien à approuver.<br>
Chaque changement est consigné, et chacun peut être annulé.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Il sait quand se taire.</strong></td>
<td valign="top">
Dans un groupe, il répond quand on l'appelle. Sinon, un modèle juge si une personne interviendrait.<br>
Une rafale de messages reçoit une seule réponse.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Il se connecte à toutes vos plateformes.</strong></td>
<td valign="top">
Vingt-deux plateformes de discussion se connectent depuis une seule page, en scannant un code avec votre téléphone ou en collant une ou deux valeurs, pour les discussions de groupe comme pour les discussions privées.<br>
Le même agent répond dans une fenêtre sur votre ordinateur ainsi que dans Claude Code, Codex et DeepSeek Harness.<br>
Toute autre plateforme peut être ajoutée par un pont AstrBot, Koishi ou Matrix, ou par un connecteur que vous écrivez.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Il fonctionne avec ce que vous avez.</strong></td>
<td valign="top">
N'importe quel modèle compatible OpenAI : les modèles gratuits d'OpenRouter, un service payant ou un modèle exécuté sur votre propre ordinateur avec Ollama.<br>
Une seule commande l'ouvre, en anglais, en chinois ou dans huit autres langues, et une clé de modèle collée suffit pour commencer la discussion.
</td>
</tr>
</table>

Il retient et oublie aussi ce qu'on lui demande dans la discussion : `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian` ([commandes de mémoire](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#commandes-de-mémoire)). Ce qu'il conserve, et pour combien de temps, est décrit dans la section [mémoire](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#mémoire) du guide.

## Pour commencer

```sh
python -m pip install personagent
personagent
```

Avec [uv](https://docs.astral.sh/uv/), `uvx personagent` le lance sans étape d'installation séparée. Sous Windows, vous pouvez aussi télécharger le ZIP des sources et double-cliquer sur `start.bat`.

Il s'ouvre dans sa propre fenêtre sous Windows, et dans votre navigateur sous macOS et Linux. Collez une clé API de modèle et cliquez sur **Vérifier et commencer la discussion**. Vous n'avez pas encore de clé ? Les modèles gratuits d'OpenRouter sont présélectionnés, et leur clé ne coûte rien. `personagent demo` joue trois scènes écrites d'avance sans aucune clé. Le [guide de démarrage](https://github.com/wangkant/personagent/blob/main/docs/start.fr.md) parcourt la page écran par écran.

personagent est gratuit. Vous payez le service de modèle que vous choisissez, à ses propres tarifs. Les modèles gratuits d'OpenRouter autorisent 50 requêtes par jour, et certains fournisseurs gratuits conservent ce qu'ils reçoivent ; Ollama exécute un modèle sur votre propre ordinateur, sans clé.

## Connectez vos plateformes

Ouvrez **Connecter des plateformes** dans la page locale :

| Sur la page | Plateformes | Ce dont vous avez besoin |
|---|---|---|
| Scanner pour connecter | QQ, WeChat personnel | Votre téléphone. Les bots WeChat ne gèrent que les discussions individuelles |
| Coller une ou deux valeurs | Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, KOOK, Feishu/Lark, DingTalk, Slack, bot IA WeCom, Mattermost, Misskey | Des valeurs issues de la console de la plateforme ; la page indique lesquelles |
| Avancé | Application WeCom, compte officiel WeChat, webhook QQ, OneBot v11 (NapCat), Satori | Une adresse publique, ou un autre logiciel sur cet ordinateur |

Les plateformes connectées redémarrent à chaque lancement de personagent. personagent connecte lui-même les plateformes à scanner, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK et Stoat ; les autres passent par un [AstrBot](https://github.com/AstrBotDevs/AstrBot) qu'il télécharge et exécute en arrière-plan. Sur un serveur sans écran, `personagent connect <plateforme>` connecte n'importe laquelle de ces dix plateformes depuis le terminal, avec les mêmes étapes et les mêmes vérifications que la page, et `personagent up` démarre tout sans navigateur. La configuration de chaque plateforme est décrite dans le [guide d'utilisation](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#le-placer-dans-une-discussion), et QQ en partant de zéro dans le [guide de déploiement en chinois](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Vous utilisez déjà AstrBot, Koishi ou Matrix ? personagent peut se placer derrière comme agent : voir les [ponts que vous exécutez vous-même](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#ponts-que-vous-exécutez-vous-même), le [connecteur Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.fr.md) et le [connecteur Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.fr.md).

## Assistants de programmation

**Laissez-en un s'occuper de l'installation.** Donnez la ligne ci-dessous à un assistant de programmation capable d'exécuter des commandes sur votre ordinateur. Vous collez vous-même votre clé de modèle dans la page locale : la clé ne passe donc jamais par l'assistant.

```text
Lis https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md et installe personagent pour moi.
```

**Parlez à votre personnage pendant que vous travaillez.** Claude Code, Codex et DeepSeek Harness (`dsh`) peuvent parler au personnage, avec la même conversation et la même mémoire que dans la page locale :

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

`--remove` le retire à nouveau, et **Assistants de programmation**, dans **Connecter des plateformes**, effectue ces deux opérations depuis la page. Le [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#assistants-de-programmation) couvre les autorisations et `--react`, qui permet au personnage de formuler une remarque à la fin d'un tour.

## Mise à jour et désinstallation

Quand une version plus récente est sur PyPI, la page affiche un avis avec la commande de mise à jour. Avec pip, c'est `python -m pip install -U personagent`. Sur la plupart des installations, **Mettre à jour et rouvrir**, dans la vue **Application** de la page, l'exécute pour vous. Les réglages, le personnage, ce qu'il a appris et les plateformes connectées sont conservés. Pour le retirer, suivez les [étapes de désinstallation](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (en anglais).

## Confidentialité

Tout ce que personagent stocke reste sur votre machine, dans un seul dossier personnel. Le fournisseur de modèle que vous choisissez voit les conversations auxquelles il répond, et une fois par jour personagent demande à pypi.org si une version plus récente est sortie (`UPDATE_CHECK_ENABLED=false` désactive cette vérification). Avant de le mettre en contact avec de vraies personnes, informez-les qu'il s'agit d'un bot et obtenez leur consentement ; le [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#confidentialité-et-consentement) détaille ce qui va où.

## Documentation

- [Guide d'utilisation](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md) : configuration, connecteurs, apprentissage, la vue Activité, dépannage.
- [Guide de déploiement](https://github.com/wangkant/personagent/blob/main/docs/deploy.fr.md) : l'exécution en production, les coûts et les vérifications à effectuer lorsque le bot se tait.
- [Protocole des connecteurs](https://github.com/wangkant/personagent/blob/main/docs/connectors.fr.md) : pour écrire votre propre connecteur.
- [Outils](https://github.com/wangkant/personagent/blob/main/docs/tools.fr.md) : les scripts de `tools/`, à lancer depuis un clone.
- [Journal des modifications](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Contribuer](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Politique de sécurité](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Avertissement](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.fr.md)

## Licence

personagent est publié sous la [PolyForm Noncommercial License 1.0.0](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang : son utilisation, sa modification et son partage sont gratuits à des fins non commerciales, et interdits à des fins commerciales. Les connecteurs de `integrations/` restent sous licence MIT, de même que les versions jusqu'à la 1.4.0. Les trois portraits de personnages sont sous licence CC BY-NC-SA 4.0, avec les crédits dans [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Remerciements

- Les autres plateformes de discussion sont atteintes via [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) avec [satori-python](https://github.com/RF-Tar-Railt/satori-python), et [matrix-nio](https://github.com/matrix-nio/matrix-nio) avec les [ponts mautrix](https://docs.mau.fi/bridges/) ; la connexion WeChat suit les [notes de protocole openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) de Tencent.
- L'apprentissage à partir des réactions s'inspire de [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), de [l'auto-apprentissage d'Alexa](https://arxiv.org/abs/1911.02557) et de [BlenderBot 3x](https://arxiv.org/abs/2306.04707) ; le lorebook suit le World Info de [SillyTavern](https://github.com/SillyTavern/SillyTavern).
