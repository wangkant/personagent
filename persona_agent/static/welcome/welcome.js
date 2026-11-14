"use strict";
const $ = (id) => document.getElementById(id);
// What the panels registered: see PA at the end of this file.
const panelHooks = { show: {}, state: [], language: [], learned: [] };
// After anything changed what was learned or where it applies: every place that shows it reads it again.
function learnedChanged(from) {
  for (const reread of panelHooks.learned) if (reread !== from) reread();
  if (from) activityLoop();
}
const translations = {
  zh: {
    chat: "开始聊天",
    platforms: "连接平台",
    settings: "角色与设置",
    activity: "动态",
    practice: "演练",
    practiceLead: "无需连接平台，即可查看角色在群聊中如何发言、如何学习。",
    app: "应用",
    appLead: "运行检查、后台运行、版本更新，以及数据的存放位置。",
    activityLead: "角色所在的群聊和私聊、近期的发言，以及学到的内容。",
    activityConnect: "连接平台",
    activityNotRunning: "角色尚未运行。在「开始聊天」中发送一条消息，或连接一个平台，角色即会启动。",
    activityNone: "暂无聊天记录。连接平台后，将角色添加到群聊或向它发送私信，记录即会显示在此处。",
    activityOff: "动态已关闭（.env 中 DASHBOARD_ENABLED=false）。",
    activity_unavailable: "暂时无法读取角色的动态，页面稍后将自动重试。",
    activity_changed: "该项已被处理，列表已刷新。",
    invalid_chat: "该聊天已不存在。",
    activityHere: "本页面",
    activityGroup: "群聊",
    activityDm: "私聊",
    activityObserving: "仍在观察",
    activityObservingHint: "角色会随着新的反应自行决定这些内容，此处无需你进行任何操作。",
    activityStageEvents: "目前已有 {have} 次认同的反应，共需 {need} 次。",
    activityStageStrong: "目前已有回复对象本人的 {have} 次明确纠正，共需 {need} 次。",
    activityStageSpeakers: "目前已有 {have} 位不同的人认同，共需 {need} 位。",
    activityStageApproval: "仍需要一位参与者给出正面反应。",
    activityStageDeciding: "仅凭反应无法确定此条内容，角色正在自行判断。",
    activityStageObserving: "角色已审视此条内容，决定继续观察。理由：“{reason}”",
    activityStageHeld: "仅凭反应无法确定此条内容，且高级设置中已关闭角色自行判断，因此它将继续处于观察状态。",
    activityStageOff: "高级设置中已关闭自动学习，因此此条内容不会投入使用。",
    activityStageReady: "已满足全部条件，将在角色收到下一次反应时投入使用。",
    activityExpires: "如果此后没有新的反应，它将于 {date} 被搁置。",
    activityByReactions: "因反应一致而投入使用。",
    activityByCharacter: "由角色自行决定投入使用。理由：“{reason}”",
    activityByPerson: "由人工操作投入使用。",
    activityFresh: "自你上次查看以来，角色有新学到的内容",
    activityLearned: "学习记录",
    activityNotes: "记忆",
    activityRecent: "近期动态",
    activityRecentNone: "暂无记录。此处仅保留近期动态，角色重启后将清空。",
    activityWording: "改进措辞",
    activityRepeat: "值得沿用的回复",
    activitySaid: "原回复",
    activityBetter: "改为",
    activityLesson: "今后遵循",
    activityFrom: "来自 {who}",
    activityAbout: "关于 {who}",
    activityRoomNote: "来自群聊",
    activityCore: "常驻记忆",
    activityForget: "删除",
    activityForgotten: "已删除。",
    listSep: "、",
    activityUndo: "撤销",
    activityUndone: "已撤销，角色不会再使用这一说法。",
    activityQuiet: "未发言",
    activityCount: "×{n}",
    activityFacts: "事实",
    activityThread: "此前的对话",
    activityEvents: "事件",
    activityRemoved: "最近删除",
    activityRemovedHint: "角色自行删除的内容可在 30 天内恢复；在本页删除的内容可在 24 小时内恢复。",
    activityRestore: "恢复",
    activityRestorePrevious: "恢复上一版本",
    activityRestored: "已恢复。",
    activity_restore_exists: "该项已存在。",
    activity_restore_gone: "该项已无法恢复。",
    activityUpdated: "更新于 {date}",
    activityCovers: "涵盖 {from} 至 {to}",
    activityFirstNoted: "首次记下于 {date}",
    activityLastUsed: "最近使用于 {date}",
    activitySaidBy: "由 {name} 所述",
    activityKindFact: "事实",
    activityKindEvent: "事件",
    activityWhyReplaced: "已被更新的事实取代",
    activityWhyMerged: "已与另一条事实合并",
    activityWhyEnded: "已不再成立",
    activityWhyEvicted: "为腾出空间而移除",
    activityWhyRewritten: "旧版本",
    activityWhyForgotten: "已在本页删除",
    activityWhyTerminal: "已通过终端命令删除",
    activityWhyUnreadable: "无法读取",
    activityUntil: "可恢复至 {date}",
    activityFoldUsed: "记忆整理：今日已使用 {used} 次调用，上限为 {cap} 次。",
    activityFoldPaused: "记忆整理因出错已暂停，下次尝试时间为 {time}。",
    activityForgetChat: "清除此聊天的记忆",
    activityForgetChatAsk: "角色将清除在此聊天中记住的全部内容：事实、事件、此前对话的摘要、常驻记忆、近期消息，以及尚可恢复的已删除内容。其他聊天中记住的内容将予以保留。在此聊天中学到的内容也将保留并继续使用。此操作无法撤销。",
    activityForgetOldChatAsk: "角色将清除在此聊天中记住的全部内容：事实、事件、此前对话的摘要、常驻记忆、近期消息，以及尚可恢复的已删除内容。其他聊天中记住的内容将予以保留。此操作无法撤销。",
    ariaNav: "导航",
    ariaLanguage: "页面语言",
    ariaSend: "发送",
    ariaChats: "聊天列表",
    activityAdmin: "管理员",
    activityLearnedRetired: "本页面的这次对话已由新的对话取代。角色在此学到或正在观察的内容已不再使用，列在「角色学到的内容」的「已搁置」中。",
    characterLang: "角色使用的语言",
    characterLangNote: "角色以此语言交流和学习。页面顶部选择的语言只改变本页面的显示。",
    activityChatForgotten: "已清除此聊天的记忆。",
    justNow: "刚刚",
    minutesAgo: "{n} 分钟前",
    hoursAgo: "{n} 小时前",
    r_below: "未被点名，且累计消息数未达到主动发言的条件",
    r_sleep: "处于夜间休息时段，按作息规律跳过",
    r_skip: "为保持自然的发言节奏而随机跳过",
    r_passed: "判断此处无需发言",
    r_addressed: "被点名或被 @",
    r_sticky: "回应此前的点名",
    r_followup: "延续自己上一条发言",
    r_trigger: "累计消息数已达到条件，考虑主动发言",
    r_first: "首次出现在此聊天中",
    r_failed: "模型未作出回应",
    r_blocked: "回复未通过安全检查，已被拦下",
    r_undelivered: "回复未能送达",
    r_proactive: "曾考虑主动发起话题，判断后决定不发言",
    r_together: "已与其他消息在同一条回复中一并作答",
    r_other: "其他原因",
    m_called: "被点名",
    m_owner: "管理员",
    m_judge: "自行判断后发言",
    m_judge_quiet: "可参与发言",
    m_followup: "跟进",
    m_proactive: "主动发起话题",
    local: "运行在你的电脑上",
    welcome: "欢迎使用 personagent",
    localReady: "本地应用已就绪",
    running: "正在运行",
    exit: "退出",
    winMin: "最小化",
    winMax: "最大化",
    winRestore: "还原",
    winClose: "关闭",
    winFailed: "窗口没有响应。",
    hero: "设置角色",
    intro: "填写模型密钥即可开始聊天，其余设置均有默认值。",
    modelTitle: "连接模型",
    modelHint: "角色通过你选择的模型服务进行聊天。",
    provider: "模型服务",
    freeNote: "OpenRouter 免费模型：密钥本身不收费，每天限 50 次请求。每次请求使用的模型可能不同，部分免费服务商会保留收到的内容。",
    getKey: "获取密钥 ↗",
    show: "显示",
    hide: "隐藏",
    keyNote: "密钥保存在本机；聊天内容会发送至你选择的模型服务。",
    advanced: "高级设置",
    characterOptions: "更改角色名称、性格或语言",
    name: "角色名称",
    character: "性格",
    customKept: "选择其他性格或立绘并保存后，你编写的人设将被替换。",
    personaReplaceAsk:
      "确定用所选性格替换你编写的人设吗？原人设将另存为 personagent 文件夹中的 persona.txt.bak。",
    personaReplaceYes: "替换",
    custom: "保留我自己编写的人设",
    personaTitle: "人设",
    personaHint: "描述角色的身份、说话方式和关注的事物。保存后立即生效，角色已学到的内容将保留。",
    personaSave: "保存人设",
    personaSaving: "正在保存…",
    personaUndo: "撤销修改",
    personaSaved: "人设已保存，角色已按新人设重新启动。",
    invalid_persona: "人设不能为空，且不能超过 4000 字。",
    save: "保存",
    featuresTitle: "更多功能",
    searchTitle: "联网搜索",
    searchHint: "遇到不了解的内容时，角色会先进行搜索。默认使用 DuckDuckGo，无需密钥；填写 Tavily 密钥可获得更稳定的结果。",
    searchFree: "DuckDuckGo（免费）",
    searchTavily: "Tavily",
    tavilyKeep: "留空以保留已保存的 Tavily 密钥",
    tavilyNew: "Tavily API Key（可选）",
    tavilyClear: "改回免费搜索",
    visionTitle: "识别图片",
    visionHint: "收到图片和表情包时，使用支持图像的模型进行描述；未开启时仅识别图片中的文字。",
    visionModel: "图像模型",
    visionSame: "使用与聊天相同的服务和密钥",
    proactiveTitle: "偶尔主动发言",
    proactiveHint: "群聊或私聊安静一段时间后，角色可能会主动发起话题，频率很低。",
    proactivePlatforms: "仅在以下平台启用（均未勾选时适用于所有平台）：",
    shareRoomsTitle: "在群聊之间共享记忆",
    shareRoomsHint: "在一个群聊中记下的关于某人的内容，也会用于此人发言的其他群聊。私聊内容和不针对具体个人的记录不会共享。",
    featuresSaved: "已保存，角色已按新设置重新启动。",
    invalid_feature: "有一项设置无效，请检查密钥和所选平台。",
    gsTitle: "开始使用",
    gsPlatform: "连接平台",
    updateLink: "新版本 {version}",
    updateTitle: "personagent {version} 已发布",
    updateNotes: "更新说明 ↗",
    updateRun: "请退出 personagent，运行以下命令，然后重新打开。",
    updateOpens: "请退出 personagent，然后使用以下命令打开新版本。",
    updateDownload: "请在更新说明页下载新版本源码，解压后覆盖 personagent 文件夹。",
    copy: "复制",
    copied: "已复制",
    close: "关闭",
    model: "模型名称",
    saveStart: "验证并开始聊天 →",
    saveAgain: "保存并返回聊天 →",
    saving: "正在验证密钥…",
    testNote: "验证时会发送一次很小的请求，可能产生少量模型费用。",
    yourCharacter: "预览",
    previewText: "性格决定角色说话的语气。",
    sample: "今天过得怎么样？有什么想聊的吗？",
    changeLater: "名称和性格可随时更改。",
    trioLabel: "也可以选择 GPT 娘、鲸鱼娘或 Claude 娘",
    qqLater: "也可以将角色接入 QQ、微信、Telegram…",
    qqLaterHint: "如需接入其他平台，请在「连接平台」中选择，扫码或填写一至两项即可完成。",
    chatHint: "本机对话，你在此处的身份是管理员。",
    newChat: "新对话",
    newChatDone: "已开始新的对话，角色记住的内容仍然保留。",
    forgetChat: "清除本次对话的记忆",
    forgetChatAsk: "角色将清除在本次对话中记住的全部内容：事实、事件、此前对话的摘要、常驻记忆、近期消息，以及尚可恢复的已删除内容，随后开始新的对话。角色在本次对话中学到的内容此后不再使用，仍列在「角色学到的内容」的「已搁置」中。其他聊天中记住的内容将予以保留。此操作无法撤销。",
    forget_needs_activity: "清除记忆需要先开启动态数据，可在「角色与设置」的高级设置中开启。",
    forgetChatDone: "已清除本次对话的记忆，并已开始新的对话。",
    forgetChatNone: "本次对话中没有记下任何内容，已开始新的对话。",
    commandsShow: "记忆命令",
    commandsHint: "点击命令即可填入输入框：",
    emptyHint: "发送一条消息以开始聊天。",
    promptHello: "你好，请做个自我介绍。",
    promptDay: "今天过得怎么样？",
    promptFilm: "请推荐一部适合周末观看的电影。",
    message: "输入消息",
    composerNote: "Enter 发送 · Shift + Enter 换行",
    platformsIntro:
      "扫码或填写一至两项即可，下载、配置和启动均会自动完成。",
    connectedTitle: "已连接的平台",
    groupScan: "扫码连接",
    groupScanHint: "在手机上确认即可，无需填写任何内容。",
    groupKey: "填写一至两项",
    groupKeyHint: "从平台的开发者后台复制，页面会说明需要复制哪几项。",
    howScan: "扫码",
    howPaste: "填写 {n} 项",
    howAdvanced: "需额外准备",
    reachAll: "群聊和私聊",
    reachDm: "仅私聊",
    reachChannels: "仅频道",
    groupAdvanced: "高级：需要公网地址或本机其他软件",
    back: "← 返回",
    guide: "前往平台后台获取 ↗",
    optional: "（可选）",
    scope: "连接后，角色将回复此平台上的群聊和私聊。",
    getQr: "获取二维码",
    connectNow: "连接",
    reconnect: "重新设置",
    disconnect: "断开连接",
    confirmDisconnect: "确定要断开 {platform} 吗？已保存的凭据将被删除。",
    disconnecting: "正在断开 {platform}…",
    isConnected: "已连接",
    paused: "已暂停",
    connectingState: "正在连接",
    failedState: "连接失败",
    pasteInstead: "改为手动填写",
    scanInstead: "改为扫码",
    pasteNote: "请在平台后台创建机器人，然后将以下各项复制到此处。",
    cancel: "取消",
    startServices: "全部启动",
    stopServices: "暂停运行",
    backToList: "返回平台列表",
    keepOpen:
      "使用期间请保持本应用运行。退出本应用时，由其启动的服务将一并停止。",
    closed: "应用已关闭",
    closedHint: "再次运行 personagent 即可返回此页面。",
    installTitle: "正在自动准备…",
    installHint:
      "首次使用时将下载 AstrBot 及所需运行环境，可能需要几分钟。请保持页面打开，无需手动操作。",
    scanTitle: "请使用手机扫码。",
    scanHint: "确认后将自动保存并启动。二维码过期后可重新获取。",
    scanHelp_qq_official: "请使用手机 QQ 扫码，并确认新建或选用一个机器人。",
    scanHelp_weixin_oc: "请使用手机微信扫码，并确认登录。",
    scanHelp_twitch:
      "请在已登录角色 Twitch 账号的浏览器中打开该链接，核对代码一致后点击 Authorize（授权）。也可用手机扫描二维码打开同一链接。",
    linkTitle: "请在浏览器中批准登录。",
    linkHint: "批准后将自动检查、保存并启动连接。链接过期后会自动更换。",
    linkOpen: "打开登录链接 ↗",
    startTitle: "正在连接角色…",
    startHint: "正在启动角色服务和聊天平台，请稍候。",
    prepareTitle: "正在获取二维码…",
    prepareHint: "请稍候。",
    checkTitle: "正在确认 {platform} 是否接受连接…",
    checkHint: "如果平台拒绝这些凭据，原因将显示在此处，且不会保存任何内容。",
    doneTitle: "{platform} 已连接，现在可以在该平台上与角色交流。",
    saved: "设置已保存，可以开始聊天。",
    thinking: "正在回复…",
    noReply: "角色未作回复，请换一个话题再试。",
    greeting: "你好，我是{name}。",
    platformsTitle: "连接平台",
    keySaved: "留空以保留已保存的密钥",
    firstConfigure: "请先连接模型，再将角色接入其他平台。",
    working: "当前操作仍在进行，请稍候。",
    offline: "与应用的连接已中断，请关闭 personagent 后重新打开。",
    auth: "请通过启动窗口中显示的本地链接打开此页面。",
    key_required: "请填写 API Key。",
    key_rejected: "密钥未通过验证。请检查密钥是否完整，以及是否属于所选服务。",
    model_limited:
      "服务商提示请求过多或额度已用完。OpenRouter 免费模型每天限 50 次请求，于 UTC 零点重置。请稍后重试，或更换其他服务。",
    model_unreachable:
      "暂时无法连接该模型。请检查网络、模型名称和服务地址后重试。",
    model_required: "请在高级设置中填写模型名称。",
    invalid_url: "请填写完整的服务地址。",
    https_required: "远程模型服务须使用 HTTPS 地址。",
    invalid_character: "请检查角色名称和性格。",
    busy: "当前操作仍在进行，请等待其完成。",
    chat_failed: "回复未能完成。请检查模型服务和网络后重试。",
    setup_failed:
      "连接未能完成。请检查网络后重试；已保存的模型和角色设置不受影响。",
    download_failed: "下载未能完成，请检查网络后重试。",
    service_failed: "聊天平台未能启动。请检查填写的内容是否正确，然后重试。",
    agent_failed: "角色未能启动。请在「应用」中执行运行检查以查看原因。",
    scan_failed: "扫码未完成或二维码已过期，请重新获取。",
    platform_rejected:
      "平台未接受此次连接，因此未保存任何内容。请检查填写的内容及平台后台的设置，然后重试。",
    token_rejected: "平台未接受该 Token，因此未保存任何内容。请重新复制完整的 Token。",
    app_rejected: "QQ 未接受该 AppID 或 AppSecret，因此未保存任何内容。请到 QQ 开放平台重新复制。",
    bot_in_use: "该机器人正被其他程序使用，或已设置 Webhook。请先停止该程序，然后重新连接。",
    message_content_intent_off:
      "Discord 拒绝了连接。请在开发者后台的 Bot 页面开启 Message Content Intent，保存后重试。",
    intents_not_allowed: "QQ 未授予该机器人接收群聊和私聊消息的权限。",
    session_expired: "登录已失效，请重新扫码。",
    bot_offline: "该 QQ 机器人已下架。",
    bot_banned: "该 QQ 机器人已被封禁。",
    network_failed: "无法连接该平台的服务器。请检查网络连接及代理设置，然后重试。",
    account_deactivated:
      "平台已停用该机器人账号或其所在组织，因此未保存任何内容。请在平台上重新启用，或新建一个机器人账号后重新连接。",
    insecure_address: "服务器地址必须以 https:// 开头。仅本机上的服务器可以使用 http 地址。",
    homeserver_invalid:
      "该地址不是可用的 Matrix 服务器，或未使用安全连接（https）。请检查地址，例如 https://matrix.org。仅本机上的服务器可以使用 http 地址。",
    owner_invalid:
      "请填写你本人的 Matrix ID，例如 @you:matrix.org。该 ID 必须是你本人的账号，而不是机器人账号。",
    channel_not_found: "所填写的 Twitch 频道中有一个不存在，或未填写任何频道。请检查频道名后重试。",
    nick_in_use: "该昵称在此网络上已被占用。请关闭正在使用该昵称的其他 IRC 客户端，或改用其他昵称。",
    nick_invalid: "该网络不接受此昵称。昵称只能包含字母、数字及 - _ [ ] { } | ^，且须以字母开头。",
    password_rejected: "网络提示该昵称的密码不正确，因此未保存任何内容。请检查该昵称在 NickServ 中的密码。",
    sasl_required: "该网络只允许已注册的昵称从你的网络地址连接。请先通过 NickServ 注册昵称，再填写其密码。",
    long_poll_off:
      "该社区未开启 Long Poll API。请在社区中打开「管理 > API 使用 > Long Poll API」，将其设为「开启」，然后重新连接。",
    message_events_off:
      "该社区尚未向机器人推送新消息。请在「管理 > API 使用 > Long Poll API > 事件类型」中勾选「收到消息（message_new）」并保存。",
    token_rights_missing:
      "该密钥缺少必需的权限。请在「管理 > API 使用」中新建密钥，勾选社区管理、消息和照片权限，再粘贴到此处。",
    not_a_bot:
      "这是个人账号的信息，而非机器人的信息，因此未保存任何内容。请在「个人设置 > 机器人」中添加一个通用机器人，并粘贴其邮箱和 API 密钥。",
    wrong_bot_type: "该机器人无法读取消息。请在 Zulip 中添加类型为「通用机器人（Generic bot）」的机器人，并使用其信息。",
    not_zulip_site:
      "该地址不是 Zulip 组织的地址。请在打开 Zulip 时从浏览器地址栏复制，例如 https://yourteam.zulipchat.com。",
    // `<code>_<platform>`: one platform's own wording of a shared code.
    bot_banned_irc: "该 IRC 网络已封禁此连接（K-line 或其他封禁）。",
    bot_banned_vk: "VK 已封禁或停用该社区。",
    token_rejected_zulip:
      "Zulip 不接受该机器人邮箱和 API 密钥，因此未保存任何内容。请在「个人设置 > 机器人」中该机器人所在行重新复制这两项。",
    token_rejected_vk:
      "VK 不接受该密钥，因此未保存任何内容。请在「管理 > API 使用 > 访问密钥」中创建社区访问密钥，并完整粘贴。",
    token_rejected_twitch: "此次 Twitch 登录未授予聊天权限。请点击「连接」并重新批准登录。",
    app_rejected_twitch:
      "Twitch 不接受此 Client ID 用于本次登录。请确认该开发者应用存在且 Client Type 为 Public，然后重新复制 Client ID。",
    session_expired_twitch: "Twitch 登录已失效。请点击「连接」并重新批准登录。",
    scan_failed_twitch: "Twitch 登录未完成、已被拒绝或链接已过期。请点击「连接」获取新的链接。",
    field_required: "请填写所有必填项。",
    invalid_field: "有一项格式不正确，请检查地址或端口。",
    invalid_platform: "暂不支持该平台。",
    invalid_message: "消息过长，请缩短后重新发送。",
    too_large: "消息过长，请缩短后重新发送。",
    permission_required: "角色需要获得在此平台回复的权限。",
    forbidden: "页面授权已失效，请重新打开启动窗口中的本地链接。",
    generic: "操作未能完成，请重试。",
    vision_unsupported: "此模型无法读取图片。请选择支持视觉的模型，或关闭图片识别。",
    stopped: "聊天平台已暂停。",
    retryChat: "重新发送",
    chatPicture: "{name} 发送的图片",
    chatPictureGone: "该图片已不存在。",
    chatViaCoding: "经由编程助手",
    closing: "正在关闭…",
  },
  en: {
    chat: "Chat",
    platforms: "Connect apps",
    settings: "Character & settings",
    activity: "Activity",
    practice: "Practice",
    practiceLead: "Without connecting an app, see how the character speaks in a group and how it learns.",
    app: "App",
    appLead: "The health check, running in the background, updates, and where the data is stored.",
    activityLead: "Where it is, what it said lately, and what it learned.",
    activityConnect: "Connect an app",
    activityNotRunning: "The character is not running. Send a message in Chat or connect an app to start it.",
    activityNone: "There are no chats yet. Connect an app, then add the character to a group or send it a direct message; the chat appears here.",
    activityOff: "Activity is turned off (DASHBOARD_ENABLED=false in .env).",
    activity_unavailable: "The character's activity could not be read. The page will try again shortly.",
    activity_changed: "This item has already been handled. The list has been refreshed.",
    invalid_chat: "This chat no longer exists.",
    activityHere: "This page",
    activityGroup: "group",
    activityDm: "DM",
    activityObserving: "Still under observation",
    activityObservingHint:
      "The character decides these items by itself as reactions arrive. Nothing here requires any action from you.",
    activityStageEvents: "Agreeing reactions so far: {have} of the {need} required.",
    activityStageStrong:
      "Clear corrections from the person the reply was addressed to so far: {have} of the {need} required.",
    activityStageSpeakers: "Different people in agreement so far: {have} of the {need} required.",
    activityStageApproval: "A positive reaction from a participant is still required.",
    activityStageDeciding: "Reactions alone cannot settle this item, so the character is deciding it itself.",
    activityStageObserving: "The character has reviewed this item and continues to observe it. Its reason: “{reason}”",
    activityStageHeld:
      "Reactions alone cannot settle this item, and the character's own decisions are turned off in the advanced settings, so it remains under observation.",
    activityStageOff: "Automatic learning is turned off in the advanced settings, so this item is not put into use.",
    activityStageReady: "It meets every condition and will be put into use with the next reaction the character receives.",
    activityExpires: "If no new reaction arrives, it will be set aside on {date}.",
    activityByReactions: "Put into use because the reactions agreed.",
    activityByCharacter: "Put into use by the character's own decision. Its reason: “{reason}”",
    activityByPerson: "Put into use by a person.",
    activityFresh: "The character has learned something new since your last visit",
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
    activityAbout: "about {who}",
    activityRoomNote: "from a group",
    activityCore: "Always in mind",
    activityForget: "Forget",
    activityForgotten: "Forgotten.",
    listSep: ", ",
    activityUndo: "Undo",
    activityUndone: "Undone. The character will no longer phrase it this way.",
    activityQuiet: "Stayed quiet",
    activityCount: "×{n}",
    activityFacts: "Facts",
    activityThread: "Earlier in this chat",
    activityEvents: "Events",
    activityRemoved: "Recently removed",
    activityRemovedHint: "Items removed by the character can be restored for 30 days; items forgotten on this page, for 24 hours.",
    activityRestore: "Restore",
    activityRestorePrevious: "Restore previous version",
    activityRestored: "Restored.",
    activity_restore_exists: "This item already exists.",
    activity_restore_gone: "This item can no longer be restored.",
    activityUpdated: "Updated {date}",
    activityCovers: "Covers {from} to {to}",
    activityFirstNoted: "First noted {date}",
    activityLastUsed: "Last used {date}",
    activitySaidBy: "Said by {name}",
    activityKindFact: "Fact",
    activityKindEvent: "Event",
    activityWhyReplaced: "Replaced by a newer fact",
    activityWhyMerged: "Merged with another fact",
    activityWhyEnded: "No longer current",
    activityWhyEvicted: "Removed to make room",
    activityWhyRewritten: "Earlier version",
    activityWhyForgotten: "Forgotten on this page",
    activityWhyTerminal: "Forgotten with the terminal command",
    activityWhyUnreadable: "Could not be read",
    activityUntil: "Restorable until {date}",
    activityFoldUsed: "Memory consolidation: {used} of {cap} calls used today.",
    activityFoldPaused: "Memory consolidation is paused after errors; the next attempt is at {time}.",
    activityForgetChat: "Forget this chat",
    activityForgetChatAsk: "The character will forget everything it remembers from this chat: the facts, the events, the summary of earlier conversation, the always-present note, the recent messages and the removed items that could still be restored. What it remembers from other chats is kept. What it learned in this chat is kept and stays in use. This cannot be undone.",
    activityForgetOldChatAsk: "The character will forget everything it remembers from this chat: the facts, the events, the summary of earlier conversation, the always-present note, the recent messages and the removed items that could still be restored. What it remembers from other chats is kept. This cannot be undone.",
    ariaNav: "Navigation",
    ariaLanguage: "Page language",
    ariaSend: "Send",
    ariaChats: "Chats",
    activityAdmin: "Admin",
    activityLearnedRetired: "This chat on this page has been replaced by a new chat. What the character learned or was observing here is no longer used; it is listed under Set aside in What the character has learned.",
    characterLang: "Language the character speaks",
    characterLangNote: "The character talks and learns in this language. The language chosen at the top of the page changes only how this page reads.",
    activityChatForgotten: "The character has forgotten this chat.",
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
    r_failed: "the model did not answer",
    r_blocked: "the reply was held back by a safety check",
    r_undelivered: "the reply could not be delivered",
    r_proactive: "considered starting a conversation and decided against it",
    r_together: "answered in the same reply as another message",
    r_other: "for another reason",
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
    winMin: "Minimize",
    winMax: "Maximize",
    winRestore: "Restore",
    winClose: "Close",
    winFailed: "The window did not respond.",
    hero: "Set up your character",
    intro:
      "Add a model API key and start chatting. Everything else has a sensible default.",
    modelTitle: "Connect a model",
    modelHint: "Your character talks through the model service you choose.",
    provider: "Model service",
    freeNote:
      "OpenRouter's free models: the key costs nothing and the limit is 50 requests a day. The model can change from one request to the next, and some free providers keep what they receive.",
    getKey: "Get an API key ↗",
    show: "Show",
    hide: "Hide",
    keyNote:
      "Your key stays on this computer. Chats go to the model service you choose.",
    advanced: "Advanced settings",
    characterOptions: "Choose a name, personality or language",
    name: "Character name",
    character: "Personality",
    customKept:
      "Choosing another personality or portrait and saving replaces the character you wrote.",
    personaReplaceAsk:
      "Replace the character you wrote with the chosen personality? Your text is kept as persona.txt.bak in the personagent folder.",
    personaReplaceYes: "Replace",
    custom: "Keep my own character",
    personaTitle: "Persona",
    personaHint:
      "Who it is, how it talks and what it cares about. Saving applies it right away and keeps what it has learned.",
    personaSave: "Save persona",
    personaSaving: "Saving…",
    personaUndo: "Undo changes",
    personaSaved: "Persona saved. The character restarted with it.",
    invalid_persona: "The persona cannot be empty or longer than 4,000 characters.",
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
    shareRoomsTitle: "Share memory between groups",
    shareRoomsHint: "What one group noted about someone also comes up in other groups they talk in. DMs and notes about a whole group stay where they are.",
    featuresSaved: "Saved. The character restarted with it.",
    invalid_feature: "Something here is not right; check the keys and apps.",
    gsTitle: "Getting started",
    gsPlatform: "Connect an app",
    updateLink: "{version} available",
    updateTitle: "personagent {version} is out",
    updateNotes: "Release notes ↗",
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
    trioLabel: "Or pick the GPT dragon girl, the DeepSeek whale girl or the Claude lady",
    qqLater: "Bring your character to QQ, WeChat, Telegram…",
    qqLaterHint:
      "To connect another app, choose it under Connect apps. Most need only a QR code scan or one or two values.",
    chatHint: "A chat on this computer. Here you are the admin.",
    newChat: "New chat",
    newChatDone: "A new chat has started. What the character remembers is kept.",
    forgetChat: "Forget this chat",
    forgetChatAsk: "The character will forget everything it remembers from this chat: the facts, the events, the summary of earlier conversation, the always-present note, the recent messages and the removed items that could still be restored. A new chat then starts. What the character learned in this chat is no longer used from then on; it remains listed under Set aside in What the character has learned. What it remembers from other chats is kept. This cannot be undone.",
    forget_needs_activity: "Forgetting a chat needs activity data, which is switched off. Turn it on in the advanced settings under Character & settings.",
    forgetChatDone: "The character has forgotten this chat, and a new chat has started.",
    forgetChatNone: "The character had noted nothing in this chat. A new chat has started.",
    commandsShow: "Memory commands",
    commandsHint: "Select a command to insert it into the message box:",
    emptyHint: "Send a message to start the conversation.",
    promptHello: "Hi, shall we get to know each other?",
    promptDay: "How has your day been?",
    promptFilm: "Recommend a film for the weekend",
    message: "Write a message",
    composerNote: "Enter to send · Shift + Enter for a new line",
    platformsIntro:
      "Scan or paste one or two values. Downloading, setup and starting happen on their own.",
    connectedTitle: "Connected apps",
    groupScan: "Scan to connect",
    groupScanHint: "Confirm on your phone. No fields need to be filled in.",
    groupKey: "Paste one or two values",
    groupKeyHint: "Copy them from the app's developer console. The page states which values are needed.",
    howScan: "Scan",
    howPaste: "Paste {n}",
    howAdvanced: "Needs setup",
    reachAll: "Groups and DMs",
    reachDm: "DMs only",
    reachChannels: "Channels only",
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
      "First use downloads AstrBot and its runtime, which can take a few minutes. Keep this page open; no manual steps are needed.",
    scanTitle: "Scan with your phone.",
    scanHint:
      "After you confirm, everything is saved and started. An expired code can be refreshed.",
    scanHelp_qq_official: "Scan with mobile QQ and confirm a new bot or one you made.",
    scanHelp_weixin_oc: "Scan with WeChat and confirm the login.",
    scanHelp_twitch:
      "Open the link in a browser that is signed in to the character's Twitch account, confirm that the code matches, and select Authorize. The QR code opens the same link on a phone.",
    linkTitle: "Approve the sign-in in your browser.",
    linkHint:
      "After you approve, the connection is checked, saved and started. An expired link is replaced automatically.",
    linkOpen: "Open the sign-in link ↗",
    startTitle: "Connecting your character…",
    startHint: "Starting the character service and chat platform.",
    prepareTitle: "Getting a QR code…",
    prepareHint: "Please wait.",
    checkTitle: "Checking that {platform} accepts the connection…",
    checkHint:
      "If the app refuses these credentials, the reason is shown here and nothing is saved.",
    doneTitle: "{platform} is connected. You can now talk to the character there.",
    saved: "Settings saved. You can start chatting.",
    thinking: "Replying…",
    noReply: "The character did not reply. Try a different topic.",
    greeting: "Hi, I'm {name}.",
    platformsTitle: "Connect apps",
    keySaved: "Leave blank to keep the saved key",
    firstConfigure: "Connect a model first, then bring the character to other apps.",
    working: "An operation is still in progress. Please wait.",
    offline:
      "The connection to the app was lost. Close personagent and open it again.",
    auth: "Open this page using the local link in the launch window.",
    key_required: "Enter your API key.",
    key_rejected:
      "The key was not accepted. Check that it is complete and belongs to this service.",
    model_limited:
      "The service reports too many requests or an exhausted quota. OpenRouter's free models allow 50 requests a day, reset at midnight UTC. Try again later or choose another service.",
    model_unreachable:
      "The model could not be reached. Check the network, the model name and the API address, then try again.",
    model_required: "Enter a model name under advanced settings.",
    invalid_url: "Enter a complete API address.",
    https_required: "Remote model services require an HTTPS address.",
    invalid_character: "Check the character name and personality.",
    busy: "An operation is still running. Please wait.",
    chat_failed:
      "The reply could not be completed. Check the model service and the network, then try again.",
    setup_failed:
      "The connection did not complete. Check the network and try again. Your model and character settings are kept.",
    download_failed: "The download did not complete. Check the network and try again.",
    service_failed:
      "The chat platform did not start. Check what you entered, then try again.",
    agent_failed: "The character did not start. Run the health check under App to see the cause.",
    scan_failed: "The scan did not complete or the code expired. Get a new code.",
    platform_rejected:
      "The app refused the connection, so nothing was saved. Check what you entered and the app's console settings, then retry.",
    token_rejected: "The app did not accept this token, so nothing was saved. Copy the complete token again.",
    app_rejected: "QQ did not accept the AppID or AppSecret, so nothing was saved. Copy them again from the QQ console.",
    bot_in_use: "Another program is using this bot, or a webhook is set for it. Stop that program, then connect again.",
    message_content_intent_off:
      "Discord refused the connection. Turn on Message Content Intent on the Bot page of the developer portal, save, and try again.",
    intents_not_allowed: "QQ has not given this bot permission to receive group and direct messages.",
    session_expired: "The login has expired. Scan again.",
    bot_offline: "This QQ bot has been taken offline.",
    bot_banned: "This QQ bot has been banned.",
    network_failed: "The app's servers could not be reached. Check the network connection and any proxy settings, then try again.",
    account_deactivated:
      "The platform has deactivated this bot account or its organization, so nothing was saved. Reactivate it on the platform, or create a new bot account and connect again.",
    insecure_address:
      "The server address must begin with https://. A plain http address is accepted only for a server on this computer.",
    homeserver_invalid:
      "This address is not a Matrix homeserver that accepts secure connections. Check the address, for example https://matrix.org. A plain http address is accepted only for a server on this computer.",
    owner_invalid:
      "Enter your own Matrix ID, for example @you:matrix.org. It must be your personal account, not the bot account.",
    channel_not_found:
      "One of the listed Twitch channels does not exist, or no channel was entered. Check the channel names and try again.",
    nick_in_use:
      "This nickname is already in use on the network. Close the other IRC client that uses it, or choose another nickname.",
    nick_invalid:
      "The network does not accept this nickname. Use only letters, digits and the characters - _ [ ] { } | ^, and begin with a letter.",
    password_rejected:
      "The network reports that the nickname's password is incorrect, so nothing was saved. Check the NickServ password for this nickname.",
    sasl_required:
      "This network accepts only registered nicknames from your network address. Register the nickname with NickServ and enter its password.",
    long_poll_off:
      "The Long Poll API is turned off for this community. In the community, open Manage > API usage > Long Poll API, set it to Enabled, and connect again.",
    message_events_off:
      "The community does not yet send new messages to the bot. Under Manage > API usage > Long Poll API > Event types, tick Incoming message (message_new) and save.",
    token_rights_missing:
      "This key lacks a required right. Create a new key under Manage > API usage with community management, messages and photos ticked, then paste it here.",
    not_a_bot:
      "These are the details of a personal account, not of a bot, so nothing was saved. Add a Generic bot under Personal settings > Bots and paste its email and API key.",
    wrong_bot_type:
      "This bot cannot read messages. In Zulip, add a bot of the type Generic bot and use its details.",
    not_zulip_site:
      "This address does not respond as a Zulip organization. Copy the address from the browser while Zulip is open, for example https://yourteam.zulipchat.com.",
    // `<code>_<platform>`: one platform's own wording of a shared code.
    bot_banned_irc: "The network has banned this connection (a K-line or another ban).",
    bot_banned_vk: "VK has blocked or deactivated this community.",
    token_rejected_zulip:
      "Zulip does not accept this bot email and API key, so nothing was saved. Copy both again from the bot's row under Personal settings > Bots.",
    token_rejected_vk:
      "VK does not accept this key, so nothing was saved. Create a community access key under Manage > API usage > Access keys and paste the whole key.",
    token_rejected_twitch:
      "The Twitch sign-in did not grant the chat permissions. Select Connect and approve the sign-in again.",
    app_rejected_twitch:
      "Twitch does not accept this Client ID for this sign-in. Check that the application exists and that its Client Type is Public, then copy the Client ID again.",
    session_expired_twitch: "The Twitch sign-in has ended. Select Connect and approve the sign-in again.",
    scan_failed_twitch:
      "The Twitch sign-in did not finish, was declined, or the link expired. Select Connect to receive a new link.",
    field_required: "Fill in every required field.",
    invalid_field: "One value is not valid. Check the address or port.",
    invalid_platform: "This app is not supported.",
    invalid_message: "That message is too long. Shorten it and send again.",
    too_large: "That message is too long. Shorten it and send again.",
    permission_required: "Your character needs permission to reply in this app.",
    forbidden:
      "The authorization for this page has expired. Reopen the local link shown in the launch window.",
    generic: "The operation did not complete. Try again.",
    vision_unsupported: "This model cannot read images. Choose a vision model or turn image reading off.",
    stopped: "Chat platform paused.",
    retryChat: "Send again",
    chatPicture: "Picture sent by {name}",
    chatPictureGone: "This picture is no longer available.",
    chatViaCoding: "via a coding assistant",
    closing: "Closing…",
  },
};
// The page's languages and their BCP 47 tags. English and Chinese live above;
// the others are translations in /assets/i18n/<code>.json, loaded when chosen,
// and a string one lacks shows in English. The character's own language
// (AGENT_LANG) is chosen on the setup card, not here.
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
const DEFAULT_NAMES = {
  zh: "小夏",
  "zh-TW": "小夏",
  ja: "ノヴァ",
  ko: "노바",
  ru: "Нова",
};
const defaultName = () => DEFAULT_NAMES[lang] || "Nova";
async function loadLang(code) {
  if (translations[code]) return;
  const response = await fetch(`/assets/i18n/${code}.json`, {
    credentials: "omit",
  });
  const data = await response.json();
  translations[code] = data.strings;
  catalogText[code] = data.catalog;
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
// Only the page inside the app window is given this key: with it the page
// draws the window's bar and may press its buttons.
const frameKey = fragment.get("frame") || sessionStorage.getItem("personagent-frame") || "";
if (fragment.has("frame")) sessionStorage.setItem("personagent-frame", frameKey);
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
// A shared code in one platform's own words (`token_rejected_zulip`), when it has them.
const tFor = (key, kind) =>
  translations.en[`${key}_${kind}`] ? t(`${key}_${kind}`) : t(key);
// `undo`, when given, is {label, run}: a button in the message that runs it.
function toast(text, undo) {
  const box = $("toast");
  box.textContent = text;
  if (undo) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "toast-action";
    button.textContent = undo.label;
    button.addEventListener("click", () => {
      clearTimeout(toastTimer);
      box.hidden = true;
      undo.run();
    });
    box.append(" ", button);
  }
  box.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (box.hidden = true), undo ? 10000 : 5000);
}
async function api(path, payload) {
  const response = await fetch(`/api/${path}`, {
    method: payload === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Personagent-Setup-Token": token,
      ...(frameKey && path === "window" ? { "X-Personagent-Window": frameKey } : {}),
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
function renderText() {
  document.documentElement.lang = LANGS[lang] || "en";
  $("language").value = lang;
  for (const node of document.querySelectorAll("[data-t]"))
    label(node, t(node.dataset.t));
  for (const node of document.querySelectorAll("[data-t-aria]"))
    node.setAttribute("aria-label", t(node.dataset.tAria));
  for (const node of document.querySelectorAll("[data-t-title]")) node.title = t(node.dataset.tTitle);
  $("message").placeholder = t("message");
  for (const image of document.querySelectorAll("#messages .picture img")) image.alt = pictureAlt();
}
function renderLanguage() {
  renderText();
  const provider = $("provider").value || state.provider;
  options($("provider"), catalog.providers, provider);
  const character = $("character").value || state.character;
  const chars = [...catalog.characters];
  if (state.character === "custom")
    chars.push({ id: "custom", name: [t("custom"), t("custom")] });
  options($("character"), chars, character);
  tiles();
  if (selected) buildFields(true);
  updateNames();
  renderStatus();
  renderActivity();
  if (!saving)
    $("save").textContent = t(state.configured ? "saveAgain" : "saveStart");
  $("api-key").placeholder = state.configured ? t("keySaved") : "sk-…";
  for (const retold of panelHooks.language) retold();
}
const characterSpec = (id) => catalog.characters.find((c) => c.id === id);
const portraitOf = (id) => characterSpec(id)?.avatar || "";
// An avatar is a letter, or a portrait sprite of four square frames side by
// side (idle, blink, talk, think) that the stylesheet animates.
function avatarParts(node) {
  if (node.querySelector(".face")) return node;
  const letter = document.createElement("span");
  letter.className = "letter";
  const face = document.createElement("span");
  face.className = "face";
  const sprite = document.createElement("span");
  sprite.className = "sprite";
  face.append(sprite);
  node.prepend(letter, face);
  // Each avatar blinks on its own clock, so two never blink together.
  node.style.setProperty("--blink-period", `${(4.6 + Math.random()).toFixed(2)}s`);
  node.style.setProperty("--blink-delay", `${(-Math.random() * 5).toFixed(2)}s`);
  return node;
}
function paintAvatar(node, src, name) {
  avatarParts(node);
  node.classList.toggle("portrait", Boolean(src));
  node.querySelector(".letter").textContent = src ? "" : Array.from(name)[0] || "";
  node.querySelector(".sprite").style.backgroundImage = src ? `url("${src}")` : "";
}
function previewPortrait() {
  const id = $("character").value || state.character;
  return portraitOf(id === "custom" ? state.avatar : id);
}
function updateNames() {
  const name =
    $("character-name").value.trim() || state.name || defaultName();
  $("preview-name").textContent = name;
  $("chat-name").textContent = state.name || name;
  const preview = previewPortrait();
  paintAvatar($("preview-avatar"), preview, name);
  for (const id of ["chat-avatar", "empty-avatar"])
    paintAvatar($(id), portraitOf(state.avatar), state.name || name);
  $("chat-greeting").textContent = t("greeting", { name: state.name || name });
  $("platforms-title").textContent = t("platformsTitle", {
    name: state.name || name,
  });
  syncTrio();
}
// The characters with a portrait, as round buttons under the sample.
function buildTrio() {
  const row = $("trio-row");
  row.replaceChildren();
  for (const item of catalog.characters.filter((c) => c.avatar)) {
    const button = avatarParts(document.createElement("button"));
    button.type = "button";
    button.className = "avatar portrait trio-pick";
    button.dataset.character = item.id;
    button.querySelector(".sprite").style.backgroundImage = `url("${item.avatar}")`;
    button.addEventListener("click", () => {
      $("character").value = item.id;
      $("character").dispatchEvent(new Event("change"));
    });
    row.append(button);
  }
  $("trio").hidden = !row.children.length;
}
function syncTrio() {
  for (const button of $("trio-row").children) {
    const item = characterSpec(button.dataset.character);
    button.setAttribute("aria-label", pick(item.name).split(/[:：]/)[0].trim());
    button.setAttribute("aria-pressed", String($("character").value === item.id));
  }
}
// A name nobody chose (empty, the default, or a character's own) follows
// the character; a typed one stays.
function characterChanged() {
  const field = $("character-name");
  const current = field.value.trim();
  const chosen = characterSpec($("character").value);
  if (
    chosen &&
    (!current ||
      current === defaultName() ||
      catalog.characters.some((c) => c.defaultName === current))
  )
    field.value = chosen.defaultName || defaultName();
  updateNames();
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
  $("character-name").value =
    state.name || characterSpec(state.character)?.defaultName || defaultName();
  $("api-key").value = "";
  $("api-key").type = "password";
  $("show-key").textContent = t("show");
  $("api-key").placeholder = state.configured ? t("keySaved") : "sk-…";
  providerChanged(false);
  updateNames();
  // The character's language is a setting; the page's own language is the reader's.
  const speaks = $("character-lang");
  if (!speaks.options.length)
    speaks.append(...[...$("language").options].map((o) => new Option(o.textContent, o.value)));
  speaks.value = (state.configured && state.lang) || lang;
  if (!speaks.value) speaks.value = lang;
}
function freeNoteChanged() {
  $("free-note").hidden = $("model").value.trim() !== "openrouter/free";
}
function providerChanged(reset = true) {
  const provider = catalog.providers.find((p) => p.id === $("provider").value);
  $("base-url").value = reset
    ? provider.baseUrl
    : state.baseUrl || provider.baseUrl;
  $("model").value = reset ? provider.model : state.model || provider.model;
  $("key-link").href = provider.keyUrl || "#";
  $("key-link").hidden = !provider.keyUrl;
  freeNoteChanged();
  $("api-key").required = provider.id !== "ollama" && !state.configured;
  if (reset && provider.id !== state.provider) {
    $("api-key").value = "";
    $("api-key").placeholder = "sk-…";
    $("api-key").required = provider.id !== "ollama";
  }
  if (provider.id === "other" || provider.id === "ollama")
    $("advanced").open = true;
  // Ollama runs here: it takes no key and a check costs nothing.
  const local = provider.id === "ollama";
  if (local || !state.configured || (reset && provider.id !== state.provider))
    $("api-key").placeholder = local ? "" : "sk-…";
  $("test-note").hidden = local;
  $("base-url").placeholder = provider.id === "other" ? "https://…/v1" : "";
}
function showView(next) {
  if (chatting && next !== "chat") {
    toast(t("working"));
    return;
  }
  if (["platforms", "activity"].includes(next) && !state.configured) {
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
  for (const section of document.querySelectorAll("[data-panel-view]"))
    section.hidden = section.dataset.panelView !== next;
  $("page-label").textContent = t(
    setup ? (state.configured ? "settings" : "welcome") : next,
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
  chatLoop();
  for (const shown of panelHooks.show[setup ? "settings" : next] || []) shown();
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
const spec = (kind) => catalog.platforms.find((p) => p.id === kind);
const platformName = (kind) => (spec(kind) ? pick(spec(kind).name) : kind);
// Each platform's mark: its logo, otherwise a short monogram in its
// colour. Logos are their owners' trademarks and only name the platform.
// Simple Icons (CC0-1.0): QQ, WeChat, Telegram, Discord, Mattermost and
// Misskey. MingCute (Apache-2.0): DingTalk. IconPark (Apache-2.0): Feishu.
// SVG Logos (CC0-1.0): Slack. TDesign (MIT): WeCom. KOOK: its site icon.
// OneBot: the logo in botuniverse/onebot (MIT). Satori has none. Matrix ([m]),
// IRC (#) and Twitch (a chat bubble) are plain glyphs drawn here, not logo files.
const LOGOS = {
  matrix:
    "M2 2h5v2H4v16h3v2H2zM22 2h-5v2h3v16h-3v2h5zM8 8h8v2H8zM8 10h2v6H8zM11 10h2v6h-2zM14 10h2v6h-2z",
  irc: "M9 3h2L8 21H6zM15 3h2l-3 18h-2zM4 8h16v2H4zM4 14h16v2H4z",
  twitch: {
    box: "0 0 24 24",
    svg: "<path fill=\"currentColor\" fill-rule=\"evenodd\" d=\"M4 2L2 6v14h5v3h3l3-3h4l5-5V2zM20 4v10l-3 3h-5l-3 3v-3H5V4zM10 7h2v5h-2zM15 7h2v5h-2z\"/>",
  },
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
  matrix: ["M", "#000000", "matrix"],
  twitch: ["T", "#9146ff", "twitch"],
  irc: ["#", "#3b4252", "irc"],
  zulip: ["Z", "#6492fe"],
  vk: ["VK", "#0077ff"],
  stoat: ["St", "#ff4654"],
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
// Platforms where the character takes no direct messages: Twitch whispers are not supported.
const NO_DMS = new Set(["twitch"]);
function describe(item) {
  const how =
    item.group === "scan"
      ? t("howScan")
      : item.group === "advanced"
        ? t("howAdvanced")
        : t("howPaste", {
            n: String(item.fields.filter((f) => f.required).length),
          });
  const reach = NO_DMS.has(item.id) ? "reachChannels" : item.groups ? "reachAll" : "reachDm";
  return [how, t(reach)];
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
  const steps = scanning ? [] : item.steps || [];
  $("panel-steps").replaceChildren(
    ...steps.map((step) => {
      const line = document.createElement("li");
      line.textContent = pick(step);
      return line;
    }),
  );
  $("panel-steps").hidden = !steps.length;
  $("panel-guide").href = item.guide || "#";
  $("panel-guide").hidden = !item.guide || scanning;
  $("panel-howto").hidden = !note && !steps.length && $("panel-guide").hidden;
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
  $("share-rooms").checked = features.shareRooms;
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
  for (const changed of panelHooks.state) changed(state);
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
  // The steps are for filling the form; a sign-in in progress keeps its link in view.
  $("panel-steps").hidden = active || !$("panel-steps").children.length;
  $("panel-progress").hidden = !active;
  $("panel-done").hidden = !done;
  $("panel-submit").disabled = working;
  const error = failed ? tFor(job.error, selected) : panelError;
  $("panel-error").hidden = !error;
  $("panel-error").textContent = error;
  $("done-title").textContent = t("doneTitle", {
    platform: platformName(selected),
  });
  if (!active) return;
  const scan = job.stage === "scan";
  // A sign-in by link (Twitch) shows the link itself; its QR is for a phone.
  const link = scan && spec(selected)?.signIn === "link";
  $("qr-box").hidden = !scan;
  $("progress-spinner").hidden = scan;
  const late = job.stage === "start" || job.stage === "check";
  $("cancel-platform").hidden = late;
  const step = link
    ? "link"
    : scan
      ? "scan"
      : late || job.stage === "prepare"
        ? job.stage
        : "install";
  $("progress-title").textContent = t(`${step}Title`, {
    platform: platformName(selected),
  });
  $("progress-hint").textContent = t(`${step}Hint`);
  $("qr-link").hidden = !link;
  if (!scan) return;
  $("scan-help").textContent = t(`scanHelp_${selected}`);
  $("qr-image").src = job.qrImage;
  if (!link) return;
  // Only an https link from the platform's own flow becomes a link here.
  const safe = /^https:\/\//.test(job.qrUrl || "") ? job.qrUrl : "";
  $("qr-link").href = safe || "#";
  $("qr-link").hidden = !safe;
  $("qr-link").textContent = t("linkOpen");
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
  "model failed": "r_failed",
  blocked: "r_blocked",
  "delivery failed": "r_undelivered",
  proactive: "r_proactive",
  "answered together": "r_together",
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
  // A reason this page does not know yet is still said in the page's words.
  return key ? t(key) : t("r_other");
}
function modeText(row) {
  if (!row.mode) return "";
  const key =
    row.mode === "judge" && !row.spoke ? "m_judge_quiet" : `m_${row.mode}`;
  return translations[lang]?.[key] || translations.en[key] || "";
}
// The dot means only "learned something new since you last looked": nothing
// here waits for the reader, so items under observation never light it.
const ACTIVITY_SEEN_KEY = "personagent-activity-seen";
function activityLatest() {
  return Math.max(0, ...(activity?.chats || []).map((chat) => chat.latest || 0));
}
function activitySeen() {
  try {
    const value = localStorage.getItem(ACTIVITY_SEEN_KEY);
    return value === null ? null : Number(value) || 0;
  } catch {
    return null;
  }
}
function markActivitySeen() {
  try {
    localStorage.setItem(ACTIVITY_SEEN_KEY, String(activityLatest()));
  } catch {
    // Without storage the dot simply stays off.
  }
}
function renderActivityDot() {
  // The first look ever records what is there instead of lighting the dot.
  if (activity?.chats && (view === "activity" || activitySeen() === null))
    markActivitySeen();
  const seen = activitySeen();
  const dot = $("activity-dot");
  dot.hidden = seen === null || activityLatest() <= seen;
  dot.title = dot.hidden ? "" : t("activityFresh");
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
function activityDate(epoch) {
  return new Date(epoch * 1000).toLocaleDateString(LANGS[lang] || "en", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
// Where an item under observation stands: one sentence, then when it would be
// set aside. The learned panel shows the same sentences (PA.standing).
function standingText(info) {
  if (!info) return [];
  const counts = {
    events: ["activityStageEvents", info.events, info.needEvents],
    strong: ["activityStageStrong", info.strong, info.needStrong],
    speakers: ["activityStageSpeakers", info.speakers, info.needSpeakers],
  };
  let head = "";
  if (info.stage === "reactions") {
    const [key, have, need] = counts[info.missing] || [];
    head = key
      ? t(key, { have: String(have ?? 0), need: String(need ?? 0) })
      : t("activityStageApproval");
  } else if (info.stage === "observing")
    head = t("activityStageObserving", { reason: info.reason || "" });
  else if (
    ["deciding", "held", "off", "ready"].includes(info.stage)
  )
    head = t(`activityStage${info.stage[0].toUpperCase()}${info.stage.slice(1)}`);
  const out = head ? [head] : [];
  if (info.expires) out.push(t("activityExpires", { date: activityDate(info.expires) }));
  return out;
}
// How an item in use came into use.
function cameInText(info) {
  if (!info || !info.by) return "";
  if (info.by === "character")
    return t("activityByCharacter", { reason: info.why || "" });
  return t(info.by === "reactions" ? "activityByReactions" : "activityByPerson");
}
// The person at this page, as its own chat names them: the admin's name, or the word for an admin.
function pagePerson() {
  return state?.adminName || t("activityAdmin");
}
function change(item, observed) {
  const card = el("div", `change${observed ? " observed" : ""}`);
  const top = el("div", "change-top");
  const from = item.self ? [pagePerson()] : item.from;
  const who = from.length ? t("activityFrom", { who: from.join(t("listSep")) }) : "";
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
  // Observed items are there to be read: their standing, and no buttons.
  const status = observed ? standingText(item.standing) : [cameInText(item.by)];
  for (const text of status.filter(Boolean))
    card.append(el("p", "change-status", text));
  if (observed) return card;
  const buttons = el("div", "change-actions");
  if (item.actions.includes("rollback"))
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
    const sender = row.self ? pagePerson() : row.sender;
    if (sender) line.append(el("strong", "", `${sender} `));
    line.append(text);
    return line;
  };
  if (!row.spoke) item.append(said(row.text));
  else {
    if (row.answered) item.append(said(row.answered));
    item.append(el("p", "reply", row.text));
  }
  // A message answered in another's reply was not passed over.
  const why = row.spoke
    ? [modeText(row)]
    : row.reason === "answered together"
      ? [reasonText(row)]
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
  if (chat.retired && (chat.learned.length || chat.observing.length))
    parts.push(el("p", "activity-note", t("activityLearnedRetired")));
  if (chat.learned.length) {
    const part = section("activityLearned", chat.learned.length);
    for (const item of chat.learned) part.append(change(item, false));
    parts.push(part);
  }
  if (chat.observing.length) {
    const part = section("activityObserving", chat.observing.length);
    part.id = "activity-observing";
    part.append(el("p", "section-hint", t("activityObservingHint")));
    for (const item of chat.observing) part.append(change(item, true));
    parts.push(part);
  }
  const remembers = memorySection(chat);
  if (remembers) parts.push(remembers);
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
    // Open on the latest chat; nothing in any chat waits for the reader.
    if (!chats.some((chat) => chat.id === activitySelected))
      activitySelected = (chats[0] || {}).id || "";
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
    toast(t("activityUndone"));
    learnedChanged();
  } catch (error) {
    toast(t(error.message));
  } finally {
    activityBusy = false;
    activityLoop();
  }
}
// ---- What a chat remembers: each group with the actions that work on it.
// Why the character or a person removed something, as the trash records it.
const REMOVED_WHY = {
  replaced: "activityWhyReplaced",
  merged: "activityWhyMerged",
  ended: "activityWhyEnded",
  evicted: "activityWhyEvicted",
  rolled_up: "activityWhyEvicted",
  rewritten: "activityWhyRewritten",
  unreadable: "activityWhyUnreadable",
};
const REMOVED_KIND = {
  note: "activityKindFact",
  episode: "activityKindEvent",
  thread: "activityThread",
  core: "activityCore",
};
function removedWhy(row) {
  if (row.why === "forgotten_page")
    return t(row.by === "terminal" ? "activityWhyTerminal" : "activityWhyForgotten");
  return REMOVED_WHY[row.why] ? t(REMOVED_WHY[row.why]) : "";
}
function clockTime(epoch) {
  return new Date(epoch * 1000).toLocaleTimeString(LANGS[lang] || "en", {
    hour: "2-digit",
    minute: "2-digit",
  });
}
// An event's time: one day with its hours, or the days it spans.
function eventWhen(event) {
  if (!event.from) return "";
  const from = new Date(event.from * 1000);
  const to = new Date((event.to || event.from) * 1000);
  if (from.toDateString() !== to.toDateString())
    return `${activityDate(event.from)} – ${activityDate(event.to)}`;
  const hours =
    to - from >= 60000
      ? `${clockTime(event.from)}–${clockTime(event.to)}`
      : clockTime(event.from);
  return `${activityDate(event.from)} ${hours}`;
}
function memoryItem(text, details, ...buttons) {
  const item = el("li");
  const body = el("div", "memory-body");
  body.append(el("span", "", text));
  const shown = details.filter(Boolean);
  if (shown.length) body.append(el("small", "", shown.join(" · ")));
  item.append(body, ...buttons);
  return item;
}
function memoryGroup(part, key, items) {
  if (!items.length) return;
  part.append(el("h4", "memory-group", t(key)));
  const list = el("ul", "notes");
  list.append(...items);
  part.append(list);
}
function memorySection(chat) {
  const notes = chat.notes || [];
  const events = chat.events || [];
  const removed = chat.removed || [];
  if (!chat.core && !chat.thread && !notes.length && !events.length && !removed.length)
    return null;
  const part = section("activityNotes");
  part.id = "activity-memory";
  const status = chat.status;
  if (status) {
    const next = Math.max(status.paused || 0, status.next || 0);
    part.append(
      el(
        "p",
        "section-hint memory-status",
        next
          ? t("activityFoldPaused", { time: clockTime(next) })
          : t("activityFoldUsed", { used: String(status.used), cap: String(status.cap) }),
      ),
    );
  }
  const forgetButton = (focus, run) => action("activityForget", "quiet", focus, run);
  if (chat.core) {
    const previous = removed.find((row) => row.kind === "core");
    const buttons = [forgetButton("forget:core", () => forget("core", chat.id, ""))];
    if (previous)
      buttons.push(
        action("activityRestorePrevious", "quiet", `restore:${previous.tid}`, () =>
          restore(previous.tid),
        ),
      );
    memoryGroup(part, "activityCore", [
      memoryItem(
        chat.core,
        [chat.coreAt && t("activityUpdated", { date: activityDate(chat.coreAt) })],
        ...buttons,
      ),
    ]);
  }
  if (chat.thread)
    memoryGroup(part, "activityThread", [
      memoryItem(
        chat.thread.text,
        [
          chat.thread.from &&
            chat.thread.to &&
            t("activityCovers", {
              from: activityDate(chat.thread.from),
              to: activityDate(chat.thread.to),
            }),
        ],
        forgetButton(`forget:thread:${chat.thread.id}`, () =>
          forget("thread", chat.id, chat.thread.id),
        ),
      ),
    ]);
  memoryGroup(
    part,
    "activityFacts",
    notes.map((note) =>
      memoryItem(
        note.text,
        [
          (note.aboutSelf || note.about) &&
            t("activityAbout", { who: note.aboutSelf ? pagePerson() : note.about }),
          (note.saidBySelf || note.saidBy) &&
            t("activitySaidBy", { name: note.saidBySelf ? pagePerson() : note.saidBy }),
          note.by && note.by !== "auto" && t("activityFrom", { who: note.by }),
          // A note from another private chat (an earlier chat on this page) is not a group's.
          note.conv !== chat.id && !String(note.conv).startsWith("private:") && t("activityRoomNote"),
          note.born && t("activityFirstNoted", { date: activityDate(note.born) }),
          note.used && t("activityLastUsed", { date: activityDate(note.used) }),
        ],
        forgetButton(`forget:${note.id}`, () => forget("note", note.conv, note.id)),
      ),
    ),
  );
  memoryGroup(
    part,
    "activityEvents",
    events.map((event) =>
      memoryItem(
        event.text,
        [eventWhen(event), [...(event.self ? [pagePerson()] : []), ...event.names].join(t("listSep"))],
        forgetButton(`forget:episode:${event.id}`, () =>
          forget("episode", chat.id, event.id),
        ),
      ),
    ),
  );
  if (removed.length) {
    const now = Date.now() / 1000;
    memoryGroup(
      part,
      "activityRemoved",
      removed.map((row) => {
        const open = row.until > now;
        return memoryItem(
          row.text,
          [
            t(REMOVED_KIND[row.kind] || "activityKindFact"),
            removedWhy(row),
            activityDate(row.at),
            open && t("activityUntil", { date: `${activityDate(row.until)} ${clockTime(row.until)}` }),
          ],
          // Past its time it can no longer come back, so nothing offers it.
          ...(open
            ? [action("activityRestore", "quiet", `restore:${row.tid}`, () => restore(row.tid))]
            : []),
        );
      }),
    );
    const heading = part.querySelectorAll("h4.memory-group");
    heading[heading.length - 1].after(el("p", "section-hint", t("activityRemovedHint")));
  }
  const whole = el("div", "memory-actions");
  whole.append(action("activityForgetChat", "quiet", "forget-whole-chat", forgetWholeChat));
  part.append(whole);
  return part;
}
// One memory write: the view waits, then shows the chat as the service has it.
async function memoryCall(path, payload, done) {
  if (activityBusy) return;
  activityBusy = true;
  const seq = ++activitySeq;
  renderActivity();
  try {
    done(await api(path, payload), seq);
  } catch (error) {
    toast(t(error.message));
  } finally {
    activityBusy = false;
    activityLoop();
  }
}
function forget(kind, conv, id) {
  return memoryCall("activity/forget", { chat: activitySelected, conv, kind, id }, (result, seq) => {
    if (seq === activitySeq) activityChat = result.chat;
    const tid = result.tid;
    toast(
      t("activityForgotten"),
      tid ? { label: t("activityUndo"), run: () => restore(tid) } : null,
    );
  });
}
function restore(tid) {
  return memoryCall("activity/restore", { chat: activitySelected, tid }, (chat, seq) => {
    if (seq === activitySeq) activityChat = chat;
    toast(t("activityRestored"));
  });
}
async function forgetWholeChat() {
  if (activityBusy) return;
  const chat = activitySelected;
  // This page's own chat starts anew, as its own Forget does, and asks the same question.
  // An earlier page chat's learned items are already out of use; another chat's stay in use.
  const retired = activityChat?.id === chat && Boolean(activityChat.retired);
  const page = chat.startsWith("private:browser:") && !retired;
  const question = page ? "forgetChatAsk" : retired ? "activityForgetOldChatAsk" : "activityForgetChatAsk";
  if (!(await ask(t(question), t("activityForgetChat")))) return;
  await memoryCall("activity/forget_chat", { chat }, () => {
    toast(t(page ? "forgetChatDone" : "activityChatForgotten"));
    if (page) {
      api("chat/history").then(showHistory, () => {});
      learnedChanged();
    }
  });
}
// As many messages as the server keeps; the history tells the page its number.
let chatKept = Infinity;
function dropBubble(node) {
  if (node.dataset.url) URL.revokeObjectURL(node.dataset.url);
  node.remove();
}
function bubble(text, kind) {
  const node = document.createElement("div");
  node.className = `bubble ${kind}`;
  node.textContent = text;
  $("messages").append(node);
  // A window left open for days holds no more than the chat keeps.
  const shown = $("messages").querySelectorAll(".bubble");
  for (let i = 0; i < shown.length - chatKept; i++) dropBubble(shown[i]);
  $("messages").scrollTop = $("messages").scrollHeight;
  return node;
}
// The newest message the chat shows, and which chat it is: a new chat starts over.
let chatSeen = 0,
  chatTag = "",
  chatTimer = null,
  chatPolling = false,
  chatPolled = 0;
// What the character sends on its own is looked for this often while the chat is on screen.
const CHAT_POLL_MS = 3000;
const pictureAlt = () => t("chatPicture", { name: state?.name || defaultName() });
function pictureGone(node) {
  node.classList.remove("loading");
  node.classList.add("gone");
  node.dataset.t = "chatPictureGone";
  node.textContent = t("chatPictureGone");
}
// The picture route needs the page's token, which an <img> cannot send.
async function showPicture(node, name) {
  try {
    const response = await fetch(`/api/chat/picture/${encodeURIComponent(name)}`, {
      headers: { "X-Personagent-Setup-Token": token },
      credentials: "omit",
    });
    if (!response.ok) throw new Error("gone");
    const blob = await response.blob();
    // Its bubble may have gone while the picture loaded.
    if (!node.isConnected) return;
    const url = URL.createObjectURL(blob);
    node.dataset.url = url;
    const image = document.createElement("img");
    image.alt = pictureAlt();
    image.addEventListener(
      "load",
      () => {
        node.classList.remove("loading");
        $("messages").scrollTop = $("messages").scrollHeight;
      },
      { once: true },
    );
    image.addEventListener("error", () => pictureGone(node), { once: true });
    image.src = url;
    node.replaceChildren(image);
  } catch {
    pictureGone(node);
  }
}
function showMessage(item, arrived = false) {
  const node =
    item.picture !== undefined
      ? bubble("", "bot picture loading")
      : bubble(item.text, item.role === "user" ? "user" : "bot");
  if (item.picture !== undefined) {
    if (item.picture) showPicture(node, item.picture);
    else pictureGone(node);
  }
  if (item.via === "coding") {
    const via = el("small", "bubble-via", t("chatViaCoding"));
    via.dataset.t = "chatViaCoding";
    Object.assign(via.style, { display: "block", marginTop: "2px", fontSize: "11.5px", opacity: "0.7" });
    node.append(via);
  }
  if (arrived) node.classList.add("arrived");
  chatSeen = Math.max(chatSeen, item.seq || 0);
  $("chat-empty").hidden = true;
  return node;
}
// A reply arrives the way a person sends it: one message at a time, each after
// about the time it takes to type, with the typing sign in between.
const TYPING = { perChar: 130, pause: 350, jitter: 450, most: 2600, whole: 9000 };
// Showing the chat afresh ends a reply that is still arriving.
let chatEpoch = 0;
function typingBubble() {
  const node = bubble("", "bot pending typing");
  node.setAttribute("role", "status");
  node.setAttribute("aria-label", t("thinking"));
  // Relabelled when the language changes.
  node.dataset.tAria = "thinking";
  const dots = el("span", "dots");
  dots.append(el("i"), el("i"), el("i"));
  node.append(dots);
  return node;
}
function typingTime(item) {
  if (item.picture !== undefined) return 600 + Math.random() * 600;
  const length = Array.from(item.text || "").length;
  return Math.min(TYPING.most, length * TYPING.perChar + TYPING.pause + Math.random() * TYPING.jitter);
}
// `spent`: how long the first message has already been waited for.
async function reveal(items, spent = 0) {
  const epoch = chatEpoch;
  let left = TYPING.whole;
  for (const item of items) {
    if (item.seq && item.seq <= chatSeen) continue;
    if (item.role === "user") {
      showMessage(item);
      continue;
    }
    const time = Math.min(left, Math.max(0, typingTime(item) - spent));
    spent = 0;
    if (time > 0) {
      const typing = typingBubble();
      avatarMood("thinking");
      await new Promise((done) => setTimeout(done, time));
      typing.remove();
      left -= time;
      if (epoch !== chatEpoch) return;
      // Shown meanwhile by another look at the chat.
      if (item.seq && item.seq <= chatSeen) continue;
    }
    showMessage(item, true);
    avatarMood("talking", Array.from(item.text || "").length);
  }
}
// A reply that is still arriving stops: its typing sign goes, and what it had
// not shown yet comes with the next look at the chat.
function stopReveal() {
  chatEpoch += 1;
  for (const node of $("messages").querySelectorAll(".bubble.typing")) node.remove();
  avatarMood("");
}
function showHistory(history) {
  stopReveal();
  for (const node of $("messages").querySelectorAll(".bubble")) dropBubble(node);
  if (history.kept) chatKept = history.kept;
  chatSeen = 0;
  chatTag = history.chat || "";
  $("chat-empty").hidden = history.messages.length > 0;
  for (const item of history.messages) showMessage(item);
  chatSeen = Math.max(chatSeen, history.last || 0);
}
async function chatLoop() {
  clearTimeout(chatTimer);
  chatTimer = null;
  if (ended || view !== "chat" || document.hidden || !state?.configured) return;
  // Opening the chat again soon after does not look sooner than the interval allows.
  const wait = chatPolled + CHAT_POLL_MS - Date.now();
  if (wait > 0) {
    chatTimer = setTimeout(chatLoop, wait);
    return;
  }
  if (!chatting && !chatPolling) {
    chatPolling = true;
    chatPolled = Date.now();
    try {
      const value = await api(`chat/history?after=${chatSeen}`);
      if (value.kept) chatKept = value.kept;
      // A reply that started meanwhile brings these messages itself.
      if (!chatting) {
        if (value.chat !== chatTag) showHistory(await api("chat/history"));
        else await reveal(value.messages.filter((item) => item.seq > chatSeen));
      }
    } catch {
      // The next look tries again; a lasting problem shows when a message is sent.
    } finally {
      chatPolling = false;
    }
  }
  clearTimeout(chatTimer);
  if (!ended && view === "chat" && !document.hidden)
    chatTimer = setTimeout(chatLoop, CHAT_POLL_MS);
}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) clearTimeout(chatTimer);
  else chatLoop();
});
let talkTimer = null;
// The chat avatar thinks while a reply is on its way, then talks for a
// while that grows with the reply.
function avatarMood(mood, length = 0) {
  const node = $("chat-avatar");
  clearTimeout(talkTimer);
  node.classList.toggle("thinking", mood === "thinking");
  node.classList.toggle("talking", mood === "talking");
  if (mood === "talking")
    talkTimer = setTimeout(
      () => node.classList.remove("talking"),
      Math.min(3200, Math.max(900, 45 * length)),
    );
}
async function send(text, mine = null) {
  if (chatting || !text.trim()) return;
  chatting = true;
  $("chat-empty").hidden = true;
  $("message").value = "";
  syncSend();
  // What the character was sending on its own comes back in order with the answer.
  stopReveal();
  mine ||= bubble(text, "user");
  const pending = typingBubble();
  const asked = performance.now();
  avatarMood("thinking");
  try {
    const value = await api("chat", { text, after: chatSeen });
    if (value.kept) chatKept = value.kept;
    // The chat as recorded, in order: anything the character sent on its own
    // meanwhile, this message and the reply.
    mine.remove();
    pending.remove();
    const own = value.messages.filter((item) => item.role === "user").pop();
    const answered = value.messages.some((item) => item.role !== "user" && own && item.seq > own.seq);
    if (value.chat !== chatTag) {
      showHistory(await api("chat/history"));
      avatarMood(answered ? "talking" : "", Array.from(value.reply || "").length);
    } else await reveal(value.messages, performance.now() - asked);
    if (!answered) {
      bubble(t("noReply"), "bot");
      avatarMood("");
    }
  } catch (error) {
    avatarMood("");
    pending.replaceChildren();
    pending.removeAttribute("role");
    pending.removeAttribute("aria-label");
    delete pending.dataset.tAria;
    pending.textContent = t(error.message);
    pending.className = "bubble failed";
    const retry = document.createElement("button");
    retry.className = "quiet";
    retry.textContent = t("retryChat");
    retry.addEventListener("click", () => {
      // send() ignores a call while another reply is on its way.
      if (chatting) return;
      pending.remove();
      send(text, mine);
    });
    pending.append(document.createElement("br"), retry);
  } finally {
    chatting = false;
    syncSend();
    $("message").focus();
    $("messages").scrollTop = $("messages").scrollHeight;
    chatLoop();
  }
}
for (const button of document.querySelectorAll(".nav"))
  button.addEventListener("click", () => showView(button.dataset.view));
// The name at the top left goes home, as a logo does.
document.querySelector(".brand").addEventListener("click", (event) => {
  event.preventDefault();
  showView("chat");
});
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
  // Before the first setup the reader's language is the natural first choice.
  if (!state.configured) $("character-lang").value = lang;
  renderLanguage();
  showView(view);
});
$("provider").addEventListener("change", () => providerChanged());
$("model").addEventListener("input", freeNoteChanged);
$("character-name").addEventListener("input", updateNames);
$("character").addEventListener("change", characterChanged);
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
      shareRooms: $("share-rooms").checked,
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
    updateNames();
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
  // A personality or portrait chosen over a character the person wrote replaces their text.
  if (
    state.character === "custom" &&
    $("character").value !== "custom" &&
    !(await ask(t("personaReplaceAsk"), t("personaReplaceYes")))
  )
    return;
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
      lang: $("character-lang").value || lang,
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
// Nothing to send while the box holds only white space.
function syncSend() {
  $("send").disabled = chatting || !$("message").value.trim();
}
$("message").addEventListener("input", syncSend);
syncSend();
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
// The commands the character takes in a chat, in the language it reads them
// in: its name first, then the words docs/guide.md lists.
// Per character language: remember, forget, what do you remember, what have you learned.
const MEMORY_COMMANDS = {
  en: ["{n}, remember ", "{n}, forget ", "{n}, what do you remember", "{n}, what have you learned"],
  zh: ["{n} 记住 ", "{n} 忘掉 ", "{n} 你都记得什么", "{n} 学到了什么"],
  "zh-TW": ["{n} 記住 ", "{n} 忘掉 ", "{n} 你都記得什麼", "{n} 你學到了什麼"],
  ja: ["{n}、覚えて：", "{n}、忘れて、", "{n}、何覚えてる？", "{n}、何を学んだ？"],
  ko: ["{n} 기억해: ", "{n} 잊어 줘: ", "{n} 뭐 기억해?", "{n} 너 뭐 배웠어?"],
  es: ["{n}, recuerda que ", "{n}, olvídate de ", "{n}, ¿qué recuerdas?", "{n}, ¿qué has aprendido?"],
  fr: ["{n}, retiens que ", "{n}, oublie ", "{n}, tu te souviens de quoi ?", "{n}, qu'est-ce que tu as appris ?"],
  de: ["{n}, merk dir, dass ", "{n}, vergiss ", "{n}, was hast du dir gemerkt?", "{n}, was hast du gelernt?"],
  "pt-BR": ["{n}, anota aí que ", "{n}, esquece ", "{n}, o que você lembra?", "{n}, o que você aprendeu?"],
  ru: ["{n}, запомни, что ", "{n}, забудь про ", "{n}, что ты помнишь?", "{n}, чему ты научилась?"],
};
function memoryCommands() {
  const name = state.name || defaultName();
  return (MEMORY_COMMANDS[state.lang] || MEMORY_COMMANDS.en).map((line) => line.replace("{n}", name));
}
$("commands-show").addEventListener("click", () => {
  const open = $("chat-commands").hidden;
  $("chat-commands").hidden = !open;
  $("commands-show").setAttribute("aria-expanded", String(open));
  if (!open) return;
  $("chat-command-list").replaceChildren(
    ...memoryCommands().map((command) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "quiet";
      chip.textContent = command.trim();
      chip.addEventListener("click", () => {
        $("message").value = command;
        $("message").dispatchEvent(new Event("input", { bubbles: true }));
        $("message").focus();
      });
      return chip;
    }),
  );
});
$("forget-chat").addEventListener("click", async () => {
  if (chatting) return toast(t("working"));
  if (!(await ask(t("forgetChatAsk"), t("forgetChat")))) return;
  $("forget-chat").disabled = true;
  try {
    const done = await api("chat/forget", {});
    showHistory(await api("chat/history"));
    toast(done.forgotten ? t("forgetChatDone") : t("forgetChatNone"));
    learnedChanged();
  } catch (error) {
    toast(t(error.message));
  } finally {
    $("forget-chat").disabled = false;
  }
});
$("reset-chat").addEventListener("click", async () => {
  if (chatting) return;
  try {
    await api("chat/reset", {});
    showHistory(await api("chat/history"));
    learnedChanged();
    toast(t("newChatDone"));
  } catch (error) {
    toast(t(error.message));
  }
});
async function refresh() {
  state = await api("state");
  renderStatus();
}
// The page's own question: a browser's confirm() names 127.0.0.1 in its title.
function ask(question, yes) {
  const box = $("ask");
  $("ask-text").textContent = question;
  $("ask-yes").textContent = yes;
  box.returnValue = "";
  return new Promise((resolve) => {
    box.addEventListener("close", () => resolve(box.returnValue === "yes"), { once: true });
    box.showModal();
  });
}
$("ask-yes").addEventListener("click", () => $("ask").close("yes"));
$("ask-no").addEventListener("click", () => $("ask").close(""));
async function disconnect(kind) {
  const sure = await ask(t("confirmDisconnect", { platform: platformName(kind) }), t("disconnect"));
  if (!sure) return;
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
// A window without a title bar of its own: the top bar moves it (app-region
// in the style sheet, which also gives the top edge its resize border) and
// holds the buttons a title bar has.
let frame = { frameless: false, maximized: false };
let frameTimer = null;
function renderFrame() {
  document.body.classList.toggle("frameless", frame.frameless);
  document.body.classList.toggle("maximized", frame.frameless && frame.maximized);
  $("window-controls").hidden = !frame.frameless;
  const key = frame.maximized ? "winRestore" : "winMax";
  const button = $("window-maximize");
  button.dataset.tAria = button.dataset.tTitle = key;
  button.setAttribute("aria-label", t(key));
  button.title = t(key);
}
async function loadFrame() {
  try {
    frame = await api("window");
  } catch {
    // In a browser tab, or before the page is let in: the window keeps its own bar.
  }
  renderFrame();
}
async function windowDo(action) {
  try {
    frame = await api("window", { action });
    renderFrame();
  } catch {
    toast(t("winFailed"));
  }
}
$("window-minimize").addEventListener("click", () => windowDo("minimize"));
$("window-maximize").addEventListener("click", () => windowDo(frame.maximized ? "restore" : "maximize"));
$("window-close").addEventListener("click", () => windowDo("close"));
// Maximizing, restoring and snapping all change the size: ask how the window stands.
window.addEventListener("resize", () => {
  if (!frame.frameless) return;
  clearTimeout(frameTimer);
  frameTimer = setTimeout(loadFrame, 150);
});
// What a panel under /assets/panels builds its part of the page with. Panel
// scripts run after this file and before the first state arrives.
window.PA = {
  $,
  api,
  t,
  toast,
  ask,
  // The Activity view's sentences for where an item stands and how it came into use.
  standing: standingText,
  cameIn: cameInText,
  refresh,
  showView,
  get state() {
    return state;
  },
  get lang() {
    return lang;
  },
  get view() {
    return view;
  },
  // { en: {key: "..."}, zh: {...} }: a panel's sentences, keyed like the rest.
  strings(tables) {
    for (const [code, table] of Object.entries(tables))
      Object.assign((translations[code] ||= {}), table);
  },
  // fn() each time `view` is opened: chat, activity, platforms, settings, practice, app.
  onShow(view, fn) {
    (panelHooks.show[view] ||= []).push(fn);
  },
  // fn(state) each time the page's state is read again.
  onState(fn) {
    panelHooks.state.push(fn);
  },
  // fn() after something elsewhere on the page changed what was learned or where it applies.
  onLearned(fn) {
    panelHooks.learned.push(fn);
  },
  // A panel changed what was learned: the other places that show it read it again.
  learnedChanged(fn) {
    learnedChanged(fn);
  },
  // fn() after the page changes language.
  onLanguage(fn) {
    panelHooks.language.push(fn);
  },
  // After a panel changed what the page is built from (a reset, a restore):
  // read the state again, fill the forms from it and empty the chat on screen.
  async reload() {
    state = await api("state");
    populate();
    renderLanguage();
    showHistory(await api("chat/history"));
  },
};
(async () => {
  // First, and not waited for: a frameless window needs its buttons whatever else loads.
  loadFrame();
  await loadLang(lang);
  if (!token) {
    renderText();
    toast(t("auth"));
    // No view can open, so the message stays up.
    clearTimeout(toastTimer);
    return;
  }
  try {
    [state, catalog] = await Promise.all([api("state"), api("catalog")]);
    // Loaded once up front, so switching characters never shows an empty circle.
    for (const item of catalog.characters)
      if (item.avatar) new Image().src = item.avatar;
    buildTrio();
    // With no choice saved, the page speaks the language the character was set up in.
    if (!storedLang() && state.lang) {
      lang = state.lang;
      await loadLang(lang);
    }
    populate();
    renderLanguage();
    showView("chat");
    showHistory(await api("chat/history"));
    chatLoop();
    poll();
    activityLoop();
  } catch (error) {
    toast(t(error.message));
    // Nothing loaded and no view is open: keep the message up.
    if (!state) clearTimeout(toastTimer);
  }
})();
