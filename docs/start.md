# Start using personagent

[中文](start.zh-CN.md) · [Full guide](guide.md)

## Open it

Install personagent from PyPI and open it:

```sh
python -m pip install personagent
personagent
```

With [uv](https://docs.astral.sh/uv/), `uvx personagent` runs it without a separate install step.

A coding agent can do the setup for you: ask it to read [setup-for-agents.md](setup-for-agents.md) and set up personagent.

On Windows you can also download the source ZIP, unpack it and double-click `start.bat`. It creates its own Python environment in the folder and opens the same page.

To run it from a clone, give it a venv of its own: `python -m venv .venv`, then `.venv/bin/python -m pip install -e .` and `.venv/bin/python -m persona_agent`. On Windows the interpreter is `.venv\Scripts\python.exe`, or you can double-click `start.bat`.

## Add a key and chat

Choose a model service, paste its API key and click **Verify & start chatting**. DeepSeek and the warm listener character are selected to begin with. **Advanced settings** holds the model name and API address, and **Choose a name or personality** holds the character's name and personality.

The key stays on your computer. Chat messages go to the model service you choose, and verifying the key and chatting may incur that service's usual charges. Click **Show** if you need to check the key. It is never included in status responses or kept in browser storage.

Your character replies in the page. Your settings are saved, so the next launch goes straight to chat.

Once it is set up, **Character & settings** has a **Persona** box with the text the character runs on. Rewrite who it is and how it talks, then click **Save persona**. The change applies at once, and what the character has learned is kept.

Below it, **More features** turns on web search, image understanding and speaking first. Search uses DuckDuckGo by default; a Tavily key makes it more reliable. Until you connect an app, the Chat view shows a short getting-started bar.

## Bring it to other apps

1. Click **Connect apps** and pick an app. Once connected, your character replies to that app's group chats and DMs.
   - **Scan to connect**: QQ and personal WeChat. Click **Get a QR code** and confirm on your phone.
     - QQ: scan with mobile QQ. QQ creates a bot or lets you pick one you already have, and personagent fetches its keys. If you made the bot yourself on [QQ's bot page](https://q.qq.com/qqbot/openclaw/login.html), click **Paste values instead** and enter its AppID and AppSecret.
     - WeChat: scan with WeChat. The bot chats one to one only, because WeChat does not pass group messages to these bots.
   - **Paste one or two values**: Telegram (a token from @BotFather), Discord (a bot token, with Message Content Intent turned on), KOOK, Feishu, DingTalk, Slack, WeCom AI bot, Mattermost and Misskey. The page tells you which values to copy from the app's console. Everything else uses defaults.
   - **Advanced**: WeCom apps, WeChat Official Accounts and QQ webhooks need a public address that forwards to their callback port. OneBot v11 (NapCat) and Satori need other software running on this computer.
2. personagent connects QQ, WeChat, Telegram and Discord itself. The other apps go through AstrBot, a third-party bridge. The first time you connect one of them, personagent downloads AstrBot with a separate Python 3.12 runtime, so keep the page open until it finishes. AstrBot then runs in the background, with no dashboard to sign in to.
3. personagent checks the credentials with the app before saving them. If the app refuses them, the page tells you and nothing is saved.
4. Connected apps are listed at the top of **Connect apps**, where you can set one up again or disconnect it.

To find a QQ bot, open mobile QQ and go to Contacts → Bots. Chat with it privately, or add it to a group you own. This route uses QQ's official bot platform, so you need no personal QQ account and no extra software. QQ decides where the bot may go. Until the bot is certified, it can join only groups its admin owns, and there is no sandbox to set up. In a group it sees only messages that @ it, unless the group owner turns on receiving all messages on the bot's profile in that group. [QQ's bot guide](https://bot.q.qq.com/wiki/bot_new_product-intro/) covers certification and the rest of the account side.

If a QR code expires, request a new one. If a download fails, retry it without repeating the model setup. Connecting an app opens only that app's groups and DMs to the character; other adapters keep their existing allowlists. LINE is not offered, because AstrBot receives LINE callbacks only through its dashboard, which personagent does not run.

## Next time

Open personagent again. Your settings are kept, and connected apps resume on their own. If it is already running, opening it again reuses the running page. Keep its launch window open while you use it. The processes it started stop with it, whether you click **Quit** or close the window, and anything a crash left behind is stopped at the next start.

When a newer version is on PyPI, the Chat view shows a notice with a link to the release notes and the update command for the way this copy was installed. A copy unpacked from the source ZIP gets a link to download the new source from the release page instead. personagent asks pypi.org at most once a day, and the request carries only its version number. Set `UPDATE_CHECK_ENABLED=false` in `.env` to turn the check off.

If you prefer the command line, use `personagent start --terminal`, `personagent init --terminal`, `personagent up`, or the `chat`, `demo` (no key needed), `run` and `connect` commands. They keep your existing `.env`, edited persona and learned memories. The [full guide](guide.md) covers the other platforms.
