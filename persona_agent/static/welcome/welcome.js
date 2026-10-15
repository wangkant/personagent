"use strict";
const $ = (id) => document.getElementById(id);
const translations = {
  zh: {
    chat: "开始聊天",
    platforms: "连接平台",
    settings: "角色与设置",
    local: "运行在你的电脑上",
    welcome: "欢迎来到 personagent",
    localReady: "本地应用已就绪",
    running: "正在运行",
    exit: "退出",
    hero: "设置你的角色",
    intro: "填一个模型密钥就能开始聊天，其他都有默认值。",
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
    yourCharacter: "预览",
    previewText: "性格决定它说话的语气。",
    sample: "今天怎么样？有什么想和我说的吗？",
    changeLater: "名字和性格，随时都能改。",
    qqLater: "也可以把它带到 QQ、微信、Telegram…",
    qqLaterHint: "先聊起来。想接入时，在「连接平台」里选一个，扫码或填一两项就好。",
    chatHint: "本机对话",
    newChat: "新对话",
    emptyHint: "说点什么，开始聊天。",
    promptHello: "你好，认识一下？",
    promptDay: "今天过得怎么样？",
    promptFilm: "推荐一部周末看的电影吧",
    message: "输入消息",
    composerNote: "Enter 发送 · Shift + Enter 换行",
    platformsIntro:
      "扫码或填一两项即可，下载、配置和启动都会自动完成。",
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
    platformsTitle: "连接平台",
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
    chat: "Chat",
    platforms: "Connect apps",
    settings: "Character & settings",
    local: "Running on your computer",
    welcome: "Welcome to personagent",
    localReady: "Local app ready",
    running: "Running",
    exit: "Quit",
    hero: "Set up your character",
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
    yourCharacter: "Preview",
    previewText: "The personality sets how it talks.",
    sample: "How was your day? Anything you want to talk about?",
    changeLater: "You can change the name and personality anytime.",
    qqLater: "Bring your character to QQ, WeChat, Telegram…",
    qqLaterHint:
      "Start with a chat. Then pick an app under Connect apps: a scan or one or two values.",
    chatHint: "Local chat",
    newChat: "New chat",
    emptyHint: "Say something to start.",
    promptHello: "Hi, shall we get to know each other?",
    promptDay: "How has your day been?",
    promptFilm: "Recommend a film for the weekend",
    message: "Write a message",
    composerNote: "Enter to send · Shift + Enter for a new line",
    platformsIntro:
      "Scan or paste one or two values. Downloading, setup and starting happen on their own.",
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
    platformsTitle: "Connect apps",
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
  // Avatars show the first character of the name.
  $("preview-avatar").textContent = Array.from(name)[0];
  for (const id of ["chat-avatar", "empty-avatar"])
    $(id).textContent = Array.from(state?.name || name)[0];
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
// Each platform's mark: its logo where Simple Icons (CC0-1.0) has one,
// otherwise a short monogram, in the platform's own colour.
const LOGOS = {
  qq:
    "M21.395 15.035a40 40 0 0 0-.803-2.264l-1.079-2.695c.001-.032.014-.562.014-.836C19.526 4.632 17.351 0 12 0S4.474 4.632 4.474 9.241c0 .274.013.804.014.836l-1.08 2.695a39 39 0 0 0-.802 2.264c-1.021 3.283-.69 4.643-.438 4.673.54.065 2.103-2.472 2.103-2.472 0 1.469.756 3.387 2.394 4.771-.612.188-1.363.479-1.845.835-.434.32-.379.646-.301.778.343.578 5.883.369 7.482.189 1.6.18 7.14.389 7.483-.189.078-.132.132-.458-.301-.778-.483-.356-1.233-.646-1.846-.836 1.637-1.384 2.393-3.302 2.393-4.771 0 0 1.563 2.537 2.103 2.472.251-.03.581-1.39-.438-4.673",
  wechat:
    "M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 0 1 .598.082l1.584.926a.272.272 0 0 0 .14.047c.134 0 .24-.111.24-.247 0-.06-.023-.12-.038-.177l-.327-1.233a.582.582 0 0 1-.023-.156.49.49 0 0 1 .201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-6.656-6.088V8.89c-.135-.01-.27-.027-.407-.03zm-2.53 3.274c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.97-.982zm4.844 0c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.969-.982z",
  telegram:
    "M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z",
  discord:
    "M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z",
  mattermost:
    "M12.081 0C7.048-.034 2.339 3.125.637 8.153c-2.125 6.276 1.24 13.086 7.516 15.21 6.276 2.125 13.086-1.24 15.21-7.516 1.727-5.1-.172-10.552-4.311-13.557l.126 2.547c2.065 2.282 2.88 5.512 1.852 8.549-1.534 4.532-6.594 6.915-11.3 5.321-4.708-1.593-7.28-6.559-5.745-11.092 1.031-3.046 3.655-5.121 6.694-5.67l1.642-1.94A4.87 4.87 0 0 0 12.08 0zm3.528 1.094a.284.284 0 0 0-.123.024l-.004.001a.33.33 0 0 0-.109.071c-.145.142-.657.828-.657.828L13.6 3.4l-1.3 1.585-2.232 2.776s-1.024 1.278-.798 2.851c.226 1.574 1.396 2.34 2.304 2.648.907.307 2.302.408 3.438-.704 1.135-1.112 1.098-2.75 1.098-2.75l-.087-3.56-.07-2.05-.047-1.775s.01-.856-.02-1.057a.33.33 0 0 0-.035-.107l-.006-.012-.007-.011a.277.277 0 0 0-.229-.14z",
  misskey:
    "M8.91076 16.8915c-1.03957.0038-1.93213-.6294-2.35267-1.366-.22516-.3217-.66989-.4364-.6761 0v2.0148c0 .8094-.29152 1.5097-.87581 2.1002-.56755.573-1.25977.8595-2.0779.8595-.80014 0-1.49298-.2865-2.07727-.8601C.28408 19.05 0 18.3497 0 17.5403V6.45968c0-.62378.17553-1.18863.52599-1.69455.36657-.52284.83426-.88582 1.4018-1.08769a2.84574 2.84574 0 0 1 1.00049-.17742c.90125 0 1.65239.35421 2.25281 1.06262l2.99713 3.51572c.06699.05016.263.43696.73192.43696.47016 0 .6916-.3868.75796-.43758l2.9717-3.5151c.6178-.70841 1.377-1.06262 2.2782-1.06262.3337 0 .6675.05893 1.0012.17742.5669.20187 1.0259.56422 1.377 1.08769.3665.50592.5501 1.07077.5501 1.69455V17.5403c0 .8094-.2915 1.5097-.8758 2.1002-.5675.573-1.2604.8595-2.0779.8595-.8008 0-1.493-.2865-2.0779-.8601-.5669-.5899-.8504-1.2902-.8504-2.0996v-2.0148c-.0496-.5499-.5303-.2032-.7009 0-.4503.8431-1.31369 1.3616-2.35264 1.366ZM21.447 8.60998c-.7009 0-1.3015-.24449-1.8019-.73348-.4838-.50571-.7257-1.11277-.7257-1.82118s.2419-1.30711.7257-1.79611c.5004-.50571 1.101-.75856 1.8019-.75856.7009 0 1.3017.25285 1.8025.75856.5003.489.7505 1.0877.7505 1.79611 0 .70841-.2502 1.31547-.7505 1.82118-.5008.48899-1.1016.73348-1.8025.73348Zm.0248.50655c.7009 0 1.2935.25285 1.7777.75856.5003.50571.7505 1.11301.7505 1.82181v6.2484c0 .7084-.2502 1.3155-.7505 1.8212-.4838.489-1.0764.7335-1.7777.7335-.7005 0-1.3011-.2445-1.8019-.7335-.5003-.5057-.7505-1.1128-.7505-1.8212v-6.2484c0-.7084.2502-1.3157.7505-1.82181.5004-.50571 1.101-.75856 1.8019-.75856Z",
};
const MARKS = {
  qq_official: ["Q", "#1ebafc", "qq"],
  weixin_oc: ["微", "#07c160", "wechat"],
  telegram: ["T", "#26a5e4", "telegram"],
  discord: ["D", "#5865f2", "discord"],
  kook: ["K", "#4f9a1c"],
  lark: ["飞", "#3370ff"],
  dingtalk: ["钉", "#1677ff"],
  slack: ["S", "#611f69"],
  wecom_ai_bot: ["企", "#0a7fe0"],
  mattermost: ["M", "#0058cc", "mattermost"],
  misskey: ["Mi", "#86b300", "misskey"],
  wecom: ["企", "#0a7fe0"],
  weixin_official_account: ["公", "#07c160", "wechat"],
  qq_official_webhook: ["Q", "#1ebafc", "qq"],
  aiocqhttp: ["N", "#d6528f"],
  satori: ["Sa", "#7a5af8"],
};
function brand(node, kind) {
  const [, colour] = MARKS[kind] || [];
  node.style.setProperty("--brand", colour || "#1c1c1a");
}
function mark(node, kind) {
  brand(node, kind);
  const [glyph, , logo] = MARKS[kind] || [kind.slice(0, 1).toUpperCase()];
  if (!LOGOS[logo]) {
    node.textContent = glyph;
    return;
  }
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", LOGOS[logo]);
  svg.append(path);
  node.replaceChildren(svg);
}
function badge(kind, size = "") {
  const node = document.createElement("span");
  node.className = `badge ${size}`.trim();
  node.setAttribute("aria-hidden", "true");
  mark(node, kind);
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
  mark($("panel-badge"), item.id);
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
