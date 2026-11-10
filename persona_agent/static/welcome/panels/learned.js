// The learned panel. See PA at the end of welcome.js.
"use strict";
PA.strings({
  en: {
    learned_title: "What the character has learned",
    learned_lead:
      "Everything the character has learned in every chat: what it uses, what awaits your decision and what was set aside. You can review and decide here even when the character is not running.",
    learned_sum: "The character uses {inUse} learned item(s) from {chats} chat(s). {waiting} item(s) await your decision.",
    learned_sum_none: "The character has not learned anything yet. Items appear here when someone corrects or approves one of its replies.",
    learned_sum_idle: "{n} item(s) belong to an earlier character or an earlier chat on this page and are not used.",
    learned_sum_other: "These items were learned while the character spoke {lang}. They are used only when it speaks {lang} again.",
    learned_not_running: "The character is not running. You can still review every item and decide here.",
    learned_lang_label: "Language learned in",
    learned_lang_en: "English",
    learned_lang_zh: "Chinese",
    learned_lang_now: "{lang} (current)",
    learned_lang_note:
      "The character also learned {n} item(s) while speaking another language. They are used again when it speaks that language.",
    learned_tab_in_use: "In use",
    learned_tab_waiting: "Pending",
    learned_tab_discarded: "Discarded",
    learned_tab_undone: "Undone",
    learned_tab_replaced: "Replaced",
    learned_hint_in_use: "These items shape the character's replies.",
    learned_hint_waiting: "These items are not used until enough people agree or you keep them.",
    learned_hint_discarded: "These items will not be used again. They remain here as a record.",
    learned_hint_undone: "These items are no longer used. You can restore any of them.",
    learned_hint_replaced: "A newer wording of the same reply has taken the place of these items.",
    learned_empty_in_use: "No items are in use.",
    learned_empty_waiting: "No items await your decision.",
    learned_empty_discarded: "No items have been discarded.",
    learned_empty_undone: "No items have been undone.",
    learned_empty_replaced: "No items have been replaced.",
    learned_loading: "Loading…",
    learned_more: "Show more",
    learned_wording: "Better wording",
    learned_repeat: "Reply worth repeating",
    learned_said: "Original",
    learned_instead: "Revised",
    learned_lesson: "Going forward",
    learned_here: "This page",
    learned_group: "group",
    learned_dm: "direct message",
    learned_chat_unknown: "Unknown chat",
    learned_gap_lang: "Not in use: another language",
    learned_gap_persona: "Not in use: earlier character",
    learned_gap_chat: "Not in use: earlier chat on this page",
    learned_why_title: "Why it is pending",
    learned_why_scope_lang: "The character uses this item only while it speaks {lang}.",
    learned_why_scope_persona:
      "This item belongs to an earlier character: the character's name or persona version has changed since it was learned. The character does not use it, and it cannot be kept.",
    learned_why_scope_chat:
      "This item was learned in an earlier chat on this page, which has since been reset. The character does not use it, and it cannot be kept.",
    learned_why_off: "Automatic application is turned off, so every item awaits your decision.",
    learned_why_against: "Other reactions disagree with this item, so the decision is left to you.",
    learned_why_conflict: "Another revision of the same reply exists, so the decision is left to you.",
    learned_why_person: "Only an admin can approve this type of item. Keep it if you agree with it.",
    learned_why_strong: "It still requires a clear correction from the person the reply was addressed to.",
    learned_why_events: "It requires {n} more agreeing reaction(s).",
    learned_why_speakers: "It requires agreement from {n} more person(s).",
    learned_why_ready:
      "It meets every rule and will apply automatically at the next reaction. You can also keep it now.",
    learned_rule_events: "Agreeing reactions: {have} of {need}",
    learned_rule_strong: "Clear corrections from the person addressed: {have} of {need}",
    learned_rule_speakers: "Different people: {have} of {need}",
    learned_rule_stale: "{n} reaction(s) older than {days} days no longer count.",
    learned_now_in_use: "In use since {when}.",
    learned_now_discarded: "Discarded on {when}. It cannot be restored.",
    learned_now_undone: "Undone on {when}. You can restore it.",
    learned_now_replaced: "Replaced on {when}. It cannot be restored.",
    learned_replaced_by: "Current wording: {text}",
    learned_context: "Preceding messages",
    learned_evidence: "Reactions",
    learned_evidence_none: "No reactions are recorded for this item.",
    learned_evidence_missing: "{n} earlier reaction(s) are no longer on record.",
    learned_someone: "A participant",
    learned_itself: "The character",
    learned_what_correction: "corrected the reply",
    learned_what_rejection: "disapproved of the reply",
    learned_what_positive: "approved of the reply",
    learned_what_neutral: "did not respond to the reply",
    learned_what_retry_acceptance: "accepted the second attempt",
    learned_what_self_eval: "scored its own reply",
    learned_what_self_review: "reviewed its own reply",
    learned_ev_better: "Suggested wording: {text}",
    learned_ev_reading: "Interpretation: {text}",
    learned_counts: "Counts toward this item",
    learned_not_counts: "Does not count toward this item",
    learned_strong: "Clear correction",
    learned_history: "History",
    learned_h_picked: "Learned",
    learned_h_in_use: "Put into use",
    learned_h_discarded: "Discarded",
    learned_h_undone: "Undone",
    learned_h_replaced: "Replaced",
    learned_by_auto: "automatically",
    learned_by_page: "by you on this page",
    learned_by_terminal: "from the terminal",
    learned_r_agreed: "{n} reactions agreed",
    learned_r_answered: "another revision for the same issue was kept",
    learned_r_replaced: "a newer wording took its place",
    learned_r_disagreed: "the person addressed disagreed",
    learned_r_note: "note: “{text}”",
    learned_replaces: "Keeping this item replaces the wording in use: “{text}”",
    learned_keep: "Keep",
    learned_keeping: "Keeping…",
    learned_back: "Restore",
    learned_backing: "Restoring…",
    learned_discard: "Discard",
    learned_discarding: "Discarding…",
    learned_undo: "Undo",
    learned_undoing: "Undoing…",
    learned_ask_discard:
      "Discard this item? It will not be used again and cannot be restored. It remains on record.",
    learned_ask_replace:
      "Use this item in place of “{text}”? The current wording will be marked as replaced and cannot be restored.",
    learned_ask_replace_yes: "Replace",
    learned_done_keep: "Kept. The character's next replies will use this item.",
    learned_done_keep_lang: "Kept. The character will use this item when it speaks {lang} again.",
    learned_done_back: "Restored. The item is in use again.",
    learned_done_discard: "Discarded.",
    learned_done_undo: "Undone. The character no longer uses this item.",
    learned_invalid: "The request was not understood. Reload the page and try again.",
    learned_unknown: "This item is no longer on record. The list has been refreshed.",
    learned_changed: "This item changed in the meantime. The list has been refreshed; review it and try again.",
    learned_scope:
      "This item belongs to an earlier character or an earlier chat on this page, so keeping it would have no effect. The list has been refreshed.",
    learned_busy: "Another change is being saved. Try again in a moment.",
    learned_unavailable:
      "The running character could not be reached. Try again shortly, or stop the character and decide here.",
    learned_failed: "The change was saved but is not yet in effect. Restart the character to apply it.",
  },
  zh: {
    learned_title: "角色学到的内容",
    learned_lead:
      "角色在所有聊天中学到的内容：正在使用的、等待你确认的以及已搁置的。角色未运行时，你也可以在此查看并处理。",
    learned_sum: "角色正在使用来自 {chats} 个聊天的 {inUse} 条内容，另有 {waiting} 条等待你确认。",
    learned_sum_none: "角色尚未学到任何内容。当有人纠正或认可它的回复时，相关内容会显示在这里。",
    learned_sum_idle: "此外，有 {n} 条内容属于之前的角色或本页面之前的对话，目前不会使用。",
    learned_sum_other: "以下内容是角色以{lang}交流时学到的，仅在它再次以{lang}交流时使用。",
    learned_not_running: "角色未运行。你仍可在此查看全部内容并进行处理。",
    learned_lang_label: "学习时使用的语言",
    learned_lang_en: "英文",
    learned_lang_zh: "中文",
    learned_lang_now: "{lang}（当前）",
    learned_lang_note: "角色以另一种语言交流时还学到了 {n} 条内容，将在它再次使用该语言时重新启用。",
    learned_tab_in_use: "使用中",
    learned_tab_waiting: "待确认",
    learned_tab_discarded: "已舍弃",
    learned_tab_undone: "已撤销",
    learned_tab_replaced: "已替换",
    learned_hint_in_use: "这些内容目前会影响角色的回复。",
    learned_hint_waiting: "这些内容在获得足够认同或由你保留之前不会使用。",
    learned_hint_discarded: "这些内容不会再使用，仅作为记录保留。",
    learned_hint_undone: "这些内容已停止使用，你可以恢复其中任意一条。",
    learned_hint_replaced: "同一回复已有更新的说法，这些内容已被替换。",
    learned_empty_in_use: "没有使用中的内容。",
    learned_empty_waiting: "没有待确认的内容。",
    learned_empty_discarded: "没有已舍弃的内容。",
    learned_empty_undone: "没有已撤销的内容。",
    learned_empty_replaced: "没有已替换的内容。",
    learned_loading: "正在加载…",
    learned_more: "显示更多",
    learned_wording: "改进说法",
    learned_repeat: "值得沿用的回复",
    learned_said: "原回复",
    learned_instead: "改为",
    learned_lesson: "今后做法",
    learned_here: "本页面",
    learned_group: "群聊",
    learned_dm: "私聊",
    learned_chat_unknown: "未知聊天",
    learned_gap_lang: "未使用：属于另一种语言",
    learned_gap_persona: "未使用：属于之前的角色",
    learned_gap_chat: "未使用：属于本页面之前的对话",
    learned_why_title: "待确认原因",
    learned_why_scope_lang: "角色仅在以{lang}交流时使用此条内容。",
    learned_why_scope_persona: "此条内容属于之前的角色：学到它之后，角色的名字或人设版本已变更。角色不会使用它，也无法保留。",
    learned_why_scope_chat: "此条内容学自本页面之前的对话，该对话已重置。角色不会使用它，也无法保留。",
    learned_why_off: "自动生效已关闭，因此每条内容都需要由你决定。",
    learned_why_against: "有其他反应与此条内容相反，因此由你决定。",
    learned_why_conflict: "同一回复存在其他改法，因此由你决定。",
    learned_why_person: "此类内容只能由管理员批准。如果你认同，请保留。",
    learned_why_strong: "仍需要回复对象本人给出一次明确纠正。",
    learned_why_events: "还需要 {n} 次认同的反应。",
    learned_why_speakers: "还需要 {n} 位不同的人认同。",
    learned_why_ready: "已满足全部条件，将在下一次有人回应时自动生效。你也可以现在保留。",
    learned_rule_events: "认同的反应：{have}/{need}",
    learned_rule_strong: "回复对象本人的明确纠正：{have}/{need}",
    learned_rule_speakers: "不同的人：{have}/{need}",
    learned_rule_stale: "有 {n} 次反应已超过 {days} 天，不再计入。",
    learned_now_in_use: "自 {when} 起使用。",
    learned_now_discarded: "已于 {when} 舍弃，无法恢复。",
    learned_now_undone: "已于 {when} 撤销，可以恢复。",
    learned_now_replaced: "已于 {when} 被替换，无法恢复。",
    learned_replaced_by: "当前说法：{text}",
    learned_context: "之前的对话",
    learned_evidence: "收到的反应",
    learned_evidence_none: "此条内容没有记录到反应。",
    learned_evidence_missing: "有 {n} 条较早的反应已不在记录中。",
    learned_someone: "某位用户",
    learned_itself: "角色本身",
    learned_what_correction: "纠正了回复",
    learned_what_rejection: "不认同此回复",
    learned_what_positive: "认可此回复",
    learned_what_neutral: "未回应此回复",
    learned_what_retry_acceptance: "接受了重新生成的回复",
    learned_what_self_eval: "为自己的回复评分",
    learned_what_self_review: "复盘了自己的回复",
    learned_ev_better: "建议说法：{text}",
    learned_ev_reading: "判断依据：{text}",
    learned_counts: "计入",
    learned_not_counts: "不计入",
    learned_strong: "明确纠正",
    learned_history: "处理记录",
    learned_h_picked: "学到",
    learned_h_in_use: "开始使用",
    learned_h_discarded: "舍弃",
    learned_h_undone: "撤销",
    learned_h_replaced: "被替换",
    learned_by_auto: "自动",
    learned_by_page: "由你在本页面操作",
    learned_by_terminal: "通过命令行",
    learned_r_agreed: "{n} 次反应认同",
    learned_r_answered: "同一问题已保留其他改法",
    learned_r_replaced: "已由更新的说法替换",
    learned_r_disagreed: "回复对象本人不认同",
    learned_r_note: "备注：“{text}”",
    learned_replaces: "保留此条内容将替换当前使用的说法：“{text}”",
    learned_keep: "保留",
    learned_keeping: "正在保留…",
    learned_back: "恢复",
    learned_backing: "正在恢复…",
    learned_discard: "舍弃",
    learned_discarding: "正在舍弃…",
    learned_undo: "撤销",
    learned_undoing: "正在撤销…",
    learned_ask_discard: "确定舍弃此条内容吗？舍弃后它将不再使用且无法恢复，但会保留在记录中。",
    learned_ask_replace: "确定用此条内容替换“{text}”吗？当前说法将标记为已替换，且无法恢复。",
    learned_ask_replace_yes: "替换",
    learned_done_keep: "已保留，角色之后的回复将使用此条内容。",
    learned_done_keep_lang: "已保留，角色再次以{lang}交流时将使用此条内容。",
    learned_done_back: "已恢复，此条内容重新投入使用。",
    learned_done_discard: "已舍弃。",
    learned_done_undo: "已撤销，角色不再使用此条内容。",
    learned_invalid: "无法识别此请求，请刷新页面后重试。",
    learned_unknown: "此条内容已不在记录中，列表已刷新。",
    learned_changed: "此条内容已被更改，列表已刷新。请查看后重试。",
    learned_scope: "此条内容属于之前的角色或本页面之前的对话，保留不会产生任何效果。列表已刷新。",
    learned_busy: "另一项更改正在保存，请稍后重试。",
    learned_unavailable: "无法连接正在运行的角色。请稍后重试，或先停止角色再在此处处理。",
    learned_failed: "更改已保存，但尚未生效。请重启角色以应用更改。",
  },
});

(() => {
  const TABS = ["in_use", "waiting", "discarded", "undone", "replaced"];
  // Reaction kinds with a label; anything else shows none (PA.t never returns the key).
  const KNOWN_WHAT = [
    "correction",
    "rejection",
    "positive",
    "neutral",
    "retry_acceptance",
    "self_eval",
    "self_review",
  ];
  const PAGE = 30;
  const root = PA.$("learned-root");
  const make = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  let data = null,
    tab = "in_use",
    lang = "",
    limit = PAGE,
    openId = "",
    detail = null,
    error = "",
    detailError = "",
    busy = "",
    loading = false,
    seq = 0,
    focusId = "";

  const card = make("div", "card side-card learned");
  card.id = "learned-card";
  const title = make("h2");
  const lead = make("p", "field-note");
  const sum = make("p", "learned-sum");
  sum.id = "learned-sum";
  const running = make("p", "field-note learned-running");
  running.id = "learned-not-running";
  const langRow = make("div", "learned-lang");
  const langLabel = make("label");
  langLabel.htmlFor = "learned-lang";
  const langPick = make("select");
  langPick.id = "learned-lang";
  langRow.append(langLabel, langPick);
  const langNote = make("p", "field-note");
  langNote.id = "learned-lang-note";
  const tabs = make("div", "learned-tabs");
  tabs.setAttribute("role", "tablist");
  const hint = make("p", "field-note learned-hint");
  const list = make("ul", "learned-list");
  list.id = "learned-list";
  const empty = make("p", "learned-empty");
  const more = make("button", "secondary learned-more");
  more.type = "button";
  more.id = "learned-more";
  const failure = make("p", "error");
  failure.id = "learned-error";
  failure.setAttribute("role", "alert");
  card.append(title, lead, sum, running, langRow, langNote, tabs, hint, list, empty, more, failure);
  root.append(card);

  // Rows and buttons are rebuilt on each render; focus follows them by id.
  document.addEventListener("focusin", (event) => {
    focusId = root.contains(event.target) ? event.target.id || "" : "";
  });
  root.addEventListener("focusout", (event) => {
    if (event.relatedTarget) return;
    const gone = event.target;
    // Only a deliberate blur forgets it; a removed or disabled control is restored.
    setTimeout(() => {
      if (gone.isConnected && !gone.disabled && document.activeElement === document.body) focusId = "";
    }, 0);
  });
  const usable = (node) => node && !node.hidden && node.getClientRects().length;
  function keepFocus() {
    if (!focusId || !root.getClientRects().length) return;
    const active = document.activeElement;
    if (active && active !== document.body && active.isConnected) return;
    const same = PA.$(focusId);
    if (usable(same)) {
      // A button disabled while it works gets focus back on the render after.
      if (!same.disabled) same.focus({ preventScroll: true });
      return;
    }
    // The item may be on its way to another tab: wait for the list.
    if (loading) return;
    const near = [openId && PA.$(`learned-row-${openId}`), PA.$(`learned-tab-${tab}`)].find(usable);
    if (near) near.focus({ preventScroll: true });
  }

  const zh = () => String(PA.lang).startsWith("zh");
  const locale = () => (PA.lang === "zh" ? "zh-CN" : PA.lang || "en");
  const date = (epoch) =>
    epoch
      ? new Date(epoch * 1000).toLocaleString(locale(), {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
  const langName = (code) =>
    code === "en" ? PA.t("learned_lang_en") : code === "zh" ? PA.t("learned_lang_zh") : code;
  function chatName(chat) {
    if (!chat || !chat.id) return PA.t("learned_chat_unknown");
    if (chat.platform === "browser") return PA.t("learned_here");
    const platform = chat.name[zh() ? 1 : 0] || chat.platform;
    const kind = PA.t(chat.kind === "dm" ? "learned_dm" : "learned_group");
    return [platform, kind, chat.tail].filter(Boolean).join(" ");
  }
  const meta = (row) => [chatName(row.chat), date(row.changed || row.when)].join(" · ");
  const scopeText = (item) =>
    PA.t(`learned_why_scope_${item.gap}`, { lang: langName(item.lang || (data && data.lang)) });

  async function load() {
    const mine = ++seq;
    loading = true;
    render();
    try {
      const query = new URLSearchParams({ tab, limit: String(limit) });
      if (lang) query.set("lang", lang);
      const value = await PA.api(`learned?${query}`);
      if (mine !== seq) return;
      data = value;
      lang = value.lang;
      // A refusal for an item that left this list stays on the card.
      error = "";
      if (openId && !value.items.some((row) => row.id === openId)) {
        error = detailError;
        openId = "";
        detail = null;
        detailError = "";
      }
    } catch (failed) {
      if (mine !== seq) return;
      error = failed.message;
    } finally {
      if (mine === seq) loading = false;
    }
    render();
  }

  async function open(id) {
    detailError = "";
    error = "";
    if (openId === id) {
      openId = "";
      detail = null;
      render();
      return;
    }
    openId = id;
    detail = null;
    render();
    try {
      const value = await PA.api(`learned/item?${new URLSearchParams({ id, lang })}`);
      if (openId === id) detail = value;
    } catch (failed) {
      if (openId === id) detailError = failed.message;
    }
    render();
  }

  async function decide(item, verb) {
    if (busy) return;
    if (verb === "discard" && !(await PA.ask(PA.t("learned_ask_discard"), PA.t("learned_discard"))))
      return;
    if (
      verb === "keep" &&
      item.replaces &&
      !(await PA.ask(
        PA.t("learned_ask_replace", { text: item.replaces }),
        PA.t("learned_ask_replace_yes"),
      ))
    )
      return;
    busy = verb;
    detailError = "";
    render();
    const done =
      verb === "discard"
        ? "learned_done_discard"
        : verb === "undo"
          ? "learned_done_undo"
          : item.gap === "lang"
            ? "learned_done_keep_lang"
            : item.tab === "undone"
              ? "learned_done_back"
              : "learned_done_keep";
    try {
      const value = await PA.api("learned/decide", { id: item.id, action: verb, lang });
      // Follow the item to where it now is, still open, so its new state shows.
      tab = value.tab || tab;
      openId = value.id;
      detail = value;
      limit = PAGE;
      PA.toast(PA.t(done, { lang: langName(item.lang) }));
    } catch (failed) {
      detailError = failed.message;
    } finally {
      busy = "";
    }
    await load();
    list.querySelector(".learned-item.open")?.scrollIntoView({ block: "nearest" });
  }

  function line(key, text, cls) {
    const row = make("div", `change-line ${cls}`);
    row.append(make("span", "label", PA.t(key)), make("p", "", text));
    return row;
  }

  function words(item) {
    const body = make("div", "change-body");
    if (item.kind === "wording") {
      body.append(line("learned_said", item.said, "was"), line("learned_instead", item.better, "now"));
      if (item.lesson) body.append(line("learned_lesson", item.lesson, "lesson"));
    } else body.append(make("p", "change-reply", item.said));
    return body;
  }

  function block(key) {
    const part = make("div", "learned-block");
    part.append(make("h4", "", PA.t(key)));
    return part;
  }

  function waiting(item) {
    const info = item.waiting;
    const part = block("learned_why_title");
    const left = {
      events: Math.max(0, info.needEvents - info.events),
      speakers: Math.max(0, info.needSpeakers - info.speakers),
    };
    const why =
      info.key === "scope"
        ? scopeText(item)
        : PA.t(`learned_why_${info.key}`, { n: String(left[info.key] ?? "") });
    part.append(make("p", "learned-why", why));
    if (info.key === "scope" && item.gap !== "lang") return part;
    const rules = make("ul", "learned-rules");
    const rule = (key, have, need, ok) => {
      const li = make("li", ok ? "ok" : "", PA.t(key, { have: String(have), need: String(need) }));
      rules.append(li);
    };
    if (info.canBeStrong)
      rule("learned_rule_strong", info.strong, info.needStrong, info.strong >= info.needStrong);
    rule("learned_rule_events", info.events, info.needEvents, info.events >= info.needEvents);
    rule("learned_rule_speakers", info.speakers, info.needSpeakers, info.speakersOk);
    part.append(rules);
    if (info.stale)
      part.append(
        make(
          "p",
          "field-note",
          PA.t("learned_rule_stale", { n: String(info.stale), days: String(info.maxAgeDays) }),
        ),
      );
    return part;
  }

  function reasonText(why) {
    if (!why || !why.key) return "";
    if (why.key === "note") return PA.t("learned_r_note", { text: why.text });
    return PA.t(`learned_r_${why.key}`, { n: why.n });
  }

  function history(item) {
    const part = block("learned_history");
    const rows = make("ol", "learned-history");
    const add = (label, when, extra) => {
      const li = make("li");
      li.append(make("strong", "", label));
      li.append(make("span", "", [...extra, date(when)].filter(Boolean).join(" · ")));
      rows.append(li);
    };
    add(PA.t("learned_h_picked"), item.when, []);
    for (const step of item.history)
      add(PA.t(`learned_h_${step.tab || "in_use"}`), step.when, [
        PA.t(`learned_by_${step.by}`),
        reasonText(step.why),
      ]);
    part.append(rows);
    return part;
  }

  function evidence(item) {
    const part = block("learned_evidence");
    if (!item.events.length) part.append(make("p", "field-note", PA.t("learned_evidence_none")));
    const rows = make("ul", "learned-events");
    for (const ev of item.events) {
      const li = make("li");
      const self = ev.what === "self_eval" || ev.what === "self_review";
      const who = self ? PA.t("learned_itself") : ev.who || PA.t("learned_someone");
      const head = make("div", "learned-event-head");
      head.append(make("strong", "", who));
      const what = KNOWN_WHAT.includes(ev.what) ? PA.t(`learned_what_${ev.what}`) : "";
      head.append(make("span", "", [what, date(ev.when)].filter(Boolean).join(" · ")));
      li.append(head);
      if (ev.said) li.append(make("p", "learned-quote", ev.said));
      if (ev.better) li.append(make("p", "learned-small", PA.t("learned_ev_better", { text: ev.better })));
      if (ev.reading) li.append(make("p", "learned-small", PA.t("learned_ev_reading", { text: ev.reading })));
      const tags = make("div", "learned-tags");
      tags.append(make("span", ev.counts ? "tag ok" : "tag", PA.t(ev.counts ? "learned_counts" : "learned_not_counts")));
      if (ev.strong) tags.append(make("span", "tag", PA.t("learned_strong")));
      li.append(tags);
      rows.append(li);
    }
    if (item.events.length) part.append(rows);
    if (item.missing > 0)
      part.append(make("p", "field-note", PA.t("learned_evidence_missing", { n: String(item.missing) })));
    return part;
  }

  function action(item, verb, cls) {
    const back = verb === "keep" && item.tab === "undone";
    const label = back ? "learned_back" : `learned_${verb}`;
    const ing = {
      keep: back ? "learned_backing" : "learned_keeping",
      discard: "learned_discarding",
      undo: "learned_undoing",
    }[verb];
    const button = make("button", cls, PA.t(busy === verb ? ing : label));
    button.type = "button";
    button.id = `learned-${verb}`;
    button.dataset.verb = verb;
    button.disabled = Boolean(busy);
    button.addEventListener("click", () => decide(item, verb));
    return button;
  }

  function full(item) {
    const box = make("div", "learned-detail");
    box.id = "learned-detail";
    const last = item.history[item.history.length - 1];
    // An item the character would not use is never described as in use.
    if (item.tab !== "waiting" && !(item.gap && item.tab === "in_use"))
      box.append(
        make("p", "learned-status", PA.t(`learned_now_${item.tab}`, { when: date(last ? last.when : item.when) })),
      );
    // Pending items explain the scope under their reason instead.
    if (item.gap && item.tab !== "waiting") box.append(make("p", "learned-status learned-out", scopeText(item)));
    if (item.replacedBy) box.append(make("p", "learned-small", PA.t("learned_replaced_by", { text: item.replacedBy })));
    if (item.waiting) box.append(waiting(item));
    if (item.context.length) {
      const part = block("learned_context");
      const rows = make("ul", "learned-context");
      for (const text of item.context) rows.append(make("li", "", text));
      part.append(rows);
      box.append(part);
    }
    box.append(evidence(item), history(item));
    if (item.replaces && item.actions.includes("keep"))
      box.append(make("p", "field-note", PA.t("learned_replaces", { text: item.replaces })));
    const buttons = make("div", "change-actions learned-actions");
    if (item.actions.includes("keep")) buttons.append(action(item, "keep", "primary small"));
    if (item.actions.includes("undo")) buttons.append(action(item, "undo", "secondary"));
    if (item.actions.includes("discard")) buttons.append(action(item, "discard", "quiet"));
    if (buttons.childElementCount) box.append(buttons);
    return box;
  }

  function row(item) {
    const li = make("li", `learned-item${item.id === openId ? " open" : ""}`);
    const head = make("button", "learned-row");
    head.type = "button";
    head.id = `learned-row-${item.id}`;
    head.dataset.id = item.id;
    head.setAttribute("aria-expanded", String(item.id === openId));
    const top = make("span", "learned-row-top");
    const kind = make("span", "change-kind", PA.t(item.kind === "wording" ? "learned_wording" : "learned_repeat"));
    if (item.gap) kind.append(make("span", "learned-gap", PA.t(`learned_gap_${item.gap}`)));
    top.append(kind, make("small", "", meta(item)));
    head.append(top, make("span", "learned-row-text", item.kind === "wording" ? item.better : item.said));
    head.addEventListener("click", () => open(item.id));
    li.append(head);
    if (item.id === openId) {
      const shown = detail && detail.id === item.id ? detail : null;
      if (shown) {
        li.append(words(shown));
        li.append(full(shown));
      } else if (!detailError) li.append(make("p", "field-note", PA.t("learned_loading")));
      if (detailError) {
        const said = make("p", "error", PA.t(detailError));
        said.setAttribute("role", "alert");
        li.append(said);
      }
    }
    return li;
  }

  function summary(totals, idle) {
    if (data.lang !== data.current) return PA.t("learned_sum_other", { lang: langName(data.lang) });
    const all = Object.values(totals).reduce((a, b) => a + b, 0);
    if (!all) return PA.t("learned_sum_none");
    const text = PA.t("learned_sum", {
      inUse: String(totals.in_use - idle.in_use),
      chats: String(data.chats),
      waiting: String(totals.waiting - idle.waiting),
    });
    const unused = Object.values(idle).reduce((a, b) => a + b, 0);
    return unused ? `${text}${zh() ? "" : " "}${PA.t("learned_sum_idle", { n: String(unused) })}` : text;
  }

  function draw() {
    title.textContent = PA.t("learned_title");
    lead.textContent = PA.t("learned_lead");
    failure.hidden = !error;
    failure.textContent = error ? PA.t(error) : "";
    if (!data) {
      sum.textContent = loading ? PA.t("learned_loading") : "";
      for (const node of [running, langRow, langNote, tabs, hint, list, empty, more]) node.hidden = true;
      return;
    }
    const totals = data.totals;
    const idle = data.idle || {};
    const all = Object.values(totals).reduce((a, b) => a + b, 0);
    sum.textContent = summary(totals, idle);
    running.hidden = data.running;
    running.textContent = PA.t("learned_not_running");
    const others = data.langs.filter((pool) => pool.code !== data.lang && pool.count);
    langRow.hidden = data.langs.length < 2;
    langLabel.textContent = PA.t("learned_lang_label");
    langPick.replaceChildren(
      ...data.langs.map((pool) => {
        const option = make(
          "option",
          "",
          pool.current ? PA.t("learned_lang_now", { lang: langName(pool.code) }) : langName(pool.code),
        );
        option.value = pool.code;
        return option;
      }),
    );
    langPick.value = data.lang;
    const elsewhere = others.reduce((a, pool) => a + pool.count, 0);
    langNote.hidden = !elsewhere || data.lang !== data.current;
    langNote.textContent = PA.t("learned_lang_note", { n: String(elsewhere) });
    tabs.hidden = !all;
    tabs.replaceChildren(
      ...TABS.map((name) => {
        const button = make("button", `learned-tab${name === tab ? " active" : ""}`);
        button.type = "button";
        button.id = `learned-tab-${name}`;
        button.dataset.tab = name;
        button.setAttribute("role", "tab");
        button.setAttribute("aria-selected", String(name === tab));
        button.append(make("span", "", PA.t(`learned_tab_${name}`)));
        const waits = name === "waiting" && totals.waiting - (idle.waiting || 0) > 0;
        button.append(make("span", `count${waits ? " review" : ""}`, String(totals[name])));
        button.addEventListener("click", () => {
          if (tab === name) return;
          tab = name;
          limit = PAGE;
          error = "";
          openId = "";
          detail = null;
          load();
        });
        return button;
      }),
    );
    hint.hidden = !all;
    hint.textContent = PA.t(`learned_hint_${tab}`);
    const items = data.tab === tab ? data.items : [];
    list.hidden = !all || !items.length;
    const scroll = window.scrollY;
    list.replaceChildren(...items.map(row));
    window.scrollTo(0, scroll);
    empty.hidden = !all || Boolean(items.length) || loading;
    empty.textContent = PA.t(`learned_empty_${tab}`);
    more.hidden = !all || data.count <= items.length;
    more.disabled = loading;
    more.textContent = PA.t(loading ? "learned_loading" : "learned_more");
  }

  function render() {
    draw();
    keepFocus();
  }

  langPick.addEventListener("change", () => {
    lang = langPick.value;
    limit = PAGE;
    openId = "";
    detail = null;
    load();
  });
  more.addEventListener("click", () => {
    limit += PAGE;
    load();
  });
  PA.onShow("activity", load);
  PA.onLanguage(render);
  render();
})();
