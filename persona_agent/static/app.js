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
    m_judge: "own judgement",
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
    h_none_url: "Your chat connector (for example the AstrBot plugin) must send to {url}",
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
    last_event: "最近消息 {t}",
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
    m_judge: "自主判断",
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
    h_none_url: "聊天连接器（比如 AstrBot 插件）要发到 {url}",
    h_none_token_set: "这里设置了 CONNECTOR_TOKEN，连接器那边要填同一个。",
    h_none_token_blank: "这里的 CONNECTOR_TOKEN 是空的：连接器那边也留空，或者两边设成同一个。",
    h_none_access: "如果设置了 ACCESS_GROUPS 或 ACCESS_DM_USERS，这个会话必须在名单里。",
    h_none_doctor: "运行 `{cli} doctor` 可以检查整条链路。",
    h_refused_t: "收到了消息，但被拒之门外",
    h_quiet_t: "消息在进来，它还没开口",
    h_quiet: "被点名（{name}）或 @ 时它会回答；否则大约 {n} 条消息后才考虑插话，而且可能决定不说。",
    footer: "私密页面：只能通过带令牌的链接打开。修改会以 “dashboard” 的身份写进只增不删的账本。",
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
  },
};

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
  shown: { hints: "", status: "", convs: "", detail: "" },
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

function clock(ts) {
  const d = new Date(ts * 1000);
  const today = new Date(nowS() * 1000);
  if (d.toDateString() === today.toDateString()) {
    return d.toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit", hour12: false });
  }
  return d.toLocaleDateString(locale(), { month: "numeric", day: "numeric" });
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
    if (!view.selected && view.convs.length
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
  // Hints are alerts: redrawn only when what they say changes.
  const hints = hintList();
  const hintKey = JSON.stringify(hints);
  if (hintKey !== view.shown.hints) {
    view.shown.hints = hintKey;
    renderHints(hints);
  }
  const statusKey = JSON.stringify([view.lang, view.down, view.failure, view.status]);
  if (statusKey !== view.shown.status) {
    view.shown.status = statusKey;
    renderOverview();
  }
  const convKey = JSON.stringify([view.lang, view.convs, view.selected]);
  if (convKey !== view.shown.convs) {
    view.shown.convs = convKey;
    renderConversations();
  }
  const detailKey = JSON.stringify([view.lang, view.selected, view.detail, view.convs && view.convs.length]);
  if (detailKey !== view.shown.detail && !view.armed && !view.busy) {
    view.shown.detail = detailKey;
    renderDetail();
  }
  renderFooter();
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
  document.getElementById("theme-toggle").textContent = t("theme_" + view.theme);
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
      : { level: "error", title: t("h_error_t", { status: f.status }), items: [f.message + (f.code ? " (" + f.code + ")" : "")] });
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
      items: a.refused.map((r) => r.conversation + ": " + r.reason),
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
    h("h3", { text: hint.title }),
    h(hint.ordered ? "ol" : "ul", null, hint.items.map((item) => h("li", { text: item }))))));
}

function card(title, extraClass, ...body) {
  return h("article", { class: "card" + (extraClass ? " " + extraClass : "") },
    h("h2", { class: "card-title", text: title }), body);
}

function kv(pairs) {
  return h("dl", { class: "kv" }, pairs.filter(Boolean).map(([k, v]) => [h("dt", { text: k }), h("dd", null, v)]));
}

function renderOverview() {
  const box = document.getElementById("overview");
  const st = view.status;
  if (!st) { replace(box); return; }
  const persona = st.persona || {};

  const service = card(t("service"), "",
    kv([
      [t("version"), st.version],
      [t("uptime"), duration(st.uptime_s)],
      [t("home"), h("span", { class: "mono", text: st.home })],
      [t("language"), st.lang === "zh" ? "中文 (zh)" : "English (en)"],
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
        h("span", { class: "chip " + (f.level === "ERROR" ? "err" : f.level === "WARN" ? "warn" : ""), text: f.level }),
        h("span", { class: "mono", text: f.key }),
        h("span", { class: "detail", text: f.detail }))))
      : h("p", { class: "empty", text: t("no_findings") }));

  replace(box, service, personaCard, modelsCard, connectorsCard, checksCard);
}

function shortId(id, n) {
  return id.length > n ? id.slice(0, n - 1) + "…" : id;
}

function renderConversations() {
  const list = document.getElementById("conv-list");
  const convs = view.convs || [];
  document.querySelector(".convs").classList.toggle("none", view.convs != null && !convs.length);
  if (!convs.length) {
    replace(list, view.convs == null ? null : h("div", { class: "card placeholder" },
      h("strong", { text: t("no_convs_t") }),
      h("span", { text: t("no_convs") })));
    return;
  }
  replace(list, convs.map((c) => h("button", {
    type: "button",
    class: "conv",
    "aria-current": c.id === view.selected ? "true" : "false",
    onclick: () => select(c.id, true),
  },
  h("span", { class: "name" },
    h("span", { class: "chip accent", text: c.platform }),
    h("span", { class: "chip", text: c.kind === "dm" ? t("dm") : t("group") }),
    h("span", { class: "id", title: c.id, text: label(c) })),
  h("span", { class: "meta" },
    h("span", { text: c.last_activity ? t("last_activity", { t: ago(c.last_activity) }) : t("never") }),
    c.memories ? h("span", { text: t("notes_n", { n: c.memories }) }) : null,
    c.learned ? h("span", { text: t("learned_n", { n: c.learned }) }) : null,
    c.pending ? h("span", { class: "hot", text: t("pending_n", { n: c.pending }) }) : null))));
}

function select(id, scroll) {
  if (view.selected === id) return;
  view.selected = id;
  view.detail = null;
  view.armed = null;
  try { history.replaceState(null, "", "#c=" + encodeURIComponent(id)); } catch (e) { /* ignore */ }
  refreshDetail().then(() => {
    render();
    if (scroll && window.matchMedia("(max-width: 900px)").matches) {
      document.getElementById("detail").scrollIntoView({ block: "start" });
    }
  });
  render();
}

function block(title, count, ...body) {
  return h("section", { class: "block" },
    h("h3", null, title, count ? h("span", { class: "count", text: String(count) }) : null), body);
}

function renderDetail() {
  const box = document.getElementById("detail");
  const d = view.detail;
  if (!view.selected || !d) {
    const none = view.convs && !view.convs.length;
    replace(box, h("div", { class: "placeholder" },
      h("strong", { text: none ? t("no_convs_t") : t("pick_t") }),
      h("span", { text: none ? t("no_convs") : t("pick") })));
    return;
  }
  const conv = (view.convs || []).find((c) => c.id === d.id) || {};
  const head = h("div", { class: "detail-head" },
    h("h2", { text: d.id }),
    h("div", { class: "line" },
      h("span", { class: "chip accent", text: d.platform }),
      h("span", { class: "chip", text: d.kind === "dm" ? t("dm") : t("group") }),
      h("span", { text: conv.last_activity ? t("last_activity", { t: ago(conv.last_activity) }) : "" })),
    d.kind === "group" && d.trigger_count
      ? h("div", { class: "note", text: t("trigger_progress", { n: d.trigger_count, c: d.counter }) })
      : null);

  const totals = d.totals || {};
  const total = (group) => totals[group] || d[group].length;
  // Long lists arrive cut to the newest; say so instead of hiding the rest.
  const more = (group) => total(group) > d[group].length
    ? h("p", { class: "empty", text: t("shown_of", { shown: d[group].length, n: total(group) }) }) : null;
  replace(box,
    head,
    block(t("decisions"), d.decisions.length, renderDecisions(d.decisions)),
    block(t("pending"), total("pending"),
      d.pending.length ? h("div", { class: "cands" }, d.pending.map(renderCandidate))
        : h("p", { class: "empty", text: t("no_pending") }), more("pending")),
    block(t("learned"), total("learned"),
      d.learned.length ? h("div", { class: "cands" }, d.learned.map(renderCandidate))
        : h("p", { class: "empty", text: t("no_learned") }), more("learned")),
    block(t("memories"), d.memories.length, renderMemories(d)),
    d.past.length ? block(t("past"), total("past"),
      h("details", null, h("summary", { text: t("show") }),
        h("div", { class: "cands" }, d.past.map(renderCandidate)), more("past"))) : null);
}

function renderDecisions(rows) {
  if (!rows.length) return h("p", { class: "empty", text: t("no_decisions") });
  return h("ul", { class: "decisions" }, rows.map((r) => {
    const reasonKey = REASONS[r.reason];
    return h("li", { class: "decision " + (r.spoke ? "spoke" : "quiet") },
      h("time", { title: stamp(r.ts), text: clock(r.ts) }),
      h("span", { class: "dot " + (r.spoke ? "on" : "off"), "aria-hidden": "true" }),
      h("div", { class: "what" },
        h("span", { class: "verb", text: r.spoke ? t("spoke") : t("quiet") }),
        r.mode ? h("span", { class: "chip", text: t("m_" + r.mode, null, r.mode) }) : null,
        h("span", { class: "reason", text: reasonKey ? t(reasonKey) : r.reason }),
        r.count > 1 ? h("span", { class: "chip", text: t("times", { n: r.count }) }) : null),
      r.excerpt ? h("div", { class: "excerpt", text: (r.spoke ? t("said") : t("after")) + " " + r.excerpt }) : null);
  }));
}

function textRow(cls, label, text) {
  return h("div", { class: "text-row " + cls },
    h("span", { class: "label", text: label }),
    h("span", { class: "body", text }));
}

function renderCandidate(c) {
  const isPair = c.type === "preference_pair";
  const head = h("div", { class: "cand-head" },
    h("span", { class: "title", text: t("t_" + c.type, null, c.type) }),
    h("span", { class: "chip " + stateClass(c.state), text: t("s_" + c.state, null, c.state) }),
    h("span", { class: "when" }, when(c.created)),
    h("span", { class: "spacer" }),
    h("span", { class: "mono when", title: c.id, text: c.id.slice(0, 12) }));

  const texts = h("div", { class: "texts" },
    isPair ? textRow("before", t("it_said"), c.reply) : textRow("after", t("reply"), c.reply),
    isPair && c.better ? textRow("after", t("better"), c.better) : null,
    c.context.length ? h("div", { class: "context", text: t("context") + ": " + c.context.join(" / ") }) : null);

  const evidenceBlock = h("div", null,
    h("p", { class: "sub", text: t("evidence") }),
    c.evidence.length ? h("ul", { class: "evidence" }, c.evidence.map(renderEvent))
      : h("p", { class: "empty", text: t("no_evidence") }),
    c.missing_evidence ? h("p", { class: "empty", text: t("missing_evidence", { n: c.missing_evidence }) }) : null);

  const parts = [head, texts];
  for (const rival of c.replaces || []) {
    parts.push(h("div", { class: "waiting", text: t("rival", { text: rival.better }) }));
  }
  if (c.checklist) parts.push(renderChecklist(c.checklist));
  parts.push(evidenceBlock);
  if (c.history.length) {
    parts.push(h("div", null,
      h("p", { class: "sub", text: t("history") }),
      h("ul", { class: "history" }, c.history.map((row) => h("li", null,
        h("time", { title: stamp(row.ts), text: ago(row.ts) }), " · ",
        historyLine(row),
        row.reason ? " · " + row.reason : "")))));
  }
  if (c.actions.length) parts.push(renderActions(c));
  return h("article", { class: "cand " + c.state }, parts);
}

function historyLine(row) {
  const what = t("hs_" + row.state, null, row.state);
  const actor = row.actor || "?";
  const who = actor === "auto" || actor === "dashboard"
    ? t("by_" + actor + "_actor") : t("by_actor", { actor });
  return view.lang === "zh" ? who + what : what + " " + who;
}

function label(conv) {
  let id = conv.id;
  if (id.startsWith("private:")) id = id.slice(8);
  if (id.startsWith(conv.platform + ":")) id = id.slice(conv.platform.length + 1);
  return id || conv.id;
}

function stateClass(state) {
  return state === "promoted" ? "ok" : state === "proposed" ? "warn" : "";
}

function renderEvent(e) {
  const head = h("div", { class: "ev-head" },
    h("span", { class: "who", text: e.speaker || "?" }),
    h("span", { text: t("k_" + e.kind, null, e.kind) + (e.reaction_type && e.kind === "reaction" ? " · " + t("rt_" + e.reaction_type, null, e.reaction_type) : "") }),
    h("span", { class: "chip " + (e.strength === "strong" ? "ok" : ""), text: t("st_" + e.strength, null, e.strength) }),
    h("span", { class: "when" }, when(e.ts)));
  return h("li", { class: "ev" + (e.counts ? "" : " not-counted") },
    head,
    e.said ? h("div", { class: "said", text: e.said }) : null,
    e.verdict ? h("div", { class: "verdict", text: t("judge") + " " + e.verdict }) : null,
    h("div", { class: "verdict", text: [
      e.speaker_is_recipient ? t("aimed_at_them") : null,
      e.accepted ? null : t("dismissed"),
      e.counts ? null : t("not_counted"),
    ].filter(Boolean).join(" · ") }));
}

function renderChecklist(cl) {
  const items = cl.rules.map((rule) => {
    let label;
    if (rule.id === "same_chat") label = rule.on ? t("c_same_chat") : t("c_any_chat");
    else label = t("c_" + rule.id, { have: rule.have, need: rule.need }, rule.id);
    const info = rule.id === "same_chat";
    return h("li", { class: "check" },
      h("span", { class: info ? "mark-info" : rule.ok ? "mark-ok" : "mark-no", "aria-hidden": "true",
        text: info ? "•" : rule.ok ? "✓" : "✕" }),
      h("span", null, info ? null : h("span", { class: "sr-only", text: (rule.ok ? t("passed") : t("not_yet")) + ": " }), label));
  });
  const waiting = cl.waiting_for.length
    ? cl.waiting_for.map((w) => t("w_" + w, null, w)).join("; ")
    : (cl.promote ? t("w_ready") : "");
  return h("div", null,
    h("p", { class: "sub", text: t("checklist") }),
    h("ul", { class: "checklist" }, items),
    waiting ? h("div", { class: "waiting" }, h("strong", { text: t("waiting_for") + " " }), waiting) : null,
    h("div", { class: "verdict-line", text: t("policy") + " " + cl.verdict }));
}

function renderActions(c) {
  return h("div", { class: "actions" }, c.actions.map((action) => {
    const armed = view.armed && view.armed.id === c.id && view.armed.action === action;
    return h("button", {
      type: "button",
      class: "btn " + (armed ? "armed" : action === "promote" || action === "replace" ? "primary" : "danger"),
      disabled: view.busy || null,
      onclick: () => act(c.id, action),
    }, armed ? t("confirm") : t("a_" + action));
  }));
}

let disarmTimer = null;

async function act(id, action) {
  if (view.busy) return;
  if (!view.armed || view.armed.id !== id || view.armed.action !== action) {
    view.armed = { id, action };
    clearTimeout(disarmTimer);
    disarmTimer = setTimeout(() => { view.armed = null; view.shown.detail = ""; render(); }, 5000);
    renderDetailNow();
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
    toast(t("refused", { msg: e.message }), true);
  }
  view.busy = false;
  view.shown.detail = "";
  await refresh();
}

function renderDetailNow() {
  view.shown.detail = "";
  renderDetail();
}

function renderMemories(d) {
  const items = [];
  if (d.core_note) {
    items.push(h("li", { class: "memory" },
      h("span", { class: "by", text: t("core_note") }),
      h("span", { class: "text", text: d.core_note })));
  }
  for (const m of d.memories) {
    items.push(h("li", { class: "memory" },
      h("span", { class: "text", text: m.text }),
      h("span", { class: "by" },
        (m.auto ? t("by_auto") : (m.by || t("by_admin"))) + " · ", when(m.time))));
  }
  if (!items.length) return h("p", { class: "empty", text: t("no_memories") });
  return h("ul", { class: "memories" }, items);
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
  el.textContent = message;
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
