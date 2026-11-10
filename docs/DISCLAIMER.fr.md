# Avertissement

[English](DISCLAIMER.md) · [简体中文](DISCLAIMER.zh-CN.md) · [繁體中文](DISCLAIMER.zh-TW.md) · [日本語](DISCLAIMER.ja.md) · [한국어](DISCLAIMER.ko.md) · [Español](DISCLAIMER.es.md) · Français · [Deutsch](DISCLAIMER.de.md) · [Português (Brasil)](DISCLAIMER.pt-BR.md) · [Русский](DISCLAIMER.ru.md)

personagent est publié sous la [PolyForm Noncommercial License 1.0.0](../LICENSE) : son utilisation, sa modification et son partage sont gratuits à des fins non commerciales, et interdits à des fins commerciales. Il place un personnage d'IA dans vos discussions, et c'est vous qui l'exécutez. Vous êtes responsable de ce qu'il dit, de l'endroit où il le dit et des comptes qu'il utilise. Cette page n'est pas un conseil juridique.

## Les plateformes de discussion et vos comptes

personagent atteint une plateforme de discussion de deux façons. Il connecte lui-même les bots officiels QQ, WeChat personnel, Telegram et Discord. Toute autre plateforme passe par une passerelle tierce, en général l'AstrBot que personagent télécharge et exécute pour vous. Le risque encouru dépend du type de compte avec lequel la connexion s'identifie.

- **Les API officielles de bots** sont faites pour les bots. Elles comprennent l'API officielle de bots QQ, l'API de bots iLink de Tencent pour WeChat personnel, Telegram, Discord, Slack, KOOK, Feishu/Lark, DingTalk, WeCom et des plateformes similaires. Vous devez tout de même respecter les conditions pour développeurs et les limites de débit de chaque plateforme.
- **Les clients non officiels** se connectent comme un compte utilisateur ordinaire et le pilotent par logiciel. La plateforme ne l'autorise pas et peut l'interdire dans ses conditions. Elle peut restreindre, geler ou bannir définitivement le compte. Cela couvre :
  - **QQ via NapCat, LLOneBot, Lagrange ou toute autre implémentation de OneBot**, qui est l'option avancée OneBot v11. Un bot QQ officiel ne nécessite aucun d'entre eux. Tencent ne les autorise pas, et le risque est le plus élevé depuis des adresses IP de cloud ou à l'étranger.
  - **WhatsApp, Signal, Messenger, Instagram, Google Messages et d'autres via une passerelle mautrix**, moyen par lequel le connecteur Matrix les atteint. La passerelle est un client non officiel de chaque réseau, et certains de ces réseaux traitent de la messagerie automatisée dans leurs conditions. Voir [les notes du connecteur Matrix](../integrations/matrix/README.fr.md#conditions-de-chaque-réseau).
  - Tout ce qui se connecte comme une personne.

Si vous utilisez l'un de ces moyens, utilisez un compte dédié que vous pouvez vous permettre de perdre, jamais votre compte principal. Dans la mesure du possible, exécutez-le depuis un réseau domestique plutôt que depuis un serveur cloud. Lisez les conditions en vigueur de chaque réseau que vous connectez. Ni l'auteur de personagent ni les mainteneurs des projets tiers avec lesquels il fonctionne (AstrBot, NapCat, Koishi, mautrix et d'autres) n'acceptent de responsabilité pour un compte perdu ou restreint.

## Informez les personnes qu'il s'agit d'un bot

- Informez les personnes d'une discussion qu'elles s'adressent à une IA, et obtenez l'accord du propriétaire ou des administrateurs du groupe avant de l'ajouter. Donnez au compte un nom qui le rend évident, et indiquez-le dans son profil lorsque la plateforme en propose un.
- Lorsque quelqu'un demande sincèrement s'il s'agit d'une IA, personagent est conçu pour le confirmer. Ne modifiez pas la fiche du personnage pour le lui faire nier.
- Ne l'utilisez pas pour vous faire passer pour une personne réelle, ni pour tromper quiconque sur la nature de son interlocuteur. Certaines plateformes et certains pays exigent de signaler les bots ou restreignent les comptes automatisés. Vérifiez les règles qui s'appliquent à vous.
- Tenez-le à l'écart des groupes où ses réponses pourraient nuire aux personnes ou les induire en erreur, comme les groupes sur des sujets médicaux, juridiques, financiers ou de crise, et les groupes avec des enfants.
- Si quelqu'un lui demande de partir, ou demande ce qu'il sait sur lui, prenez-le au sérieux. L'administrateur peut lui faire oublier une note (`<name>, forget ...`), et tout ce qu'il stocke se trouve dans son dossier personnel (voir ci-dessous).

## Crédits des portraits

Les portraits de la fille-baleine DeepSeek, de la fille-dragon GPT et de la demoiselle Claude ont été dessinés pour personagent d'après des designs que la communauté dessine déjà. La fille-baleine dérive de 溟月, un personnage original du créateur Bilibili 上善无形 (CC BY-NC-SA 4.0), dans la tenue de soubrette que ZipZipPipe lui a donnée. La fille-dragon suit la dragonne blanche de ZipZipPipe. La demoiselle Claude suit un design de la communauté dont le premier artiste n'est pas connu. Les portraits ont leur propre licence, CC BY-NC-SA 4.0 : conservez le crédit, ne les utilisez pas à des fins commerciales et partagez vos modifications sous la même licence. Voir `persona_agent/static/characters/LICENSE.md`.

## Ce que voit votre fournisseur de modèles

Chaque réponse envoie au fournisseur de modèles un prompt composé de la fiche du personnage, des messages récents de la discussion (noms compris), des notes que le bot a conservées sur la discussion et de ce qu'il a retrouvé dans ce qu'il a appris. Si vous définissez un modèle de vision, les images vont vers lui. D'autres services que vous activez en voient aussi une partie. Ils comprennent les points d'accès de secours, de jugement, d'auto-évaluation et d'embeddings que vous configurez, et la recherche web, qui envoie une courte requête à Tavily si vous définissez une clé et à DuckDuckGo sinon. La vérification des mises à jour n'envoie à pypi.org que le numéro de version de personagent, au plus une fois par jour ; `UPDATE_CHECK_ENABLED=false` la désactive.

Lisez la politique de conservation des données de chaque fournisseur avant de l'utiliser. Certains fournisseurs conservent les prompts, et certains s'en servent pour l'entraînement à moins que vous ne refusiez. La valeur par défaut, les modèles gratuits d'OpenRouter, peut atteindre de tels fournisseurs. Un modèle local (Ollama, llama.cpp) garde les prompts sur votre machine. Les personnes de la discussion n'ont accepté les conditions d'aucun fournisseur : dites-leur où vont leurs messages.

## Ce qu'il stocke sur votre machine

Tout ce qu'il conserve se trouve dans son dossier personnel. Les réglages et les clés d'API sont dans `.env`. Les identifiants des bots et l'AstrBot qu'il exécute pour vous se trouvent dans `platforms/`. `runtime/` contient les notes de discussion, les réactions qu'il a jugées (citées mot pour mot), le registre de ce qu'il a appris et les exemples appris. Si vous définissez `SERVER_LOG_FILE`, les journaux peuvent aussi contenir des détails des conversations. Conservez ce dossier à l'abri des regards. Ne le publiez jamais et ne le joignez jamais à un ticket, et sauvegardez-le si ce qu'il a appris compte pour vous. Les lois sur le stockage et le traitement des messages d'autrui varient selon les pays, et respecter les vôtres relève de votre responsabilité.

Il peut apprendre quelque chose de faux. Un changement demande deux réactions concordantes de la même discussion, dont au moins une de la personne à qui la réponse s'adressait. Chaque changement est inscrit dans un registre en ajout seul, que vous pouvez consulter et annuler avec `personagent learned` ou dans la vue **Activité** de la page locale. Vérifiez-le de temps en temps.

## Aucune garantie

Le logiciel est fourni « tel quel », sans garantie d'aucune sorte, expresse ou implicite. Les auteurs ne sont responsables d'aucune réclamation, d'aucun dommage ni d'aucune perte résultant de son utilisation. Voir la [LICENSE](../LICENSE).
