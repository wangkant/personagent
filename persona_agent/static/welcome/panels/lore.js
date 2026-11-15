"use strict";
PA.strings({
  en: {
    lore_title: "Lorebook",
    lore_entries: "Entries ({count})",
    lore_lead: "Background notes the character receives when one of their keywords appears in the recent messages, at most five at a time, highest priority first.",
    lore_builtin: "In use: the built-in lorebook, {count} entries.",
    lore_own: "In use: your own lorebook, {count} entries, from {path}.",
    lore_own_skipped: "{skipped} entries in the file have no keywords or no text and are not used.",
    lore_copy_note: "The built-in lorebook cannot be changed in place. Your first saved change writes it, with your change, to {path}; that file then replaces the built-in lorebook as a whole.",
    lore_lang: "Language of the file: {lang}, from the language the character speaks.",
    lore_broken_syntax: "The file {path} cannot be read: there is a JSON format error at line {line}, column {column}. Until it is corrected, the character uses none of its entries. Correct the file, save new entries here, or restore the built-in lorebook.",
    lore_broken_shape: "The file {path} cannot be read: its content is not in the lorebook format. Until it is corrected, the character uses none of its entries. Correct the file, save new entries here, or restore the built-in lorebook.",
    lore_broken_encoding: "The file {path} cannot be read: it is not saved as UTF-8. Until it is corrected, the character uses none of its entries. Save it again as UTF-8, save new entries here, or restore the built-in lorebook.",
    lore_broken_unreadable: "The file {path} cannot be opened. Check that it exists and that personagent may read it.",
    lore_empty: "There are no entries. Add one or import a file.",
    lore_priority: "Priority {priority}",
    lore_edit: "Edit",
    lore_delete: "Delete",
    lore_deleted: "The entry has been deleted. Save to apply the change.",
    lore_undo: "Undo",
    lore_add: "Add an entry",
    lore_new: "New entry",
    lore_f_name: "Name",
    lore_h_name: "Shown with the text in the prompt. Empty: the first keyword is used.",
    lore_f_keywords: "Keywords",
    lore_h_keywords: "Separated by commas. Case is ignored; a Latin or Cyrillic keyword matches only whole words.",
    lore_f_content: "Text",
    lore_h_content: "What the character is told when a keyword appears. At most {max} characters.",
    lore_f_priority: "Priority",
    lore_h_priority: "A whole number from {min} to {max}. Entries with a higher priority come first. Empty: 100.",
    lore_done: "Apply",
    lore_cancel: "Cancel",
    lore_err_keywords: "Enter at least one keyword: at most {count} keywords, each of at most {length} characters.",
    lore_err_content: "Enter the text, of at most {max} characters.",
    lore_err_name: "The name may have at most {max} characters.",
    lore_err_priority: "Enter a whole number from {min} to {max}, or leave the field empty.",
    lore_import: "Import a file",
    lore_importing: "Importing…",
    lore_import_hint: "A JSON file in personagent's lorebook format, or a World Info export from SillyTavern. Its entries are added below; disabled entries and entries without keywords or text are skipped. At most 1 MB.",
    lore_imported: "{taken} entries were taken from {file} and {skipped} were skipped. Save to use them.",
    lore_import_large: "The file is larger than 1 MB. Choose a smaller file.",
    lore_import_broken: "The file {file} is not valid JSON. Check that it is a lorebook or World Info export.",
    lore_import_unknown: "The file is neither a personagent lorebook nor a SillyTavern World Info export.",
    lore_import_empty: "The file contains no entry that can be used: every entry is disabled or lacks keywords or text.",
    lore_import_too_many: "With the imported entries there would be more than {max}. Delete some entries first.",
    lore_unsaved: "There are unsaved changes.",
    lore_save: "Save",
    lore_saving: "Saving…",
    lore_nothing: "There are no changes to save.",
    lore_saved_restarted: "Saved. The character has restarted and uses the new lorebook.",
    lore_saved_later: "Saved. The lorebook takes effect the next time the character starts.",
    lore_discard: "Discard changes",
    lore_reset: "Restore the built-in lorebook",
    lore_resetting: "Restoring…",
    lore_reset_ask: "Restore the built-in lorebook? Your file {name} is renamed to {name}.bak in the same folder, and the character uses the built-in entries again.",
    lore_reset_yes: "Restore",
    lore_reset_restarted: "The built-in lorebook is in use again, and the character has restarted. Your file was kept as {name}.bak.",
    lore_reset_later: "The built-in lorebook is in use again from the next time the character starts. Your file was kept as {name}.bak.",
    lore_too_many: "A lorebook may have at most {max} entries. Delete some entries, then save again.",
    lore_changed: "The lorebook file was changed outside this page. Choose “{discard}” to load the current entries, then make your changes again.",
    lore_too_large: "The lorebook is too large to save. Shorten or delete some entries.",
    lore_unknown: "This page is out of date. Close personagent and open it again.",
    lore_other_title: "Word filters and example dialogues",
    lore_other_hint: "These files can be replaced only by placing your own file in the data folder of the personagent folder; the character reads them as it starts.",
    lore_filters: "Word filters",
    lore_examples: "Example dialogues",
    lore_other_builtin: "{name}: built-in, {count} entries.",
    lore_other_own: "{name}: your own file, {count} entries, from {path}.",
    lore_other_skipped: "{count} entries in it cannot be used.",
    lore_other_syntax: "{name}: the file {path} cannot be read (JSON format error at line {line}, column {column}). The character uses none of its entries until it is corrected or removed.",
    lore_other_shape: "{name}: the file {path} cannot be read (its content is not in the expected format). The character uses none of its entries until it is corrected or removed.",
    lore_other_encoding: "{name}: the file {path} cannot be read (it is not saved as UTF-8). The character uses none of its entries until it is corrected or removed.",
    lore_other_unreadable: "{name}: the file {path} cannot be opened.",
  },
  zh: {
    lore_title: "背景设定",
    lore_entries: "条目（{count}）",
    lore_lead: "近期消息中出现某条背景设定的关键词时，角色会收到该条内容；每次最多五条，按优先级从高到低排列。",
    lore_builtin: "当前使用：内置背景设定，共 {count} 条。",
    lore_own: "当前使用：你自己的背景设定，共 {count} 条，文件为 {path}。",
    lore_own_skipped: "文件中有 {skipped} 条缺少关键词或内容，未被使用。",
    lore_copy_note: "内置背景设定不能直接修改。首次保存修改时，内置内容将连同你的修改一并写入 {path}，此后该文件将整体替换内置背景设定。",
    lore_lang: "文件语言：{lang}，取决于角色使用的语言。",
    lore_broken_syntax: "文件 {path} 无法读取：第 {line} 行第 {column} 列存在 JSON 格式错误。修正之前，角色不会使用其中任何一条。请修正该文件、在此保存新的条目，或恢复内置背景设定。",
    lore_broken_shape: "文件 {path} 无法读取：其内容不符合背景设定的格式。修正之前，角色不会使用其中任何一条。请修正该文件、在此保存新的条目，或恢复内置背景设定。",
    lore_broken_encoding: "文件 {path} 无法读取：该文件不是以 UTF-8 编码保存的。修正之前，角色不会使用其中任何一条。请以 UTF-8 编码重新保存、在此保存新的条目，或恢复内置背景设定。",
    lore_broken_unreadable: "文件 {path} 无法打开。请确认该文件存在，且 personagent 有权读取。",
    lore_empty: "暂无条目。请添加条目或导入文件。",
    lore_priority: "优先级 {priority}",
    lore_edit: "编辑",
    lore_delete: "删除",
    lore_deleted: "已删除该条目，保存后生效。",
    lore_undo: "撤销",
    lore_add: "添加条目",
    lore_new: "新条目",
    lore_f_name: "名称",
    lore_h_name: "与内容一同出现在提示词中。留空则使用第一个关键词。",
    lore_f_keywords: "关键词",
    lore_h_keywords: "以逗号分隔，不区分大小写；拉丁字母或西里尔字母的关键词仅匹配完整的词。",
    lore_f_content: "内容",
    lore_h_content: "出现关键词时告知角色的内容，最多 {max} 字。",
    lore_f_priority: "优先级",
    lore_h_priority: "{min} 至 {max} 之间的整数，优先级高的条目排在前面。留空即为 100。",
    lore_done: "确定",
    lore_cancel: "取消",
    lore_err_keywords: "请至少填写一个关键词：最多 {count} 个，每个不超过 {length} 字。",
    lore_err_content: "请填写内容，最多 {max} 字。",
    lore_err_name: "名称最多 {max} 字。",
    lore_err_priority: "请填写 {min} 至 {max} 之间的整数，或留空。",
    lore_import: "导入文件",
    lore_importing: "正在导入…",
    lore_import_hint: "支持 personagent 背景设定格式的 JSON 文件，以及 SillyTavern 导出的世界书（World Info）。文件中的条目将添加到下方；已停用的条目以及缺少关键词或内容的条目将被跳过。文件不超过 1 MB。",
    lore_imported: "已从 {file} 中导入 {taken} 条，跳过 {skipped} 条。保存后生效。",
    lore_import_large: "文件超过 1 MB，请选择较小的文件。",
    lore_import_broken: "文件 {file} 不是有效的 JSON。请确认它是背景设定文件或世界书导出文件。",
    lore_import_unknown: "该文件既不是 personagent 的背景设定，也不是 SillyTavern 导出的世界书。",
    lore_import_empty: "该文件中没有可用的条目：所有条目均已停用，或缺少关键词或内容。",
    lore_import_too_many: "加上导入的条目后将超过 {max} 条。请先删除部分条目。",
    lore_unsaved: "有尚未保存的修改。",
    lore_save: "保存",
    lore_saving: "正在保存…",
    lore_nothing: "没有需要保存的更改。",
    lore_saved_restarted: "已保存，角色已重新启动并使用新的背景设定。",
    lore_saved_later: "已保存，背景设定将在角色下次启动时生效。",
    lore_discard: "放弃修改",
    lore_reset: "恢复内置背景设定",
    lore_resetting: "正在恢复…",
    lore_reset_ask: "确定恢复内置背景设定吗？你的文件 {name} 将在同一文件夹中改名为 {name}.bak，角色将重新使用内置条目。",
    lore_reset_yes: "恢复",
    lore_reset_restarted: "已恢复内置背景设定，角色已重新启动。你的文件已保留为 {name}.bak。",
    lore_reset_later: "已恢复内置背景设定，将在角色下次启动时生效。你的文件已保留为 {name}.bak。",
    lore_too_many: "背景设定最多 {max} 条。请删除部分条目后重新保存。",
    lore_changed: "背景设定文件已在本页之外被修改。请点击「{discard}」读取当前条目，再重新修改。",
    lore_too_large: "背景设定过大，无法保存。请缩短或删除部分条目。",
    lore_unknown: "此页面已过期，请关闭 personagent 后重新打开。",
    lore_other_title: "屏蔽词和示例对话",
    lore_other_hint: "这两类文件只能通过在 personagent 文件夹的 data 文件夹中放入自己的文件来替换；角色在启动时读取。",
    lore_filters: "屏蔽词",
    lore_examples: "示例对话",
    lore_other_builtin: "{name}：内置，共 {count} 条。",
    lore_other_own: "{name}：你自己的文件，共 {count} 条，文件为 {path}。",
    lore_other_skipped: "其中 {count} 条无法使用。",
    lore_other_syntax: "{name}：文件 {path} 无法读取（第 {line} 行第 {column} 列存在 JSON 格式错误）。修正或移除之前，角色不会使用其中任何一条。",
    lore_other_shape: "{name}：文件 {path} 无法读取（内容不符合应有的格式）。修正或移除之前，角色不会使用其中任何一条。",
    lore_other_encoding: "{name}：文件 {path} 无法读取（该文件不是以 UTF-8 编码保存的）。修正或移除之前，角色不会使用其中任何一条。",
    lore_other_unreadable: "{name}：文件 {path} 无法打开。",
  },
});
(() => {
  const root = PA.$("lore-root");
  const t = PA.t;
  const MAX_FILE = 1_000_000;
  let data = null,
    entries = [],
    dirty = false,
    busy = false,
    errorCode = "",
    importNote = null,
    serial = 0;

  const el = (tag, cls, parent, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    if (parent) parent.append(node);
    return node;
  };
  const button = (cls, text, parent, id) => {
    const node = el("button", cls, parent, text);
    node.type = "button";
    if (id) node.id = id;
    return node;
  };
  const limits = () =>
    (data && data.limits) || { entries: 200, keywords: 200, keyword: 100, content: 4000, name: 80, priority: [-9999, 9999] };
  const fileName = (path) => String(path || "").split(/[\\/]/).pop();
  const splitKeywords = (text) => {
    const seen = [];
    for (const raw of String(text).split(/[,，、\n]/)) {
      const word = raw.split(/\s+/).filter(Boolean).join(" ");
      if (word && !seen.some((s) => s.toLowerCase() === word.toLowerCase())) seen.push(word);
    }
    return seen;
  };
  const same = (a, b) => a.content === b.content && a.keywords.join("\n") === b.keywords.join("\n");
  const fromServer = (list) =>
    list.map((e) => ({ name: e.name, keywords: [...e.keywords], content: e.content, priority: e.priority, key: ++serial }));

  // ---- one entry: shown, or open in its editor with a draft
  function check(draft) {
    const lim = limits();
    const keywords = splitKeywords(draft.keywords);
    if (!keywords.length || keywords.length > lim.keywords || keywords.some((k) => k.length > lim.keyword))
      return "keywords";
    const content = draft.content.trim();
    if (!content || content.length > lim.content) return "content";
    if (draft.name.trim().length > lim.name) return "name";
    const p = draft.priority.trim();
    if (p !== "" && (!/^-?\d+$/.test(p) || Number(p) < lim.priority[0] || Number(p) > lim.priority[1]))
      return "priority";
    return "";
  }
  function fieldError(field) {
    const lim = limits();
    if (field === "keywords") return t("lore_err_keywords", { count: lim.keywords, length: lim.keyword });
    if (field === "content") return t("lore_err_content", { max: lim.content });
    if (field === "name") return t("lore_err_name", { max: lim.name });
    return t("lore_err_priority", { min: lim.priority[0], max: lim.priority[1] });
  }
  const draftOf = (entry) => ({
    name: entry.name || "",
    keywords: entry.keywords.join(", "),
    content: entry.content,
    priority: entry.priority === 100 && entry.isNew ? "" : String(entry.priority),
  });
  function applyDraft(entry) {
    const field = check(entry.draft);
    entry.bad = field;
    if (field) return false;
    const d = entry.draft;
    const keywords = splitKeywords(d.keywords);
    const changed =
      entry.isNew ||
      d.name.trim() !== (entry.name || "") ||
      keywords.join("\n") !== entry.keywords.join("\n") ||
      d.content.trim() !== entry.content ||
      Number(d.priority.trim() || 100) !== entry.priority;
    Object.assign(entry, {
      name: d.name.trim(),
      keywords,
      content: d.content.trim(),
      priority: Number(d.priority.trim() || 100),
    });
    entry.draft = null;
    entry.isNew = false;
    if (changed) dirty = true;
    return true;
  }

  function editor(entry, box, index) {
    const d = entry.draft;
    const id = (name) => `lore-${entry.key}-${name}`;
    const lim = limits();
    const field = (name, kind, hint) => {
      const wrap = el("div", "lore-field", box);
      wrap.dataset.field = name;
      const label = el("label", "", wrap, t("lore_f_" + name));
      label.htmlFor = id(name);
      const input = el(kind, "", wrap);
      input.id = id(name);
      input.value = d[name];
      input.spellcheck = false;
      if (kind === "input") input.autocomplete = "off";
      input.addEventListener("input", () => {
        d[name] = input.value;
        dirty = true;
        showUnsaved();
      });
      el("p", "field-note", wrap, hint);
      if (entry.bad === name) {
        wrap.classList.add("lore-bad");
        const line = el("p", "lore-entry-error", wrap, fieldError(name));
        line.setAttribute("role", "alert");
      }
      return input;
    };
    field("name", "input", t("lore_h_name")).maxLength = lim.name * 2;
    field("keywords", "input", t("lore_h_keywords"));
    const text = field("content", "textarea", t("lore_h_content", { max: lim.content }));
    text.rows = 5;
    const priority = field("priority", "input", t("lore_h_priority", { min: lim.priority[0], max: lim.priority[1] }));
    priority.inputMode = "numeric";
    priority.placeholder = "100";
    const actions = el("div", "lore-entry-actions", box);
    const cancel = button("quiet", t("lore_cancel"), actions, id("cancel"));
    const done = button("secondary", t("lore_done"), actions, id("done"));
    cancel.addEventListener("click", () => {
      if (entry.isNew) entries.splice(entries.indexOf(entry), 1);
      entry.draft = null;
      entry.bad = "";
      render();
    });
    done.addEventListener("click", () => {
      const ok = applyDraft(entry);
      render();
      const again = root.querySelector(`[data-key="${entry.key}"]`);
      if (!ok && again) focusBad(again);
      else if (again) again.querySelector(".lore-edit")?.focus();
    });
    box.addEventListener("keydown", (event) => {
      if (event.key === "Escape") cancel.click();
    });
    return index;
  }
  function focusBad(box) {
    const bad = box.querySelector(".lore-bad input, .lore-bad textarea");
    if (bad) bad.focus();
    box.scrollIntoView({ block: "nearest" });
  }

  function entryRow(entry, index, list) {
    const box = el("div", "lore-entry", list);
    box.dataset.key = entry.key;
    box.dataset.index = index;
    if (entry.draft) {
      box.classList.add("is-editing");
      el("strong", "lore-entry-name", box, entry.isNew ? t("lore_new") : entry.name || entry.keywords[0]);
      editor(entry, box, index);
      return;
    }
    const head = el("div", "lore-entry-head", box);
    el("strong", "lore-entry-name", head, entry.name || entry.keywords[0]);
    el("span", "lore-entry-priority", head, t("lore_priority", { priority: entry.priority }));
    const actions = el("span", "lore-entry-buttons", head);
    const edit = button("quiet lore-edit", t("lore_edit"), actions, `lore-${entry.key}-edit`);
    const remove = button("quiet lore-delete", t("lore_delete"), actions, `lore-${entry.key}-delete`);
    el("p", "lore-entry-keywords", box, entry.keywords.join(", "));
    el("p", "lore-entry-content", box, entry.content);
    edit.addEventListener("click", () => {
      entry.draft = draftOf(entry);
      entry.bad = "";
      render();
      root.querySelector(`#lore-${entry.key}-keywords`)?.focus();
    });
    remove.addEventListener("click", () => {
      const at = entries.indexOf(entry);
      entries.splice(at, 1);
      const wasDirty = dirty;
      dirty = true;
      render();
      PA.toast(t("lore_deleted"), {
        label: t("lore_undo"),
        run: () => {
          entries.splice(Math.min(at, entries.length), 0, entry);
          dirty = wasDirty || entries.length !== (data ? data.entries.length : 0);
          render();
        },
      });
    });
  }

  // ---- the card
  const card = el("div", "card lore-card", root);
  card.id = "lore-card";
  const title = el("h2", "", card);
  const lead = el("p", "field-note", card);
  const source = el("p", "field-note lore-source", card);
  source.id = "lore-source";
  const copyNote = el("p", "field-note lore-copy", card);
  copyNote.id = "lore-copy-note";
  const broken = el("div", "error", card);
  broken.id = "lore-broken";
  broken.setAttribute("role", "alert");
  // Eight built-in entries would push the rest of the view down: folded until they are someone's own.
  const fold = el("details", "lore-fold", card);
  fold.id = "lore-fold";
  const foldSummary = el("summary", "", fold);
  let foldSet = false;
  const list = el("div", "lore-list", fold);
  list.id = "lore-list";
  const tools = el("div", "lore-tools", card);
  const addButton = button("secondary", "", tools, "lore-add");
  const importButton = button("secondary", "", tools, "lore-import");
  const picker = el("input", "", tools);
  picker.type = "file";
  picker.accept = ".json,application/json";
  picker.id = "lore-import-file";
  picker.hidden = true;
  picker.tabIndex = -1;
  const importHint = el("p", "field-note", card);
  const importLine = el("p", "field-note lore-imported", card);
  importLine.id = "lore-imported";
  importLine.setAttribute("role", "status");
  const error = el("div", "error", card);
  error.id = "lore-error";
  error.setAttribute("role", "alert");
  error.hidden = true;
  const actions = el("div", "card-actions lore-actions", card);
  const resetButton = button("quiet", "", actions, "lore-reset");
  const unsaved = el("span", "lore-unsaved", actions);
  unsaved.id = "lore-unsaved";
  const discardButton = button("quiet", "", actions, "lore-discard");
  const saveButton = button("primary", "", actions, "lore-save");
  const otherTitle = el("h3", "lore-subtitle", card);
  const otherHint = el("p", "field-note", card);
  const otherLines = el("div", "lore-other", card);
  otherLines.id = "lore-other";

  function showUnsaved() {
    unsaved.textContent = dirty ? t("lore_unsaved") : "";
    discardButton.hidden = !dirty;
    // A change must be seen: an edited list is never left folded.
    if (dirty) fold.open = true;
  }
  function brokenText(state, prefix, fields) {
    const reason = state.error.reason || "shape";
    return t(`${prefix}_${reason}`, { ...fields, path: state.path, line: state.error.line, column: state.error.column });
  }
  function errorText(code) {
    const lim = limits();
    if (code === "lore_too_many" || code === "lore_import_too_many") return t(code, { max: lim.entries });
    if (code === "lore_changed") return t(code, { discard: t("lore_discard") });
    if (code === "too_large") return t("lore_too_large");
    return t(code);
  }
  function showError(code, fields) {
    errorCode = code;
    error.textContent = fields ? t(code, fields) : errorText(code);
    error.hidden = false;
    error.dataset.fields = fields ? JSON.stringify(fields) : "";
  }
  function clearError() {
    errorCode = "";
    error.hidden = true;
  }

  function render() {
    title.textContent = t("lore_title");
    lead.textContent = t("lore_lead");
    addButton.textContent = t("lore_add");
    importButton.textContent = busy === "import" ? t("lore_importing") : t("lore_import");
    importHint.textContent = t("lore_import_hint");
    saveButton.textContent = busy === "save" ? t("lore_saving") : t("lore_save");
    resetButton.textContent = busy === "reset" ? t("lore_resetting") : t("lore_reset");
    discardButton.textContent = t("lore_discard");
    for (const node of [saveButton, resetButton, discardButton, importButton, addButton]) node.disabled = !!busy;
    otherTitle.textContent = t("lore_other_title");
    otherHint.textContent = t("lore_other_hint");
    if (errorCode && !error.hidden)
      error.textContent = error.dataset.fields ? t(errorCode, JSON.parse(error.dataset.fields)) : errorText(errorCode);
    importLine.hidden = !importNote;
    if (importNote) importLine.textContent = t("lore_imported", importNote);
    showUnsaved();
    if (!data) return;
    const failed = data.error && data.error.reason;
    source.textContent =
      (data.own
        ? t("lore_own", { count: data.entries.length, path: data.path })
        : t("lore_builtin", { count: data.entries.length })) +
      (data.own && data.skipped ? " " + t("lore_own_skipped", { skipped: data.skipped }) : "") +
      " " +
      t("lore_lang", { lang: data.lang });
    source.hidden = !!failed;
    foldSummary.textContent = t("lore_entries", { count: list.children.length });
    fold.hidden = !!failed;
    if (!foldSet) {
      foldSet = true;
      fold.open = !!data.own;
    }
    copyNote.textContent = t("lore_copy_note", { path: data.file });
    copyNote.hidden = data.own || !!failed;
    broken.hidden = !failed;
    if (failed) broken.textContent = brokenText(data, "lore_broken", {});
    resetButton.hidden = !data.own;
    list.replaceChildren();
    if (!entries.length) el("p", "field-note lore-empty", list, t("lore_empty"));
    entries.forEach((entry, i) => entryRow(entry, i, list));
    otherLines.replaceChildren();
    for (const [kind, nameKey] of [
      ["filters", "lore_filters"],
      ["examples", "lore_examples"],
    ]) {
      const state = data[kind];
      const name = t(nameKey);
      const line = el("p", "field-note lore-other-line", otherLines);
      line.dataset.kind = kind;
      if (state.error && state.error.reason) {
        line.classList.add("lore-other-bad");
        line.textContent = brokenText(state, "lore_other", { name });
      } else {
        line.textContent =
          t(state.own ? "lore_other_own" : "lore_other_builtin", { name, count: state.count, path: state.path }) +
          (state.skipped ? " " + t("lore_other_skipped", { count: state.skipped }) : "");
      }
    }
  }

  function take(view) {
    data = view;
    entries = fromServer(view.entries);
    dirty = false;
    importNote = null;
    render();
  }

  addButton.addEventListener("click", () => {
    if (entries.length >= limits().entries) {
      showError("lore_too_many");
      return;
    }
    const entry = { name: "", keywords: [], content: "", priority: 100, key: ++serial, isNew: true };
    entry.draft = draftOf(entry);
    entries.push(entry);
    render();
    root.querySelector(`#lore-${entry.key}-name`)?.focus();
  });

  importButton.addEventListener("click", () => {
    clearError();
    picker.value = "";
    picker.click();
  });
  picker.addEventListener("change", async () => {
    const file = picker.files && picker.files[0];
    if (!file) return;
    clearError();
    importNote = null;
    if (file.size > MAX_FILE) {
      showError("lore_import_large");
      render();
      return;
    }
    busy = "import";
    render();
    try {
      let parsed;
      try {
        parsed = JSON.parse(await file.text());
      } catch (failure) {
        showError("lore_import_broken", { file: file.name });
        return;
      }
      const found = await PA.api("lore/import", { data: parsed });
      const fresh = found.entries.filter((e) => !entries.some((have) => same(have, e)));
      if (entries.length + fresh.length > limits().entries) {
        showError("lore_import_too_many");
        return;
      }
      entries.push(...fromServer(fresh));
      importNote = { taken: fresh.length, skipped: found.skipped + found.entries.length - fresh.length, file: file.name };
      if (fresh.length) dirty = true;
    } catch (failure) {
      showError(failure.message);
    } finally {
      busy = false;
      picker.value = "";
      render();
    }
  });

  saveButton.addEventListener("click", async () => {
    if (busy || !data) return;
    clearError();
    // Open editors are applied first, so nothing typed is lost.
    for (const entry of entries)
      if (entry.draft && !applyDraft(entry)) {
        render();
        focusBad(root.querySelector(`[data-key="${entry.key}"]`));
        return;
      }
    if (!dirty) {
      render();
      PA.toast(t("lore_nothing"));
      return;
    }
    busy = "save";
    render();
    try {
      const payload = {
        stamp: data.stamp,
        entries: entries.map((e) => ({ name: e.name, keywords: e.keywords, content: e.content, priority: e.priority })),
      };
      const result = await PA.api("lore", payload);
      busy = false;
      take(result);
      PA.toast(t(result.restarted ? "lore_saved_restarted" : "lore_saved_later"));
      PA.refresh().catch(() => {});
    } catch (failure) {
      busy = false;
      const match = /^lore_invalid:(\d+):(\w+)$/.exec(failure.message);
      if (match && entries[Number(match[1])]) {
        const entry = entries[Number(match[1])];
        entry.draft = draftOf(entry);
        entry.bad = match[2];
        render();
        focusBad(root.querySelector(`[data-key="${entry.key}"]`));
        return;
      }
      showError(failure.message);
      render();
    }
  });

  discardButton.addEventListener("click", () => {
    clearError();
    load(true);
  });

  resetButton.addEventListener("click", async () => {
    if (busy || !data || !data.own) return;
    const name = fileName(data.path);
    if (!(await PA.ask(t("lore_reset_ask", { name }), t("lore_reset_yes")))) return;
    clearError();
    busy = "reset";
    render();
    try {
      const result = await PA.api("lore/reset", { stamp: data.stamp });
      busy = false;
      take(result);
      PA.toast(t(result.restarted ? "lore_reset_restarted" : "lore_reset_later", { name }));
      PA.refresh().catch(() => {});
    } catch (failure) {
      busy = false;
      showError(failure.message);
      render();
    }
  });

  async function load(force) {
    if (busy || (dirty && !force)) return;
    try {
      take(await PA.api("lore"));
      clearError();
    } catch (failure) {
      showError(failure.message);
    }
    render();
  }
  function visible() {
    const on = !!(PA.state && PA.state.configured && PA.view === "settings");
    root.hidden = !on;
    return on;
  }
  PA.onShow("settings", () => {
    if (visible()) load(false);
  });
  PA.onState(() => visible());
  PA.onLanguage(render);
  render();
})();
