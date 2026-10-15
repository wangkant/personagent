# Start using personagent

[中文](start.zh-CN.md) · [Full guide](guide.md)

## Open it

Install personagent from PyPI and open it:

```sh
python -m pip install personagent
personagent
```

With [uv](https://docs.astral.sh/uv/), `uvx personagent` runs it without a separate install step.

With a source ZIP on Windows, double-click `start.bat`. It prepares its own Python environment and opens the same page. In a clone, `python quickstart.py` does the same.

## Add a key and chat

Choose a model service, paste its API key and click **Verify & start chatting**. DeepSeek and a warm listener character are selected initially. You can change the name, personality, model and API address under optional settings.

Once it is set up, **Character & settings** also has a **Persona** box with the text the character runs on. Rewrite who it is and how it talks, then click **Save persona**: it applies at once, and what the character has learned is kept.

Below it, **More features** turns on web search with a Tavily key, image understanding and speaking first. The Chat view keeps a short getting-started bar until an app is connected.

The key stays on your computer. Chat messages go to the model service you select; verification and chat may incur that service's usual charges. Click **Show** if you need to check the key. It is not included in status responses or stored in browser storage.

Your character replies in the page. Settings are saved, so the next launch goes straight to chat.

## Bring it to other apps

1. Click **Connect apps** and pick one. Once connected, your character replies to that app's group chats and DMs.
   - **Scan to connect**: QQ and personal WeChat. Click **Get a QR code** and confirm on your phone.
     - QQ: scan with mobile QQ. It creates a bot or uses one you already made, and personagent fetches its keys. For a bot made on [QQ's bot page](https://q.qq.com/qqbot/openclaw/login.html), **Paste values instead** takes its AppID and AppSecret.
     - WeChat: scan with WeChat. It chats one to one; WeChat does not hand group messages to these bots.
   - **Paste one or two values**: Telegram (a token from @BotFather), Discord (a bot token, with Message Content Intent on), KOOK, Feishu, DingTalk, Slack, WeCom AI bot, Mattermost and Misskey. The page says which values to copy from the app's console; everything else uses defaults.
   - **Advanced**: WeCom apps, WeChat Official Accounts and QQ webhooks need a public address that forwards to their callback port; OneBot v11 (NapCat) and Satori need other software running on this computer.
2. QQ, WeChat, Telegram and Discord are connected by personagent itself. The other apps go through AstrBot, a third-party bridge: the first such connection downloads it with a separate Python 3.12 runtime, so keep the page open. It runs in the background with no dashboard to sign in to.
3. personagent checks the credentials with the app before saving them. If the app refuses them, the page says so and nothing is saved.
4. Connected apps are listed at the top of the page, where you can set one up again or disconnect it.

For QQ, find the bot in mobile QQ → Contacts → Bots, then chat privately or add it to a group you own. This uses QQ Official Bot, so no personal QQ account or extra software is needed. QQ decides where the bot may go: until it is certified, it can join only groups its admin owns, with no sandbox to set up. It sees @-messages unless the group owner turns on receiving all messages on the bot's profile in that group. [QQ's bot guide](https://bot.q.qq.com/wiki/bot_new_product-intro/) covers certification and the rest of the account side.

An expired code can be requested again. A failed download can be retried without repeating model setup. Only the app you connect gets the platform-scoped permission; other adapters stay under their existing allowlists. LINE is not offered, because AstrBot only receives LINE callbacks through its dashboard, which personagent does not run.

## Next time

Open personagent again. Your settings are kept, and connected apps resume automatically. Opening it a second time reuses the running page. Keep its launch window open while using it. The processes it started stop with it, whether you click **Quit** or the window closes; anything left by a crash is stopped at the next start.

Advanced users can use `personagent start --terminal`, `personagent init --terminal`, `personagent up`, or the `chat`, `demo` (no key needed), `run` and `connect` commands. Existing `.env`, edited persona files and learned memories are kept. Other platforms remain in the [full guide](guide.md).
