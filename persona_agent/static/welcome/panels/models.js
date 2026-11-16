// The models panel: once a key works, the model field offers the models the
// saved service lists. Any name can still be typed.
PA.strings({
  en: {
    models_count: "{count} models are available from this service. Type to filter the list, or enter any model name.",
    models_free: "Free",
    models_freeOnly: "Free models only ({count})",
  },
  zh: {
    models_count: "此服务提供 {count} 个模型。输入文字可筛选列表，也可直接填写任意模型名称。",
    models_free: "免费",
    models_freeOnly: "仅显示免费模型（{count} 个）",
  },
});
(() => {
  const { $, t } = PA;
  let listed = null;
  let asked = "";
  let shown = "";

  const list = document.createElement("datalist");
  list.id = "model-list";
  const note = document.createElement("p");
  note.className = "field-note models-note";
  note.hidden = true;
  const freeOnly = document.createElement("label");
  freeOnly.className = "check models-free";
  freeOnly.hidden = true;
  const box = document.createElement("input");
  box.type = "checkbox";
  box.id = "models-free-only";
  const words = document.createElement("span");
  freeOnly.append(box, words);
  $("model").after(list, note, freeOnly);

  // The listing belongs to the saved service; another one typed in the form has its own models.
  const matches = () =>
    listed &&
    PA.state?.configured &&
    $("provider").value === PA.state.provider &&
    $("base-url").value.replace(/\/$/, "") === (listed.baseUrl || "").replace(/\/$/, "");

  function render() {
    const on = Boolean(matches() && listed.models && listed.models.length);
    const models = on ? listed.models : [];
    const free = models.filter((m) => m.free);
    const only = box.checked && free.length > 0;
    const now = [on, PA.lang, only, models.length, listed?.baseUrl].join("|");
    if (now === shown) return;
    shown = now;
    if (!on) {
      $("model").removeAttribute("list");
      list.replaceChildren();
      note.hidden = true;
      freeOnly.hidden = true;
      return;
    }
    list.replaceChildren(
      ...(only ? free : models).map((m) => {
        const option = document.createElement("option");
        option.value = m.id;
        if (m.free) option.label = t("models_free");
        return option;
      }),
    );
    $("model").setAttribute("list", "model-list");
    note.textContent = t("models_count", { count: String(models.length) });
    note.hidden = false;
    freeOnly.hidden = !free.length;
    words.textContent = t("models_freeOnly", { count: String(free.length) });
  }

  async function load(force = false) {
    const state = PA.state;
    if (!state?.configured) {
      listed = null;
      asked = "";
      render();
      return;
    }
    // Asked again when the saved service or model changed: a new key comes with a save.
    const key = `${state.provider}|${state.baseUrl}|${state.model}`;
    if (key === asked && !force) return render();
    asked = key;
    try {
      listed = await PA.api("models");
    } catch {
      listed = null;
    }
    render();
  }

  box.addEventListener("change", render);
  for (const id of ["provider", "base-url"]) $(id).addEventListener("change", render);
  $("base-url").addEventListener("input", render);
  PA.onState(() => load());
  PA.onShow("settings", () => load(true));
  PA.onLanguage(() => {
    shown = "";
    render();
  });
})();
