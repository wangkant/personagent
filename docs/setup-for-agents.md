# Set up personagent: instructions for a coding agent

A user gave you this file and asked you to install and set up personagent for them. Follow the steps in order. Every command here works with personagent 1.3.0 from PyPI and later. Talk to the user in the language they write in, and use the Chinese names of the page's buttons (given in brackets) when they write in Chinese.

## What you are setting up

personagent is a character for group chats. It answers when called, judges when a person would join in, and learns from corrections people make. It runs on the user's computer as a Python package. A local web page at `http://127.0.0.1:<port>` handles setup, a one-to-one chat with the character, and connections to QQ, WeChat, Telegram, Discord and a dozen other chat apps. Replies come from any OpenAI-compatible model service the user has a key for.

Everything it stores lives in one **home folder**: `.env` (settings and keys), `persona.txt` (the character), `runtime/` (memory and what it learned) and `platforms/` (chat app connections).

When you are done:

1. `personagent --version` prints `personagent 1.3.0` or later.
2. The home folder has `.env` with the user's language, character name and model service, and `persona.txt` with the personality.
3. The local page is running, the user has the link, has entered their model key there and has chatted with the character.
4. Any chat apps the user wanted are connected, by the user, in the page.
5. The user knows how to start it next time, how to update it and how to undo it.

## Rules

1. **Ask the user only for the answers in step 1.** Use the defaults for everything else, and ask all the questions in one message.
2. **Never handle secrets.** Do not ask the user to paste an API key, bot token or password into the chat, and never put one in a command you run. The model key goes in through the local page (step 6). Two other routes are open only if the user prefers them: the user writes `LLM_API_KEY` into the home's `.env` themselves, or the user sets an environment variable in their own terminal for `--key-env`. If a user pastes a key into the chat anyway, do not repeat it or use it. Ask them to enter it in the page instead.
3. **Never print key values.** Do not print `.env` with `cat`, `type` or `Get-Content`. Step 5 has commands that print only whether a key is set and the settings that are not secret.
4. **The page link is a credential.** Its `#token=` part opens the page, and the page can show the saved key. Give the link only to the user. Do not post it anywhere else, and do not call the page's API yourself. Reading the link from the log, and loading the page's address without the token to see that it answers, are fine (step 6).
5. **QR-code logins are done by the user.** QQ and WeChat connect by scanning a code with a phone in the page. App tokens for Telegram, Discord and the rest are pasted into the page by the user.
6. **Do not install system software without asking.** Python, uv, pipx, Homebrew packages, apt packages and lasting changes to PATH, such as in the shell's startup files, all need a yes from the user first. Installing personagent itself is what the user asked for.
7. **Know what costs money.** The model service charges per message. Verifying the key in the page sends one tiny request. `personagent doctor` probes every configured upstream service with tiny paid requests, so ask before you run it. `personagent demo` and `personagent --version` are free. Do not run `personagent chat`, `personagent demo --online` or `personagent eval` unless the user asks: they call the model, and `eval` calls it hundreds of times.
8. **Do not run commands that wait for a person.** Bare `personagent`, `personagent init` without `--no-input`, `init --terminal`, `start --terminal`, `chat` and `connect astrbot` without a folder ask questions in a terminal or open the page and keep running. Your shell may count as a terminal: on Windows a stdin redirected from `NUL`, which many agent shells give a command, does, so bare `personagent` and `personagent init` would start the page and never return. Always pass `--no-input` to `init`. `start` and `up` run until stopped, so start them in the background as step 6 shows.
9. **Always pass `--home`.** Give every command `--home "<home>"`, where `<home>` is the home folder's absolute path. Without it personagent picks a folder by rules that depend on the current directory.

## 1. Ask the user

Ask these in one message, with the defaults shown, and accept "use the defaults":

| Question | Default | Becomes |
|---|---|---|
| Which language should the character speak? English or Chinese | the language the user writes to you in | `--lang en` or `--lang zh` |
| The character's name. It answers when its name comes up in a chat | `Nova` (English), `小夏` (Chinese) | `--name` |
| Its personality: one of the table below, or their own description | warm listener (`warm-listener`) | `--persona`, or your own `persona.txt` (step 4) |
| Which model service do they have, or want, an API key for? | DeepSeek | `--provider` (table below) |
| Where should the home folder live? | `~/personagent` (on Windows `C:\Users\<name>\personagent`) | `<home>` |
| Which chat apps should it join, if any? None are needed to start | none | step 7 |
| How to install, only if it matters (they prefer pip, or neither uv nor pipx is present) | uv, else pipx, else a virtual environment | step 3 |

Personalities:

| `--persona` | Character | 中文 |
|---|---|---|
| `dry-wit` | Dry-witted friend: deadpan, short replies, teases lightly | 毒舌损友 |
| `warm-listener` | Warm listener: asks how you are, remembers the small things | 温柔倾听者 |
| `gamer` | Gamer: co-op shooters and roguelikes, friendly trash talk | 游戏搭子 |
| `bookworm` | Bookworm: careful words, recommends books when asked | 文艺书虫 |
| `template` | A plain starting character to rewrite later | 以后自己写 |

Model services:

| `--provider` | Service | Default model | Where the user gets a key |
|---|---|---|---|
| `deepseek` | DeepSeek | `deepseek-flash` | https://platform.deepseek.com/api_keys |
| `siliconflow` | SiliconFlow | `deepseek-ai/DeepSeek-V3.2` | https://cloud.siliconflow.cn/account/ak |
| `bailian` | Alibaba Bailian / Qwen | `qwen-plus` | https://bailian.console.aliyun.com/ (outside mainland China, add `--base-url https://dashscope-intl.aliyuncs.com/compatible-mode/v1`) |
| `zhipu` | Zhipu GLM | `glm-4.7-flash`, free to use | https://bigmodel.cn/usercenter/proj-mgmt/apikeys |
| `moonshot` | Moonshot / Kimi | `kimi-k2.6` | https://platform.kimi.com/console/api-keys |
| `ark` | Volcengine Ark / Doubao | `doubao-seed-2-1-lite-260915` | https://console.volcengine.com/ark/region:ark+cn-beijing/apikey (enable the model in the Ark console first) |
| `openrouter` | OpenRouter | `deepseek/deepseek-v4.1-flash` | https://openrouter.ai/keys |
| `openai` | OpenAI | `gpt-6-luna` | https://platform.openai.com/api-keys |
| `gemini` | Google Gemini | `gemini-3.8-flash` | https://aistudio.google.com/apikey |
| `ollama` | Ollama on this computer | `qwen3` | no key; Ollama must be running with the model pulled |
| `other` | any other OpenAI-compatible service | none | needs `--base-url` and `--model` |

`--model` replaces a preset's default model.

## 2. Check the prerequisites

personagent needs Python 3.10 or later (3.10 to 3.14 are tested). uv and pipx are optional. See what is there:

```powershell
py --version
python --version
uv --version
pipx --version
```

```bash
python3 --version
uv --version
pipx --version
```

On Windows, a `python` that only offers the Microsoft Store is a placeholder, not an installation.

If uv is present, you need nothing else: uv fetches a suitable Python by itself. Otherwise, if no Python 3.10 or later is present, ask the user which of these to install, and install only after a yes:

| System | uv (recommended) | Python |
|---|---|---|
| Windows | `winget install --id astral-sh.uv -e` | `winget install --id Python.Python.3.12 -e` |
| macOS | `brew install uv`, or `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `brew install python@3.12` |
| Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | the distribution's packages, such as `sudo apt install python3 python3-venv` on Debian or Ubuntu |

A new terminal may be needed before a freshly installed command is on PATH. Call it by its full path in the meantime.

## 3. Install personagent

Use the first route that fits, unless the user chose one:

**uv** installs a `personagent` command into uv's tool folder (`uv tool dir --bin` prints it):

```bash
uv tool install personagent
```

**pipx** does the same with pipx:

```bash
pipx install personagent
```

If uv or pipx says its folder is not on PATH, call `personagent` by its full path, and ask the user before you run `uv tool update-shell` or `pipx ensurepath`, which edit the shell's startup files.

**A virtual environment** needs neither and changes no PATH. Windows PowerShell:

```powershell
python -m venv "$env:USERPROFILE\.personagent-venv"
& "$env:USERPROFILE\.personagent-venv\Scripts\python.exe" -m pip install personagent
& "$env:USERPROFILE\.personagent-venv\Scripts\personagent.exe" --version
```

macOS and Linux:

```bash
python3 -m venv ~/.personagent-venv
~/.personagent-venv/bin/python -m pip install personagent
~/.personagent-venv/bin/personagent --version
```

Other routes:

- `python -m pip install personagent` into the user's own Python, as the README shows, if they prefer it. Some systems refuse this with "externally-managed-environment": use one of the routes above instead.
- uvx runs it without installing: put `uvx` in front of every `personagent` command in this file, such as `uvx personagent --version`.
- For contributors, a clone: `git clone https://github.com/wangkant/personagent.git`, then a virtual environment inside it with `pip install -e .`, and `python -m persona_agent` in place of `personagent`, such as `.venv/bin/python -m persona_agent --home "<home>" demo`. A clone is its own home unless `--home` says otherwise.

If downloads from PyPI time out, which is common on networks in mainland China, ask the user whether to use a mirror, such as `--index-url https://pypi.tuna.tsinghua.edu.cn/simple`. pip, `uv tool install` and `pipx install` all accept `--index-url`.

Check the install:

```bash
personagent --version
```

It prints `personagent 1.3.0` or later. From here on, `personagent` means the command from your route: the full path, or `uvx personagent`, when it is not on PATH.

## 4. Create the home folder

Run `init --no-input` with the user's answers. Pass `--lang`, `--name`, `--persona` and `--provider` every time, with the step 1 defaults for anything the user left to you: left out, `--lang` falls back to the system language rather than the user's, and `--persona` to the plain `template` character rather than warm listener. The same line works in PowerShell and bash:

```bash
personagent --home "<home>" init --no-input --lang en --name Nova --persona warm-listener --provider deepseek
```

A Chinese character on Zhipu's free model:

```bash
personagent --home "<home>" init --no-input --lang zh --name 小夏 --persona dry-wit --provider zhipu
```

Any other OpenAI-compatible service:

```bash
personagent --home "<home>" init --no-input --lang en --name Nova --persona warm-listener --provider other --base-url https://api.example.com/v1 --model "<model id>"
```

What `init --no-input` does:

- It asks nothing, sends nothing over the network and does not test a key.
- No flag is required. On a fresh home, a flag left out gives the system language for `--lang`, `Nova` or `小夏` for `--name`, `template` for `--persona` and DeepSeek for `--provider`. On a home that is already set up, it keeps the saved value.
- Without a key it still succeeds, with exit code 0. The key comes in step 6.
- It ends with a "Next" list written for a person at a terminal. Skip it and follow this file: "run this setup again" there means the interactive setup that rule 8 rules out, and the `chat` command it shows calls the model, which costs money.
- It creates `<home>` if needed and writes `<home>/.env` from the shipped template, readable only by the user on macOS and Linux, and `<home>/persona.txt`.
- It exits 1 with one line of explanation when a flag is wrong: `--provider other` without `--base-url`, a `--base-url` without `https://` or `http://`, or a `--key-env` variable that is empty. An unknown `--provider` or `--persona` value exits 2 with argparse's list of choices. These failures save none of the flags. Only the empty `--key-env` variable is noticed late: by then a new home holds the template `.env`, with no name and no `persona.txt`. Fix the flag and run the whole command again.
- Run it again to change the name, personality or service. `persona.txt` follows the flags only while nobody has edited it. Switching to another service clears the saved key, so it is never sent to the wrong service, unless you also pass `--key-env`.

With `--provider ollama` no key is needed, and the page goes straight to chat. Pass a model the user has pulled, such as `--model qwen3`, and check that Ollama is running.

**A character in the user's own words.** Run `init` with `--persona template` and the name, then write their description into `<home>/persona.txt` as UTF-8 plain text, in the second person, starting with the name. Keep it under 4000 characters, so the page can edit it. Describe who the character is, how they usually talk, and what they do in the situations the user cares about:

```text
Your name is Nova. You chat with friends about films and cooking.
You speak directly and make the occasional joke.

Usually reply in a sentence or two. Explain more when someone asks a serious question.
When a friend vents, listen before offering advice.
If you have not seen a film, say so instead of inventing an opinion.
```

The name in `persona.txt` should match `--name`, which is what the character answers to. `init` leaves an edited `persona.txt` alone, and the page keeps it unless the user picks another personality there.

## 5. Check it for free

```bash
personagent --version
personagent --home "<home>" demo
```

`demo` plays three short scenes on a scripted model in a throwaway folder: what it lets pass in a group, how it learns from a correction, and how it refuses a troll. It needs no key, sends nothing anywhere, finishes in seconds and changes nothing in the home. It plays its own demo character, in the home's language.

Check that `<home>` holds `.env` and `persona.txt`. Show the user `persona.txt` if they want to read their character; it holds no secrets.

Whether a key is set, as True or False, without printing it. Windows PowerShell:

```powershell
[bool](Select-String -Path "<home>\.env" -Pattern '^LLM_API_KEY=\S' -Quiet)
```

macOS and Linux:

```bash
grep -q '^LLM_API_KEY=.' "<home>/.env" && echo "key set" || echo "no key"
```

The language, name and model service, which are not secret. Windows PowerShell:

```powershell
Select-String -Path "<home>\.env" -Pattern '^(AGENT_LANG|PERSONA_NAME|LLM_BASE_URL|LLM_MODEL)=' | ForEach-Object { $_.Line }
```

macOS and Linux:

```bash
grep -E '^(AGENT_LANG|PERSONA_NAME|LLM_BASE_URL|LLM_MODEL)=' "<home>/.env"
```

The personality is the text of `persona.txt`.

## 6. Start the page and hand over the link

`personagent start --no-browser` serves the local page on 127.0.0.1 and prints its link. It then keeps running until it is stopped, so start it in the background with its output in a log file.

Windows PowerShell:

```powershell
$env:AGENT_HOME = "<home>"
$pa = Start-Process cmd -ArgumentList '/c personagent start --no-browser > start.log 2> start-error.log' -WorkingDirectory "<home>" -WindowStyle Hidden -PassThru
$pa.Id
Start-Sleep -Seconds 5
Select-String -Path "<home>\start.log" -Pattern 'http://127\.0\.0\.1:\d+/#token=\S+' | ForEach-Object { $_.Matches.Value }
```

Run these lines as one command. `cmd` writes the log files, so do not add `-RedirectStandardOutput`, `-RedirectStandardError` or `-NoNewWindow` to `Start-Process`: with any of them the page inherits your shell's output, and when your shell reads that output through a pipe, as many agent shells do, your command does not return until the page stops. `AGENT_HOME` does the job of `--home`, so that no path has to be quoted inside the `cmd` line. If `personagent` is not on PATH, put its folder in front of PATH in the same command first, such as `$env:Path = "$env:USERPROFILE\.personagent-venv\Scripts;$env:Path"`, which lasts only as long as this shell. With uvx, the `cmd` line is `'/c uvx personagent start --no-browser > start.log 2> start-error.log'`.

macOS, Linux, or Git Bash on Windows:

```bash
nohup personagent --home "<home>" start --no-browser > "<home>/start.log" 2>&1 < /dev/null &
echo $!
sleep 5
grep -Eo 'http://127\.0\.0\.1:[0-9]+/#token=[^[:space:]]+' "<home>/start.log"
```

Note the process id the second line prints. The log starts with `personagent 1.3.0`, then the link `http://127.0.0.1:<port>/#token=<token>`, then "Keep this window open. Press Ctrl+C to stop." If the log is still empty, wait a few seconds and read it again: the first start after an install takes longer. Nothing costs money until the user verifies a key. Errors go to `start-error.log` on Windows and into `start.log` with bash.

The port is chosen anew at every start; `--port N` fixes one. `SERVER_PORT=8080` in `.env` is not the page's port: it belongs to the character's own service, which the page starts behind it.

To see that the page answers without using the token, request its address without the `#token=` part. It prints 200. Windows PowerShell: `curl.exe -s -o NUL -w "%{http_code}" --noproxy "*" http://127.0.0.1:<port>/`. bash: `curl -s -o /dev/null -w '%{http_code}\n' --noproxy '*' http://127.0.0.1:<port>/`.

While it runs, `personagent --home "<home>" start --no-browser` prints the same link and exits with 0, and "personagent is starting. Try again in a moment." with 1 when the first one has not printed it yet. When none is running, that same command starts a new page in the foreground, so use it only when you know one is running.

Give the user the link and tell them:

1. Open it in a browser on this computer. With no key saved yet, it opens on **Character & settings** [角色与设置]. The service, language, name and personality from step 4 are already filled in.
2. Get an API key from the service's key page in the table in step 1, paste it into the key field and click **Verify & start chatting** [验证并开始聊天]. One small request checks it, and nothing is saved if the service refuses it.
3. Say hello in **Chat** [开始聊天] to check the character. Rewrite the character any time in the **Persona** box [人设] under **Character & settings**.
4. Click **Quit** [退出] to stop it.

**If your background processes do not survive.** Some agent environments end them when a command or the session finishes. Then ask the user to run `personagent --home "<home>" start` in their own terminal. It opens the page in their browser; they keep that window open while they use it.

**On a remote machine over SSH**, the page listens only on that machine's 127.0.0.1. Start it with a fixed port, `personagent --home "<home>" start --no-browser --port 8765`, and have the user open a tunnel from their own computer with `ssh -N -L 8765:127.0.0.1:8765 <user>@<host>`. The same link then works in their local browser.

**If the user prefers not to use the page for the key**, one of these:

- They open `<home>/.env` in an editor, write the key after `LLM_API_KEY=` on the existing line and save it. The key is not tested this way. Check that it is set with step 5. The first chat in the page tests it, and so does `personagent doctor` (paid, so ask first).
- They set an environment variable in their own terminal and run `init` there, so the key never passes through your shell. `init --no-input` keeps the language, name, personality and service already saved. Windows PowerShell:

  ```powershell
  $env:PERSONAGENT_KEY = [Net.NetworkCredential]::new('', (Read-Host 'API key' -AsSecureString)).Password
  personagent --home "<home>" init --no-input --key-env PERSONAGENT_KEY
  Remove-Item Env:PERSONAGENT_KEY
  ```

  macOS and Linux (bash or zsh):

  ```bash
  printf 'API key: '; read -rs PERSONAGENT_KEY; echo; export PERSONAGENT_KEY
  personagent --home "<home>" init --no-input --key-env PERSONAGENT_KEY
  unset PERSONAGENT_KEY
  ```

**To stop what you started**, the user clicks **Quit** in the page, or you end the process with the id you noted. Windows PowerShell: `taskkill /PID <pid> /T /F`, with the id of `cmd` that `$pa.Id` printed. bash: `kill <pid>`. What personagent started ends with it, and the next start stops anything a hard stop left behind. Then delete the log files from the home: `start.log`, and `start-error.log` on Windows. The link in them stops working once the page stops, so nothing is lost.

## 7. Connect chat apps

The user connects apps under **Connect apps** [连接平台] in the page. Your part is to explain what each one needs, never to take the values into the chat.

| On the page | Apps | What the user needs |
|---|---|---|
| Scan to connect | QQ, personal WeChat | Their phone. WeChat bots get one-to-one chats only |
| Paste one or two values | Telegram, Discord, KOOK, Feishu/Lark, DingTalk, Slack, WeCom AI bot, Mattermost, Misskey | Values from the app's console; the page says which. Telegram: a token from @BotFather. Discord: a bot token, with Message Content Intent turned on |
| Advanced | WeCom app, WeChat Official Account, QQ webhook, OneBot v11 (NapCat), Satori | A public address, or other software running on this computer |

personagent connects QQ, WeChat, Telegram and Discord itself. The first time the user connects any other app, it downloads AstrBot and its own Python 3.12 into `<home>/platforms/`, which takes a while, so tell the user to keep the page open until it finishes. Connected apps start again whenever the page or `personagent up` starts. For QQ, the bot shows up in mobile QQ under Contacts → Bots; until QQ certifies it, it can join only groups the user owns.

From the command line, personagent connects only AstrBot:

- An AstrBot the user already runs on this computer: `personagent --home "<home>" connect astrbot "<astrbot folder>"`, where the folder is AstrBot's data folder or the one above it, holding `cmd_config.json`. It copies the plugin, writes one shared token into both sides and keeps existing settings. No group or DM is forwarded until the user lists them under `groups` and `dm_users` in the plugin's settings in AstrBot's WebUI. Then they restart AstrBot or reload its plugins. Add `--qq` to route QQ from AstrBot's OneBot (NapCat) adapter as well.
- AstrBot in Docker cannot reach 127.0.0.1 on this computer. It needs host networking, or an HTTPS address for personagent passed as `--url https://<address>`.
- `personagent --home "<home>" connect astrbot --install` downloads the managed AstrBot without the page. Ask first, because it is a large download. Let the user add apps in the page rather than with `--platform` and `--token`, which put a token on the command line.

The [deployment guide](deploy.md) covers AstrBot, NapCat, Satori, Matrix and public addresses in full.

## 8. Daily use

- **With a browser:** `personagent --home "<home>" start` opens the page and resumes the connected apps. The user keeps its window open; **Quit**, Ctrl+C or closing the window stops everything.
- **Without a browser**, on a server or to keep it running: `personagent --home "<home>" up` starts the character and every connected app. It needs the key: without one it prints "Open personagent start to finish setup first." and exits with 2. Ctrl+C stops it, and each process logs to `<home>/runtime/desktop/`. To run it in the background, use the commands from step 6 with `up` in place of `start --no-browser`, inside the `cmd` line too.
- Run either the page or `up` for one home, never both at once.
- When the home is the default `~/personagent`, the user can leave out `--home`: a bare `personagent` in a terminal opens the page. Anywhere else, every command needs the same `--home "<home>"`.

## 9. Report back

Tell the user, in their language:

- how personagent was installed, and what `personagent --version` printed
- the home folder's path, and the language, name, personality and model service
- whether a key is set (only yes or no) and whether they verified it in the page
- whether the page is running, its link if it is, and how to stop it
- which apps are connected, and what is left for them to do, such as scanning a code
- the command for next time (step 8)
- that the model service charges for every message the character answers
- anything that failed, with the command and its exact output, minus any secret

## Updating

When a newer version is on PyPI, the page and `personagent up` show a notice with the update command for this installation. Quit personagent first, then run the one for the route used:

| Installed with | Update with |
|---|---|
| uv | `uv tool upgrade personagent` |
| pipx | `pipx upgrade personagent` |
| a virtual environment or pip | `<that python> -m pip install -U personagent`, such as `~/.personagent-venv/bin/python -m pip install -U personagent`, or `& "$env:USERPROFILE\.personagent-venv\Scripts\python.exe" -m pip install -U personagent` in Windows PowerShell |
| uvx | `uvx personagent@latest --home "<home>" start`, which runs the newest version |
| a clone | `git pull`, then `pip install -e .` again in its virtual environment |

The home folder carries over: settings, character, what it learned and connected apps.

## Undoing it

1. Stop it: **Quit** in the page, Ctrl+C, or the commands at the end of step 6. Delete the step 6 log files if you made them.
2. Uninstall the package: `uv tool uninstall personagent`, `pipx uninstall personagent`, or delete the virtual environment's folder. For pip into the user's Python, `python -m pip uninstall personagent`. uvx installed nothing.
3. The home folder holds the key, the character, what it learned, the chat apps' credentials and the managed AstrBot. Delete it only after the user confirms, because that cannot be undone. Offer to keep a copy of `persona.txt` first.
4. Remind the user to revoke the API key on the service's key page if they no longer need it, and to remove the bot from their chat apps on those platforms.
5. If you installed uv, pipx or Python for this, say so. Remove them only if the user asks.
