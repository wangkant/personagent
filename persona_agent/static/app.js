"use strict";

// Every value from the server reaches the page through textContent or an
// attribute: nothing here parses HTML.

const STRINGS = {
  en: {
    title: "personagent dashboard",
    state_ready: "Running",
    state_no_key: "No model key",
    state_off: "Agent off",
    state_down: "Unreachable",
    state_error: "Error",
    other_lang: "中文",
    theme_auto: "Theme: auto",
    theme_light: "Theme: light",
    theme_dark: "Theme: dark",
    service: "Service",
    version: "Version",
    uptime: "Uptime",
    home: "Home folder",
    language: "Language",
    outbox: "Outbox",
    on: "on",
    off: "off",
    models: "Models",
    no_models: "No agent is running, so no model is in use.",
    role_reply: "Replies",
    role_gate: "Speak or stay quiet",
    role_dm: "Direct messages",
    role_fallback: "Fallback",
    role_react: "Reaction judge",
    role_eval: "Self-review",
    role_evolve: "Evolution",
    role_vision: "Images",
    role_embedding: "Embeddings",
    connectors: "Connectors",
    no_connectors: "No connector has forwarded a message yet.",
    unnamed_connector: "(no connector id)",
    last_event: "last message {t}",
    no_event: "no message yet",
    convs_n: "{n} chats",
    convs_n_1: "1 chat",
    pulling: "pulling the outbox",
    not_pulling: "not pulling the outbox",
    checks: "Configuration checks",
    no_findings: "No problems found in .env.",
    persona: "Persona",
    unnamed: "(no name: set PERSONA_NAME)",
    persona_file: "File",
    source_example: "the bundled example; write your own persona.txt",
    source_builtin: "no persona file found; using the built-in default",
    lineage: "Lineage",
    lineage_n: "{n} revisions of this document count as this character",
    lineage_1: "1 revision so far; edits keep what it learned",
    persona_version: "PERSONA_VERSION",
    conversations: "Conversations",
    no_convs_t: "No conversations yet",
    no_convs: "Chats appear here once a message arrives.",
    pick_t: "Pick a conversation",
    pick: "See why it spoke or stayed quiet there, and what it learned.",
    group: "group",
    dm: "DM",
    notes_n: "{n} notes",
    notes_n_1: "1 note",
    learned_n: "{n} learned",
    pending_n: "{n} waiting",
    last_activity: "active {t}",
    never: "no activity",
    trigger_progress: "Joins in on its own after {n} messages (CHAT_TRIGGER_COUNT); {c} so far.",
    decisions: "Speak or stay quiet",
    no_decisions: "No decision recorded since the service started.",
    spoke: "Spoke",
    quiet: "Stayed quiet",
    said: "said:",
    after: "after:",
    times: "×{n}",
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
    pending: "Waiting for approval",
    no_pending: "No proposal is waiting.",
    learned: "Learned",
    no_learned: "Nothing learned in this chat yet. It learns when people react to its replies.",
    past: "Rejected, rolled back or replaced",
    show: "Show",
    memories: "Memory notes",
    no_memories: "No memory notes in this chat.",
    core_note: "Running note",
    by_admin: "admin",
    by_auto: "saved on its own",
    t_preference_pair: "Better wording",
    t_positive_example: "Reply worth repeating",
    s_proposed: "waiting",
    s_promoted: "in use",
    s_rejected: "rejected",
    s_rolled_back: "rolled back",
    s_superseded: "replaced",
    it_said: "It said",
    better: "Better",
    reply: "Reply",
    context: "Context",
    evidence: "Evidence chain",
    no_evidence: "No evidence linked.",
    missing_evidence: "{n} linked events are no longer in the evidence log.",
    missing_evidence_1: "1 linked event is no longer in the evidence log.",
    k_reaction: "reacted",
    k_retry_acceptance: "accepted the retry",
    k_self_eval: "self-score",
    k_self_review: "self-review",
    rt_correction: "correction",
    rt_rejection: "rejection",
    rt_positive: "positive",
    rt_neutral: "neutral",
    st_strong: "strong",
    st_negative_only: "weak (says what is wrong)",
    st_weak: "weak",
    aimed_at_them: "the reply was aimed at them",
    judge: "judge:",
    dismissed: "dismissed by the judge",
    not_counted: "does not count toward this",
    checklist: "Promotion checklist",
    passed: "passed",
    not_yet: "not yet",
    c_auto: "Automatic promotion is on",
    c_no_disagreement: "No evidence against it",
    c_no_conflict: "No conflicting proposal",
    c_strong: "{have} of {need} strong: from the person it was aimed at",
    c_strong_impossible: "Only a person can promote this kind",
    c_events: "{have} of {need} agreeing events",
    c_speakers: "{have} of {need} different people (the admin counts alone)",
    c_same_chat: "Evidence only combines within this chat",
    c_any_chat: "Evidence may combine across chats (PROMOTE_REQUIRE_SAME_CONVERSATION=false)",
    waiting_for: "Waiting for:",
    w_auto: "an admin (automatic promotion is off)",
    w_admin: "an admin to decide",
    w_strong: "a direct correction from the person it was aimed at, or them accepting its retry",
    w_events: "another agreeing reaction in this chat",
    w_speakers: "another person to agree",
    w_ready: "nothing: the next reaction check promotes it",
    policy: "Policy:",
    history: "History",
    hs_promoted: "promoted",
    hs_rejected: "rejected",
    hs_rolled_back: "rolled back",
    hs_superseded: "replaced",
    by_auto_actor: "automatically",
    by_dashboard_actor: "from the dashboard",
    by_actor: "by {actor}",
    a_promote: "Promote",
    a_reject: "Reject",
    a_rollback: "Roll back",
    a_replace: "Replace",
    confirm: "Click again to confirm",
    done_promote: "Promoted. It shapes replies from the next turn.",
    done_reject: "Rejected. It will not be used.",
    done_rollback: "Rolled back. It stops shaping replies from the next turn.",
    done_replace: "Replaced. The new wording shapes replies from the next turn; the old one stays in the history.",
    rival: "Another rewrite of this reply is in use: “{text}”. Replace puts this one in its place.",
    shown_of: "Showing the newest {shown} of {n}.",
    views_failed: "Saved in the ledger, but the views could not be rebuilt; run `{cli} learned rebuild`.",
    refused: "Refused: {msg}",
    h_off_t: "The agent is turned off",
    h_off: "AGENT_ENABLED is false in .env. Set it to true and restart.",
    h_nokey_t: "No model key",
    h_nokey: "LLM_API_KEY is empty, so it cannot reply. Run `{cli} init`.",
    h_none_t: "No message has arrived since the service started",
    h_none_url: "Your chat connector (for example the AstrBot plugin) must send to `{url}`",
    h_none_token_set: "CONNECTOR_TOKEN is set here, so the connector needs the same token.",
    h_none_token_blank: "CONNECTOR_TOKEN is blank here: leave the connector's token blank too, or set the same one on both sides.",
    h_none_access: "If ACCESS_GROUPS or ACCESS_DM_USERS is set, the chat has to be listed there.",
    h_none_doctor: "`{cli} doctor` checks the whole path.",
    h_refused_t: "Messages arrived but were turned away",
    h_quiet_t: "Messages are arriving; it has not spoken yet",
    h_quiet: "It answers when called by name ({name}) or @-mentioned. Otherwise it may join in after {n} messages, and it can decide to stay quiet.",
    footer: "Private page: it opens only through its link with the token. Changes go into the append-only ledger as “dashboard”.",
    updated: "Updated {t}",
    down: "Cannot reach the service. Is `{cli} run` still running?",
    h_auth_t: "This page needs its link again",
    h_auth: "The service no longer accepts this page's sign-in. Run `{cli} doctor` and open the dashboard link it prints.",
    h_error_t: "The service answered with an error ({status})",
    just_now: "just now",
    min_ago: "{n} min ago",
    h_ago: "{n} h ago",
    d_ago: "{n} d ago",
    dur_m: "{m} min",
    dur_hm: "{h} h {m} min",
    dur_dh: "{d} d {h} h",
    status_details: "Service details",
    up: "up {t}",
    roles_n: "{n} roles",
    roles_n_1: "1 role",
    no_connector_short: "no connector yet",
    chk_n: "{n} config notes",
    chk_n_1: "1 config note",
    chk_ok: "config OK",
    outbox_on: "outbox on",
    outbox_off: "outbox off",
    spoke_n: "{n} spoke",
    quiet_n: "{n} quiet",
    show_in_chat: "Show in chat",
    from_ledger: "earlier reply, from the learning ledger",
    today: "Today",
    more_detail: "Evidence and history",
    why_detail: "Checklist, evidence and context",
    listening: "Listening",
    next_step: "Next step",
    rules_passed: "{have} of {n} passed",
    back: "All conversations",
    show_all: "Show all {n}",
    show_fewer: "Show fewer",
    latest: "Jump to latest",
    lang_zh: "Chinese (zh)",
    lang_en: "English (en)",
  },
  zh: {
    title: "personagent 面板",
    state_ready: "运行中",
    state_no_key: "缺少模型密钥",
    state_off: "代理已关闭",
    state_down: "连不上",
    state_error: "出错",
    other_lang: "English",
    theme_auto: "主题：自动",
    theme_light: "主题：浅色",
    theme_dark: "主题：深色",
    service: "服务",
    version: "版本",
    uptime: "已运行",
    home: "主目录",
    language: "语言",
    outbox: "发件箱",
    on: "开",
    off: "关",
    models: "模型",
    no_models: "代理没有运行，没有在用的模型。",
    role_reply: "回复",
    role_gate: "说不说话的判断",
    role_dm: "私聊",
    role_fallback: "备用",
    role_react: "反应评判",
    role_eval: "自评",
    role_evolve: "演化",
    role_vision: "识图",
    role_embedding: "向量检索",
    connectors: "连接器",
    no_connectors: "还没有连接器转发过消息。",
    unnamed_connector: "（没有连接器 id）",
    last_event: "最近消息：{t}",
    no_event: "还没有消息",
    convs_n: "{n} 个会话",
    pulling: "正在拉取发件箱",
    not_pulling: "没有拉取发件箱",
    checks: "配置检查",
    no_findings: ".env 里没有发现问题。",
    persona: "人设",
    unnamed: "（没有名字：请设置 PERSONA_NAME）",
    persona_file: "文件",
    source_example: "内置示例；可以自己写 persona.txt",
    source_builtin: "没找到人设文件，正在用内置默认人设",
    lineage: "版本线",
    lineage_n: "这份人设文档的 {n} 个版本都算同一个角色",
    lineage_1: "目前 1 个版本；改人设不会丢掉学到的东西",
    persona_version: "PERSONA_VERSION",
    conversations: "会话",
    no_convs_t: "还没有会话",
    no_convs: "收到消息后，会话会出现在这里。",
    pick_t: "选一个会话",
    pick: "看看它在那里为什么发言或沉默，学到了什么。",
    group: "群聊",
    dm: "私聊",
    notes_n: "{n} 条记忆",
    learned_n: "已学会 {n}",
    pending_n: "待确认 {n}",
    last_activity: "{t}活跃",
    never: "没有动静",
    trigger_progress: "累计 {n} 条消息后它会考虑主动插话（CHAT_TRIGGER_COUNT），现在是 {c} 条。",
    decisions: "发言还是沉默",
    no_decisions: "服务启动以来还没有记录。",
    spoke: "发言",
    quiet: "沉默",
    said: "说：",
    after: "针对：",
    times: "×{n}",
    r_below: "没被叫到，消息数还没到插话门槛",
    r_sleep: "深夜时段，为了作息自然跳过",
    r_skip: "为了节奏自然随机跳过",
    r_passed: "判断这里不需要它说话",
    r_addressed: "被点名或 @",
    r_sticky: "回应之前的点名",
    r_followup: "接着自己刚才的话",
    r_trigger: "消息数到了，考虑插话",
    r_first: "第一次在这个会话出现",
    m_called: "被叫到",
    m_owner: "管理员",
    m_judge: "自己决定插话",
    m_judge_quiet: "可以插话",
    m_followup: "跟进",
    m_proactive: "主动",
    pending: "等待确认",
    no_pending: "没有待确认的提议。",
    learned: "已学会",
    no_learned: "这个会话里还没学到东西。有人对它的回复做出反应时它才会学。",
    past: "已拒绝、撤回或替换",
    show: "展开",
    memories: "记忆",
    no_memories: "这个会话没有记忆。",
    core_note: "常驻笔记",
    by_admin: "管理员",
    by_auto: "它自己记的",
    t_preference_pair: "更好的说法",
    t_positive_example: "值得保留的回复",
    s_proposed: "待确认",
    s_promoted: "生效中",
    s_rejected: "已拒绝",
    s_rolled_back: "已撤回",
    s_superseded: "已替换",
    it_said: "它说的",
    better: "更好的",
    reply: "回复",
    context: "上下文",
    evidence: "证据链",
    no_evidence: "没有关联的证据。",
    missing_evidence: "有 {n} 条关联证据已不在证据日志里。",
    k_reaction: "做出反应",
    k_retry_acceptance: "接受了重说",
    k_self_eval: "自评",
    k_self_review: "自查",
    rt_correction: "纠正",
    rt_rejection: "否定",
    rt_positive: "正面",
    rt_neutral: "中性",
    st_strong: "强",
    st_negative_only: "弱（只说明哪里不对）",
    st_weak: "弱",
    aimed_at_them: "那条回复就是回给 TA 的",
    judge: "评判：",
    dismissed: "被评判驳回",
    not_counted: "不计入这条提议",
    checklist: "晋升检查",
    passed: "已满足",
    not_yet: "未满足",
    c_auto: "自动晋升已开启",
    c_no_disagreement: "没有反对的证据",
    c_no_conflict: "没有冲突的提议",
    c_strong: "强证据 {have}/{need}：来自被回复的那个人",
    c_strong_impossible: "这一类只能由人来确认",
    c_events: "一致的证据 {have}/{need}",
    c_speakers: "不同的人 {have}/{need}（管理员一人即可）",
    c_same_chat: "证据只在本会话内合并",
    c_any_chat: "证据可以跨会话合并（PROMOTE_REQUIRE_SAME_CONVERSATION=false）",
    waiting_for: "还在等：",
    w_auto: "管理员（自动晋升已关闭）",
    w_admin: "管理员来决定",
    w_strong: "被回复的人亲自纠正，或者接受它的重说",
    w_events: "本会话里再有一条一致的反应",
    w_speakers: "另一个人认同",
    w_ready: "不用等：下次检查反应时就会晋升",
    policy: "规则判断：",
    history: "经过",
    hs_promoted: "晋升",
    hs_rejected: "拒绝",
    hs_rolled_back: "撤回",
    hs_superseded: "替换",
    by_auto_actor: "自动",
    by_dashboard_actor: "在面板上",
    by_actor: "由 {actor}",
    a_promote: "采纳",
    a_reject: "拒绝",
    a_rollback: "撤回",
    a_replace: "替换",
    confirm: "再点一次确认",
    done_promote: "已采纳，从下一轮回复开始生效。",
    done_reject: "已拒绝，不会被使用。",
    done_rollback: "已撤回，从下一轮回复开始不再生效。",
    done_replace: "已替换，新的说法从下一轮回复开始生效；旧的留在经过里。",
    rival: "这条回复已经有一个生效中的改写：“{text}”。点“替换”会用这一条换掉它。",
    shown_of: "显示最新的 {shown} 条，共 {n} 条。",
    views_failed: "已写进账本，但检索视图没能重建；请运行 `{cli} learned rebuild`。",
    refused: "被拒绝：{msg}",
    h_off_t: "代理被关闭了",
    h_off: ".env 里 AGENT_ENABLED 是 false。改成 true 后重启。",
    h_nokey_t: "缺少模型密钥",
    h_nokey: "LLM_API_KEY 是空的，它没法回复。运行 `{cli} init`。",
    h_none_t: "服务启动以来还没收到任何消息",
    h_none_url: "聊天连接器（比如 AstrBot 插件）要发到 `{url}`",
    h_none_token_set: "这里设置了 CONNECTOR_TOKEN，连接器那边要填同一个。",
    h_none_token_blank: "这里的 CONNECTOR_TOKEN 是空的：连接器那边也留空，或者两边设成同一个。",
    h_none_access: "如果设置了 ACCESS_GROUPS 或 ACCESS_DM_USERS，这个会话必须在名单里。",
    h_none_doctor: "运行 `{cli} doctor` 可以检查整条链路。",
    h_refused_t: "收到了消息，但被拒之门外",
    h_quiet_t: "消息在进来，它还没开口",
    h_quiet: "被点名（{name}）或 @ 时它会回答；否则大约 {n} 条消息后才考虑插话，而且可能决定不说。",
    footer: "私密页面：只能通过带令牌的链接打开。修改会以“dashboard”的身份写进只增不删的账本。",
    updated: "更新于 {t}",
    down: "连不上服务。`{cli} run` 还在运行吗？",
    h_auth_t: "需要重新用链接打开这个页面",
    h_auth: "服务不再认这个页面的登录。运行 `{cli} doctor`，打开它打印的面板链接。",
    h_error_t: "服务返回了错误（{status}）",
    just_now: "刚刚",
    min_ago: "{n} 分钟前",
    h_ago: "{n} 小时前",
    d_ago: "{n} 天前",
    dur_m: "{m} 分钟",
    dur_hm: "{h} 小时 {m} 分钟",
    dur_dh: "{d} 天 {h} 小时",
    status_details: "服务详情",
    up: "已运行 {t}",
    roles_n: "{n} 个用途",
    no_connector_short: "还没有连接器",
    chk_n: "{n} 条配置提示",
    chk_ok: "配置正常",
    outbox_on: "发件箱开",
    outbox_off: "发件箱关",
    spoke_n: "发言 {n}",
    quiet_n: "沉默 {n}",
    show_in_chat: "在聊天里看",
    from_ledger: "更早的回复，来自学习账本",
    today: "今天",
    more_detail: "证据和经过",
    why_detail: "检查项、证据和上下文",
    listening: "在听",
    next_step: "下一步",
    rules_passed: "已满足 {have}/{n}",
    back: "全部会话",
    show_all: "全部展开（{n}）",
    show_fewer: "收起",
    latest: "跳到最新",
    lang_zh: "中文（zh）",
    lang_en: "英文（en）",
    lv_ERROR: "错误",
    lv_WARN: "警告",
    lv_INFO: "提示",
    e_active_rival: "这条回复已经有一个生效中的改写，请用“替换”",
    e_illegal_transition: "它的状态已经变了，不能再这样操作",
    e_unknown_candidate: "找不到这条提议",
    e_cross_site: "拒绝了来自其他网站的请求",
    e_foreign_origin: "拒绝了来自其他来源的请求",
  },
};

// Fixed English phrases the server sends (policy verdicts, ledger reasons,
// refusals), in Chinese. Anything else, model-written text included, stays as it is.
const SERVER_ZH = [
  [/^automatic promotion disabled \(PROMOTE_AUTO_ENABLED\)$/, () => "自动晋升已关闭（PROMOTE_AUTO_ENABLED）"],
  [/^state is (\w+), not proposed$/, (m) => "状态是“" + t("s_" + m[1], null, m[1]) + "”，不是待确认"],
  [/^compatible evidence disagrees — left for review$/, () => "有证据和它相反，留给人来看"],
  [/^a conflicting candidate exists — left for review$/, () => "有和它冲突的提议，留给人来看"],
  [/^\S+ is promotable only by a person: nothing that supports one classifies strong \((\d+) supporting\)$/,
    (m) => "这一类只能由人来采纳：支持它的证据都算不上强证据（" + m[1] + " 条支持）"],
  [/^(\d+)\/(\d+) strong events \((\d+) supporting\)$/, (m) => "强证据 " + m[1] + "/" + m[2] + "（" + m[3] + " 条支持）"],
  [/^(\d+)\/(\d+) compatible events$/, (m) => "一致的证据 " + m[1] + "/" + m[2]],
  [/^(\d+)\/(\d+) distinct speakers \((\d+) events, but corroboration means people\)$/,
    (m) => "不同的人 " + m[1] + "/" + m[2] + "（有 " + m[3] + " 条证据，但佐证要靠不同的人）"],
  [/^(\d+) compatible events, (\d+) strong$/, (m) => m[1] + " 条一致的证据，其中 " + m[2] + " 条是强证据"],
  [/^answered by (\S+)$/, (m) => "已由 " + m[1] + " 解决"],
  [/^replaced by (\S+)$/, (m) => "已被 " + m[1] + " 替换"],
  [/^(promote|reject|rollback|superseded) by operator$/, () => "在命令行操作"],
  [/^the person accepted the retry instead$/, () => "对方接受了它的重说"],
  [/^user accepted the bot's retry$/, () => "对方接受了它的重说"],
  [/^the person it was for disagreed$/, () => "被回复的人不同意"],
  [/^the admin disagreed$/, () => "管理员不同意"],
  [/^not in ACCESS_GROUPS, which lists (\S+) groups$/, (m) => "不在 ACCESS_GROUPS 里（那里列了 " + m[1] + " 的群）"],
  [/^ACCESS_GROUPS has no (\S+) entries and the connector did not filter \(prefiltered=false\)$/,
    (m) => "ACCESS_GROUPS 里没有 " + m[1] + " 的条目，连接器也没有筛选（prefiltered=false）"],
  [/^not in ADMIN_IDS or ACCESS_DM_USERS, one of which every QQ DM needs$/,
    () => "不在 ADMIN_IDS 或 ACCESS_DM_USERS 里，QQ 私聊必须在其中之一"],
  [/^not in ADMIN_IDS or ACCESS_DM_USERS, which lists (\S+) users$/,
    (m) => "不在 ADMIN_IDS 或 ACCESS_DM_USERS 里（那里列了 " + m[1] + " 的用户）"],
  [/^ACCESS_DM_USERS has no (\S+) entries and the connector did not filter \(prefiltered=false\)$/,
    (m) => "ACCESS_DM_USERS 里没有 " + m[1] + " 的条目，连接器也没有筛选（prefiltered=false）"],
  [/^the QQ webhook carries bare QQ ids only$/, () => "QQ 的 webhook 只接收不带前缀的 QQ 号"],
];

function serverText(text) {
  const s = String(text || "");
  if (view.lang !== "zh") return s;
  for (const [re, make] of SERVER_ZH) {
    const m = re.exec(s);
    if (m) return make(m);
  }
  return s;
}

// A label with its colon, ready for the value: a Chinese "：" takes no space after it.
function lead(key) {
  const s = t(key);
  return s.endsWith("：") ? s : s + " ";
}

function colon() { return view.lang === "zh" ? "：" : ": "; }

// "a; b" and "a, b" in English, "a；b" and "a，b" in Chinese.
function joined(items, strong) {
  if (view.lang === "zh") return items.join(strong ? "；" : "，");
  return items.join(strong ? "; " : ", ");
}

// `command` in a sentence is shown as code; the rest stays text.
function rich(text) {
  return String(text).split("`").map((part, i) => (i % 2 ? h("code", { text: part }) : part));
}

const REASONS = {
  "below the trigger count": "r_below",
  "sleep window": "r_sleep",
  "spontaneous skip": "r_skip",
  "passed": "r_passed",
  "addressed": "r_addressed",
  "sticky call": "r_sticky",
  "followup window": "r_followup",
  "trigger count": "r_trigger",
  "first appearance": "r_first",
};

const POLL_MS = 10000;

const view = {
  lang: "en",
  langOverride: load("personagent.lang"),
  theme: load("personagent.theme") || "auto",
  status: null,
  convs: null,
  detail: null,
  selected: null,
  clockSkew: 0,
  shown: { hints: "", status: "", convs: "", detail: "", welcome: "" },
  // Disclosures a redraw must not close again.
  open: new Set(),
  // Set when someone goes back to the list on a phone: no auto-reopen.
  closed: false,
  armed: null,
  busy: false,
  down: false,
  failure: null,
  updatedAt: 0,
};

function load(key) {
  try { return window.localStorage.getItem(key); } catch (e) { return null; }
}

function save(key, value) {
  try {
    if (value == null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch (e) { /* private window: the choice lasts for this page only */ }
}

function t(key, params, fallback) {
  const table = STRINGS[view.lang] || STRINGS.en;
  // "1 note", not "1 notes": a language with a singular gives it as key_1.
  if (params && params.n === 1 && (key + "_1") in table) key += "_1";
  const text = key in table ? table[key] : key in STRINGS.en ? STRINGS.en[key] : fallback != null ? fallback : key;
  // Commands are spelled the way this install runs them (`personagent`, `python -m persona_agent`, ...).
  const all = Object.assign({ cli: (view.status && view.status.cli) || "personagent" }, params || {});
  return text.replace(/\{(\w+)\}/g, (_, name) => (name in all ? String(all[name]) : ""));
}

function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  if (props) {
    for (const [name, value] of Object.entries(props)) {
      if (value == null || value === false) continue;
      if (name === "class") el.className = value;
      else if (name === "text") el.textContent = value;
      else if (name.startsWith("on")) el.addEventListener(name.slice(2), value);
      else el.setAttribute(name, value === true ? "" : String(value));
    }
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

function replace(el, ...kids) {
  el.replaceChildren(...kids.flat(Infinity).filter((k) => k != null && k !== false));
}

// ------------------------------------------------------------- time ----

function nowS() { return Date.now() / 1000 + view.clockSkew; }

function ago(ts) {
  if (!ts) return t("never");
  const s = Math.max(0, nowS() - ts);
  if (s < 45) return t("just_now");
  if (s < 3600) return t("min_ago", { n: Math.max(1, Math.round(s / 60)) });
  if (s < 86400) return t("h_ago", { n: Math.round(s / 3600) });
  return t("d_ago", { n: Math.round(s / 86400) });
}

function locale() { return view.lang === "zh" ? "zh-CN" : "en-US"; }

function stamp(ts) {
  if (!ts) return "";
  return new Date(ts * 1000).toLocaleString(locale(), {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function duration(s) {
  s = Math.max(0, Math.floor(s));
  const d = Math.floor(s / 86400), hr = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d) return t("dur_dh", { d, h: hr });
  if (hr) return t("dur_hm", { h: hr, m });
  return t("dur_m", { m });
}

function when(ts) {
  if (!ts) return null;
  return h("time", { title: stamp(ts), datetime: new Date(ts * 1000).toISOString() }, ago(ts));
}

// -------------------------------------------------------------- api ----

// A thrown error with a `status` is the service answering; without one, nothing answered.
async function api(path, options) {
  const res = await fetch(path, Object.assign({ credentials: "same-origin", cache: "no-store" }, options || {}));
  let body = {};
  try { body = await res.json(); } catch (e) { body = {}; }
  if (!res.ok) {
    const err = new Error(body.error || res.statusText || String(res.status));
    err.status = res.status;
    err.code = body.code || "";
    throw err;
  }
  return body;
}

function failureOf(err) {
  if (err && err.status) return { status: err.status, code: err.code || "", message: err.message || "" };
  return null;
}

async function refresh() {
  try {
    const [status, convs] = await Promise.all([
      api("api/dashboard/status"),
      api("api/dashboard/conversations"),
    ]);
    view.down = false;
    view.failure = null;
    view.clockSkew = status.now - Date.now() / 1000;
    view.status = status;
    view.convs = convs.conversations || [];
    // On a wide screen the newest chat opens by itself; a phone starts at the list.
    if (!view.selected && !view.closed && view.convs.length
        && (view.convs.length === 1 || window.matchMedia("(min-width: 901px)").matches)) {
      select(view.convs[0].id, false);
    }
    if (view.selected) await refreshDetail();
    view.updatedAt = Date.now();
  } catch (e) {
    view.failure = failureOf(e);
    view.down = !view.failure;
  }
  render();
}

async function refreshDetail() {
  if (!view.selected) { view.detail = null; return; }
  try {
    view.detail = await api("api/dashboard/conversation?id=" + encodeURIComponent(view.selected));
  } catch (e) {
    view.detail = null;
  }
}

// ----------------------------------------------------------- render ----

function render() {
  const lang = view.langOverride || (view.status && view.status.lang) || "en";
  view.lang = STRINGS[lang] ? lang : "en";
  document.documentElement.lang = view.lang === "zh" ? "zh-CN" : "en";
  document.title = t("title");
  renderTop();
  // A first visit with no chat yet: the setup steps live in the welcome card.
  let hints = hintList();
  const fresh = Array.isArray(view.convs) && !view.convs.length && !view.down && !view.failure;
  const steps = fresh ? hints.find((x) => x.id === "none") || null : null;
  if (steps) hints = hints.filter((x) => x !== steps);
  // Hints are alerts: redrawn only when what they say changes.
  const hintKey = JSON.stringify(hints);
  if (hintKey !== view.shown.hints) {
    view.shown.hints = hintKey;
    renderHints(hints);
  }
  const welcomeKey = JSON.stringify([view.lang, fresh, steps]);
  if (welcomeKey !== view.shown.welcome) {
    view.shown.welcome = welcomeKey;
    renderWelcome(fresh, steps);
  }
  const statusKey = JSON.stringify([view.lang, view.down, view.failure, view.status]);
  if (statusKey !== view.shown.status) {
    view.shown.status = statusKey;
    renderOverview();
  }
  const convKey = JSON.stringify([view.lang, view.convs, view.selected]);
  if (convKey !== view.shown.convs) {
    view.shown.convs = convKey;
    keepFocus(renderConversations);
  }
  const detailKey = JSON.stringify([view.lang, view.selected, view.detail, view.convs && view.convs.length]);
  if (detailKey !== view.shown.detail && !view.armed && !view.busy) {
    view.shown.detail = detailKey;
    keepFocus(renderDetail);
  }
  renderFooter();
}

// A redraw replaces elements; the keyboard stays on the control with the same
// data-key (a conversation, a button, a disclosure), wherever it moved.
function keepFocus(draw) {
  const was = document.activeElement;
  const holder = was && was !== document.body && was.closest ? was.closest("[data-key]") : null;
  const key = holder ? holder.getAttribute("data-key") : null;
  draw();
  if (!key || (was.isConnected && document.activeElement === was)) return;
  const next = [...document.querySelectorAll("[data-key]")].find((el) => el.getAttribute("data-key") === key);
  if (next) next.focus({ preventScroll: true });
}

function renderTop() {
  const st = view.status;
  const pill = document.getElementById("state-pill");
  if (view.down || view.failure) {
    pill.className = "pill err";
    pill.textContent = t(view.down ? "state_down" : "state_error");
  } else if (st) {
    pill.className = "pill " + (st.agent === "ready" ? "ok" : st.agent === "off" ? "off" : "err");
    pill.textContent = t("state_" + st.agent);
  }
  document.getElementById("persona-name").textContent = st && st.persona ? st.persona.name || "" : "";
  document.getElementById("lang-toggle").textContent = t("other_lang");
  const theme = document.getElementById("theme-toggle");
  const themeName = t("theme_" + view.theme);
  if (theme.textContent !== themeName) {
    replace(theme, icon(view.theme === "auto" ? "auto" : view.theme === "dark" ? "moon" : "sun"),
      h("span", { class: "btn-label", text: themeName }));
    theme.title = themeName;
  }
  document.getElementById("conv-title").textContent = t("conversations");
}

function hintList() {
  const out = [];
  if (view.down) {
    out.push({ level: "error", title: t("state_down"), items: [t("down")] });
    return out;
  }
  const f = view.failure;
  if (f) {
    out.push(f.status === 401
      ? { level: "error", title: t("h_auth_t"), items: [t("h_auth")] }
      : { level: "error", title: t("h_error_t", { status: f.status }), items: [f.message + (f.code ? (view.lang === "zh" ? "（" + f.code + "）" : " (" + f.code + ")") : "")] });
    return out;
  }
  const st = view.status;
  if (!st) return out;
  const a = st.activity || {};
  if (st.agent === "off") out.push({ level: "error", title: t("h_off_t"), items: [t("h_off")] });
  if (st.agent === "no_key") out.push({ level: "error", title: t("h_nokey_t"), items: [t("h_nokey")] });
  if (st.agent === "off") return out;
  if (!a.received) {
    out.push({
      id: "none",
      level: "warn",
      title: t("h_none_t"),
      ordered: true,
      items: [
        t("h_none_url", { url: window.location.origin }),
        a.connector_token ? t("h_none_token_set") : t("h_none_token_blank"),
        t("h_none_access"),
        t("h_none_doctor"),
      ],
    });
  } else if (a.refused && a.refused.length) {
    out.push({
      level: "warn",
      title: t("h_refused_t"),
      items: a.refused.map((r) => r.conversation + colon() + serverText(r.reason)),
    });
  }
  if (a.received && !a.spoke && st.agent === "ready") {
    out.push({
      level: "info",
      title: t("h_quiet_t"),
      items: [t("h_quiet", { name: a.persona_name || "?", n: a.trigger_count })],
    });
  }
  return out;
}

function renderHints(hints) {
  const box = document.getElementById("hints");
  replace(box, hints.map((hint) => h("div", { class: "hint " + hint.level, role: hint.level === "info" ? null : "alert" },
    h("span", { class: "hint-mark", "aria-hidden": "true" }, icon(hint.level === "info" ? "info" : "alert")),
    h("div", { class: "hint-body" },
      h("h3", { text: hint.title }),
      h(hint.ordered ? "ol" : "ul", null, hint.items.map((item) => h("li", null, rich(item))))))));
}

function renderWelcome(fresh, steps) {
  const box = document.getElementById("welcome");
  box.hidden = !fresh;
  if (!fresh) { replace(box); return; }
  replace(box, h("div", { class: "welcome-card" },
    h("figure", { class: "frame" },
      h("img", { src: "dashboard/empty-chats.webp", alt: "", width: 640, height: 384 })),
    h("div", { class: "welcome-text" },
      h("h2", { text: t("no_convs_t") }),
      h("p", { class: "lede", text: t("no_convs") }),
      steps ? h("div", { class: "steps" },
        h("p", { class: "eyebrow", text: t("next_step") }),
        h("h3", { text: steps.title }),
        h("ol", null, steps.items.map((item) => h("li", null, rich(item))))) : null)));
}

// ------------------------------------------------------------- icons ----

const SVG_NS = "http://www.w3.org/2000/svg";
const ICONS = {
  person: "M12 11.5a3.8 3.8 0 1 0 0-7.6 3.8 3.8 0 0 0 0 7.6zM4.8 20c.9-3.5 3.8-5.4 7.2-5.4s6.3 1.9 7.2 5.4",
  group: "M9 11a3.4 3.4 0 1 0 0-6.8A3.4 3.4 0 0 0 9 11zM2.8 19.5c.7-3.1 3.1-4.9 6.2-4.9s5.5 1.8 6.2 4.9M15.6 4.5a3.3 3.3 0 0 1 0 6.3M17.6 14.7c1.9.6 3.2 2.2 3.6 4.6",
  pin: "M9.5 3.8h5l-.8 5 3 3.2H7.3l3-3.2-.8-5zM12 12v8.2",
  leaf: "M5.5 18.5C5.5 10.8 10 6 18.8 5.2 18.2 13.6 13.4 18.5 5.5 18.5zM5.5 18.5l7.2-7.2",
  up: "M12 19V5.5M6.5 11 12 5.5l5.5 5.5",
  down: "M12 5v13.5M6.5 13l5.5 5.5 5.5-5.5",
  chev: "M9.5 6l6 6-6 6",
  back: "M14.5 6l-6 6 6 6",
  check: "M5.5 12.5l4.2 4.2 8.8-9.2",
  clock: "M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM12 7.5V12l3 2",
  turn: "M6 5v6.5A4.5 4.5 0 0 0 10.5 16H19M15 12l4 4-4 4",
  next: "M4.5 12h15M14 6.5l5.5 5.5-5.5 5.5",
  star: "M12 4.5l2.2 4.8 5.2.6-3.9 3.5 1.1 5.1-4.6-2.6-4.6 2.6 1.1-5.1-3.9-3.5 5.2-.6z",
  cross: "M7 7l10 10M17 7 7 17",
  alert: "M12 4.2 20.5 19H3.5zM12 10v4M12 16.6v.2",
  info: "M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM12 11v5.5M12 7.8v.2",
  sun: "M12 15.8a3.8 3.8 0 1 0 0-7.6 3.8 3.8 0 0 0 0 7.6zM12 3v1.8M12 19.2V21M5.6 5.6l1.3 1.3M17.1 17.1l1.3 1.3M3 12h1.8M19.2 12H21M5.6 18.4l1.3-1.3M17.1 6.9l1.3-1.3",
  moon: "M19.8 14.6A8 8 0 0 1 9.4 4.2a8 8 0 1 0 10.4 10.4z",
  auto: "M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM12 3.5v17M12 7h4.5M12 11h7.5M12 15h6",
};

function icon(name, cls) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.setAttribute("class", "icon" + (cls ? " " + cls : ""));
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", ICONS[name] || "");
  svg.append(path);
  return svg;
}

// ------------------------------------------------------------ status ----

function card(title, extraClass, ...body) {
  return h("article", { class: "card" + (extraClass ? " " + extraClass : "") },
    h("h2", { class: "card-title", text: title }), body);
}

function kv(pairs) {
  return h("dl", { class: "kv" }, pairs.filter(Boolean).map(([k, v]) => [h("dt", { text: k }), h("dd", null, v)]));
}

function renderOverview() {
  const bar = document.getElementById("statusbar");
  const st = view.status;
  bar.hidden = !st;
  if (!st) return;
  const persona = st.persona || {};

  const service = card(t("service"), "",
    kv([
      [t("version"), st.version],
      [t("uptime"), duration(st.uptime_s)],
      [t("home"), h("span", { class: "mono", text: st.home })],
      [t("language"), t(st.lang === "zh" ? "lang_zh" : "lang_en")],
      [t("outbox"), st.outbox ? t("on") : t("off")],
    ]));

  const lineageText = persona.revisions > 1
    ? t("lineage_n", { n: persona.revisions })
    : t("lineage_1");
  const sourceNote = persona.source === "example" ? t("source_example")
    : persona.source === "builtin" ? t("source_builtin") : "";
  const personaCard = card(t("persona"), "",
    h("p", { class: "persona-name", text: persona.name || t("unnamed") }),
    kv([
      persona.file ? [t("persona_file"), [h("span", { class: "mono", text: persona.file }),
        sourceNote ? h("div", { class: "note", text: sourceNote }) : null]] : null,
      st.agent !== "off" ? [t("lineage"), lineageText] : null,
      persona.version ? [t("persona_version"), h("span", { class: "mono", text: persona.version })] : null,
    ]));

  const byModel = new Map();
  for (const m of st.models || []) {
    if (!byModel.has(m.name)) byModel.set(m.name, []);
    byModel.get(m.name).push(t("role_" + m.role, null, m.role));
  }
  const modelsCard = card(t("models"), "",
    byModel.size
      ? h("ul", { class: "rows" }, [...byModel].map(([name, roles]) => h("li", null,
        h("div", { class: "mono model", text: name }),
        h("div", { class: "note", text: roles.join(view.lang === "zh" ? "、" : " · ") }))))
      : h("p", { class: "empty", text: t("no_models") }));

  const connectors = st.connectors || [];
  const connectorsCard = card(t("connectors"), "wide",
    connectors.length
      ? h("ul", { class: "rows" }, connectors.map((c) => h("li", null,
        h("div", { class: "row-line" },
          h("span", { class: "dot " + (c.pulling ? "on" : "off"), "aria-hidden": "true" }),
          h("span", { class: "mono", title: c.id || null, text: c.id ? shortId(c.id, 24) : t("unnamed_connector") }),
          c.platforms.map((p) => h("span", { class: "chip accent", text: p })),
          c.capabilities.map((cap) => h("span", { class: "chip", text: cap }))),
        h("div", { class: "note" },
          [c.last_event ? t("last_event", { t: ago(c.last_event) }) : t("no_event"),
            t("convs_n", { n: c.conversations }),
            c.pulling ? t("pulling") : (c.capabilities.includes("outbox") ? t("not_pulling") : null)]
            .filter(Boolean).join(" · ")))))
      : h("p", { class: "empty", text: t("no_connectors") }));

  const findings = st.preflight || [];
  const checksCard = card(t("checks"), "",
    findings.length
      ? h("ul", { class: "rows" }, findings.map((f) => h("li", { class: "finding" },
        h("span", { class: "chip " + levelClass(f.level), text: t("lv_" + f.level, null, f.level) }),
        h("span", { class: "mono", text: f.key }),
        h("span", { class: "detail", text: f.detail }))))
      : h("p", { class: "empty", text: t("no_findings") }));

  // The one-line summary; the cards open under it.
  const names = [...byModel.keys()];
  const roles = (st.models || []).length;
  const worst = findings.some((f) => f.level === "ERROR") ? "err"
    : findings.some((f) => f.level === "WARN") ? "warn" : "";
  const first = connectors[0];
  const facts = [
    names.length ? h("span", { class: "fact" },
      h("span", { class: "mono", text: joined(names) }),
      h("span", { class: "soft", text: " · " + t("roles_n", { n: roles }) })) : null,
    first ? h("span", { class: "fact" },
      h("span", { class: "dot " + (first.pulling ? "on" : "off"), "aria-hidden": "true" }),
      h("span", { class: "mono", title: first.id || null, text: first.id ? shortId(first.id, 22) : t("unnamed_connector") }),
      h("span", { class: "soft", text: " · " + joined(first.platforms)
        + (connectors.length > 1 ? " +" + (connectors.length - 1) : "") }))
      : h("span", { class: "fact" }, h("span", { class: "dot off", "aria-hidden": "true" }), t("no_connector_short")),
    h("span", { class: "fact", text: t(st.outbox ? "outbox_on" : "outbox_off") }),
    h("span", { class: "fact", text: t("up", { t: duration(st.uptime_s) }) }),
    h("span", { class: "fact mono", text: "v" + st.version }),
    h("span", { class: "fact" + (worst ? " " + worst : "") },
      findings.length ? t("chk_n", { n: findings.length }) : t("chk_ok")),
  ];
  replace(document.getElementById("facts"), facts);
  replace(document.getElementById("status-more"), t("status_details"), icon("chev", "chev"));
  replace(document.getElementById("overview"), service, personaCard, modelsCard, connectorsCard, checksCard);
}

function levelClass(level) {
  return level === "ERROR" ? "err" : level === "WARN" ? "warn" : "";
}

function shortId(id, n) {
  return id.length > n ? id.slice(0, n - 1) + "…" : id;
}

// ----------------------------------------------------- conversations ----

function renderConversations() {
  const list = document.getElementById("conv-list");
  const convs = view.convs || [];
  const section = document.querySelector(".convs");
  section.classList.toggle("none", !convs.length);
  section.classList.toggle("chat-open", !!view.selected);
  if (!convs.length) {
    replace(list);
    return;
  }
  replace(list, convs.map((c) => h("button", {
    type: "button",
    class: "conv",
    "data-key": "conv:" + c.id,
    "aria-current": c.id === view.selected ? "true" : "false",
    onclick: () => select(c.id, true),
  },
  h("span", { class: "avatar " + (c.kind === "dm" ? "dm" : "group"), "aria-hidden": "true" },
    icon(c.kind === "dm" ? "person" : "group")),
  h("span", { class: "conv-main" },
    h("span", { class: "conv-top" },
      h("span", { class: "id", title: c.id, text: label(c) }),
      h("span", { class: "ago", text: c.last_activity ? t("last_activity", { t: ago(c.last_activity) }) : t("never") })),
    h("span", { class: "conv-sub" },
      h("span", { class: "plat", text: c.platform }),
      h("span", { text: c.kind === "dm" ? t("dm") : t("group") }),
      c.memories ? h("span", { text: t("notes_n", { n: c.memories }) }) : null),
    c.pending || c.learned ? h("span", { class: "badges" },
      c.pending ? h("span", { class: "badge wait", text: t("pending_n", { n: c.pending }) }) : null,
      c.learned ? h("span", { class: "badge learned" }, icon("leaf"), t("learned_n", { n: c.learned })) : null) : null))));
}

function select(id, scroll) {
  view.closed = false;
  if (view.selected === id) return;
  view.selected = id;
  view.detail = null;
  view.armed = null;
  try { history.replaceState(null, "", "#c=" + encodeURIComponent(id)); } catch (e) { /* ignore */ }
  refreshDetail().then(() => {
    render();
    if (scroll && narrow()) {
      const pane = document.getElementById("detail");
      pane.scrollIntoView({ block: "start" });
      const head = pane.querySelector("h2");
      if (head) head.focus({ preventScroll: true });
    }
  });
  render();
}

// On a phone the list and the chat take turns; this goes back to the list.
function back() {
  const was = view.selected;
  view.selected = null;
  view.detail = null;
  view.armed = null;
  view.closed = true;
  try { history.replaceState(null, "", window.location.pathname + window.location.search); } catch (e) { /* ignore */ }
  render();
  window.scrollTo(0, 0);
  const item = [...document.querySelectorAll(".conv .id")].find((el) => el.title === was);
  if (item) item.closest(".conv").focus();
}

function narrow() {
  return window.matchMedia("(max-width: 900px)").matches;
}

function label(conv) {
  let id = conv.id;
  if (id.startsWith("private:")) id = id.slice(8);
  if (id.startsWith(conv.platform + ":")) id = id.slice(conv.platform.length + 1);
  return id || conv.id;
}

// -------------------------------------------------------------- chat ----

function renderDetail() {
  const box = document.getElementById("detail");
  const d = view.detail;
  if (!view.selected || !d) {
    const none = view.convs && !view.convs.length;
    replace(box, h("div", { class: "placeholder" },
      h("figure", { class: "frame small" },
        h("img", { src: "dashboard/listening.webp", alt: "", width: 560, height: 373 })),
      h("strong", { text: none ? t("no_convs_t") : t("pick_t") }),
      h("span", { text: none ? t("no_convs") : t("pick") })));
    watchLatest(box);
    return;
  }
  const conv = (view.convs || []).find((c) => c.id === d.id) || {};
  const stream = buildStream(d);
  replace(box,
    chatHead(d, conv),
    notesStrip(d),
    approvals(d, stream.bubbleOf),
    chatStream(d, stream),
    composer(d));
  watchLatest(box);
}

function chatHead(d, conv) {
  const quiet = d.decisions.filter((r) => !r.spoke).reduce((n, r) => n + (r.count || 1), 0);
  const spoke = d.decisions.filter((r) => r.spoke).length;
  const totals = d.totals || {};
  const learnedN = totals.learned || d.learned.length;
  const waitingN = totals.pending || d.pending.length;
  const stat = (cls, n, text) => h("li", { class: "stat" + (n ? " " + cls : ""), text });
  return h("div", { class: "chat-head" },
    h("button", { type: "button", class: "back ghost", "data-key": "back", onclick: back },
      icon("back"), h("span", { text: t("back") })),
    h("div", { class: "chat-id" },
      h("span", { class: "avatar big " + (d.kind === "dm" ? "dm" : "group"), "aria-hidden": "true" },
        icon(d.kind === "dm" ? "person" : "group")),
      h("div", { class: "chat-name" },
        h("h2", { tabindex: "-1", "data-key": "head", title: d.id, text: label(d) }),
        h("div", { class: "line" },
          h("span", { class: "chip accent", text: d.platform }),
          h("span", { class: "chip", text: d.kind === "dm" ? t("dm") : t("group") }),
          h("span", { class: "mono full-id", text: d.id }),
          conv.last_activity ? h("span", { text: t("last_activity", { t: ago(conv.last_activity) }) }) : null))),
    h("ul", { class: "stats", "aria-label": t("decisions") },
      stat("spoke", spoke, t("spoke_n", { n: spoke })),
      stat("quiet", quiet, t("quiet_n", { n: quiet })),
      stat("learned", learnedN, t("learned_n", { n: learnedN })),
      stat("wait", waitingN, t("pending_n", { n: waitingN }))));
}

function notesStrip(d) {
  const items = [];
  if (d.core_note) {
    items.push(h("li", { class: "memo core" },
      h("span", { class: "by", text: t("core_note") }),
      h("span", { class: "text", text: d.core_note })));
  }
  for (const m of d.memories) {
    items.push(h("li", { class: "memo" },
      h("span", { class: "text", text: m.text }),
      h("span", { class: "by" },
        (m.auto ? t("by_auto") : (m.by || t("by_admin"))) + " · ", when(m.time))));
  }
  return h("section", { class: "pinned" },
    h("h3", { class: "strip-title" }, icon("pin"), t("memories"),
      d.memories.length ? h("span", { class: "count", text: String(d.memories.length) }) : null),
    items.length ? h("ul", { class: "memos" }, items) : h("p", { class: "empty", text: t("no_memories") }));
}

function more(d, group, title) {
  const total = (d.totals || {})[group] || d[group].length;
  if (total <= d[group].length) return null;
  const text = t("shown_of", { shown: d[group].length, n: total });
  return h("p", { class: "empty" }, title ? h("strong", { text: title + colon() }) : null, text);
}

function approvals(d, bubbleOf) {
  const total = (d.totals || {}).pending || d.pending.length;
  if (!d.pending.length) {
    return h("p", { class: "all-clear" }, icon("check"), t("no_pending"));
  }
  // More than a few: one line each until someone asks for the full cards.
  const long = d.pending.length > QUEUE_AFTER;
  const all = !long || view.open.has(ALL_KEY);
  const toggle = long ? h("button", {
    type: "button", class: "link show-all", "data-key": ALL_KEY,
    "aria-expanded": all ? "true" : "false",
    onclick: () => {
      if (view.open.has(ALL_KEY)) view.open.delete(ALL_KEY); else view.open.add(ALL_KEY);
      keepFocus(renderDetailNow);
    },
  }, t(all ? "show_fewer" : "show_all", { n: d.pending.length }), icon(all ? "up" : "down")) : null;
  return h("section", { class: "approvals", "aria-labelledby": "approvals-title" },
    h("div", { class: "approvals-head" },
      h("h3", { id: "approvals-title" },
        h("span", { class: "pulse", "aria-hidden": "true" }), t("pending"),
        h("span", { class: "count", text: String(total) })),
      h("span", { class: "spacer" }),
      toggle,
      h("span", { class: "vignette" },
        h("img", { src: "dashboard/learned-notebook.webp", alt: "", width: 320, height: 210 }))),
    all ? d.pending.map((c) => pendingItem(c, bubbleOf[c.id]))
      : h("ul", { class: "queue" }, d.pending.map((c) => queueRow(c, bubbleOf[c.id]))),
    more(d, "pending"));
}

const QUEUE_AFTER = 3;
const ALL_KEY = "approvals:all";

// One proposal on one line: said -> better, the meter, the buttons.
function queueRow(c, bubbleId) {
  const isPair = c.type === "preference_pair" && c.better;
  const cl = c.checklist;
  const full = isPair ? c.reply + " → " + c.better : c.reply;
  return h("li", { class: "q-row", id: "p-" + c.id, tabindex: "-1", "data-key": "p:" + c.id },
    h("span", { class: "q-kind", text: t("t_" + c.type, null, c.type) }),
    h("span", { class: "q-text", title: full },
      isPair ? [
        h("span", { class: "sr-only", text: t("it_said") + colon() }),
        h("span", { class: "q-said", text: c.reply }),
        h("span", { class: "q-arrow", "aria-hidden": "true" }, icon("next")),
        h("span", { class: "sr-only", text: t("better") + colon() }),
        h("span", { class: "q-better", text: c.better }),
      ] : h("span", { class: "q-keep", text: c.reply })),
    cl ? h("span", { class: "q-meter" }, h("span", { class: "sr-only", text: t("checklist") + colon() }), checkBar(cl, true)) : null,
    h("span", { class: "q-end" },
      bubbleId ? h("button", {
        type: "button", class: "link icon-only", "data-key": "jump:" + c.id,
        title: t("show_in_chat"), "aria-label": t("show_in_chat"), onclick: () => jump("b-" + bubbleId),
      }, icon("down")) : null,
      c.actions.length ? renderActions(c) : null));
}

function pendingItem(c, bubbleId) {
  const isPair = c.type === "preference_pair" && c.better;
  const cl = c.checklist;
  // At a glance: the swap, how far it is, who reacted, the buttons; the rest opens.
  return h("article", { class: "proposal", id: "p-" + c.id, tabindex: "-1", "data-key": "p:" + c.id },
    candHead(c, bubbleId ? h("button", {
      type: "button", class: "link", "data-key": "jump:" + c.id, onclick: () => jump("b-" + bubbleId),
    }, t("show_in_chat"), icon("down")) : null),
    h("div", { class: "swap" },
      sayBubble(isPair ? t("it_said") : t("reply"), c.reply, isPair ? "x-said" : "x-keep"),
      isPair ? h("span", { class: "swap-arrow", "aria-hidden": "true" }, icon("next")) : null,
      isPair ? sayBubble(t("better"), c.better, "x-better") : null),
    cl ? checkSummary(cl) : null,
    voices(c),
    rivals(c),
    h("div", { class: "proposal-foot" },
      c.actions.length ? renderActions(c) : null,
      disclosure(c.id + ":why", h("span", { text: t("why_detail") }),
        h("div", { class: "proposal-grid" },
          h("div", { class: "exchange" }, contextBlock(c), evidenceBlock(c)),
          h("div", { class: "why" }, cl ? renderChecklist(cl) : null, historyBlock(c))))));
}

function checkBar(cl, short) {
  const scored = cl.rules.filter((rule) => rule.id !== "same_chat");
  const passed = scored.filter((rule) => rule.ok).length;
  const full = t("rules_passed", { have: passed, n: scored.length });
  return [
    h("span", { class: "bar", "aria-hidden": "true" },
      scored.map((rule) => h("span", { class: "seg" + (rule.ok ? " on" : "") }))),
    short ? [h("span", { class: "tally", "aria-hidden": "true", title: full, text: passed + "/" + scored.length }),
      h("span", { class: "sr-only", text: full })]
      : h("span", { class: "tally", text: full }),
  ];
}

function waitingText(cl) {
  return cl.waiting_for.length
    ? joined(cl.waiting_for.map((w) => t("w_" + w, null, w)), true)
    : (cl.promote ? t("w_ready") : "");
}

function checkSummary(cl) {
  const waiting = waitingText(cl);
  return h("div", { class: "glance" },
    h("span", { class: "glance-bar" }, h("span", { class: "sr-only", text: t("checklist") + colon() }), checkBar(cl)),
    waiting ? h("span", { class: "glance-wait" }, h("strong", { text: lead("waiting_for") }), waiting) : null);
}

function voices(c) {
  if (!c.evidence.length) return null;
  return h("ul", { class: "voices", "aria-label": t("evidence") }, c.evidence.map((e) => {
    const who = e.speaker || "?";
    return h("li", { class: "voice" + (e.counts ? "" : " not-counted") },
      h("span", { class: "face small " + tone(who), "aria-hidden": "true", text: initial(who) }),
      h("span", { class: "who", text: who }),
      h("span", { class: "kind", text: e.reaction_type && e.kind === "reaction"
        ? t("rt_" + e.reaction_type, null, e.reaction_type) : t("k_" + e.kind, null, e.kind) }),
      h("span", { class: "chip " + (e.strength === "strong" ? "strong" : "weak"), text: t("st_" + e.strength, null, e.strength) }));
  }));
}

function candHead(c, extra) {
  return h("div", { class: "cand-head" },
    h("span", { class: "title", text: t("t_" + c.type, null, c.type) }),
    h("span", { class: "chip " + stateClass(c.state), text: t("s_" + c.state, null, c.state) }),
    h("span", { class: "when" }, when(c.created)),
    h("span", { class: "spacer" }),
    extra,
    h("span", { class: "mono when", title: c.id, text: c.id.slice(0, 12) }));
}

function sayBubble(caption, text, cls) {
  return h("div", { class: "say " + cls },
    h("span", { class: "caption" }, cls === "x-better" ? icon("turn") : null, caption),
    h("p", { class: "bubble", text }));
}

function contextBlock(c) {
  if (!c.context.length) return null;
  const me = personaName();
  return h("div", { class: "context" },
    h("p", { class: "sub", text: t("context") }),
    h("ol", { class: "transcript" }, c.context.map((line) => {
      const m = /^([^:：]{1,40})[:：]\s?(.*)$/.exec(line);
      const who = m ? m[1].trim() : "";
      return h("li", { class: who && who === me ? "me" : null },
        who ? h("span", { class: "who", text: who }) : null,
        h("span", { class: "text" }, memberText(m ? m[2] : line)));
    })));
}

function personaName() {
  return (view.status && view.status.persona && view.status.persona.name) || "";
}

function rivals(c) {
  return (c.replaces || []).map((rival) => h("div", { class: "waiting", text: t("rival", { text: rival.better }) }));
}

function evidenceBlock(c) {
  return h("div", { class: "evidence-block" },
    h("p", { class: "sub" }, t("evidence"),
      c.evidence.length ? h("span", { class: "count", text: String(c.evidence.length) }) : null),
    c.evidence.length ? h("ol", { class: "evidence" }, c.evidence.map(renderEvent))
      : h("p", { class: "empty", text: t("no_evidence") }),
    c.missing_evidence ? h("p", { class: "empty", text: t("missing_evidence", { n: c.missing_evidence }) }) : null);
}

function historyBlock(c) {
  if (!c.history.length) return null;
  return h("div", { class: "history-block" },
    h("p", { class: "sub", text: t("history") }),
    h("ul", { class: "history" }, c.history.map((row) => h("li", null,
      h("time", { title: stamp(row.ts), text: ago(row.ts) }), " · ",
      historyLine(row),
      row.reason ? " · " + serverText(row.reason) : ""))));
}

function historyLine(row) {
  const what = t("hs_" + row.state, null, row.state);
  const actor = row.actor || "?";
  const who = actor === "auto" || actor === "dashboard"
    ? t("by_" + actor + "_actor") : t("by_actor", { actor });
  if (view.lang !== "zh") return what + " " + who;
  return who + (actor === "auto" || actor === "dashboard" ? "" : " ") + what;
}

function stateClass(state) {
  return state === "promoted" ? "ok" : state === "proposed" ? "warn" : "";
}

const TONES = 4;

// A CJK nickname shares its first character (小美, 小林): its last one tells them apart.
function initial(name) {
  const chars = [...String(name || "?")];
  const last = chars[chars.length - 1];
  return /[\u3400-\u9fff]/.test(chars[0]) ? last : chars[0].toUpperCase();
}

function toneOf(name) {
  let n = 0;
  for (const ch of String(name || "")) n = (n * 31 + ch.codePointAt(0)) % 997;
  return n % TONES;
}

function tone(name) { return "tone-" + toneOf(name); }

function renderEvent(e) {
  const who = e.speaker || "?";
  return h("li", { class: "ev" + (e.counts ? "" : " not-counted") },
    h("span", { class: "face " + tone(who), "aria-hidden": "true", text: initial(who) }),
    h("div", { class: "ev-body" },
      h("div", { class: "ev-head" },
        h("span", { class: "who", text: who }),
        h("span", { class: "kind", text: t("k_" + e.kind, null, e.kind) + (e.reaction_type && e.kind === "reaction" ? " · " + t("rt_" + e.reaction_type, null, e.reaction_type) : "") }),
        h("span", { class: "chip " + (e.strength === "strong" ? "strong" : "weak"), text: t("st_" + e.strength, null, e.strength) }),
        h("span", { class: "when" }, when(e.ts))),
      e.said ? h("p", { class: "said" }, memberText(e.said)) : null,
      e.verdict ? h("div", { class: "verdict", text: lead("judge") + serverText(e.verdict) }) : null,
      h("div", { class: "verdict flags", text: [
        e.speaker_is_recipient ? t("aimed_at_them") : null,
        e.accepted ? null : t("dismissed"),
        e.counts ? null : t("not_counted"),
      ].filter(Boolean).join(" · ") })));
}

function renderChecklist(cl) {
  const items = cl.rules.map((rule) => {
    let text;
    if (rule.id === "same_chat") text = rule.on ? t("c_same_chat") : t("c_any_chat");
    else text = t("c_" + rule.id, { have: rule.have, need: rule.need }, rule.id);
    const info = rule.id === "same_chat";
    return h("li", { class: "check " + (info ? "info" : rule.ok ? "ok" : "no") },
      h("span", { class: "mark", "aria-hidden": "true" }, info ? null : icon(rule.ok ? "check" : "clock")),
      h("span", { class: "label" },
        info ? null : h("span", { class: "sr-only", text: (rule.ok ? t("passed") : t("not_yet")) + ": " }), text),
      rule.need ? meter(rule.have, rule.need) : null);
  });
  return h("div", { class: "checklist-block" },
    h("div", { class: "sub row" }, h("span", { text: t("checklist") }), checkBar(cl)),
    h("ul", { class: "checklist" }, items),
    h("div", { class: "verdict-line", text: lead("policy") + serverText(cl.verdict) }));
}

function meter(have, need) {
  const n = Math.min(Math.max(need, Math.min(have, 6)), 8);
  const dots = [];
  for (let i = 0; i < n; i++) dots.push(h("span", { class: "pip" + (i < have ? " on" : "") }));
  return h("span", { class: "meter", "aria-hidden": "true" }, dots);
}

function renderActions(c) {
  return h("div", { class: "actions" }, c.actions.map((action) => {
    const armed = view.armed && view.armed.id === c.id && view.armed.action === action;
    return h("button", {
      type: "button",
      class: "btn " + (armed ? "armed" : action === "promote" || action === "replace" ? "primary" : "danger"),
      "data-act": c.id + ":" + action,
      "data-key": "act:" + c.id + ":" + action,
      disabled: view.busy || null,
      onclick: () => act(c.id, action),
    }, armed ? t("confirm") : t("a_" + action));
  }));
}

// ----------------------------------------------------------- stream ----

function norm(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

// The log keeps 60 characters of what it said; a proposal keeps the reply.
function sameReply(excerpt, reply) {
  const e = norm(excerpt), r = norm(reply);
  if (!e || !r) return false;
  if (e === r) return true;
  if (e.endsWith("…")) {
    const head = e.slice(0, -1);
    return head.length > 0 && r.startsWith(head);
  }
  return false;
}

function matchDecision(c, rows) {
  let best = null, score = Infinity;
  for (const r of rows) {
    if (!r.spoke || !sameReply(r.excerpt, c.reply)) continue;
    // Said before the proposal about it, as close to it as possible.
    const s = c.created ? Math.abs(c.created - r.ts) + (r.ts > c.created + 120 ? 1e9 : 0) : -r.ts;
    if (s < score) { best = r; score = s; }
  }
  return best;
}

const ORDER = { promoted: 0, proposed: 1 };

function buildStream(d) {
  const all = [...d.learned, ...d.pending, ...d.past]
    .sort((a, b) => (ORDER[a.state] ?? 2) - (ORDER[b.state] ?? 2));
  const onRow = new Map();
  const loose = new Map();
  for (const c of all) {
    const row = matchDecision(c, d.decisions);
    if (row) {
      if (!onRow.has(row)) onRow.set(row, []);
      onRow.get(row).push(c);
      continue;
    }
    // Said before the log began (or before a restart): its own bubble.
    const key = norm(c.reply);
    const said = Math.min(c.created || Infinity, ...c.evidence.map((e) => e.ts || Infinity));
    const entry = loose.get(key) || { ts: Infinity, reply: c.reply, cands: [] };
    entry.ts = Math.min(entry.ts, Number.isFinite(said) ? said - 0.001 : 0);
    entry.cands.push(c);
    loose.set(key, entry);
  }
  const items = d.decisions.map((r) => ({ ts: r.ts, row: r, cands: onRow.get(r) || [] }));
  for (const entry of loose.values()) items.push({ ts: entry.ts, ledger: true, reply: entry.reply, cands: entry.cands });
  items.sort((a, b) => a.ts - b.ts);
  const bubbleOf = {};
  items.forEach((item, i) => {
    item.key = String(i);
    for (const c of item.cands) bubbleOf[c.id] = item.key;
  });
  return { items, bubbleOf };
}

function dayOf(ts) {
  return new Date(ts * 1000).toDateString();
}

function dayLabel(ts) {
  if (dayOf(ts) === dayOf(nowS())) return t("today");
  return new Date(ts * 1000).toLocaleDateString(locale(), { month: "short", day: "numeric", weekday: "short" });
}

function hm(ts) {
  return h("time", { title: stamp(ts), datetime: new Date(ts * 1000).toISOString() },
    new Date(ts * 1000).toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit", hour12: false }));
}

function chatStream(d, stream) {
  const learnedShown = more(d, "learned", t("learned")), pastShown = more(d, "past", t("past"));
  if (!stream.items.length) {
    return h("div", { class: "stream empty-stream" },
      h("figure", { class: "frame small" },
        h("img", { src: "dashboard/listening.webp", alt: "", width: 560, height: 373 })),
      h("strong", { text: t("listening") }),
      h("span", { text: t("no_decisions") }),
      learnedShown, pastShown);
  }
  const rows = [];
  let day = "";
  for (const item of stream.items) {
    if (item.ts && dayOf(item.ts) !== day) {
      day = dayOf(item.ts);
      rows.push(h("li", { class: "day" }, h("span", { text: dayLabel(item.ts) })));
    }
    rows.push(item.row && !item.row.spoke ? quietRow(item.row) : botRow(item));
  }
  return h("section", { class: "stream", "aria-labelledby": "stream-title" },
    h("h3", { id: "stream-title", class: "sr-only", text: t("decisions") }),
    learnedShown, pastShown,
    h("ol", { class: "msgs" }, rows),
    h("div", { class: "latest-dock" },
      // Shown as it was, so a redraw can hand the keyboard back to it.
      h("button", { type: "button", class: "to-latest", hidden: latestShown ? null : true, "data-key": "latest", onclick: toLatest },
        icon("down"), h("span", { text: t("latest") }))));
}

function modeChip(r) {
  if (!r.mode) return null;
  // "judge" on a quiet line: it could have joined in, and chose not to.
  const key = r.mode === "judge" && !r.spoke ? "m_judge_quiet" : "m_" + r.mode;
  return h("span", { class: "chip mode", text: t(key, null, r.mode) });
}

function reasonText(r) {
  const key = REASONS[r.reason];
  return key ? t(key) : r.reason;
}

// A member's message: their initial, their name, the bubble on the left.
function fromMember(who, body, cls) {
  return [
    who ? h("span", { class: "face small " + tone(who), "aria-hidden": "true", text: initial(who) })
      : h("span", { class: "face small blank", "aria-hidden": "true" }),
    h("div", { class: "said-by" },
      who ? h("span", { class: "name ink-" + toneOf(who), text: who }) : null,
      h("p", { class: cls }, body)),
  ];
}

function quietRow(r) {
  return h("li", { class: "msg quiet" },
    r.excerpt ? h("div", { class: "from" },
      fromMember(r.sender, [h("span", { class: "sr-only", text: lead("after") }), memberText(r.excerpt)], "heard")) : null,
    h("p", { class: "aside" },
      h("span", { class: "ring", "aria-hidden": "true" }),
      h("strong", { text: t("quiet") }),
      modeChip(r),
      h("span", { class: "reason", text: reasonText(r) }),
      r.count > 1 ? h("span", { class: "chip", text: t("times", { n: r.count }) }) : null,
      hm(r.ts)));
}

// A leading @mention of the persona reads as a mention. One a connector put in
// front of a message that already names it ("@Nova Nova, ...") is left out.
function memberText(text) {
  const me = personaName();
  const s = String(text || "");
  if (!me || !s.startsWith("@" + me)) return s;
  const rest = s.slice(me.length + 1).trimStart();
  if (rest.startsWith(me)) return rest;
  return [h("span", { class: "mention", text: "@" + me }), rest ? " " + rest : ""];
}

// What a reply answered: the log's excerpt, or for a reply older than the log,
// the last line of a proposal's context when someone else wrote it.
function askedOf(item) {
  const r = item.row;
  if (r) return r.answered ? { who: r.sender || "", text: r.answered } : null;
  const me = personaName();
  for (const c of item.cands) {
    const line = (c.context || [])[c.context.length - 1];
    const m = line ? /^([^:：]{1,40})[:：]\s?(.*)$/.exec(line) : null;
    if (m && m[1].trim() !== me && m[2].trim()) {
      const text = [...m[2].trim()];
      return { who: m[1].trim(), text: text.length > 60 ? text.slice(0, 59).join("") + "…" : text.join("") };
    }
  }
  return null;
}

function botRow(item) {
  const r = item.row;
  const cands = item.cands;
  // A proposal holds the whole reply; the log only its start.
  let text = r ? r.excerpt : item.reply;
  for (const c of cands) if (norm(c.reply).length > norm(text).length) text = c.reply;
  const live = cands.find((c) => c.state === "promoted");
  const pending = cands.find((c) => c.state === "proposed");
  const mark = live ? (live.type === "preference_pair" ? " corrected" : " kept")
    : pending ? (pending.type === "preference_pair" ? " questioned" : " nominated") : "";
  const asked = askedOf(item);
  return [
    asked ? h("li", { class: "msg in" }, fromMember(asked.who, memberText(asked.text), "bubble in")) : null,
    h("li", { class: "msg bot" + mark, id: "b-" + item.key, tabindex: cands.length ? "-1" : null,
      "data-key": "b:" + (r ? r.ts : "ledger:" + norm(item.reply)) },
    h("p", { class: "bubble" },
      h("span", { class: "sr-only", text: t("spoke") + (view.lang === "zh" ? "，" : ", ") + lead("said") }), text,
      live && live.type !== "preference_pair" ? icon("star", "kept-star") : null),
    h("p", { class: "meta" },
      r ? [hm(r.ts), modeChip(r), h("span", { class: "reason", text: reasonText(r) })]
        : [icon("clock"), h("span", { text: t("from_ledger") })]),
    cands.map((c) => annotation(c))),
  ];
}

let latestWatch = null;
let latestShown = false;

// "Jump to latest" shows while a transcript taller than the window has its end below the fold.
function watchLatest(box) {
  if (latestWatch) { latestWatch.disconnect(); latestWatch = null; }
  const btn = box.querySelector(".to-latest");
  const list = box.querySelector(".msgs");
  if (!btn || !list || !list.lastElementChild || typeof IntersectionObserver !== "function") {
    latestShown = false;
    return;
  }
  latestWatch = new IntersectionObserver((entries) => {
    const entry = entries[entries.length - 1];
    const below = !entry.isIntersecting && entry.boundingClientRect.top > 0;
    latestShown = below && list.offsetHeight > window.innerHeight;
    btn.hidden = !latestShown;
  });
  latestWatch.observe(list.lastElementChild);
}

function toLatest() {
  const list = document.querySelector(".msgs");
  const end = list && list.lastElementChild;
  if (!end) return;
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  end.scrollIntoView({ block: "end", behavior: still ? "auto" : "smooth" });
  // The button hides once the end is in view; the keyboard lands on the last message.
  if (!end.hasAttribute("tabindex")) end.setAttribute("tabindex", "-1");
  end.focus({ preventScroll: true });
}

function annotation(c) {
  const isPair = c.type === "preference_pair";
  const tag = c.state === "promoted" ? "learned" : c.state === "proposed" ? "waiting" : "past";
  if (tag === "waiting") {
    return h("div", { class: "note-card waiting-card" },
      h("button", { type: "button", class: "tag", "data-key": "tag:" + c.id, onclick: () => jump("p-" + c.id) },
        icon("up"), t("pending") + " · " + t("t_" + c.type, null, c.type)),
      isPair && c.better ? h("p", { class: "bubble better proposed" }, icon("turn"), h("span", { text: c.better })) : null);
  }
  const key = c.id + ":ann";
  const label = [
    icon(tag === "learned" ? "leaf" : "cross"),
    h("span", { class: "tag-text", text: (tag === "learned" ? t("learned") + " · " : "") + t("t_" + c.type, null, c.type) }),
    h("span", { class: "chip " + stateClass(c.state), text: t("s_" + c.state, null, c.state) }),
    h("span", { class: "when" }, when(c.created)),
  ];
  const better = isPair && c.better ? h("p", { class: "bubble better" + (tag === "past" ? " faded" : "") },
    icon("turn"), h("span", { text: c.better })) : null;
  const detail = h("div", { class: "note-detail" },
    h("p", { class: "mono when", title: c.id, text: c.id.slice(0, 12) }),
    tag === "past" ? better : null,
    contextBlock(c),
    rivals(c),
    c.checklist ? renderChecklist(c.checklist) : null,
    evidenceBlock(c),
    historyBlock(c));
  if (tag === "past") {
    // Retired: one quiet line until opened.
    return h("div", { class: "note-card past" },
      disclosure(key, h("span", { class: "tag-line" }, label), detail),
      c.actions.length ? renderActions(c) : null);
  }
  return h("div", { class: "note-card learned" },
    h("div", { class: "tag-line" }, label, h("span", { class: "spacer" }),
      c.actions.length ? renderActions(c) : null),
    better,
    disclosure(key, h("span", null, t("more_detail"),
      c.evidence.length ? h("span", { class: "count", text: String(c.evidence.length) }) : null), detail));
}

function disclosure(key, summary, ...body) {
  return h("details", {
    class: "more",
    open: view.open.has(key) || null,
    ontoggle: (e) => { if (e.currentTarget.open) view.open.add(key); else view.open.delete(key); },
  }, h("summary", { "data-key": "more:" + key }, icon("chev", "chev"), summary), body);
}

function composer(d) {
  if (d.kind !== "group" || !d.trigger_count) return null;
  return h("div", { class: "composer" },
    meter(d.counter, d.trigger_count),
    h("p", { class: "note", text: t("trigger_progress", { n: d.trigger_count, c: d.counter }) }));
}

function jump(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ block: "center", behavior: still ? "auto" : "smooth" });
  el.classList.remove("flash");
  void el.offsetWidth;
  el.classList.add("flash");
  el.addEventListener("blur", () => el.classList.remove("flash"), { once: true });
  el.focus({ preventScroll: true });
}

// ----------------------------------------------------------- actions ----

let disarmTimer = null;

async function act(id, action) {
  if (view.busy) return;
  if (!view.armed || view.armed.id !== id || view.armed.action !== action) {
    view.armed = { id, action };
    clearTimeout(disarmTimer);
    disarmTimer = setTimeout(() => { view.armed = null; view.shown.detail = ""; render(); refocus(id, action); }, 5000);
    renderDetailNow();
    refocus(id, action);
    return;
  }
  clearTimeout(disarmTimer);
  view.armed = null;
  view.busy = true;
  renderDetailNow();
  try {
    const result = await api("api/dashboard/candidates/" + encodeURIComponent(id) + "/" + action, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Personagent-Dashboard": "1" },
      body: JSON.stringify({}),
    });
    toast(result.views_rebuilt === false ? t("views_failed") : t("done_" + action), result.views_rebuilt === false);
  } catch (e) {
    toast(t("refused", { msg: e.code ? t("e_" + e.code, null, e.message) : e.message }), true);
  }
  view.busy = false;
  view.shown.detail = "";
  await refresh();
}

// A redraw replaces the buttons; keep the keyboard where it was.
function refocus(id, action) {
  const btn = document.querySelector('[data-act="' + id + ":" + action + '"]');
  if (btn && document.activeElement === document.body) btn.focus({ preventScroll: true });
}

function renderDetailNow() {
  view.shown.detail = "";
  renderDetail();
}

function renderFooter() {
  const footer = document.getElementById("footer");
  replace(footer,
    h("span", { text: t("footer") }),
    view.updatedAt ? h("span", { text: t("updated", { t: new Date(view.updatedAt).toLocaleTimeString(locale(), { hour12: false }) }) }) : null);
}

let toastTimer = null;

function toast(message, isError) {
  const el = document.getElementById("toast");
  replace(el, rich(message));
  el.className = "toast show" + (isError ? " err" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = "toast"; }, 4000);
}

// ---------------------------------------------------------- controls ----

function applyTheme() {
  const root = document.documentElement;
  if (view.theme === "auto") delete root.dataset.theme;
  else root.dataset.theme = view.theme;
}

function wireControls() {
  document.getElementById("lang-toggle").addEventListener("click", () => {
    view.langOverride = view.lang === "zh" ? "en" : "zh";
    save("personagent.lang", view.langOverride);
    render();
  });
  document.getElementById("theme-toggle").addEventListener("click", () => {
    view.theme = { auto: "light", light: "dark", dark: "auto" }[view.theme] || "auto";
    save("personagent.theme", view.theme === "auto" ? null : view.theme);
    applyTheme();
    render();
  });
  window.addEventListener("hashchange", readHash);
}

function readHash() {
  const match = /^#c=(.+)$/.exec(window.location.hash || "");
  if (!match) return;
  let id;
  try { id = decodeURIComponent(match[1]); } catch (e) { return; }
  if (id && id !== view.selected) select(id, false);
}

let timer = null;

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(async () => {
    if (!document.hidden) await refresh();
    schedule();
  }, POLL_MS);
}

function start() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("lang") === "zh" || params.get("lang") === "en") view.langOverride = params.get("lang");
  if (["light", "dark"].includes(params.get("theme"))) view.theme = params.get("theme");
  applyTheme();
  wireControls();
  readHash();
  render();
  refresh().then(schedule);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
}

document.addEventListener("DOMContentLoaded", start);
