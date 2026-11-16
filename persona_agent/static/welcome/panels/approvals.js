// The approvals panel: new chats waiting for the admin, under the connected platforms. See PA at the end of welcome.js.
PA.strings({
  en: {
    approvals_title: "New chats waiting for approval",
    approvals_hint: "Approve a chat and the character answers it from now on. To make your own account the admin, select “This is me” on your own message and type the code the character sent you there.",
    approvals_dm: "Direct message",
    approvals_group: "Group",
    approvals_said: "First words: “{words}”",
    approvals_approve: "Approve",
    approvals_admin: "This is me",
    approvals_decline: "Decline",
    approvals_approving: "Approving…",
    approvals_declining: "Declining…",
    approvals_approved: "Approved. The character answers this chat from now on.",
    approvals_admin_done: "Approved. This account is now your admin account on {platform}.",
    approvals_declined_done: "Declined. This chat gets no answer and makes no new request.",
    approvals_admin_ask: "Type the code the character sent to your own chat on {platform}. Only the person who reads that chat has it.",
    approvals_admin_yes: "Make me the admin",
    approvals_declined: "Declined chats: {n}",
    approvals_declined_hint: "A declined chat gets no answer and makes no new request. Undo lets it ask again.",
    approvals_approved_list: "Approved chats: {n}",
    approvals_approved_hint: "These chats are answered in addition to the reply settings, also when approval is turned off. Undo removes the approval; the chat then asks again.",
    approvals_admin_tag: "Admin",
    approvals_undo: "Undo",
    approvals_undoing: "Undoing…",
    approvals_undone: "Done. The chat can ask for approval again.",
    approvals_full: "The waiting list for {platform} is full. Decide some requests to make room for new ones.",
    approvals_unverified: "This IRC sender is not identified with the network's services, so anyone could use the nick, and it cannot be made an admin. Identify with NickServ, then write again.",
    approvals_unverified_ask: "This IRC sender is not identified with the network's services: whoever uses this nick next is answered too. Approve anyway?",
    approvals_code_mismatch: "This is not the code of this request. Type the code the character sent to this chat.",
    approvals_env_locked: "ACCESS_APPROVAL_PLATFORMS is set in the environment, which overrides .env, so it cannot be changed here. Change it where the environment is set.",
    approvals_load_failed: "The waiting chats could not be read.",
    approvals_gone: "This request is no longer waiting: it expired or was decided elsewhere.",
    approvals_bad_request: "The request could not be read. Reload the page and try again.",
    approvals_write_failed: "The approvals file could not be written. Close any program that is using it, then try again.",
    approvals_not_dm: "Only the sender of a direct message can be made an admin.",
  },
  zh: {
    approvals_title: "等待批准的新对话",
    approvals_hint: "批准后，角色此后会回复该对话。如需将你自己的账号设为管理员，请在你本人发送的那条消息旁选择「这是我」，并输入角色在该对话中发给你的代码。",
    approvals_dm: "私聊",
    approvals_group: "群聊",
    approvals_said: "首条消息：“{words}”",
    approvals_approve: "批准",
    approvals_admin: "这是我",
    approvals_decline: "拒绝",
    approvals_approving: "正在批准…",
    approvals_declining: "正在拒绝…",
    approvals_approved: "已批准。角色此后会回复该对话。",
    approvals_admin_done: "已批准。该账号现为你在 {platform} 上的管理员账号。",
    approvals_declined_done: "已拒绝。该对话不会得到回复，也不会再次提出申请。",
    approvals_admin_ask: "请输入角色在你本人于 {platform} 上的对话中发送的代码。只有能查看该对话的人才知道这个代码。",
    approvals_admin_yes: "设我为管理员",
    approvals_declined: "已拒绝的对话：{n}",
    approvals_declined_hint: "已拒绝的对话不会得到回复，也不会再次提出申请。撤销后可再次申请。",
    approvals_approved_list: "已批准的对话：{n}",
    approvals_approved_hint: "除回复设置外，角色还会回复这些对话，关闭批准后也是如此。撤销即取消批准，该对话此后需重新申请。",
    approvals_admin_tag: "管理员",
    approvals_undo: "撤销",
    approvals_undoing: "正在撤销…",
    approvals_undone: "已撤销。该对话可以再次申请批准。",
    approvals_full: "{platform} 的等待列表已满。请先处理部分申请，以便接收新的申请。",
    approvals_unverified: "该 IRC 发送者未在网络服务中登录身份，任何人都可以使用这个昵称，因此不能设为管理员。请先通过 NickServ 登录身份，再重新发送消息。",
    approvals_unverified_ask: "该 IRC 发送者未在网络服务中登录身份：此后使用这个昵称的任何人也会得到回复。仍要批准吗？",
    approvals_code_mismatch: "这不是该申请的代码。请输入角色在该对话中发送的代码。",
    approvals_env_locked: "ACCESS_APPROVAL_PLATFORMS 已在环境变量中设置，环境变量优先于 .env，因此无法在此更改。请在设置环境变量的位置修改。",
    approvals_load_failed: "无法读取等待批准的对话。",
    approvals_gone: "该申请已不在等待中：已过期，或已在别处处理。",
    approvals_bad_request: "无法读取该请求。请刷新页面后重试。",
    approvals_write_failed: "无法写入批准记录文件。请关闭正在使用该文件的程序后重试。",
    approvals_not_dm: "只有私聊的发送者才能设为管理员。",
  },
});
(() => {
  const root = PA.$("approvals-root");
  let data = null;
  let loadError = false;
  let error = "";
  // The control being worked: its id and the label it shows meanwhile.
  let busyId = "",
    busyLabel = "";
  let declinedOpen = false,
    approvedOpen = false;
  // The row whose code is being typed for This is me, and what was typed.
  let typing = { id: "", value: "" };
  let shown = "";
  let asked = "";
  let returnTo = "";

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  // A DOM id for a chat id, which may hold any character the platform allows.
  const key = (id) => Array.from(new TextEncoder().encode(id), (b) => b.toString(16).padStart(2, "0")).join("");

  async function load() {
    try {
      data = await PA.api("approvals");
      loadError = false;
    } catch {
      loadError = true;
    }
    render();
  }

  // Reads again when the count of waiting chats changes, so the page polls nothing more.
  PA.onState((state) => {
    const now = JSON.stringify(state.approvalsWaiting || {}) + JSON.stringify(state.platforms || []);
    if (now === asked) return;
    asked = now;
    load();
  });
  PA.onShow("platforms", load);
  PA.onLanguage(() => {
    shown = "";
    render();
  });

  async function act(id, label, work, done, onMismatch = "") {
    busyId = id;
    busyLabel = label;
    returnTo = id;
    error = "";
    render();
    try {
      data = await work();
      if (done) PA.toast(done);
      if (typing.id && !data.waiting.some((w) => w.id === typing.id)) typing = { id: "", value: "" };
    } catch (failure) {
      error = failure.message;
      if (error === "approvals_gone") await load();
    } finally {
      busyId = busyLabel = "";
      // A disabled button drops the focus while it works: it goes back afterwards.
      returnTo = error === "approvals_code_mismatch" && onMismatch ? onMismatch : id;
      render();
      PA.refresh?.();
    }
  }

  async function decide(item, action, code = "") {
    if (action === "approve" && item.unverified
      && !(await PA.ask(PA.t("approvals_unverified_ask"), PA.t("approvals_approve")))) return;
    const platform = PA.platformName(item.platform);
    const done = {
      approve: PA.t("approvals_approved"),
      admin: PA.t("approvals_admin_done", { platform }),
      decline: PA.t("approvals_declined_done"),
    }[action];
    const id = action === "admin" ? `approvals-confirm-${key(item.id)}` : `approvals-${action}-${key(item.id)}`;
    return act(id, action === "decline" ? "approvals_declining" : "approvals_approving",
      () => PA.api("approvals/decide", { id: item.id, action, code }), done, `approvals-code-${key(item.id)}`);
  }

  function button(id, className, label, onClick) {
    const node = make("button", className, PA.t(busyId === id ? busyLabel : label));
    node.type = "button";
    node.id = id;
    node.disabled = Boolean(busyId);
    node.setAttribute("aria-busy", String(busyId === id));
    node.addEventListener("click", onClick);
    return node;
  }

  function who(item) {
    // Platform data, shown as text only; the id always, so that a borrowed name cannot pass for someone.
    const line = make("div", "approval-who");
    const name = make("strong", "", item.name || item.id);
    name.id = `approval-name-${key(item.id)}`;
    line.append(PA.badge(item.platform, "small"), name);
    if (item.name) line.append(make("code", "approval-id", item.id));
    if (item.admin) line.append(make("span", "approval-tag", PA.t("approvals_admin_tag")));
    const meta = [PA.platformName(item.platform), PA.t(item.kind === "dm" ? "approvals_dm" : "approvals_group"),
      PA.ago(item.at)];
    line.append(make("span", "approval-meta", meta.join(" · ")));
    return line;
  }

  function codeForm(item) {
    // This is me rests on the code: only the chat that received it can tell it.
    const form = make("form", "approval-code");
    const field = `approvals-code-${key(item.id)}`;
    const label = make("label", "", PA.t("approvals_admin_ask", { platform: PA.platformName(item.platform) }));
    label.htmlFor = field;
    const input = make("input");
    Object.assign(input, { id: field, value: typing.value, maxLength: 12, autocomplete: "off", spellcheck: false });
    input.setAttribute("autocapitalize", "characters");
    input.addEventListener("input", () => (typing.value = input.value));
    const id = `approvals-admin-${key(item.id)}`;
    const yes = button(`approvals-confirm-${key(item.id)}`, "secondary", "approvals_admin_yes", () => {});
    yes.type = "submit";
    yes.disabled = Boolean(busyId) || !typing.value.trim();
    input.addEventListener("input", () => (yes.disabled = Boolean(busyId) || !input.value.trim()));
    const no = button(`approvals-cancel-${key(item.id)}`, "quiet", "cancel", () => {
      typing = { id: "", value: "" };
      returnTo = id;
      render();
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (input.value.trim()) decide(item, "admin", input.value);
    });
    const line = make("div", "approval-code-line");
    line.append(input, yes, no);
    form.append(label, line);
    return form;
  }

  function waitingItem(item) {
    const row = make("li", "approval-item");
    row.append(who(item));
    if (item.words) row.append(make("p", "approval-words", PA.t("approvals_said", { words: item.words })));
    if (item.unverified) row.append(make("p", "approval-warn", PA.t("approvals_unverified")));
    const actions = make("div", "approval-actions");
    const approve = button(`approvals-approve-${key(item.id)}`, "secondary", "approvals_approve",
      () => decide(item, "approve"));
    const admin = item.kind === "dm" && !item.unverified
      ? button(`approvals-admin-${key(item.id)}`, "secondary", "approvals_admin", () => {
        typing = { id: item.id, value: "" };
        returnTo = `approvals-code-${key(item.id)}`;
        render();
      })
      : null;
    if (admin) admin.setAttribute("aria-expanded", String(typing.id === item.id));
    const decline = button(`approvals-decline-${key(item.id)}`, "quiet", "approvals_decline",
      () => decide(item, "decline"));
    // With no admin on that platform yet, the person at the page is the likeliest sender.
    if (admin && !item.hasAdmin) actions.append(admin, approve, decline);
    else actions.append(approve, ...(admin ? [admin] : []), decline);
    for (const node of actions.children) node.setAttribute("aria-describedby", `approval-name-${key(item.id)}`);
    row.append(actions);
    if (typing.id === item.id) row.append(codeForm(item));
    return row;
  }

  function decidedList(items, open, toggle, title, hint) {
    const details = make("details", "approvals-decided");
    details.open = open;
    details.addEventListener("toggle", () => toggle(details.open));
    details.append(make("summary", "", PA.t(title, { n: String(items.length) })), make("p", "field-note", PA.t(hint)));
    const list = make("ul", "approvals-list");
    for (const item of items) {
      const row = make("li", "approval-item");
      row.append(who(item));
      const actions = make("div", "approval-actions");
      const id = `approvals-undo-${key(item.id)}`;
      const undo = button(id, "quiet", "approvals_undo", () =>
        act(id, "approvals_undoing", () => PA.api("approvals/undo", { id: item.id }), PA.t("approvals_undone")));
      undo.setAttribute("aria-label", `${PA.t("approvals_undo")}: ${item.name || item.id}`);
      actions.append(undo);
      row.append(actions);
      list.append(row);
    }
    details.append(list);
    return details;
  }

  function render() {
    const now = JSON.stringify([PA.lang, data, loadError, error, busyId, declinedOpen, approvedOpen, typing.id]);
    if (now === shown) return;
    shown = now;
    const parts = [];
    if (error) {
      const box = make("div", "error", PA.t(error));
      box.setAttribute("role", "alert");
      parts.push(box);
    }
    if (loadError && !data) {
      const failed = make("p", "error", PA.t("approvals_load_failed"));
      failed.setAttribute("role", "alert");
      parts.push(failed);
    }
    if (data?.waiting.length) {
      const head = make("div", "approvals-head");
      head.append(make("h3", "", PA.t("approvals_title")));
      parts.push(head, make("p", "field-note approvals-hint", PA.t("approvals_hint")));
      const full = [...new Set((data.full || []).map((f) => f.split(":")[0]))];
      for (const platform of full)
        parts.push(make("p", "approval-warn", PA.t("approvals_full", { platform: PA.platformName(platform) })));
      const list = make("ul", "approvals-list");
      list.append(...data.waiting.map(waitingItem));
      parts.push(list);
    }
    if (data?.approved?.length)
      parts.push(decidedList(data.approved, approvedOpen, (open) => (approvedOpen = open),
        "approvals_approved_list", "approvals_approved_hint"));
    if (data?.declined.length)
      parts.push(decidedList(data.declined, declinedOpen, (open) => (declinedOpen = open),
        "approvals_declined", "approvals_declined_hint"));
    const active = document.activeElement;
    const keep = returnTo || (active && root.contains(active) ? active.id : "");
    returnTo = "";
    root.hidden = !parts.length;
    root.replaceChildren(...parts);
    // Back on the control the person used, or the next one once a decided request has gone.
    if (keep) (document.getElementById(keep) || root.querySelector("button"))?.focus({ preventScroll: true });
  }
})();
