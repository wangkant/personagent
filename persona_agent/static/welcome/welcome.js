"use strict";
const $ = (id) => document.getElementById(id);
const translations = {
  zh: {
    chat: "开始聊天",
    platforms: "连接平台",
    settings: "角色与设置",
    activity: "动态",
    activityLead: "它在哪些群和私聊里，最近说了什么，学到了什么。",
    activityConnect: "去连接平台",
    activityNotRunning: "角色还没有运行。在「开始聊天」里说一句话，或者连上一个平台，它就会启动。",
    activityNone: "还没有聊天记录。连上一个平台，把它拉进群或私聊它，这里就会出现。",
    activityOff: "动态已关闭（.env 里的 DASHBOARD_ENABLED=false）。",
    activity_unavailable: "暂时读不到角色的动态，稍后会自动重试。",
    activity_changed: "这条已经被处理过了，列表已刷新。",
    invalid_chat: "这个聊天已经不在了。",
    activityHere: "这个页面",
    activityGroup: "群聊",
    activityDm: "私聊",
    activityReview: "等你确认",
    activityReviewHint: "这些改动还在等更多反应才会自动生效，你也可以直接决定。",
    activityLearned: "学到的",
    activityNotes: "记住的事",
    activityRecent: "最近",
    activityRecentNone: "还没有记录。这里只保留最近的动态，角色重启后会清空。",
    activityWording: "换个说法",
    activityRepeat: "值得重复的回复",
    activitySaid: "它说的",
    activityBetter: "改成",
    activityLesson: "以后都这样",
    activityFrom: "来自 {who}",
    listSep: "、",
    activityKeep: "保留",
    activityDiscard: "不要",
    activityUndo: "撤销",
    activityKept: "已保留，之后的回复会用上。",
    activityDiscarded: "已放弃这条改动。",
    activityUndone: "已撤销，它不会再这样说。",
    activityQuiet: "没开口",
    activityCount: "×{n}",
    justNow: "刚刚",
    minutesAgo: "{n} 分钟前",
    hoursAgo: "{n} 小时前",
    r_below: "没被叫到，消息数还没到插话门槛",
    r_sleep: "深夜时段，为了作息自然跳过",
    r_skip: "为了节奏自然随机跳过",
    r_passed: "判断这里不需要它说话",
    r_addressed: "被点名或 @",
    r_sticky: "回应之前的点名",
    r_followup: "接着自己刚才的话",
    r_trigger: "消息数到了，考虑插话",
    r_first: "第一次在这个聊天出现",
    m_called: "被叫到",
    m_owner: "管理员",
    m_judge: "自己决定插话",
    m_judge_quiet: "可以插话",
    m_followup: "跟进",
    m_proactive: "主动",
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
    personaTitle: "人设",
    personaHint: "写它是谁、怎么说话、在意什么。保存后马上生效，它学到的东西会保留。",
    personaSave: "保存人设",
    personaSaving: "正在保存…",
    personaUndo: "撤销修改",
    personaSaved: "人设已保存，角色已按新人设重新启动。",
    invalid_persona: "人设不能为空，也不能超过 4000 字。",
    save: "保存",
    featuresTitle: "更多功能",
    searchTitle: "联网搜索",
    searchHint: "遇到不熟的事会先查一下。默认用 DuckDuckGo，不需要密钥；填 Tavily 的密钥会更稳定。",
    searchFree: "DuckDuckGo，免费",
    searchTavily: "Tavily",
    tavilyKeep: "留空保留已保存的 Tavily 密钥",
    tavilyNew: "Tavily API Key（可选）",
    tavilyClear: "改回免费搜索",
    visionTitle: "看懂图片",
    visionHint: "收到图片和表情包时，用一个能看图的模型描述它；不开时只认图里的文字。",
    visionModel: "看图模型",
    visionSame: "和聊天用同一个服务和密钥",
    proactiveTitle: "偶尔主动说话",
    proactiveHint: "群聊或私聊安静一阵后，它可能会主动开个话题，次数很少。",
    proactivePlatforms: "只在这些平台上（都不勾就是全部）：",
    featuresSaved: "已保存，角色已按新的设置重新启动。",
    invalid_feature: "这里有一项填得不对，检查一下密钥和平台。",
    gsTitle: "开始使用",
    gsPlatform: "连接一个平台",
    updateLink: "新版本 {version}",
    updateTitle: "personagent {version} 已发布",
    updateNotes: "更新内容 ↗",
    updateRun: "退出 personagent，运行下面这条命令，再重新打开。",
    updateOpens: "退出 personagent，再用下面这条命令打开新版。",
    updateDownload: "在更新内容页下载新版源码，解压后覆盖这个文件夹。",
    copy: "复制",
    copied: "已复制",
    close: "关闭",
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
    pasteInstead: "改为手动填写",
    scanInstead: "改回扫码",
    pasteNote: "在平台后台创建机器人后，把下面几项复制过来。",
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
    scanHelp_qq_official: "用手机 QQ 扫码，确认新建或选用一个机器人。",
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
    activity: "Activity",
    activityLead: "Where it is, what it said lately, and what it learned.",
    activityConnect: "Connect an app",
    activityNotRunning: "The character isn't running yet. Say something in Chat, or connect an app, and it starts.",
    activityNone: "No chats yet. Connect an app and add it to a group or message it, and they show up here.",
    activityOff: "Activity is turned off (DASHBOARD_ENABLED=false in .env).",
    activity_unavailable: "Couldn't read the character's activity just now. It will try again shortly.",
    activity_changed: "That one was already handled. The list is up to date now.",
    invalid_chat: "That chat is no longer there.",
    activityHere: "This page",
    activityGroup: "group",
    activityDm: "DM",
    activityReview: "Waiting for you",
    activityReviewHint: "These changes are waiting for more reactions before they apply on their own. You can decide now.",
    activityLearned: "Learned",
    activityNotes: "Remembers",
    activityRecent: "Recent",
    activityRecentNone: "Nothing yet. Only recent activity is kept, and a restart clears it.",
    activityWording: "Better wording",
    activityRepeat: "Reply worth repeating",
    activitySaid: "It said",
    activityBetter: "Instead",
    activityLesson: "From now on",
    activityFrom: "from {who}",
    listSep: ", ",
    activityKeep: "Keep",
    activityDiscard: "Discard",
    activityUndo: "Undo",
    activityKept: "Kept. Its next replies will use it.",
    activityDiscarded: "Discarded.",
    activityUndone: "Undone. It won't say it this way any more.",
    activityQuiet: "Stayed quiet",
    activityCount: "×{n}",
    justNow: "just now",
    minutesAgo: "{n} min ago",
    hoursAgo: "{n} h ago",
    r_below: "not addressed, below the message count for joining in",
    r_sleep: "night hours, skipped to keep a natural rhythm",
    r_skip: "skipped at random to keep a natural rhythm",
    r_passed: "judged it had nothing to add",
    r_addressed: "called by name or @-mentioned",
    r_sticky: "answering an earlier call",
    r_followup: "following up on its own reply",
    r_trigger: "enough messages to consider joining in",
    r_first: "first time in this chat",
    m_called: "called",
    m_owner: "admin",
    m_judge: "joined in on its own",
    m_judge_quiet: "could join in",
    m_followup: "follow-up",
    m_proactive: "proactive",
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
    personaTitle: "Persona",
    personaHint:
      "Who it is, how it talks and what it cares about. Saving applies it right away and keeps what it has learned.",
    personaSave: "Save persona",
    personaSaving: "Saving…",
    personaUndo: "Undo changes",
    personaSaved: "Persona saved. The character restarted with it.",
    invalid_persona: "The persona can't be empty or longer than 4,000 characters.",
    save: "Save",
    featuresTitle: "More features",
    searchTitle: "Web search",
    searchHint: "It looks up what it does not know. DuckDuckGo needs no key; a Tavily key is more reliable.",
    searchFree: "DuckDuckGo, free",
    searchTavily: "Tavily",
    tavilyKeep: "Leave blank to keep the saved Tavily key",
    tavilyNew: "Tavily API key (optional)",
    tavilyClear: "Back to free search",
    visionTitle: "Understand images",
    visionHint: "Describes images and stickers with a vision model; off, it reads only the text in them.",
    visionModel: "Vision model",
    visionSame: "Use the chat service and key",
    proactiveTitle: "Sometimes speak first",
    proactiveHint: "After a group or DM has been quiet for a while, it may start a topic, rarely.",
    proactivePlatforms: "Only on these apps (none checked means all):",
    featuresSaved: "Saved. The character restarted with it.",
    invalid_feature: "Something here is not right; check the keys and apps.",
    gsTitle: "Getting started",
    gsPlatform: "Connect an app",
    updateLink: "{version} available",
    updateTitle: "personagent {version} is out",
    updateNotes: "What's new ↗",
    updateRun: "Quit personagent, run this command, then open it again.",
    updateOpens: "Quit personagent, then open the new version with this command.",
    updateDownload: "Download the new source from the release page and unpack it over this folder.",
    copy: "Copy",
    copied: "Copied",
    close: "Close",
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
    pasteInstead: "Paste values instead",
    scanInstead: "Scan instead",
    pasteNote: "Create the bot in the platform's console, then copy these values here.",
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
    scanHelp_qq_official: "Scan with mobile QQ and confirm a new bot or one you made.",
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
// The page's languages and their BCP 47 tags. English and Chinese live above;
// the others are translations in /assets/i18n/<code>.json, loaded when chosen,
// and a string one lacks shows in English. The character's own language is
// separate and only en or zh (see charLang).
const LANGS = {
  en: "en",
  zh: "zh-CN",
  "zh-TW": "zh-TW",
  ja: "ja",
  ko: "ko",
  es: "es",
  fr: "fr",
  de: "de",
  "pt-BR": "pt-BR",
  ru: "ru",
};
const LANG_KEY = "personagent-page-language";
// Platform, service and personality names from the catalog, keyed by English.
const catalogText = {};
function browserLang() {
  for (const tag of navigator.languages || [navigator.language || ""]) {
    const low = tag.toLowerCase();
    if (low.startsWith("zh"))
      return /^zh-(tw|hk|mo|hant)/.test(low) ? "zh-TW" : "zh";
    if (low.startsWith("pt")) return "pt-BR";
    const base = low.split("-")[0];
    if (LANGS[base]) return base;
  }
  return "";
}
function storedLang() {
  try {
    const code = localStorage.getItem(LANG_KEY);
    return code && LANGS[code] ? code : "";
  } catch {
    return "";
  }
}
let lang = storedLang() || browserLang() || "en";
// What saving the settings writes to AGENT_LANG: either Chinese means zh and
// English en; any other page language keeps what the character speaks now.
const charLang = () =>
  lang === "zh" || lang === "zh-TW"
    ? "zh"
    : lang !== "en" && state?.lang === "zh"
      ? "zh"
      : "en";
const defaultName = () => (charLang() === "zh" ? "小夏" : "Nova");
async function loadLang(code) {
  if (translations[code]) return;
  try {
    const response = await fetch(`/assets/i18n/${code}.json`, {
      credentials: "omit",
    });
    if (!response.ok) return;
    const data = await response.json();
    translations[code] = data.strings || {};
    catalogText[code] = data.catalog || {};
  } catch {
    // Without the file every string shows in English.
  }
}
let state = null,
  catalog = null,
  selected = null,
  pasting = false,
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
    (value, [name, text]) => value.replaceAll(`{${name}}`, () => text),
    translations[lang]?.[key] ||
      translations.en[key] ||
      translations[lang]?.generic ||
      translations.en.generic,
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
    option.textContent = pick(item.name);
    select.append(option);
  }
  select.value = selected;
}
function renderLanguage() {
  document.documentElement.lang = LANGS[lang] || "en";
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
      chars.push({ id: "custom", name: [t("custom"), t("custom")] });
    options($("character"), chars, character);
    tiles();
    if (selected) buildFields(true);
  }
  updateNames();
  renderStatus();
  renderActivity();
  if (!saving)
    $("save").textContent = t(state?.configured ? "saveAgain" : "saveStart");
}
function updateNames() {
  const name =
    $("character-name").value.trim() || state?.name || defaultName();
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
function characterOptions() {
  const chars = [...catalog.characters];
  if (state.character === "custom")
    chars.push({ id: "custom", name: [t("custom"), t("custom")] });
  options($("character"), chars, state.character);
  $("custom-note").hidden = state.character !== "custom";
}
function populate() {
  options($("provider"), catalog.providers, state.provider);
  characterOptions();
  $("character-name").value = state.name || defaultName();
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
  if ((next === "platforms" || next === "activity") && !state.configured) {
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
  $("activity-view").hidden = next !== "activity";
  $("page-label").textContent = t(
    setup
      ? state.configured
        ? "settings"
        : "welcome"
      : next === "platforms" || next === "activity"
        ? next
        : "chat",
  );
  $("persona-card").hidden = !(setup && state.configured);
  $("features-card").hidden = !(setup && state.configured);
  if (setup && state.configured) {
    loadPersona();
    if (!featuresDirty) fillFeatures();
  }
  if (next === "chat" && state.configured) $("message").focus();
  if (next === "activity") {
    renderActivity();
    activityLoop();
  }
}
// The persona as last loaded or saved; edits are compared with it.
let personaShown = null,
  personaSaving = false;
function personaEdited() {
  const text = $("persona-text").value;
  $("persona-count").textContent = `${Array.from(text).length} / 4000`;
  $("persona-undo").hidden = personaShown === null || text === personaShown;
}
async function loadPersona() {
  // Keep unsaved edits when the page is opened again.
  if (personaShown !== null && $("persona-text").value !== personaShown) return;
  try {
    const { text } = await api("persona");
    personaShown = text;
    $("persona-text").value = text;
    $("persona-error").hidden = true;
    personaEdited();
  } catch (error) {
    $("persona-error").textContent = t(error.message);
    $("persona-error").hidden = false;
  }
}
const pick = (pair) =>
  lang === "zh" ? pair[1] : catalogText[lang]?.[pair[0]] || pair[0];
const spec = (kind) => catalog?.platforms.find((p) => p.id === kind);
const platformName = (kind) => (spec(kind) ? pick(spec(kind).name) : kind);
// Each platform's mark: its logo, otherwise a short monogram in its
// colour. Logos are their owners' trademarks and only name the platform.
// Simple Icons (CC0-1.0): QQ, WeChat, Telegram, Discord, Mattermost and
// Misskey. MingCute (Apache-2.0): DingTalk. IconPark (Apache-2.0): Feishu.
// SVG Logos (CC0-1.0): Slack. TDesign (MIT): WeCom. KOOK: its site icon.
// OneBot: the logo in botuniverse/onebot (MIT). Satori has none.
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
  dingtalk: {
    box: "0 0 24 24",
    svg: "<path fill=\"currentColor\" fill-rule=\"evenodd\" d=\"M6.802 2.02a1 1 0 0 1 .849.22l9.751 8.359a2 2 0 0 1 .235 2.799l-1.06 1.272l.87.436a1 1 0 0 1 .134 1.708l-7 5a1 1 0 0 1-1.539-1.101l1.21-4.034c-2.363-.9-3.747-3.055-4.233-5.483A1 1 0 0 1 7.01 10c-.474-.703-.86-1.42-1.134-2.149c-.649-1.73-.658-3.523.23-5.298a1 1 0 0 1 .696-.533\" clip-rule=\"evenodd\"/>",
  },
  feishu: {
    box: "0 0 48 48",
    svg: "<g fill=\"none\"><path stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"4\" d=\"M17 29C21 29 25 26.9339 28 23.4065C36 14 41.4242 16.8166 44 17.9998C38.5 20.9998 40.5 29.6233 33 35.9998C28.382 39.9259 23.4945 41.014 19 41C12.5231 40.9799 6.86226 37.7637 4 35.4063V16.9998\"/><path fill=\"currentColor\" d=\"M5.64808 15.8669C5.02231 14.9567 3.77715 14.7261 2.86694 15.3519C1.95673 15.9777 1.72615 17.2228 2.35192 18.1331L5.64808 15.8669ZM36.0021 35.7309C36.958 35.1774 37.2843 33.9539 36.7309 32.9979C36.1774 32.042 34.9539 31.7157 33.9979 32.2691L36.0021 35.7309ZM2.35192 18.1331C5.2435 22.339 10.7992 28.144 16.8865 32.2239C19.9345 34.2667 23.217 35.946 26.449 36.7324C29.6946 37.522 33.0451 37.4428 36.0021 35.7309L33.9979 32.2691C32.2049 33.3072 29.9929 33.478 27.3947 32.8458C24.783 32.2103 21.9405 30.7958 19.1135 28.9011C13.4508 25.106 8.2565 19.661 5.64808 15.8669L2.35192 18.1331Z\"/><path stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"4\" d=\"M33.5947 17C32.84 14.7027 30.8551 9.94054 27.5947 7H11.5947C15.2174 10.6757 23.0002 16 27.0002 24\"/></g>",
  },
  slack: {
    box: "0 0 256 256",
    svg: "<path fill=\"#e01e5a\" d=\"M53.841 161.32c0 14.832-11.987 26.82-26.819 26.82S.203 176.152.203 161.32c0-14.831 11.987-26.818 26.82-26.818H53.84zm13.41 0c0-14.831 11.987-26.818 26.819-26.818s26.819 11.987 26.819 26.819v67.047c0 14.832-11.987 26.82-26.82 26.82c-14.83 0-26.818-11.988-26.818-26.82z\"/><path fill=\"#36c5f0\" d=\"M94.07 53.638c-14.832 0-26.82-11.987-26.82-26.819S79.239 0 94.07 0s26.819 11.987 26.819 26.819v26.82zm0 13.613c14.832 0 26.819 11.987 26.819 26.819s-11.987 26.819-26.82 26.819H26.82C11.987 120.889 0 108.902 0 94.069c0-14.83 11.987-26.818 26.819-26.818z\"/><path fill=\"#2eb67d\" d=\"M201.55 94.07c0-14.832 11.987-26.82 26.818-26.82s26.82 11.988 26.82 26.82s-11.988 26.819-26.82 26.819H201.55zm-13.41 0c0 14.832-11.988 26.819-26.82 26.819c-14.831 0-26.818-11.987-26.818-26.82V26.82C134.502 11.987 146.489 0 161.32 0s26.819 11.987 26.819 26.819z\"/><path fill=\"#ecb22e\" d=\"M161.32 201.55c14.832 0 26.82 11.987 26.82 26.818s-11.988 26.82-26.82 26.82c-14.831 0-26.818-11.988-26.818-26.82V201.55zm0-13.41c-14.831 0-26.818-11.988-26.818-26.82c0-14.831 11.987-26.818 26.819-26.818h67.25c14.832 0 26.82 11.987 26.82 26.819s-11.988 26.819-26.82 26.819z\"/>",
  },
  wecom: {
    box: "0 0 24 24",
    svg: "<path fill=\"currentColor\" d=\"m17.326 8.158l-.003-.007a6.6 6.6 0 0 0-1.178-1.674c-1.266-1.307-3.067-2.19-5.102-2.417a9.3 9.3 0 0 0-2.124 0h-.001c-2.061.228-3.882 1.107-5.14 2.405a6.7 6.7 0 0 0-1.194 1.682A5.7 5.7 0 0 0 2 10.657c0 1.106.332 2.218.988 3.201l.006.01c.391.594 1.092 1.39 1.637 1.83l.983.793l-.208.875l.527-.267l.708-.358l.761.225c.467.137.955.227 1.517.29h.005q.515.06 1.026.059c.355 0 .724-.02 1.095-.06a9 9 0 0 0 1.346-.258c.095.7.43 1.337.932 1.81c-.658.208-1.352.358-2.061.436c-.442.048-.883.072-1.312.072q-.627 0-1.253-.072a10.7 10.7 0 0 1-1.861-.36l-2.84 1.438s-.29.131-.44.131c-.418 0-.702-.285-.702-.704c0-.252.067-.598.128-.84l.394-1.653c-.728-.586-1.563-1.544-2.052-2.287A7.76 7.76 0 0 1 0 10.658a7.7 7.7 0 0 1 .787-3.39a8.7 8.7 0 0 1 1.551-2.19c1.61-1.665 3.878-2.73 6.359-3.006a11.3 11.3 0 0 1 2.565 0c2.47.275 4.712 1.353 6.323 3.017a8.6 8.6 0 0 1 1.539 2.192c.466.945.769 1.937.769 2.978a3.06 3.06 0 0 0-2-.005c-.001-.644-.189-1.329-.564-2.09zm4.125 6.977l-.024-.024l-.024-.018l-.024-.018l-.096-.095a4.24 4.24 0 0 1-1.169-2.192q0-.038-.006-.075l-.006-.056l-.035-.144a1.3 1.3 0 0 0-.358-.61a1.386 1.386 0 0 0-1.957 0a1.4 1.4 0 0 0 0 1.963c.191.191.418.311.668.371c.024.012.06.012.084.012q.019 0 .041.006q.023.005.042.006a4.24 4.24 0 0 1 2.231 1.186c.048.048.096.095.131.143a.323.323 0 0 0 .466 0a.35.35 0 0 0 .036-.455m-1.05 4.37l-.025.025c-.119.096-.31.096-.453-.036a.326.326 0 0 1 0-.467c.047-.036.094-.083.141-.13l.002-.002a4.27 4.27 0 0 0 1.187-2.28q.005-.024.006-.043c0-.024 0-.06.012-.084a1.386 1.386 0 0 1 2.326-.67a1.4 1.4 0 0 1 0 1.964c-.167.18-.382.299-.608.359l-.143.036l-.057.005q-.035.006-.075.007a4.2 4.2 0 0 0-2.183 1.173l-.095.096q-.009.01-.018.024t-.018.024m-4.392-1.053l.024.024l.024.018q.015.009.024.018l.096.096a4.25 4.25 0 0 1 1.169 2.19q0 .04.006.076q.005.03.006.057l.035.143c.06.228.18.443.358.611c.537.539 1.42.539 1.957 0a1.4 1.4 0 0 0 0-1.964a1.4 1.4 0 0 0-.668-.371c-.024-.012-.06-.012-.084-.012q-.018 0-.041-.006l-.042-.006a4.25 4.25 0 0 1-2.231-1.185a1.4 1.4 0 0 1-.131-.144a.323.323 0 0 0-.466 0a.325.325 0 0 0-.036.455m1.039-4.358l.024-.024a.32.32 0 0 1 .453.035a.326.326 0 0 1 0 .467c-.047.036-.094.083-.141.13l-.002.002a4.27 4.27 0 0 0-1.187 2.281l-.006.042c0 .024 0 .06-.012.084a1.386 1.386 0 0 1-2.326.67a1.4 1.4 0 0 1 0-1.963c.166-.18.381-.3.608-.36l.143-.035q.026 0 .056-.006q.037-.005.075-.006a4.2 4.2 0 0 0 2.183-1.174l.096-.095l.018-.025z\"/>",
  },
  kook: {
    img: "data:image/png;base64,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",
  },
  onebot: {
    img: "data:image/png;base64,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",
  },
};
const MARKS = {
  qq_official: ["Q", "#1ebafc", "qq"],
  weixin_oc: ["微", "#07c160", "wechat"],
  telegram: ["T", "#26a5e4", "telegram"],
  discord: ["D", "#5865f2", "discord"],
  kook: ["K", "#1c1c1a", "kook"],
  lark: ["飞", "#3370ff", "feishu"],
  dingtalk: ["钉", "#0089ff", "dingtalk"],
  slack: ["S", "#611f69", "slack"],
  wecom_ai_bot: ["企", "#0082ef", "wecom"],
  mattermost: ["M", "#0058cc", "mattermost"],
  misskey: ["Mi", "#86b300", "misskey"],
  wecom: ["企", "#0082ef", "wecom"],
  weixin_official_account: ["公", "#07c160", "wechat"],
  qq_official_webhook: ["Q", "#1ebafc", "qq"],
  aiocqhttp: ["N", "#1c1c1a", "onebot"],
  qq: ["Q", "#1ebafc", "qq"],
  satori: ["Sa", "#7a5af8"],
};
function brand(node, kind) {
  const [, colour] = MARKS[kind] || [];
  node.style.setProperty("--brand", colour || "#1c1c1a");
}
function mark(node, kind) {
  brand(node, kind);
  const [glyph, , key] = MARKS[kind] || [kind.slice(0, 1).toUpperCase()];
  const logo = LOGOS[key];
  if (!logo) {
    node.textContent = glyph;
    return;
  }
  if (logo.img) {
    const img = document.createElement("img");
    img.alt = "";
    img.src = logo.img;
    node.replaceChildren(img);
    return;
  }
  // The markup is the constant above, never page or platform data.
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", logo.box || "0 0 24 24");
  if (typeof logo === "string") {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", logo);
    svg.append(path);
  } else svg.innerHTML = logo.svg;
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
  // A scan platform with fields can take pasted values instead.
  const scanning = item.group === "scan" && !pasting;
  const note = item.group === "scan" && pasting ? t("pasteNote") : pick(item.note);
  $("panel-note").textContent = note;
  $("panel-note").hidden = !note;
  $("panel-guide").href = item.guide || "#";
  $("panel-guide").hidden = !item.guide || scanning;
  $("panel-howto").hidden = !note && $("panel-guide").hidden;
  $("panel-mode").hidden = item.group !== "scan" || !item.fields.length;
  $("panel-mode").textContent = t(pasting ? "scanInstead" : "pasteInstead");
  const box = $("panel-fields");
  box.replaceChildren();
  box.hidden = scanning;
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
    input.required = field.required && !field.default && !scanning;
    input.value = kept[field.key] || "";
    box.append(label, input);
  }
  $("panel-submit").textContent = t(scanning ? "getQr" : "connectNow");
}
function openPanel(kind) {
  const job = state.job;
  if (job.state === "working" && job.platform !== kind) {
    toast(t("working"));
    return;
  }
  selected = kind;
  pasting = false;
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
// ---- the optional features, on the settings screen
const GS_KEY = "personagent-getting-started-closed";
// Edits in the features card survive a re-render until they are saved.
let featuresDirty = false,
  gettingStartedClosed = false;
function fillFeatures() {
  const features = state.features;
  featuresDirty = false;
  delete $("tavily-clear").dataset.clear;
  $("search-state").textContent = t(features.search === "tavily" ? "searchTavily" : "searchFree");
  $("tavily-key").value = "";
  $("tavily-key").placeholder = t(features.search === "tavily" ? "tavilyKeep" : "tavilyNew");
  $("tavily-clear").hidden = features.search !== "tavily";
  $("vision-on").checked = features.vision.enabled;
  $("vision-model").value = features.vision.model;
  $("vision-model").placeholder = "qwen-vl-max";
  $("vision-same").checked = features.vision.sameAsChat || !features.vision.baseUrl;
  $("vision-base").value = features.vision.baseUrl;
  $("vision-key").value = "";
  $("vision-key").placeholder = features.vision.keyHint ? t("keySaved") : "";
  $("proactive-on").checked = features.proactive.enabled;
  $("proactive-platforms").replaceChildren(
    ...state.platforms.map((kind) => {
      const box = Object.assign(document.createElement("input"), {
        type: "checkbox",
        value: kind,
        checked: features.proactive.platforms.includes(kind),
      });
      const label = document.createElement("label");
      label.className = "check";
      const text = document.createElement("span");
      text.textContent = platformName(kind);
      label.append(box, text);
      return label;
    }),
  );
  $("features-error").hidden = true;
  featureFields();
}
function featureFields() {
  $("vision-fields").hidden = !$("vision-on").checked;
  $("vision-own").hidden = $("vision-same").checked;
  $("proactive-fields").hidden = !$("proactive-on").checked || !state.platforms.length;
}
function closedGettingStarted() {
  if (gettingStartedClosed) return true;
  try {
    return localStorage.getItem(GS_KEY) === "1";
  } catch {
    return false;
  }
}
function renderGettingStarted() {
  $("getting-started").hidden =
    !state.configured || state.platforms.length > 0 || closedGettingStarted();
  $("gs-close").setAttribute("aria-label", t("close"));
}
// ---- a newer release on PyPI; closing its notice hides that version only
const UPDATE_KEY = "personagent-update-closed";
let updateClosed = "";
function closedUpdate(version) {
  if (updateClosed === version) return true;
  try {
    return localStorage.getItem(UPDATE_KEY) === version;
  } catch {
    return false;
  }
}
function renderUpdate() {
  // The bar lives in the chat view, which a page still in setup does not show.
  const update = state.configured ? state.update : null;
  // Rewriting unchanged text on every poll would drop a selection in it.
  const set = (id, text) => {
    if ($(id).textContent !== text) $(id).textContent = text;
  };
  $("update-link").hidden = !update;
  $("update-bar").hidden = !update || closedUpdate(update.version);
  if (!update) return;
  set("update-link", t("updateLink", { version: update.version }));
  set("update-title", t("updateTitle", { version: update.version }));
  $("update-notes").href = update.url;
  set("update-how", t(!update.command ? "updateDownload" : update.opens ? "updateOpens" : "updateRun"));
  $("update-command-row").hidden = !update.command;
  set("update-command", update.command);
  $("update-close").setAttribute("aria-label", t("close"));
}
function renderStatus() {
  if (!state) return;
  $("version").textContent = `v${state.version}`;
  renderGettingStarted();
  renderUpdate();
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
// ---- Activity: where it is, what it said lately, what it learned
let activity = null,
  activityChat = null,
  activitySelected = "",
  activityError = "",
  activityTimer = null,
  activityBusy = false,
  // Bumped by every load and decision, so an older answer never wins.
  activitySeq = 0,
  // What the view last drew; a poll that brings nothing new leaves the
  // page, and the keyboard focus in it, alone.
  activityShown = "";
const ACTIVITY_MS = 8000;
const ACTIVITY_IDLE_MS = 30000;
// Why it spoke or stayed quiet, as the service records it.
const REASONS = {
  "below the trigger count": "r_below",
  "sleep window": "r_sleep",
  "spontaneous skip": "r_skip",
  passed: "r_passed",
  addressed: "r_addressed",
  "sticky call": "r_sticky",
  "followup window": "r_followup",
  "trigger count": "r_trigger",
  "first appearance": "r_first",
};
// Platforms a chat can come from that Connect apps does not list.
const CHAT_PLATFORMS = { qq: "QQ", matrix: "Matrix", satori: "Satori" };
function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}
function ago(epoch) {
  const seconds = Date.now() / 1000 - Number(epoch || 0);
  if (!epoch || seconds < 60) return t("justNow");
  if (seconds < 3600)
    return t("minutesAgo", { n: String(Math.floor(seconds / 60)) });
  if (seconds < 86400)
    return t("hoursAgo", { n: String(Math.floor(seconds / 3600)) });
  return new Date(epoch * 1000).toLocaleDateString(LANGS[lang] || "en", {
    month: "short",
    day: "numeric",
  });
}
function chatTitle(chat) {
  if (chat.platform === "browser") return t("activityHere");
  const platform = spec(chat.platform)
    ? pick(spec(chat.platform).name)
    : CHAT_PLATFORMS[chat.platform] || chat.platform;
  return `${platform} ${t(chat.kind === "dm" ? "activityDm" : "activityGroup")}`;
}
function chatTail(chat) {
  if (chat.platform === "browser") return "";
  const id = String(chat.id).split(":").pop();
  return id.length > 8 ? `…${id.slice(-6)}` : id;
}
function chatBadge(chat) {
  if (chat.platform !== "browser") return badge(chat.platform, "small");
  const node = el("span", "badge small");
  node.setAttribute("aria-hidden", "true");
  node.append(document.querySelector(".brand-mark svg").cloneNode(true));
  return node;
}
function reasonText(row) {
  const key = REASONS[row.reason];
  return key ? t(key) : row.reason;
}
function modeText(row) {
  if (!row.mode) return "";
  const key =
    row.mode === "judge" && !row.spoke ? "m_judge_quiet" : `m_${row.mode}`;
  return translations[lang]?.[key] || translations.en[key] || row.mode;
}
function renderActivityDot() {
  $("activity-dot").hidden = !(activity?.chats || []).some(
    (chat) => chat.review > 0,
  );
}
function renderActivity() {
  renderActivityDot();
  if (view !== "activity") return;
  const shown = JSON.stringify([
    lang,
    activitySelected,
    activityBusy,
    activityError,
    activity,
    activityChat,
    // "3 min ago" moves on even when nothing else does.
    Math.floor(Date.now() / 60000),
  ]);
  if (shown === activityShown) return;
  activityShown = shown;
  const focused = document.activeElement?.dataset?.focus || "";
  const chats = activity?.chats || [];
  const empty = !activity
    ? activityError
    : !activity.running
      ? "activityNotRunning"
      : activity.off
        ? "activityOff"
        : chats.length
          ? ""
          : "activityNone";
  $("activity-empty").hidden = !empty;
  $("activity-empty-text").textContent = empty ? t(empty) : "";
  $("activity-connect").hidden = !["activityNone", "activityNotRunning"].includes(empty);
  $("activity-body").hidden = !activity || Boolean(empty);
  if (!activity || empty) return;
  $("activity-chats").replaceChildren(
    ...chats.map((chat) => {
      const row = el(
        "button",
        `activity-row${chat.id === activitySelected ? " active" : ""}`,
      );
      row.type = "button";
      row.dataset.focus = `chat:${chat.id}`;
      if (chat.id === activitySelected) row.setAttribute("aria-current", "true");
      const text = el("span", "row-text");
      text.append(
        el("strong", "", chatTitle(chat)),
        el(
          "small",
          "",
          [chatTail(chat), ago(chat.last)].filter(Boolean).join(" · "),
        ),
      );
      row.append(chatBadge(chat), text);
      if (chat.review)
        row.append(el("span", "count review", String(chat.review)));
      row.addEventListener("click", () => selectChat(chat.id));
      const item = el("li");
      item.append(row);
      return item;
    }),
  );
  renderChat();
  if (focused)
    document.querySelector(`[data-focus="${CSS.escape(focused)}"]`)?.focus();
}
function section(key, count) {
  const node = el("section", "activity-section");
  const title = el("h3", "", t(key));
  if (count) title.append(el("span", "count", String(count)));
  node.append(title);
  return node;
}
function action(key, cls, focus, run) {
  const button = el("button", cls, t(key));
  button.type = "button";
  button.dataset.focus = focus;
  button.disabled = activityBusy;
  button.addEventListener("click", run);
  return button;
}
function change(item, waiting) {
  const card = el("div", `change${waiting ? " waiting" : ""}`);
  const top = el("div", "change-top");
  const who = item.from.length
    ? t("activityFrom", { who: item.from.join(t("listSep")) })
    : "";
  top.append(
    el(
      "span",
      "change-kind",
      t(item.kind === "wording" ? "activityWording" : "activityRepeat"),
    ),
    el("small", "", [who, ago(item.when)].filter(Boolean).join(" · ")),
  );
  card.append(top);
  const body = el("div", "change-body");
  if (item.kind === "wording") {
    for (const [key, text, cls] of [
      ["activitySaid", item.said, "was"],
      ["activityBetter", item.better, "now"],
      // The fact behind the rewording, which every later reply in this chat sees.
      ...(item.lesson ? [["activityLesson", item.lesson, "lesson"]] : []),
    ]) {
      const line = el("div", `change-line ${cls}`);
      line.append(el("span", "label", t(key)), el("p", "", text));
      body.append(line);
    }
  } else body.append(el("p", "change-reply", item.said));
  card.append(body);
  const buttons = el("div", "change-actions");
  const keep = ["replace", "promote"].find((name) =>
    item.actions.includes(name),
  );
  if (waiting) {
    if (keep)
      buttons.append(
        action("activityKeep", "primary small", `${keep}:${item.id}`, () =>
          decide(item, keep),
        ),
      );
    if (item.actions.includes("reject"))
      buttons.append(
        action("activityDiscard", "quiet", `reject:${item.id}`, () =>
          decide(item, "reject"),
        ),
      );
  } else if (item.actions.includes("rollback"))
    buttons.append(
      action("activityUndo", "secondary", `rollback:${item.id}`, () =>
        decide(item, "rollback"),
      ),
    );
  if (buttons.childElementCount) card.append(buttons);
  return card;
}
function recentLine(row) {
  const item = el("li", row.spoke ? "spoke" : "passed");
  const said = (text) => {
    const line = el("p", "message");
    if (row.sender) line.append(el("strong", "", `${row.sender} `));
    line.append(text);
    return line;
  };
  if (!row.spoke) item.append(said(row.text));
  else {
    if (row.answered) item.append(said(row.answered));
    item.append(el("p", "reply", row.text));
  }
  const why = row.spoke
    ? [modeText(row)]
    : [t("activityQuiet"), reasonText(row)];
  if (row.count > 1) why.push(t("activityCount", { n: String(row.count) }));
  why.push(ago(row.when));
  item.append(el("small", "why", why.filter(Boolean).join(" · ")));
  return item;
}
function renderChat() {
  const box = $("activity-chat");
  const chat = activityChat?.id === activitySelected ? activityChat : null;
  if (!chat) {
    box.replaceChildren(
      el("p", "activity-note", activityError ? t(activityError) : ""),
    );
    return;
  }
  const summary = activity.chats.find((c) => c.id === chat.id) || chat;
  const head = el("div", "activity-head");
  const name = el("div");
  name.append(el("h2", "", chatTitle(summary)));
  if (chat.platform !== "browser")
    name.append(el("small", "", chat.id.replace(/^private:/, "")));
  head.append(chatBadge(summary), name);
  const parts = [head];
  if (activityError)
    parts.push(el("p", "activity-note error-note", t(activityError)));
  if (chat.review.length) {
    const part = section("activityReview", chat.review.length);
    part.append(el("p", "section-hint", t("activityReviewHint")));
    for (const item of chat.review) part.append(change(item, true));
    parts.push(part);
  }
  if (chat.learned.length) {
    const part = section("activityLearned", chat.learned.length);
    for (const item of chat.learned) part.append(change(item, false));
    parts.push(part);
  }
  if (chat.notes.length) {
    const part = section("activityNotes");
    const list = el("ul", "notes");
    for (const note of chat.notes) {
      const item = el("li");
      item.append(el("span", "", note.text));
      if (note.by && note.by !== "auto") item.append(el("small", "", note.by));
      list.append(item);
    }
    part.append(list);
    parts.push(part);
  }
  const recent = section("activityRecent");
  if (chat.recent.length) {
    const list = el("ul", "recent");
    list.append(...chat.recent.map(recentLine));
    recent.append(list);
  } else recent.append(el("p", "activity-note", t("activityRecentNone")));
  parts.push(recent);
  box.replaceChildren(...parts);
}
async function loadActivity(withChat) {
  const seq = ++activitySeq;
  try {
    const listed = await api("activity");
    if (seq !== activitySeq) return;
    activity = listed;
    activityError = "";
    const chats = activity.chats || [];
    // Open on a chat with something to decide, else the latest one.
    if (!chats.some((chat) => chat.id === activitySelected))
      activitySelected = (chats.find((chat) => chat.review) || chats[0] || {}).id || "";
    if (withChat && activitySelected) {
      const chat = await api(
        `activity/chat?id=${encodeURIComponent(activitySelected)}`,
      );
      if (seq !== activitySeq) return;
      activityChat = chat;
    }
  } catch (error) {
    if (seq !== activitySeq) return;
    activityError = error.message;
  }
  renderActivity();
}
async function activityLoop() {
  clearTimeout(activityTimer);
  if (ended) return;
  if (!document.hidden && state?.configured && !activityBusy)
    await loadActivity(view === "activity");
  clearTimeout(activityTimer);
  activityTimer = setTimeout(
    activityLoop,
    view === "activity" ? ACTIVITY_MS : ACTIVITY_IDLE_MS,
  );
}
function selectChat(id) {
  if (id === activitySelected) return;
  activitySelected = id;
  activityChat = null;
  renderActivity();
  activityLoop();
}
async function decide(item, verb) {
  if (activityBusy) return;
  activityBusy = true;
  const seq = ++activitySeq;
  renderActivity();
  try {
    const chat = await api("activity/decide", {
      id: item.id,
      action: verb,
      chat: activitySelected,
    });
    if (seq === activitySeq) activityChat = chat;
    toast(
      t(
        verb === "reject"
          ? "activityDiscarded"
          : verb === "rollback"
            ? "activityUndone"
            : "activityKept",
      ),
    );
  } catch (error) {
    toast(t(error.message));
  } finally {
    activityBusy = false;
    activityLoop();
  }
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
$("language").addEventListener("change", async () => {
  const oldDefault = defaultName();
  const next = $("language").value;
  await loadLang(next);
  // A later choice made while this file loaded wins.
  if ($("language").value !== next) return;
  lang = next;
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    // Private windows may refuse; the choice then lasts until the page closes.
  }
  if (!state.name && $("character-name").value === oldDefault)
    $("character-name").value = defaultName();
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
for (const id of ["vision-on", "vision-same", "proactive-on"])
  $(id).addEventListener("change", featureFields);
$("tavily-clear").addEventListener("click", () => {
  $("tavily-clear").dataset.clear = "1";
  $("tavily-clear").hidden = true;
  $("search-state").textContent = t("searchFree");
});
$("features-save").addEventListener("click", async () => {
  $("features-error").hidden = true;
  $("features-save").disabled = true;
  try {
    state = await api("features", {
      search: {
        tavilyKey: $("tavily-key").value,
        // A key typed after "back to free search" wins over the clear.
        clear: $("tavily-clear").dataset.clear === "1" && !$("tavily-key").value.trim(),
      },
      vision: {
        enabled: $("vision-on").checked,
        model: $("vision-model").value,
        sameAsChat: $("vision-same").checked,
        baseUrl: $("vision-base").value,
        apiKey: $("vision-key").value,
      },
      proactive: {
        enabled: $("proactive-on").checked,
        platforms: [...$("proactive-platforms").querySelectorAll("input:checked")].map(
          (box) => box.value,
        ),
      },
    });
    delete $("tavily-clear").dataset.clear;
    renderStatus();
    fillFeatures();
    toast(t("featuresSaved"));
  } catch (error) {
    $("features-error").textContent = t(error.message);
    $("features-error").hidden = false;
  } finally {
    $("features-save").disabled = false;
  }
});
$("gs-platform").addEventListener("click", () => showView("platforms"));
$("activity-connect").addEventListener("click", () => showView("platforms"));
$("gs-close").addEventListener("click", () => {
  try {
    localStorage.setItem(GS_KEY, "1");
  } catch {}
  gettingStartedClosed = true;
  $("getting-started").hidden = true;
});
$("update-link").addEventListener("click", () => {
  updateClosed = "";
  try {
    localStorage.removeItem(UPDATE_KEY);
  } catch {}
  showView("chat");
  renderUpdate();
});
$("update-close").addEventListener("click", () => {
  updateClosed = state.update ? state.update.version : "";
  try {
    localStorage.setItem(UPDATE_KEY, updateClosed);
  } catch {}
  $("update-bar").hidden = true;
});
$("update-copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("update-command").textContent);
    $("update-copy").textContent = t("copied");
    setTimeout(() => ($("update-copy").textContent = t("copy")), 2000);
  } catch {
    getSelection().selectAllChildren($("update-command"));
  }
});
$("features-card").addEventListener("input", () => (featuresDirty = true));
$("features-card").addEventListener("change", () => (featuresDirty = true));
$("tavily-key").addEventListener("input", () => delete $("tavily-clear").dataset.clear);
$("persona-text").addEventListener("input", personaEdited);
$("persona-undo").addEventListener("click", () => {
  $("persona-text").value = personaShown;
  $("persona-error").hidden = true;
  personaEdited();
});
$("persona-save").addEventListener("click", async () => {
  if (personaSaving) return;
  personaSaving = true;
  $("persona-error").hidden = true;
  $("persona-save").disabled = true;
  $("persona-save").textContent = t("personaSaving");
  // The save waits for the agent to restart; edits made meanwhile would be lost.
  $("persona-text").readOnly = true;
  const text = $("persona-text").value;
  try {
    state = await api("persona", { text });
    personaShown = text.trim();
    $("persona-text").value = personaShown;
    personaEdited();
    // The file is now the user's own, so a saved form must not replace it.
    characterOptions();
    renderStatus();
    toast(t("personaSaved"));
  } catch (error) {
    $("persona-error").textContent = t(error.message);
    $("persona-error").hidden = false;
  } finally {
    personaSaving = false;
    $("persona-text").readOnly = false;
    $("persona-save").disabled = false;
    $("persona-save").textContent = t("personaSave");
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
      lang: charLang(),
    });
    // A chosen personality rewrote persona.txt: drop the box's old text.
    if ($("character").value !== "custom") {
      personaShown = null;
      $("persona-text").value = "";
    }
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
  if (!$("panel-fields").hidden)
    for (const input of $("panel-fields").querySelectorAll("input"))
      values[input.name] = input.value;
  panelError = "";
  try {
    await api("platforms/connect", {
      platform: selected,
      values,
      mode: pasting ? "paste" : "",
      allowConversations: true,
    });
    fresh = true;
    await refresh();
  } catch (error) {
    panelError = t(error.message);
    renderStatus();
  }
});
$("panel-mode").addEventListener("click", () => {
  pasting = !pasting;
  panelError = "";
  buildFields(true);
  renderStatus();
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
  await loadLang(lang);
  if (!token) {
    toast(t("auth"));
    return;
  }
  try {
    [state, catalog] = await Promise.all([api("state"), api("catalog")]);
    // With no choice saved, the page follows the character into or out of
    // Chinese, as it always has; any other browser language stays.
    if (!storedLang()) {
      if (state.lang === "zh" && lang === "en") lang = "zh";
      else if (state.lang === "en" && (lang === "zh" || lang === "zh-TW"))
        lang = "en";
    }
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
    activityLoop();
  } catch (error) {
    toast(t(error.message));
  }
})();
