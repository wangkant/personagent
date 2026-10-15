# Start using personagent

[中文](start.zh-CN.md) · [Full guide](guide.md)

## Open it

This branch is the 1.1 development preview. Install its current source:

```sh
python -m pip install https://github.com/wangkant/personagent/archive/refs/heads/main.zip
python -m persona_agent
```

With a source ZIP on Windows, double-click `start.bat`. It prepares its own Python environment and opens the same page. In a clone, `python quickstart.py` does the same.

## Add a key and chat

Choose a model service, paste its API key and click **Verify & start chatting**. DeepSeek and a warm listener character are selected initially. You can change the name, personality, model and API address under optional settings.

The key stays on your computer. Chat messages go to the model service you select; verification and chat may incur that service's usual charges. Click **Show** if you need to check the key. It is not included in status responses or stored in browser storage.

Your character replies in the page. Settings are saved, so the next launch goes straight to chat.

## Bring it to other apps

1. Click **Connect apps** and pick one. Once connected, your character replies to that app's group chats and DMs.
   - **Scan to connect**: personal WeChat. Click **Get a QR code** and confirm in WeChat. It chats one to one; WeChat does not hand group messages to these bots.
   - **Paste one or two values**: QQ, Telegram, Discord, KOOK, Feishu, DingTalk, Slack, WeCom AI bot, Mattermost and Misskey. The page says which values to copy from the app's console; everything else uses defaults. For QQ, scan on [QQ's bot page](https://q.qq.com/qqbot/openclaw/login.html) to create a bot, then copy its AppID and AppSecret.
   - **Advanced**: WeCom apps, WeChat Official Accounts and QQ webhooks need a public address that forwards to their callback port; OneBot v11 (NapCat) and Satori need other software running on this computer.
2. QQ, WeChat, Telegram and Discord are connected by personagent itself. For the other apps, the first connection downloads AstrBot and a separate Python 3.12 runtime; keep the page open. AstrBot runs in the background with no dashboard to sign in to.
3. The app saves the credentials, starts both services and waits a few seconds to confirm the app accepted the connection. If it refused, the page says so and nothing is saved.
4. Connected apps are listed at the top of the page, where you can set one up again or disconnect it.

For QQ, find the bot in mobile QQ → Contacts → Bots, then chat privately or add it to a group you own. This uses QQ Official Bot, so no NapCat or personal QQ bot account is required. QQ decides where the bot may go: an uncertified bot is for its admin, in groups the admin owns, with no sandbox to set up; it sees @-messages unless the group owner turns on receiving all messages on the bot's profile in that group. [QQ's bot guide](https://bot.q.qq.com/wiki/bot_new_product-intro/) covers certification and the rest of the account side.

An expired code can be requested again. A failed download can be retried without repeating model setup. Only the app you connect gets the platform-scoped permission; other adapters stay under their existing allowlists. LINE is not offered, because AstrBot only receives LINE callbacks through its dashboard.

## Next time

Open personagent again. Your settings are kept, and connected apps resume automatically. Opening it a second time reuses the running page. **Quit** closes the app and stops only the processes it started. Keep its launch window open while using it.

Advanced users can use `personagent start --terminal`, `personagent init --terminal`, `personagent up`, or the existing `chat`, `run` and `connect` commands. Existing `.env`, edited persona files and learned memories are kept. Other platforms remain in the [full guide](guide.md).
