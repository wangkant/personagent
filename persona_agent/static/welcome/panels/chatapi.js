// The chatapi panel: the OpenAI-compatible API. See PA at the end of welcome.js.
PA.strings({
  en: {
    chatapi_title: "Other software",
    chatapi_hint: "Use {name} in any app that accepts an OpenAI-compatible address, such as Open WebUI, SillyTavern or a script of your own.",
    chatapi_about: "The other app sends each message to {name}, who answers with the same character and memory as everywhere else. The app's own system prompt, earlier messages and model settings are not used: only the newest message counts. Replies are text only.",
    chatapi_switch: "Turn on the OpenAI-compatible API",
    chatapi_state_on: "On",
    chatapi_state_off: "Off",
    chatapi_turning_on: "The API is turned on.",
    chatapi_turning_off: "The API is turned off.",
    chatapi_restarted: "The character was restarted to apply the change.",
    chatapi_values: "Enter these three values in the other app:",
    chatapi_address: "Address (base URL)",
    chatapi_key: "API key",
    chatapi_model: "Model",
    chatapi_show: "Show",
    chatapi_hide: "Hide",
    chatapi_copy_address: "Copy address",
    chatapi_copy_key: "Copy key",
    chatapi_copy_model: "Copy model name",
    chatapi_copied: "Copied.",
    chatapi_copy_failed: "The text could not be copied automatically. It is selected; copy it with the keyboard.",
    chatapi_new_key: "Create a new key",
    chatapi_new_key_ask: "A new key will be created. The current key stops working at once, so every app that uses it must be given the new one. Continue?",
    chatapi_new_key_yes: "Create a new key",
    chatapi_new_key_done: "A new key was created. Enter it in every app that uses this API.",
    chatapi_working: "Saving…",
    chatapi_running: "The character is running, so the address answers now.",
    chatapi_not_running: "The character is not running. The address answers only while personagent runs; sending a test message starts it.",
    chatapi_local: "Only programs on this computer can reach this address. To use it from a phone or another computer, see the guide.",
    chatapi_test_label: "Test message",
    chatapi_test_default: "Hello",
    chatapi_test: "Send a test message",
    chatapi_testing: "Waiting for the answer…",
    chatapi_test_reply: "{name} replied through the API:",
    chatapi_test_empty: "The API works, but {name} chose not to answer this message.",
    chatapi_test_note: "The test uses a conversation of its own, which appears in Activity.",
    chatapi_howto: "How to enter the values in common apps",
    chatapi_howto_webui: "Open WebUI: as an administrator, open Settings > Connections. Under Manage OpenAI API Connections, select Add Connection, enter the address in URL and the key in API Key, then select Save. If Open WebUI runs in Docker, 127.0.0.1 is the container itself; see the guide.",
    chatapi_howto_tavern: "SillyTavern: in API Connections, set the API type to Chat Completion and Chat Completion Source to Custom (OpenAI-compatible). Enter the address as the endpoint URL and the key as the API key, choose personagent as the model, then select Test Message.",
    chatapi_howto_script: "A program of your own: send each message as a POST request to the address followed by /chat/completions, with the header Authorization: Bearer and the key. The guide has examples in curl and Python.",
    chatapi_howto_user: "Each value of the request's user field is a conversation of its own; requests without it share one.",
    chatapi_loading: "Reading the API settings…",
    chatapi_load_failed: "The API settings could not be read.",
    chatapi_bad_request: "Enter a test message of at most 500 characters.",
    chatapi_no_key: "There is no key yet. Turn the API on to create one.",
    chatapi_write_failed: "The settings file could not be written. Close any program that is using it, then try again.",
    chatapi_off: "The API is turned off. Turn it on first.",
    chatapi_not_started: "The character could not be started. Check the model settings, then try again.",
    chatapi_unreachable: "The character's service did not respond at this address.",
    chatapi_timeout: "The character did not answer within three minutes.",
    chatapi_stale: "The running character was started without the API. Turn the API off and on again to restart it.",
    chatapi_key_rejected: "The running character does not accept this key. Turn the API off and on again to restart it.",
    chatapi_character_off: "The character is turned off or has no model key, so it cannot answer. Check the model settings.",
    chatapi_busy: "The character is answering as many conversations as it can. Try again in a few seconds.",
    chatapi_model_failed: "The model service did not answer. Check the model settings, or try again later.",
    chatapi_not_admitted: "The access settings do not admit API conversations: the list of people it replies to in private chats names other API users only.",
    chatapi_failed: "The test did not succeed. The character's log, runtime/desktop/agent.log in the home folder, has the details.",
  },
  zh: {
    chatapi_title: "其他软件",
    chatapi_hint: "在任何可填写 OpenAI 兼容地址的软件中使用{name}，例如 Open WebUI、SillyTavern 或你自己编写的程序。",
    chatapi_about: "其他软件把每条消息发送给{name}，{name}以与其他平台相同的人设和记忆回复。该软件自身的系统提示词、之前的消息和模型参数均不使用，只读取最新的一条消息。回复仅为文字。",
    chatapi_switch: "开启 OpenAI 兼容接口",
    chatapi_state_on: "已开启",
    chatapi_state_off: "未开启",
    chatapi_turning_on: "接口已开启。",
    chatapi_turning_off: "接口已关闭。",
    chatapi_restarted: "已重启角色以应用此更改。",
    chatapi_values: "请在其他软件中填写以下三项：",
    chatapi_address: "地址（Base URL）",
    chatapi_key: "API 密钥",
    chatapi_model: "模型",
    chatapi_show: "显示",
    chatapi_hide: "隐藏",
    chatapi_copy_address: "复制地址",
    chatapi_copy_key: "复制密钥",
    chatapi_copy_model: "复制模型名称",
    chatapi_copied: "已复制。",
    chatapi_copy_failed: "无法自动复制，内容已选中，请使用键盘复制。",
    chatapi_new_key: "生成新密钥",
    chatapi_new_key_ask: "将生成新的密钥。当前密钥会立即失效，所有使用它的软件都须改填新密钥。是否继续？",
    chatapi_new_key_yes: "生成新密钥",
    chatapi_new_key_done: "已生成新密钥。请在所有使用此接口的软件中改填新密钥。",
    chatapi_working: "正在保存…",
    chatapi_running: "角色正在运行，该地址现在可以访问。",
    chatapi_not_running: "角色未在运行。仅在 personagent 运行时可以访问该地址；发送测试消息时会启动角色。",
    chatapi_local: "只有本机上的程序可以访问该地址。如需在手机或其他电脑上使用，请参阅使用指南。",
    chatapi_test_label: "测试消息",
    chatapi_test_default: "你好",
    chatapi_test: "发送测试消息",
    chatapi_testing: "正在等待回复…",
    chatapi_test_reply: "{name}通过接口回复：",
    chatapi_test_empty: "接口工作正常，但{name}选择不回复这条消息。",
    chatapi_test_note: "测试使用单独的对话，该对话会显示在「动态」中。",
    chatapi_howto: "在常用软件中填写的方法",
    chatapi_howto_webui: "Open WebUI：以管理员身份打开 Settings > Connections，在 Manage OpenAI API Connections 中点击 Add Connection，在 URL 中填写地址、在 API Key 中填写密钥，然后点击 Save。如果 Open WebUI 运行在 Docker 中，其中的 127.0.0.1 指向容器自身，请参阅使用指南。",
    chatapi_howto_tavern: "SillyTavern：在 API Connections 中，将 API 类型设为 Chat Completion，将 Chat Completion Source 设为 Custom (OpenAI-compatible)。将地址填入端点 URL，将密钥填入 API 密钥，模型选择 personagent，然后点击 Test Message。",
    chatapi_howto_script: "自己编写的程序：把每条消息以 POST 请求发送到地址后加 /chat/completions，并附带请求头 Authorization: Bearer 加密钥。使用指南中有 curl 和 Python 示例。",
    chatapi_howto_user: "请求中 user 字段的每个值对应一个单独的对话；不带该字段的请求共用一个对话。",
    chatapi_loading: "正在读取接口设置…",
    chatapi_load_failed: "无法读取接口设置。",
    chatapi_bad_request: "请填写不超过 500 个字符的测试消息。",
    chatapi_no_key: "尚未生成密钥。开启接口时会自动生成。",
    chatapi_write_failed: "无法写入设置文件。请关闭正在使用该文件的程序后重试。",
    chatapi_off: "接口未开启，请先开启。",
    chatapi_not_started: "角色未能启动。请检查模型设置后重试。",
    chatapi_unreachable: "角色服务在该地址上没有响应。",
    chatapi_timeout: "角色在三分钟内没有回复。",
    chatapi_stale: "正在运行的角色启动时未开启接口。请关闭接口后重新开启，以重启角色。",
    chatapi_key_rejected: "正在运行的角色不接受此密钥。请关闭接口后重新开启，以重启角色。",
    chatapi_character_off: "角色已关闭或尚未设置模型密钥，无法回复。请检查模型设置。",
    chatapi_busy: "角色同时进行的对话已达上限，请稍后重试。",
    chatapi_model_failed: "模型服务没有回复。请检查模型设置，或稍后重试。",
    chatapi_not_admitted: "访问设置不允许接口对话：私聊回复名单中只列出了其他接口用户。",
    chatapi_failed: "测试未成功。详情见主目录中的角色日志 runtime/desktop/agent.log。",
  },
});
(() => {
  const root = PA.$("chatapi-root");
  let data = null;
  let loadError = false;
  // Kept only while the page is open, and only once the person asked to see it.
  let key = "";
  let shown = false;
  // Keys and codes, translated at render, so they follow a language change.
  let note = "";
  let error = "";
  let testError = "";
  let reply = null;
  let draft = null;
  let howtoOpen = false;
  let returnTo = null;

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const name = () => data?.name || PA.state?.name || "";
  const button = (id, className, label, onClick) => {
    const node = make("button", className, PA.t(label));
    node.type = "button";
    node.id = id;
    node.addEventListener("click", () => onClick(node));
    return node;
  };

  async function load() {
    try {
      data = await PA.api("chatapi");
      loadError = false;
    } catch {
      loadError = true;
    }
    render();
  }

  // Disable the control with an "-ing" label while `work` runs.
  async function busy(node, label, work) {
    const was = node.textContent;
    returnTo = node.id;
    node.disabled = true;
    node.textContent = PA.t(label);
    try {
      await work();
    } finally {
      node.disabled = false;
      if (node.isConnected) node.textContent = was;
    }
  }

  async function toggle(box) {
    const on = box.checked;
    returnTo = box.id;
    box.disabled = true;
    error = note = "";
    reply = null;
    try {
      data = await PA.api("chatapi/switch", { on });
      if (!on) {
        key = "";
        shown = false;
      }
      PA.toast(PA.t(on ? "chatapi_turning_on" : "chatapi_turning_off")
        + (data.restarted ? (["zh", "zh-TW", "ja"].includes(PA.lang) ? "" : " ") + PA.t("chatapi_restarted") : ""));
    } catch (failure) {
      box.checked = !on;
      error = failure.message;
    }
    render();
  }

  async function revealed() {
    if (!key) key = (await PA.api("chatapi/reveal", {})).key;
    return key;
  }

  async function copy(node, value, valueNode) {
    try {
      await navigator.clipboard.writeText(await value());
      PA.toast(PA.t("chatapi_copied"));
    } catch (failure) {
      if (failure?.message && failure.message.startsWith("chatapi_")) {
        error = failure.message;
        render();
        return;
      }
      // The window's own browser may refuse the clipboard: select the text instead.
      if (valueNode) {
        if (valueNode.dataset.secret && !shown) await showKey(true);
        const target = PA.$(valueNode.id);
        if (target) getSelection().selectAllChildren(target);
      }
      PA.toast(PA.t("chatapi_copy_failed"));
    }
    returnTo = node.id;
  }

  async function showKey(on) {
    error = "";
    try {
      if (on) await revealed();
      shown = on;
    } catch (failure) {
      error = failure.message;
    }
    render();
  }

  async function renew(node) {
    if (!(await PA.ask(PA.t("chatapi_new_key_ask"), PA.t("chatapi_new_key_yes")))) return;
    error = note = "";
    await busy(node, "chatapi_working", async () => {
      try {
        data = await PA.api("chatapi/key", {});
        key = "";
        if (shown) await revealed();
        note = "chatapi_new_key_done";
      } catch (failure) {
        error = failure.message;
      }
    });
    render();
  }

  async function sendTest(node, input) {
    testError = "";
    reply = null;
    draft = input.value;
    await busy(node, "chatapi_testing", async () => {
      try {
        reply = (await PA.api("chatapi/test", { text: input.value })).reply;
      } catch (failure) {
        testError = failure.message;
      }
      try {
        data = await PA.api("chatapi");
      } catch {}
    });
    render();
  }

  function errorBox(code, id) {
    const box = make("div", "error", code ? PA.t(code) : "");
    box.id = id;
    box.setAttribute("role", "alert");
    box.hidden = !code;
    return box;
  }

  // One read-only value with its buttons: shown as text, never as a field to type in.
  function valueRow(id, label, text, buttons, secret = false) {
    const row = make("div", "chatapi-row");
    const head = make("span", "chatapi-label", PA.t(label));
    head.id = `${id}-label`;
    const value = make("code", "chatapi-value", text);
    value.id = id;
    value.setAttribute("aria-labelledby", head.id);
    if (secret) value.dataset.secret = "1";
    const actions = make("span", "chatapi-actions");
    actions.append(...buttons(value));
    row.append(head, value, actions);
    return row;
  }

  function copyButton(id, aria, value, valueNode) {
    const node = button(id, "quiet chatapi-copy", "copy", (self) => copy(self, value, valueNode));
    node.setAttribute("aria-label", PA.t(aria));
    return node;
  }

  function values() {
    const part = make("div", "chatapi-values");
    part.append(make("p", "chatapi-lead", PA.t("chatapi_values")));
    part.append(valueRow("chatapi-address", "chatapi_address", data.address, (value) => [
      copyButton("chatapi-copy-address", "chatapi_copy_address", async () => data.address, value)]));
    part.append(valueRow("chatapi-key", "chatapi_key", shown && key ? key : "••••••••••••••••", (value) => {
      const toggle = button("chatapi-show", "quiet", shown ? "chatapi_hide" : "chatapi_show",
        () => showKey(!shown));
      toggle.setAttribute("aria-pressed", String(shown));
      return [toggle, copyButton("chatapi-copy-key", "chatapi_copy_key", revealed, value)];
    }, true));
    part.append(valueRow("chatapi-model", "chatapi_model", data.model, (value) => [
      copyButton("chatapi-copy-model", "chatapi_copy_model", async () => data.model, value)]));
    const actions = make("div", "chatapi-buttons");
    actions.append(button("chatapi-new-key", "quiet", "chatapi_new_key", renew));
    part.append(actions);
    if (note) {
      const done = make("p", "chatapi-done", PA.t(note));
      done.setAttribute("role", "status");
      part.append(done);
    }
    part.append(make("p", "field-note", PA.t(data.running ? "chatapi_running" : "chatapi_not_running")),
      make("p", "field-note", PA.t("chatapi_local")));
    return part;
  }

  function tester() {
    const part = make("div", "chatapi-test");
    const label = make("label", "", PA.t("chatapi_test_label"));
    label.htmlFor = "chatapi-test-text";
    const input = make("input");
    input.id = "chatapi-test-text";
    input.maxLength = 500;
    input.autocomplete = "off";
    input.value = draft ?? PA.t("chatapi_test_default");
    input.addEventListener("input", () => (draft = input.value));
    const go = button("chatapi-test", "secondary", "chatapi_test", (self) => sendTest(self, input));
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !go.disabled) {
        event.preventDefault();
        sendTest(go, input);
      }
    });
    const line = make("div", "chatapi-test-line");
    line.append(input, go);
    part.append(label, line, make("p", "field-note", PA.t("chatapi_test_note")));
    if (reply !== null) {
      const answer = make("div", "chatapi-reply");
      answer.setAttribute("role", "status");
      if (reply) {
        answer.append(make("p", "chatapi-reply-head", PA.t("chatapi_test_reply", { name: name() })),
          make("p", "chatapi-reply-text", reply));
      } else answer.append(make("p", "", PA.t("chatapi_test_empty", { name: name() })));
      part.append(answer);
    }
    part.append(errorBox(testError, "chatapi-test-error"));
    return part;
  }

  function howto() {
    const details = make("details", "chatapi-howto");
    details.id = "chatapi-howto";
    details.open = howtoOpen;
    details.addEventListener("toggle", () => (howtoOpen = details.open));
    const summary = make("summary", "", PA.t("chatapi_howto"));
    summary.id = "chatapi-howto-summary";
    details.append(summary);
    for (const item of ["chatapi_howto_webui", "chatapi_howto_tavern", "chatapi_howto_script", "chatapi_howto_user"])
      details.append(make("p", "field-note", PA.t(item)));
    return details;
  }

  function render() {
    const head = make("div", "group-head chatapi-head");
    head.append(make("h3", "group-title", PA.t("chatapi_title")));
    head.append(make("p", "group-hint", PA.t("chatapi_hint", { name: name() })));
    const parts = [head];
    if (!data) {
      const wait = make("p", "field-note", PA.t(loadError ? "chatapi_load_failed" : "chatapi_loading"));
      wait.setAttribute("role", loadError ? "alert" : "status");
      parts.push(wait);
    } else {
      const box = make("div", "feature chatapi");
      const top = make("div", "feature-head");
      const label = make("label", "check chatapi-switch");
      const check = make("input");
      check.type = "checkbox";
      check.id = "chatapi-switch";
      check.checked = data.enabled;
      check.addEventListener("change", () => toggle(check));
      label.append(check, make("span", "", PA.t("chatapi_switch")));
      const state = make("span", "feature-state chatapi-state", PA.t(data.enabled ? "chatapi_state_on" : "chatapi_state_off"));
      state.classList.toggle("chatapi-on", data.enabled);
      top.append(label, state);
      box.append(top, make("p", "field-note", PA.t("chatapi_about", { name: name() })));
      box.append(errorBox(error, "chatapi-error"));
      if (data.enabled) box.append(values(), tester(), howto());
      parts.push(box);
    }
    // Focus stays on the control the person used.
    const active = document.activeElement;
    const wanted = active && root.contains(active) && active.id ? [active.id, returnTo]
      : !active || active === document.body ? [returnTo] : [];
    returnTo = null;
    root.replaceChildren(...parts);
    for (const id of wanted) {
      const target = id && PA.$(id);
      if (target && root.contains(target)) {
        target.focus();
        break;
      }
    }
  }

  PA.onShow("platforms", load);
  PA.onLanguage(() => data && render());
  render();
})();
