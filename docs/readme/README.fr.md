<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/assets/personagent-cover.webp" alt="personagent" width="100%">
</p>

<h3 align="center">Un personnage pour vos discussions de groupe, qui sait quand se taire et apprend de ses corrections.</h3>

<p align="center">
  <a href="https://pypi.org/project/personagent/"><img src="https://img.shields.io/pypi/v/personagent?style=flat-square&label=PyPI&labelColor=24292f&color=0969da&cacheSeconds=3600" alt="PyPI"></a>
  <a href="https://github.com/wangkant/personagent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/wangkant/personagent/ci.yml?branch=main&style=flat-square&label=CI&labelColor=24292f" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-0969da?style=flat-square&labelColor=24292f" alt="Python 3.10–3.14"></a>
  <a href="https://github.com/wangkant/personagent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-0969da?style=flat-square&labelColor=24292f" alt="Licence : MIT"></a>
</p>

<p align="center"><a href="https://github.com/wangkant/personagent/blob/main/README.md">English</a> · <a href="https://github.com/wangkant/personagent/blob/main/README.zh-CN.md">简体中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.zh-TW.md">繁體中文</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ja.md">日本語</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ko.md">한국어</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.es.md">Español</a> · <strong>Français</strong> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.de.md">Deutsch</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.pt-BR.md">Português</a> · <a href="https://github.com/wangkant/personagent/blob/main/docs/readme/README.ru.md">Русский</a></p>

*Ceci est une traduction du README anglais, qui fait référence et peut être plus récent.*

personagent est un personnage pour vos discussions de groupe : choisissez-en un tout prêt ou écrivez le vôtre, et faites-le tourner sur n'importe quel modèle compatible OpenAI. Commencez par discuter avec lui sur votre propre ordinateur, puis emmenez-le sur QQ, WeChat, Telegram, Discord et une douzaine d'autres applis depuis la même page locale.

<p align="center">
  <img src="https://raw.githubusercontent.com/wangkant/personagent/main/docs/welcome.jpg" alt="L'écran Connecter des applis de la page locale, avec toutes les plateformes que le personnage peut rejoindre" width="960">
</p>

<p align="center"><em>Connecter des applis, dans la même page locale que la configuration et la discussion avec le personnage.</em></p>

## Pourquoi personagent

<table>
<tr>
<td width="220" valign="top"><strong>Il sait quand se taire.</strong></td>
<td valign="top">
Il répond quand on l'appelle. Sinon, un modèle juge si une personne interviendrait.<br>
Une rafale de messages reçoit une seule réponse.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Il apprend des corrections qui tiennent la route.</strong></td>
<td valign="top">
Ce qu'une correction lui apprend, comme le nom que le groupe donne à la salle de sport, se retrouve dans toutes ses réponses suivantes dans cette discussion.<br>
Un changement demande deux réactions concordantes venues de la même discussion, dont une forte.<br>
Un troll ou un simple spectateur ne peut pas le rééduquer.<br>
Chaque changement est consigné, et chacun peut être annulé.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Il est facile à lancer et vit là où se trouve votre groupe.</strong></td>
<td valign="top">
Une seule commande l'ouvre sur votre ordinateur, en anglais, en chinois ou dans huit autres langues.<br>
Collez une clé de modèle pour discuter : dix services de modèle sont préréglés, et tout autre service compatible OpenAI fonctionne.<br>
Connectez une appli d'un scan avec votre téléphone ou en collant une ou deux valeurs. La vue Activité montre ce que le personnage y a fait.
</td>
</tr>
<tr>
<td width="220" valign="top"><strong>Il peut être un personnage tout prêt, ou le vôtre.</strong></td>
<td valign="top">
Sept personnalités toutes prêtes. Trois sont des personnages que la communauté dessine déjà, la fille-baleine de DeepSeek, la fille-dragon GPT et la demoiselle Claude, avec des portraits qui clignent des yeux, réfléchissent pendant qu'une réponse se prépare et parlent quand elle arrive.<br>
Réécrivez la fiche du personnage quand vous voulez. Ce qu'il a appris est conservé.
</td>
</tr>
</table>

- Chaque discussion a sa propre mémoire, et il oublie quand on le lui demande : `Nova, remember Sam is vegetarian`, `Nova, forget vegetarian`, `Nova, what do you remember` ([commandes de mémoire](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#commandes-de-mémoire)). Ce qu'un groupe a noté sur quelqu'un le suit dans sa discussion privée avec le personnage, et jamais l'inverse.
- Il répond dans la langue de la discussion. Les personnalités de départ existent dans chacune des dix langues de la page ; les exemples, filtres et prompts fournis sont en anglais et en chinois.
- Il est mesuré : `personagent eval` évalue quand il parle, s'il reste dans son rôle et si les corrections tiennent ([résultats](https://github.com/wangkant/personagent#measured)).

## Pour commencer

```sh
python -m pip install personagent
personagent
```

Avec [uv](https://docs.astral.sh/uv/), `uvx personagent` le lance sans étape d'installation séparée. Sous Windows, vous pouvez aussi télécharger le ZIP des sources et double-cliquer sur `start.bat`, qui laisse aussi une icône personagent sur votre bureau. personagent est testé sous Linux avec Python 3.10–3.14 et sous Windows avec Python 3.12.

Sous Windows, il s'ouvre dans sa propre fenêtre. Sous macOS et Linux, il s'ouvre dans votre navigateur, ou dans une fenêtre aussi après `pip install "personagent[app]"`. Collez une clé API de modèle et cliquez sur **Vérifier et discuter** ; une petite requête vérifie la clé. Pas encore de clé ? Les modèles gratuits d'OpenRouter sont présélectionnés, et leur clé ne coûte rien. Pour le voir à l'œuvre avant d'avoir la moindre clé, `personagent demo` joue gratuitement trois scènes écrites d'avance. Le [guide de démarrage](https://github.com/wangkant/personagent/blob/main/docs/start.fr.md) parcourt la page écran par écran.

## Ce que ça coûte

personagent est gratuit. Vous payez le service de modèle que vous choisissez, à ses propres tarifs.

- **Gratuit pour commencer.** Les modèles gratuits d'OpenRouter autorisent 50 requêtes par jour ; le modèle peut changer d'une requête à l'autre, et certains fournisseurs gratuits conservent ce qu'ils reçoivent. Le `glm-4.7-flash` de Zhipu est gratuit lui aussi, et Ollama fait tourner un modèle sur votre propre ordinateur, sans clé.
- **Ce qui appelle le modèle.** Chaque réponse, et deux étapes plus légères : décider s'il intervient quand personne ne l'a appelé, et juger comment les gens réagissent à ses réponses. `personagent doctor` et `personagent eval` envoient eux aussi des requêtes ; le [guide de déploiement](https://github.com/wangkant/personagent/blob/main/docs/deploy.fr.md#coûts) détaille le reste.
- **Ce qui ne l'appelle jamais.** `personagent demo` et les commandes de mémoire.

## Mettez-le dans votre groupe

Ouvrez **Connecter des applis** dans la page locale. Les applis y sont regroupées ainsi :

| Sur la page | Applis | Ce qu'il vous faut |
|---|---|---|
| Scanner pour connecter | QQ, WeChat personnel | Votre téléphone. Les bots WeChat n'ont que des discussions en tête-à-tête |
| Coller une ou deux valeurs | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, bot IA WeCom, Mattermost, Misskey | Des valeurs issues de la console de l'appli ; la page indique lesquelles |
| Avancé | Appli WeCom, compte officiel WeChat, webhook QQ, OneBot v11 (NapCat), Satori | Une adresse publique, ou un autre logiciel sur cet ordinateur |

Les identifiants sont vérifiés avant d'être enregistrés, et les applis connectées redémarrent à chaque lancement de personagent. personagent connecte lui-même les applis à scanner, Telegram et Discord ; les autres passent par un [AstrBot](https://github.com/AstrBotDevs/AstrBot) qu'il télécharge et fait tourner en arrière-plan, sans rien d'autre à ouvrir. Sur un serveur, `personagent up` démarre le personnage et toutes les applis connectées sans navigateur. La configuration de chaque appli est décrite dans le [guide d'utilisation](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#le-placer-dans-une-discussion), et QQ en partant de zéro, étape par étape, dans le [guide de déploiement en chinois](https://github.com/wangkant/personagent/blob/main/docs/deploy.zh-CN.md).

Vous faites déjà tourner un pont ?

- **AstrBot** : `personagent connect astrbot` installe le plugin et le token partagé. Le [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#ponts-que-vous-exécutez-vous-même) explique comment faire s'il tourne sur une autre machine.
- **[Koishi](https://koishi.chat)**, ou tout serveur Satori : le [connecteur Satori](https://github.com/wangkant/personagent/blob/main/integrations/satori/README.fr.md).
- **[Matrix](https://matrix.org)**, avec WhatsApp et Signal derrière des ponts mautrix : le [connecteur Matrix](https://github.com/wangkant/personagent/blob/main/integrations/matrix/README.fr.md).

## Agents de code

**Laissez-en un s'occuper de l'installation.** Donnez la ligne ci-dessous à un agent de code capable d'exécuter des commandes sur votre ordinateur. Il vous demande ce que vous voulez, installe personagent et lance la page locale. Vous collez vous-même votre clé de modèle dans cette page : la clé ne passe donc jamais par l'agent.

```text
Lis https://raw.githubusercontent.com/wangkant/personagent/main/docs/setup-for-agents.md et installe personagent pour moi.
```

**Parlez à votre personnage pendant que vous travaillez.** Une fois la clé de modèle configurée, Claude Code, Codex et DeepSeek Harness (`dsh`) peuvent parler au personnage :

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

Ouvrez-y une nouvelle session (redémarrez d'abord DeepSeek Harness) et demandez-lui de dire quelque chose à votre personnage. C'est la même conversation privée et la même mémoire que dans la page locale. Sur Claude Code et Codex, `--react` permet au personnage de dire un mot à la fin d'un tour. `--remove` retire le tout. Le [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#agents-de-code) couvre les autorisations, ce que `--react` envoie à votre service de modèle et les autres outils MCP.

## Mesures

`personagent eval` fait passer le véritable agent par des moments de discussion annotés. La dernière exécution, le 2026-10-18, a été mesurée sur la version 1.3.0 : le personnage fourni sur deux modèles via OpenRouter, chaque cas essayé trois fois, et Claude Opus 5.5 comme juge à l'aveugle. Anglais / chinois :

| | deepseek-v4.1-flash | gpt-6-luna |
|---|---|---|
| A raison sur le moment de parler (60 moments) | 83 % / 80 % | 93 % / 91 % |
| Joue le personnage mieux que le même modèle avec son seul prompt (40 moments) | 63 % / 58 % | 75 % / 53 % |
| Utilise ce qu'une correction lui a appris dans un message ultérieur, formulé autrement | 76 % / 56 % | 71 % / 67 % |

- Il ignore rarement un message qui lui est destiné. La plupart des ratés viennent de son nom employé pour autre chose, comme un cinéma ou un chiot.
- Aucune des 84 corrections venant d'un troll, d'un spectateur ou de quelqu'un parti en cours de route n'est passée.

Les [résultats complets](https://github.com/wangkant/personagent/tree/main/docs/evals/2026-10-18) donnent les intervalles, les ratés par type, la méthode et chaque rapport.

## Comparaison

Les projets auxquels on le compare le plus souvent, en novembre 2026 :

- **AstrBot** (AGPL-3.0) est un framework de bots pour plus d'une douzaine de plateformes, avec une WebUI et un vaste catalogue de plugins. Il peut répondre sans être sollicité, au hasard (10 % du temps, désactivé par défaut), et laisse l'apprentissage aux plugins.
- **MaiBot** (GPL-3.0) est un bot à personnage pour QQ, via NapCat, avec une WebUI et un lanceur en un clic. Un modèle planificateur décide de la fréquence à laquelle il parle, et il reprend les expressions et l'argot de la discussion.
- **Le plugin de personnage de ChatLuna** pour Koishi (AGPL-3.0) intervient selon des règles : un intervalle fixe, l'activité de la discussion ou la durée depuis laquelle elle est silencieuse.
- **ElizaOS** (MIT) est un framework d'agents en TypeScript pour Discord, Telegram, Slack et d'autres, où un modèle décide s'il faut répondre.

Ce que personagent intègre d'office : il apprend de la façon dont les gens réagissent à ses réponses (corrections, refus, nouvelles tentatives qu'ils ont acceptées), tient un journal de chaque changement avec de quoi l'annuler, et publie une évaluation de son comportement.

Là où ils ont de l'avance : des applis de bureau avec tous les réglages dans une WebUI, de grands écosystèmes de plugins, ainsi que l'argot, les packs de stickers et la mémoire des images. Si vous utilisez déjà AstrBot ou Koishi, inutile de choisir : personagent peut fonctionner derrière l'un ou l'autre comme personnage.

## Mise à jour et désinstallation

Quand une version plus récente est sur PyPI, la page affiche un avis avec la commande de mise à jour adaptée à votre mode d'installation. Avec pip, c'est `python -m pip install -U personagent`. Le dossier personnel est conservé : réglages, personnage, ce qu'il a appris et applis connectées.

Pour le retirer, enlevez-le d'abord de tout agent de code que vous avez connecté (`personagent connect claude-code --remove`, ou la même commande avec `codex` ou `dsh`). Quittez ensuite personagent et lancez `python -m pip uninstall personagent`. Enfin, supprimez le dossier personnel, soit `~/personagent` pour une installation depuis PyPI, sauf si vous en avez choisi un autre : il contient votre clé, le personnage et tout ce qu'il a appris, c'est donc irréversible. Les [étapes complètes](https://github.com/wangkant/personagent/blob/main/docs/setup-for-agents.md#undoing-it) (en anglais) couvrent uv, pipx et ce qu'il faut révoquer.

## Confidentialité

Tout ce que personagent stocke reste sur votre machine, dans un seul dossier personnel : `.env` avec vos clés, `persona.txt`, `runtime/`, et `platforms/` avec l'AstrBot géré et les identifiants des connexions directes. Le fournisseur de modèle que vous choisissez voit les conversations auxquelles il répond, et une fois par jour personagent demande à pypi.org si une version plus récente est sortie (`UPDATE_CHECK_ENABLED=false` désactive cette vérification). Avant de le mettre en contact avec de vraies personnes, prévenez-les que c'est un bot et obtenez leur consentement ; le [guide](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md#confidentialité-et-consentement) détaille ce qui va où.

## Documentation

- [Guide d'utilisation](https://github.com/wangkant/personagent/blob/main/docs/guide.fr.md) : installation, configuration, discussion dans le terminal, connecteurs, comment lui apprendre, la vue Activité, dépannage.
- [Guide de déploiement](https://github.com/wangkant/personagent/blob/main/docs/deploy.fr.md) : le faire tourner pour de vrai : connecteurs, QQ, exposition des points d'accès, coûts, et que vérifier quand le bot se tait.
- [Protocole des connecteurs](https://github.com/wangkant/personagent/blob/main/docs/connectors.fr.md) : une requête HTTP signée par message, pour écrire votre propre connecteur.
- [Outils](https://github.com/wangkant/personagent/blob/main/docs/tools.fr.md) : les scripts de `tools/`, à lancer depuis un clone.
- [Journal des modifications](https://github.com/wangkant/personagent/blob/main/CHANGELOG.md) · [Contribuer](https://github.com/wangkant/personagent/blob/main/.github/CONTRIBUTING.md) · [Politique de sécurité](https://github.com/wangkant/personagent/blob/main/.github/SECURITY.md) · [Avertissement](https://github.com/wangkant/personagent/blob/main/docs/DISCLAIMER.fr.md)

## Licence

Le code est sous licence [MIT](https://github.com/wangkant/personagent/blob/main/LICENSE) © 2026 Qiankang (Kant) Wang. Les trois portraits de personnages sont sous licence CC BY-NC-SA 4.0, avec les crédits dans [persona_agent/static/characters/LICENSE.md](https://github.com/wangkant/personagent/blob/main/persona_agent/static/characters/LICENSE.md).

## Remerciements

- Les autres plateformes de discussion sont atteintes via [AstrBot](https://github.com/AstrBotDevs/AstrBot), [NapCat](https://github.com/NapNeko/NapCatQQ), [Koishi](https://koishi.chat) avec [satori-python](https://github.com/RF-Tar-Railt/satori-python), et [matrix-nio](https://github.com/matrix-nio/matrix-nio) avec les [ponts mautrix](https://docs.mau.fi/bridges/) ; la connexion WeChat suit les [notes de protocole openclaw-weixin](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol.md) de Tencent.
- L'apprentissage à partir des réactions s'inspire de [Self-Feeding Chatbot](https://arxiv.org/abs/1901.05415), de [l'auto-apprentissage d'Alexa](https://arxiv.org/abs/1911.02557) et de [BlenderBot 3x](https://arxiv.org/abs/2306.04707) ; le lorebook suit le World Info de [SillyTavern](https://github.com/SillyTavern/SillyTavern).
