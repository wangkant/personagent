// The runtime panel: keep running behind the window, and update from inside the app.
PA.strings({
  en: {
    runtime_bgTitle: "Run in the background",
    runtime_bgCheck: "Keep running after the window is closed",
    runtime_bgHint: "The window moves to the notification area at the bottom right, and the character keeps answering. Open or quit personagent from its icon there.",
    runtime_bgOnlyWindow: "This is available in the app window on Windows. Here, personagent stops when it is closed.",
    runtime_bgHide: "Move to the background now",
    runtime_bgSaved: "Saved. Closing the window now keeps personagent running.",
    runtime_bgOff: "Saved. Closing the window now quits personagent.",
    runtime_background_unavailable: "The notification-area icon is not available here.",
    runtime_verTitle: "Version and updates",
    runtime_verNow: "Current version: {version}.",
    runtime_verLatest: "This is the latest version.",
    runtime_verNew: "Version {version} is available.",
    runtime_verUnknown: "The last check could not reach the update server.",
    runtime_verChecked: "Last checked: {when}.",
    runtime_verNever: "No check has been made yet.",
    runtime_check: "Check for updates",
    runtime_checking: "Checking…",
    runtime_notes: "Release notes",
    runtime_update: "Update and reopen",
    runtime_updating: "Updating…",
    runtime_updateAsk: "personagent will close, update (about one minute) and reopen automatically. The character will not answer during the update.",
    runtime_updateYes: "Update",
    runtime_updateGoing: "Updating. The window will reopen automatically.",
    runtime_update_zip: "This copy was unpacked from a source ZIP and is updated manually: download the new version from the release page.",
    runtime_update_uvx: "This copy runs through uvx, which fetches the new version the next time it is started with this command:",
    runtime_update_tool_missing: "The tool that installed this copy was not found. Run this command manually:",
    runtime_update_clone_changed: "This folder contains local changes. Update it manually:",
    runtime_update_none: "No newer version is available.",
    runtime_update_not_started: "The update could not be started. personagent was left unchanged.",
    runtime_doneOk: "Updated from {from} to {version}.",
    runtime_doneFail: "The update did not complete. The previous version has been reopened.",
    runtime_log: "Show log",
    runtime_logFailed: "The log could not be read.",
    runtime_seen: "Dismiss",
    runtime_useTitle: "Model use",
    runtime_useToday: "Today — requests: {calls}; tokens: {tokens}; cost: {cost}.",
    runtime_useWeek: "Last 7 days — requests: {calls}; tokens: {tokens}; cost: {cost}.",
    runtime_useNoCost: "not reported by the provider",
    runtime_useNone: "No model requests have been recorded yet. The figures are counted on this computer from what the model service reports.",
  },
  zh: {
    runtime_bgTitle: "后台运行",
    runtime_bgCheck: "关闭窗口后继续运行",
    runtime_bgHint: "窗口将收纳至屏幕右下角的通知区域，角色继续回复消息。可通过该处的图标重新打开或退出 personagent。",
    runtime_bgOnlyWindow: "此功能仅在 Windows 的应用窗口中提供。在当前环境下，关闭 personagent 即停止运行。",
    runtime_bgHide: "立即转入后台",
    runtime_bgSaved: "已保存。关闭窗口后 personagent 将继续运行。",
    runtime_bgOff: "已保存。关闭窗口即退出 personagent。",
    runtime_background_unavailable: "当前环境不支持通知区域图标。",
    runtime_verTitle: "版本与更新",
    runtime_verNow: "当前版本：{version}。",
    runtime_verLatest: "已是最新版本。",
    runtime_verNew: "可更新至 {version}。",
    runtime_verUnknown: "上次检查未能连接到更新服务器。",
    runtime_verChecked: "上次检查时间：{when}。",
    runtime_verNever: "尚未检查更新。",
    runtime_check: "检查更新",
    runtime_checking: "正在检查…",
    runtime_notes: "更新说明",
    runtime_update: "更新并重新打开",
    runtime_updating: "正在更新…",
    runtime_updateAsk: "personagent 将关闭并更新（约一分钟），完成后自动重新打开。更新期间角色不会回复消息。",
    runtime_updateYes: "更新",
    runtime_updateGoing: "正在更新，窗口将自动重新打开。",
    runtime_update_zip: "当前安装来自源码压缩包，需手动更新：请前往发布页面下载新版本。",
    runtime_update_uvx: "当前通过 uvx 运行，下次使用以下命令启动时将自动获取新版本：",
    runtime_update_tool_missing: "未找到安装本程序所用的工具，请手动运行以下命令：",
    runtime_update_clone_changed: "此文件夹包含本地修改，请手动更新：",
    runtime_update_none: "没有可安装的新版本。",
    runtime_update_not_started: "更新未能启动，personagent 保持原状。",
    runtime_doneOk: "已从 {from} 更新至 {version}。",
    runtime_doneFail: "更新未完成，已重新打开原版本。",
    runtime_log: "查看日志",
    runtime_logFailed: "无法读取日志。",
    runtime_seen: "关闭提示",
    runtime_useTitle: "模型用量",
    runtime_useToday: "今日——请求：{calls} 次；Token：{tokens} 个；费用：{cost}。",
    runtime_useWeek: "近 7 日——请求：{calls} 次；Token：{tokens} 个；费用：{cost}。",
    runtime_useNoCost: "模型服务未提供",
    runtime_useNone: "尚无模型请求记录。数据由本机根据模型服务返回的信息统计。",
  },
});
(() => {
  const root = PA.$("runtime-root");
  // Refusals this panel has its own sentence for; any other code is the page's.
  const OWN = new Set(["background_unavailable", "update_none", "update_tool_missing",
    "update_clone_changed", "update_not_started"]);
  let info = null,
    busy = "",
    logLines = null,
    logFailed = false;
  const say = (code) => PA.t(OWN.has(code) ? `runtime_${code}` : code);
  const make = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const button = (cls, text, onClick, id) => {
    const node = make("button", cls, text);
    node.type = "button";
    node.id = id;
    node.addEventListener("click", onClick);
    return node;
  };
  async function call(name, path, payload) {
    busy = name;
    render();
    try {
      const answer = await PA.api(path, payload);
      if (answer && "version" in answer) info = answer;
      return answer;
    } catch (error) {
      PA.toast(say(error.message));
      return null;
    } finally {
      busy = "";
      render();
    }
  }
  function background() {
    const card = make("div", "card side-card runtime-card");
    card.append(make("h2", "", PA.t("runtime_bgTitle")));
    if (!info.canHide) {
      card.append(make("p", "field-note", PA.t("runtime_bgOnlyWindow")));
      return card;
    }
    const label = make("label", "check");
    const box = make("input");
    box.type = "checkbox";
    box.id = "runtime-background";
    box.checked = info.background;
    box.disabled = busy === "background";
    box.addEventListener("change", async () => {
      const answer = await call("background", "runtime/background", { on: box.checked });
      if (answer) PA.toast(PA.t(answer.background ? "runtime_bgSaved" : "runtime_bgOff"));
    });
    label.append(box, make("span", "", PA.t("runtime_bgCheck")));
    card.append(label, make("p", "field-note", PA.t("runtime_bgHint")));
    const actions = make("div", "card-actions runtime-actions");
    const hide = button("quiet", PA.t("runtime_bgHide"), () => call("hide", "runtime/hide", {}), "runtime-hide");
    hide.disabled = busy === "hide";
    actions.append(hide);
    card.append(actions);
    return card;
  }
  function done() {
    const last = info.lastUpdate;
    const box = make("div", `runtime-done ${last.ok ? "ok" : "failed"}`);
    box.id = "runtime-done";
    box.setAttribute("role", last.ok ? "status" : "alert");
    box.append(
      make("p", "", last.ok
        ? PA.t("runtime_doneOk", { from: last.from, version: info.version })
        : PA.t("runtime_doneFail")),
    );
    const actions = make("div", "runtime-actions");
    if (!last.ok)
      actions.append(button("quiet", PA.t("runtime_log"), async () => {
        try {
          logLines = (await PA.api("runtime/update/log")).lines;
          logFailed = false;
        } catch (error) {
          logFailed = true;
        }
        render();
      }, "runtime-log"));
    actions.append(button("quiet", PA.t("runtime_seen"), async () => {
      try {
        await PA.api("runtime/update/seen", {});
      } catch (error) {
        return PA.toast(say(error.message));
      }
      logLines = null;
      logFailed = false;
      info.lastUpdate = null;
      render();
    }, "runtime-seen"));
    box.append(actions);
    if (logFailed) box.append(make("p", "error", PA.t("runtime_logFailed")));
    if (logLines) {
      const log = make("pre", "runtime-log", logLines.join("\n"));
      log.id = "runtime-log-text";
      box.append(log);
    }
    return box;
  }
  function version() {
    const card = make("div", "card side-card runtime-card");
    card.append(make("h2", "", PA.t("runtime_verTitle")));
    if (info.lastUpdate) card.append(done());
    const when = info.checked
      ? PA.t("runtime_verChecked", { when: new Date(info.checked * 1000).toLocaleString(PA.lang === "zh" ? "zh-CN" : PA.lang) })
      : PA.t("runtime_verNever");
    const line = make("p", "runtime-line");
    line.id = "runtime-version";
    line.setAttribute("role", "status");
    line.append(
      make("span", "", PA.t("runtime_verNow", { version: info.version }) + " "),
      make("strong", info.update ? "runtime-new" : "", info.update
        ? PA.t("runtime_verNew", { version: info.update.version })
        // Neither a check that never reached the server nor one not yet made says "up to date".
        : info.checkFailed ? PA.t("runtime_verUnknown") : info.checked ? PA.t("runtime_verLatest") : ""),
    );
    card.append(line, make("p", "field-note", when));
    if (info.update && info.updateBlocked) {
      const why = info.updateBlocked === "update_by_hand"
        ? `runtime_update_${info.updateKind === "uvx" ? "uvx" : "zip"}`
        : `runtime_${info.updateBlocked}`;
      card.append(make("p", "field-note", PA.t(why)));
      if (info.update.command) {
        const command = make("code", "runtime-command", info.update.command);
        command.id = "runtime-command";
        card.append(command);
      }
    }
    const actions = make("div", "card-actions runtime-actions");
    const check = button("quiet", PA.t(busy === "check" ? "runtime_checking" : "runtime_check"),
      () => call("check", "runtime/check", {}), "runtime-check");
    check.disabled = Boolean(busy);
    actions.append(check);
    if (info.update) {
      const notes = make("a", "", PA.t("runtime_notes"));
      notes.id = "runtime-notes";
      notes.href = info.update.url;
      notes.target = "_blank";
      notes.rel = "noopener noreferrer";
      actions.append(notes);
      if (!info.updateBlocked) {
        const go = button("primary", PA.t(busy === "update" ? "runtime_updating" : "runtime_update"), async () => {
          if (!(await PA.ask(PA.t("runtime_updateAsk"), PA.t("runtime_updateYes")))) return;
          if (await call("update", "runtime/update", {})) {
            // Stays busy: the window is about to close.
            busy = "update";
            render();
            PA.toast(PA.t("runtime_updateGoing"));
          }
        }, "runtime-update");
        go.disabled = Boolean(busy);
        actions.append(go);
      }
    }
    card.append(actions);
    return card;
  }
  function spent() {
    const card = make("div", "card side-card runtime-card");
    card.append(make("h2", "", PA.t("runtime_useTitle")));
    const use = info.usage;
    const box = make("div", "runtime-use");
    box.id = "runtime-use";
    if (!use || !use.week || !use.week.calls) {
      box.append(make("p", "field-note", PA.t("runtime_useNone")));
      card.append(box);
      return card;
    }
    const locale = PA.lang === "zh" ? "zh-CN" : PA.lang;
    const count = (n) => new Intl.NumberFormat(locale).format(n || 0);
    const money = (n) =>
      n === null || n === undefined
        ? PA.t("runtime_useNoCost")
        : new Intl.NumberFormat(locale, { style: "currency", currency: "USD", maximumFractionDigits: 4 }).format(n);
    const line = (key, total) =>
      make("p", "runtime-line", PA.t(key, { calls: count(total.calls), tokens: count(total.tokens), cost: money(total.cost) }));
    box.append(line("runtime_useToday", use.today), line("runtime_useWeek", use.week));
    card.append(box);
    return card;
  }
  function render() {
    if (!info) return;
    // The control in use is rebuilt with the rest: give it the focus back.
    const held = root.contains(document.activeElement) ? document.activeElement.id : "";
    root.replaceChildren(background(), version(), spent());
    if (held) document.getElementById(held)?.focus();
  }
  async function load() {
    try {
      info = await PA.api("runtime");
      render();
    } catch (error) {
      // The view stays as it was; the page's own status line says why.
    }
  }
  PA.onShow("app", load);
  PA.onLanguage(render);
})();
