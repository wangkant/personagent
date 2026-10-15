"use strict";
const $ = (id) => document.getElementById(id);
const translations = {
  zh: {
    space: "你的角色空间",
    chat: "开始聊天",
    qq: "连接 QQ",
    settings: "角色与设置",
    local: "运行在你的电脑上",
    welcome: "欢迎来到 personagent",
    localReady: "本地应用已就绪",
    running: "正在运行",
    exit: "退出",
    firstStep: "从一句你好开始",
    hero: "让角色，走进你的日常。",
    intro: "填入一个模型密钥，就能开始聊天。其余的，我们已经准备好了。",
    modelTitle: "连接一个模型",
    modelHint: "角色通过你选择的模型服务与你聊天。",
    provider: "模型服务",
    getKey: "去获取密钥 ↗",
    show: "显示",
    hide: "隐藏",
    keyNote: "密钥保存在本机；聊天内容会发送给你选择的模型服务。",
    advanced: "更多设置",
    characterOptions: "给角色换个名字或性格",
    name: "角色名字",
    character: "性格",
    customKept: "已有的人设会保留；选择新性格才会替换它。",
    custom: "保留我自己写的人设",
    model: "模型名称",
    saveStart: "验证并开始聊天 →",
    saveAgain: "保存并返回聊天 →",
    saving: "正在验证密钥…",
    testNote: "会用一个很小的请求验证密钥，可能产生少量模型费用。",
    yourCharacter: "你的第一个角色",
    previewText: "会认真听你说，也有自己的性格。先聊几句，再慢慢熟悉。",
    sample: "今天怎么样？有什么想和我说的吗？",
    changeLater: "名字和性格，随时都能改。",
    qqLater: "也可以把它带到 QQ",
    qqLaterHint: "先聊起来。想接入 QQ 时，点一下连接，再用手机扫码。",
    chatHint: "在这里，先自在地聊几句。",
    newChat: "新对话",
    emptyHint: "一个简单的问候，就是故事的开始。",
    promptHello: "你好，认识一下？",
    promptDay: "今天过得怎么样？",
    promptFilm: "推荐一部周末看的电影吧",
    message: "输入消息",
    composerNote: "Enter 发送 · Shift + Enter 换行",
    bringAlong: "把熟悉的角色，带到熟悉的地方",
    qqIntro: "通过 QQ 官方机器人直接连接，无需 NapCat，也不用填写端口。",
    prepare: "自动准备组件",
    scan: "手机 QQ 扫码",
    connected: "开始使用",
    oneScan: "剩下的，只需一次扫码。",
    qqScope: "连接后，角色会回复这个 QQ 官方机器人收到的群聊和私聊。",
    connectQQ: "连接 QQ，获取二维码",
    groupNote: "添加到群聊需要你是群主；群消息范围由 QQ 的机器人设置控制。",
    scanHelp: "用手机 QQ 扫码，并确认创建或绑定机器人。",
    openQQ: "在浏览器打开授权页面 ↗",
    cancel: "取消",
    qqDone: "已经连接，去 QQ 打个招呼吧。",
    qqDoneHint:
      "在手机 QQ 的「联系人 → 机器人」找到它，开始私聊，或把它添加到你管理的群。",
    startServices: "一键启动",
    stopServices: "暂停运行",
    retry: "重试",
    keepOpen:
      "使用期间保持应用运行即可。关闭程序时，会一并停止由它启动的服务。",
    closed: "应用已关闭",
    closedHint: "再次运行 personagent，即可回到这里。",
    installTitle: "正在自动准备 QQ 连接…",
    installHint:
      "首次使用会下载 AstrBot 和所需运行环境。保持页面打开即可，不需要手动操作。",
    scanTitle: "用手机 QQ 扫一下。",
    scanHint: "授权完成后，会自动保存并启动。二维码过期可以重新获取。",
    startTitle: "正在连接你的角色…",
    startHint: "正在启动角色服务和聊天平台，很快就好。",
    boundTitle: "扫码成功，正在完成连接…",
    saved: "设置已保存。可以开始聊天了。",
    thinking: "正在回复…",
    noReply: "它暂时没有回复，换个话题试试。",
    greeting: "你好，我是 {name}。",
    qqTitle: "把 {name} 带到 QQ。",
    keySaved: "留空保留已保存的密钥",
    firstConfigure: "先连接一个模型，再把角色带到 QQ。",
    working: "当前操作还在进行，请稍等。",
    offline: "应用连接中断，请确认启动窗口仍在运行。",
    auth: "请通过启动窗口里显示的本地链接打开此页面。",
    key_required: "请填入 API Key。",
    key_rejected: "密钥未通过验证，请检查是否复制完整、是否属于所选服务。",
    model_unreachable:
      "暂时连不上这个模型，请检查网络、模型名称和服务地址后重试。",
    model_required: "请在更多设置中填写模型名称。",
    invalid_url: "请填写完整的 API 地址。",
    https_required: "远程模型服务需要使用 HTTPS 地址。",
    invalid_character: "请检查角色名字与性格。",
    busy: "当前操作还在进行，请稍等完成。",
    chat_failed: "回复没有完成，请检查模型服务和网络，再重试。",
    setup_failed:
      "这次连接没有完成。请检查网络后重试；已保存的模型和角色不会丢失。",
    forbidden: "页面授权已失效，请重新打开启动窗口里的本地链接。",
    generic: "操作没有完成，请重试。",
    stopped: "聊天平台已暂停。",
    retryChat: "重新发送",
    closing: "正在关闭…",
  },
  en: {
    space: "YOUR CHARACTER SPACE",
    chat: "Chat",
    qq: "Connect QQ",
    settings: "Character & settings",
    local: "Running on your computer",
    welcome: "Welcome to personagent",
    localReady: "Local app ready",
    running: "Running",
    exit: "Quit",
    firstStep: "IT STARTS WITH HELLO",
    hero: "A character, part of your everyday.",
    intro:
      "Add a model API key and start chatting. Everything else has a sensible default.",
    modelTitle: "Connect a model",
    modelHint: "Your character talks through the model service you choose.",
    provider: "Model service",
    getKey: "Get an API key ↗",
    show: "Show",
    hide: "Hide",
    keyNote:
      "Your key stays on this computer. Chats go to the model service you choose.",
    advanced: "Advanced settings",
    characterOptions: "Choose a name or personality",
    name: "Character name",
    character: "Personality",
    customKept:
      "Your edited character stays as it is unless you choose a new personality.",
    custom: "Keep my own character",
    model: "Model name",
    saveStart: "Verify & start chatting →",
    saveAgain: "Save & return to chat →",
    saving: "Checking your key…",
    testNote:
      "Verification sends one small model request and may incur a small charge.",
    yourCharacter: "YOUR FIRST CHARACTER",
    previewText:
      "An attentive listener with a personality of their own. Say hello and get to know each other.",
    sample: "How was your day? Anything you want to talk about?",
    changeLater: "You can change the name and personality anytime.",
    qqLater: "Bring your character to QQ, too",
    qqLaterHint:
      "Start with a chat. When you want QQ, connect it with a phone scan.",
    chatHint: "A place to talk, at your own pace.",
    newChat: "New chat",
    emptyHint: "A simple hello is a good place to start.",
    promptHello: "Hi, shall we get to know each other?",
    promptDay: "How has your day been?",
    promptFilm: "Recommend a film for the weekend",
    message: "Write a message",
    composerNote: "Enter to send · Shift + Enter for a new line",
    bringAlong: "A FAMILIAR CHARACTER, IN A FAMILIAR PLACE",
    qqIntro:
      "Connect through QQ Official Bot. No NapCat or port configuration needed.",
    prepare: "Prepare",
    scan: "Scan with QQ",
    connected: "Ready to chat",
    oneScan: "Just one phone scan from here.",
    qqScope:
      "Your character will reply to the groups and direct messages received by this QQ official bot.",
    connectQQ: "Connect QQ & get a QR code",
    groupNote:
      "You must own a group to add the bot. QQ's bot settings control which group messages it can read.",
    scanHelp: "Scan with mobile QQ and confirm bot creation or binding.",
    openQQ: "Open the authorization page ↗",
    cancel: "Cancel",
    qqDone: "Connected. Say hello in QQ.",
    qqDoneHint:
      "Find it in mobile QQ → Contacts → Bots. Chat directly or add it to a group you own.",
    startServices: "Start everything",
    stopServices: "Pause",
    retry: "Try again",
    keepOpen:
      "Keep the app running while you use it. Quitting also stops the services it started.",
    closed: "The app is closed",
    closedHint: "Run personagent again to return here.",
    installTitle: "Preparing your QQ connection…",
    installHint:
      "First use downloads AstrBot and its runtime. Keep this page open; no manual setup is needed.",
    scanTitle: "Scan with mobile QQ.",
    scanHint:
      "After you confirm, credentials are saved and services start automatically. An expired code can be refreshed.",
    startTitle: "Connecting your character…",
    startHint: "Starting the character service and chat platform.",
    boundTitle: "Scan confirmed. Finishing up…",
    saved: "Saved. You're ready to chat.",
    thinking: "Replying…",
    noReply: "No reply this time. Try another topic.",
    greeting: "Hi, I'm {name}.",
    qqTitle: "Bring {name} to QQ.",
    keySaved: "Leave blank to keep the saved key",
    firstConfigure: "Connect a model first, then bring the character to QQ.",
    working: "An operation is still in progress. Please wait.",
    offline:
      "The app disconnected. Check that its launch window is still running.",
    auth: "Open this page using the local link in the launch window.",
    key_required: "Enter your API key.",
    key_rejected:
      "The key was not accepted. Check that it is complete and belongs to this service.",
    model_unreachable:
      "Couldn't reach this model. Check the network, model name and API address, then retry.",
    model_required: "Enter a model name under advanced settings.",
    invalid_url: "Enter a complete API address.",
    https_required: "Remote model services require an HTTPS address.",
    invalid_character: "Check the character name and personality.",
    busy: "An operation is still running. Please wait.",
    chat_failed:
      "The reply failed. Check the model service and your connection, then retry.",
    setup_failed:
      "The connection didn't finish. Check your network and retry. Your model and character settings are saved.",
    forbidden:
      "This page's authorization expired. Reopen the link in the launch window.",
    generic: "That didn't finish. Please try again.",
    stopped: "Chat platform paused.",
    retryChat: "Send again",
    closing: "Closing…",
  },
};
let lang = navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";
let state = null,
  catalog = null,
  view = "chat",
  chatting = false,
  saving = false,
  ended = false;
let toastTimer = null;
const fragment = new URLSearchParams(location.hash.slice(1));
const token =
  fragment.get("token") ||
  sessionStorage.getItem("personagent-setup-token") ||
  "";
if (fragment.has("token")) {
  sessionStorage.setItem("personagent-setup-token", token);
  history.replaceState(null, "", location.pathname);
}
const t = (key, fields = {}) =>
  Object.entries(fields).reduce(
    (value, [name, text]) => value.replaceAll(`{${name}}`, text),
    translations[lang][key] || translations[lang].generic,
  );
function toast(text) {
  $("toast").textContent = text;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), 5000);
}
async function api(path, payload) {
  const response = await fetch(`/api/${path}`, {
    method: payload === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Personagent-Setup-Token": token,
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
    credentials: "omit",
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || value.detail || "generic");
  return value;
}
function label(node, text) {
  node.textContent = text;
}
function options(select, items, selected) {
  select.replaceChildren();
  for (const item of items) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.name[lang === "zh" ? 1 : 0];
    select.append(option);
  }
  select.value = selected;
}
function renderLanguage() {
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  $("language").value = lang;
  for (const node of document.querySelectorAll("[data-t]"))
    label(node, t(node.dataset.t));
  $("message").placeholder = t("message");
  if (catalog) {
    const provider = $("provider").value || state.provider;
    options($("provider"), catalog.providers, provider);
    const character = $("character").value || state.character;
    const chars = [...catalog.characters];
    if (state.character === "custom")
      chars.push({
        id: "custom",
        name: [translations.en.custom, translations.zh.custom],
      });
    options($("character"), chars, character);
  }
  updateNames();
  renderStatus();
  if (!saving)
    $("save").textContent = t(state?.configured ? "saveAgain" : "saveStart");
}
function updateNames() {
  const name =
    $("character-name").value.trim() ||
    state?.name ||
    (lang === "zh" ? "小夏" : "Nova");
  $("preview-name").textContent = name;
  $("chat-name").textContent = state?.name || name;
  $("chat-greeting").textContent = t("greeting", { name: state?.name || name });
  $("qq-title").textContent = t("qqTitle", { name: state?.name || name });
}
function populate() {
  options($("provider"), catalog.providers, state.provider);
  const chars = [...catalog.characters];
  if (state.character === "custom")
    chars.push({
      id: "custom",
      name: [translations.en.custom, translations.zh.custom],
    });
  options($("character"), chars, state.character);
  $("custom-note").hidden = state.character !== "custom";
  $("character-name").value = state.name || (lang === "zh" ? "小夏" : "Nova");
  $("api-key").value = "";
  $("api-key").type = "password";
  $("show-key").textContent = t("show");
  $("api-key").placeholder = state.configured ? t("keySaved") : "sk-…";
  providerChanged(false);
  updateNames();
}
function providerChanged(reset = true) {
  const provider = catalog.providers.find((p) => p.id === $("provider").value);
  if (!provider) return;
  $("base-url").value = reset
    ? provider.baseUrl
    : state.baseUrl || provider.baseUrl;
  $("model").value = reset ? provider.model : state.model || provider.model;
  $("key-link").href = provider.keyUrl || "#";
  $("key-link").hidden = !provider.keyUrl;
  $("api-key").required = provider.id !== "ollama" && !state.configured;
  if (reset && provider.id !== state.provider) {
    $("api-key").value = "";
    $("api-key").placeholder = "sk-…";
    $("api-key").required = provider.id !== "ollama";
  }
  if (provider.id === "other" || provider.id === "ollama")
    $("advanced").open = true;
}
function showView(next) {
  if (chatting && next !== "chat") {
    toast(t("working"));
    return;
  }
  if (next === "qq" && !state.configured) {
    toast(t("firstConfigure"));
    next = "settings";
  }
  view = next;
  for (const button of document.querySelectorAll(".nav"))
    button.classList.toggle("active", button.dataset.view === next);
  const setup = next === "settings" || (next === "chat" && !state.configured);
  $("setup-view").hidden = !setup;
  $("chat-view").hidden = setup || next !== "chat";
  $("qq-view").hidden = next !== "qq";
  $("page-label").textContent = t(
    setup
      ? state.configured
        ? "settings"
        : "welcome"
      : next === "qq"
        ? "qq"
        : "chat",
  );
  if (next === "chat" && state.configured) $("message").focus();
}
function renderStatus() {
  if (!state) return;
  $("version").textContent = `v${state.version}`;
  $("service-status").textContent = t(
    state.agentRunning ? "running" : "localReady",
  );
  $("qq-dot").hidden = !state.qqReady;
  const job = state.job,
    working = job.state === "working",
    failed = job.state === "error",
    ready = state.qqReady && !working;
  $("qq-idle").hidden = working || ready;
  $("qq-progress").hidden = !working;
  $("qq-ready").hidden = !ready;
  $("qq-error").hidden = !failed;
  $("qq-error").textContent = failed ? t(job.error) : "";
  $("retry-qq").hidden = !failed;
  $("connect-qq").disabled = working;
  $("start-services").disabled = working;
  $("start-services").hidden = state.agentRunning && state.platformRunning;
  $("stop-services").hidden = !(state.agentRunning || state.platformRunning);
  for (const [index, name] of ["install", "scan", "ready"].entries()) {
    const current = job.stage === "scan" ? 1 : job.stage === "start" ? 2 : 0;
    $("stage-" + name).classList.toggle(
      "active",
      ready || (working && index <= current),
    );
  }
  if (working) {
    const scan = job.stage === "scan";
    $("qr-box").hidden = !scan;
    $("progress-spinner").hidden = scan;
    $("progress-title").textContent = t(
      scan
        ? "scanTitle"
        : job.stage === "start"
          ? "startTitle"
          : "installTitle",
    );
    $("progress-hint").textContent = t(
      scan ? "scanHint" : job.stage === "start" ? "startHint" : "installHint",
    );
    if (scan) {
      if (
        typeof job.qrImage === "string" &&
        job.qrImage.startsWith("data:image/png;base64,")
      )
        $("qr-image").src = job.qrImage;
      try {
        const url = new URL(job.qrUrl);
        $("qr-link").hidden =
          url.protocol !== "https:" || url.hostname !== "q.qq.com";
        if (!$("qr-link").hidden) $("qr-link").href = url.href;
      } catch {
        $("qr-link").hidden = true;
      }
    }
  }
}
async function poll() {
  if (ended) return;
  try {
    state = await api("state");
    renderStatus();
  } catch (error) {
    if (error.message === "forbidden") {
      toast(t("forbidden"));
      ended = true;
    } else if (!document.hidden) {
      $("service-status").textContent = t("offline");
    }
  }
  if (!ended) setTimeout(poll, state?.job.state === "working" ? 1000 : 4000);
}
function bubble(text, kind) {
  const node = document.createElement("div");
  node.className = `bubble ${kind}`;
  node.textContent = text;
  $("messages").append(node);
  $("messages").scrollTop = $("messages").scrollHeight;
  return node;
}
async function send(text, repeat = false) {
  if (chatting || !text.trim()) return;
  chatting = true;
  $("send").disabled = true;
  $("chat-empty").hidden = true;
  $("message").value = "";
  if (!repeat) bubble(text, "user");
  const pending = bubble(t("thinking"), "bot pending");
  try {
    const value = await api("chat", { text });
    pending.textContent = value.reply || t("noReply");
    pending.classList.remove("pending");
  } catch (error) {
    pending.textContent = t(error.message);
    pending.className = "bubble failed";
    const retry = document.createElement("button");
    retry.className = "quiet";
    retry.textContent = t("retryChat");
    retry.addEventListener("click", () => {
      pending.remove();
      send(text, true);
    });
    pending.append(document.createElement("br"), retry);
  } finally {
    chatting = false;
    $("send").disabled = false;
    $("message").focus();
    $("messages").scrollTop = $("messages").scrollHeight;
  }
}
for (const button of document.querySelectorAll(".nav"))
  button.addEventListener("click", () => showView(button.dataset.view));
$("language").addEventListener("change", () => {
  const oldDefault = lang === "zh" ? "小夏" : "Nova";
  lang = $("language").value;
  if (!state.name && $("character-name").value === oldDefault)
    $("character-name").value = lang === "zh" ? "小夏" : "Nova";
  renderLanguage();
  showView(view);
});
$("provider").addEventListener("change", () => providerChanged());
$("character-name").addEventListener("input", updateNames);
$("show-key").addEventListener("click", async () => {
  try {
    if ($("api-key").type === "password") {
      if (
        !$("api-key").value &&
        state.configured &&
        $("provider").value === state.provider &&
        $("base-url").value.replace(/\/$/, "") ===
          state.baseUrl.replace(/\/$/, "")
      )
        $("api-key").value = (await api("key", {})).apiKey;
      $("api-key").type = "text";
      $("show-key").textContent = t("hide");
    } else {
      $("api-key").type = "password";
      $("show-key").textContent = t("show");
    }
  } catch (error) {
    toast(t(error.message));
  }
});
$("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (saving) return;
  saving = true;
  $("form-error").hidden = true;
  $("save").disabled = true;
  $("save").textContent = t("saving");
  try {
    state = await api("config", {
      provider: $("provider").value,
      apiKey: $("api-key").value,
      baseUrl: $("base-url").value,
      model: $("model").value,
      name: $("character-name").value,
      character: $("character").value,
      lang,
    });
    populate();
    renderStatus();
    showView("chat");
    toast(t("saved"));
  } catch (error) {
    $("form-error").textContent = t(error.message);
    $("form-error").hidden = false;
  } finally {
    saving = false;
    $("save").disabled = false;
    $("save").textContent = t(state.configured ? "saveAgain" : "saveStart");
  }
});
$("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  send($("message").value);
});
$("message").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    send($("message").value);
  }
});
for (const button of document.querySelectorAll("[data-prompt]"))
  button.addEventListener("click", () =>
    send(
      t(
        { hello: "promptHello", day: "promptDay", film: "promptFilm" }[
          button.dataset.prompt
        ],
      ),
    ),
  );
$("reset-chat").addEventListener("click", async () => {
  if (chatting) return;
  try {
    await api("chat/reset", {});
    for (const node of $("messages").querySelectorAll(".bubble")) node.remove();
    $("chat-empty").hidden = false;
  } catch (error) {
    toast(t(error.message));
  }
});
async function connect() {
  try {
    await api("qq", { allowConversations: true });
    state = await api("state");
    renderStatus();
  } catch (error) {
    toast(t(error.message));
  }
}
$("connect-qq").addEventListener("click", connect);
$("retry-qq").addEventListener("click", async () => {
  if (!state.qqReady) return connect();
  try {
    await api("start", {});
    state = await api("state");
    renderStatus();
  } catch (error) {
    toast(t(error.message));
  }
});
$("cancel-qq").addEventListener("click", async () => {
  try {
    await api("qq/cancel", {});
  } catch (error) {
    toast(t(error.message));
  }
});
$("start-services").addEventListener("click", async () => {
  try {
    await api("start", {});
    state = await api("state");
    renderStatus();
  } catch (error) {
    toast(t(error.message));
  }
});
$("stop-services").addEventListener("click", async () => {
  try {
    await api("stop", {});
    state = await api("state");
    renderStatus();
    toast(t("stopped"));
  } catch (error) {
    toast(t(error.message));
  }
});
$("exit").addEventListener("click", async () => {
  try {
    $("exit").disabled = true;
    $("exit").textContent = t("closing");
    await api("exit", {});
    ended = true;
    $("closed").hidden = false;
  } catch (error) {
    toast(t(error.message));
    $("exit").disabled = false;
  }
});
(async () => {
  if (!token) {
    toast(t("auth"));
    return;
  }
  try {
    [state, catalog] = await Promise.all([api("state"), api("catalog")]);
    if (state.lang === "zh" || state.lang === "en") lang = state.lang;
    populate();
    renderLanguage();
    showView("chat");
    const history = await api("chat/history");
    if (history.messages.length) {
      $("chat-empty").hidden = true;
      for (const item of history.messages)
        bubble(item.text, item.role === "user" ? "user" : "bot");
    }
    poll();
  } catch (error) {
    toast(t(error.message));
  }
})();
