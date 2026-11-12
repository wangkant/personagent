# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.3] — 2026-11-12

personagent is now described as an agent that behaves like a person, on every platform you use, and this release makes it more like one where it shows: replies go out at a typing pace, and what a model wrote as ordinary prose is sent as separate, readable sentences.

### Added

- **Replies on the platforms personagent connects itself arrive at a typing pace.** On Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK, Stoat, QQ and WeChat a reply used to go out as a burst. Each message now follows the time a person takes to type it (six to eight characters a second and a short pause, at most seven seconds), as on QQ through OneBot, and the wait for the model counts toward the first one. Telegram, Discord and Matrix show their typing sign meanwhile, and shortly after a private message or a message addressed to the character arrives. A typing sign that the platform is slow to accept is given up after two seconds, so it delays a message by two seconds at most. A reply to a chat waits for the reply before it. A message the character sends on its own pauses six seconds at most in all and waits five seconds at most behind a reply.
- **The page's chat shows a reply the way it is written.** Three dots stand for the character typing, and the messages of a reply appear one at a time instead of together. What the character sends on its own arrives the same way.

### Changed

- **Sentences a model wrote as ordinary prose are no longer run together.** The default style never sends a Chinese or Japanese full stop, an ellipsis or a long dash. They used to be removed, which joined three sentences into one long message with spaces, glued the words on both sides of an ellipsis together, and left two English clauses with nothing between them. A full stop now ends a message; short sentences still share a line, and a reply gains three messages at most this way. An ellipsis between words becomes a comma in Chinese and Japanese and three dots elsewhere. A long dash between words becomes a comma, one between numbers stays a range, and a single one with no spaces between Chinese, Japanese, Korean or Russian words stays a space. Before a sticker, an emoji or another mark, an ellipsis or a long dash is removed as before.
- **The speaking rules ask for text that is easy to read.** In groups and in private chats the character is told to keep one thought to a line, to use the words people say aloud, to give the answer first with at most one small example when asked to explain something, and to leave out essay connectives such as "first, second, finally" and "in short" in any language. The lines the rules quote as examples are not to be copied or translated word for word.
- **personagent is described as an agent that behaves like a person, on every platform you use.** The README in all ten languages, the cover picture, the package description and the terminal help no longer introduce it as a character for group chats only. The README's opening table now lists what makes it like a person (its character, memory, learning and judgement of when to speak) and then where it works, and the section "Put it in your group" is named "Connect your platforms". No ability changed.

## [1.4.2] — 2026-11-12

The character decides by itself what it learns, and nothing waits for a person any longer; a memory that keeps the thread of each chat across restarts, with dated events and facts it keeps current; the character's abilities after an audit; and `personagent connect <platform>` for servers without a display.

### Added

- **The character decides what reactions cannot settle.** Where a person used to be asked, the character now judges with one model call and records its decision and reason in the ledger: two people's corrections that disagree, two rewrites of the same reply, a reply worth repeating that a person approved, a correction from the person the reply was for that nobody confirmed within `REACT_FIX_WINDOW_S`, and a complaint about an item already in use. It puts the item in use, sets it aside or keeps observing it. It never puts in use a rewrite that the person it concerns refused. Before it decides, rules in the code discard a wording or lesson that carries a link, a mention of everyone, an instruction to the character or an advertising marker. An item is judged again only when the accepted reactions for or against it in its own chat change, and a failed or unusable answer changes nothing. A bystander's complaint about an item a person put in use by hand is recorded and withdraws nothing. Evidence that meets the rule still puts an item in use with no model call. `PROMOTE_JUDGE_ENABLED` (on) turns this off, and `PROMOTE_JUDGE_MODEL`, `PROMOTE_JUDGE_INTERVAL_S` and `PROMOTE_JUDGE_BATCH` set the model and the pace.
- **Items under observation are set aside after a time limit.** An item with no new reaction for `PROMOTE_OBSERVE_MAX_DAYS` (30 days; 0 = never) is set aside, and its record says so.
- **A person can bring back what the character, the time limit or a rule withdrew.** `personagent learned restore <id>`, **Bring back** in **What the character has learned** and the API action `restore` put in use again, after checking for a rewrite already in use, what the character or the time limit set aside and what the character or a rule took out of use. What a person undid or set aside, and what a content rule discarded, stays as it is, and the command says so in a sentence.
- **A memory that outlasts the conversation window.** Every message carries the time it was sent. The recent messages of each chat are kept on disk for 72 hours (`runtime/recent.json`, `MEMORY_KEEP_RECENT`), so a restart keeps the conversation. When older messages leave the window, one model call on the judge model reads that stretch of the chat and updates a running summary of earlier conversation, dated events with the people who took part, and the facts about people and the group: it adds, updates, ends and merges them. Each change is checked on its own, and a fact about a person must come from that person's own words. It replaces the earlier tidy of notes.
- **Recall chooses what to remember.** Each reply receives, within `MEMORY_PROMPT_CHARS` (2,400 characters), the summary and the facts and events that best match the message, weighed by how recent and important they are and how often replies drew on them. A person named in the message is recalled even when quiet. A time such as yesterday or last week, in any of the ten chat languages, brings that time's events first; when nothing is remembered from then, the character is told so and does not invent it. A fact is a person's own only when that person's own lines carry it. What one member says about another is kept as said by that member, never leaves its chat, and never changes, ends or merges into that person's own facts; a group fact that names someone needs that person's own line. Event dates and the day of a plan are taken in the character's time zone. The decision whether to speak sees only the summary.
- **What the character removes can be restored.** What it replaces, merges, ends, removes to make room or rewrites is kept for 30 days (`runtime/memory_trash.jsonl`); an item forgotten on the page or in the terminal, for 24 hours. A forget asked for in chat stays final, and an old message cannot bring it back. After it, or after **Forget this chat**, the daily `.bak` copies are written again and `memory.json.pre-v2` loses what was forgotten. A forget that lands while a consolidation of that chat is running discards that consolidation's answer.
- **Remembers shows everything a chat remembers.** In the Activity view: **Always in mind** with the date it changed and **Restore previous version**, **Earlier in this chat**, **Facts** with whom each is about, **Said by**, when it was first noted and last used, dated **Events**, and **Recently removed** with the date until which each item can be restored. Every item can be forgotten, the forget can be undone, and a line shows how many of today's consolidation calls are used. **Forget this chat** is offered for every chat.
- **`personagent memory`** lists what each chat remembers (`list`, `--chat`, `--json`), what can still be restored (`removed`), forgets an item by id or by a unique start of it (`forget`, and `forget core --chat` for the core note) and restores one (`restore`). It goes through the running service, or edits the files when the service is stopped.
- **Memory settings.** A **Memory** section in **Advanced settings** holds `MEMORY_CALLS_PER_DAY` (40 consolidation calls a day for all chats; 0 turns consolidation off), `MEMORY_TIDY_EVERY`, `CHAT_CONTEXT_MESSAGES`, `MEMORY_PROMPT_CHARS`, `MEMORY_EPISODES_MAX` (120 events per chat) and `MEMORY_KEEP_RECENT`. A chat is consolidated at most 16 times a day, at least 20 minutes apart; failures back off from 10 minutes to 6 hours, and three in a row pause consolidation for an hour. A malformed answer counts as a failure, and its valid changes are still kept.
- **A private chat can follow up on a plan.** When the character remembers a plan for a given day and may speak first in that private chat, it can ask after it once in the three days after.
- **A correction that teaches a fact is remembered.** When an accepted correction teaches a standing fact, such as how someone likes to be called, but carries no better reply, the fact is kept as a remembered fact of that chat.
- **Model use per model and per day.** personagent counts requests, tokens and, where the provider reports it, cost from every model response. The App view shows today and the last 7 days, and `personagent doctor` prints the same (`doctor --json` adds `model_use`). The counts are kept for 8 days in `runtime/model_usage.json`, which is written in the background, so counting never delays a reply.
- **Nicknames in the persona card.** `aliases` in `persona.card.json` lists names that call the character as its name does. Names are matched ignoring case, full-width letters and accents; ñ, ã, õ and й in a message count as letters of their own.
- **`personagent connect <platform>` connects a platform from the terminal.** QQ, WeChat, Telegram, Discord, Matrix, Twitch, IRC, Zulip, VK and Stoat are connected with the same steps, checks and saved form as **Connect apps**, so a server without a display needs no page. `personagent connect` alone lists the ten platforms and which of them are connected. Each value is also an option; `--no-input` asks nothing and exits with code 2, naming any missing value; `--remove` disconnects. QQ and WeChat print their QR code in the terminal, with the personagent window as the fallback, and Twitch prints a link and a code and waits for the approval. `personagent up` then runs personagent with its connected platforms. In `personagent start --terminal`, option 3 offers these platforms and option 5 starts personagent with them.
- **The page's chat shows pictures.** Stickers and pictures the character sends appear in the Chat view and stay in its history. A picture that is no longer stored shows a short note in its place, and the page serves a stored picture only while a message in its chat shows it.
- **The page's chat shows what the character sends later.** The answer to a memory command sent while a reply was on its way, and a message the character starts itself, appear within a few seconds while the Chat view is open, without a reload, and stay in the history. The local page is an outbox connector of its own (`connector_id` `local-welcome`) and receives only the deliveries for its own chat. A message that arrives while the chat is being forgotten is not counted as delivered, and a restarted character service is pulled at once.
- **What a coding assistant says reaches the page's chat.** What is said through `talk`, and a remark after a coding turn, appear in the Chat view marked **via a coding assistant**, also when no page was open at the time. A hook's cue does not appear.
- **`personagent eval --suite memory` measures memory with no model and no key.** Its cases, in English and Chinese, each test one mechanism, from recall, updates and time words to forgetting, restoring, restarts, room boundaries and the call limits. Consolidation answers are written in each case, and the report counts the cases that hold per mechanism: 21 cases per language, all of which hold in this version.
- **Offline checks of addressing and of the eval itself.** `data/evals/address.jsonl` holds lines in all ten chat languages that do or do not call the character, and the tests check each one with no model. The `speak` suite of `personagent eval` adds turns where the admin calls the character and turns in a quiet room where it may start a conversation (80 cases per language), and a `learning` case may omit the accepted retry, so that the character decides alone after the fix window, as in a live chat (25 cases per language).
- **The app window is tested on Linux, macOS and Windows.** A CI workflow installs personagent with the app extra, opens the window, sets the page up and chats inside it with a stand-in model (`tools/window_smoke.py`).

### Changed

- **Nothing the character learns waits for a person.** The Activity view has no **Waiting for you**, **Keep** or **Discard**. **Learned** says how each item came into use: because the reactions agreed, by the character's own decision with its reason, or by a person. **Still under observation** says in one sentence where each item stands and when it will be set aside, with no buttons. The dot on Activity means only that something new came into use since you last looked, and the per-chat count of waiting items is gone.
- **What the character has learned has three tabs**: **In use**, **Observing** and **Set aside**. Each item says who decided it and why: the reactions, the character, a person, the time limit or a rule. The actions are optional: **Put into use now**, **Set aside**, **Undo** and **Bring back**.
- **The terminal says the same.** `/why` and the trace in `personagent chat` show how many agreeing reactions an item has of how many it needs, that the character is deciding it, or that it looked and keeps observing, with its reason; the state `proposed` reads `observing`. `personagent learned` lists the items under observation by default, with the date each will be set aside, says for decided items who decided and why, and `show` prints the character's record and the judge and model of each step. The character's own answer to "what have you learned" counts items under its own review and says "decided by me" or "put in use by hand", in all ten chat languages. Nothing is described as left for the admin.
- **`PROMOTE_AUTO_ENABLED=false` stops new learning altogether.** Nothing new is put in use, neither through reactions nor by the character's decisions; what is in use stays. With `PROMOTE_MIN_SPEAKERS=2` an item the second person has not yet confirmed stays under observation.
- **Forget this chat forgets everything that chat remembers**: its facts, events, summary, core note, recent messages and the removed items that could still have been restored. It no longer deletes notes about you that other chats keep, and the confirmation says so.
- **In a group, "what do you remember" lists only that group's notes**, even with `MEMORY_SHARE_ROOMS` on, followed by up to three dated events the caller took part in. A forget in chat also removes matching events, sentences of the summary and recent messages.
- **`CHAT_CONTEXT_MESSAGES` and `MEMORY_TIDY_EVERY` keep their names with a new meaning.** The first is the number of recent messages kept per chat for replies and consolidation; a reply reads at most the last 60, or 30 when called. The second is the number of notes written in replies that also starts a consolidation, and 0 turns off every memory model call.
- **Memory files migrate on the first start.** Notes gain an id, an importance and a use count. The old file is kept as `memory.json.pre-v2`, and `memory.json`, `core_memory.json` and `episodes.json` are copied to `.bak` once a day. A damaged one stops `personagent run` and `up` with one sentence naming the copy to put in its place, instead of a traceback. An earlier version still reads the migrated `memory.json` and ignores the new files.
- **The core note is shown as 常驻记忆 in Chinese** (常駐記憶 in Traditional Chinese), and the French, Korean, Portuguese and Russian names say "always present".
- **A model failure in the page's chat is reported in words** with **Send again**, where the character used to answer with an in-character excuse.
- **The health check probes each model where the agent sends that work.** **Group chat replies** probes `LLM_MODEL`. The new **Web search decision** row probes the judge model and fails when it does not call the search tool, because search would then never run. The new **Reaction judge** row probes `REACT_MODEL` and is skipped while `REACT_LEARN_ENABLED` is off, and **Self-review model** follows `EVAL_ENABLED` and the resolved `EVAL_MODEL`.
- **Activity explains every outcome of a turn** in the page's language: the model did not answer; the reply was held back by a safety check; the reply could not be delivered; the character considered starting a conversation and decided against it; the message was answered in the same reply as another. An unknown reason reads "for another reason".
- **Several callers are answered together.** When several people call the character within one short wait, one reply answers them all and mentions the latest caller. When that reply is not sent, Activity shows a line with the reason for each caller.
- **The admin calling the character in a group is answered as a call**, and a long message that calls it reaches the model whole, up to 1,000 characters.
- **A picture that is slow to read keeps its place.** In a group the reply waits for its caption, up to 20 seconds when nothing else is running, and answers the picture and the text after it in one turn and one model call. In a private chat, a picture the character cannot see is named as unseen, so it asks instead of describing it.
- **Voice, files, videos and forwarded messages reach the model as what they are**, with a voice message's transcript where the platform gives one, and mentions carry the person's name. A mentioned person's name and the words of a forwarded message are marked as not the sender's own, so they call no one and run no memory command; a mention of the bot inside a forward on Discord or Telegram is not a call. The persona card's `reply_style` now reaches the prompt: `"emoji": true` allows emoji as the character uses them, and a `max_chars` below 800 is stated as a length limit.
- **The web search decision reads the three lines before the message**, so "what do you think of it?" is looked up for what "it" is. Whether the decision is made still depends on the message alone, so the cost is unchanged.
- **Stickers are collected on every platform.** Pictures posted in groups that arrive inline or marked as stickers, on the directly connected platforms and through connectors, enter the sticker library as on QQ. A photo a connector sends only as a link does not.
- **Learning from reactions is stricter about whom a reaction concerns.** An @ with no quote is matched to the sender's own latest reply first. The reaction judge writes its follow-up question in the chat's language, and a question in another language is not sent. A person's complaints about replies to themselves no longer block them from teaching.
- **A connector that pulls the outbox keeps its conversations.** An event from a connector without the outbox capability no longer replaces the route that a different connector with it holds for the same conversation. A pulling connector, the local page among them, therefore keeps reaching a conversation after another program, such as a coding assistant, has spoken there, and the character's own messages keep reaching the page. An event from the same connector, or from any connector with the outbox, replaces the route as before.
- **For connectors and scripts.** A group message more than 10 minutes old when it arrives, within two minutes of its platform's first message since the start, is kept as context and not answered; later, a connector whose clock runs behind is still answered. A mention of the bot after a `forward` segment is not a call. New segments `media` (voice, video, file, an unfetched photo or a sticker) and `forward`, and `name` on `mention`, are read; see the connector protocol. An item of a DM response may carry `"reason": "excuse"`, which marks the short message sent when the model failed. In the Activity API, `pending` is now `observing` in `GET conversation` and in each chat of `GET conversations`, which also gains `latest`; each item carries `standing` or `by` and `why`; `restore` is a new candidate action, and `promote` no longer brings back a rolled-back item. New memory routes are `memory/restore`, `memory/forget_chat` and `memory/list`, and `memory/forget` takes `kind` and `id` and returns the `tid` to restore. The page's own `/api/activity/decide` accepts only `rollback`. The ledger gains a `review` row and `judge` and `model` fields on lifecycle rows; an earlier version moves a `review` row aside as an unknown row kind and keeps working.
- **The Twitch tile on Connect apps says "Channels only"**, where it said "Groups and DMs". The character chats only in the listed channels; Twitch whispers are not supported.
- **One formal register in every language.** The documents and the terminal text in all ten languages use formal written language and the names the app shows. The German terminal chat says "Auf Wiedersehen." on exit.
- **The log no longer holds the text of notes the character saves from its replies.** It names the chat and the length.
- **The terminal setup names the platforms personagent connects itself** and points to `personagent connect <platform>`; its AstrBot step covers the other platforms.

### Fixed

- **A main model that hangs no longer costs the turn.** When it times out or the connection drops and `LLM_FALLBACK_MODEL` names a different model, the call moves to the fallback at once and the turn is answered within its time budget. An error a provider returns inside a normal response, such as OpenRouter's upstream failures, is handled like the matching HTTP error instead of becoming a silent blank reply. The busy warning no longer claims a switch to a fallback that is the same model.
- **A note for the character's own memory never reaches the chat.** A `[CORE_UPDATE]` block the model left unclosed, or put in the middle of a reply, is no longer sent.
- **Only a bare PASS is silence.** A reply that merely contains the word is sent. A called turn whose draft a guard refused is written once more, and so is a private reply the character declined, at most once per reader in a while, instead of leaving the person without an answer.
- **A burst of private messages is one turn**, and what someone wrote during an outage is still answered. A bystander's "lol" no longer ends a follow-up, and openers stop going into a room that never answered them.
- **Guards in all ten languages.** The checks against naming its own model or maker, leaked reasoning and assistant phrases read every chat language, and the first lets star signs, words that merely contain a maker's name and sentences about another product through. Long replies are split at the end of a sentence but not after a title or a date's ordinal, a numbered list loses its numbers only when it counts from 1, a single numbered line keeps its number, and lorebook keywords in Latin and Cyrillic scripts match whole words only.
- **A malformed self-score is ignored** instead of being stored as 0 or 9, and the self-improvement loop drafts fixes only where the person the reply was for also objected, so that the character can decide them.
- **A rejection rolls back only what was learned in its own chat.** The person a reply was for rejecting it in one chat no longer takes an item learned in another chat out of use.
- **A name no longer calls the character from inside a longer word** in Japanese katakana or in the middle of a Korean word.
- **A damaged `owner_profile.json` no longer stops replies**; the default sticker rate is used and the log warns once.
- **The model's refusal to read images has its own sentence** on the image settings, where the page used to show a general error.
- **The page and the terminal after review.** The page's pull loop survives settings it cannot read, a silent connector's route is not revived, the chat keeps as many messages as the server keeps and frees pictures, Activity lists the page's chat once with what was said, and nothing is cut off in the smallest window in any language. In the terminal, the QR code falls back to plain characters, `--no-input` never waits for a scan, unknown languages and bad input are refused in a sentence, and `doctor` lists the directly connected platforms.
- **On Linux the app window no longer prints a GTK traceback at start.** Where the app extra installed Qt and GTK is absent, the window asks for Qt by name.

## [1.4.1] — 2026-11-11

### Licence

- **personagent is now licensed for noncommercial use only**, under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0). The connectors under `integrations/` (the AstrBot plugin, the connector SDK, and the separate Matrix and Satori connectors) stay under the MIT License, and the portraits stay under CC BY-NC-SA 4.0. The platforms personagent connects directly, Matrix among them, are part of the noncommercial core. Versions 1.4.0 and earlier were released under the MIT License and remain so.

### Added

- **personagent opens in a window of its own.** On Windows `personagent` shows the local page in an app window (WebView2 through [pywebview](https://pywebview.flowrl.com/)) with its own taskbar icon, where it used to open a browser tab. Closing the window stops personagent, and asks first while an app is connected. Starting it a second time brings the window back. On macOS and Linux the page still opens in the browser; `pip install "personagent[app]"` gives it the window there too, with Qt on Linux. `--browser` keeps the browser, and where no window can open the page falls back to it. In the window, right-click works where there is text to paste into or to copy, and nowhere else.
- **`personagent shortcut`** puts an icon on the Windows desktop and in the Start menu that opens the window with no terminal behind it; `--remove` takes it away. `start.bat` makes the icon the first time it runs, then opens the window and closes its console. Started this way, personagent writes what it would print to `runtime/desktop/app.log` and says a refusal in a dialog.
- **Six more platforms, connected directly.** Matrix, Twitch, IRC (Libera.Chat, OFTC and other networks), Zulip, VK and Stoat (formerly Revolt) run in the same direct process as QQ, WeChat, Telegram and Discord, with no AstrBot. **Connect apps** shows numbered steps for each. A Matrix bot reads only unencrypted rooms and accepts invitations only from its admin's Matrix ID. Twitch signs in through a link the page shows, chats in text only in the listed channels and has no whispers. IRC joins only the listed channels. None of the six has yet been tested against the live service.
- **Two new views on the local page.** **Practice** plays the scripted demo in the page and runs a practice group, the page's version of `personagent chat`, where you write as the admin or as made-up members and see why the character replied or stayed silent. **App** holds the health check, running in the background, updates, and the data on this computer. Both open before a model is set up.
- **A health check on the page.** **Run check** in the App view tests every service the character relies on, through the running character or a separate `doctor` run. The view also says why the character, AstrBot or the platform connection failed to start, lists settings to review, renames settings retired in 1.0 as `doctor --fix` does, and shows each log with keys and tokens hidden. The App view has a red dot when something needs attention.
- **personagent can keep running with its window closed** (Windows). With **Keep running after the window is closed** on, closing the window moves personagent to an icon in the notification area, from which it opens again or quits, and the character keeps answering. `personagent start --background` starts it behind the icon.
- **Updates from inside the app.** **Check for updates** asks PyPI at once, and **Update and reopen** quits personagent, runs the update for this installation (pip, uv, pipx, or `git pull --ff-only` in a clone) and opens it again; a failed update reopens the previous version with its log. A source ZIP, uvx, a missing tool and a clone with local changes get the command or the release page instead.
- **Your data in the App view.** It adds and removes the desktop and Start-menu icon, starts personagent when you sign in to Windows (behind its icon when it runs in the background), and opens the personagent folder, the persona, the logs, memory, stickers and `data/`. **Back up now** saves everything, keys included, as one zip file; **Restore** replaces the current data with a backup's. **Clear memory** and **Reset all** start over. Each of these saves a backup first.
- **Advanced settings** under **Character & settings**: the admin and access lists, speaking and reply style, backup and secondary models, learning, and the remaining timings and limits that were available only in `.env`. **Save** writes only what changed and restarts the character.
- **What the character has learned**, in Activity, lists everything it learned in every chat, with the full record of each item, and lets you keep, undo, restore or discard items while the character is not running.
- **Coding assistants on the page.** **Connect apps** connects and removes Claude Code, Codex and DeepSeek Harness, turns end-of-turn remarks on and off and sets their interval. **Use an existing AstrBot** installs the plugin in an AstrBot you run and saves who it replies to.
- **Forget this chat and the memory commands on the Chat view.** **Forget this chat** deletes what the character noted in the page's chat and starts a new one. **Memory commands** inserts a command into the message box.

### Changed

- **Every button on the local page shows that it was pressed**: it moves a pixel and darkens while the pointer is down, where only hovering used to show.
- **Disconnecting an app asks in the page's own dialog**, where the browser's one named `127.0.0.1` in its title. Esc and Cancel keep the app connected.
- **The name at the top left of the local page goes to the chat.** It was a link that led nowhere.
- **A turn has one time budget.** A reply gets 1.5 × `LLM_TIMEOUT_S` in all, in a group, in a DM and when the character speaks first, where it used to get the timeout again for every retry and every model. A connector should allow 3 × `LLM_TIMEOUT_S` for a request, since a message first waits for the turn that was thinking when it arrived; the defaults (420 s against 360 s) already do. `LLM_MAX_RETRIES` no longer enters that sum.
- **DMs sent while a reply is on the way are answered together.** Someone who sends three more messages while the model is thinking gets one reply to all three, as a group already did, where each used to queue a reply of its own.
- **A memory command sent while a reply is on the way is answered after it** without holding its request open: through the outbox as `follow_up` where the connector pulls one, and otherwise in a response of the same conversation.
- **The Activity API sends what the page shows.** `GET /api/dashboard/conversation` no longer carries the checklists, history, full evidence, past proposals and totals that `personagent learned` prints; on a busy chat that is 0.7 ms and 30 KB in place of 4.3 ms and 197 KB, every 8 seconds. `GET /api/dashboard/status`, which nothing read, is removed.
- **The README has a product cover.** The wordmark and two real screens of the local page replace the hand-drawn scene, and the feature table reads as two plain columns.
- **A shorter README.** The measured results and the comparison with other projects are no longer on it, and the cost notes moved into Start here. The results stay in `docs/evals/2026-10-18`, and the user guide covers `personagent eval`.
- **`start.ps1` finds Python through `py -3`** and names a Python older than 3.10, or a `.venv` whose Python is gone, where it used to fail inside pip.
- **`init` flags typed at a terminal carry into the questions.** `--provider`, `--model`, `--name` and the rest answer their question; only `--lang` used to.
- **The local page's chat is the admin's.** The character treats whoever chats on the page as its admin, without an entry in `ADMIN_IDS`. A coding assistant connected through `talk` uses the same chat, so it speaks as the admin too.
- **The page's text is written in a formal register** in all ten languages. In the Chinese page, 账本 is now 学习记录.

### Fixed

- **A stuck model no longer blocks everyone.** While one group waited for a reply, each later message of that group held one of the 64 request slots until the model answered, so one busy group and a hanging model could turn every chat's requests into 429s. Messages that arrive during a turn are now set aside at once and enter the chat behind the reply, in the order they came. The same holds for DMs, for memory commands and for the character's own openers, which used to hold a conversation's lock for as long as the model took.
- **The follow-up question after a complaint waits for the reply in flight.** In a group it could land in the middle of a turn, ahead of a reply that had not seen it.
- **A connector conversation is not forgotten while the character's opener for it is being written.** With more than 256 connector conversations open, the room could be dropped mid-turn.
- **A power cut no longer keeps the service from starting.** `pending_reactions.json` and `connector_handles.json` are written without waiting for the disk; a cut-off copy of the first stopped the start, and of the second failed every turn after the model was paid. A damaged one is now moved aside as `<name>.corrupt` and the store starts empty. Every other state file still stops with an error.
- **The first AstrBot download can be cancelled**, and stops when the page quits; a half-made environment is removed so the next attempt starts clean. On Linux and macOS a download left running by a killed app is stopped at the next start or the next install.
- **A new image is downloaded once**, not once for the caption and again for the sticker library.
- **One directly connected platform that cannot load no longer stops the others.** It is skipped and marked as failed, and the rest start.
- **Saving `.env` no longer fails on Windows while the page reads it.** Replacing the file raised `PermissionError` when it was open for an instant, which could stop a start before the character spawned; the write now waits and tries again.
- **Self-evaluation, vision and the health probes turn hidden reasoning off** the way replies do, so they no longer pay for it on DeepSeek, Zhipu and Moonshot. An endpoint that rejects the switch is asked once, not on every image.

## [1.4.0] — 2026-11-10

Three characters the community already draws, with animated portraits; the character inside your coding agent; memory that stays current and can be forgotten; the local page, the terminal and the guides in ten languages; and a calmer local page.

### Added

- **The character in your coding agent.** `personagent connect claude-code`, `personagent connect codex` and `personagent connect dsh` (DeepSeek Harness) register a new MCP server, `personagent mcp`, with a `talk` tool in the same one-to-one chat and memory as the local page and a free `character` tool. It uses the open page or a running `personagent up`, and otherwise starts the page for that session. On Claude Code and Codex, `--react` adds a Stop hook that lets the character say a line when a turn ends (`CODING_REACT_COOLDOWN_S`, 30 minutes by default); `--remove` undoes it all.
- **Notes stay current.** After 8 new notes of its own in a chat (`MEMORY_TIDY_EVERY`, 0 turns it off), one call to the gate model merges repeats and drops what a newer note replaced or what time has ended. Only the notes it wrote itself change; notes people saved stay as they are and count as evidence.
- **A group's notes about someone follow them into their DM**, for replies, recall and forgetting. Nothing goes the other way: a DM stays in that DM.
- **Share memory between groups**, a switch under **More features** (`MEMORY_SHARE_ROOMS`, off by default). What one group noted about someone also comes up in other groups they talk in. DMs and notes about a whole group stay where they are.
- **Memory on the local page.** Activity shows the core note and who each note is about, and **Forget** deletes either.

- **Ten languages in the terminal.** `init --terminal`, `chat`, `demo`, every `--help` and `doctor` run in English, Simplified and Traditional Chinese, Japanese, Korean, Spanish, French, German, Brazilian Portuguese and Russian, and `--lang` and `AGENT_LANG` take all ten codes. Each language has its own starter personas and default name. Saving the local page writes the page's language to `AGENT_LANG`, and the first setup follows the system language.
- **Three characters the community already draws.** The DeepSeek whale girl, the GPT dragon girl and the Claude lady (`deepseek`, `chatgpt`, `claude`) in every setup path and all ten languages. On the local page each has a portrait that blinks, glances up while a reply is on the way and talks when it arrives, and holds still under reduced motion. Picking one without naming it names the character after it, and `PERSONA_AVATAR` keeps the portrait after the persona is edited. The portraits are CC BY-NC-SA 4.0, with credits in `persona_agent/static/characters/LICENSE.md`.
- **The documentation in ten languages.** The getting-started guide, user guide, deployment guide, connector protocol, tools page and disclaimer follow the README.

### Changed

- **Longer DM history stays in the prompt cache.** The clock, memory and examples now close the last turn, after the history, and the output protocol joins the cached system prompt. Old turns drop in a batch, from 60 messages to 40, not one pair a turn. Mean input grows about 3%, so a provider without caching costs slightly more.
- **Replies no longer use hidden thinking.** Group and DM replies now turn it off, as the gate already did, because the protocol carries its own `reasoning` field. An endpoint that insists on reasoning keeps its minimum.

- **A new setup starts on OpenRouter's free models.** OpenRouter is the first preset, with `openrouter/free`, so the only thing to get is a free key. The limit is 50 requests a day, and the local page says so under the service. A home that already names a service keeps it, and a `.env` with only a key still means DeepSeek. On a new home, `init --no-input` with a key from `--key-env` or the shell's `LLM_API_KEY` now needs `--provider` or `--base-url`, so an existing script cannot send its key to the wrong company. A 429 now logs the provider's reason, and the page says when a service is out of requests.

- **Less defensive code.** Guards for states the code itself never produces are gone: type checks on its own files and values, catch-alls around its own calls, misuse warnings. A corrupt state file (`connector_handles.json`, `stickers.json`, the direct-app credentials and others) now stops with an error instead of reading as empty. Network and model failures, the auth and SSRF checks and the handling of what chat users send are unchanged. Comments and docs lost their hedging.
- **A calmer local page.** No boxed cards: fields are a light fill with a line under them, secondary actions are text, one accent marks where you are, and the lightest text now meets 4.5:1.
- **A lighter install.** The README's illustrations no longer ship in the wheel, and Pillow 13 and websockets 17 are accepted.
- **Quicker to open.** The browser opens as soon as the page listens, not 0.8 s later; `--help` reads `.env` once, not once per sentence; the local page no longer re-reads every shipped character on each poll.

### Fixed

- **A planted instruction is refused in every language.** The check on what a memory command saves read only English and Chinese, so "always answer X" in the other eight languages was saved.
- **Talking about a model is no longer taken for claiming to be one.** The vendor check read a model id's tail on into the Chinese after it, so "作为DeepSeek的老用户…" was dropped. A rival or a fan ("我是DeepSeek的老对手", "I'm DeepSeek's biggest fan") now passes, and a character named after a vendor may say its own name; a version, a maker or a real engine said with that name still drops the reply.
- **Memory commands work in a real DM.** They reached only group chats and the terminal trial; a DM sent them to the model as ordinary chat.
- **`forget` reached only the notes.** The same fact stayed in the core note and kept reaching every prompt. Matching sentences are now cut from it too.
- **The model could not tell how old a note was**, so "has an exam tomorrow" read as current for months. Each note now carries its age, and notes are asked to give dates rather than "tomorrow".
- **Activity listed who a note was about under "who added it".**
- **A reply could send the same sticker twice.** The once-per-reply check looked stickers up by file name, but they are keyed by path, so it never matched.
- **A failing model is skipped by every call.** The cooldown after a failure applied only to group replies, so a DM, the gate and the other calls sat through the retries on every turn.
- **One failed vision call no longer blinds an image.** What OCR read during the outage was cached in the caption's place.
- **A sticker has to match.** A new, much-used sticker could clear the bar for any tag, so a comforting reply could send a teasing one.
- **Saving settings no longer replaces an old template persona** with the warm listener on a home set up by an earlier release.
- **On Windows, a script that gives no input is not a terminal.** `personagent` with its input closed opened the page and waited, and `init` asked its questions and dropped the flags.
- **Retry on a failed message no longer loses it** when another reply is on its way.
- **A long message says it is too long.** The page accepts the 8000 characters the chat does, in any script, and names the problem past that.
- **The page no longer flashes the Chinese setup form** before it shows the right view.
- **`--port` on a port in use says so** in one line. The update notice of `start` and `up` is translated, and a language outside the ten no longer breaks the line said when the model fails.

## [1.3.1] — 2026-10-26

The local page, the README and the memory commands in ten languages, and a character that answers in the language its chat uses.

### Added

- **Setup by a coding agent.** `docs/setup-for-agents.md` tells an AI coding agent how to install and set up personagent: what to ask the user, the install routes, `init --no-input`, starting the local page in the background and handing over its link, connecting apps, updating and undoing. The model key never passes through the agent: the user enters it in the page. The README has a prompt to paste, and a test checks that every command in the file parses.
- **The local page in eight more languages.** The menu at the top right now offers 繁體中文, 日本語, 한국어, Español, Français, Deutsch, Português (Brasil) and Русский besides English and 简体中文, and the browser remembers the choice; with none saved, the page follows the browser's language. Each is a translation file the page loads when chosen, and a string it lacks shows in English. The page's language and the character's are now separate: saving the settings writes `AGENT_LANG=zh` for either Chinese and `en` for English, and any other page language keeps the character's language as it was. The prompts and bundled data stay English and Chinese.
- **The README in the same eight languages**, under `docs/readme/`, with a language bar at the top of every version. English stays the reference; the translations may lag behind it.
- **Memory commands in the same ten languages.** `Nova, recuerda que...`, `ノヴァ、覚えて：...`, `Нова, запомни...` and the rest work like the English and Chinese ones, and so do forget, recall and "what have you learned". Japanese and Korean also take the verb last (`...って覚えといて`, `...다고 기억해 둬`). Each language reads its own questions, reminiscing and never-mind lines as chat. The reply, the learned summary and the line sent when a model call fails come in the language the message was written in, told by its script and, for Latin-script languages, by common words. Only the word for forgetting deletes a note: words for deleting, which chat uses for messages and lights, don't count. Each language is one module in `persona_agent/chatlangs/` with its own test cases.

### Fixed

- **Retrieval read nothing in Japanese, Korean or Russian.** With `AGENT_LANG=en` only ASCII words were search terms, so notes and examples in those chats ranked by age alone, and an accented word broke apart ("café" searched as "caf"). Words in every spaced script now count whole, and Han, katakana and Hangul runs give two-letter terms whatever the agent's language. English and Chinese text gives the same terms as before.
- **`Nova, remember!` no longer keeps a note made of punctuation.** It asks what to remember, in every language.
- **Chinese never-mind lines in Traditional characters** (`小夏 忘掉這個`) and "forgot to" lines (`小夏 忘了说，我明天不在`) are chat, not a forget that could delete notes. `帮我记一下：...` is now read as a note.

### Changed

- **The character answers in the chat's language.** The group and one-on-one style guides now say to talk in the language the group, or the other person, is using, since the guides are English and a persona may be English or Chinese and neither should decide it. A Chinese or English chat reads as before. Names attached to particles (「ノヴァちゃん」, 「Nova야」) were already recognised as calls, and the reply checks already let Japanese, Korean, Cyrillic and accented Latin through.

## [1.3.0] — 2026-10-18

A correction now teaches what it meant, not just a better wording; the local page shows what the character did and learned; and the eval measures it against a real baseline, with repeats and intervals.

### Added

- **Activity in the local page.** A new view between Chat and Connect apps lists every chat the character is in and, for the one you pick, what waits for your decision (Keep or Discard), what it learned (Undo), what it remembers, and what it recently said or let pass, with the reason. A dot on the sidebar marks a chat with something waiting. Decisions go into the same append-only ledger as `personagent learned`, with the reason `local page`.
- **A correction now teaches its lesson, not just a better wording.** What gets promoted is the character's retry, and its retrieval framing ("learn the voice in [OK]") taught tone, so a later message on the same subject came out without the fact: in the eval, 2 of 58 replies after a promotion used what the group had taught, and with this change 52 of 77 do. When a correction teaches something that holds beyond one reply (what the group calls a place or a person, a fact about someone), the reaction judge now also writes it as one sentence. Only an accepted correction from the person the reply was for, or from the admin, keeps one, and it must pass the same filter as core memory, so it cannot carry markup, instructions or trigger rules. The sentence travels with the retry that promotes. Once promoted, it goes into every later prompt in that chat as a `<taught_here>` block of quoted data, whatever the turn is about, and a rollback takes it out. The Activity view shows it under **From now on**, and `personagent learned show` prints it.
- **`personagent eval --repeat N`** runs every case N times, each in a fresh deployment. The 95% intervals count each case once, so repeats show how much a result moves between tries without inflating the sample, and every block reports how many cases went the same way on every try. Reports record the personagent version and which version of each dataset they measured.
- **`personagent eval --rejudge REPORT`** judges a kept report's replies again with the judge you set now, without calling the model under test.

### Fixed

- **A garbled verdict no longer loses the reaction.** A model now and then garbles a key of the reaction judge's JSON (`"reaction correction"`). That reaction used to be dropped without a word, which in one eval run lost a quarter of the corrections. The judge is now asked once more, and the log says when its answer could not be used.

### Changed

- **The reaction judge takes a group's word for its own names.** It is told, from user ids rather than display names, whether the person reacting is the one the reply was for. When that person corrects the bot about themselves, or about what the group calls a place, an event or a thing, the judge accepts the correction even when it is said with a laugh, unless it demeans someone, asks for something harmful, or contradicts the context. A claim about someone else still has to be self-evidently right. A person suggesting a line in ordinary chat ("say it like X") now reads as a correction, not as an attempt to steer the review; text aimed at the review itself still does. The judge's events are stamped `reaction-adjudicator/3`.
- **The persona suite compares against a real baseline.** The other reply now comes from the same model given the character text as its whole system prompt, rather than from a plain assistant that any character beats. The judge sees each pair twice with the replies swapped. A reply wins when both picks agree, and a split counts half. The 1–5 rubric is gone: the last judge gave every reply full marks.
- **The eval cases are larger and harder.** `speak` grows from 24 to 60 moments per language, with ten per language where the name means something else. `persona` grows from 18 to 40. `learning` grows from 10 to 20, adding seven group conventions the model cannot guess and three more cases that must be held.
- **The README's Measured section is a short summary of the 2026-10-18 run**: two models, three tries per case, Claude Opus 5.5 as judge. The full results, with intervals, the misses by kind, the method and every report, are in `docs/evals/2026-10-18`, including the first learning run from before corrections kept their lesson.
- **The agent service no longer serves a dashboard page.** Its startup banner and `personagent doctor` print no dashboard link, and there is no sign-in link or cookie any more; `GET /` on the service answers a short note pointing to the local page and to `personagent learned`. The JSON API under `/api/dashboard/` stays, for the local page and for scripts, and takes only the `X-Personagent-Dashboard-Token` header. The promotion checklist, evidence and history the page showed are in `personagent learned show`.
- **The docs read more plainly and match this release,** with new screenshots of Connect apps and Activity.

### Removed

- The dashboard page's files (`persona_agent/static/index.html`, `app.js`, `app.css`) and `tools/dashboard_snapshot.py`, which only captured that page.
- `personagent eval --seed`: with both orders judged, there is no order left to seed.
- The 2026-10-03 eval reports, made with the smaller cases and the plain-assistant baseline. They stay in the git history.

## [1.2.2] — 2026-10-17

personagent says when a newer version is out, and the repository keeps only what a user opens at its root.

### Added

- **personagent says when a newer version is out.** The local page and `personagent up` ask pypi.org at most once a day, in the background, and an hour later after a failed attempt; `personagent doctor` asks then and there when the last answer is a day old. The Chat view then shows a notice with the command for how this copy was installed (pip, uv's venvs, uvx, uv tool, pipx, or `git pull` plus a reinstall in a clone), with a link to the release notes; closing it hides it until the next start, and the sidebar keeps a link to bring it back. The terminal prints the same line. The request carries only personagent's version number, and `UPDATE_CHECK_ENABLED=false` turns the check off.

### Changed

- **The repository root holds only what a user opens.** `CONTRIBUTING.md` and `SECURITY.md` moved to `.github/` (GitHub still shows them), and the disclaimers to `docs/`. The build uses hatchling, with the dependencies and the pytest settings in `pyproject.toml`; `requirements.txt`, `setup.py`, `MANIFEST.in` and `pytest.ini` are gone, and the wheel ships the same files as before.
- **`start.bat` installs with `pip install -e .`**, and again whenever the dependency list in `pyproject.toml` changes, so a pull that adds a dependency installs it; when that fails after an earlier install worked, it warns and starts with what is installed. With arguments, or without a console, it runs `personagent run` with them (`--host`, `--port`, `--home`).

### Removed

- `quickstart.py`: in a clone, make a venv and run `python -m pip install -e .` and `python -m persona_agent` in it (or double-click `start.bat` on Windows); `pip install -e .` also replaces `pip install -r requirements.txt`. `python -m persona_agent init` takes `--terminal`, `--no-input` and the setup flags, and `connect astrbot DATA_DIR` the AstrBot ones.
- `main.py`: `personagent run`, or `python -m persona_agent run` in a clone.
- `start.sh`: install with pip or uv, or use a venv in a clone as above.
- `launch.vbs`, deprecated since 1.0, which 1.0 said would keep working through 1.x: it only opened `start.bat`, so double-click that instead.

## [1.2.1] — 2026-10-17

The AstrBot plugin comes as a zip on each GitHub Release instead of from a repository of its own, and the README is shorter.

### Changed

- **The AstrBot plugin no longer has a repository of its own.** It ships inside personagent as before, where `personagent connect astrbot` and the managed AstrBot install it from, and each GitHub Release now carries `astrbot_plugin_personagent.zip` for AstrBot's **Install from File**. Its `metadata.yaml` drops the `repo` link, so AstrBot's update button no longer points at the removed repository; to update, rerun `connect astrbot` or upload the newer zip (AstrBot 4.29 and later replace the installed copy; on older versions, uninstall it first). An AstrBot on another machine also needs `personagent_url` set to an HTTPS address for personagent, as before.

## [1.2.0] — 2026-10-15

The local page turns on web search, image understanding and speaking first, points a new user to connecting an app, and no value saved to `.env` can reach past its own line or name another setting.

### Added

- **The page turns on the optional features.** A **More features** card in settings turns on Tavily search (DuckDuckGo stays the free default), image understanding (with the chat service's key or another endpoint) and speaking first on chosen apps. A blank key keeps the saved one, a key is never sent to an address it was not saved for, none is returned to the page, and saving restarts a running agent.
- **A getting-started bar** in the Chat view points a new user to connecting an app until one is connected, and can be closed.

### Security

- **A value saved to `.env` can no longer write a line of its own.** A name or key holding U+2028, a vertical tab or another line break other than `\n` was written bare and later split into a new line, which could set `LLM_BASE_URL` and send the saved key elsewhere. Such values are quoted now, `.env` is split into lines the way dotenv splits it, and a `#` after any whitespace is quoted too.
- **The page refuses `${...}` in what it saves.** dotenv expands it, even inside quotes, so `${LLM_API_KEY}` typed as a vision key or a name would have become the chat key.

## [1.1.0] — 2026-10-15

personagent 1.1 lives in a local page and joins chats on its own: add one model key in the browser, chat with the character there, and connect it from the same page. QQ, WeChat, Telegram and Discord are connected by personagent itself; the other platforms go through an AstrBot that it installs and runs with no dashboard of its own.

### Added

- `personagent`, `start` and interactive `init` open a local browser page: add one model key, verify it and chat with the real character. Defaults cover the provider, model and persona; optional settings stay collapsed. Existing configuration and edited personas are kept.
- Chat platforms connect from the page's **Connect apps** screen. Personal WeChat and QQ take a phone scan (QQ can also take an AppID and AppSecret); Telegram, Discord, KOOK, Feishu, DingTalk, Slack, WeCom AI bot, Mattermost and Misskey take one or two values copied from the platform's console, and Slack's link opens a pre-filled app with Socket Mode, scopes and events already set; WeCom apps, WeChat Official Accounts, QQ webhooks, OneBot (NapCat) and Satori sit under Advanced. The first platform that goes through AstrBot downloads it and its isolated runtime and installs the plugin. Each connection starts from AstrBot's own defaults for that adapter, opens only that platform's groups and DMs to the character, and is rolled back if AstrBot logs that the platform refused it within a few seconds of starting. Connected apps can be set up again or disconnected from the same screen. QQ needs no NapCat; group ownership and message permissions stay with the user. LINE is not offered, because AstrBot always routes its callbacks through the dashboard.
- QQ official bots, personal WeChat, Telegram and Discord are connected by personagent itself (`persona_agent.direct`), with no AstrBot download: QQ through its documented API v2 WebSocket gateway, connected by a scan in mobile QQ that creates a bot or picks one already made (following Tencent's MIT-licensed bot SDK, the bot's secret comes back sealed with a key only personagent holds), WeChat through Tencent's iLink bot API as described in Tencent's MIT-licensed openclaw-weixin protocol notes, Telegram through long-polled `getUpdates`, and Discord through Gateway v10 with the Message Content intent. The credentials are checked before anything is saved, so a wrong token, a wrong QQ AppSecret or a Discord bot without Message Content Intent gets its own message, and an unreachable platform is reported as a network problem. They run in one `direct` process beside the agent, report per-platform state for the page, and use the connector protocol like every other connector; a platform previously connected through AstrBot is handed over rather than polled twice. QQ replies are passive while QQ allows them and active after that; WeChat keeps each person's context token on disk so replies work after a restart. Images are received on QQ, Telegram and Discord; outgoing images go out on Telegram and Discord only. New dependencies: `websockets` for the two gateways, `qrcode` for the login codes and `cryptography` to open QQ's sealed secret.
- The managed AstrBot runs without its dashboard, so there is no second login or password: the page, `up` and `connect astrbot --start` turn it off and keep it on loopback, and readiness comes from AstrBot's own startup log line.
- The local page shows connection progress and retries, keeps recent browser chat locally, resumes a connected bot on the next launch, reuses an already running page and stops only owned processes on exit. API routes require a per-launch capability, reject cross-origin/proxy requests, and never include keys in ordinary state responses.
- The page is plain white with warm grey type and hairlines, short page titles in place of slogans, and each platform's own logo: from Simple Icons (CC0) for QQ, WeChat, Telegram, Discord, Mattermost and Misskey, SVG Logos (CC0) for Slack, IconPark (Apache-2.0) for Feishu, MingCute (Apache-2.0) for DingTalk, TDesign (MIT) for WeCom, and KOOK's and OneBot's own icons. Satori has no logo and keeps a monogram. Connection states read as a coloured dot and a word, the character's avatar is the first character of its name, and the sidebar mark and tab icon are a small speech bubble with two eyes.
- The agent, AstrBot and the direct process that the page and `up` start end with them however they end, closing the console window included, so none is left holding the data folder's lock or answering with old code. On Windows they run in a job object that closes with the app, which also takes the interpreter a venv's `python.exe` starts; on Linux and macOS each leads its own process group, which ends once the app is gone. As a second line, the app records what it started under `runtime/desktop`, and the next start stops what an earlier run left behind, only once that run is gone and only while the process's command line still points at this home.
- The settings screen has a **Persona** box holding the text the character runs on: `persona.txt`, or the bundled template filled in the way the agent fills it. Saving writes `persona.txt` and restarts a running agent on it; what the character learned is kept, and the character menu then keeps your own text rather than replacing it.
- API keys can be shown explicitly in the page or terminal wizard. Changing a model endpoint requires re-entering its key rather than forwarding the old one automatically.
- `init` and `connect astrbot` offer to download a missing AstrBot with an isolated Python 3.12 runtime. `connect astrbot --install` also works without prompts, and `connect astrbot --start` runs the managed installation.
- `personagent up` starts the managed services together. `start --terminal`, `init --terminal`, headless flags and the existing server/connector commands remain available.
- Windows and POSIX launchers open the same welcome page interactively; the Windows VBS launcher no longer needs editable directory or QQ account constants. The installed browser flow is smoke-tested in CI on Windows and Linux.

### Fixed

- **A reply with a math sign or a number form in it is sent instead of dropped.** ², ½, ±, ≈, ≠ and subscripts used to fail the character whitelist and silence a reply the character had decided to send. They are spelled in ASCII the whitelist already takes (2^10, 1 1/2, +/-, ~, !=, H2O), mapped as whole Unicode families; ≤ and ≥ still drop the reply.
- **A model that must reason is asked for the lowest effort instead of failing.** On OpenRouter, a model that refuses to switch reasoning off ("Reasoning is mandatory") is retried at the lowest effort and remembered, on every call path including image descriptions.

### Changed

- **The README and guides lead with the platforms personagent connects itself** and treat AstrBot, NapCat, Koishi and Matrix as third-party bridges. The AstrBot plugin stays the way an AstrBot hands messages to personagent, without a badge of its own. Installing is `python -m pip install personagent` again.

## [1.0.2] — 2026-10-12

A smaller, faster codebase with the same behaviour: the package and tools are about 4,700 lines shorter, mostly comments that restated the code, duplicated helpers and scripts that only forwarded to a `personagent` command.

### Changed

- **Building a reply's context takes about half the time.** With 500 learned examples and 500 learned pairs, picking what a turn sees went from 22 ms to 11 ms, with the same result.
- **The server depends on plain `uvicorn`** instead of `uvicorn[standard]`, so websockets, watchfiles, PyYAML, httptools and uvloop are no longer installed. The server never used them.
- **The examples and feedback pools are reread whole when their file changes**, instead of reading only the appended tail. Edits made while the service runs still show up on the next turn.
- **The changelog keeps 1.x in full and summarizes 0.x.** The full earlier text is in the [v1.0.1 changelog](https://github.com/wangkant/personagent/blob/v1.0.1/CHANGELOG.md).

### Removed

- `try_chat.py` and the `tools/healthcheck.py`, `tools/candidates_admin.py` and `tools/behavior_eval.py` shims. Use `personagent chat`, `doctor`, `learned` and `eval`.
- `tools/prompt_lab.py` with `tools/fixtures.*.jsonl`, and the unfinished `tools/dspy_tune.py`. `personagent chat` tries a prompt change on the real pipeline and `personagent eval` measures it. `LAB_MODEL` (and its pre-1.0 name `PROMPT_LAB_MODEL`) is no longer read: `doctor` warns about it, and the service starts.
- A `runtime/example_candidates.json` left from before the evidence ledger is no longer touched. Nothing read it; it can be deleted.

### Fixed

- **`personagent eval` uses the eval home's persona card.** It used to read `persona.card.json` from your real home.
- **A lorebook entry with a non-numeric `scan_depth` no longer stops the whole lorebook from loading.** The key was never used and is no longer read.

## [1.0.1] — 2026-10-03

The README becomes a landing page, and the PyPI page shows it.

### Changed

- **The README is a landing page.** It shows the dashboard's chat view, three commands to try it, what makes it different, the shortest way into a group, the comparison and the measured results. Everything it used to explain in detail now lives in the user guide, [docs/guide.md](docs/guide.md) and [docs/guide.zh-CN.md](docs/guide.zh-CN.md). Its links are absolute, so they work on PyPI too.

### Fixed

- **Commands suggested under `uvx` say `uvx personagent ...`** even when uv's cache is in a folder of your choosing.

## [1.0.0] — 2026-10-03

personagent 1.0 installs as a package, sets itself up in English or Chinese, and shows its work: a demo that needs no key, a terminal chat that says why the bot spoke or stayed quiet, and a local dashboard for what it learned and the evidence behind it. Learning from a correction now works end to end, under a rule that one message, a bystander or a stranger cannot get around.

1.0 is also a stable interface. Through 1.x, the setting names, the `/v1` connector protocol (paths, headers, fields and error codes) and the data personagent stores (memory, the ledgers, the persona lineage, stickers and eval rows) stay compatible, so a 1.x upgrade needs no renames and keeps everything it learned. Python imports of `persona_agent` internals are not part of this promise and may change in any release. Getting there renamed most settings once: see "Upgrading from 0.4" below. The direct OneBot route `/v1/onebot` and `launch.vbs` are deprecated and keep working through 1.x.

### Highlights

- **Install with one command:** `uvx personagent demo` runs with nothing set up, and `uv tool install personagent` or `pipx install personagent` gives a permanent `personagent` command. A clone still works.
- **`personagent init` sets it up in English or Chinese:** 11 AI services (DeepSeek, SiliconFlow, Qwen, Zhipu, Kimi, Doubao, Ollama and more), the key tested as you enter it, four ready characters, and the AstrBot connection.
- **See it before you connect it:** `personagent demo` shows it staying quiet and learning from a correction on a scripted model, free and the same on every machine, and `personagent chat` is a simulated group that says why the bot spoke or stayed quiet.
- **Corrections that hold up are learned:** one message never teaches it anything, a change needs two agreeing reactions from the same chat with one of them strong, and every change can be rolled back.
- **A local dashboard**, opened through the private link `personagent run` prints, reads each conversation like the chat itself: who said what, where the bot stayed quiet and why, which reply was corrected and what it learned, with promote, reject, roll back and replace.
- **Upgrading is one command:** `personagent doctor --fix` renames the settings 1.0 retired.
- **Every platform through connectors:** the AstrBot plugin (QQ, Telegram, Discord, Slack, KOOK, Lark and more), Satori and Matrix, and an outbox so the bot can speak first on any of them.
- **One naming standard** for every setting, connector key and protocol field, kept through 1.x.
- **Python 3.10 to 3.14**, tested on Linux and Windows.

### Upgrading from 0.4

1. **Rename your settings: run `personagent doctor --fix`.** Old names are no longer read, and a start (`personagent run`, `personagent up` or `start.bat`) refuses with exit code 2 while any is still set, printing one `OLD -> NEW` line each. `personagent doctor --fix` renames them in `<home>/.env` by the Settings table below: it keeps the values and comments, saves the old file as `.env.bak`, and comments out an old line whose new name is already set. A retired name set in the environment rather than `.env` is listed, and must be renamed where it is set. `HOST`, `PORT` and `LOG_FILE` count only when written in `.env`. Then check `ADMIN_IDS`: it names one person, `ADMIN_NAME`, so when `OWNER_QQ` and `GATEWAY_OWNER_IDS` are moved into it, leave anyone else out. Write a non-QQ id with its platform prefix (`telegram:-1001234`).
2. **Check four defaults.** `LLM_MODEL=deepseek-chat` must become `deepseek-flash`: DeepSeek retired the old name. `QQ_ONEBOT_URL` (was `NAPCAT_API`) is now blank by default, meaning no NapCat HTTP server; if you use one and `.env` does not name it, set it (for example `http://127.0.0.1:3000`). Preflight and `personagent doctor` warn when the direct QQ route looks configured (`QQ_BOT_ID` or `QQ_ONEBOT_SECRET` set, `CONNECTOR_QQ_PLATFORMS` empty) and `QQ_ONEBOT_URL` is blank. A blank `PERSONA_TZ_OFFSET_HOURS` means UTC+8 when `AGENT_LANG=zh` and this machine's UTC offset otherwise. The AstrBot plugin's default `timeout_s` is 420 seconds, which covers the agent's own retry budget (`LLM_TIMEOUT_S × (1 + LLM_MAX_RETRIES)`, 360 s with the defaults). A `timeout_s` carried over from the old plugin or saved earlier stays as it was, so raise it if it is lower.
3. **Reinstall the AstrBot plugin** with `personagent connect astrbot <AstrBot data folder>`, then restart AstrBot. It installs `astrbot_plugin_personagent` and deletes the old `astrbot_plugin_llm_persona_gateway` directory and its settings file; left beside the new plugin, the old one would forward every message twice.
4. **Re-enter the plugin's `groups` and `dm_users`** in AstrBot's WebUI, and a `personagent_url` other than the local default. The first run carries over QQ routing and the settings that kept their names; these start empty.
5. **Update Satori and Matrix connectors** by the Connector configuration table: `PERSONAGENT_URL` is now the base URL, and the token is `CONNECTOR_TOKEN`.
6. **Code that calls the HTTP API itself** moves to the paths, headers and fields in the Protocol table. A process started as `uvicorn main:app` starts `persona_agent.server:app` instead, or `personagent run`.
7. **With `PROACTIVE_ENABLED=true`,** openers now start on every platform whose connector pulls the outbox. `PROACTIVE_PLATFORMS=qq` keeps them on QQ.
8. **Keep your data.** Memory, the ledgers, the persona lineage, stickers and eval rows keep their keys, and a DM's stored conversation key keeps its `private:` prefix, so nothing learned is lost. The group prompt's wording changed, so the provider's prompt cache misses once.

Settings:

| Old | New |
|---|---|
| `LLM_TIMEOUT` | `LLM_TIMEOUT_S` |
| `PRIVATE_MODEL`, `ANTHROPIC_PRIVATE_MODEL` | `LLM_DM_MODEL` |
| `JUDGE_MODEL` | `LLM_JUDGE_MODEL` |
| `FALLBACK_MODEL` | `LLM_FALLBACK_MODEL` |
| `FALLBACK_BASE_URL` | `LLM_FALLBACK_BASE_URL` |
| `FALLBACK_API_KEY` | `LLM_FALLBACK_API_KEY` |
| `FALLBACK_THINKING` | `LLM_FALLBACK_THINKING` |
| `FALLBACK_DURATION` | `LLM_FALLBACK_DURATION_S` |
| `RATE_WINDOW` | `LLM_RATE_WINDOW_S` |
| `RATE_THRESHOLD` | `LLM_RATE_THRESHOLD` |
| `RATE_LIMIT_COOLDOWN` | `LLM_RATE_LIMIT_COOLDOWN_S` |
| `GLM_API_KEY` | `VISION_API_KEY` |
| `GLM_BASE_URL` | `VISION_BASE_URL` |
| `MAX_IMAGE_BYTES` | `VISION_MAX_IMAGE_BYTES` |
| `BOT_NAME` | `PERSONA_NAME` |
| `TZ_OFFSET_HOURS` | `PERSONA_TZ_OFFSET_HOURS` |
| `OWNER_QQ`, `GATEWAY_OWNER_IDS` | `ADMIN_IDS` |
| `OWNER_NAME` | `ADMIN_NAME` |
| `OWNER_RELATIONSHIP` | `ADMIN_RELATIONSHIP` |
| `QQ_GROUPS`, `ALLOWED_GROUPS` | `ACCESS_GROUPS` |
| `PRIVATE_ALLOWED_QQS`, `ALLOWED_DM_USERS` | `ACCESS_DM_USERS` |
| `AGENT_TRIGGER_COUNT` | `CHAT_TRIGGER_COUNT` |
| `AGENT_CONTEXT_LEN` | `CHAT_CONTEXT_MESSAGES` |
| `AGENT_FOLLOWUP_WINDOW` | `CHAT_FOLLOWUP_WINDOW_S` |
| `AGENT_MEMORY_FILE` | `MEMORY_FILE` |
| `AGENT_MEMORY_MAX` | `MEMORY_MAX_PER_CONVERSATION` |
| `AGENT_ENABLE` | `AGENT_ENABLED` |
| `HOST` | `SERVER_HOST` |
| `PORT` | `SERVER_PORT` |
| `MAX_WEBHOOK_BODY_BYTES` | `SERVER_MAX_BODY_BYTES` |
| `LOG_FILE` | `SERVER_LOG_FILE` |
| `GATEWAY_TOKEN` | `CONNECTOR_TOKEN` |
| `GATEWAY_SOURCE_MAX_AGE_SECONDS` | `CONNECTOR_MAX_EVENT_AGE_S` |
| `GATEWAY_NATIVE_PLATFORMS` | `CONNECTOR_QQ_PLATFORMS` |
| `GATEWAY_OUTBOX` | `CONNECTOR_OUTBOX_ENABLED` |
| `MAX_INFLIGHT_GATEWAY` | `CONNECTOR_MAX_INFLIGHT` |
| `BOT_QQ` | `QQ_BOT_ID` |
| `NAPCAT_API` | `QQ_ONEBOT_URL` |
| `NAPCAT_IMAGE_DIR` | `QQ_ONEBOT_IMAGE_DIR` |
| `WEBHOOK_SECRET` | `QQ_ONEBOT_SECRET` |
| `MAX_INFLIGHT_WEBHOOKS` | `QQ_ONEBOT_MAX_INFLIGHT` |
| `PROACTIVE_ENABLE` | `PROACTIVE_ENABLED` |
| `PROACTIVE_INTERVAL` | `PROACTIVE_INTERVAL_S` |
| `PROACTIVE_MIN_SILENCE` | `PROACTIVE_MIN_SILENCE_S` |
| `PROACTIVE_COOLDOWN` | `PROACTIVE_COOLDOWN_S` |
| `PROACTIVE_DM_MIN_SILENCE` | `PROACTIVE_DM_MIN_SILENCE_S` |
| `PROACTIVE_DM_COOLDOWN` | `PROACTIVE_DM_COOLDOWN_S` |
| `REACT_LEARN` | `REACT_LEARN_ENABLED` |
| `REACT_TTL_SEC` | `REACT_TTL_S` |
| `REACT_FIX_WINDOW` | `REACT_FIX_WINDOW_S` |
| `REACT_ELICIT` | `REACT_ELICIT_ENABLED` |
| `REACT_ELICIT_DELAY` | `REACT_ELICIT_DELAY_S` |
| `REACT_ELICIT_COOLDOWN` | `REACT_ELICIT_COOLDOWN_S` |
| `PROMOTE_AUTO` | `PROMOTE_AUTO_ENABLED` |
| `EXAMPLES_MAX_AUTO` | `PROMOTE_MAX_EXAMPLES` |
| `FEEDBACK_MAX_AUTO` | `PROMOTE_MAX_FEEDBACK` |
| `EVOLVE_AUTO` | `EVOLVE_AUTO_ENABLED` |
| `EVAL_ENABLE` | `EVAL_ENABLED` |
| `AGENT_EVIDENCE_WARN_BYTES` | `LEDGER_EVIDENCE_WARN_BYTES` |
| `AGENT_CANDIDATE_LEDGER_WARN_BYTES` | `LEDGER_CANDIDATES_WARN_BYTES` |
| `PROMPT_LAB_MODEL` | `LAB_MODEL` |
| `BENCH_EVAL_DELAY` | `BENCH_EVAL_DELAY_S` |

Connector configuration:

| Connector | Old | New |
|---|---|---|
| Satori, Matrix | `PERSONAGENT_URL`, the event endpoint (`http://127.0.0.1:8080/webhook/gateway`) | `PERSONAGENT_URL`, the base URL (`http://127.0.0.1:8080`) |
| Satori, Matrix | `GATEWAY_TOKEN` | `CONNECTOR_TOKEN` |
| Satori | `SATORI_ENDPOINT` | `SATORI_URL` |
| Satori | `SATORI_FORWARDER_ID` | `SATORI_CONNECTOR_ID` |
| Satori | `SATORI_OUTBOX` | `SATORI_OUTBOX_ENABLED` |
| Satori | `SATORI_INLINE_IMAGES` | `SATORI_INLINE_IMAGES_ENABLED` |
| Matrix | `MATRIX_HOMESERVER` | `MATRIX_URL` |
| Matrix | `MATRIX_ROOMS` | `MATRIX_GROUPS` |
| Matrix | `MATRIX_FORWARDER_ID` | `MATRIX_CONNECTOR_ID` |
| Matrix | `MATRIX_OUTBOX` | `MATRIX_OUTBOX_ENABLED` |
| Matrix | `MATRIX_E2EE` | `MATRIX_E2EE_ENABLED` |
| Matrix | `MATRIX_READ_RECEIPTS` | `MATRIX_READ_RECEIPTS_ENABLED` |
| Matrix | `MATRIX_STORE_PATH` | `MATRIX_STORE_DIR` |
| AstrBot plugin | `astrbot_plugin_llm_persona_gateway` (directory and plugin name) | `astrbot_plugin_personagent` |
| AstrBot plugin | `agent_url`, the event endpoint | `personagent_url`, the base URL |
| AstrBot plugin | `gateway_token` | `connector_token` |
| AstrBot plugin | `forwarder_id` | `connector_id` |
| AstrBot plugin | `group_whitelist` | `groups` |
| AstrBot plugin | `private_whitelist` | `dm_users` |
| AstrBot plugin | `private_enabled` | none: DMs are forwarded when `dm_users` is not empty |

`*` in the plugin's `groups` or `dm_users`, as in the other connectors' lists, forwards every conversation of that kind with `"prefiltered": false`, so personagent's `ACCESS_*` lists decide.

Protocol (docs/connectors.md), where the signing scheme, the segments and every field not listed are unchanged:

| Old | New |
|---|---|
| `POST /webhook/gateway` | `POST /v1/events` |
| `POST /webhook/gateway/outbox` | `POST /v1/outbox` |
| `POST /webhook/qq`, the direct OneBot ingress (its `X-Signature` header stays) | `POST /v1/onebot` |
| `X-Gateway-Token`, `X-Gateway-Timestamp`, `X-Gateway-Nonce`, `X-Gateway-Signature` | `X-Personagent-Token`, `X-Personagent-Timestamp`, `X-Personagent-Nonce`, `X-Personagent-Signature` |
| `message_type`: `"group"` / `"private"`, in events and outbox deliveries | `conversation_type`: `"group"` / `"dm"` |
| `user_id` | `sender_id` |
| `self_id` | `bot_id` |
| `source_timestamp` | `sent_at` |
| `is_at_me` | `addressed` |
| `raw_text` | `text` |
| `forwarder_id`, in events and outbox pulls | `connector_id` |
| `caps` | `capabilities` |
| a reply's `at_user_id` | `mention_user_id` |
| error code `stale_source_event` | `stale_event` |

### Added

- **The `personagent` command, installable from PyPI.** `uvx personagent <command>` runs it without installing anything; `uv tool install personagent`, `pipx install personagent` or `pip install personagent` install it for good, and `pip install -e .` gives a clone the command too. The commands are `init`, `chat`, `demo`, `run`, `connect astrbot`, `doctor`, `learned` and `eval`; `python -m persona_agent` is the same command, and `--home DIR` works before or after the subcommand. The package ships the seed data, the example personas, the eval sets, `.env.example` and the AstrBot plugin, so it runs without a clone.
- **One home folder for settings, the persona and what it learned:** `--home DIR` or `AGENT_HOME`; else the clone being run; else the current folder when it holds `.env` and `persona.txt`; else `~/personagent`. A file under `<home>/data/` with a shipped seed's name overrides the shipped copy.
- **`personagent init`, a setup in English or Chinese.** It offers 11 AI services with their documented addresses and current models, tests the key (typed hidden) with one tiny request and on failure shows the address called, the HTTP status and a likely fix, offers four ready characters per language or the plain template, and ends with the next steps as exact commands for this machine. Re-running offers the current values. `--no-input` with `--provider`, `--base-url`, `--model`, `--key-env`, `--name`, `--lang` and `--persona` asks nothing; with no terminal and no flags it exits with code 2. `python quickstart.py` creates `.venv`, installs the requirements and runs the same setup.
- **`personagent connect astrbot [DATA_DIR]`** installs or updates the AstrBot plugin and writes the shared token on both sides. It finds AstrBot's folder, asks which chat app (and QQ details only for QQ), explains host networking or takes an HTTPS address when AstrBot runs in Docker, and never writes an address the plugin would refuse. With `DATA_DIR` and `--qq` / `--no-qq`, `--platform ... --token ...` or `--url https://...` it asks nothing; `--platform` switches the adapter on in AstrBot's config, and an existing adapter entry keeps its other settings.
- **`personagent demo [quiet|teach|troll|all]`** plays three scenes on a scripted model with the real ledger and promotion code: which group lines it answers or skips and why, a correction that holds up, and a stranger's planted instruction that changes nothing. It is the same on every machine and costs nothing; `--online` plays it on your configured model. It runs a built-in character in a temporary folder and never reads your persona or touches your `runtime/`.
- **A local dashboard at `http://127.0.0.1:<SERVER_PORT>/`**, served by `personagent run` with nothing loaded from the internet. It shows the service, its connectors and outbox, and preflight's findings, and draws each conversation as the chat: where the bot stayed quiet and why, corrected replies with what was learned from them, the full evidence chain, and proposals with each promotion rule ticked or crossed. Promote, Reject, Roll back and Replace write to the same ledger as `personagent learned`. English and Chinese, light and dark, and it works on a phone.

  It opens only through its private link, which the startup banner and `personagent doctor` print. The token is kept in `<runtime>/dashboard.token`, and opening the link sets an HttpOnly, `SameSite=Strict` cookie. A request without the token gets 401, a wrong token 403, and a host name other than `localhost`, an IP address or `SERVER_HOST` 403, which blocks DNS rebinding. `CONNECTOR_TOKEN` does not open it, and `DASHBOARD_ENABLED=false` removes it. The [deployment guide](docs/deploy.md#activity) has the details.
- **`start.bat`**: double-click it to start personagent on Windows.
- **A startup banner** with the version, the address, the home folder, the dashboard's link, and whether the agent is on, or off with the cause and the fix. The log also names the reply and gate models, and suggests a cheaper `LLM_JUDGE_MODEL` when they are the same.
- **`personagent doctor --fix`** renames the settings 1.0 retired in `<home>/.env`, keeping values and comments and saving the old file as `.env.bak`. `personagent doctor` and `doctor --json` report retired settings (`retired_settings`) and exit 1 while any remain.
- **A behavioural eval, `personagent eval`**, runs the real agent on labelled English and Chinese cases in `data/evals/`. `speak` checks the speak-or-stay-quiet decision and needs no judge; `persona` has a separate judge rate each reply and pick blind between it and a plain assistant's; `learning` drives corrections and accepted retries through the real reaction path and promotion policy, which it never bypasses, and probes the next reply before and after. The persona and learning suites need a judge that is not the model under test (`BENCH_JUDGE_MODEL`; `--allow-same-judge` runs anyway and marks the report). Each run works in a throwaway folder and writes a JSON report with every case to `<home>/benchmark_runs/`.
- **Hybrid retrieval.** Examples, contrastive pairs and memories are ranked on BM25, where the row was learned (this conversation, this persona, the shipped seeds), recency, and, when `EMBEDDING_MODEL` is set, cosine similarity from any OpenAI-compatible `/embeddings` endpoint, cached in `runtime/embeddings.jsonl`. A failing endpoint never fails a turn: it is logged once, left alone for five minutes, and the turn is ranked on the other signals. The lorebook stays keyword-triggered.
- **An admin and allowlists that work on every platform: `ADMIN_IDS`, `ACCESS_GROUPS` and `ACCESS_DM_USERS`.** Entries are `<platform>:<id>`, and a bare id is QQ. The lists apply per platform: a platform with no entries is not restricted by the agent, so one Telegram entry gates Telegram and leaves QQ alone. An event marked `"prefiltered": false` makes a platform without entries default-deny. A refusal is logged once per conversation, naming the setting that refused it.
- **The outbox: `POST /v1/outbox`.** A connector that declares `"capabilities": ["outbox"]` long-polls it for messages no request is waiting for, and only what it acks as sent counts as said ([docs/connectors.md](docs/connectors.md)). Same authentication as `/v1/events`, with its own concurrency budget. `CONNECTOR_OUTBOX_ENABLED=false` turns it off.
- **Proactive openers, the follow-up question and the excuse reach every platform with such a connector**, and are remembered only once acked. The DM loop also considers anyone still admitted who has DMed the bot through one. `PROACTIVE_PLATFORMS` (for example `qq`) limits where openers go; blank means everywhere it can reach.
- **The AstrBot plugin (1.0.0) is a full connector.** Its events carry `connector_id`, `reply_handle` and `capabilities`, and it pulls the outbox (`outbox_enabled`, on by default) and delivers on every platform that lets a bot speak first, only to a session it took from a message in that conversation, checking the allowlists again at send time.
- **A forwarded quote says what it quotes.** A `reply` segment may carry the quoted `text`, `sender_id` and `sender_name`, an `emoji` segment's `name` reaches the model, and an image with `"sticker": true` reads as a sticker. Older connectors see no change.
- **Python 3.10 to 3.14.** CI runs the suite on Linux for each version and on Windows with 3.12, and builds, installs and runs the package on both. A release is cut only from a tag on `main` after the suite passes.

### Changed

- **One naming standard.** Every setting, connector key, endpoint, header and event field follows one set of rules, and each old name is gone rather than kept as an alias (see Upgrading from 0.4): one module prefix per setting (`LLM_`, `PERSONA_`, `ACCESS_`, `CONNECTOR_`, `PROMOTE_`, ...), a unit on every duration (`_S`, `_HOURS`, `_DAYS`) and size (`_BYTES`), `_ENABLED` on a switch, a vendor's own names for its credentials, and one name, `CONNECTOR_TOKEN`, for the token the server and its connectors share.
- **A correction that holds up is learned.** When the person a reply was for corrects it and then accepts the bot's next reply, the old reply is learned as "say the retry instead"; if they move on, nothing is learned. One message never teaches it anything: a change needs two agreeing reactions from the same chat, at least one strong (the person the reply was for correcting it, or accepting the retry). With the default `PROMOTE_MIN_SPEAKERS=1`, one person can teach it only how to answer them, in their own chat. Everything is in append-only ledgers and can be rolled back ([the rule in full](docs/guide.md#corrections)).
- **Learning stays with the person a reply was for.** A remark the bot made unasked belongs to the member it @-ed, or to no one, and then only the admin can promote a rewrite of it. A bystander's answer to the follow-up question still counts as a bystander's. Several people can each wait for a retry at once, up to 8 per conversation, and memory commands never reach the reaction model.
- **One rewrite per reply.** A reply keeps at most one rewrite in use, in any mode; a second waits for the admin, who replaces the first with `personagent learned supersede` or the dashboard's Replace. A promotion also rejects the drafts its evidence answered.
- **Behind connectors, replying to or quoting the bot's message counts as a reaction it can learn from**, as an @ already did.
- **Name calls match whole words, in any case:** "luna are you there" calls Luna, "Lunar" does not. A name in Chinese, Japanese or Korean characters matches anywhere in the message.
- **Memory commands must start the message**, after any @-mention or quote. Questions and "remember when we..." are ordinary chat, and never-mind phrases such as "forget that" delete nothing; in Chinese, a message ending in 吗, 么, 呢 or 没 is a question. Recall answers only when the whole message is the recall phrase. With `AGENT_LANG=zh` every memory-command reply is in Chinese.
- **A note records who saved it and who it is about.** A note about a member reaches the prompt while they are present and can be read or forgotten only by them, its saver and the admin; anything else is a note for the whole group, labelled with its saver in recall.
- **"What have you learned" says what each proposal waits for**, and why the latest promotion passed, naming only people from the asking chat. It never calls a model and is at most four lines.
- **`PROMOTE_*` settings behave like every other setting.** An invalid or below-floor value logs a warning and uses the default or the floor (`PROMOTE_MIN_EVENTS` at least 2, `PROMOTE_MIN_STRONG` and `PROMOTE_MIN_SPEAKERS` at least 1). The defaults are unchanged.
- **`personagent chat` is a simulated group chat.** Each plain line goes through the live bot's speak-or-stay-quiet decision, which it explains (`(Nova stays quiet: <reason>)`); reactions to its replies are judged and recorded, and `/why`, `/learned` and `/reset` show and clear what the trial learned, kept in `<runtime>/trial/` apart from the live bot's. A failed model call prints one line saying what to check, never a silent persona ([the guide](docs/guide.md#chat-in-the-terminal) has the commands).
- **The scripts became `personagent` commands:** `personagent run` (`main.py`), `personagent chat` (`try_chat.py`), `personagent doctor` (`tools/healthcheck.py`), `personagent learned` (`tools/candidates_admin.py`) and `personagent eval` (`tools/behavior_eval.py`). The old scripts keep working with the same flags.
- **The default model is DeepSeek's `deepseek-flash`** at `https://api.deepseek.com`. DeepSeek retired `deepseek-chat`.
- **An exhausted balance or quota is fatal and said once.** HTTP 402, or OpenAI's `insufficient_quota` 429, is not retried or failed over; one ERROR line names the provider's host and the settings to check. A rejected key (401/403) gets a similar line. A per-minute 429 is still a rate limit.
- **`QQ_ONEBOT_URL` is blank by default**, meaning no NapCat HTTP server: no missed-mention sweep or NapCat lookups, the OneBot bridge shows as "not configured", and a QQ message the bot starts itself goes out through a connector that pulls the outbox. Set it for the direct `/v1/onebot` route or the sweep, which also needs `QQ_BOT_ID`.
- **`PERSONA_TZ_OFFSET_HOURS` is blank by default**, meaning UTC+8 when `AGENT_LANG=zh` and this machine's current UTC offset otherwise. It sets the time shown to the model and the 02:00 to 07:00 sleep window.
- **`AGENT_LANG` accepts `zh-CN`, `zh_cn`, `cn` and `chinese`** (read as `zh`) and `en-US` and `english` (read as `en`); any other value is warned about once.
- **The model-failure excuse reaches the admin too**, in the agent's language, at most once per conversation every five minutes, counted from an excuse that was delivered. In a group it needs a connector that pulls the outbox.
- **A network bind needs only `CONNECTOR_TOKEN`.** Without `QQ_ONEBOT_SECRET`, `/v1/onebot` accepts only programs on this host, and on a network bind it is off (403 `onebot_disabled`).
- **A start that cannot work stops with one sentence and exit code 2** instead of a traceback: a missing home folder, another personagent on the same home, a taken port, a `SERVER_HOST` that is not this machine's, a network bind without `CONNECTOR_TOKEN`, or a retired setting still set (one `OLD -> NEW` line each).
- **An agent that cannot answer says so.** With no `LLM_API_KEY`, or `AGENT_ENABLED=false`, `/v1/events` returns `"owned": false`, and the banner and the first event's ERROR line name the cause and the fix.
- **The launchers no longer start a server that cannot answer.** `start.sh`, `start.ps1` and `start.bat` run the setup when there is no `.env` and no `LLM_API_KEY`, or, with no terminal, say to run `python quickstart.py` and exit.
- **The connector replay guard holds 16,384 nonces** in its five-minute window and appends one line per request; a restart inside the window still refuses a replay.
- **`.env.example` reads top-down**, from the required settings to the QQ / NapCat block, with every comment on its own line so the file works with `docker --env-file` and systemd.
- **Preflight warns about what is really configured:** no `QQ_BOT_ID` warning on non-QQ setups, and new checks for `AGENT_LANG` and `PERSONA_TZ_OFFSET_HOURS`.
- **Dependencies:** `pydantic>=2.9,<3`, `fastapi>=0.128` and `Pillow>=10.4`. `requirements.txt` is the one dependency list.
- **`EVOLVE_INTERVAL_HOURS` below 0.1** is raised to 0.1 hours with a warning.
- **Logs and health checks say "DM"** instead of "private".
- **The AstrBot plugin reads each platform the way its adapter delivers it.** QQ pokes, recalls and requests no longer reach the persona as empty turns; more replies and mentions count as addressing the bot; quotes, sticker and emoji names, voice transcripts and the platform's send time come through; Telegram images are sent inline, so the bot token in their URLs never reaches the agent; and with the platform's send time, a backlog older than `CONNECTOR_MAX_EVENT_AGE_S` is refused as stale.
- **The AstrBot plugin writes each platform's way:** long replies are split under each platform's limit, Telegram shows `*` and `_` as typed, text cannot ping a whole channel, and QQ official replies are plain text.
- **The admin is the admin on every platform**, with the closer persona, authority over group memories, extra weight when correcting the bot and the exemption from `PROMOTE_MIN_SPEAKERS`.
- **The group prompt no longer assumes QQ.** Speakers are labelled `id=`, and the mention marker `[AT:id]` is spelled the way the conversation's ids are.
- **QQ through AstrBot sends the follow-up question, the excuse and proactive messages through the plugin's outbox** while it is pulling, and only otherwise through `QQ_ONEBOT_URL`.
- **A connector's own `"proactive": true` DM counts against `PROACTIVE_DM_COOLDOWN_S`**, so it and the agent's own loop cannot both open the same DM.
- **A half-delivered proactive opener is kept on record**, as a half-delivered reply already was.
- **`tools/import_stickers_folder.py` no longer defaults `VISION_MODEL`** to one vendor's model, and `tools/sticker_holdout_eval.py` stops up front when vision is not configured.
- **For code built on the engine:** the entry points live in the package (`persona_agent.server`, whose `app` replaces `main:app`, and `chat`, `doctor`, `ledger_admin`, `evals` and `cli`); a renamed setting renames its `AgentSettings` field and `Agent` attribute (`llm_timeout_s`, `access_groups`, `vision_api_key`, ...); `AgentSettings(...)` built in code has the `.env.example` defaults; identifiers say admin, connector and dm where they said owner, gateway or forwarder, and private (`persona_agent/gateway.py` is `connector.py`, `Agent.handle_gateway` is `handle_event`, `Agent.handle` is `handle_onebot`); and `agent.py` is split into mixins by concern ([CONTRIBUTING.md](.github/CONTRIBUTING.md#code-layout) has the layout).

### Fixed

- **A provider outage is retried, not mistaken for a bad key.** A 5xx that mentions quota or capacity is retried and fails over; only a 401, 402, 403 or 429 can mark the key or the account as the problem. A 400 counts as refusing a parameter only when it names it as one.
- **A base URL without `http://` or `https://` is reported** by preflight and `personagent doctor`, and `personagent init` asks again. Gemini's native `/v1beta` is reported with the `/v1beta/openai` address it needs.
- **A reply that only trails off is delivered**: "…" and "…?" go out as "..." and "...?".
- **A model answer without a `reply` key is logged**, naming the keys the model used instead.
- **A lone Hebrew vav or final nun between Latin words is refused like `|`**, so it cannot draw a fake role marker.
- **One renderer for `persona.txt`**, shared by the agent and `personagent init`.
- **OpenAI, Groq, Gemini and OpenRouter work as the main model.** DeepSeek's `thinking` field goes only to vendors that accept it, any other endpoint is asked once per URL and model, and an endpoint that refuses `max_tokens` or a fixed temperature is retried with `max_completion_tokens` or without it, and remembered.
- **Base URLs work as their vendors document them:** Zhipu's `.../api/paas/v4`, Volcengine Ark's `.../api/v3` and Gemini's `.../v1beta/openai/` get only `/chat/completions` (and `/embeddings`) appended; a plain root still gets `/v1/chat/completions`.
- **Replies in Spanish, Vietnamese, Hindi, Marathi, Nepali, Bengali, Tamil, Thai and Hebrew are delivered** instead of silently dropped.
- **Short letterless replies are delivered** when the model wrote them that way: `?`, `...`, `:)`, `10/10`, `+1`.
- **A reply the model wrote as plain text instead of JSON is kept**, and every sanitizer and leak check still runs on it.
- **A JSON reply with extra keys, capitalised keys or `"mem": []`** is understood instead of producing an empty reply.
- **A `persona.txt` copied from the shipped template works unedited:** `{bot_name}`, `{admin_name}` and `{admin_relationship}` are filled from the settings, and the template's closing note is removed.
- **After the persona is edited, the first turn after a restart uses what was learned.**
- **A setting whose value starts with `#` is named at startup**: an inline comment after an empty value is read as the value.
- **《书名》 and 「引号」 survive the sanitizer**, and quotes are removed only when they wrap the whole reply.
- **The persona stops searching the web for its own world:** questions about the persona, its friends or the chat are answered in character.
- **Fewer invented memories:** the style guide says a new person has no shared past with the persona.
- **The bot's own message, echoed back by a connector** (`sender_id` equal to `bot_id`), is ignored.
- **A connector message marked `addressed`** reads `@Name text` to the model.
- **Re-running `personagent connect astrbot` keeps the AstrBot setup:** allowlists, DMs, an accepted `personagent_url`, excluded platforms and QQ routing stay unless given again, and the plugin's existing token is reused when `.env` has none.
- **A failed persona-lineage save no longer drops earlier revisions out of scope.**
- **An image seen during a vision outage is described once the outage ends.**
- **`personagent doctor` and `/health/details` probe the DM chat with the default model when `LLM_MODEL` is unset.**
- **`personagent learned` reads `AGENT_LANG` and the pool caps as the agent does.**
- **Health probes to loopback services** bypass `HTTP_PROXY` and `HTTPS_PROXY`.
- **A crashed background task is logged at ERROR with the task's name.**
- **A leftover `.env.tmp` is recreated owner-only** instead of keeping its old mode.

### Security

- **Only the person a reply was for can make a correction stick.** A bystander's acceptance, or a later reply to someone else linked as the retry, could promote a reply its person never accepted. Now only the bot's next reply to the person who complained counts as the retry, and accepting it is strong only from the person the original reply was for.
- **A blank `SERVER_HOST` (or `--host ""`) means `127.0.0.1`**, not every network interface.
- **More proxy headers mark a request as not local** on an endpoint with no credential configured (403 `non_local_request`): `Via`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`, `True-Client-IP`, `X-Client-IP` and `X-Original-Forwarded-For`. Set `CONNECTOR_TOKEN` before adding any proxy or tunnel.
- **A bystander cannot undo what someone else taught.** Only the person a reply was for, or the admin, rolls back a learned rewrite by complaining; anyone else's complaint is linked to it as disputed and removes nothing.
- **The direct OneBot ingress, `/v1/onebot`, refuses namespaced ids**, which could pass the DM check through the admin bypass or skip the QQ group allowlist.

### Removed

- **The setting names retired by the naming standard are no longer read** (see Upgrading from 0.4). Preflight names each one still set, and warns about an id without its platform prefix, a capitalised platform, and a `CONNECTOR_QQ_PLATFORMS` entry other than `aiocqhttp`.
- **The owner is now called the admin:** `ADMIN_NAME` and `ADMIN_RELATIONSHIP`, and `--admin` and `/admin` in `personagent chat`.
- **`GLM_API_KEY` and `GLM_BASE_URL` become `VISION_API_KEY` and `VISION_BASE_URL`**, for whichever OpenAI-compatible model `VISION_MODEL` names. `VISION_BASE_URL` has no default.

### Deprecated

- **`/v1/onebot`, the direct OneBot ingress, and `launch.vbs`, which starts it,** keep working through 1.x. Every response from `/v1/onebot` carries `Deprecation: true`, with no `Sunset` date. The supported QQ route is AstrBot with `CONNECTOR_QQ_PLATFORMS=aiocqhttp`.

## [Before 1.0]

0.1.0 to 0.4.0 ran from a clone, under setting, endpoint and header names that 1.0 retired (see [Upgrading from 0.4](#upgrading-from-04)). Their full notes are in the [GitHub releases](https://github.com/wangkant/personagent/releases) for v0.2.0 to v0.4.0 and in [this file as of v1.0.1](https://github.com/wangkant/personagent/blob/v1.0.1/CHANGELOG.md); 0.1.x was not tagged.

### [0.4.0] — 2026-09-24

The interface pass. Every error the HTTP surface returned gained a stable `code` beside its sentence, `/webhook/qq` announced its deprecation in its own headers, one settings record replaced the agent's keyword parameters and scattered environment reads, and the tests became plain pytest. It fixed group @-mentions being dropped on the recommended QQ path, made the 0.2.0 rule that no persona is told to deny being an AI hold in both chat paths, and recovered blank DM replies from JSON mode. Chat text reached every prompt as data, memories could not carry instructions, few-shot rows could not restructure the system prompt, the SSRF guard covered every non-global address, the fallback model gained its own endpoint, and a rate-limited model a cooldown.

### [0.3.0] — 2026-09-04

AstrBot became the platform: QQ entered through the same gateway as every other adapter (`GATEWAY_NATIVE_PLATFORMS`), the direct OneBot ingress and `launch.vbs` were deprecated, and `DEEPSEEK_*` became `LLM_*`. It added the persona lineage, so editing the persona kept what was learned, the AstrBot step in `quickstart.py`, "what have you learned", the settings typo check (`preflight.py`) and proactive turns over the gateway, and a debugging and simplification pass removed about 1,300 lines.

### [0.2.0] — 2026-08-11

An unsupported character degraded to a missing glyph instead of silencing the reply: a STRIP / MAP / ALLOW character policy, six more scripts allowed, per-persona opt-ins and a `[style]` block. The reply ceiling rose to 800 characters, and the system prompt gained an honesty clause a persona document cannot displace. Learning moved onto the append-only evidence log and candidate ledger: no automatic signal wrote a retrieval pool, promotion required corroboration, and `EVOLVE_AUTO` proposed instead of applying. `anthropic` stopped being a runtime dependency.

### 0.1.0 and 0.1.1 — 2026-07-25

The first release: learning from real reactions, the JSON reply protocol, the whitelist reply validator, few-shot retrieval over read-only seeds and a learned `runtime/`, the platform-neutral gateway with an AstrBot forwarder, the sticker pipeline, opt-in proactive mode, a cheap gate model before the reply model, and the SSRF guard. 0.1.1 stopped a single positive signal from banking an example and let a rejection withdraw a learned one.

[Unreleased]: https://github.com/wangkant/personagent/compare/v1.4.3...HEAD
[1.4.3]: https://github.com/wangkant/personagent/compare/v1.4.2...v1.4.3
[1.4.2]: https://github.com/wangkant/personagent/compare/v1.4.1...v1.4.2
[1.4.1]: https://github.com/wangkant/personagent/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/wangkant/personagent/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/wangkant/personagent/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/wangkant/personagent/compare/v1.2.2...v1.3.0
[1.2.2]: https://github.com/wangkant/personagent/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/wangkant/personagent/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/wangkant/personagent/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/wangkant/personagent/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/wangkant/personagent/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/wangkant/personagent/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/wangkant/personagent/compare/v0.4.0...v1.0.0
[Before 1.0]: https://github.com/wangkant/personagent/blob/v1.0.1/CHANGELOG.md
[0.4.0]: https://github.com/wangkant/personagent/releases/tag/v0.4.0
[0.3.0]: https://github.com/wangkant/personagent/releases/tag/v0.3.0
[0.2.0]: https://github.com/wangkant/personagent/releases/tag/v0.2.0
