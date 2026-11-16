"use strict";
PA.strings({
  en: {
    cards_title: "Character card",
    cards_lead: "Bring in a character someone shared as a Tavern character card, or save this character as one. Cards from SillyTavern and the sites that share them are accepted as PNG, JSON or CHARX files.",
    cards_import: "Import a character card",
    cards_reading: "Reading…",
    cards_import_hint: "Nothing changes until you have reviewed the preview and chosen “Use this character”. At most 16 MB.",
    cards_preview: "Preview: {file}",
    cards_preview_lead: "Choose the parts to use. Each part replaces what the character has now.",
    cards_part_picture: "Use the picture as the character's avatar",
    cards_picture_none: "The card holds no picture, so the avatar stays as it is.",
    cards_picture_too_big: "The card's picture is too large to use, so the avatar stays as it is.",
    cards_picture_unreadable: "The card's picture cannot be read, so the avatar stays as it is.",
    cards_part_name: "Name",
    cards_name_cut: "The card's name is longer than 64 characters and has been shortened here; adjust it if needed.",
    cards_name_learned: "What the character learned as {old} is kept, but it applies only while the character is called {old}. Under the name {name} it starts learning anew; it uses what it learned again if the name is changed back. Memory of people and chats is kept either way.",
    cards_nickname: "The nickname {nick} is added to the names that call the character.",
    cards_part_persona: "Persona",
    cards_persona_hint: "Composed from the card's description, personality, situation and instructions. Edit it here before using it.",
    cards_persona_count: "{n} characters. Every reply sends the whole persona to the model, so a longer persona costs more per reply.",
    cards_persona_over: "The persona is longer than {max} characters. Shorten it before using it.",
    cards_persona_instructions: "The last section holds the card's instructions, which were written for roleplay programs and may ask for narration or actions in asterisks that chat apps do not show. Delete what does not suit a chat.",
    cards_persona_macros: "These placeholders are not replaced and appear as written: {list}.",
    cards_persona_backup: "Your current persona is kept as persona.txt.bak and a dated copy beside it.",
    cards_part_examples: "Example dialogues ({n})",
    cards_examples_none: "The card holds no example dialogues.",
    cards_examples_left: "{n} example dialogues were left out because they are too long or there are more than 200.",
    cards_examples_replace: "They replace the example dialogues in use as a whole, in {path}.",
    cards_examples_replace_own: "They replace your own example dialogues in {path} as a whole; that file is kept as a dated copy.",
    cards_part_lore: "Lorebook entries ({n})",
    cards_lore_none: "The card holds no lorebook entries that can be used.",
    cards_lore_replace: "They replace the lorebook in use as a whole, in {path}.",
    cards_lore_replace_own: "They replace your own lorebook in {path} as a whole; that file is kept as a dated copy.",
    cards_skip_regex: "{n} that match by regular expression",
    cards_skip_too_many: "{n} beyond the limit of 200",
    cards_partly_decorators: "{n} entries had decorator lines (starting with @@), which were removed.",
    cards_greeting: "Greeting from the card (not used)",
    cards_greeting_hint: "personagent has no fixed greeting: the character opens conversations in its own way. Copy the text into the persona if you want it to shape how the character speaks.",
    cards_greeting_more: "The card has {n} more greetings, also not used.",
    cards_creator_notes: "Notes from the card's author",
    cards_creator_hint: "Meant for you; the character does not receive them.",
    cards_cancel: "Cancel",
    cards_use: "Use this character",
    cards_using: "Applying…",
    cards_used: "The character has restarted with the imported card.",
    cards_used_later: "The imported card is saved and takes effect the next time the character starts.",
    cards_kept: "Kept copies: {files}.",
    cards_used_aliases: "The nickname was not added, because persona.card.json cannot be read.",
    cards_choose_one: "Choose at least one part.",
    cards_export_title: "Save as a character card",
    cards_export_hint: "Saves the name, the persona, your own example dialogues and lorebook, and the picture, in a file other programs that read character cards can open. API keys, memory, what the character learned and the names of people in your chats are not included.",
    cards_export_to: "Save to",
    cards_target_desktop: "Desktop",
    cards_target_documents: "Documents",
    cards_save_png: "Save as PNG card",
    cards_save_json: "Save as JSON card",
    cards_saving: "Saving…",
    cards_saved: "Saved: {path}",
    cards_no_targets: "No Desktop or Documents folder was found on this computer.",
    cards_draft_label: "Describe the character in a sentence or two",
    cards_draft_placeholder: "For example: a retired lighthouse keeper who loves crosswords and distrusts smartphones",
    cards_draft: "Write a draft",
    cards_drafting: "Writing…",
    cards_draft_note: "Sends one request to your model service. The draft goes into the box below and is saved only when you choose “Save persona”.",
    cards_drafted: "The draft is in the Persona box. It has not been saved.",
    cards_draft_undo: "Restore the previous text",
    cards_draft_restored: "The previous text is back in the Persona box.",
    card_too_large: "The file is larger than 16 MB, or a part inside it is too large.",
    card_unknown: "The file is not a character card. Choose a PNG or JSON character card, or a CHARX file.",
    card_broken: "The file is damaged or cannot be read as a character card.",
    card_no_data: "This picture holds no character card.",
    card_unsafe: "The file is built in a way that is not safe to open, so it was not read.",
    card_no_name: "The card has no name for the character.",
    card_expired: "This preview is no longer current. Import the card again.",
    card_nothing: "Choose at least one part.",
    card_name: "Enter a name of 1 to 64 characters.",
    card_persona: "The persona cannot be empty or longer than 16,000 characters.",
    card_aliases_unreadable: "The nickname was not added, because persona.card.json cannot be read.",
    card_invalid_place: "Choose where to save the card.",
    card_save_failed: "The card could not be saved there. Check the free space, or choose another location.",
    draft_idea: "Describe the character in 1 to 500 characters.",
    draft_empty: "The model returned no text. Try again, or describe the character differently.",
  },
  zh: {
    cards_title: "角色卡",
    cards_lead: "导入他人以 Tavern 角色卡形式分享的角色，或将当前角色保存为角色卡。支持来自 SillyTavern 及各类角色卡分享网站的 PNG、JSON 或 CHARX 文件。",
    cards_import: "导入角色卡",
    cards_reading: "正在读取…",
    cards_import_hint: "查看预览并点击「使用此角色」之前，不会做任何更改。文件不超过 16 MB。",
    cards_preview: "预览：{file}",
    cards_preview_lead: "请选择要使用的部分。所选部分将替换角色当前的对应内容。",
    cards_part_picture: "将图片设为角色头像",
    cards_picture_none: "角色卡中没有图片，头像保持不变。",
    cards_picture_too_big: "角色卡中的图片过大，无法使用，头像保持不变。",
    cards_picture_unreadable: "角色卡中的图片无法读取，头像保持不变。",
    cards_part_name: "名称",
    cards_name_cut: "角色卡中的名称超过 64 个字符，此处已截短，可按需修改。",
    cards_name_learned: "角色以「{old}」之名学到的内容会保留，但仅在角色名为「{old}」时适用。改名为「{name}」后将重新开始学习；改回原名后会重新使用此前学到的内容。对人和聊天的记忆在两种情况下都会保留。",
    cards_nickname: "别名「{nick}」将加入可点名角色的名称中。",
    cards_part_persona: "人设",
    cards_persona_hint: "由角色卡中的描述、性格、情境和说明合成。使用前可在此修改。",
    cards_persona_count: "{n} 个字符。每次回复都会将完整人设发送给模型，人设越长，每次回复的费用越高。",
    cards_persona_over: "人设超过 {max} 个字符，请先缩短。",
    cards_persona_instructions: "最后一部分是角色卡中的说明，原本为角色扮演程序编写，可能要求旁白或用星号标注动作，而聊天平台不会显示这些格式。请删除不适合聊天的内容。",
    cards_persona_macros: "以下占位符不会被替换，将按原样出现：{list}。",
    cards_persona_backup: "当前人设将另存为 persona.txt.bak，并在旁边保留一份带日期的副本。",
    cards_part_examples: "示例对话（{n}）",
    cards_examples_none: "角色卡中没有示例对话。",
    cards_examples_left: "有 {n} 段示例对话因过长或超过 200 段而未导入。",
    cards_examples_replace: "将整体替换当前使用的示例对话，写入 {path}。",
    cards_examples_replace_own: "将整体替换你自己的示例对话文件 {path}；原文件会保留一份带日期的副本。",
    cards_part_lore: "背景设定（{n} 条）",
    cards_lore_none: "角色卡中没有可用的背景设定条目。",
    cards_lore_replace: "将整体替换当前使用的背景设定，写入 {path}。",
    cards_lore_replace_own: "将整体替换你自己的背景设定文件 {path}；原文件会保留一份带日期的副本。",
    cards_skip_regex: "按正则表达式匹配的 {n} 条",
    cards_skip_too_many: "超出 200 条上限的 {n} 条",
    cards_partly_decorators: "其中 {n} 条含有以 @@ 开头的修饰行，已删除这些行。",
    cards_greeting: "角色卡中的开场白（不使用）",
    cards_greeting_hint: "personagent 没有固定的开场白，角色会以自己的方式开始对话。如希望它影响角色的说话方式，可将其复制到人设中。",
    cards_greeting_more: "角色卡中另有 {n} 条开场白，同样不使用。",
    cards_creator_notes: "角色卡作者的说明",
    cards_creator_hint: "供你阅读，不会提供给角色。",
    cards_cancel: "取消",
    cards_use: "使用此角色",
    cards_using: "正在应用…",
    cards_used: "角色已按导入的角色卡重新启动。",
    cards_used_later: "导入的角色卡已保存，将在角色下次启动时生效。",
    cards_kept: "已保留的副本：{files}。",
    cards_used_aliases: "由于 persona.card.json 无法读取，别名未能添加。",
    cards_choose_one: "请至少选择一个部分。",
    cards_export_title: "保存为角色卡",
    cards_export_hint: "保存名称、人设、你自己的示例对话和背景设定以及图片，其他支持角色卡的程序可以打开该文件。不包含 API 密钥、记忆、角色学到的内容以及聊天中他人的名字。",
    cards_export_to: "保存位置",
    cards_target_desktop: "桌面",
    cards_target_documents: "文档",
    cards_save_png: "保存为 PNG 角色卡",
    cards_save_json: "保存为 JSON 角色卡",
    cards_saving: "正在保存…",
    cards_saved: "已保存：{path}",
    cards_no_targets: "在这台计算机上未找到桌面或文档文件夹。",
    cards_draft_label: "用一两句话描述角色",
    cards_draft_placeholder: "例如：一位退休的灯塔看守人，热爱填字游戏，不信任智能手机",
    cards_draft: "生成草稿",
    cards_drafting: "正在生成…",
    cards_draft_note: "将向你的模型服务发送一次请求。草稿会填入下方的框中，只有点击「保存人设」后才会保存。",
    cards_drafted: "草稿已填入「人设」框，尚未保存。",
    cards_draft_undo: "恢复之前的内容",
    cards_draft_restored: "已在「人设」框中恢复之前的内容。",
    card_too_large: "文件超过 16 MB，或其中某一部分过大。",
    card_unknown: "该文件不是角色卡。请选择 PNG 或 JSON 角色卡，或 CHARX 文件。",
    card_broken: "文件已损坏，或无法作为角色卡读取。",
    card_no_data: "这张图片中没有角色卡数据。",
    card_unsafe: "该文件的结构不安全，因此未予读取。",
    card_no_name: "角色卡中没有角色名称。",
    card_expired: "此预览已失效，请重新导入角色卡。",
    card_nothing: "请至少选择一个部分。",
    card_name: "请填写 1 至 64 个字符的名称。",
    card_persona: "人设不能为空，且不能超过 16000 个字符。",
    card_aliases_unreadable: "由于 persona.card.json 无法读取，别名未能添加。",
    card_invalid_place: "请选择保存位置。",
    card_save_failed: "无法保存到该位置。请检查磁盘空间，或选择其他位置。",
    draft_idea: "请用 1 至 500 个字符描述角色。",
    draft_empty: "模型没有返回内容。请重试，或换一种方式描述角色。",
  },
});
(() => {
  const root = PA.$("cards-root");
  const t = PA.t;
  const MAX_FILE = 16 * 1024 * 1024;
  let overview = null,
    preview = null,
    busy = "",
    beforeDraft = null,
    draftText = null;

  const el = (tag, cls, parent, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    if (parent) parent.append(node);
    return node;
  };
  const button = (cls, parent, id) => {
    const node = el("button", cls, parent);
    node.type = "button";
    node.id = id;
    return node;
  };
  const check = (parent, id) => {
    const label = el("label", "check", parent);
    const box = el("input", "", label);
    box.type = "checkbox";
    box.id = id;
    box.checked = true;
    const text = el("span", "", label);
    return { label, box, text };
  };
  const showError = (node, code, fields) => {
    node.dataset.code = code || "";
    node.dataset.fields = fields ? JSON.stringify(fields) : "";
    node.textContent = code ? t(code, fields || {}) : "";
    node.hidden = !code;
  };
  const retell = (node) => {
    if (node.dataset.code) node.textContent = t(node.dataset.code, node.dataset.fields ? JSON.parse(node.dataset.fields) : {});
  };
  const fileName = (path) => String(path || "").split(/[\\/]/).pop();

  // ---- the section under the persona
  const card = el("div", "card cards-card", root);
  card.id = "cards-card";
  const title = el("h2", "", card);
  const lead = el("p", "field-note", card);
  const tools = el("div", "cards-tools", card);
  const importButton = button("secondary", tools, "cards-import");
  const picker = el("input", "", tools);
  picker.type = "file";
  picker.accept = ".png,.json,.charx,image/png,application/json";
  picker.id = "cards-file";
  picker.hidden = true;
  picker.tabIndex = -1;
  const importHint = el("p", "field-note", card);
  const error = el("div", "error", card);
  error.id = "cards-error";
  error.setAttribute("role", "alert");
  error.hidden = true;

  // ---- the preview
  const box = el("div", "cards-preview", card);
  box.id = "cards-preview";
  box.hidden = true;
  const previewTitle = el("h3", "cards-subtitle", box);
  previewTitle.id = "cards-preview-title";
  previewTitle.tabIndex = -1;
  const previewLead = el("p", "field-note", box);
  const pictureRow = el("div", "cards-part cards-picture-row", box);
  const image = el("img", "cards-picture", pictureRow);
  image.alt = "";
  const pictureSide = el("div", "", pictureRow);
  const pictureCheck = check(pictureSide, "cards-part-picture");
  const pictureNote = el("p", "field-note", pictureSide);

  const namePart = el("div", "cards-part", box);
  const nameCheck = check(namePart, "cards-part-name");
  const nameInput = el("input", "", namePart);
  nameInput.id = "cards-name";
  nameInput.maxLength = 64;
  nameInput.autocomplete = "off";
  nameInput.setAttribute("aria-labelledby", "cards-part-name-text");
  nameCheck.text.id = "cards-part-name-text";
  const nameNote = el("p", "field-note", namePart);

  const personaPart = el("div", "cards-part", box);
  const personaCheck = check(personaPart, "cards-part-persona");
  personaCheck.text.id = "cards-part-persona-text";
  const personaHint = el("p", "field-note", personaPart);
  const personaInput = el("textarea", "", personaPart);
  personaInput.id = "cards-persona";
  personaInput.rows = 12;
  personaInput.spellcheck = false;
  personaInput.setAttribute("aria-labelledby", "cards-part-persona-text");
  const personaCount = el("p", "field-note cards-count", personaPart);
  personaCount.id = "cards-persona-count";
  const personaNotes = el("div", "", personaPart);

  const examplesPart = el("div", "cards-part", box);
  const examplesCheck = check(examplesPart, "cards-part-examples");
  const examplesNote = el("p", "field-note", examplesPart);
  const lorePart = el("div", "cards-part", box);
  const loreCheck = check(lorePart, "cards-part-lorebook");
  const loreNote = el("p", "field-note", lorePart);

  const greeting = el("details", "cards-fold", box);
  greeting.id = "cards-greeting";
  const greetingSummary = el("summary", "", greeting);
  const greetingHint = el("p", "field-note", greeting);
  const greetingText = el("p", "cards-quote", greeting);
  const greetingMore = el("p", "field-note", greeting);
  const notes = el("details", "cards-fold", box);
  notes.id = "cards-creator-notes";
  const notesSummary = el("summary", "", notes);
  const notesHint = el("p", "field-note", notes);
  const notesText = el("p", "cards-quote", notes);

  const applyError = el("div", "error", box);
  applyError.id = "cards-apply-error";
  applyError.setAttribute("role", "alert");
  applyError.hidden = true;
  const actions = el("div", "card-actions", box);
  const cancelButton = button("quiet", actions, "cards-cancel");
  const useButton = button("primary", actions, "cards-use");

  // ---- saving a card
  const exportTitle = el("h3", "cards-subtitle", card);
  const exportHint = el("p", "field-note", card);
  const targetLabel = el("label", "", card);
  targetLabel.htmlFor = "cards-target";
  const target = el("select", "cards-target", card);
  target.id = "cards-target";
  const exportTools = el("div", "cards-tools", card);
  const pngButton = button("secondary", exportTools, "cards-save-png");
  const jsonButton = button("secondary", exportTools, "cards-save-json");
  const exportLine = el("p", "field-note cards-saved", card);
  exportLine.id = "cards-saved";
  exportLine.setAttribute("role", "status");
  const exportError = el("div", "error", card);
  exportError.id = "cards-export-error";
  exportError.setAttribute("role", "alert");
  exportError.hidden = true;

  // ---- the draft, inside the Persona section
  const draftBox = document.createElement("div");
  draftBox.className = "cards-draft";
  draftBox.id = "cards-draft";
  PA.$("persona-text").before(draftBox);
  const ideaLabel = el("label", "", draftBox);
  ideaLabel.htmlFor = "cards-idea";
  const idea = el("input", "", draftBox);
  idea.id = "cards-idea";
  idea.maxLength = 500;
  idea.autocomplete = "off";
  const draftTools = el("div", "cards-tools", draftBox);
  const draftButton = button("secondary", draftTools, "cards-draft-write");
  const undoButton = button("quiet", draftTools, "cards-draft-undo");
  undoButton.hidden = true;
  const draftNote = el("p", "field-note", draftBox);
  const draftError = el("div", "error", draftBox);
  draftError.id = "cards-draft-error";
  draftError.setAttribute("role", "alert");
  draftError.hidden = true;

  function personaLimit() {
    return (preview && preview.personaLimit) || (PA.catalog && PA.catalog.personaLimit) || 16000;
  }
  function renderCount() {
    const n = Array.from(personaInput.value).length;
    personaCount.textContent = t("cards_persona_count", { n });
    const over = n > personaLimit() || !personaInput.value.trim();
    personaCount.classList.toggle("over", n > personaLimit());
    if (n > personaLimit()) personaCount.textContent += " " + t("cards_persona_over", { max: personaLimit() });
    return !over;
  }
  function skipText(skipped) {
    return Object.entries(skipped || {})
      .map(([k, n]) => (PA.t(`cards_skip_${k}`) !== PA.t("generic") ? t(`cards_skip_${k}`, { n }) : t(`lore_skip_${k}`, { n })))
      .join(t("lore_list_sep"));
  }

  function renderPreview() {
    box.hidden = !preview;
    if (!preview) return;
    const p = preview;
    previewTitle.textContent = t("cards_preview", { file: p.file });
    previewLead.textContent = t("cards_preview_lead");
    image.hidden = !p.picture;
    if (p.picture) image.src = p.picture;
    pictureCheck.text.textContent = t("cards_part_picture");
    pictureCheck.box.disabled = !p.picture || !!busy;
    if (!p.picture) pictureCheck.box.checked = false;
    pictureNote.textContent = p.picture ? "" : t(`cards_${p.pictureNote || "picture_none"}`);
    pictureNote.hidden = !!p.picture;

    nameCheck.text.textContent = t("cards_part_name");
    const name = nameInput.value.trim() || p.name;
    const lines = [];
    if (p.nameCut) lines.push(t("cards_name_cut"));
    if (p.oldName && p.oldName !== name && nameCheck.box.checked)
      lines.push(t("cards_name_learned", { old: p.oldName, name }));
    if (p.nickname && p.nickname !== name && nameCheck.box.checked) lines.push(t("cards_nickname", { nick: p.nickname }));
    nameNote.textContent = lines.join(" ");
    nameNote.hidden = !lines.length;
    nameInput.disabled = !nameCheck.box.checked || !!busy;

    personaCheck.text.textContent = t("cards_part_persona");
    personaHint.textContent = t("cards_persona_hint");
    personaInput.disabled = !personaCheck.box.checked || !!busy;
    renderCount();
    personaNotes.replaceChildren();
    if (p.instructions) el("p", "field-note cards-warn", personaNotes, t("cards_persona_instructions"));
    if (p.macros && p.macros.length)
      el("p", "field-note", personaNotes, t("cards_persona_macros", { list: p.macros.map((m) => `{{${m}}}`).join(", ") }));
    if (p.personaOwn) el("p", "field-note", personaNotes, t("cards_persona_backup"));

    examplesCheck.text.textContent = t("cards_part_examples", { n: p.examples });
    examplesCheck.box.disabled = !p.examples || !!busy;
    if (!p.examples) examplesCheck.box.checked = false;
    const ex = [];
    if (!p.examples) ex.push(t("cards_examples_none"));
    else ex.push(t(p.examplesOwn ? "cards_examples_replace_own" : "cards_examples_replace", { path: p.examplesPath }));
    if (p.examplesLeft) ex.push(t("cards_examples_left", { n: p.examplesLeft }));
    examplesNote.textContent = ex.join(" ");

    loreCheck.text.textContent = t("cards_part_lore", { n: p.lore });
    loreCheck.box.disabled = !p.lore || !!busy;
    if (!p.lore) loreCheck.box.checked = false;
    const lo = [];
    if (!p.lore) lo.push(t("cards_lore_none"));
    else lo.push(t(p.loreOwn ? "cards_lore_replace_own" : "cards_lore_replace", { path: p.lorePath }));
    const skipped = skipText(p.loreSkipped);
    if (skipped) lo.push(t("lore_skipped", { list: skipped }));
    for (const [k, n] of Object.entries(p.lorePartly || {}))
      lo.push(k === "decorators" ? t("cards_partly_decorators", { n }) : t(`lore_partly_${k}`, { n }));
    loreNote.textContent = lo.join(" ");

    greeting.hidden = !p.greeting;
    greetingSummary.textContent = t("cards_greeting");
    greetingHint.textContent = t("cards_greeting_hint");
    greetingText.textContent = p.greeting || "";
    greetingMore.textContent = p.alternates ? t("cards_greeting_more", { n: p.alternates }) : "";
    greetingMore.hidden = !p.alternates;
    notes.hidden = !p.creatorNotes;
    notesSummary.textContent = t("cards_creator_notes");
    notesHint.textContent = t("cards_creator_hint");
    notesText.textContent = p.creatorNotes || "";

    cancelButton.textContent = t("cards_cancel");
    useButton.textContent = busy === "apply" ? t("cards_using") : t("cards_use");
    for (const node of [nameCheck.box, personaCheck.box, cancelButton, useButton]) node.disabled = !!busy;
    retell(applyError);
  }

  function render() {
    title.textContent = t("cards_title");
    lead.textContent = t("cards_lead");
    importButton.textContent = busy === "read" ? t("cards_reading") : t("cards_import");
    importButton.disabled = !!busy;
    importHint.textContent = t("cards_import_hint");
    exportTitle.textContent = t("cards_export_title");
    exportHint.textContent = t("cards_export_hint");
    targetLabel.textContent = t("cards_export_to");
    const chosen = target.value;
    target.replaceChildren();
    for (const item of (overview && overview.targets) || []) {
      const option = el("option", "", target, t(`cards_target_${item.id}`));
      option.value = item.id;
    }
    if ([...target.options].some((o) => o.value === chosen)) target.value = chosen;
    // From another device there is no folder of this computer to save into.
    const remote = Boolean(PA.state && PA.state.remote);
    const none = remote || (overview && !overview.targets.length);
    target.hidden = targetLabel.hidden = !!none;
    exportTools.hidden = remote;
    pngButton.textContent = busy === "png" ? t("cards_saving") : t("cards_save_png");
    jsonButton.textContent = busy === "json" ? t("cards_saving") : t("cards_save_json");
    for (const node of [pngButton, jsonButton, target]) node.disabled = !!busy || !!none || !overview;
    if (remote) exportLine.textContent = t("local_only");
    else if (none && !exportLine.dataset.path) exportLine.textContent = t("cards_no_targets");
    else if (exportLine.dataset.path) exportLine.textContent = t("cards_saved", { path: exportLine.dataset.path });
    else exportLine.textContent = "";
    ideaLabel.textContent = t("cards_draft_label");
    idea.placeholder = t("cards_draft_placeholder");
    draftButton.textContent = busy === "draft" ? t("cards_drafting") : t("cards_draft");
    draftButton.disabled = !!busy;
    idea.disabled = busy === "draft";
    undoButton.textContent = t("cards_draft_undo");
    draftNote.textContent = t("cards_draft_note");
    for (const node of [error, exportError, draftError]) retell(node);
    renderPreview();
  }

  // ---- import
  importButton.addEventListener("click", () => {
    showError(error, "");
    picker.value = "";
    picker.click();
  });
  picker.addEventListener("change", async () => {
    const file = picker.files && picker.files[0];
    picker.value = "";
    if (!file) return;
    showError(error, "");
    if (file.size > MAX_FILE) {
      showError(error, "card_too_large");
      return;
    }
    busy = "read";
    render();
    try {
      const found = await PA.upload("cards/read", file);
      preview = { ...found, file: file.name };
      nameInput.value = found.name;
      personaInput.value = found.persona;
      for (const part of [nameCheck, personaCheck, pictureCheck, examplesCheck, loreCheck]) part.box.checked = true;
      showError(applyError, "");
    } catch (failure) {
      preview = null;
      showError(error, failure.message);
    } finally {
      busy = "";
      render();
    }
    if (preview) {
      previewTitle.focus();
      box.scrollIntoView({ block: "start", behavior: "smooth" });
    } else importButton.focus();
  });
  for (const part of [nameCheck, personaCheck, pictureCheck, examplesCheck, loreCheck])
    part.box.addEventListener("change", renderPreview);
  nameInput.addEventListener("input", renderPreview);
  personaInput.addEventListener("input", renderCount);

  cancelButton.addEventListener("click", async () => {
    preview = null;
    render();
    importButton.focus();
    try {
      await PA.api("cards/cancel", {});
    } catch {
      /* the next import replaces it anyway */
    }
  });

  useButton.addEventListener("click", async () => {
    if (busy || !preview) return;
    showError(applyError, "");
    const parts = [
      [nameCheck, "name"],
      [personaCheck, "persona"],
      [examplesCheck, "examples"],
      [loreCheck, "lorebook"],
      [pictureCheck, "picture"],
    ]
      .filter(([part]) => part.box.checked && !part.box.disabled)
      .map(([, id]) => id);
    if (!parts.length) {
      showError(applyError, "card_nothing");
      return;
    }
    if (parts.includes("persona") && !renderCount()) {
      showError(applyError, "card_persona");
      personaInput.focus();
      return;
    }
    busy = "apply";
    render();
    let result;
    try {
      result = await PA.api("cards/apply", { id: preview.id, parts, name: nameInput.value, persona: personaInput.value });
    } catch (failure) {
      busy = "";
      if (failure.message === "card_expired") preview = null;
      showError(failure.message === "card_expired" ? error : applyError, failure.message);
      render();
      useButton.focus();
      return;
    }
    busy = "";
    preview = null;
    render();
    const said = [t(result.restarted ? "cards_used" : "cards_used_later")];
    if (result.backups.length) said.push(t("cards_kept", { files: result.backups.map(fileName).join(", ") }));
    if ((result.notes || []).includes("card_aliases_unreadable")) said.push(t("cards_used_aliases"));
    try {
      await PA.reload();
      await PA.reloadPersona();
      PA.showView("settings");
    } catch {
      /* the toast still says what changed */
    }
    PA.toast(said.join(" "));
    importButton.focus();
  });

  // ---- export
  async function save(kind, node) {
    if (busy) return;
    showError(exportError, "");
    delete exportLine.dataset.path;
    busy = kind;
    render();
    try {
      const done = await PA.api("cards/export", { to: target.value, format: kind });
      exportLine.dataset.path = done.path;
    } catch (failure) {
      showError(exportError, failure.message);
    } finally {
      busy = "";
      render();
      node.focus();
    }
  }
  pngButton.addEventListener("click", () => save("png", pngButton));
  jsonButton.addEventListener("click", () => save("json", jsonButton));

  // ---- the draft
  draftButton.addEventListener("click", async () => {
    if (busy) return;
    showError(draftError, "");
    const text = idea.value.trim();
    if (!text) {
      showError(draftError, "draft_idea");
      idea.focus();
      return;
    }
    busy = "draft";
    render();
    try {
      const done = await PA.api("cards/draft", { idea: text });
      beforeDraft = PA.personaText;
      draftText = done.text;
      PA.putPersona(done.text);
      undoButton.hidden = false;
      PA.toast(t("cards_drafted"));
    } catch (failure) {
      showError(draftError, failure.message);
    } finally {
      busy = "";
      render();
      draftButton.focus();
    }
  });
  idea.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      draftButton.click();
    }
  });
  undoButton.addEventListener("click", () => {
    if (beforeDraft === null) return;
    PA.putPersona(beforeDraft);
    beforeDraft = draftText = null;
    undoButton.hidden = true;
    PA.toast(t("cards_draft_restored"));
    PA.$("persona-text").focus();
  });
  // Edited or saved since: the earlier text is no longer one step back.
  PA.$("persona-text").addEventListener("input", () => {
    if (draftText !== null && PA.personaText !== draftText) {
      beforeDraft = draftText = null;
      undoButton.hidden = true;
    }
  });
  PA.$("persona-save").addEventListener("click", () => {
    beforeDraft = draftText = null;
    undoButton.hidden = true;
  });

  async function load() {
    try {
      overview = await PA.api("cards");
    } catch (failure) {
      showError(exportError, failure.message);
    }
    render();
  }
  function visible() {
    const on = !!(PA.state && PA.state.configured && PA.view === "settings");
    root.hidden = !on;
    return on;
  }
  PA.onShow("settings", () => {
    if (visible() && !overview) load();
  });
  PA.onState(() => visible());
  PA.onLanguage(render);
  render();
})();
