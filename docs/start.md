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

## Bring it to QQ

1. Click **Connect QQ**. The page explains that this delegates the official bot's group chats and DMs to your character.
2. The app downloads AstrBot and a separate Python 3.12 runtime as needed. Keep the page open.
3. Scan the displayed code with mobile QQ and confirm creation or binding. Credentials are saved and both services start automatically.
4. Find the bot in mobile QQ → Contacts → Bots. Chat privately or add it to a group you own.

This uses QQ Official Bot, so no NapCat or personal QQ bot account is required. QQ controls which groups you can add it to and which messages it can see; currently adding it to a group requires you to own the group. [AstrBot's official QQ guide](https://github.com/AstrBotDevs/AstrBot/wiki/en-platform-qqofficial-websockets) covers those account-side steps.

An expired code can be requested again. A failed download can be retried without repeating model setup. Only QQ Official Bot gets the platform-scoped permission; other adapters stay under their existing allowlists.

## Next time

Open personagent again. Your settings are kept, and a connected QQ bot's services resume automatically. Opening it a second time reuses the running page. **Quit** closes the app and stops only the processes it started. Keep its launch window open while using it.

Advanced users can use `personagent start --terminal`, `personagent init --terminal`, `personagent up`, or the existing `chat`, `run` and `connect` commands. Existing `.env`, edited persona files and learned memories are kept. Other platforms remain in the [full guide](guide.md).
