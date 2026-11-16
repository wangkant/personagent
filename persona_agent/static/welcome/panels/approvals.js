// The approvals panel: new chats waiting for the admin, under the connected platforms. See PA at the end of welcome.js.
PA.strings({
  en: {
    approvals_title: "New chats waiting for approval",
    approvals_hint: "Approve a chat and the character answers it from now on. “This is me” also makes that account your admin account on the platform, without looking up its id.",
    approvals_dm: "Direct message",
    approvals_group: "Group",
    approvals_said: "First words: “{words}”",
    approvals_code: "Code {code}",
    approvals_approve: "Approve",
    approvals_admin: "This is me",
    approvals_decline: "Decline",
    approvals_approving: "Approving…",
    approvals_declining: "Declining…",
    approvals_approved: "Approved. The character answers this chat from now on.",
    approvals_admin_done: "Approved. This account is now your admin account on {platform}.",
    approvals_declined_done: "Declined. This chat gets no answer and makes no new request.",
    approvals_admin_ask: "Make this account your admin account on {platform}? The admin is the person the character is closest to, may manage what it remembers about a group and teaches it directly. Only confirm if you sent this message yourself.",
    approvals_admin_yes: "Yes, this is me",
    approvals_declined: "Declined chats: {n}",
    approvals_declined_hint: "A declined chat gets no answer and makes no new request. Undo lets it ask again.",
    approvals_undo: "Undo",
    approvals_undoing: "Undoing…",
    approvals_undone: "The decline is undone; the chat can ask again.",
    approvals_load_failed: "The waiting chats could not be read.",
    approvals_gone: "This request is no longer waiting: it expired or was decided elsewhere.",
    approvals_bad_request: "The request could not be read. Reload the page and try again.",
    approvals_write_failed: "The settings file could not be written. Close any program that is using it, then try again.",
    approvals_not_dm: "Only the sender of a direct message can be made an admin.",
  },
  zh: {
    approvals_title: "等待批准的新对话",
    approvals_hint: "批准后，角色此后会回复该对话。选择「这是我」还会将该账号设为你在此平台上的管理员账号，无需查找其编号。",
    approvals_dm: "私聊",
    approvals_group: "群聊",
    approvals_said: "首条消息：“{words}”",
    approvals_code: "代码 {code}",
    approvals_approve: "批准",
    approvals_admin: "这是我",
    approvals_decline: "拒绝",
    approvals_approving: "正在批准…",
    approvals_declining: "正在拒绝…",
    approvals_approved: "已批准。角色此后会回复该对话。",
    approvals_admin_done: "已批准。该账号现为你在 {platform} 上的管理员账号。",
    approvals_declined_done: "已拒绝。该对话不会得到回复，也不会再次提出申请。",
    approvals_admin_ask: "是否将该账号设为你在 {platform} 上的管理员账号？管理员是与角色最亲近的人，可以管理角色对群聊的记忆，并可直接教导角色。仅当这条消息由你本人发送时才确认。",
    approvals_admin_yes: "确认，这是我",
    approvals_declined: "已拒绝的对话：{n}",
    approvals_declined_hint: "已拒绝的对话不会得到回复，也不会再次提出申请。撤销后可再次申请。",
    approvals_undo: "撤销",
    approvals_undoing: "正在撤销…",
    approvals_undone: "已撤销拒绝，该对话可以再次申请。",
    approvals_load_failed: "无法读取等待批准的对话。",
    approvals_gone: "该申请已不在等待中：已过期，或已在别处处理。",
    approvals_bad_request: "无法读取该请求。请刷新页面后重试。",
    approvals_write_failed: "无法写入设置文件。请关闭正在使用该文件的程序后重试。",
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
  let declinedOpen = false;
  let shown = "";
  let asked = "";
  let returnTo = "";

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

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
    const key = JSON.stringify(state.approvalsWaiting || {}) + JSON.stringify(state.platforms || []);
    if (key === asked) return;
    asked = key;
    load();
  });
  PA.onShow("platforms", load);
  PA.onLanguage(() => {
    shown = "";
    render();
  });

  async function act(id, label, work, done) {
    busyId = id;
    busyLabel = label;
    returnTo = id;
    error = "";
    render();
    try {
      data = await work();
      if (done) PA.toast(done);
    } catch (failure) {
      error = failure.message;
      if (error === "approvals_gone") await load();
    } finally {
      busyId = busyLabel = "";
      // A disabled button drops the focus while it works: it goes back afterwards.
      returnTo = id;
      render();
      PA.refresh?.();
    }
  }

  function decide(item, action) {
    const platform = PA.platformName(item.platform);
    const done = {
      approve: PA.t("approvals_approved"),
      admin: PA.t("approvals_admin_done", { platform }),
      decline: PA.t("approvals_declined_done"),
    }[action];
    return act(`approvals-${action}-${item.code}`,
      action === "decline" ? "approvals_declining" : "approvals_approving",
      () => PA.api("approvals/decide", { code: item.code, action }), done);
  }

  async function makeAdmin(item) {
    const platform = PA.platformName(item.platform);
    if (!(await PA.ask(PA.t("approvals_admin_ask", { platform }), PA.t("approvals_admin_yes")))) return;
    await decide(item, "admin");
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
    // Platform data, shown as text only.
    const line = make("div", "approval-who");
    line.append(PA.badge(item.platform, "small"), make("strong", "", item.name || item.id));
    const meta = [PA.platformName(item.platform), PA.t(item.kind === "dm" ? "approvals_dm" : "approvals_group"),
      PA.ago(item.at)];
    if (item.code) meta.push(PA.t("approvals_code", { code: item.code }));
    line.append(make("span", "approval-meta", meta.join(" · ")));
    return line;
  }

  function waitingItem(item) {
    const row = make("li", "approval-item");
    row.append(who(item));
    if (item.words) row.append(make("p", "approval-words", PA.t("approvals_said", { words: item.words })));
    const actions = make("div", "approval-actions");
    const approve = button(`approvals-approve-${item.code}`, "secondary", "approvals_approve",
      () => decide(item, "approve"));
    const admin = item.kind === "dm"
      ? button(`approvals-admin-${item.code}`, "secondary", "approvals_admin", () => makeAdmin(item))
      : null;
    const decline = button(`approvals-decline-${item.code}`, "quiet", "approvals_decline",
      () => decide(item, "decline"));
    // With no admin on that platform yet, the person at the page is the likeliest sender.
    if (admin && !item.hasAdmin) actions.append(admin, approve, decline);
    else actions.append(approve, ...(admin ? [admin] : []), decline);
    for (const node of actions.children) node.setAttribute("aria-describedby", `approval-name-${item.code}`);
    row.querySelector("strong").id = `approval-name-${item.code}`;
    row.append(actions);
    return row;
  }

  function declinedList() {
    const details = make("details", "approvals-declined");
    details.open = declinedOpen;
    details.addEventListener("toggle", () => (declinedOpen = details.open));
    const summary = make("summary", "", PA.t("approvals_declined", { n: String(data.declined.length) }));
    summary.id = "approvals-declined-summary";
    details.append(summary, make("p", "field-note", PA.t("approvals_declined_hint")));
    const list = make("ul", "approvals-list");
    data.declined.forEach((item, index) => {
      const row = make("li", "approval-item");
      row.append(who(item));
      const actions = make("div", "approval-actions");
      const undo = button(`approvals-undo-${index}`, "quiet", "approvals_undo", () =>
        act(`approvals-undo-${index}`, "approvals_undoing",
          () => PA.api("approvals/undo", { id: item.id }), PA.t("approvals_undone")));
      undo.setAttribute("aria-label", `${PA.t("approvals_undo")}: ${item.name || item.id}`);
      actions.append(undo);
      row.append(actions);
      list.append(row);
    });
    details.append(list);
    return details;
  }

  function render() {
    const key = JSON.stringify([PA.lang, data, loadError, error, busyId, declinedOpen]);
    if (key === shown) return;
    shown = key;
    const parts = [];
    const any = data && (data.waiting.length || data.declined.length);
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
    if (any) {
      if (data.waiting.length) {
        const head = make("div", "approvals-head");
        head.append(make("h3", "", PA.t("approvals_title")));
        parts.push(head, make("p", "field-note approvals-hint", PA.t("approvals_hint")));
        const list = make("ul", "approvals-list");
        list.append(...data.waiting.map(waitingItem));
        parts.push(list);
      }
      if (data.declined.length) parts.push(declinedList());
    }
    const active = document.activeElement;
    const keep = active && root.contains(active) ? active.id || returnTo : returnTo;
    returnTo = "";
    root.hidden = !parts.length;
    root.replaceChildren(...parts);
    // Back on the control the person used, or the next one once a decided request has gone.
    if (keep) (PA.$(keep) || root.querySelector("button"))?.focus({ preventScroll: true });
  }
})();
