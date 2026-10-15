"use strict";
const $ = (id) => document.getElementById(id);
const translations = {
  zh: {
    space: "你的角色空间",
    chat: "开始聊天",
    platforms: "连接平台",
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
    qqLater: "也可以把它带到 QQ、微信、Telegram…",
    qqLaterHint: "先聊起来。想接入时，在「连接平台」里选一个，扫码或填一两项就好。",
    chatHint: "在这里，先自在地聊几句。",
    newChat: "新对话",
    emptyHint: "一个简单的问候，就是故事的开始。",
    promptHello: "你好，认识一下？",
    promptDay: "今天过得怎么样？",
    promptFilm: "推荐一部周末看的电影吧",
    message: "输入消息",
    composerNote: "Enter 发送 · Shift + Enter 换行",
    bringAlong: "把熟悉的角色，带到熟悉的地方",
    platformsIntro:
      "选一个平台，扫码或填一两项。下载、配置和启动都会自动完成，不需要再登录别的后台。",
    connectedTitle: "已连接的平台",
    groupScan: "扫码就能连",
    groupScanHint: "用手机确认一下就好，什么都不用填。",
    groupKey: "粘贴一两项",
    groupKeyHint: "从平台后台复制，页面会告诉你复制哪一项。",
    howScan: "扫码",
    howPaste: "粘贴 {n} 项",
    howAdvanced: "需要额外准备",
    reachAll: "群聊和私聊",
    reachDm: "仅私聊",
    groupAdvanced: "高级：需要公网地址或本机其他软件",
    back: "← 返回",
    guide: "去平台后台获取 ↗",
    optional: "（可选）",
    scope: "连接后，角色会回复这个平台上的群聊和私聊。",
    getQr: "获取二维码",
    connectNow: "连接",
    reconnect: "重新设置",
    disconnect: "断开",
    confirmDisconnect: "断开 {platform}？保存的凭据会被删除。",
    disconnecting: "正在断开 {platform}…",
    isConnected: "已连接",
    paused: "已暂停",
    connectingState: "连接中",
    failedState: "连接失败",
    openQQ: "在浏览器打开授权页面 ↗",
    cancel: "取消",
    startServices: "一键启动",
    stopServices: "暂停运行",
    backToList: "返回平台列表",
    keepOpen:
      "使用期间保持应用运行即可。关闭程序时，会一并停止由它启动的服务。",
    closed: "应用已关闭",
    closedHint: "再次运行 personagent，即可回到这里。",
    installTitle: "正在自动准备…",
    installHint:
      "首次使用会下载 AstrBot 和所需运行环境，可能需要几分钟。保持页面打开即可，不需要手动操作。",
    scanTitle: "用手机扫一下。",
    scanHint: "确认后会自动保存并启动。二维码过期可以重新获取。",
    scanHelp_qq_official: "用手机 QQ 扫码，并确认创建或绑定机器人。",
    scanHelp_weixin_oc: "用手机微信扫码，并确认登录。",
    startTitle: "正在连接你的角色…",
    startHint: "正在启动角色服务和聊天平台，很快就好。",
    prepareTitle: "正在获取二维码…",
    prepareHint: "马上就好。",
    checkTitle: "正在确认 {platform} 接受了连接…",
    checkHint: "如果平台拒绝了这些凭据，会在这里告诉你，不会保存。",
    doneTitle: "{platform} 已连接，去打个招呼吧。",
    saved: "设置已保存。可以开始聊天了。",
    thinking: "正在回复…",
    noReply: "它暂时没有回复，换个话题试试。",
    greeting: "你好，我是 {name}。",
    platformsTitle: "把 {name} 带到你常用的地方。",
    keySaved: "留空保留已保存的密钥",
    firstConfigure: "先连接一个模型，再把角色带到其他平台。",
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
    download_failed: "下载没有完成，请检查网络后重试。",
    service_failed: "聊天平台没有启动成功。请检查填写的内容是否正确，然后重试。",
    scan_failed: "扫码没有完成或二维码已过期，请重新获取。",
    platform_rejected:
      "平台没有接受这次连接，所以没有保存。请检查填写的内容（和平台后台的设置）后重试。",
    token_rejected: "平台说这个 Token 不对，没有保存。请重新复制完整的 Token。",
    app_rejected: "QQ 说 AppID 或 AppSecret 不对，没有保存。请到 QQ 开放平台重新复制。",
    bot_in_use: "这个机器人正被别的程序使用（或设置了 Webhook）。先停掉那个程序再连接。",
    message_content_intent_off:
      "Discord 拒绝了：请在开发者后台的 Bot 页面打开 Message Content Intent，保存后重试。",
    intents_not_allowed: "QQ 没有给这个机器人收群聊和私聊消息的权限。",
    session_expired: "登录已失效，请重新扫码。",
    bot_offline: "这个 QQ 机器人已下架。",
    bot_banned: "这个 QQ 机器人已被封禁。",
    network_failed: "连不上这个平台的服务器。Telegram、Discord 在国内通常需要代理。",
    field_required: "请填写所有必填项。",
    invalid_field: "有一项格式不对，请检查地址或端口。",
    invalid_platform: "暂不支持这个平台。",
    permission_required: "需要允许角色在这个平台回复。",
    forbidden: "页面授权已失效，请重新打开启动窗口里的本地链接。",
    generic: "操作没有完成，请重试。",
    stopped: "聊天平台已暂停。",
    retryChat: "重新发送",
    closing: "正在关闭…",
  },
  en: {
    space: "YOUR CHARACTER SPACE",
    chat: "Chat",
    platforms: "Connect apps",
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
    qqLater: "Bring your character to QQ, WeChat, Telegram…",
    qqLaterHint:
      "Start with a chat. Then pick an app under Connect apps: a scan or one or two values.",
    chatHint: "A place to talk, at your own pace.",
    newChat: "New chat",
    emptyHint: "A simple hello is a good place to start.",
    promptHello: "Hi, shall we get to know each other?",
    promptDay: "How has your day been?",
    promptFilm: "Recommend a film for the weekend",
    message: "Write a message",
    composerNote: "Enter to send · Shift + Enter for a new line",
    bringAlong: "A FAMILIAR CHARACTER, IN A FAMILIAR PLACE",
    platformsIntro:
      "Pick an app, then scan or paste one or two values. Downloading, setup and starting happen on their own, with no other dashboard to sign in to.",
    connectedTitle: "Connected apps",
    groupScan: "Scan to connect",
    groupScanHint: "Confirm on your phone. Nothing to fill in.",
    groupKey: "Paste one or two values",
    groupKeyHint: "Copy them from the app's console; the page says which.",
    howScan: "Scan",
    howPaste: "Paste {n}",
    howAdvanced: "Needs setup",
    reachAll: "Groups and DMs",
    reachDm: "DMs only",
    groupAdvanced: "Advanced: needs a public address or other software",
    back: "← Back",
    guide: "Get these from the app's console ↗",
    optional: " (optional)",
    scope: "Once connected, your character replies to groups and direct messages in this app.",
    getQr: "Get a QR code",
    connectNow: "Connect",
    reconnect: "Set up again",
    disconnect: "Disconnect",
    confirmDisconnect: "Disconnect {platform}? Its saved credentials will be deleted.",
    disconnecting: "Disconnecting {platform}…",
    isConnected: "Connected",
    paused: "Paused",
    connectingState: "Connecting",
    failedState: "Failed",
    openQQ: "Open the authorization page ↗",
    cancel: "Cancel",
    startServices: "Start everything",
    stopServices: "Pause",
    backToList: "Back to all apps",
    keepOpen:
      "Keep the app running while you use it. Quitting also stops the services it started.",
    closed: "The app is closed",
    closedHint: "Run personagent again to return here.",
    installTitle: "Getting things ready…",
    installHint:
      "First use downloads AstrBot and its runtime, which can take a few minutes. Keep this page open; there's nothing to do by hand.",
    scanTitle: "Scan with your phone.",
    scanHint:
      "After you confirm, everything is saved and started. An expired code can be refreshed.",
    scanHelp_qq_official: "Scan with mobile QQ and confirm creating or binding the bot.",
    scanHelp_weixin_oc: "Scan with WeChat and confirm the login.",
    startTitle: "Connecting your character…",
    startHint: "Starting the character service and chat platform.",
    prepareTitle: "Getting a QR code…",
    prepareHint: "Just a moment.",
    checkTitle: "Checking that {platform} accepts the connection…",
    checkHint:
      "If the app refuses these credentials, you'll see it here and nothing is saved.",
    doneTitle: "{platform} is connected. Go say hello.",
    saved: "Saved. You're ready to chat.",
    thinking: "Replying…",
    noReply: "No reply this time. Try another topic.",
    greeting: "Hi, I'm {name}.",
    platformsTitle: "Bring {name} to the apps you use.",
    keySaved: "Leave blank to keep the saved key",
    firstConfigure: "Connect a model first, then bring the character to other apps.",
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
    download_failed: "The download didn't finish. Check your network and retry.",
    service_failed:
      "The chat platform didn't start. Check what you entered, then retry.",
    scan_failed: "The scan didn't finish or the code expired. Get a new code.",
    platform_rejected:
      "The app refused the connection, so nothing was saved. Check what you entered and the app's console settings, then retry.",
    token_rejected: "The app says this token is wrong, so nothing was saved. Copy the whole token again.",
    app_rejected: "QQ says the AppID or AppSecret is wrong, so nothing was saved. Copy them again from QQ's console.",
    bot_in_use: "Another program is using this bot (or a webhook is set). Stop it, then connect again.",
    message_content_intent_off:
      "Discord refused: turn on Message Content Intent on the Bot page of the developer portal, save, and retry.",
    intents_not_allowed: "QQ has not given this bot permission to receive group and direct messages.",
    session_expired: "The login has expired. Scan again.",
    bot_offline: "This QQ bot has been taken offline.",
    bot_banned: "This QQ bot has been banned.",
    network_failed: "Couldn't reach this app's servers. Check your network or proxy.",
    field_required: "Fill in every required field.",
    invalid_field: "One value isn't valid. Check the address or port.",
    invalid_platform: "This app isn't supported.",
    permission_required: "Your character needs permission to reply in this app.",
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
  selected = null,
  fresh = false,
  panelError = "",
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
    tiles();
    if (selected) buildFields(true);
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
  $("platforms-title").textContent = t("platformsTitle", {
    name: state?.name || name,
  });
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
  if (next === "platforms" && !state.configured) {
    toast(t("firstConfigure"));
    next = "settings";
  }
  view = next;
  for (const button of document.querySelectorAll(".nav"))
    button.classList.toggle("active", button.dataset.view === next);
  const setup = next === "settings" || (next === "chat" && !state.configured);
  $("setup-view").hidden = !setup;
  $("chat-view").hidden = setup || next !== "chat";
  $("platforms-view").hidden = next !== "platforms";
  $("page-label").textContent = t(
    setup
      ? state.configured
        ? "settings"
        : "welcome"
      : next === "platforms"
        ? "platforms"
        : "chat",
  );
  if (next === "chat" && state.configured) $("message").focus();
}
const pick = (pair) => pair[lang === "zh" ? 1 : 0];
const spec = (kind) => catalog?.platforms.find((p) => p.id === kind);
const platformName = (kind) => (spec(kind) ? pick(spec(kind).name) : kind);
// Each platform's mark: a short monogram in its own colour.
const MARKS = {
  qq_official: ["Q", "#1aa6e6"],
  weixin_oc: ["微", "#07a85a"],
  telegram: ["T", "#229ed9"],
  discord: ["D", "#5865f2"],
  kook: ["K", "#4f9a1c"],
  lark: ["飞", "#3370ff"],
  dingtalk: ["钉", "#1677ff"],
  slack: ["S", "#7b2a7d"],
  wecom_ai_bot: ["企", "#0a7fe0"],
  mattermost: ["M", "#1e4f9c"],
  misskey: ["Mi", "#6f9a00"],
  wecom: ["企", "#0a7fe0"],
  weixin_official_account: ["公", "#07a85a"],
  qq_official_webhook: ["Q", "#1aa6e6"],
  aiocqhttp: ["N", "#d6528f"],
  satori: ["Sa", "#7a5af8"],
};
function brand(node, kind) {
  const [glyph, colour] = MARKS[kind] || [kind.slice(0, 1).toUpperCase(), "#365a43"];
  node.style.setProperty("--brand", colour);
  return glyph;
}
function badge(kind, size = "") {
  const node = document.createElement("span");
  node.className = `badge ${size}`.trim();
  node.setAttribute("aria-hidden", "true");
  node.textContent = brand(node, kind);
  return node;
}
function describe(item) {
  const how =
    item.group === "scan"
      ? t("howScan")
      : item.group === "advanced"
        ? t("howAdvanced")
        : t("howPaste", {
            n: String(item.fields.filter((f) => f.required).length),
          });
  return [how, t(item.groups ? "reachAll" : "reachDm")];
}
function tiles() {
  for (const box of document.querySelectorAll(".tiles")) {
    box.replaceChildren();
    for (const item of catalog.platforms) {
      if (item.group !== box.dataset.group) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "tile";
      button.dataset.platform = item.id;
      brand(button, item.id);
      const text = document.createElement("span");
      text.className = "tile-text";
      const name = document.createElement("strong");
      name.textContent = pick(item.name);
      const line = document.createElement("small");
      line.textContent = describe(item).join(" · ");
      text.append(name, line);
      const tag = document.createElement("span");
      tag.className = "tile-tag";
      button.append(badge(item.id), text, tag);
      button.addEventListener("click", () => openPanel(item.id));
      box.append(button);
    }
  }
}
function buildFields(keep = false) {
  const item = spec(selected);
  const kept = {};
  if (keep)
    for (const input of $("panel-fields").querySelectorAll("input"))
      kept[input.name] = input.value;
  $("panel-title").textContent = pick(item.name);
  $("panel-badge").textContent = brand($("panel-badge"), item.id);
  brand($("platform-panel"), item.id);
  $("panel-chips").replaceChildren(
    ...describe(item).map((label) => {
      const chip = document.createElement("span");
      chip.textContent = label;
      return chip;
    }),
  );
  $("panel-note").textContent = pick(item.note);
  $("panel-note").hidden = !pick(item.note);
  $("panel-guide").href = item.guide || "#";
  $("panel-guide").hidden = !item.guide;
  $("panel-howto").hidden = !pick(item.note) && !item.guide;
  const box = $("panel-fields");
  box.replaceChildren();
  for (const field of item.fields) {
    const label = document.createElement("label");
    label.htmlFor = `field-${field.key}`;
    label.textContent = pick(field.label) + (field.required ? "" : t("optional"));
    const input = document.createElement("input");
    input.id = `field-${field.key}`;
    input.name = field.key;
    input.autocomplete = "off";
    input.spellcheck = false;
    input.type = field.secret ? "password" : "text";
    if (field.kind === "port") input.inputMode = "numeric";
    input.placeholder = field.default;
    input.required = field.required && !field.default;
    input.value = kept[field.key] || "";
    box.append(label, input);
  }
  $("panel-submit").textContent = t(
    item.group === "scan" ? "getQr" : "connectNow",
  );
}
function openPanel(kind) {
  const job = state.job;
  if (job.state === "working" && job.platform !== kind) {
    toast(t("working"));
    return;
  }
  selected = kind;
  // Back to a platform whose job is still running: keep watching it.
  fresh = job.state === "working" && job.platform === kind;
  panelError = "";
  buildFields();
  renderStatus();
  window.scrollTo(0, 0);
}
function renderConnected(connected, working) {
  const list = $("connected-list");
  list.replaceChildren();
  for (const kind of connected) {
    const row = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = platformName(kind);
    const status = document.createElement("span");
    const current = (state.platformStatus || {})[kind] || "paused";
    status.className = "state";
    status.dataset.state = current;
    status.textContent = t(
      {
        running: "running",
        connecting: "connectingState",
        failed: "failedState",
      }[current] || "paused",
    );
    const again = document.createElement("button");
    again.className = "quiet";
    again.textContent = t("reconnect");
    again.disabled = working;
    again.addEventListener("click", () => openPanel(kind));
    const remove = document.createElement("button");
    remove.className = "quiet";
    remove.textContent = t("disconnect");
    remove.disabled = working;
    remove.addEventListener("click", () => disconnect(kind));
    row.append(badge(kind, "small"), name, status, again, remove);
    list.append(row);
  }
}
function renderStatus() {
  if (!state) return;
  $("version").textContent = `v${state.version}`;
  $("service-status").textContent = t(
    state.agentRunning ? "running" : "localReady",
  );
  const job = state.job,
    working = job.state === "working",
    // A platform being connected is saved before it is checked; it counts
    // once the check passes.
    connected = state.platforms.filter(
      (kind) =>
        !(working && job.action !== "disconnect" && job.platform === kind),
    );
  $("platforms-dot").hidden = !connected.length;
  if (!catalog) return;
  for (const tile of document.querySelectorAll(".tile")) {
    const on = connected.includes(tile.dataset.platform);
    tile.classList.toggle("on", on);
    tile.querySelector(".tile-tag").textContent = on ? t("isConnected") : "";
  }
  $("connected-card").hidden = !connected.length;
  renderConnected(connected, working);
  $("start-services").disabled = working;
  $("start-services").hidden = state.agentRunning && state.platformRunning;
  $("stop-services").hidden = !(state.agentRunning || state.platformRunning);
  const servicesFailed =
    job.state === "error" && (!job.platform || job.action === "disconnect");
  $("services-error").hidden = !servicesFailed;
  $("services-error").textContent = servicesFailed ? t(job.error) : "";
  $("platform-groups").hidden = selected !== null;
  $("platform-panel").hidden = selected === null;
  if (selected === null) return;
  const mine = job.platform === selected && job.action !== "disconnect",
    active = mine && working,
    done = mine && fresh && job.state === "ready",
    failed = mine && fresh && job.state === "error";
  $("platform-form").hidden = active || done;
  $("panel-progress").hidden = !active;
  $("panel-done").hidden = !done;
  $("panel-submit").disabled = working;
  const error = failed ? t(job.error) : panelError;
  $("panel-error").hidden = !error;
  $("panel-error").textContent = error;
  $("done-title").textContent = t("doneTitle", {
    platform: platformName(selected),
  });
  if (!active) return;
  const scan = job.stage === "scan";
  $("qr-box").hidden = !scan;
  $("progress-spinner").hidden = scan;
  const late = job.stage === "start" || job.stage === "check";
  $("cancel-platform").hidden = late;
  const step = scan
    ? "scan"
    : late || job.stage === "prepare"
      ? job.stage
      : "install";
  $("progress-title").textContent = t(`${step}Title`, {
    platform: platformName(selected),
  });
  $("progress-hint").textContent = t(`${step}Hint`);
  if (!scan) return;
  $("scan-help").textContent = t(`scanHelp_${selected}`);
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
async function refresh() {
  state = await api("state");
  renderStatus();
}
async function disconnect(kind) {
  if (!confirm(t("confirmDisconnect", { platform: platformName(kind) })))
    return;
  try {
    await api("platforms/disconnect", { platform: kind });
    toast(t("disconnecting", { platform: platformName(kind) }));
    await refresh();
  } catch (error) {
    toast(t(error.message));
  }
}
$("platform-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = {};
  for (const input of $("panel-fields").querySelectorAll("input"))
    values[input.name] = input.value;
  panelError = "";
  try {
    await api("platforms/connect", {
      platform: selected,
      values,
      allowConversations: true,
    });
    fresh = true;
    await refresh();
  } catch (error) {
    panelError = t(error.message);
    renderStatus();
  }
});
for (const id of ["panel-back", "panel-finish"])
  $(id).addEventListener("click", () => {
    selected = null;
    renderStatus();
  });
$("cancel-platform").addEventListener("click", async () => {
  try {
    await api("platforms/cancel", {});
  } catch (error) {
    toast(t(error.message));
  }
});
$("start-services").addEventListener("click", async () => {
  try {
    await api("start", {});
    await refresh();
  } catch (error) {
    toast(t(error.message));
  }
});
$("stop-services").addEventListener("click", async () => {
  try {
    await api("stop", {});
    await refresh();
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
