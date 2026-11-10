// The desk panel: desktop icon, start at sign-in, where the data is, backups, starting over.
PA.strings({
  zh: {
    desk_computer_title: "本机",
    desk_icon_title: "桌面和开始菜单图标",
    desk_icon_hint: "单击图标即可打开 personagent，不显示命令行窗口。",
    desk_icon_on: "已添加",
    desk_icon_off: "未添加",
    desk_icon_other: "已有图标，但它打开的是另一份 personagent。重新添加后将指向当前这一份。",
    desk_icon_add: "添加图标",
    desk_icon_remove: "删除图标",
    desk_adding: "正在添加…",
    desk_removing: "正在删除…",
    desk_icon_added: "已在桌面和开始菜单中添加图标。",
    desk_icon_removed: "已从桌面和开始菜单中删除图标。",
    desk_login_title: "登录 Windows 后自动启动 personagent",
    desk_login_on: "已开启。登录 Windows 后自动启动 personagent；如已设置为后台运行，则只在通知区域显示图标，不打开窗口。",
    desk_login_off: "未开启。开启后将在「启动」文件夹中添加快捷方式，登录 Windows 后自动启动 personagent。",
    desk_login_other: "「启动」文件夹中的快捷方式打开的是另一份 personagent。勾选此项后将指向当前这一份。",
    desk_login_done_on: "已开启：登录 Windows 后将自动启动 personagent。",
    desk_login_done_off: "已关闭：登录 Windows 后不再自动启动 personagent。",
    desk_saving: "正在保存…",
    desk_checking: "正在检查…",
    desk_unsupported: "桌面图标和登录后自动启动仅支持 Windows。在其他系统中，请手动将 personagent 添加到启动器或登录项。",
    desk_uvx: "当前通过 uvx 从临时文件夹运行，图标无法指向该位置。请先安装 personagent：uv tool install personagent",
    desk_shortcut_failed: "Windows 未允许此项修改。请重试；如仍失败，请在命令行中运行 personagent shortcut 查看原因。",
    desk_data_title: "你的数据",
    desk_data_hint: "personagent 的全部数据保存在以下文件夹中：",
    desk_open: "打开",
    desk_opening: "正在打开…",
    desk_opened: "已打开：{place}",
    desk_place_home: "personagent 文件夹",
    desk_place_home_hint: "设置、人设、记忆和已连接的平台均保存在此。",
    desk_place_persona: "人设文件",
    desk_place_persona_hint: "persona.txt，定义角色的文本。",
    desk_place_logs: "运行日志",
    desk_place_logs_hint: "应用和角色运行时写入的记录。出现问题时可在此查看。",
    desk_place_memory: "记忆和学到的内容",
    desk_place_memory_hint: "角色记下的关于每个人的信息、学到的说法及其修改记录。",
    desk_place_stickers: "表情包",
    desk_place_stickers_hint: "角色可以发送的图片。将图片文件放入此文件夹即可。",
    desk_place_data: "背景设定、示例对话和屏蔽词",
    desk_place_data_hint: "在此放入背景设定（lorebook）、示例对话（examples）和屏蔽词（output_filter）文件，将替换内置的同类文件。角色重启后生效。",
    desk_missing: "找不到该文件或文件夹。人设文件在首次保存角色后生成；备份文件可能已被移动或删除。请刷新页面后重试。",
    desk_open_failed: "文件管理器无法打开该位置。请按上方显示的路径手动打开。",
    desk_invalid_place: "页面发出的请求无效。请刷新页面后重试。",
    desk_runtime_elsewhere: ".env 中的 AGENT_RUNTIME_DIR 指向 personagent 文件夹之外，此页面不会修改该位置。请将其改回 personagent 文件夹内。",
    desk_service_elsewhere: "角色正在另一个进程中运行（例如从命令行启动）。请先停止该进程再重试。未做任何更改。",
    desk_backup_title: "备份",
    desk_backup_hint: "将设置、人设、记忆、学到的内容、背景设定文件、表情包和平台登录信息保存为一个 zip 文件。不包含运行日志和已下载的组件。",
    desk_backup_warn: "该文件包含你的 API 密钥和平台登录信息，请妥善保管，切勿发送给他人。",
    desk_backup_to: "保存位置",
    desk_target_desktop: "桌面",
    desk_target_documents: "文档",
    desk_target_backups: "personagent 文件夹中的 backups 文件夹",
    desk_backup_now: "立即备份",
    desk_backing_up: "正在备份…",
    desk_backup_done: "已保存备份（{size}）：{path}",
    desk_backup_failed: "无法写入备份。请检查磁盘空间是否充足，或选择其他保存位置。",
    desk_restore_title: "从备份恢复",
    desk_restore_hint: "此处列出桌面、文档和 backups 文件夹中的备份。恢复将替换当前的记忆、学到的内容、设置、人设、平台登录信息、表情包和背景设定文件；替换前会自动备份当前数据。",
    desk_restore_none: "未找到备份。",
    desk_backup_line: "{when} · {size} · {place}",
    desk_restore: "恢复",
    desk_restoring: "正在恢复…",
    desk_restore_ask: "确定从 {name} 恢复吗？恢复期间角色将暂停运行。记忆、学到的内容、设置、人设、平台登录信息、表情包和背景设定文件将替换为该备份中的版本，本页的聊天记录也将清空。替换前会自动备份当前数据。",
    desk_restored: "已恢复。原有数据已备份至：{path}",
    desk_invalid_backup: "该文件不是 personagent 备份，或包含备份中不应出现的文件。未做任何更改。",
    desk_restore_failed: "恢复中途失败，且未能还原原有数据。原有数据已备份在 backups 文件夹中，从该备份恢复即可还原。",
    desk_restore_undone: "恢复中途失败，已还原为恢复前的数据。未做任何更改。",
    desk_over_title: "清除与重置",
    desk_over_hint: "以下操作执行前均会在 backups 文件夹中自动备份，执行期间角色将暂停运行。",
    desk_forget_title: "清除记忆和学到的内容",
    desk_forget_hint: "删除角色记下的关于每个人的信息、学到的说法及其修改记录、演练数据和本页的聊天记录。设置、人设、已连接的平台和表情包将保留。",
    desk_forget: "清除记忆",
    desk_forgetting: "正在清除…",
    desk_forget_ask: "确定清除角色的记忆吗？将删除角色记下的关于每个人的信息、学到的说法及其修改记录、演练数据和本页的聊天记录。设置、人设、已连接的平台和表情包将保留。清除前会自动备份，可从备份恢复。",
    desk_forgot: "已清除记忆。备份已保存至：{path}",
    desk_reset_title: "全部重置",
    desk_reset_hint: "将 personagent 恢复到首次打开时的状态：删除设置和 API 密钥、人设、记忆和学到的内容，并断开所有平台。表情包、背景设定文件夹和已下载的平台组件将保留。",
    desk_reset: "全部重置",
    desk_resetting: "正在重置…",
    desk_reset_ask: "确定全部重置吗？将删除设置和 API 密钥、人设、记忆和学到的内容、演练数据和本页的聊天记录，并断开所有平台。表情包、背景设定文件夹和已下载的平台组件将保留。重置前会自动备份，可从备份恢复。",
    desk_reset_done: "已全部重置。备份已保存至：{path}",
    desk_reset_failed: "操作中途失败。backups 文件夹中有操作前的备份，从该备份恢复即可还原。",
    desk_reload_failed: "操作已完成，但页面未能更新。请刷新页面。",
    desk_size_kb: "{n} KB",
    desk_size_mb: "{n} MB",
  },
  en: {
    desk_computer_title: "This computer",
    desk_icon_title: "Desktop and Start menu icon",
    desk_icon_hint: "Opens personagent with one click, without a terminal window.",
    desk_icon_on: "Added",
    desk_icon_off: "Not added",
    desk_icon_other: "An icon exists, but it opens another copy of personagent. Add the icon again to point it to this copy.",
    desk_icon_add: "Add icon",
    desk_icon_remove: "Remove icon",
    desk_adding: "Adding…",
    desk_removing: "Removing…",
    desk_icon_added: "The icon has been added to the desktop and the Start menu.",
    desk_icon_removed: "The icon has been removed from the desktop and the Start menu.",
    desk_login_title: "Start personagent after signing in to Windows",
    desk_login_on: "On. personagent starts after you sign in to Windows. If it is set to run in the background, it shows only its icon in the notification area and does not open the window.",
    desk_login_off: "Off. When turned on, a shortcut is added to the Startup folder so that personagent starts after you sign in to Windows.",
    desk_login_other: "A shortcut in the Startup folder opens another copy of personagent. Select this option to point it to this copy.",
    desk_login_done_on: "On: personagent will start after you sign in to Windows.",
    desk_login_done_off: "Off: personagent will no longer start after you sign in to Windows.",
    desk_saving: "Saving…",
    desk_checking: "Checking…",
    desk_unsupported: "Desktop icons and starting at sign-in are available on Windows only. On other systems, add personagent to your launcher or login items manually.",
    desk_uvx: "This copy runs through uvx from a temporary folder, which an icon cannot point to. Install personagent first: uv tool install personagent",
    desk_shortcut_failed: "Windows did not allow this change. Try again; if it still fails, run personagent shortcut in a terminal to see the reason.",
    desk_data_title: "Your data",
    desk_data_hint: "personagent keeps all of its data in this folder:",
    desk_open: "Open",
    desk_opening: "Opening…",
    desk_opened: "Opened: {place}",
    desk_place_home: "personagent folder",
    desk_place_home_hint: "Settings, persona, memory and connected platforms are all kept here.",
    desk_place_persona: "Persona file",
    desk_place_persona_hint: "persona.txt, the text that defines the character.",
    desk_place_logs: "Logs",
    desk_place_logs_hint: "Records written by the app and the character while running. Check here when a problem occurs.",
    desk_place_memory: "Memory and learned content",
    desk_place_memory_hint: "The character's notes about people, the replies it has learned and their change history.",
    desk_place_stickers: "Stickers",
    desk_place_stickers_hint: "Images the character can send. Place image files in this folder.",
    desk_place_data: "Lorebook, example dialogues and word filters",
    desk_place_data_hint: "Your own lorebook, examples and output_filter files placed here replace the built-in ones. They take effect after the character restarts.",
    desk_missing: "The file or folder does not exist. The persona file is created when a character is first saved; a backup may have been moved or deleted. Reload the page and try again.",
    desk_open_failed: "The file manager could not open this location. Open the path shown above manually.",
    desk_invalid_place: "The page sent an invalid request. Reload the page and try again.",
    desk_runtime_elsewhere: "AGENT_RUNTIME_DIR in .env points outside the personagent folder, so this page does not modify it. Move it back into the personagent folder.",
    desk_service_elsewhere: "The character is running in another process (for example, one started from a terminal). Stop that process and try again. Nothing was changed.",
    desk_backup_title: "Back up",
    desk_backup_hint: "Saves the settings, persona, memory, learned content, lorebook files, stickers and platform logins in one zip file. Logs and downloaded components are not included.",
    desk_backup_warn: "This file contains your API keys and platform logins. Keep it secure and do not send it to anyone.",
    desk_backup_to: "Save to",
    desk_target_desktop: "Desktop",
    desk_target_documents: "Documents",
    desk_target_backups: "The backups folder in the personagent folder",
    desk_backup_now: "Back up now",
    desk_backing_up: "Backing up…",
    desk_backup_done: "Backup saved ({size}): {path}",
    desk_backup_failed: "The backup could not be written. Check that there is enough free space, or choose another location.",
    desk_restore_title: "Restore from a backup",
    desk_restore_hint: "Backups on the Desktop, in Documents and in the backups folder are listed here. Restoring replaces the current memory, learned content, settings, persona, platform logins, stickers and lorebook files; the current data is backed up first.",
    desk_restore_none: "No backups found.",
    desk_backup_line: "{when} · {size} · {place}",
    desk_restore: "Restore",
    desk_restoring: "Restoring…",
    desk_restore_ask: "Restore from {name}? The character is paused during the restore. Its memory, learned content, settings, persona, platform logins, stickers and lorebook files are replaced with the versions in this backup, and this page's chat is cleared. The current data is backed up first.",
    desk_restored: "Restored. The previous data was backed up to {path}",
    desk_invalid_backup: "This file is not a personagent backup, or it contains files that a backup may not contain. Nothing was changed.",
    desk_restore_failed: "The restore failed partway, and the previous data could not be put back. The previous data is backed up in the backups folder; restore that backup to return to it.",
    desk_restore_undone: "The restore failed partway, and the previous data has been put back. Nothing was changed.",
    desk_over_title: "Clear and reset",
    desk_over_hint: "Each action below first saves a backup to the backups folder and pauses the character while it runs.",
    desk_forget_title: "Clear memory and learned content",
    desk_forget_hint: "Deletes the character's notes about people, the replies it has learned and their change history, the Practice data and this page's chat. Settings, persona, connected platforms and stickers are kept.",
    desk_forget: "Clear memory",
    desk_forgetting: "Clearing…",
    desk_forget_ask: "Clear the character's memory? This deletes its notes about people, the replies it has learned and their change history, the Practice data and this page's chat. Settings, persona, connected platforms and stickers are kept. A backup is saved first and can be restored.",
    desk_forgot: "Memory cleared. A backup was saved to {path}",
    desk_reset_title: "Reset all",
    desk_reset_hint: "Returns personagent to its first-run state: deletes the settings and API keys, the persona, memory and learned content, and disconnects every platform. Stickers, the lorebook folder and the downloaded platform component are kept.",
    desk_reset: "Reset all",
    desk_resetting: "Resetting…",
    desk_reset_ask: "Reset all? This deletes the settings and API keys, the persona, memory and learned content, the Practice data and this page's chat, and disconnects every platform. Stickers, the lorebook folder and the downloaded platform component are kept. A backup is saved first and can be restored.",
    desk_reset_done: "Reset complete. A backup was saved to {path}",
    desk_reset_failed: "The operation failed partway. The backups folder holds a backup made before it; restore that backup to return to the previous state.",
    desk_reload_failed: "The action is complete, but the page could not be updated. Reload the page.",
    desk_size_kb: "{n} KB",
    desk_size_mb: "{n} MB",
  },
});

(() => {
  const t = PA.t;
  const root = PA.$("desk-root");
  const PLACES = ["home", "persona", "logs", "memory", "stickers", "data"];
  let overview = null;
  let links = null;
  let loading = false;
  // The last result line, kept as a key so it follows a language change.
  let result = null;

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const button = (className, id) => {
    const node = el("button", className);
    node.type = "button";
    if (id) node.id = id;
    return node;
  };
  const size = (bytes) =>
    bytes >= 1024 * 1024
      ? t("desk_size_mb", { n: (bytes / 1024 / 1024).toFixed(1) })
      : t("desk_size_kb", { n: Math.max(1, Math.round(bytes / 1024)) });
  const showError = (node, code) => {
    node.dataset.code = code || "";
    node.textContent = code ? t(code) : "";
    node.hidden = !code;
  };
  // Focus lost to a disabled or rebuilt control goes back to it by id.
  const refocus = (id) => {
    const active = document.activeElement;
    if (active && active !== document.body && active.isConnected) return;
    const node = id && document.getElementById(id);
    if (node && !node.disabled) node.focus();
  };
  // A button shows its "-ing" label while `work` runs; the label comes back after.
  async function working(node, busyKey, work) {
    const label = node.textContent;
    const focused = document.activeElement === node;
    node.disabled = true;
    node.textContent = t(busyKey);
    try {
      return await work();
    } finally {
      node.disabled = false;
      node.textContent = label;
      if (focused) refocus(node.id);
    }
  }
  // After an action that changed what the page is built from.
  async function reloadPage() {
    try {
      await PA.reload();
    } catch {
      PA.toast(t("desk_reload_failed"));
    }
  }

  // ---- the cards
  const computer = el("div", "card side-card desk-card");
  computer.id = "desk-computer";
  const computerTitle = el("h2");
  const unsupported = el("p", "field-note");
  unsupported.id = "desk-unsupported";
  const uvxNote = el("p", "field-note desk-warn");
  uvxNote.id = "desk-uvx-note";
  const iconFeature = el("div", "feature");
  const iconHead = el("div", "feature-head");
  const iconTitle = el("strong");
  iconTitle.id = "desk-icon-title";
  const iconState = el("span", "feature-state");
  iconState.id = "desk-icon-state";
  iconHead.append(iconTitle, iconState);
  const iconHint = el("p", "field-note");
  const iconToggle = button("secondary desk-action", "desk-icon-toggle");
  iconFeature.append(iconHead, iconHint, iconToggle);
  const loginFeature = el("div", "feature");
  const loginLabel = el("label", "check");
  const loginBox = el("input");
  loginBox.type = "checkbox";
  loginBox.id = "desk-login";
  const loginTitle = el("span");
  loginLabel.append(loginBox, loginTitle);
  const loginNote = el("p", "field-note");
  loginNote.id = "desk-login-note";
  loginBox.setAttribute("aria-describedby", loginNote.id);
  loginFeature.append(loginLabel, loginNote);
  const computerError = el("div", "error");
  computerError.id = "desk-computer-error";
  computerError.setAttribute("role", "alert");
  computer.append(computerTitle, unsupported, uvxNote, iconFeature, loginFeature, computerError);

  const data = el("div", "card side-card desk-card");
  data.id = "desk-data";
  const dataTitle = el("h2");
  const dataHint = el("p", "field-note");
  const homePath = el("p", "desk-path");
  homePath.id = "desk-home";
  const placeList = el("div", "desk-places");
  const placeRows = {};
  for (const place of PLACES) {
    const row = el("div", "desk-row");
    const text = el("div", "desk-row-text");
    const name = el("strong");
    name.id = `desk-place-${place}`;
    const hint = el("span", "desk-row-hint");
    text.append(name, hint);
    const open = button("secondary desk-action", `desk-open-${place}`);
    // Heard as "Open <place>", not six identical "Open" buttons.
    open.setAttribute("aria-labelledby", `${open.id} ${name.id}`);
    open.addEventListener("click", () => openPlace(place, open));
    row.append(text, open);
    placeList.append(row);
    placeRows[place] = { name, hint, open };
  }
  const dataError = el("div", "error");
  dataError.id = "desk-data-error";
  dataError.setAttribute("role", "alert");
  data.append(dataTitle, dataHint, homePath, placeList, dataError);

  const backup = el("div", "card side-card desk-card");
  backup.id = "desk-backup";
  const backupTitle = el("h2");
  const backupHint = el("p", "field-note");
  const backupWarn = el("p", "field-note desk-warn");
  const targetLabel = el("label");
  targetLabel.htmlFor = "desk-target";
  const target = el("select");
  target.id = "desk-target";
  const backupResult = el("p", "desk-result");
  backupResult.id = "desk-backup-result";
  backupResult.setAttribute("role", "status");
  backupResult.hidden = true;
  const backupActions = el("div", "card-actions");
  const backupNow = button("primary", "desk-backup-now");
  backupActions.append(backupNow);
  const restoreTitle = el("h3", "desk-subtitle");
  const restoreHint = el("p", "field-note");
  const backupList = el("div", "desk-places");
  backupList.id = "desk-backups";
  const backupError = el("div", "error");
  backupError.id = "desk-backup-error";
  backupError.setAttribute("role", "alert");
  backup.append(backupTitle, backupHint, backupWarn, targetLabel, target, backupActions,
    backupResult, restoreTitle, restoreHint, backupList, backupError);

  const over = el("div", "card side-card desk-card desk-over");
  over.id = "desk-over";
  const overTitle = el("h2");
  const overHint = el("p", "field-note");
  const forgetFeature = el("div", "feature");
  const forgetHead = el("div", "feature-head");
  const forgetTitle = el("strong");
  forgetHead.append(forgetTitle);
  const forgetHint = el("p", "field-note");
  const forget = button("secondary desk-action desk-danger", "desk-forget");
  forgetFeature.append(forgetHead, forgetHint, forget);
  const resetFeature = el("div", "feature");
  const resetHead = el("div", "feature-head");
  const resetTitle = el("strong");
  resetHead.append(resetTitle);
  const resetHint = el("p", "field-note");
  const reset = button("secondary desk-action desk-danger", "desk-reset");
  resetFeature.append(resetHead, resetHint, reset);
  const overError = el("div", "error");
  overError.id = "desk-over-error";
  overError.setAttribute("role", "alert");
  over.append(overTitle, overHint, forgetFeature, resetFeature, overError);

  root.append(computer, data, backup, over);
  const errors = [computerError, dataError, backupError, overError];
  for (const node of errors) showError(node, "");

  // ---- drawing
  function renderLinks() {
    const supported = !links || links.supported;
    unsupported.hidden = supported;
    iconFeature.hidden = loginFeature.hidden = !supported;
    uvxNote.hidden = !(links && links.uvx);
    if (!links) {
      iconState.textContent = t("desk_checking");
      loginNote.textContent = t("desk_checking");
      iconToggle.textContent = t("desk_icon_add");
      iconToggle.disabled = loginBox.disabled = true;
      return;
    }
    const icon = links.icon;
    iconState.textContent = t(`desk_icon_${icon}`);
    iconState.dataset.state = icon;
    // While it works, the button keeps its "-ing" label and stays disabled.
    if (!iconToggle.dataset.busy) {
      iconToggle.textContent = t(icon === "on" ? "desk_icon_remove" : "desk_icon_add");
      // Under uvx an icon cannot be made, only taken away.
      iconToggle.disabled = icon !== "on" && links.uvx;
    }
    loginBox.checked = links.login === "on";
    loginBox.disabled = links.uvx && links.login !== "on";
    loginNote.textContent = t(`desk_login_${links.login}`);
  }

  function renderResult() {
    backupResult.hidden = !result;
    if (!result) return void (backupResult.textContent = "");
    const params = { ...result.params };
    if ("bytes" in params) params.size = size(params.bytes);
    backupResult.textContent = t(result.key, params);
  }

  function renderBackups() {
    // The list is rebuilt: a restore button that had focus gets it back.
    const active = document.activeElement;
    const focused = active && backupList.contains(active) ? active.id : "";
    backupList.replaceChildren();
    const items = overview ? overview.backups : [];
    if (!items.length) {
      backupList.append(el("p", "field-note", t("desk_restore_none")));
      return;
    }
    for (const item of items) {
      const row = el("div", "desk-row");
      const text = el("div", "desk-row-text");
      const id = `desk-restore-${item.place}-${item.name}`;
      const name = el("strong", "desk-file", item.name);
      name.id = `${id}-name`;
      text.append(
        name,
        el("span", "desk-row-hint", t("desk_backup_line", {
          when: new Date(item.when * 1000).toLocaleString(PA.lang),
          size: size(item.size),
          place: t(`desk_target_${item.place}`),
        })),
      );
      const restore = button("secondary desk-action desk-restore", id);
      restore.dataset.name = item.name;
      restore.textContent = t("desk_restore");
      restore.setAttribute("aria-labelledby", `${id} ${name.id}`);
      restore.addEventListener("click", () => restoreBackup(item, restore));
      row.append(text, restore);
      backupList.append(row);
    }
    if (focused) refocus(focused);
  }

  function renderOverview() {
    homePath.textContent = overview ? overview.home : "";
    const chosen = target.value;
    target.replaceChildren();
    for (const item of overview ? overview.targets : []) {
      const option = el("option", "", t(`desk_target_${item.id}`));
      option.value = item.id;
      target.append(option);
    }
    if (chosen && [...target.options].some((o) => o.value === chosen)) target.value = chosen;
    renderBackups();
  }

  function renderText() {
    computerTitle.textContent = t("desk_computer_title");
    unsupported.textContent = t("desk_unsupported");
    uvxNote.textContent = t("desk_uvx");
    iconTitle.textContent = t("desk_icon_title");
    iconHint.textContent = t("desk_icon_hint");
    loginTitle.textContent = t("desk_login_title");
    dataTitle.textContent = t("desk_data_title");
    dataHint.textContent = t("desk_data_hint");
    for (const place of PLACES) {
      placeRows[place].name.textContent = t(`desk_place_${place}`);
      placeRows[place].hint.textContent = t(`desk_place_${place}_hint`);
      if (!placeRows[place].open.disabled) placeRows[place].open.textContent = t("desk_open");
    }
    backupTitle.textContent = t("desk_backup_title");
    backupHint.textContent = t("desk_backup_hint");
    backupWarn.textContent = t("desk_backup_warn");
    targetLabel.textContent = t("desk_backup_to");
    if (!backupNow.disabled) backupNow.textContent = t("desk_backup_now");
    restoreTitle.textContent = t("desk_restore_title");
    restoreHint.textContent = t("desk_restore_hint");
    overTitle.textContent = t("desk_over_title");
    overHint.textContent = t("desk_over_hint");
    forgetTitle.textContent = t("desk_forget_title");
    forgetHint.textContent = t("desk_forget_hint");
    if (!forget.disabled) forget.textContent = t("desk_forget");
    resetTitle.textContent = t("desk_reset_title");
    resetHint.textContent = t("desk_reset_hint");
    if (!reset.disabled) reset.textContent = t("desk_reset");
    for (const node of errors) showError(node, node.dataset.code);
    renderResult();
    renderLinks();
    renderOverview();
  }

  // ---- reading
  async function load() {
    if (loading) return;
    loading = true;
    try {
      overview = await PA.api("desk");
      renderOverview();
      showError(dataError, "");
    } catch (error) {
      showError(dataError, error.message);
    }
    try {
      links = await PA.api("desk/shortcuts");
      showError(computerError, "");
    } catch (error) {
      links = { supported: true, uvx: false, icon: "off", login: "off" };
      showError(computerError, error.message);
    } finally {
      loading = false;
    }
    renderLinks();
  }

  // ---- acting
  iconToggle.addEventListener("click", async () => {
    const on = links.icon !== "on";
    showError(computerError, "");
    iconToggle.dataset.busy = "1";
    try {
      links = await working(iconToggle, on ? "desk_adding" : "desk_removing", () =>
        PA.api("desk/shortcut", { which: "icon", on }),
      );
      PA.toast(t(on ? "desk_icon_added" : "desk_icon_removed"));
    } catch (error) {
      showError(computerError, error.message);
    } finally {
      delete iconToggle.dataset.busy;
    }
    renderLinks();
    refocus(iconToggle.id);
  });

  loginBox.addEventListener("change", async () => {
    const on = loginBox.checked;
    showError(computerError, "");
    loginBox.disabled = true;
    loginNote.textContent = t("desk_saving");
    try {
      links = await PA.api("desk/shortcut", { which: "login", on });
      PA.toast(t(on ? "desk_login_done_on" : "desk_login_done_off"));
    } catch (error) {
      showError(computerError, error.message);
    }
    renderLinks();
    refocus(loginBox.id);
  });

  async function openPlace(place, node) {
    showError(dataError, "");
    try {
      await working(node, "desk_opening", () => PA.api("desk/open", { place }));
      PA.toast(t("desk_opened", { place: t(`desk_place_${place}`) }));
    } catch (error) {
      showError(dataError, error.message);
    }
  }

  backupNow.addEventListener("click", async () => {
    showError(backupError, "");
    try {
      const done = await working(backupNow, "desk_backing_up", () =>
        PA.api("desk/backup", { to: target.value }),
      );
      overview = { ...overview, backups: done.backups };
      result = { key: "desk_backup_done", params: { bytes: done.size, path: done.path } };
      renderResult();
      renderBackups();
    } catch (error) {
      showError(backupError, error.message);
    }
  });

  async function restoreBackup(item, node) {
    if (!(await PA.ask(t("desk_restore_ask", { name: item.name }), t("desk_restore")))) return;
    showError(backupError, "");
    let done;
    try {
      done = await working(node, "desk_restoring", () =>
        PA.api("desk/restore", { place: item.place, name: item.name }),
      );
    } catch (error) {
      showError(backupError, error.message);
      return;
    }
    overview = { ...overview, backups: done.backups };
    result = { key: "desk_restored", params: { path: done.safety } };
    renderResult();
    renderBackups();
    await reloadPage();
  }

  forget.addEventListener("click", async () => {
    if (!(await PA.ask(t("desk_forget_ask"), t("desk_forget")))) return;
    showError(overError, "");
    let done;
    try {
      done = await working(forget, "desk_forgetting", () => PA.api("desk/forget", {}));
    } catch (error) {
      showError(overError, error.message);
      return;
    }
    overview = { ...overview, backups: done.backups };
    renderBackups();
    PA.toast(t("desk_forgot", { path: done.safety }));
    await reloadPage();
  });

  reset.addEventListener("click", async () => {
    if (!(await PA.ask(t("desk_reset_ask"), t("desk_reset")))) return;
    showError(overError, "");
    let done;
    try {
      done = await working(reset, "desk_resetting", () => PA.api("desk/reset", {}));
    } catch (error) {
      showError(overError, error.message);
      return;
    }
    overview = { ...overview, backups: done.backups };
    renderBackups();
    await reloadPage();
    PA.toast(t("desk_reset_done", { path: done.safety }));
    // Nothing is set up any more: the first-run page is where to go next.
    PA.showView("settings");
  });

  renderText();
  PA.onLanguage(renderText);
  PA.onShow("app", load);
})();
