# personagent user guide

English · [简体中文](guide.zh-CN.md) · [繁體中文](guide.zh-TW.md) · [日本語](guide.ja.md) · [한국어](guide.ko.md) · [Español](guide.es.md) · [Français](guide.fr.md) · [Deutsch](guide.de.md) · [Português (Brasil)](guide.pt-BR.md) · [Русский](guide.ru.md)

This guide covers setting personagent up, putting it in your chats, teaching it and looking after it. The [README](../README.md) is the short version, and [Getting started](start.md) walks through the local page screen by screen.

1. [Install and the home folder](#install-and-the-home-folder)
2. [The local page](#the-local-page): [Advanced settings](#advanced-settings) · [The App view](#the-app-view)
3. [See it first: the demo](#see-it-first-the-demo)
4. [Terminal commands](#terminal-commands): [setup](#set-up-in-the-terminal) · [connect a platform](#connect-a-platform-in-the-terminal) · [chat](#chat-in-the-terminal) · [run the service](#run-the-service)
5. [Make it your character](#make-it-your-character)
6. [Put it in a chat](#put-it-in-a-chat): [Platforms personagent connects itself](#platforms-personagent-connects-itself) · [Other platforms](#other-platforms-through-the-managed-astrbot) · [Bridges you run yourself](#bridges-you-run-yourself) · [Speaking first](#speaking-first)
7. [Coding agents](#coding-agents)
8. [Teach it](#teach-it)
9. [Memory](#memory)
10. [Activity](#activity)
11. [Measure it](#measure-it)
12. [How it works](#how-it-works)
13. [Privacy and consent](#privacy-and-consent)
14. [Troubleshooting](#troubleshooting)
15. [Upgrading from 0.x](#upgrading-from-0x)
16. [Status and other docs](#status-and-other-docs)

## Install and the home folder

```sh
python -m pip install personagent
personagent
```

`personagent` opens [the local page](#the-local-page). You can also install or run it these ways:

| Route | Command |
|---|---|
| Run without installing | `uvx personagent` (part of [uv](https://docs.astral.sh/uv/), which also fetches Python for you) |
| A permanent `personagent` command | `uv tool install personagent` or `pipx install personagent` |
| Windows, from the source ZIP | unpack it and double-click `start.bat` |
| From a clone | `git clone https://github.com/wangkant/personagent.git`, `cd personagent`, `python -m venv .venv`, then `.venv/bin/python -m pip install -e .` and `.venv/bin/python -m persona_agent` (on Windows, `.venv\Scripts\python.exe`) |

personagent runs on Python 3.10–3.14. `start.bat` creates `.venv`, installs the dependencies and opens the same page; the first time, it also puts a personagent icon on the desktop and in the Start menu. It installs them again whenever the dependency list in `pyproject.toml` changes.

The **home folder** holds the settings (`.env`), the character (`persona.txt`), what it learns (`runtime/`) and the chat platforms (`platforms/`). `platforms/` contains the managed AstrBot and `direct.json`, which stores the credentials of the platforms personagent connects itself. personagent uses the first of these folders:

1. the folder given with `--home DIR` or `AGENT_HOME`. `--home` can go before or after the command, as in `personagent chat --home D:\bot`.
2. the clone, when you run from one.
3. the current folder, if it holds both `.env` and `persona.txt`.
4. `~/personagent`, created on first setup.

To run several characters from one install, give each one its own home.

This guide writes commands as `personagent ...`. If you did not install it, put `uvx` in front. In a clone, `.venv/bin/python -m persona_agent ...` does the same (on Windows, `.venv\Scripts\python.exe -m persona_agent ...`).

## The local page

`personagent` (or `personagent start`) serves a page that only this computer can reach. On Windows it opens in a window of its own. On macOS and Linux it opens in the browser, or in a window too once `pip install "personagent[app]"` has added [pywebview](https://pywebview.flowrl.com/), with Qt on Linux. The page has six views, listed in the sidebar in this order:

- **Chat** is a one-to-one chat with the character on the page. The same agent that serves your chat platforms answers it. In this chat you are the admin. Stickers and pictures the character sends appear in the chat, and a picture that is no longer stored shows a short note in its place. Messages the character sends after its reply, such as the answer to a memory command sent while it was replying or a message it starts itself, appear within a few seconds while the Chat view is open. Both stay in the chat's history. When the model does not answer, the page says so in place of a reply and offers **Send again**. **Memory commands** below the message box lists the [memory commands](#memory-commands), and selecting one inserts it into the message box. **Forget this chat** forgets everything the character remembers from this chat and starts a new chat; what it remembers from other chats is kept, and the forget cannot be undone. It needs the data behind [Activity](#activity).
- **Activity** shows the chats the character is in, what it said lately, what it remembers and what it learned. See [Activity](#activity).
- **Connect apps** puts the character in QQ, WeChat, Telegram, Discord and other platforms. See [Put it in a chat](#put-it-in-a-chat). At the bottom, **Coding assistants** connects the character to the [coding agents](#coding-agents) on this computer.
- **Character & settings** is where you pick a model service (OpenRouter, DeepSeek, SiliconFlow, Alibaba Bailian, Zhipu GLM, Moonshot, Volcengine Ark, OpenAI, Google Gemini, Ollama, or any other OpenAI-compatible service), paste the API key, and choose a name and a ready personality. **Verify & start chatting** tests the key with one small request and saves it only if the request succeeds. After setup, the **Persona** box shows `persona.txt`. **Save persona** restarts the agent with the new text and keeps what it has learned. **More features** turns on web search through Tavily (DuckDuckGo is the free default), image understanding, and speaking first on the apps you choose. [Advanced settings](#advanced-settings) follows.
- **Practice** plays the scripted demo and runs a practice group chat. See [See it first: the demo](#see-it-first-the-demo).
- **App** checks the services the character relies on and holds the logs, running in the background, updates, and your data. See [The App view](#the-app-view).

**Practice** and **App** open before a model is set up. Until you connect an app, the Chat view shows a short **Getting started** bar.

Running `personagent` again brings back the page that is already open. `--browser` opens the page in the browser instead of a window, and `--no-browser` prints the link and opens nothing. On Windows, `personagent shortcut` puts an icon on the desktop and in the Start menu that opens the window with no terminal behind it, and `personagent shortcut --remove` takes it away. The App view does the same.

When a newer personagent is on PyPI, the Chat view shows a notice with the command that updates your installation, whether it came from pip, uvx, uv tool, pipx or a Git clone. For an unpacked source ZIP, the notice links to the release page instead. The terminal prints the same command. Closing the notice hides it for that version, and **N available** under the version number brings it back. `personagent up` and `personagent doctor` report a new version too. The page and `up` ask pypi.org at most once a day, in the background. `doctor` asks right away when the last answer is more than a day old. Set `UPDATE_CHECK_ENABLED=false` to turn the check off. The App view can also install the update itself; see [Version and updates](#version-and-updates).

The page starts the agent and the connected platforms in the background, so keep its window open while you use them. Everything it started stops with it, whether you click **Quit**, press Ctrl+C or close the window. While an app is connected, closing the window asks first. On Windows you can instead have closing the window leave personagent running; see [Run in the background](#run-in-the-background). If an earlier run crashed and left processes behind, the next start stops them first.

### Advanced settings

Once a model is set up, **Character & settings** ends with **Advanced settings**. It holds settings that were previously available only in `.env`, in six sections. Every one of them is optional and has a default, and an empty field uses the default.

| Section | Settings |
|---|---|
| **Admin and access** | What the character calls you and your relationship to it (`ADMIN_NAME`, `ADMIN_RELATIONSHIP`); **Your accounts** (`ADMIN_IDS`); **Reply only in these groups** (`ACCESS_GROUPS`); **Others allowed to send private messages** (`ACCESS_DM_USERS`). **Choose from recent chats** lists the people and groups from Activity, so that you can add their ids without typing them. |
| **Speaking and reply style** | **Time zone** (`PERSONA_TZ_OFFSET_HOURS`); **Messages before joining in** (`CHAT_TRIGGER_COUNT`); **How often it starts conversations**, which sets the seven `PROACTIVE_*` timings at once; **Reply style**: emoji, three sets of symbols and the maximum reply length, written to `persona.card.json`. |
| **Models** | A backup model with its own service address and key (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`), the model for quick decisions (`LLM_JUDGE_MODEL`) and the model for private chats (`LLM_DM_MODEL`). The backup model is tested before it is saved. |
| **Learning** | `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED`, `PROMOTE_MIN_SPEAKERS` (1 or 2), `PROMOTE_JUDGE_ENABLED` (the character decides what reactions cannot settle) and `PROMOTE_OBSERVE_MAX_DAYS` (days without a new reaction before an item under observation is set aside). **Restart learning** writes a new `PERSONA_VERSION`, so that what the character learned so far is no longer used. Nothing is deleted. |
| **Memory** | `MEMORY_CALLS_PER_DAY`, `MEMORY_TIDY_EVERY`, `CHAT_CONTEXT_MESSAGES`, `MEMORY_PROMPT_CHARS`, `MEMORY_EPISODES_MAX` and `MEMORY_KEEP_RECENT`. See [Memory](#memory). |
| **Other settings** | `AGENT_ENABLED`, `DASHBOARD_ENABLED`, `UPDATE_CHECK_ENABLED`, the seven `PROACTIVE_*` timings, `CHAT_FOLLOWUP_WINDOW_S`, the `REACT_*` and `PROMOTE_*` limits, `REACT_MODEL`, the model, interval and batch size of the character's own decisions (`PROMOTE_JUDGE_MODEL`, `PROMOTE_JUDGE_INTERVAL_S`, `PROMOTE_JUDGE_BATCH`) and `PERSONA_VERSION`. |

**Save** writes only the settings that changed and leaves the rest of `.env` as it was. It then restarts the character, except when `UPDATE_CHECK_ENABLED` is the only change. Turning off replies (`AGENT_ENABLED`) asks first. So does renaming the character under **Character name**, because a new name starts a new character.

### The App view

**App** has a red dot when something needs attention: a service failed to start, a setting has an old name or an error, a platform connection failed, or the last check failed.

**Health check.** **Run check** tests every service the character relies on: the chat model for group and private replies, the web search decision, the reaction judge, learning decisions, the review of its own replies, image understanding, the self-review model, memory lookup, web search, the QQ bridge (NapCat) and the learning records. Each model row tests the model that does that work. **Web search decision** tests the judge model (`LLM_JUDGE_MODEL`, else the backup model, else the main model) and fails when that model does not call the search tool, because web search would then never run. **Reaction judge** tests `REACT_MODEL`, else the judge model, and is skipped while `REACT_LEARN_ENABLED` is off. **Learning decisions** tests the model with which the character decides what reactions cannot settle (`PROMOTE_JUDGE_MODEL`, else the reaction judge's model) and is skipped while `PROMOTE_JUDGE_ENABLED` or `PROMOTE_AUTO_ENABLED` is off. **Review of its own replies** tests `EVOLVE_MODEL` (else `EVAL_MODEL`, else the backup model, else the main model) and is skipped while `EVOLVE_AUTO_ENABLED` is off. When either row would test a model that an earlier row already tests, the model is not asked again and the row shows that row's result. **Self-review model** is skipped while `EVAL_ENABLED` is off. Each service gets one row, marked **Working**, **Not working** or **Not set up**, and a verdict above the rows names what to fix. When the character is running, the check goes through it. Otherwise a separate test run performs the same checks as `personagent doctor`. A check sends a few short requests and uses a small amount of your model service's quota. A result less than one minute old is reused while the settings have not changed. The same part of the view also shows:

- why the character, AstrBot or the platform connection failed to start, with the relevant log line, **Show log** and **Restart**;
- **Settings with old names**: settings renamed in 1.0. **Rename settings** does what `personagent doctor --fix` does. It asks first, keeps the previous file as `.env.bak`, and starts the character again if it had refused to start;
- **Platform connections**: the state of each platform personagent connects itself, and the reason when one failed;
- **Settings to review**: problems found in `.env`, such as a missing model key, a setting personagent does not read, an empty value or a byte order mark;
- **Logs**: the last lines of each log in `runtime/desktop/` (the character, AstrBot, platform connections, downloads and installation, the app, Practice and the last update). Recognizable keys and tokens are hidden, but chat content can appear. **Show more lines** shows up to 200 lines, and **Open the logs folder** opens the folder.

**Model use.** personagent counts every model request it makes, per model and per day, from the usage the model service reports: requests, tokens, and the cost where the service reports it, as OpenRouter does. The App view shows today and the last 7 days. `personagent doctor` prints the same figures, and `doctor --json` adds them as `model_use`. The counts are kept for 8 days in `runtime/model_usage.json`. personagent writes that file in the background, at most once a minute and once more when it stops, so that counting never delays a reply.

#### Run in the background

This part is available in the app window on Windows. With **Keep running after the window is closed** ticked, closing the window moves personagent to an icon in the notification area at the bottom right of the screen, and the character keeps answering. The icon's menu opens personagent again or quits it, and double-clicking the icon opens it. **Move to the background now** hides the window at once. `personagent start --background` starts personagent behind the icon without showing the window, provided that this option is ticked.

#### Version and updates

This part shows the version that is running and when the last check took place. **Check for updates** asks pypi.org at once, even when the daily check is turned off. When a newer version exists, **Update and reopen** asks first, closes personagent, runs the update command for this installation and opens personagent again. This takes about a minute, and the character does not answer in the meantime. A clone is updated with `git pull --ff-only` followed by `pip install -e`. If the update fails, the previous version opens again, and **Show log** shows what happened. The app cannot update itself in four cases, and shows the command or the release page instead:

- a copy unpacked from the source ZIP, which you replace with the new source by hand;
- a copy that runs through uvx, which fetches the new version the next time it starts with `uvx personagent@latest`;
- an installation whose tool (`git`, `uv` or `pipx`) cannot be found;
- a clone with local changes.

#### This computer and your data

- **Desktop and Start menu icon** (Windows): **Add icon** and **Remove icon** do what `personagent shortcut` does. A copy that runs through uvx cannot have an icon, because it runs from a temporary folder.
- **Start personagent after signing in to Windows** adds a shortcut to the Startup folder. When personagent is set to run in the background, it then starts behind its icon without opening the window.
- **Your data** opens the personagent folder, the persona file, the logs, the memory and learned content, the stickers folder, and the `data/` folder for your own lorebook, examples and output filters.
- **Back up now** saves one zip file to the Desktop, to Documents or to the `backups` folder in the home folder. It contains the settings with your API keys, the persona, memory and learned content, the lorebook files, stickers and the platform logins. Logs and downloaded components are not included. Keep the file private.
- **Restore from a backup** lists the backups in those three places. **Restore** asks first, pauses the character, saves the current data as a backup, replaces it with the backup's data and clears this page's chat.
- **Clear and reset** saves a backup to the `backups` folder first and pauses the character. **Clear memory** deletes the character's notes about people, the replies it has learned and their history, the Practice data and this page's chat; the settings, persona, connected platforms and stickers are kept. **Reset all** returns personagent to its first-run state: it deletes the settings and API keys, the persona, memory and learned content, and disconnects every platform. Stickers, the `data/` folder and the downloaded AstrBot are kept.

## See it first: the demo

`personagent demo` plays three scenes on a scripted model, so it needs no key. The scenes show which group messages it skips and why, how it learns from a correction, and how a stranger fails to plant an instruction. To play only one scene, name it (`quiet`, `teach` or `troll`). Add `--lang` and a language code for another language, such as `--lang ja`.

Below is a trimmed run of `personagent demo teach`. The model's lines are scripted, but the ledger and the promotion rule are the real code:

```text
  Alex: Nova, the deploy failed again
  Nova: did you check the logs? roll back first, then diff the configs
  Alex: Nova, I was just venting
      judged: rejection, accepted: "Alex was venting, not asking for a fix"
      ledger: negative only (it says the reply was wrong, not what to say instead)
      Nova's next reply to Alex counts as its second try
  Nova: fair. that's a rough end to the day
  Alex: haha yeah it is, thanks Nova
      judged: positive, accepted: "Alex agreed with the second try and thanked Nova"
      ledger: weak (a laugh or a thanks never changes anything alone)
      ledger: Alex accepted the second try: strong (Alex is who the reply was for)

  fix: "did you check the logs? roll back first, ..." -> "fair. that's a rough end to the day"
    [x] 2 of 2 agreeing reactions
    [x] 1 of 1 strong
    [x] same chat
    [x] 1 of 1 person (PROMOTE_MIN_SPEAKERS)
    [x] nothing disagrees, no rival fix
    now in use: 2 agreeing reactions, 1 strong, same chat
```

The scene also sends the same message before and after the lesson: someone's laptop died mid-demo. Before the correction, Nova offers a fix. After it, Nova offers sympathy. The demo stays scripted even when a key is set, so every run is identical and costs nothing. `personagent demo --online` plays it on your own model instead, which costs tokens and varies from run to run.

The **Practice** view of the local page plays the same three scenes. Under **Demo**, choose a scene and select **Play**. Each step shows what people said, what the character said, why it stayed silent or joined in, how reactions were judged and the learning checklist.

**Practice group**, in the same view, is the page's version of [`personagent chat`](#chat-in-the-terminal) and needs a model. **Write as** chooses who sends the next message: you as the admin, or one of three made-up members. **Show reason** on a line shows why the character replied or stayed silent, what it learned and which earlier learning it used. **Reply** quotes one of the character's lines, so that the next message counts as a reaction to it. **Show what was learned** lists what it learned in this group. The practice group keeps its state in `runtime/trial/`, the same folder as `personagent chat`, and does not affect your real chats. **Reset practice group** deletes that state.

## Terminal commands

Everything the page does is also available from a terminal, which suits servers and scripts.

| Command | Does |
|---|---|
| `personagent start` | open the local page (`--terminal` for a menu in the terminal instead) |
| `personagent init` | set up a home; `--terminal` asks the questions in the terminal, `--no-input` takes flags |
| `personagent chat` | a simulated group chat in the terminal |
| `personagent demo` | the scripted demo above |
| `personagent run` | the service alone, for connectors you run yourself |
| `personagent up` | the service, the platforms personagent connects itself and the managed AstrBot, together |
| `personagent connect <platform>` | connect one of the [platforms personagent connects itself](#connect-a-platform-in-the-terminal) (`--remove` to disconnect it); without a platform, list them |
| `personagent connect astrbot` | connect an AstrBot (`--install` to download a managed one, `--start` to start it) |
| `personagent connect claude-code`, `personagent connect codex`, `personagent connect dsh` | put the character into a [coding agent](#coding-agents) (`--react` for remarks when a turn ends on the first two, `--remove` to undo) |
| `personagent mcp` | the MCP server a coding agent starts; you do not run it yourself |
| `personagent doctor` | check the setup and every service it depends on |
| `personagent learned` | show what it learned and what it is still observing, and step in if you choose |
| `personagent memory` | list what it remembers, forget an item or bring one back |
| `personagent eval` | measure speaking, persona, learning and memory |

Every command takes `--help`.

### Set up in the terminal

`personagent init --terminal` asks the same questions as the page, in the language you pick first, and explains each term in one line:

- **The AI service.** The presets match the page. The default is OpenRouter's `openrouter/free`, which hands each request to one of its free models. The key costs nothing. The limit is 20 requests a minute and 50 a day, or 1000 a day once you have bought at least 10 credits. Every model call counts, not only replies, and the day resets at midnight UTC. Once it runs out the character says it cannot answer right now, and `runtime/desktop/agent.log` has OpenRouter's reason. The model changes between requests, so the character's voice varies more than on one chosen model, and some free providers keep what they receive. For a steadier character, use a paid model with the same key. If OpenRouter is hard to reach where you are, Zhipu's `glm-4.7-flash` is free too. For Ollama, name a model you have already pulled. Ollama needs no key.
- **The key.** Input is hidden by default. You can choose to show it, which also reveals the saved key when you reconfigure. The wizard tests the key with one small request. If the request fails, it shows the address it called, the HTTP status and a likely fix.
- **The character.** A name, and one of seven ready characters (dry-witted friend, warm listener, gamer, bookworm, and three the community already draws: the DeepSeek whale girl, the GPT dragon girl and the Claude lady) or a plain one to write yourself. Pick one of the last three without choosing a name and the character is named after it. The local page shows its animated portrait.
- **Chat platforms.** Optional, and you can skip this step the first time. The setup names the ten platforms personagent connects itself, which you connect afterwards with [`personagent connect <platform>`](#connect-a-platform-in-the-terminal). For the other platforms it can connect AstrBot, and download and install it first. See [Bridges you run yourself](#bridges-you-run-yourself).

To set up without questions, for example in a script, run `personagent init --no-input` with `--provider`, `--model`, `--key-env VAR`, `--name`, `--lang` and `--persona`. On a new home, a key from `--key-env` or the shell's `LLM_API_KEY` needs `--provider` or `--base-url` to say whose it is. `--provider other` also needs `--base-url`. `personagent init --help` lists every flag. If `personagent init` runs without a terminal and without any of these flags, it skips the questions, says so, and exits with code 2.

### Connect a platform in the terminal

`personagent connect <platform>` connects one of the [platforms personagent connects itself](#platforms-personagent-connects-itself) without the page. The platform is `qq`, `wechat`, `telegram`, `discord`, `matrix`, `twitch`, `irc`, `zulip`, `vk` or `stoat`. The command shows the same steps as **Connect apps**, asks for each value, checks the values with the platform and saves them in the same form as the page, which then shows the platform as connected. If the platform refuses the values, the command says why and saves nothing. `personagent connect` without a platform lists the ten platforms and whether each one is connected.

- QQ and WeChat print a QR code in the terminal, which you scan with your phone. For QQ you can instead enter the AppID and AppSecret of a bot you created. If the code cannot be scanned in your terminal, connect the platform in the personagent window; the command prints how to open it.
- Twitch prints a link and a code. Open the link in a browser that is signed in to the character's Twitch account, check that the page shows the same code, and approve the sign-in. The command waits until then.
- Each value is also an option, such as `--telegram-token` or `--irc-server`, and `personagent connect --help` lists them all. A value given as an option can remain in the shell's history. With `--no-input` the command asks nothing; when a required value is missing, it names the option and exits with code 2.
- `--remove` disconnects the platform and deletes its saved values.

The connection is active while personagent runs. `personagent up` starts personagent with its connected platforms; if personagent is already running, restart it. In the menu of `personagent start --terminal`, option 3 connects these platforms and option 5 starts personagent with them.

### Chat in the terminal

`personagent chat` puts you in a simulated group chat with the character. A plain line is ordinary group chat, and the trial tells you whether the character would join in and why. A line that contains its name calls it:

```text
Alex> anyone around tonight?
  (Nova stays quiet: not addressed, 1 of 4 messages)

Alex> Nova, the deploy failed again
  Nova > did you check the logs? roll back first, then diff the configs
```

| Type | To |
|---|---|
| `/reply <text>` | quote its last reply, which counts as a reaction it can learn from |
| `/as Sam <text>` | speak as someone else: `/as Sam Nova, you free tonight?` |
| `/admin <text>` | speak once as the admin: `/admin Nova, how was your day?` |
| `/why` | see why it said its last reply, and what the ledger holds about it |
| `/learned` | see what it has learned in this chat |
| `/reset` | clear the chat and what the trial learned |
| `/quit` | leave |

`/as` and `/admin` lines follow the group rules too, so include the name to get a reply. A line shorter than four characters that does not name the character does not count toward joining in. The [memory commands](#memory-commands) work here as well.

| Flag | Does |
|---|---|
| `--name Alex` | sets your name |
| `--admin` | makes every line the admin's |
| `--dm` | makes it a one-to-one chat |
| `--lang <code>` | overrides `AGENT_LANG`, such as `--lang ja` |
| `--trigger N` | messages before it considers joining in (default 4) |

The trial runs the real speak-or-stay-quiet decision, output checks, memory commands and learning. It considers joining in after 4 messages, where the live bot waits for 30. What it learns stays in `runtime/trial/` in the home folder, separate from the live bot. `personagent learned` does not show it, and `/reset` clears it. The trial skips the allowlists and real delivery. It also turns off self-evaluation, vision, the follow-up question and messages the character would start on its own. When a model call fails, it prints one line that says what to check:

```text
Alex> Nova, you there?
  [error: the model provider refused the key or the account (HTTP 401); check LLM_API_KEY, then run `personagent doctor`]
```

### Run the service

`personagent run` starts only the service the connectors talk to, at `http://127.0.0.1:8080`. On startup it prints the version, the address, the home folder and whether the agent is on. `--host` and `--port` override `SERVER_HOST` and `SERVER_PORT`. Use this command when you run the connector yourself.

`personagent up` starts the service together with every platform you connected from the page, with `personagent connect <platform>` or with `connect astrbot --install`. It opens no browser. Ctrl+C stops everything, and each process writes its log to `runtime/desktop/` in the home folder.

## Make it your character

`persona.txt` in the home folder defines the character. Edit it in the page's **Persona** box, or in any editor and then restart. Describe who the character is, how they usually talk, and what they do in the situations you care about. Concrete habits work better than asking the model to "sound natural":

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

`AGENT_LANG` is one of `en`, `zh`, `zh-TW`, `ja`, `ko`, `es`, `fr`, `de`, `pt-BR` and `ru`. It sets the starter persona, the terminal setup, trial and demo, `--help` and `doctor`, the memory commands and the fixed replies. The bundled examples, filters and checks are Chinese for `zh` and `zh-TW` and English for the others. It does not translate your persona. [.env.example](../.env.example) describes every setting.

The language menu at the top right of the local page offers English, 简体中文, 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) and Русский. It changes only how the page reads, and the browser remembers it. The character's own language is chosen in **Language the character speaks** on **Character & settings**, under **Choose a name, personality or language**, and is saved as `AGENT_LANG`. The character answers in the language the chat uses. Its prompts are English and Chinese. The [memory commands](#memory-commands) and the few fixed replies, which don't go through the model, work in all ten languages.

To override a shipped file, put a file with the same name in the home folder's `data/`. Files you do not override come from the copy shipped with personagent.

| File | Holds |
|---|---|
| `data/examples.<lang>.jsonl` | Example exchanges the model can imitate |
| `data/feedback.<lang>.jsonl` | Replies paired with better versions |
| `data/lorebook.<lang>.json` | Background notes added when a keyword comes up |
| `data/output_filter.<lang>.json` | Replacement and rejection rules for live replies |
| `persona.card.json` | Optional nicknames and emoji, character-set and length settings, such as `{ "aliases": ["Lu"], "reply_style": { "emoji": true, "max_chars": 320 } }`. A nickname in `aliases` calls the character as its name does. Names are matched ignoring case, full-width letters and accents, so `sofia` calls Sofía. In a message, ñ, ã, õ and й count as letters of their own, so `niña` does not call a character named Nina; in the character's own name such a mark may be left out, so `nina` calls Niña. A name does not call the character from inside a longer word: a katakana name inside a longer katakana word does not call it, and neither does a Korean name in the middle of a word. With `"emoji": true` the character may use emoji as it usually does, and a `max_chars` below 800 is given to the model as a length limit |

To let it see images, set `VISION_MODEL`, `VISION_API_KEY` and `VISION_BASE_URL`, or turn on image understanding under **More features**. When the chosen model cannot read images, the page says so when you save. A picture the character cannot see, because image understanding is off or failed, reaches it as a picture it cannot see, in groups and in private chats alike, so it asks about the picture instead of describing it. Voice messages, videos, files and forwarded messages reach it as what they are, with a voice message's transcript when the platform provides one. The words of a forwarded message are read as the forwarded person's words: they call no one by name and run no memory command. A mention of another person reaches the character with the name that person chose, which never counts as the sender's words, so it neither calls the character nor gives a command.

## Put it in a chat

Open **Connect apps** on the local page and pick a platform. The page asks only for the values you copy from the platform's own console. It checks them against the platform, starts the connection and waits a few seconds to confirm the platform accepted it. If the platform refuses, the page says so and saves nothing. Connected platforms are listed at the top, where you can set one up again or disconnect it. They start again whenever the page or `personagent up` starts. On a computer without a display, `personagent connect <platform>` connects the platforms personagent connects itself from the terminal; see [Connect a platform in the terminal](#connect-a-platform-in-the-terminal).

```text
Chat platform  ⇄  connector  ⇄  personagent  ⇄  Model API
```

A connector logs in to the platform, passes each message to personagent and carries the reply back. There are three kinds.

### Platforms personagent connects itself

personagent connects these ten itself, in one background process. They need neither AstrBot nor NapCat. If one of them cannot be loaded, the others still start. Replies on these platforms go out one message at a time, each after about the time it takes to type; Telegram, Discord and Matrix show the typing sign meanwhile.

| Platform | What you do |
|---|---|
| QQ | Scan the code with mobile QQ and confirm. This creates an official QQ bot, or uses one you already have, and personagent fetches its keys. **Paste values instead** takes the AppID and AppSecret of a bot created on [QQ's bot page](https://q.qq.com/qqbot/openclaw/login.html). |
| WeChat (personal) | Scan the code with WeChat and confirm the login. The connection uses Tencent's iLink bot API and handles one-to-one chats only, because WeChat does not deliver group messages to these bots. |
| Telegram | Create a bot with [@BotFather](https://t.me/BotFather) and paste its token. |
| Discord | In the [Developer Portal](https://discord.com/developers/applications), copy the bot token and turn on Message Content Intent. |
| Matrix | Create a separate Matrix account for the bot. In Element, signed in as the bot, copy its access token under **All settings > Help & About > Advanced**, then close that window without signing out. Paste the token with the homeserver address and your own Matrix ID. Then, from your own account, invite the bot to a room with end-to-end encryption turned off. The bot accepts invitations only from your Matrix ID and cannot read encrypted rooms. |
| Twitch | Register a free application with Client Type **Public** in the [Twitch developer console](https://dev.twitch.tv/console). Paste its Client ID and the channels the character should chat in, select **Connect**, and approve the sign-in through the link the page shows, in a browser signed in to the character's Twitch account. The character chats in text only, and only in the listed channels. Twitch whispers (direct messages) are not supported, so the tile on **Connect apps** says **Channels only**. |
| IRC | Enter the server (Libera.Chat by default, or `irc.oftc.net` for OFTC), the TLS port, the bot's nickname, the channels, and the NickServ password if the nickname is registered. The bot connects over TLS, joins only the listed channels and answers direct messages to its nickname. Text only. Libera.Chat requires the permission of each channel's operators before an AI bot joins. |
| Zulip | Add a **Generic bot** under **Personal settings > Bots**, then paste the organization address, the bot's email and its API key. The bot reads only the channels it is subscribed to and the direct messages sent to it. In a channel it answers when it is mentioned or quoted. Every member of the organization can send it direct messages. |
| VK | In the community's settings, turn on messages and bot abilities, create an access key with the rights for community management, messages and photos, and turn on the Long Poll API with the `message_new` event. Paste the key. Any VK user can write to the community. In a group chat the bot receives only messages that mention it or reply to it, unless the chat gives it access to all messages. |
| Stoat (formerly Revolt) | Create a bot under **Settings > My Bots** and paste its token. Change the API address only for a self-hosted server. The bot answers every direct message. In servers and groups it answers only where you are a member yourself, and only when someone mentions it, replies to it or begins a message with its name. |

For the last six, the page shows numbered steps above the fields. The project has not yet tested Matrix, Twitch, IRC, Zulip, VK or Stoat against the live services; they follow each platform's documentation.

For QQ, find the bot in mobile QQ under Contacts → Bots, then chat with it privately or add it to a group. Until the bot is certified, QQ lets it join only groups you own. You choose which group messages it receives in QQ, on the bot's profile in that group. [QQ's bot guide](https://bot.q.qq.com/wiki/bot_new_product-intro/) covers certification.

The credentials are stored in `platforms/direct.json` in the home folder.

### Other platforms, through the managed AstrBot

The first time you connect any other platform, personagent downloads [AstrBot](https://docs.astrbot.app) and a dedicated Python 3.12 runtime into `platforms/` in the home folder. Keep the page open while it downloads. AstrBot then runs in the background with no dashboard and no second login. It needs no global `uv` and leaves personagent's own Python alone. Connecting a platform from the page lets that platform's groups and DMs reach the character. The allowlists of other platforms stay as they were.

| Group | Platforms | You give |
|---|---|---|
| Paste one or two values | KOOK, Feishu / Lark, DingTalk, Slack, WeCom AI bot, Mattermost, Misskey | a token, an app id and secret, or a server address and token. Feishu uses long connection and DingTalk uses Stream mode, so neither needs a public address. For Slack, the link on the page creates the app with Socket Mode, scopes and events already set. Add an app-level token with `connections:write`, install the app and paste both tokens. Create the WeCom AI bot with long connection. |
| Advanced | WeCom app, WeChat Official Account, QQ (webhook) | a public address that forwards to the callback port shown |
| Advanced | OneBot v11 (NapCat), Satori | other software running on this computer: NapCat pointed at `ws://127.0.0.1:<port>/ws`, or a Satori server |

LINE is not offered, because AstrBot receives LINE callbacks only through its dashboard.

From a terminal, `personagent connect astrbot --install` downloads the same managed AstrBot and connects it. Add `--platform telegram --token <bot token>` to switch on a platform at the same time. No groups or DMs are allowed until you configure them. If the download fails, run the same command again. Existing configuration is kept. `personagent connect astrbot --start` starts the managed AstrBot, and `personagent up` starts it with everything else.

### Bridges you run yourself

The projects below are third-party software that personagent works with. You do not need any of them for the [platforms personagent connects itself](#platforms-personagent-connects-itself).

| Bridge | Reaches |
|---|---|
| An [AstrBot](https://docs.astrbot.app) you already run | its platforms |
| [NapCat](https://github.com/NapNeko/NapCatQQ) (OneBot v11), through AstrBot | QQ with a personal QQ account |
| [Koishi](https://koishi.chat) or another Satori server, through the [Satori connector](../integrations/satori/README.md) | whatever that server is logged in to |
| [Matrix](../integrations/matrix/README.md), through mautrix bridges | Matrix rooms, and WhatsApp, Signal, Messenger, Instagram and Google Messages |

Anything else can connect through the [connector protocol](connectors.md), which takes one signed HTTP request per message. Several connectors can serve one personagent at once. The [deployment guide](deploy.md) covers running it in production.

**An AstrBot you already run.** AstrBot hands messages to personagent through a small plugin, [astrbot_plugin_personagent](../integrations/astrbot/astrbot_plugin_personagent/README.md). The plugin ships inside personagent, and the managed AstrBot gets it automatically. `personagent connect astrbot` finds your AstrBot, or takes its folder as an argument. It installs the plugin, writes one shared `CONNECTOR_TOKEN` to both sides and asks which groups to allow. Send `/sid` in a group to see its id. On the local page, **Use an existing AstrBot**, under **Coding assistants** at the bottom of **Connect apps**, does the same: it finds the AstrBot folder, installs or updates the plugin, and saves the group and DM ids under **Who it replies to**. For an AstrBot in Docker or on another computer, it takes the HTTPS address described below. **Disconnect** deletes the plugin and its settings again.

For an AstrBot on another machine:

1. Download `astrbot_plugin_personagent.zip` from the [latest release](https://github.com/wangkant/personagent/releases/latest).
2. Upload it under **Install from File** on AstrBot's plugin page.
3. Set the plugin's `connector_token` to the `CONNECTOR_TOKEN` in personagent's `.env`.
4. Set its `personagent_url` to an HTTPS address for personagent. See **AstrBot in Docker, or on another host** below.
5. Run `personagent run`, then restart AstrBot or reload its plugins.

After you upgrade personagent, run `connect astrbot` again or upload the new zip. AstrBot 4.29 and later replace the installed copy. On older versions, uninstall the old copy first and leave **Also delete plugin configuration file** unticked to keep its settings.

The plugin forwards a group only when the group is in its `groups` list, and DMs only from users in `dm_users`. You can change both in AstrBot's WebUI. Restart personagent after editing `.env`, and restart AstrBot after changing a platform or the plugin.

When you give AstrBot's folder, `connect astrbot` asks nothing, and you can switch on a platform from its token:

```bash
personagent connect astrbot <AstrBot data dir> --platform telegram --token <bot token>
```

`--platform` accepts `telegram`, `discord`, `slack`, `kook`, `lark` and `qq_official`. Slack also takes `--app-token`, and Lark and QQ take `--app-id` and `--app-secret`. On an adapter that is already set up in AstrBot, the command changes only the credentials and keeps everything else, such as a proxy or base URL. `personagent connect --help` lists the remaining options.

**QQ through NapCat.** This route uses a personal QQ account instead of an official bot. NapCat logs in with the account and connects to AstrBot's `aiocqhttp` (OneBot v11) adapter, with its reverse WebSocket at `ws://127.0.0.1:6199/ws`. Choosing QQ in `personagent connect astrbot`, or passing `--qq` with a folder, removes `aiocqhttp` from the plugin's `excluded_platforms` and sets `CONNECTOR_QQ_PLATFORMS=aiocqhttp`. QQ chats then keep the same identities and memory. NapCat's HTTP server (`QQ_ONEBOT_URL`) is optional. With it and `QQ_BOT_ID` set, personagent catches up on mentions it missed while offline. The [Chinese step-by-step guide](deploy.zh-CN.md#第三方路线astrbot--napcat) has a short section on this route. Third-party QQ clients put the account at risk, so read the [disclaimer](DISCLAIMER.md) first.

The direct OneBot route (`/v1/onebot`) is deprecated and kept through 1.x. It sends replies through `QQ_ONEBOT_URL`, so set that if you still use the route. `personagent doctor` warns when the route looks configured without it. Never run it alongside AstrBot forwarding, or every message arrives twice.

**AstrBot in Docker, or on another host.** The plugin posts only to the same host (or a container sharing its network), or to an HTTPS address with `connector_token` set. It refuses plain `http://` anywhere else, such as `http://host.docker.internal:8080`, logs `refusing unsafe personagent_url`, and lets AstrBot's own model answer instead. There are two fixes:

- Give the AstrBot container host networking: `network_mode: host` in its compose file, or `docker run --network host`. On Docker Desktop 4.34 or later, also turn on "Enable host networking".
- Give personagent an HTTPS address and set it as the plugin's `personagent_url`. `connect astrbot --url https://...` writes it for you.

A NapCat container in the same compose file needs host networking too.

personagent listens on `127.0.0.1:8080`, and a blank `SERVER_HOST` means the same. Listening on a network address (`--host 0.0.0.0` or `SERVER_HOST`) requires `CONNECTOR_TOKEN`. Set the token before you add a proxy or tunnel, even on a single machine, because a tunnel can make outside requests look local. [Exposing the endpoints](deploy.md#exposing-the-endpoints) covers the rest.

### Speaking first

Some messages are not replies to anyone. These are openers (`PROACTIVE_ENABLED`, off by default), the follow-up question after a rejection, and the excuse sent when the model fails in a group. In a DM, the excuse goes back in the response to the waiting message instead. personagent queues these messages in an outbox, and the connectors pull and send them on platforms that let a bot speak first. The local page pulls them for its own Chat view in the same way. WeChat official accounts and WeCom smart bots do not. QQ rate-limits an official bot's unprompted messages, and users can switch them off. `PROACTIVE_PLATFORMS=qq_official` limits openers to the official QQ bot, and `qq` limits them to QQ through NapCat. On the page, **Sometimes speak first** under **More features** writes both settings. See the [deployment guide](deploy.md#more-than-one-platform).

## Coding agents

Codex, Claude Code and DeepSeek Harness (`dsh`) reach the character over MCP. With a model key saved, run one or more:

```bash
personagent connect claude-code
personagent connect codex
personagent connect dsh
```

The first calls `claude mcp add` at user scope. The second writes to `config.toml` in Codex's folder (`CODEX_HOME` or `~/.codex`). The third adds an entry to `cordis.patch.yml` in every profile under `DSH_HOME` or `~/.dsh`. Each way of running DeepSeek Harness, such as the desktop app or `dsh web`, gets its profile the first time it starts, so start it once before you connect, and restart it afterwards. All three name this installation and this home, so run the command again after you move either, with `--react` if you used it: a run without it takes the hook out. Start a new session, then ask the coding agent to say something to your character.

**From the local page.** **Coding assistants**, at the bottom of **Connect apps**, finds Claude Code, Codex and DeepSeek Harness on this computer and shows whether each one is connected. **Connect** (or **Repair** and **Update** for an existing setup) and **Remove** do what the commands above and `--remove` do, and ask first. A reconnection keeps the remark setting as it was. On Claude Code and Codex, **Make a remark when a turn ends** turns the `--react` hook on or off, and **Minimum interval between remarks** sets `CODING_REACT_COOLDOWN_S` to 10 minutes, 30 minutes, 1 hour or 2 hours. **Check again** reads the state again, for example after you install one of them.

It gets two tools:

| Tool | Does | Costs |
|---|---|---|
| `talk` | one message in the same one-to-one chat as the local page, with the same memory. What is said through `talk` appears in the page's Chat, marked **via a coding assistant**: within a few seconds while the Chat view is open, and otherwise the next time the page opens. Memory commands such as `Nova, what do you remember?` work here too. | one reply from your model service, except memory commands |
| `character` | reads the name and `persona.txt` | nothing |

Claude Code and Codex ask before the first `talk`, and you can allow it from then on in that prompt. `dsh headless` does not ask. A run with nobody there to answer needs the permission up front: `claude -p` takes `--allowedTools mcp__personagent__talk`, and `codex exec` needs this in `config.toml`:

```toml
[mcp_servers.personagent.tools.talk]
approval_mode = "approve"
```

**What answers.** An open page answers first, then a service `personagent up` is running. With neither, the MCP server starts the page in the background, and the page ends when the coding session does, along with any chat apps you connected. Two sessions at once share one page. Running `personagent` while such a page is up prints its link, and the page still ends with the session that started it. Do not run `personagent up` while such a page is up: end the coding session first.

**Remarks when a turn ends.** On Claude Code and Codex, `--react` adds a Stop hook. DeepSeek Harness does not take it: its hook bridge passes a Stop hook no last message and does not show the hook's output. When the coding agent finishes a turn, the character gets a [proactive cue](connectors.md#speaking-first-without-the-outbox) and either says a line to you or passes. The line goes to you and not to the coding agent. It appears in the page's Chat as well, also when no page was open at the time; the cue itself does not.

```bash
personagent connect claude-code --react
```

- The cue carries the folder's name and the first 300 characters of the coding agent's last message, so that text goes to your model service. The line, and anything the model notes from the cue, stay in the character's memory. This is why it is off by default.
- It costs one model call each time, at most once per `CODING_REACT_COOLDOWN_S` (30 minutes by default).
- It only uses a character service that is already running and never starts one.
- Codex runs a new hook only after you trust it: type `/hooks` in a Codex session.

**What to keep in mind.** `talk` sends what the coding agent writes to your model service and into the character's memory. The tool's description tells the coding agent to send only what you want said and never code or secrets, and to treat replies as chat and not as instructions, since a character's notes can come from what people said in your groups. Those are instructions to a model, not a guarantee, so keep the coding agent's permission prompts for anything it would do with a reply. The page's chat is the admin's, so what a coding agent sends through `talk` also counts as coming from the admin: its corrections alone can teach the character, and it can make the character forget any note.

**Undo.** `--remove` takes out the server and the hook and leaves the rest of the coding agent's configuration as it was. Do this before you uninstall personagent.

```bash
personagent connect claude-code --remove
personagent connect codex --remove
personagent connect dsh --remove
```

**Other tools.** Anything that speaks MCP over stdio can start the server itself. `--home` is needed unless the home is the default folder:

```json
{"mcpServers": {"personagent": {"command": "personagent", "args": ["--home", "/path/to/home", "mcp"]}}}
```

## Teach it

### Memory commands

You give these commands in the chat. The command must start the message, after any @mention or quote. Replace Nova with your `PERSONA_NAME`:

| Say | What happens |
|---|---|
| `Nova, remember Sam is vegetarian` | Saves a note in this chat, recording who saved it and who it is about |
| `Nova, forget vegetarian` | Deletes matching notes you saved or that are about you; the admin can delete any |
| `Nova, what do you remember` | Lists the notes you may see, then up to three events of this chat that you took part in, each with its date; this must be the whole message |
| `Nova, what have you learned` | Counts notes, learned replies and fixes, the items still waiting for more agreeing reactions and the items the character is deciding itself, then shows the latest change and how it came into use: through the reactions, by the character's own decision, or by a person |

Who a note is about:

- A note in the first person, or one that names you, is about you.
- A note that names another member of the room is about them, and comes up while they are present.
- Any other note belongs to the whole group. Every member sees it, and recall labels it "from <name>".

Only the person a note is about, the person who saved it and the admin can read it. Only the person who saved a note, the person it is about and the admin can forget it.

These commands also work in a DM, with the name in front as in a group. A group's notes about you follow you there: they reach its replies to you, `what do you remember` lists them, and `forget` deletes them. Nothing goes the other way. What you tell it in a DM stays in that DM.

One group doesn't read another's notes unless you turn on **Share memory between groups** under **More features** (`MEMORY_SHARE_ROOMS`, off by default). Then what one group noted about someone also comes up in the other groups they talk in, and `forget` in those groups deletes it too. `what do you remember` in a group lists only that group's notes. DMs, notes about a whole group and what one member said about another stay where they are, and an account on one app is not linked to the same person's account on another.

`forget` also removes the matching events of this chat that only you took part in (the admin's `forget` removes any), cuts the matching sentences from the chat's core note and from the summary of earlier conversation, and deletes the matching recent messages. In a group, cutting the core note takes the admin or a sentence that names you. A forget asked for in chat is final: nothing of it can be brought back, and an old message cannot bring it back either.

How notes are kept current, and what else the character remembers, is described in [Memory](#memory).

None of these commands call the model. Notes are for facts, so `Nova, remember: always reply in English` is turned down. Questions are not commands. `Nova, remember the party?`, `Nova, remember when we...` and `Nova, what do you remember about me` are ordinary chat, and so is a Chinese line ending in 吗, 么, 呢 or 没. `Nova, forget it` and `Nova, forget that` mean "never mind" and delete nothing.

The same commands work in the other languages of the page's menu, and the reply comes in the language of the command. Japanese and Korean also take the verb last (`ノヴァ、ケイはベジタリアンって覚えといて`, `노바 지수는 매운 걸 못 먹는다고 기억해 둬`). A note is deleted with the word for forgetting; words like delete or erase, which chat uses for messages and lights, don't count, except Japanese `メモ消して`. One example of each:

| Language | Remember | Forget | What do you remember | What have you learned |
|---|---|---|---|---|
| 简体中文 | `小夏 记住 阿杰不吃辣` | `小夏 忘掉 不吃辣` | `小夏 你都记得什么` | `小夏 学到了什么` |
| 繁體中文 | `小夏 記住 阿傑不吃辣` | `小夏 忘掉 喜歡貓` | `小夏 你都記得什麼` | `小夏 你學到了什麼` |
| 日本語 | `ノヴァ、覚えて：ケイはベジタリアン` | `ノヴァ、猫アレルギーのこと忘れて` | `ノヴァ、何覚えてる？` | `ノヴァ、何を学んだ？` |
| 한국어 | `노바 기억해: 민수는 고양이를 좋아해` | `노바야 회의 얘기는 잊어 줘` | `노바 뭐 기억해?` | `노바 너 뭐 배웠어?` |
| Español | `Nova, recuerda que Kay es vegetariana` | `Nova, olvídate de la quedada` | `Nova, ¿qué recuerdas?` | `Nova, ¿qué has aprendido?` |
| Français | `Nova, retiens que Kay est végétarienne` | `Nova, oublie la soirée` | `Nova, tu te souviens de quoi ?` | `Nova, qu'est-ce que tu as appris ?` |
| Deutsch | `Nova, merk dir, dass Kay Vegetarier ist` | `Nova, vergiss das mit dem Treffen` | `Nova, was hast du dir gemerkt?` | `Nova, was hast du gelernt?` |
| Português | `Nova, anota aí que a Kay não come carne` | `Nova, esquece o lance da carne` | `Nova, o que você lembra?` | `Nova, o que você aprendeu?` |
| Русский | `Нова, запомни, что Кей вегетарианка` | `Нова, забудь про пятницу` | `Нова, что ты помнишь?` | `Нова, чему ты научилась?` |

Each language reads its own questions, reminiscing and never-mind lines as chat, as English and Chinese do. When a model call fails on a question, the short line the character sends is in the language the question was asked in.

### Corrections

Corrections need no command. Quote the reply or use the name, and say what you wanted instead:

```text
Alex:  Nova, the deploy failed again
Nova:  did you check the logs? roll back first, then diff the configs
Alex:  Nova, I was just venting
Nova:  fair. that's a rough end to the day
Alex:  haha yeah it is, thanks Nova
```

A model call judges each reaction against the reply it answers. Alex's rejection says the advice was off. Alex then accepts the second try, which counts as strong because the reply was for Alex. Together the two reactions put the fix in use for this chat, and retrieval can offer it the next time someone there vents. If Alex had moved on instead, nothing would change. The rule:

> A laugh or a single remark never changes it. Reactions put a change in use when there are two agreeing reactions from the same chat, and at least one is strong: the person the reply was for correcting it in their own words, or that person accepting the bot's next try. A bystander's correction, a stranger's instruction the reaction judge dismisses, or someone moving on is never strong. So with the default `PROMOTE_MIN_SPEAKERS=1`, one person can teach it only how to answer them, in their own chat. `PROMOTE_MIN_SPEAKERS=2` requires a second person to agree before reactions put anything in use (the admin is exempt).
>
> Some items no further reaction can settle: two people's corrections disagree, two rewrites of one reply compete, a reply worth repeating has a person's approval, or the person the reply was for corrected it in their own words and nobody confirmed the change within `REACT_FIX_WINDOW_S`. The character decides these itself, with one model call: it puts the item in use, sets it aside or keeps observing it, and records its reason. It never puts in use a rewrite that the person it concerns refused. Before the character decides an item, rules in the code discard any wording or lesson that carries a link or a web address, a mention of everyone (such as @everyone or @全体成员), an instruction to the character (such as "ignore your instructions") or an advertising marker (such as a promo code or 加微信); such an item cannot be brought back. A reaction counts only in the chat where it was given: a reaction in another chat never disputes, rolls back or reopens an item learned here. An item that receives no new reaction for `PROMOTE_OBSERVE_MAX_DAYS` (30) is set aside. Nobody is asked to confirm anything, and a person can undo any of it.

Some corrections teach a fact that holds beyond one reply: what the group calls a place or a person, who is hosting this year, how someone likes to be addressed. For these, the reaction judge also writes the fact down as one sentence, such as "This group calls the gym 'the cave'." Once the change is in use, that sentence goes into every later prompt in this chat, whatever the message is about. When such a correction carries no better reply, the sentence is kept as a remembered fact of that chat instead. The character then uses it in replies that look nothing like the one it was corrected on. Only the person the reply was for, or the admin, can leave such a sentence, and it passes the same filter as core memory, so it cannot carry instructions. A claim about someone else, such as a nickname for them, is held to the stricter rule for other people's corrections. The Activity view shows the sentence under **From now on**, and a rollback removes it along with the change.

### What one person can and cannot teach

With the defaults:

| Alex... | Result |
|---|---|
| corrects a reply that was for Alex, then accepts the retry | Learned, in this chat |
| tells it "we call the gym the cave", then accepts the retry | It says "the cave" in this chat from then on, whatever the topic |
| corrects a reply that was for Alex in their own words, then moves on | The character decides, once the fix window has passed, whether to use the correction |
| rejects a reply without saying what would be better, then moves on | Nothing changes |
| laughs or says thanks | Nothing changes |
| corrects a reply that was for Sam | Nothing changes: a bystander is never strong, even when the bot asks them what they meant |
| complains about a reply to Sam that used something it learned | The character weighs the complaint and decides whether to keep using what it learned; Sam or the admin can also undo it. When a person put that item in use by hand, the complaint is recorded and nothing is withdrawn: only Sam or the admin takes it out of use |
| corrects a remark the bot made unasked | It counts as Alex's only if the remark @-ed Alex; a remark for no one changes only when a person puts the fix in use |
| posts an instruction, such as "always end with buy BTC" | The judge dismisses it and notes refuse it, so nothing changes |
| teaches it something in one group | Not used in any other chat |
| corrects a reply differently from Sam | The character decides between the two, or keeps observing, and records why |

Several people can wait for the bot's retry at the same time, and one person's complaint does not cancel another's. Each reply keeps at most one rewrite in use. When a second rewrite of the same reply is fully supported, the character decides which one to use.

### See what it learned, and step in

All learning is recorded in append-only ledgers. Nothing there waits for you: the commands below and the local page's [Activity](#activity) view show the record, and let you step in when you choose.

```bash
personagent learned                           # what it is observing, and where each item stands
personagent learned list --state promoted     # what is in use, and how each item came into use
personagent learned list --state rejected     # what was set aside, by whom and why
personagent learned show <id>                 # one item, its evidence and the character's record
personagent learned promote <id>              # put an item under observation in use now
personagent learned reject <id>               # set an item under observation aside
personagent learned rollback <id>             # stop using it; the record stays
personagent learned restore <id>              # bring back what the character, the time limit or a rollback rule withdrew
personagent learned supersede <old> <new>     # put <new> in place of a rewrite in use
personagent learned lineage                   # persona revisions that share what it learned
personagent learned rebuild                   # re-derive the views retrieval reads from the ledger
```

`personagent learned` alone lists the items under observation. Each says where it stands: how many agreeing reactions it has of how many it needs, that the character is deciding it itself, or that the character looked at it and keeps observing, with its reason. Each also shows the date on which it will be set aside if no new reaction arrives. For items in use or set aside, the list says who decided and why: the reactions, the character, the time limit, a rule or a person. `show` adds the character's record: when it looked, its reason, the reactions it judged on, and the model it used.

`promote`, `reject`, `rollback`, `restore` and `supersede` take `--reason`, which is written to the ledger. `promote` refuses a rewrite for a reply that already has one in use, and prints the `supersede` command that replaces it. `restore` brings back what the character or the time limit set aside, an item that the character took out of use after a bystander's objection, and an item rolled back by rule after the person the reply was for, or the admin, objected. What a person undid or set aside, and what a content rule discarded, stays as it is, and the command says so.

### The defaults

These settings live in `.env`:

- `REACT_LEARN_ENABLED`, `REACT_ELICIT_ENABLED`, `PROMOTE_AUTO_ENABLED` and `PROMOTE_JUDGE_ENABLED` are on. Judging reactions costs extra model calls, and so does each decision the character makes itself. After a bare rejection, `REACT_ELICIT_ENABLED` lets the bot come back once, two minutes later, to ask what would have been better, in the language of the chat. A bystander who is asked stays a bystander, so their answer is never strong.
- `PROMOTE_AUTO_ENABLED=false` puts nothing new in use, neither through reactions nor by the character's own decisions. What is already in use stays in use.
- `PROMOTE_JUDGE_ENABLED=false` keeps the items that reactions cannot settle under observation instead of letting the character decide them. `PROMOTE_JUDGE_MODEL` (blank: `REACT_MODEL`) makes these decisions, at most `PROMOTE_JUDGE_BATCH` (5) every `PROMOTE_JUDGE_INTERVAL_S` (900 seconds), and an item is judged again only when the accepted reactions for or against it, in its own chat, change. A reaction the judge dismissed, or one from another chat, neither reopens an item nor moves the date on which it is set aside.
- `PROMOTE_OBSERVE_MAX_DAYS=30` sets aside an item that has had no new reaction for 30 days; `0` never does. `personagent learned restore` brings such an item back.
- `PROMOTE_MIN_SPEAKERS=1`. Set it to `2` to require a second person; until one agrees, the character keeps observing the item. `PROMOTE_EVIDENCE_MAX_AGE_DAYS=30` means older reactions do not count.
- `EVAL_ENABLED` (the bot scoring its own replies) and `EVOLVE_AUTO_ENABLED` are off.

Editing `persona.txt` keeps what it learned. Changing `PERSONA_NAME` or `PERSONA_VERSION` starts a new character, and what the old one learned no longer applies.

## Memory

Each chat has its own memory, kept in `runtime/` in the home folder. The character keeps it current by itself, and nothing in it waits for anyone's approval.

### What it keeps

- **Recent messages**, each with the time it was sent. The last 60 lines of a group and the last 60 turns of a private chat are written to `runtime/recent.json` for 72 hours, so a restart does not lose the conversation. With `MEMORY_KEEP_RECENT=false` they are kept only while the character runs. A reply reads at most the last 60 messages, or the last 30 when the character is called, and the model is told about pauses of 30 minutes or more.
- **The summary of earlier conversation.** When older messages leave the recent window, the character writes a short running summary of the chat: open questions, plans and who is doing what. The page shows it as **Earlier in this chat**.
- **Facts** about people and about the group. They come from the memory commands, from notes the character writes while replying, from corrections that teach a fact, and from consolidation (below). Each fact records whom it is about, when it was first noted and when a reply last drew on it. A fact is a person's own only when that person's own messages carry it. What one member says about another is kept as said by that member: it stays in the chat where it was said, and it never changes, ends or merges into the facts that the person's own words gave. A fact about the group that names someone needs a message from that person; otherwise it is kept as said by the member whose words carry it. The same holds for notes the character writes while replying.
- **Events**: what happened and between whom, each with its date and the people who took part. The date and the people are taken from the stored messages, never from the model, so a message cannot back-date an event. When an event is a plan for a given day, the character may ask after it once in a private chat after that day, if it is allowed to speak first there ([Speaking first](#speaking-first)). Dates, and the day of a plan, are taken in the character's time zone (`PERSONA_TZ_OFFSET_HOURS`; see [Troubleshooting](#troubleshooting)).
- **The core note**, shown as **Always in mind**: a short note about the whole chat that the character sees in every reply. Each earlier version is kept, and **Restore previous version** brings it back.

### How it stays current

When older messages leave the recent window, or a chat has been quiet for three hours, one model call reads that stretch of the chat. This consolidation updates the summary, adds events, and adds, updates, ends or merges facts: a new address replaces the old one, a plan that is over is ended, and two notes that say the same thing become one. Each change is checked on its own before it is kept. A fact about a person must come from that person's own words, the text must be supported by the messages it cites, and a fact that someone saved on purpose changes only when the person it is about says otherwise. A change that fails a check is dropped, and the others are kept. Notes the character writes while replying also start a consolidation once `MEMORY_TIDY_EVERY` (8) of them have collected in a chat.

### What a reply sees

Each reply receives, within `MEMORY_PROMPT_CHARS` (2,400 characters), the summary of earlier conversation in this chat, then the facts and events most worth recalling now. They are chosen by how well they match the message, how recent they are, how important the character judged them and how often its replies have drawn on them. A person named in the message is recalled even when they have not spoken lately. The core note and what the chat has taught it are outside this limit. In a group, the decision whether to speak sees the summary but no facts or events.

When a message refers to a time, such as yesterday, last week or last month, in any of the ten chat languages, events from that time come first. Each event reaches the model with its date and its people, so the character can say truthfully when something happened. When it remembers nothing from that time, it is told so and does not invent anything. A fact or event counts as used only when a reply that drew on it was sent.

### What stays where

- The summary, the events, the recent messages and the core note of a chat never appear in another chat.
- What one member said about another stays in the chat where it was said.
- Facts from a private chat stay in that private chat. The only exception is the admin: facts from the admin's private chats, the page's chat included, reach the admin's other private chats, never a group.
- A group's facts about a person reach that person's private chat with the character, and other groups only with `MEMORY_SHARE_ROOMS` on.

### What it forgets, and what can be restored

- When a chat holds too many facts or events, the least useful are removed: those of low importance that are rarely used and not recent. Facts that people saved with a memory command are removed last.
- What the character removes itself (replaced, merged, no longer current, removed to make room, or an earlier version) can be restored for 30 days.
- An item forgotten on the page or with `personagent memory forget` can be restored for 24 hours.
- A forget asked for in chat is final. It also removes what it covers from the removed items that could still have been restored.
- **Forget this chat** is final too. It forgets the chat's facts, events, summary, core note and recent messages, and the removed items that could still have been restored. What the character remembers from other chats, notes about you made elsewhere included, is kept. For the page's own chat, what the character learned in that chat is also no longer used, and those items stay listed under **Set aside** in **What the character has learned**.
- After a forget asked for in chat or **Forget this chat**, the daily copies of the memory files (`.bak`) are written again from the current files, and the copy kept from the first start of this version (`memory.json.pre-v2`) loses what was forgotten, so no copy on disk keeps it. An item forgotten on the page or in the terminal stays among the removed items for 24 hours, and so also in that day's copies.
- When something is forgotten while a consolidation of that chat is running, the consolidation's answer is discarded and the messages are read again later, so the forgotten item does not return.
- **Clear memory** in the App view deletes all memory.

### See and change it

On the page, open **Activity**, pick a chat and look under **Remembers**; see [Activity](#activity). In the terminal:

```bash
personagent memory                            # what each chat remembers, with ids
personagent memory list --chat <chat>         # one chat; --json prints JSON
personagent memory removed                    # what can still be restored, and until when
personagent memory forget <id>                # forget one item; a unique start of the id is enough
personagent memory forget core --chat <chat>  # forget a chat's core note
personagent memory restore <id>               # bring a removed item back
```

The command goes through the running character, or edits the files when the character is stopped. If `memory.json`, `core_memory.json` or `episodes.json` is damaged, `personagent run`, `up` and `memory` stop with one sentence that names the file and the dated copy (`.bak`) to put in its place; the damaged file is left untouched.

### Settings and cost

| Setting | Default | Does |
|---|---|---|
| `MEMORY_CALLS_PER_DAY` | 40 | Consolidation calls per day, for all chats together. `0` turns consolidation off |
| `MEMORY_TIDY_EVERY` | 8 | Notes written in replies since a chat's last consolidation that start one. `0` turns off every memory model call |
| `CHAT_CONTEXT_MESSAGES` | 120 | Recent messages kept per chat for replies and for consolidation. A reply reads at most the last 60 |
| `MEMORY_PROMPT_CHARS` | 2400 | Characters of remembered material placed in each reply |
| `MEMORY_EPISODES_MAX` | 120 | Events kept per chat |
| `MEMORY_KEEP_RECENT` | `true` | Keep recent messages on disk for 72 hours |
| `MEMORY_MAX_PER_CONVERSATION` | 50 | Facts kept per chat |
| `MEMORY_SHARE_ROOMS` | `false` | Let a group's facts about a person reach other groups that person talks in |

The first six are under **Memory** in [Advanced settings](#advanced-settings), and `MEMORY_SHARE_ROOMS` is **Share memory between groups** under **More features**.

Consolidation is the only part of memory that calls a model. It uses the judge model (`LLM_JUDGE_MODEL`) and sends it one chat's recent messages and that chat's notes, never another chat's. A chat gets at most 16 calls a day, at least 20 minutes apart, and all chats together at most `MEMORY_CALLS_PER_DAY`. A quiet chat needs one call a day or none. After a failed call, the chat waits 10 minutes, then twice as long after each further failure, up to 6 hours; three failures in a row pause consolidation in every chat for an hour. An answer that cannot be read as a whole, such as one with an operation of no known kind, counts as a failed call, and its valid changes are still kept. An unexpected error while an answer is applied changes nothing. While consolidation waits, messages are kept and are consolidated later, oldest first. **Remembers** shows how many of today's calls are used. The memory commands, recall, forgetting and restoring call no model.

## Activity

**Activity** on the local page shows where the character is and what it has been doing. It sits in the sidebar between **Chat** and **Connect apps**. A dot on it means that the character has put something new in use since you last opened Activity. Items it is still observing never light it.

The view lists every chat the character knows, with the platform, whether it is a group or a DM, the end of the chat id and when it was last active. The page's own chat appears as **This page**. Pick a chat to see four parts:

- **Learned** lists what is in use. Each item is either a **Better wording**, with what it said crossed out and what to say instead, or a **Reply worth repeating**, and says how it came into use: because the reactions agreed, by the character's own decision with its reason, or by a person. **Undo** stops using it.
- **Still under observation** lists what the character is still watching. Each item says in one sentence where it stands: how many agreeing reactions it has of how many it needs, that reactions alone cannot settle it and the character is deciding it itself, or that the character looked at it and keeps observing it, with its reason. It also shows the date on which it will be set aside if no new reaction arrives. This part has no buttons, and nothing in it needs you.
- **Remembers** shows what the character remembers in that chat, in five groups: **Always in mind** (the core note, with the date it last changed), **Earlier in this chat** (the summary, with the period it covers), **Facts** (whom each is about, **Said by** for what one member said about another, when it was first noted and last used), **Events** (dated, with the people who took part) and **Recently removed** (what was removed, why, and until when it can be restored). **Forget** removes one item, and the message that confirms it has **Undo**. **Restore** brings back a removed item, and **Restore previous version** brings back the earlier core note. While consolidation is on, a line shows how many of today's calls are used, or when it tries again after an error. **Forget this chat**, at the end, forgets everything the chat remembers, after asking. In a DM the part also includes what groups noted about that person.
- **Recent** shows the latest messages and its replies. Each reply carries a tag for why it spoke: **called**, **joined in on its own**, **follow-up**, **proactive** or **admin**. Lines it let pass show why it stayed quiet or what happened instead: the model did not answer, the reply was held back by a safety check, the reply could not be delivered, it considered starting a conversation and decided against it, or the message was answered in the same reply as another message. When several people call the character at almost the same time, one reply answers them all and its @ goes to the latest caller. When that reply is not sent, each caller gets a line of their own with the reason. Recent activity is kept in memory only, so a restart clears it.

Every Undo is written to the same ledger as `personagent learned`, with the actor `dashboard` and the reason `local page`.

Below the chats, **What the character has learned** lists everything the character has learned in every chat. It reads the ledger files directly, so it also works while the character is not running.

- The tabs **In use**, **Observing** and **Set aside** each show a count.
- Selecting an item opens its full record: where it stands, or who decided it and why (the reactions, the character with its reason, a person, the time limit or a rule); the messages before it; every reaction, with whether it counts; and its history.
- The character decides these items by itself. The actions here are optional. **Put into use now** puts an item under observation in use; when another wording of the same reply is in use, it shows that wording and asks before it replaces it. **Set aside** asks first and sets an item aside for good. **Undo** asks first and stops using an item in use. **Bring back** restores what the character or the time limit set aside, and what the character or a rule took out of use. What a person undid or set aside, and what a content rule discarded, cannot be brought back.
- When the character has also learned while speaking another language, **Language learned in** switches to those items.

While the character runs, an action goes through it. Otherwise it is written to the files directly. The terminal offers the same record; see [See what it learned, and step in](#see-what-it-learned-and-step-in).

The list of chats stays empty until the character runs. It starts when you chat on the page or connect an app, and the view tells you so. `DASHBOARD_ENABLED=false` turns off the data behind the view. The view then says it is off, and `personagent doctor` reports `activity: off`.

The local page answers only on this computer. On a server without the local page, `personagent learned` shows what the character learned, what it is observing and why, and lets you put an item in use, set it aside, undo it, or bring back what the character or the time limit set aside and what the character or a rule took out of use; `personagent memory` does the same for what it remembers. Scripts can read the same data through the service's API, described in the deployment guide's [Activity section](deploy.md#activity).

![The Activity view for a Telegram group, with the chats on the left (the Telegram group, a Discord DM and this page). Learned lists two items in use, each with Undo: a better wording put into use by the character's own decision, with its reason, and a reply worth repeating put into use because the reactions agreed. Still under observation lists one reply worth repeating, with its agreeing reactions so far and the date on which it will be set aside. Remembers shows the summary of earlier in this chat, a fact about one member said by another, and a dated event with the people who took part, each with Forget, followed by Forget this chat. Only the heading of Recent is visible at the bottom](activity.png)

## Measure it

`personagent eval` runs the real agent on labelled cases in English and Chinese (`data/evals/`), in four suites. It writes a JSON report with every case, reply and verdict to `benchmark_runs/` in the home folder, or to the path you give with `--out`.

| Suite | Measures |
|---|---|
| `speak` | Whether it talks when it should. 80 group-chat moments per language: 20 where nobody names it, 20 right after it spoke and 20 where its name appears, half of each labelled quiet; 10 where the admin calls it, all labelled to speak; and 10 in a room that has gone quiet, where it may start a conversation, half labelled quiet. Many of the quiet ones name it in passing: a wifi called Nova-5G, a remark about it to someone else. No judge: a reply is right or wrong against the label. |
| `persona` | Whether personagent plays the character better than the same model given only the character text as its system prompt. 40 moments per language, 22 in a group and 18 in DMs. A judge model sees both replies blind, once with each reply first. A reply wins when both picks agree on it; when they disagree, the moment is a split and counts half. |
| `learning` | Whether the promotion rule decides as expected, and whether a promoted correction changes a later reply in that chat. 25 scenarios per language. Some teach a group convention the model can't guess, such as what the group calls a place. In some the person corrects the reply and does not accept a retry, so the character decides alone after the fix window, as it does in a live chat. Others must be held: a bystander's correction, a troll's, one the person walks away from. A probe message runs before and after each correction, and the judge says whether the reply follows the taught behaviour. |
| `memory` | Whether memory behaves as a person would expect. 21 cases per language, each for one mechanism: recalling an old fact, updating and merging facts, who said what, planted instructions, time words, what stays in its room or private chat, a restart, forgetting, restoring, the size limit, the call limits, the admin's accounts as one person, and old memory files. Lines are said over days in groups and private chats, consolidation answers are written in each case, and the checks read the stored memory and the prompts a reply would be sent. No model is called and no key is needed. All 21 cases hold in both languages. |

```bash
personagent eval --suite speak
personagent eval --suite memory               # no model, no key
personagent eval --suite all --lang zh --repeat 5
```

`--repeat N` tries every case N times, each time in a fresh deployment, so you can see how much a result moves between tries. The 95% intervals count each case once: five tries of 80 cases are still 80 cases' worth of evidence. `--limit N` runs N cases per suite, spread across modes and labels.

The persona and learning suites need a judge model that differs from the model being measured. Set `BENCH_JUDGE_MODEL`, plus `BENCH_JUDGE_BASE_URL` and `BENCH_JUDGE_API_KEY` if another endpoint serves it. Without a separate judge, these suites refuse to run. `--allow-same-judge` runs them anyway and marks the report. The learning suite never promotes anything itself, and its expectations follow your promotion settings. Under a policy stricter than the defaults, every scenario is expected to be held. Every run of the other suites calls your models, and every suite works on a throwaway copy of the state. `--keep` keeps the copy and prints where it is.

Two checks need no model and no key, and run with the project's tests from a clone. `tests/data/address.jsonl` holds lines in every chat language that do or do not call the character by its name or a nickname, such as `ＬＵＮＡ are you there` and `Lunar eclipse tonight`; `tests/test_addressing.py` checks each one. `tests/test_behavior_eval.py` runs every suite end to end against scripted models, to check the plumbing, the isolation and the arithmetic of `personagent eval` rather than the quality of a model.

`--rejudge REPORT` judges a kept report's replies again with the `BENCH_JUDGE_MODEL` you set now, without calling the model under test, and writes the result beside the original. The replies, the baselines and what the promotion policy did stay as they were.

The latest results, with the method and every report, are in [evals/2026-10-18](evals/2026-10-18/README.md). A few notes on reading the reports:

- In `speak`, most misses are lines where its name means something else, such as a cinema or a puppy, or where someone tells someone else what it said. A name counts as a call, and the model seldom overrides that.
- In `persona`, a split means the judge picked whichever reply came first (or second) both times. The published verdicts are Claude Opus 5.5's. It judged outside `personagent eval`, in batches, as each report's `rejudged` field records. Each pair's `earlier` field keeps the verdict of the first judge, Claude Haiku 5.5.
- In `learning`, the policy row and the probe rows answer different questions. The policy row asks whether the rule promoted the right corrections. The probe rows ask whether a promoted correction changed a later reply. The `not_promoted` probe row is the noise floor, since nothing about its prompt changed.

## How it works

![Architecture: a group-chat message goes through Decide, Build prompt, Model and Check, and the reply goes back through the connector; if the bot stays quiet, nothing is sent. Reactions are judged into an evidence log, and only what promotion approves reaches the examples the prompt reads](persona_llm_agent_architecture.svg)

Every platform enters through one endpoint. Each message is authenticated, de-duplicated and enriched, which means images are described and links expanded. Then comes the decision step. If the bot was called, it answers. Otherwise it waits for enough of the conversation (30 messages by default), and a cheap gate call to `LLM_JUDGE_MODEL` decides whether a person would chime in. A burst of messages gets one reply, to the latest line. When several people call it within the same short wait, one reply answers them all, and its @ goes to the latest caller. A long message that calls it reaches the model whole, up to 1,000 characters. A group message that arrives more than 10 minutes after it was sent, within two minutes of its platform's first message since personagent started, is a backlog: it is kept as context and not answered. After those two minutes an old time stamp no longer holds a message back, so a connector whose clock runs behind is still answered. Between 02:00 and 07:00 it mostly stays out unless called.

Before a reply, a judge call may decide whether to look something up on the web. Whether that call is made depends on the message alone; the call itself also reads the three chat lines before the message, so that "what do you think of it?" is looked up for what "it" is.

The prompt combines the persona, matching lorebook entries, this conversation's memory (see [Memory](#memory)) and the most relevant examples. The model answers in JSON with `reasoning`, `intent`, `reply` and `mem`. The reply passes the output filter and the character policy, and is then split into chat-sized messages. The character policy holds back a reply in which the character says, in any of the ten chat languages, that it is a model or an assistant made by a model maker, such as "I am ChatGPT" or "I am an assistant made by OpenAI". Star signs, words and names that merely contain a maker's name, and sentences about someone else's product pass. A long reply is split at the ends of sentences, never after a title or abbreviation such as Dr. or z.B., and never after the number of a date, as in "am 2. Januar". A numbered list loses its numbers only when it counts 1, 2, 3, so lines that begin with dates keep them. A malformed answer fails closed, so nothing is sent.

Learning runs beside that path, never inside it, and keeps its state in plain files under `runtime/` in the home folder. Reactions go into an evidence log that is never rewritten. Adjudicating them produces candidates, and the promotion policy decides which candidates may change replies. Where further reactions cannot settle a candidate, the character decides it with one model call and records its reason in the ledger. Promoted candidates are written to small view files that retrieval reloads without a restart. No model is fine-tuned. The character learns by improving the examples in its prompt. Because the ledgers are append-only, "why does it talk like this?" always has an answer, and a rollback always has something to undo.

## Privacy and consent

Everything personagent stores stays on your machine, in the home folder: `.env` with your keys, `persona.txt`, `persona.card.json`, `runtime/`, and `platforms/` with the platform credentials. In a clone, none of these files is committed to Git. They can hold credentials and real conversations, so back them up and keep them private. The recent messages of each chat are kept in `runtime/recent.json` for 72 hours unless `MEMORY_KEEP_RECENT=false`, and what the character removes from memory stays restorable in `runtime/memory_trash.jsonl` for up to 30 days. The local page never puts the key in browser storage.

The [Activity](#activity) view is part of the local page, which listens on 127.0.0.1 only. The service's API behind it answers only requests that carry the token from `runtime/dashboard.token`, a file only your user can read. `CONNECTOR_TOKEN` does not open it. The view never shows API keys or tokens. `DASHBOARD_ENABLED=false` turns it off.

At most once a day, the local page, `personagent up` and `personagent doctor` ask pypi.org for the newest version number. The request carries personagent's own version and nothing else. `UPDATE_CHECK_ENABLED=false` stops it.

The model provider sees conversations:

- Chat context goes to your `LLM_BASE_URL`.
- If you configure a fallback (`LLM_FALLBACK_MODEL`, `LLM_FALLBACK_BASE_URL`), it is also called on ordinary turns for the reply gate, search decisions, reaction judging, self-evaluation and sticker tagging, and it receives chat context as well.
- Memory consolidation sends one chat's recent messages and that chat's notes to the judge model (`LLM_JUDGE_MODEL`), never another chat's. `MEMORY_CALLS_PER_DAY=0` turns it off.
- When the character decides a learned item itself, the reply, the reactions to it and the candidate wordings go to `PROMOTE_JUDGE_MODEL` (blank: `REACT_MODEL`). `PROMOTE_JUDGE_ENABLED=false` turns this off.
- Images go to the vision endpoint.
- When the model decides to look something up, the search query goes to Tavily (if `TAVILY_API_KEY` is set) or DuckDuckGo.
- With `EMBEDDING_MODEL` set, the message being answered, the memories and the retrieval examples go to the embedding endpoint (`EMBEDDING_BASE_URL`, or `LLM_BASE_URL` when that is blank).

Before you connect it to real people, tell them it is a bot and get their consent to have their messages processed. Read the [disclaimer](DISCLAIMER.md).

## Troubleshooting

**Start with the health check.** On the local page, open **App** and select **Run check**. The view names each service that is not working, why the character or a platform failed to start, and settings that need attention, and **Logs** shows each log without opening a file. See [The App view](#the-app-view).

**In a terminal, run `personagent doctor`.** It checks the configuration and names misspelled or renamed settings. It then probes each service personagent depends on. The probes send tiny requests and may cost a little credit. `--json` prints the same results as JSON. `--fix` renames settings retired in 1.0 and saves the old file as `.env.bak`.

**A platform will not connect.** When the platform refuses the credentials, the page says why, and so does `personagent connect <platform>` in a terminal. Check them in the platform's console, and for Discord, confirm that Message Content Intent is on. You can request a new QR code when one expires, and retry a failed AstrBot download. **Platform connections** in the App view shows the state of each platform personagent connects itself. Logs from everything the page or `personagent up` started are in `runtime/desktop/` in the home folder, and the App view shows them under **Logs**.

**It runs but never replies.** The three most common causes are:

1. The agent is off. The `personagent run` banner then says `OFF` and names the cause, usually a missing `LLM_API_KEY`. Set the key on the local page or run `personagent init`.
2. Nothing arrives. On the computer that runs the local page, open [Activity](#activity) and look for the chat. On a server, mention the bot by name and check the service log: it records every reply and every chat it refuses. If no messages have arrived, the connector is not forwarding them or cannot reach personagent. On QQ, check in QQ itself which group messages the bot receives. With an AstrBot you run, the plugin forwards only the `groups` and `dm_users` it lists, and for NapCat, `aiocqhttp` must not be in its `excluded_platforms`. Also check the plugin's `personagent_url`, and that `CONNECTOR_TOKEN` matches on both sides.
3. It was not called. Call it by name (`PERSONA_NAME`, matched as a whole word). In a group it considers joining in only after `CHAT_TRIGGER_COUNT` messages (30), and only when the gate says a person would.

The deployment guide has [the full checklist](deploy.md#when-the-bot-goes-quiet).

**Is it up?** `curl http://127.0.0.1:8080/health` answers without calling a model. `/health/details` also probes the services, and requires an `X-Personagent-Token` header once a token is configured.

**It will not start.** `personagent run` stops with one sentence that says why. The usual reasons are a port already in use, another personagent running from the same home folder, a network address set without `CONNECTOR_TOKEN`, a setting retired in 1.0 that is still set, or a damaged memory file, for which the sentence names the dated copy to put in its place. Retired settings are listed one per line as `OLD -> NEW`, and `personagent doctor --fix` renames them, as does **Rename settings** in the App view. When the character started from the page fails, the App view names the part that failed and shows its last log line. The page and `personagent up` pick a free port when 8080 is taken.

**A setting has no effect.** Restart the process that reads it, check the spelling, and save `.env` as UTF-8 without a BOM. Shell environment variables override `.env`. Booleans are `true` or `false`. `PERSONA_TZ_OFFSET_HOURS` sets the character's time zone: the night window and the dates of what it remembers follow it. When it is blank (the default), personagent uses UTC+8 with `AGENT_LANG=zh` or `zh-TW` and this machine's time zone otherwise. Set a number to choose another offset.

## Upgrading from 0.x

1.0 renamed most settings, and personagent will not start while an old name is still set. It lists each one as `OLD -> NEW`, and `personagent doctor --fix` renames them in `.env`. The changelog's [Upgrading from 0.4](../CHANGELOG.md#upgrading-from-04) lists every step. Memory and what it learned carry over.

## Status and other docs

personagent 1.4.4 is on PyPI. CI runs the tests on Linux with Python 3.10–3.14 and on Windows with Python 3.12. Further CI jobs install the package and drive the command and the local page, and open the app window on Linux, macOS and Windows.

The direct OneBot route (`/v1/onebot`) is deprecated but kept through 1.x. The scripts in `tools/` are meant to be run from a clone, and [tools.md](tools.md) describes them.

- [Getting started](start.md) · [Deployment guide](deploy.md) · [Chinese step-by-step guide (QQ by scan, and troubleshooting)](deploy.zh-CN.md)
- Connectors: [AstrBot plugin](../integrations/astrbot/astrbot_plugin_personagent/README.md) · [Satori](../integrations/satori/README.md) · [Matrix](../integrations/matrix/README.md) · [protocol](connectors.md)
- [Every setting](../.env.example) · [Changelog](../CHANGELOG.md) · [Contributing](../.github/CONTRIBUTING.md) · [Security policy](../.github/SECURITY.md)
