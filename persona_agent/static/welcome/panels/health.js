// The health panel: service checks, settings findings, start failures and logs.
PA.strings({
  en: {
    health_title: "Health check",
    health_hint: "Checks whether each service the character relies on is responding. Each check sends a few short requests and uses a small amount of your model service's quota.",
    health_check: "Run check",
    health_checking: "Checking…",
    health_checking_note: "Checking each service. This usually takes a few seconds and at most about 90 seconds.",
    health_never: "No check has been run yet.",
    health_checked_at: "Checked at {time} {via}.",
    health_via_agent: "through the running character",
    health_via_doctor: "with a separate test run",
    health_reused: "The results are less than one minute old and the settings have not changed, so no new requests were sent.",
    health_verdict_ok: "Every service the character requires is working.",
    health_verdict_partly: "The character can chat, but the following are not working: {names}.",
    health_verdict_nokey: "No chat model has been set up. Add one under Character & settings.",
    health_verdict_key: "The chat model rejected the key. Check the key under Character & settings.",
    health_verdict_limit: "The chat model reports that the quota is used up or that requests are too frequent. Try again later or switch to another model service.",
    health_verdict_missing: "The chat model reports that the model name does not exist. Check the model name under Character & settings.",
    health_verdict_unreachable: "The chat model cannot be reached. Check the network connection and the service address.",
    health_verdict_other: "The chat model did not respond correctly. Check the model settings under Character & settings.",
    health_verdict_bridge: "The QQ bridge (NapCat) is not responding. The character requires it to send and receive messages.",
    health_open_settings: "Open Character & settings",
    health_probe_ledger: "Learning records",
    health_probe_dm: "Private chat replies",
    health_probe_chat: "Group chat replies and tools",
    health_probe_vision: "Image understanding",
    health_probe_eval: "Self-review model",
    health_probe_embeddings: "Memory lookup",
    health_probe_search: "Web search (Tavily)",
    health_probe_onebot: "QQ bridge (NapCat)",
    health_probe_other: "{name}",
    health_ok: "Working",
    health_bad: "Not working",
    health_skipped: "Not set up",
    health_needed: "Required",
    health_ms: "{ms} ms",
    health_details: "Technical details",
    health_ledger_note: "Some records could not be read and were skipped, or the record files are large. No action is needed unless this continues to grow.",
    health_show_skipped: "Show {count} services not set up",
    health_hide_skipped: "Hide services not set up",
    health_fail_agent: "The character is not running. It failed to start or stopped unexpectedly.",
    health_fail_astrbot: "The chat platform (AstrBot) failed to start or stopped unexpectedly.",
    health_fail_direct: "The connection to the platforms has stopped.",
    health_fail_install: "The download or installation did not finish.",
    health_fail_said: "Relevant log entry:",
    health_fail_retired: "The character cannot start because some settings still use names from an earlier version. Rename them below.",
    health_show_log: "Show log",
    health_start_again: "Restart",
    health_starting: "Starting…",
    health_started: "Restarting. This takes a few seconds.",
    health_retired_title: "Settings with old names",
    health_retired_hint: "These settings were renamed in version 1.0. The character cannot start while the old names remain.",
    health_retired_env: "{old} is set outside this app. Change it to {new} where it is set.",
    health_fix: "Rename settings",
    health_fixing: "Renaming…",
    health_fix_ask: "The following settings in .env will be renamed: {names}. Where a new name is already set, the old line will be commented out instead. The current file will first be saved as .env.bak, replacing any earlier backup. If the character is running or failed to start, it will then be restarted.",
    health_fixed: "Updated {count} setting names. The previous file was saved as .env.bak.",
    health_platforms_title: "Platform connections",
    health_platform_failed: "Failed",
    health_platform_connected: "Connected",
    health_platform_connecting: "Connecting",
    health_platform_waiting: "Not started",
    health_platform_error: "The connection stopped because of an error. Connect the platform again. If it continues to fail, see the Platform connections log below.",
    health_since: "since {time}",
    health_reconnect: "Open Connect apps",
    health_findings_title: "Settings to review",
    health_findings_none: "No problems were found in the settings.",
    health_finding_missing_key: "No model key is set, so the character cannot reply.",
    health_finding_bom: "The settings file begins with an invisible byte order mark (BOM), so its first setting is ignored. Save the file again as UTF-8 without BOM.",
    health_finding_unknown: "{key} is not a setting that personagent reads. It may be misspelled.",
    health_finding_dropped: "{key} is no longer used. Its line can be deleted.",
    health_finding_empty: "{key} is empty.",
    health_finding_other: "{key} requires attention.",
    health_level_error: "Error",
    health_level_warn: "Warning",
    health_open_home: "Open the personagent folder",
    health_opening: "Opening…",
    health_opened: "The folder was opened in the file manager.",
    health_logs_title: "Logs",
    health_logs_hint: "The last {count} lines each component wrote while running. Recognizable keys and tokens are hidden, but chat content may appear.",
    health_log_pick: "Log",
    health_log_agent: "Character",
    health_log_astrbot: "Chat platform (AstrBot)",
    health_log_direct: "Platform connections",
    health_log_install: "Downloads and installation",
    health_log_app: "This app",
    health_log_practice: "Practice",
    health_log_update: "Last update",
    health_log_reload: "Reload",
    health_log_loading: "Loading…",
    health_log_empty: "This log is empty.",
    health_log_none: "No logs are available yet. Logs appear after the character or a platform connection has started.",
    health_log_more: "Show more lines",
    health_open_logs: "Open the logs folder",
    health_attention: "Needs attention",
    health_busy: "A check is already running. Wait for it to finish.",
    health_failed: "The check could not be run. Try again. If it continues to fail, see the Character log below.",
    health_invalid_log: "This log is not available.",
    health_open_failed: "The file manager could not be opened. The logs are in runtime/desktop inside the personagent folder.",
    health_open_failed_home: "The file manager could not be opened. The settings file .env is in the personagent folder.",
    health_nothing_to_fix: "No settings need to be renamed.",
  },
  zh: {
    health_title: "运行检查",
    health_hint: "逐项检查角色所依赖的服务当前能否正常响应。每次检查会发送几条简短的请求，消耗少量模型服务额度。",
    health_check: "开始检查",
    health_checking: "正在检查…",
    health_checking_note: "正在逐项检查，通常需要几秒钟，最长约 90 秒。",
    health_never: "尚未进行检查。",
    health_checked_at: "检查时间：{time}，{via}。",
    health_via_agent: "由正在运行的角色执行",
    health_via_doctor: "通过单独的测试运行执行",
    health_reused: "结果生成于一分钟内且设置未变更，因此未重新发送请求。",
    health_verdict_ok: "角色所需的服务均运行正常。",
    health_verdict_partly: "角色可以正常聊天，但以下功能无法使用：{names}。",
    health_verdict_nokey: "尚未设置聊天模型。请在「角色与设置」中添加。",
    health_verdict_key: "聊天模型拒绝了该密钥。请在「角色与设置」中检查密钥。",
    health_verdict_limit: "聊天模型提示额度已用完或请求过于频繁。请稍后重试，或更换模型服务。",
    health_verdict_missing: "聊天模型提示该模型名称不存在。请在「角色与设置」中核对模型名称。",
    health_verdict_unreachable: "无法连接聊天模型。请检查网络连接和服务地址。",
    health_verdict_other: "聊天模型未正常响应。请在「角色与设置」中检查模型设置。",
    health_verdict_bridge: "QQ 桥接（NapCat）未响应。角色需要通过它收发消息。",
    health_open_settings: "打开「角色与设置」",
    health_probe_ledger: "学习记录",
    health_probe_dm: "私聊回复",
    health_probe_chat: "群聊回复与工具",
    health_probe_vision: "图片理解",
    health_probe_eval: "自我审查模型",
    health_probe_embeddings: "记忆查找",
    health_probe_search: "联网搜索（Tavily）",
    health_probe_onebot: "QQ 桥接（NapCat）",
    health_probe_other: "{name}",
    health_ok: "正常",
    health_bad: "异常",
    health_skipped: "未设置",
    health_needed: "必需",
    health_ms: "{ms} 毫秒",
    health_details: "技术详情",
    health_ledger_note: "部分记录无法读取，已跳过；或记录文件较大。如数量未持续增加，则无需处理。",
    health_show_skipped: "显示 {count} 项未设置的服务",
    health_hide_skipped: "隐藏未设置的服务",
    health_fail_agent: "角色未在运行：启动失败或已意外停止。",
    health_fail_astrbot: "聊天平台（AstrBot）启动失败或已意外停止。",
    health_fail_direct: "与平台的连接已中断。",
    health_fail_install: "下载或安装未完成。",
    health_fail_said: "日志中的相关记录：",
    health_fail_retired: "部分设置仍使用旧版本的名称，角色因此无法启动。请在下方重命名。",
    health_show_log: "查看日志",
    health_start_again: "重新启动",
    health_starting: "正在启动…",
    health_started: "正在重新启动，需要几秒钟。",
    health_retired_title: "使用旧名称的设置",
    health_retired_hint: "以下设置已在 1.0 版中更名。旧名称存在时，角色无法启动。",
    health_retired_env: "{old} 在本应用之外设置。请在设置它的位置改为 {new}。",
    health_fix: "重命名设置",
    health_fixing: "正在重命名…",
    health_fix_ask: "将重命名 .env 中的以下设置：{names}。如新名称已存在，旧的一行将改为注释。当前文件会先另存为 .env.bak，并覆盖已有的同名备份。如角色正在运行或此前启动失败，随后将重新启动。",
    health_fixed: "已更新 {count} 项设置名称。原文件已另存为 .env.bak。",
    health_platforms_title: "平台连接",
    health_platform_failed: "连接失败",
    health_platform_connected: "已连接",
    health_platform_connecting: "正在连接",
    health_platform_waiting: "未启动",
    health_platform_error: "连接因错误而中断。请重新连接该平台；如仍然失败，请查看下方「平台连接」日志。",
    health_since: "自 {time} 起",
    health_reconnect: "打开「连接平台」",
    health_findings_title: "需检查的设置",
    health_findings_none: "设置中未发现问题。",
    health_finding_missing_key: "未填写模型密钥，角色无法回复。",
    health_finding_bom: "设置文件开头含有不可见的字节顺序标记（BOM），第一项设置因此被忽略。请将文件另存为不带 BOM 的 UTF-8 编码。",
    health_finding_unknown: "{key} 不是 personagent 可识别的设置，可能存在拼写错误。",
    health_finding_dropped: "{key} 已不再使用，可删除该行。",
    health_finding_empty: "{key} 的值为空。",
    health_finding_other: "{key} 需要检查。",
    health_level_error: "错误",
    health_level_warn: "警告",
    health_open_home: "打开 personagent 文件夹",
    health_opening: "正在打开…",
    health_opened: "已在文件管理器中打开该文件夹。",
    health_logs_title: "运行日志",
    health_logs_hint: "各组件运行时写入的记录，显示最后 {count} 行。可识别的密钥和令牌已隐藏，但其中可能包含聊天内容。",
    health_log_pick: "日志",
    health_log_agent: "角色",
    health_log_astrbot: "聊天平台（AstrBot）",
    health_log_direct: "平台连接",
    health_log_install: "下载与安装",
    health_log_app: "本应用",
    health_log_practice: "演练",
    health_log_update: "最近一次更新",
    health_log_reload: "刷新",
    health_log_loading: "正在读取…",
    health_log_empty: "该日志暂无内容。",
    health_log_none: "暂无日志。角色或平台连接启动后将生成日志。",
    health_log_more: "显示更多行",
    health_open_logs: "打开日志文件夹",
    health_attention: "需要处理",
    health_busy: "检查正在进行，请等待其完成。",
    health_failed: "检查未能运行。请重试；如仍然失败，请查看下方「角色」日志。",
    health_invalid_log: "该日志不存在。",
    health_open_failed: "无法打开文件管理器。日志位于 personagent 文件夹下的 runtime/desktop 中。",
    health_open_failed_home: "无法打开文件管理器。设置文件 .env 位于 personagent 文件夹中。",
    health_nothing_to_fix: "没有需要重命名的设置。",
  },
});

(() => {
  const root = PA.$("health-root");
  if (!root) return;
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const button = (cls, id) => {
    const node = el("button", cls);
    node.type = "button";
    if (id) node.id = id;
    return node;
  };
  const LOG_STEP = 80;
  const LOG_MAX = 200;

  let data = null;
  let result = null;
  let reused = false;
  let checking = false;
  // Errors are kept as codes and translated when shown, so they follow a language change.
  let checkError = "";
  let showSkipped = false;
  // Rows are rebuilt on every render; an opened detail stays open.
  const openDetails = new Set();
  let fixing = false;
  let fixError = "";
  let starting = false;
  let startError = "";
  let opening = "";
  let openError = { home: "", logs: "" };
  let logName = "";
  let logLines = LOG_STEP;
  let logRows = null;
  let logLoading = false;
  let logError = "";
  let signature = "";
  let loadTimer = null;
  let waiting = false;
  // The control an action started from, focused again once it is usable.
  let focusId = "";

  // Only the zh table has these strings; zh-TW and others fall back to English.
  const zh = () => PA.lang === "zh";
  const alertNode = (id, code) => {
    const node = el("p", "error", PA.t(code));
    node.id = id;
    node.setAttribute("role", "alert");
    return node;
  };
  function restoreFocus() {
    if (!focusId) return;
    const node = PA.$(focusId);
    const active = document.activeElement;
    if (!node || (active && active !== document.body && active !== node)) focusId = "";
    else if (active === node && !node.disabled) focusId = "";
    else if (!node.disabled && !node.hidden) {
      node.focus();
      focusId = "";
    }
  }
  const clock = (seconds) => {
    try {
      return new Date(seconds * 1000).toLocaleTimeString(zh() ? "zh-CN" : PA.lang || "en", {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (error) {
      return new Date(seconds * 1000).toLocaleTimeString();
    }
  };
  const probeName = (s) =>
    PA.t(`health_probe_${s.id}`, { name: s.name });

  // The fixed parts; render() fills them.
  const card = el("div", "card side-card health-card");
  card.id = "health-card";
  const title = el("h2");
  const hint = el("p", "field-note");
  const alerts = el("div", "health-alerts");
  const results = el("div", "health-results");
  const verdict = el("p", "health-verdict");
  verdict.id = "health-verdict";
  verdict.setAttribute("role", "status");
  const verdictAction = button("secondary health-inline", "health-settings");
  const when = el("p", "field-note health-when");
  when.id = "health-when";
  const rows = el("div", "health-rows");
  rows.id = "health-rows";
  const toggle = button("quiet health-toggle", "health-toggle");
  const checkNote = el("p", "field-note health-note");
  checkNote.id = "health-check-note";
  checkNote.setAttribute("role", "status");
  const checkErr = el("p", "error");
  checkErr.id = "health-check-error";
  checkErr.setAttribute("role", "alert");
  const actions = el("div", "card-actions");
  const checkButton = button("primary", "health-check");
  actions.append(checkButton);
  results.append(verdict, verdictAction, when, rows, toggle);
  card.append(title, hint, alerts, results, checkNote, checkErr, actions);

  const logCard = el("div", "card side-card health-logs");
  logCard.id = "health-logs";
  const logTitle = el("h2");
  const logHint = el("p", "field-note");
  const logBar = el("div", "health-log-bar");
  const logLabel = el("label", "health-log-label");
  logLabel.htmlFor = "health-log-name";
  const logSelect = el("select");
  logSelect.id = "health-log-name";
  const reloadButton = button("quiet", "health-log-reload");
  const moreButton = button("quiet", "health-log-more");
  const openLogs = button("secondary", "health-open-logs");
  logBar.append(logLabel, logSelect, reloadButton, moreButton, openLogs);
  const logNone = el("p", "field-note");
  logNone.id = "health-log-none";
  const logErr = el("p", "error");
  logErr.id = "health-log-error";
  logErr.setAttribute("role", "alert");
  const logBox = el("pre", "health-log");
  logBox.id = "health-log";
  logBox.tabIndex = 0;
  logCard.append(logTitle, logHint, logBar, logNone, logErr, logBox);
  root.append(card, logCard);

  function attention() {
    if (!data) return false;
    const configured = !PA.state || PA.state.configured;
    return Boolean(
      data.failure ||
        data.retired.length ||
        data.platforms.some((p) => p.failed) ||
        data.findings.some((f) => f.level === "ERROR" && (configured || f.kind !== "missing_key")) ||
        (result && !result.ok && configured),
    );
  }

  function verdictOf(r) {
    const chat = r.services.filter((s) => s.id === "dm" || s.id === "chat");
    if (chat.length && chat.every((s) => s.ok === null)) return { key: "health_verdict_nokey", settings: true };
    const bad = chat.find((s) => s.ok === false);
    if (bad) return { key: `health_verdict_${bad.reason || "other"}`, settings: true };
    const critical = r.services.find((s) => s.critical && s.ok !== true);
    if (critical)
      return critical.id === "onebot"
        ? { key: "health_verdict_bridge" }
        : { key: "health_verdict_other", settings: true };
    const broken = r.services.filter((s) => s.ok === false);
    if (broken.length)
      return {
        key: "health_verdict_partly",
        fields: { names: broken.map(probeName).join(zh() ? "、" : ", ") },
      };
    return { key: "health_verdict_ok" };
  }

  function renderResults() {
    // A check started before this page loaded also counts.
    const busy = checking || Boolean(data && data.checking);
    checkButton.disabled = busy;
    checkButton.textContent = PA.t(busy ? "health_checking" : "health_check");
    checkNote.textContent = busy ? PA.t("health_checking_note") : "";
    checkNote.hidden = !busy;
    checkErr.textContent = checkError ? PA.t(checkError) : "";
    checkErr.hidden = !checkError;
    rows.replaceChildren();
    if (!result) {
      verdict.hidden = verdictAction.hidden = toggle.hidden = true;
      when.textContent = PA.t("health_never");
      restoreFocus();
      return;
    }
    const v = verdictOf(result);
    verdict.hidden = false;
    verdict.className = `health-verdict ${result.ok ? "is-ok" : "is-bad"}`;
    verdict.textContent = PA.t(v.key, v.fields || {});
    verdictAction.hidden = !v.settings;
    verdictAction.textContent = PA.t("health_open_settings");
    when.textContent =
      PA.t("health_checked_at", {
        time: clock(result.checkedAt),
        via: PA.t(result.via === "agent" ? "health_via_agent" : "health_via_doctor"),
      }) + (reused ? " " + PA.t("health_reused") : "");
    const skipped = result.services.filter((s) => s.ok === null);
    for (const s of result.services) {
      if (s.ok === null && !showSkipped) continue;
      const state = s.ok === true ? "is-ok" : s.ok === false ? "is-bad" : "is-off";
      const row = el("div", `health-row ${state}`);
      row.dataset.probe = s.id;
      const mark = el("span", "health-mark");
      const main = el("div", "health-row-main");
      const head = el("div", "health-row-head");
      head.append(el("strong", "", probeName(s)));
      const word = PA.t(s.ok === true ? "health_ok" : s.ok === false ? "health_bad" : "health_skipped");
      head.append(el("span", "feature-state", s.critical ? `${word} · ${PA.t("health_needed")}` : word));
      if (s.ok !== null) head.append(el("span", "health-ms", PA.t("health_ms", { ms: s.ms })));
      main.append(head);
      // The service's own English diagnostic, kept out of the row's translated text.
      if (s.detail) {
        const tech = el("details", "health-tech");
        tech.open = openDetails.has(s.id);
        tech.addEventListener("toggle", () => {
          if (tech.open) openDetails.add(s.id);
          else openDetails.delete(s.id);
        });
        tech.append(el("summary", "", PA.t("health_details")), el("p", "health-detail", s.detail));
        main.append(tech);
      }
      if (s.id === "ledger" && s.ok === false) main.append(el("p", "field-note", PA.t("health_ledger_note")));
      row.append(mark, main);
      rows.append(row);
    }
    toggle.hidden = !skipped.length;
    toggle.textContent = showSkipped
      ? PA.t("health_hide_skipped")
      : PA.t("health_show_skipped", { count: skipped.length });
    restoreFocus();
  }

  function section(titleKey, id) {
    const box = el("div", "feature health-section");
    box.id = id;
    const head = el("div", "feature-head");
    head.append(el("strong", "", PA.t(titleKey)));
    box.append(head);
    return box;
  }

  function renderAlerts() {
    // The buttons here are rebuilt: a focused one is focused again by its id.
    const active = document.activeElement;
    if (active && active.id && alerts.contains(active) && !focusId) focusId = active.id;
    alerts.replaceChildren();
    if (!data) return restoreFocus();
    const job = (PA.state && PA.state.job) || {};
    const envRetired = data.retired.filter((r) => r.where === ".env");
    if (data.failure) {
      const f = data.failure;
      const box = el("div", "health-alert");
      box.id = "health-failure";
      box.append(el("p", "health-alert-title", PA.t(`health_fail_${f.service}`)));
      if (envRetired.length && f.service === "agent")
        box.append(el("p", "field-note", PA.t("health_fail_retired")));
      if (f.said) {
        box.append(el("p", "field-note health-said-label", PA.t("health_fail_said")));
        box.append(el("p", "health-detail health-said", f.said));
      }
      const bar = el("div", "health-buttons");
      const show = button("secondary", "health-show-log");
      show.textContent = PA.t("health_show_log");
      show.addEventListener("click", () => {
        logName = f.service;
        logLines = LOG_STEP;
        loadLog();
        logCard.scrollIntoView({ block: "start", behavior: "smooth" });
      });
      bar.append(show);
      if (!envRetired.length && f.service !== "install" && job.state !== "working" && !waiting) {
        const again = button("secondary", "health-start");
        again.disabled = starting;
        again.textContent = PA.t(starting ? "health_starting" : "health_start_again");
        again.addEventListener("click", startAgain);
        bar.append(again);
      }
      box.append(bar);
      if (startError) box.append(alertNode("health-start-error", startError));
      alerts.append(box);
    }
    if (data.retired.length) {
      const box = section("health_retired_title", "health-retired");
      box.append(el("p", "field-note", PA.t("health_retired_hint")));
      const list = el("ul", "health-list");
      for (const r of data.retired) {
        const item = el("li");
        if (r.where === ".env") item.append(el("code", "health-code", `${r.old} → ${r.new}`));
        else item.textContent = PA.t("health_retired_env", { old: r.old, new: r.new });
        list.append(item);
      }
      box.append(list);
      if (envRetired.length) {
        const fix = button("secondary", "health-fix");
        fix.disabled = fixing;
        fix.textContent = PA.t(fixing ? "health_fixing" : "health_fix");
        fix.addEventListener("click", fixRetired);
        box.append(fix);
      }
      if (fixError) box.append(alertNode("health-fix-error", fixError));
      alerts.append(box);
    }
    if (data.platforms.some((p) => p.failed)) {
      const box = section("health_platforms_title", "health-platforms");
      for (const p of data.platforms) {
        const row = el("div", `health-row ${p.failed ? "is-bad" : p.state === "connected" ? "is-ok" : "is-off"}`);
        row.dataset.platform = p.id;
        const main = el("div", "health-row-main");
        const head = el("div", "health-row-head");
        head.append(el("strong", "", (p.name && p.name[zh() ? 1 : 0]) || p.id));
        const word = p.failed
          ? "health_platform_failed"
          : p.state === "connected"
            ? "health_platform_connected"
            : p.state === "connecting"
              ? "health_platform_connecting"
              : "health_platform_waiting";
        head.append(el("span", "feature-state", PA.t(word)));
        if (p.since) head.append(el("span", "health-ms", PA.t("health_since", { time: clock(p.since) })));
        main.append(head);
        if (p.failed)
          main.append(
            el("p", "field-note", PA.t(p.reason && p.reason !== "error" ? p.reason : "health_platform_error")),
          );
        row.append(el("span", "health-mark"), main);
        box.append(row);
      }
      const go = button("secondary", "health-reconnect");
      go.textContent = PA.t("health_reconnect");
      go.addEventListener("click", () => PA.showView("platforms"));
      box.append(go);
      alerts.append(box);
    }
    const box = section("health_findings_title", "health-findings");
    if (!data.findings.length) box.append(el("p", "field-note", PA.t("health_findings_none")));
    let needsKey = false;
    for (const f of data.findings) {
      const row = el("div", `health-finding ${f.level === "ERROR" ? "is-bad" : "is-warn"}`);
      row.dataset.key = f.key;
      const head = el("div", "health-row-head");
      head.append(el("span", "health-level", PA.t(f.level === "ERROR" ? "health_level_error" : "health_level_warn")));
      head.append(el("span", "health-finding-text", PA.t(`health_finding_${f.kind}`, { key: f.key })));
      row.append(head);
      if (f.kind === "other" || f.kind === "empty") row.append(el("p", "health-detail", `${f.key}: ${f.detail}`));
      if (f.kind === "missing_key") needsKey = true;
      box.append(row);
    }
    if (data.findings.length) {
      const bar = el("div", "health-buttons");
      if (needsKey) {
        const go = button("secondary", "health-finding-settings");
        go.textContent = PA.t("health_open_settings");
        go.addEventListener("click", () => PA.showView("settings"));
        bar.append(go);
      }
      const open = button("secondary", "health-open-home");
      open.disabled = opening === "home";
      open.textContent = PA.t(opening === "home" ? "health_opening" : "health_open_home");
      open.addEventListener("click", () => openFolder("home", open));
      bar.append(open);
      box.append(bar);
      if (openError.home) box.append(alertNode("health-open-home-error", openError.home));
    }
    alerts.append(box);
    restoreFocus();
  }

  function renderLogs() {
    logTitle.textContent = PA.t("health_logs_title");
    logHint.textContent = PA.t("health_logs_hint", { count: logLines });
    logLabel.textContent = PA.t("health_log_pick");
    reloadButton.textContent = PA.t(logLoading ? "health_log_loading" : "health_log_reload");
    reloadButton.disabled = logLoading;
    moreButton.textContent = PA.t("health_log_more");
    moreButton.disabled = logLoading;
    openLogs.disabled = opening === "logs";
    openLogs.textContent = PA.t(opening === "logs" ? "health_opening" : "health_open_logs");
    const names = data ? data.logs.map((l) => l.name) : [];
    const none = !names.length;
    logNone.textContent = PA.t("health_log_none");
    logNone.hidden = !none;
    for (const node of [logLabel, logSelect, reloadButton, moreButton]) node.hidden = none;
    logSelect.replaceChildren();
    for (const name of names) {
      const option = el("option", "", PA.t(`health_log_${name}`));
      option.value = name;
      logSelect.append(option);
    }
    if (names.includes(logName)) logSelect.value = logName;
    moreButton.hidden = none || logLines >= LOG_MAX || !logRows || logRows.length < logLines;
    const logCode = logError || openError.logs;
    logErr.textContent = logCode ? PA.t(logCode) : "";
    logErr.hidden = !logCode;
    logBox.hidden = none || logRows === null;
    if (logRows !== null) {
      const atEnd = logBox.scrollTop + logBox.clientHeight >= logBox.scrollHeight - 4;
      logBox.textContent = logRows.length ? logRows.join("\n") : PA.t("health_log_empty");
      if (atEnd || logBox.dataset.shown !== logName) logBox.scrollTop = logBox.scrollHeight;
      logBox.dataset.shown = logName;
    }
    restoreFocus();
  }

  function render() {
    title.textContent = PA.t("health_title");
    hint.textContent = PA.t("health_hint");
    renderResults();
    renderAlerts();
    renderLogs();
    const dot = PA.$("app-dot");
    if (dot) {
      const on = attention();
      dot.classList.toggle("health-attention", on);
      if (on) {
        dot.hidden = false;
        // Named, so the App button says more than a red dot does.
        dot.setAttribute("role", "img");
        dot.setAttribute("aria-label", PA.t("health_attention"));
      } else if (dot.dataset.health === "1") {
        dot.hidden = true;
        dot.removeAttribute("role");
        dot.removeAttribute("aria-label");
      }
      dot.dataset.health = on ? "1" : "";
    }
  }

  async function load() {
    clearTimeout(loadTimer);
    try {
      data = await PA.api("health/state");
    } catch (error) {
      return;
    }
    if (!result && data.last) result = data.last;
    if (data.checking && !checking) loadTimer = setTimeout(load, 3000);
    const names = data.logs.map((l) => l.name);
    if (!names.includes(logName)) {
      const wanted = data.failure && names.includes(data.failure.service) ? data.failure.service : names[0] || "";
      if (wanted !== logName) {
        logName = wanted;
        logRows = null;
      }
    }
    render();
    if (PA.view === "app" && logName && logRows === null && !logLoading) loadLog();
  }

  async function loadLog() {
    if (!logName) return;
    logLoading = true;
    logError = "";
    renderLogs();
    try {
      const value = await PA.api(`health/log?name=${encodeURIComponent(logName)}&lines=${logLines}`);
      if (value.name === logName) logRows = value.lines;
    } catch (error) {
      logError = error.message;
    }
    logLoading = false;
    renderLogs();
  }

  async function check() {
    focusId = "health-check";
    checking = true;
    checkError = "";
    renderResults();
    try {
      result = await PA.api("health/check", {});
      reused = Boolean(result.reused);
      showSkipped = false;
    } catch (error) {
      checkError = error.message;
    }
    checking = false;
    await load();
    render();
  }

  async function fixRetired() {
    const names = data.retired.filter((r) => r.where === ".env").map((r) => `${r.old} → ${r.new}`);
    const count = names.length;
    const ask = PA.t("health_fix_ask", { names: names.join(zh() ? "、" : ", ") });
    if (!(await PA.ask(ask, PA.t("health_fix")))) return;
    let started = false;
    focusId = "health-fix";
    fixing = true;
    fixError = "";
    renderAlerts();
    try {
      const value = await PA.api("health/fix", {});
      PA.toast(PA.t("health_fixed", { count: value.changes.length || count }));
      started = value.started;
    } catch (error) {
      fixError = error.message;
    }
    fixing = false;
    await settle(started);
  }

  async function startAgain() {
    let started = false;
    focusId = "health-start";
    starting = true;
    startError = "";
    renderAlerts();
    try {
      await PA.api("start", {});
      PA.toast(PA.t("health_started"));
      started = true;
    } catch (error) {
      startError = error.message;
    }
    starting = false;
    await settle(started);
  }

  // A started job rewrites .env: leave it alone until the page's poll sees the job end.
  async function settle(started) {
    if (!started) return load();
    waiting = true;
    signature = "";
    render();
  }

  async function openFolder(folder, node) {
    if (node && node.id) focusId = node.id;
    opening = folder;
    openError = { ...openError, [folder]: "" };
    if (node) {
      node.disabled = true;
      node.textContent = PA.t("health_opening");
    }
    try {
      await PA.api("health/open", { folder });
      PA.toast(PA.t("health_opened"));
    } catch (error) {
      // The shared code names the logs folder; the settings button gets its own sentence.
      const code = error.message === "health_open_failed" && folder === "home" ? "health_open_failed_home" : error.message;
      openError = { ...openError, [folder]: code };
    }
    opening = "";
    render();
  }

  checkButton.addEventListener("click", check);
  verdictAction.addEventListener("click", () => PA.showView("settings"));
  toggle.addEventListener("click", () => {
    showSkipped = !showSkipped;
    renderResults();
  });
  logSelect.addEventListener("change", () => {
    logName = logSelect.value;
    logLines = LOG_STEP;
    logRows = null;
    loadLog();
  });
  reloadButton.addEventListener("click", () => {
    focusId = reloadButton.id;
    loadLog();
  });
  moreButton.addEventListener("click", async () => {
    focusId = moreButton.id;
    logLines = Math.min(LOG_MAX, logLines + 60);
    await loadLog();
    // At the end of the log the button goes away; the log itself takes focus.
    if (moreButton.hidden && focusId === moreButton.id) {
      focusId = "";
      logBox.focus();
    }
  });
  openLogs.addEventListener("click", () => openFolder("logs", openLogs));

  PA.onShow("app", () => {
    load();
    if (logName) loadLog();
  });
  PA.onState((state) => {
    const job = state.job || {};
    waiting = false;
    const next = JSON.stringify([
      job.state,
      job.error,
      state.agentRunning,
      state.platformRunning,
      state.platformStatus,
      state.configured,
    ]);
    if (next !== signature) {
      signature = next;
      // A job rewrites .env as it starts; on Windows a read at that moment can make its write fail.
      if (job.state !== "working") load();
    }
  });
  PA.onLanguage(render);
  render();
})();
