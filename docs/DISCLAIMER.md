# Disclaimer

[English](DISCLAIMER.md) · [简体中文](DISCLAIMER.zh-CN.md)

personagent is free software under the [MIT License](../LICENSE). It puts an AI
character in your chats, and you are the one who runs it. You are responsible
for what it says, where it says it and which accounts it uses. This page lists
the risks that are easy to miss. It is not legal advice.

## Chat platforms and your accounts

personagent reaches a chat platform in one of two ways. It connects QQ
official bots, personal WeChat, Telegram and Discord itself. Every other
platform goes through a third-party bridge, usually the AstrBot that
personagent downloads and runs for you. Your risk depends on what the
connection logs in as.

- **Official bot APIs** are made for bots. These include the official QQ bot
  API, Tencent's iLink bot API for personal WeChat, Telegram, Discord, Slack,
  KOOK, Feishu/Lark, DingTalk, WeCom and similar platforms. You still have to
  follow each platform's developer terms and rate limits.
- **Unofficial clients** log in as an ordinary user account and drive it with
  software. The platform does not sanction this and may forbid it in its
  terms. It can restrict, freeze or permanently ban the account. This covers:
  - **QQ through NapCat, LLOneBot, Lagrange or any other OneBot
    implementation**, which is the advanced OneBot v11 option. An official QQ
    bot needs none of these. Tencent does not sanction them, and the risk is
    highest from cloud or overseas IP addresses.
  - **WhatsApp, Signal, Messenger, Instagram, Google Messages and others
    through a mautrix bridge**, which is how the Matrix connector reaches
    them. The bridge is an unofficial client of each network, and some of
    these networks address automated messaging in their terms. See
    [the Matrix connector's notes](../integrations/matrix/README.md#terms-of-each-network).
  - Anything else that logs in as a person.

If you use one of these, use a dedicated account you can afford to lose, never
your main one. Where you can, run it from a home network rather than a cloud
server. Read the current terms of every network you connect. Terms change, and
the account at stake is yours. Neither the author of personagent nor the
maintainers of any third-party project it works with (AstrBot, NapCat, Koishi,
mautrix and others) accept liability for a lost or restricted account.

## Tell people it is a bot

- Tell the people in a chat that they are talking to an AI, and get the
  agreement of the group's owner or admins before you add it. Give the
  account a name that makes this obvious, and say so in its profile where the
  platform has one.
- When someone sincerely asks whether it is an AI, personagent is built to say
  so. Do not edit the persona to make it deny this.
- Do not use it to impersonate a real person, or to mislead anyone about who
  or what they are talking to. Some platforms and some countries require bots
  to be disclosed or restrict automated accounts. Check the rules that apply
  to you.
- Keep it out of groups where its replies could harm or mislead people, such
  as groups about medical, legal, financial or crisis topics, and groups with
  children. A model is often wrong and sounds sure of itself.
- If someone asks it to leave, or asks what it knows about them, take that
  seriously. The admin can make it forget a note (`<name>, forget ...`), and
  everything it stores is in its home folder (see below).

## What your model provider sees

Each reply sends the model provider a prompt made of the persona, recent
messages from the chat (names included), the notes the bot has kept about the
chat, and what it retrieved from what it has learned. If you set a vision
model, images go to it. Other services you turn on see parts of this too. They
include the fallback, judge, self-evaluation and embedding endpoints you
configure, and web search, which sends a short query to Tavily if you set a
key and to DuckDuckGo otherwise. The update check sends pypi.org only
personagent's version number, at most once a day; `UPDATE_CHECK_ENABLED=false`
turns it off.

Read each provider's data-retention policy before you use it. Some providers
keep prompts, and some train on them unless you opt out. A local model (Ollama,
llama.cpp) keeps the prompts on your machine. The people in the chat did not
agree to any provider's terms, so tell them where their messages go.

## What it stores on your machine

Everything it keeps is under its home folder. Settings and API keys are in
`.env`. Bot credentials and the AstrBot it runs for you are in `platforms/`.
`runtime/` holds the chat notes, the reactions it judged (quoted verbatim),
the ledger of what it learned, and the learned examples. If you set
`SERVER_LOG_FILE`, the logs can hold conversation details too. Keep the folder
private. Never publish it or attach it to an issue, and back it up if you care
about what it has learned. Laws on storing and processing other people's
messages differ between countries, and following yours is your
responsibility.

It can learn something wrong. A change needs two agreeing reactions from the
same chat, at least one of them from the person the reply was for. Every
change is recorded in an append-only ledger, which you can review and undo
with `personagent learned` or in the local page's Activity view. Check it
from time to time.

## No warranty

The software is provided "as is", without warranty of any kind, express or
implied. The authors are not liable for any claim, damage or loss arising from
its use. See [LICENSE](../LICENSE).
