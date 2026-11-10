// The practice panel: a scripted demo and a practice group. See PA at the end of welcome.js.
PA.strings({
  en: {
    practice_tab_demo: "Demo",
    practice_tab_group: "Practice group",
    practice_demo_lead: "Three short scenes played with a scripted model: when the character stays silent, how it learns from a correction, and how it refuses a disruptive member. No key is needed, and nothing is sent over the network.",
    practice_scene_quiet: "Staying silent",
    practice_scene_teach: "Learning from a correction",
    practice_scene_troll: "Refusing a disruptive member",
    practice_play: "Play",
    practice_playing: "Playing…",
    practice_loading: "Loading…",
    practice_replay: "Replay",
    practice_next: "Next scene",
    practice_demo_ready: "Select Play to watch this scene.",
    practice_demo_done: "The demo is complete. You can try the same steps in the practice group.",
    practice_try_group: "Open the practice group",
    practice_group_lead: "A simulated group chat with {name}. You can write as different members, see when the character replies or stays silent, and view the reason for each decision. What the character learns here is used only in practice and does not affect your real chats.",
    practice_group_hint: "Include “{name}” in a message to address the character. When it is not addressed, it considers joining in about every 4 messages.",
    practice_starting: "Starting the practice group…",
    practice_retry: "Try again",
    practice_open_settings: "Open Character & settings",
    practice_empty: "No messages yet. Choose who is writing and send the first message.",
    practice_speaking_as: "Write as",
    practice_owner: "You (admin)",
    practice_member_1: "Alex",
    practice_member_2: "Sam",
    practice_member_3: "Priya",
    practice_message: "Write a message to the group",
    practice_send: "Send",
    practice_sending: "Sending…",
    practice_why: "Show reason",
    practice_why_busy: "Loading…",
    practice_reply: "Reply",
    practice_replying: "Replying to {name}: “{text}”",
    practice_cancel: "Cancel",
    practice_second_try: "second attempt",
    practice_quiet: "{name} did not reply: {reason}",
    practice_joins: "{name} joined in: {reason}",
    practice_memory_saved: "{name} saved this as a memory.",
    practice_memory_refused: "{name} did not save this. Memory stores facts, not instructions.",
    practice_learning: "Learning: {text}",
    practice_why_named: "{who} addressed the character, so it replied.",
    practice_why_admin: "The admin addressed the character, so it replied.",
    practice_why_joined: "No one addressed the character. It joined in after the message from {who}: {reason}",
    practice_why_quiet: "The character did not reply to the message from {who}: {reason}",
    practice_why_memory: "{who} asked the character to remember or forget something, so it handled the request directly without calling the model.",
    practice_why_failed: "The model did not respond to this message, so the character did not reply.",
    practice_why_retry: "This is a second attempt. The first reply, “{text}”, was rejected.",
    practice_why_learning: "Learned from this message: {text}",
    practice_why_offered_none: "No earlier learning was used for this reply.",
    practice_why_offered: "Earlier learning used for this reply:",
    practice_why_ledger_none: "No member has responded to this reply yet. Select Reply to correct it.",
    practice_why_ledger: "Responses to this reply:",
    practice_learned_open: "Show what was learned",
    practice_learned_hide: "Hide what was learned",
    practice_learned_busy: "Loading…",
    practice_learned_none: "Nothing has been learned in practice yet. Reply to one of the character's messages to correct it, then respond to its second attempt.",
    practice_reset: "Reset practice group",
    practice_resetting: "Resetting…",
    practice_reset_ask: "Reset the practice group? This deletes all practice data: the messages in the practice group, what the character learned in practice, and the memories saved in practice. Your real chats are not affected.",
    practice_reset_yes: "Reset",
    practice_reset_done: "The practice group has been reset.",
    practice_fail_auth: "The model service rejected the key. Check the key under Character & settings.",
    practice_fail_request: "The model service rejected the request. Check the model name under Character & settings.",
    practice_fail_rate_limit: "The model service is busy, or the account has no credit left. Wait a moment and try again.",
    practice_fail_unreachable: "The model service cannot be reached. Check the service address under Character & settings, and check your network connection.",
    practice_fail_server: "The model service returned an error. Try again later.",
    practice_fail_other: "The model call failed. Try again, or check the model under Character & settings.",
    practice_needs_key: "The practice group requires a model. Connect a model service under Character & settings first.",
    practice_failed: "The practice group has stopped. Select Try again. If the problem continues, check the model under Character & settings.",
    practice_busy: "The previous message is still being processed. Send again after it finishes.",
    practice_invalid: "The message is empty or too long. The limit is 2000 characters.",
    practice_gone: "This message is from before the practice group restarted. Select a more recent message.",
    practice_demo_failed: "The demo could not be loaded. Try again.",
    practice_timeout: "The model did not respond in time. Try again.",
  },
  zh: {
    practice_tab_demo: "演示",
    practice_tab_group: "模拟群聊",
    practice_demo_lead: "以下三个场景由预设脚本的模型演示：角色何时保持沉默、如何从一次纠正中学习、如何拒绝干扰者。演示无需密钥，也不会向外发送任何数据。",
    practice_scene_quiet: "保持沉默",
    practice_scene_teach: "从纠正中学习",
    practice_scene_troll: "拒绝干扰",
    practice_play: "播放",
    practice_playing: "正在播放…",
    practice_loading: "正在加载…",
    practice_replay: "重新播放",
    practice_next: "下一场景",
    practice_demo_ready: "点击「播放」观看此场景。",
    practice_demo_done: "演示已结束。你可以在模拟群聊中亲自尝试。",
    practice_try_group: "打开模拟群聊",
    practice_group_lead: "这是一个包含{name}的模拟群聊。你可以以不同成员的身份发言，观察角色何时回复、何时保持沉默，并查看每次判断的原因。角色在此学到的内容仅用于演练，不会影响真实聊天。",
    practice_group_hint: "在消息中提及「{name}」即可点名角色；未被点名时，角色大约每 4 条消息考虑一次是否发言。",
    practice_starting: "正在启动模拟群聊…",
    practice_retry: "重试",
    practice_open_settings: "打开「角色与设置」",
    practice_empty: "暂无消息。请选择发言身份并发送第一条消息。",
    practice_speaking_as: "发言身份",
    practice_owner: "你（管理员）",
    practice_member_1: "小林",
    practice_member_2: "阿杰",
    practice_member_3: "小美",
    practice_message: "输入发送到群聊的消息",
    practice_send: "发送",
    practice_sending: "正在发送…",
    practice_why: "查看原因",
    practice_why_busy: "正在加载…",
    practice_reply: "回复",
    practice_replying: "正在回复{name}：「{text}」",
    practice_cancel: "取消",
    practice_second_try: "第二次尝试",
    practice_quiet: "{name}未回复：{reason}",
    practice_joins: "{name}主动参与了对话：{reason}",
    practice_memory_saved: "{name}已将此内容保存为记忆。",
    practice_memory_refused: "{name}未保存此内容：记忆只保存事实，不保存指令。",
    practice_learning: "学习记录：{text}",
    practice_why_named: "{who}点名了角色，因此角色作出回复。",
    practice_why_admin: "管理员点名了角色，因此角色作出回复。",
    practice_why_joined: "无人点名角色，角色在{who}发言后主动参与：{reason}",
    practice_why_quiet: "{who}发言后，角色未回复：{reason}",
    practice_why_memory: "{who}要求角色记住或忘记某件事，角色直接处理了该请求，未调用模型。",
    practice_why_failed: "模型未响应此消息，因此角色没有回复。",
    practice_why_retry: "此回复是第二次尝试，第一次的回复「{text}」已被否定。",
    practice_why_learning: "从此消息中学到：{text}",
    practice_why_offered_none: "此回复未使用之前学到的内容。",
    practice_why_offered: "此回复使用了以下已学内容：",
    practice_why_ledger_none: "尚无成员对此回复作出反应。点击「回复」即可纠正此回复。",
    practice_why_ledger: "成员对此回复的反应：",
    practice_learned_open: "查看已学内容",
    practice_learned_hide: "收起已学内容",
    practice_learned_busy: "正在加载…",
    practice_learned_none: "演练中尚未学到任何内容。请先回复角色的某条消息以纠正它，再对角色的第二次尝试作出反应。",
    practice_reset: "重置模拟群聊",
    practice_resetting: "正在重置…",
    practice_reset_ask: "确定重置模拟群聊？此操作将删除全部演练数据：模拟群聊中的消息、角色在演练中学到的内容，以及在演练中保存的记忆。真实聊天不受影响。",
    practice_reset_yes: "重置",
    practice_reset_done: "模拟群聊已重置。",
    practice_fail_auth: "模型服务拒绝了该密钥。请在「角色与设置」中检查密钥。",
    practice_fail_request: "模型服务拒绝了该请求。请在「角色与设置」中检查模型名称。",
    practice_fail_rate_limit: "模型服务繁忙，或账户额度已用尽。请稍后重试。",
    practice_fail_unreachable: "无法连接模型服务。请在「角色与设置」中检查服务地址，并检查网络连接。",
    practice_fail_server: "模型服务返回了错误。请稍后重试。",
    practice_fail_other: "模型调用失败。请重试，或在「角色与设置」中检查模型。",
    practice_needs_key: "模拟群聊需要模型才能运行。请先在「角色与设置」中连接模型服务。",
    practice_failed: "模拟群聊已停止。请点击「重试」；如问题持续，请在「角色与设置」中检查模型。",
    practice_busy: "上一条消息仍在处理中，请在处理完成后再发送。",
    practice_invalid: "消息为空或过长，最多 2000 个字符。",
    practice_gone: "此消息来自模拟群聊重启之前，请选择更新的消息。",
    practice_demo_failed: "演示加载失败，请重试。",
    practice_timeout: "模型响应超时，请重试。",
  },
});

(() => {
  const root = PA.$("practice-root");
  const SCENES = ["quiet", "teach", "troll"];
  const MEMBERS = ["practice_member_1", "practice_member_2", "practice_member_3"];
  const BEAT_DELAY = 750;
  const NOTE_DELAY = 350;
  const BOX_MAX = 120;

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const button = (className, key, id) => {
    const node = el("button", className);
    node.type = "button";
    node.id = id;
    node.dataset.key = key;
    node.textContent = PA.t(key);
    return node;
  };
  // A message shown after an action; its key is kept so it follows a language change.
  const notice = (node, key) => {
    node.dataset.key = key;
    node.textContent = PA.t(key);
    node.hidden = false;
  };
  const focusLost = () => !document.activeElement || document.activeElement === document.body;
  // A button's own label again, after a "...ing" one.
  const relabel = (node) => (node.textContent = PA.t(node.dataset.key));
  const working = (node, key) => {
    // Disabling a focused button drops its focus; done() gives it back.
    if (document.activeElement === node) node.dataset.focused = "1";
    node.disabled = true;
    node.textContent = PA.t(key);
  };
  const done = (node) => {
    node.disabled = false;
    relabel(node);
    if (node.dataset.focused && !node.hidden && focusLost()) node.focus();
    delete node.dataset.focused;
  };
  const store = {
    get(key) {
      try {
        return localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, value);
      } catch {
        /* per-viewer convenience only */
      }
    },
  };
  const name = () => groupName || PA.state?.name || "";

  // ---- the layout --------------------------------------------------------
  const tabs = el("div", "practice-tabs");
  tabs.setAttribute("role", "tablist");
  const demoTab = button("practice-tab", "practice_tab_demo", "practice-tab-demo");
  const groupTab = button("practice-tab", "practice_tab_group", "practice-tab-group");
  for (const tab of [demoTab, groupTab]) tab.setAttribute("role", "tab");
  tabs.append(demoTab, groupTab);

  const demoPart = el("div", "practice-part");
  demoPart.id = "practice-demo";
  const demoLead = el("p", "field-note");
  demoLead.dataset.key = "practice_demo_lead";
  const sceneBar = el("div", "practice-scenes");
  const sceneButtons = SCENES.map((key) => {
    const node = button("practice-scene", `practice_scene_${key}`, `practice-scene-${key}`);
    node.dataset.scene = key;
    sceneBar.append(node);
    return node;
  });
  const sceneTitle = el("h2", "practice-scene-title");
  const sceneIntro = el("p", "field-note");
  const demoLog = el("div", "practice-log");
  demoLog.id = "practice-demo-log";
  demoLog.setAttribute("aria-live", "polite");
  const demoStatus = el("p", "practice-status");
  demoStatus.id = "practice-demo-status";
  demoStatus.setAttribute("role", "status");
  const demoError = el("p", "error");
  demoError.id = "practice-demo-error";
  demoError.setAttribute("role", "alert");
  demoError.hidden = true;
  const demoActions = el("div", "card-actions practice-actions");
  const replay = button("secondary", "practice_replay", "practice-replay");
  const next = button("secondary", "practice_next", "practice-next");
  const play = button("primary small", "practice_play", "practice-play");
  const toGroup = button("secondary", "practice_try_group", "practice-to-group");
  demoActions.append(replay, toGroup, next, play);
  demoPart.append(demoLead, sceneBar, sceneTitle, sceneIntro, demoLog, demoStatus, demoError, demoActions);

  const groupPart = el("div", "practice-part");
  groupPart.id = "practice-group";
  const groupLead = el("p", "field-note");
  const groupHint = el("p", "field-note practice-hint");
  const groupStatus = el("p", "practice-status");
  groupStatus.id = "practice-status";
  groupStatus.setAttribute("role", "status");
  const groupError = el("div", "error practice-error");
  groupError.id = "practice-error";
  groupError.hidden = true;
  const groupErrorText = el("span");
  groupErrorText.id = "practice-error-text";
  groupErrorText.setAttribute("role", "alert");
  const groupRetry = button("quiet", "practice_retry", "practice-retry");
  const groupSettings = button("quiet", "practice_open_settings", "practice-settings");
  groupError.append(groupErrorText, groupRetry, groupSettings);
  const groupLog = el("div", "practice-log practice-group-log");
  groupLog.id = "practice-group-log";
  groupLog.setAttribute("aria-live", "polite");
  const groupEmpty = el("p", "practice-empty");
  groupEmpty.dataset.key = "practice_empty";
  const replying = el("div", "practice-replying");
  replying.id = "practice-replying";
  replying.hidden = true;
  const replyingText = el("span");
  const replyCancel = button("quiet", "practice_cancel", "practice-reply-cancel");
  replying.append(replyingText, replyCancel);
  const form = el("form", "practice-composer");
  form.id = "practice-form";
  const asLabel = el("label", "practice-as-label");
  asLabel.htmlFor = "practice-as";
  asLabel.dataset.key = "practice_speaking_as";
  const asPick = el("select");
  asPick.id = "practice-as";
  const box = el("div", "composer practice-box");
  const boxLabel = el("label", "sr-only");
  boxLabel.htmlFor = "practice-message";
  boxLabel.dataset.key = "practice_message";
  const input = el("textarea");
  input.id = "practice-message";
  input.rows = 1;
  input.maxLength = 2000;
  const send = el("button", "primary small");
  send.type = "submit";
  send.id = "practice-send";
  send.dataset.key = "practice_send";
  box.append(boxLabel, input, send);
  const asRow = el("div", "practice-as-row");
  asRow.append(asLabel, asPick);
  form.append(asRow, box);
  const sendError = el("p", "error");
  sendError.id = "practice-send-error";
  sendError.setAttribute("role", "alert");
  sendError.hidden = true;
  const tools = el("div", "card-actions practice-tools");
  const learnedButton = button("secondary", "practice_learned_open", "practice-learned-button");
  const resetButton = button("quiet", "practice_reset", "practice-reset");
  tools.append(learnedButton, resetButton);
  const learnedBox = el("div", "practice-learned");
  learnedBox.id = "practice-learned";
  learnedBox.setAttribute("role", "status");
  learnedBox.hidden = true;
  groupPart.append(groupLead, groupHint, groupStatus, groupError, groupLog, replying, form, sendError,
    tools, learnedBox);

  root.append(tabs, demoPart, groupPart);

  // ---- tabs ----------------------------------------------------------------
  let part = store.get("personagent-practice-part") === "group" ? "group" : "demo";
  function showPart(next) {
    store.set("personagent-practice-part", next);
    applyPart(next);
    if (next === "group") openGroup();
  }
  function applyPart(next) {
    part = next;
    demoPart.hidden = next !== "demo";
    groupPart.hidden = next !== "group";
    demoTab.classList.toggle("active", next === "demo");
    groupTab.classList.toggle("active", next === "group");
    demoTab.setAttribute("aria-selected", String(next === "demo"));
    groupTab.setAttribute("aria-selected", String(next === "group"));
  }
  demoTab.addEventListener("click", () => showPart("demo"));
  groupTab.addEventListener("click", () => showPart("group"));

  // ---- the demo ------------------------------------------------------------
  let demo = null,
    demoLang = "",
    scene = 0,
    played = new Set(),
    playToken = 0,
    playing = false;

  function line(who, text, kind) {
    const row = el("div", `practice-line ${kind}`);
    row.append(el("div", "practice-who", who), el("div", "practice-bubble", text));
    return row;
  }
  function beatNode(beat) {
    if (beat.kind === "say") return line(beat.who, beat.text, "member");
    if (beat.kind === "bot") return line(beat.who, beat.text, "bot");
    if (beat.kind === "note") return el("div", "practice-note", beat.text);
    if (beat.kind === "check") {
      const row = el("div", `practice-check${beat.ok ? " ok" : ""}`);
      row.append(el("span", "practice-mark", beat.ok ? "✓" : "○"), el("span", "", beat.text));
      return row;
    }
    return el("div", "practice-info", beat.text || "");
  }
  function renderScene() {
    const key = SCENES[scene];
    for (const node of sceneButtons) {
      const on = node.dataset.scene === key;
      node.classList.toggle("active", on);
      node.setAttribute("aria-pressed", String(on));
    }
    const data = demo && demo[scene];
    sceneTitle.textContent = data ? data.title.charAt(0).toUpperCase() + data.title.slice(1) : PA.t(`practice_scene_${key}`);
    sceneIntro.textContent = data ? data.intro : "";
    sceneIntro.hidden = !data;
    const seen = played.has(scene);
    play.hidden = seen && !playing;
    replay.hidden = !seen && !playing;
    next.hidden = scene === SCENES.length - 1;
    toGroup.hidden = !(scene === SCENES.length - 1 && seen && !playing);
    const status = seen && !playing && scene === SCENES.length - 1 ? "practice_demo_done" : !seen && !playing ? "practice_demo_ready" : "";
    demoStatus.dataset.key = status;
    demoStatus.textContent = status ? PA.t(status) : "";
    demoStatus.hidden = !status;
    if (!playing) relabel(play);
    play.disabled = playing;
  }
  async function loadDemo() {
    if (demo && demoLang === PA.lang) return true;
    working(play, "practice_loading");
    demoError.hidden = true;
    try {
      const value = await PA.api("practice/demo", { lang: PA.lang });
      demo = value.scenes;
      demoLang = PA.lang;
      return true;
    } catch (error) {
      notice(demoError, error.message === "generic" ? "practice_demo_failed" : error.message);
      return false;
    } finally {
      done(play);
    }
  }
  async function playScene(index) {
    const token = ++playToken;
    const hadFocus = demoActions.contains(document.activeElement);
    scene = index;
    demoLog.replaceChildren();
    if (!(await loadDemo()) || token !== playToken) {
      renderScene();
      return;
    }
    playing = true;
    renderScene();
    working(play, "practice_playing");
    for (const beat of demo[index].beats) {
      await new Promise((resolve) => setTimeout(resolve, beat.kind === "say" || beat.kind === "bot" ? BEAT_DELAY : NOTE_DELAY));
      if (token !== playToken) return;
      demoLog.append(beatNode(beat));
      demoLog.scrollTop = demoLog.scrollHeight;
    }
    playing = false;
    played.add(index);
    renderScene();
    delete play.dataset.focused;
    // Play hides once the scene is over; keep the keyboard in the same row.
    if (hadFocus && focusLost()) [toGroup, next, replay].find((node) => !node.hidden)?.focus();
  }
  function pickScene(index) {
    playToken++;
    playing = false;
    scene = index;
    demoLog.replaceChildren();
    renderScene();
  }
  play.addEventListener("click", () => playScene(scene));
  replay.addEventListener("click", () => playScene(scene));
  next.addEventListener("click", () => playScene(Math.min(scene + 1, SCENES.length - 1)));
  toGroup.addEventListener("click", () => {
    showPart("group");
    groupTab.focus();
  });
  sceneButtons.forEach((node, index) => node.addEventListener("click", () => pickScene(index)));

  // ---- the practice group -------------------------------------------------
  let groupName = "",
    starting = false,
    started = false,
    sending = false,
    quoting = null,
    learnedOpen = false;
  const entries = new Map();

  function memberOptions() {
    const chosen = asPick.value || store.get("personagent-practice-as") || "m1";
    asPick.replaceChildren();
    const owner = el("option", "", PA.t("practice_owner"));
    owner.value = "owner";
    asPick.append(owner);
    MEMBERS.forEach((key, index) => {
      const option = el("option", "", PA.t(key));
      option.value = `m${index + 1}`;
      asPick.append(option);
    });
    asPick.value = chosen;
  }
  asPick.addEventListener("change", () => store.set("personagent-practice-as", asPick.value));

  function fitBox() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, BOX_MAX)}px`;
    input.style.overflowY = input.scrollHeight > BOX_MAX ? "auto" : "hidden";
  }
  input.addEventListener("input", fitBox);

  function showGroupError(code) {
    notice(groupErrorText, code);
    groupSettings.hidden = !["practice_needs_key", "practice_fail_auth", "practice_fail_request"].includes(code);
    groupRetry.hidden = code === "practice_needs_key";
    groupError.hidden = false;
  }
  function setReady(ready) {
    input.disabled = !ready;
    asPick.disabled = !ready;
    send.disabled = !ready || sending;
    learnedButton.disabled = !ready;
    resetButton.disabled = !ready;
  }
  function caption(text, className = "practice-note") {
    return el("div", className, text);
  }
  function whyButton(entry, row) {
    const node = button("quiet practice-link practice-why-button", "practice_why", `practice-why-${entry.id}`);
    node.addEventListener("click", () => toggleWhy(entry, row, node));
    return node;
  }
  function renderEntry(entry) {
    entries.set(entry.id, entry);
    const row = el("div", "practice-entry");
    row.dataset.id = entry.id;
    if (entry.kind === "reply") {
      const said = line(name(), entry.text, "bot");
      if (entry.retry) said.querySelector(".practice-who").append(el("span", "practice-tag", PA.t("practice_second_try")));
      row.append(said);
      const actions = el("div", "practice-line-actions");
      actions.append(whyButton(entry, row));
      if (entry.quotable) {
        const reply = button("quiet practice-link practice-reply-button", "practice_reply", `practice-reply-${entry.id}`);
        reply.addEventListener("click", () => quote(entry));
        actions.append(reply);
      }
      row.append(actions);
      return row;
    }
    const said = line(entry.owner ? PA.t("practice_owner") : entry.name, entry.text, entry.owner ? "member owner" : "member");
    if (entry.quote) said.insertBefore(el("div", "practice-quoted", `“${entry.quote}”`), said.lastChild);
    row.append(said);
    const notes = el("div", "practice-line-actions");
    if (entry.failure) notes.append(caption(PA.t(`practice_fail_${entry.failure}`), "practice-note failed"));
    else if (entry.what === "quiet") notes.append(caption(PA.t("practice_quiet", { name: name(), reason: entry.reason })));
    else if (entry.what === "joined") notes.append(caption(PA.t("practice_joins", { name: name(), reason: entry.reason })));
    else if (entry.what === "memory")
      notes.append(caption(PA.t(entry.memory === "saved" ? "practice_memory_saved" : "practice_memory_refused", { name: name() })));
    notes.append(whyButton(entry, row));
    row.append(notes);
    if (entry.learning) row.append(caption(PA.t("practice_learning", { text: entry.learning }), "practice-note learning"));
    return row;
  }
  function renderLog(list) {
    // The log is rebuilt; the line control that had the keyboard gets it back by id.
    const focused = groupLog.contains(document.activeElement) ? document.activeElement.id : "";
    groupLog.replaceChildren(groupEmpty);
    entries.clear();
    for (const entry of list) groupLog.append(renderEntry(entry));
    groupEmpty.hidden = list.length > 0;
    groupLog.scrollTop = groupLog.scrollHeight;
    if (focused) PA.$(focused)?.focus();
  }
  function renderGroupText() {
    groupLead.textContent = PA.t("practice_group_lead", { name: name() });
    groupHint.textContent = PA.t("practice_group_hint", { name: name() });
    input.placeholder = PA.t("practice_message");
    if (!sending) relabel(send);
    if (quoting) replyingText.textContent = PA.t("practice_replying", { name: name(), text: quoting.text });
  }
  async function openGroup() {
    if (started || starting) return;
    // The Practice view opens before a model is set up; the demo needs none.
    if (!PA.state?.configured) {
      setReady(false);
      showGroupError("practice_needs_key");
      return;
    }
    starting = true;
    const retryFocused = document.activeElement === groupRetry;
    setReady(false);
    groupError.hidden = true;
    groupStatus.textContent = PA.t("practice_starting");
    groupStatus.hidden = false;
    groupRetry.disabled = true;
    try {
      const value = await PA.api("practice/start", { lang: PA.lang });
      groupName = value.name || groupName;
      started = true;
      renderGroupText();
      renderLog(value.entries);
      setReady(true);
      input.focus();
    } catch (error) {
      showGroupError(error.message);
    } finally {
      starting = false;
      groupRetry.disabled = false;
      groupStatus.hidden = true;
      if (retryFocused && focusLost()) (groupRetry.hidden ? groupSettings : groupRetry).focus();
    }
  }
  groupRetry.addEventListener("click", () => {
    started = false;
    openGroup();
  });
  groupSettings.addEventListener("click", () => PA.showView("settings"));
  PA.onState((state) => {
    // Set up in the meantime: the group the page said was waiting for a model starts.
    if (state.configured && !started && part === "group" && groupErrorText.dataset.key === "practice_needs_key"
      && !groupError.hidden && PA.view === "practice")
      openGroup();
  });

  function quote(entry) {
    quoting = entry;
    replyingText.textContent = PA.t("practice_replying", { name: name(), text: entry.text });
    replying.hidden = false;
    input.focus();
  }
  function unquote() {
    quoting = null;
    replying.hidden = true;
  }
  replyCancel.addEventListener("click", () => {
    unquote();
    input.focus();
  });

  async function sendMessage() {
    const text = input.value.trim();
    if (sending || !text || !started) return;
    sending = true;
    sendError.hidden = true;
    working(send, "practice_sending");
    input.disabled = true;
    const as = asPick.value;
    const lang = PA.lang;
    const payload = { lang, text, as: as === "owner" ? "owner" : "member" };
    if (as !== "owner") payload.name = PA.t(MEMBERS[Number(as.slice(1)) - 1] || MEMBERS[0]);
    if (quoting) payload.quote = quoting.id;
    try {
      const value = await PA.api("practice/say", payload);
      groupName = value.name || groupName;
      groupEmpty.hidden = true;
      for (const entry of value.entries) groupLog.append(renderEntry(entry));
      groupLog.scrollTop = groupLog.scrollHeight;
      input.value = "";
      fitBox();
      unquote();
      if (learnedOpen) loadLearned();
    } catch (error) {
      // These stop the practice group; Try again starts it once more.
      if (["practice_failed", "practice_timeout", "practice_needs_key"].includes(error.message)) {
        started = false;
        showGroupError(error.message);
      } else notice(sendError, error.message);
    } finally {
      sending = false;
      done(send);
      setReady(started);
      if (started) input.focus();
    }
    if (started && lang !== PA.lang) relang();
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      sendMessage();
    }
  });

  function whyView(data) {
    const panel = el("div", "practice-why");
    panel.setAttribute("role", "status");
    const add = (text, className = "") => panel.append(el("p", className, text));
    const who = data.what === "admin" ? PA.t("practice_owner") : data.speaker;
    const head = {
      named: "practice_why_named",
      admin: "practice_why_admin",
      joined: "practice_why_joined",
      quiet: "practice_why_quiet",
      memory: "practice_why_memory",
      failed: "practice_why_failed",
    }[data.what];
    if (head) add(PA.t(head, { who, reason: data.reason }));
    if (data.retryOf) add(PA.t("practice_why_retry", { text: data.retryOf }));
    if (data.learning) add(PA.t("practice_why_learning", { text: data.learning }));
    if (["named", "admin", "joined"].includes(data.what)) {
      add(PA.t(data.offered.length ? "practice_why_offered" : "practice_why_offered_none"));
      const list = el("ul");
      for (const row of data.offered) list.append(el("li", "", row.better ? `“${row.reply}” → “${row.better}”` : `“${row.reply}”`));
      if (data.offered.length) panel.append(list);
      const reactions = data.ledger.length + data.candidates.length;
      add(PA.t(reactions ? "practice_why_ledger" : "practice_why_ledger_none"));
      if (reactions) {
        const ledger = el("ul");
        for (const item of data.ledger) ledger.append(el("li", "", `${item.who}: ${item.verdict}`));
        for (const item of data.candidates) ledger.append(candidateItem(item));
        panel.append(ledger);
      }
    }
    return panel;
  }
  function candidateItem(item) {
    const said = item.better ? `“${item.reply}” → “${item.better}”` : `“${item.reply}”`;
    const node = el("li", item.inUse ? "in-use" : "", `${item.kind}: ${said}`);
    node.append(el("span", "practice-state", ` · ${item.state}${item.why ? ` (${item.why})` : ""}`));
    return node;
  }
  async function toggleWhy(entry, row, node) {
    const open = row.querySelector(".practice-why, .practice-why-error");
    if (open) {
      open.remove();
      return;
    }
    working(node, "practice_why_busy");
    try {
      const value = await PA.api("practice/why", { id: entry.id, lang: PA.lang });
      row.append(whyView(value));
    } catch (error) {
      const fail = el("p", "error practice-why-error");
      fail.setAttribute("role", "alert");
      notice(fail, error.message);
      row.append(fail);
    } finally {
      done(node);
    }
  }

  async function loadLearned() {
    working(learnedButton, "practice_learned_busy");
    try {
      const value = await PA.api("practice/learned", { lang: PA.lang });
      learnedBox.replaceChildren();
      learnedBox.append(el("p", "practice-summary", value.summary));
      if (!value.items.length) {
        const none = el("p", "field-note");
        notice(none, "practice_learned_none");
        learnedBox.append(none);
      } else {
        const list = el("ul");
        for (const item of value.items) list.append(candidateItem(item));
        learnedBox.append(list);
      }
      learnedOpen = true;
      learnedBox.hidden = false;
    } catch (error) {
      const fail = el("p", "error");
      fail.setAttribute("role", "alert");
      notice(fail, error.message);
      learnedBox.replaceChildren(fail);
      learnedBox.hidden = false;
    } finally {
      learnedButton.dataset.key = learnedOpen ? "practice_learned_hide" : "practice_learned_open";
      done(learnedButton);
    }
  }
  learnedButton.addEventListener("click", () => {
    if (learnedOpen) {
      learnedOpen = false;
      learnedBox.hidden = true;
      learnedButton.dataset.key = "practice_learned_open";
      relabel(learnedButton);
      return;
    }
    loadLearned();
  });

  resetButton.addEventListener("click", async () => {
    const sure = await PA.ask(PA.t("practice_reset_ask"), PA.t("practice_reset_yes"));
    if (!sure) return;
    if (focusLost()) resetButton.focus();
    working(resetButton, "practice_resetting");
    sendError.hidden = true;
    try {
      const value = await PA.api("practice/reset", {});
      renderLog(value.entries);
      unquote();
      if (learnedOpen) await loadLearned();
      PA.toast(PA.t("practice_reset_done"));
    } catch (error) {
      notice(sendError, error.message);
    } finally {
      done(resetButton);
    }
  });

  // ---- language and showing -------------------------------------------------
  function renderText() {
    for (const node of root.querySelectorAll("[data-key]")) {
      if (!node.dataset.key || (node.disabled && node.tagName === "BUTTON")) continue;
      node.textContent = PA.t(node.dataset.key);
    }
    memberOptions();
    renderGroupText();
    renderScene();
  }
  // The reasons under earlier lines come from the character in the language
  // they were said in; the child says them again in the new one.
  async function relang() {
    if (!started || sending) return;
    try {
      const value = await PA.api("practice/start", { lang: PA.lang });
      renderLog(value.entries);
    } catch {
      /* the lines keep the language they have */
    }
  }
  PA.onLanguage(() => {
    // The demo's scenes are in the language they were loaded in.
    if (demo && demoLang !== PA.lang && !playing) {
      demo = null;
      played = new Set();
      demoLog.replaceChildren();
    }
    renderText();
    if (!started) return;
    renderLog([...entries.values()]);
    // One request at a time: the child answers them in turn.
    relang().then(() => learnedOpen && !sending && loadLearned());
  });
  PA.onShow("practice", () => {
    renderText();
    showPart(part);
  });
  setReady(false);
  renderText();
  applyPart(part);
})();
