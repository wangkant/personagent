# Disclaimer

[English](DISCLAIMER.md) · [简体中文](DISCLAIMER.zh-CN.md)

personagent is free software under the [MIT License](LICENSE). It puts an AI
character in chats, and you are the one who runs it: what it says, where it
says it, and which accounts it uses are your responsibility. This page lists
the risks that are easy to miss. It is not legal advice.

## Chat platforms and your accounts

personagent never logs in to a chat platform. A connector does, and what
that connector is decides your risk.

- **Official bot APIs** (Telegram, Discord, Slack, KOOK, Lark, DingTalk, LINE,
  the official QQ bot API and similar) are made for bots. You still have to
  follow each platform's developer terms and rate limits.
- **Unofficial clients** log in as an ordinary user account and drive it by
  software. The platform does not sanction this, may forbid it in its terms,
  and can restrict, freeze or permanently ban the account. This covers:
  - **QQ through NapCat, LLOneBot, Lagrange or any other OneBot
    implementation.** Tencent does not sanction them. The risk is highest from
    cloud or overseas IP addresses.
  - **WhatsApp, Signal, Messenger, Instagram, Google Messages and others
    through a mautrix bridge** (the Matrix connector). The bridge is an
    unofficial client of the network, and some of these networks name
    automated messaging in their terms. See
    [the Matrix connector's notes](integrations/matrix/README.md#terms-of-each-network).
  - Anything else that logs in as a person.

If you use one, use a dedicated account you can afford to lose, never your
main one, and run it from a home network rather than a cloud server where you
can. Read the current terms of every network you connect: they change, and the
account at stake is yours. Neither the author of personagent nor the
maintainers of AstrBot, NapCat, Koishi, mautrix or any other project it works
with accept liability for a lost or restricted account.

## Tell people it is a bot

- Tell the people in a chat that they are talking to an AI, and get the
  agreement of the group's owner or admins before you add it. Give the
  account a name that makes it obvious, and say so in its profile where the
  platform has one.
- Asked sincerely whether it is an AI, personagent is built to say so. Do not
  edit the persona to deny it.
- Do not use it to impersonate a real person, or to mislead anyone about who
  or what they are talking to. Some platforms and some countries require bots
  to be disclosed or restrict automated accounts; check yours.
- Do not put it in groups where its replies could harm or mislead people:
  medical, legal, financial or crisis topics, or groups with children. A model
  is often wrong and sounds sure of itself.
- If someone asks it to leave, or asks what it knows about them, take that
  seriously. The admin can make it forget a note (`<name>, forget ...`), and
  everything it stores is in its home folder (see below).

## What your model provider sees

Each reply sends the model provider a prompt made of the persona, recent
messages from the chat (names included), notes the bot has kept about the
chat, and what it retrieved from what it learned. Images go to your vision
model if you set one. Other services you turn on see parts of it too: the
fallback, judge, self-evaluation and embedding endpoints you configure, and
the web search, which sends a short query to Tavily (if you set a key) or to
DuckDuckGo.

Read each provider's data-retention policy before you use it. Some providers
keep prompts, and some train on them unless you opt out. A local model (Ollama,
llama.cpp) keeps the prompts on your machine. The people in the chat did not
agree to any provider's terms; tell them where their messages go.

## What it stores on your machine

Everything it keeps is under its home folder: settings and API keys in `.env`,
and in `runtime/` the chat notes, the reactions it judged (quoted verbatim),
the ledger of what it learned, and the learned examples. Logs can hold
conversation details if you set `SERVER_LOG_FILE`. Keep the folder private,
never publish it or attach it to an issue, and back it up if you care about
what it learned. Laws on storing and processing other people's messages differ
between countries; following yours is your responsibility.

It can learn something wrong. A change needs two agreeing reactions from the
same chat, at least one of them from the person the reply was for, and every
change is in an append-only ledger that you can review and undo with
`personagent learned` or the dashboard. Look at it now and then.

## No warranty

The software is provided "as is", without warranty of any kind, express or
implied. The authors are not liable for any claim, damage or loss arising from
its use. See [LICENSE](LICENSE).
