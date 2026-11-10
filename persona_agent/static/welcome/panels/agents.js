// The agents panel. See PA at the end of welcome.js.
PA.strings({
  en: {
    agents_title: "Coding assistants",
    agents_hint: "Talk with {name} from the coding assistants on this computer.",
    agents_recheck: "Check again",
    agents_checking: "Checking…",
    agents_checked: "The check is complete.",
    agents_loading: "Looking for coding assistants…",
    agents_load_failed: "The coding assistants on this computer could not be read.",
    agents_desc_claude: "Adds two tools to Claude Code for the current user of this computer: talk (the same chat as this page) and character.",
    agents_desc_codex: "Adds the same two tools to Codex, in its config.toml file.",
    agents_desc_dsh: "Adds the same two tools to every DeepSeek Harness profile.",
    agents_state_missing: "Not found on this computer",
    agents_state_missing_dsh: "Not found. Start DeepSeek Harness once, then select Check again.",
    agents_state_off: "Not connected",
    agents_state_on: "Connected",
    agents_state_other: "Set up for another folder or an earlier installation",
    agents_state_partial: "Connected in {n} of {m} profiles",
    agents_install_first: "Install it, then select Check again.",
    agents_connect: "Connect",
    agents_repair: "Repair",
    agents_update: "Update",
    agents_remove: "Remove",
    agents_connecting: "Connecting…",
    agents_removing: "Removing…",
    agents_saving: "Saving…",
    agents_ask_claude: "This runs the claude command to add personagent to Claude Code for the current user of this computer. Continue?",
    agents_ask_codex: "This adds a personagent section to the Codex config.toml file. Continue?",
    agents_ask_dsh: "This adds personagent to every DeepSeek Harness profile. Continue?",
    agents_ask_replace: "The existing setup will be replaced.",
    agents_ask_remove: "This removes the talk and character tools for {name} from {target}. Continue?",
    agents_ask_remove_react: "End-of-turn remarks will also be turned off.",
    agents_removed: "Removed from {target}.",
    agents_done_claude: "Start a new Claude Code session and ask it to talk with {name}. On first use, Claude Code asks whether to allow the tool.",
    agents_done_codex: "Start a new Codex session and ask it to talk with {name}.",
    agents_done_dsh: "Restart DeepSeek Harness to apply the change.",
    agents_react: "Make a remark when a turn ends",
    agents_react_hint: "Sends the project folder name and the beginning of the assistant's last reply to your model service. Each remark is one model call. Remarks are shown only while this app is open.",
    agents_react_ask: "When a turn ends, the project folder name and the beginning of the assistant's last reply will be sent to your model service. Turn this on?",
    agents_react_yes: "Turn on",
    agents_react_on: "Remarks are turned on.",
    agents_react_off: "Remarks are turned off.",
    agents_react_trust: "In Codex, enter /hooks and trust the personagent hook; otherwise remarks are not shown.",
    agents_cooldown: "Minimum interval between remarks",
    agents_cool_600: "10 minutes",
    agents_cool_1800: "30 minutes",
    agents_cool_3600: "1 hour",
    agents_cool_7200: "2 hours",
    agents_cool_other: "{n} minutes",
    agents_cooldown_saved: "Saved. At most one remark every {time}.",
    agents_astrbot_title: "Use an existing AstrBot",
    agents_astrbot_hint: "Installs the personagent plugin in an AstrBot that you run yourself, so that {name} replies to its chats.",
    agents_astrbot_folder: "AstrBot folder",
    agents_astrbot_found: "An AstrBot was found at this location. To use a different one, change the folder.",
    agents_astrbot_none: "No AstrBot was found in the usual locations. Paste the path of the folder that contains its data folder.",
    agents_astrbot_connected: "Connected to the AstrBot in {folder}.",
    agents_astrbot_docker: "AstrBot runs in Docker or on another computer",
    agents_astrbot_url: "Address at which AstrBot reaches personagent",
    agents_astrbot_url_hint: "Docker cannot reach 127.0.0.1 on this computer. Either enable host networking for the container and leave this field empty, or serve personagent over HTTPS and enter that address.",
    agents_astrbot_connect: "Connect",
    agents_astrbot_update: "Update plugin",
    agents_astrbot_remove: "Disconnect",
    agents_astrbot_ask: "This copies the personagent plugin into {folder}, writes its settings there and starts the character. Continue?",
    agents_astrbot_ask_remove: "This deletes the personagent plugin folder and its settings file, including the reply lists, from {folder}. Continue?",
    agents_astrbot_done: "The plugin is installed. Restart AstrBot or reload its plugins to apply it.",
    agents_astrbot_removed: "The plugin is deleted. Restart AstrBot to unload it.",
    agents_allow_title: "Who it replies to",
    agents_allow_groups: "Group IDs",
    agents_allow_dms: "IDs of people it replies to in private chats",
    agents_allow_hint: "Separate IDs with commas, or enter * for all. Send /sid in a chat to see its ID. An empty field means it replies to no one.",
    agents_allow_save: "Save",
    agents_allow_saved: "Saved. Restart AstrBot to apply the change.",
    agents_bad_target: "This assistant is not supported.",
    agents_no_cli: "The claude command was not found on this computer. Install Claude Code, then try again.",
    agents_cli_failed: "Claude Code did not accept the change. Run claude once in a terminal to complete its setup, then try again.",
    agents_no_dsh: "DeepSeek Harness has no profile yet. Start it once, then try again.",
    agents_no_codex: "Codex was not found on this computer. Install it, then try again.",
    agents_no_react: "DeepSeek Harness does not support remarks yet.",
    agents_write_failed: "The settings file could not be written. Close any program that is using it, then try again.",
    agents_bad_cooldown: "Choose one of the listed intervals.",
    agents_not_astrbot: "No AstrBot was found in this folder. Choose the folder that contains its data folder (which holds cmd_config.json).",
    agents_astrbot_managed: "This is the AstrBot that this app runs for you. Connect a chat platform above instead.",
    agents_bad_url: "Enter an address that starts with https://, or an address on 127.0.0.1.",
    agents_not_connected: "The plugin is no longer in that AstrBot. Connect it again.",
    agents_bad_ids: "Separate IDs with commas. An ID cannot contain spaces.",
    agents_service_failed: "The character could not be started. Check the model settings, then try again.",
  },
  zh: {
    agents_title: "编程助手",
    agents_hint: "在本机的编程助手中与{name}对话。",
    agents_recheck: "重新检查",
    agents_checking: "正在检查…",
    agents_checked: "检查已完成。",
    agents_loading: "正在查找编程助手…",
    agents_load_failed: "无法读取本机的编程助手。",
    agents_desc_claude: "为本机当前用户的 Claude Code 添加两个工具：talk（与本页面为同一对话）和 character。",
    agents_desc_codex: "在 Codex 的 config.toml 文件中添加相同的两个工具。",
    agents_desc_dsh: "为 DeepSeek Harness 的每个配置添加相同的两个工具。",
    agents_state_missing: "未在本机找到",
    agents_state_missing_dsh: "未找到。请先启动一次 DeepSeek Harness，再点击「重新检查」。",
    agents_state_off: "未接入",
    agents_state_on: "已接入",
    agents_state_other: "已为其他文件夹或旧版本配置",
    agents_state_partial: "已在 {m} 个配置中的 {n} 个接入",
    agents_install_first: "请先安装，再点击「重新检查」。",
    agents_connect: "接入",
    agents_repair: "修复",
    agents_update: "更新",
    agents_remove: "移除",
    agents_connecting: "正在接入…",
    agents_removing: "正在移除…",
    agents_saving: "正在保存…",
    agents_ask_claude: "将运行 claude 命令，为本机当前用户的 Claude Code 添加 personagent。是否继续？",
    agents_ask_codex: "将在 Codex 的 config.toml 文件中添加 personagent 的设置。是否继续？",
    agents_ask_dsh: "将为 DeepSeek Harness 的每个配置添加 personagent。是否继续？",
    agents_ask_replace: "现有的设置将被替换。",
    agents_ask_remove: "将从 {target} 中移除{name}的 talk 和 character 两个工具。是否继续？",
    agents_ask_remove_react: "每轮结束时的评论也将关闭。",
    agents_removed: "已从 {target} 中移除。",
    agents_done_claude: "请在 Claude Code 中新建会话，并要求它与{name}对话。首次使用时，Claude Code 会询问是否允许该工具。",
    agents_done_codex: "请在 Codex 中新建会话，并要求它与{name}对话。",
    agents_done_dsh: "重启 DeepSeek Harness 后生效。",
    agents_react: "每轮结束时发表评论",
    agents_react_hint: "会将项目文件夹名称和助手最后一条回复的开头发送给你的模型服务，每条评论计一次模型调用。仅在本应用运行时显示评论。",
    agents_react_ask: "每轮结束时，项目文件夹名称和助手最后一条回复的开头将发送给你的模型服务。是否开启？",
    agents_react_yes: "开启",
    agents_react_on: "已开启评论。",
    agents_react_off: "已关闭评论。",
    agents_react_trust: "还需在 Codex 中输入 /hooks 并信任 personagent 钩子，否则不会显示评论。",
    agents_cooldown: "评论的最短间隔",
    agents_cool_600: "10 分钟",
    agents_cool_1800: "30 分钟",
    agents_cool_3600: "1 小时",
    agents_cool_7200: "2 小时",
    agents_cool_other: "{n} 分钟",
    agents_cooldown_saved: "已保存：最多每 {time}评论一次。",
    agents_astrbot_title: "接入已有的 AstrBot",
    agents_astrbot_hint: "将 personagent 插件安装到你自行运行的 AstrBot 中，由{name}回复其中的聊天。",
    agents_astrbot_folder: "AstrBot 文件夹",
    agents_astrbot_found: "已在此位置找到 AstrBot。如需使用其他 AstrBot，请修改文件夹。",
    agents_astrbot_none: "未在常用位置找到 AstrBot。请粘贴包含其 data 文件夹的文件夹路径。",
    agents_astrbot_connected: "已接入 {folder} 中的 AstrBot。",
    agents_astrbot_docker: "AstrBot 运行在 Docker 中或其他电脑上",
    agents_astrbot_url: "AstrBot 访问 personagent 的地址",
    agents_astrbot_url_hint: "Docker 容器无法访问本机的 127.0.0.1。请为容器启用主机网络并将此处留空，或为 personagent 配置 HTTPS 地址并填写在此处。",
    agents_astrbot_connect: "接入",
    agents_astrbot_update: "更新插件",
    agents_astrbot_remove: "断开",
    agents_astrbot_ask: "将把 personagent 插件复制到 {folder}，在其中写入插件设置，并启动角色。是否继续？",
    agents_astrbot_ask_remove: "将从 {folder} 中删除 personagent 插件文件夹及其设置文件（包括回复名单）。是否继续？",
    agents_astrbot_done: "插件已安装。请重启 AstrBot 或重新加载插件后生效。",
    agents_astrbot_removed: "插件已删除。请重启 AstrBot 以卸载该插件。",
    agents_allow_title: "回复对象",
    agents_allow_groups: "群号",
    agents_allow_dms: "私聊回复的用户号码",
    agents_allow_hint: "多个号码用逗号分隔，填写 * 表示全部。在聊天中发送 /sid 可查看号码。留空表示不回复任何人。",
    agents_allow_save: "保存",
    agents_allow_saved: "已保存。重启 AstrBot 后生效。",
    agents_bad_target: "不支持该助手。",
    agents_no_cli: "本机未找到 claude 命令。请安装 Claude Code 后重试。",
    agents_cli_failed: "Claude Code 未接受此次修改。请先在终端中运行一次 claude 完成其设置，然后重试。",
    agents_no_dsh: "DeepSeek Harness 尚无配置。请先启动一次，然后重试。",
    agents_no_codex: "本机未找到 Codex。请安装后重试。",
    agents_no_react: "DeepSeek Harness 暂不支持评论功能。",
    agents_write_failed: "无法写入设置文件。请关闭正在使用该文件的程序后重试。",
    agents_bad_cooldown: "请从列出的间隔中选择一项。",
    agents_not_astrbot: "该文件夹中没有 AstrBot。请选择包含其 data 文件夹（内有 cmd_config.json）的文件夹。",
    agents_astrbot_managed: "这是本应用为你运行的 AstrBot，请直接在上方连接平台。",
    agents_bad_url: "请填写以 https:// 开头的地址，或 127.0.0.1 上的地址。",
    agents_not_connected: "该 AstrBot 中已没有 personagent 插件，请重新接入。",
    agents_bad_ids: "号码之间请用逗号分隔，单个号码中不能包含空格。",
    agents_service_failed: "角色未能启动。请检查模型设置后重试。",
  },
});

(() => {
  const root = PA.$("agents-root");
  const NAMES = { "claude-code": "Claude Code", codex: "Codex", dsh: "DeepSeek Harness" };
  const SHORT = { "claude-code": "claude", codex: "codex", dsh: "dsh" };
  let data = null;
  let loadError = false;
  // Kept as keys and codes, translated at render, so they follow a language change.
  const notes = {};
  const errors = {};
  const draft = { folder: null, url: null, docker: null, groups: null, dms: null };
  let astrbotNote = "";
  let astrbotError = "";
  let allowError = "";
  let open = false;
  // Ids to give focus back to when the control used last is gone or was disabled.
  let returnTo = null;

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const name = () => data?.name || PA.state?.name || "";
  const idOf = (item, part) => `agents-${SHORT[item.id]}-${part}`;

  async function load() {
    try {
      data = await PA.api("agents");
      loadError = false;
    } catch {
      loadError = true;
    }
    render();
  }

  // Disable the button with an "-ing" label while `work` runs.
  async function busy(button, label, work, fallback = []) {
    const was = button.textContent;
    returnTo = [button.id, ...fallback];
    button.disabled = true;
    button.textContent = PA.t(label);
    try {
      await work();
    } finally {
      button.disabled = false;
      if (button.isConnected) button.textContent = was;
    }
  }

  async function change(item, connect, react, button, label, fallback) {
    errors[item.id] = "";
    await busy(button, label, async () => {
      try {
        data = await PA.api("agents/coding", { target: item.id, connect, react });
      } catch (error) {
        errors[item.id] = error.message;
      }
    }, fallback);
    return !errors[item.id];
  }

  async function connect(item, button, key) {
    let question = PA.t(`agents_ask_${SHORT[item.id]}`);
    if (item.state === "other") question += " " + PA.t("agents_ask_replace");
    if (!(await PA.ask(question, PA.t(key)))) return;
    notes[item.id] = [];
    const react = item.react === null ? false : item.react;
    if (await change(item, true, react, button, "agents_connecting",
                     [idOf(item, "react"), idOf(item, "remove")])) {
      notes[item.id] = [`agents_done_${SHORT[item.id]}`];
      if (item.id === "codex" && react) notes[item.id].push("agents_react_trust");
    }
    render();
  }

  async function remove(item, button) {
    const target = NAMES[item.id];
    let question = PA.t("agents_ask_remove", { name: name(), target });
    if (item.react) question += " " + PA.t("agents_ask_remove_react");
    if (!(await PA.ask(question, PA.t("agents_remove")))) return;
    notes[item.id] = [];
    if (await change(item, false, false, button, "agents_removing", [idOf(item, "connect")]))
      PA.toast(PA.t("agents_removed", { target }));
    render();
  }

  async function toggleReact(item, box) {
    const on = box.checked;
    if (on && !(await PA.ask(PA.t("agents_react_ask"), PA.t("agents_react_yes")))) {
      box.checked = false;
      return;
    }
    returnTo = [box.id];
    box.disabled = true;
    errors[item.id] = "";
    try {
      data = await PA.api("agents/coding", { target: item.id, connect: true, react: on });
      notes[item.id] = on && item.id === "codex" ? ["agents_react_trust"] : [];
      PA.toast(PA.t(on ? "agents_react_on" : "agents_react_off"));
    } catch (error) {
      errors[item.id] = error.message;
    }
    render();
  }

  function stateText(item) {
    if (!item.installed)
      return PA.t(item.id === "dsh" ? "agents_state_missing_dsh" : "agents_state_missing");
    if (item.state === "partial")
      return PA.t("agents_state_partial", { n: item.connected, m: item.profiles });
    return PA.t(`agents_state_${item.state}`);
  }

  function noteBox(text) {
    const note = make("p", "agents-done", text);
    note.setAttribute("role", "status");
    return note;
  }

  function errorBox(code) {
    const error = make("div", "error", code ? PA.t(code) : "");
    error.setAttribute("role", "alert");
    error.hidden = !code;
    return error;
  }

  function row(item) {
    const box = make("div", "feature agents-row");
    box.dataset.agent = item.id;
    const head = make("div", "feature-head");
    head.append(make("strong", "", NAMES[item.id]));
    const state = make("span", "feature-state agents-state", stateText(item));
    state.classList.toggle("agents-on", item.state === "on");
    head.append(state);
    box.append(head);
    box.append(make("p", "field-note", PA.t(`agents_desc_${SHORT[item.id]}`)));
    const usable = item.installed;
    if (!usable && item.id !== "dsh")
      box.append(make("p", "field-note", PA.t("agents_install_first")));
    const linked = item.state !== "off";
    if (usable && item.state === "on" && item.react !== null) {
      const label = make("label", "check agents-react");
      const check = make("input");
      check.type = "checkbox";
      check.id = idOf(item, "react");
      check.checked = item.react;
      check.addEventListener("change", () => toggleReact(item, check));
      label.append(check, make("span", "", PA.t("agents_react")));
      box.append(label, make("p", "field-note agents-react-hint", PA.t("agents_react_hint")));
    }
    if (notes[item.id]?.length)
      box.append(noteBox(notes[item.id].map((key) => PA.t(key, { name: name() })).join(" ")));
    if (errors[item.id]) box.append(errorBox(errors[item.id]));
    if (usable) {
      const actions = make("div", "agents-actions");
      if (item.state !== "on") {
        const key = item.state === "other" ? "agents_repair"
          : item.state === "partial" ? "agents_update" : "agents_connect";
        const go = make("button", "secondary agents-connect", PA.t(key));
        go.type = "button";
        go.id = idOf(item, "connect");
        go.addEventListener("click", () => connect(item, go, key));
        actions.append(go);
      }
      if (linked) {
        const off = make("button", "quiet agents-remove", PA.t("agents_remove"));
        off.type = "button";
        off.id = idOf(item, "remove");
        off.addEventListener("click", () => remove(item, off));
        actions.append(off);
      }
      box.append(actions);
    }
    return box;
  }

  function cooldownRow() {
    const box = make("div", "feature agents-cooldown");
    const label = make("label", "", PA.t("agents_cooldown"));
    label.htmlFor = "agents-cooldown";
    const select = make("select");
    select.id = "agents-cooldown";
    for (const seconds of data.cooldowns) {
      const option = make("option", "", PA.t(`agents_cool_${seconds}`));
      option.value = String(seconds);
      select.append(option);
    }
    // A hand-written value stays shown until something else is picked.
    if (!data.cooldowns.includes(data.cooldown)) {
      const option = make("option", "", PA.t("agents_cool_other", { n: String(Math.round(data.cooldown / 60)) }));
      option.value = String(data.cooldown);
      select.append(option);
    }
    select.value = String(data.cooldown);
    const error = errorBox("");
    select.addEventListener("change", async () => {
      returnTo = [select.id];
      select.disabled = true;
      error.hidden = true;
      const seconds = Number(select.value);
      try {
        data = await PA.api("agents/cooldown", { seconds });
        PA.toast(PA.t("agents_cooldown_saved", { time: PA.t(`agents_cool_${seconds}`) }));
        render();
      } catch (failure) {
        select.value = String(data.cooldown);
        error.textContent = PA.t(failure.message);
        error.hidden = false;
      } finally {
        select.disabled = false;
      }
    });
    box.append(label, select, error);
    return box;
  }

  function field(id, text, value, onInput) {
    const label = make("label", "", text);
    label.htmlFor = id;
    const input = make("input");
    input.id = id;
    input.autocomplete = "off";
    input.spellcheck = false;
    input.value = value;
    input.addEventListener("input", () => onInput(input.value));
    return [label, input];
  }

  async function astrbotCall(path, payload, button, label, fallback) {
    astrbotError = "";
    let ok = false;
    await busy(button, label, async () => {
      try {
        data = await PA.api(path, payload);
        ok = true;
      } catch (error) {
        astrbotError = error.message;
      }
    }, fallback);
    return ok;
  }

  function astrbot() {
    const info = data.astrbot;
    const details = make("details", "agents-astrbot");
    details.id = "agents-astrbot";
    details.open = open;
    details.addEventListener("toggle", () => (open = details.open));
    const summary = make("summary", "", PA.t("agents_astrbot_title"));
    summary.id = "agents-astrbot-summary";
    details.append(summary);
    details.append(make("p", "field-note", PA.t("agents_astrbot_hint", { name: name() })));
    const folder = draft.folder ?? info.folder;
    if (info.connected)
      details.append(make("p", "agents-done", PA.t("agents_astrbot_connected", { folder: info.folder })));
    const [folderLabel, folderInput] = field("agents-folder", PA.t("agents_astrbot_folder"), folder,
      (value) => (draft.folder = value));
    details.append(folderLabel, folderInput);
    if (!info.connected)
      details.append(make("p", "field-note",
        PA.t(info.folder ? "agents_astrbot_found" : "agents_astrbot_none")));
    const docker = draft.docker ?? (info.docker || !!info.url);
    const dockerLabel = make("label", "check agents-docker");
    const dockerBox = make("input");
    dockerBox.type = "checkbox";
    dockerBox.id = "agents-docker";
    dockerBox.checked = docker;
    dockerLabel.append(dockerBox, make("span", "", PA.t("agents_astrbot_docker")));
    const urlPart = make("div", "agents-url");
    urlPart.hidden = !docker;
    const [urlLabel, urlInput] = field("agents-url", PA.t("agents_astrbot_url"), draft.url ?? info.url,
      (value) => (draft.url = value));
    urlInput.type = "url";
    urlInput.placeholder = "https://";
    urlPart.append(urlLabel, urlInput, make("p", "field-note", PA.t("agents_astrbot_url_hint")));
    dockerBox.addEventListener("change", () => {
      draft.docker = dockerBox.checked;
      urlPart.hidden = !dockerBox.checked;
    });
    details.append(dockerLabel, urlPart);
    if (astrbotNote) details.append(noteBox(PA.t(astrbotNote)));
    details.append(errorBox(astrbotError));
    const actions = make("div", "agents-actions");
    // The one dark button: connecting first, saving the reply lists once connected.
    const goKey = info.connected ? "agents_astrbot_update" : "agents_astrbot_connect";
    const go = make("button", info.connected ? "secondary agents-astrbot-connect" : "primary small agents-astrbot-connect",
      PA.t(goKey));
    go.type = "button";
    go.id = "agents-astrbot-connect";
    go.addEventListener("click", async () => {
      const where = folderInput.value.trim();
      if (!(await PA.ask(PA.t("agents_astrbot_ask", { folder: where }), PA.t(goKey))))
        return;
      astrbotNote = "";
      const url = dockerBox.checked ? urlInput.value.trim() : "";
      if (await astrbotCall("agents/astrbot", { dataDir: where, url }, go, "agents_connecting")) {
        astrbotNote = "agents_astrbot_done";
        draft.folder = null;
      }
      render();
    });
    actions.append(go);
    if (info.connected) {
      const off = make("button", "quiet agents-astrbot-remove", PA.t("agents_astrbot_remove"));
      off.type = "button";
      off.id = "agents-astrbot-remove";
      off.addEventListener("click", async () => {
        if (!(await PA.ask(PA.t("agents_astrbot_ask_remove", { folder: info.folder }), PA.t("agents_astrbot_remove"))))
          return;
        astrbotNote = "";
        if (await astrbotCall("agents/astrbot/remove", { dataDir: info.folder }, off, "agents_removing",
                              ["agents-astrbot-connect"])) {
          PA.toast(PA.t("agents_astrbot_removed"));
          draft.groups = draft.dms = null;
        }
        render();
      });
      actions.append(off);
    }
    details.append(actions);
    if (info.connected) details.append(allowList(info));
    return details;
  }

  function allowList(info) {
    const box = make("div", "agents-allow");
    box.append(make("div", "feature-head", PA.t("agents_allow_title")));
    box.append(make("p", "field-note", PA.t("agents_allow_hint")));
    const [groupsLabel, groupsInput] = field("agents-groups", PA.t("agents_allow_groups"),
      draft.groups ?? info.groups.join(", "), (value) => (draft.groups = value));
    const [dmsLabel, dmsInput] = field("agents-dms", PA.t("agents_allow_dms"),
      draft.dms ?? info.dmUsers.join(", "), (value) => (draft.dms = value));
    box.append(groupsLabel, groupsInput, dmsLabel, dmsInput, errorBox(allowError));
    const actions = make("div", "card-actions");
    const save = make("button", "primary small agents-allow-save", PA.t("agents_allow_save"));
    save.type = "button";
    save.id = "agents-allow-save";
    save.addEventListener("click", async () => {
      allowError = "";
      await busy(save, "agents_saving", async () => {
        try {
          data = await PA.api("agents/astrbot/allow", {
            dataDir: info.folder, groups: groupsInput.value, dmUsers: dmsInput.value,
          });
          draft.groups = draft.dms = null;
          PA.toast(PA.t("agents_allow_saved"));
        } catch (error) {
          allowError = error.message;
        }
      });
      render();
    });
    actions.append(save);
    box.append(actions);
    return box;
  }

  function render() {
    const head = make("div", "group-head agents-head");
    head.append(make("h3", "group-title", PA.t("agents_title")));
    head.append(make("p", "group-hint", PA.t("agents_hint", { name: name() })));
    const again = make("button", "quiet agents-recheck", PA.t("agents_recheck"));
    again.type = "button";
    again.id = "agents-recheck";
    again.addEventListener("click", () =>
      busy(again, "agents_checking", async () => {
        await load();
        if (!loadError) PA.toast(PA.t("agents_checked"));
      }),
    );
    head.append(again);
    const parts = [head];
    if (!data) {
      const note = make("p", "field-note", PA.t(loadError ? "agents_load_failed" : "agents_loading"));
      note.setAttribute("role", loadError ? "alert" : "status");
      parts.push(note);
    } else {
      const list = make("div", "agents-list");
      for (const item of data.coding) list.append(row(item));
      if (data.coding.some((item) => item.state === "on" && item.react)) list.append(cooldownRow());
      parts.push(list, astrbot());
    }
    // Focus stays on the control the person used; a disabled one has already dropped it.
    const active = document.activeElement;
    const wanted = active && root.contains(active) && active.id ? [active.id, ...(returnTo || [])]
      : !active || active === document.body ? returnTo || [] : [];
    returnTo = null;
    root.replaceChildren(...parts);
    for (const id of wanted) {
      const target = id && PA.$(id);
      if (target && root.contains(target)) {
        target.focus();
        break;
      }
    }
  }

  PA.onShow("platforms", load);
  PA.onLanguage(() => data && render());
  render();
})();
