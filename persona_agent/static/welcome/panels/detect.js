// The detect panel: before a key is set, offer what this computer already has,
// a local model server that is running or a model key in the environment.
PA.strings({
  en: {
    detect_local: "{name} is running on this computer. It needs no key, and nothing leaves the computer.",
    detect_localModel: "Model: {model}.",
    detect_localMore: "Model: {model} ({more} more; the model can be changed afterwards under Model name and address).",
    detect_useLocal: "Use {name}",
    detect_key: "A {provider} key is set on this computer, in the environment variable {variable}.",
    detect_useKey: "Use this key",
    detect_fromVariable: "From {variable}",
    detect_starting: "Verifying…",
  },
  zh: {
    detect_local: "检测到本机正在运行 {name}。使用本机模型无需密钥，聊天内容不会离开本机。",
    detect_localModel: "模型：{model}。",
    detect_localMore: "模型：{model}（另有 {more} 个；之后可在「模型名称与服务地址」中更改）。",
    detect_useLocal: "使用 {name}",
    detect_key: "检测到本机的环境变量 {variable} 中已有 {provider} 的密钥。",
    detect_useKey: "使用此密钥",
    detect_fromVariable: "来自 {variable}",
    detect_starting: "正在验证…",
  },
});
(() => {
  const { $, t } = PA;
  let found = null;
  let asked = false;
  // The provider whose key comes from the environment; another choice lets go of it.
  let taken = "";
  // What the offers were last built from: the page's state arrives every few
  // seconds, and a rebuilt button would lose a click or the keyboard's place.
  let shown = "";

  const box = document.createElement("div");
  box.id = "detect-box";
  box.className = "detect-box";
  box.hidden = true;
  $("settings-form").querySelector(".card-heading").after(box);

  function providerName(id) {
    const option = [...$("provider").options].find((o) => o.value === id);
    return option ? option.textContent : id;
  }
  function release() {
    delete $("api-key").dataset.from;
    taken = "";
  }
  function choose(provider) {
    $("provider").value = provider;
    $("provider").dispatchEvent(new Event("change"));
  }
  function start(button) {
    for (const other of box.querySelectorAll("button")) other.disabled = true;
    button.textContent = t("detect_starting");
    $("settings-form").requestSubmit();
    // The form reports what happened; its button is free again when it has.
    const wait = setInterval(() => {
      if ($("save").disabled) return;
      clearInterval(wait);
      render(true);
    }, 200);
  }
  function useLocal(row, button) {
    choose(row.provider);
    $("base-url").value = row.baseUrl;
    $("model").value = row.models[0];
    $("model").dispatchEvent(new Event("input"));
    // A local server takes any key; the form of another service asks for one.
    if (row.provider !== "ollama") $("api-key").value = row.id;
    start(button);
  }
  function useKey(row, button) {
    choose(row.provider);
    $("api-key").value = "";
    $("api-key").dataset.from = row.variable;
    $("api-key").placeholder = t("detect_fromVariable", { variable: row.variable });
    $("api-key").required = false;
    taken = row.provider;
    start(button);
  }
  function offer(text, label, act) {
    const row = document.createElement("div");
    row.className = "detect-row";
    const said = document.createElement("span");
    said.className = "detect-text";
    said.textContent = text;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary detect-use";
    button.textContent = label;
    button.addEventListener("click", () => act(button));
    row.append(said, button);
    return row;
  }
  function render(again = false) {
    const state = PA.state;
    const offered = Boolean(found && state && !state.configured);
    const now = offered ? PA.lang + JSON.stringify(found) : "";
    if (now === shown && !again) return;
    shown = now;
    box.replaceChildren();
    if (!offered) {
      box.hidden = true;
      return;
    }
    for (const row of found.local) {
      const model = row.models.length > 1
        ? t("detect_localMore", { model: row.models[0], more: String(row.models.length - 1) })
        : t("detect_localModel", { model: row.models[0] });
      box.append(offer(
        t("detect_local", { name: row.name }) + (["zh", "zh-TW", "ja"].includes(PA.lang) ? "" : " ") + model,
        t("detect_useLocal", { name: row.name }),
        (button) => useLocal(row, button),
      ));
    }
    for (const row of found.keys)
      box.append(offer(
        t("detect_key", { provider: providerName(row.provider), variable: row.variable }),
        t("detect_useKey"),
        (button) => useKey(row, button),
      ));
    box.hidden = !box.children.length;
  }

  $("provider").addEventListener("change", () => {
    if (taken && $("provider").value !== taken) release();
  });
  $("api-key").addEventListener("input", release);

  PA.onState(async (state) => {
    if (state.configured) {
      release();
      render();
      return;
    }
    if (!asked) {
      asked = true;
      try {
        found = await PA.api("detect");
      } catch {
        found = null;
      }
    }
    render();
  });
  PA.onLanguage(() => render());
})();
